"""Luma notices, checks back and remembers when asked, and forgets when told."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from luma.agent import presence
from luma.agent.runtime import Agent
from luma.memory.store import Store

NY = ZoneInfo("America/New_York")


def at(*args):
    return datetime(*args, tzinfo=NY).timestamp()


class PresenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "state.db", root / "state.key")
        self.now = at(2026, 10, 3, 21, 0)  # Saturday evening
        self.agent = Agent(store=self.store, use_model=False, now=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def memories(self):
        return [m["text"] for m in self.store.all("memory")]

    def test_facts_said_in_passing_are_kept_and_can_be_undone(self):
        result = self.agent.chat("ugh, Maya's birthday is October 18 and I have no idea what to get her")
        self.assertEqual([n["text"] for n in result["noticed"]], ["Maya's birthday is October 18"])
        self.assertIn("Maya's birthday is October 18", self.memories())
        self.agent.chat("ugh, Maya's birthday is October 18 and I still don't know")
        self.assertEqual(len(self.memories()), 1, "no duplicates")
        self.agent.chat("I'm allergic to shellfish by the way")
        self.assertEqual(self.agent.chat("forget that")["text"], "Forgotten.")
        self.assertNotIn("I'm allergic to shellfish", self.memories())
        self.assertIn("Maya's birthday is October 18", self.memories())

    def test_questions_and_commands_are_not_mistaken_for_facts(self):
        for text in ["what's my favorite food?", "remind me that I'm vegan", "text Maya that my mom's birthday is March 3"]:
            self.assertEqual(presence.notice_facts(text), [], text)

    def test_learning_can_be_switched_off(self):
        self.agent.set_presence("learn_from_chat", False)
        self.agent.chat("my girlfriend is named Maya")
        self.assertEqual(self.memories(), [])

    def test_luma_checks_back_after_something_you_mentioned(self):
        self.agent.chat("I have a job interview tomorrow and I'm kind of nervous")
        self.assertIsNone(self.agent.tick(), "not yet")
        self.now = at(2026, 10, 5, 18, 5)  # the evening after
        event = self.agent.tick()
        self.assertEqual(event["type"], "checkin")
        self.assertIn("how", event["text"].lower())
        self.assertIn("job interview", event["text"])
        self.now += 7200
        self.assertIsNone(self.agent.tick(), "asked once")

    def test_check_ins_respect_quiet_hours_and_go_stale(self):
        self.agent.chat("I've got my driving test on Monday")
        self.now = at(2026, 10, 7, 1, 0)  # quiet hours
        self.assertIsNone(self.agent.tick())
        self.now = at(2026, 10, 12, 18, 0)  # a week later: too late to ask naturally
        self.assertIsNone(self.agent.tick())

    def test_birthday_nudge_once_a_day(self):
        self.store.put("memory", {"text": "Maya's birthday is October 5"})
        self.now = at(2026, 10, 3, 9, 0)
        event = self.agent.tick()
        self.assertEqual(event["text"], "Heads up, Maya's birthday is on Monday. Want me to help you plan something?")
        self.now += 3 * 3600
        self.assertIsNone(self.agent.tick())

    def test_diary_is_off_by_default_then_private_searchable_and_expiring(self):
        self.agent.chat("the apartment on Oak Street had a leaky ceiling, I'm not taking it")
        self.assertIn("diary's off", self.agent.chat("what did I say about the apartment?")["text"])
        self.assertEqual(self.store.all("diary"), [])
        self.agent.set_presence("diary_days", 7)
        self.agent.chat("the apartment on Oak Street had a leaky ceiling, I'm not taking it")
        self.assertNotIn(b"leaky ceiling", self.store.db_path.read_bytes(), "encrypted at rest")
        found = self.agent.chat("what did I say about the apartment?")
        self.assertIn("leaky ceiling", found["text"])
        self.now += 8 * 86400
        self.agent._last_diary_prune = 0
        self.agent.tick()
        self.assertEqual([d for d in self.store.all("diary") if "leaky" in d["you"]], [])
        self.agent.chat("note to self the blue car is nicer")
        self.agent.set_presence("diary_days", 0)
        self.assertEqual(self.store.all("diary"), [], "turning it off erases it")

    def test_kids_mode_learns_nothing(self):
        self.agent.set_mode("kids")
        self.agent.chat("my dog's name is Biscuit")
        self.assertEqual(self.memories(), [])


if __name__ == "__main__":
    unittest.main()
