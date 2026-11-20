"""Keep or today: what becomes a card in the memory deck, and what stays in the day's chat.

500 lines written by hand (tests/keep_or_today.py). The dev half is a guard: rules were built on it. The held-out
half is the honest number: nothing is tuned on it, and a failure prints numbers, never a line."""
import tempfile
import unittest
from pathlib import Path

import keep_or_today
from luma.agent.runtime import Agent
from luma.control import today
from luma.memory.store import Store


class TheSet(unittest.TestCase):
    def test_500_lines_none_said_twice_and_the_halves_share_nothing(self):
        dev, held = keep_or_today.lines("dev"), keep_or_today.lines("heldout")
        self.assertEqual((len(dev), len(held)), (250, 250))
        for half in (dev, held):
            self.assertEqual(sum(1 for _, label in half if label == "keep"), 125)
        said = [t for t, _ in dev + held]
        self.assertEqual(len(set(said)), 500)

    def test_the_halves_share_no_sentence_shape(self):
        shapes = [s for _, s in keep_or_today.SHAPES]
        self.assertEqual(len(set(shapes)), len(shapes))


class Dev(unittest.TestCase):
    """The half the rules were built on: a guard against going backwards."""

    def test_what_a_friend_would_keep_becomes_a_card(self):
        missed = [t for t, label in keep_or_today.lines("dev") if label == "keep" and not keep_or_today.cards(t)]
        self.assertEqual(missed, [])

    def test_what_belongs_to_today_never_becomes_a_card(self):
        wrong = [(t, keep_or_today.cards(t)) for t, label in keep_or_today.lines("dev") if label == "today" and keep_or_today.cards(t)]
        self.assertEqual(wrong, [])


class HeldOut(unittest.TestCase):
    """The honest number, measured on Nov 20, 2026: 77 of 125 kept, 125 of 125 left in today. Numbers only."""

    def test_no_worse_than_measured(self):
        got = keep_or_today.score("heldout")
        self.assertGreaterEqual(got["keep"][0], 77, "held-out keep: %d of %d" % got["keep"])
        self.assertEqual(got["today"][0], got["today"][1], "held-out today: %d of %d" % got["today"])


class TheDeck(unittest.TestCase):
    """What the phone and the computer show: the facts, never a passing remark, and one count."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_a_passing_remark_is_kept_for_recall_but_isnt_a_card(self):
        self.agent.chat("my sister's name is Dana")
        self.agent.chat("I had such a long day at work")
        texts = [m["text"] for m in self.store.all("memory", 50)]
        self.assertIn("I had such a long day at work", texts, "still there for 'what did I say last week'")
        mem = today.payload(self.agent)["memory"]
        shown = [m["text"] for m in mem["recent"]]
        self.assertEqual(shown, ["My sister's name is Dana"])
        self.assertEqual(mem["used"], len(shown), "the count and the deck agree")

    def test_the_overview_counts_the_same_memories(self):
        from luma.agent import insights
        for line in ("my sister's name is Dana", "I'm allergic to peanuts", "ugh, traffic was awful today"):
            self.agent.chat(line)
        self.assertEqual(insights.overview(self.agent)["counts"]["memories"], today.payload(self.agent)["memory"]["used"])


if __name__ == "__main__":
    unittest.main()
