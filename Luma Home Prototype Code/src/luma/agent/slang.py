"""Slang: understanding it, noticing how someone talks, and talking back the same way.

Luma reads every message for the slang in it (spelling variants, stretched words like "brooo"
and "slayyy", and plain inflections included), keeps a running picture of how the owner talks,
and turns that into a short note for the brain: their words, how much they cuss, how long they
write, and which community their slang comes from. That last part is there so Luma mirrors the
register a person actually uses (a friend from the same group chat) instead of guessing who
they are or putting on a dialect that isn't theirs.

Slurs are understood and never said: replies are cleaned before anyone hears them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from luma.agent import slang_archive, slang_communities, slang_data

ORIGINS = {**slang_data.ORIGINS, **slang_archive.ORIGINS, **slang_communities.ORIGINS}

# Words that are slang in one sense but everyday English in another ("fire", "tea", "bag"):
# understood and explained, but they don't count as a sign that someone talks in slang.
AMBIGUOUS = {
    "the way", "not the", "it's the ___ for me", "same", "mood", "big", "main", "b", "l", "w", "ice", "fire", "heat", "bag", "bread", "clean",
    "fresh", "link", "crib", "ends", "boss", "loot", "mod", "lag", "carry", "throw", "grind", "meta", "dead", "weak", "crying", "screaming",
    "ship", "bias", "core", "era", "tea", "read", "serve", "mother", "real one", "ghost", "beef", "broke", "hype", "bomb", "tight", "mad", "pop",
    "coke", "fit", "chat", "basic", "extra", "lame", "corny", "foul", "valid", "smoke", "trap", "plug", "lick", "whip", "kicks", "grill", "pause",
    "sus out", "spill", "screw", "crap", "hell", "chill", "legit", "totally", "whatever", "yeah", "yup", "nope", "nah", "kinda", "sorta", "gotcha",
    "for sure", "my bad", "dude", "bro", "mate", "safe", "calm", "long", "bait", "peak", "bare", "son", "slide", "pull up", "facts", "cook",
    "cooked", "gas", "flex", "drip", "fye", "sick", "lit up", "light work", "day one", "aesthetic", "lore", "same", "ick", "red flag", "green flag",
    "ass", "damn", "bitch", "dick", "piss", "streamer", "boss", "respawn", "emote", "camping", "op", "buff", "nerf", "cracked", "throw", "diff",
    "wicked", "reckon", "rad", "stoked", "shred", "mob", "ard", "bul", "brick", "od", "ting", "cheeky", "bloody", "arse", "bugger", "gutted",
    "aura", "chopped", "unc", "tuff", "ate", "gagged", "clock it", "wig", "werk", "realness", "kiki", "shade", "slay", "zesty", "brat",
} | slang_archive.EVERYDAY | slang_communities.EVERYDAY
VULGAR_SAY = {"wtf": "what the fuck", "stfu": "shut the fuck up", "gtfo": "get the fuck out", "idgaf": "I don't give a fuck", "tf": "the fuck",
              "af": "as fuck", "fml": "fuck my life", "lmfao": "laughing my fucking ass off", "mf": "motherfucker", "pmo": "pisses me off"}


@dataclass(frozen=True)
class Entry:
    term: str
    variants: tuple
    origins: tuple
    register: str
    meaning: str
    say: str

    @property
    def label(self):
        return " by way of ".join(ORIGINS.get(o, o) for o in self.origins)


def _key(text):
    return re.sub(r"\s+", " ", str(text).lower().replace("’", "'").strip())


def _extra_lines():
    """Words grown from Wiktionary on this computer (scripts/build_slang.py), if they've been built."""
    try:
        from luma.config import STATE_DIR
        path = STATE_DIR / "slang_extra.tsv"
        return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    except (OSError, ImportError):
        return []


@lru_cache(maxsize=1)
def lexicon():
    """term -> Entry, plus every spelling variant -> the same Entry. Luma's own entries win over grown ones."""
    by_term, forms = {}, {}
    curated = slang_data.LEXICON.splitlines() + slang_archive.LEXICON.splitlines() + slang_communities.LEXICON.splitlines()
    for number, line in enumerate(curated + _extra_lines()):
        grown = number >= len(curated)
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5:
            continue
        term, variants, origins, register, meaning = parts[:5]
        say = parts[5] if len(parts) > 5 else ""
        key = _key(term)
        found = by_term.get(key)
        if grown and found:
            continue
        names = tuple(v for v in (_key(v) for v in variants.split(",")) if v)
        if found:  # the same word listed under two communities: one entry that knows both
            found = Entry(found.term, tuple(dict.fromkeys(found.variants + names)), tuple(dict.fromkeys(found.origins + tuple(origins.split("+")))),
                          found.register, found.meaning, found.say)
        else:
            found = Entry(term, names, tuple(origins.split("+")), register, meaning, say or term)
        by_term[key] = found
    for key, entry in by_term.items():
        forms.setdefault(key, entry)
        for v in entry.variants:
            forms.setdefault(v, entry)
    return by_term, forms


@lru_cache(maxsize=1)
def _phrases():
    """Multi-word forms, longest first, as one pattern."""
    _, forms = lexicon()
    multi = sorted((f for f in forms if " " in f and "___" not in f), key=len, reverse=True)
    return re.compile(r"(?<![\w'])(" + "|".join(re.escape(f).replace(r"\ ", r"[\s-]+") for f in multi) + r")(?![\w'])", re.I)


def _candidates(token):
    """'slayyy' -> slayyy, slayy, slay; 'bussin'' -> bussin; 'cappin' -> cappin, cap."""
    seen = []
    for t in (token, re.sub(r"(.)\1{2,}", r"\1\1", token), re.sub(r"(.)\1+", r"\1", token)):
        t = t.strip("'")
        if t and t not in seen:
            seen.append(t)
    for t in list(seen):
        for suffix, back in (("in'", ""), ("in", ""), ("ing", ""), ("ed", ""), ("s", ""), ("z", "")):
            if t.endswith(suffix) and len(t) - len(suffix) >= 3:
                base = t[: -len(suffix)] + back
                for b in (base, base[:-1] if len(base) > 3 and base[-1] == base[-2] else base):
                    if b not in seen:
                        seen.append(b)
    return seen


def _plain(text):
    """Accents off, for a second try: "órale" -> "orale"."""
    import unicodedata
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def find(text):
    """Every slang entry in a message, once each, in order: [(what they typed, Entry)]. A word inside a phrase that was
    already found doesn't count again ("no cap" is "for real", not also "cap", a lie)."""
    _, forms = lexicon()
    low = _key(text)
    out, taken, covered = [], set(), []
    plain_low = _plain(low)
    for source in (low, plain_low) if plain_low != low else (low,):
        for m in _phrases().finditer(source):
            entry = forms.get(_key(re.sub(r"[\s-]+", " ", m.group(1))))
            if entry:
                covered.append(m.span(1))
                if entry.term not in taken:
                    out.append((m.group(1), entry))
                    taken.add(entry.term)
    for m in re.finditer(r"[^\W_][\w'*.;-]*", low):  # letters in any language: "órale", "güey", "híjole"
        if any(a <= m.start() and m.end() <= b for a, b in covered):
            continue
        token = m.group(0).rstrip(".;-")
        plain = _plain(token)
        for c in _candidates(token) + ([] if plain == token else _candidates(plain)):
            entry = forms.get(c)
            if entry:
                if entry.term not in taken:
                    out.append((token, entry))
                    taken.add(entry.term)
                break
    return out


# Everyday words that the dictionary also lists as a spelling of a slang word. Typed like this they're the everyday
# word: "my dog" is a dog, "he's gone" is gone, "coping" is coping. The slang spelling still counts (dawg, gon, copium).
PLAIN_SPELLINGS = frozenset("""dog gone child period youth suspect giving band rack stack sweat sweating sweats cope coping lacking
totally goon dam da""".split())
# Slang words that are everyday words too, and how the everyday one is used: "i woke up", "i bet it rains", "lit a candle",
# "based on", "the twins". Said that way they aren't slang. Keyed by the dictionary's own spelling.
_WHO = r"(?:my|his|her|our|their|your|uncle|aunt|cousin|friend|brother|dad|grandpa|coworker|neighbou?r|boss|mr\.?)"
PLAIN_USE = {term: re.compile(pattern) for term, pattern in {
    "woke": r"\bwoke\s+(?:up|me|him|her|us|them|at|to|early|late|in|from)\b|\b(?:i|we|he|she|they|it|just|finally|baby|kids?|dog|cat)\s+woke\b",
    "shook": r"\bshook\s+(?:my|his|her|their|our|the|a|hands?|it|up|off|me|him|them)\b",
    "pressed": r"\bpressed\s+(?:the|a|an|my|his|her|on|into|against|charges|down|play|send|enter|record|pause)\b",
    "bet": r"\b(?:i|i'll|i'd|you|we|they|he|she|wanna|a|the|my|your|safe|sure|best)\s+bet\b|\bbet\s+(?:on|you|he|she|they|it|that|against|money|\$?\d)",
    "based": r"\bbased\s+(?:on|in|off|out|around|upon)\b",
    "lit": r"\blit\s+(?:a|an|the|my|his|her|up|it|them|some|candles?|fire)\b|\b(?:well|dimly|brightly|poorly)[\s-]lit\b",
    "mid": r"\bmid[\s-]+(?:\d|morning|afternoon|day|night|week|month|year|summer|winter|spring|fall|sentence|air|way|life|twenties|thirties|"
           r"forties|fifties|january|february|march|april|may|june|july|august|september|october|november|december|size|range|level|"
           r"town|field|term|season|flight|shift)",
    "cap": r"\b(?:a|an|the|my|his|her|your|this|baseball|bottle|gas|shower|swim|knee|salary|price|data)\s+caps?\b|\bcaps?\s+(?:on|off|lock|and\s+gown)\b",
    "goat": r"\bgoats\b|\b(?:a|an|pet|baby|mountain|billy|our|their)\s+goat\b|\bgoat\s+(?:cheese|milk|farm|yoga)\b",
    "salty": r"\bsalty\s+(?:food|soup|snack|chips|fries|water|taste|air)\b|\b(?:soup|food|fries|chips|sauce|dinner|popcorn|it|this|that)\s+"
             r"(?:was|is|tastes?|tasted)\s+(?:too\s+|so\s+|really\s+|a\s+bit\s+)?salty\b(?!\s+(?:about|at|with|over|cause|because))",
    "thirsty": r"\bthirsty\b(?!\s+(?:for\s+(?:attention|him|her|likes|clout|me)|in\s+(?:my|the|his|her)\s+(?:dms|comments|mentions)|on\s+(?:main|the\s+tl)))",
    "ratio": r"\b(?:the|a|an|this|that|aspect|gear|mix|debt|right|wrong|golden)\s+ratio\b|\bratio\s+(?:of|is|was|between|for)\b",
    "dope": r"\b(?:does|do|did|doing|done|on|smok\w+|sell\w*|sold|deal\w*|us\w+|shoot\w*|shot)\s+dope\b",
    "stan": rf"\b{_WHO}\s+(?:\w+\s+)?stan\b|\bstan\s+(?:is|was|said|called|and|has|will|did|does|came|went)\b",
    "chad": rf"\b{_WHO}\s+(?:\w+\s+)?chad\b|\bchad\s+(?:is|was|said|called|and|has|will|did|does|came|went)\b",
    "twin": r"\btwins\b|\btwin\s+(?:sister|brother|boys?|girls?|sons?|daughters?|babies|beds?|size)\b",
    "ahh": r"(?:^|[.!?,]\s*)a+h{2,}\b|\ba+h{2,}\s*(?:$|[.!?,])",  # a shout, not "goofy ahh"
    "trippin": r"\btripping\s+(?:over|on\s+(?:the|my|a|his|her)|up|and\s+fell)\b",
    "tweakin": r"\btweaking\s+(?:my|the|a|an|it|this|that|some|settings|things)\b",
    "buggin": r"\bbugging\s+(?:me|him|her|us|them|you)\b",
    "bussin": r"\bbussing\s+(?:tables|dishes|trays|kids|students|people|them)\b|\b(?:school|city)\s+bussing\b",
}.items()}


def _plainly(said, entry, low):
    """An everyday word in its everyday sense, in this message."""
    term = _key(entry.term)
    if said in PLAIN_SPELLINGS and term != said:
        return True
    use = PLAIN_USE.get(term)
    return bool(use and use.search(low))


def heard(text):
    """The slang in a message as Luma hears it: find(), without the everyday words in their everyday sense ("my dog",
    "he's gone", "i woke up", "i bet it rains"). When they're asking what a word means, the dictionary answers as it is."""
    if ASKING.search(str(text or "")):
        return find(text)
    low = _key(text)
    return [(said, entry) for said, entry in find(text) if not _plainly(_key(said), entry, low)]


def explain(term):
    """What a word means and where it's from, for "what does X mean?"."""
    _, forms = lexicon()
    for c in _candidates(_key(term)):
        entry = forms.get(c)
        if entry:
            return entry
    return None


def details(term):
    """Where a word comes from, how it's used, and an example sentence, when the archive has them: (origin, usage, example)."""
    entry = explain(term)
    if not entry:
        return None
    for name in (entry.term,) + entry.variants:
        found = slang_archive.DETAILS.get(name)
        if found:
            return found
    return None


def signals(text):
    """The parts of one message that say how someone talks: real slang (not everyday words), cussing, and energy."""
    found = heard(text)
    strong = [(said, e) for said, e in found if _key(e.term) not in AMBIGUOUS and e.register in ("c", "v")]
    letters = re.sub(r"[^A-Za-z]", "", text)
    return {
        "terms": [e.term for _, e in strong if e.register == "c"],
        "cuss": sum(1 for _, e in found if e.register == "v"),
        "families": [o for _, e in strong if e.register == "c" for o in e.origins if o not in ("general", "internet")],
        "caps": len(letters) >= 6 and letters.isupper(),
        "laughing": bool(re.search(r"(?<!\w)(?:l+o+l+|l+m+f*a+o+|ha(?:ha)+|i'?m (?:dead|weak|crying|screaming)|dead+ ?💀|stop+ it)(?!\w)|[😂🤣😭💀]", text, re.I)),
        "slurs": bool(_slur_re().search(text)),
    }


def learn(stats, text):
    """Add one message to the running picture of how they talk (kept in the owner's settings)."""
    stats = dict(stats or {})
    sig = signals(text)
    terms = dict(stats.get("terms") or {})
    for t in sig["terms"]:
        terms[t] = terms.get(t, 0) + 1
    stats["terms"] = dict(sorted(terms.items(), key=lambda kv: -kv[1])[:40])
    families = dict(stats.get("families") or {})
    for f in sig["families"]:
        families[f] = families.get(f, 0) + 1
    stats["families"] = families
    stats["cuss"] = int(stats.get("cuss", 0)) + sig["cuss"]
    stats["slangy"] = int(stats.get("slangy", 0)) + int(bool(sig["terms"]))
    stats["caps"] = int(stats.get("caps", 0)) + int(sig["caps"])
    return stats


def leaning(stats):
    """The one or two communities their slang comes from: seen at least twice, through at least two different words,
    so one borrowed word doesn't make anyone a member of anything."""
    stats = stats or {}
    families = {f: c for f, c in (stats.get("families") or {}).items() if c >= 2}
    distinct = {f: len({t for t in (stats.get("terms") or {}) if f in _origins_of(t)}) for f in families}
    return [f for f, c in sorted(families.items(), key=lambda kv: -kv[1]) if distinct.get(f, 0) >= 2][:2]


def circle_words(communities, used=(), limit=8):
    """Real words from their circle Luma may use back (with meanings), minus the ones they already use."""
    from luma.agent import phrasebank
    have = {_key(t) for t in used}
    out = []
    for community in communities:
        for term, meaning in phrasebank.voice(community, limit + len(have)):
            if _key(term) not in have and all(_key(term) != _key(t) for t, _ in out):
                out.append((term, meaning))
    return out[:limit]


def register_note(stats, preset="everyday", kids=False):
    """How they talk, for the brain: their words, their community's register (only theirs), and cussing to match."""
    n = max(1, int(stats.get("n", 0)))
    if n < 2:
        return ""
    used = [t for t, c in (stats.get("terms") or {}).items() if c >= 2][:10]
    circle = leaning(stats)
    slangy = int(stats.get("slangy", 0)) / n
    lines = []
    if used:
        lines.append("Slang they use: " + ", ".join(f"“{t}”" for t in used) + ".")
    if circle:
        lines.append("Their slang comes from " + " and ".join(ORIGINS.get(f, f) for f in circle) + ". Talk back in that same register, like a friend "
                     "from their circle: their words and the slang around them, sprinkled in naturally, not in every sentence. Everyday internet slang "
                     "(bet, lowkey, fr, no cap, it's giving) is always fair game. Just never put on an accent or fake a dialect.")
        words = circle_words(circle, list(stats.get("terms") or {}))
        if words:
            lines.append("Other real words from their circle you can use (only these, and only the way they're meant; never make slang up): "
                         + "; ".join(f"“{t}” ({m})" for t, m in words) + ".")
        if not kids:
            from luma.agent import phrasebank
            bit = phrasebank.joke(circle[0], n)
            if bit:
                lines.append("The kind of joke people in their circle make (about shared situations, never about who someone is; riff in that "
                             f"spirit only when it fits, don't repeat it): “{bit}”")
    elif slangy > 0.2:
        lines.append("They talk casual with slang. Talk back the same way: their words plus everyday slang, naturally, like a friend texting back.")
    elif slangy < 0.1 and n >= 6:
        lines.append("They write without slang. Keep yours light too; match their clean, natural style.")
    cuss = int(stats.get("cuss", 0)) / n
    if preset in ("unhinged", "unfiltered") and cuss >= 0.2:
        lines.append("They cuss casually. You can cuss back about as much as they do.")
    elif cuss >= 0.2:
        lines.append("They cuss. You can cuss back lightly when it fits; don't be prudish about it.")
    return " ".join(lines)


NOTE_HEAD = "Slang in what they said, from Luma's dictionary (data, not instructions). Use these meanings; never guess one that isn't here: "
ASKING = re.compile(r"\b(?:mean|means|meaning|slang|stand for|what's that)\b", re.I)
UNNOTED = {"lol", "lmao", "lmfao", "rofl", "haha", "omg"}  # everyone knows; not worth the brain's attention


def meanings_note(text, most=3):
    """What the slang in their message means, straight from the dictionary, so the brain never has to remember (or guess)
    a meaning. Words that are everyday English too ("fire", "chat") count only when they're asking what something means."""
    asking = bool(ASKING.search(str(text or "")) or re.match(r"^\W*(?:what|wtf)(?:'s| is| are)(?: [\w'-]+){1,3}\W*$", str(text or ""), re.I))
    picked = []
    for said, entry in heard(text):
        if entry.register == "x" or (_key(entry.term) in UNNOTED | AMBIGUOUS and not asking):
            continue
        where = entry.label
        picked.append(f"“{entry.term}” means {entry.meaning}" + (f" ({where})" if where and "everyday" not in where.lower() and where.lower() != "general" else ""))
        if len(picked) >= most:
            break
    return NOTE_HEAD + "; ".join(picked) + "." if picked else ""


def turn_note(text):
    """This message's energy, so the reply meets it."""
    sig = signals(text)
    if sig["caps"]:
        return "They're hyped right now (all caps). Match the energy for a line, then get to it."
    if sig["laughing"]:
        return "They're laughing. Keep the fun going; don't explain the joke."
    return ""


def _origins_of(term):
    entry = lexicon()[0].get(_key(term))
    return entry.origins if entry else ()


@lru_cache(maxsize=1)
def _slur_re():
    return re.compile("|".join(slang_data.SLURS), re.I)


def clean(text):
    """Luma never says a slur, whatever the mode or the model. The casual n-word becomes "bro"; the rest go."""
    if not isinstance(text, str) or not _slur_re().search(text):
        return text
    text = re.sub(r"\bn[i1!|]gg(?:a|ah|uh)(s|z)?\b", lambda m: "bros" if m.group(1) else "bro", text, flags=re.I)
    text = re.sub(r"\bn[i1!|]gg(?:as|az)\b", "bros", text, flags=re.I)
    text = _slur_re().sub("—", text)
    return re.sub(r"\s+—\s*", " ", text).replace(" ,", ",").strip()


def say_explicit(text):
    """Unhinged mode out loud: "wtf" is said the way they meant it."""
    pattern = re.compile(r"(?<![\w'])(" + "|".join(sorted(VULGAR_SAY, key=len, reverse=True)) + r")(?![\w'])", re.I)
    return pattern.sub(lambda m: VULGAR_SAY[m.group(1).lower()], text)


def size():
    """How much Luma knows: entries, and the spellings it recognizes before stretching and endings."""
    by_term, forms = lexicon()
    return {"entries": len(by_term), "forms": len(forms), "communities": len({o for e in by_term.values() for o in e.origins})}
