"""Which turns are hard, learned from labeled turns (data/router_turns.jsonl) and not from rules about model names.

    tier("ok thanks")                                              -> "light"
    tier("my sister called and we talked for an hour")            -> "talk"
    tier("compare leasing and buying over five years, show math") -> "hard"

A small linear model over the words of the message and how long it is. The weights (router_weights.json, next to this
file) are written by scripts/train_router.py; here they're applied in plain Python, a few dozen additions per message.
A message is called hard only when the model is sure, because a hard turn waits longer and costs more.
"""
from __future__ import annotations

import json
import math
import re
import zlib
from pathlib import Path

TIERS = ("light", "talk", "hard")
BUCKETS = 4096
WEIGHTS = Path(__file__).with_name("router_weights.json")
_model = None


def features(text):
    """The message as a handful of numbered features: its words, its word pairs, and how long and how numbered it is."""
    words = re.findall(r"[a-z0-9']+", str(text or "").lower())
    out = {}

    def add(name, value=1.0):
        bucket = zlib.crc32(name.encode()) % BUCKETS
        out[bucket] = out.get(bucket, 0.0) + value
    for word in set(words):
        add("w:" + word)
    for pair in set(zip(words, words[1:])):
        add("p:" + pair[0] + " " + pair[1], 0.5)
    count = len(words)
    add("len:" + ("1" if count <= 2 else "2" if count <= 6 else "3" if count <= 14 else "4" if count <= 30 else "5"), 2.0)
    numbers = sum(1 for word in words if word.isdigit())
    if numbers:
        add("numbers:" + ("many" if numbers >= 2 else "one"))
    if str(text or "").count(",") >= 2:
        add("commas")
    return out


def _load():
    global _model
    if _model is None:
        try:
            raw = json.loads(WEIGHTS.read_text())
            _model = {"w": {int(k): v for k, v in raw["w"].items()}, "b": raw["b"], "sure": float(raw.get("sure", 0.6))}
        except (OSError, ValueError, KeyError):
            _model = {"w": {}, "b": [0.0, 1.0, 0.0], "sure": 1.1}  # no weights: everything is talk, nothing is ever hard
    return _model


def chances(text, model=None):
    """{"light": p, "talk": p, "hard": p} for one message."""
    model = model or _load()
    score = list(model["b"])
    for bucket, value in features(text).items():
        weights = model["w"].get(bucket)
        if weights:
            for i in range(3):
                score[i] += weights[i] * value
    top = max(score)
    exp = [math.exp(s - top) for s in score]
    total = sum(exp)
    return {name: e / total for name, e in zip(TIERS, exp)}


def tier(text, model=None):
    model = model or _load()
    odds = chances(text, model)
    if odds["hard"] >= model["sure"]:
        return "hard"
    return "light" if odds["light"] > odds["talk"] else "talk"
