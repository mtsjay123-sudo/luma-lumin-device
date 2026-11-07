"""How Luma says this reply: it meets you where you are.

In a good conversation people fall into each other's pace and energy (linguists call it accommodation, and it's a big
part of why a friend sounds like they're with you). So Luma hears how you said it and says its reply to match: gentler,
a little slower and with longer pauses when you're hurting; lighter and a touch quicker when you're laughing; steady
when you want something done. Only the delivery changes, never the words. It lasts for the reply to what you just said,
then Luma goes back to its usual way of talking, so a reminder an hour later isn't said in a sad voice.

Setting "match_mood": on unless it's set to False.
"""
from __future__ import annotations

import threading
import time

# mood (from luma.agent.humor.read_tone): pace (times the voice's speed), pauses (times each pause between phrases)
FEELS = {
    "grief": {"pace": 0.90, "pauses": 1.35},
    "upset": {"pace": 0.93, "pauses": 1.25},
    "venting": {"pace": 0.96, "pauses": 1.15},
    "serious": {"pace": 0.97, "pauses": 1.10},
    "neutral": {"pace": 1.00, "pauses": 1.00},
    "task": {"pace": 1.02, "pauses": 0.95},
    "playful": {"pace": 1.03, "pauses": 0.92},
    "laughing": {"pace": 1.05, "pauses": 0.85},
}
LASTS = 120.0  # seconds: long enough for the whole reply, short enough that the next thing Luma brings up is said normally

_lock = threading.Lock()
_state = {"mood": "neutral", "at": 0.0}


def set_mood(mood, now=None):
    with _lock:
        _state.update(mood=mood if mood in FEELS else "neutral", at=time.monotonic() if now is None else now)


def set_from(said, now=None):
    """Read how they said it and get ready to answer in kind. Returns the mood."""
    from luma.agent import humor
    mood = humor.read_tone(said or "").get("mood", "neutral")
    set_mood(mood, now)
    return mood if mood in FEELS else "neutral"


def reset():
    set_mood("neutral", 0.0)


def mood(now=None):
    with _lock:
        current, at = _state["mood"], _state["at"]
    now = time.monotonic() if now is None else now
    return current if now - at <= LASTS else "neutral"


def pace(speed, now=None):
    """The voice's speed for this reply, kept in the range the voice can do."""
    return min(1.5, max(0.5, float(speed) * FEELS[mood(now)]["pace"]))


def pause(ms, now=None):
    """A pause between phrases, longer when they're hurting and shorter when it's all jokes."""
    return int(round(max(0, ms) * FEELS[mood(now)]["pauses"]))
