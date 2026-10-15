"""Luma understands people the way they really talk: slang, typos, getting cut off, getting annoyed,
needing a hand step by step. The understanding model is trained on generated scenarios and checked
on messages written by hand that the generator never produced."""
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from luma.agent import scenarios, understanding
from luma.agent.runtime import Agent
from luma.memory.store import Store
from real_talk import REAL_TALK, REAL_TALK_FRESH

NOW = 1791900000.0  # Tue 13 Oct 2026, 10:00 in New York


def accuracy(pairs):
    return sum(understanding.guess(t, 1)[0][0] == i for t, i in pairs) / len(pairs)


class ModelTests(unittest.TestCase):
    def test_it_ships_and_reads_meaning_not_templates(self):
        self.assertTrue(understanding.MODEL_PATH.exists())
        self.assertGreaterEqual(accuracy(REAL_TALK), 0.95)
        self.assertGreaterEqual(accuracy(REAL_TALK_FRESH), 0.9)

    def test_generated_scenarios_held_out(self):
        pairs = list(scenarios.generate(1500, seed=909))
        self.assertGreaterEqual(accuracy(pairs), 0.97)

    def test_every_intent_has_somewhere_to_go(self):
        for name, spec in scenarios.INTENTS.items():
            if name == "chat":
                continue
            self.assertTrue(spec.get("label"), name)
            self.assertTrue(spec.get("say") or spec.get("walk") or spec.get("action") or (spec.get("ask") and spec.get("prefix")), name)
            if spec.get("walk"):
                self.assertIn(spec["walk"], understanding.WALKS)

    def test_billions_of_ways_to_say_it(self):
        base, with_slang = scenarios.count()
        self.assertGreater(base, 500_000_000)
        self.assertGreater(with_slang, base)

    def test_slang_and_typos(self):
        self.assertEqual(understanding.normalize("Yo can u remind me abt da dentist tmrw pleaseee"), "yo can you remind me about the dentist tomorrow please")
        self.assertEqual(understanding.respell("mak a podcst abt space"), "make a podcast about space")
        self.assertEqual(understanding.respell("txt kayla im late"), "text kayla i'm late")  # names stay names


class MomentsTests(unittest.TestCase):
    def test_cut_off(self):
        self.assertIn("Remind you to what?", understanding.cut_off("remind me to"))
        self.assertIn("What should I tell them?", understanding.cut_off("can you text my"))
        self.assertIn("Keep going", understanding.cut_off("I was gonna say..."))
        for whole in ["who should I send it to", "tell me a joke", "I love her", "turn it on", "just because", "what would you like", "Okay."]:
            self.assertIsNone(understanding.cut_off(whole), whole)

    def test_frustration(self):
        self.assertEqual(understanding.frustration("that's not what I said")[:2], (1, True))
        self.assertEqual(understanding.frustration("wtf")[0], 2)
        self.assertEqual(understanding.frustration("i passed my exam!!")[0], 0)
        self.assertEqual(understanding.frustration("my wifi is not working")[0], 0)
        level, aimed, rest = understanding.frustration("you're useless remind me at 5 not 6")
        self.assertTrue(aimed)
        self.assertEqual(rest, "remind me at 5 not 6")
        self.assertFalse(understanding.frustration("ugh today sucked")[1])

    def test_picking_an_option(self):
        options = ["Set a reminder", "Text someone", "Look it up online"]
        self.assertEqual(understanding.pick("the reminder one", options), 0)
        self.assertEqual(understanding.pick("the second one", options), 1)
        self.assertEqual(understanding.pick("last one", options), 2)
        self.assertEqual(understanding.pick("yeah", options), 0)
        self.assertEqual(understanding.pick("nah neither", options), "none")
        self.assertIsNone(understanding.pick("what's the weather like", options))


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.now = NOW
        self.agent = Agent(store=self.store, use_model=False, now=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def say(self, text):
        self.now += 5
        return self.agent.chat(text)

    TORN = "mom stuff at 5"
    real_guess = staticmethod(understanding.guess)

    def torn(self):
        """The model reads TORN as torn three ways, whatever the latest training run thinks."""
        real = self.real_guess
        return mock.patch.object(understanding, "guess", side_effect=lambda t, k=4: [("calendar", 0.38), ("remind", 0.34), ("text", 0.2), ("chat", 0.08)][:k]
                                 if understanding.normalize(t) == self.TORN else real(t, k))

    def tasks(self):
        return [t["title"] for t in self.store.all("task", 20)]

    def test_reminders_however_theyre_said(self):
        self.assertIn("call mom at 5 PM", self.say("rmd me to call mom at 5pm")["text"])
        self.assertIn("about the trash tomorrow at", self.say("dont let me forget the trash tmrw")["text"])
        self.assertIn("buy cat food", self.say("i need to remember to buy cat food tmrw")["text"])
        self.assertIn("Call mom", self.tasks())

    def test_cut_off_then_finish(self):
        reply = self.say("remind me to")
        self.assertTrue(reply.get("cut_off"))
        self.assertIn("call the dentist at 3 PM", self.say("call the dentist at 3pm")["text"])

    def test_asks_when_a_detail_is_missing_and_ok_isnt_an_answer(self):
        self.assertIn("When should I remind you to water the plants", self.say("remind me to water the plants")["text"])
        self.assertIn("Take your time", self.say("ok")["text"])
        self.assertIn("water the plants tomorrow at 9 AM", self.say("tomorrow at 9am")["text"])

    def test_did_you_mean_then_pick(self):
        with self.torn():
            reply = self.say(self.TORN)
            self.assertTrue(reply.get("did_you_mean"))
            self.assertEqual(reply["choices"], ["Check your calendar", "Set a reminder", "Text someone", "Something else"])
            self.assertIn("Did you mean check your calendar, set a reminder, or text someone?", reply["text"])
            asked = self.say("the reminder one")
        self.assertIn("remind you", asked["text"])
        self.assertIn("leave for the airport at 5 PM", self.say("leave for the airport at 5pm")["text"])

    def test_none_of_those(self):
        with self.torn():
            self.say(self.TORN)
            self.assertIn("not those", self.say("nah neither")["text"])

    def test_new_request_isnt_taken_as_an_answer(self):
        with self.torn():
            self.say(self.TORN)
            self.say("set a reminder")
        reply = self.say("can you open my goals")
        self.assertEqual(reply.get("open"), "goals")

    def test_sale_alerts_start_a_watch(self):
        reply = self.say("lemme know if airpods go on sale")
        self.assertEqual(reply["helper"]["kind"], "price_watch")
        self.assertIn("under $400", self.say("tell me when the ps5 drops below 400")["text"])

    def test_messy_words_still_land(self):
        self.assertEqual(self.say("take me 2 my goalz").get("open"), "goals")
        self.assertEqual(self.say("opne my libary").get("open"), "library")

    def test_frustration_after_a_wrong_move(self):
        self.say("throw on some drake")
        reply = self.say("that's not what i said")
        self.assertTrue(reply.get("calm"))
        self.assertTrue(reply["text"].startswith(("Sorry", "My bad", "my bad")))
        self.assertNotIn("Play music", reply.get("choices", []))  # it did that already
        context = self.agent._mind_context("hi")
        self.assertTrue(any("frustrated" in m["text"] for m in context))

    def test_venting_isnt_blamed_on_luma(self):
        reply = self.say("ugh today sucked")
        self.assertFalse(reply.get("calm"))

    def test_step_by_step(self):
        first = self.say("how do I get you in chrome")
        self.assertEqual(first["walk"]["step"], 1)
        self.assertEqual(first["peek"], "apps")
        self.assertEqual(self.say("done, next")["walk"]["step"], 2)
        stuck = self.say("i'm stuck")
        self.assertIn("Chrome logo", stuck["text"])
        self.assertEqual(stuck["walk"]["step"], 2)
        self.assertEqual(self.say("got it, next")["walk"]["step"], 3)
        self.assertIn("stopping", self.say("stop")["text"])

    def test_let_me_know_isnt_a_text(self):
        reply = self.say("let me know if the store has it")
        self.assertNotIn("number", reply.get("text", ""))

    def test_facts_caught_without_the_brain(self):
        self.assertIn("You hate mushrooms", self.say("I hate mushrooms")["text"])

    def test_the_brain_gets_the_read(self):
        context = self.agent._mind_context("rmd me to call grandma at 6")
        self.assertTrue(any(m.get("guess") and "set a reminder" in m["text"] for m in context))


class EvalHarnessTests(unittest.TestCase):
    """Run generated scenarios through a real Luma: nothing crashes, and requests rarely fall through to "I can't"."""
    OFFLINE = [i for i in scenarios.INTENTS if i not in {"shop", "search", "news", "news_topic", "weather", "podcast", "open_site", "music", "chat", "goal", "briefing", "calendar"}]

    def test_scenarios_through_luma(self):
        temp = tempfile.TemporaryDirectory()
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        agent = Agent(store=store, use_model=False)
        agent.integration_on = lambda name: False
        rng = random.Random(4)
        fell_through = 0
        n = 120
        try:
            for _ in range(n):
                intent = rng.choice(self.OFFLINE)
                text = scenarios.say(intent, rng, 0.3)
                for k in ("offered", "walking", "unfinished"):
                    setattr(agent, k, None)
                store.set_setting("grilling", None)
                try:
                    reply = agent.chat(text)
                except ValueError:
                    continue  # refused on purpose (a password, an impossible time)
                if "isn't running right now" in (reply.get("text") or ""):
                    fell_through += 1
        finally:
            store.close()
            temp.cleanup()
        self.assertLess(fell_through / n, 0.12)


if __name__ == "__main__":
    unittest.main()
