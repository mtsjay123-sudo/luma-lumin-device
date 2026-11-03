"""Numbers come from what Luma read: a price, score, temperature or date in an answer built on a look-up has to be in
what was found (or what the owner said, or simple math on those). A made-up one gets one more try, then its sentence
comes out. Rounding the way people round is fine; single digits are how people talk and are left alone."""
import tempfile
import threading
import unittest
from pathlib import Path

from luma.agent import grounding
from luma.agent.runtime import Agent
from luma.memory.store import Store

FOUND = {"results": [{"title": "Nike Air Max 90 - $129.99 at Foot Locker", "snippet": "Was $150. Save 13%. Rated 4.6 by 2,031 people."},
                     {"title": "Brewers beat Cubs 5-3", "snippet": "First pitch 7:10 pm in front of 41,032."}],
         "summary": "Highs of 72°F today, low of 57 tonight. Population 1,284,000."}


class FiguresTests(unittest.TestCase):
    def check(self, reply):
        return grounding.unbacked(reply, FOUND, result=FOUND, extra=(2025, 2026, 2027))

    def test_what_was_found_passes_however_its_said(self):
        for reply in ["They're $129.99 at Foot Locker, down from $150.", "About $130, 13% off.", "Brewers won 5-3.", "Cubs lost 3-5.",
                      "First pitch was 7:10pm.", "72 today, 15 degrees warmer than tonight.", "That saves you $20.", "About 1.3 million people.",
                      "Rated 4.6 stars.", "Around 41,000 fans showed up.", "This season, 2026, has been wild."]:
            self.assertEqual(self.check(reply), [], reply)

    def test_made_up_numbers_are_caught(self):
        for reply, wrong in [("They're $119 right now.", "$119"), ("Brewers won 6-3.", "6-3"), ("It hits 75 today.", "75"),
                             ("Rated 4.5 stars.", "4.5"), ("The 2019 model is the one.", "2019"), ("Saves you 21 bucks.", "21"),
                             ("Kickoff is at 8:15 pm.", "8:15 pm"), ("Sales are up 40%.", "40%")]:
            self.assertEqual(self.check(reply), [wrong], reply)

    def test_everyday_small_numbers_are_just_talk(self):
        self.assertEqual(self.check("Got 2 options for you. Option 1 is the cheaper one."), [])

    def test_what_the_owner_said_counts(self):
        self.assertEqual(grounding.unbacked("Yep, your $45 budget covers it.", FOUND, said="find shoes under $45"), [])

    def test_a_count_of_what_was_found_counts(self):
        inbox = {"messages": [{"from": f"person {i}"} for i in range(12)]}
        self.assertEqual(grounding.unbacked("You've got 12 new emails.", inbox, result=inbox), [])

    def test_the_sentence_with_a_made_up_number_comes_out(self):
        self.assertEqual(grounding.without("They're $119 right now. Foot Locker has them. Want me to grab a pair?", ["$119"]),
                         "Foot Locker has them. Want me to grab a pair?")


class AnswersFromLookupsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)
        self.prompts = []

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def brain(self, *replies):
        replies = list(replies)
        def planner(messages, memories, tools, cancel):
            self.prompts.append(messages[-1]["content"])
            return {"type": "reply", "text": replies.pop(0) if replies else ""}
        self.agent.call_planner = planner

    def test_a_right_answer_goes_straight_out(self):
        self.brain("They're $129.99 at Foot Locker, down from $150.")
        said = self.agent._answer_from("how much are air max 90s", "web.search", FOUND, threading.Event())
        self.assertEqual(said, "They're $129.99 at Foot Locker, down from $150.")
        self.assertEqual(len(self.prompts), 1)

    def test_a_made_up_price_gets_one_more_try_naming_it(self):
        self.brain("They're $119 at Foot Locker.", "They're $129.99 at Foot Locker.")
        said = self.agent._answer_from("how much are air max 90s", "web.search", FOUND, threading.Event())
        self.assertEqual(said, "They're $129.99 at Foot Locker.")
        self.assertIn("“$119”", self.prompts[1])
        self.assertIn("isn't in what was found", self.prompts[1])

    def test_still_made_up_means_that_sentence_comes_out(self):
        self.brain("Brewers won 7-2. Great game.", "Brewers won 7-2, what a game. It was close.")
        said = self.agent._answer_from("did the brewers win", "web.search", FOUND, threading.Event())
        self.assertEqual(said, "It was close.")

    def test_nothing_left_says_so_instead_of_guessing(self):
        self.brain("It's 81 degrees.", "Looks like 79.")
        said = self.agent._answer_from("how hot is it", "web.search", FOUND, threading.Event())
        self.assertIn("couldn't pin down that exact number", said)


if __name__ == "__main__":
    unittest.main()
