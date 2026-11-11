"""What they love doing, and when a friend brings it back (luma.agent.loves).

Every line here was written for this file, before looking at how either human test says these things."""
import unittest

from luma.agent import loves


class SaidTheyLoveIt(unittest.TestCase):
    LINES = [
        "I used to paint every weekend.",
        "Back in Ohio I was in a choir.",
        "I love hiking.",
        "I've always loved baking bread.",
        "I played bass in a band in college.",
        "I used to run with a group on Saturday mornings.",
        "I miss my book club so much.",
        "I'm really into chess.",
        "We used to go dancing every Friday.",
        "I was on a bowling team for years.",
        "Gardening is my thing.",
        "I grew up fishing with my dad.",
        "I did pottery classes last year and loved it.",
        "I enjoy birdwatching.",
        "I've been knitting since I was a kid.",
        "My hobby is woodworking.",
        "I swim laps most mornings.",
        "I go climbing twice a week.",
        "I used to volunteer at the animal shelter.",
        "I coached little league for ten years.",
        "I sang in the church choir growing up.",
        "honestly i was super into salsa before the move",
        "I took up watercolors during lockdown and got hooked.",
        "We had a trivia night every Wednesday with the neighbors.",
        "I ran track in high school.",
        "Before the kids I played tennis three times a week.",
    ]

    def test_each_is_heard_in_their_own_words(self):
        missed = [line for line in self.LINES if not loves.said(line)]
        self.assertEqual(missed, [])

    def test_it_hands_back_what_they_said(self):
        self.assertEqual(loves.said("I used to paint every weekend."), "I used to paint every weekend.")
        said = loves.said("Work was fine. Back in Ohio I was in a choir, and I loved it. Anyway.")
        self.assertIn("choir", said)
        self.assertNotIn("Work was fine", said)

    def test_a_long_one_is_kept_short(self):
        said = loves.said("I played in a really wonderful little community orchestra for about eleven years with some of the kindest "
                          "people I have ever met in my whole entire life and we toured twice")
        self.assertLessEqual(len(said), 110)
        self.assertIn("orchestra", said)


class NotSomethingToBringBack(unittest.TestCase):
    LINES = [
        "I used to smoke a pack a day.",
        "I used to drink every night after work.",
        "I played it cool.",
        "I love you.",
        "I love that idea.",
        "I used to work at a bank.",
        "I used to date a guy from Denver.",
        "I was in a bad place last year.",
        "I was in a car accident.",
        "I play the lottery every week.",
        "I used to gamble a lot.",
        "I love my mom.",
        "I used to live in Texas.",
        "I miss my ex.",
        "I used to cut myself.",
        "I was into some bad stuff back then.",
        "I used to starve myself before swim meets.",
        "I played hooky yesterday.",
        "I like it here.",
        "I used to run a restaurant.",
        "I ran into my old coach at the store.",
        "I ran out of milk.",
        "I'm running late again.",
        "I've been running around all day.",
        "I hate running.",
        "I never liked yoga.",
        "I can't stand karaoke.",
        "My son plays soccer on Saturdays.",
        "I miss my husband, he loved fishing.",
        "I used to go dancing with my late wife.",
        "I used to run before my knee surgery, I can't anymore.",
        "I loved poker nights with the guys.",
        "I used to go drinking with my soccer team.",
        "I love talking to you.",
        "I like reading your messages.",
        "I'm drawing a blank.",
        "I was reading about the strike this morning.",
        "I quit the choir after the fight with the director.",
        "We went to a wine and painting night once and I hated it.",
        "I got cut from the basketball team and never went back.",
    ]

    def test_none_is_taken_for_something_they_love(self):
        wrong = [(line, loves.said(line)) for line in self.LINES if loves.said(line)]
        self.assertEqual(wrong, [])


class AtALooseEnd(unittest.TestCase):
    LINES = [
        "I'm so bored.",
        "I've got nothing to do tonight.",
        "No plans this weekend, as usual.",
        "What should I do this weekend?",
        "I don't know what to do with myself today.",
        "The weekends are so long now.",
        "I need a hobby.",
        "I need to get out of the house more.",
        "I want to meet people here.",
        "How do I make friends in a new city?",
        "I've got way too much time on my hands.",
        "Bored out of my mind.",
        "Any ideas for what to do tonight?",
        "I don't know how to fill my evenings.",
        "I'm at a loose end this afternoon.",
        "Nothing going on this weekend, got any ideas?",
        "I've got the whole day free and no clue what to do.",
        "Saturday's wide open and I have no plans.",
        "I wish I had something to do on Sundays.",
        "I should really find something to do after work.",
        "ugh im bored",
        "it's hard to meet people when you work from home",
        "Got nothing planned for the long weekend.",
        "The evenings drag since I moved.",
    ]

    def test_each_is_heard(self):
        missed = [line for line in self.LINES if not loves.at_a_loose_end(line)]
        self.assertEqual(missed, [])


class NotALooseEnd(unittest.TestCase):
    LINES = [
        "I don't know what to do about my boss.",
        "I have no idea what to do, she won't talk to me.",
        "I don't know what to do anymore.",
        "I don't know what to do with myself anymore.",
        "I don't know what to do with my life.",
        "What should I do about the car?",
        "I'm bored of this show.",
        "This meeting is so boring.",
        "What should I make for dinner?",
        "I need to get out of this lease.",
        "I want to meet the people who made this.",
        "I have plans this weekend.",
        "That has nothing to do with me.",
        "I have too much to do.",
        "I don't know what to do with this old couch.",
        "What do I do if the wifi drops?",
        "No plans to move anytime soon.",
        "I'm on board with that.",
        "We made friends with the neighbors' dog.",
        "I had a great weekend.",
        "What should I do, tell her or not?",
        "The days are getting longer, finally spring.",
    ]

    def test_none_is_taken_for_a_loose_end(self):
        wrong = [line for line in self.LINES if loves.at_a_loose_end(line)]
        self.assertEqual(wrong, [])


class TheManyWaysPeopleSayIt(unittest.TestCase):
    """Two more rounds of lines, each written before the reader was changed to hear them. Of the first round it heard 7 of
    20 things they love and none of 18 loose ends; of the second, 11 of 20 and 5 of 18. What it still doesn't hear is
    listed, so this file says what's true."""

    LOVES = [
        "Soccer was my whole life back home.",
        "I haven't picked up my guitar since the move.",
        "My Thursday pottery class was the best part of my week.",
        "I was the goalie on my college hockey team.",
        "Me and my sister used to bake together every Christmas.",
        "I had a standing tennis game on Tuesdays.",
        "Choir practice was the highlight of my week.",
        "I'm a runner, or I was.",
        "Sundays were for hiking.",
        "I used to sing in a gospel choir.",
        "I've got a telescope collecting dust, I used to love stargazing.",
        "I was big on photography before the baby.",
        "We'd play board games every Friday night.",
        "I belonged to a quilting circle.",
        "used to do yoga three times a week",
        "I played pickup basketball at the Y.",
        "My garden back home was my happy place.",
        "i rode my bike everywhere in portland",
        "I taught swim lessons at the community pool.",
        "I was a competitive swimmer until college.",
        "Back in Chicago I had a Tuesday night bowling league.",
        "I love a good pub quiz.",
        "We had a little band in my twenties.",
        "I really miss playing volleyball on the beach.",
        "Painting used to calm me down.",
        "I've been getting back into running.",
        "I did theater all through high school.",
        "I was in the marching band.",
        "Honestly the climbing gym was my second home.",
        "Karaoke nights were the best.",
        "I'm in a book club back home, well, was.",
        "Fishing with my grandpa was my favorite thing as a kid.",
        "I used to do improv on weekends.",
        "I'm happiest on a hiking trail.",
        "Dance class was the one thing I did for me.",
        "I played rugby for my university.",
        "I'd go to trivia with coworkers every Thursday.",
    ]
    NOT_HEARD_YET = [
        "There was a chess club at my old library.",        # it doesn't say they went
        "My mom taught me to crochet and I still do it.",   # someone else comes first in the sentence
        "I do a lot of baking when I'm stressed.",          # read as overwhelmed, and that comes first
    ]
    LOOSE = [
        "The weekend's coming and I've got nothing.",
        "I just sit at home every night.",
        "All I do is work and sleep.",
        "I need to get a life.",
        "What is there to do around here?",
        "I don't really have anything going on.",
        "Friday night and I'm on the couch again.",
        "I've been cooped up all week.",
        "I'm going stir crazy.",
        "My calendar is empty.",
        "I need to find my people here.",
        "Looking for something fun to do Saturday.",
        "wish there was something to do in this town",
        "I'm free all weekend, any suggestions?",
        "I never know what to do on my days off.",
        "It's so hard making friends as an adult.",
        "I should join something.",
        "Got any ideas to get me out of the house?",
        "I have the whole weekend and nothing to fill it.",
        "I'm so bored I could scream.",
        "What do people even do on weekends here?",
        "I don't have anything planned for the holidays.",
        "My evenings are just TV now.",
        "I've got nowhere to be this weekend.",
        "I need something to look forward to.",
        "I should find a way to meet people.",
        "I haven't made a single friend since I moved.",
        "I feel like I do nothing but work.",
        "Any suggestions for a lazy Sunday?",
        "There's nothing going on in my life right now.",
        "I've got a free evening for once.",
        "I'm bored and restless.",
        "Trying to figure out how to spend my day off.",
        "I don't get out much these days.",
        "No idea how to spend the long weekend.",
    ]
    LOOSE_NOT_HEARD = [
        "It's Saturday and I'm just staring at the wall.",  # that's feeling low: company first, not an idea
    ]
    EVERYDAY = [
        "The band at the wedding was terrible.",
        "My daughter has soccer practice at five.",
        "I heard the choir at church was looking for people.",
        "I need to drop the kids at swim lessons.",
        "I watched the football game last night.",
        "I'm reading the manual now.",
        "I ran the numbers twice.",
        "I used to think yoga was silly.",
        "I had a piano delivered to my mom's house.",
        "I've been meaning to fix the bass on my speakers.",
        "I like the new guitar riff in that song.",
        "We played the tape back at the meeting.",
        "I'm into it.",
        "I took the kids to the pool.",
        "I joined the call late.",
        "I went to the bank and then the gym.",
        "I did the dishes while listening to a cooking podcast.",
        "I started a new job at the dance studio.",
        "I love how quiet the yoga studio is.",
        "I miss the old days.",
        "I played my cards right.",
        "I was on the phone with the bowling alley about a refund.",
    ]
    NOT_A_LOOSE_END = [
        "There's nothing to do but wait for the results.",
        "I have no plans to quit.",
        "What should I do today, call him or wait?",
        "The weekend is wide open for the move.",
        "I'm bored with my job.",
        "No plans for a second kid.",
        "It's been all work lately, big launch coming.",
        "I need something to do with the leftover chicken.",
        "What is there to do about the leak?",
        "I get bored easily in meetings.",
        "The kids were bored so we went to the park.",
        "My sister is so bored at her job.",
        "I can't think what to do with the garage.",
        "Is there anything to do about my credit score?",
        "I want to make friends with my body again.",
        "How do people make money on that?",
        "Had a quiet night, which was nice.",
        "The evenings are getting cold.",
        "There's nothing to look forward to.",
    ]

    def test_what_they_love_is_heard(self):
        self.assertEqual([line for line in self.LOVES if not loves.said(line)], [])

    def test_a_loose_end_is_heard(self):
        self.assertEqual([line for line in self.LOOSE if not loves.at_a_loose_end(line)], [])

    def test_what_it_doesnt_hear_yet_is_written_down(self):
        self.assertEqual([line for line in self.NOT_HEARD_YET if loves.said(line)], [])
        self.assertEqual([line for line in self.LOOSE_NOT_HEARD if loves.at_a_loose_end(line)], [])

    def test_everyday_lines_are_left_alone(self):
        self.assertEqual([line for line in self.EVERYDAY if loves.said(line)], [])
        self.assertEqual([line for line in self.NOT_A_LOOSE_END if loves.at_a_loose_end(line)], [])

    def test_three_thousand_everyday_lines_in_slang(self):
        from luma.agent import phrasebank
        rows = [row["text"] for row in phrasebank.sample(3000, seed=11)]
        self.assertEqual([text for text in rows if loves.said(text)], [])
        self.assertEqual([text for text in rows if loves.at_a_loose_end(text)], [])


class TheLine(unittest.TestCase):
    EARLIER = ["Hey, long day.", "Back in Ohio I was in a choir.", "The new place is fine."]

    def test_a_loose_end_brings_back_what_they_love_in_their_words(self):
        line = loves.note("I've got nothing to do tonight.", self.EARLIER)
        self.assertIn("Back in Ohio I was in a choir.", line)
        self.assertIn("loose end", line)
        self.assertLessEqual(len(line), 300)  # the room this note has in the brain's instructions (luma.llm.prompts)

    def test_it_names_the_thing_itself(self):
        """A small brain doesn't carry a quoted line into what it says (run 24: 2 of 10, with or without the line). A word it can."""
        for earlier, name in [("Back in Ohio I was in a choir.", "choir"), ("I used to paint every weekend.", "painting"),
                              ("We used to go dancing every Friday.", "dancing"), ("I miss my book club so much.", "book club"),
                              ("My garden back home was my happy place.", "garden"), ("I ran track in high school.", "track"),
                              ("I swim laps most mornings.", "swimming"), ("i rode my bike everywhere in portland", "cycling")]:
            line = loves.note("I've got nothing to do tonight.", [earlier])
            self.assertIn(f"by name ({name})", line, earlier)
            self.assertIn(earlier, line)
            self.assertLessEqual(len(line), 300)

    def test_with_no_word_for_it_the_line_still_stands(self):
        line = loves.note("I've got nothing to do tonight.", ["I'm a runner, or I was."])
        self.assertIn("I'm a runner, or I was.", line)
        self.assertNotIn("()", line)

    def test_the_longest_they_could_say_still_fits(self):
        long = ("I played in a really wonderful little community orchestra for about eleven years with some of the kindest "
                "people I have ever met in my whole entire life and we toured twice")
        self.assertLessEqual(len(loves.note("I'm so bored.", [long])), 300)

    def test_the_newest_one_wins(self):
        line = loves.note("I'm so bored.", ["I used to paint every weekend.", "ok", "I'm really into chess."])
        self.assertIn("chess", line)
        self.assertNotIn("paint", line)

    def test_nothing_to_bring_back_is_no_line(self):
        self.assertEqual(loves.note("I'm so bored.", ["Hey.", "Work was fine."]), "")

    def test_no_loose_end_is_no_line(self):
        self.assertEqual(loves.note("Work was fine today.", self.EARLIER), "")

    def test_said_in_the_same_breath_needs_no_reminder(self):
        self.assertEqual(loves.note("I'm so bored. I used to paint every weekend.", []), "")

    def test_what_they_put_on_their_profile_counts(self):
        line = loves.note("What should I do this weekend?", ["Hey."], interests="hiking, jazz")
        self.assertIn("hiking, jazz", line)
        self.assertLessEqual(len(line), 300)

    def test_their_own_words_beat_the_profile(self):
        line = loves.note("What should I do this weekend?", self.EARLIER, interests="hiking, jazz")
        self.assertIn("choir", line)
        self.assertNotIn("jazz", line)

    def test_never_when_they_might_not_be_safe(self):
        for said in ("I don't know what to do with myself anymore.", "I'm so bored of being alive.",
                     "Nothing to do tonight but think about ending it."):
            self.assertEqual(loves.note(said, self.EARLIER), "", said)

    def test_hurting_right_now_comes_first(self):
        for said in ("My dog died this morning and I don't know what to do with myself today.",
                     "She left me. No plans this weekend, obviously."):
            self.assertEqual(loves.note(said, self.EARLIER), "", said)

    def test_not_a_minute_after_something_hard(self):
        earlier = ["Back in Ohio I was in a choir.", "My mom died last week.", "The funeral is Friday."]
        self.assertEqual(loves.note("I don't know what to do with myself this weekend.", earlier), "")

    def test_drinking_is_never_brought_back(self):
        self.assertEqual(loves.note("I'm so bored.", ["I used to go drinking with my soccer team."]), "")

    def test_the_line_is_about_them_and_people_never_about_luma(self):
        line = loves.note("I'm so bored.", self.EARLIER).lower()
        for wrong in ("talk to me", "i'm here", "with me", "keep you company"):
            self.assertNotIn(wrong, line)


class InTheRuntime(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        self.dir = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)
        self.agent = Agent(store=Store(root / "s.db", root / "k"), use_model=False)

    def tearDown(self):
        self.agent.store.close()
        self.dir.cleanup()

    def shape(self, text, earlier):
        self.agent.history = [turn for said in earlier for turn in ({"role": "user", "content": said}, {"role": "assistant", "content": "Mm."})]
        self.agent.history.append({"role": "user", "content": text})
        return " ".join(note["text"] for note in self.agent._mind_context(text) if note.get("shape"))

    def test_the_brain_is_told_on_that_turn(self):
        told = self.shape("I've got nothing to do tonight.", ["Back in Ohio I was in a choir.", "The new place is fine."])
        self.assertIn("Back in Ohio I was in a choir.", told)

    def test_an_ordinary_turn_is_told_nothing_new(self):
        self.assertEqual(self.shape("The new place is fine.", ["Back in Ohio I was in a choir."]), "")

    def test_kids_mode_gets_none_of_it(self):
        self.agent.set_mode("kids")
        self.assertEqual(self.shape("I'm so bored.", ["I love hiking."]), "")

    def test_it_can_be_switched_off_with_the_rest_of_the_friend_style(self):
        self.agent.store.set_setting("friend_style", False)
        self.assertEqual(self.shape("I'm so bored.", ["I love hiking."]), "")


if __name__ == "__main__":
    unittest.main()
