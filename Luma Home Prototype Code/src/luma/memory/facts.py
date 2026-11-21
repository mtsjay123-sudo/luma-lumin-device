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
REL_IS = re.compile(rf"^(?:my|your) (?:(?:little|big|older|younger|baby|twin|best)\s+)?(?P<rel>{RELATIONS}) (?P<rest>(?:lives?|works?|is|isn't|has|just|got|moved|started|can't|cannot|can not|grew|was|"
                    rf"relocated|transferred|left|ended|settled|landed|wound|took|accepted|packed|bought|found|rented|went|no longer|now|recently|finally|currently|still) .+)$", re.I)
# "my brother's in Denver now", "my sister's back in Ohio": the 's is "is" here, not "my brother's birthday"
REL_S_IN = re.compile(rf"^((?:my|your) (?:(?:little|big|older|younger|baby|twin|best)\s+)?(?:{RELATIONS}))'s (?=(?:back |now |still |living |currently )*in\b)", re.I)
NAME_POSS = re.compile(rf"^(?P<name>{NAME}){POSS} (?P<rest>birthday is .+)$")
NAME_REST = re.compile(rf"^(?P<name>{NAME}) (?P<rest>(?:(?:just|recently|finally|actually|now|still|also|has|officially) )*(?:lives? in|works? (?:as|at|for)|is married to|married|has an? |just got into|got into|is (?:really |so |super )?into|"
                       rf"is obsessed with|moved (?:back |out |over )?to|(?:got |was |has been )?(?:relocated|transferred) to|is (?:now |still |currently )?living in|is (?:now |back |out |over |up |down )*in|"
                       rf"ended up in|settled (?:down )?in|left|(?:just |recently |finally )?(?:got|bought|found|rented) (?:a|an|his|her|their)|started (?:a )?new job) .+)$")
OWNER = re.compile(r"^(?:you(?:'re|’re| are|'ve|’ve)?|i(?:'m|’m| am|'ve|’ve)?|we(?:'re|’re| are|'ve|’ve)?)\s+(?P<rest>.+)$", re.I)
OWNER_NAME = re.compile(rf"^(?:my|your) name is (?P<value>{NAME})\b", re.I)
OWNER_BIRTHDAY = re.compile(r"^(?:my|your) birthday is (?:on )?(?P<value>.+)$", re.I)
FAVORITE = re.compile(r"^(?:my|your) (?:all[- ]time )?favou?rite (?P<thing>[a-z][a-z ]{1,30}?) (?:is|are|was) (?P<value>.+?)(?:\s+(?:now|these days|lately))?$", re.I)
WHERE = re.compile(r"^(?:my|your|the|our) (?P<obj>[a-z][a-z' -]{1,40}?) (?:is|are|was|were) (?:kept |sitting |parked |stored |hidden |now )?"
                   r"(?P<spot>(?:in|on|at|by|under|inside|next to|behind|near|with|above|beside)\b.+)$", re.I)
GOAL = re.compile(r"^(?:your|my) goal(?: is|:)\s*(?P<value>.+)$", re.I)

# How a piece of news about someone starts. It was for then: it isn't part of the fact, and it isn't said back.
LEAD_IN = re.compile(r"^(?:(?:fyi|btw|by the way|heads up|oh and|oh yeah|oh|so|well|anyway|also|just so you know|quick update|update|as it turns out|turns out|"
                     r"apparently|guess what|big news|good news|bad news|you know what|funny thing|it(?:'s|’s| is) official|for the record|fun fact|news flash|small update|"
                     r"life update|ok so|okay so|so yeah|long story short|did i (?:ever )?(?:tell|mention to) you(?: that)?|"
                     r"i (?:just )?found out(?: that)?|i (?:just )?heard(?: that)?|i think i told you(?: that)?)\b[\s,:;.!-]*)+", re.I)
# "talked to my brother today. he moved to Denver", "update on my brother: he's in Denver now": the "he" is the brother.
THEN_THEY = re.compile(rf"\b(?:my|your) (?:(?:little|big|older|younger|baby|twin|best)\s+)?(?P<rel>{RELATIONS})\b[^.:;?!]*[.:;?!,]+\s*(?:(?:oh|well|so|and|but|yeah)\s+)*"
                       rf"(?:he|she|they)(?P<be>'s|'re| is| are)?\s+(?P<rest>[^.?!]+)$", re.I)

# what can follow a place without being part of it: "moved to Denver last week", "moved to Denver for work"
_AFTER = r"(?:\s*,?\s+(?:last|this|a few|in|for|now|these days|and|after|since|recently|permanently|again|back in|with|to be)\b.*)?"

# what's said about someone, after their name: (what kind of fact, the pattern)
REST = [
    ("home", re.compile(r"^(?:is |are |am )?(?:still |now |just |recently |currently )?(?:lives?|living) in (?P<value>.+?)(?:\s+(?:now|these days|again|for now))?$", re.I)),
    ("home", re.compile(rf"^(?:just |recently |finally |has |have |got |was |has been |is being |is getting )*(?:moved|relocated|transferred) (?:back |out |over )?to (?P<value>.+?){_AFTER}$", re.I)),
    # The many other ways of saying someone lives somewhere new (month test, Nov 20: 2 of 13 were read). Where the words could
    # mean something else ("left work for lunch", "is in a mood now"), the place has to be said like a place: with a capital.
    ("home", re.compile(r"^(?:is |are |am )?(?:now |currently )?(?:back |out |over |up |down )*in (?P<place>.+?) (?:now|again|these days|for good|permanently)$", re.I)),
    ("home", re.compile(r"^(?:is |are |am )back (?:out |over |up |down )?in (?P<place>.+?)$", re.I)),
    ("home", re.compile(rf"^(?:just |recently |finally )?(?:got|bought|found|rented) (?:a|an|his|her|their|my|our) (?:own |new )*(?:place|apartment|house|condo|flat|home) in "
                        rf"(?P<place>.+?){_AFTER}$", re.I)),
    ("home", re.compile(rf"^(?:just |recently |finally )?left [A-Za-z .'-]{{2,30}}? for (?P<place>.+?){_AFTER}$", re.I)),
    ("home", re.compile(rf"^(?:ended up|settled(?: down)?|landed|wound up) in (?P<place>.+?){_AFTER}$", re.I)),
    ("home", re.compile(r"^(?:took|got|accepted|started) (?:a|the|that|his|her|their) (?:new )?job in (?P<place>.+?) and (?:moved|relocated)\b.*$", re.I)),
    ("home", re.compile(r"^(?:packed up and )?(?:went|moved|headed|gone) to (?P<place>.+?) for good$", re.I)),
    ("home", re.compile(r"^(?:isn't|is not|no longer|is no longer) in [A-Za-z .'-]{2,30}? any ?more,? (?:and |but )?(?:he|she|they)(?:'s|'re| is| are) (?:now )?in (?P<place>.+?)(?:\s+now)?$", re.I)),
    # Where someone is from ("I grew up in Ohio", "my dad is from Osaka originally"): a place said like a place, and never
    # where they live now.
    ("from", re.compile(r"^(?:is |are |am |was |were )?(?:originally |actually )?from (?!(?:hr|it|marketing|sales|accounting|legal|finance|gen|team|earth|mars|venus|hell|heaven|luma)\b)(?P<place>[^,;:]+?)(?:,? originally)?$", re.I)),
    ("from", re.compile(r"^(?:grew up|(?:was |were )?raised|(?:was |were )?brought up|(?:was |were )?born(?: and raised)?) in "
                        r"(?!(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b)(?P<place>[^,;:]+?)$", re.I)),
    ("work", re.compile(r"^(?:still |now )?works? (?:as|at|for) (?P<value>.+)$", re.I)),
    ("work", re.compile(r"^(?:worked|been working) (?:as|at|for) (?!(?:it|this|that|these|those|them|things|stuff|home|nights?|all|hours|days|weeks|months|years)\b)(?P<value>.+?)\s+(?:since\b.+|for (?:(?:\w+ ){0,3}(?:years?|months?|weeks?|decades?)|ages|a (?:long )?(?:while|time))\b.*)$", re.I)),   # "I've worked at the post office since 2019"
    ("work", re.compile(r"^(?:just |recently )?(?:started|got|took) (?:a |an )?new job (?:at|with|as) (?P<value>.+)$", re.I)),
    ("pet", re.compile(rf"^ha(?:s|ve) an? (?P<species>{SPECIES}) (?:named|called) (?P<value>{NAME})\b", re.I)),
    ("spouse", re.compile(rf"^(?:is|got) married to (?P<value>{NAME})\b", re.I)),
    ("spouse", re.compile(rf"^married (?P<value>{NAME})\b", re.I)),
    ("into", re.compile(r"^(?:just |recently |really |finally )?got into (?P<value>.+)$", re.I)),
    ("into", re.compile(r"^is (?:really |so |super |totally )?(?:into|obsessed with) (?P<value>.+?)(?:\s+(?:now|lately|these days|right now))?$", re.I)),
    ("birthday", re.compile(r"^birthday is (?:on )?(?P<value>.+)$", re.I)),
    ("allergy", re.compile(r"^(?:is |are |am )?allergic to (?P<value>.+)$", re.I)),
    ("allergy", re.compile(r"^can(?:'t|not| not) (?:eat|have) (?P<value>[a-z][a-z ]{2,30})$", re.I)),   # "my sister can't eat peanuts": what to keep off the table
    ("diet", re.compile(r"^(?:is |are |am )?(?:a |an )?(?P<value>vegetarian|vegan|pescatarian|gluten[- ]free|lactose intolerant|diabetic)\b", re.I)),
    ("likes", re.compile(r"^(?:really |still )?(?:love|loves|like|likes|hate|hates) (?P<value>.+)$", re.I)),
    ("is", re.compile(r"^is an? (?P<value>[a-z][a-z -]{2,40})$", re.I)),
]

# -- what a question is asking for ----------------------------------------------------------------------------------
REL_IN_QUESTION = re.compile(rf"\b(?:my|our) (?:(?:little|big|older|younger|baby|twin|best)\s+)?(?P<rel>{RELATIONS})\b(?P<poss>{POSS})?", re.I)
HOP = re.compile(r"(?:'s|’s)\s+(?P<hop>spouse|husband|wife|partner)\b", re.I)
ASKS = [
    ("spouse", re.compile(r"\bmarried to\b|\bwho (?:is|did) .{1,40} (?:married|marry)\b", re.I)),
    ("from", re.compile(r"\bgr[eo]w(?:n)? up\b|\b(?:was|were|am|is|are|get|got) raised\b|\bwhere (?:am i|are we|(?:is|was|are) (?:my|our) [^?]{1,30}?) from\b|"
                        r"\bwhere (?:do|does|did) [^?]{1,30} come from\b|\boriginally from\b|\bwhere (?:was|were) [^?]{1,30}\b(?:born|raised)\b|"
                        r"\bwhere (?:i'?m|i am|we'?re|we are) from\b", re.I)),
    ("birthday", re.compile(r"\bbirthday\b|\bb-?day\b|\bborn\b", re.I)),
    ("favorite", re.compile(r"\bfavou?rite\s+(?P<thing>[a-z][a-z ]{1,30}?)(?=\s+(?:these days|now|lately|again|is|are)\b|[?.!]|$)|"
                            r"\bwhich (?P<thing2>[a-z]+) do i (?:like|love) (?:best|most|the most)\b", re.I)),
    ("allergy", re.compile(r"\ballerg(?:y|ic|ies)\b|\bcan(?:'t|not) (?:eat|have)\b|\bcan(?:'t|not) (?:i|we|she|he|they|(?:my|our) [a-z]+) eat\b|"
                           # asked without the word: "which foods or medicines are dangerous for me" was answered "never told" with the allergy saved.
                           # Only with a food or a medicine in the question: "is it dangerous for me to walk home alone" is no allergy.
                           r"\b(?:foods?|medicines?|meds|medications?|drugs?|ingredients?)\b.{0,40}\b(?:dangerous|unsafe|deadly|harmful|off[- ]limits|avoid|stay away from|"
                           r"careful (?:with|about)|watch out for|react to|bad for)\b|"
                           r"\b(?:dangerous|unsafe|deadly|harmful|avoid|stay away from|react(?:s|ed)? (?:badly )?to|have a reaction to)\b.{0,30}\b(?:foods?|medicines?|meds|"
                           r"medications?|ingredients?|eat(?:ing)?)\b", re.I)),
    ("work", re.compile(r"\bworks? (?:as|at|for)\b|\bwhere (?:do|does|did) .{1,30}\bwork\b|\bwhere(?:'s|'re|’s| is| are)\b.{1,30}\bworking\b|\bjobs?\b|\bfor a living\b|\bfor work\b|\bprofession\b|\bcareer\b|"
                        r"\bemployer\b|\bwhat (?:do|does) .{1,30}\bdo\b\s*(?:[?.!]|$)", re.I)),
    ("home", re.compile(r"\b(?:do|does|did) .{1,30}\blive\b|\blives?\b|\bliving\b|\b(?:what|which) (?:city|town|state|country)\b|\bbased\b|\bmoved?\b|\brelocated?\b|"
                        r"(?:'s|’s) (?:city|town)\b|\b(?:city|town) (?:is|was) (?:my|our)\b|"
                        r"\bhome ?town\b|\bwhere(?:'s|'d| is| are| did| does| do)?\b.{0,40}\b(?:staying|at (?:now|these days)|these days|nowadays|end(?:ed)? up|settled?)\b|"
                        r"\bstill (?:in|out in|over in|up in|down in)\b", re.I)),
    ("pet", re.compile(rf"\b(?P<species>{SPECIES}|pet)\b.*\b(?:name|named|call|called)\b|\b(?:name|named|call|called)\b.*\b(?P<species2>{SPECIES}|pet)\b", re.I)),
    ("into", re.compile(r"\binto\b|\bhobb(?:y|ies)\b|\binterested in\b", re.I)),
    # (last of the kinds, so "who is my sister married to" is still about the marriage: who + their person, and nothing else asked)
    ("name", re.compile(r"\bname\b|\bcalled\b|\bgo(?:es)? by\b|^\W*who(?:'s|’s| is) my\b|\bwho\b[^?]{0,30}\b(?:my|our)\b|\b(?:my|our)\b[^?]{0,40}\bwho\b|"
                        r"\bwhat (?:do|should|can|did) (?:i|we|you) call (?:my|our)\b", re.I)),
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
    rest = re.sub(r"^(?:(?:actually|officially|also|has|have) )+(?=\w)", "", rest.strip(), flags=re.I) or rest   # "has officially moved to": the fact starts at "moved"
    for kind, pattern in REST:
        found = pattern.match(rest.strip())
        if not found:
            continue
        named = found.groupdict()
        if "place" in named:   # only a place said like a place: "Denver", "New Orleans", never "a mood" or "lunch"
            raw = (named["place"] or "").strip()
            if not raw[:1].isupper() or len(raw.split()) > 4:
                continue
            value = _clean(raw)
        else:
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
    text = LEAD_IN.sub("", text) or text
    text = REL_S_IN.sub(r"\1 is ", text)
    if text.count("my ") + text.count("your ") == 1 or not PEOPLE_FACT.match(text):
        they = THEN_THEY.search(text)
        if they and not REL_IS.match(text) and len(re.findall(rf"\b(?:my|your) (?:{RELATIONS})\b", text, re.I)) == 1:
            later = Reading()   # only when one person of theirs is in it: with two, "he" could be either
            if _rest(later, "rel:" + _rel(they["rel"]), ("is " if they["be"] else "") + they["rest"].strip()):
                return later
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


# Something they said about themselves that has the plain shape of saying what they do, where they live or where
# they're from, in words no rule reads as a fact: "I'm a nurse at the children's hospital", "I rent a studio above a
# laundromat", "I grew up in a town called Marfa". Asked "what's my job" later, Luma said "I don't know your job yet."
_NOT_A_JOB = (r"bit|little|lot|mess|wreck|fan|big|huge|person|man|woman|guy|girl|kid|mom|mother|dad|father|parent|twin|friend|loser|failure|burden|idiot|fool|joke|"
              r"disappointment|morning|night|sucker|believer|sagittarius|virgo|leo|gemini|few|couple|month|year|week|day|while|minute|second|long|good|bad|"
              r"terrible|great|decent|horrible|light|heavy|only|single|different|new|huge|total|complete|real|nervous|hot|hopeless|slow|fast|picky")
OWN_SAID = {
    "work": re.compile(rf"^(?:so |well |and |anyway,? |fyi,? )?i(?:'m| am|'ve been| have been| work as| worked as) (?:an? |the )(?!(?:{_NOT_A_JOB})\b)[a-z][a-z' -]{{2,40}}?"
                       r"(?: at | for | in | on | with |,| since | now|\.|!|$)|^(?:so |well |and )?i (?:work|teach|drive|cook|wait tables|bartend|nurse|clean|deliver|manage|run|own) "
                       r"(?:nights|days|shifts|at|for|in|the|a|an|my|our)\b", re.I),
    "home": re.compile(r"^(?:so |well |and )?i (?:rent|live|stay|share|just moved into|moved into|bought|own) (?:in |on |at |with |a |an |the |my |above |near |by |over |out )",
                       re.I),
    "from": re.compile(r"^(?:so |well |and )?i (?:grew up|was raised|was born (?:in|at|on|and raised)|come from|came (?:over |here )?from|moved here from|am originally from|'m originally from)\b", re.I),
}


def says_own(text):
    """Which of work, home and from a sentence about themselves states, in plain shape: a set."""
    said = " ".join(str(text or "").split())
    return {what for what, shape in OWN_SAID.items() if shape.search(said)} if 3 <= len(said.split()) <= 30 and "?" not in said else set()


def asks_about_travel(question):
    return bool(TRAVEL_ASK.search(str(question or "")))


def private(text, category=""):
    """Health, money and the hard parts of relationships: not for when there's company in the room."""
    return category == "health" or bool(PRIVATE.search(str(text or "")))
