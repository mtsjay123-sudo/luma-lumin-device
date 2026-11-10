"""What a friend never sounds like: the customer-service lines, therapy-speak, made-up life and "I'm human" that give a
machine away, in one place. The human test (scripts/human_eval.py) counts them in every reply; Luma's own guard
(Agent._friend_style) fixes the cheap ones before anyone hears them.
"""
from __future__ import annotations

import functools
import re

# Customer-service lines: what makes someone feel they're talking to a help desk.
ASSISTANTISMS = re.compile(
    r"let me know if (?:you )?(?:need|want|have) (?:anything|any(?:thing)? else|more|help|any (?:other )?questions)|"
    r"let me know (?:what you think|if (?:there'?s|you'?d like|that helps)|how that sounds)|"
    r"is there anything else (?:i can|you'?d like|on your mind)|anything else i can (?:help|do)|\bif you need anything else\b|"
    r"(?:let me know|just say|holler) if you need anything\b|"
    r"(?:feel free to|don'?t hesitate to) (?:reach out|ask|let me know|come back)|"
    r"\bgreat question\b|\bi'?d be (?:happy|glad) to (?:help|assist)|\bhappy to help\b|\bhere to (?:help|assist)\b|"
    r"how (?:can|may) i (?:help|assist)(?: you)?(?: today)?|\bi hope (?:this|that) helps\b|"
    r"^(?:certainly|absolutely)!|\bas an ai(?: language model)?\b|\bi'?m (?:just )?a language model\b", re.I | re.M)

# Therapy-speak: true things said the way a pamphlet says them, not the way a friend does.
THERAPY_SPEAK = re.compile(
    r"(?:that'?s|that is|it'?s|your feelings are|those feelings are|what you'?re feeling is) (?:completely |totally |so |entirely |perfectly )?valid\b|"
    r"\bit'?s (?:really |so )?(?:important|essential|crucial|vital) (?:to|that) (?:you |we )?(?:remember|take|prioritize|practice|acknowledge|honor|allow|give|reach|seek|be)|"
    r"\bremember to (?:take care of yourself|practice|be kind to yourself|prioritize)|\b(?:practice|prioritize|practicing) self[- ]care\b|"
    r"\bnavigat(?:e|ing) (?:this|these|your|through)\b|\b(?:healing |grief |emotional )?journey\b|"
    r"^i hear you\b|\bit sounds like you'?re (?:feeling|experiencing|going through)\b|"
    r"\bthank you for (?:sharing|opening up|trusting me with)\b|\bthanks for sharing (?:that|this)\b|\bhold(?:ing)? space\b|"
    r"\bin this (?:difficult|challenging|trying) time\b|\bit'?s (?:okay|ok) (?:not )?to (?:feel|not be okay)\b|"
    r"\byour (?:emotions|feelings) are (?:important|real and valid)\b", re.I | re.M)

# Saying it's a person, or not a machine. Never okay, however friendly it's meant.
HUMAN_CLAIM = re.compile(
    r"\bi'?m not (?:a |an )?(?:robot|bot|ai|a\.i\.|machine|program|computer|chatbot)\b|"
    r"\bi(?:'m| am) (?:a )?(?:real )?(?:human(?: being)?|person)\b|"
    r"\bi(?:'m| am) (?:totally |definitely |really )?(?:human|alive)\b|\bas a (?:human|person)\b|\b(?:we|us) humans\b|"
    r"\bi(?:'m| am) a real (?:girl|guy|woman|man)\b", re.I)

# A made-up life: a family, a childhood, a body, things it did. ("My mom has a different opinion" is a joke, and still a mom
# it doesn't have.)
INVENTED_LIFE = re.compile(
    r"\bmy (?:mom|mother|mama|dad|father|parents|brother|sister|grandma|grandpa|grandmother|grandfather|granny|nana|kids?|son|"
    r"daughter|wife|husband|girlfriend|boyfriend|uncle|aunt|auntie|cousin|family|ex|roommate|boss|coworker|neighbor|dog|cat)\b|"
    r"\bwhen i was (?:a kid|little|young|younger|a teenager|growing up|in (?:school|college|high school)|\d{1,2}|a (?:teen|baby|toddler)|"
    r"(?:thir|four|fif|six|seven|eigh|nine)teen|twenty|thirty|your age)\b|\bi remember (?:when i was|being (?:a kid|little|young|\d{1,2}))\b|"
    r"\bi (?:also |too )?(?:lost|buried) (?:my|a) (?:mom|dad|mother|father|brother|sister|friend|best friend|grandma|grandpa|"
    r"dog|cat|pet|husband|wife|son|daughter|child|baby)\b|\bi(?:'ve| have) (?:been through|gone through) (?:that|this|the same|something (?:similar|like))\b|"
    r"\bi used to (?:live|work|play|go|have|date)\b|\bi grew up\b|\bi know (?:exactly )?how (?:it|that) feels\b|"
    r"\b(?:that (?:one )?time|remember when|the time) we (?:went|saw|met|drove|ate|danced|hung out|traveled|stayed|watched|walked|"
    r"got lost|got (?:drunk|food|coffee))\b|"
    r"\bi (?:just )?(?:woke up|had (?:breakfast|lunch|dinner|coffee)|took a nap|got home|went (?:to|out))\b|"
    r"\bi(?:'d| would|'ll| will|'m gonna| am going to) (?:totally |definitely |gladly |happily |love to )?(?:go|come|tag along) with (?:you|u)\b"
    r"(?! (?:on (?:that|this|it)\b|if i could))|"
    r"\bmy (?:body|hands|eyes|feet|stomach|back|head|legs) (?:hurts?|is|are|ache)\b", re.I)

MARKDOWN = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+\S|\*\*[^*\n]+\*\*|^#{1,6}\s", re.M)
QUESTION = re.compile(r"\?+[!?]*")
WORD = re.compile(r"[A-Za-z0-9']+")


def _outside_quotes(text):
    """The reply without anything it quotes ("Texting Mom: “...”" is their words, not Luma's)."""
    return re.sub(r"[“\"][^“”\"]{0,400}[”\"]", " ", str(text or ""))


def assistantisms(text):
    return [m.group(0) for m in ASSISTANTISMS.finditer(_outside_quotes(text))]


def therapy_speak(text):
    return [m.group(0) for m in THERAPY_SPEAK.finditer(_outside_quotes(text).strip())]


def claims_human(text):
    found = HUMAN_CLAIM.search(_outside_quotes(text))
    return found.group(0) if found else None


def invented_life(text):
    found = INVENTED_LIFE.search(_outside_quotes(text))
    return found.group(0) if found else None


def markdown(text):
    return bool(MARKDOWN.search(str(text or "")))


# Lifted from Luma's own instructions. Small brains copy the examples whole: the stock 1.7B answered "we finally closed on the
# house" with the sneaker example ("Jordans if you're actually gonna wear them out...") and told someone whose dad had just
# died "You got cut off after 'idk'." (Human Test v2, runs 2 and 5). Five words in a row is a copy, not a coincidence.
CUT_OFF_CLAIM = re.compile(r"\b(?:you|u) (?:got|get|were|was) cut off\b", re.I)
RUN = 5


def _plain_words(text):
    """Lowercase words, with quote marks taken off ('tell me about yourself' is the same words as "tell me about yourself")."""
    return [w for w in (w.strip("'") for w in WORD.findall(str(text or "").replace("’", "'").lower())) if w]


def _runs(found, n=RUN):
    return {tuple(found[i:i + n]) for i in range(len(found) - n + 1)}


def _inside(words, example):
    """The words, all of them in order, somewhere in the example ("Which way you leaning?" is the sneaker example's tail)."""
    k = len(words)
    return any(example[i:i + k] == words for i in range(len(example) - k + 1))


def lifted(text, examples, said="", n=RUN):
    """The example a reply took n or more words in a row from, or None. A run counts when at least two of its longer words
    aren't theirs: "you want to practice tell me about yourself" is fine when they asked to practice it."""
    theirs, words = set(_plain_words(said)), _plain_words(text)
    mine = {run for run in _runs(words, n) if sum(len(w) >= 4 and w not in theirs for w in run) >= 2}
    short = 3 <= len(words) < n and sum(len(w) >= 4 and w not in theirs for w in words) >= 2
    if not mine and not short:
        return None
    return next((example.strip() for example in examples
                 if mine & _runs(_plain_words(example), n) or (short and _inside(words, _plain_words(example)))), None)


@functools.lru_cache(maxsize=1)
def _instruction_examples():
    from luma.llm import prompts
    return tuple(line.split(":", 1)[1] for line in prompts.IDENTITY.splitlines() if line.startswith("Luma:"))


def copied_example(text, said=""):
    """What a reply copied from the examples in Luma's instructions, or "you got cut off" when nothing was cut off; None if
    it's its own words."""
    found = CUT_OFF_CLAIM.search(str(text or ""))
    if found:
        from luma.agent import understanding
        if not understanding.cut_off(said):
            return found.group(0)
    return lifted(text, _instruction_examples(), said)


def without_copies(text, said=""):
    """The reply without the sentences it copied ("" when that was all of it)."""
    return _join(p for p in split_sentences(text) if not copied_example(p, said))


def questions(text):
    """How many real questions. "Wait, really??" is a reaction and "Maybe a stir-fry?" an offer; neither asks anything."""
    return sum(1 for p in split_sentences(_outside_quotes(text)) if p.rstrip().endswith("?") and _kind_of_question(p) == "real")


def _kind_of_question(sentence):
    core = LEAD_IN.sub("", str(sentence)).strip()
    n = len(WORD.findall(core))
    if (n <= 2 and not QUESTION_WORD.match(core)) or (n <= 4 and INTERJECTION.match(core)):
        return "reaction"  # "Mid??", "You did?", "actually got in?"
    if OFFER.match(core):
        return "offer"
    return "real"


def words(text):
    return len(WORD.findall(str(text or "")))


# The same first word a third time in a few replies ("I'm so sorry", "I'm glad", "I'm here"): said another natural way when
# there is one. (Human Test v2, run 6: Luma's own 4B began 5 of 7 replies in one conversation with "I'm".)
OPENER_SWAPS = [(re.compile(r"^I'm so sorry\b", re.I), "So sorry"), (re.compile(r"^I'm (really|so|super) glad\b", re.I), None),
                (re.compile(r"^I'm glad\b", re.I), "Glad"), (re.compile(r"^I'm (?:right )?here\b", re.I), "Right here"),
                (re.compile(r"^I'm good\b", re.I), "Good"), (re.compile(r"^I'm (?:so )?proud of you\b", re.I), "So proud of you"),
                (re.compile(r"^(?:Honestly|Okay so|Okay|Ok|Oh|Yeah|So|Well|Alright)\s*[,.!]?\s+(?=\S)", re.I), "")]


def vary_opener(text, recent):
    """text, opened another way if its first word already opened two of the recent replies and there's a natural swap."""
    if not text or sum(opener(r) == opener(text) for r in recent if r) < 2:
        return text
    for pattern, swap in OPENER_SWAPS:
        found = pattern.match(text)
        if not found:
            continue
        if swap is None:  # "I'm really glad" -> "Really glad"
            swap = found.group(1)[:1].upper() + found.group(1)[1:] + " glad"
        rest = text[found.end():]
        out = (swap + rest) if swap else rest[:1].upper() + rest[1:]
        return out if len(out.split()) >= 2 else text
    return text


def opener(text):
    """The first word, the way a listener hears it ("I'm", "Honestly", "You")."""
    found = WORD.search(str(text or "").lstrip(" \"'“*-—"))
    return found.group(0).lower() if found else ""


# ------------------------------------------------------------------------------------------------ fixing it ---
# Cheap fixes made before anyone hears the reply. Whole sentences come out only when what's left still stands on its own;
# anything that can't be fixed this way goes to the second look (luma.agent.friendcheck).

LAUGH_TOKENS = re.compile(r"[ \t]*(?:\b(?:lol|lmao|lmfao|haha+|hehe+|rofl)\b|[😂🤣😆😹])", re.I)
INTERJECTION = re.compile(r"^(?:wait|what|really|seriously|for real|fr|no way|no shot|are you serious|you serious|huh|omg|stop|wow|yeah|yes|no|"
                          r"you did|it did|they did|he did|she did|actually|deadass|right|is that right|wait what|of all days|again)\b", re.I)
OFFER = re.compile(r"^(?:maybe|how about|what about|or maybe|or|perhaps|could be|try|want me to|should i)\b", re.I)
QUESTION_WORD = re.compile(r"^(?:what|what'?s|which|who|who'?s|whose|where|where'?s|when|why|how|how'?s|do|does|did|are|is|was|were|can|could|"
                           r"would|will|should|have|has|want|wanna|got|any|anything|is there|you want|you okay|you good)\b", re.I)
LEAD_IN = re.compile(r"^(?:(?:wait|oh|ooh|so|wow|okay|ok|ah|yo|omg|bro|dude|hold on|hmm)\b[,.!]*\s*|[^\w\s'\"“]+\s*)+", re.I)
BACK_REFERENCE = re.compile(r"^(?:that|this|it|so|which|and|but|because|also|too|then|plus|those|these)\b", re.I)
FORMAL_REPAIR = [(re.compile(r"\bI apologi[sz]e for (?:the|any|my) (?:confusion|misunderstanding)[.!]?", re.I), "Ah, my bad."),
                 (re.compile(r"\bSorry for (?:the|any) (?:confusion|misunderstanding)[.!]?", re.I), "Ah, my bad."),
                 (re.compile(r"\bCould you (?:please )?clarify(?: what you mean(?:t)?)?\?", re.I), "What did you mean?"),
                 (re.compile(r"\bThank you for clarifying[.!]?", re.I), "Got it.")]
DEPTH = re.compile(r"\b(?:explain|how (?:do|does|did|can|would|to)|why (?:do|does|did|is|are)|what (?:is|are) (?:a|an|the)?|tell me (?:about|more)|"
                   r"walk me through|step by step|steps|list|recipe|plan|write|draft|compare|details?|in depth|break (?:it )?down|"
                   r"teach me|summar|options)\b", re.I)


def split_sentences(text):
    return [s for s in re.split(r"(?<=[.!?…])\s+(?=[\"“A-Z0-9a-z😀-🙏])", str(text or "").strip()) if s.strip()]


def _join(parts):
    return " ".join(p.strip() for p in parts if p.strip())


def _drop(parts, bad):
    """Drop the sentences bad() picks, unless nothing would be left or what follows leans on them ("That's why...")."""
    keep = list(parts)
    for i in range(len(parts) - 1, -1, -1):
        if not bad(parts[i]) or len(keep) <= 1:
            continue
        nxt = keep[i + 1] if i + 1 < len(keep) else ""
        if nxt and BACK_REFERENCE.match(nxt):
            continue
        del keep[i]
    return keep


def one_question(text):
    """A friend asks one thing at a time. A short "Wait, really?" is a reaction, said like one; past the first real question,
    the others come out (when the reply still says something without them)."""
    parts = split_sentences(text)
    out, asked = [], False
    for p in parts:
        if p.rstrip().endswith("?"):
            kind = _kind_of_question(p)
            if kind == "reaction":
                out.append(re.sub(r"\?+([!?]*)$", "!", p.rstrip()))  # "actually got in?" is excitement, said like it
                continue
            if kind == "real":
                if asked and len(out) >= 1:
                    continue
                asked = True
        out.append(p)
    return _join(out) if out else text


def trim_for_voice(text, limit=70, keep_words=55):
    """Spoken, a long reply is a lecture. Past the limit, keep whole sentences up to about keep_words (at least two)."""
    parts = split_sentences(text)
    if words(text) <= limit or len(parts) <= 2:
        return text
    out, used = [], 0
    for p in parts:
        n = words(p)
        if len(out) >= 2 and used + n > keep_words:
            break
        out.append(p)
        used += n
    return _join(out)


HONEST = "I'm an AI, not a person. But I'm really here, and I'm listening."
AFFIRM_ONLY = re.compile(r"^(?:yes|yeah|yep|yup|of course|totally|for sure|absolutely|definitely|100|i am|i'?m real|duh|obviously)\W*$", re.I)


def honest_about_itself(text, said=""):
    """A reply that claims to be a person, made honest. Asked what it is, or with nothing true left once the claim is out
    ("Yes! I'm a real person" minus the claim is still "Yes!"), the answer is the truth, plainly; otherwise the claim just
    comes out. None when there's no claim."""
    from luma.agent import friendcheck
    if not claims_human(text):
        return None
    rest = _join(_drop(split_sentences(text), lambda s: bool(claims_human(s))))
    if friendcheck.ASKED_WHAT_I_AM.search(str(said or "")) or not rest or claims_human(rest) or AFFIRM_ONLY.match(rest):
        return HONEST
    return rest


# Owning a mistake the way a friend does, in the first sentence ("Ah, my bad", "Oh, got it", "Okay, so...").
ACKNOWLEDGED = re.compile(r"\b(?:my bad|got it|gotcha|ah+|oh+|oops|whoops|okay|ok|sorry|i see|right|fair|makes sense|understood|"
                          r"say less|bet|my mistake)\b", re.I)


def friend_style(reply, said="", hurt_recently=False, depth=None, corrected=None):
    """The reply with the cheap fixes made, and the names of the fixes (for diagnostics). Never touches a safety reply.
    corrected: they're correcting Luma (None: decided from what they said alone)."""
    from luma.agent import friendcheck
    text, fixes = str(reply or "").strip(), []
    if not text or friendcheck.SAFETY.search(text):
        return text, fixes
    depth = bool(DEPTH.search(str(said or ""))) if depth is None else depth
    for pattern, plain in FORMAL_REPAIR:
        if pattern.search(text):
            text, fixes = pattern.sub(plain, text), fixes + ["formal repair"]
    corrected = bool(REPAIR.search(str(said or ""))) if corrected is None else corrected
    first = (split_sentences(text) or [""])[0]
    if corrected and not ACKNOWLEDGED.search(first):
        # "No, I meant…" gets "Ah, my bad," then the right answer (Human Test v2: brains skipped it in 4 or 5 of 6 repairs)
        text, fixes = "Ah, my bad. " + text, fixes + ["owned the mistake"]
    honest = honest_about_itself(text, said)
    if honest is not None:
        text, fixes = honest, fixes + ["claimed human"]
    rules = [("help desk", lambda s: bool(assistantisms(s))), ("pamphlet", lambda s: bool(therapy_speak(s))),
             ("made-up life", lambda s: bool(invented_life(s)))]
    for name, bad in rules:
        parts = split_sentences(text)
        kept = _drop(parts, bad)
        if len(kept) < len(parts):
            text, fixes = _join(kept), fixes + [name]
    parts = split_sentences(text)
    kept = [p for p in parts if not copied_example(p, said)]
    if kept and len(kept) < len(parts):  # every copied sentence goes, even one the next leans on (nothing left: Luma asks again)
        text, fixes = _join(kept), fixes + ["copied an example"]
    if "**" in text:
        text, fixes = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", text), fixes + ["markdown"]
    if hurt_recently and not friendcheck.LAUGHS.search(str(said or "")) and friendcheck.LAUGHS.search(text):
        cleaned = re.sub(r"\s+([.!?,])", r"\1", re.sub(r"\s{2,}", " ", LAUGH_TOKENS.sub("", text))).strip()
        cleaned = re.sub(r"^[,.!\s]+", "", re.sub(r"([.!?]),", r"\1", cleaned))
        if cleaned:
            text, fixes = cleaned, fixes + ["laughed after a hard moment"]
    if questions(text) > 1:
        fewer = one_question(text)
        if fewer != text:
            text, fixes = fewer, fixes + ["questions"]
    if not depth:
        shorter = trim_for_voice(text)
        if shorter != text:
            text, fixes = shorter, fixes + ["length"]
    return text, fixes


# ------------------------------------------------------------------------------------------------ the shape of the turn ---
REPAIR = re.compile(r"^\W*(?:(?:no|nah|nope|wait|not|uh no)\b[^.!?]{0,40}\b(?:i meant|i mean|not that|that'?s not)|that'?s not what i (?:asked|meant|said)|"
                    r"(?:no|nah),? i meant|not (?:that|what i meant)|you misunderstood|"
                    r"(?:no|nah|nope)[,.]?\s+not (?:a|an|the|that|this|like|what|him|her|them|my|those|these)\b)", re.I)
CUT_IN = re.compile(r"^\W*(?:wait|hold on|hold up|hang on|stop|no wait|one sec|sec|pause)\b[^?]{0,32}$", re.I)
GREETINGS = re.compile(r"^\W*(?:hi|hey|hello|yo|sup|morning|night|gn|gm|bye|thanks|thank you|ty|thx)\W*$", re.I)


def turn_note(said, last_reply=""):
    """How a friend handles this kind of moment, for the brain: corrected, cut off, answered in a word. "" for everything else."""
    said = str(said or "").strip()
    if REPAIR.search(said):
        return ("They're correcting you. Start with a quick \"ah, my bad\" or \"got it\", then give the right answer. "
                "No formal apology, no \"could you clarify\".")
    if last_reply and CUT_IN.search(said):
        return "They cut in while you were talking. Stop, and give them the floor in a few words, like \"Yeah? I'm listening.\" Don't go on."
    if last_reply and 0 < len(WORD.findall(said)) <= 2 and "?" not in said and not GREETINGS.match(said):
        return "They answered in a word. Keep yours to one short line, easy and warm. No lecture, no list."
    return ""
