"""Grow Luma's slang from Wiktionary: thousands more words, each tagged with where it comes from.

    .venv/bin/python scripts/build_slang.py                  # downloads Wiktionary's English data (a few GB, streamed)
    .venv/bin/python scripts/build_slang.py --source file.jsonl.gz

Reads the machine-readable Wiktionary extract published at kaikki.org, keeps the senses Wiktionary
itself labels as slang (African-American Vernacular, Multicultural London English, Internet slang,
vulgar, regional and so on), and writes them to Luma's state folder as slang_extra.tsv. Luma reads that
file on start, on top of its own lexicon (its own entries win). Nothing is sent anywhere.

Wiktionary's definitions are licensed CC BY-SA 4.0: the file says so at the top and stays on this
computer. Social media posts, comments and creators' videos are not used: they belong to the people
who wrote them, and the platforms don't allow scraping.
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SOURCE = "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl"
SLANG_LABELS = {"slang", "internet slang", "informal", "colloquial", "vulgar", "derogatory", "offensive", "ethnic slur", "slur", "euphemistic",
                "african-american vernacular", "aave", "multicultural london english", "mle", "leet", "gaming", "video games", "lgbt", "lgbtq",
                "ballroom culture", "drag", "hip-hop", "rap", "street slang", "prison slang", "teen slang", "youth slang", "gen z", "gen alpha"}
ORIGIN_OF = [("african-american", "aave"), ("aave", "aave"), ("hip-hop", "aave"), ("multicultural london", "uk"), ("mle", "uk"), ("british", "uk"),
             ("uk", "uk"), ("london", "uk"), ("jamaica", "jam"), ("caribbean", "jam"), ("australia", "aus"), ("southern us", "south"),
             ("appalachia", "south"), ("new york", "nyc"), ("philadelphia", "philly"), ("california", "socal"), ("lgbt", "ballroom"),
             ("ballroom", "ballroom"), ("drag", "ballroom"), ("internet", "internet"), ("leet", "gaming"), ("gaming", "gaming"),
             ("video games", "gaming"), ("gen alpha", "alpha"), ("gen z", "internet"), ("mexican", "latino"), ("chicano", "la"), ("spanglish", "latino")]


def labels(sense):
    out = {t.lower() for t in sense.get("tags", []) + sense.get("raw_tags", [])}
    out |= {(c.get("name") if isinstance(c, dict) else str(c)).lower() for c in sense.get("categories", [])}
    return out


def origin(tags):
    found = [o for key, o in ORIGIN_OF if any(key in t for t in tags)]
    return "+".join(dict.fromkeys(found)) or "general"


def register(tags):
    if any("slur" in t for t in tags):
        return "x"
    if any(t in tags for t in ("derogatory", "offensive", "pejorative")):
        return "s"
    return "v" if "vulgar" in tags else "c"


def open_source(where):
    if where.startswith("http"):
        raw = urllib.request.urlopen(urllib.request.Request(where, headers={"User-Agent": "LumaSlang/1.0"}), timeout=60)
    else:
        raw = open(where, "rb")
    return io.TextIOWrapper(gzip.GzipFile(fileobj=raw) if where.endswith(".gz") else raw, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=SOURCE, help="kaikki.org English JSONL (URL or file, .gz is fine)")
    parser.add_argument("--out", help="where to write (default: Luma's state folder)")
    args = parser.parse_args()
    from luma.config import STATE_DIR
    out = Path(args.out) if args.out else STATE_DIR / "slang_extra.tsv"
    seen, rows = set(), []
    with open_source(args.source) as lines:
        for n, line in enumerate(lines, 1):
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            word = str(entry.get("word") or "").strip()
            if entry.get("lang_code") not in (None, "en") or not word or len(word) > 40 or "|" in word:
                continue
            for sense in entry.get("senses", []):
                tags = labels(sense)
                if not tags & SLANG_LABELS and not any("slang" in t for t in tags):
                    continue
                gloss = " ".join((sense.get("glosses") or [""])[0].split())[:140].replace("|", "/")
                key = (word.lower(), gloss.lower()[:40])
                if not gloss or key in seen:
                    continue
                seen.add(key)
                forms = ", ".join(sorted({f.get("form", "") for f in entry.get("forms", []) if f.get("form") and f["form"] != word and "|" not in f["form"]})[:6])
                rows.append(f"{word} | {forms} | {origin(tags)} | {register(tags)} | {gloss} | {word}")
                break  # the first slang sense of each word is enough for Luma
            if n % 200000 == 0:
                print(f"  read {n:,} entries, kept {len(rows):,} slang words")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Definitions from Wiktionary (https://en.wiktionary.org), CC BY-SA 4.0, via kaikki.org. Kept on this computer.\n"
                   + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows):,} slang words to {out}. Restart Luma to use them.")


if __name__ == "__main__":
    main()
