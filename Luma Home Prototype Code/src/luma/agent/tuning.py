"""Luma tunes itself to the person, and writes down what it changed (docs/PRESENCE_MASTER_PROMPT.md, 3.2).

Two ways a friend changes:

- Told once, it's different from then on. "That's too long" and the replies are shorter from the next one.
- It notices what lands. Each night Luma looks at its own day: when its longer replies mostly got a one-word answer
  and its shorter ones didn't, it says less from tomorrow.

Every change is one step, is a line the brain reads on the next turn, and is written in a list the owner can read:
what changed, when, and why in their own words or Luma's own count. Each can be undone with a tap, and a change they
undid isn't made again on the same evidence. Nothing here is a guess they can't see.

Two things are tuned: how long a reply is, and how often Luma speaks up on its own (a check-in after something they
mentioned, a nudge about a birthday). The second only ever goes down from where Luma starts, and back up to there:
Luma never checks in more than it does as it comes (rule 3: no engagement tricks). Told "you check in too much", it
checks in once a day at most; told again, not at all on its own. Left unanswered four check-ins running, on four
different days, it steps down itself and says so in the list. What they asked for (a reminder, an alarm, a task) is
never held back by this. Humour is learned as it happens (humor.learn).
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
# How often Luma speaks up on its own. 0: as it comes. -1: once a day at most. -2: not on its own.
QUIETEST = -2
SPOKE = "spoke_up"       # the last times Luma spoke up on its own: [{"at", "answered"}]
ANSWERED_WITHIN = 6 * 3600
_ASK = r"(?:(?:please|can you|could you|will you|would you)\s+)*"
_CHECKING = r"(?:checking (?:in|up)(?: on me| with me)?|checking on me|check-?ins?|asking(?: me)? how (?:things|everything|it|stuff) went)"
LESS = re.compile(
    LEAD + r"you(?:'re| are)? (?:check(?:ing)?|ask(?:ing)?)(?: in| up)?(?: on me| with me)?(?: how (?:things|everything|it|stuff) went)? (?:way |so |too |far too )+(?:much|often)\W*$|"
    + LEAD + _ASK + r"(?:stop|quit|less|fewer|ease up on(?: the)?|cut back on(?: the)?|go easy on(?: the)?)\s+" + _CHECKING + r"(?: so (?:much|often)| all the time| every day)?(?: please)?\W*$|"
    + LEAD + _ASK + r"check in(?: on me)? less(?: often)?(?: please)?\W*$|"
    + LEAD + r"you (?:don'?t|do not) (?:have|need) to (?:keep )?(?:check(?:ing)?)(?: in| up)? on me(?: all the time| every day| so (?:much|often)| constantly)?\W*$|"
    + LEAD + r"i don'?t need you checking (?:in|up)(?: on me)?(?: every day| all the time| so (?:much|often)| constantly)?\W*$", re.I)
MORE = re.compile(
    LEAD + r"(?:you can (?:check in(?: on me)?|ask how (?:things|everything|it) went)(?: more(?: often)?| again)|(?:start )?check(?:ing)? in on me (?:more(?: often)?|again)|"
    r"i miss you checking in(?: on me)?)\W*$", re.I)
SPEAKS_SAID = {
    -1: "Okay. I'll check in less: once a day at most. Tell me any time if you'd like more.",
    -2: "Okay. I won't check in on my own. Anything you've asked me to remind you of still comes, and I'm here whenever you talk to me.",
    0: "Okay. I'll check in the way I used to.",
}
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


def speaks(agent):
    """How often Luma speaks up on its own: 0 as it comes, -1 once a day at most, -2 not on its own."""
    try:
        return max(QUIETEST, min(0, int((agent.store.setting(KEY) or {}).get("speaks", 0))))
    except (TypeError, ValueError):
        return 0


def _change(agent, to, why, how, said=None, dial="length"):
    was = speaks(agent) if dial == "speaks" else level(agent)
    to = max(QUIETEST, min(0, to)) if dial == "speaks" else max(LOWEST, min(HIGHEST, to))
    if to == was:
        return None
    agent.store.set_setting(KEY, {**(agent.store.setting(KEY) or {}), dial: to})
    what, says = ("how often I speak up", "less" if to < was else "more") if dial == "speaks" else ("how long my replies are", "shorter" if to < was else "fuller")
    row = {"id": secrets.token_hex(4), "at": agent.clock(), "dial": dial, "what": what, "from": was, "to": to,
           "says": says, "why": str(why)[:240], "how": how, **({"said": said[:200]} if said else {})}
    agent.store.set_setting(LOG, (log(agent) + [row])[-60:])
    return row


def _spoke(agent):
    return [e for e in (agent.store.setting(SPOKE) or []) if isinstance(e, dict) and isinstance(e.get("at"), (int, float))]


def spoke_up(agent, now=None):
    """Luma just said something on its own (a check-in, a nudge). Written down, so the day's count and the night's look are true."""
    now = agent.clock() if now is None else now
    agent.store.set_setting(SPOKE, (_spoke(agent) + [{"at": float(now), "answered": False}])[-20:])


def they_spoke(agent, now=None):
    """They said something: the last thing Luma said on its own, if it was in the last few hours, was answered."""
    now = agent.clock() if now is None else now
    rows = _spoke(agent)
    if rows and not rows[-1].get("answered") and 0 <= now - rows[-1]["at"] <= ANSWERED_WITHIN:
        rows[-1]["answered"] = True
        agent.store.set_setting(SPOKE, rows)


def may_speak_up(agent, now=None):
    """May Luma start something of its own right now? Never a word about what they asked for: reminders aren't this."""
    how = speaks(agent)
    if how <= QUIETEST:
        return False
    if how == 0:
        return True
    now = agent.clock() if now is None else now
    today = datetime.fromtimestamp(now, agent.zone).date()
    return not any(datetime.fromtimestamp(e["at"], agent.zone).date() == today for e in _spoke(agent))


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
    if LESS.match(said) or MORE.match(said):
        row = _change(agent, speaks(agent) + (-1 if LESS.match(said) else 1), f"You said: “{said}”", "told", said=said, dial="speaks")
        # Luma answers this one itself: what it will do from now on is a fact, not something for a brain to word
        return {**(row or {}), "reply": SPEAKS_SAID[speaks(agent)]}
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
    quieter = _night_speaks(agent, now)
    counts = looked_at(agent, now)
    (curt_long, long_n), (curt_short, short_n) = counts["long"], counts["short"]
    if long_n < 4 or curt_long / long_n < 0.6:
        return quieter
    if short_n and curt_short / short_n > curt_long / long_n - 0.3:
        return quieter   # they're short with everything today: that's a mood, not a verdict on long replies
    if any(row.get("undone") and row.get("how") == "noticed" and row.get("dial", "length") == "length" and now - (row.get("at") or 0) < 14 * 86400 for row in log(agent)):
        return quieter   # they undid this one lately: it isn't made again on a count alone
    why = f"{curt_long} of my {long_n} longer replies today got a one-word answer" + (f", and {curt_short} of my {short_n} shorter ones." if short_n else ".")
    return _change(agent, level(agent) - 1, why, "noticed") or quieter


def _night_speaks(agent, now):
    """A step quieter when the last four things Luma said on its own, on four different days, all went unanswered.
    Counted from the last change to this dial, so each step needs four more. Not again on what they undid lately."""
    rows = log(agent)
    since = max([r.get("undone") or r.get("at") or 0 for r in rows if r.get("dial") == "speaks"], default=0)
    last = [e for e in _spoke(agent) if e["at"] > since and now - e["at"] > ANSWERED_WITHIN][-4:]
    if len(last) < 4 or any(e.get("answered") for e in last):
        return None
    if len({datetime.fromtimestamp(e["at"], agent.zone).date() for e in last}) < 4:
        return None      # one day away from home isn't a verdict
    if any(r.get("undone") and r.get("how") == "noticed" and r.get("dial") == "speaks" and now - (r.get("undone") or 0) < 14 * 86400 for r in rows):
        return None
    return _change(agent, speaks(agent) - 1, "The last four times I checked in, you didn't answer.", "noticed", dial="speaks")


def undo(agent, id):
    """Put one change back. The level goes back to what it was before it; the line stays in the list, marked undone."""
    rows = log(agent)
    row = next((r for r in rows if r.get("id") == id and not r.get("undone")), None)
    if not row:
        raise ValueError("That change is already undone.")
    row["undone"] = agent.clock()
    agent.store.set_setting(LOG, rows)
    dial = row.get("dial", "length")
    back = max(QUIETEST, min(0, int(row.get("from", 0)))) if dial == "speaks" else max(LOWEST, min(HIGHEST, int(row.get("from", 0))))
    agent.store.set_setting(KEY, {**(agent.store.setting(KEY) or {}), dial: back})
    return view(agent)


def view(agent):
    """For the apps: where it stands and what was changed, newest first."""
    return {"length": level(agent), "says": LINES.get(level(agent)) or "", "speaks": speaks(agent),
            "log": [{k: r.get(k) for k in ("id", "at", "dial", "what", "says", "to", "why", "said", "how", "undone")} for r in reversed(log(agent))]}
