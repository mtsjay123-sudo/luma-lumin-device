"""Always up on the culture and the markets, with no accounts or keys: what The Shade Room posted, what's new on YouTube, what's
blowing up, and live prices. Everything said comes from what was really read, with who posted it; nothing found means saying so."""
import json
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store
from luma.skills import markets, news

NOW = 1793116800.0  # 2026-10-27 12:00 UTC


def item(source, title, topic, hours_ago=1, url=None):
    return {"title": title, "url": url or "https://example.com/" + title.lower().replace(" ", "-")[:40], "source": source, "snippet": "",
            "published": NOW - hours_ago * 3600, "topic": topic, "seen": NOW}


class PulseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.agent = Agent(store=self.store, use_model=False, now=lambda: NOW)
        self.agent._live_news = lambda *a: []  # no network in tests
        self.store.set_setting("news", {"fetched": NOW, "items": [
            item("The Shade Room", "Singer surprises fans with a pop-up show in Atlanta", "culture"),
            item("The Shade Room", "Reality star responds to breakup rumors", "culture", 3),
            item("TMZ", "Actor spotted at courthouse", "culture", 2),
            item("YouTube · MrBeast", "I Built 100 Houses And Gave Them Away", "youtube", 5, "https://www.youtube.com/watch?v=abc"),
            item("Reddit", "This dog learned to open the fridge", "viral", 4),
            item("Reuters", "Central bank holds rates steady", "top", 2),
        ]})

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_what_the_shade_room_posted_comes_from_the_shade_room(self):
        out = self.agent.chat("what did the shade room post today?")
        self.assertIn("pop-up show in Atlanta", out["text"])
        self.assertIn("breakup rumors", out["text"])
        self.assertNotIn("courthouse", out["text"], "TMZ's story isn't The Shade Room's")
        self.assertTrue(all(r["source"] == "The Shade Room" for r in out["results"]))

    def test_whats_poppin_on_youtube_and_whats_viral(self):
        self.assertIn("100 Houses", self.agent.chat("what's poppin on youtube")["text"])
        tea = self.agent.chat("what's the tea today")["text"]
        self.assertIn("pop-up show", tea)
        self.assertIn("courthouse", tea)

    def test_nothing_from_them_means_saying_so_not_guessing(self):
        out = self.agent.chat("what's bossip saying")
        self.assertIn("I don't have anything new from Bossip", out["text"])
        self.assertIn("won't guess", out["text"])
        self.assertNotIn("results", out)

    def test_youtube_channels_are_found_from_their_public_page_and_remembered(self):
        pages = {"https://www.youtube.com/@MrBeast": b'<meta property="og:title" content="MrBeast"><script>{"channelId":"UCX6OQ3DkcsbYNE6H8uQQuVA"}</script>',
                 "https://www.youtube.com/@Nope": b"<html>not a channel</html>"}
        asked = []
        def page(url):
            asked.append(url)
            if url not in pages: raise OSError("offline")
            return pages[url]
        self.assertEqual(news.youtube_channel("MrBeast", page), {"id": "UCX6OQ3DkcsbYNE6H8uQQuVA", "name": "MrBeast"})
        self.assertIsNone(news.youtube_channel("@Nope", page))
        self.assertIsNone(news.youtube_channel("bad handle; rm", page))
        self.store.set_setting("youtube_follow", ["@MrBeast"])
        feeds = news.youtube_feeds(self.store, lambda: NOW, page)
        self.assertEqual(feeds[0], ("YouTube · MrBeast", "https://www.youtube.com/feeds/videos.xml?channel_id=UCX6OQ3DkcsbYNE6H8uQQuVA", "youtube"))
        self.assertEqual(len(feeds), 1, "handles that don't resolve are skipped")
        before = len(asked)
        news.youtube_feeds(self.store, lambda: NOW + 60, page)
        self.assertEqual(len(asked), before, "ids are looked up once and kept")

    def test_culture_feeds_are_on_by_default(self):
        names = {f[0] for f in news.FEEDS}
        for outlet in ["The Shade Room", "TMZ", "Billboard", "XXL", "Complex", "HotNewHipHop", "Reddit", "Yahoo Finance"]:
            self.assertIn(outlet, names)
        self.assertEqual(news.FRESH_SECONDS, 15 * 60)
        self.agent.helpers.ensure_system()
        reader = next(r for r in self.store.all("helper", 60) if r.get("kind") == "news")
        self.assertEqual(reader["every"], "every_15m")


QUOTES = {
    "https://stooq.com/q/l/?s=tsla.us&f=sd2t2ohlcv&h&e=csv": b"Symbol,Date,Time,Open,High,Low,Close,Volume\nTSLA.US,2026-10-27,21:00:00,247,253,246,255.00,1000\n",
    "https://stooq.com/q/l/?s=zzzz.us&f=sd2t2ohlcv&h&e=csv": b"Symbol,Date,Time,Open,High,Low,Close,Volume\nZZZZ.US,N/D,N/D,N/D,N/D,N/D,N/D,N/D\n",
    "https://api.exchange.coinbase.com/products/BTC-USD/stats": json.dumps({"open": "100000", "last": "97000.50", "high": "1", "low": "1"}).encode(),
}


def fake(url):
    if url.startswith("https://stooq.com/q/d/l/?s=tsla.us"):
        return b"Date,Open,High,Low,Close,Volume\n2026-10-23,240,245,239,244.00,1\n2026-10-24,244,251,243,250.00,1\n2026-10-27,247,253,246,255.00,1\n"
    if url.startswith("https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSLA"):
        return (b"<rss><channel><item><title>Tesla deliveries beat estimates</title><link>https://finance.yahoo.com/x</link>"
                b"<pubDate>Mon, 27 Oct 2026 10:00:00 GMT</pubDate></item></channel></rss>")
    if url in QUOTES:
        return QUOTES[url]
    raise OSError("offline")


class MarketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.agent = Agent(store=self.store, use_model=False, now=lambda: NOW)
        self.agent.market_fetch = fake
        self.agent._market_today = "2026-10-27"

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_a_stock_price_is_read_live_with_the_days_move_and_news(self):
        out = self.agent.chat("how's tesla stock doing")
        self.assertIn("Tesla (TSLA) is at $255.00, up 2.00% today.", out["text"])
        self.assertIn("Tesla deliveries beat estimates", out["text"])
        self.assertEqual(out["results"][0]["source"], "Stooq")

    def test_crypto_moves_over_24_hours(self):
        self.assertIn("Bitcoin is at $97,000.50, down 3.00% in the last 24 hours.", self.agent.chat("what's bitcoin at?")["text"])

    def test_no_quote_means_no_number(self):
        out = self.agent.chat("what's $ZZZZ stock at")
        self.assertIn("couldn't get a live price", out["text"])
        self.assertNotRegex(out["text"], r"\$\d")
        self.agent.market_fetch = lambda url: (_ for _ in ()).throw(OSError("offline"))
        self.assertIn("won't guess a number", self.agent.chat("how's the market today")["text"])

    def test_what_counts_as_a_price_question(self):
        self.assertTrue(markets.wants("should i buy apple stock"))
        self.assertTrue(markets.wants("price of $NVDA"))
        self.assertFalse(markets.wants("i went to the farmers market"))
        self.assertFalse(markets.wants("how's apple"))  # could be the fruit or the company: the brain takes it


if __name__ == "__main__":
    unittest.main()
