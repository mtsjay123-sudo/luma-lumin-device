"""What makes Luma feel like it knows you: it notices, it checks back, it remembers when asked.

Everything here is plain rules over what you said to Luma. Nothing is inferred
from other data, nothing is sent anywhere, and every saved item shows up in
Memories where you can edit or delete it.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Durable facts worth keeping, said in passing. Each pattern captures a whole fact.
DATE = r"(?:on\s+)?(?i:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-zA-Z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?\b"
I = re.I
PEOPLE = (r"(?:girlfriend|boyfriend|gf|bf|wife|husband|partner|fianc[eé]e?|mom|mother|dad|father|sister|brother|son|daughter|kid|baby|best friend|bestie|"
          r"boss|roommate|grandma|grandmother|grandpa|grandfather|aunt|uncle|cousin|niece|nephew|dog|cat|puppy)")
TOWN = r"[A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*){0,2}"
PETS = r"(?:dog|cat|puppy|kitten|parrot|bird|rabbit|bunny|hamster|turtle|fish|horse|lizard|snake|guinea pig|ferret)"
FACT_PATTERNS = [
    (r"\b(?:my|our)\s+(?:[a-z']+\s+){0,2}(?:birthday|bday|anniversary)\s+is\s+" + DATE, I),
    (r"\b[A-Z][a-z]+(?:'s|’s)\s+(?:birthday|bday)\s+is\s+" + DATE, 0),
    (r"\b(?:[Mm]y|[Oo]ur)\s+" + PEOPLE + r"(?:'s)?\s+(?:name\s+)?is\s+(?:named\s+|called\s+)?[A-Z][a-z]+\b", 0),
    # typed in lowercase ("my sister's name is dana"): only with "name is", "named" or "called", so "my mom is tired" isn't a name
    (r"\b(?:my|our)\s+" + PEOPLE + r"(?:(?:'s|’s)\s+name\s+is|\s+is\s+(?:named|called))\s+(?!(?:like|um|uh|so|really|not|kinda|literally)\b)[a-z][a-z'-]+\b", I),
    (r"\bI(?:'m| am)\s+allergic\s+to\s+[a-z]+(?:(?:,\s*|\s+and\s+|\s+or\s+)[a-z]+){0,3}", I),
    (r"\bI(?:'m| am)\s+(?:vegetarian|vegan|pescatarian|gluten[- ]free|lactose intolerant|diabetic|pregnant)\b", I),
    (r"\bI\s+(?:work|go to school)\s+(?:at|for)\s+[A-Z][\w&']*(?:\s+[A-Z][\w&']*){0,4}", 0),
    (r"\bmy\s+favou?rite\s+[a-z ]{2,20}?\s+is\s+[\w' ]{2,40}?(?=$|[.,!;]|\s+(?:and|but|btw|lol)\b)", I),
    # Where they live and are from, said with a capital ("I live in Austin", never "I live in fear"), and a move that's coming.
    (r"\bI\s+(?:live|was\s+born)\s+in\s+" + TOWN, 0),
    (r"\bI(?:'m|’m| am)\s+from\s+" + TOWN, 0),
    (r"\bI(?:'m|’m| am)\s+moving\s+to\s+" + TOWN + r"(?:\s+in\s+(?i:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-zA-Z]*)?", 0),
    # Their work, a pet by name, and the same about the people in their life.
    (r"\bI\s+work\s+as\s+an?\s+[a-z][a-z' -]{2,30}?(?=$|[.,!;]|\s+(?:and|but|so|at|in|for|now|these days)\b)", I),
    (r"\bI\s+teach\s+(?!(?:my|him|her|them|you|it|myself|people|kids)\b)[A-Za-z][\w' -]{1,40}?(?=$|[.,!;]|\s+(?:and|but|so)\b)", 0),
    (r"\bI\s+have\s+an?\s+" + PETS + r"\s+(?:named|called)\s+[A-Z][a-z]+\b", 0),
    (r"\b[Mm]y\s+" + PETS + r"\s+[A-Z][a-z]+\s+is\s+\w+\s+years?\s+old\b", 0),
    (r"\b[Mm]y\s+" + PEOPLE + r"\s+(?:works\s+(?:as|at|for)\s+(?:an?\s+)?[\w&' -]{2,40}?|is\s+allergic\s+to\s+[a-z]+(?:(?:,\s*|\s+and\s+|\s+or\s+)[a-z]+){0,3})"
     r"(?=$|[.,!;]|\s+(?:and|but|so)\b)", 0),
]
SKIP_FACTS = re.compile(r"\?|^\s*(?:(?:hey|ok|okay)\s+)?(?:luma[,\s]+)?(?:remember|remind|recall|text|message|tell|let|search|look up|find|what|who|when|where|why|how|can you|could you|would you|please)\b"
                        r"|\b(?:text|message|tell|let)\s+(?:my\s+|our\s+)?\w+\s+(?:that|to|know)\b", re.I)

EVENTS = (r"(?:job\s+)?interview|exam|test|quiz|final|midterm|appointment|doctor|dentist|surgery|date|game|match|tryouts?|recital|presentation|pitch|demo|"
          r"meeting|flight|trip|first day|last day(?= (?:at|of) (?:work|school|class|college|my job|the job|the office|my internship)\b)|(?<=\bmy )last day|audition|court date|surgery|race|show|wedding|"
          r"performance review|vet|biopsy|ultrasound|mri|ct scan|procedure|operation|inspection|moving day|baby shower|concert|gig|open mic|marathon|"
          r"thesis defense")
OPEN_LOOP = re.compile(
    r"\b(?:(?:I|we)(?:'ve| have)?\s+(?:got\s+)?(?:a|an|my|our)|my|our|there's\s+(?:a|an|my))\s+(?P<event>(?:[a-z]+\s+){0,2}?(?:" + EVENTS + r"))\b"
    r"(?P<rest>[^.?!]{0,40}?)\b(?P<when>tonight|today|tomorrow(?: (?:morning|afternoon|night))?|this (?:morning|afternoon|evening|weekend)|"
    r"(?:on |next |this )?(?:" + "|".join(WEEKDAYS) + r")(?: (?:morning|afternoon|evening|night))?)\b", re.I)


# Where things are: "I left my keys on the counter", "my car's parked on level 3".
OBJECTS = (r"(?:spare\s+|car\s+|house\s+|work\s+)?(?:keys?|wallet|phone|passport|car|truck|bike|glasses|sunglasses|charger|laptop|bag|backpack|purse|"
           r"remote|headphones|airpods|earbuds|ring|watch|id|license|umbrella|jacket|coat|shoes|medicine|meds|pills|credit card|card|tickets?|receipt|"
           r"package|documents|notebook|tablet|ipad|camera|helmet|gloves|hat|badge|key card|keycard)")
PREP = r"(?:on top of|next to|underneath|under|behind|inside|beside|near|by|on|in|at)"
# "my phone's at 2 percent" isn't where the phone is (it was kept as "Your phone is at 2 percent. Just ask where is my phone")
PLACE = r"(?!\d+\s*(?:%|percent\b|per cent\b))(?P<place>(?:the |my |our |a |his |her |level |spot |row |section )?[\w'#-]+(?: [\w'#-]+){0,5}?)(?=$|[.,!;?]|\s+(?:and|but|so|remind|can|could|please|lol|for later|later|okay|ok|real quick|rn)\b)"
LOCATION = [
    re.compile(r"\bI(?:'ve)?\s+(?:just\s+)?(?:left|put|placed|parked|stored|hid|set|dropped|keep|stashed)\s+(?:my|the|our)\s+(?P<obj>" + OBJECTS + r")\s+(?P<prep>" + PREP + r")\s+" + PLACE, re.I),
    re.compile(r"\b(?:my|the|our)\s+(?P<obj>" + OBJECTS + r")(?:\s+(?:is|are)|'s|’s|'re)\s+(?:parked\s+|sitting\s+|at\s+home\s+)?(?P<prep>" + PREP + r")\s+" + PLACE, re.I),
]
LIKES = re.compile(r"\b(?:I(?:'m|’m| am)?|im)\s+(?:really\s+|absolutely\s+|honestly\s+|so\s+)?(?P<how>love|hate|can'?t stand|don'?t eat|do not eat|don'?t drink|don'?t like|afraid of|scared of|allergic to)\s+"
                   r"(?P<what>(?!you\b|it\b|that\b|this\b|him\b|her\b|them\b|when\b|how\b|myself\b|today\b|tonight\b|right now\b|rn\b)[a-z][\w' -]{1,40}?)(?=$|[.,!;?]|\s+(?:and|but|so|lol|tho|though)\b)", re.I)
WAKE = re.compile(r"^\W*(?:(?:hey|hi|yo|ok|okay|ayy?)\W+)?(?:luma|luna|lumo|looma|lumen|loomer)\b[\s,.:!-]*", re.I)
ASIDE = re.compile(r"^\W*(?:by the way|btw|bottom drop|quick drop|quick note|note to self|real quick|fyi|heads up|just so you know)\b[\s,.:!-]*", re.I)
CLAUSE_BREAK = re.compile(r"(?<=[.!?;])\s+|,?\s+(?=(?:what|how|can you|could you|would you|should i|do you|remind me|please|any ideas|ideas for|help me)\b)", re.I)


def strip_wake(text):
    """'Hey Luma, ...', 'Luna by the way ...': the words that only get Luma's attention aren't part of the request."""
    if not isinstance(text, str):
        return text
    out = WAKE.sub("", text, count=1)
    out = ASIDE.sub("", out, count=1)
    return out.strip() or text.strip()


def clauses(text):
    return [c.strip(" ,") for c in CLAUSE_BREAK.split(text or "") if c and c.strip(" ,")]


PLURAL = {"keys", "glasses", "sunglasses", "headphones", "airpods", "earbuds", "meds", "pills", "shoes", "gloves", "tickets", "documents"}


def location_facts(text):
    """'I left my keys on the counter and my wallet's in the car' -> [('keys', 'on the counter'), ('wallet', 'in the car')]."""
    out = []
    for part in re.split(r"\s+(?:and|&)\s+(?=(?:I|my|the|our)\b)", text or "", flags=re.I):
        for pattern in LOCATION:
            m = pattern.search(part)
            if m:
                obj = " ".join(m["obj"].lower().split())
                place = " ".join(m["place"].split()).rstrip(" .,")
                if place.lower() not in {"it", "there", "here"} and obj not in {o for o, _ in out}:
                    out.append((obj, f"{m['prep'].lower()} {place}"))
                break
    return out


def location_fact(text):
    found = location_facts(text)
    return found[0] if found else None


def where_line(obj, at):
    return f"Your {obj} {'are' if obj.split()[-1] in PLURAL else 'is'} {at}"


def notice_facts(text):
    """Facts the owner stated about themselves, their people and their things, as they said them, even mid-question."""
    if not isinstance(text, str):
        return []
    text = strip_wake(text)
    found = []
    for clause in clauses(text):
        if SKIP_FACTS.search(clause) and not location_fact(clause):
            continue
        for pattern, flags in FACT_PATTERNS:
            for match in re.finditer(pattern, clause, flags):
                fact = " ".join(match.group(0).split()).strip(" ,.")
                fact = re.sub(r"\b(name\s+is|named|called)\s+([a-z])", lambda m: f"{m[1]} {m[2].upper()}", fact)  # "dana" is "Dana"
                if fact and fact.lower() not in {f.lower() for f in found}:
                    found.append(fact[0].upper() + fact[1:])
        for obj, at in location_facts(clause):
            fact = where_line(obj, at)
            if fact.lower() not in {f.lower() for f in found}:
                found.append(fact)
        like = LIKES.search(clause)
        if like:
            how = like["how"].lower().replace("’", "'")
            how = "are " + how if how.startswith(("afraid", "scared", "allergic")) else how
            fact = f"You {how} {like['what'].strip()}"
            if not any("allergic" in f.lower() for f in found) or "allergic" not in how:
                found.append(fact)
    return found[:4]


WHERE = re.compile(r"^\W*(?:(?:hey|yo|luma|luna)\W+)*(?:where(?:'s|’s| is| are| did i (?:leave|put|park|set|stash))|have you seen)\s+(?:my|the|our)\s+(?P<obj>" + OBJECTS + r")\b", re.I)


def _event_day(when, today):
    when = re.sub(r" (?:morning|afternoon|evening|night)$", "", when.lower()) if not when.lower().startswith("this ") else when.lower()
    if when in {"tonight", "today"} or when.startswith("this morning") or when.startswith("this afternoon") or when.startswith("this evening"):
        return today
    if when == "tomorrow":
        return today + timedelta(days=1)
    if when == "this weekend":
        return today + timedelta(days=(5 - today.weekday()) % 7)
    day = WEEKDAYS.index(when.split()[-1])
    ahead = (day - today.weekday()) % 7 or 7
    if when.startswith("next") and ahead < 7:
        ahead += 7 if (day - today.weekday()) % 7 == 0 else 0
    return today + timedelta(days=ahead)


# The same thing said any other way round: "I'm seeing the dentist tomorrow", "tomorrow's my first day at the new job",
# "wish me luck, the audition is tomorrow", "I'm taking the bar exam on Tuesday". (Month test, the lives Luma wasn't built
# on: the evening after, it asked how it went 8 times of 12; of 16 fresh ways of saying it, 3 were noticed.) Only when
# it's theirs (I, we, my, our, me), it hasn't happened yet, it isn't a question, and nothing says it's off.
WHEN = (r"tonight|today|tomorrow(?: (?:morning|afternoon|night))?|this (?:morning|afternoon|evening|weekend)|"
        r"(?:on |next |this )?(?:" + "|".join(WEEKDAYS) + r")(?: (?:morning|afternoon|evening|night))?")
EVENT_ANYWHERE = re.compile(r"\b(?P<event>(?:bar |driving |road |final |job |court |first |doctor'?s? |dentist |eye |vet )?(?:" + EVENTS + r"|toast|graduation|performance|"
                            r"competition|tournament|checkup|check-up|orientation|hearing|ceremony|speech))\b", re.I)
CLOSING = re.compile(r"\bclos(?:e|ing) on (?:the|our|my|a) (?:new )?(?P<what>house|apartment|condo|place|home)\b", re.I)
WHEN_ANYWHERE = re.compile(r"\b(?P<when>" + WHEN + r")\b", re.I)
THEIRS = re.compile(r"\b(?:i|i'm|im|i've|i'll|we|we're|we've|we'll|my|our|me)\b", re.I)
FLYING = re.compile(r"\b(?:fly(?:ing)? out|flying (?:to|home|back)|fly (?:to|home|back))\b", re.I)
NOT_COMING = re.compile(r"\?|\b(?:was|were|had|went|did|got back|came back|watched|saw|yesterday|last (?:night|week|month|time)|ago|already|"
                        r"don'?t|doesn'?t|didn'?t|won'?t|isn'?t|not|no|never|without|cancel\w*|postponed?|called off|reschedul\w*|moved to|pushed|"
                        r"if|maybe|might|should|would|could|every|always|usually|on tv|(?:is|are) on(?! (?:(?:mon|tues|wednes|thurs|fri|satur|sun)day|the \d))|results?|"
                        r"called|texted|emailed|said|told me|"
                        r"skipped|bombed|failed|flunked|passed|aced|nailed|blew|missed|finished|survived|crushed)\b", re.I)


# Said the plain way and still not coming up: a question, something called off, results that came back, a show that's on.
# ("I cancelled my dentist appointment tomorrow" got "Hey, how'd the appointment go?")
CALLED_OFF = re.compile(r"\?\s*$|\b(?:cancel\w*|postponed?|called off|reschedul\w*|results?|(?:show|game|match|race|finale|episode)(?:'s| is| are) on|comes? back|came back|on tv|on tonight|airs?|premieres?)\b", re.I)


def _other_ways(text, now):
    """An event of theirs coming up, said in an order the first pattern doesn't know. One at most."""
    if len(text) > 160 or not THEIRS.search(text) or NOT_COMING.search(text):
        return []
    when = WHEN_ANYWHERE.search(text)
    event = EVENT_ANYWHERE.search(text)
    topic = " ".join(event["event"].lower().split()) if event else ("flight" if FLYING.search(text) else None)
    closing = CLOSING.search(text)
    if closing:
        topic = "closing on the " + closing["what"].lower()
    if not when or not topic:
        return []
    if event and not closing:
        whose = re.search(r"\b(?:my|our)\s+(?P<rel>" + _RELS + r")(?:'s|’s|\s+(?:has|is having|is getting|goes in for|is going in for|has got))\s+"
                          r"(?:(?:a|an|her|his|their|the)\s+)?(?:[a-z]+\s+){0,2}$", text[:event.start()], re.I)
        if whose:
            topic = f"your {whose['rel'].lower()}'s {topic}"   # "my sister's wedding is this Saturday"
    day = _event_day(when["when"], now.date())
    ask_day = day if re.search(r"morning|afternoon", when["when"], re.I) else day + timedelta(days=1)
    ask_at = now.replace(year=ask_day.year, month=ask_day.month, day=ask_day.day, hour=18, minute=0, second=0, microsecond=0)
    return [{"topic": topic, "day": day.isoformat(), "ask_at": ask_at.timestamp()}] if ask_at > now else []


# What to call it when Luma asks. "my mom has surgery on Monday" was kept as "mom has surgery" ("how did the mom has
# surgery go?"). The event itself, with the few words that belong to it ("job interview", "driving test"); when it's
# their person's, "your mom's surgery"; and nothing at all when the words before it say it's over or not happening.
_RELS = (r"best friend|bestie|brother|sister|mom|mother|mama|dad|father|son|daughter|wife|husband|girlfriend|boyfriend|partner|friend|cousin|aunt|auntie|"
         r"uncle|grandma|grandpa|grandmother|grandfather|granny|nana|boss|coworker|roommate|neighbou?r|kid|baby|niece|nephew|fianc[eé]e?|dog|cat|puppy|kitten")
_CORE = re.compile(r"(?:(?:bar|driving|road|final|job|court|first|second|last|doctor'?s?|dentist|eye|vet|math|history|science|chem|bio|physics|spanish|french|"
                   r"english|work|team|school|big|blood|stress|soccer|football|baseball|basketball|hockey|piano|dance|choir|band|sales|client|board|"
                   r"staff|zoom|visa|dmv|therapy|physical|annual|phone|video|panel|group)\s+){0,2}(?:" + EVENTS + r")$", re.I)
_THEIR_PERSONS = re.compile(r"^(?P<rel>" + _RELS + r")(?:'s|’s)?(?:\s+(?:has|is having|is getting|is going in for|goes in for|got|has got|is having her|is having his))?"
                            r"(?:\s+(?:a|an|her|his|their|the|some))?\s*$", re.I)
_OVER = re.compile(r"\b(?:had|was|were|went|did|didn'?t|doesn'?t|don'?t|won'?t|isn'?t|not|no|never|cancel\w*|missed|skipped|bombed|failed|passed|aced|finished)\b", re.I)


_WENT = re.compile(r"\b(?:skipped|bombed|failed|flunked|passed|aced|nailed|blew|missed|finished|survived|crushed|went|was|were|had|did|got (?:through|back from|out of)|"
                   r"came (?:back|home) from|walked out of|just left|is over|is done|are over|are done)\b", re.I)


def _topic(event):
    """("job interview", None), ("surgery", "mom"), or (None, None) when the words say it isn't coming up."""
    event = " ".join(str(event or "").lower().replace("’", "'").split())
    core = _CORE.search(event)
    if not core:
        return event or None, None
    lead = event[:core.start()].strip()
    if not lead:
        return core.group(0), None
    if _OVER.search(lead):
        return None, None
    theirs = _THEIR_PERSONS.match(lead)
    if theirs:
        return core.group(0), theirs["rel"].lower()
    return core.group(0), None


def notice_open_loops(text, now):
    """Things coming up that a friend would ask about afterwards: (topic, event day, ask at)."""
    if not isinstance(text, str):
        return []
    loops = []
    if CALLED_OFF.search(text):
        return []
    for match in OPEN_LOOP.finditer(text):
        event, whose = _topic(match["event"])
        # "I bombed my interview today", "my review went fine today": told how it went, they aren't asked how it went
        if not event or _WENT.search(re.split(r"[.;!?]", text[:match.start()])[-1]) or _WENT.search(match["rest"] or ""):
            continue
        event = f"your {whose}'s {event}" if whose else event
        day = _event_day(match["when"], now.date())
        # Ask the next day around 6pm, or that same evening when it's in the morning or afternoon ("thursday morning": a
        # friend asks thursday night how it went).
        ask_day = day if re.search(r"morning|afternoon", match["when"], re.I) else day + timedelta(days=1)
        ask_at = now.replace(year=ask_day.year, month=ask_day.month, day=ask_day.day, hour=18, minute=0, second=0, microsecond=0)
        if ask_at > now:
            loops.append({"topic": event, "day": day.isoformat(), "ask_at": ask_at.timestamp()})
    return loops[:2] or _other_ways(text, now)


CHECK_INS = [
    "Hey, how'd the {topic} go?",
    "So, the {topic}. How'd it go?",
    "Been wondering: how did the {topic} go?",
]


# After a hard day a friend asks how you're doing, the next evening. Never "yesterday you said you were lonely": just there.
FEELING_CHECK_INS = {
    "safe": ["Hey, I've been thinking about you since we talked. How are you doing today? I'm here, and 988 is there any time too, day or night.",
             "Hey you. I wanted to check on you after the other night. How are you holding up? You can always call or text 988 too."],
    "loss": ["Hey, I've been thinking about you since we talked. How are you holding up today?",
             "Hey. How are you doing today, really? I'm still thinking about what you told me."],
    "lonely": ["Hey, I was just thinking about you. How's your day been?",
               "Hey you. How are you feeling today? Anything good, even something small?"],
    "hard": ["Hey, that sounded like a lot when we talked. How are you feeling today?",
             "Hey, checking on you. Is today any better?"],
}
FEELING_RANK = {"hard": 1, "lonely": 2, "loss": 3, "safe": 4}


def notice_feeling(kind, now):
    """A check-in for tomorrow evening after a hard moment: {'topic': 'feeling:<kind>', 'day', 'ask_at'}, or None.
    Late at night (before 5am) counts as the day before, so 'tomorrow' is this evening."""
    if kind not in FEELING_CHECK_INS:
        return None
    day = (now - timedelta(hours=5)).date()
    ask_day = day + timedelta(days=1)
    ask_at = now.replace(year=ask_day.year, month=ask_day.month, day=ask_day.day, hour=18, minute=0, second=0, microsecond=0)
    return {"topic": "feeling:" + kind, "day": day.isoformat(), "ask_at": ask_at.timestamp()}


def check_in_line(topic, seed):
    if str(topic).startswith("feeling:"):
        lines = FEELING_CHECK_INS.get(topic[8:], FEELING_CHECK_INS["hard"])
        return lines[seed % len(lines)]
    topic = re.sub(r"\b(?:mri|ct|dmv)\b", lambda m: m.group(0).upper(), str(topic))   # "the MRI", never "the mri"
    line = CHECK_INS[seed % len(CHECK_INS)]
    if str(topic).startswith("your "):   # "your mom's surgery": theirs to name, never "the your mom's surgery"
        line = line.replace("the {topic}", "{topic}")
    return line.format(topic=topic)


BIRTHDAY = re.compile(r"(?:\b(?P<who>[A-Z][a-z]+)(?:'s|’s)\s+|\b(?P<my>[Mm]y|[Oo]ur|[Yy]our)\s+(?:(?P<rel>[a-z]+)(?:'s|’s)?\s+)?)"
                      r"(?P<what>birthday|bday|anniversary)\s+is\s+(?:on\s+)?(?:(?:the\s+)?(?P<day2>\d{1,2})(?:st|nd|rd|th)?\s+of\s+(?P<month2>[A-Za-z]+)|"
                      r"(?P<month>[A-Za-z]+)\.?\s+(?P<day>\d{1,2}))")   # "the 21st of October", or "June 3"


def birthdays(memories, today):
    """Upcoming birthdays and anniversaries found in saved memories, soonest first."""
    found = []
    for memory in memories:
        match = BIRTHDAY.search(memory.get("text", ""))
        if not match:
            continue
        said, day = match["month"] or match["month2"], match["day"] or match["day2"]
        month = MONTHS.get(said.lower()) or MONTHS.get(said.lower()[:3])
        try:
            when = date(today.year, month, int(day)) if month else None
        except ValueError:
            when = None
        if not when:
            continue
        if when < today:
            when = when.replace(year=today.year + 1)
        what = "anniversary" if match["what"] == "anniversary" else "birthday"
        if match["who"]:
            whose = match["who"] + "'s"
        elif match["rel"]:
            whose = "your " + match["rel"] + "'s"
        else:
            whose = "your"
        found.append({"whose": whose, "what": what, "date": when, "days": (when - today).days})
    return sorted(found, key=lambda b: b["days"])


def theirs(item):
    """Their own birthday, not someone else's and not an anniversary."""
    return item["whose"] == "your" and item["what"] == "birthday"


def nudge_line(item, name="", gentle=False):
    days = item["days"]
    if theirs(item):
        # Their own birthday isn't a thing to plan a text for. A friend says happy birthday, on the day and not before.
        # gentle: they've been having a hard time, so it's said quietly and asks nothing of them.
        if days:
            return ""
        who = ", " + name if name else ""
        return f"Happy birthday{who}. I'm glad I get to say it." if gentle else f"Happy birthday{who}! I'm glad I get to say it. How do you want to spend it?"
    if days == 0:
        return f"It's {item['whose']} {item['what']} today. Want help with a text or a last-minute plan?"
    when = "tomorrow" if days == 1 else "on " + item["date"].strftime("%A")
    return f"Heads up, {item['whose']} {item['what']} is {when}. Want me to help you plan something?"


def diary_matches(entries, query, limit=4):
    terms = {t for t in re.findall(r"[a-z0-9']+", query.lower()) if len(t) > 2} - {"the", "and", "what", "did", "say", "said", "about", "tell", "you", "told", "mention", "mentioned", "last", "week"}
    scored = []
    for entry in entries:
        words = set(re.findall(r"[a-z0-9']+", (entry.get("you", "") + " " + entry.get("luma", "")).lower()))
        score = len(terms & words)
        if score:
            scored.append((score, entry.get("created", 0), entry))
    return [e for _, _, e in sorted(scored, key=lambda x: (-x[0], -x[1]))[:limit]]


def said_when(ts, now, zone):
    """'2 hours ago', 'this morning', 'yesterday at 6 PM': when they told Luma."""
    if not ts:
        return ""
    gap = now - ts
    if gap < 90: return "just now"
    if gap < 3600: return f"{int(gap // 60)} minutes ago"
    if gap < 6 * 3600: return f"{int(gap // 3600)} hour{'s' if gap >= 7200 else ''} ago"
    then, today = datetime.fromtimestamp(ts, zone), datetime.fromtimestamp(now, zone)
    at = then.strftime("%-I:%M %p").replace(":00 ", " ")
    if then.date() == today.date(): return f"today at {at}"
    if (today.date() - then.date()).days == 1: return f"yesterday at {at}"
    return then.strftime("on %A, %B %-d")


def options_in(reply):
    """A question that offers a few short choices ("Wireless or wired?", "Do you want Marshall, Belkin or Sony?") -> the choices, to tap."""
    if not isinstance(reply, str) or "?" not in reply:
        return []
    last = re.split(r"(?<=[.!?])\s+", reply.strip())[-1]
    if not last.endswith("?") or " or " not in last.lower() or len(last) > 160:
        return []
    body = re.sub(r"^(?:so |and |also |okay[, ]+|ok[, ]+)?(?:do you (?:want|prefer|need)|would you (?:like|rather|prefer)|should i (?:go with|do|use|pick|get)|"
                  r"want (?:me to )?|which (?:one|do you want)[:,]?|you want|prefer|is it|are you thinking)\s*", "", last[:-1], flags=re.I)
    parts = [p.strip(" ,.:;\"'“”") for p in re.split(r",\s*(?:or\s+)?|\s+or\s+", body) if p.strip(" ,.:;")]
    parts = [re.sub(r"^(?:the |a |an )", "", p, flags=re.I) for p in parts]
    if not 2 <= len(parts) <= 4 or any(len(p.split()) > 5 or not p for p in parts):
        return []
    return [p[0].upper() + p[1:] for p in parts]
