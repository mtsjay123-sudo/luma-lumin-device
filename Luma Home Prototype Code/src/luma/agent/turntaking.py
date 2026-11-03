"""Taking turns like a friend: noticing when Luma jumped in too early, and checking when someone's said a lot.

Cut someone off: a friend who starts answering and hears you keep going stops, lets you finish, then says "sorry,
I didn't mean to cut you off" and answers the whole thing, not just the last half. Luma does the same. When it had
only just started talking (a couple of seconds) and they carried on, or they carried on with "and...", "but...",
"because..." or after a sentence left hanging ("remind me to..."), what they said before and what they said after
are one thought: Luma stops, says a quick sorry, and answers both together. A clear new request ("wait, what time
is it?") is just a new request.

Said a lot: someone who talks for a while often asks something in the middle of it. A friend checks before
answering when it's not clear what they want ("wait, just so I've got it: you're asking...?"), and just answers
when it is. Luma is told to do exactly that, and never to repeat it all back.
"""
from __future__ import annotations

import re
import zlib

JUST_STARTED = 1.6     # seconds: they kept going before Luma's first words had even landed
EARLY = 4.0            # seconds: still early in Luma's answer, so "and...", "but..." carries on their thought
LONG_WORDS = 70        # a turn this long is someone talking for a while
CARRY_ON = re.compile(r"^\W*(?:and|but|or|so|because|cause|'cause|cuz|like|then|also|plus|which|that|um+|uh+|anyway|i mean|"
                      r"wait no|actually|except|unless|especially|or like|and then|and also)\b", re.I)
HANGING = re.compile(r"(?:\b(?:and|but|or|so|because|the|a|an|to|my|your|for|with|of|about|that|if|when|like|um|uh)|,"
                     r"|\bto (?:call|text|tell|ask|get|buy|send|email|grab|pick up|book|order|pay|message|remind|invite|meet|see))\s*[.…]*\s*$", re.I)
NEW_REQUEST = re.compile(r"^\W*(?:(?:hey |ok |okay )?luma\b|what time|set an? |remind me|call |text |play |stop\b|pause\b|turn (?:on|off)|open )", re.I)
SORRY = ["Sorry, I didn't mean to cut you off.", "Oh, my bad, I jumped in too early.", "Sorry, go ahead, I cut you off there.",
         "Wait, sorry, I didn't let you finish."]


def cut_them_off(spoke_for, before, after):
    """Luma had been talking `spoke_for` seconds when they carried on with `after` (having said `before`). Was it
    still their turn? spoke_for is None when Luma wasn't talking at all."""
    if spoke_for is None or not before or not after:
        return False
    if NEW_REQUEST.match(after):
        return False
    if spoke_for <= JUST_STARTED:
        return True
    if spoke_for <= EARLY:
        if CARRY_ON.match(after) or HANGING.search(before.strip()):
            return True
        try:
            from luma.agent import understanding
            return bool(understanding.cut_off(before))
        except Exception:
            return False
    return False


def together(before, after):
    """Their whole thought, said in two goes: "remind me to call" + "my sister tomorrow" -> one sentence."""
    before = before.strip()
    after = after.strip()
    joined = re.sub(r"[.…]+$", "", before) if HANGING.search(before) or CARRY_ON.match(after) else before
    if joined and not re.search(r"[.!?,]$", joined) and not CARRY_ON.match(after):
        joined += ","
    return f"{joined} {after[:1].lower() + after[1:] if CARRY_ON.match(after) else after}".strip()


def sorry(seed):
    """A quick sorry, different now and then, the same for the same words."""
    return SORRY[zlib.crc32(str(seed).encode("utf-8", "ignore")) % len(SORRY)]


def turn_note(text):
    """For the brain, when they've said a lot: check what they're asking only if it isn't clear; never repeat it all back."""
    words = len(str(text or "").split())
    if words < LONG_WORDS:
        return ""
    questions = len(re.findall(r"\?", text)) + len(re.findall(r"\b(?:should i|do you think|what do i|how do i|what would you|is it|am i)\b", text, re.I))
    ask = ("They asked more than one thing in there. Answer the one that matters most first, then the rest briefly." if questions >= 2 else
           "")
    return ("They talked for a while, like a friend telling you something. Show you were listening: pick up the one detail that "
            "matters most. If it isn't clear what they want from you (advice, an opinion, or just to vent), check with one short "
            "question first, the way a friend does: “Wait, just so I've got it: you're asking whether ...?” If it is clear, just answer. "
            "Never repeat everything back to them. " + ask).strip()
