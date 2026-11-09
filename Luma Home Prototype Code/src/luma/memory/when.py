"""When a question is about a time: "last spring", "in May 2024", "two years ago", "yesterday".

window() turns the words into a span of real time, so Luma looks at what was said then and not at something from
another year that happens to share a word. No model: a few plain patterns, read in the owner's own time zone."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
_MONTH = r"(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
SEASONS = {"spring": 3, "summer": 6, "fall": 9, "autumn": 9, "winter": 12}   # the month each one starts
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
NUMBERS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
           "couple": 2, "few": 3}
UNITS = {"day": 1, "week": 7, "month": 30.44, "year": 365.25}

MONTH_YEAR = re.compile(rf"\b{_MONTH}\.?,?\s+(?:of\s+)?(?P<year>(?:19|20)\d\d)\b", re.I)
YEAR = re.compile(r"\b(?:in|during|back in|from|of)\s+(?P<year>(?:19|20)\d\d)\b", re.I)
SEASON = re.compile(r"\b(?P<which>last|this(?: past)?|over the|in the|during the)\s+(?P<season>spring|summer|fall|autumn|winter)\b", re.I)
LAST_MONTH_NAME = re.compile(rf"\b(?:last|in|this past|back in)\s+{_MONTH}\b(?!\s+\d)", re.I)
AGO = re.compile(r"\b(?P<n>\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|a couple(?: of)?|a few)\s+(?P<unit>day|week|month|year)s?\s+ago\b", re.I)
RELATIVE = re.compile(r"\b(?P<which>last|this past|this|earlier this|over the)\s+(?P<unit>year|month|week|weekend)\b", re.I)
SIMPLE = re.compile(r"\b(?P<word>yesterday|today|tonight|last night|this morning|the other day|recently|lately)\b", re.I)
WEEKDAY = re.compile(r"\b(?:last|on|this past)\s+(?P<day>monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
BEFORE = re.compile(r"\b(?:used to|before|previously|formerly|back then|at the time|old (?:job|place|apartment|house)|did i use to)\b", re.I)


def _month_number(word):
    return next(i + 1 for i, m in enumerate(MONTHS) if m.startswith(word.lower().rstrip(".")[:3]))


def _month_span(year, month, months=1, zone=timezone.utc):
    start = datetime(year, month, 1, tzinfo=zone)
    end_month = month - 1 + months
    end = datetime(year + end_month // 12, end_month % 12 + 1, 1, tzinfo=zone)
    return start, end


def window(text, now=None, zone=timezone.utc):
    """(start, end, the words that said it) as timestamps, or None when the question isn't about a time."""
    text = str(text or "")
    today = datetime.fromtimestamp(now, zone) if now is not None else datetime.now(zone)
    span = None
    found = MONTH_YEAR.search(text)
    if found:
        span = _month_span(int(found["year"]), _month_number(found["month"]), zone=zone)
    if span is None:
        found = SEASON.search(text)
        if found:
            first = SEASONS[found["season"].lower()]
            year = today.year - (1 if first == 12 and today.month < 3 else 0)  # in January, "this winter" began in December
            start, end = _month_span(year, first, 3, zone)
            which = found["which"].lower()
            if which == "last" and end > today:        # still in it: the one before
                start, end = _month_span(year - 1, first, 3, zone)
            elif which != "last" and not which.startswith("this") and start > today:  # "in the spring", said in January
                start, end = _month_span(year - 1, first, 3, zone)
            span = (start, end)
    if span is None:
        found = YEAR.search(text)
        if found:
            year = int(found["year"])
            span = (datetime(year, 1, 1, tzinfo=zone), datetime(year + 1, 1, 1, tzinfo=zone))
    if span is None:
        found = AGO.search(text)
        if found:
            raw = found["n"].lower()
            count = int(raw) if raw.isdigit() else next(NUMBERS[w] for w in reversed(raw.split()) if w in NUMBERS)
            days = UNITS[found["unit"].lower()]
            middle = today - timedelta(days=count * days)
            slack = timedelta(days=max(1, days / 2))
            span = (middle - slack, middle + slack)
    if span is None:
        found = RELATIVE.search(text)
        if found:
            unit, last = found["unit"].lower(), found["which"].lower() in ("last", "this past", "over the")
            if unit == "year":
                year = today.year - (1 if last else 0)
                span = (datetime(year, 1, 1, tzinfo=zone), datetime(year + 1, 1, 1, tzinfo=zone))
            elif unit == "month":
                year, month = (today.year, today.month - 1) if last else (today.year, today.month)
                if month == 0:
                    year, month = year - 1, 12
                span = _month_span(year, month, zone=zone)
            else:
                monday = (today - timedelta(days=today.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
                if unit == "weekend":
                    saturday = monday - timedelta(days=2) if last or today.weekday() < 5 else monday + timedelta(days=5)
                    span = (saturday, saturday + timedelta(days=2))
                else:
                    start = monday - timedelta(days=7) if last else monday
                    span = (start, start + timedelta(days=7))
    if span is None:
        found = LAST_MONTH_NAME.search(text)
        if found:
            month = _month_number(found["month"])
            year = today.year if month < today.month else today.year - 1  # the last one that's over
            span = _month_span(year, month, zone=zone)
    if span is None:
        found = WEEKDAY.search(text)
        if found:
            back = (today.weekday() - DAYS.index(found["day"].lower())) % 7 or 7
            start = (today - timedelta(days=back)).replace(hour=0, minute=0, second=0, microsecond=0)
            span = (start, start + timedelta(days=1))
    if span is None:
        found = SIMPLE.search(text)
        if found:
            word = found["word"].lower()
            midnight = today.replace(hour=0, minute=0, second=0, microsecond=0)
            if word in ("today", "tonight", "this morning"):
                span = (midnight, midnight + timedelta(days=1))
            elif word in ("yesterday", "last night"):
                span = (midnight - timedelta(days=1), midnight + (timedelta(hours=6) if word == "last night" else timedelta(0)))
            else:
                span = (today - timedelta(days=14 if word == "the other day" else 45), today + timedelta(seconds=1))
    if span is None:
        return None
    return span[0].timestamp(), span[1].timestamp(), found.group(0)


def about_the_past(text):
    """ "where did i live before", "my old job": the answer is what used to be true, not what's true now."""
    return bool(BEFORE.search(str(text or "")))
