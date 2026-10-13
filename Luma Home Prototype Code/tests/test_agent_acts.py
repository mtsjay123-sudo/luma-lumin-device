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



class LooseEndsTests(unittest.TestCase):
    """Things an independent check caught: taught tasks taking over chat, chats that stopped saving, news that never saved."""
    def setUp(self):
        import tempfile
        from pathlib import Path
        from luma.agent.runtime import Agent
        from luma.agent.taught import Recorder
        from luma.memory.store import Store
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "db", Path(self.temp.name) / "key")
        self.agent = Agent(store=self.store, use_model=False)
        self.Agent = Agent
        for name in ["coffee", "email", "pay rent now", "pay rent early"]:
            r = Recorder("https://shop.example/")
            r.steps = [{"do": "click", "target": {"tag": "button", "label": name}}]
            self.agent.taught.save(name, r)
        self.ran = []
        self.agent.taught.run = lambda row, cancel_event=None: self.ran.append(row["name"]) or {"text": "ran"}

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_ordinary_questions_never_start_a_taught_task(self):
        for said in ["do you think coffee is healthy?", "do I have any new email?", "do my homework", "run", "do it"]:
            self.agent.chat(said)
        self.assertEqual(self.ran, [])

    def test_the_named_task_is_the_one_that_runs(self):
        self.agent.enable("browser", True)
        self.agent._browser_available = lambda: True
        self.agent.chat("run pay rent now")
        self.agent.chat("coffee")
        self.agent.chat("redo my email again")
        self.assertEqual(self.ran, ["pay rent now", "coffee", "email"])

    def test_a_chat_with_an_order_number_keeps_saving(self):
        # A reply that quoted an order number from an email or a store.
        self.agent.transcripts["main"].append({"role": "luma", "text": "Your order 112-1234567-1234567 shipped today.", "at": self.agent.clock()})
        self.agent.chat("yo")
        again = self.Agent(store=self.store, use_model=False)
        texts = [m["text"] for m in again.transcripts["main"]]
        self.assertIn("yo", texts)
        self.assertNotIn("1234567-1234567", str(texts))

    def test_the_main_chat_survives_lots_of_side_chats(self):
        self.agent.chat("yo")
        for _ in range(45):
            self.agent.chat("hi", thread=self.agent.new_thread()["id"])
        again = self.Agent(store=self.store, use_model=False)
        self.assertEqual(again.transcripts["main"][0]["text"], "yo")

    def test_one_bad_headline_never_stops_the_news_from_saving(self):
        from luma.skills import news
        rss = (b"<rss><channel><item><title>Big launch today</title><link>https://x.com/a/status/1846382910456712345</link></item>"
               b"<item><title>Markets close higher</title><link>https://news.example/markets</link></item></channel></rss>")
        result = news.refresh(self.store, self.agent.clock, fetch=lambda url: rss)
        self.assertEqual([i["title"] for i in result["items"]], ["Markets close higher"])
        self.assertEqual(len(news.cached(self.store)["items"]), 1)

    def test_personal_questions_are_not_answered_with_headlines(self):
        from luma.skills import news
        self.store.set_setting("news", {"fetched": self.agent.clock(), "items": [
            {"title": "Judge blocks executive order on tariffs", "url": "https://news.example/order", "source": "Wire", "snippet": "", "published": self.agent.clock()},
            {"title": "Jake Paul announces next fight", "url": "https://news.example/jake", "source": "Wire", "snippet": "", "published": self.agent.clock()}]})
        for said in ["what's the latest with my order?", "any news from Jake?"]:
            self.assertNotEqual(self.agent.chat(said).get("section"), "news")


class MindTests(unittest.TestCase):
    """About you, mood, and thinking it through."""
    def setUp(self):
        import tempfile
        from pathlib import Path
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "db", Path(self.temp.name) / "key")
        self.agent = Agent(store=self.store, use_model=False, now=lambda: 1791900000)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_about_you_is_cleaned_saved_and_becomes_birthday_reminders(self):
        self.agent.set_about({"name": "Xiena", "birthday": "2001-10-14", "home": "Raleigh",
                              "people": [{"name": "Maya", "relation": "girlfriend", "birthday": "03-02"},
                                         {"name": "", "relation": "nobody"}]})
        about = self.agent.about
        self.assertEqual(about["birthday"], "10-14")
        self.assertEqual(about["birth_year"], 2001)
        self.assertEqual(len(about["people"]), 1)
        self.assertEqual(self.agent.profile["name"], "Xiena")
        texts = [m["text"] for m in self.store.all("memory", 50) if m.get("source") == "about_you"]
        self.assertIn("My birthday is October 14", texts)
        self.assertIn("Maya's birthday is March 2", texts)
        with self.assertRaises(ValueError):
            self.agent.set_about({"birthday": "nonsense"})

    def test_about_summary_reaches_the_model_context(self):
        self.agent.set_about({"name": "Sam", "interests": "rock climbing, lo-fi", "home": "Austin"})
        seen = self.agent._mind_context("what should I do this weekend")
        about = next((c for c in seen if c.get("about")), None)
        self.assertIsNotNone(about)
        self.assertIn("rock climbing", about["text"])
        self.assertIn("Austin", about["text"])

    def test_mood_shifts_with_what_they_say(self):
        from luma.agent import mind
        sad = mind.next_mood(None, "honestly today was a really rough day and I feel lonely", 1000)
        self.assertEqual(sad["feeling"], "worried about them")
        glad = mind.next_mood(sad, "wait I got the job!!", 1000 + 10)
        self.assertEqual(glad["feeling"], "so happy for them")

    def test_deep_think_runs_several_passes_then_answers(self):
        calls = []
        def planner(history, memories, tools, mode):
            calls.append(history[-1]["content"][:40])
            return {"type": "reply", "text": f"pass {len(calls)}"}
        from luma.agent.runtime import Agent
        agent = Agent(store=self.store, use_model=True, planner=planner, now=lambda: 1791900000)
        out = agent.chat("should I quit my job? think hard about it")
        self.assertEqual(out["text"], "pass 4")  # 3 thinking passes + 1 answer
        self.assertEqual(out["thinking"], ["Understanding it", "Looking at it three ways", "Checking myself"])
