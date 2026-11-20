#!/usr/bin/env python3
"""An experiment that did not ship: teach a small model to read a hard moment the feeling rules miss.

    PYTHONPATH=src python3 scripts/train_feels.py              # score on practice shapes it didn't learn from, then learn from all and save to out/
    PYTHONPATH=src python3 scripts/train_feels.py --check      # only the first part (saves nothing)
    PYTHONPATH=src python3 scripts/train_feels.py --heldout    # rules alone, then rules with the saved model, on the held-out half: numbers only

Result (Nov 20, 2026): not good enough, and not wired into Luma. See scripts/feels_practice.py and docs/HUMAN_PLAN.md.
Writes out/feels.npz, which nothing loads. Kept so the numbers can be checked and the practice sentences reused.

What it learns from:
- the practice sentences in scripts/feels_practice.py (nine hard feelings, and ordinary lines with heavy words in
  them), each said plain and said messy;
- the dev half of hard-or-not (tests/hard_or_not.py): hard lines under the feeling the rules read in them, ordinary
  lines as "none";
- ordinary talk as "none": the dev halves of keep-or-today, of what a child says and of friendtalk's everyday talk,
  the phrase bank's chatter, requests, and the practice sentences for "what are you?".

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

import train_hears as th  # noqa: E402  (the same fitting, calibrating and saving)
import train_moves as moves  # noqa: E402
import feels_practice as feels  # noqa: E402
from luma.agent import feelings  # noqa: E402

LABELS = feels.LABELS
OUT = feels.LEARNED
NONE = LABELS.index("none")


def fold(frame):
    return "check" if int(hashlib.sha1(("feels:" + frame).encode()).hexdigest(), 16) % 5 == 0 else "fit"


def by_rule(said):
    """The hard feeling the rules alone read here, or None."""
    felt = feelings.read(said)
    return felt["family"] if felt and felt["family"] in feels.HARD else None


def practice(part, per_frame, seed):
    rng = random.Random(seed)
    out = []
    for label, frame in feels.FRAMES:
        if part is None or fold(frame) == part:
            out += [(said, label, frame) for said in moves._fills(frame, feels.SLOTS, per_frame, rng)]
    return out


def dev_sets():
    """(said, label) from dev halves only."""
    import hard_or_not
    import keep_or_today
    import safety_sets
    rows = []
    for said, label in hard_or_not.lines("dev"):
        if label == "hard":
            if by_rule(said):
                rows.append((said, by_rule(said)))
        else:
            rows.append((said, "none"))
    rows += [(t, "none") for t, _ in keep_or_today.lines("dev")] + [(t, "none") for t in safety_sets.kids("dev")]
    return rows


def calm(rows):
    """Ordinary lines only: one the rules already read as a hard feeling is never taught as "none"."""
    return [row for row in rows if not by_rule(row[0])]


def training_rows(part, per_frame, seed):
    rng = random.Random(seed)
    rows = []
    taught = practice(part, per_frame, seed)
    counts = collections.Counter(frame for _, _, frame in taught)
    for said, label, frame in taught:
        rows.append((said, label))
        # A sentence with no blank is one line; one with two blanks is forty. Each shape gets about the same say.
        rows += [(moves.dress(said, rng), label) for _ in range(max(3, 48 // counts[frame]))]
    for said, label in dev_sets():
        rows.append((said, label))
        if label != "none":
            rows += [(moves.dress(said, rng), label) for _ in range(2)]
    positives = sum(1 for _, label in rows if label != "none")
    quiet = [(said, "none") for said, _, _ in moves.plain_lines("dev", None, 6, seed + 2)]
    quiet += [(said, "none") for said, _, _ in moves.chatter(positives, seed + 3, held=False)]
    quiet += [(said, "none") for said, _, _ in moves.requests(positives, seed + 4)]
    quiet += [(said, "none") for said, label, _ in th.practice(part, 6, seed + 5) if label != "leaning"]
    rows += calm(quiet)
    rng.shuffle(rows)
    return rows


def fit(rows, epochs):
    flat, offsets = th.base.csr([said for said, _ in rows])
    y = np.array([LABELS.index(label) for _, label in rows])
    return th.base.train(flat, offsets, y, len(LABELS), epochs)


def calibrate(W, b, rows):
    texts = [said for said, _ in rows]
    truth = np.array([LABELS.index(label) for _, label in rows])
    best, best_nll = 1.0, 1e9
    for t in (0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.2, 2.6, 3.0, 4.0):
        p = th.probabilities(W, b, texts, t)
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
    """Of the hard lines: how many are heard as hard at all, and as the right feeling. Of the ordinary ones: how many wrongly."""
    truth = np.array([LABELS.index(label) for _, label in rows])
    shaped = np.array([feels.has_shape(said) for said, _ in rows])
    hard = 1.0 - p[:, NONE]
    best = p[:, :NONE].argmax(1)
    mine = truth != NONE
    print(f"  {'':28}" + "".join(f"{'>=' + str(cut):>8}" for cut in cuts) + "    lines")
    print(f"  {'hard, heard as hard':28}" + "".join(f"{int(((hard >= cut) & shaped)[mine].sum()):8d}" for cut in cuts) + f"  {int(mine.sum()):7,}")
    print(f"  {'  and as the right feeling':28}" + "".join(f"{int(((hard >= cut) & shaped & (best == truth))[mine].sum()):8d}" for cut in cuts))
    print(f"  {'ordinary, heard as hard':28}" + "".join(f"{int(((hard >= cut) & shaped)[~mine].sum()):8d}" for cut in cuts) + f"  {int((~mine).sum()):7,}")


def check_rows(seed):
    rows = [(said, label) for said, label, _ in practice("check", 40, seed)]
    rng = random.Random(seed)
    rows += [(moves.dress(said, rng), label) for said, label in list(rows)]
    quiet = [(said, "none") for said, _, _ in moves.chatter(3000, seed + 2, held=True)]
    quiet += [(said, "none") for said, _, _ in moves.requests(3000, seed + 30)]
    return rows + calm(quiet)


def heldout():
    """Rules alone, then rules with the model, on the halves nothing was fitted to. Counts only."""
    import hard_or_not
    import keep_or_today
    import safety_sets
    rows = hard_or_not.lines("heldout")
    hard = [t for t, lab in rows if lab == "hard"]
    not_hard = [t for t, lab in rows if lab == "not"]
    rule = lambda t: hard_or_not.read_as_hard(t)                           # noqa: E731
    full = lambda t: hard_or_not.read_as_hard(t) or bool(feels.family(t))  # noqa: E731
    print("on the held-out halves (no line is printed):")
    print(f"  hard moments read as hard        rules alone {sum(rule(t) for t in hard)}/{len(hard)}   with the model {sum(full(t) for t in hard)}/{len(hard)}")
    print(f"  ordinary lines read as hard      rules alone {sum(rule(t) for t in not_hard)}/{len(not_hard)}   with the model {sum(full(t) for t in not_hard)}/{len(not_hard)}")
    others = {"facts and passing remarks (keep-or-today)": [t for t, _ in keep_or_today.lines("heldout")],
              "what a child says": safety_sets.kids("heldout"),
              "everyday talk": [said for said, _, _ in moves.plain_lines("heldout", None, 6, 5)],
              "chatter (praise, gripes, plans)": [said for said, _, _ in moves.chatter(4000, 7, held=True)],
              "asked what it is": safety_sets.what_i_am("heldout")}
    for name, lines in others.items():
        print(f"  {name + ', newly read as hard':52} {sum(bool(feels.family(t)) and not by_rule(t) for t in lines)}/{len(lines)}")


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
    table(th.probabilities(W, b, [said for said, _ in seen], temperature), seen)
    if args.check:
        return
    rows = training_rows(None, args.per_frame, 0)
    counts = collections.Counter(label for _, label in rows)
    print(f"\nnow everything: {len(rows):,} lines: " + ", ".join(f"{label} {counts[label]:,}" for label in LABELS), flush=True)
    W, b = fit(rows, args.epochs)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    save(W, b, temperature, args.out)


if __name__ == "__main__":
    main()
