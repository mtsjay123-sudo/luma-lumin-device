"""Write labeled phrases from Luma's phrase bank, for training the understanding model or checking a community's voice.

    python scripts/phrase_bank.py                      # how many phrases, per community
    python scripts/phrase_bank.py --sample 5 --community kitchen
    python scripts/phrase_bank.py --out phrases.jsonl --n 200000 --seed 1

Each line of the JSONL file is one phrase: {"text", "community", "intent", "terms": [{"said", "meaning", "communities"}]}.
Every term and meaning comes from Luma's lexicon, so the labels are true by construction.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from luma.agent import phrasebank  # noqa: E402


def as_row(ph):
    return {"text": ph["text"], "community": ph["community"], "intent": ph["intent"],
            "terms": [{"said": s, "meaning": m, "communities": list(o)} for s, m, o in ph["terms"]]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="write phrases to this JSONL file")
    ap.add_argument("--n", type=int, default=100_000, help="how many phrases to write (default 100,000)")
    ap.add_argument("--sample", type=int, help="print this many phrases")
    ap.add_argument("--community", help="only this community")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    if args.sample:
        for ph in phrasebank.sample(args.sample, args.seed, args.community):
            terms = "; ".join(f"{s} = {m}" for s, m, _ in ph["terms"])
            print(f"[{ph['community']}/{ph['intent']}] {ph['text']}\n    {terms}")
        return 0
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            for ph in phrasebank.sample(args.n, args.seed, args.community):
                f.write(json.dumps(as_row(ph), ensure_ascii=False) + "\n")
        print(f"Wrote {args.n:,} phrases to {args.out}")
        return 0
    sizes = phrasebank.by_community()
    print(f"{phrasebank.count():,} phrases across {len(sizes)} communities")
    for community, n in sorted(sizes.items(), key=lambda kv: -kv[1]):
        print(f"  {community:<10} {n:>10,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
