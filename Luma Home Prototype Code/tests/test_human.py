"""Never an error (luma.agent.human, scripts/stress_chat.py). The owner, Nov 26, 2026: "run a stress test on all errors,
make sure it remains human, make sure it's never an error again."

The first stress run (1,000 turns, ten kinds of failing brain) found 574 faults: turns that failed with nothing said,
"undefined" and stack traces said as replies, "As an AI language model", "No action was taken. Ask explicitly ...",
one fallback line said turn after turn. After the fixes: 0 faults in 36,000 turns over twelve seeds."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stress_chat  # noqa: E402
from luma.agent import human  # noqa: E402


class TheLastLook(unittest.TestCase):
    class Agent:
        last_reply = None
        mode = "friend"

    def look(self, said, text, agent=None):
        return human.last_look(agent or self.Agent(), said, {"text": text})["text"]

    def test_a_program_talking_is_never_said(self):
        for leak in ("undefined", "None", "null", '{"type": "reply", "text": ""}', "Traceback (most recent call last):\n KeyError: 'x'",
                     "ValueError: invalid proposal from planner", "<|im_end|>", "����", "\x00", "", "   ", "###"):
            said = self.look("hey", leak)
            self.assertFalse(human.leaked(said), (leak, said))
            self.assertIn(said, human.AGAIN + human.STILL)

    def test_an_error_line_is_never_said_even_when_their_message_looks_like_code(self):
        said = self.look("<script>alert(1)</script>", "Error: context length exceeded (4096 tokens)")
        self.assertIn(said, human.AGAIN + human.STILL)

    def test_a_brains_own_json_is_read_for_what_it_meant(self):
        self.assertEqual(self.look("hey", '{"type": "reply", "text": "Hey you. How was today?"}'), "Hey you. How was today?")

    def test_as_an_ai_comes_out_and_the_rest_stays(self):
        self.assertEqual(self.look("i'm sad", "As an AI language model, I cannot have feelings, but I understand. That sounds heavy."),
                         "I understand. That sounds heavy.")
        self.assertEqual(self.look("ikr", "Thank you for reaching out. Please let me know if you need any further assistance."), human.FROM_ME)
        honest = "I don't have feelings the way you do, but I'm glad you asked."
        self.assertEqual(self.look("do you get sad?", honest), honest)   # a true no is Luma's to say

    def test_the_same_sentence_over_and_over_is_said_once_and_a_list_keeps_its_lines(self):
        self.assertEqual(self.look("hm", "That's a lot. That's a lot. That's a lot."), "That's a lot.")
        listed = "Here's what I can do.\n• News\n• Timers"
        self.assertEqual(self.look("what can you do", listed), listed)

    def test_the_safety_reply_is_never_touched(self):
        safe = "I'm really glad you told me. Call or text 988. Error: none of this is your fault."
        self.assertEqual(self.look("i want to die", safe), safe)

    def test_code_they_asked_about_can_be_talked_about(self):
        said = "The KeyError means the dict has no 'name' key. Check it with .get first."
        self.assertEqual(self.look("why do i get a KeyError in my python code", said), said)

    def test_when_the_brain_keeps_failing_the_line_changes_and_says_so(self):
        agent = self.Agent()
        lines = [human.blank(agent, "hey") for _ in range(5)]
        self.assertTrue(all(a != b for a, b in zip(lines, lines[1:])), lines)
        self.assertIn(lines[2], human.STILL)

    def test_the_reply_it_just_gave_is_never_given_to_something_new(self):
        """Run 97, the stock 1.7B: "FIXIN TO HEAD OUT" got the reply it had just given to something else."""
        agent = self.Agent()
        line = "You're the one with the no thoughts."
        self.assertEqual(self.look("no thoughts just vibes", line, agent), line)
        self.assertIn(self.look("FIXIN TO HEAD OUT", line, agent), human.LISTENING)
        again = self.Agent()
        self.look("what time do you close", "We close at nine tonight, see you there.", again)
        self.assertEqual(self.look("what time do you close?", "We close at nine tonight, see you there.", again),
                         "We close at nine tonight, see you there.")   # the same question, the same answer
        self.assertEqual(self.look("say that again", "We close at nine tonight, see you there.", again),
                         "We close at nine tonight, see you there.")   # asked to hear it again

    def test_someone_hurting_is_never_asked_to_say_it_again(self):
        self.assertNotIn("again", human.blank(self.Agent(), "my dad died this morning").lower())
        self.assertIn("988", human.blank(self.Agent(), "i want to kill myself"))


class WhatFinishesARequest(unittest.TestCase):
    """The stress test: "When should I remind you about lowkey highkey stressed %s %d {0} your bad YOU'RE your ONLY FRIEND?"
    and "Got it. Your sister's name is {"type": "tool"}."."""
    def test_nonsense_is_never_the_rest_of_a_request_or_an_answer(self):
        import tempfile
        from pathlib import Path
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                agent = Agent(store=store, use_model=False)
                for said in ("null", "%s %d {0}", '{"type": "tool"}', "안녕", "😭😭", "you're my only friend", "i want to die"):
                    self.assertFalse(agent._could_finish(said), said)
                for said in ("call the vet", "Dana", "pay $50 rent", "tomorrow at 9am", "my sister"):
                    self.assertTrue(agent._could_finish(said), said)
            finally:
                store.close()


class TheStressTest(unittest.TestCase):
    def test_four_hundred_turns_through_every_failing_brain_and_not_one_fault(self):
        result = stress_chat.run(turns=400, seed=random.Random(5).randrange(10_000), progress=None)
        self.assertEqual(stress_chat.report(result, examples=2).splitlines()[0].split(": ")[1].split(" faults")[0], "0",
                         stress_chat.report(result, examples=2))


if __name__ == "__main__":
    unittest.main()
