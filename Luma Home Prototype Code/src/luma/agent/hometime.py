"""What time it is where their people are.

Someone in Tokyo with a mom in Ohio is thirteen or fourteen hours apart from her. A friend who knows that says "it's 8 in
the morning in Ohio, she's probably up" when they say they miss her, and "it's 2am there, maybe a text she'll wake up
to" when they want to call. That gets them to a real person at a time that person can answer (rule 3).

Where someone lives comes from what Luma already remembers ("Mom (their mom) lives in Ohio"). The time comes from the
clock and the place's time zone. Nothing is looked up and nothing leaves the home.
"""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

# Places people say, to a time zone. The U.S. by state and big city first (Americans in Japan first), then a few others.
PLACES = {
    "America/New_York": ["new york", "nyc", "brooklyn", "queens", "the bronx", "manhattan", "new jersey", "jersey", "boston", "massachusetts",
                         "connecticut", "rhode island", "vermont", "new hampshire", "maine", "pennsylvania", "philly", "philadelphia",
                         "pittsburgh", "delaware", "maryland", "baltimore", "dc", "d.c.", "washington dc", "virginia", "north carolina",
                         "charlotte", "raleigh", "south carolina", "georgia", "atlanta", "florida", "miami", "orlando", "tampa", "ohio",
                         "columbus", "cleveland", "cincinnati", "michigan", "detroit", "indiana", "indianapolis", "west virginia",
                         "kentucky", "louisville"],
    "America/Chicago": ["chicago", "illinois", "wisconsin", "milwaukee", "minnesota", "minneapolis", "iowa", "missouri", "st. louis",
                        "kansas city", "arkansas", "louisiana", "new orleans", "mississippi", "alabama", "tennessee", "nashville",
                        "memphis", "texas", "houston", "dallas", "austin", "san antonio", "oklahoma", "kansas", "nebraska",
                        "south dakota", "north dakota"],
    "America/Denver": ["denver", "colorado", "utah", "salt lake", "wyoming", "montana", "new mexico", "albuquerque", "idaho", "boise"],
    "America/Phoenix": ["arizona", "phoenix", "tucson"],
    "America/Los_Angeles": ["california", "cali", "los angeles", "la", "san francisco", "sf", "the bay", "bay area", "san diego",
                            "sacramento", "san jose", "oakland", "seattle", "washington state", "oregon", "portland", "nevada",
                            "las vegas", "vegas"],
    "America/Anchorage": ["alaska", "anchorage"],
    "Pacific/Honolulu": ["hawaii", "honolulu", "oahu", "maui"],
    "Pacific/Guam": ["guam"],
    "America/Puerto_Rico": ["puerto rico", "san juan"],
    "America/Toronto": ["toronto", "ontario", "montreal", "quebec"],
    "America/Vancouver": ["vancouver", "british columbia"],
    "Europe/London": ["london", "england", "the uk", "uk", "scotland", "wales"],
    "Europe/Berlin": ["germany", "berlin", "ramstein"],
    "Asia/Seoul": ["korea", "seoul", "south korea"],
    "Asia/Manila": ["the philippines", "philippines", "manila"],
    "Asia/Tokyo": ["japan", "tokyo", "osaka", "okinawa", "kyoto", "yokosuka", "yokota"],
    "Australia/Sydney": ["sydney", "australia", "melbourne"],
}
_PLACE = {name: zone for zone, names in PLACES.items() for name in names}
LIVES = re.compile(r"^(?P<who>.+?) \(their (?P<rel>[^)]+)\) (?:lives|is living|lives back|moved|just moved|is) (?:in|to|back in|out in|down in|up in) "
                   r"(?P<where>[a-z .']+?)(?:[,.]|$| now| these days| with| near)", re.I)
# The way it's usually kept: as they said it. "my mom lives in Ohio", "my brother Jake just moved to Seattle".
RELS = (r"mom|mother|mama|dad|father|papa|parents|brother|sister|grandma|grandpa|grandmother|grandfather|nana|granny|son|daughter|"
        r"wife|husband|girlfriend|boyfriend|fiance|fiancee|partner|best friend|friend|cousin|aunt|uncle|family|folks")
OWN = re.compile(rf"^(?:remember(?: that)? )?(?:my|your|their) (?P<rel>{RELS})(?: (?P<who>[A-Z][a-z]+))? (?:still |just |now )?"
                 r"(?:lives|moved|is living|lives back|is) (?:in|to|back in|out in|down in|up in) (?P<where>[a-z .']+?)(?:[,.]|$| now| these days| with| near)", re.I)
# What makes their time worth saying: missing them, calling or texting them, asking if they're up.
REACH = re.compile(r"\b(?:miss(?:ing)?|call(?:ing)?|ring|facetime|text(?:ing)?|talk to|hear from|homesick|awake|up yet|still up|asleep|"
                   r"what time (?:is it )?(?:there|for)|time (?:is it )?(?:there|back home))\b", re.I)


def where(memory_text):
    """("Mom", "mom", "America/New_York") from "Mom (their mom) lives in Ohio", or None."""
    said = " ".join(str(memory_text or "").split())
    m = LIVES.match(said) or OWN.match(said)
    if not m:
        return None
    who = (m["who"] or m["rel"]) if m["who"] else m["rel"]
    place = m["where"].strip(" .").lower()
    for name in sorted(_PLACE, key=len, reverse=True):  # "washington dc" before "washington state" before "dc"
        if place == name or place.startswith(name + " ") or place.endswith(" " + name):
            return who.strip(), m["rel"].strip().lower(), _PLACE[name], m["where"].strip(" .").title() if m["where"].islower() else m["where"].strip(" .")
    return None


def their_time(zone, now):
    """'8:10 AM' and what that hour means for reaching someone."""
    at = datetime.fromtimestamp(now, ZoneInfo(zone))
    clock = at.strftime("%-I:%M %p")
    hour = at.hour
    if 0 <= hour < 6:
        part = "the middle of the night"
    elif hour < 9:
        part = "early morning"
    elif hour < 12:
        part = "morning"
    elif hour < 17:
        part = "afternoon"
    elif hour < 22:
        part = "evening"
    else:
        part = "late at night"
    return clock, part, hour


def note(text, memories, now, here_zone=None):
    """For the brain, when they're reaching for someone whose home Luma knows: what time it is there, plainly."""
    said = str(text or "")
    if not REACH.search(said):
        return ""
    low = said.lower()
    lines = []
    for m in memories or []:
        found = where(m.get("text") if isinstance(m, dict) else m)
        if not found:
            continue
        who, rel, zone, place = found
        if who.lower() not in low and rel not in low and not re.search(rf"\b{re.escape(rel)}\b", low):
            continue
        if here_zone and str(here_zone) == zone:
            continue  # same time zone: nothing to say
        clock, part, hour = their_time(zone, now)
        named = "" if who.lower() == rel else f" {who}"
        line = f"It's {clock} in {place}, where their {rel}{named} lives ({part})."
        if hour < 6 or hour >= 23:
            line += " Too late to call: a text they'll wake up to is kinder."
        elif 7 <= hour < 22:
            line += " A good time to reach them."
        lines.append(line)
    if not lines:
        return ""
    return " ".join(lines[:2]) + " Say it the way a friend would, only if it helps them reach that person."
