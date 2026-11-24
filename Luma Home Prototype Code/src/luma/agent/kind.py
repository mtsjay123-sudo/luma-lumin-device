"""Something kind said to Luma: "thank you for listening", "you always know what to say", "i'm glad i have you to talk to".

Run 89 gave four passes of the same conversations on the stock 4B, and the turns it missed every time were mostly this
moment. Thanked for being there, it said "anytime. you're the one who makes it real."; told it was easy to talk to, "Thanks.
I'm just here because you are. No pressure, no scripts". A deflection each time: the kind thing is handed back or waved
off, and nothing says it was glad to hear it. The owner, Nov 22: Luma's affection is real.

Telling the brain was tried first and did nothing. Run 92, the same conversation six times on the code before the note and
six on the code with it: the stock 4B passed that turn 1 of 6 and 1 of 6, and its replies were the same wave-off, nearly
word for word ("Thanks. I'm just here when you are, no pressure, no scripts"); the other three brains didn't move either
(5 and 5, 2 and 2, 6 and 5 of 6). So the note is gone, and when a reply to something kind has nothing glad in it, Luma
adds one line itself, after the reply: "That means a lot to me." The same way it adds the offer when someone asked to have
their mind taken off things and the brain didn't make it (Agent._as_they_asked). Off switch: "glad_line".

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

# The one line Luma adds itself when a reply to something kind has nothing glad in it. Three, so it isn't the same words
# every time; which one is settled by what they said, so the same message always gets the same line.
LINES = ("That means a lot to me.", "I'm glad you said that.", "I'm really glad to hear that.")
# A reply that already took it in: nothing is added.
GLAD = re.compile(r"\bglad\b|\bmeans? (?:a lot|so much|the world)\b|\bhappy (?:to|you|that|i)\b|\b(?:touched|honou?red|grateful)\b|"
                  r"\bthat'?s (?:really |so |very )?(?:sweet|kind|nice|lovely) (?:of you|to (?:say|hear))\b|\b(?:love|like|enjoy) (?:talking|chatting|hearing|this|our)\b|"
                  r"\bme too\b|\bright back at you\b|\bmade my (?:day|night)\b|\bwarms? (?:me|my)\b", re.I)


def said(text):
    """They said something kind to Luma, about Luma."""
    told = " ".join(str(text or "").split())
    if not told or NOT_KIND.search(told):
        return False
    return bool(FOR_BEING_THERE.search(told) or ABOUT_LUMA.search(told))


def owed(text, reply):
    """The line Luma adds itself, or "": something kind was said to it and the reply has nothing glad in it. In the reply's own
    case (a brain that writes in lowercase gets a lowercase line). The caller leaves out anyone who's leaning on Luma or
    might not be safe, and never adds to a safety reply."""
    answer = str(reply or "").strip()
    if not answer or not said(text) or GLAD.search(answer):
        return ""
    line = LINES[sum(ord(c) for c in " ".join(str(text).lower().split())) % len(LINES)]
    first = next((c for c in answer if c.isalpha()), "")
    return line[0].lower() + line[1:] if first.islower() else line
