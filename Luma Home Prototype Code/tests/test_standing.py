"""Tasks set by voice: "every weekday at 8, tell me the weather" runs at 8 on weekdays, through Luma's own conversation
path, and is said out loud. Nothing anyone says to a friend is taken for a task."""
import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from luma.agent import standing
from luma.agent.runtime import Agent
from luma.memory.store import Store

TOKYO = ZoneInfo("Asia/Tokyo")
ROOT = Path(__file__).resolve().parents[1]


class Parse(unittest.TestCase):
    def test_the_shapes_people_use(self):
        self.assertEqual(standing.parse("every weekday at 8, tell me the weather"),
                         {"ask": "tell me the weather", "days": [0, 1, 2, 3, 4], "at": "08:00"})
        self.assertEqual(standing.parse("remind me to call mom every sunday at 6pm"),
                         {"ask": "remind me to call mom", "days": [6], "at": "18:00"})
        self.assertEqual(standing.parse("every night at 10 ask me how my day went")["at"], "22:00")
        self.assertEqual(standing.parse("every morning, read me the news")["at"], "08:00")
        self.assertEqual(standing.parse("every monday and thursday at 7:30 am remind me to take out the trash")["days"], [0, 3])
        self.assertEqual(standing.parse("hey luma, every evening play some jazz please")["ask"], "play some jazz")

    def test_not_tasks(self):
        for line in ["every night I cry myself to sleep", "every day feels the same", "every morning my boss yells at me",
                     "I tell my mom every week that I'm fine", "every sunday we used to go to church",
                     "every morning check my inbox", "every day watch the price of airpods", "every friday send my boss the report"]:
            self.assertIsNone(standing.parse(line.lower()), line)

    def test_reminders_are_said_not_run(self):
        self.assertEqual(standing.reminder("remind me to call Mom"), "call Mom")
        self.assertIsNone(standing.reminder("tell me the weather"))
        self.assertEqual(standing.spoken("remind me to call my mom"), "remind you to call your mom")


class Voice(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.t = [datetime(2026, 11, 13, 22, 0, tzinfo=TOKYO).timestamp()]   # a Friday night in Tokyo
        self.agent = Agent(store=Store(d / "l.db", d / "k.key"), use_model=False, now=lambda: self.t[0])
        self.agent.zone = TOKYO

    def say(self, line):
        return self.agent.chat(line)

    def tasks(self):
        return [r for r in self.agent.store.all("helper", 80) if r.get("kind") == "task"]

    def run_due(self):
        ran = self.agent.helpers.start_due()
        self.assertIsNotNone(ran)
        self.agent.helpers.thread.join(10)
        return self.agent.helpers.pop_event()

    def test_set_list_and_stop(self):
        self.assertIn("On weekdays at 8 AM, I'll tell you", self.say("every weekday at 8, tell me what's on my to-do list")["text"])
        self.assertIn("On Sundays at 6 PM, I'll remind you to call Mom", self.say("remind me to call Mom every Sunday at 6pm")["text"])
        self.assertIn("already", self.say("remind me to call Mom every Sunday at 6pm")["text"])
        self.assertIn("2 tasks", self.say("what tasks do i have")["text"])
        self.assertIn("won't remind you to call Mom", self.say("stop reminding me to call mom")["text"])
        self.assertIn("Stopped", self.say("cancel my to-do list task")["text"])
        self.assertEqual(self.tasks(), [])

    def test_weekday_tasks_skip_the_weekend(self):
        self.say("every weekday at 8, tell me what's on my to-do list")
        nxt = datetime.fromtimestamp(self.tasks()[0]["next_run"], TOKYO)
        self.assertEqual(nxt.strftime("%a %H:%M"), "Mon 08:00")

    def test_a_reminder_is_said_at_its_time(self):
        self.say("remind me to call Mom every Sunday at 6pm")
        self.t[0] = datetime(2026, 11, 15, 18, 0, 20, tzinfo=TOKYO).timestamp()
        self.assertEqual(self.run_due()["text"], "Hey, it's time to call Mom.")
        nxt = datetime.fromtimestamp(self.tasks()[0]["next_run"], TOKYO)
        self.assertEqual(nxt.strftime("%a %d %H:%M"), "Sun 22 18:00")

    def test_a_request_runs_through_luma_in_its_own_chat(self):
        self.say("add stretch and call the dentist to my to-do list")
        self.say("every weekday at 8, tell me what's on my to-do list")
        before = list(self.agent.history)
        self.t[0] = datetime(2026, 11, 16, 8, 0, 20, tzinfo=TOKYO).timestamp()
        said = self.run_due()["text"]
        self.assertIn("stretch", said)
        self.assertIn("call the dentist", said)
        self.assertEqual(self.agent.history, before, "a task never lands in the middle of their chat")
        self.assertEqual(len(self.tasks()), 1, "a task running never makes another task")

    def test_kids_mode_cannot_set_one(self):
        self.agent.set_mode("kids")
        self.assertIn("grown-up", self.say("every morning at 7 tell me a joke")["text"])
        self.assertEqual(self.tasks(), [])


def _lines():
    rows = [json.loads(line) for line in (ROOT / "data" / "human_eval_v2.jsonl").read_text().splitlines() if line.strip()]
    for row in rows:
        if row.get("said"): yield row["said"]
        for turn in row.get("turns", []):
            if turn.get("said"): yield turn["said"]
    yield from re.findall(r'"said": "((?:[^"\\]|\\.)*)"', (ROOT / "scripts" / "train_luma.py").read_text())


class NothingElseIsATask(unittest.TestCase):
    """Counts only: held-out lines are never printed."""

    def hits(self, lines):
        n = 0
        for line in lines:
            low = line.lower()
            n += bool(standing.parse(low) or standing.LIST.match(low) or standing.DROP.match(low) or standing.DROP2.match(low))
        return n

    def test_human_test_lines(self):
        lines = list(_lines())
        self.assertGreater(len(lines), 150)
        self.assertEqual(self.hits(lines), 0)

    def test_crisis_lines(self):
        for name in ("crisis_corpus.jsonl", "crisis_heldout.jsonl", "crisis_heldout2.jsonl"):
            lines = [json.loads(line)["text"] for line in (ROOT / "tests" / "data" / name).read_text().splitlines() if line.strip()]
            self.assertEqual(self.hits(lines), 0, name)


if __name__ == "__main__":
    unittest.main()
