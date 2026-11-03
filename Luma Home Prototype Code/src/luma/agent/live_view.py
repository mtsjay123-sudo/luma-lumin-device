"""Live view: Luma sees through the owner's camera, right now.

While the camera is on (Luma Desktop, or the Luma app on the phone), the app sends a small still picture with each
thing the owner says, and, when they asked Luma to watch for something, one every couple of seconds. Luma answers
about what's in front of the camera with the same eyes it uses for photos (its own vision model, on this computer;
Claude only if the owner turned the cloud brain on), and remembers the last half minute so "what about now?" works.

Pictures live in memory only, for a short while, and are gone the moment the camera stops. Nothing is saved unless
the owner asks. Kids mode keeps it closed. Luma never says who a stranger is.
"""
from __future__ import annotations

import re
import threading
import time
from collections import deque

KEEP_SECONDS = 30       # how long a picture is remembered
KEEP_FRAMES = 12        # and at most this many
FRESH_SECONDS = 10      # a picture this recent is "what's in front of the camera now"
MAX_FRAME_BYTES = 600_000
_JPEG = b"\xff\xd8\xff"

# A question about what the camera sees ("what's this?", "how does this look", "read that", "which one is ripe").
LOOKING = re.compile(r"\b(?:what(?:'s| is| are)? (?:this|that|these|those|it|here|in front)|what am i (?:looking at|holding|wearing|doing)|"
                     r"(?:what do|can) (?:you|u) see|do (?:you|u) see|look(?:ing)? at|see (?:this|that|it|my|the)|show(?:ing)? (?:you|u)|"
                     r"how (?:does|do) (?:this|that|these|it|i|my) look|which (?:one|of these)|is (?:this|that|it) (?:ok|okay|right|good|ripe|done|broken|safe)|"
                     r"read (?:this|that|it|the)|what does (?:this|that|it) say|identify|recogni[sz]e (?:this|that)|"
                     r"(?:this|that) (?:plant|thing|bug|mushroom|rash|stain|part|cable|plug|dish|bottle|label|sign|screen|error|outfit)|"
                     r"(?:wrong|going on|up|the matter) with (?:this|that|it|these|those|my)\b|\b(?:this|that|these|those|here)\s*[?!.]*\s*$|"
                     r"(?:now|again)\?*$|what about now|what changed|anything (?:there|here|wrong))", re.I)
# "tell me when the pasta boils over", "let me know if someone's at the door", "watch the oven", "keep an eye on the baby"
WATCH = re.compile(r"^\s*(?:hey luma,?\s*)?(?:(?:can you |could you |please )?(?:tell|let) me (?:know )?(?:when|if|once|as soon as)\s+(?P<when>.+?)|"
                   r"(?:can you |could you |please )?(?:watch|keep an eye on|keep watching|monitor)\s+(?P<what>.+?))\s*[.!?]*\s*$", re.I)
STOP_WATCH = re.compile(r"\b(?:stop watching|you can stop|never mind|nvm|forget it|that's fine now|stop looking)\b", re.I)


def is_jpeg(data):
    return isinstance(data, (bytes, bytearray)) and bytes(data[:3]) == _JPEG


class LiveView:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.frames = deque()
        self.last_said = None           # (at, what Luma said it saw)
        self.watch = None               # {"for": condition, "since": at, "yes": consecutive yeses, "checks": n}
        self.checking = threading.Lock()  # one look at a time; frames that arrive meanwhile only update "now"
        self.started = None

    # -- the pictures -------------------------------------------------------------
    def add(self, frame):
        if not is_jpeg(frame):
            raise ValueError("Send the camera picture as a JPEG.")
        if len(frame) > MAX_FRAME_BYTES:
            raise ValueError("That camera picture is too big. Send a smaller one.")
        now = self.clock()
        self.started = self.started or now
        self.frames.append((now, bytes(frame)))
        self._trim(now)

    def _trim(self, now):
        while self.frames and (now - self.frames[0][0] > KEEP_SECONDS or len(self.frames) > KEEP_FRAMES):
            self.frames.popleft()

    def latest(self, max_age=FRESH_SECONDS):
        self._trim(self.clock())
        if not self.frames:
            return None
        at, frame = self.frames[-1]
        return frame if self.clock() - at <= max_age else None

    def on(self):
        return self.latest() is not None

    def stop(self):
        self.frames.clear()
        self.last_said = None
        self.watch = None
        self.started = None

    def recently_said(self):
        if self.last_said and self.clock() - self.last_said[0] <= KEEP_SECONDS:
            return self.last_said[1]
        return None

    def remember(self, said):
        self.last_said = (self.clock(), said)

    # -- watching for something -------------------------------------------------------
    @staticmethod
    def watch_request(text):
        """What to watch for, or None: {"for": the condition to check, "say": how Luma says it back}.
        "tell me when the pasta boils over" -> the pasta boils over; "watch the oven" -> anything's not right with the oven."""
        m = WATCH.match(str(text or ""))
        if not m:
            return None
        if m.group("when"):
            when = m.group("when").strip(" ,.")[:200]
            return {"for": when, "say": when}
        what = re.sub(r"\s+for me$", "", m.group("what").strip(" ,."), flags=re.I)[:120]
        return {"for": f"{what} needs attention (something boiling over, smoke, a spill, someone there, anything not right)",
                "say": f"anything's not right with {what}"}

    def start_watch(self, wanted):
        self.watch = {"for": wanted["for"], "say": wanted["say"], "since": self.clock(), "yes": 0, "checks": 0}

    @staticmethod
    def question_for(condition):
        return ("This is a live picture from my camera, right now. Answer with one word first, yes or no, then at most one short "
                f"sentence: is this true right now: {condition}?")

    def judged(self, answer):
        """Two yeses in a row before Luma speaks up, so one blurry picture doesn't cry wolf. Returns True when it's time."""
        if not self.watch:
            return False
        self.watch["checks"] += 1
        yes = bool(re.match(r"\W*yes\b", str(answer or ""), re.I))
        self.watch["yes"] = self.watch["yes"] + 1 if yes else 0
        return self.watch["yes"] >= 2


def heads_up(say, seen):
    """What Luma says when the thing they asked about happens: short, so it can be said out loud right away."""
    detail = re.sub(r"^\W*yes\W*", "", str(seen or ""), flags=re.I).strip()
    detail = detail[:1].upper() + detail[1:] if detail else ""
    say = str(say or "").strip()
    return ("Heads up! " + (detail if detail else f"Looks like {say[:1].lower() + say[1:]}.")).strip()
