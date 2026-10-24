"""Luma's expressive voice: open-source speech that sounds like a person, with real laughs.

On a Mac with Apple Silicon, Luma can talk with a newer open model running on the Mac itself:
Chatterbox-Turbo (Resemble AI, MIT) or Qwen3-TTS (Alibaba Qwen, Apache-2.0), through mlx-audio.
Both clone a voice from a few seconds of audio, so Luma keeps the voice people already know: the
classic voice reads one short line once, and the new model learns that voice from it. No real
person's voice is copied.

It runs in its own process with its own Python (luma/audio/voice_server.py), downloads in the
background, and the classic voice keeps talking until it's ready, and takes over again if the new
one ever stops. Setting "natural_voice": "auto" (on when this computer can run it), "on" or "off".
"""
from __future__ import annotations

import base64
import json
import os
import platform
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

REF_TEXT = "Hey, it's me. I'm really glad you're here, so tell me everything. I'm listening."
SERVER = Path(__file__).with_name("voice_server.py")
REST_AFTER_FAILURE = 600  # after the new voice stops, the classic one talks for ten minutes before trying again


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
                    raise RuntimeError(message.get("error") or "The new voice couldn't do that.")
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
        """A few seconds of Luma's classic voice, for the new model to learn Luma's voice from."""
        home = _home()
        home.mkdir(parents=True, exist_ok=True)
        path = home / f"luma-ref-{voice}.wav"
        if path.exists() and path.stat().st_size > 20000:
            return path
        from luma.audio import tts
        if not tts.ready():
            return None
        tts.synthesize(REF_TEXT, str(path), voice=voice)
        return path

    def prepare(self, engine="expressive", voice="luma", timeout=3600):
        """Download (the first time) and load the new voice. Runs in the background; the classic voice talks meanwhile."""
        if not supported():
            self.state, self.note = "off", "The new voice needs a Mac with Apple Silicon."
            return self.status()
        if not python_path():
            self.state, self.note = "waiting", "Getting the new voice's tools ready in the background."
            return self.status()
        self.state, self.note = "loading", "Getting Luma's new voice ready (a one-time download)."
        try:
            ref = self.reference(voice)
            if engine == "studio" and not ref:
                engine = "expressive"  # Qwen3 needs a voice to learn from; Chatterbox has its own until then
            result = self._call("load", timeout, engine=engine, ref=str(ref) if ref else None, ref_text=REF_TEXT if ref else None)
            self.engine, self.repo, self.tags, self.rate = result.get("engine"), result.get("repo"), bool(result.get("tags")), int(result.get("rate") or 24000)
            # A first sentence warms it up and tells us how fast it is on this Mac.
            warm = self._call("say", 300, text="Okay, I'm here.")
            self.rtf = warm.get("rtf")
            self.state, self.note = "ready", ""
        except Exception as error:
            self._fail(error)
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
            self.state = "off"  # it will be tried again on the next prepare
        return self.state == "ready"

    def say(self, text, timeout=60):
        """One phrase in the new voice: (16-bit samples, sample rate). Raises if it can't; the caller uses the classic voice."""
        if not self.ready():
            raise RuntimeError("The new voice isn't ready.")
        try:
            message = self._call("say", timeout, text=text)
        except Exception as error:
            self._fail(error)
            raise
        pcm = np.frombuffer(base64.b64decode(message["pcm"]), dtype="<i2").astype(np.int16)
        if not pcm.size:
            raise RuntimeError("The new voice made no sound.")
        self.rtf = message.get("rtf", self.rtf)
        return pcm, int(message.get("rate") or self.rate)

    def status(self):
        return {"supported": supported(), "installed": bool(python_path()), "state": self.state, "engine": self.engine,
                "model": self.repo, "laughs": self.tags, "note": self.note, "speed": self.rtf}


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
