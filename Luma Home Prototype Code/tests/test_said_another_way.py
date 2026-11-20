"""A sister's name, where a mom lives, that a brother moved: the same facts, said any other way round (people.plainly).

The month test on real brains, on the lives Luma wasn't built on (run 56, Nov 20, 2026): asked a sister's name or where a
mom lives, the small brains said it 0 times of 12. Counts on that half (no line read) showed why: the lines that had
told Luma weren't read as facts at all.

Three sets of lines, all written by hand that day:
- BUILT_ON: the first two sets. The readers were built on these; they are a guard.
- NOT (near misses): must never be read as a name or a home.
- HONEST: a third set written after the readers were finished, and never used to change them. The floors are what was
  measured once, that day. Before: of the 10 names Luma said 1 and answered "I don't know your sister's name yet" to 9.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT / "tests")]

from luma.agent import keeps, people  # noqa: E402
from luma.memory import facts  # noqa: E402

NAMES = ["my sister goes by Priya", "everyone calls my sister Priya", "Priya, that's my sister", "my sister? her name's Priya", "the name of my sister is Priya",
         "you can call my sister Priya", "my sister is Priya, by the way", "Priya's my sister's name", "I have a sister, Priya", "my sister, she's called Priya",
         "it's Priya, my sister's name", "we named my sister Priya after our grandma", "meet my sister, Priya", "my sister's called Priya", "that's Priya, my sister",
         "my sister - Priya - is the funny one", "my sister, Priya", "I've got a sister called Priya"]
HOMES = ["my mom's out in Tampa", "Tampa is where my mom lives", "my mom calls Tampa home", "my mom has a place in Tampa", "my mom's been in Tampa for years",
         "my mom is down in Tampa", "home for my mom is Tampa", "my mom resides in Tampa", "my mom stays in Tampa", "my mom's house is in Tampa", "my mom, she's in Tampa",
         "my mom's place is in Tampa", "my mom moved down to Tampa years ago", "my mom's lived in Tampa forever", "my mom retired to Tampa", "my mom has an apartment in Tampa"]
MOVES = ["Marcus just took a job in Denver, he's moving next week", "so Marcus packed up and left for Denver", "Marcus got transferred to Denver",
         "Marcus and his wife bought a house in Denver", "Marcus finally made the move to Denver", "heard from Marcus, he's all settled in Denver",
         "Marcus's new place is in Denver", "Marcus swapped Austin for Denver", "Marcus headed out to Denver for good", "Marcus is settling into Denver",
         "Marcus up and moved to Denver", "Marcus has a new apartment in Denver", "Marcus traded Austin for Denver"]
NOT = ["my sister and Priya went out", "my sister loves Priya", "my sister met Priya", "my sister's friend Priya", "my sister's Honda", "my sister is Priya's roommate",
       "I told my sister, Mom is coming", "call my sister Sunday", "text my sister Happy birthday", "my sister, Lord help her", "my mom is Japanese", "my sister is Catholic",
       "is my sister called Priya?", "my brother, Target employee of the month", "I have a sister and Priya is her friend", "my mom called Priya",
       "my sister is the Queen of drama", "tell my sister Priya says hi", "my best friend's dog is Biscuit", "my sister named her dog Priya",
       "my sister is called every day by Priya", "my mom's in Tampa this week", "my dad is in Tampa visiting", "my mom lived in Tampa when she was little",
       "my mom has a place in her heart for Tampa", "Marcus might move to Denver", "Marcus left his keys in Denver", "Marcus headed to Target",
       "my mom moved my stuff to Storage", "my brother lives for Sunday football", "Marcus drove to Denver", "my sister is Pregnant", "my mom is down in the dumps",
       "my sister is mad at me", "my mom calls me every day", "everyone calls my sister crazy", "where does my mom live", "Marcus wants to move to Denver",
       "Marcus is thinking about moving to Denver", "Marcus is visiting Denver", "my brother left for Denver this weekend"]
HONEST = {
    "name": (["this is my sister Priya", "say hi to my sister, Priya", "my sister (Priya) is visiting next month", "Priya, she is my sister", "my sister's name? Priya",
              "people call my sister Priya", "my older sister is called Priya", "so my sister, Priya, just had a baby", "my sister who is named Priya lives nearby",
              "I call my sister Pri, but her name is Priya"], [], "what's my sister's name", "Priya", None),
    "home": (["my mom lives out by Tampa", "my mom's home is Tampa", "my mom has lived in Tampa her whole life", "my mom's apartment is in Tampa", "my mom is based out of Tampa",
              "Tampa, that is where my mom is", "my mom bought a condo in Tampa", "my mom's still in Tampa", "my mom never left Tampa",
              "my mom's been living in Tampa since the nineties"], [], "where does my mom live", "Tampa", None),
    "moved": (["Marcus is a Denver resident now", "Marcus lives out in Denver now", "Marcus moved out to Denver in the fall", "Marcus got himself an apartment in Denver",
               "turns out Marcus is living in Denver", "Marcus left Texas for Denver", "Marcus took a transfer to Denver", "Marcus is done with Austin, he is in Denver now"],
              ["my brother's name is Marcus", "my brother lives in Austin"], "where does my brother live now", "Denver", "Austin"),
}


def lived(setup, line, question, want, old=None):
    """Luma is told it, days pass, they ask: "LUMA" (Luma says it), "told" (a small brain is handed it), "OLD" (the old city, said flat) or "MISS"."""
    import human_eval
    from luma.llm import prompts
    calls = []

    def planner(messages, context, allowed, *args, **kwargs):
        calls.append((list(messages), list(context)))
        return {"type": "reply", "text": f"Okay, {len(calls)}."}

    s = human_eval.Session(planner)
    try:
        for said in setup:
            s.say(said)
        if setup:
            s.at({"day": 9, "time": "19:00"})
            s.new_conversation()
        s.say(line)
        s.say("I had ramen for lunch")
        s.at({"day": 20, "time": "19:00"})
        s.new_conversation()
        start = len(calls)
        reply = s.say(question)[0]
        told = "\n".join(prompts.build_plan_parts(c, [], "friend", None, "(the time)", compact=True)[1] + "\n" + m[-1]["content"] for m, c in calls[start:])
        if old and old in reply and want not in reply:
            return "OLD"
        return "LUMA" if want in reply else "told" if want in told else "MISS"
    finally:
        s.close()


class TheSameFactTurnedAround(unittest.TestCase):
    def test_a_name_is_read_however_the_sentence_is_turned(self):
        self.assertEqual([said for said in NAMES if people.plainly(said) != ["My sister's name is Priya"]], [])

    def test_where_someone_lives_is_read_however_the_sentence_is_turned(self):
        self.assertEqual([said for said in HOMES if people.plainly(said) != ["My mom lives in Tampa"]], [])

    def test_a_move_is_read_by_its_signs_for_someone_luma_knows_by_name(self):
        self.assertEqual([said for said in MOVES if people.plainly(said, ["Marcus"]) != ["Marcus lives in Denver"]], [])
        self.assertEqual(people.plainly("my brother made the move to Denver"), ["My brother lives in Denver"])
        self.assertEqual(people.plainly("so Marcus packed up and left for Denver"), [], "a name Luma was never told is nobody's move")

    def test_near_misses_are_not_facts(self):
        self.assertEqual([said for said in NOT if people.plainly(said, ["Marcus"])], [])

    def test_the_plain_sentence_is_one_the_rest_of_luma_reads(self):
        self.assertEqual(facts.read("My sister's name is Priya").slots, [("rel:sister", "name", "priya")])
        self.assertEqual(facts.read("My mom lives in Tampa").slots, [("rel:mom", "home", "tampa")])
        self.assertEqual(facts.read("Marcus lives in Denver").slots, [("name:marcus", "home", "denver")])

    def test_one_fact_one_card(self):
        """Said the plain way the rules already read it: no second card. And "home for my mom is Tampa" doesn't name her Tampa."""
        for said in ("my sister's name is Priya", "my brother Marcus lives in Austin"):
            self.assertEqual(len(keeps.cards(said, model=False)), 1, said)
        self.assertEqual(keeps.cards("my mom lives in Tampa", model=False), [])   # read from the line itself, as it always was: no card added
        self.assertEqual(keeps.cards("home for my mom is Tampa", model=False), ["My mom lives in Tampa"])
        self.assertEqual(keeps.cards("my sister goes by Priya", model=False), ["My sister's name is Priya"])

    def test_a_name_is_asked_for_without_the_word(self):
        for question in ("remind me who my sister is", "my sister is who again", "what do I call my sister", "what does my sister go by", "tell me who my sister is"):
            self.assertEqual(facts.asked(question)["what"], "name", question)
        self.assertEqual(facts.asked("who is my sister married to")["what"], "spouse")


class ToldThenAsked(unittest.TestCase):
    def test_built_on_lines_luma_says_the_fact_itself(self):
        for line in NAMES[::3]:
            self.assertEqual(lived([], line, "what's my sister's name", "Priya"), "LUMA", line)
        for line in HOMES[::3]:
            self.assertEqual(lived([], line, "where does my mom live", "Tampa"), "LUMA", line)

    def test_the_honest_number_on_lines_nothing_was_built_on(self):
        """Measured once, Nov 20, 2026. Luma says it / a small brain is handed it / missed:
        names 5 / 2 / 3 of 10 (before: 1 / 0 / 9); homes 4 / 6 / 0 (before: 1 / 9 / 0); moves 4 / 4 / 0 of 8 (before: 3 / 5 / 0)."""
        floors = {"name": (5, 3), "home": (4, 0), "moved": (4, 0)}
        for kind, (lines, setup, question, want, old) in HONEST.items():
            got = [lived(setup, line, question, want, old) for line in lines]
            says, missed = floors[kind]
            self.assertGreaterEqual(got.count("LUMA"), says, f"{kind}: {got}")
            self.assertLessEqual(got.count("MISS"), missed, f"{kind}: {got}")
            self.assertEqual(got.count("OLD"), 0, f"{kind}: the old city, said flat")

    def test_luma_doesnt_say_it_was_never_told_when_something_kept_may_hold_it(self):
        import human_eval
        s = human_eval.Session(lambda messages, context, allowed, *a, **k: {"type": "reply", "text": "Okay."})
        try:
            s.say("this is my sister Priya")
            s.at({"day": 9, "time": "19:00"})
            s.new_conversation()
            self.assertTrue(s.agent._kept_might_say("what's my sister's name"))
            self.assertNotIn("I don't know", s.say("what's my sister's name")[0])
            self.assertFalse(s.agent._kept_might_say("what's my brother's name"))     # nothing kept about a brother
            self.assertIn("I don't know", s.say("what's my brother's name")[0])       # and that is still said plainly
        finally:
            s.close()


class AskedWithRemindMe(unittest.TestCase):
    """The month test's held-out lives, without a brain, fell from 40 of 40 to 20 of 40 on recall the hour the name became
    a fact (counted Nov 20, 2026; no line read): the question was read as "show my reminders" and answered "Nothing on your
    list right now". These lines are mine, written to find it. A question a saved fact answers is never a command."""

    ASKED = ["remind me what my sister's called", "what do I call my sister again", "can you remind me my sister's name", "my sister's name, remind me",
             "remind me who my sister is", "remind me of my sister's name", "could you tell me my sister's name"]
    # Each is something else, and stays so: a reminder with a time, the list, a phone call, a question that asks for more.
    NOT_THE_NAME = ["has my sister called?", "remind me to call my sister at 5", "remind me of my sister's birthday tomorrow at 9", "what are my reminders",
                    "who called my sister", "what did my sister call about", "remind me what's on my list", "can you remind me to text my sister tonight"]

    def setUp(self):
        import human_eval
        self.calls = []

        def planner(messages, context, allowed, *args, **kwargs):
            self.calls.append(list(messages))
            return {"type": "reply", "text": f"Okay, {len(self.calls)}."}

        self.s = human_eval.Session(planner)
        for said in ("my sister goes by Priya", "my sister called me today"):
            self.s.say(said)
        self.s.at({"day": 17, "time": "19:00"})
        self.s.new_conversation()

    def tearDown(self):
        self.s.close()

    def test_luma_says_the_name_and_makes_nothing(self):
        for question in self.ASKED:
            out = self.s.agent.chat(question)
            self.assertEqual(out.get("text"), "Your sister's name is Priya.", question)
            self.assertNotIn("action", out, question)      # no task made, no list opened
            self.assertNotIn("cut_off", out, question)
            self.s.new_conversation()
        self.assertEqual(self.s.agent.propose("tasks.list", {}).get("tasks"), [])

    def test_a_reminder_the_list_and_a_phone_call_stay_what_they_are(self):
        for question in self.NOT_THE_NAME:
            out = self.s.agent.chat(question)
            self.assertNotIn("Priya", str(out.get("text") or out.get("summary") or ""), question)
            self.s.new_conversation()
        made = [t["title"] for t in self.s.agent.propose("tasks.list", {})["tasks"]]
        self.assertEqual(len(made), 3, made)               # the three reminders were made, and nothing else


class AMoveDoesntHoldBackAName(unittest.TestCase):
    """When something newer has been said about a person that Luma can't read as a fact, where they live goes to the brain
    with both lines (never the old city, flat). That guard was also holding back their name: on the month test's held-out
    lives 8 of 8 name questions went to the brain for it (counted Nov 20, 2026; no line read). These lines are mine."""

    def setUp(self):
        import human_eval
        self.calls = []

        def planner(messages, context, allowed, *args, **kwargs):
            self.calls.append(list(messages))
            return {"type": "reply", "text": f"Okay, {len(self.calls)}."}

        self.s = human_eval.Session(planner)
        for said in ("my sister goes by Priya", "my sister's birthday is March 4", "my sister lives in Austin"):
            self.s.say(said)
        self.s.at({"day": 9, "time": "19:00"})
        self.s.new_conversation()
        for said in ("my sister's whole life is in Denver these days", "my sister said the apartment in Denver has a view"):
            self.s.say(said)
        self.s.at({"day": 17, "time": "19:00"})
        self.s.new_conversation()

    def tearDown(self):
        self.s.close()

    def test_her_name_and_birthday_are_still_said_by_luma(self):
        for question, want in (("what's my sister's name", "Your sister's name is Priya."), ("remind me what my sister's called", "Your sister's name is Priya."),
                               ("when's my sister's birthday", "Your sister's birthday is March 4.")):
            before = len(self.calls)
            self.assertEqual(self.s.agent.chat(question).get("text"), want, question)
            self.assertEqual(len(self.calls), before, question)   # no brain needed
            self.s.new_conversation()

    def test_where_she_lives_is_still_the_brains_with_both(self):
        for question in ("where does my sister live", "where does my sister live now"):
            before = len(self.calls)
            self.assertNotIn("Austin", str(self.s.agent.chat(question).get("text")), question)
            self.assertGreater(len(self.calls), before, question)
            self.s.new_conversation()


if __name__ == "__main__":
    unittest.main()
