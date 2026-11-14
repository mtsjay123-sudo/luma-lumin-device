"""What Luma plays out loud that isn't her voice: sleep sounds, the radio, songs from their own folder, an alarm's chime.

One thing plays at a time, on its own thread, and stops the moment it's asked to. Sleep sounds are made right here
(nothing is downloaded or sent). The radio and their songs are decoded by ffmpeg when it's installed on the Luma; it's
a separate program, run as one, not part of Luma's code. Everything follows Luma's volume and dips while she talks.
"""
from __future__ import annotations

import shutil
import subprocess
import threading
import time

import numpy as np

from luma.audio import loudness

RATE = 24000
BLOCK = RATE // 2


def noise(kind, seconds, rate=RATE, seed=None):
    """`seconds` of a sleep sound, as float32 in -1..1, made from noise and nothing else."""
    rng = np.random.default_rng(seed)
    n = int(seconds * rate)
    white = rng.standard_normal(n).astype(np.float32)

    def pink(x):
        spectrum = np.fft.rfft(x)
        f = np.arange(len(spectrum), dtype=np.float64)
        f[0] = 1.0
        out = np.fft.irfft(spectrum / np.sqrt(f), n=len(x))   # 1/f: softer than white, like steady rain on a roof
        return out / (np.abs(out).max() + 1e-9) * 0.8

    def brown(x):
        out = np.cumsum(x * 0.02)
        out -= np.convolve(out, np.ones(2401) / 2401, mode="same")   # keep it from wandering off
        return out / (np.abs(out).max() + 1e-9) * 0.8

    def low(x, k):
        return np.convolve(x, np.ones(k) / k, mode="same")

    t = np.arange(n) / rate
    if kind == "white noise": out = white * 0.25
    elif kind == "pink noise": out = pink(white)
    elif kind == "brown noise": out = brown(white)
    elif kind == "ocean":
        swell = 0.25 + 0.75 * (0.5 + 0.5 * np.sin(2 * np.pi * t / (7.5 + 1.5 * np.sin(2 * np.pi * t / 41))))
        out = (0.6 * brown(white) + 0.4 * low(white, 6) * 0.5) * swell ** 2
    elif kind == "rain":
        bed = low(white, 3) * 0.18
        drops = np.zeros(n, dtype=np.float32)
        hits = rng.integers(0, max(1, n - 400), size=int(seconds * 90))
        decay = np.exp(-np.arange(400) / 40.0).astype(np.float32)
        for h in hits:
            drops[h:h + 400] += decay * rng.uniform(0.05, 0.35) * rng.choice([-1, 1])
        out = bed + drops - low(drops, 9)
    elif kind == "fireplace":
        bed = brown(white) * 0.35
        crackle = np.zeros(n, dtype=np.float32)
        decay = np.exp(-np.arange(240) / 18.0).astype(np.float32)
        for h in rng.integers(0, max(1, n - 240), size=int(seconds * 14)):
            crackle[h:h + 240] += decay * rng.standard_normal(240).astype(np.float32) * rng.uniform(0.2, 0.9)
        out = bed + crackle * 0.5
    elif kind == "stream":
        out = (low(white, 2) - low(white, 40)) * (0.5 + 0.12 * np.sin(2 * np.pi * t * 0.31) + 0.08 * np.sin(2 * np.pi * t * 1.7))
    elif kind == "wind":
        gust = 0.35 + 0.65 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 9 + 2 * np.sin(2 * np.pi * t / 23)))
        out = (brown(white) * 0.7 + low(white, 25) * 0.6) * gust
    else:
        raise ValueError("Unknown sound.")
    out = np.asarray(out, dtype=np.float32)
    peak = float(np.abs(out).max()) or 1.0
    return np.clip(out / peak * 0.6, -1, 1)


def chime(rate=RATE):
    """A soft three-note rise for an alarm, gentler than a beep."""
    notes = []
    for f, length in ((523.25, 0.32), (659.25, 0.32), (783.99, 0.7)):
        t = np.arange(int(length * rate)) / rate
        env = np.minimum(1, t / 0.01) * np.exp(-t * 3.2)
        notes.append((np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env * 0.4)
    return np.concatenate(notes).astype(np.float32)


class Player:
    """Plays one thing at a time on the Luma's speaker. `out(blocks, should_stop)` plays float32 blocks; tests pass
    their own. Without a speaker (a computer with no sound device) every method still works and plays nothing."""

    def __init__(self, out=None, ffmpeg=None):
        self.out = out or _speaker
        self.ffmpeg = ffmpeg if ffmpeg is not None else _find_ffmpeg()
        self._stop = threading.Event()
        self._thread = None
        self._proc = None

    def busy(self):
        return bool(self._thread and self._thread.is_alive())

    def set_volume(self, level):
        loudness.set_level(level)

    def stop(self):
        self._stop.set()
        proc, self._proc = self._proc, None
        if proc:
            try: proc.kill()
            except Exception: pass
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)
        self._thread = None

    def _run(self, blocks):
        self.stop()
        self._stop = threading.Event()
        stop = self._stop
        self._thread = threading.Thread(target=lambda: self._play(blocks, stop), daemon=True, name="luma-player")
        self._thread.start()

    def _play(self, blocks, stop):
        try:
            self.out(blocks, stop.is_set)
        except Exception:
            pass

    def chime(self):
        self._run(iter([chime()]))

    def sound(self, kind, seconds):
        noise(kind, 0.05)   # unknown kinds fail here, before anything starts

        def blocks():
            made = noise(kind, 60)
            end = time.monotonic() + seconds
            fade = np.linspace(0, 1, BLOCK, dtype=np.float32)
            first = True
            while time.monotonic() < end:
                for i in range(0, len(made), BLOCK):
                    piece = made[i:i + BLOCK]
                    if first: piece = piece * fade[: len(piece)]; first = False
                    if time.monotonic() >= end - 8:   # the last few seconds fade out
                        piece = piece * max(0.0, (end - time.monotonic()) / 8)
                    yield piece
                    if time.monotonic() >= end: return
        self._run(blocks())

    def _decode(self, source):
        if not self.ffmpeg:
            raise RuntimeError("Playing music needs ffmpeg on the Luma.")
        proc = subprocess.Popen([self.ffmpeg, "-nostdin", "-loglevel", "quiet", "-reconnect", "1", "-reconnect_streamed", "1", "-i", source,
                                 "-f", "s16le", "-ac", "1", "-ar", str(RATE), "-"] if source.startswith(("http://", "https://")) else
                                [self.ffmpeg, "-nostdin", "-loglevel", "quiet", "-i", source, "-f", "s16le", "-ac", "1", "-ar", str(RATE), "-"],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        self._proc = proc
        while True:
            raw = proc.stdout.read(BLOCK * 2)
            if not raw: break
            yield np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0

    def stream(self, url):
        if not url.startswith(("https://", "http://")): raise ValueError("Only web radio streams.")
        if not self.ffmpeg: raise RuntimeError("Playing the radio needs ffmpeg on the Luma.")
        self._run(self._decode(url))

    def play_files(self, paths):
        if not self.ffmpeg: raise RuntimeError("Playing songs needs ffmpeg on the Luma.")
        paths = list(paths)

        def blocks():
            for path in paths:
                yield from self._decode(path)
        self._run(blocks())


def _find_ffmpeg():
    """The same FFmpeg video uses: LUMA_FFMPEG, the system's, Homebrew's, or the one Luma Desktop installs."""
    try:
        from luma.skills.video import ffmpeg
        return ffmpeg()
    except Exception:
        return shutil.which("ffmpeg")


def _speaker(blocks, should_stop):
    """Play float32 blocks on the Luma's speaker, at Luma's volume, dipping while she talks."""
    import os
    import sounddevice as sd
    from luma.hardware.device import resolve_audio_device
    device = resolve_audio_device(os.getenv("LUMA_OUTPUT_DEVICE"), sd.query_devices(), direction="output")
    with sd.OutputStream(samplerate=RATE, channels=1, dtype="float32", device=device) as stream:
        smooth = 1.0
        for block in blocks:
            if should_stop(): stream.abort(); return
            want = loudness.gain() * loudness.under_voice()
            ramp = np.linspace(smooth, want, len(block), dtype=np.float32)   # volume changes glide, never click
            smooth = want
            stream.write(loudness.limit(np.asarray(block, dtype=np.float32) * ramp).reshape(-1, 1))


def make_player():
    """A Player for this machine's speaker, or None when there's no speaker to play on (so Luma never says she's
    playing something nobody can hear). LUMA_PLAYER=0 turns it off."""
    import os
    if os.environ.get("LUMA_PLAYER", "1") == "0":
        return None
    try:
        import sounddevice as sd
        info = sd.query_devices(kind="output")
        if not info or int(info.get("max_output_channels", 0)) < 1:
            return None
    except Exception:
        return None
    return Player()
