"""Small slips a small brain makes, fixed before anyone sees them: "the the", "a apple", "an car", "word ,", ",,".

Only the safe ones. Anything that could be on purpose stays: "no no no", "had had", "so so", lowercase replies to
someone who types in lowercase, "!!" and "??", "wait.. what", ellipses, emoji, links and code.
"""
from __future__ import annotations

import re

# Doubled words that are almost always a slip (not "had had", "that that", "no no", "very very").
DOUBLED = re.compile(r"\b(the|a|an|to|of|in|on|at|is|it|and|for|with|you|your|my|i|be|was|are|we|they|this|from|but|or|if|as|by)\s+\1\b", re.I)
# "a" before a vowel sound, "an" before a consonant. Words that start with a vowel letter but a consonant sound (and the reverse) are left alone.
A_BEFORE_VOWEL = re.compile(r"\b([Aa]) (?!(?:one|once|uni\w*|use\w*|usu\w*|ute\w*|uto\w*|uro\w*|eu\w*|ewe\w*|uk\w*|ufo\w*|ouija)\b)([aeio]\w*|u(?!ni|s|t|r|k|f|b|ph)\w*)")
AN_BEFORE_CONSONANT = re.compile(r"\b([Aa])n (?!(?:h(?:our|onest|onor|onour|eir|erb)\w*)\b)([b-df-hj-np-tv-z][a-z]\w*)")
A_BEFORE_SILENT_H = re.compile(r"\b([Aa]) (h(?:our|onest|onor|onour|eir)\w*)\b")
SPACE_BEFORE = re.compile(r"(?<=\w) +([,.;:!?])(?=\s|$)")
DOUBLE_COMMA = re.compile(r",\s*,")
SPACES = re.compile(r"(?<=\S) {2,}(?=\S)")


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
