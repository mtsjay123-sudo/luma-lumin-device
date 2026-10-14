"""Emails for later, and emails said in one breath.

"Email Sam tomorrow at 9 saying the deck is ready", "schedule me an email for
Friday reminding me to call the bank", or just "schedule me an email". Luma
picks out who, what and when, asks only for what's missing, writes it, and
shows the exact words, address and time. Only Allow schedules it; at that time
those same words go out and nothing else. "Cancel my scheduled email" stops it.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

ADDRESS = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
EMAIL = r"e-?mails?"
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY = r"(?:mon|tues?|wed(?:nes)?|thu(?:rs)?|fri|sat(?:ur)?|sun)(?:day)?"
NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "ten": 10, "fifteen": 15, "twenty": 20,
                "thirty": 30, "forty five": 45, "few": 3, "couple": 2, "couple of": 2, "half an": 0.5, "half a": 0.5}
PART = {"morning": 9, "afternoon": 14, "evening": 18, "night": 20, "tonight": 20, "noon": 12, "midnight": 0}

# Typos a fast typist or a speech-to-text pass makes in the words that decide what to do.
_SCHEDULE = re.compile(r"\bs(?:c?h|k)?c?h?e?[iy]?d+(?:u|j|y)?[aeiouy]?[lk]+[eu]?l?e?\b", re.I)
TYPOS = [
    (re.compile(r"\b(?:emial|emali|eamil|emal|emaill|emai|eemail|ermail|e-mail)(s?)\b", re.I), r"email\1"),
    (re.compile(r"\b(?:tmrw|tmr|tmrrw|tomorow|tommorow|tommorrow|tomorroww|2morrow|2moro|tomoro|tmorrow)\b", re.I), "tomorrow"),
    (re.compile(r"\b(?:tonite|2nite)\b", re.I), "tonight"),
    (re.compile(r"\b(?:knews|newz|nws|neews|nwes|nuews)\b", re.I), "news"),
]


def _near_schedule(word):
    """'shceudle', 'scheudle', 'schedual': close enough to 'schedule', and not a real word like 'saddle'."""
    from difflib import SequenceMatcher
    w = word.lower()
    if w in {"schedule", "scheduled", "schedules", "scheduling", "shuttle", "saddle", "sidled", "shudder", "sledged", "shoulder", "sundial"}: return False
    return "d" in w and "l" in w and w[:2] in {"sc", "sh", "sk", "sd"} and SequenceMatcher(None, w, "schedule").ratio() >= 0.74


def fix_typos(text):
    """'shceydke me an emial tmrw' -> 'schedule me an email tomorrow'. Only these few deciding words are touched."""
    text = str(text or "")
    text = _SCHEDULE.sub(lambda m: m.group(0) if m.group(0).lower() in {"schedule", "sidle", "sidled"} else "schedule", text)
    text = re.sub(r"\bs[a-z]{5,9}\b", lambda m: "schedule" if _near_schedule(m.group(0)) else m.group(0), text, flags=re.I)
    for pattern, fixed in TYPOS:
        text = pattern.sub(fixed, text)
    return text


SCHEDULE_ASK = re.compile(rf"\b(?:schedule|set up|queue(?: up)?|line up)\s+(?:me\s+|up\s+|for me\s+)?(?:an?\s+|the\s+|that\s+|this\s+|my\s+|some\s+|these\s+|those\s+)?{EMAIL}\b"
                          rf"|\b{EMAIL}\s+(?:for|to go out|to send)\s+(?:later|tomorrow|tonight)\b|\bschedule (?:it|that|this) (?:to go out|to send|for)\b"
                          rf"|\b(?:remind|ping|nudge) me (?:by|via|over|with an?|in an?|through) {EMAIL}\b", re.I)
SEND_ASK = re.compile(rf"\b(?:send|write|shoot|drop)\s+(?:me|myself|[a-z][\w'.-]*(?:\s+[a-z][\w'.-]*)?|[\w.+-]+@[\w.-]+)?\s*(?:an?\s+|the\s+)?{EMAIL}\b"
                      rf"|^\W*(?:please\s+)?e-?mail\s+(?!(?:me|my|us)\s+(?:back|address)|address|account|inbox|password)(?:to\s+)?\S", re.I)
SAYS = re.compile(r"\b(?:saying|that says|to say|and say|which says|telling (?:them|him|her|me)(?: that)?|that tells (?:them|him|her|me)|"
                  r"asking (?:them|him|her)(?: to| if| whether)?|letting (?:them|him|her) know(?: that)?|let (?:them|him|her) know(?: that)?|"
                  r"reminding me(?: to| about| that)?|to remind me(?: to| about| that)?|remind me(?: to| about| that)?|about|re|regarding|with the subject)\s*[:,-]?\s+(?P<what>.+)$"
                  r"|:\s*(?P<what2>.+)$", re.I | re.S)
REMINDER = re.compile(r"\bremind(?:ing|er)?\b", re.I)
NOT_A_NAME = {"me", "myself", "him", "her", "them", "it", "about", "saying", "that", "tomorrow", "tonight", "today", "later", "at", "in", "on", "for",
              "to", "a", "an", "the", "this", "and", "so", "but", "now", "please", "out", "back", "reminding", "telling", "asking", "letting",
              "with", "when", "next", "every", "each", "around", "by", "before", "after", "morning", "evening", "afternoon", "noon", "real",
              "schedule", "send", "write", "email", "emails", "mail", "be", "is", "go", "goes", "going", "something", "someone", "anyone", "everyone",
              "can", "could", "would", "will", "should", "you", "your", "do", "does", "even", "just", "really", "actually", "also", "what", "how",
              "why", "who", "where", "texts", "text", "people", "somebody", "all", "everybody", "us", "we", "i", "my"}
NEVERMIND = re.compile(r"^\W*(?:never ?mind|nvm|forget (?:it|that|about it)|cancel(?: (?:it|that))?|no(?:pe)?(?: thanks)?|stop|drop it|don'?t)\W*$", re.I)
CANCEL_LATER = re.compile(rf"\b(?:cancel|stop|delete|unschedule|call off|don'?t send)\b.{{0,30}}\bscheduled {EMAIL}\b"
                          rf"|\b(?:cancel|unschedule)\s+(?:the|that|my)\s+(?:\w+\s+){{0,2}}{EMAIL}\b", re.I)
LIST_LATER = re.compile(rf"\b(?:what|which|any|show|list|see)\b.{{0,30}}\bscheduled {EMAIL}\b|\b{EMAIL}\s+(?:are|do i have|have i got)\s+scheduled\b|^\W*(?:my\s+)?scheduled {EMAIL}\W*$", re.I)


NEW_TOPIC = re.compile(r"^\W*(?:what|whats|what's|how|who|why|where|which|is|are|was|does|do|did|can|could|would|will|should|tell me|show me|"
                       r"remind|text|call|find|search|look|check|open|play|buy|order|book|plan|make|set|turn|catch me up|news|weather|hey|yo|hi|hello|thanks?)\b", re.I)


def wants(text):
    """'schedule me an email', 'email Sam tomorrow at 9 saying …', 'send an email to x@y.com saying …'."""
    text = fix_typos(text)
    if re.search(r"\b(?:every|each)\s+(?:morning|day|evening|night|hour|week)\b|\b(?:check|read|go through|any|new|unread|did i get)\b[^.?!]{0,20}\be-?mails?\b", text, re.I):
        return False
    if SCHEDULE_ASK.search(text):
        return True
    return bool(SEND_ASK.search(text)) and bool(SAYS.search(text) or TIME_SAID.search(text))


def _hour(h, minute, meridiem, part):
    h = int(h)
    meridiem = (meridiem or "").replace(".", "").lower()
    if meridiem == "pm" and h < 12: h += 12
    elif meridiem == "am" and h == 12: h = 0
    elif not meridiem:
        if part in {"evening", "night", "tonight", "afternoon"} and h < 12: h += 12
        elif part is None and 1 <= h <= 6: h += 12  # "at 5" means 5 in the afternoon
    return h, int(minute or 0)


TIME_SAID = re.compile(rf"\b(?:today|tonight|tomorrow|later(?: today| on)?|next week|this (?:morning|afternoon|evening|weekend)|in the (?:morning|afternoon|evening)|"
                       rf"(?:on |this |next ){DAY}|{DAY} (?:morning|afternoon|evening|night|at)|(?:at|@|around)\s*\d{{1,2}}(?::\d{{2}})?|\d{{1,2}}(?::\d{{2}})?\s*(?:am|pm|a\.m\.|p\.m\.)|"
                       r"noon|midnight|in\s+(?:\d{1,3}|an?|one|two|three|five|ten|fifteen|twenty|thirty|few|couple(?: of)?|half an?)\s*(?:min(?:ute)?s?|h(?:ou)?rs?|hours?|days?|weeks?))\b", re.I)


def when(text, now, zone):
    """When it should go out, as a timestamp, plus the words that said so. (None, []) when they didn't say."""
    text = fix_typos(text).lower()
    m = re.search(r"\bin\s+(?P<n>\d{1,3}|an?|one|two|three|four|five|six|ten|fifteen|twenty|thirty|forty five|few|couple(?: of)?|half an?)\s*"
                  r"(?P<unit>min(?:ute)?s?|h(?:ou)?rs?|hours?|days?|weeks?)\b", text)
    if m:
        n = float(m["n"]) if m["n"].isdigit() else NUMBER_WORDS.get(m["n"], 1)
        unit = m["unit"]
        seconds = 60 if unit.startswith("m") else 86400 if unit.startswith("d") else 7 * 86400 if unit.startswith("w") else 3600
        return now + n * seconds, [m.span()]
    local = datetime.fromtimestamp(now, zone)
    date, part, spans = local.date(), None, []
    roll = timedelta(days=1)  # a time that already passed today means tomorrow
    d = re.search(rf"\b(?:(?P<rel>today|tonight|tomorrow)(?:\s+(?P<part1>morning|afternoon|evening|night))?|(?P<later>later(?: today| on)?)|(?P<nextweek>next week)|"
                  rf"this (?P<part2>morning|afternoon|evening|weekend)|in the (?P<part3>morning|afternoon|evening)|"
                  rf"(?:(?P<which>on|this|next)\s+)?(?P<day>{DAY})(?:\s+(?P<part4>morning|afternoon|evening|night))?)\b", text)
    if d and (d["day"] and not d["which"] and not d["part4"] and not re.search(r"\s+at\b", text[d.end():d.end() + 4])):
        d = None if len(d["day"]) < 6 else d  # "sat" or "sun" alone aren't days ("I sat down"); "Saturday" is
    if d:
        spans.append(d.span())
        if d["later"]:
            return now + 3 * 3600, spans
        if d["rel"] == "tomorrow": date, roll = date + timedelta(days=1), timedelta(0)
        elif d["rel"] == "tonight": part = "tonight"
        elif d["rel"] == "today": roll = timedelta(0)
        elif d["nextweek"]: date, roll = date + timedelta(days=7 - local.weekday()), timedelta(0)
        elif d["part2"] == "weekend": date, part, roll = date + timedelta(days=(5 - local.weekday()) % 7), "morning", timedelta(days=7)
        elif d["day"]:
            want = next(i for i, name in enumerate(WEEKDAYS) if name.startswith(d["day"][:3]))
            ahead = (want - local.weekday()) % 7
            if ahead == 0 and d["which"] == "next": ahead = 7
            date, roll = date + timedelta(days=ahead), timedelta(days=7)
        part = part or d["part1"] or d["part2"] or d["part3"] or d["part4"]
    t = re.search(r"\b(?:at|@|around|by)\s*(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>am|pm|a\.m\.|p\.m\.)?(?![\d:])"
                  r"|\b(?P<h2>\d{1,2})(?::(?P<m2>\d{2}))?\s*(?P<ap2>am|pm|a\.m\.|p\.m\.)|\b(?P<word>noon|midnight)\b", text)
    if t:
        spans.append(t.span())
        if t["word"]:
            hour, minute = PART[t["word"]], 0
        else:
            hour, minute = _hour(t["h"] or t["h2"], t["m"] or t["m2"], t["ap"] or t["ap2"], part)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None, []
        evening_guess = not t["word"] and not (t["ap"] or t["ap2"]) and not part and hour < 12
    elif part:
        hour, minute, evening_guess = PART[part], 0, False
    elif d:
        hour, minute, evening_guess = 9, 0, False
    else:
        return None, []
    at = datetime(date.year, date.month, date.day, hour, minute, tzinfo=zone)
    if t and evening_guess and at.timestamp() <= now < (at + timedelta(hours=12)).timestamp():
        at += timedelta(hours=12)  # "at 8" said at 3pm means tonight at 8
    if at.timestamp() <= now and roll:
        at += roll
    return at.timestamp(), spans


def _strip(text, spans):
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + " " + text[end:]
    return text


def _clean_what(what):
    what = re.sub(r"\s+", " ", what or "").strip(" \t,.;:-")
    what = re.sub(r"\b(?:please|thanks|thank you|pls|plz)\W*$", "", what, flags=re.I).strip(" ,.;:-")
    what = re.sub(r"^(?:(?:by|via|over|through|with an?|in an?)\s+e-?mails?\s*)?(?:that|to)?\s*", "", what, flags=re.I)
    return what[:600]


def parse(text, now, zone, answering=None):
    """Who it's to, what it says and when it goes, from what they said. answering: the slots asked for last time."""
    fixed = fix_typos(text).strip()
    out = {}
    at, spans = when(fixed, now, zone)
    if at is not None:
        out["when"] = at
    address = ADDRESS.search(fixed)
    if address:
        out["to"], out["to_kind"] = address.group(0), "address"
        spans = spans + [address.span()]
    body_part = _strip(fixed, spans)
    if "to" not in out:
        me = re.search(rf"\b(?:to|for)\s+(?:me|myself)\b|\b{EMAIL}\s+(?:me|myself)\b|\b(?:schedule|send|write|shoot|drop)\s+(?:me|myself)\s+(?:an?\s+)?{EMAIL}\b"
                       r"|\bremind(?:ing)? me\b|^\W*(?:to\s+)?(?:me|myself)\b", body_part, re.I)
        name = None
        if not me:
            for pattern in (rf"\b{EMAIL}\s+to\s+(?P<n>my\s+[a-z]+|[A-Za-z][\w'.-]*(?:\s+[A-Z][\w'.-]*)?)",
                            rf"\b(?:send|write|shoot|drop)\s+(?P<n>my\s+[a-z]+|[A-Za-z][\w'.-]*(?:\s+[A-Z][\w'.-]*)?)\s+(?:an?\s+)?{EMAIL}\b",
                            rf"^\W*(?:please\s+)?e-?mail\s+(?P<n>my\s+[a-z]+|[A-Za-z][\w'.-]*(?:\s+[A-Z][\w'.-]*)?)",
                            rf"\b(?:schedule|set up)\s+(?:an?\s+)?{EMAIL}\s+(?:to|for)\s+(?P<n>my\s+[a-z]+|[A-Za-z][\w'.-]*(?:\s+[A-Z][\w'.-]*)?)"):
                hit = re.search(pattern, body_part, re.I)
                if hit:
                    words = hit["n"].split()
                    while words and words[-1].lower() in NOT_A_NAME: words.pop()
                    if words and words[0].lower() not in NOT_A_NAME:
                        name = " ".join(words)
                        break
            if not name and answering and "to" in answering.get("missing", ()):
                bare = re.match(r"^\W*(?:to\s+|it'?s (?:to|for)\s+|send it to\s+)?(?P<n>my\s+[a-z]+|[A-Z][\w'.-]*(?:\s+[A-Z][\w'.-]*)?)\b", body_part)
                if bare and bare["n"].split()[0].lower() not in NOT_A_NAME:
                    name = bare["n"]
        if me:
            out["to"], out["to_kind"] = "me", "me"
        elif name:
            out["to"], out["to_kind"] = name.strip(), "name"
    said = SAYS.search(body_part)
    if said:
        what = _clean_what(said["what"] or said["what2"])
        if what and not re.fullmatch(r"(?:it|that|this|something|an? e-?mail)", what, re.I):
            out["what"] = what
            out["reminder"] = bool(REMINDER.search(said.group(0)))
    if "what" not in out and answering and "what" in answering.get("missing", ()):
        rest = body_part
        rest = re.sub(rf"^\W*(?:(?:to|for)\s+(?:me|myself)|me|myself)\b|\b(?:it should say|make it say|say|tell (?:them|him|her))\b", " ", rest, flags=re.I)
        if out.get("to_kind") == "name": rest = re.sub(rf"^\W*(?:to\s+)?{re.escape(out['to'])}\b", " ", rest, flags=re.I)
        rest = _clean_what(re.sub(r"^\W*(?:and|then|also)\b", " ", rest, flags=re.I))
        if len(rest) >= 3 and not text.rstrip().endswith("?") and not re.match(r"(?:what|how|why|who|where|can you|could you|tell me about|is it|are you|do you)\b", rest, re.I):
            out["what"] = rest
            out["reminder"] = bool(REMINDER.search(text))
    if REMINDER.search(fixed) and out.get("to_kind") == "me":
        out["reminder"] = True
    return out


def subject(what, reminder=False):
    words = re.sub(r"\s+", " ", what or "").strip(" .!?")
    if reminder:
        return ("Reminder: " + words)[:90]
    first = re.split(r"(?<=[.!?])\s", words, maxsplit=1)[0]
    first = first if len(first) <= 70 else first[:67].rsplit(" ", 1)[0] + "…"
    return (first[:1].upper() + first[1:]) if first else "A quick note"
