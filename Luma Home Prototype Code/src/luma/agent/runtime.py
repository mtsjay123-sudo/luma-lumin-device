"""Durable local agent with explicit, inspectable tool actions.

The language model may propose a tool call; it cannot confirm actions or enable
integrations. Only the owner's CLI/API control path can do those things.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from luma.config import STATE_DB_PATH, STATE_KEY_PATH
from luma.memory.store import Store, reject_payment_secrets
from luma.integrations.providers import Providers, ProviderError, OutcomeUnknown


@dataclass(frozen=True)
class Tool:
    description: str
    fields: dict
    service: str | None = None
    confirm: bool = False
    kids: bool = False


TOOLS = {
    "memory.remember": Tool("Save an explicitly requested personal memory locally", {"text": "string"}),
    "memory.recall": Tool("Find saved memories", {"query": "string"}),
    "tasks.create": Tool("Save a reminder with an ISO 8601 due date including time zone", {"title": "string", "due": "string"}, kids=True),
    "tasks.list": Tool("List unfinished reminders", {}, kids=True),
    "tasks.complete": Tool("Mark a reminder complete", {"id": "string"}, kids=True),
    "routines.create": Tool("Schedule a daily local reminder at HH:MM", {"title": "string", "at": "string"}, kids=True),
    "web.search": Tool("Search the live web with cited links; price results are not quotes", {"query": "string"}, "web_search", False),
    "sms.send": Tool("Send the exact text to an E.164 phone number using Twilio", {"to": "string", "body": "string"}, "sms", True),
    "home.light": Tool("Control a configured Home Assistant light", {"entity_id": "string", "state": "string", "brightness": "integer"}, "home_assistant", True),
    "food.checkout": Tool("Prepare a shopping list and merchant checkout handoff; does not purchase", {"merchant": "string", "items": "string", "budget_cents": "integer"}, "shopping", True),
}


def validate(name, args):
    if name not in TOOLS: raise ValueError("Unknown tool.")
    if not isinstance(args, dict) or set(args) != set(TOOLS[name].fields):
        raise ValueError("Tool arguments must match its declared fields exactly.")
    for key, typ in TOOLS[name].fields.items():
        val = args[key]
        if typ == "string" and (not isinstance(val, str) or not val.strip() or len(val) > 2000):
            raise ValueError(f"{key} must be nonempty text of at most 2000 characters.")
        if typ == "integer" and (type(val) is not int or val < 0): raise ValueError(f"{key} must be a nonnegative integer.")
    reject_payment_secrets(args)
    if name == "sms.send":
        if not re.fullmatch(r"\+[1-9]\d{7,14}", args["to"]): raise ValueError("Use an exact E.164 recipient such as +19195550123.")
        if len(args["body"]) > 1000: raise ValueError("SMS text must be at most 1000 characters.")
    if name == "home.light":
        if not re.fullmatch(r"light\.[a-z0-9_]+", args["entity_id"]) or args["state"] not in {"on", "off"} or args["brightness"] > 100:
            raise ValueError("Only named lights, on/off and brightness 0–100 are supported.")
    if name == "tasks.create":
        due = datetime.fromisoformat(args["due"].replace("Z", "+00:00"))
        if due.tzinfo is None: raise ValueError("Due date must include a time zone or UTC offset.")
    if name == "routines.create" and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", args["at"]):
        raise ValueError("Routine time must be HH:MM in 24-hour time.")
    if name == "food.checkout" and not 100 <= args["budget_cents"] <= 100000:
        raise ValueError("Set a checkout budget between $1 and $1,000, in cents.")


class Agent:
    def __init__(self, store=None, providers=None, planner=None, use_model=True, now=None):
        self.store = store or Store(STATE_DB_PATH, STATE_KEY_PATH)
        self.providers = providers or Providers()
        self.planner = planner
        self.use_model = use_model
        self.clock = now or time.time
        self.lock = threading.RLock()
        self.history = []  # conversations are RAM-only; explicit memories persist
        self.speaking = False
        self.zone = ZoneInfo(self.providers.env.get("LUMA_TIMEZONE", "America/New_York"))
        # A new process starts with the microphone muted, even after a crash.
        self.store.set_setting("muted", True)

    @property
    def mode(self): return self.store.setting("mode", "friend")
    @property
    def muted(self): return self.store.setting("muted", True)

    def set_mode(self, mode):
        if mode not in {"friend", "study", "cofounder", "kids"}: raise ValueError("Choose friend, study, cofounder or kids.")
        with self.lock:
            self.store.set_setting("mode", mode)
            self.history.clear()

    def set_muted(self, value):
        self.store.set_setting("muted", bool(value))

    def enable(self, service, value):
        if service not in {"web_search", "sms", "home_assistant", "shopping"}: raise ValueError("Unknown integration.")
        if self.mode == "kids" and value: raise ValueError("Integrations cannot be enabled in kids mode.")
        self.store.set_setting("integration:" + service, bool(value))

    def hush(self, minutes=30):
        if not 1 <= minutes <= 1440: raise ValueError("Hush must be 1–1440 minutes.")
        self.store.set_setting("hush_until", self.clock() + minutes * 60)

    def status(self):
        return {"provider_ready": {"web_search": bool(self.providers.env.get("BRAVE_SEARCH_API_KEY")), "sms": all(self.providers.env.get(k) for k in ["TWILIO_ACCOUNT_SID","TWILIO_AUTH_TOKEN","TWILIO_FROM_NUMBER"]), "home_assistant": all(self.providers.env.get(k) for k in ["HOME_ASSISTANT_URL","HOME_ASSISTANT_TOKEN","LUMA_ALLOWED_LIGHTS"]), "shopping": self.providers.env.get("LUMA_MERCHANTS_JSON", "{}") != "{}"}, "mode": self.mode, "microphone_muted": self.muted, "camera": "not connected", "memory": "encrypted local payloads; lexical retrieval", "conversation_storage": "RAM only", "integrations": {s: self.store.setting("integration:" + s, False) for s in ["web_search", "sms", "home_assistant", "shopping"]}, "quiet_hours": self.store.setting("quiet_hours", [23, 7]), "hush_until": self.store.setting("hush_until", 0), "model_enabled": self.use_model, "tasks": len(self.store.all("task")), "routines": len(self.store.all("routine"))}

    def _check(self, name):
        spec = TOOLS[name]
        if self.mode == "kids" and not spec.kids: raise ValueError("This tool is unavailable in kids mode.")
        if spec.service and not self.store.setting("integration:" + spec.service, False):
            raise ValueError(f"{spec.service} is off. Enable it explicitly in local settings first.")

    def propose(self, name, args):
        validate(name, args)
        if name == "tasks.create":
            due = datetime.fromisoformat(args["due"].replace("Z", "+00:00")).timestamp()
            if not self.clock() < due <= self.clock()+366*86400: raise ValueError("Choose a reminder in the future, within one year.")
        self._check(name)
        token = secrets.token_hex(4)
        row = self.store.put("action", {"tool": name, "arguments": args, "state": "pending" if TOOLS[name].confirm else "ready", "created": self.clock(), "expires": self.clock() + 600, "approval_hash": hashlib.sha256(token.encode()).hexdigest()})
        if TOOLS[name].confirm:
            # Token is returned once to the local control surface, never to LLM.
            return {"action": row["id"], "state": "pending", "tool": name, "arguments": args, "confirm_token": token, "expires": row["expires"], "summary": "Review these exact details. Confirm locally to continue; nothing has been sent or ordered."}
        return self._execute(row, {"ready"})

    def confirm(self, id, token):
        row = self.store.get("action", id)
        if not row: raise ValueError("Action not found.")
        if row["state"] != "pending": raise ValueError("Action is no longer awaiting approval; do not retry uncertain side effects.")
        if self.clock() > row["expires"]:
            self.store.transition(id, {"pending"}, "expired")
            raise ValueError("Approval expired. Create a fresh action and review it again.")
        if not hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(), row["approval_hash"]):
            raise ValueError("Incorrect confirmation token.")
        return self._execute(row, {"pending"})

    def cancel(self, id):
        row = self.store.transition(id, {"pending", "ready"}, "cancelled")
        return {"action": id, "state": row["state"]}

    def _execute(self, row, expected):
        name, args = row["tool"], row["arguments"]
        validate(name, args)
        self._check(name)  # recheck mode/consent at action time
        self.store.transition(row["id"], expected, "executing", started=self.clock())
        try:
            result = self._run(name, args)
            state = "handoff" if result.get("handoff") else "succeeded"
            self.store.transition(row["id"], {"executing"}, state, result=result, finished=self.clock())
            return {"action": row["id"], "state": state, **result}
        except OutcomeUnknown as e:
            self.store.transition(row["id"], {"executing"}, "unknown", error=str(e))
            return {"action": row["id"], "state": "unknown", "summary": str(e)}
        except (ProviderError, ValueError) as e:
            self.store.transition(row["id"], {"executing"}, "failed", error=str(e))
            return {"action": row["id"], "state": "failed", "summary": str(e)}
        except Exception:
            # Unexpected failure after dispatch must never be reported as success.
            self.store.transition(row["id"], {"executing"}, "unknown", error="Unexpected failure; inspect provider state before retrying.")
            raise

    def _run(self, name, args):
        if name == "memory.remember":
            row = self.store.put("memory", {"text": args["text"], "source": "explicit_user_request"})
            return {"summary": "Remembered locally.", "memory": row}
        if name == "memory.recall": return {"memories": self.store.recall(args["query"])}
        if name == "tasks.create":
            due = datetime.fromisoformat(args["due"].replace("Z", "+00:00")).timestamp()
            row = self.store.put("task", {"title": args["title"], "due": due, "done": False, "notified": False, "mode": self.mode})
            return {"summary": "Reminder saved locally. The runtime must be running to notify you; quiet hours and hush apply.", "task": row}
        if name == "tasks.list": return {"tasks": [r for r in self.store.all("task") if not r["done"] and r.get("mode", "friend") == self.mode]}
        if name == "tasks.complete":
            row = self.store.get("task", args["id"])
            if not row or row.get("mode", "friend") != self.mode: raise ValueError("Reminder not found in this mode.")
            row["done"] = True
            self.store.put("task", row, row["id"])
            return {"summary": "Reminder completed."}
        if name == "routines.create":
            row = self.store.put("routine", {**args, "last_day": None, "enabled": True, "mode": self.mode})
            return {"summary": "Daily routine saved in " + str(self.zone) + ".", "routine": row}
        if name == "web.search": return self.providers.search(args)
        if name == "sms.send": return self.providers.sms(args)
        if name == "home.light": return self.providers.light(args)
        if name == "food.checkout": return self.providers.checkout(args)
        raise ValueError("Tool has no handler.")

    def tick(self):
        """Coalesce due local reminders, honor hush/quiet and cap proactive turns.

        This scheduler never executes an external tool or buys/sends anything.
        It delivers text even with the microphone muted; caller gates audio.
        """
        with self.lock:
            now = self.clock()
            local = datetime.fromtimestamp(now, self.zone)
            start, end = self.store.setting("quiet_hours", [23, 7])
            quiet = (local.hour >= start or local.hour < end) if start > end else (start <= local.hour < end)
            if quiet or self.speaking or now < self.store.setting("hush_until", 0) or now - self.store.setting("last_proactive", 0) < 1800: return None
            due = [r for r in self.store.all("task", 1000) if not r["done"] and not r["notified"] and r["due"] <= now and r.get("mode", "friend") == self.mode]
            routines = [r for r in self.store.all("routine", 1000) if r["enabled"] and r["last_day"] != local.date().isoformat() and r["at"] <= local.strftime("%H:%M") and r.get("mode", "friend") == self.mode]
            if not due and not routines: return None
            titles = []
            for row in due[:5]:
                row["notified"] = True
                self.store.put("task", row, row["id"])
                titles.append(row["title"])
            for row in routines[:max(0, 5-len(titles))]:
                row["last_day"] = local.date().isoformat()
                self.store.put("routine", row, row["id"])
                titles.append(row["title"])
            self.store.set_setting("last_proactive", now)
            return {"type": "reminder", "text": "A reminder for you: " + "; ".join(titles), "created": now}

    def chat(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 4000: raise ValueError("Enter 1–4000 characters.")
        text = text.strip()
        reject_payment_secrets(text)
        with self.lock:
            lowered = text.lower()
            if lowered in {"hush", "not now", "stop"}:
                self.hush(); return {"text": "Okay. I'll hold reminders for 30 minutes."}
            if lowered in {"mute", "privacy on"}:
                self.set_muted(True); return {"text": "Microphone muted. Typed controls still work."}
            # A modest deterministic safety fallback, not a clinical classifier.
            if any(p in lowered for p in ["kill myself", "end my life", "suicide tonight", "hurt myself now"]):
                return {"text": "I'm concerned about your immediate safety. If you might act now, call emergency services or get someone nearby to stay with you. In the US or Canada, call or text 988. I haven't contacted anyone."}
            if lowered.startswith("remember "):
                return self.propose("memory.remember", {"text": text[9:].strip()})
            if lowered.startswith("recall "):
                return self.propose("memory.recall", {"query": text[7:].strip()})
            if lowered in {"tasks", "my tasks", "my reminders"}: return self.propose("tasks.list", {})
            m = re.fullmatch(r"remind me in (\d+) (minute|minutes|hour|hours|day|days) to (.+)", text, re.I)
            if m:
                delay = int(m[1]) * (60 if m[2].lower().startswith("minute") else 3600 if m[2].lower().startswith("hour") else 86400)
                if not 60 <= delay <= 366*86400: raise ValueError("Choose a reminder between one minute and one year away.")
                return self.propose("tasks.create", {"title": m[3], "due": datetime.fromtimestamp(self.clock()+delay, self.zone).isoformat()})
            if lowered.startswith("search "): return self.propose("web.search", {"query": text[7:].strip()})
            m = re.fullmatch(r"text (\+[1-9]\d{7,14})\s*:\s*(.+)", text, re.S)
            if m: return self.propose("sms.send", {"to": m[1], "body": m[2]})
            m = re.fullmatch(r"every day at ((?:[01]\d|2[0-3]):[0-5]\d) (.+)", text, re.I)
            if m: return self.propose("routines.create", {"title": m[2], "at": m[1]})
            if not self.use_model:
                return {"text": "Local tools are ready. Try 'remember ...', 'recall ...', 'remind me in 5 minutes to ...', 'tasks', or 'every day at 09:00 ...'. Model conversation is disabled."}
            context = [] if self.mode == "kids" else self.store.recall(text)
            informational = bool(re.match(r"^(?:(?:can|could|would) you )?(?:explain|describe|tell me about|how |what |why )", lowered))
            allowed = {k: {"description": v.description, "fields": v.fields} for k, v in TOOLS.items() if (not informational or k in {"web.search", "memory.recall", "tasks.list"}) and (self.mode != "kids" or v.kids) and (not v.service or self.store.setting("integration:"+v.service, False))}
            if self.planner is None:
                from luma.llm.inference import plan
                planner = plan
            else: planner = self.planner
            self.history.append({"role": "user", "content": text})
            self.history = self.history[-20:]
            answer = planner(self.history, context, allowed, self.mode)
            if answer.get("type") == "tool":
                name, arguments = answer.get("name"), answer.get("arguments")
                if name not in allowed:
                    return {"text": "No action was taken. Ask explicitly if you want me to save a memory, create a reminder, or prepare an action."}
                if name == "sms.send" and arguments.get("to", "") not in text:
                    return {"text": "Give me the exact recipient phone number and message so I can prepare it for review."}
                result = self.propose(name, arguments)
                # Do not include confirmation token or raw provider content in the LLM context.
                self.history.append({"role": "assistant", "content": "An action was proposed. Read the authoritative action result on the local control surface."})
                return result
            reply = answer.get("text")
            if not isinstance(reply, str) or not reply.strip(): raise ValueError("Local model returned no usable reply.")
            self.history.append({"role": "assistant", "content": reply[:2000]})
            return {"text": reply[:2000]}
