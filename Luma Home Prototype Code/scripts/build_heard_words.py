"""Make the list of words Luma has heard (src/luma/agent/heard_words.txt.gz), for telling a word that's new
(luma.agent.pickup). It's every word in Luma's own code, its packs of things people say, its slang dictionary and its
documents. No word list from anywhere else is used (rule 7), and nothing under tests/ or data/ is read, so no test's
wording decides what counts as known.

    python scripts/build_heard_words.py
"""
import gzip
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def words():
    """Each word with how many times Luma's own text has it: a slip of the fingers is a slip toward a common word."""
    from collections import Counter
    seen = Counter()
    files = [p for p in (ROOT / "src" / "luma").rglob("*.py") if "vendor" not in p.parts] + sorted((ROOT / "docs").glob("*.md")) + [ROOT / "scripts" / "finetune_data.py"]
    for path in files:
        seen.update(WORD.findall(path.read_text(errors="ignore").lower()))
    return sorted((w, n) for w, n in seen.items() if 2 <= len(w) <= 24)


if __name__ == "__main__":
    found = words()
    out = ROOT / "src" / "luma" / "agent" / "heard_words.txt.gz"
    with gzip.GzipFile(out, "wb", mtime=0) as f:
        f.write("\n".join(f"{w} {min(n, 999)}" for w, n in found).encode())
    print(len(found), "words,", out.stat().st_size, "bytes")
