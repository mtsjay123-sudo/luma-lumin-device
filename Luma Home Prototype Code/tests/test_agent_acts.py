"""Luma acts instead of shrugging: the web is on out of the box, "try now" redoes the last
request, and a model that says it has no real-time access gets overruled by a real look-up."""
import json
import tempfile
import unittest
from pathlib import Path

from test_dots_features import FakeBrowser, LISTINGS, STORES
from luma.agent.runtime import Agent
from luma.integrations.providers import Providers
from luma.memory.store import Store


class SearchBrowser(FakeBrowser):
    def search_results(self):
        return [{"title": "Raleigh weather today: sunny, 72F", "url": "https://weather.example/raleigh", "snippet": "Sunny with a high of 72."}]


def shrugging_planner(messages, context, allowed, mode):
    """A small model on a bad day: it claims it can't see anything live."""
    if "[What your" in messages[-1]["content"]:
        return {"type": "reply", "text": "It's sunny and 72 in Raleigh today."}
    return {"type": "reply", "text": "I don't have access to real-time data, so I can't check that for you."}


class AgentActsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "state.db", root / "state.key")
        self.agent = Agent(store=self.store, providers=Providers(env={"LUMA_SHOP_STORES_JSON": json.dumps(STORES)}),
                           use_model=True, planner=shrugging_planner)
        self.agent._browser = SearchBrowser(LISTINGS)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_reading_the_web_is_on_out_of_the_box(self):
        self.assertTrue(self.agent.integration_on("browser"))
        self.assertTrue(self.agent.integration_on("web_search"))
        self.assertFalse(self.agent.integration_on("mail"))  # anything personal stays opt-in
        self.agent.enable("browser", False)
        self.assertFalse(self.agent.integration_on("browser"))

    def test_shopping_works_without_turning_anything_on(self):
        result = self.agent.chat("find me the cheapest AirPods Pro 2")
        self.assertTrue(result["offers"])
        self.assertEqual(result["offers"][0]["price"], min(o["price"] for o in result["offers"]))

    def test_try_now_does_the_last_thing_again(self):
        self.agent.enable("browser", False)
        first = self.agent.chat("find me the cheapest AirPods Pro 2")
        self.assertIn("browser", first["text"])
        self.agent.enable("browser", True)
        again = self.agent.chat("try now")
        self.assertTrue(again["offers"])

    def test_a_shrug_about_a_price_becomes_a_price_check(self):
        result = self.agent.chat("airpods pro 2, what do they cost these days")
        self.assertTrue(result["offers"])
        self.assertNotIn("real-time", result.get("text", ""))

    def test_a_shrug_about_anything_live_becomes_a_web_search(self):
        result = self.agent.chat("is it going to rain in raleigh")
        self.assertEqual(result["results"][0]["url"], "https://weather.example/raleigh")
        self.assertIn("sunny", result["text"].lower())
        self.assertNotIn("real-time", result["text"])

    def test_live_questions_go_to_the_web_before_the_model_can_guess(self):
        self.agent.planner = lambda messages, context, allowed, mode: (
            {"type": "reply", "text": "It's 70% likely to rain tomorrow afternoon."} if "[What your" in messages[-1]["content"]
            else {"type": "reply", "text": "Just checked: light rain in the morning."})
        result = self.agent.chat("is it going to rain in raleigh tomorrow")
        self.assertEqual(result["results"][0]["url"], "https://weather.example/raleigh")
        self.assertIn("70%", result["text"])

    def test_a_claim_to_have_checked_without_checking_gets_a_real_look(self):
        self.agent.planner = lambda messages, context, allowed, mode: (
            {"type": "reply", "text": "Sunny and 72."} if "[What your" in messages[-1]["content"]
            else {"type": "reply", "text": "I just checked and the museum is free on Sundays."})
        result = self.agent.chat("is the art museum free on sundays")
        self.assertTrue(result["results"])

    def test_how_much_right_now_compares_stores(self):
        result = self.agent.chat("how much are airpods pro 2 right now")
        self.assertTrue(result["offers"])
        self.assertNotIn("offers", self.agent.chat("how much is 20% of 80"))

    def test_a_signed_out_feed_asks_to_sign_in_instead_of_summarizing_nothing(self):
        class SignedOut(SearchBrowser):
            def open(self, url):
                super().open(url)
                return {"url": "https://www.instagram.com/accounts/login/", "title": "Instagram",
                        "text": "Phone number, username, or email  Password  Log in  Forgot password?", "elements": []}
            def show_for_sign_in(self, url):
                raise AssertionError("signing in happens inside Luma's window, not a pop-up")
        self.agent._browser = SignedOut(LISTINGS)
        result = self.agent.chat("catch me up on instagram")
        self.assertIn("isn't signed in to Instagram", result["text"])
        self.assertEqual((result["sign_in"], result["url"]), ("Instagram", "https://www.instagram.com/"))
        self.assertNotIn("summar", result["text"].lower())
        self.assertEqual(self.agent.pending_handoff["retry"], "catch me up on instagram")

    def test_rules_still_win(self):
        self.agent.rules.set("browse", "block")
        result = self.agent.chat("is it going to rain in raleigh")
        self.assertNotIn("results", result)


if __name__ == "__main__":
    unittest.main()


class GreetingWithoutModelTests(unittest.TestCase):
    def test_yo_gets_a_friendly_hello_not_a_status_message(self):
        import tempfile
        from pathlib import Path
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "db", Path(folder) / "key")
            agent = Agent(store=store, use_model=False)
            try:
                for hello in ["yo", "what's good", "hey luma!"]:
                    reply = agent.chat(hello)["text"]
                    self.assertIn("What can I take off your plate?", reply)
                    self.assertNotIn("Model conversation is disabled", reply)
            finally:
                store.close()


class ChatsAreKeptTests(unittest.TestCase):
    def test_side_chats_and_the_main_chat_are_still_there_after_a_restart(self):
        import tempfile
        from pathlib import Path
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "db", Path(folder) / "key")
            try:
                first = Agent(store=store, use_model=False)
                first.chat("yo")
                side = first.new_thread()
                first.chat("ideas for a picnic on saturday", thread=side["id"])
                again = Agent(store=store, use_model=False)
                listed = {t["id"]: t for t in again.thread_list()}
                self.assertEqual(listed[side["id"]]["title"], "ideas for a picnic on saturday")
                self.assertEqual(listed[side["id"]]["messages"], 2)
                self.assertEqual(again.transcripts["main"][0]["text"], "yo")
                self.assertEqual(again.history[0], {"role": "user", "content": "yo"})
                again.delete_thread(side["id"])
                self.assertNotIn(side["id"], {t["id"] for t in Agent(store=store, use_model=False).thread_list()})
            finally:
                store.close()


class NewsTests(unittest.TestCase):
    """Luma reads free public news feeds so a model trained earlier still knows what happened today."""
    @classmethod
    def setUpClass(cls):
        import functools, http.server, threading
        from pathlib import Path
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(Path(__file__).parent / "fixtures" / "web"))
        handler.log_message = lambda *a: None
        cls.site = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.site.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.site.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.site.shutdown()

    def setUp(self):
        import json, os, tempfile
        from pathlib import Path
        from unittest import mock
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "db", Path(self.temp.name) / "key")
        feeds = json.dumps([["Test Wire", self.base + "/news-rss.xml"], ["Tech Daily", self.base + "/news-atom.xml"], ["Broken", self.base + "/nope.xml"]])
        self.env = mock.patch.dict(os.environ, {"LUMA_NEWS_FEEDS": feeds})
        self.env.start()
        self.agent = Agent(store=self.store, use_model=False, now=lambda: 1791900000)  # Tue 13 Oct 2026
        self.agent.news_allow_local = True

    def tearDown(self):
        self.env.stop()
        self.store.close()
        self.temp.cleanup()

    def test_reads_every_feed_drops_old_and_duplicate_stories(self):
        result = self.agent.read_news(force=True)
        titles = [i["title"] for i in result["items"]]
        self.assertEqual(len(titles), 3)
        self.assertEqual(titles.count("Fed holds interest rates steady, signals one more cut this year"), 1)
        self.assertNotIn("Old story from last month", titles)
        self.assertEqual(result["failed"], ["Broken"])
        self.assertEqual(result["items"][0]["snippet"] if result["items"][0]["source"] == "Test Wire" else "", "The Federal Reserve left rates unchanged on Tuesday.")

    def test_news_questions_are_answered_from_todays_headlines_with_sources(self):
        reply = self.agent.chat("what's the news today")
        self.assertIn("Fed holds interest rates steady", reply["text"])
        self.assertEqual(reply["section"], "news")
        self.assertTrue(all(r["url"].startswith("https://") for r in reply["results"]))
        topic = self.agent.chat("what's the latest on starship")
        self.assertEqual([r["url"] for r in topic["results"]], ["https://news.example/starship"])

    def test_matching_headlines_reach_the_model_as_background(self):
        self.agent.read_news(force=True)
        seen = self.agent._news_context("should I buy the new M6 MacBook Pro")
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0]["news"])
        self.assertIn("Tech Daily: Apple announces M6 MacBook Pro", seen[0]["text"])
        self.assertEqual(self.agent._news_context("help me write a poem"), [])
