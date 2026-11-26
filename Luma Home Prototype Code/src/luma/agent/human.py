"""Never an error: the last look at everything Luma says, and what it says when its brain fails.

The owner, Nov 26, 2026: "run a stress test on all errors, make sure it remains human, make sure it's never an error
again." The stress test (scripts/stress_chat.py) found, in 1,000 turns: a brain that crashed or ran out of time made
the whole turn fail with nothing said; "undefined", "None", "Error: context length exceeded" and a stack trace were
said as replies; "As an AI language model ..." and "Please let me know if you need any further assistance" got
through; a broken tool call came back as "No action was taken. Ask explicitly if you want me to ..."; and the one
fallback line, "I lost my train of thought on that one. Say it again?", came out turn after turn.

What happens now:

- **The brain fails** (raises, times out, answers nothing): Luma says a short human line (`blank`). The first time,
  it asks them to say it again; if it keeps happening, it says plainly that it's having trouble right now, and that
  timers, reminders and lists still work. Never the same line twice in a row. Someone hurting is met first, never
  asked to repeat themselves, and anyone who might not be safe gets 988.
- **A reply that's a program talking** (`LEAK`: a stack trace, an exception's name, "None", JSON, a model's own
  tokens, symbols that aren't words) is replaced the same way. Left alone when they asked about code or an error
  themselves, or the reply shows code on purpose.
- **"As an AI ..." and help-desk sentences** (`ROBOT`) come out, and what's left is said; if nothing is left, a line
  that's Luma's own.
- **The safety reply is never touched.** Neither is a reply that carries 988, 119 or 0570-064-556.

`said_instead` (in the runtime) covers what Luma refuses on purpose: each refusal is said as a sentence.
"""
from __future__ import annotations

import re

LEAK = re.compile(
    r"traceback \(most recent call|\b(?:key|value|runtime|type|attribute|index|timeout|name|os|import|assertion|zerodivision)error\b|"
    r"\bexception:|\berrno\b|\bNoneType\b|object at 0x[0-9a-f]+|^\s*(?:none|null|undefined|nan|true|false|\[\]|\{\})\s*$|^\s*[\[{]\s*\"|"
    r"<\|?/?(?:im_start|im_end|endoftext|eot_id|start_header_id|end_header_id|think|s)\|?>|\[/?INST\]|\[object Object\]|"
    r"invalid proposal|no usable reply|context (?:length|window) (?:exceeded|is full)|out of memory|\bcuda\b|\.gguf\b|"
    r"\bplanner\b|\x00|�|^\W*#{2,}\W*$|^\W*$", re.I)
ROBOT = re.compile(
    r"\bas an? (?:ai|artificial intelligence|language model|large language model|virtual assistant|ai assistant|chatbot|digital assistant)\b|"
    r"\bi(?:'m| am) (?:just |only |merely )?(?:an? )?(?:ai|artificial intelligence|language model|large language model|ai assistant|"
    r"virtual assistant|chatbot|program|computer program|bot)\b|"
    r"\b(?:is there )?anything else (?:i can|i could) (?:help|assist)|\b(?:let me know|feel free to (?:ask|reach out)) if (?:you )?(?:need|have) any (?:further|more|other)|"
    r"\bfurther assistance\b|\bthank you for reaching out\b|\bhow (?:can|may) i (?:assist|help) you (?:today|further)\b|\bi'?m here to (?:help|assist) you\b", re.I)
# Never a reply, whatever they asked: a bare value, a model's own tokens, symbols that aren't words, a stack trace.
ALWAYS = re.compile(r"^\s*(?:none|null|undefined|nan|true|false|\[\]|\{\}|\[object object\])\s*$|^\s*(?:[A-Z]\w*)?(?:Error|Exception)\b: |context (?:length|window) (?:exceeded|is full)|\(\d+ tokens\)|invalid proposal from|no usable reply|^\s*\{\s*\"(?:type|text|name|tool|arguments|action)\"|<\|?/?(?:im_start|im_end|endoftext|eot_id|"
                    r"start_header_id|end_header_id)\|?>|\[/?INST\]|\x00|�|traceback \(most recent call|^\W*$", re.I)
STRAY = re.compile(r"(?:^|(?<=\s))(?:#{2,}|<\|[a-z_]+\|>|</?think>|</?s>)(?=\s|$)", re.I)
CODE_TALK = re.compile(r"\b(?:code|error|bug|stack|exception|python|javascript|json|traceback|script|program|terminal|compile|debug)\b|```", re.I)
SAFE = re.compile(r"\b988\b|\b119\b|0570-064-556|AYUDA")

AGAIN = [
    "Sorry, I blanked for a second. Say that one more time?",
    "Wait, I lost that. What were you saying?",
    "Hm, that slipped past me. Say it again?",
    "Sorry, run that by me again?",
]
STILL = [
    "I'm having a hard time thinking straight right now. I'm still here, though. Give me a minute and try me again?",
    "Something's off on my end right now, so I can't answer properly. Timers, reminders and your lists still work while I sort myself out.",
    "I'm still a bit foggy. I haven't gone anywhere. Try me again in a minute?",
]
LISTENING = [
    "I'm listening. Keep going.",
    "Mm. Then what?",
    "Okay, I'm with you. Tell me more.",
    "Yeah? Go on.",
]
HURT = {"loss": "I'm so sorry. I'm here with you. Take all the time you need.",
        "lonely": "I'm really glad you're talking to me. I'm here. What's been going on?"}
HURT_ELSE = "I'm sorry, that sounds really hard. I'm here. Tell me what happened?"
SAFETY = ("I'm really glad you told me, and I'm right here. Are you safe right now? If you're thinking about ending your life, "
          "please call or text 988, any time, day or night. Keep talking to me.")
FROM_ME = "I'm here. Tell me more?"
# Luma's own lines for something on its side not working. Said once; the second time in a row it's said another way.
TROUBLE = ("Something went wrong on my side with that one",)


def _again_said():
    from luma.agent import style
    return {style.HONEST.strip(): "Still Luma. Not a person, a presence, and I'm right here with you."}


class _Lazy(dict):
    def __contains__(self, key):
        return key in _again_said()

    def __getitem__(self, key):
        return _again_said()[key]


AGAIN_SAID = _Lazy()


def _at_risk(said):
    """Anything the crisis net or the softer safety reader would answer with 988."""
    from luma.agent import friendcheck
    from luma.agent.runtime import CRISIS
    return bool(CRISIS.search(said.lower()) or friendcheck.at_risk(said))


def _streak(agent):
    return int(getattr(agent, "_blanks", 0) or 0)


def _pick(agent, lines):
    """A line from these, never the one said last."""
    last = (getattr(agent, "_last_blank", None) or getattr(agent, "last_reply", None) or "").strip()
    n = _streak(agent)
    for k in range(len(lines)):
        line = lines[(n + k) % len(lines)]
        if line != last:
            return line
    return lines[0]


def blank(agent, said):
    """What Luma says when its brain failed this turn. Counts the failures in a row."""
    from luma.agent import friendcheck
    said = str(said or "")
    try:
        if _at_risk(said):
            return SAFETY
        hurt = friendcheck.hurting(said)
    except Exception:
        hurt = None
    line = HURT.get(hurt, HURT_ELSE) if hurt else _pick(agent, AGAIN if _streak(agent) < 2 else STILL)
    agent._blanks = _streak(agent) + 1
    agent._last_blank = line
    return line


OWN = set(AGAIN) | set(STILL) | set(LISTENING) | set(HURT.values()) | {HURT_ELSE, SAFETY}


def listening(agent, said):
    """The brain heard them and could only say what it said before: Luma listens instead of asking them to repeat it."""
    from luma.agent import friendcheck
    said = str(said or "")
    try:
        if _at_risk(said):
            return SAFETY
        hurt = friendcheck.hurting(said)
    except Exception:
        hurt = None
    line = HURT.get(hurt, HURT_ELSE) if hurt else _pick(agent, LISTENING)
    agent._last_blank = line
    return line


def went_well(agent):
    agent._blanks = 0


def leaked(text, said=""):
    """A reply that's a program talking, not Luma."""
    if not isinstance(text, str) or not text.strip():
        return True
    if ALWAYS.search(text):
        return True
    if CODE_TALK.search(str(said or "")):
        return False   # they asked about code or an error: the words may be the answer
    return bool(LEAK.search(text))


def unrobot(text):
    """The reply without its "as an AI" and help-desk sentences. "" when nothing of it was Luma's own."""
    if not isinstance(text, str) or not ROBOT.search(text):
        return text
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = []
    for part in parts:
        if not ROBOT.search(part):
            kept.append(part)
            continue
        # "As an AI language model, I cannot have feelings, but I understand." keeps what comes after the "but"
        tail = re.split(r",?\s+but\s+", part, maxsplit=1, flags=re.I)
        if len(tail) == 2 and not ROBOT.search(tail[1]) and len(tail[1].split()) >= 2:
            kept.append(tail[1][:1].upper() + tail[1][1:])
    return " ".join(kept).strip()


def tidy(text):
    """A brain's stray tokens and markers taken out, its own JSON read for what it meant to say, a stray value in front
    dropped, and a sentence it said more than once said once."""
    if not isinstance(text, str) or "```" in text:
        return text
    if text.strip().startswith("{"):
        import json
        try:
            meant = json.loads(text.strip())
        except ValueError:
            meant = None
        if isinstance(meant, dict) and isinstance(meant.get("text"), str) and meant["text"].strip():
            text = meant["text"].strip()
    lead = re.match(r"\s*(?:none|null|undefined|nan)\b[\s.:,-]+(?=\S)", text, re.I)
    if lead:
        rest = text[lead.end():]
        text = rest[:1].upper() + rest[1:]
    if STRAY.search(text):
        text = re.sub(r"[ \t]{2,}", " ", STRAY.sub("", text)).strip()
    parts = re.split(r"(?<=[.!?])[ \t]+", text)
    keys = [re.sub(r"\W+", " ", part.lower()).strip() for part in parts]
    if len(set(k for k in keys if len(k.split()) >= 3)) == len([k for k in keys if len(k.split()) >= 3]):
        return text   # nothing said twice: left exactly as it was, lines and lists and all
    seen, kept = set(), []
    for part, key in zip(parts, keys):
        if key and key in seen and len(key.split()) >= 3:
            continue
        seen.add(key)
        kept.append(part)
    return " ".join(kept).strip()


def _alike(a, b):
    import difflib
    a, b = " ".join(re.findall(r"[a-z0-9']+", str(a or "").lower())), " ".join(re.findall(r"[a-z0-9']+", str(b or "").lower()))
    return a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def said_again(agent, said, text):
    """The reply Luma gave last time, word for word, to something new. The stress test on a real brain (run 97, the stock
    1.7B): "FIXIN TO HEAD OUT" got "You're the one with the no thoughts.", the reply it had just given to something else.
    Not when they said the same thing again or asked to hear it again, never a safety line or one of Luma's own, and only
    when a brain wrote it this turn: Luma's own lines ("The mic is on.", "Your list is empty.") are the same true answer
    however the question is put."""
    wrote = getattr(agent, "_brain_wrote", None)
    if callable(wrote) and not wrote(text):
        return False
    last, last_said = getattr(agent, "_last_out", None), getattr(agent, "_last_said", None)
    if not isinstance(text, str) or not last or last_said is None or text.strip() != str(last).strip():
        return False
    if len(re.findall(r"[A-Za-z']+", text)) < 5 or text in OWN or SAFE.search(text) or _alike(said, last_said):
        return False
    try:
        from luma.agent.runtime import ASKED_AGAIN
        if ASKED_AGAIN.search(str(said or "")):
            return False
    except Exception:
        pass
    return True


def last_look(agent, said, result):
    """Everything Luma says passes here last. A reply carrying the safety lines is never changed."""
    out = _last_look(agent, said, result)
    if isinstance(out, dict) and isinstance(out.get("text"), str):
        if said_again(agent, said, out["text"]):
            out = {**out, "text": listening(agent, said)}
        agent._last_out = out["text"]
        agent._last_said = str(said or "")
    return out


def _last_look(agent, said, result):
    if not isinstance(result, dict):
        return {"text": blank(agent, said)}
    text = result.get("text")
    if text is None and isinstance(result.get("summary"), str) and result["summary"].strip():
        went_well(agent)
        return result   # a tool's result, said in its summary (a timer, a list)
    if isinstance(text, str) and SAFE.search(text):
        went_well(agent)
        return result
    if isinstance(text, str) and text.startswith(TROUBLE) and text == (getattr(agent, "last_reply", None) or ""):
        return {**result, "text": blank(agent, said)}   # the same general line twice in a row: said another way
    if isinstance(text, str):
        tidied = tidy(text)
        if tidied != text:
            text = tidied
            result = {**result, "text": text}
    if leaked(text, said):
        if result.get("summary") and isinstance(result["summary"], str) and not leaked(result["summary"], said):
            return {**result, "text": result["summary"]}
        return {**result, "text": blank(agent, said)}
    if isinstance(text, str) and text.strip() in AGAIN_SAID and text.strip() == (getattr(agent, "_last_out", None) or "").strip():
        return {**result, "text": AGAIN_SAID[text.strip()]}   # asked what it is twice in a row: the same truth, said another way
    cleaned = unrobot(text)
    if cleaned != text:
        result = {**result, "text": cleaned or FROM_ME}
    if result.get("text") not in OWN:   # one of Luma's own lines for a failed brain isn't a turn that went well
        went_well(agent)
    return result
