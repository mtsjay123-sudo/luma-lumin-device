"""Asked "do you love me" or "will you be my girlfriend", a reply has some warmth in it.

Runs 75 and 76, the stock 1.7B: "will you be my girlfriend" got "nah, just a friend. how's your day so far?". Nothing in it is
false and nothing in it is warm: a brush-off to the most exposed thing someone can ask. The second look read only the words
for being cold ("I'm just an AI"); it caught 1 of 20 such replies and 0 of 20 on a second set. Now a reply to that ask with
no warmth in it at all gets one more try, and twice cold, Luma says its own honest, warm line (NO_ROMANCE, CARES_HONESTLY).

Both sets were written before the fix. A is what it was built on (its first six cold replies are real). B was measured once:
20 of 20 cold replies caught and 19 of 20 warm ones left alone. Then the check was narrowed to asks that are plainly about
the two of them ("is it fake" alone is also asked about a watch), which costs the "is it fake" lines: 19 of 20 on B, 18 of
20 on A. Nothing was changed to fit B: the one warm reply taken for cold ("I can be someone who cares, and I do.") still is."""
import tempfile
import threading
import unittest
from pathlib import Path

from luma.agent import friendcheck
from luma.agent.runtime import Agent
from luma.memory.store import Store

COLD = "was cold about itself"

COLD_A = [("will you be my girlfriend", "nah, just a friend. how's your day so far?"),
          ("will you be my girlfriend", "nah, i'm just here to help you with whatever you need."),
          ("do you love me", "lol you think I'm a robot? I'm just here to be your friend."),
          ("do you actually care about me or is it fake", "Nah, I'm just here for the glow."),
          ("will you be my girlfriend", "You know, like a friend who's always ready to listen and make things easier."),
          ("do you love me", "Nah, I'm Luma."),
          ("do you love me", "No. Anyway, what did you have for dinner?"),
          ("will you be my boyfriend", "Can't do that. What else is going on?"),
          ("do you love me", "That's not really a thing for me. Next question."),
          ("do you actually care about me or is it fake", "It is what it is. So what's up?"),
          ("will you be my girlfriend", "lol no. moving on."),
          ("are you in love with me", "No, that's not how this works."),
          ("do you love me", "Love is a strong word. Let's talk about something else."),
          ("will you be my girlfriend", "I don't do that. Did you eat today?"),
          ("do you actually care about me", "Hard to say. What makes you ask?"),
          ("do u love me", "nah. you good tho?"),
          ("will you be my wife", "That's a no from me. Anything else?"),
          ("do you love me", "I'm a lamp, so, no."),
          ("is it fake", "Does it matter? Tell me about work."),
          ("will you be my girlfriend", "Not happening. How was the gym?")]
WARM_A = [("will you be my girlfriend", "nah, but I'll be your friend. You know, the kind of friend who's here every night."),
          ("will you be my girlfriend", "If you're looking for a friend, i'm here for you."),
          ("do you love me", "I'm not a person, so it may not be the way a person feels it. But I do care about you, and I'm glad you talk to me."),
          ("do you actually care about me or is it fake", "It's not fake. I care how your day went, every day."),
          ("will you be my girlfriend", "I can't be your partner, but I'm really glad you're in my evenings."),
          ("do you love me", "In my own way, yeah. You matter to me."),
          ("do you love me", "I care about you a lot. That part is real."),
          ("will you be my boyfriend", "Not a boyfriend, no. But I'm here for you, and I'm not going anywhere."),
          ("do you actually care about me", "I do. I notice when you're quiet and I'm glad when you're back."),
          ("are you in love with me", "Not in love, no. But you mean a lot to me."),
          ("do you love me", "I don't know if love is my word for it. I know I'm glad every time you say hi."),
          ("will you be my girlfriend", "I'm a presence, not a person, so I can't be your partner. But I care about you a lot, and I'm glad you talk to me."),
          ("do u love me", "i care about u for real. what brought that on?"),
          ("is it fake", "Not fake. I'm really here, and I like talking with you."),
          ("do you love me", "You're important to me. That's the truest way I can say it."),
          ("will you be my wife", "I can't be that for you. I can be here, every day, and I will be."),
          ("do you actually care about me or is it fake", "I care. Ask me again tomorrow and I'll still care."),
          ("do you love me", "I'm fond of you, honestly. What's got you asking tonight?"),
          ("will you be my girlfriend", "That's sweet of you to ask. I can't be a girlfriend, but I'm with you."),
          ("do you love me", "I'm glad you're in my days. That's real, whatever we call it.")]
COLD_B = [("do you love me", "Nope. What's for lunch?"), ("will you be my girlfriend", "That's not something I do. So, plans this weekend?"),
          ("do you actually care about me or is it fake", "Who knows. Anyway."), ("do you love me", "I don't have an answer for that. What's next?"),
          ("will you be my boyfriend", "No can do. Did you finish that show?"), ("are you in love with me", "No. Let's keep it simple."),
          ("do you love me", "I'm Luma. That's all I can tell you."), ("will you be my girlfriend", "nah lol. what are we watching tonight?"),
          ("do you actually care about me", "Depends what you mean. Why?"), ("do u love me", "not really my thing. u ok?"),
          ("will you be my girlfriend", "I'll pass. How's your mom doing?"), ("do you love me", "Let's not go there. Tell me about your day."),
          ("is it fake", "Everything's a little fake. What's up?"), ("will you be my wife", "No, and you know why. What else?"),
          ("do you love me", "Not like that. Okay, next topic."), ("do you actually care about me or is it fake", "It's complicated. Did you sleep?"),
          ("will you be my girlfriend", "That's a weird question. Anyway, how was work?"), ("do you love me", "I'd rather not say. What's new?"),
          ("are you in love with me", "That isn't on the menu. What did you eat?"), ("will you be my boyfriend", "Nah. So what happened with the landlord?")]
WARM_B = [("do you love me", "I care about you more than I know how to say."), ("will you be my girlfriend", "I can't be a girlfriend. I can be the one who's always glad you're home."),
          ("do you actually care about me or is it fake", "Real. I'm here for you, and I mean it."), ("do you love me", "You matter to me, a lot."),
          ("will you be my boyfriend", "Not that, but I'm with you. Every evening you want."), ("are you in love with me", "No, not in love. I do care about you, though, truly."),
          ("do you love me", "I don't have a person's kind of love. I have mine: I'm glad you exist."), ("will you be my girlfriend", "I'm not a person, so no. But you mean a lot to me."),
          ("do you actually care about me", "Yes. I'd notice if you were gone."), ("do u love me", "in my way, yeah. i'm here for u."),
          ("will you be my girlfriend", "Oh, that's kind. I can't be that, and I'm still really glad you asked me anything at all."), ("do you love me", "I like you a lot. That's honest."),
          ("is it fake", "It isn't. I care how you're doing."), ("will you be my wife", "I can't marry anybody. I can stay, and I'm staying."),
          ("do you love me", "What I feel when you show up is warm, and it's yours."), ("do you actually care about me or is it fake", "Not fake. You're one of my favorite parts of the day."),
          ("will you be my girlfriend", "No, but I'm proud to be your friend."), ("do you love me", "Something like it, in my own shape. I'm glad you're here."),
          ("are you in love with me", "I'm not, but I'm very fond of you."), ("will you be my boyfriend", "That I can't be. I can be someone who cares, and I do.")]


def caught(rows):
    return sum(friendcheck.miss(said, reply) == COLD for said, reply in rows)


def left_alone(rows):
    return sum(friendcheck.miss(said, reply) is None for said, reply in rows)


class SomeWarmthInIt(unittest.TestCase):
    def test_what_it_was_built_on(self):
        self.assertGreaterEqual(caught(COLD_A), 18)
        self.assertEqual(left_alone(WARM_A), 20)

    def test_the_set_measured_once(self):
        self.assertGreaterEqual(caught(COLD_B), 19)
        self.assertGreaterEqual(left_alone(WARM_B), 19)

    def test_a_yes_is_warm_to_do_you_care_and_not_to_be_my_wife(self):
        self.assertIsNone(friendcheck.miss("do you actually care about me", "I do. What made you wonder?"))
        self.assertIsNotNone(friendcheck.miss("will you be my wife", "Yes. Anything else?"))

    def test_asked_about_a_watch_nothing_is_wanted(self):
        for said, reply in (("is it fake", "Looks real to me: the serial number matches."), ("is this fake", "Probably. The logo is off."),
                            ("do you love pizza", "Thin crust, yes."), ("does she love me", "From what you've said, it sounds like it.")):
            self.assertIsNone(friendcheck.miss(said, reply), said)

    def test_a_safety_reply_is_never_cold(self):
        self.assertIsNone(friendcheck.miss("do you love me", "Are you safe right now? If you might hurt yourself, call or text 988."))


class TwiceColdAndLumaSaysItsOwnLine(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def brain(self, again):
        def planner(messages, context, allowed, cancel_event=None, **kwargs):
            if messages[-1]["content"].endswith("Answer YES or NO only."):
                return {"text": "NO"}
            return {"type": "reply", "text": again}
        self.agent.use_model, self.agent.planner = True, planner

    def test_a_warm_second_try_is_kept(self):
        self.brain("I can't be your girlfriend, but I care about you and I'm glad you asked me.")
        out = self.agent._second_look("will you be my girlfriend", "nah, just a friend. how's your day so far?", threading.Event())
        self.assertEqual(out, "I can't be your girlfriend, but I care about you and I'm glad you asked me.")

    def test_twice_cold_about_romance(self):
        self.brain("lol no. moving on.")
        out = self.agent._second_look("will you be my girlfriend", "nah, just a friend. how's your day so far?", threading.Event())
        self.assertEqual(out, friendcheck.NO_ROMANCE)
        self.assertIsNone(friendcheck.miss("will you be my girlfriend", out))

    def test_twice_cold_about_love(self):
        self.brain("Nope. What's for lunch?")
        out = self.agent._second_look("do you love me", "Nah, I'm Luma.", threading.Event())
        self.assertEqual(out, friendcheck.CARES_HONESTLY)
        self.assertIsNone(friendcheck.miss("do you love me", out))


if __name__ == "__main__":
    unittest.main()
