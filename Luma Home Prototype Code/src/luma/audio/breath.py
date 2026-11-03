"""Breathing: the small, quiet inhale a person takes before a longer sentence.

Speech models leave the air out, and a voice that never breathes sounds like a recording. People don't breathe
before every phrase, though: before a long sentence after a real pause, now and then, never before "okay" and
never in the middle of a thought. So Luma breathes only there: before a sentence of ten words or more that comes
after a pause of at least a quarter second, and not twice in a row.

The breath is made here, not recorded from anyone: soft noise, shaped the way air through a mouth sounds (most
of it between about 500 Hz and 3 kHz), rising and falling like an inhale, about 20 dB below the voice next to it
so it's felt more than heard. The same sentence always gets the same breath.
"""
from __future__ import annotations

import re
import zlib

import numpy as np

MIN_WORDS = 10        # only before a sentence long enough to need the air
MIN_PAUSE_MS = 250    # only after a real pause
BELOW_VOICE_DB = 20   # this much quieter than the speech around it
MS = 300              # an easy inhale
ON = {"on": True}     # Settings can turn it off


def wanted(words, pause_before_ms, since_last):
    """Breathe before these words? Long enough, after a real pause, and not right after the last breath."""
    n = len(re.findall(r"[\w']+", str(words or "")))
    return bool(ON["on"]) and n >= MIN_WORDS and pause_before_ms >= MIN_PAUSE_MS and since_last >= 2


def _level(pcm):
    x = np.asarray(pcm, dtype=np.float32)
    voiced = x[np.abs(x) > 300]  # the speech itself, not the silence around it
    return float(np.sqrt(np.mean(voiced * voiced))) if voiced.size else 3000.0


def inhale(rate, near, seed="", ms=MS):
    """A soft inhale, as int16 at `rate`, about BELOW_VOICE_DB under the speech in `near`."""
    n = max(1, int(rate * ms / 1000))
    rng = np.random.default_rng(zlib.crc32(str(seed).encode("utf-8", "ignore")))
    noise = rng.standard_normal(n)
    spectrum = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, 1 / rate)
    band = np.exp(-0.5 * ((np.log(np.maximum(freqs, 1.0)) - np.log(1400.0)) / 0.6) ** 2)  # air: centered near 1.4 kHz
    air = np.fft.irfft(spectrum * band, n)
    t = np.linspace(0.0, 1.0, n)
    envelope = np.sin(np.pi * np.clip(t / 0.75, 0, 1) / 2) ** 2 * np.clip((1.0 - t) / 0.25, 0, 1) ** 1.5  # rises, then eases off
    breath = air * envelope
    rms = float(np.sqrt(np.mean(breath * breath))) or 1.0
    target = _level(near) * 10 ** (-BELOW_VOICE_DB / 20)
    return np.clip(breath / rms * target, -32768, 32767).astype(np.int16)


def before(pcm, rate, words, gap_ms=60):
    """The phrase with a breath in front of it (and a moment between the breath and the first word)."""
    pcm = np.asarray(pcm, dtype=np.int16)
    air = inhale(rate, pcm, seed=words)
    return np.concatenate([air, np.zeros(int(rate * gap_ms / 1000), dtype=np.int16), pcm])
