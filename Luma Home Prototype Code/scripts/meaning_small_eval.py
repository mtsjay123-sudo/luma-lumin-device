#!/usr/bin/env python3
"""What the lamp's small meaning model does for recall, measured (luma.memory.meaning, the "small" engine).

Asked in the fact's own words, Luma finds a fact among a thousand memories. Asked in other words ("who do i see about my
glasses" / "my eye doctor is Dr. Marchetti") it mostly doesn't, and says "never told" (tests/test_a_fact_in_a_crowd.py:
19 of 40 found, 11 wrongly "never told"). The meaning model Luma has for that runs on computers with 16 GB. The lamp's
is a static one: a row of numbers for each word-piece, averaged over a sentence (potion-base-8M, MIT, 30 MB).

    python -I scripts/meaning_small_eval.py --model <a folder holding model.safetensors and tokenizer.json>

It runs Luma's own reader of that model through Luma's own search, with the switch on for the length of the run, and
prints: the two fresh sets of forty, the memory test on its built-on lives, and on the held-out lives (counts only,
never a line), with words alone and with the small model at a few settings of how close a memory has to be. What to
watch: found in other words going up, and "never told" still said when it was never told (the memory test's "never").

With the model2vec package here too, it first checks that Luma's reader gives the same numbers for a sentence as the
package the model was made with.

The model is a download: it sits in a folder of its own, and this is run with -I. Here in the cloud session it can't be
fetched; GitHub's machines can (meaning-small.yml).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT / "tests")]

SAME = ["my eye doctor is Dr. Marchetti", "who do i see about my glasses", "the trash goes out Monday and Thursday", "what days is garbage pickup",
        "I keep my passport in the fireproof box under the bed", "hello there", "ok", "¿dónde está mi pasaporte?", "it's 7:42, I'm late again!!"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="a folder holding the static model's files")
    ap.add_argument("--close", default="0.35,0.4,0.45,0.55", help="how close a memory has to be to count (cosine), one run for each")
    ap.add_argument("--size", type=int, default=1000)
    args = ap.parse_args()

    import numpy as np
    import memory_eval
    import test_a_fact_in_a_crowd as crowd
    from luma.memory import meaning

    folder = Path(args.model)
    card = folder / "README.md"
    if card.exists():
        said = [line.strip() for line in card.read_text(errors="replace").splitlines()[:40] if line.lower().startswith("license")]
        print("the model's card says:", "; ".join(said) or "(no license line in the first 40 lines)")
    (folder / "ok").write_text(meaning.SMALL_TAG)

    kept = {name: getattr(meaning, name) for name in ("small_folder", "small_wanted", "model_path", "available", "catch_up", "SMALL_CLOSE", "embedder")}
    real_catch_up, real_available = meaning.catch_up, meaning.available
    try:
        meaning.small_folder = lambda: folder
        meaning.model_path = lambda: None                 # never the bigger model, even where it is
        meaning.embedder = None
        meaning.small_wanted = lambda store: True         # the owner's yes, for the length of this run
        meaning.catch_up = lambda store, memories, wait=False: real_catch_up(store, memories, wait=True)   # worked out before the answer, not behind it
        if meaning.engine() != "small":
            raise SystemExit("Luma couldn't read the model in that folder (it needs model.safetensors, tokenizer.json and the tokenizers package).")
        meaning._embed("hello there")                     # reads the model in
        if meaning.engine() != "small":
            raise SystemExit("Luma couldn't read the model in that folder.")
        rows = meaning._small["model"].rows
        print(f"Luma's own reader: {rows.shape[0]:,} word-pieces, {rows.shape[1]} numbers each; a sentence is kept as {meaning.DIMS}")
        try:
            from model2vec import StaticModel
            theirs = StaticModel.from_pretrained(str(folder))
            worst = 0.0
            for text in SAME:
                mine, other = meaning._embed(text), np.asarray(theirs.encode([text])[0], dtype=np.float32)[:meaning.DIMS]
                other = other / max(float(np.linalg.norm(other)), 1e-9)
                worst = max(worst, float(np.abs(mine - other).max()) if mine is not None else 1.0)
            print(f"against the package the model was made with, on {len(SAME)} sentences: the furthest apart any number is, {worst:.6f}")
        except ImportError:
            print("(model2vec isn't here, so Luma's reader isn't checked against it)")

        def report(label):
            plain, other, never = crowd.asked(crowd.BUILT_ON)
            print(f"  {label:22} forty built-on facts: plain {plain}/40, other words {other}/40, wrongly never told {never}")
            plain, other, never = crowd.asked(crowd.SECOND)
            print(f"  {label:22} the second forty:     plain {plain}/40, other words {other}/40, wrongly never told {never}")
            for split in ("dev", "heldout"):
                totals, told = {}, [0, 0]
                for seed in memory_eval.SEEDS[split]:
                    one = memory_eval.run_one(seed, args.size, split, forget=False)
                    for kind, counts in one["by_kind"].items():
                        have = totals.setdefault(kind, [0, 0])
                        have[0] += counts["right"]
                        have[1] += counts["asked"]
                    told[0] += one["told"]["said_never"]
                    told[1] += one["told"]["asked"]
                print(f"  {label:22} memory test, {split:8}: " + ", ".join(f"{kind} {a}/{b}" for kind, (a, b) in sorted(totals.items()))
                      + f"; told but said never told {told[0]}/{told[1]}")

        meaning.available = lambda store=None: False
        print("words alone:")
        report("words alone")
        meaning.available = real_available
        for close in [float(x) for x in args.close.split(",")]:
            meaning.SMALL_CLOSE = close
            print(f"with the small model, a memory counts at {close} or closer:")
            report(f"small model @ {close}")
    finally:
        for name, value in kept.items():
            setattr(meaning, name, value)


if __name__ == "__main__":
    main()
