"""The life file, the day's story, and the nightly tidy.

- **The life file** is what a close friend just knows: who they are, where they live and work, their people and what's
  going on with each, what they love, what they can't eat. It's made of what's true *now* (a newer fact has taken the
  place of an older one), kept short, and rebuilt whenever anything Luma remembers changes. The cloud brain reads it at
  the start of every turn; a small local brain gets the few memories that fit the message instead.
- **Episodes** are a short story of each day, made from what was said that day, then one of each month.
- **Sleep** is the tidy Luma does at night: the same sentence kept twice becomes one, older memories get a key of their
  own, yesterday gets its episode, and the life file is refreshed.

Everything here is built from memories and says which ones ("from"), so forgetting a memory takes what was built from
it too (luma.memory.store).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from luma.memory import facts

FILE = "life:file"
ROOM = 6000          # characters of life file for a cloud brain (about 1,500 tokens)
LINES_A_DAY = 3
BACKFILL_DAYS = 45   # days of episodes written in one night, newest first: an old life is caught up over a few nights


def file(store, room=ROOM, private=True):
    """The life file as text. Kept, and rebuilt only when what Luma remembers has changed. With company in the room
    (private=False) the private things are left out, and that version isn't kept."""
    stamp = [store.changes(), store.count("episode")]  # moves when a memory or a day's story is written or forgotten
    kept = store.get("life", FILE) if private else None
    if kept and kept.get("stamp") == stamp and kept.get("room") == room:
        return kept["text"]
    lines, used, size = [], [], 0
    for memory in store.whats_true():
        text = " ".join(str(memory.get("text") or "").split())
        if not text or (not private and facts.private(text, memory.get("category") or "")):
            continue
        if size + len(text) + 3 > room:
            break
        lines.append("- " + text)
        used.append(memory["id"])
        size += len(text) + 3
    lately = [e for e in store.all("episode", 400) if e.get("span") == "day"][:3] if private else []
    for episode in sorted(lately, key=lambda e: e.get("day", "")):
        line = f"- ({episode['day']}) {episode['text']}"
        if size + len(line) + 1 > room * 1.15:
            break
        lines.append(line)
        used += [i for i in episode.get("from", []) if i not in used]
        size += len(line) + 1
    text = "\n".join(lines)
    if private and text:
        store.put("life", {"text": text, "from": used, "stamp": stamp, "room": room}, FILE)
    return text


def _day_span(day, zone):
    start = datetime(day.year, day.month, day.day, tzinfo=zone)
    return start.timestamp(), (start + timedelta(days=1)).timestamp()


def _story(memories, summarize=None, most=LINES_A_DAY):
    """A few lines that say what a day (or a month) held: the moments that mattered first."""
    ranked = sorted(memories, key=lambda m: (-facts.weight(m.get("text"), m.get("source") or "said"), m.get("created") or 0))[:most]
    ranked.sort(key=lambda m: m.get("created") or 0)
    lines = [" ".join(str(m.get("text") or "").split()).rstrip(".") + "." for m in ranked if m.get("text")]
    if summarize is not None and lines:
        try:
            better = summarize(lines)
            if isinstance(better, str) and better.strip():
                return better.strip()[:400], [m["id"] for m in ranked]
        except Exception:
            pass
    return " ".join(lines)[:400], [m["id"] for m in ranked]


def _day(key):
    year, month, day = (int(part) for part in key.split("-"))
    return datetime(year, month, day).date()


def _write_day(store, day, zone, summarize):
    said = [m for m in store.said_between(*_day_span(day, zone)) if m.get("source") in ("said", "log")]
    text, used = _story(said, summarize) if said else ("", [])
    if text:
        store.put("episode", {"day": day.isoformat(), "span": "day", "text": text, "from": used, "created": _day_span(day, zone)[0]},
                  "episode:" + day.isoformat())
    return bool(text)


def _write_month(store, first, zone, summarize):
    last_day = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    start, end = _day_span(first, zone)[0], _day_span(last_day, zone)[1]
    said = [m for m in store.said_between(start, end) if facts.weight(m.get("text"), m.get("source") or "") in (1, 2)]
    text, used = _story(said, summarize, most=5) if said else ("", [])
    if text:
        store.put("episode", {"day": first.strftime("%Y-%m"), "span": "month", "text": text, "from": used, "created": start},
                  "episode:" + first.strftime("%Y-%m"))
    return bool(text)


def write_episodes(store, now, zone=timezone.utc, days=BACKFILL_DAYS, summarize=None):
    """Yesterday and the days before it that have no story yet (newest first, `days` of them), each month that's over, and
    any story that was taken when a memory in it was forgotten (written again from what's left). Returns how many."""
    today = datetime.fromtimestamp(now, zone).date()
    have = {e.get("day") for e in store.all("episode", 1000000)}
    written = 0
    for back in range(1, days + 1):
        day = today - timedelta(days=back)
        if day.isoformat() not in have:
            written += _write_day(store, day, zone, summarize)
    first = today.replace(day=1)
    for _ in range(max(1, days // 30)):  # the months that are over
        first = (first - timedelta(days=1)).replace(day=1)
        if first.strftime("%Y-%m") not in have:
            written += _write_month(store, first, zone, summarize)
    redo = store.setting("stories_to_redo", []) or []
    for key in redo:
        try:
            if len(key) == 10 and _day(key) < today:
                written += _write_day(store, _day(key), zone, summarize) if store.get("episode", "episode:" + key) is None else 0
            elif len(key) == 7 and _day(key + "-01") < today.replace(day=1):
                written += _write_month(store, _day(key + "-01"), zone, summarize) if store.get("episode", "episode:" + key) is None else 0
        except ValueError:
            continue
    if redo:
        store.set_setting("stories_to_redo", [])
    return written


def episodes(store, start, end, span="month"):
    """The stories of the months (or days) inside a span of time, oldest first."""
    return sorted((e for e in store.all("episode", 100000) if e.get("span") == span and start <= (e.get("created") or 0) < end), key=lambda e: e.get("created") or 0)


def sleep(store, now, zone=timezone.utc, summarize=None):
    """The nightly tidy. Returns what it did."""
    merged = 0
    for keep, repeat in store.repeats():  # the same sentence kept twice: the newest stays
        if " ".join(str(keep.get("text") or "").split()) == " ".join(str(repeat.get("text") or "").split()):
            merged += bool(store.delete("memory", repeat["id"]))
    resealed = store.reseal()
    written = write_episodes(store, now, zone, summarize=summarize)
    file(store)
    return {"merged": merged, "resealed": resealed, "episodes": written}
