"""Sums are worked out with a calculator, not by the brain.

"What's 18% of 240", "a 20% tip on $64.50", "split 126 between 4", "what's 47 times 12": find() recognizes the few plain
shapes people ask out loud and works them out exactly, in decimal, with no eval. The brain is told the result as a note
for the turn (note), and a reply that doesn't carry the calculator's number is put right (holds, line).

It only fires when the message really is a sum. "I work 9-5", "it's open 24/7", "we lost 3-2" and a phone number aren't."""
from __future__ import annotations

import re
from decimal import Decimal, DivisionByZero, InvalidOperation

UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
         "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_NAMED = {**{word: i for i, word in enumerate(UNITS)}, **{word: i * 10 for i, word in enumerate(TENS) if word}}
_WORD = "|".join(sorted(_NAMED, key=len, reverse=True))
# a run of number words: "nine", "twenty five", "two hundred", "a hundred and fifty", "three thousand"
SPOKEN = re.compile(rf"\b(?:(?:a|{_WORD})\s+(?:hundred|thousand)|{_WORD})(?:(?:\s+and)?[\s-]+(?:{_WORD}|hundred|thousand))*\b")
NUM = r"\$?\d[\d,]*(?:\.\d+)?"
A = r"(?:(?:a|an|the|my|our|that)\s+)?"
TIP = re.compile(rf"({NUM})\s*(?:%|percent)\s+tip\s+(?:on|for)\s+{A}(?:[a-z]+\s+){{0,3}}?(?:of\s+)?({NUM})")
OFF = re.compile(rf"({NUM})\s*(?:%|percent)\s+off\s+(?:of\s+)?{A}({NUM})")
OFF_AFTER = re.compile(rf"({NUM})\s+(?:[a-z]+\s+){{0,2}}?(?:with|at|after)\s+({NUM})\s*(?:%|percent)\s+off")
OF = re.compile(rf"({NUM})\s*(?:%|percent)\s+of\s+({NUM})")
SPLIT = re.compile(rf"split\s+({NUM})\s+(?:(?:evenly|equally)\s+)?(?:(?:between|among|amongst|by|across|with)\s+({NUM})\b|({NUM})\s+ways)|"
                   rf"({NUM})\s+(?:split|divided)\s+(?:(?:evenly|equally)\s+)?(?:between|among|amongst|across)\s+({NUM})\b")
EXPR = rf"{NUM}(?:\s*[+*]\s*{NUM}|\s+[-/]\s+{NUM})+"
ASKED = re.compile(rf"(?:\bwhat'?s|\bwhat is|\bhow much is|\bcalculate|\bcompute|\bwork out|\bsolve|\badd up)\s+(?:the\s+)?(?:answer to\s+|sum of\s+|total of\s+)?({EXPR})(?![\d/-])")
ALONE = re.compile(rf"^\W*({EXPR})\W*$")
SPOKEN_OPS = [(r"\s+multiplied\s+by\s+", " * "), (r"\s+divided\s+by\s+", " / "), (r"\s+plus\s+", " + "), (r"\s+minus\s+", " - "), (r"\s+times\s+", " * "),
              (r"\s+[x×]\s+", " * "), (r"\s*÷\s*", " / ")]
SAID_OPS = {"+": "plus", "-": "minus", "*": "times", "/": "divided by"}


def _spoken(match):
    total = part = 0
    for word in re.split(r"[\s-]+", match.group(0)):
        if word in ("and", "a"):
            part = part or (1 if word == "a" else 0)
        elif word == "hundred":
            part = (part or 1) * 100
        elif word == "thousand":
            total, part = total + (part or 1) * 1000, 0
        else:
            part += _NAMED[word]
    return str(total + part)


def _plain(text):
    """Lowercased, with numbers said in words written as digits and operators said in words written as signs."""
    text = SPOKEN.sub(_spoken, " ".join(str(text or "").lower().split()))
    for said, sign in SPOKEN_OPS:
        text = re.sub(rf"(?<=\d){said}(?=\$?\d)", sign, text)
    return text


def _n(text):
    return Decimal(text.replace("$", "").replace(",", ""))


def _work(expr):
    """A chain of numbers and + - * /, with * and / first. None if it can't be worked out (a division by zero)."""
    parts = re.findall(rf"{NUM}|[+*/-]", expr)
    numbers, signs = [_n(p) for p in parts[0::2]], parts[1::2]
    terms, pending = [numbers[0]], []
    try:
        for sign, number in zip(signs, numbers[1:]):
            if sign == "*":
                terms[-1] *= number
            elif sign == "/":
                terms[-1] /= number
            else:
                pending.append(sign)
                terms.append(number)
    except (DivisionByZero, InvalidOperation, ZeroDivisionError):
        return None
    total = terms[0]
    for sign, term in zip(pending, terms[1:]):
        total = total + term if sign == "+" else total - term
    return total


def _show(value, money):
    """(the number as it's said, whether it had to be rounded)."""
    if money:
        cents = value.quantize(Decimal("0.01"))
        return f"${cents:,.2f}", cents != value
    exact = value.quantize(Decimal("0.0001"))
    rounded = exact != value
    shown = value.quantize(Decimal("0.01")) if rounded else exact
    text = f"{shown:,f}"
    return (text.rstrip("0").rstrip(".") if "." in text else text), rounded


def find(text):
    """The sum in a message, worked out: {"ask", "say", "also", "about", "value"}, or None when it isn't a sum."""
    plain = _plain(text)
    try:
        found = TIP.search(plain)
        if found:
            share, bill = _n(found[1]), _n(found[2])
            tip = bill * share / 100
            say, about = _show(tip, True)
            return {"kind": "tip", "ask": f"a {found[1].rstrip('%')}% tip on {_show(bill, True)[0]}", "say": say, "also": _show(bill + tip, True)[0], "about": about, "value": tip}
        found = OFF.search(plain) or OFF_AFTER.search(plain)
        if found:
            share, price = (_n(found[1]), _n(found[2])) if found.re is OFF else (_n(found[2]), _n(found[1]))
            if not 0 < share <= 100:
                return None
            left = price * (100 - share) / 100
            say, about = _show(left, True)
            return {"kind": "off", "ask": f"{_show(share, False)[0]}% off {_show(price, True)[0]}", "say": say, "also": None, "about": about, "value": left}
        found = OF.search(plain)
        if found:
            money = "$" in found[2]
            value = _n(found[2]) * _n(found[1]) / 100
            say, about = _show(value, money)
            return {"kind": "of", "ask": f"{found[1]}% of {found[2]}", "say": say, "also": None, "about": about, "value": value}
        found = SPLIT.search(plain)
        if found:
            whole, ways = (found[1], found[2] or found[3]) if found[1] else (found[4], found[5])
            people = _n(ways)
            if people != people.to_integral_value() or not 2 <= people <= 1000:
                return None
            value = _n(whole) / people
            say, about = _show(value, "$" in whole)
            return {"kind": "split", "ask": f"{whole} split {int(people)} ways", "say": say, "also": None, "about": about, "value": value}
        found = ASKED.search(plain) or ALONE.match(plain)
        if found:
            value = _work(found[1])
            if value is None:
                return None
            say, about = _show(value, "$" in found[1])
            ask = re.sub(r"\s*([+*/-])\s*", lambda sign: f" {SAID_OPS[sign[1]]} ", found[1]) if not re.search(r"\d-\d", found[1]) else found[1]
            return {"kind": "sum", "ask": ask, "say": say, "also": None, "about": about, "value": value}
    except (InvalidOperation, ArithmeticError):
        return None
    return None


def line(found):
    """The sum and its answer as one plain sentence: what Luma says when the brain's reply doesn't carry the number."""
    about = "about " if found["about"] else ""
    if found["kind"] == "tip":
        return f"{found['ask'][0].upper()}{found['ask'][1:]} is {about}{found['say']}, which makes {found['also']} in all."
    if found["kind"] == "off":
        return f"{found['ask']} comes to {about}{found['say']}."
    if found["kind"] == "split":
        return f"{found['ask']} is {about}{found['say']} each."
    return f"{found['ask']} is {about}{found['say']}."


def note(found):
    """What the brain is told for the turn."""
    return "Worked out with a calculator, so say this number exactly and don't work it out again: " + line(found)


def holds(reply, found):
    """The reply says the calculator's number, however it's written ($90, 90 dollars, $90.00, 15,000)."""
    want = found["value"].quantize(Decimal("0.01"))
    slack = Decimal("0.01") if found["about"] else Decimal("0")
    for said in re.findall(NUM, str(reply or "")):
        try:
            if abs(_n(said).quantize(Decimal("0.01")) - want) <= slack:
                return True
        except InvalidOperation:
            continue
    return False
