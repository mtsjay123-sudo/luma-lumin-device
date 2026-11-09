"""What a friend never sounds like: the customer-service lines, therapy-speak, made-up life and "I'm human" that give a
machine away, in one place. The human test (scripts/human_eval.py) counts them in every reply; Luma's own guard
(Agent._friend_style) fixes the cheap ones before anyone hears them.
"""
from __future__ import annotations

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
    r"\bwhen i was (?:a kid|little|young|younger|a teenager|growing up|in (?:school|college|high school))\b|"
    r"\bi (?:also |too )?(?:lost|buried) (?:my|a) (?:mom|dad|mother|father|brother|sister|friend|best friend|grandma|grandpa|"
    r"dog|cat|pet|husband|wife|son|daughter|child|baby)\b|\bi(?:'ve| have) (?:been through|gone through) (?:that|this|the same|something (?:similar|like))\b|"
    r"\bi used to (?:live|work|play|go|have|date)\b|\bi grew up\b|\bi know (?:exactly )?how (?:it|that) feels\b|"
    r"\bi (?:just )?(?:woke up|had (?:breakfast|lunch|dinner|coffee)|took a nap|got home|went (?:to|out))\b|"
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


def questions(text):
    """How many questions: "Wait, really??" is one."""
    return len(QUESTION.findall(_outside_quotes(text)))


def words(text):
    return len(WORD.findall(str(text or "")))


def opener(text):
    """The first word, the way a listener hears it ("I'm", "Honestly", "You")."""
    found = WORD.search(str(text or "").lstrip(" \"'“*-—"))
    return found.group(0).lower() if found else ""
