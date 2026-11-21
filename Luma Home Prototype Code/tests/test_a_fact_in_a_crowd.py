"""A fact among a thousand memories (Nov 21, 2026): is the thing they told Luma in the first five it finds?

The memory test's lives ask about the facts those lives were built from. These are other things people tell a friend
(a dentist, where the spare key is, a daughter's cello), each asked plainly and asked in other words, hidden in one of
the memory test's built-on lives so there are a thousand other memories around, a mom, a daughter and a boss already.

BUILT_ON: forty, written without reading the memory test's templates. What they showed, and what was fixed:
- "what are my mom's favorite flowers" was handed five other facts about mom: whatever else is kept about a person came
  before the one memory that has the question's own words. A memory that stands out by its words now comes right after
  the fact itself (luma.memory.index, "1a").
- "what do i do on saturday mornings" and "which race am i running this fall" were answered "nothing saved from then":
  a habit and something still to come were read as a day to look back at (when.said_then).
- "what flowers should i get my mother" was "nobody saved as my mother" with "mom" in every memory (index.KIN).
- The same sentence said six times filled the list by itself; it's handed over once.
- A few more everyday words for the same thing (index._SAME), from these forty only.
Found in the first five: asked plainly 31 -> 38 of 40, in other words 17 -> 27; wrongly "never told" 8 -> 0.

SECOND: forty more, written before any of that was built and measured once before and once after. The honest number:
asked plainly 33 -> 38 of 40; in other words 17 -> 19; wrongly "never told" 12 -> 11. So the order is better and what's
asked in other words mostly isn't: no word of the question is in the memory ("who do i see about my glasses" / "my eye
doctor is Dr. Marchetti"), and without the meaning model (computers with 16 GB) Luma can't tell that from never told.

The memory test's own numbers are the same on both halves before and after (held out: 159 of 187, 102 of 135)."""
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

BUILT_ON = [
    ('my dentist is Dr. Okafor on Maple Street', "who's my dentist", 'which doctor do i see for my teeth'),
    ('I keep the spare key under the blue flowerpot', "where's my spare key", "how do i get in if i'm locked out"),
    ('my wifi password is on a sticky note inside the pantry door', 'where did i put the wifi password', "where's the note with the internet login"),
    ('I take my blood pressure pill every morning with breakfast', 'when do i take my blood pressure pill', 'what time of day is my heart medication'),
    ('my car is a 2014 Honda Civic', 'what car do i drive', 'what make is my vehicle'),
    ('my anniversary is October 3rd', 'when is my anniversary', 'what day did i get married'),
    ("my landlord's name is Mr. Petrov", "what's my landlord's name", 'who do i pay rent to'),
    ("I'm a size 9 and a half in shoes", "what's my shoe size", 'what size sneakers do i wear'),
    ('my daughter Imani plays the cello', 'what instrument does my daughter play', 'what does imani play in the orchestra'),
    ('I park on level 3 of the Grant Street garage', 'where do i park', 'which floor of the garage is my car on'),
    ('my best friend from college is Teodoro', "who's my best friend from college", 'who was i closest to at university'),
    ("I get my hair cut at Lucille's on 5th", 'where do i get my hair cut', "what's the name of my salon"),
    ("my son's soccer practice is on Wednesdays at 4", "when is my son's soccer practice", 'what day does my boy have football training'),
    ("I'm lactose intolerant", 'am i lactose intolerant', 'can i have dairy'),
    ("my grandmother's maiden name was Kowalczyk", "what was my grandmother's maiden name", 'what was grandma called before she married'),
    ("I'm training for the Chicago marathon in October", 'what marathon am i training for', 'which race am i running this fall'),
    ('my favorite tea is jasmine', "what's my favorite tea", 'what tea do i like best'),
    ('my boss is named Henrietta', "what's my boss's name", 'who do i report to at work'),
    ("the dog's vet is Riverside Animal Clinic", "who's the dog's vet", "where do i take the dog when he's sick"),
    ('I was born in Tucson', 'where was i born', 'what city am i originally from'),
    ('my locker combination is 14 32 8', "what's my locker combination", 'what are the numbers for my gym lock'),
    ('my mechanic is Sal at Fairview Auto', "who's my mechanic", 'where do i get my car fixed'),
    ('I sing tenor in the church choir', 'what do i sing in the choir', "what's my voice part"),
    ('my nephew Dario is seven', 'how old is my nephew', 'what age is dario'),
    ('I usually order the pad see ew from Thai Orchid', 'what do i order from thai orchid', "what's my usual at the thai place"),
    ('my wife is allergic to shellfish', 'what is my wife allergic to', "what can't my wife eat"),
    ('my library card number ends in 4471', 'what does my library card number end in', 'what are the last digits of my library card'),
    ('I volunteer at the food bank on Saturday mornings', 'when do i volunteer at the food bank', 'what do i do on saturday mornings'),
    ('my brother-in-law Wes is a firefighter', 'what does my brother-in-law do', "what's wes's job"),
    ('the recycling goes out every other Thursday', 'when does the recycling go out', 'what day is recycling pickup'),
    ('my passport expires in March 2029', 'when does my passport expire', 'how long is my passport good for'),
    ('I learned to swim at Lake Wenatchee', 'where did i learn to swim', 'which lake did i learn swimming in'),
    ('my accountant is Priscilla Vance', "who's my accountant", 'who does my taxes'),
    ("my mom's favorite flowers are peonies", "what are my mom's favorite flowers", 'what flowers should i get my mother'),
    ("I've been vegetarian since 2019", 'how long have i been vegetarian', 'when did i stop eating meat'),
    ('my seat at the stadium is section 112 row F', "where's my seat at the stadium", 'which section do i sit in at the games'),
    ("the baby's pediatrician is Dr. Lindqvist", "who's the baby's pediatrician", 'which doctor does the baby see'),
    ('my first car was a red Datsun', 'what was my first car', 'what did i drive when i first got my license'),
    ('I keep the Christmas decorations in the attic crawl space', 'where are the christmas decorations', 'where did i store the holiday stuff'),
    ('my study group meets in room 204 of the science building', 'where does my study group meet', 'which room is my study group in'),
]
SECOND = [
    ('my eye doctor is Dr. Marchetti', "who's my eye doctor", 'who do i see about my glasses'),
    ('the fuse box is in the hallway closet', "where's the fuse box", 'where do i go when the power trips'),
    ("I'm allergic to penicillin", 'what am i allergic to', "which antibiotic can't i take"),
    ('my gym membership renews on the 15th', 'when does my gym membership renew', 'what day do they charge me for the gym'),
    ('my cousin Odalys teaches kindergarten', 'what does my cousin do', 'what grade does odalys teach'),
    ('I take the 7:42 train to work', 'what train do i take to work', 'what time is my morning commute'),
    ('my blood type is O negative', "what's my blood type", 'what type of blood do i have'),
    ("the plumber's number is on the fridge", "where's the plumber's number", 'who do i call about a leak'),
    ('my aunt Rosalind lives in Savannah', 'where does my aunt live', 'which city is rosalind in'),
    ("I'm reading Middlemarch for book club", 'what am i reading for book club', 'which novel is my reading group on'),
    ("my uncle's birthday is July 22nd", "when is my uncle's birthday", 'what day was my uncle born'),
    ('I buy my coffee beans from Finch Roasters', 'where do i buy my coffee beans', 'which roaster do i get my coffee from'),
    ('my niece Talia is starting high school this year', 'what is my niece starting this year', 'what school year is talia going into'),
    ('the car insurance is with Ridgeline Mutual', "who's my car insurance with", 'which company insures my vehicle'),
    ('my therapist is on Thursdays at 5', 'when is my therapist', 'what day do i have counseling'),
    ('I keep my passport in the fireproof box under the bed', "where's my passport", 'where do i keep my travel documents'),
    ("my neighbor Mr. Abernathy feeds the cat when I'm away", "who feeds the cat when i'm away", 'who looks after my pet when i travel'),
    ("I'm doing a pottery class on Monday nights", 'what class am i doing on monday nights', 'when is my ceramics class'),
    ("my favorite pizza place is Luigi's on Dell Avenue", "what's my favorite pizza place", 'where do i like to get pizza'),
    ('my roommate Sunniva works night shifts at the hospital', 'what shifts does my roommate work', 'when is sunniva at work'),
    ('the trash goes out Monday and Thursday', 'when does the trash go out', 'what days is garbage pickup'),
    ('I ran my first 10k in 58 minutes', 'how fast was my first 10k', 'what was my time in my first race'),
    ('my stepdad Gerald collects stamps', 'what does my stepdad collect', "what's gerald's hobby"),
    ("I'm saving up for a trip to Portugal next spring", 'what am i saving up for', 'where am i planning to travel'),
    ('my phone plan is with Northwind Mobile', "who's my phone plan with", 'which carrier am i on'),
    ('the dog gets his heartworm pill on the first of the month', 'when does the dog get his heartworm pill', "what day is the dog's medicine"),
    ('my mother-in-law is vegan', 'is my mother-in-law vegan', 'does my mother-in-law eat meat'),
    ('I teach Sunday school to the third graders', 'who do i teach at sunday school', 'which grade is my church class'),
    ('my bike is a blue Trek with a basket', 'what does my bike look like', 'what kind of bicycle do i have'),
    ('I get migraines when I skip lunch', 'when do i get migraines', 'what gives me headaches'),
    ('my godson Elio was baptized in April', 'when was my godson baptized', "what month was elio's christening"),
    ('the wifi router is behind the bookshelf', "where's the wifi router", "where's the internet box"),
    ('my coworker Bartholomew is retiring in June', 'when is my coworker retiring', 'who at work is leaving in june'),
    ('I donate blood every eight weeks', 'how often do i donate blood', 'how frequently do i give blood'),
    ('my high school mascot was the Fighting Herons', 'what was my high school mascot', 'what were we called at my high school'),
    ("I'm trying to drink eight glasses of water a day", 'how much water am i trying to drink', "what's my hydration goal"),
    ('my tailor is on the corner of 9th and Alder', "where's my tailor", 'where do i get my pants hemmed'),
    ("the kids' bedtime is 8:30 on school nights", "what's the kids' bedtime", 'when do the children go to sleep on weeknights'),
    ('my lease ends on August 31st', 'when does my lease end', 'how long do i have the apartment for'),
    ('I proposed to my partner at Cannon Beach', 'where did i propose', 'where did i get engaged'),
]


def asked(facts):
    """(found asked plainly, found asked in other words, wrongly "never told") for facts hidden in a built-on life."""
    import memory_eval
    from luma.memory.store import Store
    life = memory_eval.Life(11, 1000, "dev")
    rng = random.Random(4)
    times = sorted(m["created"] for m in life.memories)
    mine = [{"text": said, "source": "said", "created": rng.uniform(times[100], times[-50]), "id": f"x{i}"} for i, (said, _, _) in enumerate(facts)]
    life.memories = sorted(list(life.memories) + mine, key=lambda m: m["created"])
    plain = other = never = 0
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "s.db", Path(folder) / "k")
        try:
            memory_eval.fill(store, life)
            for said, first, second in facts:
                for which, question in (("plain", first), ("other", second)):
                    found, never_told = memory_eval.look_up(store, question)[:2]
                    hit = any(said.lower() == str(m.get("text", "")).lower() for m in found)
                    plain += hit and which == "plain"
                    other += hit and which == "other"
                    never += bool(never_told)
        finally:
            store.close()
    return plain, other, never


class AFactInACrowd(unittest.TestCase):
    def test_the_lines_it_was_built_on(self):
        plain, other, never = asked(BUILT_ON)
        self.assertGreaterEqual(plain, 38, plain)
        self.assertGreaterEqual(other, 27, other)
        self.assertEqual(never, 0, never)

    def test_the_honest_number(self):
        plain, other, never = asked(SECOND)
        self.assertGreaterEqual(plain, 38, plain)
        self.assertGreaterEqual(other, 19, other)
        self.assertLessEqual(never, 11, never)


class WhatChanged(unittest.TestCase):
    def setUp(self):
        from luma.memory.store import Store
        self.folder = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.folder.name) / "s.db", Path(self.folder.name) / "k")

    def tearDown(self):
        self.store.close()
        self.folder.cleanup()

    def keep(self, *lines):
        import time
        now = time.time()
        self.store.put_many("memory", [{"text": line, "source": "said", "created": now - 86400 * (len(lines) - i + 30), "category": "notes"}
                                       for i, line in enumerate(lines)])

    def texts(self, question):
        found = self.store.search(question)
        return [m["text"] for m in found["memories"]], found

    def test_a_habit_and_something_still_to_come_arent_a_day_to_look_back_at(self):
        from luma.memory import when
        self.keep("I volunteer at the food bank on Saturday mornings", "I'm training for the Chicago marathon in October", "the bus was late again")
        for question in ("what do i do on saturday mornings", "which marathon am i running this fall"):
            texts, found = self.texts(question)
            self.assertTrue(found["known"], question)
            self.assertTrue(texts, question)
        self.assertFalse(when.said_then("what do i do on saturday mornings"))
        self.assertFalse(when.said_then("what am i doing this weekend", "this weekend"))
        self.assertTrue(when.said_then("what did i do last saturday", "last saturday"))
        self.assertTrue(when.said_then("what happened in march", "in march"))

    def test_looking_back_still_means_only_what_was_kept_then(self):
        self.keep("I volunteer at the food bank on Saturday mornings")
        texts, found = self.texts("what did i tell you yesterday")
        self.assertFalse(found["known"])

    def test_my_mother_is_my_mom(self):
        self.keep("my mom's favorite flowers are peonies", "my dad's truck is a Ford", "I had pasta for dinner")
        texts, found = self.texts("what flowers should i get my mother")
        self.assertTrue(found["known"], found["why"])
        self.assertIn("my mom's favorite flowers are peonies", texts)
        texts, found = self.texts("what does my father drive")
        self.assertIn("my dad's truck is a Ford", texts)
        texts, found = self.texts("what's my godmother's name")       # nobody by that name or any other word for it
        self.assertFalse(found["known"])

    def test_the_same_sentence_is_handed_over_once(self):
        self.keep(*["Took the car in, it's making that noise again"] * 6, "my car is a 2014 Honda Civic")
        texts, _ = self.texts("what about my car")
        self.assertEqual(len(texts), len(set(texts)))
        self.assertIn("my car is a 2014 Honda Civic", texts)


if __name__ == "__main__":
    unittest.main()
