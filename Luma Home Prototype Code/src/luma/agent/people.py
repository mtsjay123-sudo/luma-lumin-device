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
# Three more ways a name comes with who they are. Only with a capital: "a friend called earlier" names nobody.
_ADJ = r"(?:(?:little|big|older|younger|best|baby|twin)\s+)?"
APPOSED = re.compile(r"\b(?P<name>[A-Z][a-z]{1,14}),\s+my\s+" + _ADJ + r"(?P<rel>" + RELATIONS + r")\b,?(?P<rest>[^.!?]{0,90})")           # "Marcus, my brother, called"
NAMED_AS = re.compile(r"\b(?:a|an|my|one|our)\s+" + _ADJ + r"(?P<rel>" + RELATIONS + r")\s+(?:named|called)\s+(?P<name>[A-Z][a-z]{1,14})\b(?P<rest>[^.!?]{0,90})")
IN_BRACKETS = re.compile(r"\bmy\s+" + _ADJ + r"(?P<rel>" + RELATIONS + r")\s+\((?P<name>[A-Z][a-z]{1,14})\)(?P<rest>[^.!?]{0,90})", re.I)
NOT_NAMES = set("""a an the and or but if so to of in on at for with from is are was were be been being it its this that these those
you your i me my we us our they them their he him his she her do does did have has had just not no yes yeah got get can will would
could should like know let what how why when where who maybe some something really all up out about as more one too very much any
there here then than now well oh okay ok sure keeps kept always never said says told called calls texted texts died passed left came
comes went goes loves loved likes liked hates hated wants wanted needs needed thinks thought lives lived works worked started finally
still also lol lmao rn tho though even didn't doesn't won't can't isn't wasn't used made makes took takes gave gives bought sent sends
asked asks ate eats broke fell moved moves found lost won became becomes turned turns gets getting got's literally lowkey honestly
basically kinda sorta again already almost actually only ever recently suddenly constantly probably definitely totally barely
who's that's he's she's they're i'm is's""".split())
# What someone does ("my mom work nights") or is ("my dad mad at me"). Without a capital letter these aren't taken as a
# name after "my sister". With one they are: "My dog Happy". None of them is a common first name.
WHAT_THEY_DO = set("""live work love want need think say tell call text come go make take give buy send ask eat break fall move find lose
win become turn keep leave stay visit feel look seem sound hear see talk speak try help care mind remember forget understand believe
drive play use start stop drink sleep wake cook pay read write run walk sit stand wear bring meet miss hurt cry laugh smile worry wish
plan own stays stayed acts act hit hits mad sad sick crazy tired mean nice cool funny weird right wrong fine good bad great old young
busy angry upset happy scared proud dead alive gone home back pregnant drunk late early single smart dumb stupid cute hot cold
trippin tripping wild tall short fat skinny lazy broke bored annoyed stressed depressed lonely jealous worried""".split())
# "where does my sister live", "should my mom know", "is my dad right": a question, and the word after the relation is what
# they do or are. "this is my sister maya" isn't a question: the helping verb has to start the sentence or follow a question word.
ASKING = re.compile(r"(?:^|[.!?,;:]\s*|\b(?:and|but|so|or)\s+|\b(?:what|where|when|why|how|who|which)\s+(?:\w+\s+){0,2}?)"
                    r"(?:do|does|did|can|could|should|would|will|might|must|may|is|are|was|were|has|have|had|"
                    r"don'?t|doesn'?t|didn'?t|can'?t|couldn'?t|shouldn'?t|wouldn'?t|won'?t|isn'?t|aren'?t|wasn'?t|weren'?t|hasn'?t|haven'?t)\s+$", re.I)
PHRASAL = re.compile(r"^\s*(?:away|out|on|by|up|down|off|over|back|around|in|me|us|you|him|her|them)\b", re.I)
DURABLE = re.compile(r"^(?:(?:really|just|recently|lately|finally|totally|so)\s+)?(?:"
                     r"is (?:(?:so |really |totally |kind of |kinda )?(?:obsessed with|into|allergic to|scared of|afraid of|terrified of|"
                     r"good at|great at|amazing at|bad at|learning|studying|turning \d+|turning|vegan|vegetarian|retired|pregnant|engaged|"
                     r"married|in (?:college|school|high school|grad school|\w+ grade))|an? \w+|\d+(?: years old)?)|"
                     r"got into|started|loves?|likes?|hates?|plays?|collects?|works (?:at|as|in|for)|lives in|moved (?:back )?to|relocated to|transferred to|"
                     r"is (?:now |still )?living in|is back in (?-i:[A-Z])|ended up in (?-i:[A-Z])|settled (?:down )?in (?-i:[A-Z])|(?:got|bought|found|rented) (?:a|an|his|her|their) (?:own |new )*"
                     r"(?:place|apartment|house|condo) in (?-i:[A-Z])|can'?t eat|doesn'?t eat|"
                     r"has (?:a|an|two|three|\d+)|wants to be|is learning|graduated|got (?:a|her|his) (?:first|new))\b", re.I)
PRONOUN_START = re.compile(r"^\s*(?:and\s+|but\s+|so\s+|like\s+)?(?:he|she|they|his|her|their|him)\b", re.I)


def _name_ok(name, text):
    low = name.lower()
    if low in NOT_NAMES or len(low) < 2:
        return False
    if low in WHAT_THEY_DO and not name[:1].isupper():
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
        if ASKING.search(text[:m.start()]) and not m["name"][:1].isupper():
            continue  # "where does my sister live": no capital, and it's where a verb goes
        if _name_ok(m["name"], text) and not PHRASAL.match(m["rest"]):  # "my dad passd away": a verb, typo and all
            found.append((m["name"].capitalize(), m["rel"].lower(), m["rest"].strip(" ,")))
    for pattern in (NAMED, APPOSED, NAMED_AS, IN_BRACKETS):
        for m in pattern.finditer(text):
            row = (m["name"].capitalize(), m["rel"].lower(), m["rest"].strip(" ,"))
            if m["name"][:1].isupper() and _name_ok(m["name"], text) and row[:2] not in [f[:2] for f in found]:
                found.append(row)
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


# ---------------------------------------------------------------------------------------------------------------------
# Said another way round. The month test on real brains, on the lives Luma wasn't built on (run 56, Nov 20, 2026): asked a
# sister's name or where a mom lives, the small brains said it 0 times of 12. The lines that had told Luma weren't read as
# facts at all: of 12 fresh ways of giving a sister's name, asked "what's my sister's name" Luma itself said "I don't know
# your sister's name yet" after 9. These read the same two facts however the sentence is turned, and hand back the plain
# sentence the rest of Luma already understands ("My sister's name is Priya", "My mom lives in Tampa").
_REL = r"(?:my|our)\s+" + _ADJ + r"(?P<rel>" + RELATIONS + r")"
_NAME = r"(?P<name>[A-Z][a-z]{1,14})"
_PLACE = r"(?P<place>[A-Z][a-zA-Z.'-]+(?: [A-Z][a-zA-Z.'-]+){0,2})"
_END = r"(?=\s*(?:[,.!?;]|$|\b(?:by the way|btw|fyi|after|for short|now)\b))"
NAMED_PLAINLY = [re.compile(p) for p in (
    r"\b" + _REL + r"\s+(?:goes by|is called|is named|'s called|'s named|answers to|is known as)\s+" + _NAME + r"\b",
    r"\b(?:[Ee]veryone|[Ee]verybody|[Ww]e|[Pp]eople|[Tt]hey|[Yy]ou can|[Yy]ou could|I|[Ff]olks)(?:\s+all|\s+just)?\s+calls?\s+" + _REL + r"\s+" + _NAME + r"\b",
    r"\b" + _REL + r"\s*[?,:-]+\s*(?:[Hh]er|[Hh]is|[Tt]heir)\s+name(?:'s| is)\s+" + _NAME + r"\b",
    r"\b" + _REL + r"\s*,\s*(?:she|he|they)(?:'s| is|'re| are)\s+(?:called|named)\s+" + _NAME + r"\b",
    r"\b[Tt]he name of\s+" + _REL + r"\s+is\s+" + _NAME + r"\b",
    r"\b" + _REL + r"\s+is\s+" + _NAME + _END,
    r"\b" + _NAME + r"(?:'s| is)\s+" + _REL + r"'s name\b",
    r"\b[Ii]t'?s\s+" + _NAME + r"\s*,\s*" + _REL + r"'s name\b",
    r"\b" + _NAME + r"\s*,\s*that'?s\s+" + _REL + r"\b",
    r"\b" + _NAME + r"(?:'s| is)\s+" + _REL + _END,
    r"\bI(?:'ve| have)?\s+(?:got\s+)?an?\s+" + _ADJ + r"(?P<rel>" + RELATIONS + r")\s*,\s*" + _NAME + _END,
    r"\b(?:[Ww]e|[Mm]y parents|[Tt]hey|[Mm]om|[Dd]ad)\s+named\s+" + _REL + r"\s+" + _NAME + r"\b",
)]
# Not a name, however it's capitalised: what someone is, not what they're called.
NOT_A_NAME = re.compile(r"(?:ese|ish|ian|ican|can|lic|ist|ite|ean)$|^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|January|February|March|April|May|June|"
                        r"July|August|September|October|November|December|Catholic|Jewish|Muslim|Christian|Buddhist|Hindu|Democrat|Republican|Black|White|"
                        r"Asian|Latino|Latina|Deaf|Type|Dr|Mr|Mrs|Ms|God|OK|Okay|Mom|Dad|Home|Here|There|Back|Fine|Good|Great|Sick|Dead|Gone|Luma|"
                        r"Pregnant|Engaged|Married|Single|Divorced|Retired|Alive|Happy|Sad|Mad|Angry|Upset|Tired|Busy|Away|Out|In|Late|Early|Right|Wrong|Gay|"
                        r"Trans|Vegan|Sober|Blind|Autistic|Diabetic|Awesome|Amazing|Crazy|Wild|Funny|Sweet|Nice|Mean|Cool|Hot|Cold|Old|Young|Tall|Short|Rich|"
                        r"Broke|Lost|Free|Ready|Done|Next|First|Last|Number|Team|Queen|King|Boss|Family|Everything|Nothing|Something|Love)$", re.I)
_IN = r"(?:(?:way |far )?(?:out|down|up|over|back)\s+)"
LIVES_PLAINLY = [re.compile(p) for p in (
    r"\b" + _REL + r"(?:'s| is| has been|'s been|'s living| is living| lives| stays| resides| is based|'s based)\s+" + _IN + r"in\s+" + _PLACE,
    r"\b" + _REL + r"(?: has been|'s been|'s living| is living| stays| resides| is based|'s based)\s+in\s+" + _PLACE,
    r"\b" + _REL + r"\s*,\s*(?:she|he|they)(?:'s| is|'re| are)\s+" + _IN + r"?in\s+" + _PLACE,
    r"\b" + _PLACE + r"\s+is where\s+" + _REL + r"\s+(?:lives|is|stays|settled|ended up|is based)\b",
    r"\b" + _REL + r"\s+calls\s+" + _PLACE + r"\s+home\b",
    r"\b" + _REL + r"\s+has\s+(?:a|her|his|their|her own|his own)\s+(?:place|house|apartment|condo|home|flat)\s+in\s+" + _PLACE,
    r"\b" + _REL + r"'s\s+(?:place|house|apartment|condo|home|flat)\s+is\s+" + _IN + r"?in\s+" + _PLACE,
    r"\b[Hh]ome for\s+" + _REL + r"\s+is\s+" + _PLACE,
)]
# There for now, not living there.
ONLY_VISITING = re.compile(r"\b(?:this (?:week|weekend|month|morning|afternoon|evening)|today|tonight|tomorrow|right now|for (?:the|a) (?:weekend|week|day|night|few days|"
                           r"holidays?|conference|wedding|funeral|trip)|for (?:work|business|christmas|thanksgiving|vacation)|until|till|visiting|on vacation|"
                           r"on a trip|travell?ing|flying|driving|stuck|stranded|passing through|for now|temporarily)\b", re.I)
ASKING_IT = re.compile(r"\?\s*$|^\W*(?:what|who|where|when|which|why|how|is|are|does|do|did|can|could|would|should|remind|tell)\b", re.I)


# Someone moved, said by the signs of a move and not by a sentence shape: "Marcus packed up and left for Denver", "Marcus and
# his wife bought a house in Denver", "my brother made the move to Denver". Who it is has to be someone Luma already
# knows as theirs (a name it was told, or "my brother"); the place is the last one said like a place.
MOVE_SIGN = re.compile(r"\b(?:mov(?:ed?|ing) (?:to|back|out|over|up|down|in|into|here|away)|relocat\w+|transferr\w+|left (?:for|(?-i:[A-Z]))|leaving (?:for|(?-i:[A-Z]))|for good|settled|settling|new (?:place|apartment|house|home|city)|"
                       r"bought (?:a|their|his|her) (?:house|place|condo|home)|got (?:a|his|her|their) (?:own )?(?:place|house|apartment)|(?:a|new|the) job (?:in|out in)|"
                       r"swapped|traded|packed up|made the (?:move|jump|leap)|lives?|(?:'s|has|have) lived|living|based|calls|retired to|settl\w+ into)\b", re.I)
HAS_A_PLACE = re.compile(r"\bhas (?:an?|her|his|their)(?: own)? (?:place|house|apartment|condo|home|flat) (?:in|near|outside|out in|down in|up in) [A-Z]")
NOT_SURE_OF_IT = re.compile(r"\b(?:might|maybe|thinking (?:of|about)|wants? to|would like|considering|if|whether|hopes? to|hoping|talks? about|talking about|"
                            r"should|could|would|used to|grew up|was born|born|visit\w*|trip|vacation|flew|flying|drove|driving|when (?:she|he|they|i|we) (?:was|were)|"
                            r"as a (?:kid|child|girl|boy)|growing up|back then|at the time|before (?:she|he|they|i|we))\b", re.I)
PLACE_AFTER = re.compile(r"\b(?:in|to|for|into)\s+" + _PLACE)


def _moved(text, names):
    who = None
    rel = re.search(r"\b" + _REL + r"\b(?!'s\s+(?!in\b|out\b|down\b|up\b|over\b|back\b|been\b|living\b|moved\b|lived\b))", text)
    for name in names or ():
        if re.search(rf"\b{re.escape(name)}\b", text):
            who = name
            break
    if not who and rel:
        who = "My " + rel["rel"].lower()
    if not who or not (MOVE_SIGN.search(text) or HAS_A_PLACE.search(text)) or NOT_SURE_OF_IT.search(text) or ONLY_VISITING.search(text) or len(text.split()) > 24:
        return None
    places = [m["place"].rstrip(".,") for m in PLACE_AFTER.finditer(text)]
    places = [p for p in places if not NOT_A_NAME.search(p.split()[0]) and p.split()[0] not in (names or ()) and p.lower() != who.lower()]
    return f"{who} lives in {places[-1]}" if places else None


# A name by what stands between it and the person, not by the shape of the sentence: "meet my sister, Priya", "that's Priya,
# my sister", "I've got a sister called Priya", "my sister - Priya - is the funny one". Only linking words may stand between
# them ("my sister loves Priya" and "my sister's friend Priya" have more), and the name has to end its phrase.
LINKS = set("is 's called named name names goes by go known as that's thats this she's he's they're shes hes her his their the a an we i you everyone everybody "
            "people folks call calls it's its meet say hi to".split())
_TOKEN = re.compile(r"[A-Za-z][A-Za-z']*|[,;:()-]|[.!?]")
_MARK = (",", "-", ":", "(", ";")
_STOPS = ("", ",", "-", ".", "!", ")", ";")


def _a_name(token, text, rels):
    return (token[:1].isupper() and len(token) > 2 and token.lower() not in LINKS and not token.lower().endswith("'s") and _name_ok(token, text)
            and not NOT_A_NAME.search(token) and token.lower() not in rels)


def _named_by_links(text):
    """(relation, Name) when only linking words stand between someone of theirs and a name; or None."""
    tokens = _TOKEN.findall(text.replace("’", "'"))
    rels = RELATIONS.split("|")
    first_person = bool(re.search(r"\bI(?:'ve| have| got)\b", text))
    for i, tok in enumerate(tokens):
        low = tok.lower()
        base = low[:-2] if low.endswith("'s") else low
        two = (tokens[i - 1].lower() + " " + base) if i else ""
        rel = two if two in rels else base if base in rels else None   # "best friend" is two words
        start = i - 1 if rel == two else i
        if not rel:
            continue
        j = start - 1
        while j >= 0 and tokens[j].lower() in ("little", "big", "older", "younger", "baby", "twin"):
            j -= 1
        if j < 0 or not (tokens[j].lower() in ("my", "our") or (tokens[j].lower() in ("a", "an", "one") and first_person)):
            continue
        possessive = low.endswith("'s")
        # the name after the person: "my sister, Priya" / "my sister is called Priya" / "a sister called Priya"
        k, between = i + 1, (["'s"] if possessive else [])
        while k < len(tokens) and k <= i + 6:
            t = tokens[k]
            if t[:1].isupper() and t.lower() not in LINKS:
                after = tokens[k + 1] if k + 1 < len(tokens) else ""
                words = [b for b in between if b not in _MARK]
                # "my mom called Priya" is a phone call; "my sister is called Priya" and "a sister called Priya" are a name
                phoned = "called" in words and tokens[j].lower() in ("my", "our") and not ({"is", "'s", "she's", "he's", "they're"} & set(words))
                if _a_name(t, text, rels) and between and words != ["'s"] and not phoned and (after in _STOPS or after.lower() in ("is", "by", "btw", "and")):
                    return rel, t
                break
            if t.lower() not in LINKS and t not in _MARK:
                break
            between.append(t.lower())
            k += 1
        # the name before the person: "that's Priya, my sister" / "Priya is my sister"
        if possessive:
            continue
        k = j - 1
        while k >= 0 and k >= j - 5:
            t = tokens[k]
            if t[:1].isupper() and t.lower() not in LINKS:
                nxt = tokens[k + 1] if k + 1 < len(tokens) else ""
                tail = tokens[i + 1] if i + 1 < len(tokens) else ""
                if _a_name(t, text, rels) and (k > 0 or nxt in (",", "is", "'s")) and tail in _STOPS:
                    return rel, t
                break
            if t.lower() not in LINKS and t not in _MARK:
                break
            k -= 1
    return None


def plainly(text, names=()):
    """["My sister's name is Priya", "My mom lives in Tampa"]: the same facts, read from a sentence turned any other way.
    Only from a statement, never a question; a name has to be said like a name and a place like a place. names: the
    people Luma already knows as theirs, by name."""
    text = " ".join(str(text or "").replace("’", "'").split())
    if not text or len(text) > 200 or ASKING_IT.search(text):
        return []
    out, place = [], None
    moved = _moved(text, names)
    if moved:
        return [moved]
    if not ONLY_VISITING.search(text):
        for pattern in LIVES_PLAINLY:
            m = pattern.search(text)
            if m and not NOT_A_NAME.search(m["place"].split()[0]):
                place = m["place"].rstrip(".,")
                out.append(f"My {m['rel'].lower()} lives in {place}")
                break
    if not place:   # one sentence, one fact: "home for my mom is Tampa" doesn't also name her Tampa
        for pattern in NAMED_PLAINLY:
            m = pattern.search(text)
            if m and len(m["name"]) > 2 and _name_ok(m["name"], text) and not NOT_A_NAME.search(m["name"]) and m["name"].lower() not in RELATIONS.split("|"):
                out.append(f"My {m['rel'].lower()}'s name is {m['name']}")
                break
        if not out:
            found = _named_by_links(text)
            if found:
                out.append(f"My {found[0]}'s name is {found[1]}")
    return out
