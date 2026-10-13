"""Your calendar, free: Luma reads the private iCal (ICS) link your calendar app gives you.

Google Calendar: Settings → your calendar → "Secret address in iCal format".
iCloud: share the calendar as a public link. Outlook: Publish calendar → ICS.
The link is read-only, so Luma can see what's coming up but can't change it.
"""
from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo

MAX_BYTES = 3_000_000
WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Luma/1.0 (calendar)", "Accept": "text/calendar, */*"})
    with urllib.request.urlopen(request, timeout=15) as response:
        if urllib.parse.urlsplit(response.geturl()).scheme != "https":
            raise ValueError("That calendar link redirected somewhere that isn't secure.")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("That calendar is too big to read.")
    return data.decode("utf-8", "replace")


def check_link(url):
    url = str(url or "").strip()
    if url.startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or "." not in parts.hostname or parts.username or len(url) > 2000:
        raise ValueError("Paste the calendar's private iCal link (it starts with https:// or webcal://).")
    return url


def _unfold(text):
    return re.sub(r"\r?\n[ \t]", "", text).splitlines()


def _unescape(value):
    return value.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def _when(value, params, zone):
    """An ICS date or date-time as an aware datetime, plus whether it's all-day."""
    value = value.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
        day = datetime.strptime(value[:8], "%Y%m%d").date()
        return datetime.combine(day, dtime(0, 0), zone), True
    stamp = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
    if value.endswith("Z"):
        return stamp.replace(tzinfo=timezone.utc), False
    tzid = params.get("TZID")
    try:
        return stamp.replace(tzinfo=ZoneInfo(tzid) if tzid else zone), False
    except Exception:
        return stamp.replace(tzinfo=zone), False


def parse(text, zone):
    events, current = [], None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT":
            if current and "start" in current:
                events.append(current)
            current = None
            continue
        if current is None or ":" not in line:
            continue
        head, value = line.split(":", 1)
        name, *rest = head.split(";")
        params = dict(p.split("=", 1) for p in rest if "=" in p)
        name = name.upper()
        try:
            if name == "DTSTART":
                current["start"], current["all_day"] = _when(value, params, zone)
            elif name == "DTEND":
                current["end"], _ = _when(value, params, zone)
            elif name == "DURATION":
                m = re.fullmatch(r"P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", value.strip())
                if m:
                    w, d, h, mi, s = (int(x or 0) for x in m.groups())
                    current["duration"] = timedelta(weeks=w, days=d, hours=h, minutes=mi, seconds=s)
            elif name == "SUMMARY":
                current["title"] = _unescape(value)[:200]
            elif name == "LOCATION":
                current["location"] = _unescape(value)[:200]
            elif name == "RRULE":
                current["rrule"] = dict(p.split("=", 1) for p in value.split(";") if "=" in p)
            elif name == "EXDATE":
                current.setdefault("exdates", set()).update(_when(v, params, zone)[0] for v in value.split(","))
            elif name == "STATUS":
                current["cancelled"] = value.strip().upper() == "CANCELLED"
            elif name == "RECURRENCE-ID":
                current["recurrence_id"], _ = _when(value, params, zone)
            elif name == "UID":
                current["uid"] = value.strip()
        except (ValueError, KeyError):
            continue
    return events


def _occurrences(event, start, end):
    """Expand the common repeat rules (daily, weekly by day, monthly, yearly) inside [start, end)."""
    first = event["start"]
    length = event.get("end", first + event.get("duration", timedelta(hours=0 if event.get("all_day") else 1))) - first
    rule = event.get("rrule")
    if not rule:
        if first < end and first + max(length, timedelta(minutes=1)) > start:
            yield first, length
        return
    freq = rule.get("FREQ", "")
    interval = max(1, int(rule.get("INTERVAL", "1") or 1))
    count = int(rule["COUNT"]) if rule.get("COUNT", "").isdigit() else None
    until = None
    if rule.get("UNTIL"):
        try:
            until, _ = _when(rule["UNTIL"], {}, first.tzinfo)
        except ValueError:
            until = None
    days = [WEEKDAYS[d[-2:]] for d in rule.get("BYDAY", "").split(",") if d[-2:] in WEEKDAYS] if freq == "WEEKLY" else []
    exdates = event.get("exdates", set())
    made = 0
    cursor = first
    for _ in range(3000):
        candidates = [cursor]
        if freq == "WEEKLY" and days:
            monday = cursor - timedelta(days=cursor.weekday())
            candidates = sorted(monday + timedelta(days=d) for d in days)
        for when in candidates:
            if when < first:
                continue
            if until and when > until or count is not None and made >= count:
                return
            made += 1
            if when >= end:
                return
            if when + max(length, timedelta(minutes=1)) > start and when not in exdates:
                yield when, length
        if freq == "DAILY":
            cursor += timedelta(days=interval)
        elif freq == "WEEKLY":
            cursor += timedelta(weeks=interval)
        elif freq == "MONTHLY":
            month = cursor.month - 1 + interval
            year = cursor.year + month // 12
            try:
                cursor = cursor.replace(year=year, month=month % 12 + 1)
            except ValueError:
                cursor = cursor.replace(year=year, month=month % 12 + 1, day=28)
        elif freq == "YEARLY":
            try:
                cursor = cursor.replace(year=cursor.year + interval)
            except ValueError:
                cursor = cursor.replace(year=cursor.year + interval, day=28)
        else:
            return
        if cursor >= end and (freq != "WEEKLY" or cursor - timedelta(days=cursor.weekday()) >= end):
            return


class CalendarFeed:
    def __init__(self, store, zone, fetcher=fetch, clock=time.time):
        self.store = store
        self.zone = zone if isinstance(zone, ZoneInfo) else ZoneInfo(str(zone))
        self.fetcher = fetcher
        self.clock = clock
        self._cache = None

    def connected(self):
        return bool(self.store.setting("calendar_ics"))

    def status(self):
        link = self.store.setting("calendar_ics")
        if not link:
            return {"connected": False}
        return {"connected": True, "host": urllib.parse.urlsplit(link).hostname}

    def connect(self, url):
        url = check_link(url)
        text = self.fetcher(url)
        if "BEGIN:VCALENDAR" not in text[:2000]:
            raise ValueError("That link didn't return a calendar. Copy the iCal (.ics) link.")
        self.store.set_setting("calendar_ics", url)
        self._cache = {"at": self.clock(), "events": parse(text, self.zone)}
        return self.status()

    def disconnect(self):
        self.store.set_setting("calendar_ics", None)
        self._cache = None
        return {"connected": False}

    def _events(self):
        link = self.store.setting("calendar_ics")
        if not link:
            raise ValueError("Your calendar isn't connected yet. Add its iCal link in Apps.")
        if not self._cache or self.clock() - self._cache["at"] > 600:
            self._cache = {"at": self.clock(), "events": parse(self.fetcher(link), self.zone)}
        return self._cache["events"]

    def between(self, start, end):
        events = [e for e in self._events() if not e.get("cancelled")]
        moved = {(e.get("uid"), e["recurrence_id"]) for e in events if e.get("recurrence_id")}
        out = []
        for event in events:
            for when, length in _occurrences(event, start, end):
                if not event.get("recurrence_id") and (event.get("uid"), when) in moved:
                    continue
                local = when.astimezone(self.zone)
                out.append({"title": event.get("title") or "(busy)", "location": event.get("location"), "all_day": event.get("all_day", False),
                            "start": local.timestamp(), "end": (local + length).timestamp(),
                            "time": "All day" if event.get("all_day") else local.strftime("%-I:%M %p")})
        out.sort(key=lambda e: (e["start"], e["title"]))
        return out[:60]

    def agenda(self, days=1, offset=0):
        today = datetime.fromtimestamp(self.clock(), self.zone).date() + timedelta(days=offset)
        start = datetime.combine(today, dtime(0, 0), self.zone)
        return self.between(start, start + timedelta(days=max(1, min(int(days), 14))))

    @staticmethod
    def describe(events, label="today"):
        if not events:
            return f"Nothing on your calendar {label}."
        parts = [(e["title"] if e["all_day"] else f"{e['title']} at {e['time']}") for e in events[:5]]
        more = f", plus {len(events) - 5} more" if len(events) > 5 else ""
        return f"{label.capitalize()} you've got " + "; ".join(parts) + more + "."
