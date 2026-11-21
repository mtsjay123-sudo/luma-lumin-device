"""A small worry or a low mood, said the way people say it: "lowkey scared about tomorrow", "bro i'm kinda sad today".

Not heavy, so Luma had no line for it and told the brain humor was welcome; with a "lowkey" or a "bro" in it, the
brain was told "They're joking around: be funny back". Found by reading what a brain is told on the conversations of
Human Test v2 (Nov 21, 2026); built on fresh lines, none of them the test's.

BUILT_ON / PLAY: twenty feelings said casually and twenty lines of real play or plain talk in the same words. Before:
5 of 20 got a gentle line (9 "be funny back", 6 "humor is welcome"). After: 20 of 20, none of the play lines taken.
SECOND / SECOND_PLAY: written before the change went in, measured once: 4 -> 20 of 20, none of the twenty taken.
"""
import unittest

from luma.agent import feelings, humor

BUILT_ON = [
    'lowkey scared about tomorrow',
    "bro i'm kinda sad today",
    'deadass stressed rn',
    'fr fr i feel like crap',
    'lowkey nervous for my first day',
    'lowkey dreading monday',
    'kinda nervous about the interview',
    'a little worried about my mom tbh',
    "i'm a bit scared of flying next week",
    'ngl kinda lonely tonight',
    "bruh i'm lowkey not okay",
    "sis i'm stressed about rent",
    'highkey anxious about the results',
    "no cap i've been feeling off all week",
    'honestly a bit down today',
    "bro i'm worried about my dad",
    "kinda bummed i didn't get invited",
    'lowkey sad the trip got cancelled',
    "tbh i'm nervous about seeing her again",
    "on god i'm so tired of everything",
]
PLAY = [
    'bro roast me',
    'lowkey obsessed with this song',
    "deadass the best tacos i've ever had",
    "bruh you're a mess",
    'sis that outfit ate',
    'fr fr this show is so good',
    'lowkey want pizza',
    'no cap that was hilarious',
    'bet, see you at 8',
    'ayo guess what i just found',
    'the way he tripped over nothing',
    'not the dog wearing sunglasses',
    'highkey proud of my sourdough',
    "bro i'm so hungry",
    'lowkey excited for the weekend',
    'kinda want to dye my hair',
    'a little tired but it was a good day',
    'deadass thought it was friday',
    'bruh the wifi is so slow',
    'on god these fries are fire',
]
SECOND = [
    'ngl a little scared to go back to work',
    "bro i'm lowkey stressed about finals",
    'kinda sad my friend moved away',
    'lowkey anxious about the flight',
    'tbh a bit lonely since the move',
    'honestly kinda worried about money this month',
    "bruh i'm nervous for the date tonight",
    "sis i've been kinda down lately",
    "no cap i'm scared of the results",
    'low key overwhelmed with everything rn',
    'kinda dreading the family dinner',
    "fr i'm a little homesick",
    "i'm lowkey worried she's mad at me",
    'deadass anxious about tomorrow',
    'a bit nervous about the surgery ngl',
    'highkey stressed about this deadline',
    "man i'm kinda bummed about the game",
    'slightly terrified of this presentation lol',
    'honestly just a little sad tonight',
    "dude i'm worried i'll mess it up",
]
SECOND_PLAY = [
    'lowkey craving tacos',
    'bro that movie was insane',
    'deadass forgot my own birthday',
    "sis you're hilarious",
    'ngl that burger was mid',
    'highkey in love with this playlist',
    'kinda want to learn guitar',
    'fr fr best day ever',
    'no cap i could eat that every day',
    'bruh my cat is so dramatic',
    'a little obsessed with this show',
    'the way my dog just looked at me',
    'not the neighbor mowing at 7am',
    'honestly kinda proud of this drawing',
    'on god that game was wild',
    "bet, i'll bring snacks",
    'lowkey think i nailed it',
    'dude guess what i found at the thrift store',
    "tbh i'd rather stay in tonight",
    "man i'm so full",
]


def gentle(line):
    note = humor.turn_note(line)
    return bool(note) and "be funny back" not in note and "humor is welcome" not in note and ("warm" in note or "No jokes" in note or "on their side" in note)


class ASmallFeelingIsStillAFeeling(unittest.TestCase):
    def test_the_lines_it_was_built_on(self):
        for line in BUILT_ON:
            self.assertTrue(gentle(line), (line, humor.turn_note(line)[:60]))
        for line in PLAY:
            self.assertFalse(gentle(line), (line, humor.turn_note(line)[:60]))

    def test_the_second_set_is_the_honest_number(self):
        self.assertEqual(sum(gentle(line) for line in SECOND), 20)             # measured once: 20 of 20 (4 before)
        self.assertEqual([line for line in SECOND_PLAY if gentle(line)], [])

    def test_what_the_brain_is_told(self):
        note = humor.turn_note("lowkey nervous for my first day")
        self.assertTrue(note.startswith("They're a little nervous: be warm and easy about it"), note)
        self.assertLessEqual(len(note), 200)       # a small device's brain is given 200 characters of a note
        self.assertTrue(humor.turn_note("bro i'm kinda sad today").startswith("They're a little down"))
        self.assertTrue(humor.turn_note("slightly terrified of this presentation lol").startswith("They're a little nervous"))   # the laugh is nerves

    def test_the_subject_left_off_is_put_back(self):
        self.assertEqual(feelings._said_in_full("lowkey scared about tomorrow"), "i'm lowkey scared about tomorrow")
        self.assertEqual(feelings._said_in_full("deadass stressed rn"), "i'm stressed rn")
        self.assertEqual(feelings._said_in_full("honestly a bit down today"), "i'm a bit down today")
        for line in ("lowkey want pizza", "kinda down to get tacos", "bro that movie was insane", "so sad that show ended?"):
            self.assertIn(feelings._said_in_full(line), ("", "i'm so sad that show ended?"), line)

    def test_small_stays_small_and_big_stays_big(self):
        small = lambda line: feelings.read(line)["heavy"] is False and feelings.read(line)["strength"] == 1  # noqa: E731
        for line in ("i'm worried about my mom's surgery", "kinda bummed i didn't get invited", "a little worried about my mom tbh"):
            self.assertTrue(small(line), line)
        for line in ("i'm so worried about my mom", "i'm worried and i can't sleep", "i'm bummed, i didn't get the job", "i'm terrified about tomorrow"):
            self.assertTrue(feelings.read(line)["heavy"], line)
            self.assertIn("Read the room", humor.turn_note(line), line)

    def test_asked_for_something_and_the_ask_comes_first(self):
        self.assertEqual(feelings.note(feelings.read("i'm a bit nervous, can you quiz me"), asked=True), "")


if __name__ == "__main__":
    unittest.main()
