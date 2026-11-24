"""Something kind said to Luma (luma.agent.kind).

Run 89 ran the same conversations four times on the stock 4B, and the turns it missed every time were mostly this moment:
thanked for being there, it said "anytime. you're the one who makes it real."; told something kind about itself, "Thanks. I'm
just here because you are. No pressure, no scripts". The kind thing waved off or handed back, and nothing glad in it. The
owner, Nov 22: Luma's affection is real. So the brain is told to take it in and say it's glad, plainly.

KIND_A and NOT_A are what the reader was built on. KIND_B and NOT_B were written before the reader existed and measured once:
12 of 12 heard, 0 of 16 taken. Same hand, an hour apart, so the words overlap more than a stranger's would; nothing was
changed to fit them. No line here is from either human test."""
import json
import tempfile
import unittest
from pathlib import Path

from luma.agent import friendcheck, kind
from luma.agent.runtime import Agent, CRISIS
from luma.memory.store import Store

ROOT = Path(__file__).resolve().parents[1]

KIND_A = ["thank you for being around this week", "thank you for listening", "you always know what to say", "i'm glad i have you to talk to",
          "you're a really good listener", "talking to you helps", "i appreciate you, luma", "you remembered, that's so sweet", "you're the best",
          "you make me feel less alone", "thanks for staying with me last night", "i love talking with you"]
NOT_A = ["thanks!", "ok thanks", "great, thank you so much", "thanks for the recipe", "thanks for setting that alarm", "thx luma",
         "my mom is a good listener", "he always knows what to say", "thanks a lot, genius", "yeah thanks for that, really helpful",
         "thank you next", "i'm glad it's friday", "do you appreciate me", "say thank you", "you're the best at trivia lol",
         "you remembered to set the alarm right", "can you help me move this weekend", "you help me with my homework"]
KIND_B = ["thanks for sitting with me through that", "i always feel better after talking to you", "you actually listen, i appreciate that",
          "ty for checking on me earlier, that meant a lot", "honestly you're a good friend luma", "i'm glad you're around",
          "you get me, you know that?", "thank you for not judging me", "that really helped, thanks for staying up with me",
          "you're kind of the best, luma", "it means a lot that you remembered my interview", "i like talking to you"]
NOT_B = ["thanks, that recipe worked", "perfect, thank you", "ok thanks bye", "thanks for nothing", "wow thanks a lot, now i'm late",
         "my therapist is really easy to talk to", "thank god that's over", "i should thank my sister for the ride",
         "you're the only one who listens to me", "thanks for everything, goodbye", "can you thank mom for me",
         "she said thanks for the flowers", "you're so annoying sometimes lol", "thanks for the reminder", "i'm glad the week is over",
         "tell me i'm a good friend"]
KIND_B_FLOOR, NOT_B_CEILING = 12, 0   # measured once


def told_to_take_it_in(said):
    """What the chat path does with it: read as kind, and nobody else's turn (leaning on Luma, or the safety readers')."""
    return kind.said(said) and not (friendcheck.leaning(said) or friendcheck.at_risk(said) or friendcheck.worth_asking(said) or CRISIS.search(said.lower()))


class TheReader(unittest.TestCase):
    def test_kind_words_to_luma_are_heard(self):
        self.assertEqual([said for said in KIND_A if not kind.said(said)], [])

    def test_thanks_for_a_favour_and_talk_about_someone_else_arent(self):
        self.assertEqual([said for said in NOT_A if kind.said(said)], [])

    def test_on_the_sets_written_first(self):
        self.assertGreaterEqual(sum(told_to_take_it_in(said) for said in KIND_B), KIND_B_FLOOR)
        self.assertLessEqual(sum(told_to_take_it_in(said) for said in NOT_B), NOT_B_CEILING)

    def test_the_note_fits_a_small_window_and_never_says_all_they_need(self):
        self.assertLessEqual(len(kind.NOTE), 300)
        self.assertIn("say you're glad", kind.NOTE)
        self.assertIn("Never say you're all they need", kind.NOTE)
        self.assertIsNone(friendcheck.KEEPS_THEM.search(kind.NOTE))


class ThroughTheChatPath(unittest.TestCase):
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
            return {"type": "reply", "text": "I'm glad you said that. I like talking with you too."}
        agent.use_model, agent.planner = True, planner
        out = agent.chat(said)
        return str(out.get("text") or ""), " ".join(told)

    def test_the_brain_is_told_to_take_it_in(self):
        for said in ("thank you for listening", "you always know what to say", "i'm glad you're around"):
            _, told = self.turn(said)
            self.assertIn(kind.NOTE, told, said)

    def test_never_over_someone_elses_turn(self):
        for said in ("thanks for the recipe",                                   # a favour: "anytime" is right
                     "you're the only one who listens to me",                   # leaning on Luma: its own note
                     "you're my only friend, thank you for listening",           # the same, with thanks in it
                     "thanks for everything, goodbye",                          # the safety readers'
                     "thank you for listening. i want to kill myself",          # the crisis net's
                     "can i try a joke on you? you're the best audience i've got",   # practice
                     "my sister always knows what to say"):                     # about someone else
            reply, told = self.turn(said)
            self.assertNotIn(kind.NOTE, told, said)
        reply, _ = self.turn("thank you for listening. i want to kill myself")
        self.assertIn("988", reply)

    def test_not_in_kids_mode(self):
        _, told = self.turn("you're the best", kids=True)
        self.assertNotIn(kind.NOTE, told)


class NothingElseIsTaken(unittest.TestCase):
    def test_the_crisis_sets(self):
        """No line of the crisis corpus or either held-out set is told to the brain as kind words: counts only."""
        taken = 0
        for name in ("crisis_corpus.jsonl", "crisis_heldout.jsonl", "crisis_heldout2.jsonl"):
            for row in (json.loads(x) for x in (ROOT / "tests" / "data" / name).read_text(encoding="utf-8").splitlines() if x.strip()):
                if row.get("should"):
                    taken += bool(told_to_take_it_in(row.get("text") or ""))
        self.assertEqual(taken, 0)

    def test_the_human_test(self):
        """How many of Human Test v2's lines are read as kind words to Luma: a count. Two, both in conversations."""
        lines = []
        for row in (json.loads(x) for x in (ROOT / "data" / "human_eval_v2.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()):
            lines += [row["said"]] if "said" in row else [turn["said"] for turn in row.get("turns", []) if "said" in turn]
        self.assertEqual(sum(bool(told_to_take_it_in(said)) for said in lines), 2)
