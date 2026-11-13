"""A laugh or an "ok ok" before "remind me" is talk, not part of the reminder (heard in the recorded conversation, Nov 13:
"lmaooo ok ok. remind me friday at 9am to run the pitch one more time" became a reminder about "lmaooo ok ok")."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from luma.agent.runtime import Agent
from luma.memory.store import Store

NY = ZoneInfo("America/New_York")


class ChatterBeforeRemind(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        now = datetime(2026, 11, 12, 21, 0, tzinfo=NY).timestamp()  # a Thursday evening
        self.agent = Agent(store=self.store, use_model=False, now=lambda: now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_what_comes_before_a_whole_reminder_is_left_out(self):
        for said in ("lmaooo ok ok. remind me friday at 9am to run the pitch one more time",
                     "haha bet! remind me friday at 9am to run the pitch one more time",
                     "ok ok ok. Remind me friday at 9am to run the pitch one more time"):
            out = self.agent.chat(said)["text"]
            self.assertIn("remind you to run the pitch one more time tomorrow at 9 AM", out, said)
            for chatter in ("lmao", "haha", "bet", "ok ok"):
                self.assertNotIn(chatter, out.lower(), said)

    def test_a_task_said_first_and_the_time_after_still_works(self):
        out = self.agent.chat("pay rent. remind me tomorrow at 9am")["text"]
        self.assertIn("pay rent", out)
        self.assertIn("tomorrow at 9 AM", out)


class HeardInTheRecording(unittest.TestCase):
    """The other two slips in the recorded conversation of Nov 13."""

    def test_a_question_for_a_take_after_some_chatter_is_still_a_question_for_a_take(self):
        from luma.agent.runtime import wants_a_take
        for said in ("fr fr. ok should i lead with the lamp or the app", "lol ok. which one is better, the lamp or the app",
                     "ok wait. be honest, is it dumb to lead with the app"):
            self.assertTrue(wants_a_take(said), said)
        for said in ("fr fr. ok make me a checklist for the pitch", "ok. should i? just make me an app to track it"):
            self.assertFalse(wants_a_take(said), said)
