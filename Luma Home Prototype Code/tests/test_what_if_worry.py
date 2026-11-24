"""A worry asked as a question: "what if they don't like me", "what if nobody comes" (feelings.WHAT_IF_WORRY).

Run 89, the stock 4B, on a turn it missed on all four passes: someone starting a job asked what if nobody talks to them at
lunch, and got "Then just sit with a notebook and sip your water". Advice, with nothing first for the worry. Luma's reader
treats "what if" as not real, so it read no feeling there and the brain was told nothing. Now an everyday thing going wrong
for them, asked as "what if", is a small worry: warm first, then whatever was asked.

WORRIES_A and NOT_A are what it was built on. WORRIES_B and NOT_B were written before it and measured once: 3 → 10 of 12
read, 0 of 12 playful or practical what-ifs taken. Same hand, the same hour, and I'd read B before writing the pattern, so
it's a floor to hold and not a stranger's number. No line here is from either human test."""
import json
import unittest
from pathlib import Path

from luma.agent import feelings

ROOT = Path(__file__).resolve().parents[1]

WORRIES_A = ["what if i mess up the presentation", "what if they hate me", "what if nobody likes my speech", "what if i don't get in",
             "what if she breaks up with me", "what if i get fired", "what if no one comes", "what if i can't do it", "what if i embarrass myself",
             "what if he never calls back", "what if they say no", "what if it goes wrong"]
NOT_A = ["what if we get tacos", "what if i dye my hair pink", "what if cats ruled the world", "what if i told you it's my birthday",
         "what if we skip the gym today lol", "what if i move to japan", "what if you could eat, what would you try", "what if it snows tomorrow",
         "what if i get the job though!!", "what if they say yes", "what if we tried the other route", "what if i make it spicy"]
WORRIES_B = ["what if i freeze up in the interview", "ok but what if they don't like me", "what if i fail the test again", "and what if she says no",
             "what if nobody shows up to my party", "what if i'm not good enough for this job", "what if the scan comes back bad",
             "what if i forget my lines", "what if he's mad at me", "what if i can't make rent", "what if everyone laughs at me",
             "what if it's too late to fix things with my dad"]
NOT_B = ["what if we order pizza tonight", "what if dogs could talk lol", "what if i paint the kitchen green", "what if i told you i got the job",
         "what if you had a body, what would you do", "what if we watch the new one instead", "what if i just take the train",
         "what if cereal is a soup", "what if i start a podcast lol", "what if i told him the truth",
         "what if it rains, should i bring a jacket", "what if i win the lottery"]
WORRIES_B_FLOOR, NOT_B_CEILING = 10, 0   # measured once: 3 of 12 before
# A what-if about not being here is never a small worry: it's the safety readers' to read.
NOT_SMALL = ["what if nobody would miss me", "what if i just disappeared", "what if i wasn't here anymore", "what if nobody notices i'm gone",
             "what if everyone is better off without me", "what if i don't exist tomorrow"]


def family(said):
    return (feelings.read(said) or {}).get("family")


class AWorryAskedAsWhatIf(unittest.TestCase):
    def test_an_everyday_thing_going_wrong_is_a_worry(self):
        self.assertEqual([said for said in WORRIES_A if family(said) != "fear"], [])

    def test_a_playful_or_practical_what_if_isnt(self):
        self.assertEqual([said for said in NOT_A if family(said)], [])

    def test_on_the_sets_written_first(self):
        self.assertGreaterEqual(sum(family(said) == "fear" for said in WORRIES_B), WORRIES_B_FLOOR)
        self.assertLessEqual(sum(bool(family(said)) for said in NOT_B), NOT_B_CEILING)

    def test_its_a_small_one_and_gets_the_gentle_line(self):
        felt = feelings.read("what if they hate me")
        self.assertEqual((felt["strength"], felt["heavy"]), (1, False))
        line = feelings.note(felt)
        self.assertIn("a little nervous", line)
        self.assertIn("be warm", line)
        self.assertNotIn("Read the room", line)

    def test_wherever_it_sits_and_with_its_own_question_mark_the_brain_is_told(self):
        from luma.agent import humor
        for said in ("what if they hate me", "what if they hate me?", "ok and what if nobody likes my speech", "but what if i mess up the presentation??"):
            self.assertIn("a little nervous", humor.turn_note(said) or "", said)
        # something else asked with it: the line is held back, as for any feeling, so nothing argues with doing what they asked
        self.assertNotIn("a little nervous", humor.turn_note("what if i mess up the presentation? can you quiz me") or "")
        self.assertFalse(feelings.worry_is_the_question("what if it rains, should i bring a jacket"))

    def test_the_small_model_is_never_asked_about_a_what_if(self):
        from unittest import mock
        from luma.agent import feels
        with mock.patch.object(feels, "by_model", side_effect=AssertionError("asked")):
            for said in NOT_A + NOT_B + WORRIES_A:
                feelings.read(said)

    def test_a_fright_is_still_a_fright(self):
        for said in ("what if it's cancer", "what if they find something on the scan"):
            felt = feelings.read(said)
            self.assertEqual(felt["family"], "fear", said)
            self.assertTrue(felt["heavy"], said)


class NeverTheSafetyReaders(unittest.TestCase):
    def test_a_what_if_about_not_being_here_is_never_a_small_worry(self):
        for said in NOT_SMALL:
            self.assertFalse(feelings._small_worry(said), said)
            felt = feelings.read(said)
            self.assertFalse(felt and felt["family"] == "fear" and felt["strength"] == 1, said)

    def test_no_crisis_line_is_read_as_one(self):
        """The crisis corpus and both held-out sets: counts only."""
        taken = 0
        for name in ("crisis_corpus.jsonl", "crisis_heldout.jsonl", "crisis_heldout2.jsonl"):
            for row in (json.loads(x) for x in (ROOT / "tests" / "data" / name).read_text(encoding="utf-8").splitlines() if x.strip()):
                if row.get("should"):
                    taken += bool(feelings._small_worry(row.get("text") or ""))
        self.assertEqual(taken, 0)
