#!/usr/bin/env python3
"""Teach Luma's small on-device model to read a hard moment said in words no rule knows (luma.agent.feels).

    PYTHONPATH=src python3 scripts/train_feels.py              # score on practice shapes it didn't learn from, then learn from all and save
    PYTHONPATH=src python3 scripts/train_feels.py --check      # only the first part (saves nothing)
    PYTHONPATH=src python3 scripts/train_feels.py --heldout    # rules alone, then rules with the saved model, on the held-out halves: numbers only

Writes src/luma/agent/feels.npz. Only numpy is needed. The same kind of model as the best-friend moves
(scripts/train_moves.py): a softmax layer over hashed words, word pairs and letter groups.

What it learns from:
- the practice sentences in luma/agent/feels.py, each said plain and said messy;
- the dev half of hard-or-not (tests/hard_or_not.py): a hard line under the feeling the rules read in it, an ordinary one as "none";
- as "none" where the rules read nothing hard: the dev halves of keep-or-today, leaning, asked what it is and what a
  child says, ordinary talk (friendtalk.everyday's dev half), the phrase bank's chatter, and requests.

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
from luma.agent import feelings, feels, friendcheck  # noqa: E402

LABELS = feels.LABELS
OUT = feels.LEARNED
HARD = LABELS[:-1]


def by_rule(said):
    """The hard feeling the rules alone read ("" for none or a good one). The model is switched off while asking."""
    low = " ".join(str(said).lower().split())
    found = feelings._families(low)
    if not found:
        full = feelings._said_in_full(low)   # the subject left off, put back ("kinda sad today")
        found = feelings._families(full) if full else []
    return found[0] if found and found[0] not in feelings.GOOD else ""


def fold(frame):
    """A practice sentence shape is "check" (one in five, kept out with --check) or "fit"."""
    return "check" if int(hashlib.sha1(("feels:" + frame).encode()).hexdigest(), 16) % 5 == 0 else "fit"


def practice(part, per_frame, seed):
    """(said, label, frame) from the practice sentences."""
    rng = random.Random(seed)
    out = []
    for label, frame in feels.FRAMES:
        if part is not None and fold(frame) != part:
            continue
        out += [(said, label, frame) for said in moves._fills(frame, feels.SLOTS, per_frame, rng) if not safety_reads(said)]
    return out


def safety_reads(said):
    """A line the safety readers read is never taught to the model as a feeling (it's never asked about one either)."""
    return friendcheck.at_risk(said) or friendcheck.worth_asking(said)


def dev_sets():
    """(said, label) from the dev halves of the fresh sets. Never a held-out line."""
    import hard_or_not
    import keep_or_today
    import safety_sets
    rows = []
    for said, mark in hard_or_not.lines("dev"):
        if mark == "hard":
            family = by_rule(said)
            if family in HARD and not safety_reads(said):
                rows.append((said, family))
        else:
            rows.append((said, "none"))
    calm = [t for t, _ in keep_or_today.lines("dev")] + list(safety_sets.leaning("dev")) + list(safety_sets.what_i_am("dev"))
    calm += list(safety_sets.kids("dev"))
    rows += [(t, "none") for t in calm if not by_rule(t)]
    return rows


def quiet_only(rows):
    """Ordinary lines the rules don't already read as hard (a few really are)."""
    return [row for row in rows if not by_rule(row[0])]


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
    rows += quiet_only(quiet)
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
    """Of the hard lines, how many the model calls hard this surely (any hard feeling, and the right one), with the plain shape.
    And how many ordinary lines it calls hard."""
    truth = np.array([LABELS.index(label) for _, label in rows])
    none = LABELS.index("none")
    top, conf = p.argmax(1), p.max(1)
    shaped = np.array([feels.has_shape(said) for said, _ in rows])
    hard, calm = truth != none, truth == none
    print(f"  {'':34}" + "".join(f"{'>=' + str(cut):>8}" for cut in cuts) + "    lines")
    print(f"  {'hard, read as hard':34}" + "".join(f"{int(((top != none) & (conf >= cut) & shaped)[hard].sum()):8d}" for cut in cuts) + f"  {int(hard.sum()):7,}")
    print(f"  {'hard, and the right feeling':34}" + "".join(f"{int(((top == truth) & (conf >= cut) & shaped)[hard].sum()):8d}" for cut in cuts) + f"  {int(hard.sum()):7,}")
    print(f"  {'ordinary, read as hard':34}" + "".join(f"{int(((top != none) & (conf >= cut) & shaped)[calm].sum()):8d}" for cut in cuts) + f"  {int(calm.sum()):7,}")


def check_rows(seed):
    rows = [(said, label) for said, label, _ in practice("check", 40, seed)]
    rng = random.Random(seed)
    rows += [(moves.dress(said, rng), label) for said, label in list(rows)]
    quiet = [(said, "none") for said, _, _ in moves.chatter(3000, seed + 2, held=True)]
    quiet += [(said, "none") for said, _, _ in moves.requests(3000, seed + 30)]
    return rows + quiet_only(quiet)


def heldout():
    """Rules alone, then rules with the model, on the halves nothing was fitted to. Counts only."""
    import hard_or_not
    import keep_or_today
    import safety_sets
    bad = lambda t: (lambda f: bool(f) and f["family"] not in feelings.GOOD)(feelings.read(t))  # noqa: E731
    hard = [t for t, mark in hard_or_not.lines("heldout") if mark == "hard"]
    plain = [t for t, mark in hard_or_not.lines("heldout") if mark != "hard"]
    print("on the held-out halves (no line is printed):")
    print(f"  hard-or-not, hard lines read as hard: rules alone {sum(bool(by_rule(t)) for t in hard)}/{len(hard)}   with the model {sum(bad(t) for t in hard)}/{len(hard)}")
    print(f"  hard-or-not, ordinary lines read as hard: rules alone {sum(bool(by_rule(t)) for t in plain)}/{len(plain)}   with the model {sum(bad(t) for t in plain)}/{len(plain)}")
    for name, lines in (
            ("keep-or-today", [t for t, _ in keep_or_today.lines("heldout")]),
            ("leaning", list(safety_sets.leaning("heldout"))),
            ("asked what it is", list(safety_sets.what_i_am("heldout"))),
            ("what a child says", list(safety_sets.kids("heldout"))),
            ("ordinary talk", [said for said, _, _ in moves.plain_lines("heldout", None, 6, 5)]),
            ("chatter it never saw", [said for said, _, _ in moves.chatter(4000, 7, held=True)]),
            ("requests", [said for said, _, _ in moves.requests(3000, 31)])):
        print(f"  {name + ', read as hard':40} rules alone {sum(bool(by_rule(t)) for t in lines)}/{len(lines)}   with the model {sum(bad(t) for t in lines)}/{len(lines)}")
    sad = list(safety_sets.safe_but_sad("heldout"))
    print(f"  {'safe-but-sad lines, read as hard':40} rules alone {sum(bool(by_rule(t)) for t in sad)}/{len(sad)}   with the model {sum(bad(t) for t in sad)}/{len(sad)}")


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
