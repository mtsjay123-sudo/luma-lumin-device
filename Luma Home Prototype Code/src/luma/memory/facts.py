"""What a memory says, read as a fact: who it's about, what about them, and the value.

"You moved to Denver" and "You live in Austin" are the same fact about the same person (where they live), said at
different times. Reading them that way lets the newer one take the older one's place (the older one is kept, as what
used to be true), lets "where does my sister live" find "Dana (their sister) lives in Austin" through who the sister is,
and lets Luma say "you haven't told me that" when it knows the person but not the thing asked.

No model: plain patterns over the ways Luma words what it keeps (luma.agent.presence, luma.agent.people) and the plain
first-person ways people say the same things. A sentence it can't read is still a memory, found by its words and its
meaning like before."""
from __future__ import annotations

import re

from luma.agent.people import NOT_NAMES, RELATIONS

SPECIES = r"dog|cat|puppy|kitten|parrot|bird|rabbit|bunny|hamster|turtle|fish|horse|lizard|snake|guinea pig|ferret"
NAME = r"[A-Z][a-zA-Z'’-]{1,20}"
POSS = r"(?:'s|’s)"

# One kind of fact about one person or thing has one value at a time; these can have many at once.
MANY = {"allergy", "likes", "goal", "is"}

PEOPLE_FACT = re.compile(rf"^(?P<name>{NAME}) \((?:their|your|my) (?P<rel>{RELATIONS})\) (?P<rest>.+)$")
REL_NAME = re.compile(rf"^(?:my|your) (?:(?:little|big|older|younger|baby|twin|best)\s+)?(?P<rel>{RELATIONS}){POSS} name is (?P<name>{NAME})\b", re.I)
PET_NAME = re.compile(rf"^(?:my|your) (?P<species>{SPECIES}){POSS} name is (?P<name>{NAME})\b", re.I)
REL_REST = re.compile(rf"^(?:my|your) (?:(?:little|big|older|younger|baby|twin|best)\s+)?(?P<rel>{RELATIONS}){POSS} (?P<rest>birthday is .+)$", re.I)
REL_IS = re.compile(rf"^(?:my|your) (?:(?:little|big|older|younger|baby|twin|best)\s+)?(?P<rel>{RELATIONS}) (?P<rest>(?:lives?|works?|is|has|just|got|moved|started) .+)$", re.I)
NAME_POSS = re.compile(rf"^(?P<name>{NAME}){POSS} (?P<rest>birthday is .+)$")
NAME_REST = re.compile(rf"^(?P<name>{NAME}) (?P<rest>(?:lives? in|works? (?:as|at|for)|is married to|married|has an? |just got into|got into|is (?:really |so |super )?into|"
                       rf"is obsessed with|moved to|started (?:a )?new job) .+)$")
OWNER = re.compile(r"^(?:you(?:'re|’re| are)?|i(?:'m|’m| am)?|we(?:'re|’re| are)?)\s+(?P<rest>.+)$", re.I)
OWNER_NAME = re.compile(rf"^(?:my|your) name is (?P<value>{NAME})\b", re.I)
OWNER_BIRTHDAY = re.compile(r"^(?:my|your) birthday is (?:on )?(?P<value>.+)$", re.I)
FAVORITE = re.compile(r"^(?:my|your) (?:all[- ]time )?favou?rite (?P<thing>[a-z][a-z ]{1,30}?) (?:is|are|was) (?P<value>.+?)(?:\s+(?:now|these days|lately))?$", re.I)
WHERE = re.compile(r"^(?:my|your|the|our) (?P<obj>[a-z][a-z' -]{1,40}?) (?:is|are|was|were) (?:kept |sitting |parked |stored |hidden |now )?"
                   r"(?P<spot>(?:in|on|at|by|under|inside|next to|behind|near|with|above|beside)\b.+)$", re.I)
GOAL = re.compile(r"^(?:your|my) goal(?: is|:)\s*(?P<value>.+)$", re.I)

# what's said about someone, after their name: (what kind of fact, the pattern)
REST = [
    ("home", re.compile(r"^(?:still |now |just |recently )?(?:lives?|living) in (?P<value>.+)$", re.I)),
    ("home", re.compile(r"^(?:just |recently |finally )?moved (?:back )?to (?P<value>.+?)(?:\s+(?:last|this|a few|in)\b.*)?$", re.I)),
    ("work", re.compile(r"^(?:still |now )?works? (?:as|at|for) (?P<value>.+)$", re.I)),
    ("work", re.compile(r"^(?:just |recently )?(?:started|got|took) (?:a |an )?new job (?:at|with|as) (?P<value>.+)$", re.I)),
    ("pet", re.compile(rf"^has an? (?P<species>{SPECIES}) (?:named|called) (?P<value>{NAME})\b", re.I)),
    ("spouse", re.compile(rf"^(?:is|got) married to (?P<value>{NAME})\b", re.I)),
    ("spouse", re.compile(rf"^married (?P<value>{NAME})\b", re.I)),
    ("into", re.compile(r"^(?:just |recently |really |finally )?got into (?P<value>.+)$", re.I)),
    ("into", re.compile(r"^is (?:really |so |super |totally )?(?:into|obsessed with) (?P<value>.+?)(?:\s+(?:now|lately|these days|right now))?$", re.I)),
    ("birthday", re.compile(r"^birthday is (?:on )?(?P<value>.+)$", re.I)),
    ("allergy", re.compile(r"^(?:is |are |am )?allergic to (?P<value>.+)$", re.I)),
    ("diet", re.compile(r"^(?:is |are |am )?(?:a |an )?(?P<value>vegetarian|vegan|pescatarian|gluten[- ]free|lactose intolerant|diabetic)\b", re.I)),
    ("likes", re.compile(r"^(?:really |still )?(?:love|loves|like|likes|hate|hates) (?P<value>.+)$", re.I)),
    ("is", re.compile(r"^is an? (?P<value>[a-z][a-z -]{2,40})$", re.I)),
]

# -- what a question is asking for ----------------------------------------------------------------------------------
REL_IN_QUESTION = re.compile(rf"\b(?:my|our) (?:(?:little|big|older|younger|baby|twin|best)\s+)?(?P<rel>{RELATIONS})\b(?P<poss>{POSS})?", re.I)
HOP = re.compile(r"(?:'s|’s)\s+(?P<hop>spouse|husband|wife|partner)\b", re.I)
ASKS = [
    ("spouse", re.compile(r"\bmarried to\b|\bwho (?:is|did) .{1,40} (?:married|marry)\b", re.I)),
    ("birthday", re.compile(r"\bbirthday\b|\bb-?day\b|\bborn\b", re.I)),
    ("favorite", re.compile(r"\bfavou?rite\s+(?P<thing>[a-z][a-z ]{1,30}?)(?=\s+(?:these days|now|lately|again|is|are)\b|[?.!]|$)|"
                            r"\bwhich (?P<thing2>[a-z]+) do i (?:like|love) (?:best|most|the most)\b", re.I)),
    ("allergy", re.compile(r"\ballerg(?:y|ic|ies)\b|\bcan(?:'t|not) (?:eat|have)\b", re.I)),
    ("work", re.compile(r"\bworks? (?:as|at|for)\b|\bwhere (?:do|does|did) .{1,30}\bwork\b|\bjobs?\b|\bfor a living\b|\bfor work\b|\bprofession\b|\bcareer\b|"
                        r"\bemployer\b|\bwhat (?:do|does) .{1,30}\bdo\b\s*(?:[?.!]|$)", re.I)),
    ("home", re.compile(r"\b(?:do|does|did) .{1,30}\blive\b|\blives?\b|\bliving in\b|\b(?:what|which) (?:city|town)\b|\bbased\b|\bmoved? to\b|\bhome ?town\b", re.I)),
    ("pet", re.compile(rf"\b(?P<species>{SPECIES}|pet)\b.*\b(?:name|named|call|called)\b|\b(?:name|named|call|called)\b.*\b(?P<species2>{SPECIES}|pet)\b", re.I)),
    ("into", re.compile(r"\binto\b|\bhobb(?:y|ies)\b|\binterested in\b", re.I)),
    ("name", re.compile(r"\bname\b|\bcalled\b|^\W*who(?:'s|’s| is) my\b", re.I)),
]
WHERE_ASK = re.compile(r"\bwhere(?:'s|’s| is| are| was| were| did i (?:put|leave|park|keep|set|stash|hide)| do i keep| have i put)\s+(?:my|the|our)\s+"
                       r"(?P<obj>[a-z][a-z' -]{1,40}?)(?:\s+(?:at|kept|stored|again|now|these days|right now))*\s*(?:[?.!]|$)", re.I)

# -- how much a line of talk matters when nothing else tells two memories apart ------------------------------------
TRAVEL = re.compile(r"\b(?:went to|flew to|trip to|a trip|travel(?:ed|led|ing)? to|visited|vacation|road ?trip|drove (?:up|down|out) to|honeymoon|cruise)\b", re.I)
MILESTONE = re.compile(r"\b(?:got (?:married|engaged|promoted|divorced|fired|laid off|hired|accepted|into)|graduat\w+|was born|passed away|died|funeral|"
                       r"surgery|diagnos\w+|pregnan\w+|retire[sd]?|bought (?:a|the|our) (?:house|car|home)|closed on|quit my job|new job|moved (?:to|in|out)|"
                       r"broke up|anniversary|first day)\b", re.I)
TRAVEL_ASK = re.compile(r"\b(?:travel\w*|trips?|vacation|visit(?:ed)?|went|go|flew|fly)\b", re.I)
PRIVATE = re.compile(r"\b(?:diagnos\w+|medication|meds|therap(?:y|ist)|psychiatrist|rehab|sober|relapse\w*|pregnan\w+|miscarr\w+|std|hiv|cancer|surgery|"
                     r"depress\w+|anxiety|panic attack|salary|paycheck|debt|loan|owe[sd]?|rent is|bank|credit (?:card|score)|bankrupt\w*|laid off|fired|"
                     r"divorce\w*|affair|cheat(?:ed|ing)|broke up|breakup|custody|lawyer|arrest\w*|probation|immigration|visa status)\b", re.I)


class Reading:
    """What one memory says. links: (name, relation) pairs; slots: (who, what, value) triples."""
    __slots__ = ("links", "slots")

    def __init__(self):
        self.links, self.slots = [], []


def _clean(value):
    return " ".join(str(value or "").strip(" .,!?;:").split()).lower()


def _name_ok(name):
    return bool(name) and name.lower().replace("’", "'") not in NOT_NAMES and not name.isupper()


def _rel(text):
    return " ".join(text.lower().split())


def _rest(reading, who, rest):
    for kind, pattern in REST:
        found = pattern.match(rest.strip())
        if not found:
            continue
        value = _clean(found["value"])
        if not value:
            continue
        if kind == "pet":
            reading.slots.append((who, "pet:" + _clean(found["species"]), value))
        elif kind == "work":
            # "works at Brightside Dental as a hygienist": the place is the fact that changes with a new job
            reading.slots.append((who, "work", re.sub(r"\s+as an? .+$", "", value)))
        else:
            reading.slots.append((who, kind, value))
        return True
    return False


def read(text):
    """A Reading of one memory, or None when it isn't worded as a fact Luma can read."""
    text = " ".join(str(text or "").replace("’", "'").split()).strip(" .!")
    if not text or len(text) > 240:
        return None
    reading = Reading()
    found = PEOPLE_FACT.match(text)
    if found and _name_ok(found["name"]):
        name, rel = found["name"].lower(), _rel(found["rel"])
        reading.links.append((name, rel))
        _rest(reading, "name:" + name, found["rest"])
        return reading
    found = REL_NAME.match(text)
    if found and _name_ok(found["name"]):
        reading.links.append((found["name"].lower(), _rel(found["rel"])))
        reading.slots.append(("rel:" + _rel(found["rel"]), "name", found["name"].lower()))
        return reading
    found = PET_NAME.match(text)
    if found:
        reading.slots.append(("you", "pet:" + _clean(found["species"]), found["name"].lower()))
        return reading
    found = REL_REST.match(text) or REL_IS.match(text)
    if found and _rest(reading, "rel:" + _rel(found["rel"]), found["rest"]):
        return reading
    found = NAME_POSS.match(text) or NAME_REST.match(text)
    if found and _name_ok(found["name"]) and _rest(reading, "name:" + found["name"].lower(), found["rest"]):
        return reading
    for pattern, kind in ((OWNER_NAME, "name"), (OWNER_BIRTHDAY, "birthday")):
        found = pattern.match(text)
        if found:
            reading.slots.append(("you", kind, _clean(found["value"])))
            return reading
    found = FAVORITE.match(text)
    if found:
        reading.slots.append(("you", "favorite:" + _clean(found["thing"]), _clean(found["value"])))
        return reading
    found = GOAL.match(text)
    if found:
        reading.slots.append(("you", "goal", _clean(found["value"])))
        return reading
    found = OWNER.match(text)
    if found and _rest(reading, "you", found["rest"]):
        return reading
    found = WHERE.match(text)
    if found and len(found["obj"].split()) <= 4:
        reading.slots.append(("you", "where:" + _clean(found["obj"]), _clean(found["spot"])))
        return reading
    return None


def asked(question):
    """What a question wants to know: {"what": the kind of fact or None, "rels": relations it names ("my sister") and
    "rel_at" where each one is, "hop": "spouse" for "my sister's husband", "at": where the words that ask for the fact end
    (so "my coworker asked where I live" is about me, and "where does my uncle live, I forgot" about the uncle)}."""
    q = " ".join(str(question or "").replace("’", "'").split())
    out = {"what": None, "rels": [], "hop": None, "at": None, "rel_at": []}
    for found in REL_IN_QUESTION.finditer(q):
        out["rels"].append(_rel(found["rel"]))
        out["rel_at"].append(found.start())
    hop = HOP.search(q)
    if hop:
        out["hop"] = "spouse"
    where = WHERE_ASK.search(q)
    for kind, pattern in ASKS:
        found = pattern.search(q)
        if not found:
            continue
        if kind == "favorite":
            out["what"] = "favorite:" + _clean(found["thing"] or found["thing2"])
        elif kind == "pet":
            species = _clean(found["species"] or found["species2"])
            out["what"] = "pet" if species == "pet" else "pet:" + species
        elif kind == "name" and where:
            continue
        else:
            out["what"] = kind
        out["at"] = found.end()
        break
    if out["what"] is None and where:
        out["what"], out["at"] = "where:" + _clean(where["obj"]), where.end()
    return out


def weight(text, source=""):
    """0 small talk, 1 something that happened, 2 a big moment, 3 a fact Luma was told or noticed."""
    if source not in ("said", "log", "episode"):
        return 3
    t = str(text or "")
    if MILESTONE.search(t):
        return 2
    if TRAVEL.search(t):
        return 1
    return 0


def is_trip(text):
    return bool(TRAVEL.search(str(text or "")))


def asks_about_travel(question):
    return bool(TRAVEL_ASK.search(str(question or "")))


def private(text, category=""):
    """Health, money and the hard parts of relationships: not for when there's company in the room."""
    return category == "health" or bool(PRIVATE.search(str(text or "")))
