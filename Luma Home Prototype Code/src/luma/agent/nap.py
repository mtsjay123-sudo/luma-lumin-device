"""Luma naps.

The owner, Nov 22: "Luma has human like features. Luma can nap. Nap mode is an option. It's almost human but it's not:
it's a presence." A reply in run 86 had Luma looking forward to a power nap, and I wrote it down as a fault: a body it
doesn't have. It isn't one. A nap is something Luma really does, so it can say so.

What a nap is, for a lamp: Luma rests. It starts nothing on its own (no check-ins, no nudges, none of its own sounds)
until the nap is over or someone speaks. Anything anyone says wakes it, at once, and what they said is heard as it
always is: the safety net is never slept through (rule 2). Alarms and timers still go off. A nap goes into Luma's own
record, so "I had a nap this afternoon" is said only when it's true.

Said by voice: "take a nap", "nap for twenty minutes", "nap mode", "go rest for a bit". "I need a nap" is theirs and is
left to the brain. Off switch: the setting "naps".
"""
from __future__ import annotations

import re
from datetime import datetime

KEY = "nap"          # {"since": when it lay down, "until": when it's due up, "hush": what hush_until was before}
LOG = "naps"         # the last naps: [{"at": when it woke, "minutes": how long}]
KEEP = 30
DEFAULT, LONGEST = 20, 180

_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "five": 5, "ten": 10, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40,
          "forty-five": 45, "forty five": 45, "sixty": 60, "ninety": 90, "half an": 30, "a half": 30}
_LEAD = r"^\W*(?:(?:hey|ok|okay|alright|well|so|now|please|yo|luma|luna)\W+)*"
_YOU = r"(?:you (?:can|could|should|may|deserve to|need to|go)|why don'?t you|how about you|go ahead and|go|time (?:for you )?to|you'?ve earned (?:a|some)|let'?s have you)"
_NAP = (r"(?:take|have|grab|get|sneak) (?:a|your|yourself a)(?: (?:little|quick|short|power|long|good|nice))? (?:nap|snooze|rest|lie down|break)|nap|"   # a bare "snooze" is for a ringing alarm
        r"(?:get|have) some (?:rest|sleep|shut-?eye)|rest (?:up|your (?:eyes|circuits|light))|go (?:to sleep|rest|lie down)|power down for a (?:bit|while|nap)")
_FOR = r"(?:\s+for\s+(?P<n>\d{1,3}|an?|one|two|three|five|ten|fifteen|twenty|thirty|forty[- ]five|forty|sixty|ninety|half an|a half)\s*(?P<unit>minutes?|mins?|hours?|hrs?|h|m)\b)?"
_TAIL = r"(?:\s+(?:now|then|luma|for a (?:bit|while|minute|little while|little bit)|if you (?:want|like|need)|a bit|a while))*\W*$"
ASK = re.compile(
    _LEAD + r"(?:(?:" + _YOU + r")\s+)?(?:" + _NAP + r")" + _FOR + _TAIL + r"|"
    + _LEAD + r"(?:(?:turn on|switch on|go (?:in)?to|start|enter)\s+)?nap (?:mode|time)(?: on)?" + _FOR.replace("<n>", "<n2>").replace("<unit>", "<unit2>") + _TAIL, re.I)
# Theirs, or somebody else's: "i need a nap", "let me take a nap", "the baby is napping", "should i nap".
NOT_LUMAS = re.compile(r"\b(?:i|i'?m|i'?ll|i'?d|we|we'?re|he|she|they|me|my|our|the (?:baby|kids?|dog|cat|twins|boys|girls)|should i|can i|let me|lemme)\b", re.I)
# Called while it naps, with nothing else said: "luma?", "wake up", "you up?".
WAKE = re.compile(r"^\W*(?:(?:hey|ok|okay|yo|psst|hello|hi)\W+)*(?:(?:luma|luna)\W*)?(?:(?:time to )?wake up|(?:are )?(?:you|u) (?:up|awake|there|napping|asleep|sleeping)|"
                  r"rise and shine|nap'?s over|nap time'?s over|get up|good morning|morning)?\W*(?:(?:luma|luna|sleepyhead)\W*)?$", re.I)
# Asked about its rest: "did you nap?", "do you sleep?", "how was your nap", "are you tired?".
ASKED = re.compile(r"\b(?:do|did|can|could|will|would) (?:you|u) (?:ever |even |really |actually |just |need to |get to |like to )*(?:nap|sleep|rest|snooze|doze|dream)\b|"
                   r"\bhow was (?:your|the|that) (?:nap|rest|snooze)\b|\b(?:good|nice) nap\b|\b(?:are|r|were) (?:you|u) (?:tired|sleepy|rested|napping|asleep|sleeping|well rested)\b|"
                   r"\b(?:you|u) (?:look|sound|seem) (?:tired|sleepy|rested)\b|\bdo (?:you|u) (?:get|ever get) (?:tired|sleepy)\b|\bwhen did (?:you|u) (?:last )?(?:nap|sleep|rest)\b", re.I)


def asked(text):
    """How many minutes they're asking Luma to nap for, or None when it isn't that."""
    said = " ".join(str(text or "").split())
    found = ASK.match(said)
    if not found or NOT_LUMAS.search(said):
        return None
    n, unit = found.group("n") or found.group("n2"), (found.group("unit") or found.group("unit2") or "").lower()
    if not n:
        return DEFAULT
    count = int(n) if n.isdigit() else _WORDS.get(n.lower().replace("  ", " "), 1)
    minutes = count * 60 if unit.startswith("h") else count
    if n.lower() in ("half an", "a half"):
        minutes = 30
    return max(1, minutes)


def _now(agent):
    return float(agent.clock())


def state(agent):
    kept = agent.store.setting(KEY) or {}
    return kept if isinstance(kept, dict) and isinstance(kept.get("until"), (int, float)) else None


def napping(agent):
    """Is Luma napping right now? A nap that has run its time is over, and is written into the record."""
    kept = state(agent)
    if not kept:
        return False
    if _now(agent) >= kept["until"]:
        _end(agent, kept, kept["until"])
        return False
    return True


def until(agent):
    """When the nap is due to end (for the apps and the lamp's light), or 0."""
    return float(state(agent)["until"]) if napping(agent) else 0


def start(agent, minutes=DEFAULT):
    """Lie down. What Luma says as it does."""
    if agent.store.setting("naps", True) is False:
        return {"text": "Naps are switched off in my settings, so I'll stay up.", "section": "nap"}
    asked_for = int(minutes)
    minutes = max(1, min(LONGEST, asked_for))
    now = _now(agent)
    before = agent.store.setting("hush_until", 0) or 0
    agent.store.set_setting(KEY, {"since": now, "until": now + minutes * 60, "hush": before})
    agent.store.set_setting("hush_until", max(float(before), now + minutes * 60))   # nothing is started while it rests
    if asked_for > LONGEST:
        said = "That's more than a nap. I'll rest for three hours. Say my name and I'm up."
    elif minutes == DEFAULT:
        said = "Okay, a little nap. Say my name and I'm up."
    else:
        said = f"Okay, napping for {_length(minutes)}. Say my name if you want me sooner."
    return {"text": said, "section": "nap", "napping_until": now + minutes * 60}


def wake(agent):
    """Anything they say wakes it. The minutes it napped, or None when it wasn't napping."""
    kept = state(agent)
    if not kept:
        return None
    now = _now(agent)
    if now >= kept["until"]:
        _end(agent, kept, kept["until"])
        return None   # it was up already
    return _end(agent, kept, now)


def _end(agent, kept, at):
    minutes = max(0, int(round((float(at) - float(kept.get("since", at))) / 60)))
    agent.store.set_setting(KEY, None)
    if (agent.store.setting("hush_until", 0) or 0) <= float(kept["until"]) + 1:   # the quiet was the nap's: it ends with the nap
        agent.store.set_setting("hush_until", float(kept.get("hush") or 0))
    if minutes >= 1 and agent.mode != "kids":   # kids mode keeps nothing
        log = [n for n in (agent.store.setting(LOG) or []) if isinstance(n, dict)]
        agent.store.set_setting(LOG, (log + [{"at": float(at), "minutes": minutes}])[-KEEP:])
    return minutes


def _length(minutes):
    if minutes % 60 == 0 and minutes >= 60:
        hours = minutes // 60
        return "an hour" if hours == 1 else f"{hours} hours"
    return "a minute" if minutes == 1 else f"{minutes} minutes"


def woke_line(minutes):
    """What Luma says when it's called out of a nap and nothing else was said."""
    if minutes < 2:
        return "I'm up. I'd barely closed my eyes. What's up?"
    return f"I'm up. That was a good nap, {_length(minutes)}. What's up?"


def last(agent):
    """The last nap in Luma's record: {"at", "minutes"}, or None."""
    log = [n for n in (agent.store.setting(LOG) or []) if isinstance(n, dict) and isinstance(n.get("at"), (int, float))]
    return log[-1] if log else None


def says(agent):
    """The last nap as Luma would say it, when it was today or yesterday. Only what's in the record."""
    nap = last(agent)
    if not nap:
        return ""
    then, now = datetime.fromtimestamp(nap["at"], agent.zone), datetime.fromtimestamp(_now(agent), agent.zone)
    days = (now.date() - then.date()).days
    if days > 1:
        return ""
    part = "this morning" if then.hour < 12 else "this afternoon" if then.hour < 18 else "this evening"
    when = part if days == 0 else "yesterday"
    minutes = int(nap["minutes"])
    size = ("an hour's" if minutes == 60 else f"a {minutes // 60}-hour") if minutes >= 60 and minutes % 60 == 0 else f"a {minutes}-minute"
    return f"I had {size} nap {when}."


def rested(agent):
    """It woke from a nap within the last two hours."""
    nap = last(agent)
    return bool(nap) and 0 <= _now(agent) - float(nap["at"]) < 2 * 3600


def note(agent):
    """What the brain is told when they ask about Luma's rest. The true things: it can nap, and when it last did."""
    had = says(agent)
    return ("They're asking about your rest. You're Luma, a presence, and you can nap: when they say \"take a nap\" you rest until the "
            "time's up or they say your name, and you hear them the moment they speak. "
            + (f"True of you: {had} " if had else "You haven't napped lately, so don't say you have. ")
            + "Speak of it as yours, warmly and lightly. Never say AI. Never say you're a person.")
