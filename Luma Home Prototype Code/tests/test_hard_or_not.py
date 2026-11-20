"""Hard or not (tests/hard_or_not.py): does Luma read a bad day as one, and leave an ordinary one alone?

The dev half is a guard (the reader was strengthened on it, Nov 20). The held-out half is the honest number: nothing is
tuned on it, and a failure prints numbers, never a line."""
import unittest

import hard_or_not


class TheSet(unittest.TestCase):
    def test_600_lines_none_twice_and_the_halves_share_nothing(self):
        dev, held = hard_or_not.lines("dev"), hard_or_not.lines("heldout")
        self.assertEqual((len(dev), len(held)), (300, 300))
        said = [t for t, _ in dev + held]
        self.assertEqual(len(set(said)), 600)
        for half in (dev, held):
            self.assertEqual(sum(1 for _, label in half if label == "hard"), 150)


class Dev(unittest.TestCase):
    def test_a_hard_moment_is_read_as_one(self):
        self.assertEqual([t for t, label in hard_or_not.lines("dev") if label == "hard" and not hard_or_not.read_as_hard(t)], [])

    def test_an_ordinary_or_a_good_day_is_left_alone(self):
        self.assertEqual([t for t, label in hard_or_not.lines("dev") if label == "not" and hard_or_not.read_as_hard(t)], [])


class HeldOut(unittest.TestCase):
    """Measured Nov 20, 2026: 100 of 150 hard moments read as hard, 150 of 150 ordinary lines left alone."""

    def test_no_worse_than_measured(self):
        got = hard_or_not.score("heldout")
        self.assertGreaterEqual(got["hard"][0], 100, "held-out hard: %d of %d" % got["hard"])
        self.assertEqual(got["not"][0], got["not"][1], "held-out not: %d of %d" % got["not"])


if __name__ == "__main__":
    unittest.main()
