"""Luma's expressive voice: open-source speech that sounds like a person, with real laughs.

On a Mac with Apple Silicon, Luma can talk with a newer open model running on the Mac itself:
Chatterbox-Turbo (Resemble AI, MIT) or Qwen3-TTS (Alibaba Qwen, Apache-2.0), through mlx-audio.
Both clone a voice from a few seconds of audio, so Luma keeps the voice people already know: the
classic voice reads one short paragraph once, and the new model learns that voice from it. No real
person's voice is copied.

It runs in its own process with its own Python (luma/audio/voice_server.py), downloads in the
background, and the classic voice keeps talking until it's ready, and takes over again if the new
one ever stops, garbles a phrase or can't keep up on this Mac.
Setting "natural_voice": "auto" (on when this computer can run it), "on" or "off".
"""
from __future__ import annotations

import base64
import json
import os
import platform
import queue
import re
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

import numpy as np

REF_TEXT = ("Hey, it's me. I'm really glad you're here. So tell me everything, how was your day? "
            "Take your time, I'm listening, and I've got all the time in the world for you.")
REF_SECONDS = 6.0          # Chatterbox needs more than five seconds of a voice to learn it
SERVER = Path(__file__).with_name("voice_server.py")
REST_AFTER_FAILURE = 600   # after the new voice stops, the classic one talks for ten minutes before trying again
RETRIES = 3                # times it comes back on its own in one run, so a broken install can't loop forever
SPEED_LINE = "Alright, so tell me everything that happened today, I'm listening."
MAX_RTF = 0.9              # it has to make speech faster than it talks, or the conversation stalls between phrases
SLOW_FOR = 7 * 86400       # an engine that was too slow on this Mac isn't tried again for a week
ENGINES = ("expressive", "studio")
# Smaller (quantized) builds of each model: a little less detail, a lot faster. Tried when the full one can't keep up.
FASTER = {"expressive": ["mlx-community/chatterbox-turbo-8bit", "mlx-community/chatterbox-turbo-4bit"],
          "studio": ["mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit"]}
TAGS = re.compile(r"\[(?:laugh|chuckle|sigh|cough)\]")


def _seconds(path):
    try:
        with wave.open(str(path)) as clip:
            return clip.getnframes() / float(clip.getframerate() or 1)
    except (OSError, EOFError, wave.Error):
        return 0.0


def sounds_right(text, seconds):
    """Speech models sometimes babble on, or stop partway. Real speech of this text can't be this long or this short."""
    tags = len(TAGS.findall(text or ""))
    n = len(TAGS.sub("", text or "").strip())
    if not n:
        return True
    return n / 60 <= seconds <= 2.0 + n / 5 + 1.5 * tags


def _home():
    from luma.config import MODELS_DIR
    return Path(os.environ.get("LUMA_NATURAL_DIR") or MODELS_DIR / "natural").expanduser()


def python_path():
    """The voice's own Python: from the app's setup, or one pointed at directly (CI, a developer's Mac)."""
    direct = os.environ.get("LUMA_VOICE_PYTHON")
    if direct:
        return Path(direct) if Path(direct).exists() else None
    env = os.environ.get("LUMA_VOICE_ENV")
    if not env:
        return None
    candidate = Path(env) / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    return candidate if candidate.exists() else None


def supported():
    """Apple Silicon only (mlx runs on the Mac's GPU), unless a voice Python is pointed at directly."""
    if os.environ.get("LUMA_VOICE_PYTHON"):
        return True
    return sys.platform == "darwin" and platform.machine() == "arm64"


class CouldntSay(RuntimeError):
    """The voice is running fine but couldn't make this one phrase."""


class NaturalVoice:
    def __init__(self):
        self.proc = None
        self.lines = None
        self.lock = threading.Lock()
        self.ident = 0
        self.state = "off"        # off · waiting (no voice Python yet) · loading · ready · failed
        self.note = ""
        self.engine = None
        self.repo = None
        self.tags = False
        self.rate = 24000
        self.failed_at = 0.0
        self.rtf = None
        self.loader = None
        self.device = None
        self.want = ("expressive", "luma")
        self.retries = 0
        self.strikes = 0          # phrases in a row that didn't come out right
        self.slow_streak = 0      # phrases in a row that took too long to make
        self.tried = []           # each model tried on this Mac, and how fast it was

    # -- the process -------------------------------------------------------------
    def _start(self):
        python = python_path()
        if not python:
            raise FileNotFoundError("The new voice isn't installed on this computer yet.")
        home = _home()
        (home / "hf").mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "HF_HOME": str(home / "hf"), "PYTHONUNBUFFERED": "1", "TOKENIZERS_PARALLELISM": "false",
               "HF_HUB_DISABLE_TELEMETRY": "1"}
        log = open(home / "voice.log", "ab")
        # -I: the voice's Python sees only its own packages, never Luma's folder (so no file there can shadow a library).
        self.proc = subprocess.Popen([str(python), "-I", "-u", str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=log, cwd=str(home), env=env)
        self.lines = queue.Queue()
        proc, lines = self.proc, self.lines

        def read():
            for raw in proc.stdout:
                lines.put(raw)
            lines.put(None)
        threading.Thread(target=read, daemon=True, name="luma-voice-reader").start()

    def _call(self, op, timeout, **fields):
        with self.lock:
            if self.proc is None or self.proc.poll() is not None:
                self._start()
            self.ident += 1
            ident = self.ident
            self.proc.stdin.write((json.dumps({"id": ident, "op": op, **fields}) + "\n").encode())
            self.proc.stdin.flush()
            deadline = time.time() + timeout
            while True:
                left = deadline - time.time()
                if left <= 0:
                    self._kill()
                    raise TimeoutError("The new voice took too long.")
                try:
                    raw = self.lines.get(timeout=min(left, 0.5))
                except queue.Empty:
                    continue
                if raw is None:
                    self._kill()
                    raise RuntimeError("The new voice stopped unexpectedly.")
                try:
                    message = json.loads(raw)
                except ValueError:
                    continue
                if message.get("id") != ident:
                    continue
                if not message.get("ok"):
                    raise CouldntSay(message.get("error") or "The new voice couldn't do that.")
                return message

    def _kill(self):
        if self.proc is not None:
            try:
                self.proc.kill()
                self.proc.wait(3)
            except Exception:
                pass
        self.proc = None

    def stop(self):
        with self.lock:
            self._kill()
        self.state = "off"

    # -- getting ready -------------------------------------------------------------
    def reference(self, voice="luma"):
        """About ten seconds of Luma's classic voice, for the new model to learn Luma's voice from."""
        home = _home()
        home.mkdir(parents=True, exist_ok=True)
        path = home / f"luma-ref-2-{voice}.wav"
        if path.exists() and _seconds(path) >= REF_SECONDS:
            return path
        from luma.audio import tts
        if not tts.ready():
            return None
        tts.synthesize(REF_TEXT, str(path), voice=voice)
        return path

    # -- how fast it runs on this Mac -------------------------------------------------
    def _speeds(self):
        try:
            return json.loads((_home() / "speed.json").read_text())
        except (OSError, ValueError):
            return {}

    def _remember_speed(self, engine, rtf):
        if rtf is None:
            return
        speeds = self._speeds()
        speeds[engine] = {"rtf": rtf, "at": time.time()}
        try:
            (_home() / "speed.json").write_text(json.dumps(speeds))
        except OSError:
            pass

    def too_slow_here(self, engine):
        seen = self._speeds().get(engine) or {}
        return bool(seen) and seen.get("rtf", 0) > MAX_RTF and time.time() - seen.get("at", 0) < SLOW_FOR

    def prepare(self, engine="expressive", voice="luma", timeout=3600):
        """Download (the first time) and load the new voice. Runs in the background; the classic voice talks meanwhile.

        Tries the engine they picked first, then the other one, and keeps the first that loads and can keep up
        with a conversation on this Mac. If neither can, the classic voice keeps talking."""
        self.want = (engine, voice)
        if not supported():
            self.state, self.note = "off", "The new voice needs a Mac with Apple Silicon."
            return self.status()
        if not python_path():
            self.state, self.note = "waiting", "Getting the new voice's tools ready in the background."
            return self.status()
        self.state, self.note = "loading", "Getting Luma's new voice ready (a one-time download)."
        try:
            ref = self.reference(voice)
        except Exception as error:
            self._fail(error)
            return self.status()
        slow, last, self.tried = [], None, []
        for candidate in [engine] + [e for e in ENGINES if e != engine]:
            if candidate == "studio" and not ref:
                continue  # Qwen3 needs a voice to learn from; Chatterbox has its own until then
            if self.too_slow_here(candidate):
                slow.append(candidate)
                continue
            best = None
            for repos in [None] + ([FASTER[candidate]] if FASTER.get(candidate) else []):  # the full model, then its smaller builds
                try:
                    result = self._call("load", timeout, engine=candidate, ref=str(ref) if ref else None, ref_text=REF_TEXT if ref else None,
                                        **({"repos": repos} if repos else {}))
                    self._call("say", 300, text="Okay, I'm here.")  # the first sentence warms it up
                    timed = self._call("say", 300, text=SPEED_LINE)
                except Exception as error:
                    last = error
                    with self.lock:
                        self._kill()  # the next try starts in a fresh process
                    continue
                rtf = timed.get("rtf")
                self.tried.append({"model": result.get("repo"), "speed": rtf})
                if rtf is None or rtf <= MAX_RTF:
                    self._remember_speed(candidate, rtf)
                    self.engine, self.repo, self.tags = result.get("engine"), result.get("repo"), bool(result.get("tags"))
                    self.rate, self.device, self.rtf = int(result.get("rate") or 24000), result.get("device"), rtf
                    self.strikes = self.slow_streak = 0
                    self.state, self.note = "ready", ""
                    return self.status()
                best = rtf if best is None else min(best, rtf)
                with self.lock:
                    self._kill()
            if best is not None:
                self._remember_speed(candidate, best)
                slow.append(candidate)
        if slow:
            self.state = "slow"
            self.note = "This Mac can't make the new voice fast enough for a conversation yet, so Luma is using her classic voice."
            return self.status()
        self._fail(last or RuntimeError("The new voice couldn't keep up on this Mac."))
        return self.status()

    def prepare_in_background(self, engine="expressive", voice="luma", delay=20):
        if self.loader and self.loader.is_alive():
            return
        def run():
            time.sleep(delay)  # let the brain load first
            # The app installs the voice's tools in the background after setup: wait for them (up to a few hours).
            for _ in range(360):
                if not supported() or python_path():
                    break
                self.state, self.note = "waiting", "Getting the new voice's tools ready in the background."
                time.sleep(60)
            self.prepare(engine, voice)
        self.loader = threading.Thread(target=run, daemon=True, name="luma-voice-loader")
        self.loader.start()

    def _fail(self, error):
        self.state = "failed"
        self.failed_at = time.time()
        self.note = (str(error) or type(error).__name__)[:300]
        with self.lock:
            self._kill()

    # -- talking -------------------------------------------------------------
    def ready(self):
        if self.state == "failed" and time.time() - self.failed_at > REST_AFTER_FAILURE:
            self.state = "off"
            if self.retries < RETRIES:  # rested: try the new voice again in the background
                self.retries += 1
                self.prepare_in_background(*self.want, delay=0)
        return self.state == "ready"

    def say(self, text, timeout=60):
        """One phrase in the new voice: (16-bit samples, sample rate). Raises if it can't; the caller uses the classic voice."""
        if not self.ready():
            raise RuntimeError("The new voice isn't ready.")
        try:
            message = self._call("say", timeout, text=text)
        except CouldntSay:
            self._strike()  # one phrase it couldn't make: the classic voice says it
            raise
        except Exception as error:  # it crashed or hung: the classic voice takes over for a while
            self._fail(error)
            raise
        pcm = np.frombuffer(base64.b64decode(message["pcm"]), dtype="<i2").astype(np.int16)
        rate = int(message.get("rate") or self.rate)
        if not pcm.size or not sounds_right(text, pcm.size / rate):
            self._strike()
            raise RuntimeError("That phrase didn't come out right.")
        self.strikes = 0
        self.rtf = message.get("rtf", self.rtf)
        self.slow_streak = self.slow_streak + 1 if (self.rtf or 0) > MAX_RTF * 1.6 else 0
        if self.slow_streak >= 3:  # this one is fine, but it's making people wait: the classic voice takes over
            self._remember_speed(self.engine, self.rtf)
            self._fail(RuntimeError("The new voice got too slow on this Mac."))
        return pcm, rate

    def _strike(self):
        """This phrase goes to the classic voice. Three in a row and the classic voice takes over for a while."""
        self.strikes += 1
        if self.strikes >= 3:
            self._fail(RuntimeError("The new voice kept garbling its words."))

    def status(self):
        return {"supported": supported(), "installed": bool(python_path()), "state": self.state, "engine": self.engine,
                "model": self.repo, "laughs": self.tags, "note": self.note, "speed": self.rtf, "device": self.device, "tried": self.tried}


_voice = None
_voice_lock = threading.Lock()


def voice():
    global _voice
    with _voice_lock:
        if _voice is None:
            _voice = NaturalVoice()
        return _voice


def active():
    """Is the new voice the one talking right now, and can it laugh?"""
    return _voice is not None and _voice.ready() and _voice.tags


def speaking():
    """Is the new voice the one talking right now (laughing or not)?"""
    return _voice is not None and _voice.ready()
