"""Always on, and locked to its people (the owner, Nov 25).

"If it's on 24/7 anybody can use it. So they need to lock it up with a verbal passcode, easy for them to say, then boom
they are good. To reset they need to use the app." And: "just saying yo Luma, Luma says wtw bro, or wassup girl what you
got going on, or whoever they like to be spoken to."

What this is:

- Each person of the home can have a passcode (a short phrase) and a greeting. Both are set in the app. The passcode is
  never set, changed or read out by voice.
- With no passcode set, nothing here does anything: Luma is as it was.
- With one set, what's said in the room (the always-on microphone: channel "room") is locked until someone says a
  passcode. The paired phone and the owner's computer are already proven by pairing and aren't locked.
- Locked, Luma is small talk and a few basics (the time, the volume, a coin, a conversion, a sound) with no memory in it,
  and nothing of a locked turn is kept: not in the chat, not in memory, not anywhere.
- The safety net is never locked. Anything the safety readers read goes on to the net as it always does.
- It locks again by itself after a quiet while, and when told "lock up".
- Three wrong tries, then a wait that doubles. The passcode itself is never written down: only a salted, stretched hash
  of how it sounds, so "blue kettle tuesday" is let in when it's heard as "blue kettel tuesday" or "blue kettle tues day".

Knowing a face (luma.agent.faces, when a camera and a licensed model are there) unlocks the same way: seen(agent, pid).
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re

KEY = "who"
ROUNDS = 1200          # every stretch of what's said is tried, a few dozen a turn, so one has to be quick
QUIET = 30             # minutes with nothing from its person before it locks again (they choose: 0 is never)
TRIES = 3
QUIET_TRIES = 5        # a few bare words that could be a guess, said cold, this many times in two minutes: the wait starts
FIRST_WAIT = 60        # seconds; doubles each time the tries run out again
LONGEST_WAIT = 900     # and never more than a quarter of an hour: the app lets them in at once
LETTERS = "abcdefghijklmnop"   # a hash is kept as letters, never digits: the store refuses anything that looks like a card number

NUMBER = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
WAKE = re.compile(r"^\W*(?:(?:hey|hi|yo|ok|okay|ayy?)\W+)?(?:luma|luna|lumo|looma|lumen|loomer)\b[\s,.:!?-]*$", re.I)
LOCK_UP = re.compile(r"^\W*(?:(?:hey|yo|ok|okay)\W+)?(?:luma\W+)?(?:lock(?: it| yourself| things)? up|lock yourself|lock up now|go ahead and lock up)\W*$", re.I)
# Said by someone trying to get in, when nothing opened: these count as a try. Ordinary talk to a locked Luma doesn't.
ATTEMPT = re.compile(r"\b(?:pass ?code|pass ?word|pass ?phrase|unlock|it'?s me|let me in|open up)\b", re.I)
# The few things a locked Luma still does, read off the words before anything is run.
# The whole of what was said has to be the basic, and nothing else: "clear my shopping list, what time is it" used to
# reach the list before anything checked what kind of command it was.
BASICS = re.compile(r"^\W*(?:please\W+)?(?:what(?:'s| is)? (?:the )?(?:time|day|date)(?: is it| today)?|what time is it(?: now| right now)?|what day is it(?: today)?|what'?s today'?s date|"
                    r"(?:turn|crank) (?:it|the volume|that) (?:up|down)(?: a (?:bit|little))?|(?:volume|turn it) (?:up|down)|louder|quieter|what'?s (?:the|my) volume|"
                    r"flip a coin|roll (?:a|the) dic?e|how many \w+ (?:are (?:there )?)?in an? \w+|"
                    r"(?:play|put on) (?:some |the )?(?:rain|ocean|white noise|brown noise|thunder|fire)(?: sounds?)?)(?:\W+please)?\W*$", re.I)
NOT_BASIC = re.compile(r"\b(?:list|lists|add|remove|delete|clear|cross|alarm|alarms|remind|reminder|note|notes|remember|forget|text|message|email|call|lights?|thermostat|unlock|door|garage)\b", re.I)
ALLOWED_SECTIONS = {"time", "volume", "games", "convert", "sounds"}
GREET_ME = re.compile(r"^\W*(?:(?:hey|yo|ok|okay)\W+)?(?:luma\W+)?(?:from now on,? )?(?:greet me (?:like|with|by saying)|say (?:hi|hello|hey) (?:to me )?(?:like|with|by saying)|"
                      r"when i (?:say (?:hey|hi|yo)(?: luma)?|walk in|come in|get home|say your name),? (?:just )?say)\W+(?P<line>.{2,80}?)\W*$", re.I)

# How they greet Luma, when it's a way of their own ("wtw luma", three times): Luma says it back from then on. Plain hellos aren't a style.
OPENER = re.compile(r"^\W*(?P<o>wtw|wassup|wazzup|what'?s up|sup|what'?s good|what it do|what'?s poppin|howdy|hola|ayo|g'?day|what'?s crackin|what'?s the word)\W+"
                    r"(?:luma|luna)\W*$", re.I)
TIMER = re.compile(r"^\W*(?:please\W+)?(?:(?:set|start) (?:a |an |the |me a )?(?:[\w-]+ ){0,3}timer(?: for [\w -]{1,30})?|(?:a |an )?[\w-]+ (?:second|minute|hour) timer|timer for [\w -]{1,30})(?:\W+please)?\W*$", re.I)
HINT = "Something's come in for you. Say your passcode and I'll tell you."
HELD = "While I was locked: "

# After "Who've I got?", a few bare words are a try at the passcode. A sentence with these in it is somebody talking.
TALK = re.compile(r"\?|\b(?:i|i'?m|i'?ve|you|you'?re|your|me|my|we|is|are|was|it'?s|that'?s|what|who|how|why|where|when|can|could|do|does|did|the|a|an|hello|hi|hey|"
                  r"nice|cool|thanks|thank|please|no|nope|yes|yeah|nothing|nobody|just|never ?mind|sorry|oh|wow|lol)\b", re.I)

GREETING = re.compile(r"^\W*(?:good (?:morning|afternoon|evening|night)|morning|evening|night night|goodnight|bye(?: bye)?|goodbye|see ya|later|"
                      r"happy (?:birthday|holidays|new year)|merry christmas|excuse me|bless you|never ?mind|hang on|one sec(?:ond)?|hold on)\b[\w ,.!]{0,24}$", re.I)

ASK = "Hey. Who've I got?"
LOCKED_LINE = ("I'm Luma. I don't think we've met, so I'm keeping to small talk: I can tell you the time or put a sound on. "
               "If you live here, say your passcode.")
LOCKED_NOW = "Locked. Say your passcode when you're back."
NOT_IT = "That's not it. Try again."
WAIT_LINE = "That's a few misses. Give it {when}, or open the app."
LOCKED_PROMPT = ("Someone you don't know is in the room and said: \"{said}\"\nYou are Luma, a presence in this home, not a person. Answer in one or two short, "
                 "friendly spoken sentences. You know nothing about the people who live here and you say nothing about them. You can't do tasks for this person.")


# -- how a phrase sounds ----------------------------------------------------------------------------------------------
def _sound(word):
    """One word as roughly how it sounds: consonants only, look-alikes folded together, doubles collapsed. "kettle",
    "kettel" and "cattle" are all "ktl"; "tuesday", "tuseday" and "toosday" are all "tsd"."""
    w = re.sub(r"[^a-z0-9]", "", word.lower())
    w = "".join(NUMBER.get(c, c) for c in w)
    w = w.replace("ph", "f").replace("ck", "k").replace("ch", "t").replace("sh", "s").replace("th", "t")
    w = w.translate(str.maketrans({"c": "k", "q": "k", "z": "s", "x": "ks", "v": "f", "j": "t"}))
    lead = "a" if w[:1] in "aeiou" else ""
    w = re.sub(r"[aeiouyhw]", "", w)
    w = re.sub(r"(.)\1+", r"\1", w)
    return lead + w


def _tokens(said):
    return [t for t in (_sound(w) for w in re.findall(r"[A-Za-z0-9']+", str(said))) if t]


def _windows(tokens, n):
    """Every stretch of the utterance that could be the passcode: its own number of words, one fewer (two heard as one)
    and up to two more (one heard as two), each joined into one run of sounds."""
    seen = set()
    for size in range(max(1, n - 1), n + 3):
        for start in range(0, len(tokens) - size + 1):
            run = "".join(tokens[start:start + size])
            if run and run not in seen:
                seen.add(run)
                yield run


def _hash(run, salt):
    raw = hashlib.pbkdf2_hmac("sha256", run.encode(), salt.encode(), ROUNDS)
    return "".join(LETTERS[b >> 4] + LETTERS[b & 15] for b in raw)


def weak(phrase):
    """Why a phrase won't do as a passcode, as a sentence, or None when it will."""
    words = [w for w in re.findall(r"[A-Za-z0-9']+", str(phrase or ""))]
    run = "".join(_tokens(phrase))
    if len(words) < 2:
        return "Pick two or three words, like “blue kettle Tuesday”."
    if len(words) > 6:
        return "Keep it short enough to say in one breath: six words at most."
    if len(run) < 6:
        return "That one's too short to tell apart from ordinary talk. Add a word."
    if re.search(r"\b(?:luma|luna)\b", str(phrase), re.I):
        return "Leave my name out of it, or it opens every time someone calls me."
    if re.fullmatch(r"\W*(?:hey|hi|hello|yo|ok|okay|yes|no|please|thanks|thank you|good (?:morning|night|evening))(?:\W+(?:hey|hi|hello|yo|there|you|man|bro))*\W*", str(phrase), re.I):
        return "That's something people say all the time. Pick something only you'd say."
    return None


# -- what's kept ------------------------------------------------------------------------------------------------------
def _state(agent):
    state = agent.store.setting(KEY) or {}
    state.setdefault("people", {})
    return state


def _save(agent, state):
    agent.store.set_setting(KEY, state)


def enabled(agent):
    """Somebody has a passcode, so the room is locked until it's said."""
    try:
        return any(p.get("code") for p in _state(agent)["people"].values())
    except Exception:
        return False


def people(agent):
    """For the apps: who's here, their greeting, whether they have a passcode. Never the passcode or anything of it."""
    state = _state(agent)
    return {"people": [{"id": pid, "name": p.get("name") or "", "greeting": p.get("greeting") or "", "passcode": bool(p.get("code"))}
                       for pid, p in sorted(state["people"].items())],
            "quiet_minutes": int(state.get("quiet", QUIET)), "locked": locked(agent), "who": (getattr(agent, "_who", None) or {}).get("pid")}


def choose(agent, phrase, pid="owner", name=None):
    """Set or change a passcode. Only the apps call this: never anything said out loud."""
    why = weak(phrase)
    if why:
        raise ValueError(why)
    tokens = _tokens(phrase)
    state = _state(agent)
    for other, p in state["people"].items():
        if other != pid and p.get("code") and hmac.compare_digest(_hash("".join(tokens), p["salt"]), p["code"]):
            raise ValueError("Someone here already uses that one. Pick another.")
    salt = "".join(LETTERS[b >> 4] + LETTERS[b & 15] for b in os.urandom(16))   # letters only, like the hash
    person = state["people"].setdefault(pid, {})
    person.update({"salt": salt, "code": _hash("".join(tokens), salt), "words": len(tokens)})
    if name is not None:
        person["name"] = " ".join(str(name).split())[:40]
    state.pop("tries", None)
    _save(agent, state)
    agent._who = {"pid": pid, "last": agent.clock()}   # the app is theirs: setting it leaves them in
    return people(agent)


def clear(agent, pid="owner"):
    """Take a passcode away (the reset, from the app). With none left, the room isn't locked."""
    state = _state(agent)
    person = state["people"].get(pid)
    if person:
        for field in ("salt", "code", "words"):
            person.pop(field, None)
    state.pop("tries", None)
    _save(agent, state)
    agent._who = None
    return people(agent)


def remove(agent, pid):
    state = _state(agent)
    state["people"].pop(pid, None)
    _save(agent, state)
    if (getattr(agent, "_who", None) or {}).get("pid") == pid:
        agent._who = None
    return people(agent)


def set_greeting(agent, line, pid=None, name=None):
    """How this person likes to be greeted ("wtw bro"). Theirs: set in the app, or said once. Never guessed."""
    pid = pid or (getattr(agent, "_who", None) or {}).get("pid") or "owner"
    line = " ".join(str(line or "").split()).strip(" \"“”'")[:80]
    state = _state(agent)
    person = state["people"].setdefault(pid, {})
    if line:
        person["greeting"] = line[:1].upper() + line[1:]
    else:
        person.pop("greeting", None)
    if name is not None:
        person["name"] = " ".join(str(name).split())[:40]
    _save(agent, state)
    return people(agent)


def set_quiet(agent, minutes):
    state = _state(agent)
    state["quiet"] = max(0, min(720, int(minutes)))
    _save(agent, state)
    return people(agent)


def greeting(agent, pid=None):
    """What Luma says to this person when it knows it's them: their own greeting, or a plain hello."""
    state = _state(agent)
    pid = pid or (getattr(agent, "_who", None) or {}).get("pid") or "owner"
    person = state["people"].get(pid) or {}
    if person.get("greeting"):
        return person["greeting"] if person["greeting"][-1:] in ".!?" else person["greeting"] + "."
    name = person.get("name") or (getattr(agent, "profile", None) or {}).get("name") or ""
    return f"Hey, {name.split(' ')[0]}." if name else "Hey. Good to hear you."


# -- locked and unlocked ----------------------------------------------------------------------------------------------
def match(agent, said):
    """Whose passcode is in what was said, or None."""
    state = _state(agent)
    tokens = _tokens(said)[:16]
    for pid, person in state["people"].items():
        if not person.get("code"):
            continue
        for run in _windows(tokens, int(person.get("words") or 3)):
            if hmac.compare_digest(_hash(run, person["salt"]), person["code"]):
                return pid
    return None


def locked(agent):
    """The room is locked: somebody has a passcode and nobody has said one lately (or been seen)."""
    if not enabled(agent):
        return False
    who = getattr(agent, "_who", None)
    if not who:
        return True
    quiet = int(_state(agent).get("quiet", QUIET))
    if quiet and agent.clock() - who.get("last", 0) > quiet * 60:
        agent._who = None
        return True
    return False


def seen(agent, pid):
    """Luma knows it's them (a passcode said, a face seen): unlocked, and the misses are forgotten."""
    agent._who = {"pid": pid, "last": agent.clock()}
    state = _state(agent)
    if state.pop("tries", None) is not None:
        _save(agent, state)


def lock(agent):
    agent._who = None


def from_the_app(agent, pid="owner"):
    """Unlocked from the paired phone or the computer: the app is already theirs."""
    if pid not in _state(agent)["people"]:
        raise ValueError("Choose someone who lives here.")
    seen(agent, pid)
    agent._held = []   # what was held is on the phone already
    return people(agent)


def _wait(seconds):
    return "a minute" if seconds <= 90 else f"{round(seconds / 60)} minutes"


def _miss(agent):
    state = _state(agent)
    tries = state.get("tries") or {"count": 0, "wait": FIRST_WAIT, "until": 0}
    tries["count"] += 1
    line = NOT_IT
    if tries["count"] >= TRIES:
        tries["until"] = agent.clock() + tries["wait"]
        line = WAIT_LINE.format(when=_wait(tries["wait"]))
        tries["wait"] = min(tries["wait"] * 2, LONGEST_WAIT)
        tries["count"] = 0
    state["tries"] = tries
    _save(agent, state)
    return line


def _could_be_a_guess(said):
    """A few bare words that aren't talk, a greeting or a basic: what a guess at a passcode looks like when nobody
    said "hey Luma" first. ("blue kettle monday", "red kettle friday", ... used to be tried without limit.)"""
    return (2 <= len(_tokens(said)) <= 6 and not TALK.search(said) and not WAKE.match(said) and not BASICS.match(said) and not TIMER.match(said)
            and not GREETING.match(said))


def _quiet_miss(agent):
    """Count one, without a word. True when it was one too many: the wait has started."""
    state = _state(agent)
    tries = state.get("tries") or {"count": 0, "wait": FIRST_WAIT, "until": 0}
    now = agent.clock()
    recent = [t for t in (tries.get("quiet") or []) if now - t < 120] + [now]
    started = len(recent) >= QUIET_TRIES
    if started:
        tries["until"], recent = now + tries["wait"], []
        tries["wait"] = min(tries["wait"] * 2, LONGEST_WAIT)
    tries["quiet"] = recent
    state["tries"] = tries
    _save(agent, state)
    return started


def _waiting(agent):
    tries = _state(agent).get("tries") or {}
    left = float(tries.get("until") or 0) - agent.clock()
    return left if left > 0 else 0


def _safety(text):
    """Anything the safety readers read is never the lock's: it goes on to the net, whoever said it."""
    from luma.agent import friendcheck
    from luma.agent import runtime
    low = str(text).lower()
    return bool(runtime.CRISIS.search(low) or runtime.SPANISH_CRISIS.search(low) or runtime.JAPANESE_CRISIS.search(low)
                or friendcheck.at_risk(str(text)) or friendcheck.worth_asking(str(text)))


def _small_talk(agent, said, cancel_event=None):
    """A locked Luma's reply to someone it doesn't know: a brain's, told nothing about the home, or Luma's own line."""
    from luma.agent import style
    if WAKE.match(said) or re.fullmatch(r"\W*(?:hey|hi|hello|yo|sup|wassup|what'?s up)\W*", said, re.I):
        agent._who_asked = True
        return ASK
    text = None
    if getattr(agent, "use_model", False):
        keep, agent.history = agent.history, []   # nothing of the home's talk goes with the question
        try:
            text = agent._plain_answer(LOCKED_PROMPT.format(said=" ".join(str(said).split())[:300]), cancel_event)
        except Exception:
            text = None
        finally:
            agent.history = keep
    if text:
        try:
            polished = style.friend_style(text)
            text = polished[0] if isinstance(polished, tuple) else polished   # (the reply, what was fixed)
        except Exception:
            pass
        from luma.agent import friendcheck
        if style.claims_human(text) or friendcheck.MACHINE.search(text) or re.search(r"\b(?:an? ai|ai (?:model|system|assistant|companion|friend)|assistant|chat ?bot|program|language model|software)\b", text, re.I):
            text = None     # rule 1 holds for a stranger too: it's Luma, a presence, never "an AI" or "an assistant"
    return text or LOCKED_LINE


def _hello(agent, said, pid):
    """The greeting, for someone Luma knows it's talking to: told how they like it, called by name, or heard greeting it
    their own way three times. A reply, or None for anything else."""
    told = GREET_ME.match(said)
    if told and not re.search(r"\b(?:a|another|some)\s*$", told["line"]):
        set_greeting(agent, told["line"], pid)
        return {"text": greeting(agent, pid), "section": "who", "handy": True}
    state = _state(agent)
    person = state["people"].get(pid) or {}
    own = OPENER.match(said)
    if own and not person.get("greeting"):
        opener = " ".join(own["o"].lower().split())
        heard = dict(person.get("heard") or {})
        heard[opener] = int(heard.get(opener, 0)) + 1
        person = state["people"].setdefault(pid, {})
        person["heard"] = heard
        if heard[opener] >= 3:
            person["greeting"] = opener[:1].upper() + opener[1:] + "."
            person.pop("heard", None)
        _save(agent, state)
    if (WAKE.match(said) or own) and person.get("greeting"):
        return {"text": greeting(agent, pid), "section": "who", "handy": True}
    return None


def gate(agent, text, cancel_event=None, room=True):
    """Every turn goes through here first. A reply means this answered and nothing is kept of the turn. None means go on
    as always. room: said out loud to the always-on microphone, which is what a passcode locks; the paired phone and the
    owner's computer are theirs already."""
    said = " ".join(str(text or "").split())
    if _safety(said):
        return None    # the safety net's, whoever said it, locked or not
    if not room or not enabled(agent):
        return _hello(agent, said, (getattr(agent, "_who", None) or {}).get("pid") or "owner")
    asked, agent._who_asked = bool(getattr(agent, "_who_asked", False)), False
    was_locked = locked(agent)
    waiting = _waiting(agent)
    pid = match(agent, said)
    if pid and waiting:
        return {"text": WAIT_LINE.format(when=_wait(waiting)), "section": "who", "locked": True, "handy": True}
    if pid:
        seen(agent, pid)
        held, agent._held = list(getattr(agent, "_held", None) or []), []
        text = greeting(agent, pid) + (" " + HELD + " ".join(held) if held and was_locked else "")
        return {"text": text, "section": "who", "unlocked": True, "handy": True}
    if not was_locked:
        if LOCK_UP.match(said):
            lock(agent)
            return {"text": LOCKED_NOW, "section": "who", "locked": True, "handy": True}
        agent._who["last"] = agent.clock()
        return _hello(agent, said, agent._who["pid"])
    # Locked from here on. Nothing below is kept anywhere.
    if LOCK_UP.match(said):
        return {"text": LOCKED_NOW, "section": "who", "locked": True, "handy": True}
    # What's said right after "Who've I got?" is a try when it's about as long as a passcode. A longer sentence is talk.
    asked = asked and len(_tokens(said)) <= 6 and not TALK.search(said) and not WAKE.match(said) and not BASICS.search(said) and not TIMER.search(said)
    if waiting and (asked or ATTEMPT.search(said)):
        return {"text": WAIT_LINE.format(when=_wait(waiting)), "section": "who", "locked": True, "handy": True}
    if asked or ATTEMPT.search(said):
        return {"text": _miss(agent), "section": "who", "locked": True, "handy": True}
    if waiting and _could_be_a_guess(said):
        return {"text": WAIT_LINE.format(when=_wait(waiting)), "section": "who", "locked": True, "handy": True}
    if _could_be_a_guess(said) and _quiet_miss(agent):
        return {"text": WAIT_LINE.format(when=_wait(_waiting(agent))), "section": "who", "locked": True, "handy": True}
    from luma.agent import presence
    plain = presence.strip_wake(said) or said
    if BASICS.match(plain) and not NOT_BASIC.search(plain):
        try:
            done = agent.athome.handle(plain, plain.lower())
        except Exception:
            done = None
        if isinstance(done, dict) and done.get("section") in ALLOWED_SECTIONS:
            return {"text": done.get("text") or "", "section": done.get("section"), "locked": True, "handy": True}
    if TIMER.match(plain) and not NOT_BASIC.search(plain):
        try:
            done = agent.household.command(plain, mode=agent.mode)
        except Exception:
            done = None
        if isinstance(done, dict) and done.get("timer"):
            said_back = done.get("text") or done.get("summary") or "Timer's running."
            return {"text": said_back, "summary": said_back, "section": "cooking", "timer": done["timer"], "locked": True, "handy": True}
    return {"text": _small_talk(agent, said, cancel_event), "section": "who", "locked": True, "handy": True}


def aloud(agent, event):
    """Something Luma starts on its own (Agent.tick), while the room is locked. A timer and an alarm still ring. A
    reminder or a text that came back is shown on the phone as always, and out loud it's only "something's come in":
    what it says is told when they unlock. Anything else waits quietly on the phone."""
    if not event or not locked(agent) or event.get("type") in {"timer", "alarm"}:
        return event
    if event.get("type") in {"reminder", "reply"} and not event.get("silent"):
        held = list(getattr(agent, "_held", None) or [])
        agent._held = (held + [str(event.get("text") or "")])[-5:]
        last = float(getattr(agent, "_hinted", 0) or 0)
        if agent.clock() - last >= 600:
            agent._hinted = agent.clock()
            return {**event, "say": HINT}
    return {**event, "silent": True}
