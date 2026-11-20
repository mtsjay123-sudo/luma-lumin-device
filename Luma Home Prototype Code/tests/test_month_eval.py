"""The month test (scripts/month_eval.py): a made-up person lives 28 days with one Luma, and the same moments are then
said to a Luma that never met them. Here: a few dev lives, with a stand-in brain, reading what a brain is told."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import month_eval  # noqa: E402


class Lives(unittest.TestCase):
    def test_the_same_seed_is_the_same_person(self):
        a, b = month_eval.Life(3), month_eval.Life(3)
        self.assertEqual([(d, [t.get("say") for t in turns]) for d, _, turns in a.days()], [(d, [t.get("say") for t in turns]) for d, _, turns in b.days()])

    def test_dev_and_held_out_share_no_seed_and_no_line(self):
        self.assertFalse(set(month_eval.SEEDS["dev"]) & set(month_eval.SEEDS["heldout"]))
        said = lambda split: {t["say"] for seed in month_eval.SEEDS[split][:6] for _, _, turns in month_eval.Life(seed, split).days() for t in turns}  # noqa: E731
        self.assertFalse(said("dev") & said("heldout"))

    def test_every_way_to_be_met_is_lived(self):
        self.assertEqual({month_eval.Life(seed).style for seed in month_eval.SEEDS["dev"]}, set(month_eval.STYLES))


class AMonth(unittest.TestCase):
    """A guard on the half the code was built on. The held-out half is run by hand, numbers only."""

    @classmethod
    def setUpClass(cls):
        cls.result = month_eval.run("dev", lives=4, progress=lambda line: None)
        cls.table = month_eval.tally(cls.result)

    def test_a_month_in_luma_knows_what_a_stranger_cannot(self):
        for kind in ("comfort", "recall", "update", "people"):
            passed, of = self.table[kind]["month"]
            self.assertEqual(passed, of, kind)
            self.assertEqual(self.table[kind]["fresh"][0], 0, kind + ": a Luma that never met them can't know")

    def test_it_asks_how_it_went_and_leaves_a_closed_subject_alone(self):
        for kind in ("callback", "closed", "never"):
            passed, of = self.table[kind]["month"]
            self.assertEqual(passed, of, kind)

    def test_held_out_results_are_saved_without_a_line_of_what_was_said(self):
        summary = month_eval.summary({**self.result, "split": "heldout"})
        self.assertNotIn("Missed", summary)


if __name__ == "__main__":
    unittest.main()
