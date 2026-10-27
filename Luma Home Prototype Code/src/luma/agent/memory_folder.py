"""The memory folder: everything Luma remembers, kept encrypted on the device, sorted the way people think about it
(people, dates, places, likes, plans, health, notes), and the room it all takes up.

From the phone or the computer the owner can open it, fix or forget one memory, clear a whole kind or everything
older than a few months, and make room on the device (old chats, the news Luma has read, browser caches, old files)
so new memories fit without moving to the cloud. Nothing here is ever deleted without the owner asking.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from luma.control.today import folder_size, kind_of

KINDS = ["People", "Dates", "Places", "Likes", "Plans", "Health", "Notes"]
DAY = 86400
# Browser caches only: sign-ins (cookies, saved sessions) stay, so nobody gets logged out.
BROWSER_CACHES = ("Default/Cache", "Default/Code Cache", "Default/GPUCache", "Default/Service Worker/CacheStorage", "ShaderCache", "GrShaderCache")


def _bytes(value):
    return len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))


def folder(agent, per_kind=200):
    """Every memory, sorted into kinds, newest first, with how much room they take."""
    rows = agent.store.all("memory", 100000)
    kinds = {k: [] for k in KINDS}
    for m in rows:
        text = " ".join(str(m.get("text", "")).split())
        if text:
            kinds[kind_of(text)].append({"id": m.get("id"), "text": text[:500], "when": m.get("created"), "source": m.get("source")})
    for items in kinds.values():
        items.sort(key=lambda i: -(i.get("when") or 0))
    return {**agent.memory_quota(), "bytes": sum(_bytes(m) for m in rows),
            "kinds": [{"kind": k, "count": len(v), "items": v[:per_kind]} for k, v in kinds.items() if v]}


def forget(agent, ids=None, kind=None, older_than_days=None):
    """Forget the memories they picked: by id, a whole kind, or everything older than N days. Returns how many."""
    if not ids and not kind and not older_than_days:
        raise ValueError("Pick the memories to forget.")
    if kind and kind not in KINDS:
        raise ValueError("Pick one of: " + ", ".join(KINDS) + ".")
    if older_than_days is not None and (type(older_than_days) is not int or older_than_days < 1):
        raise ValueError("Say how many days old, like 90.")
    wanted = {str(i) for i in (ids or [])}
    cutoff = agent.clock() - older_than_days * DAY if older_than_days else None
    gone = 0
    for m in agent.store.all("memory", 100000):
        text = str(m.get("text", ""))
        hit = (str(m.get("id")) in wanted or (kind and kind_of(text) == kind)
               or (cutoff is not None and (m.get("created") or agent.clock()) < cutoff))
        if hit and agent.store.delete("memory", m["id"]):
            gone += 1
    return {"forgotten": gone, **agent.memory_quota()}


# ---------------------------------------------------------------- making room on the device ---


def _old_chats(agent, days=30):
    cutoff = agent.clock() - days * DAY
    out = []
    for row in agent.store.all("chat", 400):
        log = row.get("log") or []
        last = max((m.get("at") or 0 for m in log), default=0)
        if row.get("thread") != "main" and last and last < cutoff:
            out.append(row)
    return out


def _old_files(agent, days=30):
    cutoff = agent.clock() - days * DAY
    return [f for f in agent.store.all("file", 2000) if (f.get("created") or agent.clock()) < cutoff]


def _file_paths(agent, rows):
    root = Path(agent.files_dir)
    ids = {str(r.get("id")) for r in rows}
    return [p for p in root.glob("*") if p.is_file() and p.name.split("-", 1)[0] in ids] if root.is_dir() else []


def _browser_dirs(agent):
    base = Path(agent.store.db_path).parent / "browser-profile"
    return [base / sub for sub in BROWSER_CACHES if (base / sub).is_dir()]


def space(agent):
    """What could go to make room, biggest first. Memories themselves are in the folder, one by one."""
    news = agent.store.setting("news") or {}
    chats = _old_chats(agent)
    files = _old_files(agent)
    diary = agent.store.all("diary", 5000)
    options = [
        {"key": "news", "label": "News and posts I've read", "detail": "I read them again on my own every 15 minutes.", "bytes": _bytes(news) if news.get("items") else 0},
        {"key": "old_chats", "label": "Chats older than 30 days", "detail": f"{len(chats)} chat{'s' if len(chats) != 1 else ''}. What I learned about you stays in memory.",
         "bytes": sum(_bytes(c) for c in chats)},
        {"key": "old_files", "label": "Files I made over 30 days ago", "detail": f"{len(files)} deck{'s' if len(files) != 1 else ''}, docs and apps.",
         "bytes": sum(p.stat().st_size for p in _file_paths(agent, files))},
        {"key": "browser_cache", "label": "Browser cache", "detail": "Pictures and pages saved to load faster. You stay signed in.",
         "bytes": sum(folder_size(d) for d in _browser_dirs(agent))},
        {"key": "diary", "label": "My diary of our days", "detail": f"{len(diary)} entr{'ies' if len(diary) != 1 else 'y'}.", "bytes": sum(_bytes(d) for d in diary)},
    ]
    options = [o for o in options if o["bytes"] > 0]
    options.sort(key=lambda o: -o["bytes"])
    return {"options": options, "memories": {**agent.memory_quota(), "bytes": sum(_bytes(m) for m in agent.store.all("memory", 100000))}}


def clean(agent, key):
    """Clear one kind of thing to make room. Returns roughly how many bytes came back."""
    before = {o["key"]: o["bytes"] for o in space(agent)["options"]}
    if key == "news":
        agent.store.set_setting("news", {"fetched": 0, "items": [], "failed": []})
    elif key == "old_chats":
        for row in _old_chats(agent):
            ident = row.get("thread")
            if ident in agent.threads:
                agent.delete_thread(ident)
            else:
                agent.store.delete("chat", row["id"])
    elif key == "old_files":
        rows = _old_files(agent)
        for path in _file_paths(agent, rows):
            path.unlink(missing_ok=True)
        for row in rows:
            agent.store.delete("file", row["id"])
    elif key == "browser_cache":
        for d in _browser_dirs(agent):
            shutil.rmtree(d, ignore_errors=True)
    elif key == "diary":
        for row in agent.store.all("diary", 5000):
            agent.store.delete("diary", row["id"])
    else:
        raise ValueError("Pick something from the list to clear.")
    from luma.control import today
    today._SIZES.clear()  # the storage panel shows the new room right away
    return {"cleared": key, "freed_bytes": before.get(key, 0), **space(agent)}


def size_label(n):
    """'3.2 MB', '840 KB'."""
    for unit, size in (("GB", 2 ** 30), ("MB", 2 ** 20), ("KB", 2 ** 10)):
        if n >= size:
            return f"{n / size:.1f} {unit}"
    return f"{n} bytes"
