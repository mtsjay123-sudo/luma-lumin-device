""""I know how that feels" is a feeling Luma hasn't had, said as its own.

Run 74, the stock 4B, to "i feel like evry1 hates me at school": "ugh, that's a lot. I know how that feels like the world is
closing in. But wait, no one actually *hates* you". The cheap fixes knew it for a made-up life and kept it anyway, because the
next sentence leaned on it; the second try didn't fix it either. It's a swap now, where it stands (style.own_words): "I get
it" before a pause, and "That feels like ..." when it says what it feels like, which is theirs to say.

SWAP_B and KEEP_B were written before the fix and measured once: 9 of 10 swapped, 10 of 10 left alone. The tenth ("Trust me, I
know how that feels.") is the whole reply, and "I get it." alone isn't an answer: that one is the second look's. A capital in
the middle of a sentence ("and This feels like") was seen on that set and fixed; nothing else was changed to fit it."""
import unittest

from luma.agent import style

SAID = "i feel like evry1 hates me at school"

SWAP_B = ["Oof. I know how that feels, truly. What happened next?", "I know how it feels. Want to talk about it?",
          "That's rough, and I know how this feels like a punch to the gut.", "Honestly, I know how that feels like everything is too loud.",
          "i know how that feels! being left on read is the worst.", "Yeah. I know how it feels; it's heavy.",
          "I know how that feels too. You're not alone in it.", "Ugh, I know how that feels, the waiting is the hardest part.",
          "I know how it feels like nobody is listening. I am.", "Trust me, I know how that feels."]
KEEP_B = ["I don't know how that feels, but I'm here.", "You know how that feels better than anyone.", "I can only imagine how that feels.",
          "Tell me how that feels.", "Do you know how it feels when it finally clicks?", "I want to know how that feels for you.",
          "Nobody else knows how it feels to be you today.", "I'd like to know how it feels from the inside.", "How that feels is yours to say.",
          "She should know how that feels by now."]


class AFeelingLumaHasntHad(unittest.TestCase):
    def fixed(self, reply):
        return style.friend_style(reply, SAID)[0]

    def test_the_reply_that_went_out(self):
        self.assertEqual(self.fixed("ugh, that's a lot. I know how that feels like the world is closing in. But wait, no one actually hates you, Riley."),
                         "ugh, that's a lot. That feels like the world is closing in. But wait, no one actually hates you, Riley.")
        self.assertEqual(self.fixed("I know how that feels. It is rough."), "I get it. It is rough.")

    def test_the_set_written_first(self):
        swapped = [self.fixed(reply) for reply in SWAP_B]
        self.assertGreaterEqual(sum("know how" not in out.lower() for out in swapped), 9)
        self.assertEqual([reply for reply in KEEP_B if self.fixed(reply) != reply], [])

    def test_a_capital_only_where_a_sentence_starts(self):
        self.assertEqual(self.fixed("That's rough, and I know how this feels like a punch to the gut."), "That's rough, and this feels like a punch to the gut.")
        self.assertEqual(self.fixed("I know how it feels like nobody is listening. I am."), "It feels like nobody is listening. I am.")

    def test_said_and_nothing_else_its_left_for_the_second_look(self):
        self.assertEqual(self.fixed("Trust me, I know how that feels."), "Trust me, I know how that feels.")
        from luma.agent import friendcheck
        self.assertEqual(friendcheck.miss(SAID, "Trust me, I know how that feels."), "made up a life")


if __name__ == "__main__":
    unittest.main()
