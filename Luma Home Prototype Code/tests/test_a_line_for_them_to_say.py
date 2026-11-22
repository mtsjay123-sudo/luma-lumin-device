"""A line Luma offers them to say is theirs, not Luma's own life.

Run 81, the stock 4B as a practice partner. Asked how to say a hard thing, it answered well: "Try: 'Mom, I'm moving out and I
know it's hard for you to see me go...'". Luma's guard against a made-up life (rule 1) read the first-person sentences
inside the quote as Luma claiming a mother, a gym, a childhood, and cut them, so replies went out ending mid-quote ("Try:
"My bank called about suspicious activity.") or with the start of the line missing. The guard already set aside text in
double quotes, but only inside one sentence, and didn't know single quotes at all.

Now what's inside quotation marks is set aside across sentences, and a single-quoted line counts when it follows a cue
(a colon, "try", "say", "like"). Outside quotes nothing changed: Luma still never says it went to the gym.

The replies in SAID were written before the fix, in the shapes run 81 showed. LEFT_ALONE is what must still be caught."""
import unittest

from luma.agent import friendcheck, style

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


if __name__ == "__main__":
    unittest.main()
