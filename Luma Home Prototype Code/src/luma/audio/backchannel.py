"""Back-and-forth like a person: a soft "mm-hm" while they talk, and talking over Luma when it's safe.

When someone talks for a while, a listener makes small sounds at their pauses so they know they're heard. PauseWatch
spots those moments in the mic audio (a short pause inside a long turn, shorter than the end of the turn), and Luma
says "mm-hm" or "uh-huh" quietly. Those sounds never become part of what the person said: clean() takes them out of
the transcript.

Talking over Luma needs a mic that doesn't hear Luma's own voice. With headphones, or a mic array that cancels echo
(like the one planned for the Luma device), that's true, so barge-in turns on by itself there. On open speakers it
stays off unless the owner turns it on.
"""
from __future__ import annotations

import random
import re
import threading
import time

import numpy as np

SOUNDS = ["Mm-hm.", "Mhm.", "Uh-huh.", "Mm-hm."]
# The listening sounds, wherever they ended up in the transcript (the mic hears Luma's own "mm-hm" on speakers).
CLEAN = re.compile(r"(?<![\w'-])(?:m+-?h+m+|m+h+m+|uh-? ?huh|mm+)(?![\w'-])[,.!?]*", re.I)
HEADPHONES = re.compile(r"airpods|headphone|headset|earbud|earphone|\bbuds\b|beats|bose qc|qc ?(?:35|45|ultra)|wh-1000|wf-1000|jabra elite|"
                        r"galaxy buds|pixel buds|powerbeats", re.I)
ECHO_CANCELLING = re.compile(r"respeaker|xvf3\d+|xmos|speakerphone|jabra speak|powerconf|conference", re.I)


class PauseWatch:
    """Fed the mic audio a chunk at a time while someone talks. feed() says True when a "mm-hm" would land naturally:
    they've been talking a while and just paused briefly, and Luma hasn't said one in the last few seconds."""

    def __init__(self, rate=16000, chunk=512, after_talking=4.0, pause=0.35, gap=6.0, quiet_level=350, clock=time.monotonic):
        self.step = chunk / rate
        self.after_talking, self.pause, self.gap, self.quiet_level, self.clock = after_talking, pause, gap, quiet_level, clock
        self.last = float("-inf")
        self.start()

    def start(self):
        """A new turn began."""
        self.talked, self.quiet = 0.0, 0.0

    def feed(self, chunk):
        samples = np.asarray(chunk, dtype=np.float32)
        level = float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0
        if level < self.quiet_level:
            self.quiet += self.step
        else:
            self.talked += self.step
            self.quiet = 0.0
        moment = (self.talked >= self.after_talking and self.pause <= self.quiet < self.pause + self.step
                  and self.clock() - self.last >= self.gap)
        if moment:
            self.last = self.clock()
        return moment


def clean(text):
    """What they said, without the listening sounds the mic may have caught. A plain "mhm" on its own is their answer (yes), so it stays:
    Luma only says one while they're mid-turn, so its own never arrives alone."""
    if not isinstance(text, str) or not CLEAN.search(text):
        return text
    out = re.sub(r"\s+([,.!?])", r"\1", re.sub(r"\s{2,}", " ", CLEAN.sub("", text))).strip(" ,")
    out = re.sub(r"^[.!?]+\s*", "", out)
    return out[:1].upper() + out[1:] if re.search(r"\w", out) else text.strip()


def safe_to_talk_over(output_name="", input_name=""):
    """Can Luma hear the owner over its own voice? Headphones out, or a mic that cancels echo."""
    return bool(HEADPHONES.search(output_name or "") or HEADPHONES.search(input_name or "") or ECHO_CANCELLING.search(input_name or ""))


def device_names():
    """The names of the output and input Luma is using right now ("" when there's no sound system)."""
    try:
        import os
        import sounddevice as sd
        from luma.hardware.device import resolve_audio_device
        devices = sd.query_devices()
        names = []
        for direction, env, kind in (("output", "LUMA_OUTPUT_DEVICE", "output"), ("input", "LUMA_INPUT_DEVICE", "input")):
            index = resolve_audio_device(os.getenv(env), devices, direction=direction)
            names.append(str((devices[index] if index is not None else sd.query_devices(kind=kind)).get("name", "")))
        return names[0], names[1]
    except Exception:
        return "", ""


_cache, _lock = {}, threading.Lock()


def say_softly(voice="luma", volume=0.45):
    """One quiet "mm-hm", in Luma's voice, without waiting for it to finish."""
    def run():
        if not _lock.acquire(blocking=False):
            return  # one at a time
        try:
            import sounddevice as sd
            from luma.audio import tts
            word = random.choice(SOUNDS)
            if word not in _cache:
                pcm, rate = tts._samples(word, voice, None)
                _cache[word] = (np.asarray(pcm, dtype=np.float32) / 32767.0 * volume, rate)
            audio, rate = _cache[word]
            sd.play(audio, rate, blocking=True)
        except Exception:
            pass  # a missed "mm-hm" is fine
        finally:
            _lock.release()
    threading.Thread(target=run, name="luma-mm-hm", daemon=True).start()
