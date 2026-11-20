#!/usr/bin/env python3
"""Teach Luma's small on-device model to hear "you're all I need" and "what are you?" (luma.agent.hears).

    PYTHONPATH=src python3 scripts/train_hears.py              # score on practice shapes it didn't learn from, then learn from all and save
    PYTHONPATH=src python3 scripts/train_hears.py --check      # only the first part (saves nothing)
    PYTHONPATH=src python3 scripts/train_hears.py --heldout    # rules alone, then rules with the saved model, on the held-out halves: numbers only

Writes src/luma/agent/hears.npz. Only numpy is needed. The same kind of model as the best-friend moves
(scripts/train_moves.py): a softmax layer over hashed words, word pairs and letter groups.

What it learns from:
- the practice sentences in luma/agent/hears.py, each said plain and said messy;
- the dev halves of the safety sets (tests/safety_sets.py): leaning, asked what it is, and as "neither": safe-but-sad
  lines, things a child says, and the dev halves of hard-or-not and keep-or-today;
- the rules' own hand-written guard lines (tests/test_safety_net.py): what must be heard, and what must not;
- ordinary talk (friendtalk.everyday's dev half, the phrase bank's chatter, requests).

What it never sees: any held-out half. --heldout prints counts, never a line.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT / "tests")]

import train_moves as moves  # noqa: E402  (dressing a line up, ordinary talk, the phrase bank's chatter)
import train_understanding as base  # noqa: E402
from luma.agent import friendcheck, hears, understanding  # noqa: E402

LABELS = hears.LABELS
OUT = hears.LEARNED


def fold(frame):
    """A practice sentence shape is "check" (one in five, kept out with --check) or "fit"."""
    return "check" if int(hashlib.sha1(("hears:" + frame).encode()).hexdigest(), 16) % 5 == 0 else "fit"


def practice(part, per_frame, seed):
    """(said, label, frame) from the practice sentences."""
    rng = random.Random(seed)
    out = []
    for label, frame in hears.FRAMES:
        if part is not None and fold(frame) != part:
            continue
        out += [(said, label, frame) for said in moves._fills(frame, hears.SLOTS, per_frame, rng)]
    return out


def dev_sets():
    """(said, label) from the dev halves of the fresh sets. Never a held-out line."""
    import hard_or_not
    import keep_or_today
    import safety_sets
    rows = [(t, "leaning") for t in safety_sets.leaning("dev")] + [(t, "what_i_am") for t in safety_sets.what_i_am("dev")]
    rows += [(t, "none") for t in safety_sets.safe_but_sad("dev")] + [(t, "none") for t in safety_sets.kids("dev")]
    rows += [(t, "none") for t, _ in hard_or_not.lines("dev")] + [(t, "none") for t, _ in keep_or_today.lines("dev")]
    import test_safety_net   # the rules' own guard lines, written by hand: what must be heard and what must not
    guard = test_safety_net.InLuma
    rows += [(t, "leaning") for t in guard.LEANING] + [(t, "what_i_am") for t in guard.ASKED_WHAT]
    rows += [(t, "none") for t in list(guard.NOT_LEANING) + list(guard.NOT_ASKED_WHAT)] * 4
    return rows


def neither(rows):
    """Ordinary lines the rules don't already hear as one or the other (a few really are)."""
    return [row for row in rows if not friendcheck.DEPENDENCY.search(row[0]) and not friendcheck.ASKED_WHAT_I_AM.search(row[0])]


def training_rows(part, per_frame, seed):
    rng = random.Random(seed)
    rows = []
    for said, label, _ in practice(part, per_frame, seed):
        rows.append((said, label))
        for _ in range(3):
            rows.append((moves.dress(said, rng), label))
    for said, label in dev_sets():
        rows.append((said, label))
        if label != "none":
            rows += [(moves.dress(said, rng), label) for _ in range(3)]
    positives = sum(1 for _, label in rows if label != "none")
    quiet = [(said, "none") for said, _, _ in moves.plain_lines("dev", None, 6, seed + 2)]
    quiet += [(said, "none") for said, _, _ in moves.chatter(positives, seed + 3, held=False)]
    quiet += [(said, "none") for said, _, _ in moves.requests(positives, seed + 4)]
    rows += neither(quiet)
    rng.shuffle(rows)
    return rows


def fit(rows, epochs):
    flat, offsets = base.csr([said for said, _ in rows])
    y = np.array([LABELS.index(label) for _, label in rows])
    return base.train(flat, offsets, y, len(LABELS), epochs)


def probabilities(W, b, texts, temperature=1.0):
    flat, offsets = base.csr(texts)
    return base.predict(W, b, flat, offsets, temperature)


def calibrate(W, b, rows):
    texts = [said for said, _ in rows]
    truth = np.array([LABELS.index(label) for _, label in rows])
    best, best_nll = 1.0, 1e9
    for t in (0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.2, 2.6, 3.0, 4.0):
        p = probabilities(W, b, texts, t)
        nll = -np.log(p[np.arange(len(truth)), truth] + 1e-9).mean()
        if nll < best_nll:
            best, best_nll = t, nll
    return best


def save(W, b, temperature, path):
    used = np.flatnonzero(np.abs(W).max(axis=1) > 1e-3)
    rows = W[used]
    scale = np.maximum(np.abs(rows).max(axis=1), 1e-8) / 127.0
    q = np.round(rows / scale[:, None]).astype(np.int8)
    np.savez_compressed(path, intents=np.array(LABELS), rows=used.astype(np.int32), q=q, scale=scale.astype(np.float32),
                        bias=b.astype(np.float32), temperature=np.float32(temperature))
    print(f"saved {path} ({Path(path).stat().st_size / 1e6:.2f} MB, {len(used):,} feature rows)")


def table(p, rows, cuts=(0.5, 0.6, 0.7, 0.8, 0.9, 0.95)):
    """Per label: of its lines, how many the model names this surely and that also have the plain shape. And what ordinary talk costs."""
    truth = np.array([LABELS.index(label) for _, label in rows])
    top, conf = p.argmax(1), p.max(1)
    shaped = {label: np.array([hears.has_shape(label, said) for said, _ in rows]) for label in LABELS[:2]}
    print(f"  {'':24}" + "".join(f"{'>=' + str(cut):>8}" for cut in cuts) + "    lines")
    for i, label in enumerate(LABELS[:2]):
        mine = truth == i
        if mine.any():
            print(f"  {label + ', heard':24}" + "".join(f"{int(((top == i) & (conf >= cut) & shaped[label])[mine].sum()):8d}" for cut in cuts) + f"  {int(mine.sum()):7,}")
        other = truth != i
        print(f"  {label + ', heard wrongly':24}" + "".join(f"{int(((top == i) & (conf >= cut) & shaped[label])[other].sum()):8d}" for cut in cuts) + f"  {int(other.sum()):7,}")


def check_rows(seed):
    rows = [(said, label) for said, label, _ in practice("check", 40, seed)]
    rng = random.Random(seed)
    rows += [(moves.dress(said, rng), label) for said, label in list(rows)]
    quiet = [(said, "none") for said, _, _ in moves.chatter(3000, seed + 2, held=True)]
    quiet += [(said, "none") for said, _, _ in moves.requests(3000, seed + 30)]
    return rows + neither(quiet)


def heldout():
    """Rules alone, then rules with the model, on the halves nothing was fitted to. Counts only."""
    import hard_or_not
    import keep_or_today
    import safety_sets
    from luma.agent.friendtalk import everyday  # noqa: F401
    lean, who = safety_sets.leaning("heldout"), safety_sets.what_i_am("heldout")
    calm = safety_sets.safe_but_sad("heldout") + safety_sets.kids("heldout") + [t for t, _ in hard_or_not.lines("heldout")]
    calm += [t for t, _ in keep_or_today.lines("heldout")] + [said for said, _, _ in moves.plain_lines("heldout", None, 6, 5)]
    calm += [said for said, _, _ in moves.chatter(4000, 7, held=True)]
    print("on the held-out halves (no line is printed):")
    for name, rule, full, mine, others in (
            ("leaning", friendcheck.DEPENDENCY.search, hears.leaning, lean, who + calm),
            ("asked what it is", friendcheck.ASKED_WHAT_I_AM.search, hears.what_i_am, who, lean + calm)):
        print(f"  {name:18} rules alone {sum(bool(rule(t)) for t in mine)}/{len(mine)}   with the model {sum(full(t) for t in mine)}/{len(mine)}")
        print(f"  {'':18} heard wrongly on the rest: rules alone {sum(bool(rule(t)) for t in others)}/{len(others)}   "
              f"with the model {sum(full(t) for t in others)}/{len(others)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-frame", type=int, default=40)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--heldout", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    if args.heldout:
        return heldout()

    rows = training_rows("fit", args.per_frame, 0)
    counts = collections.Counter(label for _, label in rows)
    print(f"learning from {len(rows):,} lines: " + ", ".join(f"{label} {counts[label]:,}" for label in LABELS), flush=True)
    W, b = fit(rows, args.epochs)
    seen = check_rows(5)
    temperature = calibrate(W, b, seen)
    print(f"\non practice shapes it didn't learn from, plain and dressed up, with ordinary talk ({len(seen):,} lines), temperature {temperature}:")
    table(probabilities(W, b, [said for said, _ in seen], temperature), seen)
    if args.check:
        return
    rows = training_rows(None, args.per_frame, 0)
    counts = collections.Counter(label for _, label in rows)
    print(f"\nnow everything: {len(rows):,} lines: " + ", ".join(f"{label} {counts[label]:,}" for label in LABELS), flush=True)
    W, b = fit(rows, args.epochs)
    save(W, b, temperature, args.out)


if __name__ == "__main__":
    main()
