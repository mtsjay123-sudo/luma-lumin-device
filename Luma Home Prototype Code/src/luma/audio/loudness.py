"""How loud Luma is, in one place: her voice and anything she plays follow the same volume (0 to 10), and music dips
while she talks so she can be heard over it. No sound library here, so anything can ask."""
from __future__ import annotations

import threading

_lock = threading.Lock()
_level = 8   # where she's always been: 8 is the loudness Luma had before there was a volume
_talking = 0


def set_level(level):
    global _level
    with _lock:
        _level = max(0, min(10, int(level)))


def level():
    return _level


def gain():
    """How much to scale sound for a volume of 0..10: 8 leaves it as it was, each step is about the same change to the
    ear, 10 is about half again as loud (see `limit`, which keeps that from clipping)."""
    return 0.0 if _level <= 0 else 10 ** ((_level - 8) * 0.08)


def limit(audio):
    """Turned up past where she was made, the loudest peaks are rounded off instead of cracking."""
    import numpy as np
    a = np.asarray(audio, dtype=np.float32)
    over = np.abs(a) > 0.9
    if over.any():
        a = a.copy()
        a[over] = np.sign(a[over]) * (0.9 + 0.1 * np.tanh((np.abs(a[over]) - 0.9) / 0.1))
    return a


def talking(on):
    """Luma started (True) or stopped (False) talking: music under her dips to a quarter, then comes back."""
    global _talking
    with _lock:
        _talking = max(0, _talking + (1 if on else -1))


def under_voice():
    return 0.25 if _talking else 1.0
