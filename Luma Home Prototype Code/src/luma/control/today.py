"""Today: everything the phone app's home screen shows, in one call.

Today's chat chains (the rest after), the newest memories for the memory deck, the device itself (storage
left and what Luma uses of it, the mic, the brain, whether a computer is connected), projects in motion, and
how many things are waiting for a yes. One request matters when the phone is reaching home through the relay.
"""
from __future__ import annotations

import json
import os
import time
import shutil
from datetime import datetime
from pathlib import Path

GB = 2 ** 30


_SIZES = {}  # path -> (when, bytes): the phone asks every 15 seconds, folders don't change that fast
SIZE_TTL = 600


def folder_size(path, limit=200_000):
    """Bytes in a folder, stopping after `limit` files so a huge folder can't stall the phone. Remembered for ten minutes."""
    key = str(path)
    hit = _SIZES.get(key)
    if hit and time.monotonic() - hit[0] < SIZE_TTL:
        return hit[1]
    size = _walk_size(path, limit)
    _SIZES[key] = (time.monotonic(), size)
    return size


def _walk_size(path, limit):
    total, seen = 0, 0
    try:
        for root, _dirs, files in os.walk(path):
            for name in files:
                try:
                    total += os.lstat(os.path.join(root, name)).st_size
                except OSError:
                    pass
                seen += 1
                if seen >= limit:
                    return total
    except OSError:
        pass
    return total


def storage(agent):
    """Disk space on the device's data drive, and what Luma itself takes up of it."""
    from luma.config import LLAMA_MODEL_PATH
    data = Path(agent.store.db_path).parent
    try:
        disk = shutil.disk_usage(data)
    except OSError:
        return None
    models = folder_size(LLAMA_MODEL_PATH.parent) if LLAMA_MODEL_PATH.parent.is_dir() else 0
    files = folder_size(agent.files_dir) if agent.files_dir.is_dir() else 0
    db = sum(p.stat().st_size for p in data.glob(Path(agent.store.db_path).name + "*") if p.is_file())
    free = disk.free / GB
    return {"unit": "GB", "total": round(disk.total / GB, 1), "free": round(free, 1), "used": round((disk.total - disk.free) / GB, 1),
            "luma": {"models": round(models / GB, 2), "data": round(db / GB, 3), "files": round(files / GB, 2)},
            "low": disk.free / max(1, disk.total) < 0.10}


def chats(agent, limit=12):
    """Chat chains, today's first, each with its last line so the list reads like a messages app."""
    midnight = datetime.fromtimestamp(agent.clock(), agent.zone).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    rows = []
    for t in agent.thread_list():
        log = agent.transcripts.get(t["id"]) or []
        last = next((m for m in reversed(log) if m.get("text")), None)
        rows.append({**t, "today": bool(t.get("updated") and t["updated"] >= midnight),
                     "today_messages": sum(1 for m in log if m.get("at", 0) >= midnight),
                     "last": {"role": last.get("role"), "text": " ".join(str(last.get("text", "")).split())[:140]} if last else None})
    rows.sort(key=lambda r: -(r.get("updated") or 0))
    return rows[:limit]


# First match wins: a birthday is a date even if it mentions mom; a savings goal is a plan even if it names a month.
KINDS = (("Dates", ("birthday", "anniversary", "every year")),
         ("Plans", ("saving", "trip", "plan", "goal", "want to", "going to", "training for")),
         ("Dates", ("january", "february", "march", "april", "may ", "june", "july", "august", "september", "october", "november", "december")),
         ("Places", ("where", "drawer", "keys", "parked", "lives in", "address", "street", "on peachtree", "kitchen", "closet")),
         ("Likes", ("love", "like", "hate", "favorite", "prefer", "can't stand", "allergic", "coffee", "food")),
         ("People", ("mom", "dad", "sister", "brother", "wife", "husband", "girlfriend", "boyfriend", "friend", "boss", "son", "daughter", "dr.")),
         ("Health", ("gym", "workout", "doctor", "dentist", "medicine", "sleep")))


def kind_of(text):
    low = " " + text.lower() + " "
    return next((name for name, words in KINDS if any(w in low for w in words)), "Notes")


def memory(agent, deck=24):
    quota = agent.memory_quota()
    recent = []
    for m in agent.store.all("memory", deck):
        text = " ".join(str(m.get("text", "")).split())
        if text:
            recent.append({"id": m.get("id"), "text": text[:280], "kind": kind_of(text), "when": m.get("created") or m.get("at") or m.get("saved")})
    return {**quota, "recent": recent}


def device(agent):
    from luma.llm import brain
    host = getattr(agent, "link_host", None)
    peers = host.peers() if host else []
    paired = agent.link.device() if getattr(agent, "link", None) else None
    try:
        thinking = brain.status().get("thinking_with")
    except Exception:
        thinking = None
    return {"storage": storage(agent), "mic": "off" if agent.muted else "on", "speaking": bool(agent.speaking), "busy": bool(agent.busy),
            "brain": thinking, "computer": {"paired": bool(peers), "here": bool(host and host.connected()), "name": (peers[0].get("name") if peers else None),
                         "recent": host.recent(3) if host else []},
            "device": {"name": (paired or {}).get("name")} if paired else None}


def projects(agent, limit=4):
    try:
        from luma.control import work_api
        eng = work_api.engine(agent)
        out = []
        for p in eng.projects.list()[:limit]:
            v = work_api.view(eng, p)
            run = v.get("run") or {}
            steps = run.get("steps") or []
            out.append({"id": v["id"], "name": v["name"], "state": "running" if v["working"] else run.get("state") or "new",
                        "done": sum(1 for s in steps if s.get("state") == "done"), "steps": len(steps), "updated": v.get("updated")})
        return out
    except Exception:
        return []


def payload(agent):
    """GET /api/today. Kids mode gets the time of day and nothing personal."""
    if agent.mode == "kids":
        return {"kids": True, "name": "", "chats": [], "memory": None, "device": None, "projects": [], "approvals": 0}
    waiting = sum(1 for r in agent.store.all("action", 40) if r.get("state") == "pending")
    return {"name": (agent.profile.get("name") or "").split(" ")[0], "now": agent.clock(), "chats": chats(agent), "memory": memory(agent),
            "device": device(agent), "projects": projects(agent), "approvals": waiting}


def compact(agent):
    """The same day, small enough for one sealed relay message (Luma Cloud caps them near 17 KB)."""
    full = payload(agent)
    if full.get("kids"):
        return full
    cut = lambda text, n: (str(text or "")[:n - 1] + "\u2026") if len(str(text or "")) > n else str(text or "")
    chats_ = [{"id": c.get("id"), "title": cut(c.get("title"), 60), "updated": c.get("updated"), "today": c.get("today"),
               "last": {"role": (c.get("last") or {}).get("role"), "text": cut((c.get("last") or {}).get("text"), 120)}} for c in full["chats"][:8]]
    mem = full["memory"] or {}
    memory_ = {k: mem.get(k) for k in ("used", "limit", "plan") if k in mem}
    memory_["recent"] = [{"id": m.get("id"), "text": cut(m.get("text"), 140), "kind": m.get("kind"), "when": m.get("when")} for m in (mem.get("recent") or [])[:12]]
    dev = full["device"] or {}
    device_ = {"storage": dev.get("storage"), "mic": dev.get("mic"), "brain": dev.get("brain"),
               "computer": {k: (dev.get("computer") or {}).get(k) for k in ("paired", "here", "name")}}
    projects_ = [{"name": cut(p.get("name"), 60), "state": p.get("state"), "done": p.get("done"), "steps": p.get("steps")} for p in full["projects"][:4]]
    return {"name": full["name"], "now": full["now"], "chats": chats_, "chats_today": sum(1 for c in full["chats"] if c.get("today")),
            "memory": memory_, "device": device_, "projects": projects_, "approvals": full["approvals"]}


def chain(agent, thread_id, keep=30, limit=14000):
    """One chat chain for the phone: its title and last messages, small enough for one sealed relay message."""
    match = next((t for t in agent.thread_list() if t.get("id") == thread_id), None)
    if not match:
        raise ValueError("That chat isn't on your Luma anymore.")
    log = [m for m in (agent.transcripts.get(thread_id) or []) if m.get("text")][-keep:]
    out = {"id": thread_id, "title": str(match.get("title") or "Chat")[:80],
           "messages": [{"role": m.get("role"), "text": str(m.get("text"))[:700], "at": m.get("at")} for m in log]}
    while out["messages"] and len(json.dumps(out)) > limit:
        out["messages"].pop(0)  # the oldest go first
    return out
