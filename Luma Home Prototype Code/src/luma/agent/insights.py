"""How much Luma has worked for you and what it's done: the numbers behind the Overview page.

Work time is measured, never estimated: the seconds Luma spent thinking through a reply,
and the length of each job it ran (comparing prices, a helper's scheduled run). Kept per
day on this computer, for the last 120 days.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta

WORK_KEY = "work_log"
_lock = threading.Lock()


def log(store, zone, when, seconds=0.0, **counts):
    """Add work to the day it happened on (in their time zone)."""
    day = datetime.fromtimestamp(when, zone).date().isoformat()
    with _lock:
        book = dict(store.setting(WORK_KEY) or {})
        entry = dict(book.get(day) or {})
        entry["s"] = round(entry.get("s", 0) + max(0.0, min(float(seconds or 0), 6 * 3600)), 1)
        for key, n in counts.items():
            entry[key] = entry.get(key, 0) + int(n)
        book[day] = entry
        for old in sorted(book)[:-120]:
            del book[old]
        store.set_setting(WORK_KEY, book)


def say_time(seconds):
    """3h 12m, 14m, 40s."""
    seconds = int(round(seconds or 0))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes // 60}h {minutes % 60:02d}m"


def overview(agent):
    store, zone = agent.store, agent.zone
    now = agent.clock()
    today = datetime.fromtimestamp(now, zone).date()
    book = store.setting(WORK_KEY) or {}
    week = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        entry = book.get(day.isoformat()) or {}
        week.append({"day": day.isoformat(), "label": "Today" if i == 0 else day.strftime("%a"), "s": entry.get("s", 0),
                     "chats": entry.get("chats", 0), "tasks": entry.get("tasks", 0)})
    total = sum(e.get("s", 0) for e in book.values())
    this_week = sum(d["s"] for d in week)
    last_week = sum((book.get((today - timedelta(days=i)).isoformat()) or {}).get("s", 0) for i in range(7, 14))
    memories = [m for m in store.all("memory", 5000) if m.get("text") and not m.get("news")]
    files = store.all("file", 500)
    reminders = [t for t in store.all("task", 500) if not t.get("done")]
    pending = [r for r in store.all("action", 100) if r.get("state") == "pending" and r.get("expires", 0) >= now]
    first = store.setting("first_seen") or now
    recent = []
    for job in agent.activity.recent[:6]:
        if job.get("finished") and job.get("started"):
            recent.append({"title": job.get("title"), "state": job.get("state"), "summary": job.get("summary"), "finished": job.get("finished"),
                           "took": say_time(job["finished"] - job["started"])})
    return {
        "worked": {"today": week[-1]["s"], "week": this_week, "last_week": last_week, "total": total,
                   "today_text": say_time(week[-1]["s"]), "week_text": say_time(this_week), "total_text": say_time(total)},
        "week": week,
        "counts": {"chats": sum(e.get("chats", 0) for e in book.values()), "tasks": sum(e.get("tasks", 0) for e in book.values()),
                   "memories": len(memories), "files": len(files), "reminders": len(reminders), "helpers": len(agent.helpers.list()),
                   "waiting": len(pending)},
        "days_together": max(1, int((now - first) // 86400) + 1),
        "now": agent.activity.view(),
        "recent": recent,
    }
