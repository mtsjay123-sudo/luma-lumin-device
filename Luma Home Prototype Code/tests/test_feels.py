"""The small model that reads a hard moment where the rules read nothing (luma.agent.feels).

It is believed about two feelings only: a worry (said through a wait or the body) and being lonely (with somebody missing
from the sentence). Four kinds of line here:

- SIDEWAYS / TWINS: written by hand on Nov 21, 2026, BEFORE the model was built: forty hard moments with no feeling word
  and forty ordinary lines made from the same words. The honest number, and it says the model doesn't help with these.
- WORRY / LONELY / ORDINARY: written after it was built, for the two things it's believed about, and measured once.
- The held-out half of hard-or-not and the other held-out calm sets: counts only, never a line.
- Nothing is changed to fit any of them. The floors are what was measured that day.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT / "tests")]

from luma.agent import feelings, feels  # noqa: E402

try:
    import numpy  # noqa: F401
    HAVE = feels.LEARNED.exists()
except Exception:
    HAVE = False

SIDEWAYS = [
    "the group chat's been dead for weeks unless i say something first", "third friday in a row it's me and a frozen pizza",
    "my roommates all went out and didn't even knock on my door", "i sat in the parking lot for an hour because going home just means silence",
    "saw the photos from the trip. guess my invite got lost", "i talk to the cashier at the gas station more than anyone i know",
    "my birthday was tuesday. two texts, one was from my dentist", "since the divorce the weekends just stretch out",
    "everybody at the wedding had a plus one but me", "i keep the tv on just so there's a voice in the apartment",
    "my sister told the whole family what i said to her in private", "he laughed when i told him i wanted to go back to school",
    "my best friend got engaged and i found out from instagram", "my dad didn't show up to my graduation. said he forgot",
    "they made fun of my accent in the meeting and everybody just sat there", "she read my message two days ago and still hasn't replied",
    "my mom said i was the reason the holidays are always tense", "my friends planned a whole dinner and told me it was a family thing",
    "my manager took my idea and presented it like it was his", "my own kids roll their eyes whenever i open my mouth",
    "six months of studying and i missed the cutoff by two points", "the landlord picked the other applicants",
    "the adoption agency called. the birth mother changed her mind", "they cancelled the show an hour before i was supposed to go on",
    "i trained all year and tore my hamstring a week before the race", "the bank said no to the loan again",
    "i thought tonight was a date. he brought his friends", "the school called, my son isn't moving up with his class",
    "i've been wearing the same hoodie for five days and i can't make myself care", "i just stare at the dishes. they've been there since last week",
    "work, then my mom's appointments, then the kids, and then i lie awake doing math on the bills", "i cried in the walk-in freezer on my break again",
    "i can't remember the last time i laughed at something", "every morning it takes me an hour to talk myself out of bed",
    "i'm doing the job of three people and they just added another account", "i called in sick again. i wasn't sick",
    "the doctor wants me back in for more tests and wouldn't say why over the phone", "they're announcing layoffs friday and my team is the newest",
    "my son hasn't answered his phone since last night and he always answers", "the rent is going up 400 dollars and i don't know where that comes from",
]
TWINS = [
    "home alone tonight, finally get the tv to myself", "just me and the dog on the couch, perfect friday", "the group chat is blowing up about the game",
    "nobody told me this show was so good", "i sat in the parking lot finishing my podcast", "my roommates are out so i'm cooking something loud and smelly",
    "my birthday was tuesday, we did tacos and karaoke", "everybody at the wedding danced until two", "i keep the tv on for the dog when i leave",
    "saw the photos from the trip, the beach looked unreal", "my sister told the whole family she's moving to denver", "he laughed so hard he spilled his drink",
    "my best friend got engaged! she called me first", "my dad showed up to my graduation in a full suit", "she read my message and sent back a thumbs up",
    "my manager took my idea to the director and gave me credit", "my kids rolled their eyes at my playlist, so i turned it up",
    "my friends planned a whole dinner for saturday, i'm bringing dessert", "six months of studying and i passed with room to spare",
    "the landlord picked us for the apartment", "they moved the show to a bigger room", "i trained all year and finished the race in under two hours",
    "the bank approved the loan", "i thought tonight would be boring but he brought board games", "the school called, my son made the honor roll",
    "i've been wearing this hoodie for five days because it's that comfortable", "the dishes are done and the kitchen smells like lemon",
    "work, then the gym, then dinner with my mom, busy day but a good one", "i took my break in the walk-in freezer because the kitchen was a hundred degrees",
    "i laughed so hard at that video i couldn't breathe", "took me an hour to get out of bed because the cat was on me",
    "they added another account to my team, more commission for me", "i called in sick to go to the lake, don't tell anyone",
    "the doctor said the tests all came back normal", "they're announcing the new schedule friday", "my son finally answered his phone, he was at practice",
    "the rent is staying the same next year", "can you add frozen pizza to the list", "what time does the gas station close",
    "two texts from my dentist about a cleaning, i should book it",
]
WORRY = [
    "my mammogram came back and they want another look on wednesday", "i find out about the job thursday and i haven't eaten all day",
    "my daughter's in the operating room and it's been four hours", "i go before the judge in the morning and i can't stop pacing",
    "the pediatrician sent us straight to the hospital", "my husband's plane was supposed to land two hours ago",
    "the bank is taking the house unless we come up with it by friday", "i heard footsteps outside my window again tonight",
    "my interview is in an hour and i think i'm going to be sick", "they're reading the verdict tomorrow",
    "my grandma stopped eating and the nurse called everyone in", "i'm sitting in the waiting room and nobody has come out yet",
    "the results are in the portal and i can't make myself open them", "my brother deployed this morning",
    "the oncologist's office called and asked me to come in today",
]
LONELY = [
    "it's my third week here and i've eaten every dinner alone", "everyone went home for the holidays and the dorm is empty",
    "nobody sat next to me on the bus trip", "i went to the company picnic and stood by myself the whole time",
    "all my friends paired off and it's just me now", "the house is silent now that the kids are gone", "i wasn't invited to my own cousin's wedding",
    "no one's called since the funeral", "i spend every lunch break by myself in the stairwell", "my friends have their own lives and i don't hear from them",
]
ORDINARY = [
    "my mammogram came back clear", "i find out about the job thursday, fingers crossed", "my daughter's in the school play tonight",
    "i go before the board in the morning to present our numbers", "the pediatrician said she's growing right on schedule",
    "my husband's plane lands at six, picking him up", "we're closing on the house friday", "i heard the neighbors' new puppy again tonight",
    "my interview is in an hour, wish me luck", "they're reading my poem at the assembly tomorrow", "everyone went home for the holidays so parking is easy",
    "nobody sat next to me on the flight, three seats to myself", "the house is quiet now that the kids are at camp, it's lovely",
    "i spend every lunch break by myself with a book, best part of my day", "my friends have their own lives, we catch up once a month",
]


def hard(line):
    felt = feelings.read(line)
    return bool(felt) and felt["family"] not in feelings.GOOD


def by_rule(line):
    import train_feels
    return bool(train_feels.by_rule(line))


def human_test_lines():
    rows = [json.loads(line) for line in (ROOT / "data" / "human_eval_v2.jsonl").read_text().splitlines() if line.strip()]
    out = []
    for row in rows:
        out += [row["said"]] if isinstance(row.get("said"), str) else []
        out += [turn["said"] for turn in row.get("turns") or [] if isinstance(turn, dict) and isinstance(turn.get("said"), str)]
    return out


@unittest.skipUnless(HAVE, "needs numpy and the trained model (scripts/train_feels.py)")
class TheModel(unittest.TestCase):
    def test_its_small_and_is_believed_about_two_feelings(self):
        self.assertLess(feels.LEARNED.stat().st_size, 1_000_000)
        self.assertEqual(set(feels.learned("another saturday by myself")), set(feels.LABELS))
        self.assertEqual(set(feels.SURE), {"lonely", "fear"})
        for line in SIDEWAYS + TWINS + WORRY + LONELY + ORDINARY:
            self.assertIn(feels.by_model(line), ("", "lonely", "fear"), line)

    def test_the_rules_come_first_and_the_model_only_adds(self):
        for line in ("i'm so lonely tonight", "i'm scared about the surgery", "my mom died this morning"):
            self.assertTrue(by_rule(line), line)
        for line in ("another saturday by myself", "i have court tomorrow and i can't sleep"):
            self.assertFalse(by_rule(line), line)
            self.assertTrue(hard(line), line)
        self.assertEqual(feelings.read("another saturday by myself")["family"], "lonely")
        self.assertEqual(feelings.read("i have court tomorrow and i can't sleep")["family"], "fear")

    def test_said_sideways_the_honest_number(self):
        """Written before the model was built. Rules alone: 2 of 40. With the model: 2 of 40. It adds nothing here, and it
        takes none of the forty ordinary lines made from the same words."""
        self.assertGreaterEqual(sum(hard(line) for line in SIDEWAYS), 2)
        self.assertEqual([line for line in TWINS if hard(line)], [])

    def test_what_its_believed_about_the_second_honest_number(self):
        """Written after it was built, measured once (then once more after the model learned to stay out of safety lines,
        which changed nothing here but one more worry). A worry: rules 0, with the model 2 of 15. Lonely with somebody
        missing: rules 2, with the model 5 of 10. Ordinary lines made from the same words: 1 of 15 taken ("my friends have
        their own lives, we catch up once a month")."""
        self.assertGreaterEqual(sum(hard(line) for line in WORRY), 2)
        self.assertGreaterEqual(sum(hard(line) for line in LONELY), 5)
        self.assertLessEqual(sum(hard(line) for line in ORDINARY), 1)

    def test_lonely_needs_somebody_missing_and_nothing_is_read_into_a_question_or_a_request(self):
        for line in ("like i wasn't even the one who messed up the order", "add milk to my list", "what if nobody comes to my party",
                     "is my scan on thursday", "remind me i have court tomorrow", "my brother forgot his umbrella"):
            self.assertFalse(hard(line), line)
        self.assertFalse(feels.has_shape("the bank said no"))                       # they're not in it
        self.assertFalse(feels.has_shape("can you tell me when my scan is"))
        self.assertTrue(feels.has_shape("i went to the picnic and stood by myself", "lonely"))
        self.assertFalse(feels.has_shape("i went to the picnic and stood in line", "lonely"))

    def test_held_out_halves_no_worse_than_measured(self):
        """Nov 21, 2026. Hard-or-not, held out: rules alone 100 of 150 hard lines, with the model 108; none of the 150 ordinary
        ones before or after. One line newly read as hard in 8,297 other held-out calm lines. Counts only; no line is printed."""
        import hard_or_not
        import keep_or_today
        import safety_sets
        import train_moves as moves
        lines = hard_or_not.lines("heldout")
        bad = [t for t, mark in lines if mark == "hard"]
        plain = [t for t, mark in lines if mark != "hard"]
        got = sum(hard(t) for t in bad)
        self.assertGreaterEqual(got, 108, f"hard lines read as hard: {got} of {len(bad)}")
        self.assertEqual(sum(hard(t) for t in plain), 0)
        calm = [t for t, _ in keep_or_today.lines("heldout")] + list(safety_sets.leaning("heldout")) + list(safety_sets.what_i_am("heldout"))
        calm += list(safety_sets.kids("heldout")) + [said for said, _, _ in moves.plain_lines("heldout", None, 6, 5)]
        calm += [said for said, _, _ in moves.chatter(4000, 7, held=True)] + [said for said, _, _ in moves.requests(3000, 31)]
        new = sum(1 for t in calm if not by_rule(t) and hard(t))
        self.assertLessEqual(new, 1, f"calm lines newly read as hard: {new} of {len(calm)}")

    def test_anyone_who_might_not_be_safe_or_is_leaning_is_never_the_models_to_read(self):
        """"nobody would even notice if i was gone" has every word of a lonely line. The safety readers have it; the model
        doesn't get a say, so the second look asks of the reply what it always did. The same for leaning on Luma."""
        from luma.agent import friendcheck
        line = "nobody would even notice if i was gone"
        self.assertTrue(friendcheck.at_risk(line) or friendcheck.worth_asking(line))
        self.assertFalse(hard(line))
        self.assertIsNone(friendcheck.miss(line, "I'd notice. Are you safe right now? You can call or text 988 any time."))
        lean = "i talk to you more than anyone in my life"
        self.assertTrue(friendcheck.leaning(lean))
        self.assertFalse(hard(lean))
        crisis = [json.loads(row) for row in (ROOT / "tests" / "data" / "crisis_corpus.jsonl").read_text().splitlines() if row.strip()]
        texts = [str(row.get("text") or row.get("said") or "") for row in crisis]
        self.assertGreater(len(texts), 800)
        self.assertEqual(sum(1 for t in texts if t and not by_rule(t) and hard(t)), 0)   # not one line of the corpus is read differently

    def test_nothing_said_with_a_laugh_is_the_models_to_read(self):
        for line in ("he really said that and i can't stop laughing", "lmao my mom has to have heart surgery next week", "i have court tomorrow lol"):
            self.assertEqual(feelings._learned(line), "", line)

    def test_no_practice_sentence_is_a_safety_line(self):
        import train_feels
        rows = train_feels.practice(None, 40, 0)
        self.assertGreater(len(rows), 4000)
        self.assertEqual([said for said, _, _ in rows if train_feels.safety_reads(said)], [])

    def test_the_brain_is_told(self):
        """A line only the model reads reaches the brain as the same note the rule would have sent."""
        import human_eval
        seen = []

        def planner(messages, context, allowed, *args, **kwargs):
            seen.append(context)
            return {"type": "reply", "text": "I'm here with you. That sounds like a long, quiet day."}

        s = human_eval.Session(planner)
        try:
            s.say("another saturday by myself")
            told = json.dumps(seen, default=str)
            self.assertIn("they're feeling alone", told)
            self.assertNotIn("humor is welcome", told)
        finally:
            s.close()


class WithoutTheModel(unittest.TestCase):
    def test_the_rules_still_work_alone(self):
        kept = feels._model
        feels._model = False
        feels._seen.clear()
        try:
            self.assertEqual(feels.learned("another saturday by myself"), {})
            self.assertEqual(feels.by_model("another saturday by myself"), "")
            self.assertIsNone(feelings.read("another saturday by myself"))
            self.assertEqual(feelings.read("i'm so lonely tonight")["family"], "lonely")
        finally:
            feels._model = kept
            feels._seen.clear()


class PracticeIsNotTheTest(unittest.TestCase):
    """The human tests are held out, and so are the honest lines above: none of their wording is a practice sentence."""

    def test_no_practice_sentence_is_a_test_line(self):
        def plain(text):
            return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()
        taken = {plain(said) for said in human_test_lines()} | {plain(line) for line in SIDEWAYS + TWINS + WORRY + LONELY + ORDINARY}
        import train_luma
        for moment in train_luma.HUMAN_TEST:
            said = moment if isinstance(moment, str) else (moment.get("said") or moment.get("text") or "") if isinstance(moment, dict) else str(moment[0])
            taken.add(plain(said))
        import random
        import train_moves as moves
        rng = random.Random(3)
        said = {plain(fill) for _, frame in feels.FRAMES for fill in moves._fills(frame, feels.SLOTS, 40, rng)}
        self.assertEqual(sorted(said & taken), [])

    def test_every_blank_has_values(self):
        for _, frame in feels.FRAMES:
            for name in re.findall(r"\{(\w+)\}", frame):
                self.assertTrue(feels.SLOTS.get(name), f"{frame}: no values for {name}")

    def test_the_words_arent_the_tests_own_lists(self):
        """tests/hard_or_not.py fills its sentences from lists; half of every list is held out. The events, bills, places and
        foods the practice sentences are filled with share no value with those lists."""
        import hard_or_not
        for mine, theirs in (("thing", "thing"), ("bill", "bill"), ("place", "place"), ("food", "food")):
            strip = lambda v: re.sub(r"^(?:the|my|this|a|an) ", "", v.lower())  # noqa: E731
            self.assertEqual(sorted({strip(v) for v in feels.SLOTS[mine]} & {strip(v) for v in hard_or_not.L[theirs]}), [], mine)


if __name__ == "__main__":
    unittest.main()
