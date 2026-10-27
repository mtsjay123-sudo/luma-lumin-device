"""Funny like a friend: Luma reads the room first. It jokes back when they're joking, keeps it plain when they're hurting or
serious, tells its own bits on the topic they asked about without repeating itself, learns which kind of funny lands with
them, and never makes a joke out of a tragedy in the news. Small language slips are fixed before anyone sees them."""
import random
import tempfile
import unittest
from pathlib import Path

from luma.agent import humor, humor_bank, polish
from luma.agent.runtime import Agent
from luma.memory.store import Store
from luma.llm.prompts import build_plan_prompt


class ToneTests(unittest.TestCase):
    def test_reading_the_room(self):
        for text, mood in [("i'm dead 😂", "laughing"), ("LMAOOO nah you're wild", "laughing"), ("i'm crying 😭😭", "laughing"),
                           ("bro my boss is tweakin today fr", "playful"), ("my grandma passed away last night", "grief"),
                           ("i've been crying all day", "upset"), ("I feel so overwhelmed with work", "upset"), ("i got laid off today", "upset"),
                           ("be serious, how do I fix my credit", "serious"), ("remind me to call mom at 5", "task"), ("he is dead lol", "grief")]:
            self.assertEqual(humor.read_tone(text)["mood"], mood, text)

    def test_the_ways_people_say_it(self):
        for text, mood in [("my grandma passed this morning", "grief"), ("she passed last night", "grief"), ("had to put my dog down", "grief"),
                           ("we lost grandma today", "grief"), ("my brother passed the bar", "neutral"), ("she passed her test", "neutral"),
                           ("ugh i'm so tired of this job", "venting"), ("my boss keeps scheduling meetings at 5", "venting"),
                           ("this job is killing me lmao", "laughing"), ("i passed my exam!!", "playful")]:
            self.assertEqual(humor.read_tone(text)["mood"], mood, text)
        self.assertEqual(humor.level({"mood": "venting"}), "none", "on their side first")
        self.assertIn("on their side", humor.turn_note("ugh i'm so tired of this job"))
        self.assertEqual(humor.feedback("lmaooo ok that one was good", {"text": "x"}), "+")
        self.assertEqual(humor.feedback("good one", {"text": "x"}), "+")

    def test_a_loss_a_minute_ago_still_counts(self):
        loss = ["my grandma passed this morning"]
        self.assertIn("stay gentle", humor.turn_note("idk what to do with myself today bro", recent=loss))
        self.assertIn("stay gentle", humor.turn_note("what should I eat", recent=loss))
        memory = humor.turn_note("hahaha she used to cheat at spades every single time", recent=loss)
        self.assertIn("One light touch at most", memory, "laughing about a memory: laugh with them, gently")
        self.assertNotIn("be funny back", memory)
        self.assertIn("be funny back", humor.turn_note("hahaha she used to cheat at spades every single time", recent=["what should I eat"]))

    def test_how_much_humor(self):
        self.assertEqual(humor.level({"mood": "laughing"}), "full")
        self.assertEqual(humor.level({"mood": "playful"}, dial=1), "light")
        for mood in ("grief", "upset", "serious"):
            self.assertEqual(humor.level({"mood": mood}, dial=3), "none", "no dial setting makes a hard moment funny")
        self.assertEqual(humor.level({"mood": "task"}), "none", "getting something done comes first")
        self.assertEqual(humor.level({"mood": "laughing"}, dial=0), "none")

    def test_the_note_for_the_brain(self):
        rng = random.Random(1)
        sad = humor.turn_note("my dad passed away this morning", rng=rng)
        self.assertIn("No jokes", sad)
        playful = humor.turn_note("lmao my boss really scheduled a meeting at 4:59 on a friday", rng=rng)
        self.assertIn("be funny back", playful)
        self.assertIn("never pass off a joke as something a real comedian said", playful)
        self.assertEqual(humor.turn_note("remind me to call the dentist", rng=rng), "")
        kids = humor.turn_note("lol my dog ate my homework", mode="kids", rng=rng)
        self.assertNotIn("roast", kids.split("\n", 1)[1] if "\n" in kids else "")


class BankTests(unittest.TestCase):
    def test_five_hundred_of_our_own(self):
        clean = [b for b in humor_bank.all_bits() if not b[3]]
        self.assertGreaterEqual(len(clean), 500)
        texts = [b[2] for b in humor_bank.all_bits()]
        self.assertEqual(len(texts), len(set(texts)), "no bit twice")
        self.assertEqual(set(humor_bank.KEYWORDS), set(humor_bank.BANK))
        for topic, style, text, grown in humor_bank.all_bits():
            self.assertNotRegex(text.lower(), r"\bn[i1]gg|\bf[a@]g|\bretard", "never a slur, not even in a grown bit")

    def test_never_joke_about_the_heavy_news(self):
        heavy = ["15 killed in shooting downtown", "Hurricane forces thousands to evacuate", "Actor dies at 54", "Senate passes budget bill",
                 "Company announces 2,000 layoffs", "Teen diagnosed with rare cancer"]
        for title in heavy:
            self.assertIsNotNone(humor.sensitive(title), title)
        for title in ["Jay-Z to perform at Super Bowl halftime show", "New iPhone drops with one less button", "Dog learns to open the fridge"]:
            self.assertIsNone(humor.sensitive(title), title)
        items = [{"title": t, "source": "X", "topic": "top"} for t in heavy]
        self.assertIsNone(humor.news_bit(items))


class AgentHumorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_a_joke_about_the_topic_they_asked_and_never_the_same_one_twice(self):
        work = {t for _, t in humor_bank.BANK["work"]}
        seen = set()
        for _ in range(25):
            line = self.agent.chat("tell me a joke about work")["text"]
            self.assertIn(line, work)
            seen.add(line)
        self.assertEqual(len(seen), 25, "all 25 work bits before any repeats")

    def test_dad_jokes_are_still_the_classics(self):
        from luma.agent import jokes
        self.assertIn(self.agent.chat("tell me a dad joke")["text"], jokes.JOKES)
        self.assertIn(self.agent.chat("another one")["text"], jokes.JOKES)

    def test_it_learns_what_lands(self):
        self.agent.chat("tell me a joke about my mom")
        bit = self.agent.last_bit
        self.agent.chat("lmaooo")
        taste = self.store.setting("humor_taste")
        self.assertEqual(taste["likes"][bit["style"]], 1)
        self.agent.chat("make me laugh")
        self.assertIn("corny", self.agent.chat("that's corny")["text"])
        self.assertEqual(self.store.setting("humor_taste")["dial"], 1, "a joke that didn't land turns it down")
        self.assertEqual(self.agent.chat("be funnier")["text"], "Bet, I'll bring the jokes more.")
        self.assertEqual(self.store.setting("humor_taste")["dial"], 2)
        self.agent.chat("less jokes")
        self.agent.chat("less jokes")
        self.assertEqual(self.store.setting("humor_taste")["dial"], 0)

    def test_the_news_but_only_the_light_stuff(self):
        self.store.set_setting("news", {"fetched": 0, "items": [
            {"title": "15 killed in shooting downtown", "source": "AP", "url": "https://a.com/1", "topic": "top"},
            {"title": "Jay-Z to perform at Super Bowl halftime show", "source": "BBC", "url": "https://a.com/2", "topic": "culture"}]})
        out = self.agent.chat("what's funny in the news?")
        self.assertIn("Jay-Z to perform at Super Bowl halftime show (BBC)", out["text"])
        self.assertNotIn("shooting", out["text"])
        self.assertEqual(out["results"][0]["source"], "BBC")
        self.assertIn("not making fun of the heavy stuff", self.agent.chat("what's funny in the news?")["text"], "that was the only light one")

    def test_with_the_brain_down_it_still_reads_the_room(self):
        self.assertIn("I'm so sorry", self.agent.chat("my grandma passed this morning")["text"])
        vent = self.agent.chat("ugh my boss keeps scheduling meetings at 5")
        self.assertNotIn("calendar", vent["text"].lower(), "venting isn't a calendar question")
        self.assertRegex(vent["text"], r"happened|going on")
        story = self.agent.chat("i'm dead 😂 my boss said reply all to the whole company")
        self.assertFalse(story.get("did_you_mean"), "a story they're laughing about isn't a text to send")
        self.agent.chat("tell me a joke about my mom")
        self.assertIn(self.agent.chat("lmaooo ok that one was good")["text"], self.agent.LAUGHED_BACK)
        self.assertNotIn(self.agent.chat("lol my cousin tried to parallel park for twenty whole minutes")["text"], self.agent.LAUGHED_BACK,
                         "a new story isn't a reaction to the last joke")
        self.agent.chat("tell me a joke about work")
        self.agent.chat("my dog passed away last night")
        self.assertNotIn(self.agent.chat("lol")["text"], self.agent.LAUGHED_BACK, "no 'glad that landed' right after a loss")

    def test_web_trouble_is_said_plainly(self):
        self.agent._browser_available = lambda: True
        class Broken:
            def open(self, url):
                raise RuntimeError("Page.goto: net::ERR_TUNNEL_CONNECTION_FAILED at https://html.duckduckgo.com/html/?q=x")
        self.agent._browser = Broken()
        with self.assertRaises(Exception) as caught:
            self.agent.search_web("how do I fix my credit")
        self.assertNotIn("ERR_", str(caught.exception))
        self.assertIn("Wi-Fi", str(caught.exception))

    def test_the_brain_hears_the_room(self):
        context = self.agent._mind_context("lmao my cousin brought store-bought potato salad to the cookout")
        note = next(m["text"] for m in context if m.get("humor"))
        self.assertIn("be funny back", note)
        prompt = build_plan_prompt(context, {}, "friend", {})
        self.assertIn("be funny back", prompt, "the humor note gets its own room in the prompt, not cut off with the mood")
        sad = self.agent._mind_context("my grandma passed away this morning")
        self.assertIn("No jokes", next(m["text"] for m in sad if m.get("humor")))


class PolishTests(unittest.TestCase):
    def test_safe_fixes_only(self):
        self.assertEqual(polish.tidy("I think the the black one is better ."), "I think the black one is better.")
        self.assertEqual(polish.tidy("That was a amazing show and an great time"), "That was an amazing show and a great time")
        self.assertEqual(polish.tidy("It took a hour"), "It took an hour")
        for kept in ["a university, a one-time thing, a European trip, an MBA, an hour", "no no no, I had had enough", "wait.. what",
                     "Okay... so", "lol i cant", "see https://a.com/the the", "`a apple`", "!!", "huh??"]:
            self.assertEqual(polish.tidy(kept), kept)
        self.assertEqual(polish.slips("the the cat ,"), 2)


if __name__ == "__main__":
    unittest.main()
