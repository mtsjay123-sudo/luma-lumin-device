"""An ex, a subject they've closed, and a wish to vent: said back like a friend, and kept with what it means.

Found Nov 26, 2026 (the owner, reading the app's chats): "please don't bring up my ex again" got "My brain isn't
running right now ...", and "I don't need advice, I just need to vent" got the same line as the turn before. Luma had
learned both (luma.agent.rapport) and said nothing that showed it. And it didn't know who the ex was: "my boyfriend
Caden" had been said, and nothing connected the two.

What a friend does, and Luma now does, by code:

- **A subject closed** ("please don't bring up my ex again", "can we not talk about the divorce"), when that's the whole
  of what they said: "Okay. I won't bring that up." The subject is kept in How to be with you, as before.
- **When it's their ex,** Luma works out who that is, so it can't slip:
  - an ex it already knows: it just says it won't bring them up, and never says the name;
  - a partner it knows and no ex ("my boyfriend's name is Caden"): it asks once, "Is Caden your ex now?". On a yes
    the old card is rewritten ("Caden used to be my boyfriend"), a new one is kept with the day, and Caden becomes a
    name Luma doesn't raise. On a no, nothing changes;
  - nobody: it asks the name, so it never says it by accident ("You don't have to tell me"). A name is kept; anything
    else is let go and the message is read as what it is.
- **A breakup said plainly** ("Caden and I broke up", "I broke up with my boyfriend") updates what Luma knows,
  quietly: the brain answers the moment. They haven't asked Luma not to talk about it, so nothing is closed.
- **Only the wish to vent** ("I don't need advice, I just need to vent"): "Okay. No advice, I'm just listening. Go
  ahead." With anything else in the message (what happened), the brain answers it, told how to be with them.
- **The name stays out.** A reply that names an ex they've closed is cut to the sentences that don't, unless they said
  the name themselves or asked about their ex.

Never in kids mode. Anything the safety readers read is never an answer to one of Luma's questions, and the crisis net
has already answered before any of this runs. "Forget everything" forgets it all.
"""
from __future__ import annotations

import re
from datetime import datetime

KEY = "exes"            # [{"name", "was", "at", "closed"}]: who their exes are
ASKED = "ex_asked"      # the question Luma is waiting on: {"kind": "name" | "confirm", "name", "was", "id", "at"}
WAITS = 600             # seconds an answer to that question is listened for

PARTNERS = r"boyfriend|girlfriend|partner|husband|wife|fianc[eé]e?|bf|gf|man|woman"
_NAME = r"[A-Z][a-z]+(?:[-'][A-Z]?[a-z]+)?(?: [A-Z][a-z]+)?"
# "my boyfriend's name is Caden", "my boyfriend is Caden", "Caden is my boyfriend", "my boyfriend Caden ..."
PARTNER_FACT = re.compile(rf"(?i:\bmy (?P<rel>{PARTNERS})(?:'s name)? (?:is|was) )(?P<name>{_NAME})\b|"
                          rf"\b(?P<name2>{_NAME})(?i: (?:is|was) my (?P<rel2>{PARTNERS}))\b")
PARTNER_SAID = re.compile(rf"(?i:\bmy (?P<rel>boyfriend|girlfriend|partner|husband|wife|fianc[eé]e?) )(?P<name>{_NAME})\b")
EX_FACT = re.compile(rf"(?i:\bmy ex(?:-?(?:{PARTNERS}))?(?:'s name)? is )(?P<name>{_NAME})\b|\b(?P<name2>{_NAME})(?i: is my ex)\b")
EX_TOPIC = re.compile(r"^(?:my |the |our )?ex(?:\b|-)", re.I)
NOT_A_NAME = {"I", "It", "That", "This", "He", "She", "They", "We", "My", "The", "Me", "And", "But", "So", "Ok", "Okay", "Yeah", "Yes", "No",
              "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Today", "Tonight", "Tomorrow", "Lol", "Idk",
              "Ugh", "Nope", "Nah", "Never", "Nothing", "Nobody", "Whatever", "Why", "What", "Who", "Forget", "Just"}

BROKE = re.compile(
    rf"^\W*(?:(?:so|well|yeah|ugh|update|welp|honestly)\W+)*(?:"
    rf"(?P<a>{_NAME}) and i (?:broke up|split up|called it quits|aren'?t together anymore|are not together anymore|are done|ended (?:it|things))|"
    rf"(?:me and|i and) (?P<b>{_NAME}) (?:broke up|split up|called it quits)|"
    rf"i (?:broke up with|dumped|left|ended (?:it|things) with) (?:my (?P<rel_c>{PARTNERS})|(?P<c>{_NAME}))|"
    rf"(?:my (?P<rel_d>{PARTNERS})|(?P<d>{_NAME})) (?:broke up with me|dumped me|left me|ended (?:it|things) with me)|"
    rf"(?:it'?s|its) over (?:between me and|with) (?P<e>{_NAME})|"
    rf"(?P<f>{_NAME}) is my ex(?: now)?|"
    rf"my (?P<rel_g>{PARTNERS}) and i (?:broke up|split up|called it quits|aren'?t together anymore)|"
    rf"we (?:broke up|split up|called it quits|aren'?t together anymore|are not together anymore|'re not together anymore|re not together anymore)"
    rf")\b(?![^.!?]*\b(?:again|on this|on that|the bill|the work|into)\b)", re.I)

NAME_SAID = re.compile(rf"^\W*(?:ugh|well|oh|um|uh)?\W*(?:(?:his|her|their) name(?:'s| is| was)|it'?s|it was|they'?re called|(?:he|she)'?s called)?\s*"
                       rf"(?P<name>[A-Za-z][a-z]+(?:[-'][A-Za-z]?[a-z]+)?(?: [A-Z][a-z]+)?)\W*(?:lol|lmao|haha)?\W*$", re.I)
DECLINE = re.compile(r"\b(?:rather not|don'?t want to|dont want to|never ?mind|forget it|doesn'?t matter|move on|skip it|no thanks|not saying|pass)\b|^\W*(?:no|nope|nah)\W*$", re.I)
YES = re.compile(r"^\W*(?:yes|yeah|yep|yup|ya|mhm|correct|right|he is|she is|they are|sadly|unfortunately|yes sadly)\b", re.I)
NO = re.compile(r"^\W*(?:no|nope|nah|not him|not her|not them|different (?:guy|girl|person|one))\b", re.I)

VENT_ONLY = re.compile(
    r"^\W*(?:(?:i )?(?:don'?t|do not|dont) (?:need|want) (?:any )?(?:advice|solutions|fixing|you to fix (?:it|anything))[,.;]?\s*|"
    r"(?:no|not looking for) advice(?: please)?[,.;]?\s*)?"
    r"(?:(?:can (?:you|u) )?just (?:listen|let me (?:vent|rant))(?: to me)?(?: for a (?:sec|second|minute|bit))?|"
    r"(?:i )?(?:just )?(?:need|want|wanna|gotta) to (?:vent|rant)(?: for a (?:sec|second|minute|bit))?|can i (?:vent|rant)(?: to you)?)"
    r"(?:\W+(?:ok|okay|please|pls|rn))*\W*$", re.I)


def _now(agent):
    return agent.clock()


def _when(agent):
    try:
        return datetime.fromtimestamp(_now(agent), agent.zone).strftime("%b %-d, %Y")
    except Exception:
        return ""


def _proper(name):
    return " ".join(part[:1].upper() + part[1:] for part in str(name).split())


def known(agent):
    """Their exes: [{"name", "was", "at", "closed"}]."""
    rows = agent.store.setting(KEY)
    return [r for r in rows if isinstance(r, dict) and r.get("name")] if isinstance(rows, list) else []


def ex_names(agent, closed_only=False):
    return [r["name"] for r in known(agent) if r.get("closed") or not closed_only]


def _memories(agent, words):
    found = agent.store.mentioning(words)
    if found is None:
        found = agent.store.all("memory", 100000)
    return [m for m in found or [] if isinstance(m.get("text"), str)]


def partner(agent):
    """The partner Luma knows of who isn't an ex: {"name", "was", "id"} or None. The newest one said."""
    exes = {n.lower() for n in ex_names(agent)}
    best = None
    for word in ("boyfriend", "girlfriend", "partner", "husband", "wife", "fiance", "fiancee", "fiancé", "bf", "gf"):
        for m in _memories(agent, [word]):
            if m.get("source") == "said":
                continue   # what they said, as they said it, stays as it was: only a fact card says who's who
            hit = PARTNER_FACT.search(m["text"]) or PARTNER_SAID.search(m["text"])
            if not hit or re.search(r"\bused to be\b|\bmy ex\b", m["text"], re.I):
                continue
            name, rel = hit.groupdict().get("name") or hit.groupdict().get("name2"), hit.groupdict().get("rel") or hit.groupdict().get("rel2")
            if not name or name in NOT_A_NAME or name.lower() in exes:
                continue
            at = float(m.get("created") or m.get("at") or 0)
            if best is None or at >= best["at"]:
                best = {"name": name, "was": rel.lower(), "id": m.get("id"), "at": at}
    return best


def notice_partner(agent, text):
    """"my boyfriend Caden is taking me to dinner": the partner's name, said in passing, is kept as a card."""
    if agent.mode == "kids" or not agent.store.setting("learn_from_chat", True):
        return None
    m = PARTNER_SAID.search(str(text or ""))
    if not m or m["name"] in NOT_A_NAME or m["name"].lower() in {n.lower() for n in ex_names(agent)}:
        return None
    rel = m["rel"].lower()
    return agent.remember_fact(f"My {rel}'s name is {m['name']}", source="noticed_in_conversation")


def closing(text):
    """The subject this message closes, when closing it is the whole of what they said; or ""."""
    from luma.agent import rapport
    said = " ".join(str(text or "").split())
    if len(said.split()) > 14 or said.count("?") or re.search(r"[.!;]\s+\w", said.rstrip(".! ")):
        return ""
    m = rapport.CLOSED.search(said)
    if not m or m.start() > 12:
        return ""
    topic = " ".join(m["what"].split()).strip(" .,'")
    if topic.lower() in rapport.NOT_A_SUBJECT:
        return ""
    tail = said[m.end():].strip(" .,!")
    if tail and not re.fullmatch(r"(?:again|anymore|any more|right now|today|tonight|please|pls|ok|okay|ever|at all|for now|seriously|i mean it|thanks|thank you)(?:[ ,]+\w+)*", tail, re.I):
        return ""
    return topic


def broke_up(text):
    """(name or None, the word for who they were or None) when they say they broke up; None otherwise."""
    m = BROKE.search(" ".join(str(text or "").split()))
    if not m:
        return None
    g = m.groupdict()
    name = next((g[k] for k in "abcdef" if g.get(k) and not g[k].lower().startswith("my ")), None)
    if name and " " in name and not name.split()[1][0].isupper():
        name = name.split()[0]   # read without case: "Caden last night" is Caden
    if name:
        if _proper(name).split()[0] in NOT_A_NAME:
            return None
        if not name[0].isupper():   # read without case, so a name typed in lowercase counts; an everyday word doesn't
            from luma.agent import pickup
            if name.split()[0].lower() in pickup.everyday():
                return None
        name = _proper(name)
    rel = next((g[k] for k in ("rel_c", "rel_d", "rel_g") if g.get(k)), None)
    return (name, rel.lower() if rel else None)


def name_in(text):
    """The name in their answer to "what's their name?", or None."""
    said = " ".join(str(text or "").split())
    if not said or len(said.split()) > 6 or DECLINE.search(said):
        return None
    m = NAME_SAID.match(said)
    if not m:
        return None
    name = _proper(m["name"])
    first = name.split()[0]
    if first in NOT_A_NAME:
        return None
    if not m["name"][0].isupper() and " " not in m["name"]:
        from luma.agent import pickup
        if m["name"].lower() in pickup.everyday() or len(m["name"]) < 2:
            return None
    return name


def _closed_topic(agent, name, said):
    """The name joins the subjects they've closed, so a check-in never asks about them and the brain is told."""
    from luma.agent import rapport
    profile = rapport._clean(agent.store.setting(rapport.KEY))
    if not any(e["topic"].lower() == name.lower() for e in profile["easy"]):
        profile["easy"].append({"topic": name, "said": rapport._quote(said), "at": float(_now(agent))})
        del profile["easy"][:-rapport.EASY_KEEP]
        agent.store.set_setting(rapport.KEY, profile)


def make_ex(agent, name, was=None, card=None, closed=True, said=""):
    """Keep that this person is their ex, with when and who they'd been; and, when the subject is closed, never raise them."""
    name = _proper(name)
    rows = [r for r in known(agent) if r["name"].lower() != name.lower()]
    before = next((r for r in known(agent) if r["name"].lower() == name.lower()), {})
    rows.append({"name": name, "was": was or before.get("was"), "at": _now(agent), "closed": bool(closed or before.get("closed"))})
    agent.store.set_setting(KEY, rows[-200:])
    day = _when(agent)
    text = f"My ex is {name}" + (f". {name} used to be my {was}" if was else "") + (f". Told Luma on {day}" if day else "")
    if closed:
        text += f". I'd rather Luma didn't bring {name} up"
    try:
        agent.remember_fact(text, source="noticed_in_conversation")
    except Exception:
        pass
    if card:   # the old cards aren't true anymore: each says what it used to be. What they said stays as they said it.
        for old in _memories(agent, [name.split()[0].lower()]):
            hit = PARTNER_FACT.search(old["text"]) or PARTNER_SAID.search(old["text"])
            if old.get("source") != "said" and hit and (hit.groupdict().get("name") or hit.groupdict().get("name2") or "").lower() == name.lower():
                rel = (hit.groupdict().get("rel") or hit.groupdict().get("rel2") or was or "partner").lower()
                agent.store.put("memory", {**old, "text": f"{name} used to be my {rel}"}, id=old["id"])
    if closed:
        _closed_topic(agent, name, said or f"don't bring up {name}")


def _ask(agent, **what):
    agent.store.set_setting(ASKED, {**what, "at": _now(agent)})


def answer(agent, text):
    """Their answer to the question Luma asked about their ex, or None when this isn't one (it's then read as usual)."""
    from luma.agent import friendcheck
    asked = agent.store.setting(ASKED)
    if not isinstance(asked, dict):
        return None
    agent.store.set_setting(ASKED, None)   # one message, and only that one, can answer it
    said = " ".join(str(text or "").split())
    if _now(agent) - float(asked.get("at") or 0) > WAITS or friendcheck.at_risk(said) or friendcheck.worth_asking(said):
        return None
    if asked.get("kind") == "confirm":
        if YES.match(said) and len(said.split()) <= 8:
            make_ex(agent, asked["name"], asked.get("was"), card={"id": asked.get("id")}, said=said)
            return "Got it. I've noted that, and I won't bring them up."
        if NO.match(said) and len(said.split()) <= 8:
            _ask(agent, kind="name")
            return "Okay, my mistake. What's their name, so I never bring them up by accident? You don't have to tell me."
        return None
    if DECLINE.search(said) and len(said.split()) <= 8:
        return "That's fine. I won't bring them up."
    name = name_in(said)
    if name:
        make_ex(agent, name, said=said)
        return "Got it. I won't say it."
    return None


def acknowledge(agent, text):
    """Luma's own reply when they close a subject in so many words, or None."""
    topic = closing(text)
    if not topic:
        return None
    if not EX_TOPIC.match(topic):
        return "Okay. I won't bring that up."
    exes = known(agent)
    if exes:
        for row in exes:
            if not row.get("closed"):
                make_ex(agent, row["name"], row.get("was"), said=text)
        return "Okay. I won't bring them up again."
    who = partner(agent)
    if who:
        _ask(agent, kind="confirm", name=who["name"], was=who["was"], id=who.get("id"))
        return f"Okay, I won't bring it up. Just so I keep it straight: is {who['name']} your ex now?"
    _ask(agent, kind="name")
    return "Okay, I won't bring them up. So I never slip and say it by accident, what's their name? You don't have to tell me."


def heard(agent, text):
    """Everything this module does with a message, after the crisis net and before the brain. Returns Luma's reply, or
    None for the brain to answer (having kept what it could)."""
    from luma.agent import friendcheck
    if agent.mode == "kids":
        return None
    said = " ".join(str(text or "").split())
    if not said or friendcheck.at_risk(said):
        return None
    if agent.store.setting(ASKED):
        reply = answer(agent, said)
        if reply:
            return reply
    reply = acknowledge(agent, said)
    if reply:
        return reply
    split = broke_up(said)
    if split:
        name, was = split
        who = partner(agent)
        if name is None and who and (was is None or was == who["was"]):
            make_ex(agent, who["name"], who["was"], card=who, closed=False, said=said)
        elif name:
            make_ex(agent, name, was or (who["was"] if who and who["name"].lower() == name.lower() else None),
                    card=who if who and who["name"].lower() == name.lower() else None, closed=False, said=said)
    notice_partner(agent, said)
    if VENT_ONLY.match(said):
        return "Okay. No advice, I'm just listening. Go ahead."
    return None


def keep_out(agent, said, reply):
    """A reply that names an ex they've closed, when they didn't say the name and didn't ask about their ex, loses the
    sentences that do."""
    if not isinstance(reply, str) or agent.mode == "kids":
        return reply
    names = ex_names(agent, closed_only=True)
    said = str(said or "")
    if not names or re.search(r"\bex\b", said, re.I):
        return reply
    if "?" in said and re.search(rf"\b(?:{PARTNERS}|dating|seeing)\b", said, re.I):
        return reply   # "what's my boyfriend's name?": they asked, so they're told (Caden is their ex now)
    named = [n for n in names if re.search(rf"\b{re.escape(n)}\b", reply, re.I) and not re.search(rf"\b{re.escape(n)}\b", said, re.I)]
    if not named:
        return reply
    pattern = re.compile("|".join(rf"\b{re.escape(n)}\b" for n in named), re.I)
    parts = re.split(r"(?<=[.!?])\s+", reply.strip())
    kept = [p for p in parts if not pattern.search(p)]
    return " ".join(kept) if kept else "I'm here. Go on."
