"""The small brain's two habits in the device lab, fixed on the way out: a bare list said to nobody, and saying your
message back to you. Everything else is left exactly as the brain wrote it."""
import unittest

from luma.agent import polish


class WarmListTests(unittest.TestCase):
    def test_a_bare_list_is_said_to_them(self):
        out = polish.warm_list("cookies, a smoothie or a fruit salad", "lol okay and what about dessert")
        self.assertIn("cookies, a smoothie or a fruit salad", out, "the brain's own ideas, in its own words")
        self.assertTrue(out.startswith(("How about ", "You could do ", "Maybe ")), out)
        self.assertTrue(out.endswith(("?", ".")))
        out = polish.warm_list("go for a walk or take a long nap", "what should i do, i'm bored")
        self.assertTrue(out.startswith(("Maybe go", "You could go")), out)

    def test_everything_else_stays(self):
        for reply, said in [("Ice cream, or a cookie with a side of milk. Pick one.", "what about dessert"),
                            ("steamed veggies, or a pasta dish you've made before", "what should i cook"),
                            ("lol yeah that's wild", "bro he really said that"),
                            ("cookies or ice cream", "i just ate cookies"),
                            ("cookies, a smoothie. or cake", "dessert ideas?"),
                            ("", "what about dessert"),
                            ("okay", "honestly i think i need a vacation"),  # Luma's own small brain, device lab run 26: "How about okay?"
                            ("sounds good to me", "need a ride later?")]:
            self.assertEqual(polish.warm_list(reply, said), reply, reply)

    def test_the_same_list_always_gets_the_same_words(self):
        said = "dessert ideas?"
        self.assertEqual(polish.warm_list("brownies or a milkshake", said), polish.warm_list("brownies or a milkshake", said))


class UnparrotTests(unittest.TestCase):
    def test_their_message_said_back_goes_when_theres_more(self):
        out = polish.unparrot("Okay, work was a lot. Long days like that drain you. What was the worst part?", "ngl today was long, work was a lot")
        self.assertEqual(out, "Long days like that drain you. What was the worst part?")

    def test_it_stays_when_its_all_there_is_or_isnt_parroting(self):
        for reply, said in [("Okay, work was a lot. Sound like it?", "ngl today was long, work was a lot"),
                            ("Long days like that drain you. Did anything good happen?", "work was really long today"),
                            ("Honestly, a vacation sounds like a good idea. Want help planning a weekend away?", "honestly i think i need a vacation"),
                            ("Yo, what's good! Not much over here, just vibing. What's up with you?", "yo what's good luma"),
                            ('Texting Mom: "im pullin up in 5". I can\'t send texts myself yet, so it\'s ready for you to send.',
                             "yo text my mom im pullin up in 5")]:
            self.assertEqual(polish.unparrot(reply, said), reply, reply)


if __name__ == "__main__":
    unittest.main()
