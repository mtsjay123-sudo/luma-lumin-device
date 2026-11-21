"""Luma's own sounds: a few short notes that aren't words.

Luma is a presence, not a person, and until now everything it expressed was a sentence. A friend who isn't a person can
have a voice of its own as well: a quick rising pair when something's done, a bright trill at good news, a soft low
note when someone's had a rough one, a hello and a goodnight. Each is made here from sine waves (nothing downloaded,
nothing recorded), is under a second, is quieter than speech, and comes just before the words, never instead of them.

    chirps.for_reply("Got it. I'll remind you at six.", "task")   ->  "yes"
    chirps.sound("yes")                                           ->  float32 samples at 24 kHz

When there's none: on a safety reply, with someone in grief or upset or being serious, in the middle of a long reply,
and most of the time otherwise. The same reply always gets the same answer, so a replay sounds the same.

Off unless the owner turns it on (setting "own_sounds"): what a sound is like is for ears to judge, and nobody has
heard these yet. "Let me hear your sounds" plays them all; "use your sounds" and "stop using your sounds" switch it.
"""
from __future__ import annotations

import re
import zlib

import numpy as np

RATE = 24000
LOUD = 0.22          # the alarm's chime is 0.4: these sit under the voice

# name: [(start Hz, end Hz, seconds)], what it's for. Notes glide from one pitch to the next, so it sings, not beeps.
SOUNDS = {
    "yes": ([(659.25, 698.46, 0.08), (880.0, 932.33, 0.13)], "done, or noted"),
    "delight": ([(523.25, 783.99, 0.12), (783.99, 1046.5, 0.10), (1046.5, 1318.5, 0.16)], "good news, or a laugh"),
    "curious": ([(587.33, 587.33, 0.10), (659.25, 987.77, 0.22)], "didn't catch that"),
    "soft": ([(440.0, 392.0, 0.24), (349.23, 329.63, 0.34)], "with them on a rough one"),
    "hello": ([(523.25, 523.25, 0.10), (659.25, 659.25, 0.10), (783.99, 698.46, 0.26)], "hello"),
    "night": ([(783.99, 659.25, 0.26), (659.25, 523.25, 0.30), (523.25, 493.88, 0.40)], "goodnight"),
}

SAFETY = re.compile(r"\b988\b|\b119\b|0570|are you safe|stay(?:ing)? (?:right )?here with you|hurt yourself|end your life", re.I)
DONE = re.compile(r"^\W*(?:got it|done|okay,? i'?ll|ok,? i'?ll|saved|sent|set|added|noted|all set|timer'?s? set|alarm'?s? set|playing|opening|turned (?:on|off))\b", re.I)
HELLO = re.compile(r"^\W*(?:good morning|morning|hey(?: there)?|hi(?: there)?|hello|welcome (?:back|home))\b", re.I)
NIGHT = re.compile(r"^\W*(?:good ?night|night|sleep (?:well|tight)|sweet dreams)\b", re.I)
MISSED = re.compile(r"^\W*(?:you got cut off|i didn'?t catch|say that again|sorry,? (?:what|say)|one more time)\b", re.I)
QUIET_MOODS = {"grief", "upset", "serious"}   # with someone hurting, a friend is quiet: no note at all


def _note(start, end, seconds, rate=RATE):
    n = int(seconds * rate)
    t = np.arange(n) / rate
    freq = start + (end - start) * (t / max(seconds, 1e-6)) ** 0.7              # a glide that leans into the end
    freq = freq * (1 + 0.006 * np.sin(2 * np.pi * 9.0 * t))                     # a touch of life, like a voice
    phase = 2 * np.pi * np.cumsum(freq) / rate
    wave = np.sin(phase) + 0.22 * np.sin(2 * phase) + 0.07 * np.sin(3 * phase)   # round, with a little shine
    attack, release = min(0.012, seconds / 4), min(0.06, seconds / 2)
    env = np.minimum(1, t / attack) * np.minimum(1, (seconds - t) / release)
    return wave * np.clip(env, 0, 1)


def sound(name, rate=RATE):
    """One of Luma's sounds as float32 samples, or an empty array for a name it doesn't have."""
    spec = SOUNDS.get(name)
    if not spec:
        return np.zeros(0, dtype=np.float32)
    gap = np.zeros(int(0.012 * rate))
    parts = []
    for start, end, seconds in spec[0]:
        parts += [_note(start, end, seconds, rate), gap]
    out = np.concatenate(parts[:-1])
    return (out / max(1e-6, float(np.abs(out).max())) * LOUD).astype(np.float32)


def for_reply(reply, mood="neutral"):
    """The sound that goes before this reply, or None. mood: luma.audio.feel.mood()."""
    text = " ".join(str(reply or "").split())
    if not text or SAFETY.search(text) or mood in QUIET_MOODS:
        return None
    roll = zlib.crc32(text.encode("utf-8", "ignore")) % 100
    if NIGHT.match(text):
        return "night"
    if HELLO.match(text) and len(text.split()) <= 14:
        return "hello"
    if MISSED.match(text):
        return "curious"
    if DONE.match(text):
        return "yes" if roll < 60 else None           # most times, not every time
    if mood in ("laughing", "playful"):
        return "delight" if roll < 40 else None
    if mood == "venting":
        return "soft" if roll < 30 else None
    return None
