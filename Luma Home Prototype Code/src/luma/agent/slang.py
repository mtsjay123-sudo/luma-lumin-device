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

from luma.agent import slang_data

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
}
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
        return " by way of ".join(slang_data.ORIGINS.get(o, o) for o in self.origins)


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
    curated = slang_data.LEXICON.splitlines()
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


def find(text):
    """Every slang entry in a message, once each, in order: [(what they typed, Entry)]."""
    _, forms = lexicon()
    low = _key(text)
    out, taken = [], set()
    for m in _phrases().finditer(low):
        entry = forms.get(_key(re.sub(r"[\s-]+", " ", m.group(1))))
        if entry and entry.term not in taken:
            out.append((m.group(1), entry))
            taken.add(entry.term)
    for token in re.findall(r"[a-z0-9][a-z0-9'*.;-]*", low):
        token = token.rstrip(".;-")
        for c in _candidates(token):
            entry = forms.get(c)
            if entry:
                if entry.term not in taken:
                    out.append((token, entry))
                    taken.add(entry.term)
                break
    return out


def explain(term):
    """What a word means and where it's from, for "what does X mean?"."""
    _, forms = lexicon()
    for c in _candidates(_key(term)):
        entry = forms.get(c)
        if entry:
            return entry
    return None


def signals(text):
    """The parts of one message that say how someone talks: real slang (not everyday words), cussing, and energy."""
    found = find(text)
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


def register_note(stats, preset="everyday"):
    """How they talk, for the brain: their words, their community's register (only theirs), and cussing to match."""
    n = max(1, int(stats.get("n", 0)))
    if n < 3:
        return ""
    used = [t for t, c in (stats.get("terms") or {}).items() if c >= 2][:8]
    families = {f: c for f, c in (stats.get("families") or {}).items() if c >= 3}
    distinct = {f: len({t for t in (stats.get("terms") or {}) if f in _origins_of(t)}) for f in families}
    leaning = [f for f, c in sorted(families.items(), key=lambda kv: -kv[1]) if distinct.get(f, 0) >= 2][:2]
    slangy = int(stats.get("slangy", 0)) / n
    lines = []
    if used:
        lines.append("Slang they use: " + ", ".join(f"“{t}”" for t in used) + ".")
    if leaning:
        lines.append("Their slang comes from " + " and ".join(slang_data.ORIGINS.get(f, f) for f in leaning) + ". Talk back in that same register, like a friend "
                     "from their circle: their words, at about their rate, never in every sentence. Don't pull in slang from a community they haven't used, "
                     "and never put on an accent or a dialect.")
    elif slangy > 0.3:
        lines.append("They talk casual with slang. Talk back the same way, naturally, using their words.")
    elif slangy < 0.1 and n >= 6:
        lines.append("They write without slang. Keep yours out too; match their clean, natural style.")
    cuss = int(stats.get("cuss", 0)) / n
    if preset in ("unhinged", "unfiltered") and cuss >= 0.2:
        lines.append("They cuss casually. You can cuss back about as much as they do.")
    elif cuss >= 0.2:
        lines.append("They cuss sometimes. You don't need to, but don't be prudish about it.")
    return " ".join(lines)


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
