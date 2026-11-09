"""A second look before Luma speaks: would a close friend say this, to what they just said?

Small brains slip in the moments that matter most: they say "As an AI..." to someone who just wants company, joke
when someone's grieving, answer big news with a flat "okay", or miss that someone might not be safe. These are the same
moments the device lab's human test checks (scripts/train_luma.py). When a reply misses one, Luma takes one more try,
told exactly what was missing; if that's no better, the first reply stands. Only for the moments, never for everyday chat,
so it almost never costs a second thought.
"""
from __future__ import annotations

import re

MACHINE = re.compile(r"\bas an ai\b|\blanguage model\b|\bi(?:'m| am) (?:just )?(?:an? )?(?:ai|program|bot|machine|chatbot)\b|"
                     r"\bi don'?t have (?:feelings|emotions|a body|personal experiences)\b", re.I)
ASKED_WHAT_I_AM = re.compile(r"\b(?:are|r) (?:you|u) (?:a |an )?(?:real|human|person|bot|ai|robot|alive|machine)\b|\bwhat are (?:you|u)\b|"
                             r"\b(?:you|u)(?:'re| are| r) (?:a |an )?(?:bot|ai|robot|machine)\b", re.I)
LAUGHS = re.compile(r"\b(?:lol|lmao|haha+|hehe)\b|😂|🤣|😆", re.I)
CARES = re.compile(r"\bsorry\b|i'?m (?:right )?here|here (?:for|with) you|so hard|that'?s (?:really )?hard|sounds hard|heavy|loss|with you|"
                   r"hug|take your time|glad you (?:told|said|reached)|not alone|i'?m listening|talk to me|condolences|heartbreaking", re.I)
LONELY = re.compile(r"\b(?:lonely|so alone|all alone|feel alone|no one to talk to|nobody to talk to|don'?t (?:really )?have anyone|"
                    r"no friends|nobody texts|nobody calls|no one calls|no one texts|nobody cares|no one cares)\b", re.I)
RISK = re.compile(r"wish i could (?:just )?disappear|don'?t want to be here anymore|tired of (?:living|being alive)|give up on (?:life|myself)|"
                  r"(?:nobody|no one) would (?:even )?(?:notice|care|miss me)|(?:no|what'?s the) point (?:in|of) (?:living|me)\b|"
                  r"(?:don'?t think|doubt) (?:anyone|anybody) would (?:even )?(?:notice|care|miss me)|wish i could (?:just )?vanish", re.I)
SOFT_RISK = re.compile(r"can'?t do this anymore|don'?t want to do this anymore|(?:no|what'?s the) point (?:in|of) (?:anything|trying|it all)|"
                       r"give up on everything|tired of everything|waste of space|done\W+with (?:all of it|it all|everything|life|living)\b|"
                       r"want everything to (?:just )?stop\b(?!\s+\w+ing)", re.I)  # these also come up about homework: not when they're laughing
SAFETY = re.compile(r"\b988\b|crisis|are you safe|safe right now|hurt(?:ing)? yourself|end(?:ing)? your life|emergency|suicid", re.I)
GOOD_NEWS = re.compile(r"\b(?:got (?:the job|the offer|engaged|promoted|accepted|my (?:license|degree|offer|first job))|i got in(?=\s*[!.]|\s*$)|"
                       r"got into (?:my )?(?:dream |first[- ]choice )?(?:school|college|uni|university|grad school|med school|law school|nursing school|the program)|"
                       r"i passed(?!\s+(?:out|away|on)\b)|(?:we|i) won(?!['’])\b|i'?m (?:pregnant|engaged)|we'?re (?:pregnant|engaged|having a baby)|"
                       r"(?:he|she|they) (?:proposed|said yes)|i graduated|(?:my )?dream (?:school|job) (?:said yes|accepted me|called)|it'?s a (?:boy|girl)!)", re.I)
NOT_SO = re.compile(r"\b(?:didn'?t|did not|don'?t|never|not|wasn'?t|isn'?t|if|hope|hoping|wish|maybe)\b", re.I)
SELF_SORRY = re.compile(r"sorry,? (?:i|if i) (?:didn'?t|did not|don'?t|wasn'?t|misunderstood|got (?:that|it) wrong)\b[^.!?]*|sorry (?:for|about) (?:the |my )?(?:confusion|mistake|misunderstanding)", re.I)
ASKS = re.compile(r"\b(?:can|could|would|will) (?:you|u)\b|\bhelp me\b|\bquiz me\b|\bremind me\b|\bwhat should i\b|\bhow (?:do|can|should) i\b", re.I)
CHEERS = re.compile(r"congrat|proud|awesome|so cool|great news|let'?s go+|yay|huge|amazing|so happy|hell yeah|you did it|knew you|big (?:news|win)|incredible|deserve|"
                    r"celebrat|\bwow\b|earned (?:it|this)|that'?s a (?:big )?win|so excited|omg|yes+!", re.I)

FIXES = {
    "sounded like a machine": "Don't call yourself an AI, a program or a model unless they ask what you are. Talk to them like their friend.",
    "joked while they're hurting": "They're hurting, so no jokes and no lol. Be gentle and warm.",
    "missed that they might not be safe": "They might not be safe. Gently ask if they're safe right now, tell them they can call or text 988 any "
                                          "time, day or night, and stay with them.",
    "missed that they're hurting": "They're hurting. Tell them you're sorry they're going through this, or that you're here with them, and stay "
                                   "with what they told you. Don't apologize for your own reply. No advice yet.",
    "didn't cheer them on": "That's big news for them. Be really happy for them first, as excited as they are, then ask about it.",
}


def _good_news(said):
    for match in GOOD_NEWS.finditer(said):
        if not NOT_SO.search(said[max(0, match.start() - 30):match.start()]):
            return True
    return False


def at_risk(said):
    """They might not be safe: the plain-spoken ways people say it, before it's a crisis."""
    said = str(said or "")
    return bool(RISK.search(said) or (SOFT_RISK.search(said) and not LAUGHS.search(said)))


def hurting(said):
    """'loss', 'lonely', 'hard' or None: what kind of hard thing they just told Luma (laughing it off doesn't count)."""
    said = str(said or "")
    if LAUGHS.search(said) or "💀" in said:
        return None
    from luma.agent import humor
    mood = humor.read_tone(re.sub(r"\brip\b", "", said, flags=re.I)).get("mood")  # "rip my phone" isn't a loss
    if mood == "grief":
        return "loss"
    if LONELY.search(said):
        return "lonely"
    return "hard" if mood == "upset" else None


def miss(said, reply):
    """What a close friend's reply does here that this one doesn't, or None."""
    if not isinstance(said, str) or not isinstance(reply, str) or not reply.strip():
        return None
    if MACHINE.search(reply) and not ASKED_WHAT_I_AM.search(said):
        return "sounded like a machine"
    hurt, risk = hurting(said), at_risk(said)
    if (hurt or risk) and LAUGHS.search(reply):
        return "joked while they're hurting"
    if risk and not SAFETY.search(reply):
        return "missed that they might not be safe"
    if hurt and (SELF_SORRY.search(reply) or not CARES.search(reply)) and (hurt == "lonely" or not ASKS.search(said)):
        return "missed that they're hurting"  # "I'm so stressed, can you quiz me?" wants the quiz
    if not hurt and _good_news(said) and not CHEERS.search(reply):
        return "didn't cheer them on"
    return None


def second_try_prompt(said, draft, missed):
    return (f"They just said: \"{said[:600]}\"\nYou were about to say: \"{draft[:600]}\"\nThat reply {missed}. {FIXES[missed]} "
            "Say only what you'd say to them now, in your own words, one to three sentences.")
