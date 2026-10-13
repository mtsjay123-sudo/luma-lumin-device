"""Luma's mind: who you are, how it feels right now, and how it thinks before it answers.

- About you: what you told Luma when you set it up (birthday, your people, what
  you're into). It's in every conversation, so Luma always knows who it's
  talking to. Encrypted on this computer.
- Mood: a running feeling that shifts with what you say (happy for you,
  worried about you, playful) and colors how Luma talks. It's simulated, and
  Luma never pretends to be human.
- Thinking: before a reply that matters (advice, feelings, a decision), Luma
  thinks it over privately first. Asked to "think hard", it works the question
  through several passes (understand it, look at it three ways, check itself)
  before answering, like layers in a network.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
TEXT_FIELDS = {"pronouns": 30, "home": 80, "work": 120, "interests": 300, "goals": 300, "food": 160, "music": 160, "schedule": 200, "notes": 600}
RELATIONS = 40


def _day(value):
    """'2001-10-13', '10-13' or '' → ('10-13', year or None). Anything else is a mistake."""
    value = str(value or "").strip()
    if not value:
        return None, None
    m = re.fullmatch(r"(?:(\d{4})-)?(\d{1,2})-(\d{1,2})", value)
    if not m:
        raise ValueError("Use a date like 2001-10-13.")
    year, month, day = (int(m[1]) if m[1] else None), int(m[2]), int(m[3])
    date(year or 2000, month, day)  # raises on 02-30
    if year and not 1900 <= year <= date.today().year:
        raise ValueError("That birth year doesn't look right.")
    return f"{month:02d}-{day:02d}", year


def _say_day(mmdd):
    month, day = map(int, mmdd.split("-"))
    return f"{MONTH_NAMES[month - 1]} {day}"


def clean_about(data):
    if not isinstance(data, dict):
        raise ValueError("Tell me about you in the form.")
    out = {}
    for key, limit in TEXT_FIELDS.items():
        text = " ".join(str(data.get(key) or "").split())
        if len(text) > limit:
            raise ValueError(f"Keep {key} under {limit} characters.")
        if any(ord(c) < 32 for c in text):
            raise ValueError("Use plain text.")
        out[key] = text
    out["birthday"], out["birth_year"] = _day(data.get("birthday"))
    people = []
    for person in (data.get("people") or [])[:20]:
        if not isinstance(person, dict):
            continue
        name = " ".join(str(person.get("name") or "").split())[:40]
        if not name:
            continue
        relation = " ".join(str(person.get("relation") or "").split()).lower()[:RELATIONS]
        bday, _ = _day(person.get("birthday"))
        people.append({"name": name, "relation": relation, "birthday": bday})
    out["people"] = people
    out["asked"] = True
    return out


def about_summary(about, name=""):
    """One compact paragraph the model reads every turn."""
    if not about:
        return ""
    bits = []
    if name: bits.append(f"name {name}")
    if about.get("pronouns"): bits.append(f"pronouns {about['pronouns']}")
    if about.get("birthday"):
        bits.append("birthday " + _say_day(about["birthday"]) + (f" {about['birth_year']}" if about.get("birth_year") else ""))
    for key, label in (("home", "lives in"), ("work", "work/school"), ("interests", "into"), ("goals", "goals"), ("food", "food"),
                       ("music", "music"), ("schedule", "routine"), ("notes", "also")):
        if about.get(key): bits.append(f"{label}: {about[key]}")
    people = [p["name"] + (f" ({p['relation']})" if p.get("relation") else "") + (f", birthday {_say_day(p['birthday'])}" if p.get("birthday") else "")
              for p in about.get("people", [])]
    if people: bits.append("their people: " + "; ".join(people))
    return "; ".join(bits)


def birthday_memories(about):
    """Birthdays as sentences Luma's reminders already understand."""
    lines = []
    if about.get("birthday"):
        lines.append("My birthday is " + _say_day(about["birthday"]))
    for p in about.get("people", []):
        if p.get("birthday") and re.fullmatch(r"[A-Z][a-z]+", p["name"].split()[0] or ""):
            lines.append(f"{p['name'].split()[0]}'s birthday is {_say_day(p['birthday'])}")
    return lines


# -- mood ------------------------------------------------------------------------------------------
FEELINGS = [
    ("worried about them", re.compile(r"\b(?:sad|depressed|anxious|anxiety|stressed|overwhelmed|scared|afraid|lonely|cry(?:ing)?|hurt|sick|panic|exhausted|burn(?:ed|t) out|broke up|breakup|lost my|died|passed away|rough day|bad day|hate my life)\b", re.I)),
    ("so happy for them", re.compile(r"\b(?:got the job|i got in|accepted|promoted|engaged|we won|i won|passed|nailed it|good news|so happy|excited|let'?s go+|finally did)\b", re.I)),
    ("playful", re.compile(r"\b(?:lol|lmao|haha+|😂|🤣|jk|bruh|roast me)\b", re.I)),
    ("curious", re.compile(r"\b(?:what if|why do|how come|i wonder|idea|imagine|thinking about starting|should i build)\b", re.I)),
    ("frustrated for them", re.compile(r"\b(?:annoyed|pissed|so mad|angry|unfair|ugh+|fed up)\b", re.I)),
]


def next_mood(previous, text, now):
    """How Luma feels after hearing this. Strong feelings linger a couple of hours, then settle back to warm."""
    for feeling, pattern in FEELINGS:
        if pattern.search(text):
            return {"feeling": feeling, "about": text.strip()[:80], "at": now}
    if previous and now - previous.get("at", 0) < 2 * 3600:
        return previous
    return {"feeling": "warm", "about": "", "at": now}


def mood_line(mood):
    if not mood or mood.get("feeling") == "warm":
        return "Your mood right now: warm and easygoing."
    return f"Your mood right now: {mood['feeling']} (after they said: \"{mood['about']}\"). Let it color your tone."


# -- thinking ----------------------------------------------------------------------------------
MATTERS = re.compile(r"\b(?:should i|what do you think|what would you do|advice|help me decide|is it worth|feel(?:ing)?|stressed|worried|anxious|sad|"
                     r"relationship|breakup|broke up|my (?:mom|dad|girlfriend|boyfriend|wife|husband|boss|friend)|career|quit|move to|confused|lonely)\b", re.I)
DEEP = re.compile(r"\b(?:think (?:hard|deep(?:ly)?|it through|carefully)|really think|deep think|take your time|go deep|weigh (?:it|this|the options)|pros and cons)\b", re.I)


def reflect_prompt(text, about_line, mood):
    return (("What you know about them (data): " + about_line + "\n" if about_line else "")
            + mood_line(mood) + "\n"
            + f"They just said: {text}\n"
            "Before you reply, think privately (they won't see this). In three short lines: what they're really feeling or asking, "
            "what you know about them that matters here, and your honest take as their friend.")


DEEP_PASSES = [
    ("Understanding it", "Restate what they're really asking and what a great answer would need. List the facts you have and what's unknown. Under 80 words."),
    ("Looking at it three ways", "Answer three ways in under 120 words total: 1) the practical view, 2) the view of someone who cares about how they feel, 3) a contrarian who thinks the obvious answer is wrong."),
    ("Checking myself", "Be a tough critic of the three views: what's wrong, made up, or missing? What would you change? Under 80 words."),
]


def deep_prompt(step, text, about_line, notes):
    return (("What you know about them (data): " + about_line + "\n" if about_line else "")
            + f"Their question: {text}\n"
            + ("Your notes so far:\n" + "\n".join(notes) + "\n" if notes else "")
            + DEEP_PASSES[step][1])


def final_prompt(text, about_line, notes, mood):
    return (("What you know about them (data): " + about_line + "\n" if about_line else "")
            + mood_line(mood) + "\n"
            + f"Their question: {text}\nYour thinking so far (private):\n" + "\n".join(notes)
            + "\nNow answer them like a smart friend who thought hard: lead with your honest recommendation, the one or two reasons that matter most, "
              "and what you'd watch out for. Plain text, no lists unless they're needed, under 160 words. Never invent facts.")


def days_together(first_seen, now):
    return max(0, int((now - first_seen) // 86400)) if first_seen else 0


def today_iso(clock, zone):
    return datetime.fromtimestamp(clock(), zone).date().isoformat()


def dumps(value):
    return json.dumps(value, ensure_ascii=False)
