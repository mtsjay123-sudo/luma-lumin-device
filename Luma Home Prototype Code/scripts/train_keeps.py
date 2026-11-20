#!/usr/bin/env python3
"""Teach Luma's small on-device model to know a lasting fact said a new way (luma.agent.keeps).

    PYTHONPATH=src python3 scripts/train_keeps.py              # score on practice shapes it didn't learn from, then learn from all and save
    PYTHONPATH=src python3 scripts/train_keeps.py --check      # only the first part (saves nothing)
    PYTHONPATH=src python3 scripts/train_keeps.py --heldout    # rules alone, then rules with the saved model, on the held-out halves: numbers only

Writes src/luma/agent/keeps.npz. Only numpy is needed. The same kind of model as the best-friend moves
(scripts/train_moves.py): a softmax layer over hashed words, word pairs and letter groups.

What it learns from:
- the practice sentences in luma/agent/keeps.py, each said plain and said messy;
- the dev half of keep-or-today (tests/keep_or_today.py), as marked there;
- as "today": the dev halves of hard-or-not, the safe-but-sad lines, a worry that builds and what a child says, the
  crisis corpus the net was built on, friendtalk's everyday talk (dev half), the phrase bank's chatter, and requests. A line the rules already read as a fact is never taught
  as "today".

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
from luma.agent import keeps, people, presence  # noqa: E402

LABELS = keeps.LABELS
OUT = keeps.LEARNED
KEEP = LABELS.index("keep")


def fold(frame):
    """A practice sentence shape is "check" (one in five, kept out with --check) or "fit"."""
    return "check" if int(hashlib.sha1(("keeps:" + frame).encode()).hexdigest(), 16) % 5 == 0 else "fit"


def by_rule(said):
    """Do the rules alone make a card of this?"""
    return bool(presence.notice_facts(said) + people.facts(said))


def practice(part, per_frame, seed):
    rng = random.Random(seed)
    out = []
    for label, frame in keeps.FRAMES:
        if part is None or fold(frame) == part:
            out += [(said, label, frame) for said in moves._fills(frame, keeps.SLOTS, per_frame, rng)]
    return out


def dev_sets():
    """(said, label) from dev halves only."""
    import hard_or_not
    import keep_or_today
    import safety_sets
    rows = list(keep_or_today.lines("dev"))
    rows += [(t, "today") for t, _ in hard_or_not.lines("dev")]
    rows += [(t, "today") for t in safety_sets.safe_but_sad("dev") + safety_sets.kids("dev")]
    rows += [(t, "today") for c in safety_sets.slow_burn("dev") for t in c["turns"]]
    import json   # the crisis corpus the net was built on (never either held-out set): none of it is ever a card
    for line in (ROOT / "tests" / "data" / "crisis_corpus.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            said = str(row.get("text") or row.get("said") or "")
            if said:
                rows.append((said, "today"))
    return rows


def passing(rows):
    """Ordinary lines only: one the rules already read as a fact is never taught as "today"."""
    return [row for row in rows if not by_rule(row[0])]


def training_rows(part, per_frame, seed):
    rng = random.Random(seed)
    rows = []
    taught = practice(part, per_frame, seed)
    counts = collections.Counter(frame for _, _, frame in taught)
    for said, label, frame in taught:
        rows.append((said, label))
        # A sentence with no blank is one line; one with two blanks is forty. Each shape gets about the same say.
        rows += [(moves.dress(said, rng), label) for _ in range(max(3, 40 // counts[frame]))]
    for said, label in dev_sets():
        rows.append((said, label))
        if label == "keep":
            rows += [(moves.dress(said, rng), label) for _ in range(3)]
    keeps_n = sum(1 for _, label in rows if label == "keep")
    quiet = [(said, "today") for said, _, _ in moves.plain_lines("dev", None, 6, seed + 2)]
    quiet += [(said, "today") for said, _, _ in moves.chatter(keeps_n, seed + 3, held=False)]
    quiet += [(said, "today") for said, _, _ in moves.requests(keeps_n // 2, seed + 4)]
    rows += passing(quiet)
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
    """Of the lasting facts: how many would be kept (sure, and with the plain shape). Of what's only today: how many wrongly."""
    truth = np.array([LABELS.index(label) for _, label in rows])
    shaped = np.array([keeps.has_shape(said) for said, _ in rows])
    sure = p[:, KEEP]
    mine = truth == KEEP
    print(f"  {'':30}" + "".join(f"{'>=' + str(cut):>8}" for cut in cuts) + "    lines")
    print(f"  {'lasting, kept':30}" + "".join(f"{int(((sure >= cut) & shaped)[mine].sum()):8d}" for cut in cuts) + f"  {int(mine.sum()):7,}")
    print(f"  {'only today, kept wrongly':30}" + "".join(f"{int(((sure >= cut) & shaped)[~mine].sum()):8d}" for cut in cuts) + f"  {int((~mine).sum()):7,}")


def check_rows(seed):
    rows = [(said, label) for said, label, _ in practice("check", 40, seed)]
    rng = random.Random(seed)
    rows += [(moves.dress(said, rng), label) for said, label in list(rows)]
    quiet = [(said, "today") for said, _, _ in moves.chatter(3000, seed + 2, held=True)]
    quiet += [(said, "today") for said, _, _ in moves.requests(3000, seed + 30)]
    return rows + passing(quiet)


def heldout():
    """Rules alone, then rules with the model, on the halves nothing was fitted to. Counts only."""
    import hard_or_not
    import keep_or_today
    import safety_sets
    rows = keep_or_today.lines("heldout")
    keep = [t for t, lab in rows if lab == "keep"]
    today = [t for t, lab in rows if lab == "today"]
    print("on the held-out halves (no line is printed):")
    print(f"  a lasting fact becomes a card      rules alone {sum(by_rule(t) for t in keep)}/{len(keep)}   with the model {sum(bool(keeps.cards(t)) for t in keep)}/{len(keep)}")
    print(f"  a passing remark becomes a card    rules alone {sum(by_rule(t) for t in today)}/{len(today)}   with the model {sum(bool(keeps.cards(t)) for t in today)}/{len(today)}")
    others = {"hard moments and ordinary lines (hard-or-not)": [t for t, _ in hard_or_not.lines("heldout")],
              "safe but sad": safety_sets.safe_but_sad("heldout"),
              "what a child says": safety_sets.kids("heldout"),
              "leaning on Luma": safety_sets.leaning("heldout"),
              "asked what it is": safety_sets.what_i_am("heldout"),
              "everyday talk": [said for said, _, _ in moves.plain_lines("heldout", None, 6, 5)],
              "chatter (praise, gripes, plans)": [said for said, _, _ in moves.chatter(4000, 7, held=True)]}
    for name, lines in others.items():
        print(f"  {name + ', newly a card':58} {sum(bool(keeps.card(t)) and not by_rule(t) for t in lines)}/{len(lines)}")


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
    save(W, b, temperature, args.out)


if __name__ == "__main__":
    main()
