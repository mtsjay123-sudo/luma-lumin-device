"""News the way a friend tells it: one story once, where outlets disagree, nothing old called breaking, nothing made up,
what they care about from what they've told Luma, and never hard news pushed at someone having a bad time."""
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store
from luma.skills import news

NOW = datetime(2026, 11, 9, 15, 0).timestamp()
H = 3600


def item(source, title, hours_ago, topic="us", snippet="", url=None):
    return {"source": source, "title": title, "published": NOW - hours_ago * H, "topic": topic, "snippet": snippet,
            "url": url or f"https://{source.lower().replace(' ', '')}.example/{abs(hash(title)) % 10**6}"}


BRIDGE = [item("Metro Wire", "BREAKING: Harbor City bridge collapse leaves 12 dead", 5),
          item("Capital Dispatch", "At least 15 dead after Harbor City bridge collapse", 3),
          item("Coastline News", "Harbor City bridge collapse: rescue crews search the river", 1)]
VOTE = [item("Wire One", "Riverton council approves the new transit line", 4), item("Northside Post", "Riverton transit line wins council approval", 2)]
GAME = [item("Field Report", "Riverton Otters beat the Pines 3-1 in the cup final", 1, "sports")]
ALL = BRIDGE + VOTE + GAME


class TheHelpers(unittest.TestCase):
    def test_where_outlets_give_different_numbers_it_says_so(self):
        self.assertEqual(news.differs(BRIDGE), "Capital Dispatch says 15, Metro Wire says 12")
        self.assertEqual(news.differs(VOTE), "")
        story = next(s for s in news.stories(ALL, 8) if "bridge" in s["title"].lower())
        self.assertIn("15", story["differs"])
        self.assertEqual(len(story["outlets"]), 3)

    def test_nothing_old_is_breaking(self):
        self.assertEqual(news.calm("BREAKING: Harbor City bridge collapse leaves 12 dead", 5), "Harbor City bridge collapse leaves 12 dead")
        self.assertTrue(news.calm("BREAKING: Harbor City bridge collapse leaves 12 dead", 0.5).startswith("BREAKING"))
        self.assertEqual(news.calm("Just in: Council votes tonight", 3), "Council votes tonight")

    def test_hard_news_is_known_for_what_it_is(self):
        self.assertTrue(news.hard(BRIDGE[0]))
        self.assertTrue(news.hard(item("Wire One", "Wildfire forces thousands to evacuate", 1)))
        self.assertFalse(news.hard(VOTE[0]))
        self.assertFalse(news.hard(GAME[0]))

    def test_a_written_answer_is_held_to_the_headlines_it_was_given(self):
        given = news.stories(BRIDGE, 3)
        self.assertEqual(news.grounded("A bridge in Harbor City collapsed. Metro Wire says 12 died and Capital Dispatch says 15.", given, NOW), [])
        made_up = news.grounded("Breaking: Reuters reports 40 dead in Harbor City.", news.stories(BRIDGE[:2], 3), NOW)  # the newest word is 3 hours old
        self.assertEqual(len(made_up), 3, made_up)
        self.assertEqual(len(news.grounded("Breaking: rescue crews are searching the river in Harbor City.", given, NOW)), 0, "an hour old can be breaking")

    def test_what_they_care_about_comes_from_what_they_told_luma(self):
        temp = tempfile.TemporaryDirectory()
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        try:
            store.put("memory", {"text": "You live in Austin", "created": NOW - 900 * 86400})
            store.put("memory", {"text": "You moved to Riverton", "created": NOW - 90 * 86400})
            store.put("memory", {"text": "Your favorite team is the Otters", "created": NOW - 80 * 86400})
            wanted = news.interests(store)
            self.assertIn("riverton", wanted)
            self.assertIn("the otters", wanted)
            self.assertNotIn("austin", wanted, "where they used to live isn't where they live")
            self.assertEqual({i["source"] for i in news.about_them(ALL, wanted)}, {"Wire One", "Northside Post", "Field Report"})
        finally:
            store.close()
            temp.cleanup()

    def test_an_alert_is_new_widely_carried_or_theirs_and_told_once(self):
        fresh = news.stories(news.within(ALL, 2, NOW), 8)
        first = news.worth_an_alert(fresh, set(), ["the otters"], NOW)
        self.assertIn("Otters", first["title"], "one outlet, but it's their team")
        self.assertIsNone(news.worth_an_alert(fresh, {news._key(s) for s in fresh}, ["the otters"], NOW))
        self.assertIsNone(news.worth_an_alert(news.stories(VOTE, 4), set(), [], NOW), "two outlets, hours old, nothing of theirs")


class InLuma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.agent = Agent(store=self.store, use_model=False)
        self.now = [NOW]
        self.agent.clock = lambda: self.now[0]
        self.store.set_setting("news", {"fetched": NOW, "items": ALL})
        self.live = []
        self.agent._live_news = lambda query, section, hours: self.live.append(query or section) or []

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_one_story_is_told_once_with_who_says_what(self):
        out = self.agent.news_reply("what's the latest on the harbor city bridge")
        self.assertEqual(out["text"].lower().count("bridge collapse"), 1, out["text"])
        self.assertIn("they differ", out["text"])
        self.assertNotIn("BREAKING", out["text"])
        self.assertIn("1h ago", out["text"], "the newest word on it, not the first")
        self.assertEqual(len(out["results"]), 1)
        self.assertTrue(out["results"][0]["url"].startswith("https://"), "the app links the source")

    def test_whats_already_here_is_answered_without_a_search(self):
        self.store.set_setting("news", {"fetched": NOW, "items": ALL + [item("Wire One", "Riverton transit line: what riders should know", 6)]})
        began = time.perf_counter()
        out = self.agent.news_reply("any news on the riverton transit line")
        self.assertLess(time.perf_counter() - began, 0.3)
        self.assertEqual(self.live, [])
        self.assertIn("transit", out["text"].lower())

    def test_a_slow_search_gets_two_seconds_then_what_it_had(self):
        def slow(query, section, hours):
            time.sleep(5)
            return [item("Late Wire", "Too late to matter", 0)]
        self.agent._live_news = slow
        self.agent.LIVE_NEWS_WAIT = 0.3
        began = time.perf_counter()
        out = self.agent.news_reply("what's the news about the otters")
        self.assertLess(time.perf_counter() - began, 2)
        self.assertIn("Otters", out["text"])
        self.assertNotIn("Too late", out["text"])

    def test_a_made_up_outlet_or_number_from_the_brain_is_never_said(self):
        self.agent.use_model = True
        self.agent.planner = lambda messages, context, allowed, mode: {"type": "reply", "text": "Reuters reports 40 dead in the Harbor City collapse."}
        out = self.agent.news_reply("what's the latest on the harbor city bridge")
        self.assertNotIn("Reuters", out["text"])
        self.assertNotIn("40", out["text"])
        self.agent.planner = lambda messages, context, allowed, mode: {"type": "reply", "text": "A bridge came down in Harbor City. Metro Wire says 12 died; Capital Dispatch says 15."}
        self.assertIn("Capital Dispatch says 15", self.agent.news_reply("what's the latest on the harbor city bridge")["text"])

    def test_reading_the_room(self):
        shown = lambda text: " ".join(m["text"] for m in self.agent._news_context(text))  # noqa: E731
        self.assertIn("bridge", shown("did you hear about the harbor city bridge collapse").lower())
        self.agent.history = [{"role": "user", "content": "my dad passed away last night"}, {"role": "assistant", "content": "{}"}]
        self.assertEqual(shown("i keep thinking about that harbor city bridge collapse"), "", "they're grieving and didn't ask for the news")
        self.assertIn("transit", shown("the riverton transit line vote went through i think").lower())
        self.assertIn("bridge", self.agent.news_reply("what's the news on the harbor city bridge collapse")["text"].lower(), "they asked: it's theirs to hear")
        top = self.agent.news_reply("what's in the news")["text"]
        self.assertIn("transit", top.lower())

    def test_alerts_are_off_until_turned_on_never_for_kids_and_one_an_hour(self):
        self.store.put("memory", {"text": "Your favorite team is the Otters", "created": NOW - 80 * 86400})
        local = datetime.fromtimestamp(NOW, self.agent.zone)
        self.assertIsNone(self.agent._news_alert(NOW, local))
        self.store.set_setting("news_alerts", True)
        self.store.set_setting("mode", "kids")
        self.assertIsNone(self.agent._news_alert(NOW, local))
        self.store.set_setting("mode", "friend")
        first = self.agent._news_alert(NOW, local)
        self.assertIn("Otters", first["text"])
        self.assertIsNone(self.agent._news_alert(NOW + 60, local), "one an hour")
        self.now[0] = NOW + 2 * H
        self.assertIsNone(self.agent._news_alert(NOW + 2 * H, local), "told once")

    def test_no_hard_alert_on_a_hard_day(self):
        self.store.set_setting("news_alerts", True)
        self.store.set_setting("news", {"fetched": NOW, "items": [item(s, "Harbor City bridge collapse leaves 12 dead", 1) for s in ("Metro Wire", "Wire One", "Coastline News")]})
        local = datetime.fromtimestamp(NOW, self.agent.zone)
        self.store.put("checkin", {"topic": "feeling:grief", "day": local.date().isoformat(), "asked": False, "mode": "friend"})
        self.assertIsNone(self.agent._news_alert(NOW, local))


if __name__ == "__main__":
    unittest.main()
