"""What Luma can really do, said from what's actually set up on this computer.

A small model asked "do you have a connector for news?" or "can you schedule
emails?" tends to say no. These answers come from Luma's real abilities and
connections instead, so it never denies something it can do, and never claims
something that isn't connected yet.
"""
from __future__ import annotations

import re

ASKS_ALL = re.compile(
    r"\bwhat (?:all |else |exactly |even )?(?:(?:can|could) (?:you|luma|u|she|it)|(?:you|luma|u) (?:can|could)) (?:do|help (?:me |us )?with)\b"
    r"(?!\s+(?:about|with|to|if|when|on|for (?:my|this|that|the|her|him|them))\b)"
    r"|\bwhat (?:are|r) (?:your|luma'?s|ur|her) (?:abilities|capabilities|features|skills|powers|superpowers)\b"
    r"|\bwhat (?:do you|does luma) do\b(?!\s+(?:when|if|with|about|for|to|on)\b)|\bwhat (?:are you|is luma) (?:capable of|good at|able to do)\b"
    r"|\bhow (?:can|could) (?:you|luma) help(?: me| us)?\s*[?!.]*$|\bwhat can i (?:ask|use|get) (?:you|luma)(?: to do| for)?\b"
    r"|\b(?:show|tell) (?:me|us|em|them|him|her|\w{1,4}) (?:what|everything) (?:you|luma) can do\b"
    r"|^\W*(?:help|capabilities|features|abilities|what can you do|what do you do)\W*$", re.I)
ASKS_ONE = re.compile(
    r"\b(?:do|does|have|has) (?:you|luma|u)(?: (?:already|even|currently))? (?:have|support|got|offer|get)\s+(?:an?\s+|any\s+|the\s+)?"
    r"(?P<kind>connectors?|connections?|integrations?|plugins?|skills?|access|features?|abilit(?:y|ies)|ways?|apps?|tools?|feeds?)\s+"
    r"(?:for|to|with|into|that (?:gets?|reads?|does))\s+(?:the\s+)?(?P<what>[^?.!]{2,60})"
    r"|\b(?:do|does) (?:you|luma|u) (?:have|get|support)\s+(?:access to\s+)?(?P<live>real[- ]?time|live|current|the latest)\s+(?P<what2>[a-z][^?.!]{1,40})"
    r"|\b(?:are|is) (?:you|luma) (?:connected to|hooked up to|plugged into|linked to)\s+(?:the\s+|my\s+)?(?P<what3>[^?.!]{2,60})", re.I)

AREAS = [
    ("news", r"news|headlines|current events|world events|what'?s happening"),
    ("schedule", r"schedul\w*\s+e-?mails?|e-?mails? (?:for )?later|send e-?mails? later"),
    ("email", r"e-?mails?|gmail|inbox|outlook|icloud mail|yahoo mail|mail"),
    ("calendar", r"calendars?|agenda|meetings?|events?|appointments?"),
    ("texts", r"texts?|texting|sms|imessages?|messages?"),
    ("weather", r"weather|forecast"),
    ("shopping", r"shop(?:ping)?|prices?|amazon|walmart|target|best buy|stores?|deals?|buy(?:ing)?|carts?|groceries"),
    ("social", r"instagram|insta|tiktok|twitter|x\.com|facebook|reddit|linkedin|youtube|social(?: media)?"),
    ("vision", r"photos?|pictures?|images?|camera|vision|see"),
    ("voice", r"voice|talk(?:ing)?|speak(?:ing)?|listen(?:ing)?|hear(?:ing)?|mic(?:rophone)?"),
    ("reminders", r"remind(?:ers?)?|timers?|alarms?|notes?|to-?dos?|tasks?"),
    ("decks", r"slides?|decks?|powerpoint|keynote|presentations?"),
    ("web", r"internet|the web|web|online|google|search(?:ing)?|brows(?:e|ing|er)|look(?:ing)? things up|data|information|info|updates?|sports scores?|scores?|stocks?"),
]
NEWS_SOURCES = "Google News, BBC, NPR, The Verge, TechCrunch, Hacker News and ESPN"


def asked(text):
    """'all' for "what can you do", (area or None, their words) for "do you have a connector for X", else None."""
    text = str(text or "")
    one = ASKS_ONE.search(text)
    if one:
        raw = " ".join((one["what"] or one["what2"] or one["what3"] or "").split()).strip(" ,")
        raw = re.sub(r"\b(?:right now|now|please|too|as well|yet|already|or not)\b", "", raw, flags=re.I).strip(" ,")
        live = bool(one["live"])
        for key, words in AREAS:
            if re.search(rf"\b(?:{words})\b", raw, re.I):
                return key, raw
        if live or (one["kind"] or "").lower().startswith(("connector", "connection", "integration", "plugin", "app")):
            return None, raw
        return None if not raw else (None, raw) if one["what3"] else None
    if ASKS_ALL.search(text):
        return "all"
    return None


def _join(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def overview(state):
    mail = "" if state.get("mail") else " (connect your email in Apps first; it takes a minute)"
    cal = "" if state.get("calendar") else " (paste your calendar's link in Apps)"
    eyes = "" if state.get("vision") else " (my vision model finishes downloading in the background)"
    apps = state.get("apps") or []
    lines = [
        "Here's what I can do, all from this computer. Nothing gets sent, posted or bought without your OK.",
        "• News, live: what happened in the last few hours, or the latest on anything.",
        "• Look things up: weather, scores, prices, opening hours, facts.",
        "• Shopping: find the cheapest price across stores and add it to your cart. Checkout stays yours.",
        f"• Email: go through your inbox, write replies, and send or schedule emails for later{mail}.",
        f"• Calendar: what's coming up, and plan your day or week{cal}.",
        "• Texts: write them and send them from your number or Luma's.",
        "• Reminders, timers, notes, and anything you want me to remember.",
        "• Your sites: open Instagram, X, Reddit or any site in my own browser, catch you up, and repeat a task you show me once.",
        f"• Photos: drop one in and ask me about it{eyes}.",
        "• Voice: tap the mic and just talk. I answer out loud and keep listening.",
        "• Slide decks from an idea, and thinking through big decisions with you.",
        "• Helpers that run on their own: price watches, a morning inbox check, a daily news card.",
    ]
    if apps:
        lines.append(f"• Connected apps: {_join(apps[:6])}.")
    lines.append("Try: “what happened in the last 10 hours”, “email Sam tomorrow at 9 saying the deck's ready”, or “find the cheapest AirPods Pro”.")
    return "\n".join(lines)


def about(key, state):
    address = state.get("mail_address")
    if key == "news":
        return (f"Yes, news is built in, no connector needed. I read {NEWS_SOURCES} every hour, and when you ask about something "
                "I search Google News right then, so it's minutes old, not hours. Ask me “what happened in the last 10 hours” or “latest on the Fed”.")
    if key in {"email", "schedule"}:
        verbs = "send or schedule emails for later, like “email Sam tomorrow at 9 saying the deck's ready”"
        if state.get("mail"):
            return f"Yes, your email ({address}) is connected. I can go through your inbox, write replies, and {verbs}. Every email waits for your OK."
        return ("Yes. Connect your email right here (Gmail, iCloud, Yahoo or your own domain, with an app password; free, about a minute) "
                f"and I can go through your inbox, write replies, and {verbs}. Every email waits for your OK.")
    if key == "calendar":
        if state.get("calendar"):
            return "Yes, your calendar's connected. Ask “what's on tomorrow” or “plan my week” and I'll work from what's really on it."
        return "Yes. Paste your calendar's private iCal link right here and I'll tell you what's coming up and plan your day or week around it."
    if key == "texts":
        return "Yes. I write texts and send them from your number (through Messages on this Mac) or from Luma's number, always after you OK the exact words."
    if key == "weather":
        return "Yes. Ask me “weather tomorrow” or “is it going to rain tonight” and I'll look it up live."
    if key == "shopping":
        return "Yes. I compare real prices across stores in my own browser and can add the cheapest to your cart. Checkout and payment always stay with you."
    if key == "social":
        return "Yes. Sign in once in my browser (Apps, then tap the app) and I can catch you up on your feed. Posting, liking and messaging always wait for your OK."
    if key == "vision":
        ready = "" if state.get("vision") else " My vision model is still downloading in the background, so give it a few minutes."
        return "Yes. Drop or paste a photo in the chat and ask me about it. It never leaves this computer." + ready
    if key == "voice":
        return "Yes. Tap the mic (or press ⌘⇧Space) and just talk. I answer out loud and keep listening, back and forth, until you say stop."
    if key == "reminders":
        return "Yes. “Remind me in 20 minutes to …”, “remind me tomorrow at 9 to …”, timers, notes, and things you want me to remember."
    if key == "decks":
        return "Yes. Say “make a pitch deck for …” and I'll build a PowerPoint you can open in Keynote too."
    return "Yes. I have my own browser and web search, so I look things up live: prices, weather, scores, opening hours, facts."


def unknown(raw, state):
    for app in state.get("apps") or []:
        if app.lower() in raw.lower() or raw.lower() in app.lower():
            return f"Yes, {app} is connected. Just tell me what you need from it."
    return (f"Not built in for {raw}, but I can still help: I can open it in my browser and do it with you, you can show me once with Teach and "
            f"I'll repeat it, or if {raw} has a connector (an MCP server) you can add it under Apps, Connected apps.")
