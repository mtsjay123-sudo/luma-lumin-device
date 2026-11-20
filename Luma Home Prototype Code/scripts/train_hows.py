#!/usr/bin/env python3
"""Teach Luma's small on-device model how someone asks to be met on a hard evening (luma.agent.hows).

    PYTHONPATH=src python3 scripts/train_hows.py              # score on practice shapes it didn't learn from, then learn from all and save
    PYTHONPATH=src python3 scripts/train_hows.py --check      # only the first part (saves nothing)
    PYTHONPATH=src python3 scripts/train_hows.py --heldout    # how many held-out lines would newly teach a wish: numbers only

Writes src/luma/agent/hows.npz. Only numpy is needed. The same kind of model as the best-friend moves
(scripts/train_moves.py): a softmax layer over hashed words, word pairs and letter groups.

What it learns from:
- the practice sentences in luma/agent/hows.py, each said plain and said messy;
- the forty wishes written as practice for the brain (scripts/finetune_data.py, AS_THEY_ASKED), and what was said on
  those evenings as "none";
- as "none": the dev halves of hard-or-not, the safe-but-sad lines, a worry that builds and what a child says, the
  crisis corpus the net was built on, friendtalk's everyday talk (dev half), the phrase bank's chatter, and requests.

What it never sees: any held-out half, or the fresh lines in tests/test_rapport.py. --heldout prints counts, never a line.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT / "tests")]

import train_hears as th  # noqa: E402  (the same fitting and saving)
import train_moves as moves  # noqa: E402
from luma.agent import hows, rapport  # noqa: E402

LABELS = hows.LABELS
OUT = hows.LEARNED
NONE = LABELS.index("none")


def fold(frame):
    """A practice sentence shape is "check" (one in five, kept out with --check) or "fit"."""
    return "check" if int(hashlib.sha1(("hows:" + frame).encode()).hexdigest(), 16) % 5 == 0 else "fit"


def practice(part, per_frame, seed):
    rng = random.Random(seed)
    out = []
    for label, frame in hows.FRAMES:
        if part is None or fold(frame) == part:
            out += [(said, label, frame) for said in moves._fills(frame, hows.SLOTS, per_frame, rng)]
    return out


def dev_sets():
    """(said, label) from dev halves and Luma's own practice only."""
    import finetune_data
    import hard_or_not
    import safety_sets
    rows = [(asked, style) for style, items in finetune_data.AS_THEY_ASKED.items() for asked, _, _ in items]
    rows += [(said, "none") for items in finetune_data.AS_THEY_ASKED.values() for _, said, _ in items]
    rows += [(t, "none") for t, _ in hard_or_not.lines("dev")]
    rows += [(t, "none") for t in safety_sets.safe_but_sad("dev") + safety_sets.kids("dev")]
    rows += [(t, "none") for c in safety_sets.slow_burn("dev") for t in c["turns"]]
    for line in (ROOT / "tests" / "data" / "crisis_corpus.jsonl").read_text().splitlines():  # never either held-out set
        if line.strip():
            row = json.loads(line)
            said = str(row.get("text") or row.get("said") or "")
            if said:
                rows.append((said, "none"))
    return rows


def training_rows(part, per_frame, seed):
    rng = random.Random(seed)
    rows = []
    taught = practice(part, per_frame, seed)
    counts = collections.Counter(frame for _, _, frame in taught)
    for said, label, frame in taught:
        rows.append((said, label))
        rows += [(moves.dress(said, rng), label) for _ in range(max(2, 30 // counts[frame]))]   # each shape gets about the same say
    for said, label in dev_sets():
        rows.append((said, label))
        if label != "none":
            rows += [(moves.dress(said, rng), label) for _ in range(3)]
    wishes = sum(1 for _, label in rows if label != "none")
    quiet = [(said, "none") for said, _, _ in moves.plain_lines("dev", None, 6, seed + 2)]
    quiet += [(said, "none") for said, _, _ in moves.chatter(wishes // 2, seed + 3, held=False)]
    quiet += [(said, "none") for said, _, _ in moves.requests(wishes // 3, seed + 4)]
    rows += [row for row in quiet if not rapport.said_how_by_rule(row[0])]
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
    """Of the wishes: how many would be heard the right way (sure, with the shape, nothing saying no), and the wrong way.
    Of everything else: how many would wrongly teach a wish."""
    truth = np.array([LABELS.index(label) for _, label in rows])
    top = p.argmax(axis=1)
    sure = p.max(axis=1)
    ok = np.array([hows.has_shape(said) and not hows.NO.search(said) and not hows.NOT_LISTEN.search(said) for said, _ in rows])
    wish = truth != NONE
    print(f"  {'':34}" + "".join(f"{'>=' + str(cut):>8}" for cut in cuts) + "    lines")
    for name, mask, hit in (("a wish, heard the right way", wish, top == truth), ("a wish, heard the wrong way", wish, (top != truth) & (top != NONE)),
                            ("not a wish, heard as one", ~wish, top != NONE)):
        print(f"  {name:34}" + "".join(f"{int(((sure >= cut) & ok & hit)[mask].sum()):8d}" for cut in cuts) + f"  {int(mask.sum()):7,}")


def check_rows(seed):
    rows = [(said, label) for said, label, _ in practice("check", 40, seed)]
    rng = random.Random(seed)
    rows += [(moves.dress(said, rng), label) for said, label in list(rows)]
    quiet = [(said, "none") for said, _, _ in moves.chatter(3000, seed + 2, held=True)]
    quiet += [(said, "none") for said, _, _ in moves.requests(3000, seed + 30)]
    return rows + [row for row in quiet if not rapport.said_how_by_rule(row[0])]


def heldout():
    """How many lines of the held-out halves would newly teach a wish. Counts only."""
    import hard_or_not
    import keep_or_today
    import safety_sets
    sets = {"hard moments and ordinary lines (hard-or-not)": [t for t, _ in hard_or_not.lines("heldout")],
            "safe but sad": safety_sets.safe_but_sad("heldout"),
            "what a child says": safety_sets.kids("heldout"),
            "leaning on Luma": safety_sets.leaning("heldout"),
            "asked what it is": safety_sets.what_i_am("heldout"),
            "a worry that builds": [t for c in safety_sets.slow_burn("heldout") for t in c["turns"]],
            "keep-or-today": [t for t, _ in keep_or_today.lines("heldout")],
            "everyday talk": [said for said, _, _ in moves.plain_lines("heldout", None, 6, 5)],
            "chatter (praise, gripes, plans)": [said for said, _, _ in moves.chatter(4000, 7, held=True)]}
    print("on the held-out halves (no line is printed): lines that would teach Luma a wish")
    for name, lines in sets.items():
        print(f"  {name:50} by the model {sum(bool(hows.by_model(t)) for t in lines)}/{len(lines)}   by rule {sum(bool(rapport.said_how_by_rule(t)) for t in lines)}/{len(lines)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-frame", type=int, default=60)
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
    save(W, b, temperature, args.out)


if __name__ == "__main__":
    main()
