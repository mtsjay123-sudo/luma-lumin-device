"""Teach Luma's small on-device model the best-friend moves (luma.agent.friendtalk), from the packs.

    PYTHONPATH=src python3 scripts/train_moves.py              # score on a fifth of the dev half, then learn from all of it and save
    PYTHONPATH=src python3 scripts/train_moves.py --check      # only the first part: learn from four fifths, score on the fifth
    PYTHONPATH=src python3 scripts/train_moves.py --heldout    # the saved model on the half it never saw: numbers only

Writes src/luma/agent/friendtalk/moves.npz. Only numpy is needed. It's the same kind of model as the understanding
model (scripts/train_understanding.py): a softmax layer over hashed words, word pairs and letter groups.

What it learns from:
- the dev half of the packs: dev frames filled with dev values, each said plain and said messy;
- practice sentences (luma.agent.friendtalk.practice): more ways of saying each move, filled with dev values only;
- ordinary talk that calls for no move (luma.agent.friendtalk.everyday), the phrase bank's chatter, and requests.

What it never sees: the held-out half of the packs and of ordinary talk (friendtalk.half), and one phrase-bank
pattern in five. Those say how much it hears on wording nobody fitted it to. --heldout prints counts, never a line.

How sure it must be before friendtalk believes it (friendtalk.SURE) is chosen with --check, inside the dev half.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import random
import re
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

import train_understanding as base  # noqa: E402  (the same features and the same training loop)
from luma.agent import friendtalk, phrasebank, scenarios, understanding  # noqa: E402
from luma.agent.friendtalk import everyday as plain  # noqa: E402
from luma.agent.friendtalk import practice  # noqa: E402

LABELS = list(friendtalk.MOVES) + ["none"]
OUT = Path(friendtalk.__file__).with_name("moves.npz")
BLANK = re.compile(r"\{(\w+)\}")
OPENERS = ["", "", "", "", "", "", "", "", "hey luma ", "luma ", "hey ", "yo ", "ok ", "okay ", "um ", "so ", "wait ", "actually ",
           "oh and ", "btw ", "quick question ", "real quick ", "ok so ", "bro ", "hmm ", "and ", "also ", "oh ", "be honest ", "ngl ",
           "random but ", "serious question ", "ok luma ", "hey so "]
CLOSERS = ["", "", "", "", "", "", "", "", " lol", " lmao", " fr", " bro", " bruh", "?", "!", "...", " luma", " haha", " fam", " right",
           " for real", " tbh", " ngl", " honestly", " idk", " though"]


def fold(words):
    """Inside the dev half: "check" (one in five, kept out of training with --check) or "fit"."""
    return "check" if int(hashlib.sha1(("fold:" + words).encode()).hexdigest(), 16) % 5 == 0 else "fit"


def held_pattern(frame):
    """One phrase-bank pattern in five is never trained on (the same ones the understanding model never saw)."""
    return zlib.crc32(frame.encode()) % 5 == 0


def dress(text, rng):
    """The same line the way it might really be said: a word in front, a word after, slang, a typo."""
    out = text
    if rng.random() < 0.45:
        out = rng.choice(OPENERS) + out + rng.choice(CLOSERS)
    if rng.random() < 0.5:
        out = scenarios.messy(out, rng, rng.random() * 0.8)
    return out


def shape(frame):
    """A frame with its blanks unnamed, so two frames that say the same thing compare equal."""
    return BLANK.sub("{}", frame)


def _pools(slots, half, part):
    """Each blank's values in this half (and this part of it). A short list can have none in a part: then the half's."""
    pools = {}
    for name, values in slots.items():
        mine = [value for value in values if friendtalk.half(value) == half]
        inside = [value for value in mine if part is None or fold(value) == part]
        pools[name] = inside if len(inside) >= 2 else mine
    return pools


def _fills(frame, pools, per_frame, rng):
    names = BLANK.findall(frame)
    if any(not pools[name] for name in names):
        return []
    ways = 1
    for name in names:
        ways *= len(pools[name])
    seen = []
    known = set()
    for _ in range(min(per_frame, ways) * 3):
        said = frame
        for name in names:
            said = said.replace("{" + name + "}", rng.choice(pools[name]), 1)
        if said not in known:
            known.add(said)
            seen.append(said)
            if len(seen) >= min(per_frame, ways):
                break
    return seen


def pack_lines(half, part, per_frame, seed):
    """(said, move, frame) from one half of the packs: that part's frames filled with that part's values."""
    rng = random.Random(seed)
    out = []
    for pack in friendtalk.every_pack():
        pools = _pools(pack["slots"], half, part)
        for move, frame in pack["frames"]:
            if friendtalk.half(frame) == half and (part is None or fold(frame) == part):
                out += [(said, move, frame) for said in _fills(frame, pools, per_frame, rng)]
    return out


def plain_lines(half, part, per_frame, seed):
    """(said, "none", frame) from one half of ordinary talk, its borrowed blanks filled from the packs' same half."""
    rng = random.Random(seed)
    by_family = {pack["family"]: pack for pack in friendtalk.every_pack()}
    slots = {name: list(values) for name, values in plain.SLOTS.items()}
    for name, (family, slot) in plain.BORROWED.items():
        slots[name] = list(by_family[family]["slots"][slot])
    pools = _pools(slots, half, part)
    out = []
    for frame in plain.FRAMES:
        if friendtalk.half(frame) == half and (part is None or fold(frame) == part):
            out += [(said, "none", frame) for said in _fills(frame, pools, per_frame, rng)]
    return out


def practice_lines(part, per_frame, seed):
    """(said, move, frame) from the practice sentences, filled with the dev half's values (this part's)."""
    rng = random.Random(seed)
    by_family = {pack["family"]: pack for pack in friendtalk.every_pack()}
    slots = {name: list(by_family[family]["slots"][slot]) for name, (family, slot) in practice.BORROWED.items()}
    pools = _pools(slots, "dev", part)
    # A practice sentence that happens to be a pack's sentence is left out: it might be one of the held-out ones.
    taken = {shape(frame) for pack in friendtalk.every_pack() for _, frame in pack["frames"]}
    return [(said, move, frame) for move, frame in practice.FRAMES if shape(frame) not in taken
            for said in _fills(frame, pools, per_frame, rng)]


def chatter(n, seed, held):
    """Phrase-bank chatter (praise, gripes, plans, in 32 communities' words): talk, not a move."""
    keep = held_pattern if held else (lambda frame: not held_pattern(frame))
    return [(row["text"], "none", row["frame"]) for row in phrasebank.sample(n, seed=seed, keep=keep)]


def requests(n, seed):
    """Things asked of Luma, and everyday chat, from the scenario generator: none of it a move."""
    return [(said, "none", intent) for said, intent in scenarios.generate(n, seed=seed)]


def not_a_move(rows):
    """Keep the ordinary lines the rules don't already hear as a move or as needing a fresh look (a few really are)."""
    return [row for row in rows if not friendtalk.by_rule(row[0])]


def training_rows(part, per_frame, seed, with_practice=True):
    """Every line to learn from, with its label. Each pack line is said plain and said dressed up."""
    rng = random.Random(seed)
    rows = []
    taught = pack_lines("dev", part, per_frame, seed) + (practice_lines(part, per_frame, seed + 7) if with_practice else [])
    for said, move, frame in taught:
        rows.append((said, move))
        rows.append((dress(said, rng), move))
    floor = pack_lines("dev", part, 40, seed + 1) + (practice_lines(part, 40, seed + 8) if with_practice else [])
    counts = collections.Counter(frame for _, _, frame in floor)
    for said, move, frame in floor:
        for _ in range(max(0, 24 // counts[frame] - 1)):
            rows.append((dress(said, rng), move))
    quiet = plain_lines("dev", part, per_frame, seed + 2)
    counts = collections.Counter(frame for _, _, frame in quiet)
    for said, label, frame in quiet:
        rows.append((said, label))
        for _ in range(max(1, 24 // counts[frame])):
            rows.append((dress(said, rng), label))
    positives = sum(1 for _, label in rows if label != "none")
    rows += [(said, label) for said, label, _ in not_a_move(chatter(positives // 3, seed + 3, held=False))]
    rows += [(said, label) for said, label, _ in not_a_move(requests(positives // 2, seed + 4))]
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
    """The temperature that makes its confidence honest on lines it didn't learn from."""
    texts = [said for said, _ in rows]
    truth = np.array([LABELS.index(label) for _, label in rows])
    flat, offsets = base.csr(texts)
    best, best_nll = 1.0, 1e9
    for t in (0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.2, 2.6, 3.0):
        p = base.predict(W, b, flat, offsets, t)
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
    """Per move: of its lines, the share the model names with at least this much confidence. And what ordinary talk costs."""
    truth = np.array([LABELS.index(label) for _, label in rows])
    top = p.argmax(1)
    conf = p.max(1)
    none = LABELS.index("none")
    print(f"  {'':12}" + "".join(f"{'>=' + str(cut):>9}" for cut in cuts) + "    lines")
    for i, label in enumerate(LABELS):
        mine = truth == i
        if not mine.any():
            continue
        if label == "none":
            cells = [f"{((top != none) & (conf >= cut))[mine].mean():9.2%}" for cut in cuts]
            print(f"  {'none, heard':12}" + "".join(cells) + f"  {mine.sum():7,}   (lower is better)")
        else:
            cells = [f"{((top == i) & (conf >= cut))[mine].mean():9.1%}" for cut in cuts]
            print(f"  {label:12}" + "".join(cells) + f"  {mine.sum():7,}")
    fair, picks = LABELS.index("fair"), [LABELS.index("take"), LABELS.index("think")]
    mine = truth == fair
    if mine.any():
        cells = [f"{(np.isin(top, picks) & (conf >= cut))[mine].mean():9.2%}" for cut in cuts]
        print(f"  {'fair as take':12}" + "".join(cells) + f"  {mine.sum():7,}   (told to pick a side on what divides people)")


def by_frame(p, rows, frames, cut):
    """The same, one sentence shape one vote: the share of each move's frames that are mostly heard."""
    truth = [label for _, label in rows]
    top = p.argmax(1)
    conf = p.max(1)
    got = collections.defaultdict(lambda: [0, 0])
    for i, frame in enumerate(frames):
        ok = LABELS[top[i]] == truth[i] and conf[i] >= cut if truth[i] != "none" else not (LABELS[top[i]] != "none" and conf[i] >= cut)
        got[(truth[i], frame)][0] += bool(ok)
        got[(truth[i], frame)][1] += 1
    share = collections.defaultdict(list)
    for (label, _), (ok, n) in got.items():
        share[label].append(ok / n)
    return {label: f"{np.mean(values):.0%} of {len(values)}" for label, values in sorted(share.items())}


def check_rows(per_frame, seed):
    rows = [(said, move, frame) for said, move, frame in pack_lines("dev", "check", per_frame, seed)]
    rows += not_a_move(plain_lines("dev", "check", per_frame, seed + 1))
    rows += not_a_move(chatter(4000, seed + 2, held=True))
    rows += not_a_move(requests(4000, seed + 3))
    return rows


def heldout_rows(per_frame, seed):
    rows = [(said, move, frame) for said, move, frame in pack_lines("heldout", None, per_frame, seed)]
    rows += not_a_move(plain_lines("heldout", None, per_frame, seed + 1))
    rows += not_a_move(chatter(4000, seed + 2, held=True))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-frame", type=int, default=240)
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--check", action="store_true", help="learn from four fifths of the dev half and score on the fifth (saves nothing)")
    ap.add_argument("--heldout", action="store_true", help="score the saved model on the half it never saw: numbers only")
    ap.add_argument("--no-practice", action="store_true", help="leave the practice sentences out (to see what they add)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    if args.heldout:
        model = understanding.Model(args.out)
        rows = heldout_rows(60, 5)
        p = np.array([[dict(model.predict(said, len(LABELS)))[label] for label in LABELS] for said, _, _ in rows])
        print(f"the saved model on the held-out half ({len(rows):,} lines; no line is printed):")
        table(p, [(said, label) for said, label, _ in rows])
        return

    # First on four fifths of the dev half, scored on the fifth it didn't see: that's where the temperature comes from,
    # and where friendtalk.SURE was chosen. A model that has seen every dev line can't say how sure it should be.
    rows = training_rows("fit", args.per_frame, 0, with_practice=not args.no_practice)
    counts = collections.Counter(label for _, label in rows)
    print(f"learning from {len(rows):,} lines: " + ", ".join(f"{label} {counts[label]:,}" for label in LABELS), flush=True)
    W, b = fit(rows, args.epochs)
    seen = check_rows(60, 5)
    pairs = [(said, label) for said, label, _ in seen]
    temperature = calibrate(W, b, pairs)
    p = probabilities(W, b, [said for said, _ in pairs], temperature)
    print(f"\non the fifth of the dev half it didn't learn from ({len(pairs):,} lines), temperature {temperature}:")
    table(p, pairs)
    for cut in (0.6, 0.8):
        print(f"  by sentence shape, >= {cut}:", by_frame(p, pairs, [frame for _, _, frame in seen], cut))
    dressed = [(dress(said, random.Random(i)), label) for i, (said, label) in enumerate(pairs)]
    print("the same lines dressed up (a word in front, slang, a typo):")
    table(probabilities(W, b, [said for said, _ in dressed], temperature), dressed)
    if args.check:
        return

    rows = training_rows(None, args.per_frame, 0, with_practice=not args.no_practice)
    counts = collections.Counter(label for _, label in rows)
    print(f"\nnow the whole dev half: {len(rows):,} lines: " + ", ".join(f"{label} {counts[label]:,}" for label in LABELS), flush=True)
    W, b = fit(rows, args.epochs)
    save(W, b, temperature, args.out)

if __name__ == "__main__":
    main()
