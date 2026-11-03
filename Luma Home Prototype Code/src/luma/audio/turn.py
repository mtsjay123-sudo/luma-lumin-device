"""Knowing when the owner is done talking, not just quiet: Pipecat's Smart Turn v3 (BSD-2-Clause).

A pause isn't the end of a thought. "Remind me to call... um... my sister tomorrow" has a long gap in the middle, and a
plain silence timer either cuts it off or makes every reply wait. Smart Turn is a small model (Whisper Tiny's encoder
with a classifier, about 8 MB) that listens to how the sentence sounded, the pitch falling at the end or hanging in
the middle, and says whether the turn is complete.

So Luma checks at a short pause: done means it answers right away; not done means it keeps listening a little longer
for the rest. If the model isn't here (it downloads once, in the background), Luma uses its plain silence timer, the
way it always has.

The audio goes in exactly the way the model was trained on (pipecat-ai/smart-turn inference.py): 16 kHz mono, the
last 8 seconds of the turn, padded with silence at the start, normalized, as Whisper's 80-band log-mel spectrogram.
That spectrogram is computed here in numpy, matching transformers' WhisperFeatureExtractor(chunk_length=8), so no
PyTorch or transformers is needed on the device.
"""
from __future__ import annotations

import os
import threading
import urllib.request
from pathlib import Path

import numpy as np

RATE = 16_000
SECONDS = 8
N_FFT, HOP, MELS = 400, 160, 80
THRESHOLD = 0.5
REPO = "https://huggingface.co/pipecat-ai/smart-turn-v3/resolve/main/"
# Newest first. The model card lists the files; the first one that downloads (and is the right size) is kept.
FILES = ["smart-turn-v3.2-cpu.onnx", "smart-turn-v3.1-cpu.onnx", "smart-turn-v3.1.onnx", "smart-turn-v3.0.onnx"]
UA = {"User-Agent": "LumaDesktop/1.0 (+https://github.com/mtsjay123-sudo/luma-lumin-device)"}


def _hz_to_mel(f):
    f = np.asarray(f, dtype=np.float64)
    mel = 3.0 * f / 200.0
    log = f >= 1000.0
    return np.where(log, 15.0 + np.log(np.maximum(f, 1e-10) / 1000.0) / (np.log(6.4) / 27.0), mel)


def _mel_to_hz(m):
    m = np.asarray(m, dtype=np.float64)
    f = 200.0 * m / 3.0
    log = m >= 15.0
    return np.where(log, 1000.0 * np.exp((np.log(6.4) / 27.0) * (m - 15.0)), f)


def _filters():
    """Whisper's mel filterbank: 80 Slaney-style triangles from 0 to 8 kHz, area-normalized."""
    freqs = np.linspace(0, RATE / 2, N_FFT // 2 + 1)
    edges = _mel_to_hz(np.linspace(_hz_to_mel(0.0), _hz_to_mel(RATE / 2), MELS + 2))
    gaps = np.diff(edges)
    slopes = edges[:, None] - freqs[None, :]
    down = -slopes[:-2] / gaps[:-1, None]
    up = slopes[2:] / gaps[1:, None]
    bank = np.maximum(0.0, np.minimum(down, up))
    bank *= (2.0 / (edges[2:MELS + 2] - edges[:MELS]))[:, None]
    return bank.astype(np.float64)


_FILTERS = None


def prepare(audio):
    """The turn as the model expects it: float audio, the last 8 seconds, silence padded at the start."""
    x = np.asarray(audio)
    x = x.astype(np.float32) / 32768.0 if x.dtype.kind in "iu" else x.astype(np.float32)
    n = RATE * SECONDS
    return x[-n:] if len(x) >= n else np.concatenate([np.zeros(n - len(x), dtype=np.float32), x])


def features(audio):
    """(1, 80, 800) log-mel features, the way WhisperFeatureExtractor(chunk_length=8, do_normalize=True) makes them."""
    global _FILTERS
    if _FILTERS is None:
        _FILTERS = _filters()
    x = prepare(audio).astype(np.float64)
    x = (x - x.mean()) / np.sqrt(x.var() + 1e-7)
    padded = np.pad(x, (N_FFT // 2, N_FFT // 2), mode="reflect")
    window = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N_FFT) / N_FFT)  # periodic Hann
    frames = np.lib.stride_tricks.sliding_window_view(padded, N_FFT)[::HOP] * window
    power = np.abs(np.fft.rfft(frames, n=N_FFT, axis=1)) ** 2          # (frames, 201)
    mel = _FILTERS @ power.T[:, :-1]                                    # drop the last frame, as Whisper does: (80, 800)
    log = np.log10(np.maximum(mel, 1e-10))
    log = np.maximum(log, log.max() - 8.0)
    return ((log + 4.0) / 4.0).astype(np.float32)[None, :, :]


class SmartTurn:
    def __init__(self, path):
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.inter_op_num_threads = 1
        options.intra_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0].name

    def probability(self, audio):
        """How sure the model is that the turn is finished, 0 to 1."""
        out = self.session.run(None, {self.input: features(audio)})
        return float(np.asarray(out[0]).reshape(-1)[0])

    def complete(self, audio):
        return self.probability(audio) > THRESHOLD


def folder():
    from luma.config import MODELS_DIR
    return Path(MODELS_DIR) / "smart-turn"


def model_path():
    found = sorted(folder().glob("*.onnx")) if folder().is_dir() else []
    return found[-1] if found else None


_model, _tried, _lock = None, False, threading.Lock()


def model():
    """The Smart Turn model, or None when it isn't downloaded yet (or onnxruntime isn't installed)."""
    global _model, _tried
    with _lock:
        if not _tried:
            _tried = True
            path = model_path()
            if path:
                try:
                    _model = SmartTurn(path)
                except Exception:
                    _model = None
        return _model


def finished(audio):
    """True or False from the model, or None when there's no model (then the plain silence timer decides)."""
    m = model()
    if m is None:
        return None
    try:
        return m.complete(audio)
    except Exception:
        return None


PAUSE_MS = 300     # with the model, a pause this long gets the question "is that the end?"
PLAIN_MS = 900     # without it, the plain silence timer
HOLD_S = 1.6       # "not done yet" waits this much longer for the rest before giving up
MMHM_AFTER_S = 3.0 # a "mm-hm" at a mid-thought pause, once they've been talking this long


class Ending:
    """When a turn ends. At each pause the model is asked; "not done" holds the turn open a little longer for the rest,
    and new speech carries on the same turn. Without a model every pause ends the turn, as before."""

    def __init__(self, decide=None, hold=HOLD_S, clock=None):
        import time
        self.decide = decide or finished
        self.hold = hold
        self.clock = clock or time.monotonic
        self.holding = None

    def paused(self, audio):
        """A pause after speech. True if the turn is over now; False if it's held open waiting for more."""
        if self.decide(audio) is False:
            self.holding = self.holding or self.clock()
            return False
        self.holding = None
        return True

    def resumed(self):
        """They kept talking: the same turn goes on."""
        self.holding = None

    def timed_out(self):
        return self.holding is not None and self.clock() - self.holding > self.hold

    def reset(self):
        self.holding = None


fetching = {"running": False, "error": None}


def fetch_in_background(opener=None):
    """Download the model once (about 8 MB) so the next time Luma listens it can tell a pause from the end of a turn."""
    if model_path() or fetching["running"] or os.environ.get("LUMA_NO_DOWNLOADS"):
        return
    fetching.update(running=True, error=None)

    def run():
        global _tried
        try:
            folder().mkdir(parents=True, exist_ok=True)
            for name in FILES:
                request = urllib.request.Request(REPO + name, headers=UA)
                try:
                    with (opener or urllib.request.urlopen)(request, timeout=60) as response:
                        data = response.read(64_000_000)
                except Exception:
                    continue
                if 4_000_000 <= len(data) <= 60_000_000 and data[:1] == b"\x08":  # an ONNX file (a protobuf starting with its IR version)
                    part = folder() / (name + ".part")
                    part.write_bytes(data)
                    part.rename(folder() / name)
                    with _lock:
                        _tried = False  # load it on the next turn
                    return
            fetching["error"] = "Couldn't download the Smart Turn model right now."
        finally:
            fetching["running"] = False

    threading.Thread(target=run, daemon=True).start()
