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


class AQuestionIsNeverAnOrderToSave(unittest.TestCase):
    """Month test on real brains, run 50: "where does my mom live" was answered "Saved. I'll remember that about the house."
    on every life by the 4B brain: the word "where" offered it the tool that saves a house note, and it took it."""

    @classmethod
    def setUpClass(cls):
        import human_eval
        cls.offered = []

        def planner(messages, context, allowed, *args, **kwargs):
            cls.offered.append(sorted(allowed or {}))
            return {"type": "reply", "text": "Okay."}

        cls.s = human_eval.Session(planner)

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def test_a_plain_question_is_offered_nothing_that_saves(self):
        saves = {"household.save", "memory.remember", "contacts.save"}
        for said in ("where does my mom live", "where does my brother live now", "where did I put the warranty for the dishwasher",
                     "do you remember where the spare key is", "what's the wifi password again?", "who's my landlord"):
            self.assertFalse(saves & set(self.s.agent.available_tools(said)), said)

    def test_asking_luma_to_keep_something_still_can(self):
        tools = self.s.agent.available_tools
        self.assertIn("household.save", tools("save that the water filter is under the sink"))
        self.assertIn("household.save", tools("the manual for the dryer is in the hall closet, save that"))
        self.assertIn("memory.remember", tools("remember that the wifi password is on the fridge"))
        self.assertIn("memory.remember", tools("can you remember my mom's birthday is June 3?"))

    def test_when_a_fact_states_it_luma_says_the_fact_and_no_tool_is_offered(self):
        """With or without a question mark (a voice has none). The same run: the small brain said "I don't know where your
        brother is right now" with the fact in front of it."""
        say = lambda text: (lambda out: out[0] if isinstance(out, tuple) else out.get("text"))(self.s.say(text))  # noqa: E731
        self.s.say("my mom lives in Tucson")
        self.s.say("my brother lives in Austin")
        self.s.say("my brother moved to Denver last week")
        del self.offered[:]
        self.assertIn("Tucson", say("where does my mom live"))
        self.assertIn("Tucson", say("where does my mom live?"))
        self.assertIn("Denver", say("where does my brother live now"))
        self.assertEqual([tools for tools in self.offered if tools], [])

    def test_what_no_fact_states_is_still_the_brains(self):
        say = lambda text: (lambda out: out[0] if isinstance(out, tuple) else out.get("text"))(self.s.say(text))  # noqa: E731
        for asked in ("where does my cousin live", "where does my mom want to go for dinner", "what does my boss want from me", "where is my life going"):
            self.assertEqual(say(asked), "Okay.", asked)
