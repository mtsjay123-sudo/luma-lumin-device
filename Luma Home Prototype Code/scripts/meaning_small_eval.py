#!/usr/bin/env python3
"""An experiment: can a meaning model small enough for the lamp find what was told in other words?

Asked in the fact's own words, Luma finds a fact among a thousand memories. Asked in other words ("who do i see about my
glasses" / "my eye doctor is Dr. Marchetti") it mostly doesn't, and says "never told" (tests/test_a_fact_in_a_crowd.py:
19 of 40 found, 11 wrongly "never told"). The meaning model Luma has (luma.memory.meaning: Qwen3-Embedding-0.6B) runs
on computers with 16 GB, not on a $250 lamp. This tries a static one: a table of word-piece meanings averaged over a
sentence, no network to run, a few megabytes, numpy only (model2vec, MIT).

    python -I scripts/meaning_small_eval.py --model <a folder holding the model>

It stands in for luma.memory.meaning for the length of the run and changes nothing in Luma. Printed: the two fresh sets
of forty, the memory test on its built-on lives, and on the held-out lives (counts only, never a line), with words
alone and with the small model at a few settings of how close a memory has to be. What to watch: found in other
words going up, and "never told" still said when it was never told (the memory test's "never" kind).

The model is a download: it sits in a folder of its own, and this is run with -I.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT / "tests")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="a folder holding a model2vec static model")
    ap.add_argument("--close", default="0.35,0.45,0.55,0.65", help="how close a memory has to be to count (cosine), one run for each")
    ap.add_argument("--size", type=int, default=1000)
    args = ap.parse_args()

    import numpy as np
    from model2vec import StaticModel
    import memory_eval
    import test_a_fact_in_a_crowd as crowd
    from luma.memory import meaning
    from luma.memory.store import Store

    card = Path(args.model) / "README.md"
    if card.exists():
        said = [line.strip() for line in card.read_text(errors="replace").splitlines()[:40] if line.lower().startswith("license")]
        print("the model's card says:", "; ".join(said) or "(no license line in the first 40 lines)")
    model = StaticModel.from_pretrained(args.model)

    def unit(texts):
        vectors = np.asarray(model.encode(list(texts)), dtype=np.float32)
        return vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-9)

    print(f"one sentence is {unit(['hello there']).shape[1]} numbers")
    state = {"close": None, "rows": {}}

    def near(store, index, query, limit):
        """[(how close, row)] by meaning, the shape Store._near hands the index."""
        key = (id(store), len(index.ids))
        if key not in state["rows"]:
            state["rows"].clear()
            texts = {m["id"]: m.get("text", "") for m in store._read([i for i in index.ids if i is not None])}
            state["rows"][key] = unit([texts.get(i, "") for i in index.ids])
        close = state["rows"][key] @ unit([query])[0]
        best = np.argsort(-close)[:limit]
        return [(float(close[r]), int(r)) for r in best if close[r] >= state["close"]]

    was_available, was_near = meaning.available, Store._near

    def report(label):
        plain, other, never = crowd.asked(crowd.BUILT_ON)
        print(f"  {label:22} forty built-on facts: plain {plain}/40, other words {other}/40, wrongly never told {never}")
        plain, other, never = crowd.asked(crowd.SECOND)
        print(f"  {label:22} the second forty:     plain {plain}/40, other words {other}/40, wrongly never told {never}")
        for split in ("dev", "heldout"):
            totals = {}
            told = [0, 0]
            for seed in memory_eval.SEEDS[split]:
                one = memory_eval.run_one(seed, args.size, split, forget=False)
                for kind, counts in one["by_kind"].items():
                    got = counts if isinstance(counts, (list, tuple)) else (counts.get("right", counts.get("hit", 0)), counts.get("asked", counts.get("n", 0)))
                    have = totals.setdefault(kind, [0, 0])
                    have[0] += got[0]
                    have[1] += got[1]
                told[0] += one["told"]["said_never"]
                told[1] += one["told"]["asked"]
            print(f"  {label:22} memory test, {split:8}: " + ", ".join(f"{kind} {a}/{b}" for kind, (a, b) in sorted(totals.items()))
                  + f"; told but said never told {told[0]}/{told[1]}")

    try:
        meaning.available = lambda store: False
        print("words alone:")
        report("words alone")
        meaning.available = lambda store: True
        Store._near = near
        for close in [float(x) for x in args.close.split(",")]:
            state["close"] = close
            state["rows"].clear()
            print(f"with the small model, a memory counts at {close} or closer:")
            report(f"small model @ {close}")
    finally:
        meaning.available, Store._near = was_available, was_near


if __name__ == "__main__":
    main()
