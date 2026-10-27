"""What's new in the world, read live from free public news feeds (RSS/Atom).

The local model only knows what it learned before its training ended. Every
15 minutes Luma reads public feeds (world news, the culture: The Shade Room, TMZ,
Billboard, XXL, Complex and friends, what's new on big YouTube channels, what's
blowing up on Reddit, markets) and keeps two days of it. When
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
    ("ESPN", f"{GOOGLE}/search?q=site:espn.com+when:1d&{REGION}", "sports"),  # the feed turns some networks away: the same stories through Google News
    # The culture: what people are actually talking about.
    ("The Shade Room", "https://theshaderoom.com/feed/", "culture"),
    ("The Shade Room", f"{GOOGLE}/search?q=site:theshaderoom.com+when:2d&{REGION}", "culture"),
    ("TMZ", "https://www.tmz.com/rss.xml", "culture"),
    ("Billboard", "https://www.billboard.com/feed/", "culture"),
    ("XXL", "https://www.xxlmag.com/feed/", "culture"),
    ("Bossip", "https://bossip.com/feed/", "culture"),
    ("Complex", f"{GOOGLE}/search?q=site:complex.com+when:2d&{REGION}", "culture"),
    ("HotNewHipHop", f"{GOOGLE}/search?q=site:hotnewhiphop.com+when:2d&{REGION}", "culture"),
    ("Google News", f"{GOOGLE}/headlines/section/topic/ENTERTAINMENT?{REGION}", "culture"),
    ("Reddit", "https://www.reddit.com/r/popular/top/.rss?t=day", "viral"),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex", "business"),
    ("Google News", f"{GOOGLE}/headlines/section/topic/BUSINESS?{REGION}", "business"),
]
# TikTok and Instagram can't be read without an account, and Luma doesn't scrape creators. What it reads instead, and says so: what
# news outlets report is blowing up there, what people are searching right now (Google Trends) and what they looked up most (Wikipedia).
SOCIAL = [
    ("Google News", f"{GOOGLE}/search?q=tiktok+viral+OR+trend+OR+trending+when:2d&{REGION}", "tiktok"),
    ("Google News", f"{GOOGLE}/search?q=instagram+viral+OR+trending+when:2d&{REGION}", "instagram"),
    ("Google News", f"{GOOGLE}/search?q=tiktok+song+OR+sound+viral+OR+trending+when:7d&{REGION}", "tiktok"),  # the sounds everyone's using
    ("Google Trends", "https://trends.google.com/trending/rss?geo=US", "trending"),
]
WIKI_TOP = "https://en.wikipedia.org/api/rest_v1/feed/featured/{day}"
# Not headlines: kept for "what's trending" and "what's new on YouTube", left out of "what's in the news".
NOT_HEADLINES = {"youtube", "viral", "trending", "lookedup", "tiktok", "instagram"}
# Celebrity and gossip feeds: theirs is "what's the tea", not "what's the top news" (a big one still reaches the top through Google News).
NOT_TOP = NOT_HEADLINES | {"culture"}
# Big YouTube channels whose new uploads Luma keeps up with (the owner can add their own). A handle that doesn't resolve is skipped.
DEFAULT_YOUTUBE = ["@MrBeast", "@KaiCenat", "@IShowSpeed", "@Complex", "@genius", "@FirstWeFeast", "@NBA", "@NFL", "@SNL", "@colbertlateshow",
                   "@WWE", "@Druski", "@BETNetworks", "@HotNewHipHop", "@XXL"]
# Outlets people ask about by name, and the site to search when the cache has nothing from them.
SOURCES = {
    "The Shade Room": (r"(?:the )?shade ?room|tsr|theshaderoom", "theshaderoom.com"), "TMZ": (r"tmz", "tmz.com"),
    "Billboard": (r"billboard", "billboard.com"), "XXL": (r"xxl", "xxlmag.com"), "Bossip": (r"bossip", "bossip.com"),
    "Complex": (r"complex", "complex.com"), "HotNewHipHop": (r"hnhh|hot ?new ?hip ?hop", "hotnewhiphop.com"),
    "YouTube": (r"youtube|yt", None), "Reddit": (r"reddit", None), "ESPN": (r"espn", "espn.com"),
}
# "what did the shade room post", "what's poppin on youtube", "what's the tea": the culture, not a search.
ASKS_CULTURE = re.compile(
    r"\b(?:what(?:'s|s| is| did| has)?|anything|any(?:thing)? new|new|latest|post(?:ed|ing)?|say(?:ing)?|on)\b.{0,40}\b(?:shade ?room|tsr|tmz|bossip|"
    r"hnhh|hot ?new ?hip ?hop|xxl|billboard)\b|\b(?:shade ?room|tsr|tmz|bossip)\b.{0,30}\b(?:post(?:ed|ing)?|say(?:ing)?|got|up to|report(?:ed|ing)?)\b|"
    r"\bwhat'?s (?:poppin|popping|trending|viral|hot|the move|going viral)\b(?! (?:with you|wit you|w you))|\bwhat'?s (?:new |good |poppin |popping |trending |viral |hot )?on "
    r"(?:youtube|yt|reddit|tik ?tok|instagram|insta|ig|the gram|twitter|x)\b|\b(?:tik ?tok|instagram|insta|ig) (?:trends?|trending|viral)\b|"
    r"\b(?:trending|viral|blowing up|going viral) (?:on|right now|today|rn)\b|\bwhat(?:'s| is| are) (?:people|everybody|everyone|folks) (?:talking about|searching|posting|saying)\b|"
    r"\b(?:top|biggest) trends\b|\b(?:new|latest) (?:youtube|yt) (?:videos?|uploads?)\b|\bwhat'?s the tea\b|\bspill(?: the)? tea\b|\b(?:any|the) (?:tea|gossip|drama) "
    r"(?:today|rn|right now|lately)\b|\bcelebrity (?:news|gossip|drama)\b|\bhip ?hop news\b|\bwho(?:'s| is) beefing\b", re.I)
# Google News' own sections: what Luma reads when you ask for "sports news" or "business news".
TOPICS = {"world": "WORLD", "us": "NATION", "business": "BUSINESS", "tech": "TECHNOLOGY", "sports": "SPORTS",
          "science": "SCIENCE", "health": "HEALTH", "entertainment": "ENTERTAINMENT"}
# Read from Luma's own feeds, not a Google section.
OWN_TOPICS = {"culture", "youtube", "viral"}
SOCIAL_TOPICS = {"tiktok", "instagram", "trending"}
TOPIC_WORDS = {
    "tiktok": r"tik ?tok|tiktoks",
    "instagram": r"instagram|insta|ig|the gram|reels?",
    "youtube": r"youtube|yt videos?|youtubers?",
    "viral": r"reddit",
    "culture": r"shade ?room|tsr|tmz|bossip|xxl|hnhh|tea|gossip|drama|beef(?:ing)?|poppin|popping|hip ?hop|rap(?:pers?)?|the culture|pop culture|celeb(?:s|rity|rities)? (?:news|gossip|drama)",
    "world": r"world news|international|global|foreign", "us": r"u\.s\.?|us news|national|america|american|domestic",
    "business": r"business|markets?|stocks?|economy|economic|finance|financial|money|wall street",
    "tech": r"tech|technology|ai|a\.i\.|startups?|silicon valley|gadgets?",
    "sports": r"sports?|nba|nfl|mlb|nhl|soccer|football|basketball|baseball|hockey|tennis|golf|f1|ufc",
    "science": r"science|space|nasa|climate", "health": r"health|medical|medicine|covid|flu",
    "entertainment": r"entertainment|celebrity|celebrities|movies?|films?|music|hollywood|tv shows?|box office",
    "trending": r"trending|trends|viral|going viral|blowing up|memes?|(?:people|everybody|everyone|folks) (?:are |is )?(?:talking about|searching|posting|saying)",
}
KEEP_HOURS = 48
MAX_ITEMS = 600
FRESH_SECONDS = 15 * 60  # the background reader: every 15 minutes
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
    """They want the headlines or the culture (not: "I have good news")."""
    text = str(text or "")
    return bool(ASKS_NEWS.search(text) or ASKS_CULTURE.search(text)) and not SHARING_NEWS.search(text)


def named_source(text):
    """'what did the shade room post' -> 'The Shade Room'. None when they didn't name an outlet."""
    text = str(text or "").lower()
    for name, (words, _site) in SOURCES.items():
        if re.search(rf"\b(?:{words})\b", text):
            return name
    return None


def from_source(items, name):
    """What one outlet put out: 'YouTube' covers every channel Luma follows."""
    return [i for i in items if i.get("source") == name or (name == "YouTube" and str(i.get("source", "")).startswith("YouTube"))
            or (name == "Reddit" and i.get("topic") == "viral")]


YT_ID = re.compile(r'"(?:channelId|externalId|browseId)":"(UC[\w-]{22})"|<meta itemprop="(?:identifier|channelId)" content="(UC[\w-]{22})"|/channel/(UC[\w-]{22})')
YT_NAME = re.compile(r'<meta property="og:title" content="([^"]{1,80})"')


def youtube_channel(handle, fetch_page):
    """A channel's id and name from its public page (@handle), so its uploads can be read from YouTube's free feed."""
    handle = "@" + str(handle or "").strip().lstrip("@")
    if not re.fullmatch(r"@[\w.-]{2,40}", handle):
        return None
    page = fetch_page(f"https://www.youtube.com/{handle}").decode("utf-8", "replace")
    found = YT_ID.search(page)
    if not found:
        return None
    name = YT_NAME.search(page)
    return {"id": next(g for g in found.groups() if g), "name": html.unescape(name.group(1)) if name else handle[1:]}


YT_VIDEO = re.compile(r'"videoRenderer":\{"videoId":"([\w-]{11})"')
YT_TITLE = re.compile(r'"title":\{"runs":\[\{"text":"((?:[^"\\]|\\.){1,200})"')
YT_WHEN = re.compile(r'"publishedTimeText":\{"simpleText":"(?:Streamed |Premiered )?(\d+) (second|minute|hour|day|week|month|year)s? ago"')
JUNK_TITLE = re.compile(r"^\s*(?:Browsing|Archives?|Category|Tag|Author)\s*:|\bArchives?\s*[-–|]\s*\S|"
                        r"(?:\s/\s[^/]+){2,}\s+-\s+\w+$|\bEvents Calendar\b", re.I)  # index pages, and store pages ("SSSTUFFF / Layered Shirt / Sweatshirts - Complex")  # "Browsing: X", "X Archives - The Shade Room"
UNIT_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 7 * 86400, "month": 30 * 86400, "year": 365 * 86400}


def youtube_page_items(page, source, now, limit=15):
    """New uploads from a channel's public videos page: the title, the link and roughly when, the same as its feed gives."""
    text = page.decode("utf-8", "replace") if isinstance(page, bytes) else str(page)
    items = []
    for m in YT_VIDEO.finditer(text):
        window = text[m.end(): m.end() + 6000]
        title, when = YT_TITLE.search(window), YT_WHEN.search(window)
        if not title:
            continue
        try:
            name = json.loads(f'"{title.group(1)}"')
        except ValueError:
            name = title.group(1)
        item = {"title": html.unescape(name), "url": f"https://www.youtube.com/watch?v={m.group(1)}", "source": source, "snippet": ""}
        if when:
            item["published"] = now - int(when.group(1)) * UNIT_SECONDS[when.group(2)]
        if not any(i["url"] == item["url"] for i in items):
            items.append(item)
        if len(items) >= limit:
            break
    return items


def youtube_feeds(store, clock, fetch_page):
    """Feeds for the YouTube channels Luma follows: the defaults plus any the owner added. Ids are looked up once and kept."""
    known = dict(store.setting("youtube_channels") or {})
    handles = list(dict.fromkeys((store.setting("youtube_follow") or []) + DEFAULT_YOUTUBE))[:40]
    changed = False
    for handle in handles:
        row = known.get(handle)
        if row is None or (not row.get("id") and clock() - row.get("checked", 0) > 7 * 86400):
            try:
                found = youtube_channel(handle, fetch_page)
            except Exception:
                found = None
            known[handle] = {**(found or {}), "checked": clock()}
            changed = True
    if changed:
        store.set_setting("youtube_channels", known)
    return [(f"YouTube · {known[h]['name']}", f"https://www.youtube.com/feeds/videos.xml?channel_id={known[h]['id']}", "youtube")
            for h in handles if known.get(h, {}).get("id")]


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


GN_OUTLET = re.compile(r"<font[^>]*>([^<]{2,40})</font>", re.I)
# Searches for "viral" pull in spam pages planted on hijacked sites ("XXX viral video Original Clip", walls of hashtags). Never a story.
SPAM = re.compile(r"\bxxx\b|\b18\s*\+|\bnsfw\b|\bporn|\bnude|\bsex(?:y)? (?:tape|video|clip)|\bleak(?:ed)? (?:video|clip|mms)|\bmms\b|"
                  r"\b(?:full|original|viral) (?:video|clip)s?\b.{0,40}\b(?:original|link|full|new|hot|watch)\b|\bhot pics\b|\bwatch (?:full|now|free)\b|"
                  r"\btelegram link\b|\bclick here\b|[~*+#!]{2,}|\[\s*clips?\b|(?:#\w+.*){4,}|[\U0001F459\U0001F51E\U0001F351\U0001F346\U0001F4A6]|"
                  r"\(viral|@\w+\)|\bviral video\s+(?:news|link|original|full|leak\w*|download|hd|telegram)\b", re.I)
# Places spam gets planted (a hospital system's site, a town hall's), and outlets in a script an English edition doesn't use.
SPAM_OUTLET = re.compile(r"NYC Health \+ Hospitals|[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")


def parse_trends(data, source="Google Trends"):
    """What people in the US are searching right now: each term, about how many searches, and the headline behind it."""
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return []
    strip = lambda tag: tag.rsplit("}", 1)[-1]
    out = []
    for node in root.iter():
        if strip(node.tag) != "item":
            continue
        fields = {}
        for child in node:
            fields.setdefault(strip(child.tag), child)
        term = _clean(fields["title"].text if "title" in fields else "", 120)
        if not term:
            continue
        traffic = _clean(fields["approx_traffic"].text if "approx_traffic" in fields else "", 20)
        story = {}
        for part in node.iter():
            if strip(part.tag) == "news_item":
                story = {strip(c.tag): _clean(c.text, 200) for c in part}
                break
        url = story.get("news_item_url") or ""
        if not url.startswith("https://"):
            url = "https://trends.google.com/trends/explore?geo=US&q=" + urllib.parse.quote_plus(term)
        behind = story.get("news_item_title", "")
        item = {"title": term, "url": url[:600], "source": source, "published": _when(fields["pubDate"].text) if "pubDate" in fields else None,
                "snippet": (behind + (f" ({story['news_item_source']})" if story.get("news_item_source") else "")) if behind else ""}
        if traffic:
            item["traffic"] = traffic
        out.append(item)
        if len(out) >= 25:
            break
    out.sort(key=lambda i: searches(i.get("traffic")), reverse=True)  # the biggest searches first
    return out


def searches(traffic):
    """'2,000+' or '20K+' -> 2000 or 20000; 0 when unknown."""
    m = re.match(r"\s*([\d.,]+)\s*([kKmM]?)", str(traffic or ""))
    if not m:
        return 0
    try:
        n = float(m.group(1).replace(",", ""))
    except ValueError:
        return 0
    return int(n * {"k": 1_000, "m": 1_000_000}.get(m.group(2).lower(), 1))


def parse_mostread(data, source="Wikipedia"):
    """What people looked up most on Wikipedia (the day before): a good read on what everybody's curious about."""
    try:
        doc = json.loads(data)
    except (ValueError, TypeError):
        return []
    top = (doc or {}).get("mostread") or {}
    when = _when(str(top.get("date") or "").replace("Z", "") + "T23:59:00+00:00") if top.get("date") else None
    out = []
    for a in top.get("articles") or []:
        title = str(a.get("normalizedtitle") or (a.get("titles") or {}).get("normalized") or "").strip()
        page = ((a.get("content_urls") or {}).get("desktop") or {}).get("page") or ""
        if not title or not page.startswith("https://") or re.match(r"(?:Main Page|Special:|Wikipedia:|Portal:|File:|Help:)", title):
            continue
        out.append({"title": title, "url": page[:600], "source": source, "published": when, "views": a.get("views"),
                    "snippet": _clean(a.get("description") or a.get("extract") or "", 200)})
        if len(out) >= 15:
            break
    return out


PARSERS = {"trending": parse_trends, "lookedup": parse_mostread}


def extras(now):
    """Luma's own trend sources, with today's date where the address needs it."""
    import time as _time
    return SOCIAL + [("Wikipedia", WIKI_TOP.format(day=_time.strftime("%Y/%m/%d", _time.gmtime(now))), "lookedup")]


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
        if title and link.startswith(("https://", "http://")) and not SPAM.search(title):
            outlet = source
            if source.startswith("Google News"):  # "Headline - Outlet": credit the outlet that wrote it
                head, dash, tail = title.rpartition(" - ")
                if dash and head and 1 < len(tail) <= 40:
                    title, outlet = head.strip(), tail.strip()
                if SPAM_OUTLET.search(outlet):
                    continue
            raw = summary.text if summary is not None else ""
            also = []
            if source.startswith("Google News") and raw:  # its top stories list the other outlets covering the same story
                also = list(dict.fromkeys(o.strip() for o in GN_OUTLET.findall(raw) if o.strip() and o.strip() != outlet))[:12]
            snippet = "" if also else _clean(raw, 280)
            if snippet.startswith(title[:40]): snippet = ""  # Google News repeats the headline as the summary
            item = {"title": title, "url": link[:600], "source": outlet, "snippet": snippet, "published": when}
            if also: item["also"] = also
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
    own = fetch is None and not os.environ.get("LUMA_NEWS_FEEDS")  # Luma's own sources (not a test's, not the owner's custom list)
    fetch = fetch or (lambda url: _fetch(url, allow_local=allow_local))
    found, failed = [], []
    lock = threading.Lock()
    now = clock()

    def read(name, url, kind="top"):
        reader = PARSERS.get(kind, parse)
        try:
            items = reader(fetch(url), name)
        except Exception:
            items = None
        if not items and own and kind not in PARSERS:  # some sites only answer a browser
            try:
                items = parse(_fetch_page(url, allow_local=allow_local), name)
            except Exception:
                items = None
        if not items and own and kind == "youtube":  # the feed is down: the same titles from the channel's public list of videos
            try:
                channel = url.split("channel_id=", 1)[1]
                items = youtube_page_items(_fetch_page(f"https://www.youtube.com/channel/{channel}/videos", allow_local=allow_local), name, now)
            except Exception:
                items = None
        items = [i for i in items or [] if not JUNK_TITLE.search(i.get("title") or "")]  # anywhere in the title: "Zeus Archives - The Shade Room"
        for item in items or []:
            item["topic"] = kind
            item["seen"] = now  # when Luma first saw it: the age for a story with no date
        with lock:
            (found.extend(items) if items else failed.append(name))

    sources = list(feeds())
    if own:
        sources += extras(now)
        try:
            sources += youtube_feeds(store, clock, lambda url: _fetch_page(url, allow_local=allow_local))
        except Exception:
            pass  # YouTube unreachable: the rest of the news still comes in
    workers = [threading.Thread(target=read, args=feed, daemon=True) for feed in sources]
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


# "World Series", "World Cup", "Big Ten", "Top Gun": the everyday word is part of the name.
KEEP_BEFORE = {"world": {"series", "cup", "war", "bank", "championship", "championships", "record", "tour", "health", "trade", "games"},
               "big": {"ten", "east", "12", "brother"}, "top": {"gun", "chef", "model"}, "good": {"morning", "friday"}}


def query_for(text):
    """The words worth searching the news for, in the order they said them."""
    out = []
    said = WORDS.findall(str(text).lower())
    for n, w in enumerate(said):
        if w in KEEP_BEFORE and n + 1 < len(said) and said[n + 1] in KEEP_BEFORE[w]:
            out.append(w)
            continue
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


# Outlets that report first-hand: their headline is the one to lead with when several cover the same story.
WIRES = {"Associated Press", "AP News", "Reuters", "BBC", "BBC News", "NPR", "The New York Times", "The Washington Post", "The Wall Street Journal",
         "CNN", "NBC News", "ABC News", "CBS News", "Bloomberg", "The Guardian", "Financial Times", "Axios", "Politico", "USA Today", "ESPN"}


COLUMN = re.compile(r"^(?:opinion|analysis|column|commentary|review|editorial|perspective|letters?|discursive verses|the big story)\b", re.I)


def stories(items, limit=8):
    """The same story from different outlets, grouped, biggest first: the one the most outlets are covering, then the newest.
    Each: the lead item plus 'outlets' (everyone covering it) and 'latest' (its newest update)."""
    def same(a, b):  # the same word, or the same stem ("Israel", "Israelis"; "elect", "election")
        return a == b or (len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5])

    groups = []
    for item in sorted(items, key=when, reverse=True):
        words = terms(item["title"])
        if not words:
            continue
        home = None
        for g in groups:
            matched = [w for w in words if any(same(w, v) for v in g["words"])]
            shared = len(matched)
            close_in_time = abs(when(item) - when(g["items"][0])) <= 12 * 3600
            if shared >= 3 or (shared >= 2 and (shared / len(words | g["words"]) >= 0.3 or (close_in_time and any(len(w) >= 7 for w in matched)))):
                home = g
                break
        if home is None:
            groups.append({"words": set(words), "items": [item]})
        else:
            home["items"].append(item)
    out = []
    for g in groups:
        outlets = list(dict.fromkeys([i["source"] for i in g["items"]] + [o for i in g["items"] for o in i.get("also", [])]))
        # Google's own pick for the story (the one listing who else covers it), else a first-hand outlet, else the newest. Not a column.
        lead = max(g["items"], key=lambda i: (len(i.get("also", [])), i["source"] in WIRES and not COLUMN.search(i["title"]), when(i)))
        out.append(dict(lead, outlets=outlets, latest=max(when(i) for i in g["items"])))
    def weight(s):  # how many outlets carry it; a first-hand outlet counts a little more, gossip only one site has a little less
        first_hand = any(o in WIRES for o in s["outlets"])
        lone_gossip = len(s["outlets"]) == 1 and s.get("topic") == "culture"
        return min(len(s["outlets"]), 6) + (0.5 if first_hand else 0) - (0.5 if lone_gossip else 0)
    out.sort(key=lambda s: (weight(s), s["latest"]), reverse=True)
    return out[:limit]


def credit(story, short=True):
    """Who's reporting it: 'BBC, NPR and 4 others', or 'only TMZ so far' when one outlet has it (said as theirs, not as fact)."""
    outlets = story.get("outlets") or [story.get("source", "")]
    if len(outlets) <= 1:
        return f"only {outlets[0]} so far" if story.get("topic") not in NOT_HEADLINES else outlets[0]
    named = outlets[:2]
    rest = len(outlets) - len(named)
    return ", ".join(named) + (f" and {rest} other{'s' if rest != 1 else ''}" if rest else "")


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
