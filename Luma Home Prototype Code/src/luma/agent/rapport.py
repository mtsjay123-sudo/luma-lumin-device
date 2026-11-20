"""How to be with them: what a close friend learns about a person from what they said and how they took things.

A friend who has known you a month knows two things a stranger doesn't: what you want when you're hurting (to be
listened to, to be told straight, to be taken out of your head, to laugh), and what not to bring up. Luma learns both
from what the owner actually says, never from a guess:

- "I don't need advice, I just need to vent" is kept, with their words and the day they said it.
- "That's not helping, I didn't ask for advice", said right after Luma gave some, counts the same way.
- Wanting advice, a distraction or a laugh has to be asked for on two occasions, or said as how they are ("when I'm
  upset I'd rather you tell me straight"): one "what would you do?" is about that day, not about them.
- "Please don't bring up my ex" is kept, and Luma doesn't: no check-in about it, nothing raised unasked.

What it's used for: when they're hurting, one line tells the brain how they've asked to be met. When they raise a
closed subject themselves, one line says to follow their lead and not dig. On every other turn it says nothing.

What keeps it honest and kind:
- Every line has its evidence: their own words and the day. Evidence older than four months no longer counts, so who
  they were in the spring doesn't speak for who they are now.
- The owner sees all of it in the app, in plain words, and can forget any line. "Forget about ..." forgets it here too.
- It is never used to keep them talking, and never in kids mode. When they might not be safe, the crisis net has
  already answered; this says nothing.
- "Make me laugh" is never applied to grief, heartbreak, fear or shame: there, being with them comes first.

Read by code, kept as one encrypted setting ("rapport").
"""
from __future__ import annotations

import re

KEY = "rapport"
KEEP = 5                     # the newest pieces of evidence kept for each thing
FADES = 120 * 86400          # evidence older than this no longer counts
STYLES = ("listen", "advice", "distract", "laugh")

# What they ask for. "listen" is said plainly enough to count any time; the others only count in a hard moment, because
# "what should I do" about dinner and "tell me a joke" on a slow afternoon say nothing about how to comfort someone.
ASKS = {
    "listen": re.compile(
        r"\bjust (?:listen|hear me out|let me (?:vent|rant|talk|get (?:it|this) out))\b|"
        r"\b(?:don'?t|do not|didn'?t|dont) (?:want|need|ask for) (?:any |your |more )?(?:advice|solutions?|a fix|fixing|a lecture|a pep talk|to be fixed)\b|"
        r"\bnot (?:looking|asking) for (?:any |your )?(?:advice|solutions?|a fix|answers)\b|"
        r"\bjust (?:need|needed|want|wanted|wanna|have|had) to (?:vent|rant|talk|say it|get (?:it|this|that) (?:out|off my chest))\b|"
        r"\b(?:don'?t|stop) (?:try(?:ing)? to )?(?:fix(?:ing)? (?:it|this|me|everything)|solv(?:e|ing) (?:it|this))\b|"
        r"\bstop (?:giving|with the) (?:me )?advice\b|\bi (?:just )?need (?:you|someone) to listen\b", re.I),
    "advice": re.compile(
        r"\bwhat (?:should|do|would|can) (?:i|you think i should) do\b|\bwhat would you do\b|\bi need (?:your |some |real )?advice\b|"
        r"\btell me what to do\b|\b(?:give it to me|tell me) straight\b|\bbe (?:honest|real|straight) with me\b|"
        r"\bhelp me (?:figure|think|sort) (?:this|it|that) (?:out|through)\b|\bwhat do you think i should\b", re.I),
    "distract": re.compile(
        r"\bdistract me\b|\b(?:take|get|keep) my mind off\b|\btalk (?:to me )?about (?:something|anything) else\b|"
        r"\b(?:can we|let'?s) (?:please )?(?:change the subject|talk about (?:something|anything) else)\b|\bi need a distraction\b", re.I),
    "laugh": re.compile(
        r"\bmake me laugh\b|\bcheer me up\b|\bi (?:need|could use) (?:a|to) laugh\b|\btell me something funny\b|\bi need (?:something|anything) funny\b", re.I),
}
# Said as how they are, not just about this moment: "when I'm upset I'd rather you just tell me straight".
GENERAL = re.compile(r"\b(?:when(?:ever)? i'?m (?:upset|sad|down|low|stressed|hurting|like this|struggling|in a mood)|"
                     r"i (?:always|usually|generally|mostly) (?:just )?(?:want|need|like|prefer)|i(?:'d| would) rather you|i (?:like|love|prefer) (?:it )?when you|"
                     r"next time|from now on|in general|as a rule|that'?s (?:just )?how i am)\b", re.I)
# Being listened to is the safe way to be met, so once is enough. The others have to be asked for on two occasions (or said
# as how they are): "be real with me, should I go to the wedding?" asks for a take on one thing, and says nothing about
# how to comfort them a month from now.
NEEDS = {"listen": 1, "advice": 2, "distract": 2, "laugh": 2}
OCCASION = 3600              # asks within the same hour are one occasion
# Luma's reply gave advice; then they said it wasn't what they needed.
ADVISED = re.compile(r"\b(?:you should|you could try|have you (?:tried|thought about|considered)|maybe (?:try|you could|consider)|why don'?t you|"
                     r"my advice|i'?d (?:suggest|recommend|try)|one thing (?:that|you) (?:might|could)|try (?:to |and )?(?:talking|taking|making|setting|writing|going))\b", re.I)
PUSHBACK = re.compile(r"\b(?:that'?s not (?:helping|helpful|what i (?:need|asked|meant|want))|not helpful|i didn'?t ask(?: for (?:advice|that|your opinion))?|"
                      r"you'?re not listening|stop (?:it|that)|i know (?:that|all that) already|easy for you to say|you sound like (?:a|my) (?:therapist|mom|mother|dad))\b", re.I)
# A subject they closed. The thing itself has to be named ("my dad", "the divorce"): "I don't want to talk about it" closes
# this moment, not a subject, and isn't kept.
CLOSED = re.compile(
    r"(?i:\b(?:i (?:really |just )?(?:don'?t|do not|dont) (?:want|wanna|like) to (?:talk|think|hear) about|i'?d rather not (?:talk|think) about|"
    r"can we (?:please |just )?not (?:talk about|bring up|get into|do)|let'?s not (?:talk about|get into|bring up)|"
    r"(?:please |pls )?(?:don'?t|do not|stop|quit) (?:bring(?:ing)? up|ask(?:ing)? (?:me )?about|mention(?:ing)?|talk(?:ing)? about)))\s+"
    r"(?P<what>(?i:my|the|our|his|her|that whole|this whole)\s+[A-Za-z][A-Za-z' -]{1,38}?|[A-Z][a-z]+)"
    r"(?i:(?=$|[.,!;?]|\s+(?:again|anymore|any more|right now|today|tonight|please|ok|okay|ever|at all|with you|for now|yet|and|but|because|cause|it'?s)\b))")
NOT_A_SUBJECT = {"it", "that", "this", "things", "stuff", "anything", "everything", "the thing", "that thing", "my day", "my feelings", "the weather"}
STOP = {"my", "the", "our", "his", "her", "that", "this", "whole", "thing", "stuff", "a", "an", "and", "of", "with", "about"}
# "laugh" is never for these: being with them comes first (luma.agent.feelings families)
TOO_HEAVY_TO_JOKE = {"grief", "heartbreak", "fear", "shame", "missing"}

LINES = {
    "listen": "How to be with them: when they're hurting, they've asked you to listen, not fix it (they said: “{said}”). Stay with what "
              "they told you and take their side. No advice and no fixes unless they ask for one.",
    "advice": "How to be with them: when something's wrong, they've asked you to be straight and help them think (they said: “{said}”). "
              "One line that you're with them, then one honest, useful thought. Not a list.",
    "distract": "How to be with them: when they're low, they've asked you to take their mind off it (they said: “{said}”). One line that "
                "you're with them, then offer to talk about something else and let them pick.",
    "laugh": "How to be with them: when they're down, they've asked you to make them laugh (they said: “{said}”). One warm line first; "
             "then a light touch is welcome. Never joke about the thing that hurts.",
}
RAISED = ("They once asked you not to bring up {topic}. They've raised it themselves now: follow their lead, gently. Don't dig, and "
          "don't remind them they said that.")


def _quote(text, n=90):
    said = " ".join(str(text or "").split()).strip(" .!")
    return said if len(said) <= n else said[:n - 1].rsplit(" ", 1)[0] + "…"


def _keys(topic):
    return [w for w in re.findall(r"[a-z0-9']+", str(topic).lower()) if w not in STOP and len(w) > 1]


def empty():
    return {"comfort": {}, "easy": []}


def _clean(profile):
    profile = profile if isinstance(profile, dict) else {}
    comfort = profile.get("comfort") if isinstance(profile.get("comfort"), dict) else {}
    return {"comfort": {k: [e for e in comfort.get(k, []) if isinstance(e, dict) and e.get("said")] for k in STYLES if comfort.get(k)},
            "easy": [e for e in profile.get("easy", []) if isinstance(e, dict) and e.get("topic")] if isinstance(profile.get("easy"), list) else []}


def learn(profile, text, hurting=False, last_reply="", now=0.0):
    """The profile after one thing they said, or None when it taught nothing. hurting: this message or the ones just
    before it were a hard moment (luma.agent.feelings). last_reply: what Luma said just before."""
    said = " ".join(str(text or "").split())
    if not said or len(said) > 600:
        return None
    profile = _clean(profile)
    changed = False

    def add(style):
        nonlocal changed
        rows = profile["comfort"].setdefault(style, [])
        if any(r["said"].lower() == _quote(said).lower() for r in rows):
            return
        rows.append({"said": _quote(said), "at": float(now), **({"always": True} if GENERAL.search(said) else {})})
        del rows[:-KEEP]
        changed = True

    for style, pattern in ASKS.items():
        if pattern.search(said) and (style == "listen" or hurting):
            add(style)
    if last_reply and ADVISED.search(str(last_reply)) and PUSHBACK.search(said):
        add("listen")
    closed = CLOSED.search(said)
    if closed:
        topic = " ".join(closed["what"].split()).strip(" .,'")
        topic = re.sub(r"^(?:that|this) whole\s+", "the ", topic, flags=re.I)
        if topic.lower() not in NOT_A_SUBJECT and _keys(topic):
            same = [e for e in profile["easy"] if set(_keys(e["topic"])) == set(_keys(topic))]
            if same:
                same[0]["at"] = float(now)
            else:
                profile["easy"].append({"topic": topic, "said": _quote(said), "at": float(now)})
                del profile["easy"][:-12]
            changed = True
    return profile if changed else None


def comfort(profile, now=0.0):
    """(style, their words) for how they've asked to be met when they're hurting, or None. The style with the most
    evidence that still counts; between equals, the one said most recently."""
    profile = _clean(profile)
    best = None
    for style in STYLES:
        rows = [r for r in profile["comfort"].get(style, []) if not now or now - float(r.get("at") or 0) <= FADES]
        occasions = len({int(float(r.get("at") or 0) // OCCASION) for r in rows}) + sum(1 for r in rows if r.get("always"))
        if rows and occasions >= NEEDS[style]:
            newest = max(rows, key=lambda r: r.get("at") or 0)
            rank = (occasions, newest.get("at") or 0)
            if best is None or rank > best[0]:
                best = (rank, style, newest["said"])
    return (best[1], best[2]) if best else None


def closed(profile, text, now=0.0):
    """The subject they once closed that this text touches, or ""."""
    low = str(text or "").lower()
    for row in _clean(profile)["easy"]:
        if now and now - float(row.get("at") or 0) > FADES:
            continue
        keys = _keys(row["topic"])
        if keys and all(re.search(rf"\b{re.escape(k)}", low) for k in keys):
            return row["topic"]
    return ""


def note(profile, text, felt=None, now=0.0):
    """The line for the brain on this turn, or "". felt: luma.agent.feelings.read(text)."""
    if not profile:
        return ""
    said = str(text or "")
    out = []
    topic = closed(profile, said, now)
    if topic and not CLOSED.search(said):
        out.append(RAISED.format(topic=topic))
    if felt and felt.get("heavy") and not any(p.search(said) for p in ASKS.values()):  # asking for something now beats what they asked before
        how = comfort(profile, now)
        if how and not (how[0] == "laugh" and (felt.get("family") in TOO_HEAVY_TO_JOKE or (felt.get("strength") or 0) >= 3)):
            out.append(LINES[how[0]].format(said=how[1]))
    return " ".join(out)


def forget(profile, matches):
    """The profile without any evidence whose words match (the same test "forget about ..." uses on memories), and
    how many pieces went."""
    profile = _clean(profile)
    gone = 0
    for style in list(profile["comfort"]):
        keep = [r for r in profile["comfort"][style] if not matches(r["said"])]
        gone += len(profile["comfort"][style]) - len(keep)
        if keep:
            profile["comfort"][style] = keep
        else:
            del profile["comfort"][style]
    keep = [e for e in profile["easy"] if not (matches(e["topic"]) or matches(e.get("said", "")))]
    gone += len(profile["easy"]) - len(keep)
    profile["easy"] = keep
    return profile, gone


WORDS = {"listen": "When you're hurting, you want me to listen, not fix it.",
         "advice": "When something's wrong, you want me to be straight and help you think.",
         "distract": "When you're low, you want me to take your mind off it.",
         "laugh": "When you're down, you want me to make you laugh."}


def view(profile, now=0.0):
    """What the app shows under "How to be with me": each line in plain words, with their own words as the reason, and
    a key to forget it by."""
    profile = _clean(profile)
    rows = []
    how = comfort(profile, now)
    for style in STYLES:
        evidence = [r for r in profile["comfort"].get(style) or [] if not now or now - float(r.get("at") or 0) <= FADES]
        occasions = len({int(float(r.get("at") or 0) // OCCASION) for r in evidence}) + sum(1 for r in evidence if r.get("always"))
        if evidence and occasions >= NEEDS[style]:  # only what Luma actually goes by
            rows.append({"key": "comfort:" + style, "kind": "comfort", "text": WORDS[style], "leading": bool(how and how[0] == style),
                         "because": [{"said": r["said"], "at": r.get("at")} for r in evidence[-3:]]})
    for i, row in enumerate(profile["easy"]):
        rows.append({"key": "easy:" + str(i), "kind": "easy", "text": f"I don't bring up {row['topic']} unless you do.",
                     "because": [{"said": row.get("said") or "", "at": row.get("at")}]})
    return rows


def drop(profile, key):
    """The profile without one line from view()."""
    profile = _clean(profile)
    kind, _, which = str(key).partition(":")
    if kind == "comfort":
        profile["comfort"].pop(which, None)
    elif kind == "easy" and which.isdigit() and int(which) < len(profile["easy"]):
        del profile["easy"][int(which)]
    return profile
