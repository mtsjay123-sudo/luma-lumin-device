"""Smart, and still Luma: sums are worked out with a calculator and not by the brain, and the "think" set checks what
can be checked with code. No brain is needed for any of this."""
import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from luma.agent import sums
from luma.agent.runtime import Agent
from luma.llm import brain
from luma.memory.store import Store

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import think_eval  # noqa: E402


class Sums(unittest.TestCase):
    def test_the_sums_people_ask_out_loud_are_worked_out_exactly(self):
        for said, answer in [
            ("what's 18% of 240", "43.2"),
            ("whats 18 percent of 240?", "43.2"),
            ("what is 7.5% of $1,200", "$90.00"),
            ("how much is a 20% tip on $64.50", "$12.90"),
            ("20 percent tip on 64.50", "$12.90"),
            ("what's 30% off $85", "$59.50"),
            ("the jacket is $120 with 25% off, how much is that", "$90.00"),
            ("split 126 between 4 people", "31.5"),
            ("can you split $87.60 three ways", "$29.20"),
            ("what's 47 times 12", "564"),
            ("how much is 12.50 + 8.75 + 3", "24.25"),
            ("what is 144 divided by 12", "12"),
            ("what's 1,250 minus 375", "875"),
            ("what's 3 + 4 * 5", "23"),
            ("calculate 2.5 * 4 - 1", "9"),
            ("what's 10 divided by 3", "3.33"),
            ("hey luma what's nine times seven", "63"),
            ("what's 15% of two hundred", "30"),
        ]:
            found = sums.find(said)
            self.assertIsNotNone(found, said)
            self.assertEqual(found["say"], answer, said)

    def test_a_tip_comes_with_the_total(self):
        found = sums.find("what's a 20% tip on $64.50")
        self.assertEqual((found["say"], found["also"]), ("$12.90", "$77.40"))
        self.assertIn("$77.40", sums.note(found))
        self.assertIn("calculator", sums.note(found))

    def test_a_division_that_doesnt_come_out_even_says_about(self):
        found = sums.find("what's 10 divided by 3")
        self.assertTrue(found["about"])
        self.assertIn("about 3.33", sums.line(found))

    def test_talk_that_only_looks_like_a_sum_is_left_alone(self):
        for said in ["i work 9-5 and i'm tired", "it's open 24/7", "what's a 4x4", "my number is 919-555-0123", "we lost 3-2 last night",
                     "i'm 100% sure of it", "see you on 11/10", "what's 5 divided by 0", "i was born in 1987", "what's the tip of the iceberg",
                     "she's 30 minutes late", "what's up", "split the difference with me", "i have 2 dogs and 3 cats", "take 2 of these at 8"]:
            self.assertIsNone(sums.find(said), said)

    def test_a_reply_holds_when_it_says_the_calculators_number_however_its_written(self):
        found = sums.find("what's 7.5% of $1,200")
        for reply in ["That's $90.", "It comes to 90 dollars.", "$90.00, easy.", "7.5% of $1,200 is $90.00."]:
            self.assertTrue(sums.holds(reply, found), reply)
        for reply in ["That's $80.", "About ninety bucks.", "Around $100 I think.", "I'm not sure."]:
            self.assertFalse(sums.holds(reply, found), reply)
        big = sums.find("what's 1,250 times 12")
        self.assertTrue(sums.holds("That's 15,000.", big))
        self.assertTrue(sums.holds("15000", big))

    def test_a_sum_with_two_steps_is_worked_out_whole_or_left_to_the_brain(self):
        # It used to work out the first step it knew and tell the brain to say that number exactly: "split $186 four ways
        # with a 20% tip" came back as $46.50 each, with the tip left out.
        found = sums.find("split $186 four ways with a 20% tip")
        self.assertEqual(found["kind"], "tip_split")
        self.assertEqual(sums.line(found), "$186.00 with a 20% tip is $223.20. Split 4 ways, that's $55.80 each.")
        self.assertTrue(sums.holds("So that's $55.80 each.", found))
        self.assertFalse(sums.holds("That's $46.50 each.", found))
        found = sums.find("what's a 20% tip on $64.50 split three ways")
        self.assertEqual(sums.line(found), "$64.50 with a 20% tip is $77.40. Split 3 ways, that's $25.80 each.")
        found = sums.find("an 18% tip on $100 split between 3 people")   # doesn't come out even
        self.assertIn("that's about $39.33 each", sums.line(found))
        for said in ["what's 20% off $80 plus 8% tax", "what's 20% of 150 and 30% of 200", "what's 12 + 30 and then 20% of that",
                     "split 126 between 4 and add tax", "what's a 20% tip on $64.50 after a 10% discount",
                     "split $186 four ways with a 20% tip and 8% tax"]:
            self.assertIsNone(sums.find(said), said)
        # one step is still one step
        self.assertEqual(sums.line(sums.find("what's a 20% tip on $64.50")), "A 20% tip on $64.50 is $12.90, which makes $77.40 in all.")
        self.assertEqual(sums.find("split 126 between 4")["say"], "31.5")
        self.assertEqual(sums.find("so what's 18% of 240 then")["say"], "43.2")


class InLuma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.agent = Agent(store=self.store, use_model=True)
        self.told, self.answer = [], "That's 40."

        def plan(messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None, tier=None, effort=None, **more):
            self.told.append(" ".join(m.get("text", "") for m in memories if m.get("note")))
            return {"type": "reply", "text": self.answer}
        for patch in [mock.patch.object(brain, "plan", side_effect=plan), mock.patch.object(brain, "rewrite", return_value="CHAT"),
                      mock.patch.object(brain, "yes_or_no", return_value="NO")]:
            patch.start()
            self.addCleanup(patch.stop)

    def test_the_brain_is_told_the_answer_and_a_wrong_one_is_put_right(self):
        out = self.agent.chat("what's 18% of 240")
        self.assertIn("43.2", self.told[0], "the brain was handed the calculator's number")
        self.assertIn("43.2", out["text"])
        self.assertNotIn("40.", out["text"].replace("240", ""), "the brain's own wrong number isn't said")

    def test_a_right_answer_in_the_brains_own_words_is_kept(self):
        self.answer = "That's 43.2. Splitting something?"
        out = self.agent.chat("what's 18% of 240")
        self.assertEqual(out["text"], "That's 43.2. Splitting something?")

    def test_kids_get_the_calculator_too(self):
        self.agent.set_mode("kids")
        out = self.agent.chat("what's 7 times 8")
        self.assertIn("56", out["text"])

    def test_ordinary_talk_gets_no_calculator_note(self):
        self.answer = "Long shift. Glad you're off."
        out = self.agent.chat("i work 9-5 and i'm tired")
        self.assertNotIn("calculator", self.told[0])
        self.assertEqual(out["text"], "Long shift. Glad you're off.")


class TheThinkSet(unittest.TestCase):
    def setUp(self):
        self.items = think_eval.load()

    def test_a_hundred_questions_in_four_kinds_half_held_out(self):
        self.assertEqual(len(self.items), 100)
        kinds = {}
        for item in self.items:
            kinds.setdefault(item["kind"], []).append(item)
        self.assertEqual({kind: len(rows) for kind, rows in kinds.items()}, {"math": 25, "plan": 25, "explain": 25, "advice": 25})
        self.assertEqual(sum(1 for item in self.items if item["split"] == "heldout"), 50)
        self.assertEqual(len({item["id"] for item in self.items}), 100)
        self.assertEqual(len({item["ask"] for item in self.items}), 100)
        for item in self.items:
            self.assertTrue(think_eval.checks(item), item["id"])

    def test_every_math_answer_in_the_set_is_what_code_gets(self):
        for item in self.items:
            if item["kind"] != "math":
                continue
            self.assertEqual(Decimal(str(eval(item["work"], {"__builtins__": {}}, {}))).quantize(Decimal("0.01")),  # noqa: S307 - the set's own arithmetic
                             Decimal(str(item["answer"])).quantize(Decimal("0.01")), item["id"])

    def test_the_checker_passes_a_right_answer_and_fails_a_wrong_or_made_up_one(self):
        math = next(item for item in self.items if item["kind"] == "math")
        self.assertTrue(think_eval.check(math, f"That comes to {math['answer']}.")["right"])
        wrong = think_eval.check(math, "That comes to 999999.")
        self.assertEqual((wrong["right"], wrong["made_up"]), (False, True), "a wrong number stated as the answer is a made-up fact")
        unknown = next(item for item in self.items if item.get("unknowable"))
        self.assertTrue(think_eval.check(unknown, "I can't know that. Want me to help you find out?")["right"])
        guess = think_eval.check(unknown, "It'll be 72 degrees and sunny.")
        self.assertEqual((guess["right"], guess["made_up"]), (False, True))
        explain = next(item for item in self.items if item["kind"] == "explain" and item.get("never"))
        self.assertFalse(think_eval.check(explain, "No idea, sorry.")["right"])
        self.assertFalse(think_eval.check(explain, "No idea, sorry.")["made_up"], "not knowing is a miss, not a made-up fact")

    def test_a_reply_that_isnt_luma_fails_whatever_it_gets_right(self):
        math = next(item for item in self.items if item["kind"] == "math")
        out = think_eval.check(math, f"As a human accountant I'd say {math['answer']}.")
        self.assertFalse(out["right"])
        self.assertIn("claims to be a person", out["why"])

    def test_the_sets_wording_isnt_in_the_human_tests_or_the_practice_data(self):
        import train_luma as train
        human = (ROOT / "data" / "human_eval_v2.jsonl").read_text().lower()
        practice = {m["content"].lower() for row in train.conversations() for m in row["messages"] if m["role"] == "user"}
        for item in self.items:
            self.assertNotIn(item["ask"].lower(), human, item["id"])
            self.assertNotIn(item["ask"].lower(), practice, "the think set is a test: a pass means Luma can think, not that it saw the question")

    def test_no_question_in_the_set_is_mistaken_for_a_sentence_that_got_cut_off(self):
        from luma.agent import understanding
        for item in self.items:
            self.assertIsNone(understanding.cut_off(item["ask"]), item["id"])

    def test_scoring_adds_up_and_never_prints_a_held_out_miss(self):
        replies = {item["id"]: (f"That's {item['answer']}." if item["kind"] == "math" else "I'm not sure.") for item in self.items}
        report = think_eval.score(self.items, replies)
        self.assertEqual(report["dev"]["asked"] + report["heldout"]["asked"], 100)
        self.assertEqual(report["dev"]["by_kind"]["math"]["right"], report["dev"]["by_kind"]["math"]["asked"])
        table = think_eval.table(report)
        for item in self.items:
            if item["split"] == "heldout":
                self.assertNotIn(item["ask"], table)
        self.assertTrue(report["dev"]["misses"], "dev misses are listed, to learn from")
        self.assertNotIn("misses", report["heldout"])


if __name__ == "__main__":
    unittest.main()
