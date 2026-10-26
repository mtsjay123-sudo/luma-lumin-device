"""Text the way it should sound out loud.

People type "ngl gng that's crazy 😭" but say "not gonna lie, gang, that's crazy" and laugh.
This turns written replies into what a person would actually say: texting shorthand spoken
in full, laughs as laughs (an expressive voice can really laugh; the plain voice just takes a
beat), and pauses where a person would breathe: a beat after "okay so," or "ngl,", a longer
one at "...", a slightly longer one after a question, and the most between paragraphs.
"""
from __future__ import annotations

import re
import zlib

LAUGH = "⟨laugh⟩"   # ⟨laugh⟩: a real laugh in an expressive voice, a short beat in the plain one
SIGH = "⟨sigh⟩"
BREAK = "⟨p⟩"       # a paragraph's worth of pause

# What people type, and what they say out loud.
SAY = {
    "ngl": "not gonna lie", "gng": "gang", "fr": "for real", "frfr": "for real for real", "fr fr": "for real for real",
    "istg": "I swear to God", "idk": "I don't know", "idc": "I don't care", "ion": "I don't", "ian": "I ain't",
    "tbh": "to be honest", "tbf": "to be fair", "rn": "right now", "imo": "in my opinion", "imho": "in my honest opinion",
    "wya": "where you at", "wyd": "what you doing", "hbu": "how about you", "wbu": "what about you", "ong": "on God",
    "nvm": "never mind", "omg": "oh my God", "omfg": "oh my God", "brb": "be right back", "ty": "thank you",
    "tysm": "thank you so much", "np": "no problem", "icl": "I can't lie", "ily": "I love you", "lmk": "let me know",
    "hmu": "hit me up", "tho": "though", "thx": "thanks", "pls": "please", "plz": "please", "ppl": "people",
    "bc": "because", "cuz": "'cause", "u": "you", "ur": "your", "yk": "you know", "ykwim": "you know what I mean",
    "jk": "just kidding", "irl": "in real life", "afaik": "as far as I know", "tmrw": "tomorrow", "tmr": "tomorrow",
    "2day": "today", "2nite": "tonight", "lowk": "lowkey", "highk": "highkey", "pmo": "pisses me off",
    "wtf": "what the heck", "wth": "what the heck", "fyi": "just so you know", "bf": "boyfriend", "gf": "girlfriend",
    "bday": "birthday", "w/": "with", "w/o": "without", "b/c": "because", "smth": "something", "sm": "so much",
    "abt": "about", "prolly": "probably", "def": "definitely", "obv": "obviously", "esp": "especially",
}
_WORDS = sorted(SAY, key=len, reverse=True)
_SAY_RE = re.compile(r"(?<![\w'/])(" + "|".join(re.escape(w) for w in _WORDS) + r")(?![\w'/])", re.I)
# "fr", "u", "ur", "def", "sm" and "bc" are also ordinary letters or words in other places (an "FR-8" part, "def"
# in code): only take them when they're lowercase, the way they're texted.
_LOWER_ONLY = {"u", "ur", "fr", "def", "sm", "bc", "esp", "obv", "abt", "bf", "gf"}

LAUGH_WORDS = re.compile(r"(?<!\w)(?:l+o+l+|l+m+a+o+|l+m+f+a+o+|ha(?:ha)+h?|ha ha(?: ha)*|he(?:he)+|rofl)(?!\w)", re.I)
LAUGH_EMOJI = re.compile("[\U0001F602\U0001F923\U0001F62D\U0001F480☠\U0001F606\U0001F639]️?")  # 😂 🤣 😭 💀 ☠ 😆 😹
SIGH_EMOJI = re.compile("(?:\U0001F62E‍\U0001F4A8|\U0001F644|\U0001F612|\U0001F611|\U0001F629|\U0001F62B)️?")  # 😮‍💨 🙄 😒 😑 😩 😫
OTHER_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]")
SMH = re.compile(r"(?<!\w)smh(?!\w)", re.I)

# Openers people take a beat after: "Okay so, ...", "Not gonna lie, ...", "Real talk, ...".
OPENERS = re.compile(r"^(?:okay so|ok so|so basically|not gonna lie|real talk|honestly|look|listen|wait|hmm+|um+|okay|ok|so|yo|nah|yeah|bet|"
                     r"gang|for real|lowkey|bro|girl|man|oh|ooh|ah|alright|anyway|anyways|I can't lie|to be honest)"
                     r"(?:,? (?:gang|bro|girl|man|fam))?,\s+", re.I)


EXPLICIT = {"on": False}  # unhinged mode: "wtf" is said the way it was meant


def say_it(text):
    """Shorthand spoken in full, laughs and sighs marked, other emoji dropped."""
    if EXPLICIT["on"]:
        from luma.agent import slang
        text = slang.say_explicit(text)
    def word(match):
        raw = match.group(1)
        key = raw.lower()
        if key in _LOWER_ONLY and raw != key:
            # "U good?" at the start of a sentence still means "you", but "U.S." and "FR-8" don't.
            rest = match.string[match.end():match.end() + 2]
            if not (key in ("u", "ur") and raw in ("U", "Ur") and re.match(r" [a-z]", rest)):
                return raw
        out = SAY[key]
        if raw[0].isupper():
            out = out[0].upper() + out[1:]
        return out
    text = SIGH_EMOJI.sub(" " + SIGH + " ", text)
    text = LAUGH_EMOJI.sub(" " + LAUGH + " ", text)
    text = LAUGH_WORDS.sub(" " + LAUGH + " ", text)
    text = SMH.sub(" " + SIGH + " ", text)
    text = OTHER_EMOJI.sub("", text)
    text = _SAY_RE.sub(word, text)
    text = re.sub(r"(?:\s*" + LAUGH + r")+", " " + LAUGH, text)  # one laugh, not three
    text = re.sub(r"(?:\s*" + SIGH + r")+", " " + SIGH, text)
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    # Said out loud, "ngl gang that's crazy" has commas in it: "Not gonna lie, gang, that's crazy".
    text = re.sub(r"(?i)(^|[.!?]\s+)(not gonna lie|to be honest|to be fair|I can't lie|real talk|on God|for real for real|for real|I swear to God|in my opinion)"
                  r"(?:\s+(gang|bro|fam|girl|twin))?(?=\s+\w)(?!,)",
                  lambda m: m.group(1) + m.group(2) + ("," + " " + m.group(3) if m.group(3) else "") + ",", text)
    text = re.sub(r"(?<=\w) (gang|twin|fam)(?= \w)(?!,)", r", \1,", text) if re.search(r"(?i)\b(gang|twin|fam) (how|what|why|you|we|i|that|this|it)\b", text) else text
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text[:1].upper() + text[1:]


# Replies that should come out crisp, not thought about: confirmations, things Luma did, hard moments.
CRISP = re.compile(r"(?i)^(?:got it|done|okay,? i'?ll|ok,? i'?ll|i'?ll|here'?s|found|playing|opening|your |saved|sent|set|added|reminder|timer|"
                   r"mic'?s|i can'?t|i couldn'?t|i'?m really glad you told me|you got cut off|my bad|good (?:morning|night|evening|afternoon)|"
                   r"why did|what do you call|i'?m reading|i only know)\b")
THINK_START = re.compile(r"(?i)^(?:i'?d|i think|i feel like|honestly|probably|maybe|it depends|depends|i'?m not sure|the|that'?s|that|"
                         r"i (?:like|love|lean|prefer|wouldn'?t|would)|if i were you|personally|kinda|lowkey|it'?s|it was|you should|you could)\b")
THINK_MID = re.compile(r"\b(?:I think|I feel like|I'd say|I'd probably|I'd go with|probably|honestly|the real question is)\b(?![,.])")


def think_aloud(text):
    """Now and then, a thinking sound where a person would make one: "Hmm... I'd go with the black one", "I think, um, the
    second one". Real people do it when they're weighing something, not when they're confirming a reminder, reading a number
    or helping someone through a hard moment, so those stay crisp. At most one per reply, about a third of the replies that
    could take one, and always the same for the same words (so it sounds natural, not random every replay)."""
    t = (text or "").strip()
    if (len(t.split()) < 8 or re.search(r"\d|988|[“”\"]", t) or CRISP.match(t) or OPENERS.match(t)
            or re.match(r"(?i)^(?:uh|um|hmm|okay so|so)\b", t)):
        return text
    h = zlib.crc32(t.encode("utf-8", "ignore"))
    if h % 100 >= 35:
        return text
    pick = (h // 100) % 4
    if THINK_START.match(t):
        lead = ["Hmm...", "Okay so,", "Uh,", "Mm..."][pick]
        rest = t if re.match(r"I\b|I'", t) else t[:1].lower() + t[1:]
        return f"{lead} {rest}"
    m = THINK_MID.search(t)
    if m:
        return t[:m.end()] + [", um,", "... uh,", ", like,", "..."][pick] + t[m.end():]
    return text


def for_voice(text, expressive=False):
    """The cue marks as a given voice wants them: [laugh]/[sigh] for an expressive voice, nothing for the plain one."""
    if expressive:
        text = text.replace(LAUGH, "[laugh]").replace(SIGH, "[sigh]")
    else:
        text = text.replace(LAUGH, "").replace(SIGH, "")
    text = text.replace(BREAK, "")
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"^[\s,.;:]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


PAUSES = {".": 300, "!": 260, "?": 380, "…": 520, ",": 150, ";": 220, ":": 220, "-": 200, "opener": 160, "laugh": 220, "sigh": 260, "break": 600}


def _jitter(ms, seed):
    """A little natural variation, the same every time for the same words."""
    wobble = (zlib.crc32(seed.encode("utf-8", "ignore")) % 25 - 12) / 100.0
    return int(round(ms * (1 + wobble)))


def beats(text):
    """Split speech where a person takes a real breath: paragraph breaks, "...", laughs, dashes and openers.
    Returns [(words, kind of pause after)]; sentences inside a beat stay together so their melody connects."""
    out = []
    for para in [p for p in text.split(BREAK)]:
        pieces = re.split(r"(\.\.\.+|…|" + LAUGH + "|" + SIGH + r"|\s[—–-]\s|—)", para)
        current = ""
        for piece in pieces:
            if piece is None or not piece.strip():
                if piece and current:
                    current += piece
                continue
            if piece in ("...", "…") or re.fullmatch(r"\.\.\.+", piece):
                if current.strip():
                    out.append([current.strip(), "…"])
                current = ""
            elif piece == LAUGH or piece == SIGH:
                if current.strip():
                    out.append([current.strip(), "laugh" if piece == LAUGH else "sigh"])
                out.append([piece, "laugh" if piece == LAUGH else "sigh"])
                current = ""
            elif re.fullmatch(r"\s?[—–-]\s?", piece):
                if current.strip():
                    out.append([current.strip(), "-"])
                current = ""
            else:
                current += piece
        if current.strip():
            out.append([current.strip(), None])
        if out:
            out[-1][1] = "break"
    if out and not text.rstrip().endswith(BREAK):
        out[-1][1] = None  # the very end: just its own punctuation's pause
    # A beat after an opener at the start of a sentence ("Okay so, ..."), if what follows is a real sentence.
    final = []
    for words, after in out:
        m = OPENERS.match(words)
        if m and len(words) - m.end() > 12:
            final.append([words[:m.end()].strip(), "opener"])
            final.append([words[m.end():].strip(), after])
        else:
            final.append([words, after])
    return [(w, a) for w, a in final if w]


def pause_ms(chunk, after=None):
    """How long to wait after a chunk: what the beat ended with, else its last punctuation."""
    if after == "break":
        base = PAUSES["break"]
    elif after:
        base = PAUSES.get(after, 200)
    else:
        end = chunk.rstrip()[-1:] if chunk.strip() else "."
        base = PAUSES.get(end, 180)
    return _jitter(base, chunk)
