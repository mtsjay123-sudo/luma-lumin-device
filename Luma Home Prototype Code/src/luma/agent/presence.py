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
FACT_PATTERNS = [
    (r"\b(?:my|our)\s+(?:[a-z']+\s+){0,2}(?:birthday|bday|anniversary)\s+is\s+" + DATE, I),
    (r"\b[A-Z][a-z]+(?:'s|’s)\s+(?:birthday|bday)\s+is\s+" + DATE, 0),
    (r"\b(?:[Mm]y|[Oo]ur)\s+(?:girlfriend|boyfriend|wife|husband|partner|mom|mother|dad|father|sister|brother|son|daughter|best friend|boss|dog|cat)(?:'s)?\s+(?:name\s+)?is\s+(?:named\s+|called\s+)?[A-Z][a-z]+\b", 0),
    (r"\bI(?:'m| am)\s+allergic\s+to\s+[a-z]+(?:(?:,\s*|\s+and\s+|\s+or\s+)[a-z]+){0,3}", I),
    (r"\bI(?:'m| am)\s+(?:vegetarian|vegan|pescatarian|gluten[- ]free|lactose intolerant|diabetic|pregnant)\b", I),
    (r"\bI\s+(?:work|go to school)\s+(?:at|for)\s+[A-Z][\w&']*(?:\s+[A-Z][\w&']*){0,4}", 0),
    (r"\bmy\s+favou?rite\s+[a-z ]{2,20}?\s+is\s+[\w' ]{2,40}?(?=$|[.,!;]|\s+(?:and|but|btw|lol)\b)", I),
]
SKIP_FACTS = re.compile(r"\?|^\s*(?:(?:hey|ok|okay)\s+)?(?:luma[,\s]+)?(?:remember|remind|recall|text|message|tell|let|search|look up|find|what|who|when|where|why|how|can you|could you|would you|please)\b"
                        r"|\b(?:text|message|tell|let)\s+(?:my\s+|our\s+)?\w+\s+(?:that|to|know)\b", re.I)

EVENTS = r"(?:job\s+)?interview|exam|test|quiz|final|midterm|appointment|doctor|dentist|surgery|date|game|match|tryouts?|recital|presentation|pitch|demo|meeting|flight|trip|first day|audition|court date|surgery|race|show"
OPEN_LOOP = re.compile(
    r"\b(?:(?:I|we)(?:'ve| have)?\s+(?:got\s+)?(?:a|an|my|our)|my|our|there's\s+(?:a|an|my))\s+(?P<event>(?:[a-z]+\s+){0,2}?(?:" + EVENTS + r"))\b"
    r"(?P<rest>[^.?!]{0,40}?)\b(?P<when>tonight|today|tomorrow|this (?:morning|afternoon|evening|weekend)|on (?:" + "|".join(WEEKDAYS) + r")|(?:next|this) (?:" + "|".join(WEEKDAYS) + r"))\b", re.I)


def notice_facts(text):
    """Facts the owner stated about themselves or their people, as they said them."""
    if not isinstance(text, str) or SKIP_FACTS.search(text):
        return []
    found = []
    for pattern, flags in FACT_PATTERNS:
        for match in re.finditer(pattern, text, flags):
            fact = " ".join(match.group(0).split()).strip(" ,.")
            if fact and fact.lower() not in {f.lower() for f in found}:
                found.append(fact[0].upper() + fact[1:])
    return found[:3]


def _event_day(when, today):
    when = when.lower()
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


def notice_open_loops(text, now):
    """Things coming up that a friend would ask about afterwards: (topic, event day, ask at)."""
    if not isinstance(text, str):
        return []
    loops = []
    for match in OPEN_LOOP.finditer(text):
        event = " ".join(match["event"].lower().split())
        day = _event_day(match["when"], now.date())
        # Ask the next day around 6pm, or the same evening for "today/tonight" morning events.
        ask_day = day + timedelta(days=1) if match["when"].lower() not in {"this morning", "this afternoon"} else day
        ask_at = now.replace(year=ask_day.year, month=ask_day.month, day=ask_day.day, hour=18, minute=0, second=0, microsecond=0)
        if ask_at > now:
            loops.append({"topic": event, "day": day.isoformat(), "ask_at": ask_at.timestamp()})
    return loops[:2]


CHECK_INS = [
    "Hey, how'd the {topic} go?",
    "So, the {topic}. How'd it go?",
    "Been wondering: how did the {topic} go?",
]


def check_in_line(topic, seed):
    return CHECK_INS[seed % len(CHECK_INS)].format(topic=topic)


BIRTHDAY = re.compile(r"(?:\b(?P<who>[A-Z][a-z]+)(?:'s|’s)\s+|\b(?P<my>[Mm]y|[Oo]ur)\s+(?:(?P<rel>[a-z]+)(?:'s|’s)?\s+)?)"
                      r"(?P<what>birthday|bday|anniversary)\s+is\s+(?:on\s+)?(?P<month>[A-Za-z]+)\.?\s+(?P<day>\d{1,2})")


def birthdays(memories, today):
    """Upcoming birthdays and anniversaries found in saved memories, soonest first."""
    found = []
    for memory in memories:
        match = BIRTHDAY.search(memory.get("text", ""))
        if not match:
            continue
        month = MONTHS.get(match["month"].lower()) or MONTHS.get(match["month"].lower()[:3])
        try:
            when = date(today.year, month, int(match["day"])) if month else None
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


def nudge_line(item):
    days = item["days"]
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
