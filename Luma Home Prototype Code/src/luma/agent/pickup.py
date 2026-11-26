"""A friend picks up your words the first time (docs/PRESENCE_MASTER_PROMPT.md, 3.2).

They say a word Luma has never heard, one of their own. Luma keeps it with the sentence it came in, and the
brain is told, that same turn: this is their word, work out what it means from how they used it, and you can use it
back once. It's kept as theirs: shown in the app, forgotten with a tap or with everything.

What counts as new: a word that isn't in anything Luma has heard (its own packs, slang dictionary and documents:
`heard_words.txt.gz`, made by `scripts/build_heard_words.py`), isn't a slip of the fingers for one that is, isn't a
name, a laugh or a drawn-out word, and comes inside a sentence. Luma's list is small (twenty thousand words), so an
ordinary word it doesn't have can be taken for new; the note says so and tells the brain to leave an ordinary word alone.

Never while they're hurting or might not be safe, and never in kids mode: those turns are for something else.

No made-up word is written anywhere in Luma's code or documents as an example: the list is built from them, so a word
written there is a word Luma "has heard". The examples live in tests/pickup_lines.py, which the list never reads.
"""
from __future__ import annotations

import gzip
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

KEY = "picked_up"
KEEP = 40
WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
ENDINGS = ("'s", "ing", "ings", "ed", "es", "s", "ly", "er", "ers", "est", "y", "ish", "ness", "ful", "less", "able", "n't", "'d", "'ll", "'ve", "'re", "in")
LAUGH = re.compile(r"^(?:(?:ha|he|hi|ho|ah|eh|lo|ja|ka|bw?a)+h?|l+o+l+(?:ol)*|l+m+f*a+o+|r+o+f+l+|a+w+|o+h+|u+g+h+|h+m+|m+h*m+|y+a+s+|e+w+|z+)$")
LETTERS = "abcdefghijklmnopqrstuvwxyz"


COMMON = 15   # seen this often in Luma's own text, a word is one people mistype ("again", "believe", "tomorrow")


@lru_cache(maxsize=1)
def heard():
    """Every word Luma has heard, with how often its own text has it."""
    try:
        with gzip.open(Path(__file__).with_name("heard_words.txt.gz"), "rt") as f:
            return {word: int(count) for word, count in (line.split() for line in f.read().splitlines() if line.strip())}
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=1)
def common():
    return frozenset(word for word, count in heard().items() if count >= COMMON)


def _known(word, known):
    """This word, or the plain word it's made from, is one Luma has heard."""
    if word in known:
        return True
    for end in ENDINGS:
        if word.endswith(end) and len(word) - len(end) >= 2:
            stem = word[:-len(end)]
            if stem in known or stem + "e" in known or (stem[-1:] == stem[-2:-1] and stem[:-1] in known) or (end in ("es", "ed", "er", "est") and stem[-1:] == "i" and stem[:-1] + "y" in known):
                return True
    return False


def _slip(word, known):
    """A slip of the fingers for a common word: one letter wrong, missing, extra, or two swapped. Only toward a common
    word: "agian" is "again", but a coined word isn't a slip just because some rare word is a letter away. (The first
    forty made-up words: 17 were waved through as slips for some word or other.)"""
    known = common()
    for i in range(len(word) + 1):
        if i < len(word):
            if _known(word[:i] + word[i + 1:], known):                                   # one letter extra
                return True
            if i < len(word) - 1 and _known(word[:i] + word[i + 1] + word[i] + word[i + 2:], known):   # two swapped
                return True
        for c in LETTERS:
            if _known(word[:i] + c + word[i:], known):                                    # one letter missing
                return True
            if i < len(word) and c != word[i] and _known(word[:i] + c + word[i + 1:], known):   # one letter wrong
                return True
    return False


def new_words(text, theirs=()):
    """The words in what they said that Luma has never heard, in the order they came. theirs: words already picked up."""
    said = str(text or "")
    tokens = WORD.findall(said)
    if len(tokens) < 4 or len(said) > 400:
        return []          # a word alone isn't used in anything to learn it from
    known, have, out = heard(), {t.lower() for t in theirs}, []
    for n, token in enumerate(tokens):
        word = token.lower()
        if not 3 <= len(word) <= 16 or word in have or word in out or "'" in word:
            continue
        if token[:1].isupper() and not said.isupper() and (n > 0 or len(tokens) > 1 and not said[:1].islower()) and not token.isupper():
            if n > 0:
                continue   # a name, said the way names are written
        if _known(word, known):
            continue
        squeezed = re.sub(r"(.)\1{2,}", r"\1", word)        # "sooooo", "stoppp", "yesssss"
        if squeezed != word and (_known(squeezed, known) or _known(re.sub(r"(.)\1+", r"\1", word), known) or LAUGH.match(squeezed)):
            continue
        if LAUGH.match(word) or not re.search(r"[aeiouy]", word):
            continue       # a laugh, or letters that aren't a word ("hmm", "brb", "pls")
        if _slip(word, known):
            continue
        out.append(word)
    return out[:2]          # more than two in one sentence is another language or a keyboard, not a word of theirs


def _state(agent):
    return dict(agent.store.setting(KEY) or {})


def _day(agent):
    return datetime.fromtimestamp(agent.clock(), agent.zone).date().isoformat()


def notice(agent, text):
    """Keep any new word with the sentence it came in, and return the line that tells the brain. None when there's
    nothing of theirs in play. The caller decides when not to ask (hurting, kids mode, a safety turn)."""
    state = _state(agent)
    sentence = " ".join(str(text).split())[:200]
    # asked twice in one turn (a retry), the word is still new this turn
    just = [w for w, e in state.items() if e.get("in") == sentence and agent.clock() - (e.get("at") or 0) < 120]
    fresh = new_words(text, theirs=[w for w in state if w not in just])
    for word in fresh:
        state[word] = {"in": sentence, "at": agent.clock(), "said": None}
    if fresh:
        state = dict(sorted(state.items(), key=lambda kv: kv[1].get("at") or 0)[-KEEP:])
        agent.store.set_setting(KEY, state)
    today = _day(agent)
    used_now = [w for w in state if w not in fresh and re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", str(text).lower())]
    lines = []
    for word in fresh:
        lines.append(f"They just used a word that's new to you: “{word}”. If you know it as an ordinary word, ignore this note. If it's their own word, work out "
                     "what they mean from how they used it and go with it: don't ask what it means unless you truly can't tell, and don't make a thing of it. "
                     "You can use it back once, the way they did.")
    for word in used_now[:3]:
        entry = state[word]
        again = "You've already said it back today, so leave it to them now." if entry.get("said") == today else "You can use it back once today, the way they do."
        lines.append(f"“{word}” is a word of theirs. They first said it like this: “{entry.get('in', '')}”. {again}")
    return " ".join(lines) or None


def said_back(agent, reply):
    """After a reply: any of their words Luma used is marked for today, so it isn't worn out."""
    state = _state(agent)
    low, today, changed = str(reply or "").lower(), _day(agent), False
    for word, entry in state.items():
        if entry.get("said") != today and re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", low):
            entry["said"], changed = today, True
    if changed:
        agent.store.set_setting(KEY, state)
    return changed


def view(agent):
    return [{"word": w, "in": e.get("in") or "", "at": e.get("at")} for w, e in sorted(_state(agent).items(), key=lambda kv: -(kv[1].get("at") or 0))]


def forget(agent, word):
    state = _state(agent)
    if state.pop(str(word).lower(), None) is not None:
        agent.store.set_setting(KEY, state)
    return view(agent)
