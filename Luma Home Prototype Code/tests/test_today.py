"""The phone's home screen in one call: today's chats first, the memory deck with tabs, the device's
storage left, and nothing personal in kids mode."""
import tempfile
import time
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.control import today
from luma.memory.store import Store


class TodayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_todays_chats_come_first_with_their_last_line(self):
        now = self.agent.clock()
        old = self.agent.new_thread("Last week")["id"]
        self.agent.transcripts[old] += [{"role": "you", "text": "hi", "at": now - 8 * 86400}]
        new = self.agent.new_thread("Taco plan")["id"]
        self.agent.transcripts[new] += [{"role": "you", "text": "is atl good", "at": now - 60}, {"role": "luma", "text": "Midtown, not Peachtree.", "at": now - 30}]
        chats = today.payload(self.agent)["chats"]
        self.assertEqual(chats[0]["title"], "Taco plan")
        self.assertTrue(chats[0]["today"])
        self.assertEqual(chats[0]["last"], {"role": "luma", "text": "Midtown, not Peachtree."})
        self.assertFalse(next(c for c in chats if c["title"] == "Last week")["today"])

    def test_memory_deck_has_tabs_and_the_plan_limit(self):
        for text in ["Spare keys are in the blue kitchen drawer", "You hate cilantro", "Your sister Nia lives in Durham", "Saving for Tokyo in March"]:
            self.store.put("memory", {"text": text})
        mem = today.payload(self.agent)["memory"]
        kinds = {m["text"]: m["kind"] for m in mem["recent"]}
        self.assertEqual(kinds["Spare keys are in the blue kitchen drawer"], "Places")
        self.assertEqual(kinds["You hate cilantro"], "Likes")
        self.assertEqual(kinds["Saving for Tokyo in March"], "Plans")  # a goal with a month in it is still a plan
        self.assertEqual(mem["used"], 4)
        self.assertEqual(mem["limit"], self.agent.FREE_MEMORIES)

    def test_device_reports_storage_left(self):
        s = today.payload(self.agent)["device"]["storage"]
        self.assertGreater(s["total"], 0)
        self.assertLessEqual(s["free"], s["total"])
        self.assertIn("models", s["luma"])

    def test_kids_mode_shows_nothing_personal(self):
        self.store.put("memory", {"text": "private"})
        self.agent.set_mode("kids")
        out = today.payload(self.agent)
        self.assertTrue(out["kids"])
        self.assertIsNone(out["memory"])
        self.assertEqual(out["chats"], [])


if __name__ == "__main__":
    unittest.main()
