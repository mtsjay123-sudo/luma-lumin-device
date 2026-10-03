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
from luma.integrations.bookings import CalBookings
from luma.agent.contacts import ContactBook
from luma.agent.household import Household, TOOL_SPECS
from luma.agent.workflows import Workflows
from luma.hardware.device import DeviceController
from luma.integrations.mac_messages import MacMessages
from luma.integrations.commerce import GroceryService, validate_list
from luma.agent.conversation import wants_message, style_update, grocery_request
from luma.agent import texting
from luma.integrations.luma_cloud import LumaCloud, QuotaReached


@dataclass(frozen=True)
class Tool:
    description: str
    fields: dict
    service: str | None = None
    confirm: bool = False
    kids: bool = False


TOOLS = {
    "personality.set_style": Tool("Change conversation style only when asked: tone warm/direct/playful, language_style plain/contemporary/classic, verbosity brief/balanced/detailed", {"tone":"string", "language_style":"string", "verbosity":"string"}),
    "memory.remember": Tool("Save an explicitly requested personal memory locally", {"text": "string"}),
    "memory.recall": Tool("Find saved memories", {"query": "string"}),
    "tasks.in": Tool("Create a reminder a stated number of minutes from now; prefer this for relative times instead of calculating dates", {"title":"string", "minutes":"integer"}, kids=True),
    "tasks.create": Tool("Save a reminder with an ISO 8601 due date including time zone", {"title": "string", "due": "string"}, kids=True),
    "tasks.list": Tool("List unfinished reminders", {}, kids=True),
    "tasks.complete": Tool("Mark a reminder complete", {"id": "string"}, kids=True),
    "routines.create": Tool("Schedule a daily local reminder at HH:MM", {"title": "string", "at": "string"}, kids=True),
    "web.search": Tool("Search the live web with cited links; price results are not quotes", {"query": "string"}, "web_search", False),
    "messages.prepare": Tool("Draft a message to a saved contact name or exact phone number; prepare sending for review", {"recipient": "string", "body": "string"}),
    "mac_messages.send": Tool("Submit a reviewed message through this Mac Messages account", {"to": "string", "body": "string", "transport": "string"}, "sms", True),
    "sms.send": Tool("Send the exact text to an E.164 phone number using Twilio", {"to": "string", "body": "string"}, "sms", True),
    "luma.send": Tool("Send a reviewed text from Luma's number", {"to": "string", "body": "string"}, "sms", True),
    "booking.availability": Tool("Find real available appointment slots for a configured service", {"service": "string", "start": "string", "end": "string", "time_zone": "string"}, "booking"),
    "booking.create": Tool("Book only a slot selected in the local booking form", {"offer_id": "string", "name": "string", "email": "string"}, "booking", True),
    "home.light": Tool("Control a configured Home Assistant light", {"entity_id": "string", "state": "string", "brightness": "integer"}, "home_assistant", True),
    "food.checkout": Tool("Prepare a shopping list and merchant checkout handoff; does not purchase", {"merchant": "string", "items": "string", "budget_cents": "integer"}, "shopping", True),
}


TOOLS.update({name: Tool(spec["description"], spec["fields"], kids=name.startswith(("timers.", "cooking.", "briefing."))) for name, spec in TOOL_SPECS.items()})

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
    if name in {"sms.send", "mac_messages.send", "luma.send"}:
        if not re.fullmatch(r"\+[1-9]\d{7,14}", args["to"]): raise ValueError("Use an exact E.164 recipient such as +19195550123.")
        if len(args["body"]) > 1000: raise ValueError("SMS text must be at most 1000 characters.")
    if name == "mac_messages.send" and args["transport"] not in {"imessage", "sms"}: raise ValueError("Choose iMessage or SMS forwarding explicitly.")
    if name == "home.light":
        if not re.fullmatch(r"light\.[a-z0-9_]+", args["entity_id"]) or args["state"] not in {"on", "off"} or args["brightness"] > 100:
            raise ValueError("Only named lights, on/off and brightness 0–100 are supported.")
    if name == "tasks.in" and not 1 <= args["minutes"] <= 525600: raise ValueError("Choose 1–525600 minutes.")
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
        self.contacts = ContactBook(self.store)
        self.groceries = GroceryService(env=self.providers.env, request=getattr(self.providers, "request", None), clock=self.clock)
        self.bookings = CalBookings(self.store, env=self.providers.env, request=getattr(self.providers, "request", None), clock=self.clock)
        self.device = DeviceController.from_env()
        self.cloud = LumaCloud(self.store, env=self.providers.env, request=getattr(self.providers, "cloud_request", None), clock=self.clock)
        self.awaiting = None  # the one text/action the owner can approve by saying "send it"
        self.awaiting_contact = None  # a text waiting on "what's their number?"
        self._last_reply_poll = 0
        self.lock = threading.RLock()
        self.history = []  # conversations are RAM-only; explicit memories persist
        self.turn_guard = threading.Lock()
        self.turn_cancel = threading.Event()
        self.busy = False
        self.last_task = None
        self.last_reply = ""
        self.last_draft = None
        self.speaking = False
        self.zone = ZoneInfo(self.providers.env.get("LUMA_TIMEZONE", "America/New_York"))
        self.household = Household(self.store, now=self.clock, zone=str(self.zone))
        self.workflows = Workflows(self)
        # A new process starts with the microphone muted, even after a crash.
        self.store.set_setting("muted", True)

    @property
    def mode(self): return self.store.setting("mode", "friend")
    @property
    def muted(self): return self.store.setting("muted", True)

    @property
    def profile(self):
        return self.store.setting("personality", {"name": "", "tone": "warm", "language_style": "plain", "verbosity": "balanced"})

    def set_profile(self, profile):
        from luma.llm.prompts import normalize_profile
        if self.mode == "kids": raise ValueError("Set household preferences in adult mode.")
        profile = normalize_profile(profile)
        self.store.set_setting("personality",profile)
        return self.profile

    def set_mode(self, mode):
        if mode not in {"friend", "study", "cofounder", "kids"}: raise ValueError("Choose friend, study, cofounder or kids.")
        self.interrupt()
        with self.lock:
            self.last_task = self.last_draft = self.awaiting = self.awaiting_contact = None
            self.last_reply = ""
            self.store.set_setting("mode", mode)
            self.history.clear()

    def set_muted(self, value):
        if value: self.interrupt()
        self.store.set_setting("muted", bool(value))

    def interrupt(self):
        # Deliberately does not acquire the model/conversation lock.
        with self.turn_guard:
            self.turn_cancel.set()
        return {"state": "interrupted", "text": "Okay, I'm listening. Your completed steps are kept."}

    def new_turn(self):
        with self.turn_guard:
            self.turn_cancel.set()
            self.turn_cancel = threading.Event()
            return self.turn_cancel

    @property
    def voice_preferences(self):
        from luma.config import VOICE_SPEED
        return self.store.setting("voice_preferences", {"voice":"luma", "speed":VOICE_SPEED})

    def set_voice_preferences(self, value):
        from luma.audio.tts import validate_preferences
        if self.mode == "kids": raise ValueError("Set the household voice in adult mode.")
        value = validate_preferences(value)
        self.interrupt()
        self.store.set_setting("voice_preferences", value)
        return value

    def set_preset(self, preset, adult_confirmed=False):
        from luma.llm.prompts import profile_for_preset
        return self.set_profile(profile_for_preset(preset, self.profile, adult_confirmed=adult_confirmed, mode=self.mode))

    def set_quiet_hours(self, start, end):
        if any(type(v) is not int or not 0 <= v <= 23 for v in (start, end)):
            raise ValueError("Quiet hours use whole hours from 0 to 23. Matching hours disable quiet time.")
        self.store.set_setting("quiet_hours", [start, end])
        return {"quiet_hours": [start, end]}

    def available_tools(self, text, agent_mode=False):
        lowered = text.lower()
        informational = bool(re.match(r"^(?:(?:can|could|would) you )?(?:explain|describe|tell me about|how |what |why )", lowered))
        allowed = {k: {"description": v.description, "fields": v.fields} for k, v in TOOLS.items()
                   if k not in {"booking.create", "sms.send", "mac_messages.send"}
                   and (agent_mode or not informational or k in {"web.search", "memory.recall", "tasks.list", "timers.list", "household.find", "briefing.today"})
                   and (self.mode != "kids" or v.kids)
                   and (not v.service or self.store.setting("integration:" + v.service, False))}
        if not agent_mode and re.match(r"^(?:(?:can|could|would) you )?(?:explain|describe|tell me about)\b", lowered): allowed = {}
        relevant = set()
        groups = [
            (r"\b(?:remember|recall|memory|memories)\b", {"memory.remember", "memory.recall", "household.find"}),
            (r"\b(?:remind|reminder|reminders|tasks?|routine|every day)\b", {"tasks.in", "tasks.create", "tasks.list", "tasks.complete", "routines.create"}),
            (r"\b(?:timers?|countdown)\b", {"timers.start", "timers.list", "timers.control"}),
            (r"\b(?:recipe|cooking|next step|previous step)\b", {"cooking.step"}),
            (r"\b(?:household|pantry|manual|warranty|maintenance|save|where)\b", {"household.save", "household.find"}),
            (r"\b(?:briefing|my day|today's plans)\b", {"briefing.today", "tasks.list"}),
            (r"\b(?:search|look up|find online|research|latest|current price)\b", {"web.search"}),
            (r"\b(?:appointment|availability|book|booking)\b", {"booking.availability"}),
            (r"\b(?:lights?|brightness)\b", {"home.light"}),
            (r"\b(?:talk|speak|style|tone|reply|replies)\b", {"personality.set_style"}),
        ]
        for pattern, names in groups:
            if re.search(pattern, lowered): relevant.update(names)
        if wants_message(text): relevant.add("messages.prepare")
        # Conversational requests to 'talk to me' aren't preference changes.
        if not re.search(r"\b(?:more|less|style|tone|shorter|longer|slang|brief|detailed|playful|direct|classic|modern)\b",lowered): relevant.discard("personality.set_style")
        allowed = {name: spec for name, spec in allowed.items() if name in relevant}
        if not wants_message(text): allowed.pop("messages.prepare", None)
        if "messages.prepare" in allowed:
            allowed["messages.prepare"]["saved_contact_names"] = [c["name"] for c in sorted(self.contacts.list(), key=lambda c: c["name"].casefold() not in text.casefold())[:24]]
        return allowed

    def call_planner(self, messages, context, allowed, cancel_event, profile=None):
        if self.planner is not None: return self.planner(messages, context, allowed, self.mode)
        from luma.llm.inference import plan
        return plan(messages, context, allowed, self.mode, profile=profile or self.profile, cancel_event=cancel_event)

    def enable(self, service, value):
        if service not in {"web_search", "sms", "home_assistant", "shopping", "booking"}: raise ValueError("Unknown integration.")
        if self.mode == "kids" and value: raise ValueError("Integrations cannot be enabled in kids mode.")
        self.store.set_setting("integration:" + service, bool(value))

    def hush(self, minutes=30):
        if not 1 <= minutes <= 1440: raise ValueError("Hush must be 1–1440 minutes.")
        self.store.set_setting("hush_until", self.clock() + minutes * 60)

    @property
    def message_route(self):
        return self.store.setting("message_route", "phone_draft")

    def set_message_route(self, route):
        if self.mode == "kids": raise ValueError("Message settings are unavailable in kids mode.")
        if route not in {"phone_draft", "twilio", "mac_imessage", "mac_sms", "luma_number"}: raise ValueError("Choose a supported texting route.")
        self.store.set_setting("message_route", route)
        self.enable("sms", route != "phone_draft")
        return {"route": route}

    def status(self):
        env=self.providers.env
        mac=MacMessages(env=env).readiness()
        sms_ready=all(env.get(k) for k in ["TWILIO_ACCOUNT_SID","TWILIO_AUTH_TOKEN","TWILIO_FROM_NUMBER"]) if self.message_route=="twilio" else mac["available"] if self.message_route.startswith("mac_") else self.cloud.signed_in() if self.message_route=="luma_number" else False
        from luma.config import LLAMA_MODEL_PATH
        return {"voice_preferences":self.voice_preferences, "physical_privacy":self.device.privacy_state(), "daily_briefing_enabled":self.store.setting("daily_briefing_enabled",False), "daily_briefing_hour":self.store.setting("daily_briefing_hour",8), "busy":self.busy,"speaking":self.speaking,"barge_in":self.store.setting("barge_in",False),"model_name":LLAMA_MODEL_PATH.name, "message_route":self.message_route, "mac_messages_available":mac["available"], "texting":self.texting_status(), "profile": self.profile if self.mode!='kids' else {}, "time_zone":str(self.zone), "provider_ready":{"booking":bool(env.get("CAL_COM_API_KEY") and env.get("LUMA_CAL_EVENT_TYPES_JSON","{}")!='{}'), "web_search":bool(env.get("BRAVE_SEARCH_API_KEY")), "sms":sms_ready, "home_assistant":all(env.get(k) for k in ["HOME_ASSISTANT_URL","HOME_ASSISTANT_TOKEN","LUMA_ALLOWED_LIGHTS"]), "shopping":bool(env.get("INSTACART_API_KEY") or env.get("LUMA_MERCHANTS_JSON","{}")!='{}'), "groceries":bool(env.get("INSTACART_API_KEY"))}, "mode":self.mode, "microphone_muted":self.muted, "camera":"not connected", "memory":"encrypted local payloads; lexical retrieval", "conversation_storage":"RAM only", "integrations":{s:self.store.setting("integration:"+s,False) for s in ["web_search","sms","home_assistant","shopping","booking"]}, "quiet_hours":self.store.setting("quiet_hours",[23,7]), "hush_until":self.store.setting("hush_until",0), "model_enabled":self.use_model, "tasks":len(self.store.all("task")), "routines":len(self.store.all("routine"))}

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
        if name == "messages.prepare": return self.prepare_message(args["recipient"], args["body"])
        review = self.bookings.preview(args) if name == "booking.create" else None
        token = secrets.token_hex(4)
        row = self.store.put("action", {"tool": name, "arguments": args, "review": review, "state": "pending" if TOOLS[name].confirm else "ready", "created": self.clock(), "expires": self.clock() + 600, "approval_hash": hashlib.sha256(token.encode()).hexdigest()})
        if TOOLS[name].confirm:
            # Token is returned once to the local control surface, never to LLM.
            return {"action": row["id"], "state": "pending", "tool": name, "arguments": args, "review": review, "confirm_token": token, "expires": row["expires"], "summary": "Review these exact details. Confirm locally to continue; nothing has been sent or ordered."}
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
        if self.awaiting and self.awaiting["action"] == id: self.awaiting = None
        return self._humanize(row, self._execute(row, {"pending"}))

    def cancel(self, id):
        if self.awaiting and self.awaiting["action"] == id: self.awaiting = None
        row = self.store.transition(id, {"pending", "ready"}, "cancelled")
        return {"action": id, "state": row["state"]}

    def _humanize(self, row, result):
        """Say what happened the way a person would, from the verified result."""
        if row["tool"] not in {"sms.send", "mac_messages.send", "luma.send"} or result.get("text"):
            return result
        contact = self.contacts.by_phone(row["arguments"]["to"])
        name = contact["name"] if contact else row["arguments"]["to"]
        route = {"luma.send": "luma_number", "sms.send": "twilio"}.get(row["tool"], "mac_" + row["arguments"].get("transport", "imessage"))
        if result.get("state") == "succeeded":
            result["text"] = texting.sent_text(name, route, result)
        elif result.get("state") in {"failed", "unknown"}:
            result["text"] = result.get("summary")
        return result

    def _remember_sent(self, to, body):
        self.store.put("sent_text", {"to": to, "body": body, "created": self.clock()})
        old = self.store.all("sent_text", 400)[300:]
        for row in old: self.store.delete("sent_text", row["id"])

    def _examples(self, phone):
        return [r["body"] for r in self.store.all("sent_text", 300) if r.get("to") == phone][:5][::-1]

    def texting_status(self):
        account = self.cloud.cached_account()
        return {"route": self.message_route, "enabled": self.store.setting("integration:sms", False),
                "luma_number": {"signed_in": self.cloud.signed_in(), "verifying": bool(self.store.setting("luma_cloud_pending")),
                                "account": account},
                "sent_this_month": sum(1 for r in self.store.all("sent_text", 300)
                                       if datetime.fromtimestamp(r["created"], self.zone).strftime("%Y-%m") == datetime.fromtimestamp(self.clock(), self.zone).strftime("%Y-%m"))}

    def _execute(self, row, expected):
        name, args = row["tool"], row["arguments"]
        validate(name, args)
        self._check(name)  # recheck mode/consent at action time
        if name == "sms.send" and self.message_route != "twilio": raise ValueError("The texting route changed. Prepare a fresh message for review.")
        if name == "mac_messages.send" and self.message_route != "mac_"+args["transport"]: raise ValueError("The texting route changed. Prepare a fresh message for review.")
        if name == "luma.send" and self.message_route != "luma_number": raise ValueError("The texting route changed. Prepare a fresh message for review.")
        self.store.transition(row["id"], expected, "executing", started=self.clock())
        try:
            result = self._run(name, args, action_id=row["id"])
            state = "handoff" if result.get("handoff") else "succeeded"
            self.store.transition(row["id"], {"executing"}, state, result=result, finished=self.clock())
            if name in {"sms.send", "mac_messages.send", "luma.send"}:
                self._remember_sent(args["to"], args["body"])
            return {"action": row["id"], "state": state, **result}
        except QuotaReached as e:
            self.store.transition(row["id"], {"executing"}, "failed", error=str(e))
            return {"action": row["id"], "state": "failed", "quota": True, "upgrade_url": e.upgrade_url, "summary": texting.quota_text(e), "section": "people"}
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

    def _run(self, name, args, action_id=None):
        if name in TOOL_SPECS:
            result = self.household.run(name, args, mode=self.mode)
            result["section"] = "household" if name.startswith("household.") else "cooking" if name.startswith(("timers.", "cooking.")) else "daily-briefing"
            return result
        if name == "personality.set_style":
            profile=self.set_profile({**self.profile,**args})
            return {"profile":profile,"summary":"Conversation style saved. I'll use your preferences in future replies."}
        if name == "memory.remember":
            row = self.store.put("memory", {"text": args["text"], "source": "explicit_user_request"})
            return {"summary": "Remembered locally.", "memory": row}
        if name == "memory.recall": return {"memories": self.store.recall(args["query"])}
        if name == "tasks.in":
            due = datetime.fromtimestamp(self.clock()+args["minutes"]*60,self.zone).isoformat()
            return self._run("tasks.create", {"title":args["title"],"due":due})
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
        if name == "booking.availability": return self.bookings.availability(args)
        if name == "booking.create": return self.bookings.create(args)
        if name == "web.search": return self.providers.search(args)
        if name == "sms.send": return self.providers.sms(args)
        if name == "luma.send": return self.cloud.send(args["to"], args["body"], client_ref=action_id or secrets.token_hex(8))
        if name == "mac_messages.send":
            env={**self.providers.env,"LUMA_MESSAGES_TRANSPORT":args["transport"]}
            return MacMessages(env=env).send({"to":args["to"],"body":args["body"]})
        if name == "home.light": return self.providers.light(args)
        if name == "food.checkout": return self.providers.checkout(args)
        raise ValueError("Tool has no handler.")

    def prepare_message(self, recipient, body):
        if self.mode == "kids": raise ValueError("Messages are unavailable in kids mode.")
        try: contact = self.contacts.resolve(recipient)
        except ValueError:
            if not isinstance(recipient, str): raise
            simpler = re.sub(r"^(?:my|our)\s+", "", recipient.strip(), flags=re.I)
            if simpler == recipient: raise
            contact = self.contacts.resolve(simpler)
        if isinstance(body, str):
            body = texting.mirror_style(body.strip(), self._examples(contact["phone"]))
        args = {"to": contact["phone"], "body": body}
        validate("sms.send", args)
        name = contact["name"]
        if self.store.setting("integration:sms", False):
            route, account, result = self.message_route, None, None
            if route == "luma_number":
                account = self.cloud.cached_account()
                if account and account.get("texts_left") == 0:
                    try: account = self.cloud.account(refresh=True)
                    except ProviderError: pass
                if account and account.get("texts_left") == 0:
                    plus = account.get("plus") or {}
                    error = QuotaReached(f"You've used your {account.get('texts_limit')} free texts from Luma's number this month." if account.get("plan") != "plus"
                                         else f"You've sent all {account.get('texts_limit')} texts included in Luma Plus this month.", plan=account.get("plan", "free"), plus=plus)
                    draft = self.store.put("phone_draft", {**args, "name": name, "created": self.clock()})
                    return {"state": "quota", "quota": True, "message_draft": draft, "section": "people", "upgrade_available": bool(plus.get("available")),
                            "text": texting.quota_text(error)}
                result = self.propose("luma.send", args)
            elif route.startswith("mac_"): result = self.propose("mac_messages.send",{**args,"transport":route[4:]})
            elif route == "twilio": result = self.propose("sms.send", args)
            if result:
                result.update(recipient_name=name, text=texting.pending_text(name, body, route, account))
                return result
        draft = self.store.put("phone_draft", {**args, "name": name, "created": self.clock()})
        return {"state": "draft", "message_draft": draft, "recipient_name": name, "text": texting.draft_text(name, body),
                "summary": "Message drafted for your phone. Copy the text, open Messages and tap Send there. Luma has not sent it."}

    TEXT_REQUEST = re.compile(
        r"(?:(?:hey|hi|yo|okay|ok)[,\s]+)?(?:luma[,\s]+)?(?:(?:can|could|would|will) you\s+)?(?:please\s+)?"
        r"(?:(?:text|message|sms|imessage)\s+(?P<r1>.+?)\s+(?P<c1>to say|to tell (?:her|him|them)|and (?:say|tell (?:her|him|them))|to|that|saying)\s+(?P<b1>.+)"
        r"|let\s+(?P<r2>.+?)\s+know\s+(?:that\s+)?(?P<b2>.+))", re.I | re.S)
    TELL_REQUEST = re.compile(
        r"(?:(?:hey|hi|yo|okay|ok)[,\s]+)?(?:luma[,\s]+)?(?:(?:can|could|would|will) you\s+)?(?:please\s+)?"
        r"tell\s+(?!me\b|us\b|him\b|her\b|them\b)((?:my|our)\s+[\w'-]+|[A-Za-z][\w'-]*)\s+(?:that\s+)?(.+)", re.I | re.S)

    def _text_request(self, text):
        match = self.TEXT_REQUEST.fullmatch(text.strip())
        if match and match["r1"]:
            recipient, connector, request = match["r1"], "to" if match["c1"].lower() == "to" else "that", match["b1"]
        elif match:
            recipient, connector, request = match["r2"], "that", match["b2"]
        else:
            tell = self.TELL_REQUEST.fullmatch(text.strip())
            if not tell: return None
            try: self.contacts.resolve(tell[1])  # "tell X" only means a text when X is someone saved
            except ValueError: return None
            recipient, connector, request = tell[1], "that", tell[2]
        if self.mode == "kids":
            return {"text": "I can't text people in kids mode. Ask a grown-up to help with that one."}
        recipient = recipient.strip().strip(",")
        quoted = re.fullmatch(r'\s*["“](.+?)["”]\s*[.!?]?\s*', request, re.S)
        body = quoted[1] if quoted else texting.template_text(connector, request)
        try:
            return self.prepare_message(recipient, body)
        except ValueError as error:
            if "multiple contacts" in str(error):
                return {"text": f"More than one person is saved as {recipient}. Which one did you mean?", "section": "people"}
            if "contact" not in str(error):
                return {"text": str(error)}
            self.awaiting_contact = {"label": recipient, "body": body, "created": self.clock()}
            label = re.sub(r"^(?:my|our)\s+", "", recipient, flags=re.I).lower()
            pronoun = "her" if label in {"girl", "girlfriend", "wife", "mom", "mother", "mama", "sister", "sis", "aunt", "grandma", "daughter", "bae"} else \
                      "his" if label in {"boy", "boyfriend", "husband", "dad", "father", "brother", "bro", "uncle", "grandpa", "son"} else "their"
            ask = f"Who's {recipient}? Give me {pronoun} name and number" if recipient.lower().startswith(("my ", "our ")) else f"What's {recipient}'s number? Send it"
            return {"text": ask + " and I'll save it and get the text ready.", "section": "people"}

    @staticmethod
    def _phone_from_text(text):
        match = re.search(r"(?<!\d)(\+?\d[\d\s().-]{8,17}\d)(?!\d)", text)
        if not match: return None, text
        digits = re.sub(r"\D", "", match[1])
        if match[1].startswith("+") and 8 <= len(digits) <= 15: phone = "+" + digits
        elif len(digits) == 10: phone = "+1" + digits
        elif len(digits) == 11 and digits.startswith("1"): phone = "+" + digits
        else: return None, text
        return phone, (text[:match.start()] + " " + text[match.end():]).strip()

    def _contact_followup(self, text):
        pending = self.awaiting_contact
        if not pending or self.mode == "kids": return None
        if self.clock() - pending["created"] > 600:
            self.awaiting_contact = None
            return None
        phone, rest = self._phone_from_text(text)
        if not phone: return None
        rest = re.sub(r"(?i)\b(?:her|his|their|my|the)?\s*(?:name\s+is|name's|number\s+is|number's|it's|its|it is|that's|thats|she's|he's|called)\b", " ", rest)
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", rest) if w.lower() not in {"and", "her", "his", "their", "number", "name", "is", "at", "the", "phone", "cell"}]
        label = re.sub(r"^(?:my|our)\s+", "", pending["label"], flags=re.I)
        name = " ".join(w[:1].upper() + w[1:] for w in words[:3]) or label[:1].upper() + label[1:]
        aliases = [label] if label.casefold() != name.casefold() else []
        self.awaiting_contact = None
        try:
            self.contacts.save({"name": name, "phone": phone, "aliases": aliases})
            result = self.prepare_message(name, pending["body"])
        except ValueError as error:
            return {"text": "I couldn't save that: " + str(error), "section": "people"}
        result["text"] = f"Saved {name}" + (f" as your {label}" if aliases else "") + ". " + result.get("text", "")
        return result

    SAVE_CONTACT = re.compile(r"(?:please\s+)?(?:save|add)\s+(?P<name>[A-Za-z][\w' -]{0,40}?)(?:'s)?(?:\s+(?:number|cell|phone))?(?:\s*(?:as|is|:|,|-))?\s+(?P<phone>\+?[\d(][\d\s().-]{8,18}\d)(?:\s*(?:,|and)?\s*(?:as|she's|he's|that's)\s+(?P<alias>(?:my|our)\s+[\w' -]{1,30}))?\.?", re.I)

    def _save_contact_request(self, text):
        match = self.SAVE_CONTACT.fullmatch(text.strip())
        if not match or self.mode == "kids": return None
        phone, _ = self._phone_from_text(match["phone"])
        if not phone: return None
        name = " ".join(w[:1].upper() + w[1:] for w in match["name"].split())
        alias = match["alias"]
        try:
            record = self.contacts.save({"name": name, "phone": phone, "aliases": [alias] if alias else []})
        except ValueError as error:
            return {"text": str(error), "section": "people"}
        extra = f" — I'll know who you mean by {alias.lower()}" if alias else ""
        return {"text": f"Got it, {record['name']} is saved{extra}.", "contact": record, "section": "people"}

    def replies_summary(self, text=""):
        replies = [r for r in self.store.all("sms_reply", 30)]
        if not replies:
            if self.message_route != "luma_number":
                return {"text": "I can only see replies to Luma's number. Texts to your own number show up on your phone."}
            return {"text": "Nobody's texted back yet."}
        lowered = text.lower()
        named = [r for r in replies if r.get("name") and r["name"].lower() in lowered]
        picks = (named or replies)[:3]
        for r in picks:
            if not r.get("announced"): self.store.put("sms_reply", {**r, "announced": True}, r["id"])
        return {"text": " ".join(f"{r['name']} said: “{r['body']}”" + ("." if not r['body'].endswith(('.', '!', '?')) else "") for r in picks), "replies": picks}

    def _poll_replies(self):
        """Fetch replies to Luma's number about once a minute. Network happens outside the agent lock."""
        if self.message_route != "luma_number" or self.mode == "kids" or not self.cloud.signed_in(): return
        if self.clock() - self._last_reply_poll < max(5, int(self.providers.env.get("LUMA_REPLY_POLL_SECONDS", "60") or 60)): return
        self._last_reply_poll = self.clock()
        try: replies = self.cloud.inbox()
        except ProviderError: return
        for reply in replies:
            sender = str(reply.get("from", ""))
            contact = self.contacts.by_phone(sender)
            row = {"from": sender, "name": contact["name"] if contact else sender, "body": " ".join(str(reply.get("body", "")).split())[:1600],
                   "received_at": reply.get("received_at"), "announced": False}
            try: self.store.put("sms_reply", row, "sms_reply:" + str(reply.get("id")))
            except ValueError: self.store.put("sms_reply", {**row, "body": "(a message with a long number in it; check your messages)"}, "sms_reply:" + str(reply.get("id")))

    def message_status(self, action_id):
        self._check("sms.send")
        action = self.store.get("action", action_id)
        if not action or action.get("tool") != "sms.send" or not action.get("result", {}).get("message_id"):
            raise ValueError("No SMS receipt exists for this action.")
        status = self.providers.sms_status({"message_id": action["result"]["message_id"]})
        self.store.put("sms_receipt", {**status, "action_id": action_id, "checked": self.clock()}, "sms_receipt:" + action_id)
        return status

    def tick(self):
        """Coalesce due local reminders, honor hush/quiet and cap proactive turns.

        This scheduler never executes an external tool or buys/sends anything.
        It delivers text even with the microphone muted; caller gates audio.
        """
        self._poll_replies()
        with self.lock:
            timer_events = self.household.timer_events(mode=self.mode, deliver=not self.speaking)
            if timer_events:
                return {"type":"timer", "text":" ".join(e["text"] for e in timer_events), "created":self.clock()}
            now = self.clock()
            local = datetime.fromtimestamp(now, self.zone)
            start, end = self.store.setting("quiet_hours", [23, 7])
            quiet = (local.hour >= start or local.hour < end) if start > end else (start <= local.hour < end)
            # Replies always show up; during quiet hours they arrive silently.
            if not self.speaking and now >= self.store.setting("hush_until", 0) and self.mode != "kids":
                fresh = [r for r in self.store.all("sms_reply", 20) if not r.get("announced")][::-1][:3]
                if fresh:
                    for r in fresh: self.store.put("sms_reply", {**r, "announced": True}, r["id"])
                    lines = [f"{r['name']} texted back: “{r['body']}”" for r in fresh]
                    return {"type": "reply", "text": " ".join(lines), "created": now, "silent": quiet}
            if quiet or self.speaking or now < self.store.setting("hush_until", 0) or now - self.store.setting("last_proactive", 0) < 1800: return None
            due = [r for r in self.store.all("task", 1000) if not r["done"] and not r["notified"] and r["due"] <= now and r.get("mode", "friend") == self.mode]
            routines = [r for r in self.store.all("routine", 1000) if r["enabled"] and r["last_day"] != local.date().isoformat() and r["at"] <= local.strftime("%H:%M") and r.get("mode", "friend") == self.mode]
            if not due and not routines:
                if self.store.setting("daily_briefing_enabled", False) and local.hour >= self.store.setting("daily_briefing_hour", 8):
                    briefing = self.household.briefing(mode=self.mode, proactive=True)
                    if briefing: self.store.set_setting("last_proactive", now)
                    return briefing
                return None
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

    def chat(self, text, *, cancel_event=None, agent_mode=False, resume_id=None):
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
            raise ValueError("Enter 1–4000 characters.")
        reject_payment_secrets(text)
        spoken = self._spoken_approval(text)
        if spoken is not None: return spoken
        if text.strip().lower() in {"wait", "stop talking", "stop speaking", "never mind", "nevermind"}:
            return self.interrupt()
        event = cancel_event or self.new_turn()
        with self.lock:
            if event.is_set(): return {"state":"interrupted", "text":"Stopped before starting."}
            self.busy = True
            self.history.append({"role":"user", "content":text.strip()})
            self.history = self.history[-20:]
            try:
                result = self.workflows.run(text, event, resume_id=resume_id) if agent_mode else self._chat(text, event)
                if event.is_set() and not result.get("action") and not result.get("workflow"):
                    return {"state":"interrupted", "text":"Okay. Tell me what you want to change."}
                if result.get("task"): self.last_task = result["task"]["id"]
                if result.get("state") == "pending" and result.get("confirm_token"):
                    self.awaiting = {"action": result["action"], "token": result["confirm_token"], "expires": result.get("expires", self.clock() + 600)}
                if result.get("message_draft"): self.last_draft = result["message_draft"]["id"]
                reply = result.get("text") or result.get("summary") or "Read the verified result in the local controls."
                self.last_reply = reply
                from luma.agent.workflows import observation
                self.history.append({"role":"assistant", "content":observation(result)})
                return result
            except Exception as error:
                from luma.llm.inference import GenerationCancelled
                if isinstance(error, GenerationCancelled):
                    self.history.append({"role":"assistant", "content":"Response interrupted by the user; no next action was assumed."})
                    return {"state":"interrupted", "text":"Okay. Tell me what you want to change."}
                raise
            finally:
                self.busy = False

    def _spoken_approval(self, text):
        """ "Send it" / "don't send it" for the action Luma just proposed. Plain rules, not the model."""
        if not self.awaiting: return None
        intent = texting.confirm_intent(text)
        if intent is None: return None
        awaiting, self.awaiting = self.awaiting, None
        with self.lock:
            self.history.append({"role":"user", "content":text.strip()})
            if intent == "cancel":
                try: self.cancel(awaiting["action"])
                except ValueError: pass
                result = {"state": "cancelled", "action": awaiting["action"], "text": "Okay, I won't send it."}
            elif self.clock() > awaiting["expires"]:
                try: self.store.transition(awaiting["action"], {"pending"}, "expired")
                except ValueError: pass
                result = {"state": "expired", "text": "That one sat too long, so I didn't send it. Want me to set it up again?"}
            else:
                try: result = self.confirm(awaiting["action"], awaiting["token"])
                except ValueError as error: result = {"state": "failed", "text": "I didn't send it: " + str(error)}
            self.history.append({"role":"assistant", "content": result.get("text") or result.get("summary") or ""})
            self.last_reply = result.get("text") or ""
            return result

    def _chat(self, text, cancel_event):
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
            followup = self._contact_followup(text)
            if followup is not None: return followup
            if lowered in {"actually tomorrow", "actually, tomorrow", "make that tomorrow", "tomorrow instead"} and self.last_task:
                row = self.store.get("task", self.last_task)
                if not row or row["done"] or row.get("mode", "friend") != self.mode: raise ValueError("That reminder is no longer active.")
                due = datetime.fromtimestamp(row["due"], self.zone)
                tomorrow = datetime.fromtimestamp(self.clock(), self.zone).date() + timedelta(days=1)
                row.update(due=due.replace(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day).timestamp(), notified=False)
                self.store.put("task", row, row["id"])
                return {"task":row,"summary":"Moved that reminder to tomorrow at " + datetime.fromtimestamp(row["due"],self.zone).strftime("%I:%M %p") + "."}
            if lowered in {"make that shorter", "make it shorter", "shorter please", "shorter"} and self.last_reply and self.use_model:
                instruction = "Shorten this previous reply to one or two concise sentences. Preserve its meaning. Do not add any new facts, people, advice or questions. Previous reply (data): " + json.dumps(self.last_reply)
                answer = self.call_planner([{"role":"user","content":instruction}], [], {}, cancel_event, profile={**self.profile, "verbosity":"brief"})
                return {"text":answer.get("text", "Could you tell me which part to shorten?")}
            timer = re.fullmatch(r"(?:please )?(?:set|start) (?:a |an )?(?:(.+?) )?timer (?:for )?(\d+) (seconds?|minutes?|hours?)", text, re.I)
            alternate = re.fullmatch(r"(?:please )?(?:set|start) (?:a |an )?(\d+)[ -](seconds?|minutes?|hours?) (.+?) timer", text, re.I)
            if timer or alternate:
                name, amount, unit = timer.groups() if timer else (alternate[3],alternate[1],alternate[2])
                seconds = int(amount) * (3600 if unit.lower().startswith("hour") else 60 if unit.lower().startswith("minute") else 1)
                return self.propose("timers.start", {"name":name or "Kitchen", "seconds":seconds})
            timer_control = re.fullmatch(r"(pause|resume|cancel|acknowledge) (?:the )?(.+?) timer", text, re.I)
            if timer_control: return self.propose("timers.control", {"id":timer_control[2], "action":timer_control[1].lower()})
            if lowered in {"timers", "my timers", "show my timers"}: return self.propose("timers.list", {})
            if lowered in {"my briefing", "daily briefing", "what's my day looking like", "what is my day looking like"}: return self.propose("briefing.today", {})
            household_result = self.household.command(text, mode=self.mode)
            if household_result is not None:
                household_result.setdefault("section", "cooking")
                return household_result
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
            # Common ways of asking for a text are drafted by rules, not the model,
            # so nothing gets added to what the owner said.
            texted = self._text_request(text)
            if texted is not None: return texted
            saved = self._save_contact_request(text)
            if saved is not None: return saved
            if re.search(r"\b(?:did|has)\b.{1,40}\b(?:text(?:ed)?|messag(?:e|ed)|repl(?:y|ied)|respond(?:ed)?|write|written|wrote)\b.{0,20}\bback\b|\b(?:any|new)\s+(?:texts|replies|messages)\b|\bwho texted\b", lowered):
                return self.replies_summary(text)
            m = re.fullmatch(r"(?:please )?text ([^:\n]{1,90}):\s*(.+)", text, re.S | re.I)
            if m: return self.prepare_message(m[1], m[2])
            m = re.fullmatch(r"every day at ((?:[01]\d|2[0-3]):[0-5]\d) (.+)", text, re.I)
            if m: return self.propose("routines.create", {"title": m[2], "at": m[1]})
            style = style_update(text, self.profile)
            if style:
                self.set_profile(style)
                return {"text": "Got it. I've saved your conversation preferences: " + style['language_style'] + " language and " + style['verbosity'] + " replies.", "profile": style}
            if self.mode != 'kids' and grocery_request(text) and not wants_message(text):
                ready = bool(self.providers.env.get('INSTACART_API_KEY'))
                return {"text": ("Let's build the grocery list and check nearby retailers. " if ready else "Connect Instacart in the local setup to create a shoppable grocery list and check nearby retailers. ") + "I don't have verified product prices or stock to choose the cheapest eggs. Review the exact listing, total and saved payment method at merchant checkout; I haven't placed an order.", "section": "groceries"}
            if re.search(r"\b(?:what|which) (?:llm|(?:language |ai )?model) (?:are you|do you|does luma|is luma)\b", lowered):
                from luma.config import LLAMA_MODEL_PATH
                name = LLAMA_MODEL_PATH.name
                label = 'Qwen3 4B Instruct 2507' if name.startswith('Qwen_Qwen3-4B-Instruct-2507') else 'Llama 3.2 3B Instruct' if name.startswith('Llama-3.2-3B-Instruct') else name
                return {"text": ("I'm using " if self.use_model else "Conversation is off. The configured model is ") + label + ", running locally on this Mac. Your saved preferences shape how I reply; the model weights have not been fine-tuned."}
            if not self.use_model:
                return {"text": "Local tools are ready. Try 'remember ...', 'recall ...', 'remind me in 5 minutes to ...', 'tasks', or 'every day at 09:00 ...'. Model conversation is disabled."}
            context = [] if self.mode == "kids" else (self.store.recall(text) + [{"text":r["title"] + ": " + r["details"]} for r in self.household.records(query=text,mode=self.mode)[:3]])
            allowed = self.available_tools(text)
            answer = self.call_planner(self.history, context, allowed, cancel_event)
            if cancel_event.is_set(): return {"state":"interrupted", "text":"Stopped before taking another action."}
            if answer.get("type") == "tool":
                name, arguments = answer.get("name"), answer.get("arguments")
                if name not in allowed:
                    return {"text": "No action was taken. Ask explicitly if you want me to save a memory, create a reminder, or prepare an action."}
                if name == "sms.send" and arguments.get("to", "") not in text:
                    return {"text": "Give me the exact recipient phone number and message so I can prepare it for review."}
                try:
                    result = self.propose(name, arguments)
                except ValueError as error:
                    if name != "messages.prepare": raise
                    return {"text": str(error) + " Choose the exact person and message in People & Texts.", "section": "people"}
                # Do not include confirmation token or raw provider content in the LLM context.
                return result
            reply = answer.get("text")
            if not isinstance(reply, str) or not reply.strip(): raise ValueError("Local model returned no usable reply.")
            return {"text": reply[:2000]}
