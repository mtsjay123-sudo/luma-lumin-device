"""Current and accurate: the top story is the one the most outlets are covering (not just the newest), a story only one outlet has
is said to be theirs, and "what's trending on TikTok" is answered from what Luma can really read (news coverage of what's blowing
up there, Google Trends searches, Wikipedia's most read), said for what it is. Luma never claims to have scrolled TikTok."""
import json
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store
from luma.skills import news

NOW = 1793116800.0  # 2026-10-27 16:00 UTC


def item(source, title, topic="top", hours_ago=1, **extra):
    return dict({"title": title, "url": "https://example.com/" + title.lower().replace(" ", "-")[:40], "source": source, "snippet": "",
                 "published": NOW - hours_ago * 3600, "topic": topic, "seen": NOW}, **extra)


TRENDS_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel><title>Daily Search Trends</title>
<item><title>world series game 3</title><ht:approx_traffic>2000000+</ht:approx_traffic><pubDate>Tue, 27 Oct 2026 10:00:00 +0000</pubDate>
<ht:news_item><ht:news_item_title>Dodgers and Blue Jays meet in Game 3 tonight</ht:news_item_title><ht:news_item_url>https://www.espn.com/mlb/story</ht:news_item_url><ht:news_item_source>ESPN</ht:news_item_source></ht:news_item>
</item>
<item><title>daylight saving time</title><ht:approx_traffic>500000+</ht:approx_traffic><pubDate>Tue, 27 Oct 2026 09:00:00 +0000</pubDate></item>
</channel></rss>"""

MOSTREAD = json.dumps({"mostread": {"date": "2026-10-26Z", "articles": [
    {"normalizedtitle": "Main Page", "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Main_Page"}}},
    {"normalizedtitle": "2026 World Series", "views": 812000, "description": "Championship series of Major League Baseball",
     "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/2026_World_Series"}}},
]}}).encode()

GOOGLE_TOP = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Senate passes funding bill to end shutdown - Reuters</title><link>https://news.google.com/rss/articles/abc</link>
<pubDate>Tue, 27 Oct 2026 11:00:00 GMT</pubDate>
<description>&lt;ol&gt;&lt;li&gt;&lt;a href="https://news.google.com/a"&gt;Senate passes funding bill&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;Reuters&lt;/font&gt;&lt;/li&gt;&lt;li&gt;&lt;a href="https://news.google.com/b"&gt;Shutdown nears end&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;NPR&lt;/font&gt;&lt;/li&gt;&lt;li&gt;&lt;a href="https://news.google.com/c"&gt;What's in the bill&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;Axios&lt;/font&gt;&lt;/li&gt;&lt;/ol&gt;</description>
</item></channel></rss>"""


class ReadingTests(unittest.TestCase):
    def test_google_trends_searches_with_the_story_behind_them(self):
        got = news.parse_trends(TRENDS_RSS)
        self.assertEqual([g["title"] for g in got], ["world series game 3", "daylight saving time"])
        self.assertEqual(got[0]["traffic"], "2000000+")
        self.assertIn("Dodgers and Blue Jays", got[0]["snippet"])
        self.assertEqual(got[0]["url"], "https://www.espn.com/mlb/story")
        self.assertTrue(got[1]["url"].startswith("https://trends.google.com/trends/explore"), "no story: a link to the search itself")
        self.assertEqual(news.parse_trends(b"not xml"), [])

    def test_wikipedias_most_read_without_its_own_pages(self):
        got = news.parse_mostread(MOSTREAD)
        self.assertEqual([g["title"] for g in got], ["2026 World Series"])
        self.assertEqual(got[0]["views"], 812000)
        self.assertEqual(news.parse_mostread(b"{"), [])

    def test_google_news_lists_who_else_is_covering_it(self):
        got = news.parse(GOOGLE_TOP, "Google News")
        self.assertEqual(got[0]["source"], "Reuters")
        self.assertEqual(got[0]["also"], ["NPR", "Axios"])
        self.assertEqual(got[0]["snippet"], "", "not a run-on list of other headlines")

    def test_trend_sources_are_read_with_the_rest(self):
        urls = [f[1] for f in news.extras(NOW)]
        self.assertTrue(any("trends.google.com/trending/rss" in u for u in urls))
        self.assertTrue(any("tiktok" in u for u in urls) and any("instagram" in u for u in urls))
        self.assertIn("en.wikipedia.org/api/rest_v1/feed/featured/2026/10/27", " ".join(urls))
        store = Store(Path(tempfile.mkdtemp()) / "s.db", Path(tempfile.mkdtemp()) / "k")
        try:
            def fetch(url):
                return TRENDS_RSS if "trends.google" in url else MOSTREAD if "wikipedia" in url else GOOGLE_TOP
            import os
            from unittest import mock
            with mock.patch.object(news, "feeds", lambda: [("Google News", "https://news.google.com/rss", "top")] + news.extras(NOW)):
                got = news.refresh(store, lambda: NOW, fetch=fetch)
            kinds = {i["topic"] for i in got["items"]}
            self.assertTrue({"trending", "lookedup", "top"} <= kinds, kinds)
        finally:
            store.close()


class RankingTests(unittest.TestCase):
    def test_the_story_everyone_is_covering_leads_not_just_the_newest(self):
        items = [item("TMZ", "Rapper spotted leaving club with mystery woman", "culture", 0.2),
                 item("BBC", "Senate passes funding bill ending government shutdown", hours_ago=2),
                 item("NPR", "Senate passes bill to end the government shutdown", hours_ago=1.5),
                 item("Axios", "Government shutdown ends as Senate passes funding bill", hours_ago=1),
                 item("ESPN", "Dodgers win Game 2 of the World Series", "sports", 3)]
        ranked = news.stories(items)
        self.assertIn("shutdown", ranked[0]["title"])
        self.assertEqual(set(ranked[0]["outlets"]), {"BBC", "NPR", "Axios"})
        self.assertIn(news.credit(ranked[0]), {"Axios, NPR and 1 other", "Axios, BBC and 1 other", "BBC, NPR and 1 other", "NPR, BBC and 1 other",
                                               "Axios, NPR, BBC", "NPR, Axios and 1 other", "BBC, Axios and 1 other"})
        gossip = next(r for r in ranked if r["source"] == "TMZ")
        self.assertEqual(news.credit(gossip), "only TMZ so far")


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.agent = Agent(store=self.store, use_model=False, now=lambda: NOW)
        self.agent._live_news = lambda *a: []
        self.store.set_setting("news", {"fetched": NOW, "items": [
            item("BBC", "Senate passes funding bill ending government shutdown", hours_ago=2),
            item("NPR", "Senate passes bill to end the government shutdown", hours_ago=1.5),
            item("TMZ", "Rapper spotted leaving club with mystery woman", "culture", 0.2),
            item("Google Trends", "world series game 3", "trending", 2, snippet="Dodgers and Blue Jays meet in Game 3 tonight (ESPN)", traffic="2000000+"),
            item("Wikipedia", "2026 World Series", "lookedup", 12),
            item("Rolling Stone", "The 'silent walk' trend is taking over TikTok", "tiktok", 5),
            item("People", "Celebrity couple's Instagram post breaks the internet", "instagram", 6),
            item("Reddit", "TIL octopuses have three hearts", "viral", 1),
            item("YouTube · MrBeast", "I Built 100 Houses", "youtube", 3),
        ]})

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_top_news_leads_with_what_everyone_is_covering_and_leaves_out_trends(self):
        out = self.agent.chat("what's the top news right now")
        self.assertTrue(out["text"].split("): ", 1)[1].startswith("Senate passes"), out["text"])
        self.assertRegex(out["text"], r"\((?:BBC, NPR|NPR, BBC)")
        self.assertIn("only TMZ so far", out["text"])
        for not_news in ("world series game 3", "octopuses", "100 Houses", "2026 World Series"):
            self.assertNotIn(not_news, out["text"])

    def test_whats_trending_on_tiktok_is_said_for_what_it_is(self):
        out = self.agent.chat("what's trending on tiktok rn")
        self.assertIn("silent walk", out["text"])
        self.assertIn("can't scroll TikTok myself", out["text"])
        self.assertNotIn("Instagram post", out["text"])
        ig = self.agent.chat("whats viral on ig")
        self.assertIn("Instagram post breaks the internet", ig["text"])

    def test_what_everybody_is_talking_about(self):
        out = self.agent.chat("what's everybody talking about today?")
        self.assertIn("searching right now: world series game 3", out["text"])
        self.assertIn("Most looked up yesterday: 2026 World Series", out["text"])
        self.assertIn("silent walk", out["text"])
        self.assertEqual({r["source"] for r in out["results"]} >= {"Google Trends", "Wikipedia"}, True)

    def test_nothing_trending_means_saying_so(self):
        self.store.set_setting("news", {"fetched": NOW, "items": []})
        out = self.agent.chat("what's trending on tiktok")
        self.assertIn("won't guess", out["text"])
        self.assertNotIn("results", out)


if __name__ == "__main__":
    unittest.main()
