"""Teach the router which turns are hard, from labeled turns.

    python scripts/train_router.py train              # learns from the dev half, writes src/luma/llm/router_weights.json
    python scripts/train_router.py test               # the held-out half: how often it's right, and what it mixes up

Half of the labeled turns (data/router_turns.jsonl) are held out: they're never trained on, never used to pick a setting,
and their misses are never printed. How sure it must be before calling a turn hard is picked on the dev half alone.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from luma.llm import router  # noqa: E402

DATA = ROOT / "data" / "router_turns.jsonl"


def rows(split):
    return [r for r in (json.loads(line) for line in DATA.read_text().splitlines() if line.strip()) if r["split"] == split]


def matrix(turns):
    x = np.zeros((len(turns), router.BUCKETS), dtype=np.float64)
    for i, turn in enumerate(turns):
        for bucket, value in router.features(turn["text"]).items():
            x[i, bucket] = value
    y = np.array([router.TIERS.index(turn["tier"]) for turn in turns])
    return x, y


def fit(x, y, steps=400, rate=0.5, decay=1e-3):
    """Plain softmax regression: no randomness, so the same turns always give the same weights."""
    w, b = np.zeros((router.BUCKETS, 3)), np.zeros(3)
    onehot = np.eye(3)[y]
    for _ in range(steps):
        z = x @ w + b
        z -= z.max(axis=1, keepdims=True)
        p = np.exp(z)
        p /= p.sum(axis=1, keepdims=True)
        grad = (p - onehot) / len(y)
        w -= rate * (x.T @ grad + decay * w)
        b -= rate * grad.sum(axis=0)
    return w, b


def as_model(w, b, sure):
    used = np.flatnonzero(np.abs(w).sum(axis=1) > 1e-6)
    return {"w": {int(i): [round(float(v), 4) for v in w[i]] for i in used}, "b": [round(float(v), 4) for v in b], "sure": sure}


def score(model, turns):
    table = {a: {b: 0 for b in router.TIERS} for a in router.TIERS}
    for turn in turns:
        table[turn["tier"]][router.tier(turn["text"], model)] += 1
    right = sum(table[t][t] for t in router.TIERS)
    return right / max(1, len(turns)), table


def pick_sure(turns, folds=5):
    """How sure before a turn is called hard: tried on the dev half, five ways, each time on turns it didn't learn from.
    The lowest bar that calls no more than 2 in 100 everyday turns hard; a wrongly hard turn waits longer and costs more."""
    best = None
    for sure in (0.5, 0.6, 0.7, 0.8):
        wrong_hard = everyday = caught = hard = 0
        for fold in range(folds):
            train = [t for i, t in enumerate(turns) if i % folds != fold]
            held = [t for i, t in enumerate(turns) if i % folds == fold]
            model = as_model(*fit(*matrix(train)), sure)
            for turn in held:
                said = router.tier(turn["text"], model)
                if turn["tier"] == "hard":
                    hard += 1
                    caught += said == "hard"
                else:
                    everyday += 1
                    wrong_hard += said == "hard"
        row = (sure, wrong_hard / max(1, everyday), caught / max(1, hard))
        print(f"  sure {sure}: everyday turns called hard {100 * row[1]:.1f}%, hard turns caught {100 * row[2]:.1f}% (dev, five ways)")
        if row[1] <= 0.02 and best is None:
            best = row
    return (best or row)[0]


def show(name, accuracy, table):
    print(f"{name}: right {100 * accuracy:.1f}%")
    print("| was \\ called | " + " | ".join(router.TIERS) + " |\n|---|---|---|---|")
    for was in router.TIERS:
        print(f"| {was} | " + " | ".join(str(table[was][called]) for called in router.TIERS) + " |")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("what", choices=["train", "test"])
    args = parser.parse_args()
    if args.what == "train":
        dev = rows("dev")
        sure = pick_sure(dev)
        model = as_model(*fit(*matrix(dev)), sure)
        router.WEIGHTS.write_text(json.dumps({"buckets": router.BUCKETS, "tiers": router.TIERS, "sure": sure, "b": model["b"],
                                              "w": {str(k): v for k, v in sorted(model["w"].items())}, "learned_from": len(dev)}, separators=(",", ":")))
        show(f"dev ({len(dev)} turns it learned from)", *score(model, dev))
        print("wrote", router.WEIGHTS.relative_to(ROOT), f"({router.WEIGHTS.stat().st_size // 1024} KB)")
    else:
        router._model = None
        held = rows("heldout")
        show(f"held out ({len(held)} turns it never saw)", *score(router._load(), held))


if __name__ == "__main__":
    main()
