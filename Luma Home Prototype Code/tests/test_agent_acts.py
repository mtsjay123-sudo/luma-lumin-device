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
                self.shown = url
                return {"url": url}
        self.agent._browser = SignedOut(LISTINGS)
        result = self.agent.chat("catch me up on instagram")
        self.assertIn("isn't signed in to Instagram", result["text"])
        self.assertEqual(self.agent._browser.shown, "https://www.instagram.com/")
        self.assertNotIn("summar", result["text"].lower())
        self.assertEqual(self.agent.pending_handoff["retry"], "catch me up on instagram")

    def test_rules_still_win(self):
        self.agent.rules.set("browse", "block")
        result = self.agent.chat("is it going to rain in raleigh")
        self.assertNotIn("results", result)


if __name__ == "__main__":
    unittest.main()
