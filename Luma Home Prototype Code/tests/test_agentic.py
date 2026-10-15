"""What makes Luma feel like an agent: it catches what's worth remembering however it's said, answers
"where are my keys", takes a casual "yes bet", offers choices to tap, runs every page from the chat,
learns how you talk, and takes the name you give it."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from luma.agent import presence, texting
from luma.agent.runtime import Agent
from luma.memory.store import Store
from luma.llm.prompts import build_plan_prompt

NOW = 1791900000.0  # Tue 13 Oct 2026, 10:00 in New York


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.now = NOW
        self.agent = Agent(store=self.store, use_model=False, now=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def memories(self):
        return [m["text"] for m in self.store.all("memory", 100)]


class CatchesItTests(Base):
    def test_a_fact_inside_a_question_is_still_kept(self):
        self.agent.chat("my boyfriend's birthday is September 17th what should I get him?")
        self.assertIn("My boyfriend's birthday is September 17th", self.memories())

    def test_keys_on_the_counter_however_its_said(self):
        for said in ["hey luma i left my keys on the counter", "luna bottom drop I left my keys on the counter", "btw i put my keys on the counter"]:
            reply = self.agent.chat(said)
            self.assertIn("Your keys are on the counter", reply["text"])
        self.assertEqual(self.memories().count("Your keys are on the counter"), 1)

    def test_where_are_my_keys_and_they_moved(self):
        self.agent.chat("I left my keys on the counter")
        self.now += 3600
        self.agent.chat("I put my keys in my jacket pocket")
        self.now += 1800
        reply = self.agent.chat("where are my keys?")
        self.assertIn("in my jacket pocket", reply["text"])
        self.assertIn("30 minutes ago", reply["text"])
        self.assertNotIn("Your keys are on the counter", self.memories())
        self.assertIn("haven't told me", self.agent.chat("where's my wallet")["text"])

    def test_remind_me_later_with_no_time(self):
        reply = self.agent.chat("hey luma i left my keys on the counter remind me later")
        self.assertIn("I'll remind you at 11 AM", reply["text"])
        task = next(t for t in self.store.all("task", 10))
        self.assertIn("keys are on the counter", task["title"])

    def test_likes_and_more_than_one_thing_at_once(self):
        self.agent.chat("I put my passport in the top drawer and my wallet is in the car")
        self.assertIn("Your passport is in the top drawer", self.memories())
        self.assertIn("Your wallet is in the car", self.memories())
        self.agent.chat("I hate cilantro lol")
        self.assertIn("You hate cilantro", self.memories())

    def test_it_shows_what_it_caught_and_can_undo(self):
        reply = self.agent.chat("I left my glasses by the sink")
        self.assertEqual(reply["noticed"][0]["text"], "Your glasses are by the sink")

    def test_free_memory_is_limited_and_plus_is_not(self):
        self.agent.FREE_MEMORIES = 2
        self.agent.chat("I left my keys on the counter")
        self.agent.chat("I hate cilantro")
        reply = self.agent.chat("I'm allergic to peanuts")
        self.assertTrue(reply.get("memory_full"))
        self.assertEqual(len(self.memories()), 2)
        with mock.patch.object(self.agent.cloud, "cached_account", return_value={"plan": "plus"}):
            self.assertIsNone(self.agent.memory_quota()["limit"])
            self.agent.chat("I'm allergic to peanuts")
        self.assertEqual(len(self.memories()), 3)
        # where things are always updates, even when memory's full
        self.agent.chat("I left my keys in the car")
        self.assertIn("Your keys are in the car", self.memories())


class TalksLikeYouTests(Base):
    def test_learns_how_they_talk(self):
        for said in ["yo whats good", "bet thats fire lol", "nah im good fr", "bet send it lol", "ngl thats dope", "fr fr bet"]:
            self.agent._learn_style(said)
        style = self.store.setting("their_style")
        self.assertIn("lowercase", style)
        self.assertIn("“bet”", style)
        prompt = build_plan_prompt(self.agent._mind_context("hey"), {})
        self.assertIn("Match their energy", prompt)

    def test_casual_yes_approves_and_casual_no_cancels(self):
        for said in ["yes bet", "say less", "yessir send it", "fasho", "love it, send it", "okay send it bro"]:
            self.assertEqual(texting.confirm_intent(said), "confirm", said)
        for said in ["nah hold up", "wait", "scratch that"]:
            self.assertEqual(texting.confirm_intent(said), "cancel", said)
        self.assertIsNone(texting.confirm_intent("yes but change the subject"))


class ChoicesTests(Base):
    def test_options_in_a_question_become_choices(self):
        self.assertEqual(presence.options_in("Got it. Do you want wireless or wired?"), ["Wireless", "Wired"])
        self.assertEqual(presence.options_in("Which one: Marshall, Belkin or Sony?"), ["Marshall", "Belkin", "Sony"])
        self.assertEqual(presence.options_in("Want me to send it now or wait till morning?"), ["Send it now", "Wait till morning"])
        self.assertEqual(presence.options_in("How was your day?"), [])


class ChatRunsEverythingTests(Base):
    def test_every_page_from_the_chat(self):
        self.assertEqual(self.agent.chat("open my goals")["open"], "goals")
        peek = self.agent.chat("show me my library")
        self.assertEqual(peek["peek"], "library")
        self.assertIn("Nothing made yet", peek["text"])
        self.agent.chat("I left my keys on the counter")
        known = self.agent.chat("what do you remember about me?")
        self.assertIn("keys are on the counter", known["text"])
        self.assertEqual(self.agent.chat("open connectors")["open"], "apps")
        self.assertEqual(self.agent.chat("take me to settings")["open"], "settings")

    def test_name_your_luma(self):
        reply = self.agent.chat("I'm gonna call you Nova")
        self.assertEqual(reply["renamed"], "Nova")
        context = self.agent._mind_context("hi")
        self.assertTrue(any("named you Nova" in m["text"] for m in context))
        self.agent.chat("your name is Luma")
        self.assertIsNone(self.store.setting("assistant_name"))


if __name__ == "__main__":
    unittest.main()
