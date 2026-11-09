"""The people in their life, the way a friend keeps track: "my brother marcus just got into bouldering" means Marcus is
their brother (not them) and he climbs now.

Two uses:
- In a conversation, a short note sits next to their newest message: who's who, and what they said about each person. A
  small brain then doesn't ask "Wait, so you're Marcus?" or forget the climbing three turns later when they ask what to get
  him (the device lab's small brain did both).
- Across days, what they said about someone is kept as a memory ("Lily (their daughter) is obsessed with dinosaurs right
  now"), so "what should I get Lily?" on Friday finds it.
"""
from __future__ import annotations

import re

RELATIONS = (r"best friend|bestie|brother|sister|mom|mother|mama|dad|father|son|daughter|wife|husband|girlfriend|boyfriend|"
             r"partner|friend|cousin|aunt|auntie|uncle|grandma|grandpa|grandmother|grandfather|granny|nana|boss|coworker|"
             r"roommate|neighbou?r|kid|baby|niece|nephew|fianc[eé]e?|ex|teacher|coach|stepmom|stepdad|godmother|godfather|"
             r"dog|cat|puppy|kitten")
MENTION = re.compile(r"\bmy\s+(?:(?:little|big|older|younger|baby|twin|step|half|oldest|youngest|new|old|best)\s+)?(?P<rel>" + RELATIONS
                     + r")\s+(?P<name>[A-Za-z][a-z'’]{1,14})\b(?P<rest>[^.!?]{0,90})", re.I)
NAMED = re.compile(r"\b(?P<name>[A-Z][a-z]{1,14})\s+(?:is|was)\s+my\s+(?:(?:little|big|older|younger|best)\s+)?(?P<rel>" + RELATIONS
                   + r")\b(?P<rest>[^.!?]{0,90})")
NOT_NAMES = set("""a an the and or but if so to of in on at for with from is are was were be been being it its this that these those
you your i me my we us our they them their he him his she her do does did have has had just not no yes yeah got get can will would
could should like know let what how why when where who maybe some something really all up out about as more one too very much any
there here then than now well oh okay ok sure keeps kept always never said says told called calls texted texts died passed left came
comes went goes loves loved likes liked hates hated wants wanted needs needed thinks thought lives lived works worked started finally
still also lol lmao rn tho though even didn't doesn't won't can't isn't wasn't used made makes took takes gave gives bought sent sends
asked asks ate eats broke fell moved moves found lost won became becomes turned turns gets getting got's literally lowkey honestly
basically kinda sorta again already almost actually only ever recently suddenly constantly probably definitely totally barely
who's that's he's she's they're i'm is's""".split())
PHRASAL = re.compile(r"^\s*(?:away|out|on|by|up|down|off|over|back|around|in|me|us|you|him|her|them)\b", re.I)
DURABLE = re.compile(r"^(?:(?:really|just|recently|lately|finally|totally|so)\s+)?(?:"
                     r"is (?:(?:so |really |totally |kind of |kinda )?(?:obsessed with|into|allergic to|scared of|afraid of|terrified of|"
                     r"good at|great at|amazing at|bad at|learning|studying|turning \d+|turning|vegan|vegetarian|retired|pregnant|engaged|"
                     r"married|in (?:college|school|high school|grad school|\w+ grade))|an? \w+|\d+(?: years old)?)|"
                     r"got into|started|loves?|likes?|hates?|plays?|collects?|works (?:at|as|in|for)|lives in|can'?t eat|doesn'?t eat|"
                     r"has (?:a|an|two|three|\d+)|wants to be|is learning|graduated|got (?:a|her|his) (?:first|new))\b", re.I)
PRONOUN_START = re.compile(r"^\s*(?:and\s+|but\s+|so\s+|like\s+)?(?:he|she|they|his|her|their|him)\b", re.I)


def _name_ok(name, text):
    low = name.lower()
    if low in NOT_NAMES or len(low) < 2:
        return False
    if re.search(r"(?:ing|ly)$", low) and len(low) > 4 or (low.endswith("ed") and len(low) > 4):
        return False
    lowercase_text = text == text.lower()
    return lowercase_text or name[:1].isupper()


def mentions(text):
    """[(Name, relation, what they said right after)] in one message."""
    text = str(text or "")
    found = []
    for m in MENTION.finditer(text):
        if _name_ok(m["name"], text) and not PHRASAL.match(m["rest"]):  # "my dad passd away": a verb, typo and all
            found.append((m["name"].capitalize(), m["rel"].lower(), m["rest"].strip(" ,")))
    for m in NAMED.finditer(text):
        if _name_ok(m["name"], text):
            found.append((m["name"].capitalize(), m["rel"].lower(), m["rest"].strip(" ,")))
    return found


def _sentence_with(text, name):
    for s in re.split(r"(?<=[.!?])\s+", str(text)):
        if re.search(rf"\b{re.escape(name)}\b", s, re.I):
            return s.strip()[:140]
    return ""


def in_conversation(user_messages):
    """{Name: {"relation": ..., "said": [what they said about them]}} across their messages, oldest first."""
    people = {}
    last = None
    for msg in user_messages:
        msg = str(msg or "")
        found = mentions(msg)
        for name, rel, _ in found:
            person = people.setdefault(name, {"relation": rel, "said": []})
            line = _sentence_with(msg, name)
            if line and line not in person["said"]:
                person["said"].append(line)
            last = name
        if not found:
            hit = next((n for n in people if re.search(rf"\b{re.escape(n)}\b", msg, re.I)), None)
            if hit:
                line = _sentence_with(msg, hit)
                if line and line not in people[hit]["said"]:
                    people[hit]["said"].append(line)
                last = hit
            elif last and PRONOUN_START.search(msg) and len(people[last]["said"]) < 4:
                people[last]["said"].append(msg.strip()[:140])  # "he goes like 4 times a week now lol", about the last one named
            else:
                last = None
    return people


def note(user_messages, newest="", limit=2):
    """The note next to their newest message, or "" when nobody has come up."""
    people = in_conversation(list(user_messages) + [newest])
    if not people:
        return ""
    newest_low = str(newest).lower()
    ranked = sorted(people.items(), key=lambda kv: (kv[0].lower() not in newest_low, -list(people).index(kv[0])))[:limit]
    parts = []
    for name, p in ranked:
        quotes = "; ".join(f"“{s}”" for s in p["said"][-2:])
        parts.append(f"{name}, their {p['relation']}" + (f" ({quotes})" if quotes else ""))
    return ("People they've told you about. They're not the person you're talking to; talk with them about these people: "
            + " | ".join(parts) + ".")[:420]


def facts(text):
    """What's worth keeping about someone they love, as memories: "Lily (their daughter) is obsessed with dinosaurs right now".
    Only things about the person, not passing events ("my mom called" isn't kept)."""
    out = []
    for name, rel, rest in mentions(text):
        rest = re.sub(r"\s+(?:lol|lmao|tbh|ngl|fr|rn)\b.*$", "", rest, flags=re.I).strip(" ,")
        if rest and DURABLE.match(rest) and 2 <= len(rest.split()) <= 16:
            out.append(f"{name} (their {rel}) {rest}")
    return out
