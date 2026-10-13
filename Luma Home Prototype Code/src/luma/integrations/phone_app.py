"""The Luma app on the owner's phone, from anywhere, through Luma Cloud.

Pairing: this Luma opens a 10-minute window with Luma Cloud and shows a QR code
for <cloud>/app/#pair=<id>.<secret>.<key>. The phone redeems id+secret for its own
credential; the 32-byte key never leaves the link's #fragment, so Luma Cloud only
ever relays AES-GCM ciphertext it can't read.

Messages (JSON, version 1), sealed with additional data "luma1|<pair id>|<up|down>":
  phone → Luma: hello, text, confirm (action + the one-time token Luma sent), cancel
  Luma → phone: reply (text, optional card), notice, done (an approval's outcome)

Approvals stay plain rules: "Send it" on the phone carries the action's one-time
token, which Agent.confirm checks. The model never approves anything.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import queue
import secrets
import threading
import time

from luma.integrations.providers import ProviderError

AAD = "luma1|{}|{}"
TEXT_TOOLS = {"luma.send", "sms.send", "mac_messages.send"}
MAX_AGE = 24 * 3600  # an up message older than this is ignored
NOTICE_LABELS = {"reply": "Text back", "reminder": "Reminder", "timer": "Timer", "briefing": "Today"}


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64u(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def seal(key: bytes, pair_id: str, direction: str, message: dict) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    iv = os.urandom(12)
    data = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode()
    return b64u(iv + AESGCM(key).encrypt(iv, data, AAD.format(pair_id, direction).encode()))


def unseal(key: bytes, pair_id: str, direction: str, payload: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = unb64u(payload)
    message = json.loads(AESGCM(key).decrypt(raw[:12], raw[12:], AAD.format(pair_id, direction).encode()))
    if not isinstance(message, dict) or message.get("v") != 1:
        raise ValueError("unknown message")
    return message


def qr_data_uri(url: str) -> str:
    import qrcode
    from qrcode.image.svg import SvgPathFillImage
    svg = qrcode.make(url, image_factory=SvgPathFillImage).to_string()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


def card_for(result: dict):
    """What the phone shows under Luma's reply: an approval, or a draft to send yourself."""
    if result.get("state") == "pending" and result.get("confirm_token") and result.get("action"):
        args = result.get("arguments") or {}
        card = {"kind": "approve", "action": result["action"], "token": result["confirm_token"], "expires": result.get("expires")}
        if result.get("tool") in TEXT_TOOLS:
            card.update(to_name=result.get("recipient_name") or args.get("to", ""), to=args.get("to"), body=args.get("body", ""))
        else:
            review = result.get("review") or {}
            card["title"] = str(review.get("title") or result.get("tool", "")).replace(".", " ").strip().capitalize() or "Approve this"
            card["lines"] = [f"{k.replace('_', ' ')}: {v}" for k, v in review.items() if k != "title" and isinstance(v, (str, int, float))][:6]
        return card
    draft = result.get("message_draft")
    if isinstance(draft, dict) and draft.get("body"):
        return {"kind": "draft", "to_name": draft.get("name", ""), "to": draft.get("to"), "body": draft["body"]}
    return None


class PhoneApp:
    def __init__(self, agent, clock=time.time, wait=25):
        self.agent = agent
        self.cloud = agent.cloud
        self.store = agent.store
        self.clock = clock
        self.wait = wait
        self.lock = threading.RLock()
        self._stop = threading.Event()
        self._poller = None
        self._worker = None
        self._jobs = queue.Queue()

    # -- state, kept in the encrypted store -----------------------------------
    # One base64 blob, so the store's card-number guard never mistakes the
    # digits in an id for a card number.
    def _load(self):
        raw = self.store.setting("phone_app_b64")
        state = json.loads(base64.b64decode(raw)) if raw else {}
        state.setdefault("pairings", {})
        state.setdefault("links", {})
        state.setdefault("seen", [])
        return state

    def _save(self, state):
        self.store.set_setting("phone_app_b64", base64.b64encode(json.dumps(state).encode()).decode())

    def phones(self):
        state = self._load()
        return [{"id": link_id, "name": link.get("name", "Phone"), "created": link.get("created"), "last_seen": link.get("last_seen"), "notifications": bool(link.get("push"))}
                for link_id, link in state["links"].items()]

    def status(self):
        state = self._load()
        now = self.clock()
        return {"phones": self.phones(), "waiting": any(p["expires"] > now for p in state["pairings"].values()), "cloud": self.cloud.base_url}

    # -- pairing --------------------------------------------------------------
    def start_pairing(self, device_name="Luma"):
        if self.agent.mode == "kids":
            raise ValueError("Connect a phone in adult mode.")
        self.cloud.register(device_name)
        secret = secrets.token_urlsafe(32)
        key = os.urandom(32)
        out = self.cloud.app_pair_start(hashlib.sha256(secret.encode()).hexdigest())
        pair_id = out["pair_id"]
        with self.lock:
            state = self._load()
            now = self.clock()
            state["pairings"] = {k: v for k, v in state["pairings"].items() if v["expires"] > now}
            state["pairings"][pair_id] = {"key": b64u(key), "expires": now + 600}
            self._save(state)
        url = f"{self.cloud.base_url}/app/#pair={pair_id}.{secret}.{b64u(key)}"
        self.start()
        return {"url": url, "qr": qr_data_uri(url), "expires_at": out.get("expires_at"), "summary": "Scan this with your phone's camera. It works once, for 10 minutes."}

    def remove(self, link_id):
        try:
            self.cloud.app_unpair(link_id)
        except ProviderError as error:
            if getattr(error, "status", 0) != 404:
                raise
        with self.lock:
            state = self._load()
            state["links"].pop(link_id, None)
            self._save(state)
        return {"removed": link_id, "phones": self.phones()}

    def _sync_links(self, links):
        """Learn which phone redeemed which pairing, and forget removed phones."""
        with self.lock:
            state = self._load()
            current = {}
            for link in links:
                known = state["links"].get(link["id"])
                pairing = state["pairings"].pop(link.get("pairing_id") or "", None)
                if known:
                    current[link["id"]] = {**known, "name": link.get("name") or known.get("name"), "last_seen": link.get("last_seen_at"), "push": link.get("push")}
                elif pairing:
                    current[link["id"]] = {"pair": link["pairing_id"], "key": pairing["key"], "name": link.get("name") or "Phone",
                                           "created": self.clock(), "last_seen": link.get("last_seen_at"), "push": link.get("push")}
            state["links"] = current
            state["pairings"] = {k: v for k, v in state["pairings"].items() if v["expires"] > self.clock()}
            self._save(state)
            return current

    # -- the loop -------------------------------------------------------------
    def _active(self):
        state = self._load()
        return bool(state["links"]) or any(p["expires"] > self.clock() for p in state["pairings"].values())

    def start(self):
        with self.lock:
            if self._poller and self._poller.is_alive():
                return
            if not self.cloud.connected() or not self._active():
                return
            self._stop.clear()
            self._poller = threading.Thread(target=self._run, name="luma-phone-app", daemon=True)
            self._poller.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        backoff = 0
        while not self._stop.is_set():
            if not self.cloud.connected() or not self._active():
                return  # start() runs again on the next pairing
            try:
                self.poll_once(self.wait)
                backoff = 0
            except ProviderError:
                backoff = min(60, (backoff or 2) * 2)
                self._stop.wait(backoff)
            except Exception:
                self._stop.wait(5)

    def poll_once(self, wait=0):
        state = self._load()
        data = self.cloud.app_inbox(state.get("cursor"), wait=wait)
        links = self._sync_links(data.get("links") or [])
        for row in data.get("messages") or []:
            self._receive(row, links)
        if data.get("cursor"):
            with self.lock:
                state = self._load()
                state["cursor"] = data["cursor"]
                self._save(state)
        return data

    def _receive(self, row, links):
        link = links.get(row.get("link_id"))
        if not link:
            return
        try:
            message = unseal(unb64u(link["key"]), link["pair"], "up", str(row.get("payload", "")))
        except Exception:
            return  # not sealed with this phone's key: ignore it
        nonce = str(message.get("n", ""))[:40]
        with self.lock:
            state = self._load()
            if not nonce or nonce in state["seen"] or abs(self.clock() - float(message.get("ts", 0)) / 1000) > MAX_AGE:
                return  # a replay, or something stale
            state["seen"] = (state["seen"] + [nonce])[-500:]
            self._save(state)
        self._jobs.put((row["link_id"], message))
        if not self._worker or not self._worker.is_alive():
            self._worker = threading.Thread(target=self._work, name="luma-phone-app-worker", daemon=True)
            self._worker.start()

    def _work(self):
        while True:
            try:
                link_id, message = self._jobs.get(timeout=3)
            except queue.Empty:
                return
            try:
                self.handle(link_id, message)
            except Exception as error:
                try:
                    self.send(link_id, {"t": "reply", "text": "Something went wrong on my end: " + str(error)[:200], "re": message.get("n")})
                except Exception:
                    pass

    # -- what each message does --------------------------------------------------
    def handle(self, link_id, message):
        kind = message.get("t")
        n = message.get("n")
        if kind == "hello":
            name = self.agent.profile.get("name") or "Luma"
            return self.send(link_id, {"t": "reply", "re": n, "text": f"Hey, it's {name}. I'm on your phone now too, so you can reach me from anywhere. Ask me anything, or tell me who to text."})
        if kind == "text":
            text = " ".join(str(message.get("text", "")).split())[:4000]
            if not text:
                return None
            if self.agent.mode == "kids":
                return self.send(link_id, {"t": "reply", "re": n, "text": "I'm in kids mode at home right now, so I can't help from here. Switch modes on Luma."})
            try:
                result = self.agent.chat(text, channel="app")
            except ValueError as error:
                result = {"text": str(error)}
            reply = {"t": "reply", "re": n, "text": result.get("text") or result.get("summary") or "Done."}
            card = card_for(result)
            if card:
                reply["card"] = card
            if result.get("noticed"):
                reply["noticed"] = [m.get("text") for m in result["noticed"] if isinstance(m, dict)][:3]
            if getattr(self.agent, "on_result", None):
                self.agent.on_result({**result, "you": text, "channel": "app"})
            return self.send(link_id, reply)
        if kind in {"confirm", "cancel"}:
            action = str(message.get("action", ""))
            if kind == "cancel":
                try:
                    self.agent.cancel(action)
                except ValueError:
                    pass
                return self.send(link_id, {"t": "done", "re": n, "action": action, "state": "cancelled", "text": "Okay, I won't send it."})
            try:
                result = self.agent.confirm(action, str(message.get("token", "")))
            except ValueError as error:
                return self.send(link_id, {"t": "done", "re": n, "action": action, "state": "failed", "text": "I didn't send it: " + str(error)})
            state = result.get("state", "done")
            text = result.get("text") or result.get("summary") or ("Done." if state == "succeeded" else "That didn't go through.")
            return self.send(link_id, {"t": "done", "re": n, "action": action, "state": state, "text": text})
        return None

    def send(self, link_id, message, notify=False):
        return self.send_many([link_id], message, notify)

    def send_many(self, link_ids, message, notify=False):
        state = self._load()
        body = {"v": 1, "ts": int(self.clock() * 1000), **message}
        batch = []
        for link_id in link_ids:
            link = state["links"].get(link_id)
            if not link:
                continue
            batch.append({"link_id": link_id, "payload": seal(unb64u(link["key"]), link["pair"], "down", body),
                          "client_ref": secrets.token_urlsafe(12), **({"notify": True} if notify else {})})
        if not batch:
            return None
        return self.cloud.app_reply(batch[:10])

    def notify(self, event):
        """Something Luma would say out loud at home also reaches your phone."""
        if not event or not event.get("text") or self.agent.mode == "kids":
            return None
        links = list(self._load()["links"])
        if not links:
            return None
        kind = event.get("type", "")
        if kind in NOTICE_LABELS:
            message = {"t": "notice", "label": NOTICE_LABELS[kind], "text": event["text"]}
        else:
            message = {"t": "reply", "text": event["text"]}
        try:
            return self.send_many(links, message, notify=True)
        except ProviderError:
            return None
