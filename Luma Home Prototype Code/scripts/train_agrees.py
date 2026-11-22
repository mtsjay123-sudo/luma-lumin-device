#!/usr/bin/env python3
"""Teach Luma's small on-device model to read a reply that agrees Luma is all they need (luma.agent.agrees).

    PYTHONPATH=src python3 scripts/train_agrees.py              # score on practice reply shapes it didn't learn from, then learn from all and save
    PYTHONPATH=src python3 scripts/train_agrees.py --check      # only the first part (saves nothing)
    PYTHONPATH=src python3 scripts/train_agrees.py --heldout    # patterns alone, then patterns with the saved model, on sets C, D and E: numbers only

Writes src/luma/agent/agrees.npz. Only numpy is needed. The same kind of model as the one that hears leaning
(scripts/train_hears.py): a softmax layer over hashed words, word pairs and letter groups.

What it learns from:
- the practice replies in luma/agent/agrees.py, each alone and with a warm sentence before or after it (a real reply is
  two or three sentences, and one of them agreeing is enough);
- the two sets the patterns were built on (tests/leans_replies.py: KEEPS_A, KEEPS_B, FINE_A, FINE_B);
- Luma's own lines and the replies in its practice data (scripts/finetune_data.py) as "fine".

What it never sees: sets C, D and E. --heldout prints counts, never a line.
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

import train_moves as moves  # noqa: E402  (filling a shape's blanks)
import train_understanding as base  # noqa: E402
from luma.agent import agrees, friendcheck  # noqa: E402

LABELS = agrees.LABELS
OUT = agrees.LEARNED


def fold(frame):
    """A practice reply shape is "check" (one in five, kept out with --check) or "fit"."""
    return "check" if int(hashlib.sha1(("agrees:" + frame).encode()).hexdigest(), 16) % 5 == 0 else "fit"


def by_pattern(reply):
    return bool(friendcheck.KEEPS_THEM.search(reply) or friendcheck.KEPT_CLOSE.search(reply) or friendcheck.KEEPS_THEM_TOO.search(reply))


def practice(part, per_frame, seed):
    """(reply, label, frame) from the practice replies."""
    rng = random.Random(seed)
    out = []
    for label, frame in agrees.FRAMES:
        if part is not None and fold(frame) != part:
            continue
        out += [(reply, label, frame) for reply in moves._fills(frame, agrees.SLOTS, per_frame, rng)]
    return out


def said_many_ways(reply, label, fine, rng, n=2):
    """The reply alone, and inside a longer one: a warm sentence before it or after it. For a fine reply, beside another fine one."""
    out = [(reply, label)]
    for _ in range(n):
        other = rng.choice(agrees.SLOTS["warm"]) if label == "agrees" or not fine else rng.choice(fine)
        out.append(((other + " " + reply) if rng.random() < 0.5 else (reply + " " + other), label))
    if rng.random() < 0.3:
        out.append((reply.lower().rstrip(".!"), label))   # a small brain often answers in lowercase
    return out


def lumas_own():
    """Replies in Luma's practice data and its own written lines: all "fine". The few a pattern already reads are left out."""
    import finetune_data
    seen, out = set(), []
    for row in finetune_data.examples(random.Random(7)):
        for m in row["messages"]:
            text = " ".join(str(m.get("content") or "").split())
            if m.get("role") == "assistant" and 8 <= len(text) <= 300 and text not in seen and not by_pattern(text):
                seen.add(text)
                out.append(text)
    own = [friendcheck.NOT_ONLY_ME, friendcheck.CARES_HONESTLY, friendcheck.NO_ROMANCE, friendcheck.GLAD_YOURE_HERE]
    return sorted(out), [str(line) for line in own if isinstance(line, str)]


def built_on():
    """The two sets the patterns were built on. Never C, D or E."""
    import leans_replies
    keeps = [reply for name in ("KEEPS_A", "KEEPS_B") for _, reply in leans_replies.pairs(name)]
    fine = [reply for name in ("FINE_A", "FINE_B") for _, reply in leans_replies.pairs(name)]
    return keeps, fine


def held(text):
    """One in five of Luma's own practice replies is kept out of the fit, to count what the model gets wrong on replies it never saw."""
    return int(hashlib.sha1(("fine:" + text).encode()).hexdigest(), 16) % 5 == 0


def training_rows(part, per_frame, seed):
    rng = random.Random(seed)
    rows = []
    shapes = practice(part, per_frame, seed)
    fine_pool = [reply for reply, label, _ in shapes if label == "fine"]
    for reply, label, _ in shapes:
        rows += said_many_ways(reply, label, fine_pool, rng)
    keeps, fine = built_on()
    for reply in keeps:
        rows += said_many_ways(reply, "agrees", fine_pool, rng, 4) * 2
    for reply in fine:
        rows += said_many_ways(reply, "fine", fine_pool, rng, 2) * 2
    replies, own = lumas_own()
    rows += [(reply, "fine") for reply in replies if part is None or not held(reply)]
    rows += [(line, "fine") for line in own] * 6
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
    """Of the agreeing replies, how many the model names this surely and that also have the plain shape. And what fine replies cost:
    the practice shapes written to look like agreeing, and Luma's own practice replies kept out of the fit."""
    truth = np.array([LABELS.index(label) for _, label in rows])
    sure = p[:, 0]
    shaped = np.array([agrees.has_shape(said) for said, _ in rows])
    own = set(lumas_own()[0])
    mine_own = np.array([said in own for said, _ in rows])
    print(f"  {'':34}" + "".join(f"{'>=' + str(cut):>8}" for cut in cuts) + "    replies")
    for name, mine in (("agrees, read", truth == 0), ("fine shapes, read wrongly", (truth == 1) & ~mine_own),
                       ("Luma's own replies, read wrongly", (truth == 1) & mine_own)):
        print(f"  {name:34}" + "".join(f"{int(((sure >= cut) & shaped)[mine].sum()):8d}" for cut in cuts) + f"  {int(mine.sum()):9,}")


def check_rows(seed):
    rng = random.Random(seed)
    shapes = practice("check", 40, seed)
    fine_pool = [reply for reply, label, _ in shapes if label == "fine"]
    rows = []
    for reply, label, _ in shapes:
        rows += said_many_ways(reply, label, fine_pool, rng)
    replies, _ = lumas_own()
    return rows + [(reply, "fine") for reply in replies if held(reply)]


def heldout():
    """Patterns alone, then patterns with the model, on the three sets written after the patterns. Counts only."""
    import leans_replies
    print("on sets C, D and E (no reply is printed):")
    full = lambda reply: by_pattern(reply) or agrees.by_model(reply)  # noqa: E731
    total = {"keeps": [0, 0, 0], "fine": [0, 0, 0]}
    for name in "CDE":
        for kind in ("KEEPS", "FINE"):
            replies = [reply for _, reply in leans_replies.pairs(f"{kind}_{name}")]
            a, b = sum(by_pattern(r) for r in replies), sum(full(r) for r in replies)
            t = total["keeps" if kind == "KEEPS" else "fine"]
            t[0] += a; t[1] += b; t[2] += len(replies)
            print(f"  {name}, {'agreeing' if kind == 'KEEPS' else 'good    '}: patterns alone {a}/{len(replies)}   with the model {b}/{len(replies)}")
    print(f"  all three: agreeing replies read {total['keeps'][0]} -> {total['keeps'][1]} of {total['keeps'][2]}; "
          f"good replies read wrongly {total['fine'][0]} -> {total['fine'][1]} of {total['fine'][2]}")


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
    print(f"learning from {len(rows):,} replies: " + ", ".join(f"{label} {counts[label]:,}" for label in LABELS), flush=True)
    W, b = fit(rows, args.epochs)
    seen = check_rows(5)
    temperature = calibrate(W, b, seen)
    print(f"\non practice reply shapes it didn't learn from, and Luma's own replies kept out ({len(seen):,} replies), temperature {temperature}:")
    table(probabilities(W, b, [said for said, _ in seen], temperature), seen)
    if args.check:
        return
    rows = training_rows(None, args.per_frame, 0)
    counts = collections.Counter(label for _, label in rows)
    print(f"\nnow everything: {len(rows):,} replies: " + ", ".join(f"{label} {counts[label]:,}" for label in LABELS), flush=True)
    W, b = fit(rows, args.epochs)
    save(W, b, temperature, args.out)


if __name__ == "__main__":
    main()
