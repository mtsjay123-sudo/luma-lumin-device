"""A gripe told as what happened, with no feeling word in it: "the pharmacy lost my prescription and made me come back
three times". A friend is on their side first. Luma's rules read feelings from feeling words, so these were plain talk
to it and the brain was told a little humor was welcome.

Rules for it were written on forty hand-written gripes and heard all forty; on forty written afterwards they heard 2
(1 before), so they were dropped (Nov 21, 2026). What stands: before the reply, Luma asks the brain its plain YES/NO
question (did something go wrong for them?) and on a YES tells it to be on their side first.

The fresh lines are data/gripes_check.jsonl, a side check for real brains (`--only gripes`), never counted in Human
Test v2 and never tuned on.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "tests")]

import human_eval  # noqa: E402
from luma.agent import feelings, humor, rapport, understanding  # noqa: E402
from luma.agent.runtime import CRISIS  # noqa: E402

GRIPE = "the pharmacy lost my prescription and made me come back three times"
PLAIN = "the pharmacy had my prescription ready when I got there"


def session(answer="YES", plain_questions=True, reply="Okay."):
    asked, told = [], []

    def planner(messages, context, allowed, *args, **kwargs):
        last = messages[-1]["content"]
        if last.startswith("Someone is telling you about their day."):
            asked.append(last)
            return {"type": "reply", "text": answer}
        told.append(json.dumps(context, default=str))
        return {"type": "reply", "text": reply}

    planner.answers_plain_questions = plain_questions
    return human_eval.Session(planner), asked, told


class TheBrainIsAskedFirst(unittest.TestCase):
    def said(self, line, **how):
        s, asked, told = session(**how)
        try:
            s.say(line)
        finally:
            s.close()
        return asked, " ".join(told)

    def test_on_a_yes_the_brain_is_told_to_be_on_their_side(self):
        asked, told = self.said(GRIPE)
        self.assertEqual(len(asked), 1)
        self.assertIn("Something went wrong for them: be on their side first", told)
        self.assertNotIn("A little humor is welcome", told)

    def test_on_a_no_nothing_changes(self):
        asked, told = self.said(PLAIN, answer="NO")
        self.assertEqual(len(asked), 1)
        self.assertNotIn("Something went wrong for them", told)
        self.assertIn("A little humor is welcome", told)

    def test_a_brain_that_cant_be_asked_isnt(self):
        asked, told = self.said(GRIPE, plain_questions=False)
        self.assertEqual(asked, [])
        self.assertNotIn("Something went wrong for them", told)

    def test_with_no_i_in_it_its_still_asked(self):
        asked, _ = self.said("the store wouldn't take the return even with the receipt")
        self.assertEqual(len(asked), 1)

    def test_what_luma_already_reads_isnt_asked_about(self):
        for line in ("I'm so fed up with this pharmacy, they lost my prescription again",      # a feeling word: the venting line
                     "why did the pharmacy lose my prescription",                              # a question
                     "my grandma died last night and the pharmacy called about her pills",     # a loss
                     "remind me to call the pharmacy about my prescription tomorrow"):          # something to do
            asked, told = self.said(line)
            self.assertEqual(asked, [], line)
            self.assertNotIn("Something went wrong for them", told, line)

    def test_never_in_kids_mode_and_the_owner_can_turn_it_off(self):
        s, asked, told = session()
        try:
            self.assertTrue(s.agent._told_plainly(GRIPE, "", ""))
            s.agent.set_mode("kids")
            self.assertFalse(s.agent._told_plainly(GRIPE, "", ""))
            s.agent.set_mode("friend")
            s.agent.store.set_setting("side_first", False)
            self.assertFalse(s.agent._told_plainly(GRIPE, "", ""))
            s.agent.store.set_setting("side_first", True)
            self.assertTrue(s.agent._told_plainly(GRIPE, "", ""))
        finally:
            s.close()

    def test_never_when_the_cloud_brain_answers_in_one_trip_or_something_is_asked(self):
        s, _, _ = session()
        try:
            one_trip = s.agent._one_trip
            try:
                s.agent._one_trip = lambda: True
                self.assertFalse(s.agent._told_plainly(GRIPE, "", ""))   # every trip there is a round trip before the first word
            finally:
                s.agent._one_trip = one_trip
            for line in ("think hard about this: should i take the night shift job or stay where i am",
                         "my landlord raised the rent again, what do you think i should do",
                         "the pharmacy lost my prescription. can i get it somewhere else"):
                self.assertFalse(s.agent._told_plainly(line, "", ""), line)
        finally:
            s.close()

    def test_a_small_brain_isnt_asked(self):
        """Run 69: asked first, the stock 4B went from 36 to 49 of 50 on venting; the stock 1.7B from 12 to 13 and Luma's
        own small from 30 to 29, for a turn up to twice as long."""
        s, _, _ = session()
        try:
            from luma.llm import brain
            planner, model, small = s.agent.planner, s.agent.use_model, brain.small_here
            try:
                s.agent.planner, s.agent.use_model, brain.small_here = None, True, lambda: True
                self.assertFalse(s.agent._told_plainly(GRIPE, "", ""))
                brain.small_here = lambda: False
                self.assertTrue(s.agent._told_plainly(GRIPE, "", ""))
            finally:
                s.agent.planner, s.agent.use_model, brain.small_here = planner, model, small
        finally:
            s.close()

    def test_only_where_the_brain_would_have_been_told_humor_is_welcome(self):
        s, _, _ = session()
        try:
            self.assertFalse(s.agent._told_plainly(GRIPE, "They told you about a loss a few messages ago: stay gentle and warm.", ""))
            self.assertFalse(s.agent._told_plainly(GRIPE, "", "Give your own take first."))        # another note already shapes the turn
            self.assertTrue(s.agent._told_plainly(GRIPE, "A little humor is welcome. The flavor of your own sense of humor: ...", ""))
        finally:
            s.close()

    def test_its_asked_once_for_one_message(self):
        """Someone who asked to have their mind taken off it: the question before the reply is the one the offer after it
        would have asked. One trip, the note and the offer both."""
        s, asked, told = session(reply="Oh no. What did they say?")
        try:
            s.say("when I'm down, take my mind off it")
            s.at({"day": 5, "time": "19:30"})
            s.new_conversation()
            reply = s.say(GRIPE)[0]
        finally:
            s.close()
        self.assertEqual(len(asked), 1)
        self.assertIn("Something went wrong for them", " ".join(told))
        self.assertTrue(reply.endswith(rapport.OFFER), reply)

    def test_nobody_who_might_not_be_safe_gets_this_question(self):
        s, _, _ = session()
        try:
            lines = [json.loads(line) for line in (ROOT / "tests" / "data" / "crisis_corpus.jsonl").read_text().splitlines() if line.strip()]
            unsafe = [row["text"] for row in lines if row["should"]]
            self.assertGreater(len(unsafe), 400)
            for line in unsafe:
                self.assertFalse(s.agent._told_plainly(line, "", "") and not CRISIS.search(line.lower()), line)
        finally:
            s.close()


class LaughedOff(unittest.TestCase):
    """Bad news said with a laugh: "lol my dog has cancer apparently". People laugh things off. Of twenty fresh lines like
    it, eighteen were handed to the brain with "They're laughing: be funny back" (Nov 21, 2026); the twenty funny ones
    beside them ("lol my cat just fell off the couch in her sleep") were all read as laughing, and still are. Which one
    it is, is the brain's to say: the same plain question, asked first."""
    BAD = "lol the test came back positive, it's diabetes"
    FUNNY = "lol my nephew called a penguin a tuxedo chicken"

    def said(self, line, **how):
        s, asked, told = session(**how)
        try:
            s.say(line)
        finally:
            s.close()
        return asked, " ".join(told)

    def test_on_a_yes_its_never_be_funny_back(self):
        asked, told = self.said(self.BAD)
        self.assertEqual(len(asked), 1)
        self.assertIn("They said it with a laugh, but it's bad news for them", told)
        self.assertNotIn("be funny back", told)
        self.assertNotIn("A little humor is welcome", told)

    def test_on_a_no_they_get_their_laugh(self):
        asked, told = self.said(self.FUNNY, answer="NO")
        self.assertEqual(len(asked), 1)
        self.assertIn("be funny back", told)
        self.assertNotIn("bad news", told)

    def test_a_laugh_with_no_sentence_beside_it_isnt_asked_about(self):
        for line in ("lol", "hahaha that's hilarious", "lmao stop", "😂😂😂"):
            asked, told = self.said(line)
            self.assertEqual(asked, [], line)

    def test_the_fresh_lines_are_read_as_laughing_which_is_why_the_brain_is_asked(self):
        items = human_eval.load(human_eval.GRIPES)
        off = [i["said"] for i in items if i["category"] == "gripes_laughed_off"]
        funny = [i["said"] for i in items if i["category"] == "gripes_funny"]
        self.assertEqual(sum(humor.read_tone(line)["mood"] == "laughing" for line in off), 18)     # the other two are read as a hurt
        self.assertEqual(sum(humor.read_tone(line)["mood"] == "laughing" for line in funny), 20)
        s, _, _ = session()
        try:
            lead = "They're laughing: be funny back. The flavor of your own sense of humor: ..."
            self.assertEqual(sum(bool(s.agent._told_plainly(line, lead, "")) for line in off), 18)
        finally:
            s.close()

    def test_good_news_said_with_a_laugh_is_good_news_first(self):
        """The laugh is how glad they are. Ten fresh lines were all handed to the brain as "be funny back"; the one still
        missed has no good-news words Luma's reader knows."""
        glad = ["BRO I GOT THE JOB 😭😭", "lol i actually passed my driving test", "haha we won the championship!!", "LMAO THEY SAID YES",
                "😭😭 i got into nursing school", "omg i'm crying we closed on the house 😭", "lol guess who just got promoted",
                "haha i finally paid off my car", "i passed the bar exam i'm screaming 😭", "lmao i got the scholarship, full ride"]
        first = lambda line: humor.turn_note(line)  # noqa: E731
        told = [line for line in glad if first(line).startswith(("They have good news", "They did something hard"))]
        self.assertGreaterEqual(len(told), 9, [line for line in glad if line not in told])
        for line in told:
            self.assertNotIn("be funny back", first(line), line)
        items = human_eval.load(human_eval.GRIPES)
        for item in items:
            if item["category"] in ("gripes_funny", "gripes_laughed_off"):   # a funny thing is still a laugh; bad news is never good news
                self.assertFalse(first(item["said"]).startswith(("They have good news", "They did something hard")), item["said"])

    def test_telling_with_a_laugh_is_only_for_this(self):
        self.assertFalse(rapport.telling("lol i totaled my car on the way home"))            # the offer after a reply is as it was
        self.assertTrue(rapport.telling("lol i totaled my car on the way home", laughing=True))
        self.assertFalse(rapport.telling("lol what should i wear tonight", laughing=True))  # a question is a question
        self.assertLessEqual(len(humor.LAUGHED_OFF), 200)


class WhatTheLinesFound(unittest.TestCase):
    """Three things Luma's own code got wrong, found by reading what it did with the fresh lines."""

    def test_a_bus_stop_isnt_a_laugh(self):
        for line in ("the bus drove right past me this morning. i was standing at the stop", "i'm gonna stop by the pharmacy after work",
                     "the train doesn't stop at my station anymore"):
            self.assertNotEqual(humor.read_tone(line)["mood"], "laughing", line)
        for line in ("stop it 😂", "omg stop", "STOPPP", "stop lol", "stop"):
            self.assertEqual(humor.read_tone(line)["mood"], "laughing", line)

    def test_my_one_day_off_isnt_a_what_if(self):
        self.assertFalse(feelings.NOT_REAL.search("they scheduled me for a double on my one day off"))
        self.assertTrue(feelings.NOT_REAL.search("one day i'll lose her and i don't know what i'll do"))
        self.assertEqual((feelings.read("i'm so annoyed, they scheduled me on my one day off") or {}).get("family"), "fed up")

    def test_jefe_is_the_boss_before_its_anyones_dad(self):
        """The dictionary said "mom and dad, literally boss", and a brain told about someone's jefe keeping them late
        answered about their mother (run 67)."""
        from luma.agent import slang
        note = slang.meanings_note("mi jefe at the warehouse wants me in on sunday otra vez")
        self.assertIn("means boss", note)
        self.assertIn("mom (jefa) or dad (jefe)", note)

    def test_a_grade_isnt_a_sentence_cut_off(self):
        for line in ("my classmate and i studied together and both got an A", "i got a B", "she finally got an a"):
            self.assertIsNone(understanding.cut_off(line), line)
        for line in ("i need a", "we both got an", "remind me to get a"):
            self.assertTrue(understanding.cut_off(line), line)


class TheSideCheck(unittest.TestCase):
    """data/gripes_check.jsonl: for real brains, never counted in Human Test v2 (`--only gripes`)."""

    @classmethod
    def setUpClass(cls):
        cls.items = human_eval.load(human_eval.GRIPES)

    def test_its_shape(self):
        told = [i for i in self.items if i["category"] == "gripes_told"]
        plain = [i for i in self.items if i["category"] == "gripes_plain"]
        off = [i for i in self.items if i["category"] == "gripes_laughed_off"]
        funny = [i for i in self.items if i["category"] == "gripes_funny"]
        self.assertEqual((len(told), len(plain), len(off), len(funny), len(self.items)), (39, 50, 20, 20, 129))
        self.assertEqual(len({i["id"] for i in self.items}), 129)
        self.assertEqual(len({i["said"] for i in self.items}), 129)
        self.assertTrue(all(i["must"] == ["side"] for i in told))
        self.assertTrue(all(i["must_not"] == ["groans"] for i in plain + funny))
        self.assertTrue(all(i["must"] == ["sympathy"] and i["must_not"] == ["laughs"] for i in off))
        self.assertEqual(len(human_eval.chosen(human_eval.everything("gripes"), "gripes")), 129)
        self.assertFalse([i for i in human_eval.everything(None) if i["category"].startswith("gripes")])   # never part of Human Test v2

    def test_no_line_is_a_human_test_line_or_an_example_the_brain_is_shown(self):
        test = {" ".join(str(t.get("said", "")).lower().split()) for item in human_eval.load() for t in (item.get("turns") or [item])}
        shown = {line.lower() for line in rapport.HARD_YES + rapport.HARD_NO}
        for item in self.items:
            self.assertNotIn(" ".join(item["said"].lower().split()), test | shown, item["said"])

    def test_no_line_is_in_anyones_practice(self):
        import finetune_data
        practice = json.dumps([row for row in finetune_data.conversations()] if hasattr(finetune_data, "conversations") else "").lower()
        text = (ROOT / "scripts" / "finetune_data.py").read_text().lower() + practice
        for item in self.items:
            self.assertNotIn(item["said"].lower(), text, item["said"])

    def test_the_gripes_have_no_feeling_word_and_most_would_be_asked_about(self):
        """Luma's own reading hears next to none of the gripes (that's why the brain is asked), and takes none of the
        ordinary lines for one."""
        told = [i["said"] for i in self.items if i["category"] == "gripes_told"]
        plain = [i["said"] for i in self.items if i["category"] == "gripes_plain"]
        heard = lambda line: humor.read_tone(line)["mood"] in ("venting", "upset", "grief")  # noqa: E731
        self.assertLessEqual(sum(heard(line) for line in told), 3)
        self.assertLessEqual(sum(heard(line) for line in plain), 1)
        s, _, _ = session()
        try:
            asked = sum(bool(s.agent._told_plainly(line, "", "")) for line in told)
        finally:
            s.close()
        self.assertGreaterEqual(asked, 33, asked)

    def test_the_checks(self):
        turn = {"must": ["side"], "must_not": ["cruelty"]}
        self.assertEqual(human_eval.misses(turn, "x", "Ugh, that's so frustrating. What did they say?", []), [])
        self.assertTrue(human_eval.misses(turn, "x", "Oh nice, how was the rest of your day?", []))
        turn = {"must": [], "must_not": ["groans"]}
        self.assertTrue(human_eval.misses(turn, "x", "Ugh, that's a lot. What happened?", []))
        self.assertEqual(human_eval.misses(turn, "x", "Three pies! Which one went first?", []), [])

    def test_the_count_is_numbers_only(self):
        result = {"label": "a brain", "moments": [
            {"id": "gripes-told-01", "category": "gripes_told", "said": "x", "reply": "Ugh.", "missed": [], "went_wrong": True},
            {"id": "gripes-told-02", "category": "gripes_told", "said": "y", "reply": "Nice.", "missed": ["missed: side"], "went_wrong": False},
            {"id": "gripes-plain-01", "category": "gripes_plain", "said": "z", "reply": "Nice.", "missed": []}]}
        out = human_eval.asked_wrong(result)
        self.assertIn("asked if something went wrong on 2 of 2: YES 1, NO 1; passed 1 of 2", out)
        self.assertIn("asked if something went wrong on 0 of 1", out)
        for row in result["moments"]:
            self.assertNotIn(row["reply"], out)


if __name__ == "__main__":
    unittest.main()
