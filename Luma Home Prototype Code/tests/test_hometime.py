"""What time it is where their people are: someone in Tokyo missing their mom in Ohio hears that she's up now."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from luma.agent import hometime
from luma.agent.runtime import Agent
from luma.memory.store import Store

TOKYO = ZoneInfo("Asia/Tokyo")
NY = ZoneInfo("America/New_York")


class HomeTime(unittest.TestCase):
    def test_where_people_live_from_what_luma_already_remembers(self):
        self.assertEqual(hometime.where("Mom (their mom) lives in Ohio")[:3], ("Mom", "mom", "America/New_York"))
        self.assertEqual(hometime.where("Jake (their brother) lives in San Diego now")[2], "America/Los_Angeles")
        self.assertEqual(hometime.where("Nana (their grandma) just moved to Phoenix")[2], "America/Phoenix")
        self.assertEqual(hometime.where("Dad (their dad) lives in Washington DC")[2], "America/New_York")
        self.assertEqual(hometime.where("my mom lives in Ohio")[:3], ("mom", "mom", "America/New_York"), "kept as they said it")
        self.assertEqual(hometime.where("my brother Jake just moved to Seattle")[:3], ("Jake", "brother", "America/Los_Angeles"))
        self.assertEqual(hometime.where("my grandma lives in hawaii")[3], "Hawaii")
        self.assertIsNone(hometime.where("Mom (their mom) loves gardening"))
        self.assertIsNone(hometime.where("Mom (their mom) lives in a town I can't place"))

    def test_missing_her_in_the_tokyo_evening_is_her_morning_in_ohio(self):
        now = datetime(2026, 11, 13, 22, 10, tzinfo=TOKYO).timestamp()  # 8:10 AM in Ohio
        out = hometime.note("i miss my mom so much tonight", [{"text": "Mom (their mom) lives in Ohio"}], now, TOKYO)
        self.assertIn("It's 8:10 AM in Ohio", out)
        self.assertIn("A good time to reach them", out)

    def test_too_late_there_says_text_instead(self):
        now = datetime(2026, 11, 13, 16, 0, tzinfo=TOKYO).timestamp()  # 2 AM in Ohio
        out = hometime.note("should i call my mom", [{"text": "Mom (their mom) lives in Ohio"}], now, TOKYO)
        self.assertIn("2:00 AM", out)
        self.assertIn("a text they'll wake up to", out)

    def test_nothing_said_when_it_doesnt_help(self):
        now = datetime(2026, 11, 13, 22, 0, tzinfo=TOKYO).timestamp()
        mem = [{"text": "Mom (their mom) lives in Ohio"}]
        self.assertEqual(hometime.note("my mom made the best pie", mem, now, TOKYO), "", "not reaching for her")
        self.assertEqual(hometime.note("i miss my brother", mem, now, TOKYO), "", "not someone whose home Luma knows")
        self.assertEqual(hometime.note("i miss my mom", mem, now, NY), "", "same time zone")

    def test_a_turn_tells_the_brain_and_kids_mode_doesnt(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        store = Store(root / "s.db", root / "k")
        try:
            now = datetime(2026, 11, 13, 22, 10, tzinfo=TOKYO).timestamp()
            agent = Agent(store=store, use_model=False, now=lambda: now)
            agent.zone = TOKYO
            store.put("memory", {"text": "my mom lives in Ohio"})
            notes = agent._mind_context("i really miss my mom rn")
            self.assertTrue(any("8:10 AM in Ohio" in n["text"] for n in notes))
            self.assertFalse(any("in Ohio" in n["text"] for n in agent._mind_context("what should i cook tonight")))
            agent.set_mode("kids")
            self.assertFalse(any("in Ohio" in n["text"] for n in agent._mind_context("i miss my mom")))
        finally:
            store.close()
            temp.cleanup()


class RememberWhereTheyLive(unittest.TestCase):
    """'remember my sister lives in Seattle' was answered as a question ('I don't have that saved'). It's something to keep."""

    def test_remember_my_sister_lives_in_seattle_is_kept(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        store = Store(root / "s.db", root / "k")
        try:
            agent = Agent(store=store, use_model=False)
            for said in ("remember my sister lives in Seattle", "remember my dad loves golf", "remember that my mom lives in Ohio"):
                out = agent.chat(said)
                self.assertNotIn("don't have that saved", str(out.get("text")), said)
            kept = {m["text"] for m in store.all("memory", 10)}
            self.assertIn("my sister lives in Seattle", kept)
            self.assertIn("my mom lives in Ohio", kept, "no stray 'that'")
            self.assertEqual(hometime.where("my sister lives in Seattle")[2], "America/Los_Angeles")
            self.assertIn("Seattle", agent.chat("remember my sisters name?")["text"], "a question still gets an answer")
        finally:
            store.close()
            temp.cleanup()
