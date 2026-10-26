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

    def test_slang_is_conversation_not_a_command(self):
        before = self.agent.store.setting("hush_until", 0)
        self.agent.chat("ngl i need a drink")
        self.assertEqual(self.agent.store.setting("hush_until", 0), before)


if __name__ == "__main__":
    unittest.main()
