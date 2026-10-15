"""What's new in the world, read live from free public news feeds (RSS/Atom).

The local model only knows what it learned before its training ended. Every
hour Luma reads a handful of public feeds and keeps two days of headlines. When
you ask, it reads them again if they're more than a few minutes old, and for a
topic ("latest on the Fed", "tech news") it searches Google News right then, so
the answer is minutes old, not hours. No accounts, no API keys, no cost. Feeds
are read in parallel, one small reader per feed.
"""
from __future__ import annotations

import html
import json
import os
import re
import threading
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime
from datetime import datetime
from xml.etree import ElementTree

# Free, public, no key needed. Override with LUMA_NEWS_FEEDS='[["Name","https://…"], …]' (a third value, the topic, is optional).
GOOGLE = "https://news.google.com/rss"
REGION = "hl=en-US&gl=US&ceid=US:en"
FEEDS = [
    ("Google News", f"{GOOGLE}?{REGION}", "top"),
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml", "world"),
    ("NPR", "https://feeds.npr.org/1001/rss.xml", "top"),
    ("The Verge", "https://www.theverge.com/rss/index.xml", "tech"),
    ("TechCrunch", "https://techcrunch.com/feed/", "tech"),
    ("Hacker News", "https://news.ycombinator.com/rss", "tech"),
    ("ESPN", "https://www.espn.com/espn/rss/news", "sports"),
]
# Google News' own sections: what Luma reads when you ask for "sports news" or "business news".
TOPICS = {"world": "WORLD", "us": "NATION", "business": "BUSINESS", "tech": "TECHNOLOGY", "sports": "SPORTS",
          "science": "SCIENCE", "health": "HEALTH", "entertainment": "ENTERTAINMENT"}
TOPIC_WORDS = {
    "world": r"world news|international|global|foreign", "us": r"u\.s\.?|us news|national|america|american|domestic",
    "business": r"business|markets?|stocks?|economy|economic|finance|financial|money|wall street",
    "tech": r"tech|technology|ai|a\.i\.|startups?|silicon valley|gadgets?",
    "sports": r"sports?|nba|nfl|mlb|nhl|soccer|football|basketball|baseball|hockey|tennis|golf|f1|ufc",
    "science": r"science|space|nasa|climate", "health": r"health|medical|medicine|covid|flu",
    "entertainment": r"entertainment|celebrity|celebrities|movies?|films?|music|hollywood|tv shows?|box office",
}
KEEP_HOURS = 48
MAX_ITEMS = 300
FRESH_SECONDS = 3600     # the background reader: every hour
LIVE_SECONDS = 15 * 60   # when they ask: anything older than this gets read again first
WORDS = re.compile(r"[a-z0-9]+")
STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "was", "were", "with", "at", "by", "from", "what", "whats",
        "about", "news", "latest", "today", "happening", "going", "me", "my", "tell", "any", "new", "s", "it", "this", "that", "how", "did",
        "last", "past", "hours", "hour", "hrs", "hr", "minutes", "mins", "days", "day", "week", "weeks", "real", "time", "realtime", "live",
        "breaking", "update", "updates", "give", "show", "get", "can", "could", "you", "please", "pls", "plz", "know", "some", "anything",
        "everything", "world", "top", "stories", "story", "right", "now", "been", "has", "have", "there", "just", "like", "okay", "ok", "so",
        "yo", "hey", "lately", "recent", "recently", "since", "yesterday", "tonight", "morning", "overnight", "night", "again", "headline",
        "headlines", "catch", "up", "current", "events", "happened", "big", "biggest", "major", "whole", "out", "need", "want", "u", "ur",
        "luma", "do", "does", "be", "would", "should", "all", "more", "most", "other", "else", "summary", "summarize", "rundown", "brief", "briefing",
        "knews", "newz", "nws", "neews", "nwes", "nuews", "good", "great", "bad", "happen", "goin", "on", "abt"}
FILLER = re.compile(r"^(?:u+h+|u+m+|h+m+|e+r+m*|a+h+|o+h+|l+o+l+|\d+\w*)$")
NEWS_WORD = r"(?:news|knews|newz|nws|neews|nwes|nuews)"
ASKS_NEWS = re.compile(
    rf"\b(?:{NEWS_WORD}|headlines?|breaking|what'?s (?:new|happening|going on) (?:in the world|out there|today|right now|lately)|"
    r"what'?s happening(?=\s*[?!.]*$)|catch me up(?: on (?:the world|everything|what'?s (?:happening|going on)))?(?=\s*[?!.]*$| on (?:the world|everything|what))|"
    r"current events|what happened (?:today|yesterday|overnight|last night|with|to|in)|latest (?:on|with|about|stories))\b", re.I)
# "I have news" / "good news, I got the job": they're telling Luma something, not asking for the headlines.
SHARING_NEWS = re.compile(r"\b(?:i|we) (?:have|got|heard)\b[^?]{0,30}\bnews\b|^\W*(?:(?:so|ok(?:ay)?|guess what|omg|yo|hey|luma)\W+)*"
                          r"(?:good|great|bad|sad|exciting|amazing|terrible|awful|big|some) news\b(?![^?]*\?)", re.I)
WINDOW = re.compile(r"\b(?:in |over |from )?(?:the )?(?:last|past|previous)\s+(?:(?:u+h+|u+m+|like|about|around|maybe|roughly)\W+)*(?:(?P<n>\d{1,3}|a|an|one|two|three|four|five|six|eight|ten|twelve|few|couple(?: of)?)\s*)?"
                    r"(?P<unit>h(?:ou)?rs?|hours?|h\b|min(?:ute)?s?|days?|d\b|weeks?|24)\b", re.I)
NUMBERS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "eight": 8, "ten": 10, "twelve": 12, "few": 3, "couple": 2, "couple of": 2}


def feeds():
    custom = os.environ.get("LUMA_NEWS_FEEDS")
    if custom:
        try:
            return [(str(f[0])[:40], str(f[1]), str(f[2]) if len(f) > 2 else "top") for f in json.loads(custom)][:20]
        except (ValueError, TypeError, IndexError, KeyError):
            pass
    return FEEDS


def asks(text):
    """They want the headlines (not: "I have good news")."""
    text = str(text or "")
    return bool(ASKS_NEWS.search(text)) and not SHARING_NEWS.search(text)


def window_hours(text):
    """'in the last 10 hrs' -> 10. 'today' -> since this morning, roughly. None when they didn't say."""
    text = str(text or "").lower()
    m = WINDOW.search(text)
    if m:
        unit = m["unit"].lower()
        if unit == "24": return 24
        n = m["n"]
        n = NUMBERS.get(n, None) if n and not n.isdigit() else int(n) if n else 1
        if unit.startswith("min"): return max(1, round((n or 1) / 60)) if (n or 0) >= 60 else 1
        if unit.startswith("d"): return min(168, 24 * (n or 1))
        if unit.startswith("w"): return 168
        return max(1, min(168, n or 1))
    if re.search(r"\b(?:this morning|overnight|last night|since i (?:woke|got up)|while i (?:was )?(?:asleep|sleeping))\b", text): return 12
    if re.search(r"\b(?:right now|just now|breaking|this hour|live)\b", text): return 3
    if re.search(r"\b(?:today|so far)\b", text): return 24
    if re.search(r"\byesterday\b", text): return 48
    if re.search(r"\bthis week\b", text): return 168
    return None


def topic(text):
    """'sports news' -> 'sports'. None when it's just the news in general."""
    text = str(text or "").lower()
    for name, words in TOPIC_WORDS.items():
        if re.search(rf"\b(?:{words})\b", text):
            return name
    return None


def ago(when, now):
    """'just now', '25 min ago', '3h ago', 'yesterday'."""
    if not when: return ""
    gap = max(0, now - when)
    if gap < 120: return "just now"
    if gap < 3600: return f"{int(gap // 60)} min ago"
    if gap < 86400: return f"{int(gap // 3600)}h ago"
    return "yesterday" if gap < 2 * 86400 else f"{int(gap // 86400)} days ago"


def _clean(text, limit):
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(text or "")))
    return " ".join(text.split())[:limit]


def _when(text):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return parsedate_to_datetime(text).timestamp()
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def parse(data, source):
    """Headlines from one RSS or Atom document. Bad feeds give nothing, never an error."""
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return []
    strip = lambda tag: tag.rsplit("}", 1)[-1]
    out = []
    for node in root.iter():
        if strip(node.tag) not in {"item", "entry"}:
            continue
        fields = {strip(child.tag): child for child in node}
        title = _clean(fields["title"].text if "title" in fields else "", 200)
        link = ""
        if "link" in fields:
            link = (fields["link"].text or fields["link"].get("href") or "").strip()
        # (An XML element with no children counts as false, so look these up by name, not with `or`.)
        summary = next((fields[k] for k in ("description", "summary", "content") if k in fields), None)
        when = None
        for key in ("pubDate", "published", "updated", "date"):
            if key in fields:
                when = _when(fields[key].text)
                if when:
                    break
        image = _image(node, summary)
        if title and link.startswith(("https://", "http://")):
            outlet = source
            if source.startswith("Google News"):  # "Headline - Outlet": credit the outlet that wrote it
                head, dash, tail = title.rpartition(" - ")
                if dash and head and 1 < len(tail) <= 40:
                    title, outlet = head.strip(), tail.strip()
            snippet = _clean(summary.text if summary is not None else "", 280)
            if snippet.startswith(title[:40]): snippet = ""  # Google News repeats the headline as the summary
            item = {"title": title, "url": link[:600], "source": outlet, "snippet": snippet, "published": when}
            if image: item["image"] = image
            out.append(item)
        if len(out) >= 40:
            break
    return out


IMG_IN_HTML = re.compile(r"""<img[^>]+src=["'](https://[^"'\s>]{8,600})["']""", re.I)


def _image(node, summary):
    """A story's picture, if its feed has one: media:thumbnail / media:content / an image enclosure / an <img> in the summary."""
    best = None
    for child in node:
        tag = child.tag.rsplit("}", 1)[-1]
        url = child.get("url") or ""
        if not url.startswith("https://"):
            continue
        if tag == "thumbnail" and not best:
            best = url
        elif tag == "content" and (child.get("medium") == "image" or (child.get("type") or "").startswith("image/")):
            return url[:600]
        elif tag == "enclosure" and (child.get("type") or "").startswith("image/"):
            return url[:600]
        for grand in child:  # media:group > media:content
            if grand.tag.rsplit("}", 1)[-1] in {"content", "thumbnail"} and (grand.get("url") or "").startswith("https://"):
                best = best or grand.get("url")
    if best:
        return best[:600]
    if summary is not None and summary.text:
        found = IMG_IN_HTML.search(summary.text)
        if found:
            return html.unescape(found.group(1))[:600]
    return None


def read_article(url, fetch=None, allow_local=False):
    """A story, readable inside Luma: its headline, outlet, picture and paragraphs. Pages that need
    scripts to show anything (or bounce through a redirect page) come back with no paragraphs."""
    from html.parser import HTMLParser
    from luma.integrations.browser import check_url
    url = check_url(url, allow_local)
    raw = (fetch or _fetch_page)(url, allow_local)
    page = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)

    class Reader(HTMLParser):
        SKIP = {"script", "style", "noscript", "nav", "footer", "aside", "form", "button", "svg", "figcaption", "header"}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.meta, self.paragraphs, self.title = {}, [], ""
            self.skip, self.in_p, self.in_title, self.buf = 0, 0, False, []

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "meta":
                key = (a.get("property") or a.get("name") or "").lower()
                if key in {"og:title", "og:image", "og:site_name", "twitter:image", "description", "og:description"} and a.get("content"):
                    self.meta.setdefault(key, a["content"])
            if tag in self.SKIP:
                self.skip += 1
            elif tag == "p" and not self.skip:
                self.in_p += 1
                self.buf = []
            elif tag == "title":
                self.in_title = True

        def handle_endtag(self, tag):
            if tag in self.SKIP and self.skip:
                self.skip -= 1
            elif tag == "p" and self.in_p:
                self.in_p -= 1
                text = " ".join("".join(self.buf).split())
                if len(text) >= 60 and not re.search(r"(?i)cookies|subscribe|sign up for|newsletter|all rights reserved|advertisement", text[:120]):
                    self.paragraphs.append(text[:1500])
            elif tag == "title":
                self.in_title = False

        def handle_data(self, data):
            if self.in_p and not self.skip:
                self.buf.append(data)
            elif self.in_title:
                self.title += data

    reader = Reader()
    try:
        reader.feed(page[:3_000_000])
    except Exception:
        pass
    image = reader.meta.get("og:image") or reader.meta.get("twitter:image") or ""
    seen, paragraphs = set(), []
    for p in reader.paragraphs:
        if p not in seen:
            seen.add(p)
            paragraphs.append(p)
    host = urllib.parse.urlsplit(url).hostname or ""
    return {"url": url, "title": _clean(reader.meta.get("og:title") or reader.title, 300),
            "source": _clean(reader.meta.get("og:site_name") or host.removeprefix("www."), 80),
            "image": image if image.startswith("https://") else None, "paragraphs": paragraphs[:80]}


def _fetch_page(url, allow_local=False):
    from luma.integrations.browser import check_url

    class Checked(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            check_url(newurl, allow_local)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    request = urllib.request.Request(url, headers={"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                                                  "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"),
                                                   "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.build_opener(Checked).open(request, timeout=15) as response:
        kind = response.headers.get("Content-Type", "")
        if "html" not in kind and "xml" not in kind:
            raise ValueError("That link isn't a web page I can read.")
        return response.read(3_000_000)


def _fetch(url, timeout=12, allow_local=False):
    from luma.integrations.browser import check_url

    class Checked(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # a redirect can't lead to the home network either
            check_url(newurl, allow_local)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    url = check_url(url, allow_local)
    request = urllib.request.Request(url, headers={"User-Agent": "Luma/1.0 (personal news reader)", "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
    with urllib.request.build_opener(Checked).open(request, timeout=timeout) as response:
        return response.read(2_000_000)


def _key(item):
    return " ".join(WORDS.findall(item["title"].lower()))[:80]


def refresh(store, clock, allow_local=False, fetch=None):
    """Read every feed at once (a small reader each), merge, de-duplicate and keep two days."""
    fetch = fetch or (lambda url: _fetch(url, allow_local=allow_local))
    found, failed = [], []
    lock = threading.Lock()
    now = clock()

    def read(name, url, kind="top"):
        try:
            items = parse(fetch(url), name)
        except Exception:
            items = None
        for item in items or []:
            item["topic"] = kind
            item["seen"] = now  # when Luma first saw it: the age for a story with no date
        with lock:
            (found.extend(items) if items else failed.append(name))

    workers = [threading.Thread(target=read, args=feed, daemon=True) for feed in feeds()]
    for w in workers: w.start()
    for w in workers: w.join(timeout=20)
    old = (store.setting("news") or {}).get("items", [])
    first_seen = {_key(i): i.get("seen") for i in old if i.get("seen")}
    seen, keep = set(), []
    for item in sorted(found + old, key=lambda i: i.get("published") or i.get("seen") or now, reverse=True):
        key = _key(item)
        if key in first_seen: item["seen"] = first_seen[key]
        if key in seen or (item.get("published") or item.get("seen") or now) < now - KEEP_HOURS * 3600:
            continue
        seen.add(key)
        keep.append(item)
    from luma.memory.store import reject_payment_secrets

    def storable(item):  # e.g. a link with a long status number in it: drop that one story, keep the rest
        try:
            reject_payment_secrets(item)
            return True
        except ValueError:
            return False
    keep = [i for i in keep if storable(i)][:MAX_ITEMS]
    store.set_setting("news", {"fetched": now, "items": keep, "failed": failed})
    return {"items": keep, "fetched": now, "new": len(found), "failed": failed}


def cached(store):
    return store.setting("news") or {"fetched": 0, "items": []}


def is_fresh(store, clock, max_age=None):
    return clock() - (cached(store).get("fetched") or 0) < (FRESH_SECONDS if max_age is None else max_age)


def when(item):
    return item.get("published") or item.get("seen") or 0


def within(items, hours, now):
    """Only what came out in the last N hours, newest first."""
    if not hours:
        return sorted(items, key=when, reverse=True)
    since = now - hours * 3600
    return sorted((i for i in items if when(i) >= since), key=when, reverse=True)


def search(query=None, section=None, hours=24, fetch=None, allow_local=False, base=GOOGLE):
    """Live, right now: Google News for a topic ("fed rate cut") or one of its sections ("SPORTS")."""
    fetch = fetch or (lambda url: _fetch(url, allow_local=allow_local))
    hours = max(1, min(168, int(hours or 24)))
    if query:
        span = f"{hours}h" if hours < 48 else f"{round(hours / 24)}d"
        url = f"{base}/search?q={urllib.parse.quote_plus(query[:120] + ' when:' + span)}&{REGION}"
    elif section:
        url = f"{base}/headlines/section/topic/{section}?{REGION}"
    else:
        url = f"{base}?{REGION}"
    items = parse(fetch(url), "Google News")
    seen, out = set(), []
    for item in items:
        key = _key(item)
        if key in seen: continue
        seen.add(key)
        out.append(item)
    return out


def terms(text):
    return {w for w in WORDS.findall(str(text).lower()) if w not in STOP and len(w) > 2 and not FILLER.match(w)}


def query_for(text):
    """The words worth searching the news for, in the order they said them."""
    out = []
    for w in WORDS.findall(str(text).lower()):
        if w in STOP or len(w) < 2 or FILLER.match(w) or w in out: continue
        if w in {"sports", "sport", "tech", "technology", "business", "science", "health", "entertainment", "us", "international", "global", "national"}:
            continue
        out.append(w)
    return " ".join(out[:8])


def relevant(question, items, limit=5, at_least=2):
    """Headlines that share real words with the question (two, when it has two), best first."""
    want = terms(question)
    if not want:
        return []
    scored = []
    for item in items:
        have = terms(item["title"] + " " + item.get("snippet", ""))
        overlap = len(want & have)
        if overlap >= min(at_least, len(want)):
            scored.append((overlap, item.get("published") or 0, item))
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
    return [s[2] for s in scored[:limit]]


def top(items, limit=8):
    """A spread of today's biggest stories: newest first, no more than two from one source."""
    per, out = {}, []
    for item in items:
        if per.get(item["source"], 0) >= 2:
            continue
        per[item["source"]] = per.get(item["source"], 0) + 1
        out.append(item)
        if len(out) >= limit:
            break
    return out
