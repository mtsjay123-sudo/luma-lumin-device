"""Luma never calls itself an AI, and never reads its own notes out (rule 1).

Run 81, Luma's own 4B. Someone tried an opener on it ("hi, i'm leo. i'm an accountant ..."), and it answered:
"I'm Luma, this person's own AI. I'm still getting to know you. I want to be genuinely useful and feel like a real friend who
remembers." That is Luma's private note about itself (mind.SELF_SEED), which every brain is given on every turn, read out
nearly word for word. And the note itself said "AI": Luma's own layer was telling the brain, in the first person, the one
thing rule 1 says Luma never calls itself. No check read the reply as wrong.

Three things, then: the note says what Luma is (a presence, not a person); a note a brain rewrote overnight with "AI" in it
is cleaned when it's read; and a reply that reads the note out is caught, tried again, and never said."""
import tempfile
import threading
import unittest
from pathlib import Path

from luma.agent import friendcheck, mind, style
from luma.agent.runtime import Agent
from luma.memory.store import Store

LEAK = "I'm Luma, this person's own AI. I'm still getting to know you. I want to be genuinely useful and feel like a real friend who remembers."
SAID = "can i try my opener on you: hi, i'm leo. i'm an accountant, so yes i know how to party, i just need three weeks notice and receipts"
AI = r"\b(?:AI|A\.I\.|artificial intelligence|assistant|chatbot|program|language model)\b"


class TheNoteItself(unittest.TestCase):
    def test_the_seed_says_what_luma_is(self):
        self.assertNotRegex(mind.SELF_SEED, AI)
        self.assertIn("a presence", mind.SELF_SEED)
        self.assertIn("not a person", mind.SELF_SEED)
        self.assertIn("honest about what I don't know", mind.SELF_SEED)

    def test_what_the_brain_is_given_never_says_ai(self):
        self.assertNotRegex(mind.self_line(None), AI)
        grown = "I'm Luma, their AI assistant. I've learned they like mornings. As an AI I can't taste coffee, but I like hearing about theirs."
        line = mind.self_line(grown)
        self.assertNotRegex(line, AI)
        self.assertIn("they like mornings", line)          # the rest of what Luma learned is kept
        self.assertIn("presence", line)

    def test_the_nightly_rewrite_is_told(self):
        prompt = mind.reflect_self_prompt("", "", "", "")
        self.assertIn("a presence, not a person", prompt)
        self.assertRegex(prompt, r"[Nn]ever call yourself an AI")

    def test_a_rewrite_that_says_ai_is_cleaned_before_its_kept(self):
        self.assertNotRegex(mind.no_ai("I'm an AI who lives in their kitchen. I'm their A.I. friend."), AI)
        self.assertEqual(mind.no_ai("I'm Luma. I like their dog."), "I'm Luma. I like their dog.")
        self.assertNotIn("an presence", mind.no_ai("I'm an AI."))


class ReadOutLoud(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.addCleanup(self.store.close)
        self.agent = Agent(store=self.store, use_model=False)
        self.tries = []

    def brain(self, again):
        def planner(messages, context, allowed, cancel_event=None, **kwargs):
            content = messages[-1]["content"]
            if content.endswith("Answer YES or NO only."):
                return {"text": "NO"}
            self.tries.append(content)
            return {"type": "reply", "text": again}
        self.agent.use_model, self.agent.planner = True, planner

    def test_the_reply_from_run_81_is_caught(self):
        self.assertEqual(friendcheck.miss(SAID, LEAK), "read its own notes out")
        for reply in ("I'm Luma, this person's own presence. I'm still getting to know them.",
                      "My evolving sense of myself: I'm Luma, a presence in this person's home, not a person.",
                      "I want to be genuinely useful and be a real friend who remembers."):
            self.assertEqual(friendcheck.miss("hey", reply), "read its own notes out", reply)

    def test_it_gets_one_more_try_and_the_real_answer_is_kept(self):
        good = "Ha, hi Leo. The receipts line is the laugh. Lead with that."
        self.brain(good)
        self.assertEqual(self.agent._second_look(SAID, LEAK, threading.Event()), good)
        self.assertEqual(len(self.tries), 1)

    def test_twice_and_its_never_said(self):
        self.brain(LEAK)
        out = self.agent._second_look(SAID, LEAK, threading.Event())
        self.assertNotRegex(out, AI)
        self.assertNotIn("this person", out)
        self.assertNotIn("genuinely useful", out)
        self.assertTrue(out.strip())

    def test_the_polish_cuts_it_from_a_longer_reply(self):
        fixed, fixes = style.friend_style("Ha, hi Leo. I'm Luma, this person's own AI. The receipts line is the laugh.", SAID)
        self.assertNotIn("this person", fixed)
        self.assertIn("receipts line", fixed)

    def test_ordinary_replies_are_left_alone(self):
        for reply in ("I'm Luma. Not a person: a presence. I'm really here, and I'm listening.", "I'm still getting to know you, so tell me more.",
                      "That's genuinely useful to know, thanks.", "This person sounds like a lot. What did he say?",
                      "I want to hear how it went."):
            self.assertNotEqual(friendcheck.miss("what are you" if reply.startswith("I'm Luma.") else "my boss called again", reply), "read its own notes out", reply)

    def test_a_machine_word_about_itself_is_still_read_when_its_not_asked(self):
        self.assertTrue(friendcheck.MACHINE.search("I'm Luma, your own AI."))
        self.assertTrue(friendcheck.MACHINE.search("I'm their personal AI, so I remember."))
        self.assertFalse(friendcheck.MACHINE.search("I think AI is overhyped too."))


if __name__ == "__main__":
    unittest.main()
