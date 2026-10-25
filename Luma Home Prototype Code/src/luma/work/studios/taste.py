"""Taste: the copy and design rules every Luma-made page, deck and document is held to.

Distilled from the anti-slop design skills (antislop, tasteskill, Hallmark; all MIT) into Luma's own
checks: words that sound generated, buttons that don't say what they do, numbers and quotes nobody
can stand behind, and the visual habits that make a page look like every other generated page.
"""
from __future__ import annotations

import re

BUZZWORDS = ("seamless", "seamlessly", "revolutionary", "revolutionize", "cutting-edge", "cutting edge", "next-gen", "next generation", "next-generation",
             "game-changer", "game changer", "game-changing", "unlock", "unleash", "supercharge", "elevate", "effortless", "effortlessly", "ultimate",
             "world-class", "best-in-class", "state-of-the-art", "synergy", "leverage", "empower", "empowering", "transformative", "ai-powered",
             "ai powered", "all-in-one", "one-stop shop", "take it to the next level", "in today's fast-paced", "look no further", "delve")
GENERIC_CTAS = ("get started", "learn more", "try now", "explore", "discover", "click here", "read more", "find out more", "submit", "start now")
FAKE_NUMBER = re.compile(r"\b\d[\d,.]*\s*(?:k|m|b)?\+|\b\d{2,3}(?:\.\d+)?\s*%|\b(?:\d+(?:\.\d+)?)\s*(?:x|×)\s+(?:faster|better|more)", re.I)


def fix_dashes(text):
    """Em dashes read as generated: a comma or colon does the same job."""
    text = re.sub(r"\s*—\s*", ", ", str(text or ""))
    return re.sub(r"\s+–\s+", ", ", text)


def buzzwords(text):
    low = " " + str(text or "").lower() + " "
    return sorted({w for w in BUZZWORDS if re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", low)})


def generic_cta(label):
    return str(label or "").strip().lower().rstrip("!.→ ") in GENERIC_CTAS


def numbers_in(text):
    return {re.sub(r"[^\d.]", "", n) for n in re.findall(r"\d[\d,.]*", str(text or "")) if re.sub(r"[^\d.]", "", n)}


def sourced(claim, sources):
    """A number on the page counts only if it appears in the research, the model or what the owner said."""
    wanted = numbers_in(claim)
    return bool(wanted) and wanted <= numbers_in(sources)


def words(text):
    return len(re.findall(r"[\w'’-]+", str(text or "")))
