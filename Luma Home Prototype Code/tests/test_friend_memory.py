"""Memory like a friend's, over days: the people in their life, what's coming up for them, and forgetting when asked."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from luma.agent.runtime import Agent
from luma.memory.store import Store

NY = ZoneInfo("America/New_York")


def at(*args):
    return datetime(*args, tzinfo=NY).timestamp()


class OverDays(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.now = at(2026, 11, 10, 19, 0)  # a Tuesday evening
        self.agent = Agent(store=self.store, use_model=False, now=lambda: self.now)
        self.agent.use_model = True
        self.contexts = []

        def planner(messages, context, allowed, mode):
            self.contexts.append(" ".join(str(m.get("content")) for m in messages) + " "
                                 + " ".join(str(c.get("text")) for c in context if isinstance(c, dict)))
            return {"type": "reply", "text": "Oh nice, tell me more."}
        self.agent.planner = planner

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def new_conversation(self):
        self.agent.history = []
        self.agent.threads["main"] = self.agent.history

    def test_thursday_morning_gets_asked_about_thursday_night(self):
        self.agent.chat("i have a job interview at the hospital thursday morning")
        self.now = at(2026, 11, 12, 18, 5)
        event = self.agent.tick()
        self.assertEqual(event["type"], "checkin")
        self.assertIn("job interview", event["text"])

    def test_the_people_in_their_life_are_there_days_later(self):
        self.agent.chat("My daughter Lily is obsessed with dinosaurs right now.")
        self.now = at(2026, 11, 13, 10, 0)
        self.new_conversation()
        self.agent.chat("What should I get Lily for her birthday?")
        self.assertTrue(self.contexts)
        for seen in self.contexts[-3:]:  # every trip through the brain for that question, whichever path it took
            self.assertIn("dinosaurs", seen, "what they said about Lily reaches the brain three days later")

    def test_forget_that_takes_the_check_in_too(self):
        self.agent.chat("i have a job interview at the hospital thursday morning")
        self.assertTrue(self.store.all("checkin"))
        self.assertEqual(self.agent.chat("forget that")["text"], "Forgotten.")
        self.assertEqual([c for c in self.store.all("checkin") if not c["topic"].startswith("feeling:")], [])
        self.now = at(2026, 11, 12, 18, 5)
        self.assertIsNone(self.agent.tick(), "and Luma doesn't ask about it later")

    def test_forget_about_a_thing_forgets_every_trace_of_it(self):
        self.agent.chat("i have a job interview at the hospital thursday morning")
        self.agent.chat("My daughter Lily is obsessed with dinosaurs right now.")
        out = self.agent.chat("forget about the job interview")
        self.assertEqual(out["text"], "Done, it's forgotten.")
        self.assertEqual([c for c in self.store.all("checkin") if "interview" in c["topic"]], [])
        self.assertIn("Lily (their daughter) is obsessed with dinosaurs right now", [m["text"] for m in self.store.all("memory")],
                      "only what was about the interview")
        out = self.agent.chat("forget about lily and the dinosaurs")
        self.assertEqual(out["text"], "Done, it's forgotten.")
        self.assertEqual(self.store.all("memory"), [])
        self.assertEqual(self.agent.chat("forget about the zoo trip")["text"], "I didn't have anything saved about that.")

    def test_forget_about_it_is_never_mind_not_a_wipe(self):
        self.agent.chat("My daughter Lily is obsessed with dinosaurs right now.")
        self.agent.chat("forget about it")
        self.assertTrue(self.store.all("memory"), "\"forget about it\" means never mind")


if __name__ == "__main__":
    unittest.main()
