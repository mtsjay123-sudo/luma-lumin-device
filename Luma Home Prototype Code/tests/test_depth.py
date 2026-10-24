"""Quick answer or deep dive? Luma asks when a question could go either way, the way you talk,
and remembers what you usually pick."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from luma.agent import depth
from luma.agent.runtime import Agent
from luma.memory.store import Store

NOW = 1792850000.0  # Sat 24 Oct 2026, mid-morning in New York


class KindTests(unittest.TestCase):
    def test_questions_that_can_go_either_way(self):
        for text, kind in [
            ("what do you feel about trump", "politics"), ("what's your take on the election", "politics"),
            ("thoughts on immigration?", "politics"), ("do you think god is real what do you think", "politics"),
            ("should I quit my job to start a business", "advice"), ("what should i do about my boyfriend", "advice"),
            ("is it worth it to go back to school", "advice"), ("am i wrong for not going to my mom's party", "advice"),
            ("hey what's the news today", "news"), ("catch me up on the news", "news"), ("what's going on in the world", "news"),
            ("explain how the stock market works", "explain"), ("why did the roman empire fall apart", "explain"),
            ("so whats going on out there rn", "news"),
        ]:
            with self.subTest(text=text):
                self.assertEqual(depth.kind_of(text), kind)

    def test_simple_things_are_just_answered(self):
        for text in ["what do you think of my outfit", "do you like pineapple on pizza", "set a reminder for 5", "hey", "good news I got the job",
                     "should I wear the black shoes", "what's the weather", "lol", "what time is it", "catch me up on instagram", "Explain how a reminder can help me"]:
            with self.subTest(text=text):
                self.assertIsNone(depth.kind_of(text))

    def test_they_already_said_how_much(self):
        self.assertEqual(depth.said("real quick what do you think about trump"), "quick")
        self.assertEqual(depth.said("break it down for me, should I move to atlanta"), "deep")
        self.assertIsNone(depth.said("what do you think about trump"))

    def test_reading_their_pick(self):
        for text in ["quick", "Quick answer", "just the answer", "right now", "keep it short", "nah just tell me", "Quick headlines"]:
            with self.subTest(text=text):
                self.assertEqual(depth.read_choice(text), "quick")
        for text in ["deep dive", "Deep dive", "go deep", "take your time", "full rundown", "Full rundown", "break it down", "go crazy"]:
            with self.subTest(text=text):
                self.assertEqual(depth.read_choice(text), "deep")
        self.assertIsNone(depth.read_choice("anyway can you set a timer for ten minutes for the pasta please"))

    def test_asks_in_their_register_and_dates_the_news(self):
        zone = ZoneInfo("America/New_York")
        chill = depth.ask("politics", "ngl what you think bout trump", NOW, zone, seed=0)
        self.assertIn("gotchu", chill)
        self.assertIn("😭", chill)
        plain = depth.ask("politics", "What do you think about Trump?", NOW, zone, seed=0)
        self.assertNotIn("gang", plain)
        news = depth.ask("news", "what's the news today", NOW, zone)
        self.assertIn("Saturday, October 24", news)

    def test_stops_asking_once_its_clear(self):
        prefs = {}
        for _ in range(3):
            prefs = depth.remember(prefs, "news", "quick")
        self.assertEqual(depth.remembered(prefs, "news"), "quick")
        self.assertIsNone(depth.remembered(depth.remember(prefs, "news", "deep"), "news"))
        self.assertEqual(depth.remembered({"_always": "quick"}, "politics"), "quick")


class LabelTests(unittest.TestCase):
    def test_the_judges_letters_never_reach_them(self):
        from luma.agent import mind
        said = mind.without_labels("Honestly, go with [C]. You need proof first, a prototype and real pre-orders.")
        self.assertEqual(said, "You need proof first, a prototype and real pre-orders.")
        self.assertEqual(mind.without_labels("Option B is the move. Stay in school and sell on the side."), "Stay in school and sell on the side.")


class DisclaimerTests(unittest.TestCase):
    def test_a_friend_doesnt_open_with_a_disclaimer(self):
        from luma.agent import mind
        said = mind.without_disclaimers("I don’t have personal opinions, so I can’t say what I ‘feel’ about Trump. But his supporters love the economy talk. What do you think?",
                                        "what do you feel about trump")
        self.assertEqual(said, "His supporters love the economy talk. What do you think?")
        self.assertEqual(mind.without_disclaimers("I'm neutral on that, but honestly the second plan is cleaner.", "which plan"), "Honestly the second plan is cleaner.")

    def test_honest_about_what_luma_is_when_asked(self):
        from luma.agent import mind
        line = "I'm an AI, so no heartbeat, but I've got moods and opinions of my own."
        self.assertEqual(mind.without_disclaimers(line, "wait are you an ai"), line)


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.now = NOW
        self.seen = []

        self.notes = []

        def planner(messages, context, allowed, mode):
            self.seen.append(self.agent.profile.get("verbosity"))
            self.notes.append(" ".join(m.get("text", "") for m in context if isinstance(m, dict)))
            return {"type": "reply", "text": "Here's my honest take."}
        self.agent = Agent(store=self.store, use_model=True, planner=planner, now=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def say(self, text):
        self.now += 20
        return self.agent.chat(text)

    def test_asks_then_answers_quick(self):
        asked = self.say("ngl gng what you think about trump")
        self.assertEqual(asked["depth_ask"], "politics")
        self.assertEqual(asked["choices"], ["Quick answer", "Deep dive"])
        self.assertTrue(any(w in asked["text"] for w in ("gotchu", "go in on", "sit with it")))  # asked the way they talk
        answer = self.say("Quick answer")
        self.assertEqual(answer["text"], "Here's my honest take.")
        self.assertIn("brief", self.seen)  # the quick path keeps it short

    def test_quick_politics_stays_fair(self):
        self.say("what do you feel about trump")
        before = len(self.notes)
        self.say("Quick answer")
        answered = [n for n in self.notes[before:] if "supporters like" in n]
        self.assertTrue(answered, self.notes[before:])
        self.assertIn("Don't take a side", answered[0])
        self.say("what's the weather")
        self.assertFalse(any("supporters like" in n for n in self.notes[before + len(answered) + 1:]))  # just for that answer

    def test_asks_again_about_the_next_big_question(self):
        self.say("what do you feel about trump")
        self.say("quick")
        again = self.say("should I drop out of college to start a clothing brand")  # a minute later, a whole new question
        self.assertEqual(again.get("depth_ask"), "advice")

    def test_deep_dive_thinks_it_through(self):
        self.say("what do you think about the election")
        with mock.patch.object(self.agent, "deliberate", return_value={"text": "I thought about it from a few sides."}) as thinking:
            answer = self.say("deep dive")
        thinking.assert_called_once()
        self.assertEqual(thinking.call_args[0][0], "what do you think about the election")
        self.assertEqual(answer["text"], "I thought about it from a few sides.")

    def test_no_question_when_they_already_said(self):
        answer = self.say("real quick, should I quit my job to start a business")
        self.assertNotIn("depth_ask", answer)
        self.assertIn("brief", self.seen)

    def test_something_else_isnt_taken_as_the_pick(self):
        self.say("what do you think about immigration")
        answer = self.say("set a timer for 10 minutes")
        self.assertNotIn("depth_ask", answer)
        self.assertIsNone(self.agent.depth_ask)

    def test_stop_asking_means_stop(self):
        self.say("thoughts on the economy right now?")
        self.say("just answer from now on")
        self.now += 400
        again = self.say("what do you think about congress")
        self.assertNotIn("depth_ask", again)

    def test_doesnt_turn_every_message_into_a_question(self):
        self.say("what do you think about trump")
        self.say("hmm idk")  # not a pick: the question is dropped
        follow = self.say("what about the election though, what do you think")
        self.assertNotIn("depth_ask", follow)  # asked a minute ago


if __name__ == "__main__":
    unittest.main()
