"""Storage, like the storage page on a phone: what Luma keeps for you, how much room it takes, what happens when it
runs out, and how room comes back.

Everything Luma keeps lives on this device, sealed. How much fits is the device's own storage, less a little kept free so
the device keeps working (RESERVE), or less still when the owner set a cap ("let Luma use up to 5 GB"). Luma itself (its
brain and its voices) is counted apart, the way a phone counts its system.

room(agent)["state"]:
    "ok"      there's room
    "nearly"  almost none left: Luma says so once, plainly, at a calm moment
    "full"    nothing new is kept and nothing new is made until there's room. The talk itself goes on, and so do
              check-ins and the safety net: those are never what gets cut.

Room comes back by deleting: one memory, a kind of memory, old chats, a file Luma made (luma.agent.memory_folder, and
remove() here). The database then hands the space back to the device (Store.compact), so the number on the screen is
the number on the disk.

More room in Luma Cloud is the cloud's one job. It's offered only when Luma Cloud says it's there (more()), and nothing
is ever bought or moved without the owner's yes. No brain is involved in any of this.
"""
from __future__ import annotations

import shutil
from pathlib import Path

GB, MB = 2 ** 30, 2 ** 20
RESERVE = 256 * MB            # kept free on the device, so it can keep working and the database can tidy itself
LOW = 200 * MB                # under this much left, Luma says it's almost out of room
CAP = "storage_cap_bytes"     # the owner's own cap on what Luma keeps, or nothing
SAID = "storage_said"         # what Luma last said about room ("nearly", "full"), so it says each once
MEMORY_KINDS = ("memory", "vector", "episode", "life")   # a memory, what it means, and what was written from it

NEARLY_LINE = ("Heads up: I'm almost out of room for new memories on this device. "
               "When you have a minute, Make room in the Luma app shows what's taking up space.")
FULL_LINE = ("I'm out of room on this device, so I can't keep new memories until there's space. "
             "Make room in the Luma app shows what's taking it up, and you choose what goes.")
CANT_KEEP = "I'm out of room on this device, so I can't keep that yet. Make room in the Luma app, then tell me again."
CANT_MAKE = "I'm out of room on this device, so I can't make that yet. Make room in the Luma app first."


def disk_usage(path):
    """The drive Luma's data is on. Its own function so a test can stand in a full or an empty drive."""
    return shutil.disk_usage(path)


def _sizes_on_disk(agent):
    from luma.agent import memory_folder
    from luma.control.today import folder_size
    files = folder_size(agent.files_dir) if agent.files_dir.is_dir() else 0
    cache = sum(folder_size(d) for d in memory_folder._browser_dirs(agent))
    return max(0, agent.store.file_bytes() - agent.store.spare_bytes()), files, cache  # spare room inside the file is room again


def kept_bytes(agent):
    """Everything Luma keeps for them, in bytes on the device: the database, the files it made, the browser's cache."""
    return sum(_sizes_on_disk(agent))


def room(agent):
    """How much is used, how much fits, how much is left, and which state that is. Cheap enough to ask on every memory."""
    used = kept_bytes(agent)
    try:
        disk = disk_usage(Path(agent.store.db_path).parent)
        free, total = int(disk.free), int(disk.total)
    except OSError:
        free, total = None, None
    cap = agent.store.setting(CAP)
    cap = int(cap) if isinstance(cap, (int, float)) and not isinstance(cap, bool) and cap > 0 else None
    limit = used + max(0, free - RESERVE) if free is not None else None
    if cap is not None:
        limit = cap if limit is None else min(limit, cap)
    if limit is None:  # the drive wouldn't say, and there's no cap: nothing to hold Luma to
        return {"used": used, "limit": None, "left": None, "share": 0.0, "state": "ok", "cap": None, "reserve": RESERVE, "disk": None}
    left = max(0, limit - used)
    state = "full" if left <= 0 else "nearly" if (left < LOW or (cap is not None and used >= 0.9 * limit)) else "ok"
    return {"used": used, "limit": limit, "left": left, "share": round(min(1.0, used / limit), 4) if limit else 1.0, "state": state, "cap": cap,
            "reserve": RESERVE, "disk": {"total": total, "free": free} if total is not None else None}


def full(agent):
    return room(agent)["state"] == "full"


def set_cap(agent, gb):
    """The owner's cap on what Luma keeps here, in GB (1 or more), or None for "as much as the device has"."""
    if gb is None:
        agent.store.set_setting(CAP, None)
        return room(agent)
    if isinstance(gb, bool) or not isinstance(gb, (int, float)) or gb < 1 or gb > 100000:
        raise ValueError("Say how many GB Luma may use, 1 or more. Or turn the cap off.")
    agent.store.set_setting(CAP, int(gb * GB))
    return room(agent)


def usage(agent):
    """What's using the room, by kind, biggest first: the bar on the storage screen. The kinds add up to all of it."""
    sizes = agent.store.sizes()
    database, files_on_disk, cache = _sizes_on_disk(agent)
    of = lambda kinds: (sum(sizes.get(k, {}).get("bytes", 0) for k in kinds), sum(sizes.get(k, {}).get("count", 0) for k in kinds))  # noqa: E731
    memories, _ = of(MEMORY_KINDS)
    chats, chat_count = of(("chat",))
    file_rows, file_count = of(("file",))
    diary, diary_count = of(("diary",))
    news = agent.store.size_of("setting", "setting:news")
    named = memories + chats + file_rows + diary + news
    kinds = [
        {"key": "memories", "label": "Memories", "detail": "What you've told me, and what I've learned about you.", "bytes": memories,
         "count": sizes.get("memory", {}).get("count", 0), "how": "forget"},
        {"key": "chats", "label": "Chats", "detail": "Our conversations, word for word.", "bytes": chats, "count": chat_count, "how": "old_chats"},
        {"key": "files", "label": "Things I made", "detail": "Decks, documents, podcasts and small apps.", "bytes": file_rows + files_on_disk,
         "count": file_count, "how": "old_files"},
        {"key": "diary", "label": "My diary", "detail": "A few lines about each day.", "bytes": diary, "count": diary_count, "how": "diary"},
        {"key": "news", "label": "News I've read", "detail": "I read it again on my own.", "bytes": news, "count": None, "how": "news"},
        {"key": "cache", "label": "Browser cache", "detail": "Pictures and pages saved to load faster.", "bytes": cache, "count": None, "how": "browser_cache"},
        {"key": "other", "label": "Everything else", "detail": "Settings, reminders, check-ins, the record of what I've done, and the database's own upkeep.",
         "bytes": max(0, database - named), "count": None, "how": None},
    ]
    kinds = [k for k in kinds if k["bytes"] > 0]
    kinds.sort(key=lambda k: -k["bytes"])
    return {"kinds": kinds, "bytes": sum(k["bytes"] for k in kinds)}


def _chat_title(row):
    title = " ".join(str(row.get("title") or "").split())
    if title:
        return title[:80]
    first = next((m.get("text") for m in row.get("log") or [] if m.get("role") == "user" and m.get("text")), "")
    return (" ".join(str(first).split())[:60] or "A chat")


def biggest(agent, limit=12):
    """The biggest single things, biggest first, each one deletable by itself: chats and the files Luma made."""
    from luma.agent import memory_folder
    items = []
    for row in agent.store.all("chat", 400):
        if row.get("thread") == "main":
            continue  # the one running conversation isn't a thing to throw away from here
        last = max((m.get("at") or 0 for m in row.get("log") or []), default=0)
        items.append({"kind": "chat", "id": row["id"], "title": _chat_title(row), "bytes": memory_folder._bytes(row), "when": last or None})
    for row in agent.store.all("file", 2000):
        on_disk = sum(p.stat().st_size for p in memory_folder._file_paths(agent, [row]))
        items.append({"kind": "file", "id": row["id"], "title": str(row.get("title") or row.get("name") or "A file")[:80],
                      "bytes": on_disk + memory_folder._bytes(row), "when": row.get("created")})
    items.sort(key=lambda i: -i["bytes"])
    return items[:limit]


def tidy(agent):
    """After anything is deleted: hand the space back to the device, and let the storage numbers be read fresh."""
    from luma.control import today
    back = agent.store.compact()
    today._SIZES.clear()
    return back


def remove(agent, kind, ident):
    """Delete one chat or one file Luma made. Returns the bytes that came back. Memories go through forget(), which also
    forgets what they meant and what was written from them."""
    from luma.agent import memory_folder
    before = kept_bytes(agent)
    if kind == "file":
        row = agent.store.get("file", str(ident))
        if not row:
            raise ValueError("That file isn't on your Luma anymore.")
        for path in memory_folder._file_paths(agent, [row]):
            path.unlink(missing_ok=True)
        agent.store.delete("file", row["id"])
    elif kind == "chat":
        row = agent.store.get("chat", str(ident))
        if not row or row.get("thread") == "main":
            raise ValueError("That chat isn't on your Luma anymore.")
        thread = row.get("thread")
        if thread in getattr(agent, "threads", {}):
            agent.delete_thread(thread)
        else:
            agent.store.delete("chat", row["id"])
    else:
        raise ValueError("Pick a chat or a file. Memories are forgotten from the memory folder.")
    tidy(agent)
    return {"removed": kind, "freed_bytes": max(0, before - kept_bytes(agent)), **room(agent)}


def more(agent):
    """More room in Luma Cloud, when Luma Cloud says it's there, else None. It's the cloud's one job, it isn't open yet,
    and nothing is bought or moved without the owner's yes."""
    try:
        account = agent.cloud.cached_account() or {}
    except Exception:
        account = {}
    offer = account.get("storage") or {}
    if not offer.get("available"):
        return None
    return {"label": "More room with Luma Cloud", "detail": "Kept sealed, so only your Luma can open it. Nothing moves without your yes.",
            "url": offer.get("url") or None}


def line(state):
    return FULL_LINE if state == "full" else NEARLY_LINE if state == "nearly" else ""


def asked_about_room(agent):
    """ "My memory is full, can I buy more?": the truth about where memories live and how to make room. While more room in
    Luma Cloud isn't open there's nothing to buy, and Luma says so; once it's really on offer, Luma names it, with the yes."""
    state = room(agent)["state"]
    lead = {"full": "It's full right now, so I can't keep new things until there's space. ",
            "nearly": "It's almost full. "}.get(state, "There's room right now. ")
    here = "I keep what you tell me right here on this device, and how much fits is its storage. "
    how = "Make room in the Luma app shows what's taking up space, and you choose what goes."
    if more(agent):
        return here + lead + how + " You can also add room with Luma Cloud. That only happens with your yes."
    return "There's nothing to buy for that. " + here + lead + how


def summary(agent):
    """The storage screen in one call: how full, what's using it, the biggest things, what could go, and the database's
    own check. Kids mode gets nothing personal."""
    if agent.mode == "kids":
        return {"kids": True}
    from luma.agent import memory_folder
    from luma.config import LLAMA_MODEL_PATH
    from luma.control.today import folder_size
    used, lines = agent.store.kept_counts()
    models = folder_size(LLAMA_MODEL_PATH.parent) if LLAMA_MODEL_PATH.parent.is_dir() else 0
    return {**room(agent), "kinds": usage(agent)["kinds"], "luma": models, "biggest": biggest(agent), "options": memory_folder.space(agent)["options"],
            "memories": {"count": used, "lines": lines}, "health": agent.store.health(), "more": more(agent)}


def compact(agent, limit=12000):
    """The same screen, small enough for one sealed relay message (Luma Cloud caps them near 17 KB)."""
    import json
    full_page = summary(agent)
    if full_page.get("kids"):
        return full_page
    cut = lambda text, n: (str(text or "")[:n - 1] + "\u2026") if len(str(text or "")) > n else str(text or "")  # noqa: E731
    out = {k: full_page[k] for k in ("used", "limit", "left", "share", "state", "cap", "luma")}
    out["kinds"] = [{k: kind[k] for k in ("key", "label", "bytes", "count", "how")} for kind in full_page["kinds"]]
    out["biggest"] = [{"kind": b["kind"], "id": b["id"], "title": cut(b["title"], 50), "bytes": b["bytes"]} for b in full_page["biggest"][:8]]
    out["options"] = [{"key": o["key"], "label": o["label"], "bytes": o["bytes"]} for o in full_page["options"]]
    out["health"] = {"ok": full_page["health"]["ok"], "problems": len(full_page["health"]["problems"])}
    out["more"] = bool(full_page["more"])
    while out["biggest"] and len(json.dumps(out)) > limit:
        out["biggest"].pop()
    return out
