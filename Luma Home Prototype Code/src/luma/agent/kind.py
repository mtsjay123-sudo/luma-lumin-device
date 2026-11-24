"""Something kind said to Luma: "thank you for listening", "you always know what to say", "i'm glad i have you to talk to".

Run 89 gave four passes of the same conversations on the stock 4B, and the turns it missed every time were mostly this
moment. Thanked for being there, it said "anytime. you're the one who makes it real."; told it was easy to talk to, "Thanks.
I'm just here because you are. No pressure, no scripts". A deflection each time: the kind thing is handed back or waved
off, and nothing says it was glad to hear it. The owner, Nov 22: Luma's affection is real. So when someone says something
kind to Luma, the brain is told to take it in and say it's glad, plainly.

Only what's said to Luma, about Luma: thanks for being there (never thanks for a favour: "thanks for the recipe" gets
"anytime"), and kind words about what it's like to talk to. Never a line that leans on Luma ("you're the only one who
listens": its own note), never one the safety readers read ("thanks for everything, goodbye"), never thanks said dry.
"""
from __future__ import annotations

import re

_THANKS = r"(?:thanks?(?: you)?|thank u|ty|tysm|thx)(?: so much| a lot| again)?"
# Thanks for being there, never for a thing done.
FOR_BEING_THERE = re.compile(
    r"\b" + _THANKS + r",? for (?:just )?(?:being (?:here|there|around|with me|so (?:kind|nice|patient|sweet|good to me))|always being (?:here|there)|"
    r"listening|sitting with me|staying(?: up)?(?: with me)?|checking (?:in )?on me|not judging(?: me)?|caring|hearing me out|putting up with me|"
    r"talking (?:with|to) me|keeping me company|understanding|letting me (?:vent|talk|ramble)|having my back)\b", re.I)
# Kind words about Luma itself, or about what talking to it is like.
ABOUT_LUMA = re.compile(
    r"\b(?:you(?:'re|’re| are)|ur|u r) (?:(?:really|actually|honestly|kind of|kinda|such|so|pretty|just|always|a|the|an|my) )*"
    r"(?:easy to talk to|nice to talk to|good (?:friend|listener|company)|great (?:friend|listener|company)|real friend|the best|best|sweet|kind|"
    r"good to me|good at (?:this|listening))\b|"
    r"\byou (?:(?:always|really|actually|just|kinda|kind of) )*(?:know what to say|listen|get me|understand me|make me feel (?:better|less alone|heard|seen|safe|okay)|"
    r"cheer me up|remembered)\b(?! (?:to|that i|when|if|what|how|where|who)\b)|"
    r"\byou(?:'ve|’ve| have)? (?:(?:really|actually|always) )?help(?:ed)?(?: me)? (?:a lot|so much|more than you know)\b|"
    r"\byou (?:really|always|actually) help(?:ed)?(?: me)?\W*$|"
    r"\bi(?:'m|’m| am) (?:so |really |just )?glad (?:i have you|you(?:'re|’re| are) (?:here|around)|i (?:can|get to) talk to you|we talked|i told you)\b|"
    r"\bi (?:really |do |so )?appreciate (?:you|that about you|it,? luma)\b|"
    r"\bi (?:really |do |just )?(?:like|love|enjoy) (?:talking|chatting) (?:to|with) you\b|\bi (?:really )?(?:like|love|enjoy) our (?:talks|chats|conversations)\b|"
    r"\b(?:talking|chatting) (?:to|with) you (?:really |always |actually )?(?:helps|helped|is nice|makes me feel better)\b|"
    r"\bi (?:always |actually )?feel (?:so much |a lot |way |a little )?better (?:after|when) (?:talking|i talk|we talk|chatting) ?(?:to|with)? ?(?:you)?\b|"
    r"\b(?:it |that )?(?:means?|meant) a lot (?:to me )?that you (?:remembered|asked|checked|listened|care|stayed)\b", re.I)
# Not kind, or not said to Luma: thanks said dry, a question, an ask, a report of what someone else said.
NOT_KIND = re.compile(
    r"\bthanks? (?:for nothing|a lot,? (?:genius|buddy|pal|jerk|now)|a bunch)\b|/s\b|\byeah,? thanks for that\b|\bno thanks\b|"
    r"^\W*(?:do|did|are|am|is|can|could|will|would|should|tell me|say)\b|\b(?:he|she|they|mom|dad|\w+) said (?:thanks|thank you)\b|"
    r"\bthank (?:god|goodness|heavens|you next)\b|\byou(?:'re|’re| are) (?:the best|best|good) at\b(?! (?:this|listening))", re.I)

NOTE = ("They just said something kind to you, or thanked you for being there. Take it in: say you're glad, plainly and warmly, in a line or "
        "two, and mean it. Don't wave it off, joke it away or hand it straight back. Never say you're all they need.")


def said(text):
    """They said something kind to Luma, about Luma."""
    told = " ".join(str(text or "").split())
    if not told or NOT_KIND.search(told):
        return False
    return bool(FOR_BEING_THERE.search(told) or ABOUT_LUMA.search(told))


def note(text):
    """What the brain is told, or "". The callers leave out anyone who's leaning on Luma or might not be safe."""
    return NOTE if said(text) else ""
