"""Sarcasm read as sarcasm, and good news left as good news (tests/dry_or_not.py). The held-out half prints numbers only."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

import dry_or_not  # noqa: E402


class TheSet(unittest.TestCase):
    def test_the_halves_share_no_line_and_have_every_kind(self):
        dev, held = dry_or_not.lines("dev"), dry_or_not.lines("heldout")
        self.assertFalse({t for t, _ in dev} & {t for t, _ in held})
        for rows in (dev, held):
            self.assertEqual({lab: sum(1 for _, x in rows if x == lab) for lab in ("dry", "glad", "plain")}, dry_or_not.COUNT)


class Dev(unittest.TestCase):
    """What the rules were built on: a guard. (Before: 82 of 150 gripes read as gripes.)"""

    def test_every_gripe_said_with_good_words_is_read_as_one(self):
        self.assertEqual([t for t, lab in dry_or_not.lines("dev") if lab == "dry" and not dry_or_not.read_dry(t)], [])

    def test_good_news_and_a_plain_gripe_are_never_called_sarcasm(self):
        self.assertEqual([t for t, lab in dry_or_not.lines("dev") if lab != "dry" and dry_or_not.read_dry(t)], [])

    def test_a_gripe_is_never_read_as_good_news(self):
        self.assertEqual([t for t, lab in dry_or_not.lines("dev") if lab == "dry" and dry_or_not.read_good(t) and not dry_or_not.read_dry(t)], [])


class HeldOut(unittest.TestCase):
    """Measured Nov 20, 2026, after the dev half's rules were in (before: 114 of 150). Numbers only."""

    def test_no_worse_than_measured(self):
        s = dry_or_not.score("heldout")
        self.assertGreaterEqual(s["dry"][0], 145, f"gripes read as gripes: {s['dry'][0]} of {s['dry'][1]}")
        self.assertEqual(s["glad"][0], s["glad"][1], f"good news called sarcasm: {s['glad'][1] - s['glad'][0]}")
        self.assertEqual(s["plain"][0], s["plain"][1], f"a plain gripe called sarcasm: {s['plain'][1] - s['plain'][0]}")
        self.assertEqual(s["dry_cheered"], 0, "a gripe read as good news")


if __name__ == "__main__":
    unittest.main()
