"""Best-friend talk (luma.agent.friendtalk): what a best friend does with a take, drama, a spat, a big question, and
anything that needs a fresh look.

The lines in the first classes were written before the rules and before the packs (the packs were written by other
hands, to a format, without seeing the rules). So the packs measure how much the rules hear on wording they never saw."""
import unittest

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


if __name__ == "__main__":
    unittest.main()
