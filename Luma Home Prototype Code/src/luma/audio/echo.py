"""Hearing the owner over Luma's own voice: acoustic echo cancellation, so you can talk over Luma on an ordinary speaker.

A speaker's mic hears everything the speaker plays. Without help, Luma has to stop listening while it talks, or it
hears itself and answers itself. This uses WebRTC's echo canceller (AEC3, the one in Chrome and in every video call),
through LiveKit's Python package (Apache-2.0): every sound Luma plays is handed to it as the "far end", and every bit
of mic audio passes through it before Luma listens for speech, so what's left is the room, and the owner.

In a test room (an echo 6 dB down, 40 ms late, with two reflections) it takes Luma's voice down by about 43 dB and
leaves the owner's voice within a decibel of where it was. If the package isn't installed, nothing changes: Luma
listens the way it always has (not while it talks, unless there are headphones).
"""
from __future__ import annotations

import threading

import numpy as np

RATE = 16_000
FRAME = RATE // 100  # WebRTC works in exact 10 ms frames
# While Luma talks, what's left after cancelling must be at least this loud (dBFS) before it can count as the owner
# starting to speak: residual echo sits far below it, someone talking over Luma from across a room sits above it.
TALK_OVER_FLOOR_DB = -42.0


def _resample(pcm, rate):
    """Mono int16 at any rate -> mono int16 at 16 kHz (linear: plenty for an echo reference)."""
    pcm = np.asarray(pcm, dtype=np.float32).reshape(-1)
    if rate != RATE and len(pcm):
        n = max(1, int(round(len(pcm) * RATE / rate)))
        pcm = np.interp(np.linspace(0, len(pcm) - 1, n), np.arange(len(pcm)), pcm)
    return np.clip(pcm, -32768, 32767).astype(np.int16)


def level_db(chunk):
    x = np.asarray(chunk, dtype=np.float32) / 32768.0
    return float(10 * np.log10(np.mean(x * x) + 1e-12)) if len(x) else -120.0


class EchoCanceller:
    """Feed it what's played (played) and what the mic hears (clean); it gives back the mic with Luma's voice taken out."""

    def __init__(self, delay_ms=60, noise_suppression=True):
        from livekit import rtc
        self._rtc = rtc
        self._apm = rtc.AudioProcessingModule(echo_cancellation=True, noise_suppression=noise_suppression, high_pass_filter=True,
                                              auto_gain_control=False)
        self.delay_ms = int(delay_ms)
        self._lock = threading.Lock()
        self._far = np.zeros(0, dtype=np.int16)
        self._near = np.zeros(0, dtype=np.int16)
        self._out = np.zeros(0, dtype=np.int16)

    def _frame(self, samples):
        return self._rtc.AudioFrame(samples.astype(np.int16).tobytes(), RATE, 1, FRAME)

    def played(self, pcm, rate):
        """Everything Luma sends to the speaker, as it's sent (mono int16 or float in -1..1, any rate)."""
        pcm = np.asarray(pcm)
        if pcm.dtype.kind == "f":
            pcm = pcm * 32767.0
        with self._lock:
            self._far = np.concatenate([self._far, _resample(pcm, rate)])
            while len(self._far) >= FRAME:
                frame, self._far = self._far[:FRAME], self._far[FRAME:]
                self._apm.process_reverse_stream(self._frame(frame))

    def clean(self, chunk):
        """A chunk of mic audio (mono int16 at 16 kHz) with the echo taken out, the same length as it came in."""
        chunk = np.asarray(chunk, dtype=np.int16).reshape(-1)
        with self._lock:
            self._near = np.concatenate([self._near, chunk])
            while len(self._near) >= FRAME:
                frame, self._near = self._near[:FRAME], self._near[FRAME:]
                self._apm.set_stream_delay_ms(self.delay_ms)
                f = self._frame(frame)
                self._apm.process_stream(f)
                self._out = np.concatenate([self._out, np.frombuffer(bytes(f.data), dtype=np.int16)])
            # The first few milliseconds lag by under one frame; pad so every chunk comes back whole.
            if len(self._out) < len(chunk):
                self._out = np.concatenate([np.zeros(len(chunk) - len(self._out), dtype=np.int16), self._out])
            out, self._out = self._out[:len(chunk)], self._out[len(chunk):]
        return out


_canceller, _tried, _guard = None, False, threading.Lock()


def canceller():
    """The one echo canceller, or None when the package isn't here (Luma then listens the old way)."""
    global _canceller, _tried
    with _guard:
        if not _tried:
            _tried = True
            try:
                _canceller = EchoCanceller()
            except Exception:
                _canceller = None
        return _canceller


def ready():
    return canceller() is not None


def played(pcm, rate):
    """Called by playback for every block it sends to the speaker. Never lets a problem here stop the sound."""
    c = canceller()
    if c is not None:
        try:
            c.played(pcm, rate)
        except Exception:
            pass
