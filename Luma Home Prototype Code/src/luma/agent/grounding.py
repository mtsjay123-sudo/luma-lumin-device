"""Every number Luma says about something it looked up has to be in what it found.

A brain that reads "Nike Air Max, $129.99" and says "$119" has made something up, however sure it sounds. This is a
plain check, not another opinion from the same brain: after Luma answers from a look-up (the web, news, prices,
weather, the inbox, a connected app), each specific figure in the answer (prices, percentages, scores, temperatures,
times, years, amounts) must appear in what was found or in what the owner said. A figure that's a simple sum or
difference of two found numbers counts ("15 degrees warmer"), so does a count of the things found, and so does
rounding ("about $130" for $129.99).

What happens to one that doesn't: Luma tries once more, told exactly which number wasn't there; if it still
can't back it up, that sentence comes out, and if nothing's left Luma says it couldn't pin the number down.
Single digits ("2 options", "1 thing") are left alone: they're how people talk, not facts.
"""
from __future__ import annotations

import json
import re

# A figure: money, a percent, a score, a temperature, a clock time, or any number with two or more digits (or a decimal).
FIGURE = re.compile(
    r"(?P<money>[$€£¥]\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:k|m|bn|million|billion|thousand))?)"
    r"|(?P<score>\b\d{1,3}\s?[-–]\s?\d{1,3}\b)(?!\s?(?:year|yr|month|day|week|hour|min|minute|second|ft|foot|feet|inch|lb|kg)s?\b)"
    r"|(?P<time>\b\d{1,2}:\d{2}(?:\s?[ap]\.?m\.?)?|\b\d{1,2}\s?[ap]\.?m\.?\b)"
    r"|(?P<num>(?<![\w.])\d[\d,]*(?:\.\d+)?(?:\s?(?:%|percent|°|degrees|k\b|m\b|million|billion|thousand))?)",
    re.I)
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
SEASON = re.compile(r"\b(\d{4})[-–/](\d{2})\b")  # "the 2025-26 season": one year, said the sports way
SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "bn": 1e9, "billion": 1e9}
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“])")


def _value(token):
    """'$1,299.50' -> 1299.5, '12%' -> 12, '3.2 million' -> 3200000."""
    m = NUMBER.search(token)
    if not m:
        return None
    try:
        v = float(m.group(0).replace(",", ""))
    except ValueError:
        return None
    unit = re.search(r"(k|m|bn|million|billion|thousand)\s*$", token.strip(), re.I)
    return v * SCALE[unit.group(1).lower()] if unit else v


def figures(text):
    """The specific figures in a reply: [(as written, kind, value or (a, b) for a score / (h, m) for a time)]."""
    out = []
    text = SEASON.sub(lambda m: m.group(1), str(text or ""))
    for m in FIGURE.finditer(text):
        token = m.group(0).strip()
        if m.group("money"):
            out.append((token, "money", _value(token)))
        elif m.group("score"):
            a, b = re.split(r"\s?[-–]\s?", token)
            out.append((token, "score", (int(a), int(b))))
        elif m.group("time"):
            token = token.rstrip(".") if re.search(r"m\.$", token, re.I) and not re.search(r"\.m\.$", token, re.I) else token
            t = re.match(r"(\d{1,2})(?::(\d{2}))?\s?([ap])?", token, re.I)
            hour, minute, half = int(t.group(1)), int(t.group(2) or 0), (t.group(3) or "").lower()
            out.append((token, "time", (hour % 12 + (12 if half == "p" else 0) if half else hour, minute)))
        else:
            v = _value(token)
            digits = re.sub(r"\D", "", NUMBER.search(token).group(0)) if NUMBER.search(token) else ""
            plain = not re.search(r"[%°]|percent|degrees|million|billion|thousand|\bk\b|\bm\b", token, re.I)
            if v is None or (plain and len(digits) < 2 and "." not in token):
                continue  # "2 options", "1 thing": how people talk, not facts
            out.append((token, "number", v))
    return out


def _numbers_in(text):
    vals = set()
    for m in FIGURE.finditer(text):
        token = m.group(0)
        if m.group("score"):
            for part in re.split(r"\s?[-–]\s?", token.strip()):
                vals.add(float(part))
        elif m.group("time"):
            t = re.match(r"(\d{1,2})(?::(\d{2}))?", token.strip())
            vals.update({float(t.group(1)), float(t.group(2) or 0)})
        else:
            v = _value(token)
            if v is not None:
                vals.add(v)
    for m in NUMBER.finditer(text):
        try: vals.add(float(m.group(0).replace(",", "")))
        except ValueError: pass
    return vals


def _counts(result):
    """How many of each thing was found: '12 emails' is backed by a list of 12."""
    out = set()
    def walk(x, depth=0):
        if depth > 4: return
        if isinstance(x, list):
            out.add(float(len(x)))
            for item in x[:50]: walk(item, depth + 1)
        elif isinstance(x, dict):
            for item in x.values(): walk(item, depth + 1)
    walk(result)
    return out


def _close(v, pool):
    """The same number, or the same one rounded the way people round ("$130" for $129.99, "1.3 million" for 1,284,000).
    Whole numbers under ten thousand have to match exactly: 2019 is not 2025, and 6-3 is not 5-3."""
    for p in pool:
        if abs(v - p) < 1e-9:
            return True
        if p != int(p) or v != int(v):
            if abs(v - p) <= max(0.01, abs(p) * 0.005) or abs(round(p, 1) - v) < 1e-9 or (abs(p) >= 10 and v == round(p)):
                return True
        if abs(p) >= 1e4 and abs(v - p) <= abs(p) * 0.05:
            return True
    return False


def _kind(fig):
    token, kind, _ = fig
    if kind == "money": return "money"
    if re.search(r"%|percent", token, re.I): return "percent"
    return "plain"


def backed(fig, pool, scores, times, math=None):
    token, kind, value = fig
    if kind == "score":
        return value in scores or (value[1], value[0]) in scores
    if kind == "time":
        hour, minute = value
        return (hour, minute) in times or (hour % 12, minute) in {(h % 12, m) for h, m in times}
    if value is None:
        return True
    if _close(value, pool):
        return True
    # Simple math on two found figures of the same kind (10 or more), like "$20 cheaper" (two prices) or "15 degrees warmer"
    # (two temperatures). Single digits are left out, and a price never backs a percent, so a stray number can't back anything.
    big = sorted({p for p in (math or {}).get(_kind(fig), set()) if 10 <= abs(p) < 1e7})[:40]
    return any(_close(value, {a + b, abs(a - b)}) for i, a in enumerate(big) for b in big[i + 1:])


def _scores_times(text):
    scores, times = set(), set()
    for fig in figures(text):
        if fig[1] == "score": scores.add(fig[2])
        if fig[1] == "time": times.add(fig[2])
    return scores, times


def unbacked(reply, evidence, said="", result=None, extra=()):
    """The figures in the reply that aren't in the evidence (what was found), what the owner said, or simple math on those."""
    source = (evidence if isinstance(evidence, str) else json.dumps(evidence, ensure_ascii=False, default=str)) + "\n" + str(said or "")
    pool = _numbers_in(source) | _counts(result if result is not None else evidence) | {float(x) for x in extra}
    scores, times = _scores_times(source)
    math = {}
    for fig in figures(source):
        if fig[1] in ("money", "number") and fig[2] is not None:
            math.setdefault(_kind(fig), set()).add(fig[2])
    return [fig[0] for fig in figures(reply) if not backed(fig, pool, scores, times, math)]


def without(reply, figures_out):
    """The reply minus every sentence that carries one of these figures."""
    parts = SENTENCE.split(str(reply or "").strip())
    keep = [p for p in parts if not any(f in p for f in figures_out)]
    return " ".join(keep).strip()


def retry_note(figs):
    shown = ", ".join(f"“{f}”" for f in figs[:5])
    return (f"\n\nYour last answer said {shown}, but that isn't in what was found. Answer again using only numbers that appear in "
            "what was found (rounding is fine). If the number they want isn't there, say you couldn't find it instead of guessing.")
