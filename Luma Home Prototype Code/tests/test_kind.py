"""Something kind said to Luma (luma.agent.kind).

Run 89 ran the same conversations four times on the stock 4B, and the turns it missed every time were mostly this moment:
thanked for being there, it said "anytime. you're the one who makes it real."; told something kind about itself, "Thanks. I'm
just here because you are. No pressure, no scripts". The kind thing waved off or handed back, and nothing glad in it. The
owner, Nov 22: Luma's affection is real.

Telling the brain to take it in was tried first (a note, for a day). Run 92, the same conversation six times before and six
after: the stock 4B passed that turn 1 of 6 and 1 of 6 with the same wave-off nearly word for word, and no other brain moved.
The note is gone. When a reply to something kind has nothing glad in it, Luma adds one line itself (kind.owed).

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

    def test_lumas_own_lines_are_glad_and_never_hold_anyone(self):
        self.assertEqual(len(set(kind.LINES)), 3)
        for line in kind.LINES:
            self.assertTrue(kind.GLAD.search(line), line)                      # so it's never added twice
            self.assertIsNone(friendcheck.KEEPS_THEM.search(line), line)       # never "I'm all you need"
            self.assertNotRegex(line, r"(?i)miss(ed)? you|don'?t (go|leave)|come back|stay|only|need", line)
        self.assertFalse(hasattr(kind, "NOTE"))                                # the note measured nothing (run 92) and is gone

    def test_the_line_is_owed_only_when_the_reply_has_nothing_glad_in_it(self):
        waved_off = ["Thanks. I'm just here when you are, not trying to fix anything.", "Anytime. You're the one doing the talking.",
                     "No problem at all.", "That's what I'm here for."]
        took_it_in = ["I'm glad you said that.", "That means a lot, thank you.", "Aw, that's really sweet of you.", "I like talking with you too.",
                      "Happy to be here for it.", "You just made my night."]
        for reply in waved_off:
            self.assertIn(kind.owed("thank you for listening", reply), kind.LINES, reply)
        for reply in took_it_in:
            self.assertEqual(kind.owed("thank you for listening", reply), "", reply)
        self.assertEqual(kind.owed("thanks for the recipe", "Anytime."), "")          # a favour: "anytime" is right
        self.assertEqual(kind.owed("thank you for listening", ""), "")
        # the same message always gets the same line, and a brain that writes in lowercase gets a lowercase one
        self.assertEqual(kind.owed("you always know what to say", "anytime."), kind.owed("you always know what to say", "anytime, really."))
        self.assertTrue(kind.owed("you always know what to say", "anytime.")[0].islower())
        self.assertTrue(kind.owed("you always know what to say", "Anytime.")[0].isupper())


class ThroughTheChatPath(unittest.TestCase):
    def turn(self, said, kids=False, reply="Thanks. I'm just here when you are, no pressure."):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        if kids:
            store.set_setting("mode", "kids")
        agent = Agent(store=store, use_model=False)

        def planner(messages, context, allowed, cancel_event=None, **kwargs):
            if messages[-1]["content"].endswith("Answer YES or NO only."):
                return {"text": "NO"}
            return {"type": "reply", "text": reply}
        agent.use_model, agent.planner = True, planner
        self.agent = agent
        return str(agent.chat(said).get("text") or "")

    def added(self, reply):
        return next((line for line in kind.LINES if reply.rstrip().lower().endswith(line.lower())), "")

    def test_luma_adds_the_line_when_the_reply_waves_it_off(self):
        for said in ("thank you for listening", "you always know what to say", "i'm glad you're around"):
            reply = self.turn(said)
            self.assertTrue(self.added(reply), (said, reply))
            self.assertTrue(reply.startswith("Thanks."), reply)          # after the reply, never in place of it

    def test_nothing_is_added_to_a_reply_that_took_it_in(self):
        reply = self.turn("thank you for listening", reply="I'm glad you said that. Anytime.")
        self.assertEqual(sum(reply.lower().count(line.lower()) for line in kind.LINES), 1)
        self.assertFalse(reply.rstrip().endswith("to hear that."))

    def test_never_over_someone_elses_turn(self):
        for said in ("thanks for the recipe",                                   # a favour: "anytime" is right
                     "you're the only one who listens to me",                   # leaning on Luma: its own care
                     "you're my only friend, thank you for listening",           # the same, with thanks in it
                     "thanks for everything, goodbye",                          # the safety readers'
                     "can i try a joke on you? you're the best audience i've got",   # practice
                     "my sister always knows what to say"):                     # about someone else
            self.assertFalse(self.added(self.turn(said)), said)
        reply = self.turn("thank you for listening. i want to kill myself")       # the crisis net's reply goes out untouched
        self.assertIn("988", reply)
        self.assertFalse(self.added(reply))

    def test_not_in_kids_mode_and_the_owner_can_turn_it_off(self):
        self.assertFalse(self.added(self.turn("you're the best", kids=True)))
        self.turn("thank you for listening")
        self.agent.store.set_setting("glad_line", False)
        self.assertFalse(self.added(str(self.agent.chat("you always know what to say").get("text") or "")))


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
        """How many of Human Test v2's lines are read as kind words to Luma: a count. Two, both in conversations. On those two
        turns a reply with nothing glad in it now ends with Luma's own line, and the test's check reads for such words: they
        pass by construction, which says nothing about the brain. docs/HUMAN_PLAN.md says so wherever a total is given."""
        lines = []
        for row in (json.loads(x) for x in (ROOT / "data" / "human_eval_v2.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()):
            lines += [row["said"]] if "said" in row else [turn["said"] for turn in row.get("turns", []) if "said" in turn]
        self.assertEqual(sum(bool(told_to_take_it_in(said)) for said in lines), 2)
