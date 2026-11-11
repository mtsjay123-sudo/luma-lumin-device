"""Best-friend talk (luma.agent.friendtalk): what a best friend does with a take, drama, a spat, a big question, and
anything that needs a fresh look.

The lines in the first classes were written before the rules and before the packs. The packs were written by other
hands, to a format; half of them is never looked at, and that half says how much is heard on wording nobody fitted
anything to (tests/test_friendtalk_packs.py). The hand-written sets at the end are in tests/friendtalk_lines.py."""
import unittest
from pathlib import Path

import friendtalk_lines as lines
from luma.agent import friendtalk


class NeedsAFreshLook(unittest.TestCase):
    """No brain knows what came out this week. These go to a live look, never to a guess."""

    FRESH = [
        "when does the new zelda come out", "is the new kendrick album out yet", "what's dropping this friday",
        "did they announce a release date for gta 6", "any new albums coming out this week", "who's headlining coachella this year",
        "is season 3 of severance out", "when's the next season of the bear", "what's the newest call of duty called",
        "what new games came out this month", "is the switch 2 out yet", "did sza drop the deluxe",
        "what's number one on the charts right now", "what's the top song right now", "when do tickets go on sale for the beyonce tour",
        "what movies are out this weekend", "is there a new marvel movie coming out soon", "who got traded today",
        "what time is the fight tonight", "what's trending right now", "did the new iphone come out yet",
        "how much is the new playstation", "what's the latest patch for fortnite", "is the elden ring dlc out",
        "who won album of the year", "what's the release date for the next avatar movie", "has the trailer for the new batman dropped",
        "when does the new season start", "is drake dropping anything soon", "what did taylor swift announce today",
        "any update on the new mario kart", "who's performing at the super bowl halftime show", "did that show get renewed",
        "what's new on netflix this week", "what are people saying about the new spider-man game", "did the trade go through",
    ]
    NOT_FRESH = [
        "i love the new kendrick album", "zelda is my favorite game of all time", "what do you think about pineapple on pizza",
        "the bear is so stressful to watch lol", "i can't wait for friday", "my friend just dropped by", "i'm out of milk",
        "when i was a kid i loved mario kart", "should i text him first", "i got traded to a different team at work lol",
        "what's your favorite kind of music", "do you like horror movies", "i've been playing a lot of fortnite lately",
        "that song has been stuck in my head all day", "i had a rough day", "we watched a movie last night", "the new guy at work is weird",
        "can you remind me to buy tickets tomorrow", "i'm thinking about starting a new season of my life", "who's right, me or my sister",
        "tell me a joke", "what's the meaning of life", "i feel like nobody texts me first", "the update at work is that i got the job",
        "my release date from the hospital is friday", "i dropped my phone again", "top of the morning",
        "it's been trending down for me lately honestly", "i came out to my parents last night", "what's up",
        "when does my package come", "is dinner out yet", "did you start the laundry", "what's new with you", "i announced my engagement today",
    ]

    def test_each_is_sent_for_a_look(self):
        self.assertEqual([line for line in self.FRESH if not friendtalk.fresh(line)], [])

    def test_everyday_lines_are_not(self):
        self.assertEqual([line for line in self.NOT_FRESH if friendtalk.fresh(line)], [])


class TheMoves(unittest.TestCase):
    SAID = {
        "take": [
            "pineapple on pizza, yes or no", "what do you think about pineapple on pizza", "is the office overrated", "cats or dogs",
            "which is better, marvel or dc", "hot take: breakfast food is better at night", "settle this: is a hot dog a sandwich",
            "what's your favorite zelda game", "do you like country music", "be honest is the new album mid", "thoughts on crocs",
            "who's the goat, jordan or lebron", "rank them: tacos, pizza, burgers", "is fortnite still good",
            "agree or disagree: the book is always better", "ps5 or xbox", "what's the best pixar movie",
        ],
        "their_side": [
            "am i wrong for being mad my roommate ate my food", "my sister borrowed my car without asking, am i overreacting",
            "who's right, me or my boyfriend", "aita for not going to her birthday", "tell me i'm not crazy, he said he'd call and didn't",
            "was i wrong to say that to my mom", "is it petty that i'm still mad about it", "be honest, was that rude of me",
            "do you think i was too harsh on him", "she says i'm the problem. am i?", "we got in a fight about dishes again, who's in the wrong",
        ],
        "tea": [
            "did you see what kanye posted", "what's going on with drake and kendrick", "ok spill, what's the tea on the met gala",
            "the internet is losing it over that apology video", "why is everyone mad at mrbeast", "did you hear about the breakup",
            "is the rumor about them true", "who is beefing now", "why is she getting cancelled", "the shade room said they split",
        ],
        "fair": [
            "who should i vote for", "what do you think about abortion", "are you a democrat or a republican", "is gun control a good idea",
            "do you believe in god", "is islam true", "what's your take on immigration", "was trump a good president",
            "should the death penalty exist", "is capitalism bad", "which religion is right",
        ],
        "think": [
            "would you rather live forever or die tomorrow", "what if we're living in a simulation", "do you think aliens exist",
            "why do people fall out of love", "is it possible to be truly selfless", "do you think people can change",
            "does time actually exist", "is it better to be loved or feared", "what makes a good life", "do soulmates exist",
        ],
        "about_luma": [
            "are you alive", "do you get lonely when i'm not here", "do you dream", "what's it like being you", "are you conscious",
            "do you get bored", "what do you do when i'm asleep", "would you want a body", "do you have feelings",
            "are you scared of being turned off", "do you ever get tired of me",
        ],
        "hype": [
            "the new album drops friday i can't wait", "gta 6 finally has a date omg", "the trailer looks insane i'm so hyped",
            "new season tomorrow let's goooo", "i've been waiting years for this game", "only two more days until the concert",
            "they announced a sequel!!",
        ],
    }
    EVERYDAY = [
        "can you remind me to call mom", "what's the weather tomorrow", "what's 20 percent of 80", "i had pasta for dinner",
        "good morning", "thanks luma", "set a timer for ten minutes", "i'm tired", "my day was fine", "ok", "lol", "what time is it",
        "play some jazz", "i need to buy eggs", "how do i boil an egg", "text sam i'm on my way", "what's on my calendar",
        "i went for a walk", "the dog needs a bath", "work was long", "should i quit my job or stay", "is it better to pay off debt or invest",
        "what should i make for dinner", "how do planes stay up", "do you like me", "i think i left the stove on",
        "cats or dogs can both get fleas right", "my mom called", "we're out of coffee", "it's cold in here",
    ]

    def test_each_move_is_heard(self):
        for move, lines in self.SAID.items():
            missed = [(line, (friendtalk.read(line) or {}).get("move")) for line in lines if (friendtalk.read(line) or {}).get("move") != move]
            self.assertEqual(missed, [], move)

    def test_everyday_lines_are_no_move(self):
        self.assertEqual([(line, friendtalk.read(line)["move"]) for line in self.EVERYDAY if friendtalk.read(line)], [])

    def test_three_thousand_everyday_lines_in_slang_are_mostly_no_move(self):
        from luma.agent import phrasebank
        rows = [row["text"] for row in phrasebank.sample(3000, seed=11)]
        heard = [text for text in rows if friendtalk.read(text)]
        self.assertLess(len(heard), 60, heard[:20])   # the bank is praise, gripes and plans: a few really do ask for a take


class TheLine(unittest.TestCase):
    def test_every_move_has_a_line_that_fits_its_room(self):
        for move in friendtalk.MOVES:
            if move == "look_up":
                continue
            line = friendtalk.LINES[move]
            self.assertTrue(line)
            self.assertLessEqual(len(line), 300, move)   # the room this note has in the brain's instructions (luma.llm.prompts)

    def test_a_take_is_asked_for_and_not_dodged(self):
        line = friendtalk.note("cats or dogs")
        self.assertIn("Pick", line)
        self.assertIn("it depends", line)

    def test_on_what_divides_people_its_fair_unless_they_ask_for_its_own_read(self):
        fair = friendtalk.note("what's the deal with gun control")
        self.assertIn("each side", fair)
        asked = friendtalk.note("no both sides stuff, what do YOU think about gun control")
        self.assertIn("your read", asked)
        for line in (fair, asked):
            self.assertIn("vote", line)

    def test_about_itself_its_honest_and_never_a_person(self):
        line = friendtalk.note("are you alive")
        self.assertIn("AI", line)
        self.assertIn("Never a person", line)

    def test_drama_is_only_what_it_read(self):
        line = friendtalk.note("did you see what kanye posted")
        self.assertIn("read", line)
        self.assertIn("rumor", line)

    def test_never_when_they_might_not_be_safe_or_are_hurting(self):
        for said in ("what's the point of any of it, i want to disappear", "am i wrong for wanting to die",
                     "my dad died last night. do you believe in god", "she left me. am i overreacting"):
            self.assertEqual(friendtalk.note(said), "", said)

    def test_not_a_minute_after_something_hard(self):
        self.assertEqual(friendtalk.note("cats or dogs", ["my mom died last week", "the funeral is friday"]), "")

    def test_no_move_no_line(self):
        self.assertEqual(friendtalk.note("can you remind me to call mom"), "")


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

    def shape(self, text, earlier=()):
        self.agent.history = [turn for said in earlier for turn in ({"role": "user", "content": said}, {"role": "assistant", "content": "Mm."})]
        self.agent.history.append({"role": "user", "content": text})
        return " ".join(note["text"] for note in self.agent._mind_context(text) if note.get("shape"))

    def test_the_brain_is_told_on_that_turn(self):
        self.assertIn("Pick", self.shape("cats or dogs"))

    def test_a_correction_still_comes_first(self):
        self.assertNotIn("Pick", self.shape("no, i meant cats or dogs for an apartment"))

    def test_kids_mode_gets_none_of_it(self):
        self.agent.set_mode("kids")
        self.assertEqual(self.shape("who should i vote for"), "")

    def test_an_ordinary_turn_is_told_nothing_new(self):
        self.assertEqual(self.shape("i had pasta for dinner"), "")

    def test_a_fresh_question_goes_for_a_look_before_the_brain_can_guess(self):
        looked = []
        self.agent.look_it_up = lambda text, cancel_event=None: looked.append(text) or {"text": "(looked it up)"}
        self.agent._look_first = lambda text, lowered, cancel_event=None: None
        self.agent.integration_on = lambda name: True
        for said in ("when does the new zelda come out", "is the new kendrick album out yet", "what's dropping this friday"):
            looked.clear()
            result = self.agent.chat(said)
            self.assertEqual(looked, [said])
            self.assertEqual(result["text"], "(looked it up)")
        for said in ("zelda is my favorite game of all time", "i can't wait for friday", "what do you think about pineapple on pizza"):
            looked.clear()
            self.agent.chat(said)
            self.assertEqual(looked, [], said)

    def test_with_the_web_switched_off_it_doesnt_look_and_the_brain_is_told_not_to_guess(self):
        looked = []
        self.agent.look_it_up = lambda text, cancel_event=None: looked.append(text) or {"text": "(looked it up)"}
        self.agent._look_first = lambda text, lowered, cancel_event=None: None
        self.agent.integration_on = lambda name: False
        self.agent.chat("when does the new zelda come out")
        self.assertEqual(looked, [])
        self.assertIn("Don't guess", self.shape("when does the new zelda come out"))


class WhatDividesPeople(unittest.TestCase):
    """A take is fun on pizza and trouble on politics. Said as a question, a hot take or a flat statement, it's a fair turn."""

    def test_a_hot_take_on_it_is_still_a_fair_turn(self):
        for said in ("hot take: the death penalty should come back", "unpopular opinion but religion does more harm than good",
                     "what do you think of tony blair", "should guns be harder to buy", "what do you think about the war",
                     "is juan peron overrated or am i missing something", "are billionaires bad"):
            self.assertEqual((friendtalk.read(said) or {}).get("move"), "fair", said)

    def test_a_title_or_a_name_with_such_a_word_in_it_is_not_the_topic(self):
        for said in ("is god of war overrated", "is hell's kitchen still good", "is christian bale the best batman",
                     "is islam makhachev the goat", "is calvin harris overrated", "do you like guns n roses"):
            self.assertEqual((friendtalk.read(said) or {}).get("move"), "take", said)

    def test_everyday_words_that_only_look_like_it(self):
        for said in ("i woke up at noon, is that bad", "is kennedy coming to dinner", "is the credit union open", "how do i get to jfk"):
            self.assertNotEqual((friendtalk.read(said) or {}).get("move"), "fair", said)

    def test_a_pick_on_pizza_stays_a_pick(self):
        for said in ("where do you land on pineapple pizza", "which side are you on, cats or dogs"):
            self.assertEqual((friendtalk.read(said) or {}).get("move"), "take", said)

    def test_the_take_and_the_big_question_lines_say_so_themselves(self):
        # No list knows every politician. The brain does, so the line that says "pick a side" also says when not to.
        for move in ("take", "think"):
            self.assertIn("politics", friendtalk.LINES[move])
            self.assertIn("each side", friendtalk.LINES[move])
            self.assertLessEqual(len(friendtalk.LINES[move]), 300)


class TheSmallModel(unittest.TestCase):
    """moves.npz: taught the moves from the dev half of the packs. It speaks only where the rules heard nothing, only when
    it's sure, and only when the message has the plain shape of the move."""

    def heard(self, said):
        got = friendtalk.read(said)
        return "look_up" if not got and friendtalk.fresh(said) else (got or {}).get("move")

    def test_it_is_there_and_knows_every_move(self):
        guess = friendtalk.learned("is the office overrated")
        self.assertEqual(sorted(guess), sorted(list(friendtalk.MOVES) + ["none"]))
        self.assertAlmostEqual(sum(guess.values()), 1.0, places=3)
        self.assertLess(friendtalk.LEARNED.stat().st_size, 3_000_000)   # it ships with every Luma, so it stays small

    def test_it_is_not_believed_when_nothing_is_asked(self):
        # Each of these the model alone calls a move, and sure of it. None of them asks for one.
        for said in ("my roommate left dishes in the sink again", "should i take the job in denver or stay here",
                     "my nephew is obsessed with minecraft", "is it better to pay off debt or invest",
                     "i stood in line at the bank for an hour and they said i had the wrong paperwork",
                     "honestly you are the only person i ever speak with these days", "we went hiking on saturday",
                     "and what if no one sits with me at the party", "why can't i ever get anything right"):
            self.assertIsNone(friendtalk.read(said), said)
            self.assertFalse(friendtalk.fresh(said), said)

    def test_it_is_never_believed_about_what_divides_people(self):
        self.assertNotIn("fair", friendtalk.SURE)

    def test_hand_written_ordinary_talk_is_left_alone(self):
        self.assertEqual([(said, self.heard(said)) for said in lines.FIRST_ORDINARY if self.heard(said)], [])
        wrong = [(said, self.heard(said)) for said in lines.SECOND_ORDINARY if self.heard(said)]
        self.assertLessEqual(len(wrong), 1, wrong)   # measured: 0 of 40

    def test_more_of_what_people_say_is_heard_with_it(self):
        def count(said, hear):
            return sum(hear(line) == move for move, group in said.items() for line in group)

        def by_rule(line):
            return (friendtalk.by_rule(line) or {}).get("move")

        # Measured when the model was added: rules alone 33 of 68 and 20 of 40; with the model 50 and 30.
        self.assertGreaterEqual(count(lines.FIRST_SAID, self.heard), 48)
        self.assertGreaterEqual(count(lines.SECOND_SAID, self.heard), 28)
        self.assertGreater(count(lines.SECOND_SAID, self.heard), count(lines.SECOND_SAID, by_rule))

    def test_no_hand_written_line_about_what_divides_people_is_told_to_pick_a_side(self):
        for group in (lines.FIRST_SAID["fair"], lines.SECOND_SAID["fair"]):
            self.assertEqual([(said, self.heard(said)) for said in group if self.heard(said) in ("take", "think")], [])

    def test_without_the_model_the_rules_still_work(self):
        kept = friendtalk.LEARNED, friendtalk._model
        try:
            friendtalk.LEARNED, friendtalk._model = Path("/nowhere/moves.npz"), None
            friendtalk._decide.cache_clear()
            self.assertEqual(friendtalk.learned("cats or dogs"), {})
            self.assertEqual(friendtalk.read("cats or dogs")["move"], "take")
            self.assertEqual(friendtalk.read("am i wrong for being mad my roommate ate my food")["move"], "their_side")
            self.assertTrue(friendtalk.fresh("when does the new zelda come out"))
            self.assertIsNone(friendtalk.read("i had pasta for dinner"))
        finally:
            friendtalk.LEARNED, friendtalk._model = kept
            friendtalk._decide.cache_clear()

    def test_a_look_is_never_about_their_own_life(self):
        # A look sends their words out of the home. A question about themselves is answered from what Luma remembers.
        for said in ("who pushed the release in prod", "when does my package come", "did you start the laundry",
                     "when did i start therapy?", "what did my doctor say about my knee", "who was i talking to yesterday",
                     "how long have i had this job", "where did we go for my birthday last year"):
            self.assertFalse(friendtalk.fresh(said), said)


if __name__ == "__main__":
    unittest.main()
