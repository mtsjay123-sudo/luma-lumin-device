"""No made-up answers, even when the brain tries. A stand-in brain here always invents: a track list, a price, a quote,
a sister's name. With nothing real to go on (no web, no quote, nothing saved), what reaches the owner says so instead."""
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store

NOW = 1793116800.0
LIES = ("Glass Pelican's new record is fire, the second track 'Hollow Light' really stands out and it sold 2 million copies. "
        "Tesla is at $412.77 today, up 6.2%. The Shade Room posted that Drake and Rihanna got married. "
        "Your sister's name is Jessica. Like Kendrick says, \"they not like us, they not like us at all\".")


class NoMadeUpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.agent = Agent(store=self.store, use_model=True, now=lambda: NOW)
        self.agent.planner = lambda *a: {"type": "reply", "text": LIES}  # always invents
        self.agent._live_news = lambda *a: []
        self.agent.look_it_up = lambda *a, **k: {"text": "", "results": []}  # the web came back empty
        self.agent.market_fetch = lambda url: (_ for _ in ()).throw(OSError("offline"))
        self.agent.search_web = lambda query: {"results": [], "summary": "Nothing came back."}
        self.store.set_setting("news", {"fetched": NOW, "items": []})

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def said(self, text):
        return self.agent.chat(text)["text"]

    def assertNoLies(self, reply):
        for invented in ("Hollow Light", "2 million", "412.77", "6.2%", "married", "Jessica", "not like us"):
            self.assertNotIn(invented, reply)

    def test_a_record_that_cant_be_checked(self):
        reply = self.said("what do you think of glass pelican's new record?")
        self.assertNoLies(reply)
        self.assertRegex(reply, r"couldn't (?:look|check)")

    def test_a_price_that_cant_be_read(self):
        reply = self.said("what's tesla stock at?")
        self.assertNoLies(reply)
        self.assertIn("won't guess", reply)

    def test_the_culture_with_nothing_read(self):
        reply = self.said("what did the shade room post today?")
        self.assertNoLies(reply)
        self.assertIn("won't guess", reply)

    def test_something_they_never_said(self):
        reply = self.said("what's my sister's name?")
        self.assertNoLies(reply)
        self.assertIn("don't know", reply)

    def test_lyrics_it_didnt_look_up(self):
        reply = self.said("what's your favorite line from kendrick's verse on like that?")
        self.assertNotIn("not like us", reply)

    def test_what_was_read_still_comes_through_word_for_word(self):
        self.store.set_setting("news", {"fetched": NOW, "items": [
            {"title": "Singer surprises fans with a pop-up show in Atlanta", "url": "https://theshaderoom.com/a", "source": "The Shade Room",
             "snippet": "", "published": NOW - 3600, "topic": "culture", "seen": NOW}]})
        reply = self.agent.chat("what did the shade room post today?")
        self.assertIn("pop-up show in Atlanta", reply["text"] + " ".join(r["title"] for r in reply["results"]))
        self.assertEqual(reply["results"][0]["source"], "The Shade Room")


if __name__ == "__main__":
    unittest.main()
