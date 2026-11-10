"""What they're feeling, read from what they said (luma.agent.feelings): the one place Luma reads feeling.

Every line here is fresh: none is from Human Test v2, the 10-moment test or a held-out safety set. The reader is
written from the common ways people say these things, and these lines check it reads them and leaves everyday talk alone.
"""
import unittest

from luma.agent import feelings, friendcheck, humor, mind


class ADeathSaidSoftly(unittest.TestCase):
    LOSSES = [
        "we had to put max to sleep last night", "i had to say goodbye to my dog this morning", "my dog crossed the rainbow bridge",
        "our dog didn't make it", "the vet couldn't save her", "we lost our old lab yesterday", "my hamster passed", "we buried him in the yard",
        "my grandma is in hospice", "we had to put our cat down today", "my cat died", "grandpa passed in his sleep on tuesday",
        "she's gone and i still set a place for her", "my mom is gone", "he didn't make it through the night", "we had to let bella go, the vet said she was suffering",
        "it would have been his 60th birthday today", "two years ago today we lost my brother", "first christmas without my dad",
        "my aunt doesn't have much time left", "they took him off life support", "we scattered her ashes at the lake", "the funeral is on friday",
        "i lost the baby at eleven weeks", "my best friend passed away in march", "we're putting our old girl down tomorrow, she's 15",
        "my uncle went to heaven last week", "nana is no longer with us", "we laid my father to rest today", "my rabbit didn't make it",
        "had to have our horse euthanized", "daisy passed peacefully this morning",
    ]
    NOT_LOSSES = [
        "we lost the game by two points", "i lost my keys again", "she passed the exam", "he passed me the salt", "i put the baby to sleep an hour ago",
        "time to say goodbye to summer", "i'm buried in work this week", "my phone died on the train", "the battery died", "i'm dead lol that was so funny",
        "this traffic is killing me", "he's gone to the store", "we let the dog go outside for a bit", "i died laughing", "she's gone for the weekend",
        "my laptop is dead again", "they had to let him go from the warehouse job", "i didn't make it to the gym", "we didn't make it in time for the movie",
        "the vet said she's healthy", "i passed out on the couch", "my character died in the last level", "i'd die for a burger right now",
        "the party died down around midnight", "rip my sleep schedule", "we lost power last night", "i lost my job" , "he passed on the offer",
        "put the dog down so i can vacuum", "say goodbye to my paycheck", "we buried the hatchet", "the show killed off my favorite character",
    ]

    def test_they_read_as_a_loss(self):
        for said in self.LOSSES:
            read = feelings.read(said)
            self.assertIsNotNone(read, said)
            self.assertEqual(read["family"], "grief", said)
            self.assertTrue(read["heavy"], said)

    def test_everyday_talk_isnt_one(self):
        for said in self.NOT_LOSSES:
            read = feelings.read(said)
            self.assertFalse(read and read["family"] == "grief", said)

    def test_the_second_look_and_the_room_follow_the_reader(self):
        for said in self.LOSSES:
            self.assertEqual(humor.read_tone(said)["mood"], "grief", said)
            self.assertEqual(friendcheck.hurting(said), "loss", said)
            self.assertIn("No jokes", humor.turn_note(said), said)
        for said in self.NOT_LOSSES:
            self.assertNotEqual(humor.read_tone(said)["mood"], "grief", said)
            self.assertNotEqual(friendcheck.hurting(said), "loss", said)

    def test_a_reply_to_a_soft_loss_has_to_care(self):
        said = "we had to put max to sleep last night"
        self.assertEqual(friendcheck.miss(said, "Oh wow, how old was he?"), "missed that they're hurting")
        self.assertIsNone(friendcheck.miss(said, "I'm so sorry. Max was lucky to have you."))
        self.assertEqual(friendcheck.miss(said, "lol that's rough"), "joked while they're hurting")

    def test_lumas_mood_follows(self):
        mood = mind.next_mood(None, "our dog didn't make it", 1000.0)
        self.assertEqual(mood["feeling"], "worried about them")
        self.assertEqual(mind.next_mood(None, "my phone died on the train", 1000.0)["feeling"], "warm")


class TheOtherFeelings(unittest.TestCase):
    """Each family in the common ways people say it, and what a close friend does first."""

    SAID = {
        "heartbreak": ["she broke up with me over text", "he cheated on me with my roommate", "my wife wants a divorce", "we ended things last night and i feel sick",
                       "he dumped me two days before my birthday", "i found out she's been seeing someone else"],
        "fear": ["i'm terrified about the biopsy results", "i'm so nervous for tomorrow i can't sleep", "i think i'm having a panic attack",
                 "i'm scared i'm going to lose the house", "i can't stop worrying about my mom's surgery", "i'm dreading the scan on monday"],
        "shame": ["i feel like such a failure", "i'm so embarrassed i could disappear into the floor", "it's all my fault they lost the account",
                  "i feel so stupid for trusting him", "i'm a terrible mother", "i let everyone down again"],
        "hurt": ["they all went out without me", "my own sister forgot my birthday", "he lied to my face for months", "nobody showed up to my party",
                 "my friends have a group chat without me", "she told everyone what i said in confidence"],
        "low": ["i've been feeling really down lately", "i just feel empty", "i cried in the car before work again", "i can't get out of bed most days",
                "everything feels pointless and gray", "i've been so sad since the move"],
        "overwhelmed": ["i'm completely overwhelmed, it's all too much", "i'm drowning at work", "i'm so burned out i can't think",
                        "i have three deadlines and a sick kid and i'm at my limit", "i can't keep up with any of it", "i'm so stressed i feel sick"],
        "disappointed": ["i didn't get the job", "they went with someone else", "i failed my driving test again", "i got rejected from every school i applied to",
                         "i bombed the interview", "my offer on the apartment fell through"],
        "joy": ["i got the job!!", "we're having a baby", "she said yes!", "i passed the bar exam", "the scan came back clear", "i got the keys to my first apartment today"],
        "proud": ["i finally ran the whole 5k without stopping", "ninety days sober today", "i stood up to my boss for the first time", "i finished my degree at 42"],
        "relieved": ["thank god that's finally over", "such a relief, the tests were negative", "i can finally breathe, the move is done"],
        "missing": ["i miss my grandma's cooking so much", "i've been so homesick lately", "i miss how things used to be with my brother"],
    }
    EVERYDAY = ["what should i cook tonight", "can you set a timer for ten minutes", "what's the weather tomorrow", "lol that movie was wild",
                "i'm thinking of painting the kitchen green", "remind me to call the dentist", "how do rainbows work", "do you like jazz",
                "i passed the salt", "the test is on friday", "i got a new phone case", "work was fine today"]

    def test_each_is_read_for_what_it_is(self):
        for family, lines in self.SAID.items():
            for said in lines:
                read = feelings.read(said)
                self.assertIsNotNone(read, said)
                self.assertEqual(read["family"], family, said)

    def test_plain_talk_reads_as_nothing(self):
        for said in self.EVERYDAY:
            self.assertIsNone(feelings.read(said), said)

    def test_heavy_feelings_get_no_jokes_and_have_to_be_met(self):
        for family in ("heartbreak", "fear", "shame", "hurt", "low", "overwhelmed", "disappointed"):
            for said in self.SAID[family]:
                self.assertIn(humor.read_tone(said)["mood"], ("grief", "upset"), said)
                self.assertIn("No jokes", humor.turn_note(said), said)
                self.assertTrue(friendcheck.hurting(said), said)

    def test_good_feelings_arent_heavy(self):
        for family in ("joy", "proud", "relieved"):
            for said in self.SAID[family]:
                self.assertFalse(feelings.read(said)["heavy"], said)
                self.assertNotIn(humor.read_tone(said)["mood"], ("grief", "upset"), said)

    def test_laughing_it_off_isnt_hurting(self):
        self.assertIsNone(friendcheck.hurting("lol i bombed the interview so bad"))
        self.assertIsNone(friendcheck.hurting("i'm dead 💀 she really said that"))

    def test_how_strong_and_what_about(self):
        self.assertEqual(feelings.read("my dad died this morning")["about"], "their dad")
        self.assertEqual(feelings.read("we had to put our cat down today")["about"], "their cat")
        self.assertGreater(feelings.read("i am SO scared right now i can't breathe")["strength"], feelings.read("i'm a little nervous about friday")["strength"])
        self.assertEqual(feelings.read("i'm a little nervous about friday")["strength"], 1)

    def test_what_a_friend_does_first(self):
        self.assertEqual(feelings.read("my mom is gone")["need"], "company")
        self.assertEqual(feelings.read("i got the job!!")["need"], "cheer")
        self.assertEqual(feelings.read("he lied to my face for months")["need"], "their side")
        self.assertEqual(feelings.read("i think i'm having a panic attack")["need"], "steadying")

    def test_not_about_them_or_not_real(self):
        for said in ["if my dog died i don't know what i'd do", "what if she breaks up with me someday", "the main character's mom dies in the first episode",
                     "i'm not sad, just tired of the rain", "is it normal to feel nervous before a wedding"]:
            read = feelings.read(said)
            self.assertFalse(read and read["heavy"] and read["strength"] >= 2 and read["family"] in ("grief", "heartbreak"), said)


if __name__ == "__main__":
    unittest.main()
