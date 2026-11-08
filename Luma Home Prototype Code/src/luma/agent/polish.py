"""Small slips a small brain makes, fixed before anyone sees them: "the the", "a apple", "an car", "word ,", ",,".

Only the safe ones. Anything that could be on purpose stays: "no no no", "had had", "so so", lowercase replies to
someone who types in lowercase, "!!" and "??", "wait.. what", ellipses, emoji, links and code.
"""
from __future__ import annotations

import re
import zlib

# Doubled words that are almost always a slip (not "had had", "that that", "no no", "very very").
DOUBLED = re.compile(r"\b(the|a|an|to|of|in|on|at|is|it|and|for|with|you|your|my|i|be|was|are|we|they|this|from|but|or|if|as|by)\s+\1\b", re.I)
# "a" before a vowel sound, "an" before a consonant. Words that start with a vowel letter but a consonant sound (and the reverse) are left alone.
A_BEFORE_VOWEL = re.compile(r"\b([Aa]) (?!(?:one|once|uni\w*|use\w*|usu\w*|ute\w*|uto\w*|uro\w*|eu\w*|ewe\w*|uk\w*|ufo\w*|ouija)\b)([aeio]\w*|u(?!ni|s|t|r|k|f|b|ph)\w*)")
AN_BEFORE_CONSONANT = re.compile(r"\b([Aa])n (?!(?:h(?:our|onest|onor|onour|eir|erb)\w*)\b)([b-df-hj-np-tv-z][a-z]\w*)")
A_BEFORE_SILENT_H = re.compile(r"\b([Aa]) (h(?:our|onest|onor|onour|eir)\w*)\b")
SPACE_BEFORE = re.compile(r"(?<=\w) +([,.;:!?])(?=\s|$)")
DOUBLE_COMMA = re.compile(r",\s*,")
SPACES = re.compile(r"(?<=\S) {2,}(?=\S)")
# An em dash between words reads as written, not said: a comma. Lines that start with a dash (lists) and en-dash ranges stay.
EM_DASH = re.compile(r"(?<=[\w)'\"’”])[ \t]*—[ \t]*(?=[\w'\"‘“(])")


def tidy(text):
    """The reply with only the safe fixes made. Code and links are left exactly as they are."""
    if not isinstance(text, str) or not text or "```" in text:
        return text
    parts = _parts(text)
    for i in range(0, len(parts), 2):
        piece = parts[i]
        piece = DOUBLED.sub(lambda m: m.group(1), piece)
        piece = A_BEFORE_VOWEL.sub(lambda m: m.group(1) + "n " + m.group(2), piece)
        piece = AN_BEFORE_CONSONANT.sub(lambda m: m.group(1) + " " + m.group(2), piece)
        piece = A_BEFORE_SILENT_H.sub(lambda m: m.group(1) + "n " + m.group(2), piece)
        piece = SPACE_BEFORE.sub(r"\1", piece)
        piece = DOUBLE_COMMA.sub(",", piece)
        piece = EM_DASH.sub(", ", piece)
        piece = SPACES.sub(" ", piece)
        parts[i] = piece
    return "".join(parts)


def _parts(text):
    return re.split(r"(https?://\S+|`[^`]*`)", text)  # odd pieces are links and inline code: never touched


def slips(text):
    """How many fixes tidy() would make: the language check in the lab counts these across real replies."""
    if not isinstance(text, str) or not text or "```" in text:
        return 0
    prose = _parts(text)[::2]
    return sum(len(p.findall(piece)) for piece in prose
               for p in (DOUBLED, A_BEFORE_VOWEL, AN_BEFORE_CONSONANT, A_BEFORE_SILENT_H, SPACE_BEFORE, DOUBLE_COMMA))


# What a person should never read: a program's error. Caught on the way out, whatever part of Luma it came from.
TECHNICAL = re.compile(r"net::ERR_\w+|\bPage\.\w+:|Traceback \(most recent|\[Errno -?\d+\]|<urlopen error|\b(?:HTTPError|URLError|ConnectionError|"
                       r"ConnectionRefusedError|ConnectionResetError|RemoteDisconnected|TimeoutError|SSLError|SSLCertVerificationError|JSONDecodeError|"
                       r"KeyError|TypeError|AttributeError|IndexError|NameError|OSError|BrokenPipeError)(?:\(|: )|Tunnel connection failed|Max retries exceeded|"
                       r"\bobject at 0x[0-9a-f]+|'NoneType' object|getaddrinfo failed|Name or service not known|nodename nor servname")
NETWORK = re.compile(r"net::ERR_|Tunnel|URLError|urlopen|Connection(?:Error|Refused|Reset)|RemoteDisconnected|timed? ?out|Timeout|Name or service|getaddrinfo|"
                     r"nodename|Errno (?:-?2|-?3|8|51|60|61|64|65|101|110|111|113)\]|SSL|Max retries|unreachable", re.I)


def plain_errors(text):
    """A reply that carries a program's error, said the way a person would: what didn't work, and what to try."""
    if not isinstance(text, str) or "```" in text or len(text) > 400:
        return text  # code, or a real explanation (helping debug someone's code mentions errors on purpose)
    m = TECHNICAL.search(text)
    if not m:
        return text
    online = bool(NETWORK.search(text))
    lead = re.split(r"\s*(?::\s|\s\(|\s—\s|\s-\s)", text[:m.start()], maxsplit=1)[0].strip().rstrip(".:;,(")
    if not (lead.lower().startswith(("i couldn", "i can't", "i didn", "that didn", "that one didn", "i got partway", "i wasn't able")) and len(lead) <= 90):
        lead = "I couldn't reach the internet" if online else "Something went wrong on my side with that one"
    if online and not lead.lower().endswith(("just now", "right now")):
        lead += " just now"
    return lead + (". The connection didn't go through, so check the Wi-Fi and ask me again?" if online else ". Try me again in a minute?")


# -- the small brain's two habits in the device lab: a bare list said to nobody, and saying your message back to you ---------
PERSON = re.compile(r"\b(?:you|your|you're|yours|you'll|you'd|you've|yourself|u|ur|i|i'm|i'd|i'll|i've|me|my|we|we're|let's|us)\b", re.I)
ASKS = re.compile(r"\b(?:what should|what (?:can|do) (?:i|we)|what about|any ideas|ideas|recs?|recommend|suggest|what to (?:get|cook|make|eat|wear|"
                  r"watch|do|say|text)|should i|need (?:a|an|some))\b|\?", re.I)
DOING = {"go", "try", "get", "make", "take", "grab", "watch", "call", "do", "read", "order", "bake", "cook", "text", "play", "put", "start",
         "bring", "buy", "plan", "book", "see", "visit", "write", "throw", "pick", "head", "hit", "check", "join", "sign"}
_FILL = set("""the a an and or but so to of in on at for with is are was were be been it its that this there then than as by from
up out about just really very also too okay ok yeah yes oh lol ngl honestly""".split())


def warm_list(text, said):
    """A bare list said to nobody ("cookies, a smoothie or a fruit salad"), to someone who asked what to do: said to them
    ("How about cookies, a smoothie or a fruit salad?"). Only that shape: lowercase, one line, no "you" or "I" anywhere."""
    if not isinstance(text, str) or not isinstance(said, str):
        return text
    t = text.strip()
    if (not t or not t[0].islower() or "\n" in t or not 3 <= len(t.split()) <= 25 or not re.search(r",| or ", t)  # a list: "x, y or z"
            or PERSON.search(t) or re.search(r"[.!?]\s+\S", t)
            or not ASKS.search(said) or "```" in t or "http" in t):
        return text
    body = t.rstrip(".!? ")
    pick = zlib.crc32(body.encode("utf-8", "ignore"))
    if body.split()[0] in DOING:
        lead, end = [("Maybe ", "."), ("You could ", ".")][pick % 2]
    else:
        lead, end = [("How about ", "?"), ("You could do ", "."), ("Maybe ", ".")][pick % 3]
    return lead + body + end


def _words(text):
    return {w for w in re.findall(r"[a-z']+", text.lower()) if len(w) > 2 and w not in _FILL}


GREETING = re.compile(r"^\W*(?:yo+|hey+|hi+|hello|sup|wass?up|what'?s (?:good|up|poppin)|good (?:morning|night|evening|afternoon)|gm|gn)\b", re.I)


def unparrot(text, said):
    """A reply that opens by saying their message back ("Okay, work was a lot. Long days drain you..."): that first sentence
    goes when there's a real reply after it. Kept when it's all there is, when it's a greeting said back ("Yo, what's good!"),
    and when it quotes them on purpose (Texting Mom: "pullin up in 5")."""
    if not isinstance(text, str) or not isinstance(said, str) or GREETING.search(said):
        return text
    parts = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)
    if len(parts) < 2 or len(parts[1].split()) < 5 or re.search(r'[:"“”]', parts[0]) or len(parts[0].split()) > 12:
        return text
    theirs, mine = _words(said), _words(parts[0])
    shared = theirs & mine
    if len(shared) >= 2 and len(shared) >= len(theirs) / 2 and len(mine - theirs) <= 1:
        rest = parts[1]
        return rest[:1].upper() + rest[1:]
    return text
