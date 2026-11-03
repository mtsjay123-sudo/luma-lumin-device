"""Render a sample explainer video in Luma's voice: python scripts/explainer_sample.py out/

The CI voice job runs this on a real Mac (with Luma's voice installed) so the result can be watched: download
"Luma-explainer-sample" from the run. The script is written the way Luma's brain writes one for the video studio.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from luma.work import explainer  # noqa: E402

SCRIPT = """# What a blockchain is
A shared notebook :: A blockchain is a shared record that thousands of computers keep at the same time.
No one owns it :: No single company holds the master copy, so nobody can quietly change it.
# How the blocks link
Blocks in a chain :: New records are grouped into blocks, and each block carries a fingerprint of the one before it.
Change one, break all :: Change an old block and its fingerprint stops matching, so everyone can see it was tampered with.
# Why people use it
Trust without a middleman :: That's how strangers can trade with each other without a bank in the middle.
Not magic, just math :: It's slower than a normal database, so it only makes sense when nobody wants one company in charge."""

if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    result = explainer.render(explainer.parse_script(SCRIPT, "How a blockchain works"), "How a blockchain works", out, progress=print)
    print(f"{result['duration']}s, voice: {result['voice']}, chapters: {', '.join(result['chapters'])}")
    for name, path in result["videos"].items():
        print(name, path)
