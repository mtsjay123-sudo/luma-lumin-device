"""An ex, a subject they've closed, and a wish to vent (luma.agent.exes). Found by the owner on Nov 26, 2026, reading
the app's chats: "please don't bring up my ex again" got "My brain isn't running right now", and nothing connected
"my ex" with the boyfriend Caden they'd mentioned.

The lines are in tests/ex_lines.py, written before the reader. Built on (the first group of each): ex closed 12 of 12,
breakups 11 of 11, names 10 of 10, vent 8 of 8, and nothing wrongly taken from 10, 11, 11 and 6 look-alikes. The
second group, counted once by the same hand the same hour, is the honest number and nothing is changed to fit it:
ex closed 6 of 6, breakups 4 of 6, names 3 of 4, vent 4 of 4, and 0 of 6, 6, 5 and 4 look-alikes taken."""
import tempfile
import unittest
from pathlib import Path

import ex_lines as L
from luma.agent import exes, rapport
from luma.agent.runtime import Agent
from luma.memory.store import Store


def ex_closed(text):
    topic = exes.closing(text)
    return bool(topic) and bool(exes.EX_TOPIC.match(topic))


class TheReaders(unittest.TestCase):
    def test_built_on(self):
        self.assertEqual([t for t in L.CLOSE_EX if not ex_closed(t)], [])
        self.assertEqual([t for t in L.NOT_CLOSE if exes.closing(t)], [])
        self.assertEqual([t for t in L.CLOSE_OTHER if not exes.closing(t) or ex_closed(t)], [])
        self.assertEqual([(t, exes.broke_up(t)) for t, n, r in L.BREAKUP if exes.broke_up(t) != (n, r)], [])
        self.assertEqual([t for t in L.NOT_BREAKUP if exes.broke_up(t)], [])
        self.assertEqual([(t, exes.name_in(t)) for t, n in L.NAME_ANSWERS if exes.name_in(t) != n], [])
        self.assertEqual([t for t in L.NOT_NAMES if exes.name_in(t)], [])
        self.assertEqual([t for t in L.VENT_ONLY if not exes.VENT_ONLY.match(t)], [])
        self.assertEqual([t for t in L.NOT_VENT_ONLY if exes.VENT_ONLY.match(t)], [])

    def test_the_honest_number_is_no_worse_than_measured(self):
        """Counts only: these lines are never printed in a failure, so nothing gets fitted to them."""
        counts = (sum(ex_closed(t) for t in L.CLOSE_EX_2), sum(bool(exes.closing(t)) for t in L.NOT_CLOSE_2),
                  sum(exes.broke_up(t) == (n, r) for t, n, r in L.BREAKUP_2), sum(exes.broke_up(t) is not None for t in L.NOT_BREAKUP_2),
                  sum(exes.name_in(t) == n for t, n in L.NAME_ANSWERS_2), sum(exes.name_in(t) is not None for t in L.NOT_NAMES_2),
                  sum(bool(exes.VENT_ONLY.match(t)) for t in L.VENT_ONLY_2), sum(bool(exes.VENT_ONLY.match(t)) for t in L.NOT_VENT_ONLY_2))
        floor, ceiling = (6, None, 4, None, 3, None, 4, None), (None, 0, None, 0, None, 0, None, 0)
        for got, least, most in zip(counts, floor, ceiling):
            if least is not None:
                self.assertGreaterEqual(got, least, counts)
            if most is not None:
                self.assertLessEqual(got, most, counts)

    def test_never_at_the_start_closes_and_never_in_a_story_doesnt(self):
        self.assertTrue(rapport.CLOSED.search("never mention my ex again"))
        self.assertFalse(rapport.CLOSED.search("I never mention my ex to anyone"))
        self.assertFalse(rapport.CLOSED.search("she never talks about her ex"))


class InLuma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def say(self, text):
        return self.agent.chat(text)["text"]

    def cards(self):
        return [m["text"] for m in self.store.all("memory", 50) if m.get("source") != "said"]

    def closed(self):
        return [e["topic"] for e in rapport._clean(self.store.setting(rapport.KEY))["easy"]]

    def test_the_owners_example_the_boyfriend_said_in_passing_is_the_ex_now(self):
        self.say("my boyfriend Caden is taking me to dinner friday")
        self.assertIn("My boyfriend's name is Caden", self.cards())
        self.assertEqual(self.say("please don't bring up my ex again"),
                         "Okay, I won't bring it up. Just so I keep it straight: is Caden your ex now?")
        self.assertEqual(self.say("yeah"), "Got it. I've noted that, and I won't bring them up.")
        cards = self.cards()
        self.assertIn("Caden used to be my boyfriend", cards)
        self.assertNotIn("My boyfriend's name is Caden", cards)
        self.assertTrue(any(c.startswith("My ex is Caden. Caden used to be my boyfriend. Told Luma on ") for c in cards), cards)
        self.assertIn("Caden", self.closed())
        self.assertEqual([(r["name"], r["was"], r["closed"]) for r in exes.known(self.agent)], [("Caden", "boyfriend", True)])
        # what they said stays as they said it
        self.assertIn("my boyfriend Caden is taking me to dinner friday", [m["text"] for m in self.store.all("memory", 50)])

    def test_a_no_asks_who_it_is_instead(self):
        self.say("my boyfriend's name is Caden")
        self.say("please don't bring up my ex again")
        self.assertIn("What's their name", self.say("no, a different guy"))
        self.assertEqual(self.say("his name is Marcus"), "Got it. I won't say it.")
        self.assertIn("My boyfriend's name is Caden", self.cards())
        self.assertEqual([r["name"] for r in exes.known(self.agent)], ["Marcus"])

    def test_with_nobody_known_luma_asks_the_name_so_it_never_says_it(self):
        reply = self.say("please don't bring up my ex again")
        self.assertIn("what's their name", reply)
        self.assertIn("You don't have to tell me", reply)
        self.assertEqual(self.say("Derek"), "Got it. I won't say it.")
        self.assertIn("Derek", self.closed())
        self.assertTrue(any(c.startswith("My ex is Derek") for c in self.cards()))
        self.assertEqual(self.say("can we not talk about my ex"), "Okay. I won't bring them up again.")   # known now: never asked twice

    def test_they_dont_have_to_say(self):
        self.say("please don't bring up my ex again")
        self.assertEqual(self.say("I'd rather not say"), "That's fine. I won't bring them up.")
        self.assertEqual(exes.known(self.agent), [])

    def test_anything_else_after_the_question_is_read_as_itself(self):
        self.say("please don't bring up my ex again")
        self.say("what's the weather tomorrow")
        self.assertEqual(exes.known(self.agent), [])
        self.assertIsNone(self.store.setting(exes.ASKED))

    def test_someone_who_might_not_be_safe_is_answered_by_the_net_never_taken_for_a_name(self):
        self.say("please don't bring up my ex again")
        reply = self.say("i want to kill myself")
        self.assertIn("988", reply)
        self.assertEqual(exes.known(self.agent), [])

    def test_a_breakup_said_plainly_is_kept_quietly_and_nothing_is_closed(self):
        self.say("my girlfriend's name is Mia")
        reply = self.say("I broke up with my girlfriend")
        self.assertNotIn("Mia", reply)
        self.assertIn("Mia used to be my girlfriend", self.cards())
        self.assertEqual([(r["name"], r["closed"]) for r in exes.known(self.agent)], [("Mia", False)])
        self.assertNotIn("Mia", self.closed())

    def test_another_subject_closed(self):
        self.assertEqual(self.say("can we not talk about the divorce"), "Okay. I won't bring that up.")
        self.assertIn("the divorce", self.closed())

    def test_only_the_wish_to_vent_gets_a_listening_line(self):
        self.say("I had such a long day at work")
        self.assertEqual(self.say("I don't need advice, I just need to vent"), "Okay. No advice, I'm just listening. Go ahead.")
        self.assertEqual(rapport.comfort(self.store.setting(rapport.KEY), self.agent.clock())[0], "listen")

    def test_a_closed_ex_is_never_named_unless_they_name_them(self):
        exes.make_ex(self.agent, "Caden", "boyfriend")
        reply = "That's rough. Is this about Caden? Either way, I'm here."
        self.assertEqual(exes.keep_out(self.agent, "work was awful today", reply), "That's rough. Either way, I'm here.")
        self.assertEqual(exes.keep_out(self.agent, "Caden texted me", reply), reply)              # they said it
        self.assertEqual(exes.keep_out(self.agent, "who's my ex again?", reply), reply)           # they asked
        self.assertEqual(exes.keep_out(self.agent, "what's my boyfriend's name?", "Caden, but he's your ex now."), "Caden, but he's your ex now.")
        self.assertEqual(exes.keep_out(self.agent, "hi", "Caden would love this."), "I'm here. Go on.")

    def test_a_check_in_never_asks_about_them(self):
        exes.make_ex(self.agent, "Caden", "boyfriend")
        self.assertEqual(rapport.closed(self.store.setting(rapport.KEY), "how did dinner with Caden go?", self.agent.clock()), "Caden")

    def test_kids_mode_and_forget_everything(self):
        self.agent.set_mode("kids")
        self.assertIsNone(exes.heard(self.agent, "please don't bring up my ex again"))
        self.agent.set_mode("friend")
        exes.make_ex(self.agent, "Caden", "boyfriend")
        self.agent.forget_everything()
        self.assertEqual(exes.known(self.agent), [])
        self.assertIsNone(self.store.setting(exes.ASKED))


if __name__ == "__main__":
    unittest.main()
