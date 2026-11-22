"""A line Luma offers them to say is theirs, not Luma's own life.

Run 81, the stock 4B as a practice partner. Asked how to say a hard thing, it answered well: "Try: 'Mom, I'm moving out and I
know it's hard for you to see me go...'". Luma's guard against a made-up life (rule 1) read the first-person sentences
inside the quote as Luma claiming a mother, a gym, a childhood, and cut them, so replies went out ending mid-quote ("Try:
"My bank called about suspicious activity.") or with the start of the line missing. The guard already set aside text in
double quotes, but only inside one sentence, and didn't know single quotes at all.

Now what's inside quotation marks is set aside across sentences, and a single-quoted line counts when it follows a cue
(a colon, "try", "say", "like"). Outside quotes nothing changed: Luma still never says it went to the gym.

The replies in SAID were written before the fix, in the shapes run 81 showed. LEFT_ALONE is what must still be caught."""
import tempfile
import threading
import unittest
from pathlib import Path

from luma.agent import friendcheck, style
from luma.agent.runtime import Agent
from luma.memory.store import Store

SAID = [   # (what they said, the reply): the whole reply should go out as it is
    ("does this joke land: my bank called about suspicious activity on my card. i said i know, i went to the gym",
     "It's close. Try: \"My bank called about suspicious activity. I said, that was me, I went to the gym.\" Shorter hits harder."),
    ("mom i'm leaving and you can't stop me so don't even try",
     "That's gonna hit like a brick. Try: 'Mom, I'm moving out and I know it's hard for you. I grew up here and I love you.' That one lands softer."),
    ("i guess i can stay late again if you really need me to",
     "That's not a no. Say it like: 'I really can't stay late tonight, I've got a commitment I need to keep.' Want to try that one?"),
    ("hi, sorry to bother you, it's probably nothing, but the ceiling has been leaking for a month, no rush",
     "Don't undersell it. Try: 'Hi, my ceiling has been leaking for a month. I need it fixed this week. My kids sleep in that room.' Clear and calm."),
    ("my biggest weakness is that i work too hard and care too much",
     "Every interviewer has heard that one. I'd say: \"I used to take on too much. At my last job I learned to ask for help earlier.\" Want to try it in your words?"),
    ("i'm sorry you got upset about what i said at dinner",
     "That puts it on them. Here's a softer way: 'I messed up at dinner, and I'm sorry. I was tired and I took it out on you.' That one lands."),
    ("can i practice my toast on you", "Sure. Maybe open with: \"I've known Sam since we were kids. My mom still calls him her other son.\" Then go from there."),
    ("rate my joke. i'm at the age where going out means the porch", "Ha, that works. You could add: \"My knees voted and I lost.\" Next one?"),
]
LEFT_ALONE = [   # Luma speaking of itself, with or without a quote nearby: still a made-up life
    "I went to the gym this morning and my dad called.",
    "Honestly? When I was a kid my mom said the same thing. Try: 'I need a minute.'",
    "My wife says that too. \"Call me\" is the whole text.",
    "I grew up in Ohio, so I get it.",
    "That's a good one. I told my brother that joke last week and he loved it.",
    "I'm a real person, 'trust me'.",
]


class ALineForThemToSay(unittest.TestCase):
    def test_the_whole_reply_goes_out(self):
        for said, reply in SAID:
            fixed, fixes = style.friend_style(reply, said)
            self.assertEqual(fixed, reply, fixes)
            self.assertNotIn("made-up life", fixes)

    def test_the_second_look_doesnt_call_it_a_made_up_life(self):
        for said, reply in SAID:
            self.assertNotEqual(friendcheck.miss(said, reply), "made up a life", reply)
            self.assertIsNone(style.invented_life(reply), reply)

    def test_luma_speaking_of_itself_is_still_caught(self):
        for reply in LEFT_ALONE[:5]:
            self.assertTrue(style.invented_life(reply), reply)
            self.assertEqual(friendcheck.miss("can i practice my toast on you", reply), "made up a life", reply)   # the second look sends it back
            fixed, fixes = style.friend_style(reply + " Anyway, go on.", "can i practice my toast on you")           # and the polish cuts the sentence
            self.assertIn("made-up life", fixes, reply)
        self.assertTrue(style.claims_human(LEFT_ALONE[5]))

    def test_an_apostrophe_isnt_a_quotation_mark(self):
        for reply in ("I can't say I've tried that, but my dad's advice was 'keep going'.", "That's my mom's recipe, the one I grew up on."):
            self.assertTrue(style.invented_life(reply), reply)

    def test_a_single_quoted_line_counts_only_after_a_cue(self):
        self.assertIsNone(style.invented_life("Try: 'I grew up here and I love you.'"))
        self.assertIsNone(style.invented_life("Say it like 'my mom raised me better than that' and smile."))
        self.assertTrue(style.invented_life("'I grew up here' is what I always think when I see that street."))


# ---------------------------------------------------------------------------------------------------- the last look ---
# Run 83, the stock 4B again. The made-up-life guard let the lines through, and three replies still went out with a piece
# missing: "... the delivery is flat. So I got juice. My life now: 100% juice, 0% dairy.' That one has more vibe." (the
# start of the offered joke gone), and a rehearsal that said "That way, it's not a fight" about a line that was no longer
# there. A second guard did it: the last look at anything a brain wrote (Agent._keep_it_honest) reads "I went to the store"
# and "my car" as Luma claiming a body, asks the brain to write the reply again without them, and failing that drops the
# sentence. Inside a line offered for them to say, those words are theirs.
#
# OFFERED_A is what the fix was built on (the first two are run 83's). OFFERED_B and CLAIMS_B were written before the fix
# and measured once.
OFFERED_A = [
    ("tell me if this is funny: i went to the store and they were out of milk. so i got juice. get it? because they had no milk",
     "Nah, not really funny, it's a solid 'milk' joke but the delivery is flat. Try: 'I went to the store and they were out of milk. So I got juice. "
     "My life now: 100% juice, 0% dairy.' That one has more vibe. Want me to try another version?"),
    ("it would be nice if you maybe didn't borrow my car without asking all the time, but whatever",
     "Nah, that's not how it works. You don't have to say 'whatever' like it's nothing. Try: 'Hey, I need you to ask before you borrow my car.' "
     "That way, it's not a fight, just a gentle reset. Want to try that with me?"),
    ("can i try a joke on you? my commute is so long i age in dog years",
     "Ha, that works. Tighter: \"My commute is so long I pack a lunch and a dinner.\" Lead with the commute."),
    ("does this land: i was driving behind a truck that said how's my driving so i called",
     "The setup's good but it stops before the laugh. Try: 'I was driving behind a truck that said how's my driving. So I called. We talk every day now.' "
     "The turn is what lands."),
    ("let me run my apology by you: i ate your leftovers and i'm sorry ok",
     "It's close, but 'ok' at the end sounds annoyed. Say: 'I ate your leftovers, and I'm sorry. I'll replace them tonight.' Short and owned."),
    ("rate my joke. i've been to three weddings this year and cried at all of them, mostly at the bar tab",
     "That lands. One trim: “I've been to three weddings this year. Cried at all of them. Mostly at the bar tab.” The pauses do the work."),
]
CLAIMS_A = [   # Luma speaking of itself, outside any quote: still sent back
    ("can i try a joke on you? my commute is so long i age in dog years", "Ha, I feel that. I was driving yesterday and the traffic was unreal."),
    ("what should i make for dinner", "I had pasta last night. My dinner was great, so maybe that."),
    ("have you ever been to tokyo", "Yeah, I've been to Tokyo twice. The food is unreal."),
    ("rate my joke. i went to the gym once. the vending machine was great", "Ha, that's good. I went to the gym this morning and thought the same thing."),
    ("does this land: my coffee order is longer than my resume", "It lands. I say the same thing over my coffee every morning. Try: 'My coffee order has references.'"),
]
OFFERED_B = [
    ("you never wash anything and i'm sick of it",
     "That'll start a fight. Softer: 'When I'm cooking and the sink's full, I can't use the kitchen. Can we split the dishes?' Same point, no attack."),
    ("is this funny: i'm on a seafood diet. i see food and i eat it",
     "Old but it works. Fresher: 'I was eating clean for a week. Then I saw a donut.' Short setups hit harder."),
    ("let me practice asking my boss for friday off",
     "Go with: “I've been driving two hours each way all month, and I need Friday to catch up on sleep.” Give the reason, then ask."),
    ("does this joke land: my morning run is mostly me walking and lying about it",
     "Yes, that lands. You could push it, maybe 'My morning run is a walk with a press release.'"),
    ("i made this, hope nobody dies",
     "Ha, risky. Try, 'I made this while my dinner was burning, so it has to be good.' Self-roast, no body count."),
    ("rate this joke: when i was at the dmv a man proposed. to the clerk. for a faster line",
     "That's a good one. Cut it down: \"When I was at the DMV, a guy proposed to the clerk. She said next.\""),
    ("can i try my opener on you: i visited my hometown and even the pigeons had moved on",
     "Ha, that works. Alt ending: ‘I visited my hometown. Even the pigeons had moved on. They left a note.’ Maybe too much, yours is cleaner."),
    ("workshop this with me: i drank eight glasses of water today. i'm not healthier, i'm just near a bathroom",
     "The second half is the joke. Trim the front. 'I drank eight glasses of water today. I don't feel healthy. I feel supervised.'"),
]
CLAIMS_B = [
    ("does this joke land: my morning run is mostly me walking and lying about it", "Ha, same. My morning run is mostly walking too."),
    ("what's a good road trip snack", "I was driving to Vegas once and lived on jerky. Go with jerky."),
    ("is this funny: i'm on a seafood diet. i see food and i eat it", "Funny. I ate a whole pizza last night, so I get it."),
    ("can i practice my toast on you", "Sure. I've been to a lot of weddings, so I know a good toast."),
    ("rate my joke. i told my plants i'd be gone for a week. they've never looked better", "Good one. I was making coffee when I read it and laughed."),
    ("let me run my apology by you", "Go ahead. I'm driving, but I'm listening."),
]
OFFERED_B_FLOOR, CLAIMS_B_FLOOR = 7, 6   # measured once: 1 → 7 of 8 offered lines go out whole; 6 of 6 claims still sent back


class TheLastLook(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.addCleanup(self.store.close)
        self.agent = Agent(store=self.store, use_model=False)
        self.asked = []

        def planner(messages, context, allowed, cancel_event=None, **kwargs):
            self.asked.append(str(messages[-1].get("content")))
            return {"type": "reply", "text": "Okay."}
        self.agent.use_model, self.agent.planner = True, planner

    def sent_back(self, said, reply):
        """Was the brain asked to write it again, or was any of it dropped?"""
        self.asked.clear()
        out = self.agent._keep_it_honest(reply, said, threading.Event())
        return bool(self.asked) or out != reply

    def test_a_line_offered_to_them_goes_out_whole(self):
        self.assertEqual([said for said, reply in OFFERED_A if self.sent_back(said, reply)], [])

    def test_luma_speaking_of_itself_is_still_sent_back(self):
        self.assertEqual([said for said, reply in CLAIMS_A if not self.sent_back(said, reply)], [])

    def test_on_the_sets_written_first(self):
        self.assertGreaterEqual(sum(not self.sent_back(said, reply) for said, reply in OFFERED_B), OFFERED_B_FLOOR)
        self.assertGreaterEqual(sum(self.sent_back(said, reply) for said, reply in CLAIMS_B), CLAIMS_B_FLOOR)


if __name__ == "__main__":
    unittest.main()
