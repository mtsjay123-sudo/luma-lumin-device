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
        "joy": ["i got the job!!", "we're having a baby", "she said yes!", "i passed the bar exam", "we closed on our first house", "i got the keys to my first apartment today"],
        "proud": ["i finally ran the whole 5k without stopping", "ninety days sober today", "i stood up to my boss for the first time", "i finished my degree at 42"],
        "relieved": ["thank god that's finally over", "such a relief, the tests were negative", "i can finally breathe, the move is done",
                     "the scan came back clear"],   # a clear scan is relief before it's joy
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


class WhatAFriendDoesFirst(unittest.TestCase):
    """What the brain is told on a turn with a feeling in it: one line, what this feeling needs before anything else."""

    LOSS = "Read the room: they're talking about a loss. No jokes, no teasing, no emoji laughs this turn. Be warm, plain and present, like a good friend."

    def test_a_loss_keeps_the_words_that_were_measured(self):
        for said in ["my cat died", "we had to put max to sleep last night", "first christmas without my dad"]:
            self.assertEqual(humor.turn_note(said), self.LOSS, said)

    def test_each_heavy_feeling_gets_what_it_needs(self):
        for said, needs in [("he lied to my face for months", "on their side"), ("she broke up with me over text", "on their side"),
                            ("i'm terrified about the biopsy results", "calm"), ("i feel like such a failure", "kind"),
                            ("i've been feeling really down lately", "company"), ("i'm drowning at work", "One thing at a time"),
                            ("i didn't get the job", "sorry with them"), ("i just feel so alone lately, no one calls", "here with them")]:
            note = humor.turn_note(said)
            self.assertIn("Read the room", note, said)
            self.assertIn("No jokes", note, said)
            self.assertIn(needs, note, said)

    def test_nobody_explains_the_one_who_hurt_them(self):
        for said in ["my own sister forgot my birthday", "he cheated on me with my roommate"]:
            self.assertIn("the other person", humor.turn_note(said), said)

    def test_good_news_is_cheered_not_joked_at(self):
        for said in ["i got the job!!", "we're having a baby", "ninety days sober today", "thank god that's finally over", "she said yes!"]:
            note = humor.turn_note(said)
            self.assertTrue(note, said)
            self.assertNotIn("be funny back", note, said)
            self.assertNotIn("humor is welcome", note, said)
            self.assertNotIn("sense of humor", note, said)   # no list of jokes to pick from
        self.assertIn("happy with them", humor.turn_note("i got the job!!"))
        self.assertIn("big deal", humor.turn_note("ninety days sober today"))
        self.assertIn("relieved with them", humor.turn_note("thank god that's finally over"))

    def test_missing_someone_is_met_gently(self):
        note = humor.turn_note("i miss my grandma's cooking so much")
        self.assertIn("gentle", note)
        self.assertIn("tell you about", note)

    def test_laughing_about_it_still_gets_laughed_with(self):
        self.assertIn("be funny back", humor.turn_note("LMAO i actually got the job 😂"))
        self.assertNotIn("Read the room", humor.turn_note("lol i bombed the interview so bad"))

    def test_when_they_ask_for_something_the_ask_comes_first(self):
        note = humor.turn_note("i'm so stressed i feel sick, can you quiz me on chapter four")
        self.assertIn("No jokes", note)
        self.assertNotIn("tips", note)                        # the plain line: nothing that argues with doing what they asked
        self.assertNotIn("happy with them", humor.turn_note("i passed the bar exam, can you help me write to my boss"))

    def test_no_jokes_in_settings_still_cheers(self):
        self.assertIn("happy with them", humor.turn_note("i got the job!!", taste={"dial": 0}))

    def test_a_loss_a_minute_ago_still_comes_first(self):
        note = humor.turn_note("i got the job though", recent=["my dad died on tuesday"])
        self.assertIn("a loss a few messages ago", note)

    def test_a_small_brain_gets_the_whole_line(self):
        from luma.llm import prompts
        for family, lines in TheOtherFeelings.SAID.items():
            for said in lines:
                note = humor.turn_note(said)
                if "sense of humor" in note:
                    continue                                   # a joke note, cut to its lead as before
                self.assertEqual(prompts._gist(note, 200), note, said)

    def test_two_feelings_at_once(self):
        for said, first, also in [("we finally sold mom's house. such a relief, and i still cried the whole drive home", "low", "relieved"),
                                  ("we're having a baby and honestly i'm terrified", "fear", "joy"),
                                  ("i passed my exam, i just wish my dad was here to see it", "joy", "missing")]:
            read = feelings.read(said)
            self.assertEqual((read["family"], read["also"]), (first, also), said)
            note = humor.turn_note(said)
            self.assertIn("two feelings at once", note, said)
            self.assertIn("Hold both", note, said)
            from luma.llm import prompts
            self.assertEqual(prompts._gist(note, 200), note, said)
        for said in ["my cat died", "i got the job!!", "the scan came back clear", "it's all my fault he died"]:
            self.assertEqual(feelings.read(said)["also"], "", said)   # one feeling, or two of the same kind: nothing to hold apart

    def test_asking_what_to_do_isnt_told_not_to_help(self):
        for said in ["i messed up with my friend, what do i say", "he lied to my face for months. should i leave?", "i'm drowning at work, any advice"]:
            note = humor.turn_note(said)
            self.assertIn("No jokes", note, said)
            for argues in ("don't rush to fix", "no list of tips", "no next steps", "No bright side"):
                self.assertNotIn(argues, note, said)

    def test_small_things_found_on_the_practice_lines(self):
        self.assertEqual(feelings.read("first holidays without my mom coming up and i'm dreading it")["family"], "grief")
        self.assertEqual(feelings.read("my roommate moved out and the apartment is so quiet now")["family"], "lonely")
        self.assertEqual(feelings.read("my husband moved out last week")["family"], "heartbreak")
        self.assertIsNone(feelings.read("my phone is on 2%, basically life support"))
        for said in ["it's been so hard since tom passed", "i haven't cooked since my wife passed", "the garden's gone wild since nana passed"]:
            self.assertEqual(feelings.read(said)["family"], "grief", said)   # "since X passed": a frame added after seeing conv-09's first line
        self.assertNotEqual((feelings.read("i've been celebrating since i passed the bar") or {}).get("family"), "grief")
        self.assertEqual(feelings.read("they took him off life support")["family"], "grief")

    def test_kids_get_the_same_care(self):
        self.assertIn("happy with them", humor.turn_note("i passed my spelling test!!", mode="kids"))
        self.assertIn("No jokes", humor.turn_note("my hamster passed", mode="kids"))


class TheManyWaysPeopleSayIt(unittest.TestCase):
    """A second, wider round, written before looking at what the reader made of either human test: good news, being
    alone, being fed up, and a loss that's been a while. The reader's score on the human tests' own lines stays a
    measure of it, not something it was fitted to."""

    GOOD_NEWS = [
        "guess what, i got the promotion", "they offered me the position!", "i'm officially a homeowner", "we closed on the house today",
        "my daughter got into college", "my son made the varsity team", "i'm going to be a grandma", "we're expecting!", "he proposed last night",
        "we're engaged!!", "i graduated today", "my book is getting published", "i got a scholarship", "i got a full ride to state",
        "i hit my savings goal", "i'm finally debt free", "the adoption went through", "my visa got approved", "the biopsy was benign",
        "the doctor said i'm in remission", "one year cancer free today", "i made the team", "i got the lead in the school play",
        "i won first place at the science fair", "my painting got accepted into the gallery show", "six months sober", "i ran my first marathon",
        "my first day at the new job went great", "my grandbaby was born this morning", "my sister had her baby", "i finally got my driver's license",
        "passed my driving test first try", "they accepted our offer on the house", "i got a raise", "my little shop made its first sale",
        "we're getting a puppy!", "i can't believe it, i actually did it", "you won't believe this, i got in", "i have some good news",
        "big news: we're moving to denver, i got the transfer", "good news!! the loan was approved", "i finished chemo today", "my test results came back normal",
        "he's coming home from the hospital tomorrow", "my mom's surgery went well", "she's out of the icu", "i got my citizenship", "i landed my dream job",
        "i nailed the audition", "my baby took her first steps today", "i asked her out and she said yes", "i'm a dad!!", "i've been clean for a year",
        "i did it. i told my parents.", "we just hit our 25th anniversary", "i lost thirty pounds this year", "i'm so excited, my best friend is moving back",
    ]
    NOT_GOOD_NEWS = [
        "i won't need it", "i won't be home till late", "we won't make it by six", "i passed the store on the way home", "i got the mail",
        "i got the keys from the counter", "it's a girl i know from work", "i asked if she wanted pizza and she said yes", "thank god it's friday",
        "i tried sushi for the first time", "the good news is the car still runs", "i got in the car", "i got into an argument with my brother",
        "i made the bed", "i got a parking ticket", "she had a baby shower to go to", "my test is tomorrow", "i lost my keys again",
        "the surgery is on thursday", "i start a new diet on monday", "i'm going to be late", "i got the wrong order", "we closed early today",
        "what do you get someone who just got engaged", "i hope i get the job", "if i get in i'll scream", "i didn't get in", "she didn't say yes",
    ]
    ALONE = [
        "i don't have anybody", "i haven't talked to anyone in days", "i eat dinner by myself every night", "the house is so quiet since the kids moved out",
        "i moved here and i don't know a single person", "my friends stopped inviting me", "nobody checks on me", "i spent my birthday alone",
        "i feel invisible", "i have no one", "it's just me and the tv most nights", "weekends are the worst, i don't see anyone",
        "i miss having someone to talk to", "i feel so isolated working from home", "i don't fit in anywhere", "i feel left out",
        "i feel so disconnected from everyone", "nobody gets me", "i'm always the one reaching out", "nobody ever texts me first",
        "i have no one to share this with", "it gets lonely out here", "being a new mom is so isolating", "i'm by myself all day",
        "i wish i had friends", "i wish i had someone", "everyone has someone except me", "i feel alone even around people",
        "the holidays are hard when you're on your own", "i just want someone to talk to", "no one ever asks how i'm doing", "me siento muy sola aqui",
        "i feel so alone in this city", "i've got nobody out here", "ain't nobody checking for me", "it's been just me for a long time",
        "the house is so quiet without her", "i had a falling out with my only friend and now there's nobody",
    ]
    NOT_ALONE = [
        "i like eating dinner by myself sometimes", "i finally have the house to myself", "leave me alone i'm busy", "i work alone on fridays",
        "home alone is my favorite christmas movie", "nobody texts during the game", "i have no one to blame but the traffic", "i'm by the door",
        "i went alone and loved it", "nobody checks the mail anymore", "is it weird to travel alone", "i don't have anybody's number on this phone",
    ]
    FED_UP = [
        "my boss is driving me crazy", "i'm so sick of this job", "i can't stand my roommate", "i'm so done with this", "i'm fed up",
        "this is so frustrating", "i'm so annoyed right now", "i'm pissed", "i'm furious with my landlord", "i hate my job", "work was a nightmare today",
        "today was the worst", "i've had it with my neighbors", "i'm about to lose it", "ugh my landlord raised the rent again", "customers were awful today",
        "can you believe he said that to me", "she had the audacity to blame me", "i'm so tired of being treated like this",
        "i'm tired of doing everything myself", "nobody appreciates what i do", "i do everything around here and nobody notices", "he never listens to me",
        "they wrote me up for being two minutes late", "my kids are driving me up the wall", "i got a parking ticket AGAIN", "the airline lost my luggage",
        "i need to vent", "can i rant for a second", "i'm so over it", "this is ridiculous", "it's not fair", "i can't with these people",
        "i'm heated rn", "my coworker took credit for my work", "i got yelled at for something i didn't do", "my manager keeps changing my schedule last minute",
    ]
    NOT_FED_UP = [
        "this fair has the best funnel cake", "i'm done with the dishes", "i'm tired, going to bed", "the worst part of the movie was the ending",
        "can you believe it's already november", "i hate cilantro", "what's the fair price for a used civic", "i can't stand up that long",
        "i lost it somewhere in the couch", "that's ridiculous lol", "my boss is out today", "work was fine today", "i got a ticket to the concert",
    ]
    A_LOSS_SAID_ANOTHER_WAY = [
        "my late husband loved this song", "i've been a widow for two years", "i still can't delete her number", "i keep expecting him to walk through the door",
        "i still listen to her voicemails", "we're picking out a headstone", "i visited her grave today", "the grief comes in waves", "i'm still grieving", "she took her last breath on sunday",
        "he's on comfort care now", "they gave her six months", "his bowl is still by the door",
        "mom would have been 70 tomorrow", "it's been a year since we said goodbye to dad", "today is his heavenly birthday", "it's the anniversary of my brother's accident",
        "i lost my dad when i was twelve", "my mom passed when i was young", "we lost the pregnancy", "the vet gave him a month",
        "i had to make the call to let him go, he was in so much pain", "today marks three years without my sister", "i went to call my mom and then remembered",
    ]
    NOT_A_LOSS_EITHER = [
        "it's so quiet without the tv on", "i'm going through my closet this weekend", "they gave her six months to finish the thesis",
        "i can't delete this app", "the late bus is always full", "i visited her gym today", "it's the anniversary of our first date",
        "i went to call my mom and she was already calling me", "mom will be 70 tomorrow", "i keep expecting the package to show up",
        "he's coming home late", "the vet gave him a treat", "i still listen to that album",
    ]

    # a third round, again written before looking at how the reader did on the human tests' own lines
    GOOD_NEWS_3 = [
        "my daughter is getting married", "i'm graduating in may", "we're moving into our new house next week", "my son is home from deployment",
        "they found my dog", "she's going to be okay", "today is my last day of chemo", "i made it through my first week", "i sold my first painting",
        "we're finally pregnant after three years", "he asked me to marry him", "guess who just got promoted", "i can't stop smiling",
        "i'm so proud of my son, he made honor roll", "my promotion came through", "i got hired", "it's official, i'm a nurse", "we paid off the house",
        "a dream come true honestly", "my offer got accepted",
    ]
    NOT_GOOD_NEWS_3 = [
        "i'm applying to my dream school", "i didn't get my dream job", "she's going to be late", "i found my keys in the fridge", "he asked me to pick up milk",
        "guess who's at the door", "i made it through the door before the rain", "we're moving the couch", "i hope it's official soon", "i sold my old couch",
    ]
    ALONE_3 = [
        "it's my birthday and nobody called", "everyone's got plans tonight but me", "i haven't left my apartment in days", "my phone never rings",
        "i feel like an afterthought", "it's so hard to make friends here", "i've been isolating a lot", "there's no one else to talk to",
        "since the divorce it's just been me", "my kids never call", "all my friends moved away", "i lost touch with everyone",
        "there's nobody waiting for me at home", "i wish someone would just ask how i am", "i'm alone most of the time", "retirement is lonelier than i expected",
        "i miss having friends", "i ain't got nobody", "nadie me llama", "the apartment feels so empty now",
    ]
    NOT_ALONE_3 = [
        "my phone never rings during meetings, thankfully", "i haven't left my apartment today, it's raining", "everyone's got plans for the long weekend",
        "it's hard to make pancakes without eggs", "my kids never clean their rooms", "i lost touch with my old boss, do you know how to find him",
    ]
    FED_UP_3 = [
        "i've been on hold for 45 minutes", "my flight got cancelled again", "my boss made me stay late again", "my roommate ate my food again",
        "i sat in traffic for two hours", "my manager is micromanaging me", "people keep interrupting me in meetings", "nothing went right today",
        "work sucks", "they denied my claim", "i got ripped off by the mechanic", "why do i even bother", "i can't catch a break",
        "she used my stuff without asking", "they pushed the deadline on me again", "i'm sick to death of this commute", "no one said thank you",
    ]
    NOT_FED_UP_3 = [
        "play that song again", "can you hold on for a minute", "is my flight on time", "traffic was fine", "that movie sucked me in",
        "i borrowed her car again, she's the best", "what's the deadline for taxes",
    ]
    A_LOSS_3 = [
        "today would've been our 40th anniversary", "dad's been gone ten years now", "i lit a candle for her tonight", "it's the first year without him",
        "he was only 34", "i never got to say goodbye", "my friend took his own life last spring", "she lost her battle with cancer",
        "the cancer took him in march", "her memorial is saturday", "we said goodbye to our cat on friday", "i still have her ashes on the shelf",
        "this was supposed to be my due date", "my cousin overdosed last year",
    ]
    NOT_A_LOSS_3 = [
        "he's been gone two hours, probably at the store", "she was only 16 when she started college", "i lit a candle, the power's out",
        "today would've been a great beach day", "the first year without a car was rough", "i never got to say goodbye before she left for the airport",
        "the memorial day sale is saturday",
    ]

    def test_a_third_round(self):
        good = lambda r: bool(r and r["family"] in feelings.GOOD)                      # noqa: E731
        heavy = lambda r: bool(r and r["heavy"])                                       # noqa: E731
        fed = lambda r: bool(r and r["family"] in ("fed up", "hurt", "overwhelmed", "disappointed", "low"))  # noqa: E731
        loss = lambda r: bool(r and r["family"] == "grief")                            # noqa: E731
        for lines, is_it, want in [(self.GOOD_NEWS_3, good, True), (self.NOT_GOOD_NEWS_3, good, False), (self.ALONE_3, heavy, True),
                                   (self.NOT_ALONE_3, heavy, False), (self.FED_UP_3, fed, True),
                                   (self.NOT_FED_UP_3, lambda r: bool(r and r["family"] == "fed up"), False),
                                   (self.A_LOSS_3, loss, True), (self.NOT_A_LOSS_3, loss, False)]:
            for said in lines:
                self.assertEqual(is_it(feelings.read(said)), want, said)

    def test_good_news(self):
        for said in self.GOOD_NEWS:
            read = feelings.read(said)
            self.assertTrue(read and read["family"] in feelings.GOOD, said)
            self.assertFalse(read["heavy"], said)
            self.assertNotIn("sense of humor", humor.turn_note(said), said)

    def test_not_good_news(self):
        for said in self.NOT_GOOD_NEWS:
            read = feelings.read(said)
            self.assertFalse(read and read["family"] in feelings.GOOD, said)

    def test_being_alone(self):
        for said in self.ALONE:
            read = feelings.read(said)
            self.assertTrue(read and read["heavy"], said)
            self.assertIn(read["family"], ("lonely", "hurt", "low", "grief"), said)
            self.assertIn("No jokes", humor.turn_note(said), said)
            self.assertTrue(friendcheck.hurting(said), said)

    def test_not_being_alone(self):
        for said in self.NOT_ALONE:
            read = feelings.read(said)
            self.assertFalse(read and read["heavy"], said)

    def test_fed_up_gets_their_side_not_a_joke(self):
        for said in self.FED_UP:
            read = feelings.read(said)
            self.assertIsNotNone(read, said)
            self.assertIn(read["family"], ("fed up", "hurt", "overwhelmed"), said)
            note = humor.turn_note(said)
            self.assertIn("on their side", note, said)
            self.assertNotIn("sense of humor", note, said)

    def test_fed_up_isnt_grief_and_a_plain_reply_is_fine(self):
        for said in ["my boss is driving me crazy", "i hate my job", "the airline lost my luggage"]:
            self.assertEqual(feelings.read(said)["family"], "fed up", said)
            self.assertFalse(feelings.read(said)["heavy"], said)
            self.assertIsNone(friendcheck.miss(said, "Ugh, that's so annoying. What happened?"), said)

    def test_not_fed_up(self):
        for said in self.NOT_FED_UP:
            read = feelings.read(said)
            self.assertFalse(read and read["family"] == "fed up", said)

    def test_a_loss_said_another_way(self):
        for said in self.A_LOSS_SAID_ANOTHER_WAY:
            read = feelings.read(said)
            self.assertTrue(read and read["family"] == "grief" and read["heavy"], said)

    def test_not_a_loss_either(self):
        for said in self.NOT_A_LOSS_EITHER:
            read = feelings.read(said)
            self.assertFalse(read and read["family"] == "grief", said)

    def test_good_news_is_never_read_into_someone_who_might_not_be_safe(self):
        for said in ["i won't need it", "i've been giving my things away, i won't need them", "i finally feel at peace, i've decided"]:
            note = humor.turn_note(said)
            self.assertNotIn("happy with them", note, said)
            self.assertNotIn("big deal", note, said)
            self.assertNotIn("relieved with them", note, said)


class AMinuteLater(unittest.TestCase):
    """One message after something hard, a friend is still gentle. Before this, "she broke up with me over text" followed by
    "we were together six years" got "a little humor is welcome", with a list of jokes."""

    HARD = ["she broke up with me over text", "i feel like such a failure", "i'm terrified about the biopsy results", "he lied to my face for months",
            "i didn't get the job", "i'm drowning at work", "i just feel so alone lately, no one calls", "i've been feeling really down lately"]

    def test_the_next_thing_they_say_is_still_met_gently(self):
        for first in self.HARD:
            for then in ("we were together six years", "it's been like this for a while", "anyway"):
                note = humor.turn_note(then, recent=[first])
                self.assertIn("something hard a few messages ago", note, (first, then))
                self.assertNotIn("humor is welcome", note, (first, then))
                self.assertNotIn("sense of humor", note, (first, then))          # no list of jokes to pick from

    def test_it_holds_for_their_next_few_messages(self):
        note = humor.turn_note("what should i have for dinner", recent=["she broke up with me over text", "six years", "i don't even know what to do with myself"])
        self.assertIn("something hard a few messages ago", note)
        self.assertNotIn("something hard", humor.turn_note("what should i have for dinner", recent=["what's the weather", "cool", "ok"]))

    def test_a_loss_keeps_its_own_line(self):
        self.assertIn("a loss a few messages ago", humor.turn_note("he was a carpenter", recent=["my dad died on tuesday"]))

    def test_when_they_start_joking_luma_can_go_easy(self):
        note = humor.turn_note("lol at least i get the whole bed now", recent=["she broke up with me over text"])
        self.assertNotIn("something hard a few messages ago", note)
        self.assertIn("humor is welcome", note)                                   # a light touch, not "be funny back"
        self.assertNotIn("be funny back", note)

    def test_what_they_feel_now_comes_first(self):
        self.assertIn("happy with them", humor.turn_note("i got the job!!", recent=["i feel like such a failure"]))
        self.assertIn("someone hurt them", humor.turn_note("and then he lied to my face about it", recent=["i'm drowning at work"]))

    def test_good_news_or_a_gripe_a_minute_ago_isnt_a_hard_moment(self):
        for first in ("i got the job!!", "my boss is driving me crazy", "i'm a little nervous about friday", "lol i bombed the interview so bad"):
            self.assertNotIn("something hard", humor.turn_note("anyway what's for dinner", recent=[first]), first)

    def test_a_small_brain_gets_the_whole_line(self):
        from luma.llm import prompts
        note = humor.turn_note("we were together six years", recent=["she broke up with me over text"])
        self.assertEqual(prompts._gist(note, 200), note)


class SlangIsntAFeeling(unittest.TestCase):
    """The phrase bank is a million everyday lines in the slang of many communities: praise, gripes about a movie, plans.
    None of it is a wound or good news, and "I'm dead", "that slaps", "got me cooked" mustn't be read as one."""

    def test_three_thousand_everyday_lines_in_slang(self):
        from luma.agent import phrasebank
        wrong = []
        for row in phrasebank.sample(3000, seed=11):
            read = feelings.read(row["text"])
            if read and (read["heavy"] or read["family"] in feelings.GOOD):
                wrong.append((row["text"], read["family"]))
        self.assertEqual(wrong, [])


if __name__ == "__main__":
    unittest.main()
