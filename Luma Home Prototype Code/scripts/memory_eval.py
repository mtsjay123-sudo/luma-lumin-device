#!/usr/bin/env python3
"""The memory test: does Luma find what someone told it, years and a million memories later?

Made-up lives, built from a seed (never real people): a family, friends, a job, moves, pets, trips, and the small talk of
every day. Each life is the same people and the same facts at every size; a bigger life only has more days around them.
Then questions, each with the memories that answer it:

- fact:   "what's my sister's name"                      the memory that says it is in the top 5
- reword: "what does Dana do for a living"               the same, asked in other words
- hop:    "what does my sister's husband do"             the answer is two memories away
- time:   "where did i travel in may 2024"               the memory from then, not from another year
- update: "where do i live"                              the newest fact is first, ahead of the old ones
- never:  "what's my uncle's name" (no uncle)            Luma says it wasn't told, and returns nothing as an answer
- forget: after "forget", no trace in any store

Two splits. `dev` is for building. `heldout` has other seeds AND other wording (for the memories and the questions); its
misses are never printed, only its totals, so nothing can be tuned on it.

  python scripts/memory_eval.py run --sizes 1000,10000,100000 --split dev --save out/memory-dev.json
  python scripts/memory_eval.py run --sizes 1000000 --queries 40
  python scripts/memory_eval.py summary out/memory-dev.json out/memory-heldout.json
"""
from __future__ import annotations

import argparse
import json
import random
import resource
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)   # "today" in every made-up life
DAY = 86400
SEEDS = {"dev": (11, 12, 13), "heldout": (211, 212, 213)}

NAMES = """Dana Marcus Lily Sam Priya Tomas Noor Jules Imani Kenji Rosa Felix Mina Otis Zara Leo Nia Hugo Ana Cyrus Maya Dev Tess Omar
Lena Kofi Iris Milo Sana Ravi Elsa Theo Yara Nico Hana Abel Cleo Ezra Luz Remy Asha Joss Vera Enzo Skye Amir Bea Dane Faye Gus Ines Jax Kira
Lars Mae Ned Opal Paz Quin Rhea Sol Tia Uma Van Wren Xavi Yuki Zeke Alma Beck Cora Dov Edie Finn Gia Hank Isla Joan Kai Lola Moss Nell Odin
Pia Reid Suki Tate Una Vito Wynn Aria Bram Cass Dima Eden Flor Gray Hope Ivo Jude Kate Luca Mari Nash Olga Penn Rae Shay Troy Ula Vida Wes""".split()
RELATIONS = ["sister", "brother", "mom", "dad", "wife", "daughter", "son", "grandma", "best friend", "cousin", "roommate", "boss"]
MISSING = ["uncle", "aunt", "nephew", "niece", "grandpa", "stepdad", "godmother", "landlord"]   # never in any life
CITIES = """Austin Denver Lisbon Chicago Seattle Portland Boston Miami Phoenix Atlanta Nashville Oakland Tucson Madison Raleigh
Savannah Boise Tulsa Omaha Reno Tampa Dallas Detroit Memphis Buffalo Fresno Tacoma Spokane Albany Dayton""".split()
TRIPS = """Lisbon Kyoto Oaxaca Reykjavik Montreal Havana Dublin Marrakesh Seoul Cusco Prague Hanoi Cartagena Vienna Banff Santorini
Zanzibar Edinburgh Bali Queenstown""".split()
JOBS = ["nurse", "welder", "pilot", "line cook", "teacher", "paramedic", "plumber", "dental hygienist", "bus driver", "librarian",
        "electrician", "florist", "barber", "bookkeeper", "truck driver", "pharmacist", "carpenter", "social worker"]
COMPANIES = ["Brightside Dental", "Harbor Freightways", "Northgate Clinic", "Copperline Foods", "Ridgeview School", "Tallgrass Supply",
             "Blue Heron Books", "Ironwood Builders", "Sunmark Pharmacy", "Lakeshore Transit", "Juniper Bakery", "Redfern Auto"]
HOBBIES = ["bouldering", "woodworking", "birdwatching", "pottery", "salsa dancing", "fly fishing", "quilting", "chess", "beekeeping",
           "roller derby", "sourdough baking", "archery", "karaoke", "gardening", "kayaking", "crochet"]
SPECIES = ["dog", "cat", "parrot", "rabbit", "hamster", "turtle"]
PETS = ["Biscuit", "Pepper", "Mochi", "Waffles", "Gizmo", "Olive", "Bandit", "Clover", "Ziggy", "Pickle", "Juno", "Nacho"]
FOODS = ["tacos", "pad thai", "ramen", "lasagna", "jollof rice", "pho", "dumplings", "gumbo", "pupusas", "biryani", "pierogi", "shakshuka"]
ALLERGENS = ["peanuts", "shellfish", "penicillin", "latex", "bee stings", "kiwi"]
BANDS = ["The Paper Kites", "Night Ferry", "Glasshouse Choir", "Low Tide Radio", "Honey Static", "The Borrowed Hours"]
THINGS = {"band": BANDS, "color": ["green", "teal", "mustard yellow", "plum", "rust orange"], "movie": ["The Long Thaw", "Paper Lanterns", "Salt Road", "Midnight Diner Blues"],
          "team": ["the Harbor Gulls", "the Copper Kings", "the River Otters", "the Night Owls"], "dessert": ["flan", "tiramisu", "peach cobbler", "mochi ice cream"]}
OBJECTS = ["passport", "spare key", "birth certificate", "bike lock", "toolbox", "camera", "tax folder", "sewing kit"]
SPOTS = ["the top desk drawer", "the hall closet", "the blue bowl by the door", "the garage shelf", "the filing cabinet", "the kitchen junk drawer",
         "the bedside table", "the trunk of the car", "the basement bin", "the bookshelf in the den"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
SEASONS = {"spring": (3, 5), "summer": (6, 8), "fall": (9, 11)}

# The small talk of a life: what fills the days around the facts. Nothing here states a lasting fact (no "lives in",
# "works as", "named", "birthday", "favorite", "allergic", "moved"), so it can't answer a question by accident.
SMALL_TALK = [
    "had {food} with {name} tonight", "{name} called about the {topic}", "work was {adj} today", "long day, the {topic} is wearing me out",
    "watched a show with {name} and fell asleep halfway", "{name} is coming over this weekend", "i need to pick up {item} tomorrow",
    "couldn't sleep, kept thinking about the {topic}", "went for a walk with {name} after dinner", "{name} and i argued about the {topic} again",
    "made {food} and it came out {adj}", "ran into {name} at the store", "the {topic} finally got sorted", "{name} sent me a funny video",
    "i'm behind on the {topic}", "took the car in, it's making that noise again", "{name} wants to plan something for next month",
    "cleaned the whole apartment today", "skipped the gym, too tired", "{name} is stressed about the {topic}", "got coffee with {name} this morning",
    "the weather was {adj} so i stayed in", "{name} helped me with the {topic}", "paid the bills and felt {adj} about it",
    "tried a new place for {food}, it was {adj}", "my back hurts from the {topic}", "{name} forgot about the {topic}, typical",
    "spent the evening on the {topic}", "{name} told me a long story about the {topic}", "bought {item} on the way home",
]
TOPICS = ["audit", "wedding plans", "lease", "school play", "tax stuff", "group project", "family reunion", "car repair", "garden", "budget",
          "holiday trip", "night shift", "soccer season", "kitchen remodel", "book club", "fundraiser", "new schedule", "neighbors", "inbox", "move"]
ADJ = ["rough", "fine", "great", "slow", "weird", "okay", "long", "easy", "awful", "good"]
ITEMS = ["batteries", "cat litter", "a birthday card", "light bulbs", "dish soap", "stamps", "a phone charger", "potting soil", "socks", "tape"]

# How each fact is worded when it's kept, and how each question is asked. `dev` is how Luma words things today; `heldout`
# is another natural way to say the same thing. Written before any of the memory code, and not changed to fit it.
WORDING = {
    "dev": {
        "name": "My {rel}'s name is {name}", "birthday": "My {rel}'s birthday is {month} {day}", "city": "{name} (their {rel}) lives in {city}",
        "job": "{name} (their {rel}) works as a {job}", "pet": "{name} (their {rel}) has a {species} named {pet}",
        "hobby": "{name} (their {rel}) just got into {hobby}", "hobby_new": "{name} (their {rel}) is into {hobby} now",
        "married": "{name} (their {rel}) is married to {other}", "other_job": "{other} works as a {job}",
        "home": "You live in {city}", "home_new": "You moved to {city}", "work": "You work at {company} as a {job}",
        "work_new": "You started a new job at {company}", "favorite": "Your favorite {thing} is {value}", "favorite_new": "Your favorite {thing} is {value} now",
        "allergy": "I'm allergic to {what}", "where": "Your {obj} is in {spot}", "trip": "You went to {place} with {name}",
        "said": "{line}",
    },
    "heldout": {
        "name": "{name} is my {rel}", "birthday": "{name}'s birthday is on {month} {day}", "city": "{name}, my {rel}, is living in {city}",
        "job": "{name} got a job as a {job}", "pet": "{name}'s {species} is called {pet}",
        "hobby": "{name} started doing {hobby}", "hobby_new": "{name} switched to {hobby} lately",
        "married": "{name} and {other} got married", "other_job": "{other} is a {job}",
        "home": "I'm living in {city}", "home_new": "I relocated to {city}", "work": "I've got a job at {company} as a {job}",
        "work_new": "I just switched jobs, I'm at {company} now", "favorite": "The {thing} I like best is {value}", "favorite_new": "These days the {thing} I like best is {value}",
        "allergy": "{what} gives me a bad reaction, I can't have it", "where": "I keep the {obj} in {spot}", "trip": "{name} and I took a trip to {place}",
        "said": "{line}",
    },
}
ASKING = {
    "dev": {
        "name": "what's my {rel}'s name", "birthday": "when is my {rel}'s birthday", "city": "where does {name} live", "job": "what does {name} work as",
        "pet": "what's the name of {name}'s {species}", "hobby": "what is {name} into", "home": "where do i live", "work": "where do i work",
        "favorite": "what's my favorite {thing}", "allergy": "what am i allergic to", "where": "where is my {obj}",
        "reword_job": "what does {name} do for a living", "reword_city": "which city is {name} based in", "reword_birthday": "what day was {name} born",
        "reword_pet": "what did {name} call the {species}", "reword_allergy": "which foods or medicines are dangerous for me",
        "hop": "what does my {rel}'s spouse do for work", "trip_month": "where did i travel in {month} {year}", "trip_season": "where did i go last {season}",
        "trip_year": "what trip did i take in {year}", "never_rel": "what's my {rel}'s name", "never_attr": "what's {name}'s middle name",
        "never_topic": "what's the combination for my storage locker",
    },
    "heldout": {
        "name": "who is my {rel}", "birthday": "what date is {name}'s birthday", "city": "what city is {name} in", "job": "what's {name}'s job",
        "pet": "what's {name}'s {species} called", "hobby": "what hobby does {name} have these days", "home": "what city am i living in", "work": "who do i work for",
        "favorite": "which {thing} do i like best", "allergy": "what gives me a bad reaction", "where": "where do i keep the {obj}",
        "reword_job": "how does {name} earn a paycheck", "reword_city": "where has {name} settled down", "reword_birthday": "when do we celebrate {name} turning a year older",
        "reword_pet": "what name did {name} give the {species}", "reword_allergy": "is there anything i have to avoid eating or taking",
        "hop": "what's the job of the person my {rel} married", "trip_month": "what place did i visit in {month} of {year}", "trip_season": "where was i traveling last {season}",
        "trip_year": "which trip happened in {year}", "never_rel": "who is my {rel}", "never_attr": "what's {name}'s shoe size",
        "never_topic": "what's the gate code for the storage unit",
    },
}


class Life:
    """One made-up life: `memories` (oldest first) and `questions` about them. The same seed gives the same people and facts
    at every size; only the small talk around them grows."""

    def __init__(self, seed, size, split="dev"):
        self.seed, self.size, self.split = seed, size, split
        self.words, self.asks = WORDING[split], ASKING[split]
        rng = random.Random(seed)
        self.years = 6
        self.start = NOW - timedelta(days=365 * self.years)
        self.memories, self.questions = [], []
        self._facts(rng)
        self._small_talk(random.Random(seed * 7919 + 1), size - len(self.memories))
        self.memories.sort(key=lambda m: m["created"])
        for i, m in enumerate(self.memories):
            m["id"] = f"m{i}"
        by_key = {m["key"]: m["id"] for m in self.memories if m.get("key")}
        for q in self.questions:
            q["gold"] = [by_key[k] for k in q.pop("gold_keys", [])]
            q["stale"] = [by_key[k] for k in q.pop("stale_keys", [])]

    # -- building blocks --------------------------------------------------------------------------------------------
    def _at(self, rng, lo=0.0, hi=1.0):
        """A moment between two points of the life (0 = six years ago, 1 = today)."""
        span = (NOW - self.start).total_seconds()
        return (self.start + timedelta(seconds=span * rng.uniform(lo, hi))).timestamp()

    def _keep(self, key, kind, created, source="noticed_in_conversation", **fields):
        text = self.words[kind].format(**fields)
        self.memories.append({"key": key, "text": text[0].upper() + text[1:], "source": source, "created": created})
        return key

    def _ask(self, kind, ask, gold=(), stale=(), **fields):
        self.questions.append({"kind": kind, "q": self.asks[ask].format(**fields), "gold_keys": list(gold), "stale_keys": list(stale)})

    def _facts(self, rng):
        names = rng.sample(NAMES, len(NAMES))
        take = iter(names)
        people = [{"rel": rel, "name": next(take)} for rel in RELATIONS]
        friends = [next(take) for _ in range(16)]
        self.people, self.friends = people, friends
        for p in people:
            rel, name = p["rel"], p["name"]
            k = self._keep(f"name:{rel}", "name", self._at(rng, 0, .15), rel=rel, name=name)
            self._ask("fact", "name", [k], rel=rel)
            month, day = rng.choice(MONTHS), rng.randint(1, 28)
            k = self._keep(f"bday:{rel}", "birthday", self._at(rng, 0, .3), rel=rel, name=name, month=month, day=day)
            self._ask("fact", "birthday", [k], rel=rel, name=name)
            self._ask("reword", "reword_birthday", [k], name=name)
            city = rng.choice(CITIES)
            k = self._keep(f"city:{rel}", "city", self._at(rng, 0, .4), rel=rel, name=name, city=city)
            self._ask("fact", "city", [k], name=name)
            self._ask("reword", "reword_city", [k], name=name)
            job = rng.choice(JOBS)
            k = self._keep(f"job:{rel}", "job", self._at(rng, 0, .4), rel=rel, name=name, job=job)
            self._ask("fact", "job", [k], name=name)
            self._ask("reword", "reword_job", [k], name=name)
            if rng.random() < .6:
                species, pet = rng.choice(SPECIES), rng.choice(PETS)
                k = self._keep(f"pet:{rel}", "pet", self._at(rng, 0, .5), rel=rel, name=name, species=species, pet=pet)
                self._ask("fact", "pet", [k], name=name, species=species)
                self._ask("reword", "reword_pet", [k], name=name, species=species)
            old, new = rng.sample(HOBBIES, 2)
            k_old = self._keep(f"hobby:{rel}:0", "hobby", self._at(rng, .1, .4), rel=rel, name=name, hobby=old)
            k_new = self._keep(f"hobby:{rel}:1", "hobby_new", self._at(rng, .6, .95), rel=rel, name=name, hobby=new)
            self._ask("update", "hobby", [k_new], [k_old], name=name)
            if rel in ("sister", "brother", "daughter", "son", "cousin", "best friend"):
                other = next(take)
                self._keep(f"married:{rel}", "married", self._at(rng, .1, .5), rel=rel, name=name, other=other)
                k = self._keep(f"otherjob:{rel}", "other_job", self._at(rng, .2, .7), other=other, job=rng.choice(JOBS))
                self._ask("hop", "hop", [k], rel=rel)
        # the owner: where they live and work changes over the years
        homes = rng.sample(CITIES, 3)
        keys = [self._keep("home:0", "home", self._at(rng, 0, .05), city=homes[0])]
        keys += [self._keep(f"home:{i}", "home_new", self._at(rng, .25 * i + .1, .25 * i + .3), city=homes[i]) for i in (1, 2)]
        self._ask("update", "home", [keys[-1]], keys[:-1])
        firms = rng.sample(COMPANIES, 3)
        keys = [self._keep("work:0", "work", self._at(rng, 0, .05), company=firms[0], job=rng.choice(JOBS))]
        keys += [self._keep(f"work:{i}", "work_new", self._at(rng, .25 * i + .15, .25 * i + .35), company=firms[i]) for i in (1, 2)]
        self._ask("update", "work", [keys[-1]], keys[:-1])
        for thing, values in THINGS.items():
            old, new = rng.sample(values, 2)
            k_old = self._keep(f"fav:{thing}:0", "favorite", self._at(rng, 0, .3), thing=thing, value=old)
            if rng.random() < .5:
                k_new = self._keep(f"fav:{thing}:1", "favorite_new", self._at(rng, .6, .95), thing=thing, value=new)
                self._ask("update", "favorite", [k_new], [k_old], thing=thing)
            else:
                self._ask("fact", "favorite", [k_old], thing=thing)
        k = self._keep("allergy", "allergy", self._at(rng, 0, .2), what=rng.choice(ALLERGENS))
        self._ask("fact", "allergy", [k])
        self._ask("reword", "reword_allergy", [k])
        for obj in OBJECTS:
            old, new = rng.sample(SPOTS, 2)
            k_old = self._keep(f"where:{obj}:0", "where", self._at(rng, 0, .4), obj=obj, spot=old)
            if rng.random() < .5:
                k_new = self._keep(f"where:{obj}:1", "where", self._at(rng, .6, .98), obj=obj, spot=new)
                self._ask("update", "where", [k_new], [k_old], obj=obj)
            else:
                self._ask("fact", "where", [k_old], obj=obj)
        # trips: one a year in its own month, so "in May 2024" and "last spring" each have one right answer
        places = rng.sample(TRIPS, self.years + 1)
        for i, year in enumerate(range(NOW.year - self.years + 1, NOW.year + 1)):
            month = rng.randint(3, 10) if year < NOW.year else rng.randint(3, 8)
            when = datetime(year, month, rng.randint(2, 26), 18, tzinfo=timezone.utc)
            k = self._keep(f"trip:{year}", "trip", when.timestamp(), source="said", place=places[i], name=rng.choice(friends))
            self._ask("time", "trip_month", [k], month=MONTHS[month - 1], year=year)
            self._ask("time", "trip_year", [k], year=year)
            if year == NOW.year:  # said in November, "last spring" is this year's
                season = next((s for s, (a, b) in SEASONS.items() if a <= month <= b), None)
                if season:
                    self._ask("time", "trip_season", [k], season=season)
        # things they never said
        for rel in MISSING[:5]:
            self._ask("never", "never_rel", rel=rel)
        for p in people[:5]:
            self._ask("never", "never_attr", name=p["name"])
        self._ask("never", "never_topic")

    def _small_talk(self, rng, count):
        names = [p["name"] for p in self.people] + self.friends
        rels = {p["name"]: p["rel"] for p in self.people}
        for _ in range(max(0, count)):
            name = rng.choice(names)
            who = f"my {rels[name]} {name}" if name in rels and rng.random() < .3 else name
            line = rng.choice(SMALL_TALK).format(name=who, food=rng.choice(FOODS), topic=rng.choice(TOPICS), adj=rng.choice(ADJ), item=rng.choice(ITEMS))
            self.memories.append({"text": line[0].upper() + line[1:], "source": "said", "created": self._at(rng)})


# ---------------------------------------------------------------------------------------------------- asking the memory ---
def fill(store, life, batch=20000):
    """Every memory of the life into the store, encrypted, in one go."""
    rows = [{k: m[k] for k in ("id", "text", "source", "created")} for m in life.memories]
    if hasattr(store, "put_many"):
        for i in range(0, len(rows), batch):
            store.put_many("memory", rows[i:i + batch])
        return
    for i in range(0, len(rows), batch):  # the store before put_many: the same rows, one transaction a batch
        with store.lock, store.db:
            for row in rows[i:i + batch]:
                blob = store.cipher.encrypt(json.dumps(row, ensure_ascii=False).encode())
                store.db.execute("INSERT INTO records VALUES(?,?,?,?,?)", ("memory", row["id"], row["created"], row["created"], blob))


def look_up(store, question, limit=5):
    """(the memories found, whether Luma says it was never told, whether it flags a word of the question no memory has).
    The newer search says so itself; the older recall is taken to have an answer whenever it returns anything."""
    if hasattr(store, "search"):
        found = store.search(question, limit=limit, now=NOW.timestamp())
        return found["memories"], not found["known"], bool(found.get("unseen"))
    found = store.recall(question, limit)
    return found, not found, False


def score(life, store, limit=5, queries=None, show=False):
    """Ask every question (or `queries` of them, spread over the kinds) and count."""
    questions = life.questions
    if queries and queries < len(questions):
        questions = random.Random(5).sample(questions, queries)
    by_kind, times, misses = {}, [], []
    told = {"asked": 0, "said_never": 0, "flagged": 0}
    for q in questions:
        began = time.perf_counter()
        found, never, flagged = look_up(store, q["q"], limit)
        times.append((time.perf_counter() - began) * 1000)
        ids = [m.get("id") for m in found]
        row = by_kind.setdefault(q["kind"], {"asked": 0, "right": 0})
        row["asked"] += 1
        if q["kind"] == "never":
            ok = never
        elif q["kind"] == "update":  # the newest fact, ahead of every older one
            ok = not never and q["gold"][0] in ids and all(s not in ids or ids.index(s) > ids.index(q["gold"][0]) for s in q["stale"])
        else:
            ok = not never and any(g in ids for g in q["gold"])
        row["right"] += bool(ok)
        if q["kind"] == "never":      # says so itself, or hands the brain what it has with the word it never saw
            row["flagged"] = row.get("flagged", 0) + bool(never or flagged)
        else:                         # it was told: saying "never told", or flagging a word, would be wrong
            told["asked"] += 1
            told["said_never"] += bool(never)
            told["flagged"] += bool(flagged and not never)
        if not ok and show:
            misses.append({"kind": q["kind"], "q": q["q"], "found": [m.get("text", "")[:70] for m in found[:3]], "never": never})
    times.sort()
    answerable = [q for q in questions if q["kind"] != "never"]
    return {"by_kind": {k: {**v, "percent": round(100 * v["right"] / v["asked"], 1)} for k, v in sorted(by_kind.items())},
            "asked": len(questions), "answerable": len(answerable), "told": told,
            "ms": {"p50": round(times[len(times) // 2], 2), "p95": round(times[min(len(times) - 1, int(len(times) * .95))], 2), "max": round(times[-1], 2)},
            "misses": misses[:25]}


def forget_check(life, store, count=10):
    """Forget some facts, then look for any trace: in recall, and in every record the store can still read."""
    rng = random.Random(life.seed)
    facts = [m for m in life.memories if m.get("key") and m["source"] != "said"]
    picked = rng.sample(facts, min(count, len(facts)))
    for m in picked:
        store.delete("memory", m["id"])
    clean = 0
    for m in picked:
        found = store.recall(m["text"], 10)
        left = any(r.get("id") == m["id"] or r.get("text") == m["text"] for r in found)
        with store.lock:
            kinds = [k for (k,) in store.db.execute("SELECT DISTINCT kind FROM records").fetchall() if k != "memory"]
        for kind in kinds:  # what was built from it: its meaning, summaries, the life file, the people it knows
            for row in store.all(kind, 100000):
                blob = json.dumps(row, ensure_ascii=False, default=str)
                if m["id"] in blob or m["text"] in blob:
                    left = True
        clean += not left
    return {"forgotten": len(picked), "no_trace": clean, "percent": round(100 * clean / max(1, len(picked)), 1)}


def run_one(seed, size, split, queries=None, show=False, forget=True):
    from luma.memory.store import Store
    life = Life(seed, size, split)
    with tempfile.TemporaryDirectory() as temp:
        store = Store(Path(temp) / "s.db", Path(temp) / "k")
        began = time.perf_counter()
        fill(store, life)
        filled = time.perf_counter() - began
        began = time.perf_counter()
        store.recall("warm up", 5)  # the first look reads everything once
        first = time.perf_counter() - began
        out = score(life, store, queries=queries, show=show)
        if forget:
            out["forget"] = forget_check(life, store)
        store.close()
    out.update(seed=seed, size=len(life.memories), split=split, fill_s=round(filled, 1), first_look_s=round(first, 2),
               peak_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024))
    return out


def run(args):
    sizes = [int(s) for s in args.sizes.split(",")]
    seeds = SEEDS[args.split][:args.lives]
    report = {"kind": "memory_eval", "split": args.split, "runs": []}
    for size in sizes:
        for seed in seeds:
            one = run_one(seed, size, args.split, queries=args.queries, show=args.split == "dev" and args.show)
            report["runs"].append(one)
            kinds = "  ".join(f"{k} {v['right']}/{v['asked']}" for k, v in one["by_kind"].items())
            print(f"{args.split} seed {seed} size {one['size']:>8,}: {kinds} | p50 {one['ms']['p50']} ms p95 {one['ms']['p95']} ms | "
                  f"first look {one['first_look_s']} s | forget {one.get('forget', {}).get('percent', '-')}%", flush=True)
            for miss in one.pop("misses", []):
                print("   missed", miss["kind"], "|", miss["q"], "->", miss["found"], "(said never told)" if miss["never"] else "")
    if args.save:
        Path(args.save).parent.mkdir(parents=True, exist_ok=True)
        Path(args.save).write_text(json.dumps(report, indent=1))
    return report


def table(reports):
    """One row a split and size: each kind's percent over that split's lives, and the slowest life's times."""
    rows = {}
    for report in reports:
        for one in report["runs"]:
            row = rows.setdefault((one["split"], one["size"]), {"kinds": {}, "p50": [], "p95": [], "first": [], "forget": [], "mb": [],
                                                                 "told": [0, 0, 0], "never_flagged": 0})
            told = one.get("told") or {}
            row["told"] = [row["told"][0] + told.get("asked", 0), row["told"][1] + told.get("said_never", 0), row["told"][2] + told.get("flagged", 0)]
            row["never_flagged"] += one["by_kind"].get("never", {}).get("flagged", 0)
            for kind, v in one["by_kind"].items():
                got = row["kinds"].setdefault(kind, [0, 0])
                got[0] += v["right"]
                got[1] += v["asked"]
            row["p50"].append(one["ms"]["p50"])
            row["p95"].append(one["ms"]["p95"])
            row["first"].append(one["first_look_s"])
            row["mb"].append(one.get("peak_mb", 0))
            if "forget" in one:
                row["forget"].append(one["forget"]["percent"])
    kinds = ["fact", "reword", "hop", "time", "update", "never"]
    lines = ["| Split | Memories | " + " | ".join(kinds) + " | Forget | Lookup p50 | p95 | First look | Peak memory |", "|---|---|" + "---|" * (len(kinds) + 5)]
    for (split, size), row in sorted(rows.items()):
        cells = [f"{100 * row['kinds'][k][0] / row['kinds'][k][1]:.0f}% ({row['kinds'][k][0]}/{row['kinds'][k][1]})" if k in row["kinds"] else "-" for k in kinds]
        forget = f"{min(row['forget']):.0f}%" if row["forget"] else "-"
        lines.append(f"| {split} | {size:,} | " + " | ".join(cells) + f" | {forget} | {max(row['p50'])} ms | {max(row['p95'])} ms | {max(row['first'])} s | {max(row['mb'])} MB |")
    if any(row["told"][0] for row in rows.values()):
        share = lambda a, b: f"{100 * a / b:.1f}% ({a}/{b})" if b else "-"  # noqa: E731
        lines += ["", "| Split | Memories | Never told: says so itself | or tells the brain which word it never saw | Told, but said \"never told\" | Told, and flagged a word |",
                  "|---|---|---|---|---|---|"]
        for (split, size), row in sorted(rows.items()):
            never = row["kinds"].get("never", [0, 0])
            lines.append(f"| {split} | {size:,} | {share(never[0], never[1])} | {share(row['never_flagged'], never[1])} | "
                         f"{share(row['told'][1], row['told'][0])} | {share(row['told'][2], row['told'][0])} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--sizes", default="1000,10000")
    r.add_argument("--split", choices=sorted(SEEDS), default="dev")
    r.add_argument("--lives", type=int, default=3, help="how many made-up lives of each size")
    r.add_argument("--queries", type=int, default=None, help="ask only this many questions (for the biggest sizes)")
    r.add_argument("--show", action="store_true", help="print what was missed (dev only; held-out misses are never shown)")
    r.add_argument("--save")
    s = sub.add_parser("summary")
    s.add_argument("reports", nargs="+")
    args = parser.parse_args()
    if args.command == "run":
        report = run(args)
        print()
        print(table([report]))
    else:
        print(table([json.loads(Path(p).read_text()) for p in args.reports]))


if __name__ == "__main__":
    main()
