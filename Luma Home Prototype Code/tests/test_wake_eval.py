"""The wake test's arithmetic (scripts/wake_eval.py), on timelines made up here. No recording exists yet, so nothing in
this file says anything about how well Luma hears its name."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import wake_eval  # noqa: E402


class TheArithmetic(unittest.TestCase):
    def test_a_wake_just_after_the_phrase_is_hearing_it_and_any_other_is_false(self):
        s = wake_eval.score([{"hours": 1, "said": [{"at": 10, "distance": 3}, {"at": 60, "distance": 3}, {"at": 90, "distance": 5}],
                              "woke": [10.8, 400.0]}])
        self.assertEqual(s["heard"], {"3": [1, 2], "5": [0, 1]})
        self.assertEqual(s["false"], 1)
        self.assertEqual(s["false_in_24h"], 24.0)

    def test_one_wake_answers_one_phrase(self):
        s = wake_eval.score([{"hours": 1, "said": [{"at": 10, "distance": 1}, {"at": 11, "distance": 1}], "woke": [11.5]}])
        self.assertEqual(s["heard"], {"1": [1, 2]})
        self.assertEqual(s["false"], 0)

    def test_a_wake_before_the_phrase_or_long_after_it_is_false(self):
        s = wake_eval.score([{"hours": 2, "said": [{"at": 10, "distance": 3}], "woke": [9.5, 13.1]}])
        self.assertEqual(s["heard"], {"3": [0, 1]})
        self.assertEqual(s["false"], 2)

    def test_look_alikes_said_on_purpose_are_counted_apart(self):
        s = wake_eval.score([{"hours": 1, "said": [], "near": [{"at": 5, "phrase": "Hey Lumen"}, {"at": 50, "phrase": "hey lumen"}], "woke": [5.4]}])
        self.assertEqual(s["near"], {"hey lumen": [1, 2]})
        self.assertEqual(s["false"], 0)
        self.assertIn("| hey lumen | 1 of 2 |", wake_eval.summary(s))

    def test_what_else_was_going_on_is_kept_apart(self):
        s = wake_eval.score([{"hours": 1, "said": [{"at": 1, "distance": 3, "room": "tv on"}, {"at": 9, "distance": 3}], "woke": [9.2]}])
        self.assertEqual(s["rooms"], {"tv on": [0, 1], "quiet": [1, 1]})


class TheVerdict(unittest.TestCase):
    def day(self, heard, false):
        said = [{"at": 10 * n, "distance": 3} for n in range(300)]
        return {"hours": 24, "said": said, "woke": [10 * n + 0.5 for n in range(heard)] + [50_000 + n for n in range(false)]}

    def test_with_too_little_recorded_there_is_no_verdict(self):
        s = wake_eval.score([{"hours": 2, "said": [{"at": 10 * n, "distance": 3} for n in range(300)], "woke": [10 * n + 0.5 for n in range(300)]}])
        self.assertIsNone(s["passed"])
        self.assertIn("Too little to say", wake_eval.summary(s))
        few = wake_eval.score([{"hours": 24, "said": [{"at": 10, "distance": 3}], "woke": [10.5]}])
        self.assertIsNone(few["passed"])

    def test_the_bar_is_95_in_100_at_three_metres_and_one_false_wake_a_day(self):
        self.assertTrue(wake_eval.score([self.day(285, 1)])["passed"])
        self.assertFalse(wake_eval.score([self.day(284, 0)])["passed"])
        self.assertFalse(wake_eval.score([self.day(300, 2)])["passed"])
        self.assertIn("not met", wake_eval.summary(wake_eval.score([self.day(300, 2)])))

    def test_recordings_add_up(self):
        half = {"hours": 12, "said": [{"at": 10 * n, "distance": 3} for n in range(150)], "woke": [10 * n + 0.5 for n in range(150)]}
        s = wake_eval.score([half, half])
        self.assertEqual((s["hours"], s["heard"]["3"]), (24.0, [300, 300]))
        self.assertTrue(s["passed"])

    def test_nothing_recorded_says_so(self):
        s = wake_eval.score([])
        self.assertIsNone(s["false_in_24h"])
        self.assertIn("no recording to count them over", wake_eval.summary(s))


if __name__ == "__main__":
    unittest.main()
