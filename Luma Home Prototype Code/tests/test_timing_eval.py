"""The timing test's own arithmetic (scripts/timing_eval.py), on timelines written by hand. It says nothing about
Luma until there are real conversations to score."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import timing_eval  # noqa: E402

R = {"pause": 0.3, "plain": 0.9, "hold": 1.6}


class Decided(unittest.TestCase):
    def test_it_uses_lumas_own_numbers(self):
        self.assertEqual(timing_eval.rules(), R)

    def test_a_clean_ending_is_decided_one_pause_after_they_stop(self):
        at, cut = timing_eval.decided({"speech": [[0.0, 2.0]]}, r=R)
        self.assertEqual((round(at, 2), cut), (2.3, False))

    def test_a_short_breath_is_never_asked_about(self):
        at, cut = timing_eval.decided({"speech": [[0.0, 1.0], [1.2, 2.0]]}, r=R)
        self.assertEqual((round(at, 2), cut), (2.3, False))

    def test_a_mid_thought_pause_the_model_gets_right_is_waited_through(self):
        at, cut = timing_eval.decided({"speech": [[0.0, 1.0], [1.8, 3.0]], "done": [False, True]}, r=R)
        self.assertEqual((round(at, 2), cut), (3.3, False))

    def test_a_mid_thought_pause_the_model_gets_wrong_is_a_cut_in(self):
        at, cut = timing_eval.decided({"speech": [[0.0, 1.0], [1.8, 3.0]], "done": [True, True]}, r=R)
        self.assertEqual((round(at, 2), cut), (1.3, True))

    def test_a_very_long_pause_runs_out_the_hold_and_is_a_cut_in(self):
        at, cut = timing_eval.decided({"speech": [[0.0, 1.0], [3.5, 5.0]], "done": [False, True]}, r=R)
        self.assertEqual((round(at, 2), cut), (2.9, True))

    def test_with_no_model_every_long_pause_ends_the_turn(self):
        self.assertEqual(timing_eval.decided({"speech": [[0.0, 1.0], [2.0, 3.0]]}, plain=True, r=R), (1.9, True))
        at, cut = timing_eval.decided({"speech": [[0.0, 1.0], [1.5, 3.0]]}, plain=True, r=R)
        self.assertEqual((round(at, 2), cut), (3.9, False))


class Scored(unittest.TestCase):
    def timeline(self):
        turns = []
        for i in range(20):
            start = i * 10.0
            turns.append({"speech": [[start, start + 2.0]], "reply_at": start + 2.0 + 0.2 + 0.05 * i})  # people answer 0.2 to 1.15 s later
        turns[3] = {"speech": [[30.0, 31.0], [31.8, 32.0]], "done": [True, True], "reply_at": 32.4}   # the model jumps in at a mid-thought pause
        return {"turns": turns}

    def test_cut_ins_the_wait_and_the_window(self):
        got = timing_eval.score([self.timeline()], latency=0.5)
        self.assertEqual((got["turns"], got["cut_ins"]), (20, 1))
        self.assertEqual(got["wait_median"], 0.3)
        low, high = got["window"]
        self.assertTrue(0.2 <= low <= 0.4 and 1.0 <= high <= 1.15, got["window"])
        self.assertEqual(got["in_window"], 19, "0.3 s to decide and 0.5 s to speak is 0.8 s: inside; the cut-in never counts")

    def test_a_slow_voice_falls_out_of_the_window(self):
        self.assertEqual(timing_eval.score([self.timeline()], latency=2.0)["in_window"], 0)

    def test_too_few_turns_gives_no_window(self):
        got = timing_eval.score([{"turns": [{"speech": [[0, 1]], "reply_at": 1.3}]}])
        self.assertIsNone(got["window"])
        self.assertIn("too few", timing_eval.summary(got))

    def test_nothing_recorded_says_so(self):
        self.assertIn("Record some conversations first", timing_eval.summary(timing_eval.score([])))


if __name__ == "__main__":
    unittest.main()
