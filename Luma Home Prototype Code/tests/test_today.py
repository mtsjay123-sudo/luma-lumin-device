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
        self.assertIsNone(mem["limit"], "no limit on the device")

    def test_device_reports_storage_left(self):
        s = today.payload(self.agent)["device"]["storage"]
        self.assertGreater(s["total"], 0)
        self.assertLessEqual(s["free"], s["total"])
        self.assertIn("models", s["luma"])

    def signed_in(self, **account):
        self.agent.cloud.signed_in = lambda: True
        self.store.set_setting("luma_cloud_account", {"plan": "free", "texts_used": 12, "texts_limit": 30, "texts_left": 18,
                                                      "period_ends": "2026-12-01T12:00:00Z", **account})  # noon: Dec 1 wherever the test runs

    def test_with_no_account_there_is_no_plan_to_show(self):
        self.assertIsNone(today.payload(self.agent)["account"])
        self.assertIsNone(today.compact(self.agent)["account"])

    def test_the_plan_says_what_is_left_and_that_home_has_no_limit(self):
        self.signed_in()
        plan = today.payload(self.agent)["account"]
        self.assertEqual((plan["plan"], plan["state"]), ("free", "ok"))
        self.assertEqual(plan["texts"], {"used": 12, "limit": 30, "left": 18})
        self.assertIn("18 of 30 texts left this month", plan["line"])
        self.assertIn("no limit", plan["line"])
        self.assertEqual(today.compact(self.agent)["account"], plan, "the same plan reaches the phone away from home")

    def test_running_low_says_when_the_month_starts_over(self):
        self.signed_in(texts_used=27, texts_left=3)
        plan = today.payload(self.agent)["account"]
        self.assertEqual(plan["state"], "low")
        self.assertIn("3 of 30 texts left", plan["line"])
        self.assertIn("Dec 1", plan["line"])

    def test_used_up_says_what_still_works_and_never_pushes(self):
        self.signed_in(texts_used=30, texts_left=0, plus={"price": "$9.99/month", "texts_limit": 300})
        plan = today.payload(self.agent)["account"]
        self.assertEqual(plan["state"], "out")
        line = plan["line"]
        self.assertIn("This month's 30 texts are used", line)
        self.assertIn("Dec 1", line)
        self.assertIn("still talks at home", line)
        self.assertIn("Luma Plus has 300 a month", line)
        for push in ("upgrade now", "don't miss", "!", "only", "hurry", "running out"):
            self.assertNotIn(push, line.lower())

    def test_plus_is_named_and_is_never_offered_itself(self):
        self.signed_in(plan="plus", texts_used=300, texts_limit=300, texts_left=0, plus={"price": "$9.99/month", "texts_limit": 300})
        plan = today.payload(self.agent)["account"]
        self.assertEqual((plan["plan"], plan["state"]), ("plus", "out"))
        self.assertIn("300", plan["line"])
        self.assertNotIn("Luma Plus has", plan["line"])
        self.signed_in(plan="plus", texts_used=10, texts_limit=300, texts_left=290)
        self.assertTrue(today.payload(self.agent)["account"]["line"].startswith("Luma Plus."))

    def test_a_plan_with_odd_numbers_never_breaks_the_home_screen(self):
        for odd in ({"texts_limit": None, "texts_left": None, "texts_used": None}, {"texts_limit": "many", "texts_left": -4}, {"period_ends": "soon"},
                    {"texts_limit": 0, "texts_left": 0, "texts_used": 0}):
            self.signed_in(**odd)
            plan = today.payload(self.agent)["account"]
            self.assertIn(plan["state"], {"ok", "low", "out"}, odd)
            self.assertTrue(plan["line"], odd)
            self.assertNotIn("None", plan["line"])

    def test_kids_mode_shows_no_plan(self):
        self.signed_in()
        self.agent.set_mode("kids")
        self.assertNotIn("account", today.payload(self.agent))

    def test_kids_mode_shows_nothing_personal(self):
        self.store.put("memory", {"text": "private"})
        self.agent.set_mode("kids")
        out = today.payload(self.agent)
        self.assertTrue(out["kids"])
        self.assertIsNone(out["memory"])
        self.assertEqual(out["chats"], [])


if __name__ == "__main__":
    unittest.main()
