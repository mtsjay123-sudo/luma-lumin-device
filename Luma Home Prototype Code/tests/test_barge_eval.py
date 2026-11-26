"""The barge-in test's arithmetic (scripts/barge_eval.py), on timelines made up here. No recording exists yet, so
nothing in this file says how fast Luma goes quiet. What the code does when someone talks over it is checked at the
bottom, with a stand-in for the voice."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import barge_eval  # noqa: E402


class TheArithmetic(unittest.TestCase):
    def test_quiet_within_300_ms_is_in_time(self):
        s = barge_eval.score([{"minutes": 5, "interruptions": [{"at": 10.0, "quiet_at": 10.3}, {"at": 20.0, "quiet_at": 20.31}, {"at": 30.0, "quiet_at": 30.1}]}])
        self.assertEqual((s["in_time"], s["of"], s["never"]), (2, 3, 0))
        self.assertEqual(s["middle"], 0.3)

    def test_talking_straight_through_counts_against_it(self):
        s = barge_eval.score([{"minutes": 5, "interruptions": [{"at": 10.0, "quiet_at": None}, {"at": 20.0, "quiet_at": 19.0}, {"at": 30.0, "quiet_at": 30.2}]}])
        self.assertEqual((s["in_time"], s["of"], s["never"]), (1, 3, 2))
        self.assertIn("Talked straight through: 2", barge_eval.summary(s))

    def test_going_quiet_with_nobody_speaking_is_counted_by_talking_time(self):
        s = barge_eval.score([{"minutes": 20, "interruptions": [{"at": 1, "quiet_at": 1.1}], "false_stops": [50.0, 400.0]}])
        self.assertEqual((s["false_stops"], s["false_in_ten_minutes"]), (2, 1.0))

    def test_no_verdict_under_two_hundred(self):
        few = barge_eval.score([{"minutes": 5, "interruptions": [{"at": n, "quiet_at": n + 0.1} for n in range(199)]}])
        self.assertIsNone(few["passed"])
        self.assertIn("Too few to say", barge_eval.summary(few))
        self.assertIn("No interruptions recorded yet", barge_eval.summary(barge_eval.score([])))

    def test_the_bar_is_95_in_100(self):
        def day(late):
            return [{"minutes": 60, "interruptions": [{"at": n, "quiet_at": n + (0.5 if n < late else 0.2)} for n in range(200)]}]
        self.assertTrue(barge_eval.score(day(10))["passed"])
        self.assertFalse(barge_eval.score(day(11))["passed"])
        self.assertIn("not met", barge_eval.summary(barge_eval.score(day(11))))


if __name__ == "__main__":
    unittest.main()
