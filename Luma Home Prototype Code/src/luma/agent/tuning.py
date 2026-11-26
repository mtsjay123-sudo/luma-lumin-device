"""Luma tunes itself to the person, and writes down what it changed (docs/PRESENCE_MASTER_PROMPT.md, 3.2).

Two ways a friend changes:

- Told once, it's different from then on. "That's too long" and the replies are shorter from the next one.
- It notices what lands. Each night Luma looks at its own day: when its longer replies mostly got a one-word answer
  and its shorter ones didn't, it says less from tomorrow.

Every change is one step, is a line the brain reads on the next turn, and is written in a list the owner can read:
what changed, when, and why in their own words or Luma's own count. Each can be undone with a tap, and a change they
undid isn't made again on the same evidence. Nothing here is a guess they can't see.

Only the length of a reply is tuned so far. Humour is learned as it happens (humor.learn); how often Luma speaks up
on its own isn't tuned yet.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime

KEY, LOG = "tuned", "tuning_log"
LOWEST, HIGHEST = -2, 1
LINES = {
    -2: "They've told you your replies run long. One or two short sentences, unless they ask for more.",
    -1: "They like shorter replies from you. Two or three short sentences, unless they ask for more.",
    1: "They like you to say a bit more. Take a few sentences when there's something worth saying.",
}
LEAD = r"^\W*(?:(?:hey|ok|okay|yo|ugh|wow|lol|luma)\W+)*"
SHORTER = re.compile(LEAD + r"(?:that(?:'s| is| was)|this is|it'?s|you'?re being)?\s*(?:way |so |a bit |a little |kind of |kinda )?(?:too long|too wordy|too much(?: text| talking| words)?|a lot)\b"
                     r"(?:\W+(?:keep it (?:brief|short)|shorter(?: please)?))?\W*$|"
                     + LEAD + r"(?:you (?:talk|say|write|type) (?:way |so |too )+much|you don'?t (?:have|need) to say so much|too many words|less (?:talking|words)|"
                     r"tl;?dr|get to the point|why are your (?:answers|replies|messages) so long|"
                     r"(?:can|could|will) you (?:please )?(?:keep|make) (?:it|them|that|your (?:answers|replies)) (?:shorter|short|brief|briefer)|"
                     r"(?:keep it|make it|be) (?:shorter|short|brief|briefer)(?: please)?(?: from now on)?|"
                     r"(?:shorter|short|brief|briefer) (?:answers|replies|messages)(?: please)?(?: from now on)?|"
                     r"just the short version(?: from now on| please)?)\W*$", re.I)
LONGER = re.compile(LEAD + r"(?:you can (?:say|tell me) more|say more(?: than that)?|(?:longer|fuller) (?:answers|replies)(?: please)?|don'?t be so (?:short|brief) with me|"
                    r"you(?:'re| are) being (?:too |so )?(?:short|brief)(?: with me)?|i (?:want|like) (?:more|longer) (?:detail|answers|replies)(?: from you)?)\W*$", re.I)
CURT = re.compile(r"^\W*(?:ok(?:ay)?|k+|sure|yeah|yep|yup|mhm+|mm+|uh huh|right|fine|cool|got it|i see|whatever|ok then|alright)\W*$", re.I)
LONG_REPLY, SHORT_REPLY = 40, 25      # words


def level(agent):
    try:
        return max(LOWEST, min(HIGHEST, int((agent.store.setting(KEY) or {}).get("length", 0))))
    except (TypeError, ValueError):
        return 0


def note(agent):
    """The line the brain reads this turn, or None."""
    return LINES.get(level(agent))


def log(agent):
    return list(agent.store.setting(LOG) or [])


def _change(agent, to, why, how, said=None):
    was = level(agent)
    to = max(LOWEST, min(HIGHEST, to))
    if to == was:
        return None
    agent.store.set_setting(KEY, {**(agent.store.setting(KEY) or {}), "length": to})
    row = {"id": secrets.token_hex(4), "at": agent.clock(), "what": "how long my replies are", "from": was, "to": to,
           "says": "shorter" if to < was else "fuller", "why": str(why)[:240], "how": how, **({"said": said[:200]} if said else {})}
    agent.store.set_setting(LOG, (log(agent) + [row])[-60:])
    return row


def heard(agent, text):
    """Told once: "that's too long", "you can say more". The change is made now, with their words as the reason.
    Returns the change, or None. It never answers for the brain: the reply to this very message is already shorter."""
    said = " ".join(str(text or "").split())
    if len(said.split()) > 12:
        return None
    last = (log(agent) or [{}])[-1]
    if last.get("how") == "told" and not last.get("undone") and agent.clock() - (last.get("at") or 0) < 30:
        return None      # one message read twice in one turn (as said, and as tidied) is one telling
    if SHORTER.match(said):
        return _change(agent, level(agent) - 1, f"You said: “{said}”", "told", said=said)
    if LONGER.match(said):
        return _change(agent, level(agent) + 1, f"You said: “{said}”", "told", said=said)
    return None


def _words(text):
    return len(re.findall(r"[A-Za-z0-9']+", str(text or "")))


def looked_at(agent, now=None):
    """Luma's own count of the day: of its longer replies and its shorter ones, how many got a one-word answer."""
    now = agent.clock() if now is None else now
    start = datetime.fromtimestamp(now, agent.zone).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    turns = [m for m in agent.transcripts.get("main", []) if (m.get("at") or 0) >= start and m.get("text")]
    counts = {"long": [0, 0], "short": [0, 0]}      # [curt answers, replies]
    for mine, theirs in zip(turns, turns[1:]):
        if mine.get("role") == "user" or theirs.get("role") != "user":
            continue
        size = _words(mine["text"])
        kind = "long" if size >= LONG_REPLY else "short" if size <= SHORT_REPLY else None
        if kind:
            counts[kind][1] += 1
            counts[kind][0] += bool(CURT.match(theirs["text"]))
    return counts


def night(agent, now=None):
    """Once a night. A step shorter when most of the longer replies (four or more of them) got a one-word answer and
    the shorter ones mostly didn't. Not again on evidence they already undid. Returns the change, or None."""
    now = agent.clock() if now is None else now
    day = datetime.fromtimestamp(now, agent.zone).date().isoformat()
    state = dict(agent.store.setting(KEY) or {})
    if state.get("night") == day:
        return None
    agent.store.set_setting(KEY, {**state, "night": day})
    counts = looked_at(agent, now)
    (curt_long, long_n), (curt_short, short_n) = counts["long"], counts["short"]
    if long_n < 4 or curt_long / long_n < 0.6:
        return None
    if short_n and curt_short / short_n > curt_long / long_n - 0.3:
        return None      # they're short with everything today: that's a mood, not a verdict on long replies
    if any(row.get("undone") and row.get("how") == "noticed" and now - (row.get("at") or 0) < 14 * 86400 for row in log(agent)):
        return None      # they undid this one lately: it isn't made again on a count alone
    why = f"{curt_long} of my {long_n} longer replies today got a one-word answer" + (f", and {curt_short} of my {short_n} shorter ones." if short_n else ".")
    return _change(agent, level(agent) - 1, why, "noticed")


def undo(agent, id):
    """Put one change back. The level goes back to what it was before it; the line stays in the list, marked undone."""
    rows = log(agent)
    row = next((r for r in rows if r.get("id") == id and not r.get("undone")), None)
    if not row:
        raise ValueError("That change is already undone.")
    row["undone"] = agent.clock()
    agent.store.set_setting(LOG, rows)
    agent.store.set_setting(KEY, {**(agent.store.setting(KEY) or {}), "length": max(LOWEST, min(HIGHEST, int(row.get("from", 0))))})
    return view(agent)


def view(agent):
    """For the apps: where it stands and what was changed, newest first."""
    return {"length": level(agent), "says": LINES.get(level(agent)) or "", "log": [{k: r.get(k) for k in ("id", "at", "what", "says", "why", "said", "how", "undone")} for r in reversed(log(agent))]}
