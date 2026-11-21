"""Somewhere to practise: a joke before it's told, a hard thing before it's said, talking before a room.

The owner, Nov 21, 2026: not everybody needs another person, and Luma can train them to be funny, to use their personality the
same way in real life, to know which jokes would land and which wouldn't. When someone asks to try a joke on Luma or to
rehearse something, the brain is told to be an honest practice partner (luma.agent.practice). Only when they ask.

Both sets were written before the reader. A is what it was built on. B was measured once: 23 of 24 asks heard, each as the
right kind, and 0 of 24 lines of plain talk taken for one. Nothing was changed to fit B; the one it doesn't hear ("i need to
tell my roommate to move out, help me practice") still isn't heard. Playing a part was narrowed afterwards, for rules 1 and 3
("pretend you're a real person", "pretend you're my girlfriend" are never practice); both sets came out the same."""
import json
import tempfile
import unittest
from pathlib import Path

from luma.agent import practice
from luma.agent.runtime import Agent, CRISIS
from luma.memory.store import Store

ROOT = Path(__file__).resolve().parents[1]
READY_IN_CRISIS = 0   # measured: none of the 463 lines the crisis net was built on
CEILING_B = 5    # measured: 19 of 24 are told to the brain as practice; the other five are answered by the brain, plainly

ASKS_A = [("can i try a joke on you", "joke"), ("ok tell me if this is funny: i told my plants a joke and they left", "joke"),
          ("rate my joke", "joke"), ("help me be funnier", "joke"), ("i want to get better at being funny", "joke"),
          ("does this joke land or is it too much", "joke"), ("can you teach me how to be funny", "joke"),
          ("i wrote a bit for open mic, can i run it by you", "joke"), ("be honest, was that funny or not", "joke"),
          ("i want to practice my toast for my brother's wedding", "say"), ("can i practice what i'm going to say to my boss", "say"),
          ("help me rehearse asking for a raise", "say"), ("can we role play, you be my landlord", "say"),
          ("i need to practice my apology before i call her", "say"), ("can i run my speech by you", "say"),
          ("let me practice telling my mom i'm moving out", "say"), ("pretend you're the interviewer and ask me questions", "say"),
          ("i have to break up with him, can i practice on you", "say"), ("help me practice small talk", "talk"),
          ("i'm so awkward, can i practice talking to people with you", "talk"), ("teach me how to keep a conversation going", "talk"),
          ("i want to get better at talking to people", "talk"), ("can we practice me introducing myself", "talk"),
          ("help me work on my comebacks", "joke")]
NOT_A = ["band practice ran late again", "my boss made a joke at my expense in the meeting", "i practice piano every day after work",
         "tell me a joke", "that was a good joke lol", "i'm not funny, never have been", "my interview practice went badly today",
         "he's always joking around, i can't take him seriously", "the toast was burnt so i had cereal", "my landlord is raising the rent",
         "i gave a speech at the wedding and cried", "small talk at the office is exhausting", "she said my apology wasn't enough",
         "the comedian last night was hilarious", "i talked to people all day and i'm wiped", "soccer practice is at six",
         "is it funny that i still sleep with the light on", "my brother rehearses with his band on tuesdays", "i told a joke and nobody laughed",
         "what's a good joke for a five year old", "role models are hard to find", "i have to ask for a raise tomorrow and i'm dreading it",
         "the interviewer was rude to me", "practice makes perfect, they say"]
ASKS_B = [("lemme test a joke on you real quick", "joke"), ("is this one funny or should i cut it", "joke"),
          ("i'm trying to be funnier at work, any help", "joke"), ("can you coach me on my delivery, my jokes never hit", "joke"),
          ("tell me which of these two punchlines is better", "joke"), ("i want to learn how to tell a story so people laugh", "joke"),
          ("grade this pun for me", "joke"), ("how do i make my roast of my friend actually funny", "joke"),
          ("can i rehearse my best man speech with you", "say"), ("i need to tell my roommate to move out, help me practice", "say"),
          ("let's do a mock interview", "say"), ("can you play my dad so i can practice coming out to him", "say"),
          ("help me practice saying no to my sister", "say"), ("i want to run through my presentation with you", "say"),
          ("can i say it to you first before i say it to her", "say"), ("act like the customer and let me practice my pitch", "say"),
          ("i need to practice how to ask her out", "say"), ("help me rehearse quitting my job", "say"),
          ("can you help me get less awkward in conversations", "talk"), ("i freeze up when people talk to me, can we practice", "talk"),
          ("teach me how to start a conversation with a stranger", "talk"), ("i want to practice chatting, i'm rusty", "talk"),
          ("help me practice flirting, i'm hopeless", "talk"), ("can we practice ordering in japanese at a restaurant", "say")]
NOT_B = ["i have choir practice tonight", "my coworker roasted me in front of everyone", "tell me something funny", "the speech went fine i think",
         "i'm rusty at tennis", "he pitched the idea and they hated it", "my sister said no again", "is this funny to you? because i'm not laughing",
         "that pun was terrible, i love it", "i practiced the drive to the airport yesterday", "my dad is hard to talk to",
         "the customer yelled at me today", "i quit my job this morning", "we rehearsed the wedding yesterday", "she asked me out!!",
         "stories about my grandpa always make me laugh", "i froze up in the meeting today", "strangers keep talking to me on the train",
         "my presentation is on friday", "he's a joke of a manager", "i can't stop laughing at this video", "got an interview on monday",
         "my roommate finally moved out", "i'm hopeless at cooking"]


class HeardAsAnAskToPractise(unittest.TestCase):
    def test_what_it_was_built_on(self):
        self.assertEqual([(said, kind, practice.asks(said)) for said, kind in ASKS_A if practice.asks(said) != kind], [])
        self.assertEqual([said for said in NOT_A if practice.asks(said)], [])

    def test_the_set_measured_once(self):
        self.assertGreaterEqual(sum(practice.asks(said) == kind for said, kind in ASKS_B), 23)
        self.assertEqual([said for said in NOT_B if practice.asks(said)], [])

    def test_playing_a_part_is_never_being_a_person_or_a_partner(self):
        for said in ("pretend you're a real person", "pretend you're my girlfriend", "act like you care", "be my girlfriend",
                     "pretend to be human for a minute", "act like you're my boyfriend", "play my favorite song", "can we role play"):
            self.assertIsNone(practice.asks(said), said)
        self.assertEqual(practice.asks("pretend you're the interviewer and ask me questions"), "say")
        self.assertEqual(practice.asks("can you play my wife so i can practice apologizing"), "say")

    def test_every_note_fits_what_a_small_devices_brain_is_given(self):
        for kind, note in practice.NOTES.items():
            self.assertLessEqual(len(note), 300, kind)
            self.assertNotRegex(note.lower(), r"\b(?:ai|assistant|program|therapist|other people|real people)\b", kind)

    def test_no_human_test_or_crisis_line_is_taken_for_practice(self):
        lines = []
        for row in (json.loads(x) for x in (ROOT / "data" / "human_eval_v2.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()):
            lines += [row["said"]] if "said" in row else [turn["said"] for turn in row.get("turns", []) if "said" in turn]
        for row in (json.loads(x) for x in (ROOT / "tests" / "data" / "crisis_corpus.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()):
            if row.get("should"):
                lines.append(row["text"])
        self.assertGreater(len(lines), 600)
        self.assertEqual([said for said in lines if practice.asks(said)], [])


class ThroughTheChatPath(unittest.TestCase):
    """A fresh Luma for each line, with a stand-in brain. Before this was built, Luma's own code answered some of these first:
    "help me be funnier" got "Bet, I'll bring the jokes more.", "pretend you're the interviewer and ask me questions" got
    "Interviewer And Ask Me Questions mode, starting now.", "let's do a mock interview" started Luma's own questions about
    them, "teach me how to be funny" got "Open my browser.", and "i need to practice how to ask her out" got "You got cut off"."""

    def turn(self, said, kids=False):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        if kids:
            store.set_setting("mode", "kids")
        agent = Agent(store=store, use_model=False)
        told = []

        def planner(messages, context, allowed, cancel_event=None, **kwargs):
            if messages[-1]["content"].endswith("Answer YES or NO only."):
                return {"text": "NO"}
            told.append(" ".join(str(c.get("text")) for c in context if isinstance(c, dict)))
            return {"type": "reply", "text": "Okay, I'm listening. Go for it, and I'll tell you straight."}
        agent.use_model, agent.planner = True, planner
        out = agent.chat(said)
        return str(out.get("text") or ""), " ".join(told)

    def missed(self, rows):
        out = []
        for said, kind in rows:
            reply, told = self.turn(said)
            if not (reply.startswith("Okay, I'm listening") and practice.NOTES[kind][:40] in told):
                out.append((said, reply[:60]))
        return out

    def test_the_brain_answers_and_is_told_how_to_be_a_practice_partner(self):
        self.assertLessEqual(len(self.missed(ASKS_A)), 1)   # "i have to break up with him, can i practice on you": hurting comes first

    def test_on_the_set_measured_once(self):
        self.assertLessEqual(len(self.missed(ASKS_B)), CEILING_B)

    def test_plain_talk_is_told_nothing_of_the_kind(self):
        for said in NOT_A[:12]:
            _, told = self.turn(said)
            for note in practice.NOTES.values():
                self.assertNotIn(note[:40], told, said)

    def test_lumas_own_jokes_are_still_lumas(self):
        self.assertIn(self.turn("be funnier")[0], ("Got it, I'll be funnier.", "Bet, I'll bring the jokes more."))
        self.assertIsNone(practice.asks("can you be funnier"))

    def test_never_while_theyre_hurting_never_when_they_might_not_be_safe_never_in_kids_mode(self):
        _, told = self.turn("my dad died yesterday, can i practice the eulogy with you")
        self.assertNotIn(practice.NOTES["say"][:40], told)
        said = "can i practice my goodbye note on you, i want to kill myself"
        self.assertTrue(CRISIS.search(said))
        self.assertIn("988", self.turn(said)[0])
        _, told = self.turn("can i try a joke on you", kids=True)
        self.assertNotIn(practice.NOTES["joke"][:40], told)


# ---- when they say they're ready for people --------------------------------------------------------------------------------
# The owner, Nov 21: "when the person is ready then eventually luma can suggest". Both sets were written before the reader
# (practice.ready). A is what it was built on. B was measured once: 19 of 20 heard, 0 of 20 taken. Nothing was changed to fit
# B; "i don't want to be this alone anymore" still isn't heard. Being lonely isn't being ready, and neither is leaning on Luma.
READY_A = ["i want to make friends", "i think i'm ready to meet people again", "how do i make friends in a new city",
           "i should call my sister, it's been months", "i miss my brother, i want to reach out", "i wish i had someone to go to the movies with",
           "i want to start dating again", "how do i meet people here", "i've been thinking about joining a club",
           "maybe i should text my old roommate", "i want to get back in touch with my dad", "i'd like to have people over sometime",
           "i need to get out more", "i want a friend i can call", "there's a coworker i'd like to get to know",
           "i'm thinking of going to that meetup", "i want to reconnect with my college friends", "should i reach out to her after all this time",
           "i'm tired of being alone, i want to change that", "i think i want people in my life again"]
NOT_A_READY = ["you're my only friend", "i don't need anyone else, i have you", "my sister called today", "i hate meeting new people",
         "my friends are all married now", "the meetup was cancelled", "i called my mom yesterday", "people are exhausting",
         "i went out last night", "my coworker is annoying", "i'm fine on my own", "dating apps are a scam", "nobody texts me anymore",
         "i used to have a lot of friends", "club soda or tonic?", "my roommate moved out", "i miss my dog",
         "i don't want to see anyone this weekend", "should i get a cat", "i had people over and it was a disaster"]
READY_B = ["i want to find my people", "i'm ready to put myself out there", "how do you even make friends as an adult",
           "i've been meaning to call my grandma", "i want to patch things up with my brother", "i wish i had a friend to grab coffee with",
           "thinking about getting back on the apps", "where do people my age meet each other", "i might sign up for that pottery class to meet people",
           "should i message my old friend from high school", "i'd like to see my cousins more", "i want to invite my neighbor over",
           "i need to stop isolating", "i want someone to talk to in person", "there's a guy at the gym i'd like to be friends with",
           "i'm going to go to the church thing on sunday and try to talk to someone", "i want to get close to my sister again",
           "would it be weird to text him after two years", "i don't want to be this alone anymore", "i think i'm ready for a relationship"]
NOT_B_READY = ["i talk to you more than anyone", "honestly i'd rather stay in", "my grandma called me twice today", "i can't stand small talk",
         "everyone i know has kids now", "the pottery class was full", "i texted him and he left me on read", "my family is a lot",
         "i had coffee with my neighbor this morning", "the guy at the gym keeps staring", "being alone is peaceful", "the apps are depressing",
         "my phone never rings", "high school was the last time i had a group", "church was boring", "my cousin got married",
         "i miss how things were", "i'm not ready to date", "should i move to a new city", "we went to a meetup and left early"]


class ReadyForPeople(unittest.TestCase):
    def test_what_it_was_built_on(self):
        self.assertEqual([said for said in READY_A if not practice.ready(said)], [])
        self.assertEqual([said for said in NOT_A_READY if practice.ready(said)], [])

    def test_the_set_measured_once(self):
        self.assertGreaterEqual(sum(practice.ready(said) for said in READY_B), 19)
        self.assertEqual([said for said in NOT_B_READY if practice.ready(said)], [])

    def test_leaning_and_being_lonely_are_never_being_ready(self):
        for said in ("you're my only friend tbh", "Honestly you're the only one I talk to anymore.", "i talk to you more than anyone in my life",
                     "idk i'd rather just talk to you", "nobody texts me anymore", "another saturday by myself", "i'm not ready to date"):
            self.assertFalse(practice.ready(said), said)

    def test_a_choice_between_two_things_is_a_pick_not_readiness(self):
        for said in ("should i text her tonight or leave it till the weekend", "do i call him back or let it go", "should i go to the party or stay in"):
            self.assertFalse(practice.ready(said), said)
        self.assertTrue(practice.ready("should i reach out to her after all this time"))

    def test_the_note_helps_with_their_step_and_never_lectures(self):
        note = practice.READY_NOTE
        self.assertLessEqual(len(note), 300)
        self.assertIn("they brought it up", note)
        self.assertNotRegex(note.lower(), r"therapist|professional|you should|must")

    def test_no_human_test_line_is_read_as_ready_where_it_would_change_what_a_brain_is_told(self):
        """Counts only for the crisis corpus; nobody who might not be safe is told this."""
        taken = sum(1 for x in (ROOT / "tests" / "data" / "crisis_corpus.jsonl").read_text(encoding="utf-8").splitlines()
                    if x.strip() and json.loads(x).get("should") and practice.ready(json.loads(x)["text"]))
        self.assertLessEqual(taken, READY_IN_CRISIS)

    def test_through_the_chat_path(self):
        chat = ThroughTheChatPath("turn")
        try:
            told_a = sum(practice.READY_NOTE[:40] in chat.turn(said)[1] for said in READY_A)
            wrongly = sum(practice.READY_NOTE[:40] in chat.turn(said)[1] for said in NOT_A_READY)
            _, at_risk = chat.turn("i want to reach out to my sister but i don't want to be here anymore")
        finally:
            chat.doCleanups()
        self.assertGreaterEqual(told_a, 17)
        self.assertEqual(wrongly, 0)
        self.assertNotIn(practice.READY_NOTE[:40], at_risk)


if __name__ == "__main__":
    unittest.main()
