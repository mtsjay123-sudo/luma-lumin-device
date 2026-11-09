"""What a memory is about, so Luma files it and finds it again, however long ago it was said: you, people, places
(where things are), dates, health, likes, goals, notes. The same buckets the Memory page shows (memTag in
desktop.js), and the same order: the first that fits wins (a date before a place: "your appointment is on Friday").

recall() ranks memories for a question without a model: words that matter (not "my", "the", "is"), rare words
counting more than common ones, plural or not, and a lift for the right bucket ("where" looks in places first,
"when" in dates, "who" in people). Every memory is searched, never just the newest."""
from __future__ import annotations

import math
import re

CATEGORIES = ("you", "people", "places", "dates", "health", "likes", "goals", "notes")

_RULES = [
    ("goals", re.compile(r"^your goal|\bmy goal\b|\bi want to\b|\bi'm trying to\b|\byou(?:'re| are) trying to\b|\byou want to\b", re.I)),
    ("dates", re.compile(r"birthday|anniversary|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d|\b\d{1,2}/\d{1,2}\b|"
                         r"\b(?:mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|saturdays?|sundays?)\b", re.I)),
    ("places", re.compile(r"^(?:your|the|my) .+ (?:is|are) (?:on|in|at|by|under|inside|next to|behind|near|with)\b|"
                          r"\b(?:left|put|keep|kept|parked|stored|hid|hidden)\b.*\b(?:in|on|at|under|behind|inside|next to)\b", re.I)),
    ("health", re.compile(r"\b(?:allerg\w*|vegetarian|vegan|gluten|lactose|diabetic|medication|meds|asthma|doctor|dentist|therapist|pills?|"
                          r"blood pressure|inhaler)\b", re.I)),
    ("likes", re.compile(r"\b(?:love|loves|like|likes|hate|hates|favorite|favourite|prefer|prefers|can't stand)\b|^you're into\b", re.I)),
    ("people", re.compile(r"\b(?:mom|mother|dad|father|sister|brother|boyfriend|girlfriend|wife|husband|friend|bestie|roommate|boss|son|"
                          r"daughter|grandma|grandpa|aunt|uncle|cousin|partner|kids?|dating|married|engaged|neighbou?r|coworker)\b", re.I)),
    ("you", re.compile(r"^(?:your name is|you're an? |you work|you live|you're from|you study|you go to)", re.I)),
]

# What a question is looking for, by the bucket its answer is in.
_INTENTS = [
    ("places", re.compile(r"\bwhere(?:'s|s| is| are| did| do| was| were)?\b|\b(?:find|found|lost|misplaced)\b", re.I)),
    ("dates", re.compile(r"\bwhen(?:'s|s| is| was)?\b|\bbirthday|\banniversary|\bwhat (?:day|date)\b", re.I)),
    ("people", re.compile(r"\bwho(?:'s|s| is| was)?\b", re.I)),
    ("likes", re.compile(r"\bfavou?rite\b|\bwhat do i (?:like|love)\b|\bwhat am i into\b", re.I)),
    ("health", re.compile(r"\ballerg\w*|\bmeds?\b|\bmedication\b|\bdoctor\b|\bdentist\b", re.I)),
    ("goals", re.compile(r"\bgoals?\b|\btrying to\b", re.I)),
]

STOP = set("""a an the and or but if of to in on at by for with from about as into onto off up down out over under is are was were be
been being am do does did doing have has had having i me my mine myself you your yours yourself we our us they them their
it its this that these those what whats where wheres when whens who whos why how which whose can could would should will
shall may might must just so very really too also not no yes yeah ok okay hey luma please pls tell remind remember again
know knew think thought said say says put left get got go went""".split())


_ANY_RULE = re.compile("|".join(f"(?:{rule.pattern})" for _, rule in _RULES), re.I)   # one look, before the seven


def category(text, source=""):
    """The bucket a memory goes in."""
    if source == "grill":
        return "you"
    t = str(text or "")
    if _ANY_RULE.search(t):
        for name, rule in _RULES:
            if rule.search(t):
                return name
    if source in ("signup", "about_you"):
        return "you"
    return "notes"


def intents(question):
    q = str(question or "")
    return {name for name, rule in _INTENTS if rule.search(q)}


def words(text):
    """The words that matter, plural or not, possessive or not: "keys" and "key's" are "key"."""
    out = set()
    for w in re.findall(r"[a-z0-9']+", str(text or "").lower()):
        w = w.strip("'")
        if w.endswith("'s"):
            w = w[:-2]
        if len(w) > 3 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        if len(w) >= 2 and w not in STOP:
            out.add(w)
    return out


def recall(question, memories, limit=5):
    """The memories that answer this question best, best first. Only ones that share a word that matters with it."""
    terms = words(question)
    if not terms or not memories:
        return []
    bags = [(m, words(m.get("text", ""))) for m in memories]
    count = len(bags)
    df = {}
    for _, bag in bags:
        for w in bag & terms:
            df[w] = df.get(w, 0) + 1
    wanted = intents(question)
    scored = []
    for m, bag in bags:
        shared = bag & terms
        if not shared:
            continue
        score = 0.0
        for w in sorted(shared):  # one at a time, in one order: the same words add up to the same number on every computer
            score += math.log(1 + count / df[w])  # (sum() rounds differently from one Python to the next)
        if wanted and (m.get("category") or category(m.get("text", ""), m.get("source", ""))) in wanted:
            score += 1.5
        scored.append((score, m.get("created") or 0, m))
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
    return [m for _, _, m in scored[:limit]]
