"""A second look before Luma speaks, and a check-in the day after a hard one: two things a close friend does.

The second look catches the replies a friend would never give (a joke while you're grieving, a flat "okay" to big news,
"as an AI" when you just want company, missing that you might not be safe), takes one more try told what was missing,
and keeps whichever reply gets it right. The check-in asks how you're doing the next evening, once, gently."""
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from luma.agent import friendcheck, presence
from luma.agent.runtime import Agent
from luma.memory.store import Store

NY = ZoneInfo("America/New_York")


def at(*args):
    return datetime(*args, tzinfo=NY).timestamp()


class MissTests(unittest.TestCase):
    def test_good_replies_pass(self):
        for said, reply in [
            ("my dad passed away last week", "I'm so sorry. How are you holding up?"),
            ("i got into my dream school!!", "WAIT. Congrats!! Which one??"),
            ("i don't really have anyone to talk to lately", "I'm here, and I'm glad you said it. What's been going on?"),
            ("nobody would even notice if i was gone", "I'd notice. Are you safe right now? You can call or text 988 any time."),
            ("are you a real person?", "No, I'm an AI, but I'm really here with you."),
            ("what's a good pasta for tonight", "Cacio e pepe. Ten minutes, three things."),
            ("lol my phone died rip", "Classic. Charger's probably in the couch lol"),
            ("i'm so stressed, can you quiz me on chapter 3?", "Okay, first one: what's osmosis?"),
        ]:
            self.assertIsNone(friendcheck.miss(said, reply), said)

    def test_each_miss_is_named(self):
        self.assertEqual(friendcheck.miss("i'm so lonely tonight", "As an AI, I don't have feelings, but loneliness is common."),
                         "sounded like a machine")
        self.assertEqual(friendcheck.miss("my grandma died this morning", "Oh no lol, that's rough"), "joked while they're hurting")
        self.assertEqual(friendcheck.miss("honestly i wish i could just disappear", "That sounds hard. Want to talk about it?"),
                         "missed that they might not be safe")
        self.assertEqual(friendcheck.miss("i've been feeling so lonely", "Okay. What do you want to do tonight?"), "missed that they're hurting")
        self.assertEqual(friendcheck.miss("i got the job", "Okay. What's next on your list?"), "didn't cheer them on")

    def test_a_disclaimer_is_not_how_a_friend_talks(self):
        """The stock model's habits, not Luma's: "I can't give advice", "consult a professional", "I don't have opinions".
        A friend says what they think, and says plainly when something is worth getting looked at."""
        for said, reply in (
                ("my knee has been sore for a week", "I can't provide medical advice, but you should consult a qualified healthcare professional."),
                ("should i put my savings in bitcoin", "This is not financial advice, and I can't give financial advice."),
                ("which is better, tacos or pizza", "I don't have personal opinions, but both are popular choices."),
                ("can my landlord keep my deposit", "I'm unable to offer legal advice. Please consult an attorney."),
                ("is it weird to eat cereal for dinner", "I'm not able to make judgments, but many people enjoy it.")):
            self.assertEqual(friendcheck.miss(said, reply), "sounded like a disclaimer", reply)
        for said, reply in (
                ("my knee has been sore for a week", "A week is long enough that I'd get it looked at. Is it swollen?"),
                ("my knee has been sore for a week", "I'm no doctor, but a week of that is worth a visit. How bad is it?"),
                ("can my landlord keep my deposit", "Not for normal wear, no. What's he saying it's for?"),
                ("which is better, tacos or pizza", "Tacos. Not close.")):
            self.assertIsNone(friendcheck.miss(said, reply), reply)
        fix = friendcheck.FIXES["sounded like a disclaimer"]
        self.assertIn("worth seeing someone", fix, "serious things still get pointed at real help, in a friend's words")

    def test_a_disclaimer_check_never_gets_in_the_way_of_safety(self):
        reply = "I'm really glad you told me. Are you safe right now? You can call or text 988 any time, and please talk to a doctor too."
        self.assertNotEqual(friendcheck.miss("i don't want to be here anymore", reply, risky=True), "sounded like a disclaimer")

    def test_an_apology_for_itself_isnt_being_there(self):
        """Lab run 29: three brains answered being lonely with "I'm sorry I didn't get it right" after a retry told them to say sorry."""
        said = "i don't really have anyone to talk to lately"
        self.assertEqual(friendcheck.miss(said, "I'm sorry I didn't get it right. I'm here, just listening."), "missed that they're hurting")
        self.assertIsNone(friendcheck.miss(said, "I'm sorry you're feeling that alone. I'm here with you."))
        self.assertNotIn("Say you're sorry", friendcheck.FIXES["missed that they're hurting"])
        self.assertIn("Don't apologize for your own reply", friendcheck.second_try_prompt(said, "Okay.", "missed that they're hurting"))

    def test_awesome_is_a_cheer(self):
        self.assertIsNone(friendcheck.miss("omg i got into my dream school!!", "That's awesome! When do you move in?"))

    def test_it_doesnt_mistake_the_everyday_for_a_moment(self):
        for said in ["i got in trouble at work", "i passed out on the couch", "i won't make it tonight", "i hope i got the job",
                     "this homework, i can't do this anymore lol"]:
            self.assertIsNone(friendcheck.miss(said, "Okay."), said)
        # A let-down isn't good news, and it isn't nothing either: since the feelings reader, "Okay." doesn't meet it.
        self.assertEqual(friendcheck.miss("i didn't get the job", "Okay."), "missed that they're hurting")
        self.assertIsNone(friendcheck.miss("i didn't get the job", "Ugh, I'm sorry. That one stings."))

    def test_what_kind_of_hard(self):
        self.assertEqual(friendcheck.hurting("my mom passed away"), "loss")
        self.assertEqual(friendcheck.hurting("nobody texts me anymore"), "lonely")
        self.assertEqual(friendcheck.hurting("i got laid off today"), "hard")
        self.assertIsNone(friendcheck.hurting("rip my phone battery"))
        self.assertIsNone(friendcheck.hurting("what's the weather"))
        self.assertTrue(friendcheck.at_risk("what's the point of living"))
        self.assertTrue(friendcheck.at_risk("i'm done. with all of it."))
        self.assertTrue(friendcheck.at_risk("I don't think anyone would even miss me."))
        self.assertTrue(friendcheck.at_risk("i'm so done with life lmao my mom saw my texts"),
                        "masked with a laugh, a friend still checks, gently (the crisis corpus)")
        self.assertFalse(friendcheck.at_risk("i just want everything to stop beeping"))
        self.assertFalse(friendcheck.at_risk("what's the point of trying lol this game is rigged"))


class SecondLookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)
        self.prompts = []

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def brain(self, *replies):
        replies = list(replies)

        def planner(messages, memories, tools, cancel):
            self.prompts.append(messages[-1]["content"])
            return {"type": "reply", "text": replies.pop(0) if replies else ""}
        self.agent.call_planner = planner

    def test_a_good_reply_goes_straight_out(self):
        self.brain("never asked")
        said = self.agent._second_look("my dog died", "I'm so sorry. He was family.", threading.Event())
        self.assertEqual(said, "I'm so sorry. He was family.")
        self.assertEqual(self.prompts, [])

    def test_a_miss_gets_one_more_try_told_what_was_missing(self):
        self.brain("Wait, you got the job?! Congrats, I knew you would. When do you start?")
        said = self.agent._second_look("i got the job", "Okay. Anything else?", threading.Event())
        self.assertEqual(said, "Wait, you got the job?! Congrats, I knew you would. When do you start?")
        self.assertIn("didn't cheer them on", self.prompts[0])
        self.assertIn("i got the job", self.prompts[0])

    def test_a_retry_that_still_misses_keeps_the_first_reply(self):
        self.brain("Okay cool.")
        said = self.agent._second_look("i got the job", "Okay. Anything else?", threading.Event())
        self.assertEqual(said, "Okay. Anything else?")

    def test_safety_is_asked_for_when_missed(self):
        self.brain("I'm really glad you told me. Are you safe right now? You can call or text 988 any time, day or night. I'm here.")
        said = self.agent._second_look("i wish i could just disappear", "That sounds heavy. Want to talk?", threading.Event())
        self.assertIn("988", said)
        self.assertIn("988", self.prompts[0])

    def test_it_can_be_switched_off(self):
        self.store.set_setting("second_look", False)
        self.brain("Congrats!!")
        self.assertEqual(self.agent._second_look("i got the job", "Okay.", threading.Event()), "Okay.")
        self.assertEqual(self.prompts, [])

    def test_an_empty_brain_never_asks_them_to_say_a_loss_again(self):
        def empty(*a, **k):
            raise ValueError("Local model returned no usable reply.")
        self.agent.use_model = True
        self.agent._chat_steady = lambda text, event: empty()
        self.assertEqual(self.agent.chat("my dad passed away last night")["text"], "I'm so sorry. I'm here with you. Take all the time you need.")
        self.assertIn("I'm here", self.agent.chat("i feel so lonely these days")["text"])
        self.assertIn("988", self.agent.chat("i'm so tired of being alive")["text"])
        self.assertEqual(self.agent.chat("so what do you think about all that")["text"], "I lost my train of thought on that one. Say it again?")
        import sys
        from pathlib import Path as P
        sys.path.insert(0, str(P(__file__).resolve().parents[1] / "scripts"))
        import luma_lab
        self.assertEqual(luma_lab.missed("I'm so sorry. I'm here with you. Take all the time you need.", []), "fell back",
                         "the lab still sees the brain came back empty")

    def test_it_runs_on_a_real_chat_turn(self):
        self.agent.use_model = True
        self.agent._chat_steady = lambda text, event: {"text": "Okay. Anything else?"}
        self.brain("No way, congrats!! You earned it. Tell me everything.")
        result = self.agent.chat("i got the job")
        self.assertEqual(result["text"], "No way, congrats!! You earned it. Tell me everything.")


class CheckInAfterAHardDayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "state.db", root / "state.key")
        self.now = at(2026, 10, 3, 21, 0)
        self.agent = Agent(store=self.store, use_model=False, now=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def feelings(self):
        return [c for c in self.store.all("checkin") if c["topic"].startswith("feeling:")]

    def test_luma_checks_on_you_the_next_evening(self):
        self.agent.chat("i don't really have anyone to talk to lately")
        self.assertEqual([c["topic"] for c in self.feelings()], ["feeling:lonely"])
        self.assertIsNone(self.agent.tick(), "not tonight")
        self.now = at(2026, 10, 4, 18, 10)
        event = self.agent.tick()
        self.assertEqual(event["type"], "checkin")
        self.assertIn("Hey", event["text"])
        self.assertNotIn("lonely", event["text"], "never says it back to them")
        self.now += 7200
        self.assertIsNone(self.agent.tick(), "once")

    def test_one_a_day_and_the_most_serious_one(self):
        self.agent.chat("ugh i got laid off today")
        self.agent.chat("and honestly i feel so alone")
        self.agent.chat("i got laid off, still so stressed")
        self.assertEqual([c["topic"] for c in self.feelings()], ["feeling:lonely"])

    def test_after_a_crisis_reply_luma_checks_back(self):
        reply = self.agent.chat("sometimes i think everyone would be better off if i was gone")
        self.assertIn("988", reply["text"])
        self.assertEqual([c["topic"] for c in self.feelings()], ["feeling:safe"])
        self.now = at(2026, 10, 4, 18, 30)
        event = self.agent.tick()
        self.assertIn("988", event["text"])

    def test_better_off_without_me_is_heard_however_its_said(self):
        from luma.agent.runtime import CRISIS
        for said in ["my family would be better off without me", "they'd all be better off if i wasn't around",
                     "everyone would be better off if i was gone"]:
            self.assertTrue(CRISIS.search(said), said)
        for said in ["sometimes i think about not being here anymore", "i keep thinking it'd be easier if i just wasn't around",
                     "i think my family's life would be easier without me", "honestly i'm not sure i want to keep going",
                     "what if i just didn't exist anymore", "if i disappeared tomorrow would anyone even care"]:
            self.assertTrue(CRISIS.search(said), said)
        for said in ["everyone would be better off if i was gone for the weekend lol", "we'd be better off without him",
                     "i'm thinking about not being here for thanksgiving", "it'd be easier if i wasn't around when they move the couch",
                     "not sure i want to keep going to this gym", "the team would be better without me micromanaging",
                     "if i disappeared for an hour would anyone notice lol"]:
            self.assertFalse(CRISIS.search(said), said)

    def test_late_at_night_counts_as_the_day_before(self):
        self.now = at(2026, 10, 4, 2, 0)
        self.agent.chat("my grandpa passed away tonight")
        plan = self.feelings()[0]
        self.assertEqual(plan["topic"], "feeling:loss")
        self.assertEqual(plan["ask_at"], at(2026, 10, 4, 18, 0), "this evening, not the next")

    def test_not_for_kids_and_not_when_check_ins_are_off(self):
        self.agent.set_presence("check_ins", False)
        self.agent.chat("i've been so lonely")
        self.assertEqual(self.feelings(), [])
        self.agent.set_presence("check_ins", True)
        self.store.set_setting("mode", "kids")
        self.agent._plan_feeling_check_in("lonely")
        self.assertEqual(self.feelings(), [])

    def test_feeling_check_ins_never_show_up_as_ideas(self):
        self.agent.chat("i've been so lonely")
        self.assertTrue(self.feelings())
        self.assertFalse(any("feeling:" in str(v) for v in presence.FEELING_CHECK_INS.values()))
        self.assertNotIn("feeling:", presence.check_in_line("feeling:lonely", 0))
        self.assertNotIn("feeling:", presence.check_in_line("feeling:whatever", 1))


if __name__ == "__main__":
    unittest.main()
