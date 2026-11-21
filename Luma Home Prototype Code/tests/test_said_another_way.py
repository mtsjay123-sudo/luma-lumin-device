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


class ABirthdayAJobAnAllergy(unittest.TestCase):
    """The same method for three more facts (Nov 21, 2026). Twenty-four lines written by hand, eight of each, told to Luma
    and asked about weeks later: Luma said 6 back, and to 10 it answered "I don't know ... yet" after being told. The
    readers were built on those 24 and on the near misses. HONEST was written after the readers were finished and
    measured once; nothing was changed for it."""

    BUILT_ON = {
        "birthday": (["my mom was born on June 3", "June 3 is my mom's birthday", "my mom turns 60 on June 3", "we celebrate my mom's birthday on June 3",
                      "my mom's bday is June 3", "my mom has a birthday coming up, June 3", "the 3rd of June is when my mom was born"],
                     "My mom's birthday is ", "when's my mom's birthday", "June"),
        "work": (["my brother's a nurse at Mercy Hospital", "my brother got hired at Mercy Hospital", "my brother has been at Mercy Hospital for years, he's a nurse",
                  "Mercy Hospital is where my brother works", "my brother's job is at Mercy Hospital", "my brother does nursing over at Mercy Hospital",
                  "my brother is employed by Mercy Hospital", "my brother just started a job with Mercy Hospital"],
                 "My brother works at Mercy Hospital", "where does my brother work", "Mercy"),
        "allergy": (["my sister can't eat peanuts", "my sister has a peanut allergy", "peanuts make my sister break out in hives",
                     "my sister is deathly allergic to peanuts", "no peanuts for my sister, allergy", "my sister carries an epipen for peanuts"],
                    "My sister ", "what is my sister allergic to", "peanut"),
    }
    NOT = ["my mom's birthday party is on June 3", "my mom turns 60 next year", "my mom was born in 1962", "my mom was born on June 3 or 4, I forget",
           "is my mom's birthday June 3", "my brother wants to work at Mercy Hospital", "my brother applied at Mercy Hospital",
           "my brother used to work at Mercy Hospital", "my brother got fired from Mercy Hospital", "my brother is a patient at Mercy Hospital",
           "my sister is a student at Ohio State", "my brother is a regular at Joe's Bar",
           "my brother has been at Mercy Hospital for years, the doctors still don't know what's wrong", "my sister can't eat until noon",
           "my sister can't have dessert tonight", "my sister can't have kids", "my sister can't have visitors yet", "my mom is so allergic to mornings lol",
           "my dad is allergic to effort", "my sister can't eat out this week", "my brother might start at Mercy Hospital in the spring",
           "my sister has a peanut butter obsession", "my mom has a birthday coming up", "my brother got a job offer but turned down Mercy Hospital"]
    HONEST = {
        "birthday": (["my dad's birthday falls on March 12", "March 12, that's my dad's birthday", "my dad was born March 12, 1960", "dad's birthday is March 12",
                      "my dad will be 70 on March 12", "we always do dinner for my dad's birthday, March 12"], "when's my dad's birthday", "March"),
        "work": (["my sister works over at Target", "my sister's a cashier at Target", "my sister has a job at Target", "Target hired my sister last month",
                  "my sister's been working at Target since June", "my sister manages a Target"], "where does my sister work", "Target"),
        "allergy": (["my brother has a shellfish allergy", "my brother can't eat shellfish", "shellfish sends my brother to the ER",
                     "my brother's allergic to shellfish", "my brother breaks out if he eats shellfish", "don't ever give my brother shellfish, he's allergic"],
                    "what is my brother allergic to", "shellfish"),
    }
    HONEST_NOT = ["my dad's retirement party is March 12", "my sister shops at Target every week", "my brother hates shellfish", "my sister interviewed at Target",
                  "my dad was born in March, I think", "my brother can't eat this late"]

    def test_each_is_turned_into_the_plain_sentence_and_read_as_that_fact(self):
        for kind, (lines, plain, _, want) in self.BUILT_ON.items():
            for line in lines:
                got = people.plainly(line)
                self.assertEqual(len(got), 1, line)
                self.assertTrue(got[0].startswith(plain), (line, got))
                reading = facts.read(got[0])
                self.assertTrue(reading and any(slot[1] == kind and want.lower() in slot[2] for slot in reading.slots), (line, got))

    def test_near_misses_are_not_facts(self):
        self.assertEqual([line for line in self.NOT + self.HONEST_NOT if people.plainly(line)], [])

    def test_a_person_who_cant_have_kids_is_never_a_food_fact(self):
        self.assertEqual(keeps.cards("my sister can't have kids", model=False), [])
        self.assertEqual(people.plainly("my sister can't have dairy"), ["My sister can't eat dairy"])

    def test_told_then_asked_luma_says_it(self):
        for kind, (lines, _, question, want) in self.BUILT_ON.items():
            for line in lines[::3]:
                self.assertEqual(lived([], line, question, want), "LUMA", line)

    def test_the_honest_number_on_lines_nothing_was_built_on(self):
        """Measured once, Nov 21, 2026. Luma says it / a small brain is handed it / missed:
        birthdays 4 / 0 / 2 of 6 (before: 3 / 0 / 3); jobs 1 / 5 / 0 (before: 0 / 6 / 0); allergies 4 / 0 / 2 (before: 2 / 0 / 4)."""
        floors = {"birthday": (4, 2), "work": (1, 0), "allergy": (4, 2)}
        for kind, (lines, question, want) in self.HONEST.items():
            got = [lived([], line, question, want) for line in lines]
            says, missed = floors[kind]
            self.assertGreaterEqual(got.count("LUMA"), says, f"{kind}: {got}")
            self.assertLessEqual(got.count("MISS"), missed, f"{kind}: {got}")


class AboutThemselves(unittest.TestCase):
    """The same method for what they say about themselves (Nov 21, 2026): a job, a birthday, where they're from, a pet's
    name. BUILT_ON: 24 lines written by hand, told to Luma and asked about weeks later. Luma said 9 back, a small brain was
    handed 6, and 9 were lost ("I turn 40 on May 12", then "I don't know your birthday yet"). The readers were built on those and
    on the near misses. HONEST was written after the readers were finished and measured once; nothing was changed for
    it, except two ways Luma worded an answer ("You was raised in Fresno", "I don't know your birthday again yet")."""

    BUILT_ON = [
        ("I work at the library downtown", "where do I work?", "library"), ("I just started at Costco last week", "where do I work again", "Costco"),
        ("I'm a nurse at St. Mary's", "what do I do for work?", "nurse"), ("been driving for UPS for six years now", "who do I work for?", "UPS"),
        ("my birthday is March 9", "when's my birthday?", "March 9"), ("I turn 40 on May 12", "when is my birthday", "May 12"),
        ("I was born on July 4th", "do you remember my birthday?", "July 4"), ("my bday's the 21st of October", "what day is my birthday?", "October"),
        ("I'm allergic to shellfish", "what am I allergic to?", "shellfish"), ("I can't eat gluten", "what can't I eat?", "gluten"),
        ("I'm a vegetarian", "do I eat meat?", "vegetarian"), ("penicillin gives me hives, I'm allergic", "which medicine am I allergic to?", "penicillin"),
        ("my dog's name is Biscuit", "what's my dog's name?", "Biscuit"), ("we named the kitten Mochi", "what did we name the kitten?", "Mochi"),
        ("I have a cat called Pepper", "what's my cat called?", "Pepper"), ("Biscuit is my dog, he's a beagle", "what kind of dog is Biscuit?", "beagle"),
        ("I live in Osaka", "where do I live?", "Osaka"), ("I grew up in Ohio", "where did I grow up?", "Ohio"),
        ("I'm from Tucson originally", "where am I from?", "Tucson"), ("we moved to Fukuoka in the spring", "where do I live now?", "Fukuoka"),
        ("my favorite food is ramen", "what's my favorite food?", "ramen"), ("I drive a blue Honda Civic", "what car do I drive?", "Civic"),
        ("I root for the Mariners", "which team do I root for?", "Mariners"), ("my middle name is Rae", "what's my middle name?", "Rae"),
    ]
    TURNED = {"I just started at Costco last week": "I work at Costco", "I'm a nurse at St. Mary's": "I work as a nurse at St. Mary's",
              "been driving for UPS for six years now": "I work for UPS", "I turn 40 on May 12": "My birthday is May 12",
              "I was born on July 4th": "My birthday is July 4th", "my bday's the 21st of October": "My birthday is the 21st of October",
              "we named the kitten Mochi": "My kitten's name is Mochi", "Biscuit is my dog, he's a beagle": "My dog's name is Biscuit",
              "I've been cooking at Denny's since March": "I work at Denny's", "born and raised in Dayton": "I grew up in Dayton",
              "Ohio is where I grew up": "I grew up in Ohio", "I come from Lisbon": "I'm from Lisbon"}
    NOT = ["I'm a regular at Joe's Diner", "I'm a beast at Mario Kart", "I'm a senior at Lincoln High", "I used to work at Costco", "I applied at Costco last week",
           "I might start at Target next month", "I started at Planet Fitness yesterday", "I work with Dana on Tuesdays", "I shop at Costco every Sunday",
           "my interview is at Google tomorrow", "I'm working at Starbucks today to get out of the house", "I quit my job at Walmart", "I got fired from Amazon",
           "I'm a huge fan of Costco", "if I worked at Disney I'd never leave", "my brother has been driving for UPS for years", "I'm a student at Ohio State",
           "I turn 40 next year", "I was born in a hospital in the middle of a blizzard", "my birthday party is on Saturday",
           "I feel like I was born on the wrong planet", "I was born in June", "I think my birthday dinner is on May 12", "my passport expires on March 9",
           "I'm from the future", "I just came from Target", "I grew up in a small town", "I grew up poor", "I'm back from Denver", "I got a call from Chicago",
           "I'm from HR", "my wife says I'm from Mars", "I wish I grew up in Hawaii", "I'm visiting from Chicago this week",
           "my sister was born and raised in Ohio", "this is my dog", "That is my cat on the couch", "we called the vet about the kitten",
           "I named the file Report", "Here is my cat", "we might name the puppy Max", "what did we name the kitten?", "where did I grow up?", "when was I born?"]
    HONEST = [
        ("I teach third grade over at Lincoln Elementary", "where do I work?", "Lincoln"), ("got hired at Trader Joe's, I start Monday", "where do I work now?", "Trader Joe's"),
        ("I'm a line cook at Denny's", "what's my job again?", "cook"), ("I've been with Delta for eleven years", "who do I work for?", "Delta"),
        ("I do IT support for the county", "what do I do for a living?", "IT support"), ("my job's at the Honda plant", "where do I work?", "Honda"),
        ("my birthday's coming up, June 14", "when's my birthday?", "June 14"), ("I'll be 33 on the 2nd of August", "when is my birthday?", "August"),
        ("born December 1st, a winter baby", "when was I born?", "December 1"), ("October 30 is my birthday", "what's my birthday?", "October 30"),
        ("I'm a March baby, the 17th", "when's my birthday again?", "17"), ("I'm a Texas girl, born and raised in Lubbock", "where did I grow up?", "Lubbock"),
        ("originally I'm from Manila", "where am I from?", "Manila"), ("I was raised in Fresno by my grandparents", "where was I raised?", "Fresno"),
        ("Detroit's my hometown", "where did I grow up?", "Detroit"), ("I spent my whole childhood in Lagos", "where am I from again?", "Lagos"),
        ("our new puppy is called Waffles", "what's my puppy's name?", "Waffles"), ("I named my cat Miso", "what's my cat's name?", "Miso"),
        ("Juniper is our rabbit", "what's our rabbit called?", "Juniper"), ("my parrot answers to Kiwi", "what's my parrot's name?", "Kiwi"),
        ("I have a peanut allergy", "what am I allergic to?", "peanut"), ("dairy doesn't agree with me, I'm lactose intolerant", "what can't I eat?", "lactose"),
        ("I live out in Sapporo these days", "where do I live?", "Sapporo"), ("we just bought a house in Raleigh", "where do I live now?", "Raleigh"),
    ]

    @staticmethod
    def about_them(line):
        """What the readers take from a line as a fact about the person talking (a job, a birthday, where they're from, a pet's name)."""
        pets = {"dog", "cat", "kitten", "puppy", "rabbit", "parrot"}
        slots = [slot for text in [line] + people.plainly(line) for slot in (getattr(facts.read(text), "slots", None) or [])]
        return [slot for slot in slots if (slot[0] == "you" and slot[1] in ("work", "birthday", "from"))
                or (slot[1] == "name" and slot[0].startswith("rel:") and slot[0][4:] in pets)]

    def test_each_is_turned_into_the_plain_sentence(self):
        for line, plain in self.TURNED.items():
            self.assertEqual(people.plainly(line), [plain], line)
            self.assertTrue(self.about_them(plain), plain)

    def test_where_they_are_from_is_its_own_fact_and_its_own_question(self):
        for line, who in (("I grew up in Ohio", "you"), ("I'm from Tucson originally", "you"), ("I was born in Osaka", "you"),
                          ("my dad is from Osaka originally", "rel:dad"), ("my mom grew up in Tampa", "rel:mom")):
            self.assertEqual([(slot[0], slot[1]) for slot in facts.read(line).slots], [(who, "from")], line)
        for question in ("where did I grow up?", "where am I from?", "where was I born?", "where is my dad from?", "where did my mom grow up"):
            self.assertEqual(facts.asked(question)["what"], "from", question)
        for question in ("when was I born", "where do I live?", "where does my mom live"):
            self.assertNotEqual(facts.asked(question)["what"], "from", question)

    def test_near_misses_are_not_facts_about_them(self):
        self.assertEqual([line for line in self.NOT if self.about_them(line)], [])

    def test_only_a_question_about_the_fact_is_answered_from_it(self):
        from luma.agent.runtime import Agent
        for question in ("who do I work for?", "where am I from again", "what am I allergic to?", "where do I work again", "can you remind me where I work",
                         "do you remember where I grew up", "when was I born?", "what can't I eat?"):
            self.assertTrue(Agent.OWN_SELF_ASK.match(Agent.POLITE_ASK.sub("", question)), question)
        for question in ("what do I do?", "what do I do now", "where do I go from here", "who do I call about this", "what am I doing wrong",
                         "where am I supposed to park", "when do I leave for the airport", "what can I eat tonight", "where did I put my keys",
                         "who do I work with on Friday", "where should I work today"):
            self.assertFalse(Agent.OWN_SELF_ASK.match(Agent.POLITE_ASK.sub("", question)), question)

    def test_said_back_in_good_english(self):
        from luma.agent.runtime import Agent
        self.assertEqual(Agent._yours("I was raised in Fresno by my grandparents"), "You were raised in Fresno by your grandparents")
        self.assertEqual(Agent._yours("I am allergic to shellfish"), "You are allergic to shellfish")
        self.assertEqual(Agent._yours("I work at Costco"), "You work at Costco")

    def test_told_then_asked_what_was_built_on(self):
        """Measured Nov 21, 2026: Luma says it 19 of 24 (before: 9), a small brain is handed 3 (6), lost 2 (9)."""
        got = [lived([], line, question, want) for line, question, want in self.BUILT_ON]
        self.assertGreaterEqual(got.count("LUMA"), 19, got)
        self.assertLessEqual(got.count("MISS"), 2, got)

    def test_the_honest_number_on_lines_nothing_was_built_on(self):
        """Measured once, Nov 21, 2026: Luma says it 12 of 24 (before: 4), a small brain is handed 1 (2), lost 11 (18)."""
        got = [lived([], line, question, want) for line, question, want in self.HONEST]
        self.assertGreaterEqual(got.count("LUMA"), 12, got)
        self.assertLessEqual(got.count("MISS"), 11, got)

    def test_two_allergies_are_the_brains_to_say_together(self):
        self.assertEqual(lived(["I'm allergic to shellfish"], "I can't eat gluten", "what am I allergic to?", "gluten"), "told")


if __name__ == "__main__":
    unittest.main()
