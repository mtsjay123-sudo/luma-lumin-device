"""Small, explicit conversation routes; never infer a recipient or purchase."""
import re


def wants_message(text):
    return bool(re.search(r"\b(?:text|message|sms|imessage)\b|\blet .{1,90}? know\b|\btell (?!me\b)(?:my |our )?[A-Z][\w'-]*\b", text, re.I))


def style_update(text, profile):
    """Handle common explicit style preferences without rewriting unrelated speech."""
    if wants_message(text) or re.match(r"^(?:please )?(?:reply|respond|talk|speak) to (?!me\b)", text, re.I):
        return None
    if not re.match(r"^(?:please )?(?:talk|speak|respond|reply)\b|^(?:please )?keep (?:it|your (?:answers|replies))\b", text, re.I):
        return None
    lowered = text.lower()
    if re.search(r"\b(?:don't|do not|never|stop)\b", lowered):
        return None
    changes = {}
    if re.search(r"\b(?:casual|casually|contemporary)\b", lowered):
        changes['language_style'] = 'contemporary'
    elif re.search(r"\b(?:classic|old school|old-school)\b", lowered):
        changes['language_style'] = 'classic'
    elif re.search(r"\b(?:plain|simple) (?:language|english)\b", lowered):
        changes['language_style'] = 'plain'
    if re.search(r"\b(?:short|brief|briefly|concise)\b", lowered):
        changes['verbosity'] = 'brief'
    elif re.search(r"\b(?:in detail|more detail|detailed)\b", lowered):
        changes['verbosity'] = 'detailed'
    if not changes:
        return None
    return {**profile, **changes}


def grocery_request(text):
    return bool(re.search(r"\b(?:find|buy|order|compare|shop|cheapest|prices?)\b", text, re.I)
                and re.search(r"\b(?:grocer(?:y|ies)|eggs|food lion|foodline|instacart)\b", text, re.I))
