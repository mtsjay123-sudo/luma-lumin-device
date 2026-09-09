"""Local household memory, cooking timers, recipes and factual daily briefings.

All records use the existing encrypted Store. This module does not search the
web, invent grocery prices, send messages, or execute a purchase. Timer delivery
requires the runtime to be running; overdue timers are recovered after restart.
"""
from __future__ import annotations

import math
import re
import time
import uuid
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from luma.memory.store import reject_payment_secrets


CATEGORIES = ("pantry", "location", "preference", "manual", "warranty", "maintenance")
MODES = {"friend", "study", "cofounder", "kids"}
TOOL_SPECS = {
    "timers.start": {"description": "Start a named local cooking timer, 1 to 86400 seconds", "fields": {"name": "string", "seconds": "integer"}},
    "timers.list": {"description": "Read named timers and time remaining", "fields": {}},
    "timers.control": {"description": "Pause, resume, cancel or acknowledge an existing timer using its ID or exact name", "fields": {"id": "string", "action": "string"}},
    "household.save": {"description": "Save an explicitly requested household fact; category is pantry, location, preference, manual, warranty or maintenance", "fields": {"category": "string", "title": "string", "details": "string"}},
    "household.find": {"description": "Search saved household facts, pantry notes, manuals and warranties", "fields": {"query": "string"}},
    "cooking.step": {"description": "Control a saved recipe using its ID or exact title; start, next, back, repeat, pause, resume or finish", "fields": {"id": "string", "action": "string"}},
    "briefing.today": {"description": "Read today's saved commitments, unfinished tasks and household follow-ups", "fields": {}},
}


def _text(value, label, maximum=2000, empty=False):
    if not isinstance(value, str) or len(value.strip()) > maximum or (not empty and not value.strip()):
        raise ValueError(f"{label} must be {'optional' if empty else 'nonempty'} text of at most {maximum} characters.")
    result = value.strip()
    reject_payment_secrets(result)
    return result


def _scope(mode):
    if mode not in MODES:
        raise ValueError("Choose friend, study, cofounder or kids mode.")
    return "kids" if mode == "kids" else "adult"


def _url(value):
    value = _text(value, "Source URL", 1500, empty=True)
    if value:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Use a complete HTTPS source URL without embedded credentials.")
    return value


def _duration(seconds):
    seconds = max(0, math.ceil(seconds))
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    pieces = [f"{value} {unit}{'s' if value != 1 else ''}" for value, unit in [(hours, "hour"), (minutes, "minute"), (seconds, "second")] if value]
    return " and ".join(pieces) or "0 seconds"


class Household:
    def __init__(self, store, now=None, zone="America/New_York"):
        self.store = store
        self.clock = now or time.time
        self.zone = ZoneInfo(str(zone))
        self.session = uuid.uuid4().hex
        self.started_at = self._now()

    def _now(self):
        value = float(self.clock())
        if not math.isfinite(value):
            raise ValueError("Clock is unavailable.")
        return value

    def _rows(self, kind, mode):
        scope = _scope(mode)
        return [r for r in self.store.all(kind, 1000) if r.get("scope", "adult") == scope]

    def _resolve(self, kind, identifier, mode):
        identifier = _text(identifier, "Record ID or name", 160)
        row = self.store.get(kind, identifier)
        if row and row.get("scope", "adult") == _scope(mode):
            return row
        label = "name" if kind == "household_timer" else "title"
        matches = [r for r in self._rows(kind, mode) if r.get(label, "").casefold() == identifier.casefold()]
        if kind == "household_timer":
            active = [r for r in matches if r["state"] in {"running", "paused"} or (r["state"] == "elapsed" and not r.get("announced"))]
            matches = active or matches
        if len(matches) == 1:
            return matches[0]
        if matches:
            raise ValueError("More than one saved record has that name. Choose its exact ID.")
        raise ValueError("Saved record not found in this household mode.")

    def _timer_view(self, row, now):
        row = dict(row)
        if row["state"] == "running":
            row["remaining_seconds"] = max(0, math.ceil(row["ends_at"] - now))
            if now >= row["ends_at"]:
                row.update(state="elapsed", elapsed_at=row["ends_at"])
                self.store.put("household_timer", row, row["id"])
        elif row["state"] != "paused":
            row["remaining_seconds"] = 0
        # Compare session IDs rather than mistaking a routine page refresh for a restart.
        row["recovered_after_restart"] = row.get("session") != self.session
        row["elapsed_while_stopped"] = row["recovered_after_restart"] and row["ends_at"] <= self.started_at and row["state"] == "elapsed"
        row["overdue_seconds"] = max(0, int(now - row["ends_at"])) if row["state"] == "elapsed" else 0
        return row

    def timers(self, mode="friend", include_finished=False):
        with self.store.lock:
            rows = [self._timer_view(r, self._now()) for r in self._rows("household_timer", mode)]
            if not include_finished:
                rows = [r for r in rows if r["state"] in {"running", "paused"} or (r["state"] == "elapsed" and not r.get("announced"))]
            return sorted(rows, key=lambda r: (r["state"] != "elapsed", r.get("ends_at") or float("inf"), r["name"].casefold()))

    def start_timer(self, name, seconds, mode="friend"):
        name = _text(name, "Timer name", 80)
        if type(seconds) is not int or not 1 <= seconds <= 86400:
            raise ValueError("Set a timer between 1 second and 24 hours.")
        with self.store.lock:
            active = self.timers(mode)
            if len(active) >= 24:
                raise ValueError("Finish or acknowledge an existing timer before starting another.")
            if any(r["name"].casefold() == name.casefold() for r in active):
                raise ValueError("That timer name is already in use. Choose a different name or finish it first.")
            now = self._now()
            row = self.store.put("household_timer", {"name": name, "duration_seconds": seconds, "remaining_seconds": seconds,
                "state": "running", "started_at": now, "ends_at": now + seconds, "announced": False,
                "session": self.session, "scope": _scope(mode)})
            return self._timer_view(row, now)

    def timer_action(self, id, action, mode="friend"):
        if action not in {"pause", "resume", "cancel", "acknowledge"}:
            raise ValueError("Choose pause, resume, cancel or acknowledge.")
        with self.store.lock:
            now = self._now()
            row = self._timer_view(self._resolve("household_timer", id, mode), now)
            if action == "pause":
                if row["state"] != "running":
                    raise ValueError("Only a running timer can be paused.")
                row.update(state="paused", remaining_seconds=max(0.001, row["ends_at"] - now), paused_at=now)
            elif action == "resume":
                if row["state"] != "paused":
                    raise ValueError("Only a paused timer can be resumed.")
                row.update(state="running", ends_at=now + row["remaining_seconds"], session=self.session)
            elif action == "cancel":
                if row["state"] not in {"running", "paused", "elapsed"}:
                    raise ValueError("That timer is already finished.")
                row.update(state="cancelled", announced=True, finished_at=now)
            else:
                if row["state"] != "elapsed":
                    raise ValueError("Only an elapsed timer can be acknowledged.")
                row.update(announced=True, acknowledged_at=now)
            self.store.put("household_timer", row, row["id"])
            return self._timer_view(row, now)

    def is_quiet(self):
        now = self._now()
        hour = datetime.fromtimestamp(now, self.zone).hour
        hours = self.store.setting("quiet_hours", [23, 7])
        if not isinstance(hours, list) or len(hours) != 2 or any(type(h) is not int or not 0 <= h <= 23 for h in hours):
            hours = [23, 7]
        start, end = hours
        quiet = (hour >= start or hour < end) if start > end else start <= hour < end
        return quiet or now < self.store.setting("hush_until", 0)

    def timer_events(self, mode="friend", deliver=True):
        """Claim due text notifications once per running Store; keep suppressed ones due.

        Quiet hours/hush suppress proactive timer announcements. The timer panel
        always shows elapsed timers, including those that elapsed while stopped.
        """
        with self.store.lock:
            rows = [r for r in self.timers(mode) if r["state"] == "elapsed" and not r.get("announced")]
            if not deliver or self.is_quiet():
                return []
            events = []
            for row in rows:
                row.update(announced=True, announced_at=self._now())
                self.store.put("household_timer", row, row["id"])
                suffix = " It elapsed while Luma was not running." if row["elapsed_while_stopped"] else ""
                events.append({"type": "timer", "id": row["id"], "name": row["name"], "text": f"Your {row['name']} timer is done.{suffix}",
                    "recovered_after_restart": row["recovered_after_restart"], "elapsed_while_stopped": row["elapsed_while_stopped"], "overdue_seconds": row["overdue_seconds"]})
            return events

    def save_record(self, category, title, details, id=None, source_url="", due_date="", mode="friend"):
        if category not in CATEGORIES:
            raise ValueError("Choose pantry, location, preference, manual, warranty or maintenance.")
        value = {"category": category, "title": _text(title, "Title", 160), "details": _text(details, "Details", 12000),
                 "source_url": _url(source_url), "due_date": _text(due_date, "Due date", 10, empty=True), "scope": _scope(mode)}
        if due_date:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due_date):
                raise ValueError("Use a YYYY-MM-DD due date.")
            date.fromisoformat(due_date)
        with self.store.lock:
            if id:
                old = self._resolve("household_record", id, mode)
                id = old["id"]
                value["created_at"] = old.get("created_at", self._now())
            else:
                value["created_at"] = self._now()
            value["updated_at"] = self._now()
            return self.store.put("household_record", value, id)

    def records(self, category=None, query="", mode="friend"):
        if category is not None and category not in CATEGORIES:
            raise ValueError("Unknown household category.")
        query = _text(query, "Search", 500, empty=True)
        terms = set(re.findall(r"\w+", query.casefold()))
        rows = [r for r in self._rows("household_record", mode) if category is None or r["category"] == category]
        if terms:
            def score(row):
                words = set(re.findall(r"\w+", (row["title"] + " " + row["details"] + " " + row["category"]).casefold()))
                return len(terms & words)
            rows = [r for r in rows if score(r)]
            rows.sort(key=lambda r: (-score(r), -r.get("updated_at", 0)))
        return rows

    def delete_record(self, id, mode="friend"):
        with self.store.lock:
            row = self._resolve("household_record", id, mode)
            return self.store.delete("household_record", row["id"])

    def save_recipe(self, title, steps, ingredients=None, source_url="", id=None, mode="friend"):
        title = _text(title, "Recipe title", 160)
        if not isinstance(steps, list) or not 1 <= len(steps) <= 80:
            raise ValueError("A recipe needs between 1 and 80 steps.")
        steps = [_text(step, "Recipe step", 2000) for step in steps]
        if ingredients is None:
            ingredients = []
        if not isinstance(ingredients, list) or len(ingredients) > 100:
            raise ValueError("Use up to 100 ingredient notes.")
        ingredients = [_text(item, "Ingredient", 300) for item in ingredients]
        value = {"title": title, "steps": steps, "ingredients": ingredients, "source_url": _url(source_url), "scope": _scope(mode),
                 "state": "saved", "step_index": 0, "updated_at": self._now()}
        with self.store.lock:
            if id:
                old = self._resolve("household_recipe", id, mode)
                id = old["id"]
                # Editing an active recipe does not silently move the cooking cursor.
                value.update(state=old["state"], step_index=min(old["step_index"], len(steps) - 1))
            return self._recipe_view(self.store.put("household_recipe", value, id))

    @staticmethod
    def _recipe_view(row):
        return {**row, "step_number": row["step_index"] + 1, "step_count": len(row["steps"]), "current_step": row["steps"][row["step_index"]]}

    def recipes(self, mode="friend"):
        return [self._recipe_view(row) for row in self._rows("household_recipe", mode)]

    def delete_recipe(self, id, mode="friend"):
        with self.store.lock:
            row = self._resolve("household_recipe", id, mode)
            return self.store.delete("household_recipe", row["id"])

    def recipe_action(self, id, action, mode="friend"):
        if action not in {"start", "next", "back", "repeat", "pause", "resume", "finish"}:
            raise ValueError("Choose start, next, back, repeat, pause, resume or finish.")
        with self.store.lock:
            row = self._resolve("household_recipe", id, mode)
            if action == "start":
                row.update(state="cooking", step_index=0)
            elif action == "resume":
                if row["state"] != "paused":
                    raise ValueError("Only a paused recipe can be resumed.")
                row["state"] = "cooking"
            elif action == "pause":
                if row["state"] != "cooking":
                    raise ValueError("Start the recipe before pausing it.")
                row["state"] = "paused"
            elif action == "finish":
                if row["state"] not in {"cooking", "paused"}:
                    raise ValueError("Start the recipe before finishing it.")
                row.update(state="finished", finished_at=self._now())
            elif action in {"next", "back"}:
                if row["state"] != "cooking":
                    raise ValueError("Start or resume the recipe to change steps.")
                step = row["step_index"] + (1 if action == "next" else -1)
                if not 0 <= step < len(row["steps"]):
                    raise ValueError("This is the last step. Mark the recipe finished when ready." if action == "next" else "You are already at the first step.")
                row["step_index"] = step
            row["updated_at"] = self._now()
            self.store.put("household_recipe", row, row["id"])
            return self._recipe_view(row)

    def briefing(self, mode="friend", proactive=False):
        """Use only recorded facts. User-requested reads remain available at night."""
        scope = _scope(mode)
        with self.store.lock:
            now = self._now()
            local = datetime.fromtimestamp(now, self.zone)
            day = local.date().isoformat()
            key = "household_briefing_day:" + scope
            if proactive and (self.is_quiet() or self.store.setting(key) == day):
                return None
            tomorrow = datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), self.zone).timestamp()
            def visible(row):
                return _scope(row.get("mode", "friend")) == scope
            unfinished = [r for r in self.store.all("task", 1000) if not r.get("done") and visible(r)]
            due = sorted([r for r in unfinished if r.get("due", float("inf")) < tomorrow], key=lambda r: r["due"])
            routines = sorted([r for r in self.store.all("routine", 1000) if r.get("enabled") and visible(r) and r.get("last_day") != day], key=lambda r: r.get("at", ""))
            followups = [r for r in self.records(mode=mode) if r.get("due_date") and r["due_date"] <= day]
            timers = self.timers(mode)
            parts = []
            if due:
                parts.append("Due by today: " + "; ".join(r["title"] for r in due[:5]) + ".")
            if routines:
                parts.append("Today's routines: " + "; ".join(f"{r['title']} at {r['at']}" for r in routines[:5]) + ".")
            if followups:
                parts.append("Household follow-ups: " + "; ".join(r["title"] for r in followups[:5]) + ".")
            if timers:
                parts.append(f"You have {len(timers)} active or unacknowledged timer{'s' if len(timers) != 1 else ''}.")
            if not parts:
                parts.append("There are no saved commitments due today or household follow-ups.")
            if len(unfinished) > len(due):
                later = len(unfinished) - len(due)
                parts.append(f"{later} other unfinished reminder{'s' if later != 1 else ''} are saved for later.")
            if proactive and not (due or routines or followups or timers):
                return None
            if proactive:
                self.store.set_setting(key, day)
            return {"type": "briefing", "date": day, "time_zone": str(self.zone), "text": " ".join(parts),
                    "tasks": due[:20], "unfinished_count": len(unfinished), "routines": routines[:20],
                    "followups": followups[:20], "timers": timers, "scope": "Saved local records; external calendars and store prices are not included."}

    def run(self, name, args, mode="friend"):
        """Small adapter for the existing runtime Tool registry."""
        if name not in TOOL_SPECS or not isinstance(args, dict) or set(args) != set(TOOL_SPECS[name]["fields"]):
            raise ValueError("Household tool arguments do not match the declared fields.")
        if name == "timers.start":
            row = self.start_timer(**args, mode=mode)
            return {"timer": row, "summary": f"Your {row['name']} timer is running for {_duration(row['duration_seconds'])}."}
        if name == "timers.list":
            rows = self.timers(mode)
            descriptions = [f"{r['name']}: {_duration(r['remaining_seconds'])} left{' (paused)' if r['state'] == 'paused' else ''}" if r["state"] != "elapsed" else f"{r['name']}: done" for r in rows]
            return {"timers": rows, "summary": "; ".join(descriptions) + "." if rows else "You don't have any active timers."}
        if name == "timers.control":
            row = self.timer_action(**args, mode=mode)
            state = "acknowledged" if args["action"] == "acknowledge" else row["state"]
            return {"timer": row, "summary": f"Your {row['name']} timer is {state}."}
        if name == "household.save":
            return {"record": self.save_record(**args, mode=mode), "summary": "Household note saved locally. You can edit or delete it in Household."}
        if name == "household.find":
            rows = self.records(**args, mode=mode)
            summary = " ".join(f"{r['title']}: {r['details'][:400]}" for r in rows[:3]) if rows else "I couldn't find a saved household note matching that."
            return {"records": rows, "summary": summary}
        if name == "cooking.step":
            row = self.recipe_action(**args, mode=mode)
            summary = f"Step {row['step_number']} of {row['step_count']}: {row['current_step']}"
            if args["action"] == "pause":
                summary = f"{row['title']} is paused at step {row['step_number']}. Say resume when you're ready."
            elif args["action"] == "finish":
                summary = f"{row['title']} is marked finished. Enjoy your food."
            return {"recipe": row, "summary": summary}
        return self.briefing(mode=mode)

    def command(self, text, mode="friend"):
        """Fast paths for explicit cooking commands; None leaves general chat alone."""
        if not isinstance(text, str):
            return None
        text = re.sub(r"[.!?]+$", "", text.strip())
        timer = re.fullmatch(r"(?:please )?(?:set|start) (?:a |an )?(?:(.+?) )?timer for (\d+) (seconds?|minutes?|hours?)(?: (?:called|named) (.+))?", text, re.I)
        if timer:
            before, amount, unit, after = timer.groups()
            seconds = int(amount) * (3600 if unit.lower().startswith("hour") else 60 if unit.lower().startswith("minute") else 1)
            name = after or before or "Cooking"
            return self.run("timers.start", {"name": name, "seconds": seconds}, mode)
        control = re.fullmatch(r"(?:please )?(pause|resume|cancel|acknowledge) (?:my |the )?(.+?) timer", text, re.I)
        if control:
            return self.run("timers.control", {"id": control[2], "action": control[1].lower()}, mode)
        if re.fullmatch(r"(?:(?:show|list) (?:my |the )?)?timers", text, re.I):
            return self.run("timers.list", {}, mode)
        if re.fullmatch(r"(?:(?:show|give|read) me (?:my |a )?)?(?:daily briefing|today's briefing|my briefing)", text, re.I):
            return self.briefing(mode)
        step = re.fullmatch(r"(?:please )?(next step|previous step|repeat (?:that|the step)|pause (?:the )?recipe|resume (?:the )?recipe)", text, re.I)
        if step:
            active = [r for r in self.recipes(mode) if r["state"] in {"cooking", "paused"}]
            if len(active) != 1:
                return {"text": "Choose the recipe in Cooking so I know which one you mean.", "section": "household"}
            action = "next" if text.lower().endswith("next step") else "back" if "previous" in text.lower() else "repeat" if "repeat" in text.lower() else "pause" if "pause" in text.lower() else "resume"
            return self.run("cooking.step", {"id": active[0]["id"], "action": action}, mode)
        return None
