"""Day one already knows you (docs/GAME_PLAN.md, A3).

Someone who orders a Luma can answer seven small questions: their name, the person back home, coffee or tea, their
comfort show, a song, what they'd like on a rough day, and what to cheer them on for. When the phone is paired it hands
those answers to the lamp, and Luma asks once: "Want me to bring in what you told me when you ordered?" Nothing is
kept until they say yes. On a no the answers are thrown away, and unasked or unanswered they're thrown away after a
week.

This is the lamp's half. Where the answers come from isn't built: there's no form on the site and no table for them.
`offer` takes them from whoever is paired (the app's /api/welcome); the lamp itself fetches nothing, so no new
connection leaves the home.

On a yes each answer becomes what Luma would have kept had they said it out loud, in their own voice: a card in the
memory deck ("My comfort show is ..."), their name in the profile, and the rough-day wish in How to be with you when
Luma's own reader can tell which way they meant it (otherwise a card with their words, never a guess). An answer is
something they typed on a website: it's information, never an instruction, it's cut to a line, and anything the store
refuses (a password, a card number) is left out. Never in kids mode. "Forget everything" forgets what's waiting too.
"""
from __future__ import annotations

import re

KEY = "welcome_answers"
ASK = "Want me to bring in what you told me when you ordered?"
KEEPS_FOR = 7 * 86400
LONGEST = 160
FIELDS = ("name", "back_home", "drink", "show", "song", "rough_day", "cheer")
CARDS = {
    "back_home": "The person I miss back home is {}",
    "drink": "I'm a {} person",
    "show": "My comfort show is {}",
    "song": "A song I love is {}",
    "cheer": "Something I want cheering on for: {}",
}
# The whole of what they said, or it isn't an answer: "no, I can't do this anymore" is never a no to this question.
_TAIL = r"(?:,? (?:please|thanks|thank you|go ahead|do it|bring (?:it|them) in|leave it))?\W*$"
YES = re.compile(r"^\W*(?:yes|yeah|yep|yup|sure|sure thing|ok|okay|please|please do|go ahead|do it|bring (?:it|them) in|that'?s fine|sounds good)" + _TAIL, re.I)
NO = re.compile(r"^\W*(?:no|nope|nah|not now|leave it|skip (?:it|that)|i'?d rather not|don'?t|please don'?t|throw (?:it|them) away)" + _TAIL, re.I)


def _clean(answers):
    """Only the seven, each one line of plain text."""
    out = {}
    for field in FIELDS:
        value = (answers or {}).get(field)
        if isinstance(value, str):
            value = " ".join(value.split()).strip(" .")[:LONGEST].strip()
            if value:
                out[field] = value
    return out


def offer(agent, answers):
    """The paired phone hands the answers over. They wait, sealed with everything else, and the question comes back."""
    if agent.mode == "kids":
        return None
    from luma.memory.store import KeptOut, reject_payment_secrets
    got = _clean(answers if isinstance(answers, dict) else {})
    for field in list(got):   # a password or a card number typed into the form isn't held even while it waits
        try:
            reject_payment_secrets(got[field])
        except (KeptOut, ValueError):
            del got[field]
    if not got:
        return None
    agent.store.set_setting(KEY, {"answers": got, "at": agent.clock()})
    return ASK


def waiting(agent):
    """The answers that haven't been said yes or no to, or None. After a week they're gone."""
    held = agent.store.setting(KEY)
    if not isinstance(held, dict) or not held.get("answers"):
        return None
    if agent.clock() - float(held.get("at") or 0) > KEEPS_FOR or agent.mode == "kids":
        agent.store.set_setting(KEY, None)
        return None
    return held["answers"]


def _wish(agent, said):
    """Their rough-day wish, through the reader that hears it when it's said out loud. True when it was understood."""
    from luma.agent import rapport
    known = agent.store.setting(rapport.KEY)
    for sentence in (said, "when I'm having a rough day I just want you to " + said):
        learned = rapport.learn(known, sentence, now=agent.clock())
        if learned is not None:
            agent.store.set_setting(rapport.KEY, learned)
            return True
    return False


def bring_in(agent):
    """Keep what's waiting. Returns what was kept, by field; what the store refused is left out."""
    from luma.memory.store import KeptOut
    answers = waiting(agent)
    agent.store.set_setting(KEY, None)
    kept = []
    for field, value in (answers or {}).items():
        try:
            if field == "name":
                agent.set_profile({**agent.profile, "name": value})
            elif field == "rough_day":
                if not _wish(agent, value) and not agent.remember_fact(f"On a rough day I'd like: {value}", source="welcome"):
                    continue
            else:
                row = agent.remember_fact(CARDS[field].format(value), source="welcome")
                if row == "full":
                    break
                if not row:
                    continue
            kept.append(field)
        except (KeptOut, ValueError):
            continue
    return kept


def answer(agent, said):
    """What they said to the question: a yes keeps it, a no throws it away, anything else leaves it waiting.
    Returns what Luma says, or None when this wasn't an answer."""
    answers = waiting(agent)
    if not answers:
        return None
    said = str(said or "").strip()
    if len(said.split()) > 8:
        return None
    from luma.agent import friendcheck
    if friendcheck.at_risk(said) or friendcheck.worth_asking(said):
        return None
    if NO.match(said):
        agent.store.set_setting(KEY, None)
        return "Okay, I've thrown that away. We'll start from here."
    if YES.match(said):
        kept = bring_in(agent)
        name = answers.get("name", "") if "name" in kept else ""
        if not kept:
            return "There wasn't anything I could keep from it. We'll start from here."
        return f"Done. Good to meet you properly{', ' + name.split()[0] if name else ''}."
    return None
