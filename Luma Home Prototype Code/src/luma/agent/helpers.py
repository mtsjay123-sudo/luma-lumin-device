"""Luma's always-on work: helpers that run on a schedule, the feed they fill, and ideas.

A helper is a small standing job the owner set up ("watch the price of AirPods
Pro 2 and tell me under $180", "go through my inbox every morning", "catch me
up on Instagram at 6"). Helpers only read and prepare. Anything that would
send, post or spend becomes an approval card, exactly as if the owner had asked
in chat. Each run leaves a card in the feed; only news worth a buzz notifies.
"""
from __future__ import annotations

import re
import threading
from collections import deque
from datetime import datetime, timedelta

EVERY = {"hourly": 3600, "every_6h": 6 * 3600, "daily": 86400, "weekly": 7 * 86400}
KINDS = {
    "price_watch": "Price watch",
    "inbox_digest": "Inbox check",
    "feed_digest": "Feed catch-up",
    "agenda": "Morning agenda",
    "goal": "Goal",
    "ideas": "Ideas",
    "news": "News",
    "reflect": "Reflection",
}
FEED_KEEP = 200


class Feed:
    """Cards Luma leaves for the owner: deals, inbox summaries, feed catch-ups, updates."""

    def __init__(self, store, clock):
        self.store = store
        self.clock = clock

    def add(self, card):
        from luma.memory.store import mask_long_numbers
        card = mask_long_numbers(card)
        card = {"kind": card.get("kind", "update"), "title": str(card.get("title") or "")[:160], "body": str(card.get("body") or "")[:1600],
                "items": card.get("items") or [], "url": card.get("url"), "helper": card.get("helper"), "action": card.get("action"),
                "created": self.clock(), "read": False, "feedback": None}
        try:
            row = self.store.put("card", card)
        except ValueError:
            row = self.store.put("card", {**card, "items": [], "body": "(Some of this looked like a card number, so I left it out.)"})
        for old in self.store.all("card", FEED_KEEP + 40)[FEED_KEEP:]:
            self.store.delete("card", old["id"])
        return row

    def list(self, limit=40):
        return self.store.all("card", limit)

    def mark_read(self, ident):
        row = self.store.get("card", str(ident))
        if not row:
            raise ValueError("That card is gone.")
        row["read"] = True
        return self.store.put("card", row, row["id"])

    def delete(self, ident):
        return self.store.delete("card", str(ident))


class Helpers:
    def __init__(self, agent):
        self.agent = agent
        self.store = agent.store
        self.events = deque(maxlen=20)
        self.thread = None
        self.lock = threading.Lock()

    # -- set up ----------------------------------------------------------------
    def list(self):
        rows = [r for r in self.store.all("helper", 60) if not r.get("system")]
        return sorted(rows, key=lambda r: r.get("created", 0))

    def _next_run(self, row, after):
        every = EVERY[row["every"]]
        if row.get("at") and row["every"] in {"daily", "weekly"}:
            hour, minute = map(int, row["at"].split(":"))
            local = datetime.fromtimestamp(after, self.agent.zone)
            when = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
            while when.timestamp() <= after:
                when += timedelta(days=1 if row["every"] == "daily" else 7)
            return when.timestamp()
        return after + every

    def create(self, kind, title=None, params=None, every="daily", at=None, system=False, run_now=True):
        if self.agent.mode == "kids":
            raise ValueError("Helpers are available in adult mode.")
        if kind not in KINDS:
            raise ValueError("Choose a price watch, inbox check, feed catch-up, agenda or goal.")
        if every not in EVERY:
            raise ValueError("Choose hourly, every 6 hours, daily or weekly.")
        if at is not None and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(at)):
            raise ValueError("Use a time like 07:30.")
        params = dict(params or {})
        if kind == "price_watch":
            query = " ".join(str(params.get("query") or "").split())[:120]
            if len(query) < 2:
                raise ValueError("Tell me what to watch the price of.")
            target = params.get("target")
            target = float(target) if target not in (None, "", 0) else None
            if target is not None and not 0 < target < 100000:
                raise ValueError("Pick a target price between $1 and $100,000.")
            params = {"query": query, "target": target}
            title = title or f"Price of {query}" + (f" under ${target:,.0f}" if target else "")
        elif kind == "feed_digest":
            site = str(params.get("site") or "instagram").lower()
            if site not in self.agent.FEEDS:
                raise ValueError("Pick Instagram, TikTok, X, Facebook, Reddit, LinkedIn or YouTube.")
            params = {"site": site}
            title = title or f"Catch me up on {self.agent.FEEDS[site][0]}"
        elif kind == "goal":
            goal = " ".join(str(params.get("goal") or "").split())
            if not 3 <= len(goal) <= 500:
                raise ValueError("Describe the goal in a sentence.")
            params = {"goal": goal}
            title = title or goal[:80]
        elif kind == "inbox_digest":
            title = title or "Go through my inbox"
        elif kind == "agenda":
            title = title or "My day, every morning"
        elif kind == "ideas":
            title = title or "Ideas for me"
        elif kind == "news":
            title = title or "Read the news"
        elif kind == "reflect":
            title = title or "Reflect on us"
        now = self.agent.clock()
        row = {"kind": kind, "title": str(title)[:120], "params": params, "every": every, "at": at, "enabled": True, "system": system,
               "created": now, "last_run": None, "last_result": None, "last_error": None, "runs": 0, "history": [], "seen": [], "low": None}
        row["next_run"] = now + 2 if run_now else self._next_run(row, now)
        return self.store.put("helper", row)

    def update(self, ident, **changes):
        row = self.store.get("helper", str(ident))
        if not row:
            raise ValueError("That helper is gone.")
        if "enabled" in changes:
            row["enabled"] = bool(changes["enabled"])
            if row["enabled"]:
                row["next_run"] = self._next_run(row, self.agent.clock())
        if changes.get("run_now"):
            row["enabled"] = True
            row["next_run"] = self.agent.clock()
        if changes.get("every") in EVERY:
            row["every"] = changes["every"]
            row["next_run"] = self._next_run(row, self.agent.clock())
        return self.store.put("helper", row, row["id"])

    def delete(self, ident):
        return self.store.delete("helper", str(ident))

    def ensure_system(self):
        """The daily ideas pass, so the Ideas tab has fresh things to suggest."""
        if not any(r.get("kind") == "ideas" for r in self.store.all("helper", 60)):
            self.create("ideas", every="daily", at="07:20", system=True, run_now=False)
        # Read the news every hour, so Luma knows what happened after its training (and re-reads on the spot when asked).
        reader = next((r for r in self.store.all("helper", 60) if r.get("kind") == "news"), None)
        if not reader:
            self.create("news", every="hourly", system=True, run_now=True)
        elif reader.get("every") != "hourly":
            self.update(reader["id"], every="hourly")
        # Every night, Luma reflects on its conversations and rewires its sense of itself.
        if not any(r.get("kind") == "reflect" for r in self.store.all("helper", 60)):
            self.create("reflect", every="daily", at="03:30", system=True, run_now=False)

    # -- running ---------------------------------------------------------------
    def due(self, now):
        return [r for r in self.store.all("helper", 60) if r.get("enabled") and r.get("next_run", 0) <= now]

    def start_due(self):
        """Called from the clock. Runs at most one helper at a time, never over the owner."""
        if self.agent.mode == "kids" or self.agent.busy or self.agent.activity.busy():
            return None
        with self.lock:
            if self.thread and self.thread.is_alive():
                return None
            due = self.due(self.agent.clock())
            if not due:
                return None
            row = sorted(due, key=lambda r: r["next_run"])[0]
            self.thread = threading.Thread(target=self.run, args=(row["id"],), name="luma-helper", daemon=True)
            self.thread.start()
            return row["id"]

    def run(self, ident):
        from luma.agent.activity import Stopped
        row = self.store.get("helper", ident)
        if not row:
            return None
        now = self.agent.clock()
        try:
            outcome = getattr(self, "_run_" + row["kind"])(row)
        except Stopped:
            row = self.store.get("helper", ident) or row
            row["next_run"] = self.agent.clock() + 900  # gave way to the owner; try again soon
            self.store.put("helper", row, ident)
            return None
        except Exception as error:  # a helper failing shouldn't stop the others
            row = self.store.get("helper", ident) or row
            row.update(last_run=now, last_error=str(error)[:240], next_run=self._next_run(row, self.agent.clock()))
            self.store.put("helper", row, ident)
            return {"error": str(error)}
        row = self.store.get("helper", ident) or row
        row.update(outcome.get("state", {}))
        row.update(last_run=now, last_error=None, runs=row.get("runs", 0) + 1, next_run=self._next_run(row, self.agent.clock()),
                   last_result=(outcome.get("card") or {}).get("title"))
        self.store.put("helper", row, ident)
        card = self.agent.feed.add({**outcome["card"], "helper": ident}) if outcome.get("card") else None
        if outcome.get("notify"):
            self.events.append({"type": "helper", "text": outcome["notify"], "created": self.agent.clock(), "card": card["id"] if card else None})
        return outcome

    def pop_event(self):
        try:
            return self.events.popleft()
        except IndexError:
            return None

    # -- the kinds -------------------------------------------------------------
    def _run_price_watch(self, row):
        from luma.skills import shopping
        query, target = row["params"]["query"], row["params"].get("target")
        result = self.agent.shop(query, background=True)
        best = result.get("best")
        state = {}
        if not best:
            return {"card": {"kind": "deal", "title": f"No match for {query} right now", "body": result["text"]}, "state": state}
        history = (row.get("history") or [])[-29:] + [{"at": self.agent.clock(), "price": best["price"], "store": best["store"]}]
        low = row.get("low")
        state = {"history": history, "low": best["price"] if low is None else min(low, best["price"])}
        line = f"{best['title'][:70]} is {shopping.money(best['price'])} at {best['store']}"
        notify = None
        if target and best["price"] <= target and row.get("alerted_price") != best["price"]:
            notify = f"Price drop: {line}, under your ${target:,.0f} target."
            state["alerted_price"] = best["price"]
        elif low is not None and best["price"] < low - 0.009:
            notify = f"New low: {line} (was {shopping.money(low)})."
        title = f"{query}: {shopping.money(best['price'])} at {best['store']}"
        return {"card": {"kind": "deal", "title": title, "body": result["text"], "items": result["offers"][:6], "url": best.get("url")},
                "notify": notify, "state": state}

    def _run_inbox_digest(self, row):
        mail = self.agent.mail
        messages = mail.inbox(limit=15, unread_only=True)
        seen = set(row.get("seen") or [])
        fresh = [m for m in messages if m["id"] not in seen]
        state = {"seen": (list(seen) + [m["id"] for m in fresh])[-300:]}
        if not messages:
            return {"card": {"kind": "inbox", "title": "Inbox zero", "body": "No unread email right now."}, "state": state}
        body = self.agent.summarize_mail(messages)
        items = [{"title": m["subject"], "from": m["from"], "snippet": m["snippet"], "id": m["id"], "date": m["date"]} for m in messages[:8]]
        notify = (f"{len(fresh)} new email{'s' if len(fresh) != 1 else ''}. " + body)[:300] if fresh else None
        return {"card": {"kind": "inbox", "title": f"{len(messages)} unread email{'s' if len(messages) != 1 else ''}", "body": body, "items": items},
                "notify": notify, "state": state}

    def _run_feed_digest(self, row):
        import threading as _threading
        site = row["params"]["site"]
        label = self.agent.FEEDS[site][0]
        with self.agent.lock:
            result = self.agent.check_feed(site, f"What's new on my {label}?", _threading.Event())
        return {"card": {"kind": "feed", "title": f"Your {label}", "body": result.get("text", ""), "url": result.get("url")}}

    def _run_agenda(self, row):
        text = self.agent.briefing_text()
        return {"card": {"kind": "today", "title": datetime.fromtimestamp(self.agent.clock(), self.agent.zone).strftime("%A, %B %-d"), "body": text},
                "notify": text}

    def _run_goal(self, row):
        import threading as _threading
        goal = row["params"]["goal"]
        if not self.agent.use_model:
            return {"card": {"kind": "update", "title": goal[:80], "body": "Turn on the local model and I'll work on this goal for you."}}
        self.agent.activity.start("goal", goal[:80], background=True)
        try:
            with self.agent.lock:
                result = self.agent.workflows.run(goal, _threading.Event())
        finally:
            self.agent.activity.finish("Done for now.")
        text = result.get("text") or result.get("summary") or "I made some progress."
        card = {"kind": "approval" if result.get("state") == "pending" else "update", "title": goal[:80], "body": text}
        if result.get("state") == "pending":
            card["action"] = result.get("action")
        return {"card": card, "notify": text[:240]}

    def _run_news(self, row):
        from luma.skills import news
        result = self.agent.read_news(force=True)
        today = datetime.fromtimestamp(self.agent.clock(), self.agent.zone).date().isoformat()
        if not result.get("items") or row.get("carded") == today:
            return {}
        # Once a day, the morning's biggest stories as a card in the feed.
        picks = news.top(result["items"], 6)
        body = "\n".join(f"{p['source']}: {p['title']}" for p in picks)
        return {"card": {"kind": "update", "title": "Today's news", "body": body, "items": [], "url": picks[0]["url"] if picks else None},
                "state": {"carded": today}}

    def _run_reflect(self, row):
        if self.agent.use_model:
            self.agent.reflect_self()
        return {}

    def _run_ideas(self, row):
        items = self.agent.model_ideas()
        if items:
            self.store.set_setting("ideas_model", {"day": datetime.fromtimestamp(self.agent.clock(), self.agent.zone).date().isoformat(), "items": items})
        return {}
