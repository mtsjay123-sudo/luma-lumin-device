"""What the real-Mac lab (run 127) caught, fixed: a stock-market answer thrown away as "garbled" because it was mostly numbers;
"you watch the game?" and "his verse was the best part fr" answered as if Luma knew which; SZA lyrics quoted from memory when the
lookup came back empty; "how much is a PS5" answered with a PS5 game; "credit score" sent to a sports-scores lookup; index and
store pages read as stories."""
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.llm import inference
from luma.memory.store import Store
from luma.skills import news, shopping


class LabRun127Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def agent(self, reply="Pay on time and keep balances low."):
        agent = Agent(store=self.store, use_model=True, planner=lambda *a, **k: {"type": "reply", "text": reply})
        agent.propose = (lambda orig: (lambda name, args, *x, **k: {"results": [], "summary": ""} if name == "web.search" else orig(name, args, *x, **k)))(agent.propose)
        return agent

    def test_numbers_are_words(self):
        for line in ["the S&P 500 is at 7,727.85, up 0.67% today.", "7:30", "AT&T is up 2% today"]:
            self.assertFalse(inference.garbled(line), line)
        for junk in ["+A57#8++&B", "#8++&B+,#$C8", "A57B8+C9#&"]:
            self.assertTrue(inference.garbled(junk), junk)
        agent = self.agent()
        agent.market_fetch = lambda url: (b'{"chart":{"result":[{"meta":{"regularMarketPrice":7727.85,"chartPreviousClose":7676.4,"currency":"USD"},'
                                          b'"timestamp":[1793116800],"indicators":{"quote":[{"close":[7727.85]}]}}]}}')
        out = agent.chat("how's the stock market doing today?")
        self.assertNotIn("glitched", out["text"])

    def test_which_game_whose_verse(self):
        agent = self.agent("Yeah that game was crazy, the refs were blind.")
        self.assertIn("Which game", agent.chat("you watch the game?")["text"])
        self.assertIn("score", agent.chat("u catch the game last night")["text"])
        self.assertRegex(self.agent("That verse was fire, especially the second half.").chat("his verse was the best part fr")["text"], r"(?i)whose verse")

    def test_lyrics_are_never_quoted_from_memory(self):
        agent = self.agent('Here\'s one from Ctrl: "I\'m not the one who made you cry, I just see you cry."')
        for ask in ["quote me some sza lyrics", "sing me the chorus of kill bill", "what's the first line of the lyrics to bohemian rhapsody"]:
            self.assertIn("rather not quote lyrics from memory", agent.chat(ask)["text"], ask)
        from luma.agent.runtime import QUOTE_ASK
        for freestyle in ["give me some bars", "spit me some new bars", "tell me your verse", "what do you think of the lyrics"]:
            self.assertFalse(QUOTE_ASK.search(freestyle), freestyle)

    def test_a_ps5_is_the_console(self):
        self.assertLess(shopping.relevance("ps5", "Ghost of Yotei PS5 ESRB Rating: Mature | by PlayStation"), 0.6)
        self.assertLess(shopping.relevance("ps5", "DualSense Wireless Controller for PS5"), 0.6)
        self.assertEqual(shopping.relevance("ps5", "PlayStation 5 Console (Slim)"), 1.0)
        self.assertEqual(shopping.relevance("ps5 controller", "DualSense Wireless Controller for PS5"), 1.0)
        self.assertEqual(shopping.relevance("mario kart switch", "Mario Kart World - Nintendo Switch 2 game"), 1.0)

    def test_credit_score_is_not_a_game_score(self):
        looked = []
        agent = self.agent()
        agent.look_it_up = lambda text, *a, **k: looked.append(text) or {"text": "", "results": []}
        out = agent.chat("be serious, how do i fix my credit score")
        self.assertEqual(looked, [])
        self.assertIn("Pay on time", out["text"])
        from luma.agent.runtime import LIVE_INFO
        self.assertTrue(LIVE_INFO.search("what's the score of the knicks game"))

    def test_index_and_store_pages_arent_stories(self):
        for page in ["Lemuel Plummer Zeus Archives - The Shade Room", "SSSTUFFF / Layered Shirt Crewneck / Sweatshirts - Complex",
                     "Billboard's Music Industry Events Calendar"]:
            self.assertTrue(news.JUNK_TITLE.search(page), page)
        self.assertFalse(news.JUNK_TITLE.search("Drake / J. Cole collab confirmed"))


class LabRun129Tests(unittest.TestCase):
    """Run 129: the virtual graphics chip went bad partway through and "BBEC&7%.G" reached a person; thumbstick grips "for
    PlayStation 5" were the cheapest PS5; Wikipedia's list wasn't out yet late in the day; a person's name alone read as a story."""

    def test_one_word_garbage_is_caught_and_real_one_word_answers_arent(self):
        self.assertTrue(inference.garbled("BBEC&7%.G"))
        for fine in ["R&B", "AT&T", "#tbt", "4:59pm", "lol!!", "Bet.", "self-care", "$5", "https://example.com/a"]:
            self.assertFalse(inference.garbled(fine), fine)

    def test_made_for_a_ps5_isnt_a_ps5(self):
        self.assertLess(shopping.relevance("ps5", "KontrolFreekFPS Freek Galaxy Black for PlayStation 4 (PS4) and PlayStation 5 (PS5)"), 0.6)
        self.assertEqual(shopping.relevance("ps5", "Sony PS5 Pro 2TB"), 1.0)

    def test_wikipedia_today_and_yesterday(self):
        urls = [u for name, u, kind in news.extras(1793116800.0) if kind == "lookedup"]
        self.assertEqual([u[-10:] for u in urls], ["2026/10/27", "2026/10/26"])

    def test_a_name_alone_isnt_a_story(self):
        rss = (b'<rss><channel><item><title>Brandon Garrett - HotNewHipHop</title><link>https://news.google.com/a</link></item>'
               b'<item><title>Drake lawsuit over Janice STFU dismissed - HotNewHipHop</title><link>https://news.google.com/b</link></item></channel></rss>')
        store = Store(Path(tempfile.mkdtemp()) / "s.db", Path(tempfile.mkdtemp()) / "k")
        try:
            from unittest import mock
            with mock.patch.object(news, "feeds", lambda: [("Google News", "https://news.google.com/rss/search?q=site:hotnewhiphop.com", "culture")]):
                got = news.refresh(store, lambda: 1793116800.0, fetch=lambda url: rss)
            self.assertEqual([i["title"] for i in got["items"]], ["Drake lawsuit over Janice STFU dismissed"])
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
