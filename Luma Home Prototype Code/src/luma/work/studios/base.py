"""What every studio shares: the shape of a result, quality checks, and small helpers."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field


@dataclass
class Result:
    files: list = field(default_factory=list)      # project-relative paths this step made
    summary: str = ""                              # one or two sentences for the owner and for later steps
    data: dict = field(default_factory=dict)       # what later steps can build on (findings, numbers, colors)
    checks: list = field(default_factory=list)     # [{"check", "ok", "detail"}] filled in by the studio's check()

    def passed(self):
        return all(c["ok"] for c in self.checks if c.get("blocking", True))

    def failures(self):
        return [c for c in self.checks if not c["ok"] and c.get("blocking", True)]


def check(name, ok, detail="", blocking=True):
    return {"check": name, "ok": bool(ok), "detail": str(detail)[:300], "blocking": blocking}


class Studio:
    name = ""            # the plan's tool name
    agent = ""           # which specialist runs it
    title = ""           # for people
    description = ""     # for the brain: what to fill in, and how
    fields = {}          # the structured output the brain returns
    tier = "heavy"       # how strong a brain the step deserves

    def make(self, ctx, args):
        raise NotImplementedError

    def check(self, ctx, result):
        return []

    def fallback(self, ctx, task):
        """Arguments to use when no brain answered (None: this studio needs one)."""
        return None


def text(value, limit=2000):
    return " ".join(str(value or "").split())[:limit]


def esc(value):
    return html.escape(str(value or ""), quote=True)


def slug(value, fallback="item"):
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")[:48] or fallback


def hex_color(value, fallback):
    value = str(value or "").strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{3}", value):
        value = "".join(ch * 2 for ch in value)
    named = {"red": "E5484D", "orange": "F76B15", "yellow": "FFC53D", "green": "30A46C", "teal": "12A594", "blue": "0090FF", "navy": "1E3A8A",
             "purple": "8E4EC6", "violet": "6E56CF", "pink": "D6409F", "black": "111111", "white": "FFFFFF", "gold": "C9A227", "gray": "8B8D98"}
    value = named.get(value.lower(), value)
    return "#" + value.upper() if re.fullmatch(r"[0-9a-fA-F]{6}", value) else fallback


def luminance(color):
    channels = [int(color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    """WCAG contrast ratio between two colors (4.5 or more reads well for body text)."""
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable_on(background, light="#FFFFFF", dark="#111111"):
    return light if contrast(background, light) >= contrast(background, dark) else dark


def shade(color, amount):
    """Darken (negative) or lighten (positive) a color by `amount` (0..1)."""
    rgb = [int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    target = 255 if amount > 0 else 0
    return "#" + "".join(f"{round(c + (target - c) * abs(amount)):02X}" for c in rgb)
