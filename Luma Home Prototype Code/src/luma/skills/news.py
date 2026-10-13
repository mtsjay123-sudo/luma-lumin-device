"""What's new in the world, read fresh from free public news feeds (RSS/Atom).

The local model only knows what it learned before its training ended. Every few
hours Luma reads a handful of public feeds, keeps two days of headlines, and
uses them when you ask about the news or something that's in it. No accounts,
no API keys, no cost. Feeds are read in parallel, one small reader per feed.
"""
from __future__ import annotations

import html
import json
import os
import re
import threading
import urllib.request
from email.utils import parsedate_to_datetime
from datetime import datetime
from xml.etree import ElementTree

# Free, public, no key needed. Override with LUMA_NEWS_FEEDS='[["Name","https://…"], …]'.
FEEDS = [
    ("Google News", "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"),
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("NPR", "https://feeds.npr.org/1001/rss.xml"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("Hacker News", "https://news.ycombinator.com/rss"),
    ("ESPN", "https://www.espn.com/espn/rss/news"),
]
KEEP_HOURS = 48
MAX_ITEMS = 150
FRESH_SECONDS = 3 * 3600
WORDS = re.compile(r"[a-z0-9]+")
STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "was", "with", "at", "by", "from", "what", "whats",
        "about", "news", "latest", "today", "happening", "going", "me", "my", "tell", "any", "new", "s", "it", "this", "that", "how", "did"}
ASKS_NEWS = re.compile(r"\b(?:news|headlines|what'?s (?:happening|going on) (?:in the world|today|right now)|catch me up on the world|"
                       r"current events|what happened (?:today|with|to|in)|latest (?:on|with|about))\b", re.I)


def feeds():
    custom = os.environ.get("LUMA_NEWS_FEEDS")
    if custom:
        try:
            return [(str(n)[:40], str(u)) for n, u in json.loads(custom)][:20]
        except (ValueError, TypeError):
            pass
    return FEEDS


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
        if title and link.startswith(("https://", "http://")):
            out.append({"title": title, "url": link[:600], "source": source, "snippet": _clean(summary.text if summary is not None else "", 280),
                        "published": when})
        if len(out) >= 40:
            break
    return out


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


def refresh(store, clock, allow_local=False, fetch=None):
    """Read every feed at once (a small reader each), merge, de-duplicate and keep two days."""
    fetch = fetch or (lambda url: _fetch(url, allow_local=allow_local))
    found, failed = [], []
    lock = threading.Lock()

    def read(name, url):
        try:
            items = parse(fetch(url), name)
        except Exception:
            items = None
        with lock:
            (found.extend(items) if items else failed.append(name))

    workers = [threading.Thread(target=read, args=feed, daemon=True) for feed in feeds()]
    for w in workers: w.start()
    for w in workers: w.join(timeout=20)
    now = clock()
    old = (store.setting("news") or {}).get("items", [])
    seen, keep = set(), []
    for item in sorted(found + old, key=lambda i: i.get("published") or now, reverse=True):
        key = " ".join(WORDS.findall(item["title"].lower()))[:80]
        if key in seen or (item.get("published") or now) < now - KEEP_HOURS * 3600:
            continue
        seen.add(key)
        keep.append(item)
    keep = keep[:MAX_ITEMS]
    try:
        store.set_setting("news", {"fetched": now, "items": keep, "failed": failed})
    except ValueError:  # a headline that looks like a card number; drop numbers and keep the rest
        keep = [{**i, "snippet": re.sub(r"\d{6,}", "", i["snippet"])} for i in keep]
        store.set_setting("news", {"fetched": now, "items": keep, "failed": failed})
    return {"items": keep, "fetched": now, "new": len(found), "failed": failed}


def cached(store):
    return store.setting("news") or {"fetched": 0, "items": []}


def is_fresh(store, clock):
    return clock() - (cached(store).get("fetched") or 0) < FRESH_SECONDS


def terms(text):
    return {w for w in WORDS.findall(str(text).lower()) if w not in STOP and len(w) > 2}


def relevant(question, items, limit=5, at_least=2):
    """Headlines that share real words with the question, best first."""
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
