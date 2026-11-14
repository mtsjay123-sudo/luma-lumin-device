"""Tasks: something Luma does on its own, on a schedule they set by voice.

"Every weekday at 8, tell me the weather." "Every Sunday at 6pm, remind me to call Mom." "Every night at 10, ask me how
my day went." At that time Luma runs the request through its own conversation path, as if they'd just said it, and
says the answer out loud (quietly during quiet hours). A reminder is just said.

What keeps this safe and kind:
- Only a plain request in the shape of a command starts a task ("every X, tell me / remind me / read me / ask me /
  play ..."). "Every night I cry myself to sleep" is something they told Luma, never a schedule; the crisis net reads
  every message before this does anyway.
- A task can only do what they could ask in chat. Anything that would send, post or buy still waits for their yes, and
  web look-ups still go through the switches they already set. Inbox, calendar and price watches keep the helpers they
  already have.
- Not in kids mode. At most 20.

Read by code, never by the brain, and kept as a helper (kind "task") so it shows with the others.
"""
from __future__ import annotations

import re

from luma.agent.athome import CLOCK, DAYNAMES, END, LEAD, clock_of, say_clock, say_days

WHEN = (r"(?P<when>day|morning|night|evening|afternoon|weekday|weekend|week|"
        r"(?:(?:mon|tues|wednes|thurs|fri|satur|sun)day(?:,? (?:and |& )?)?)+)")
DOES = (r"(?P<ask>(?:tell|give|read|remind|play|ask|check|say|show|update|brief|quiz|teach|motivate|hype|cheer|wish|wake|"
        r"start|let me know|sing|get me|catch me up|text me a reminder)\b.{2,200}?)")
AT = r"(?: at " + CLOCK + r")?"
FIRST = re.compile(LEAD + r"(?:every|each) " + WHEN + AT + r",? " + DOES + END, re.I)
LAST = re.compile(LEAD + DOES + r",? (?:every|each) " + WHEN + AT.replace("?P<", "?P<x") + END, re.I)
LIST = re.compile(LEAD + r"(?:what(?: are)?(?: my)? (?:scheduled |standing |recurring )?tasks(?: do i have| have i (?:got|set))?(?: scheduled| set up)?"
                  r"|(?:show|list|read)(?: me)? (?:all )?my (?:scheduled |standing |recurring )?tasks|my (?:scheduled|standing|recurring) tasks"
                  r"|what do you do (?:for me )?every (?:day|morning|week))" + END, re.I)
DROP = re.compile(LEAD + r"(?:cancel|stop|delete|remove|turn off|end|kill)(?: all)?(?: of)? (?:my |the |that )?(?P<what>[\w' -]{1,60}?) (?:task|tasks)" + END, re.I)
DROP2 = re.compile(LEAD + r"(?:stop|quit|don'?t keep) (?P<what>(?:telling|reminding|reading|asking|giving|playing|checking|saying|waking)\b.{1,80}?)"
                   r"(?:,? (?:every|each) " + WHEN.replace("?P<", "?P<y") + r")?" + END, re.I)
# Kept by the helpers they already have, so they're never doubled up.
ELSEWHERE = re.compile(r"\b(?:inbox|e-?mails?|gmail|mail|calendar|agenda|instagram|insta|tiktok|twitter|facebook|reddit|linkedin|youtube|"
                       r"price of|watch the price|send|post|buy|order|pay)\b", re.I)
TIMES = {"morning": "08:00", "day": "09:00", "weekday": "08:00", "weekend": "10:00", "week": "09:00", "afternoon": "13:00",
         "evening": "18:00", "night": "21:00"}


def days_for(when):
    w = when.lower()
    if w in {"day", "morning", "night", "evening", "afternoon"}: return []
    if w == "weekday": return [0, 1, 2, 3, 4]
    if w == "weekend": return [5, 6]
    if w == "week": return [0]
    return [i for i, name in enumerate(DAYNAMES) if re.search(name[:3] + r"\w*day", w)]


def parse(low):
    """{"ask", "days", "at"} for a new task, or None."""
    m = FIRST.match(low)
    prefix = ""
    if not m:
        m = LAST.match(low)
        prefix = "x"
    if not m: return None
    ask = " ".join(m["ask"].split()).strip(" ,.")
    if ELSEWHERE.search(ask): return None
    when = m["when"].lower()
    g = m.groupdict()
    clock = {k[len(prefix):]: v for k, v in g.items() if k.startswith(prefix) and k[len(prefix):] in {"clock", "h", "m", "ap", "part"}}
    if clock.get("clock"):
        hour, minute, sure = clock_of(clock)
        if not sure and when in {"evening", "night"} and hour < 12: hour += 12
        if not sure and when == "afternoon" and hour < 12: hour += 12
        at = f"{hour:02d}:{minute:02d}"
    else:
        at = TIMES.get(when, "09:00")
    return {"ask": ask, "days": days_for(when), "at": at}


def spoken(ask):
    """What they asked, turned toward them: "remind me to call Mom" -> "remind you to call Mom"."""
    out = re.sub(r"\b(?:me)\b", "you", ask, flags=re.I)
    out = re.sub(r"\bmy\b", "your", out, flags=re.I)
    return re.sub(r"\bi\b", "you", out)


def reminder(ask):
    """The thing to say, when the task is only a reminder ("remind me to call Mom" -> "call Mom"); else None."""
    m = re.match(r"(?:remind me|text me a reminder)(?: to| about| that)? (.+)", ask, re.I)
    return m[1].strip() if m else None


def when_words(row):
    from datetime import datetime
    hour, minute = map(int, row["at"].split(":"))
    clock = say_clock(datetime(2000, 1, 1, hour, minute))
    days = (row.get("params") or {}).get("days") or []
    return (say_days(days) if days else "every day") + f" at {clock}"


class Tasks:
    """The voice side of tasks: make one, list them, stop one. The running is in Helpers._run_task."""

    LIMIT = 20

    def __init__(self, agent):
        self.agent = agent

    def rows(self):
        return [r for r in self.agent.store.all("helper", 80) if r.get("kind") == "task"]

    def handle(self, text, low):
        low = (low or text).strip().lower()
        if LIST.match(low): return self.list()
        m = DROP2.match(low)
        if m: return self.drop(m["what"])
        m = DROP.match(low)
        if m: return self.drop(m["what"])
        new = parse(low)
        if new: return self.create(text, new)
        return None

    def create(self, text, new):
        if self.agent.mode == "kids":
            return {"text": "That's one for a grown-up to set up.", "section": "goals"}
        if len(self.rows()) >= self.LIMIT:
            return {"text": f"You've got {self.LIMIT} tasks already. Let's stop one first.", "section": "goals"}
        # Their own words, as they said them (the match was on lowercase of the same text).
        start = text.lower().find(new["ask"].lower()[:20])
        ask = text[start:start + len(new["ask"])] if start >= 0 else new["ask"]
        from luma.memory.store import reject_payment_secrets
        reject_payment_secrets(ask)
        for row in self.rows():
            if row["params"].get("ask", "").lower() == ask.lower() and row.get("at") == new["at"] and row["params"].get("days", []) == new["days"]:
                return {"text": "You've already got that one. It's still on.", "section": "goals", "helper": row}
        row = self.agent.helpers.create("task", title=ask[:120], params={"ask": ask, "days": new["days"]}, every="daily", at=new["at"], run_now=False)
        return {"text": f"Done. {when_words(row)[0].upper() + when_words(row)[1:]}, I'll {spoken(ask)}.", "section": "goals", "helper": row}

    def list(self):
        rows = self.rows()
        if not rows:
            return {"text": "No tasks yet. Try “every weekday at 8, tell me the weather.”", "section": "goals", "tasks": []}
        bits = [f"{when_words(r)}, {spoken(r['params']['ask'])}" for r in rows[:8]]
        head = "One task: " if len(rows) == 1 else f"{len(rows)} tasks: "
        return {"text": head + "; ".join(bits) + ".", "section": "goals", "tasks": [r["id"] for r in rows]}

    def drop(self, what):
        what = re.sub(r"\b(?:the|my|that|every|each|morning|night|evening|day|weekday|weekend|week|me|you|to|a|an)\b", " ", what.lower())
        words = {w for w in re.findall(r"[a-z']{3,}", what)} - {"telling", "reminding", "reading", "asking", "giving", "playing", "checking", "saying", "waking", "task", "tasks"}
        rows = self.rows()
        if not rows: return {"text": "There aren't any tasks to stop.", "section": "goals"}
        if not words or words <= {"all"}:
            hits = rows if "all" in what or len(rows) == 1 else []
        else:
            stems = {w[:5] for w in words}
            hits = [r for r in rows if stems & {w[:5] for w in re.findall(r"[a-z']{3,}", r["params"]["ask"].lower())}]
        if not hits:
            return {"text": "I couldn't tell which one. " + self.list()["text"], "section": "goals"}
        for r in hits:
            self.agent.helpers.delete(r["id"])
        if len(hits) == 1:
            return {"text": f"Stopped. I won't {spoken(hits[0]['params']['ask'])} anymore.", "section": "goals"}
        return {"text": f"Stopped all {len(hits)}.", "section": "goals"}
