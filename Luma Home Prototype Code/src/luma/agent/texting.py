"""Texting people for the owner, the way a friend would.

Luma writes the text in the owner's voice, shows it, and sends it only when the
owner says so ("send it", or the Approve button). Approval is matched here with
plain rules, never by the language model, so a model mistake can't send a text.
"""
from __future__ import annotations

import re

CONFIRM = re.compile(
    r"^(?:(?:yes|yeah|yea|yep|yup|ya|sure|ok|okay|bet|perfect|cool|great|looks good|sounds good)[,!.\s]*)?"
    r"(?:send(?: it| that| that text| the text)?(?: now)?|do it|go ahead|go for it|confirm|ship it|approved?|"
    r"yes|yeah|yea|yep|yup|sure|ok|okay|bet|looks good|sounds good)(?: please)?[.!\s]*$", re.I)
CANCEL = re.compile(
    r"^(?:no|nah|nope|don'?t send(?: it| that)?|do not send(?: it| that)?|cancel(?: it| that)?|"
    r"never ?mind|scrap (?:it|that)|hold off|forget it|not yet)[.!\s]*$", re.I)

ROUTE_LABELS = {
    "mac_imessage": "your number",
    "mac_sms": "your number",
    "luma_number": "Luma's number",
    "twilio": "your Twilio number",
}

# Third-person words about the recipient become "you" when written to them.
# "they" is left alone: it usually means someone else ("the store said they're out").
PRONOUNS = [
    (r"\bshe is\b|\bhe is\b", "you are"),
    (r"\bshe's\b|\bhe's\b", "you're"),
    (r"\bshe was\b|\bhe was\b", "you were"),
    (r"\bshe has\b|\bhe has\b", "you have"),
    (r"\bshe'll\b|\bhe'll\b", "you'll"),
    (r"\bshe'd\b|\bhe'd\b", "you'd"),
    (r"\bherself\b|\bhimself\b", "yourself"),
    (r"\bhers\b", "yours"),
    (r"\bhis\b", "your"),
    # "her" before a noun is possessive ("her keys"); otherwise it's "you" ("pick her up").
    (r"\bher\b(?=\s+(?!(?:up|out|back|down|off|over|in|on|at|to|from|for|with|and|or|but|when|if|later|now|tonight|today|tomorrow|soon|again|too|a|an|the|that|this|some|so)\b)[a-z])", "your"),
    (r"\bshe\b|\bhe\b|\bhim\b|\bher\b", "you"),
]


def confirm_intent(text):
    if not isinstance(text, str):
        return None
    cleaned = re.sub(r"^(?:hey\s+)?(?:luma|luna)[\s,!.:]+", "", text.strip(), flags=re.I).strip()
    if CANCEL.fullmatch(cleaned):
        return "cancel"
    if CONFIRM.fullmatch(cleaned):
        return "confirm"
    return None


def to_recipient(text):
    """Rewrite third-person references so the text speaks to the recipient."""
    for pattern, replacement in PRONOUNS:
        text = re.sub(pattern, lambda m: replacement.capitalize() if m.group(0)[0].isupper() else replacement, text, flags=re.I)
    return text


def template_text(connector, request):
    """A natural first-person text from an instruction, without a model."""
    request = request.strip().strip('"“”').rstrip(".!? ")
    request = to_recipient(request)
    if connector == "to":
        body = "Can you " + request + "?"
    else:
        # Keep their casing: "omw" stays "omw", which is how they actually text.
        body = request
        if re.match(r"^(?:are|is|can|could|will|would|do|did|have|what|when|where|who|why|how)\b", body, re.I):
            body += "?"
    return body


def numbers(text):
    return set(re.findall(r"\d+", text))


def safe_draft(draft, request):
    """Reject model drafts that add facts (times, amounts) or sound like a bot."""
    if not isinstance(draft, str):
        return None
    draft = draft.strip().strip('"“”').strip()
    if not draft or len(draft) > max(200, 3 * len(request)):
        return None
    if not numbers(draft) <= numbers(request):
        return None
    if re.search(r"\b(?:as an ai|i'?m an ai|language model|luma here|this is luma|on behalf of)\b", draft, re.I):
        return None
    return draft


def compose_prompt(owner, name, request, examples):
    lines = [f"Write the text message {owner or 'the user'} wants to send to {name}.",
             f"What they asked: {request}",
             "Write it as them, in first person, talking straight to " + name + ". Sound like a real person texting:",
             "short, casual, their usual tone. Keep every detail they gave. Don't add times, places, items or promises.",
             "No greeting unless they asked for one, no sign-off, no emojis unless their past texts use them."]
    if examples:
        lines.append("How they usually text " + name + ":")
        lines += ["- " + e for e in examples[-3:]]
    lines.append('Reply with only the text message in "text".')
    return "\n".join(lines)


def describe_route(route, account=None):
    label = ROUTE_LABELS.get(route, "your phone")
    if route == "luma_number" and account and isinstance(account.get("texts_left"), int):
        left = account["texts_left"]
        if account.get("plan") != "plus" and left <= 5:
            label += f" ({left} free text{'s' if left != 1 else ''} left this month)"
    return label


def pending_text(name, body, route, account=None):
    return f"Here's the text for {name}: “{body}”. Want me to send it from {describe_route(route, account)}?"


def draft_text(name, body):
    return (f"Here's the text for {name}: “{body}”. Texting isn't connected yet, so tap Copy and send it from your phone. "
            "To have me send it, set up your number or Luma's number in People & Texts.")


def quota_text(error):
    plus = getattr(error, "plus", {}) or {}
    if getattr(error, "plan", "free") == "plus":
        return str(error) + " It resets on the 1st. I can still send from your own number through Messages."
    price = plus.get("price", "$9.99/month")
    limit = plus.get("texts_limit", 300)
    return (str(error) + f" Luma Plus is {price} for {limit} texts a month and your own Luma number. "
            "Or I can send this one from your own number through Messages, which is free.")


def sent_text(name, route, result):
    if route == "luma_number":
        plus = result.get("plan") == "plus"
        line = f"Sent to {name} from {'your Luma number' if plus else 'Luma’s number'}."
        left = result.get("texts_left")
        if isinstance(left, int) and not plus and left == 0:
            line += " That was your last free text this month."
        elif isinstance(left, int) and not plus and left <= 5:
            line += f" {left} free text{'s' if left != 1 else ''} left this month."
        return line
    if route.startswith("mac_"):
        return f"Sent to {name} from your number."
    return f"Sent to {name}."


def mirror_style(body, examples):
    """Match how the owner actually texts this person: case and end punctuation."""
    examples = [e for e in examples if isinstance(e, str) and e.strip()]
    if len(examples) < 2:
        return body
    if all(e == e.lower() for e in examples):
        body = body.lower()
    if not any(re.search(r"[.!]$", e.strip()) for e in examples):
        body = re.sub(r"\.$", "", body.strip())
    return body


APPROVE_BY_TEXT = re.compile(r"^\s*(?:yes|y|yeah|yep|send|send it|ok|okay|confirm|do it)\s*[,:!.-]?\s*(\d{4})\b", re.I)


def sms_code_reply(text, code):
    """Over SMS, approval needs the one-time code (caller ID can be spoofed; the code can't)."""
    match = APPROVE_BY_TEXT.match(text or "")
    if match:
        return "confirm" if match[1] == code else "wrong_code"
    return confirm_intent(text)


def for_sms(result, code=None):
    """Turn a Luma result into a text message back to the owner."""
    text = result.get("text") or result.get("summary") or "Done."
    text = re.sub(r"\*\*|`|^#+\s*", "", text, flags=re.M)
    if result.get("state") == "pending" and code:
        text += f" Reply YES {code} to send, or NO to cancel."
    if result.get("file"):
        text += " It's in the Luma app to download."
    if len(text) > 600:
        text = text[:590].rsplit(" ", 1)[0] + "…"
    return text
