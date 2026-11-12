"""Small, explicit conversation routes; never infer a recipient or purchase."""
import re


def interruption_intent(text):
    """Recognize addressed interruption controls without rewriting their content.

    Use only for an active conversation turn. Corrections still go to the
    conversational runtime with its history; this function changes no action.
    """
    if not isinstance(text, str):
        return None
    cleaned = re.sub(r"^(?:hey\s+)?(?:luma|luna)[\s,!.:]+", "", text.strip(), flags=re.I).strip()
    if re.fullmatch(r"(?:please )?(?:wait|stop|hold on|pause|stop talking|that's enough|that is enough)[.!?]*", cleaned, re.I):
        return "stop"
    if re.match(r"^(?:please )?(?:make (?:that|it) shorter|shorter(?: please)?|say (?:that|it) (?:more )?briefly)\b", cleaned, re.I):
        return "shorter"
    if re.match(r"^(?:(?:wait|hold on)[,\s]+)?(?:actually|make that|I meant|instead)\b", cleaned, re.I):
        return "correction"
    return None


# Someone texting them, or not: "my old friends don't even text me", "she never texts back", "he finally texted me". It's
# about their life, not a wish to send anything (run 34: Luma's own 4B answered the first with a draft to Mom about groceries).
THEIR_TEXTS = re.compile(r"\b(?:text|message|dm|call|write)(?:s|ed|ing)?\s+(?:me|us)\b(?!\s+(?:the|a|an|my|your|that|this|what|when|where|how|if)\b)|"
                         r"\b(?:text|message|dm|call|write)(?:s|ed|ing)?\s+(?:me\s+|us\s+)?back\b|"
                         r"\b(?:don'?t|doesn'?t|didn'?t|never|hardly|barely|rarely|haven'?t|hasn'?t|stopped)\s+(?:even\s+|ever\s+)*"
                         r"(?:text|message|call|reach|check|written|texted|called|messaged)\w*\b", re.I)
ASKS_TO_SEND = re.compile(r"^\W*(?:(?:please|hey|ok|okay|luma)[,\s]+)*(?:(?:can|could|would|will) (?:you|u)\b|text\b|message\b|send\b|tell\b|let\b|shoot\b)|"
                          r"\bshould i\b", re.I)


def wants_message(text):
    if THEIR_TEXTS.search(text) and not ASKS_TO_SEND.search(text):
        return False
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
    if re.search(r"\b(?:casual|casually|contemporary|slang)\b", lowered):
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
