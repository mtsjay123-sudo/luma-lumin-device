"""Keeping up: when they bring up an album, a game, a show, a movie or a book, Luma reads up on it without being asked.

A friend who says "that might be newer than what I know" every time you mention a record isn't much of a friend. A
friend goes and looks, and comes back knowing what it is and what people are saying about it.

- asked(text): "have you heard the new kendrick album", "did you watch severance". They asked Luma about one thing.
- mentioned(text): "i've been listening to the new kendrick album all day". They only brought it up.

Both hand back the name of the thing and the search to make for it, or None.

What leaves the home is the name of the thing and nothing else. Never their sentence, never a word about them or the
people in their life: a phrase with any such word in it is not searched at all (private()). Luma can't hear, watch or
play anything, so it never says it did: it says it read up on it (HOW, claims_it_did()).

The runtime does the looking (luma.agent.runtime: _keep_up, _keepup_context), through the same web search, the same
switch and the same rules as every other look-up. Never in kids mode, and never when they're hurting.
"""
import re

# What a person reads up on. Not phones or cars (that's shopping), and not "the game" or "the fight" (which one? Luma asks).
WORK = (r"album|record|ep|mixtape|single|song|track|soundtrack|movie|film|show|series|sitcom|anime|manga|book|novel|memoir|podcast|"
        r"documentary|doc|trailer|musical|game|dlc|expansion|remake|remaster|sequel|prequel|spinoff|reboot|special")
PART = r"season|episode"
NUMBER = r"\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|finale|premiere"
NEW = r"new|newest|latest|upcoming|last|final|first|next"

# Words that make a phrase theirs, not a title. A phrase with one of these in it is never searched. ("my hero academia" and
# "how i met your mother" are lost to this too: Luma asks about those instead of looking. Better that than a leak.)
THEIRS = re.compile(
    r"\b(?:i|i'?m|i'?ve|i'?d|i'?ll|my|mine|myself|our|ours|ourselves|"
    r"mom|mum|mother|dad|father|parents?|sister|brother|son|daughter|kids?|child|children|baby|wife|husband|boyfriend|girlfriend|"
    r"partner|fianc[ée]e?|friends?|bestie|boss|manager|coworkers?|colleagues?|neighbou?rs?|therapist|counsell?or|doctor|nurse|teacher|"
    r"professor|roommate|landlord|ex|uncle|aunt|cousin|grandma|grandpa|grandmother|grandfather|nephew|niece|stepdad|stepmom|"
    r"church|school|class|work|job|office|house|apartment|home|family|band|team|group chat)\b|[@/\\]|https?:|\d{5,}", re.I)
# "me", "us" and "you" are in plenty of titles ("the last of us", "call me by your name"), so they're allowed inside a name,
# never at the front of one ("us last night", "you yesterday").
THEIRS_FIRST = re.compile(r"^(?:me|us|we|you|your|yours|u|ur|him|her|them)\b", re.I)
# Their own making isn't something to look up: "i wrote a new song", "we recorded our new ep".
MADE = re.compile(r"\b(?:wrote|written|writing|made|making|recorded|recording|drew|drawing|built|building|filmed|filming|directed|"
                  r"composed|produced|published|self[- ]published|working on|finished writing|started writing)\b", re.I)
# Words that are never the name between "new" and "album": "a new favorite album", "the new kind of show".
NOT_A_NAME = {"a", "an", "the", "this", "that", "these", "those", "some", "any", "no", "favorite", "favourite", "fav", "own", "little", "big",
              "old", "whole", "same", "other", "kind", "sort", "type", "good", "bad", "great", "best", "worst", "really", "very", "so", "such",
              "one", "it", "and", "or", "but", "is", "was", "are", "were", "be", "to", "for", "with", "at", "on", "in", "from", "about", "like",
              "just", "also", "tv", "video", "board", "card", "phone", "mobile", "computer", "pc", "picture", "photo", "comic", "cook",
              "text", "school", "note", "check", "bank", "audio", "music", "rock", "pop", "rap", "country", "jazz", "horror", "comedy",
              "action", "reality", "true", "crime", "cooking", "kids", "family", "christmas", "holiday", "birthday", "wedding", "baby",
              "show", "series", "movie", "film", "story", "book", "game", "album", "song", "season", "episode", "thing", "stuff", "year",
              "day", "week", "month", "trip", "plan", "life", "night", "weekend", "podcast", "channel", "playlist"}
WORD = r"[\w][\w'&.:-]*"

LEAD = r"^\W*(?:(?:yo|ayo|aye|hey|ok|okay|so|wait|luma|bro|bruh|sis|btw|also|oh|ngl|lowkey|random but|quick question)[, ]+){0,3}"
ASKED = re.compile(
    LEAD + r"(?:"
    r"(?:have |do |did )?(?:you|u|ya)(?: ever| already| even)? (?P<of>heard of|heard about|hear about|know about|know of)|"
    r"(?:have |ever |so have )?(?:you|u|ya)(?: ever| already| even)? (?P<done>seen|watched|heard|listened to|played|read|checked out|caught|peeped)|"
    r"ever (?P<ever>seen|watched|heard|listened to|played|read)|"
    r"did (?:you|u|ya)(?: ever| already| even)? (?P<did>see|watch|hear|listen to|play|read|check out|catch|peep)"
    r")\s+(?P<what>.{2,70}?)\W*$", re.I)
NOT_A_THING = re.compile(r"^(?:me|him|her|them|it|that|this|these|those|what|how|why|when|where|who|whose|if|whether|from|back|anything|"
                         r"something|everything|nothing|any|some|all|about what|the news|the latest|the one|one|both|each)\b", re.I)
UNNAMED = re.compile(rf"^(?:the|that|this|his|her|their|a|an|any|some)?\s*(?:{NEW})?\s*(?P<what>{WORK}|{PART}|part|chapter)s?(?: yet| already| tho(?:ugh)?)?$", re.I)
EVENT = re.compile(r"^(?:the|that|this|last night'?s|tonight'?s|today'?s)\s+(?:game|fight|match|race|finale|premiere|episode|performance|speech|debate|"
                   r"halftime show|announcement)\b", re.I)
VERBS = {"see": "seen", "watch": "watched", "hear": "heard", "listen to": "listened to", "play": "played", "read": "read",
         "check out": "checked out", "catch": "caught", "peep": "seen", "peeped": "seen", "hear about": "heard about"}

# "the new kendrick album", "sza's new single", "the new season of the bear", "season 3 of the white lotus"
NAMED_NEW = re.compile(rf"\b(?:{NEW})\s+(?P<name>(?:{WORD}\s+){{1,4}}?)(?P<kind>{WORK})s?\b", re.I)
WHOSE_NEW = re.compile(rf"\b(?P<name>(?:{WORD}\s+){{0,3}}{WORD}'s)\s+(?:{NEW})\s+(?P<kind>{WORK})s?\b", re.I)
# Where the name stops: "season 3 of the white lotus [is so good]", "the final season of stranger things [wrecked me]".
AFTER = (r"is|was|has|had|got|gets|just|and|but|so|last|this|all|every|yesterday|tonight|today|already|finally|again|rn|right now|with|on|at|"
         r"in|for|because|cause|cuz|since|when|while|til|until|lol|lmao|tbh|ngl|fr|wrecked|made|makes|broke|killed|ended|ends|hit|hits|"
         r"came|comes|dropped|drops|starts|started|slaps|slapped|went|goes|kept|keeps|left|blew|ruined|destroyed|saved|changed|took|takes|"
         r"feels|felt|looks|looked|sounds|sounded|deserves|needs|needed|might|will|would|could|should|can|did|does|really|actually|"
         r"honestly|though|tho|too|still|never|always")
PART_OF = re.compile(rf"\b(?:(?:the\s+)?(?:{NEW})\s+)?(?P<part>{PART})(?:\s+(?:{NUMBER}))?\s+of\s+(?P<name>(?:{WORD}\s+){{0,5}}?{WORD})"
                     rf"(?=\s+(?:{AFTER})\b|\W*$)", re.I)
QUESTION = re.compile(r"[?]|^\W*(?:(?:is|are|was|were|do|does|did|should|would|could|can|have|has|will)\s+(?:you|u|ya|i|we|they|it|he|she|"
                      r"the|this|that|there|anyone|anybody|any)|who|whos|what|whats|which|why|how|where|when)\b", re.I)

HOW = ("They asked if you've {verb} it. You're Luma, a presence in a lamp: you can't hear, watch, play or read it the way they do, so never say you have. Say you "
       "just read up on it, then one or two real things from what was found (what it is, when it came out, what people are saying). Use only "
       "what was found. Then ask what they think of it.")
CLAIMS = re.compile(r"\b(?:yes|yeah|yep|yup),? i(?:'ve| have| did)\b|\bi(?:'ve| have)? (?:just |already |actually )?(?:heard|listened to|watched|"
                    r"seen|saw|played|finished|binged) (?:it|that|the|this|some|all|every)\b|\bi(?:'ve| have) read (?:it|the|that|this)\b|"
                    r"\bwhen i (?:heard|listened|watched|saw|played|read)\b|\bi(?:'ve| have) been (?:listening|watching|playing|reading)\b", re.I)


def private(phrase):
    """Is there anything of theirs in this phrase? Then it isn't a title, and it's never sent anywhere."""
    phrase = str(phrase or "").strip()
    return bool(THEIRS.search(phrase) or THEIRS_FIRST.match(phrase))


def _clean(phrase):
    phrase = re.sub(r"\s+", " ", str(phrase or "")).strip(" \t\n.,!?;:\"“”'")
    phrase = re.sub(r"(?:\s+(?:yet|already|tho|though|lol|lmao|fr|tbh|or nah|or not|at all|by any chance|btw|rn|right now))+$", "", phrase, flags=re.I)
    phrase = re.sub(r"^(?:the|that|this)\s+(?=(?:new|newest|latest|upcoming|final|first|next)\b)", "", phrase, flags=re.I)   # "the new x album" -> "new x album"
    return phrase[:80]


def _thing(phrase):
    """{"what", "query"} for a phrase that names something, or None when it's theirs, too long or not a name at all."""
    phrase = _clean(phrase)
    words = phrase.split()
    if not words or len(words) > 9 or private(phrase) or MADE.search(phrase):
        return None
    return {"what": phrase, "query": phrase.lower()}


def asked(text):
    """"have you heard the new kendrick album": {"what": "new kendrick album", "query": "new kendrick album", "verb": "heard"}.
    "have you heard this album", with nothing named: {"unnamed": "album"}, so Luma can ask which. Otherwise None."""
    text = " ".join(str(text or "").split())
    if not text or len(text) > 160:
        return None
    found = ASKED.match(text)
    if not found:
        return None
    what = found["what"].strip()
    verb = found["done"] or found["did"] or found["of"] or found["ever"]
    verb = VERBS.get(verb.lower(), verb.lower())
    if EVENT.match(what):
        return None   # "did you watch the game": which game? Luma already asks that one its own way
    unnamed = UNNAMED.match(what)
    if unnamed and unnamed["what"].lower() not in ("game", "episode", "part"):
        return {"unnamed": unnamed["what"].lower(), "verb": verb}
    if NOT_A_THING.match(what) or unnamed:
        return None
    thing = _thing(what)
    if not thing or len(thing["what"]) < 3:
        return None
    return {**thing, "verb": verb}


def mentioned(text):
    """"i've been listening to the new kendrick album all day": {"what": "new kendrick album", "query": "new kendrick album"}.
    A statement that brings up something new by name. A question isn't one (those have their own paths), and neither is
    anything of their own ("my new album of baby photos", "i wrote a new song")."""
    text = " ".join(str(text or "").split())
    if not text or len(text) > 240 or QUESTION.search(text) or MADE.search(text):
        return None
    for pattern in (WHOSE_NEW, PART_OF, NAMED_NEW):
        for found in pattern.finditer(text):
            name = found["name"].strip()
            names = [re.sub(r"'s$", "", word.lower()) for word in name.split()]
            if not names or all(word in NOT_A_NAME for word in names):
                continue
            if pattern is NAMED_NEW and any(word in NOT_A_NAME for word in names if word not in ("of", "the", "and", "in", "to")):
                continue   # "a new favorite album", "the new kind of show"
            before = text[max(0, found.start() - 12):found.start()].lower()
            if re.search(r"\b(?:my|our|your|his|her|their)\s+$", before):
                continue   # "my new kendrick album poster"? theirs: leave it
            thing = _thing(found.group(0))
            if thing:
                return thing
    return None


def claims_it_did(reply):
    """Did the reply say Luma heard it, watched it or played it? It can't have."""
    return bool(CLAIMS.search(str(reply or "")))


def note(what, found):
    """What the brain is handed when they only brought the thing up: what Luma just read about it, as information."""
    return f"About {what}: {found}"
