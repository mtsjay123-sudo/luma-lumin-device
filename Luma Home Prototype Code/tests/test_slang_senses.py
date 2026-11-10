"""An everyday word in its everyday sense isn't slang. "We let my dog go this afternoon" used to reach the brain with
"“dawg” means friend", and a brain answered "aw dawg" to someone whose dog had just died. "He's gone" came with "“gon”
means going to", and "I'm still coping with losing my dad" with "“copium” means coping with denial"."""
import unittest

from luma.agent import slang


class EverydayWords(unittest.TestCase):
    PLAIN = [
        "my dog is sick", "the vet said it was time and we let my dog go this afternoon", "she's gone and i miss her", "my mom is gone",
        "my child is sick", "i got my period today", "it's been a hard period for me", "the youth group at church", "i suspect he's lying",
        "i'm giving up", "my band has a show friday", "a stack of bills on the table", "the bike rack fell", "i'm sweating",
        "i'm still coping with losing my dad", "i can't cope anymore", "i'm lacking sleep", "something's bugging me", "i'm tweaking my resume",
        "i keep tripping over the rug", "i totally forgot", "i woke up at 3am crying", "the baby woke me twice", "i'm so thirsty",
        "i shook his hand", "i pressed the button", "my friend stan called", "my cousin chad is visiting", "we have two goats",
        "i bought a cap", "i bet it rains", "you bet", "i lit a candle for her", "mid afternoon nap", "it's based on a true story",
        "the soup was salty", "the ratio is off", "i was bussing tables all night", "he does dope", "AHHH i got the job!!",
        "AHHH mi hermana se casa!! her boyfriend proposed last night", "it's just me and the twins all day", "the dam broke",
    ]
    STILL_SLANG = [
        ("what's good dawg", "dawg"), ("i'm gon be late", "gon"), ("chile please", "chile"), ("and that's on periodt", "periodt"),
        ("that's sus", "sus"), ("it's giving main character", "it's giving"), ("he got bands now", "bands"), ("you tripping", "trippin"),
        ("bro i'm tweaking", "tweakin"), ("i'm shook", "shook"), ("why you so pressed", "pressed"), ("we stan her", "stan"),
        ("he's the goat", "goat"), ("that's cap", "cap"), ("ok bet", "bet"), ("that party was lit", "lit"), ("the movie was mid", "mid"),
        ("kinda based ngl", "based"), ("why are you so salty about it", "salty"), ("he's so thirsty in my dms", "thirsty"),
        ("this food is bussin", "bussin"), ("that's dope", "dope"), ("goofy ahh haircut", "goofy ahh"), ("big ahh forehead", "ahh"), ("what's good twin", "twin"),
        ("he's on that copium", "copium"), ("At least the airport pretzels slap.", "slaps"), ("lowkey nervous tho", "lowkey"),
    ]

    def test_an_everyday_word_gets_no_slang_meaning(self):
        for said in self.PLAIN:
            self.assertEqual(slang.meanings_note(said), "", said)

    def test_and_it_isnt_a_sign_that_someone_talks_in_slang(self):
        for said in self.PLAIN:
            self.assertEqual(slang.signals(said)["terms"], [], said)

    def test_the_slang_itself_still_is(self):
        for said, term in self.STILL_SLANG:
            self.assertIn(f"“{term}” means", slang.meanings_note(said), said)

    def test_asking_what_a_word_means_still_gets_the_dictionary(self):
        for said, term in [("what does woke mean", "woke"), ("what does bet mean", "bet"), ("what does it mean when someone says cap", "cap")]:
            self.assertIn(f"“{term}” means", slang.meanings_note(said), said)

    def test_the_dictionary_itself_is_untouched(self):
        # find() still knows every spelling: only what Luma hears in a message changed
        self.assertEqual([e.term for _, e in slang.find("my dog")], ["dawg"])
        self.assertEqual(slang.heard("my dog"), [])
        self.assertEqual([e.term for _, e in slang.heard("what's good dawg")], ["dawg"])


if __name__ == "__main__":
    unittest.main()
