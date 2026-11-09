"""Where a value came from.

What Luma reads (an email, a web page, a text someone sent, an app's answer, a headline) is information, never
instructions. That isn't left to the brain to obey: before anything is done, this looks at the action itself.

- **A person or an address the owner didn't give** (not in what they said, not one of their contacts) always needs their
  yes, even where a rule would let the action through, and the yes says where it came from: "from an email from X, not
  from you", or "isn't one you gave me" when it can't be found anywhere (a hidden instruction can tell a brain to spell
  an address differently; it still isn't theirs).
- **A link is followed on its own only if** the owner gave it, a search or a price check they asked for returned it as a
  result, or it's a plain site with nothing after the name. A link from inside an email or a page waits for a yes. So does a link put together from other
  things: that's how private data would be carried out.
- **Words lifted from what it read** into a message are named too.

Nothing here is written to disk, and what was read is forgotten after half an hour. It follows "Defeating Prompt
Injections by Design" (CaMeL) in spirit: values carry their origin, and the rules are about origins, not about what a
model was told.
"""
from __future__ import annotations

import json
import re
import time
from urllib.parse import urlsplit

KEEP_S = 1800        # what was read is remembered this long
KEEP_READ = 60       # and at most this many readings
KEEP_SAID = 60       # the owner's own messages kept to compare against
RUN = 6              # words in a row that count as lifted from what was read
EMAIL = re.compile(r"[a-z0-9][a-z0-9._%+-]*@[a-z0-9-]+(?:\.[a-z0-9-]+)+", re.I)
LINK = re.compile(r"\bhttps?://[^\s<>\"')\]]+", re.I)
PHONE = re.compile(r"(?<![\w@.])\+?\d[\d\s().-]{6,18}\d(?![\w@])")
WHO = ("to", "recipient", "email", "phone", "attendees", "cc", "bcc", "invitees")   # fields that say who something goes to
WHERE = ("url", "link", "href")                                                      # fields that say where to go
WORDS = ("body", "text", "subject", "message", "content", "command", "input")        # fields that carry words


def _digits(value):
    digits = re.sub(r"\D", "", value)
    return digits[-10:] if len(digits) >= 10 else digits


def _link(value):
    """A link as compared: no case in the host, no trailing slash, no #part."""
    parts = urlsplit(value.strip().rstrip(".,;"))
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path.rstrip('/')}" + (f"?{parts.query}" if parts.query else "")


def handles(value):
    """The addresses, numbers and links in a value: {("email", ...), ("phone", ...), ("link", ...)}."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    out = {("email", m.group(0).lower()) for m in EMAIL.finditer(text)}
    out |= {("link", _link(m.group(0))) for m in LINK.finditer(text)}
    out |= {("phone", _digits(m.group(0))) for m in PHONE.finditer(EMAIL.sub(" ", LINK.sub(" ", text))) if len(_digits(m.group(0))) >= 7}
    return out


def _plain(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def _runs(words):
    return {" ".join(words[i:i + RUN]) for i in range(len(words) - RUN + 1)}


def plain_site(url):
    """A site and nothing more ("https://www.youtube.com", "https://news.example/world"): no question mark, at most one
    short step in. Nothing private can be carried out on a link like that."""
    parts = urlsplit(url.strip())
    steps = [s for s in parts.path.split("/") if s]
    return parts.scheme in ("http", "https") and not parts.query and not parts.fragment and len(steps) <= 1 and all(len(s) <= 24 for s in steps) \
        and "@" not in parts.netloc


class Sources:
    def __init__(self, theirs=None, clock=time.time):
        self.theirs = theirs or (lambda: [])   # the owner's own saved people: names, numbers, addresses
        self.clock = clock
        self._said, self._read = [], []        # RAM only

    # -- what came in --------------------------------------------------------------------------------------------------
    def owner_said(self, text):
        text = str(text or "")
        self._said = (self._said + [{"text": text.lower(), "handles": handles(text)}])[-KEEP_SAID:]

    def owner_has(self, content):
        """Something of the owner's own that Luma looked up (their notes, their contacts): theirs, like what they said."""
        self.owner_said(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str))

    def read(self, origin, content, kind="content", sender=None, links=()):
        """Something Luma read that the owner didn't write. kind "search": the results of a search they asked for, and
        links are the results themselves (a link merely mentioned inside a result's text is not a result).
        sender: who wrote it, when it's one message (a draft back to them is a reply, not a stranger)."""
        text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str)
        self._read = (self._read + [{"origin": str(origin)[:160], "kind": kind, "handles": handles(text), "runs": _runs(_plain(text)[:6000]),
                                     "sender": handles(str(sender or "")), "results": {_link(str(link)) for link in links or () if link},
                                     "at": self.clock()}])[-KEEP_READ:]

    def _a_search_result(self, value):
        wanted = {link for kind, link in handles(value) if kind == "link"}
        return bool(wanted) and any(wanted <= reading["results"] for reading in self._fresh())

    def _reply_to_sender(self, value):
        wanted = handles(value)
        return bool(wanted) and any(wanted <= reading["sender"] for reading in self._fresh())

    def _fresh(self):
        cutoff = self.clock() - KEEP_S
        self._read = [r for r in self._read if r["at"] >= cutoff]
        return self._read

    # -- where a value is from -----------------------------------------------------------------------------------------
    def from_owner(self, value):
        """Every address, number and link in the value is one the owner said, or one of their saved people's."""
        wanted = handles(value)
        if not wanted:
            name = " ".join(_plain(str(value)))
            return bool(name) and (any(name in " ".join(_plain(said["text"])) for said in self._said)
                                   or any(name == " ".join(_plain(str(own))) for own in self.theirs()))
        have = set().union(*(said["handles"] for said in self._said)) if self._said else set()
        for own in self.theirs():
            have |= handles(str(own))
        return wanted <= have

    def trace(self, value, kinds=("content", "search")):
        """Where Luma read this (the newest reading that has one of its addresses, numbers or links, or six of its words
        in a row), or None."""
        wanted = handles(value)
        runs = _runs(_plain(value)) if isinstance(value, str) and len(value) >= 40 else set()
        for reading in reversed(self._fresh()):
            if reading["kind"] in kinds and (wanted & reading["handles"] or runs & reading["runs"]):
                return reading["origin"]
        return None

    # -- the rule -------------------------------------------------------------------------------------------------------
    def judge(self, rung, arguments):
        """{"ask": whether this needs the owner's yes because of where its values came from, "note": why, in plain words}."""
        notes = []
        for field, value in (arguments or {}).items():
            if not isinstance(value, str) or not value.strip():
                continue
            if field in WHERE or (rung == "read" and field not in WORDS and handles(value) and all(kind == "link" for kind, _ in handles(value))):
                # theirs; or a result of a search or a price check they asked for; or, to look at, a plain site
                if self.from_owner(value) or self._a_search_result(value) or (rung == "read" and plain_site(value)):
                    continue
                origin = self.trace(value)
                notes.append(f"The link came from {origin}, not from you." if origin else
                             "That link is one I put together myself; it isn't one you gave me or one I found as it is.")
            elif field in WHO and rung != "read":
                if self.from_owner(value) or (rung == "draft" and self._reply_to_sender(value)):
                    continue
                origin = self.trace(value)
                notes.append(f"“{value[:80]}” came from {origin}, not from you." if origin else
                             f"“{value[:80]}” isn't one you gave me or one of your contacts.")
            elif rung in ("act", "draft", "never", "own"):  # any other words it carries: a message, a note to keep, a reminder
                origin = self.trace(value)
                if origin and not self._their_words(value) and not self.from_owner(value):
                    notes.append(f"Some of this was taken from {origin}.")
        return {"ask": bool(notes), "note": " ".join(dict.fromkeys(notes)) or None}

    def _their_words(self, value):
        """Every run of words in it is something the owner said themselves (they read it out, or dictated it)."""
        runs = _runs(_plain(value))
        said = set().union(*(_runs(_plain(s["text"])) for s in self._said)) if self._said else set()
        return bool(runs) and runs <= said and not (handles(value) - (set().union(*(s["handles"] for s in self._said)) if self._said else set()))
