"""Requests wrapped in slang still get done right: the slang isn't part of the reminder, the text goes to the
right person without a "that", the reason can come before "remind me", and a new request after Luma asks a
follow-up question isn't stuffed into the old one."""
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store


class SlangTalkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.agent = Agent(store=self.store, use_model=False)
        self.agent.contacts.save({"name": "Mom", "phone": "+19195550111", "aliases": "my mom, mom"})
        self.agent.contacts.save({"name": "Jordan", "phone": "+19195550122", "aliases": ""})

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def titles(self):
        return [t["title"] for t in self.agent._run("tasks.list", {})["tasks"]]

    def test_slang_tags_stay_out_of_reminders(self):
        reply = self.agent.chat("can u remind me abt the dentist tmrw no cap")["text"]
        self.assertNotIn("cap", reply)
        self.agent.chat("remind me to call grandma tmrw fr")
        self.assertEqual(sorted(self.titles()), ["Call grandma", "The dentist"])

    def test_the_reason_can_come_first(self):
        self.assertIn("go to the gym at 6", self.agent.chat("finna go to the gym remind me at 6")["text"])
        self.assertIn("Go to the gym", self.titles())

    def test_a_text_without_that(self):
        reply = self.agent.chat("yo text my mom im pullin up in 5")
        self.assertIn("Mom", reply["text"])
        self.assertIn("pullin up in 5", reply["text"])
        self.assertIn("what should it say", self.agent.chat("text jordan back later")["text"].lower())  # not a message to send
        self.assertIn("sister", self.agent.chat("text my sister happy bday")["text"])  # someone new: Luma asks for the number

    def test_a_new_request_after_a_question_starts_fresh(self):
        self.assertIn("What should I remind you about", self.agent.chat("remind me at 6")["text"])
        reply = self.agent.chat("play some drake fr")["text"]
        self.assertIn("Playing drake on", reply)
        self.assertEqual(self.titles(), [])
        self.agent.chat("remind me at 6")
        self.assertIn("call mom at 6", self.agent.chat("call mom")["text"])  # an answer is still an answer

    def test_questions_about_what_they_told_luma(self):
        self.assertEqual(self.agent.chat("my mom's birthday is June 3")["text"], "Got it. Your mom's birthday is June 3.")
        self.assertEqual(self.agent.chat("when is my moms bday?")["text"], "Your mom's birthday is June 3.")
        self.assertIn("don't know your dads birthday yet", self.agent.chat("whats my dads birthday")["text"])  # never Mom's by mistake
        self.assertNotIn("don't know", self.agent.chat("what's my schedule today")["text"])  # a lookup, not a memory

    def test_jokes_are_told_as_written_and_not_repeated(self):
        from luma.agent import jokes
        first = self.agent.chat("tell me a joke")["text"]
        self.assertIn(first, jokes.JOKES)
        second = self.agent.chat("another one")["text"]
        self.assertIn(second, jokes.JOKES)
        self.assertNotEqual(first, second)
        told = {self.agent.chat("tell me a joke")["text"] for _ in range(len(jokes.JOKES) - 2)}
        self.assertEqual(len(told | {first, second}), len(jokes.JOKES))  # every joke once before any repeats
        self.assertFalse(jokes.asked("another one", 0, 100))  # "another one" alone isn't a joke request

    def test_a_plain_hello_gets_a_plain_hello_back(self):
        self.agent.use_model = True  # even with the brain on: it's instant and in their register
        reply = self.agent.chat("yo what's good luma")["text"]
        self.assertTrue(reply.startswith(("Yo", "Ayy", "What's good")), reply)
        self.assertRegex(self.agent.chat("hey luma")["text"], r"^(?:Up late|Morning|Hey|Evening)")

    def test_luma_never_claims_it_heard_or_watched_something(self):
        self.agent.planner = lambda *a: {"type": "reply", "text": "Nah 😭 what lost you, the beats or the hooks?"}
        self.assertEqual(self.agent._without_senses("Nah, I heard the first track was solid. Which part lost you?", "ngl that album kinda mid"),
                         "Nah 😭 what lost you, the beats or the hooks?")
        from luma.agent.runtime import SENSED
        for claim in ["I was actually listening to it while making coffee", "had it on repeat all day", "I've been to Tokyo"]:
            self.assertTrue(SENSED.search(claim), claim)
        for fine in ["I hear you, that sucks", "I see what you mean", "I'm listening to you", "I'm watching out for you", "sounds like the bridge lost you"]:
            self.assertFalse(SENSED.search(fine), fine)
        self.agent.planner = lambda *a: {"type": "reply", "text": "I watched it twice, it's great."}  # a rewrite that still claims it
        self.assertEqual(self.agent._without_senses("I watched it twice. The ending is wild though!", "seen dune?"), "The ending is wild though!")

    def test_have_you_seen_it_gets_an_honest_answer(self):
        self.assertIn("Can't watch", self.agent.chat("you seen the new spiderman movie?")["text"])
        self.assertRegex(self.agent.chat("have you heard the new sza album")["text"], r"listen|hear")
        self.assertRegex(self.agent.chat("yo u tried the new popeyes sandwich")["text"], r"taste|eat")
        self.assertNotIn("watch", self.agent.chat("you seen my keys?")["text"].lower())  # that's a where-is question

    def test_slang_is_conversation_not_a_command(self):
        before = self.agent.store.setting("hush_until", 0)
        self.agent.chat("ngl i need a drink")
        self.assertEqual(self.agent.store.setting("hush_until", 0), before)


if __name__ == "__main__":
    unittest.main()
