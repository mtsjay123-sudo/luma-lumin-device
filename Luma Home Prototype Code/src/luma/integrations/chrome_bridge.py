"""Luma for Chrome: Luma drives the owner's own Chrome through a small extension.

The extension pairs once with a short code shown in Luma, then keeps one request open
to Luma on this computer (127.0.0.1) and does what Luma asks: open a tab, play music in
a background tab, read the page that's open. It never types passwords and never sends
anything off this computer; Luma's own approval rules still decide what needs an OK.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import queue
import secrets
import threading
import time
from pathlib import Path

KINDS = {"open", "play", "read", "tabs"}
STALE = 30  # a step nobody picked up in this long is dropped, so nothing old runs by surprise later


def install(source, port=8095, target=None):
    """Copy the extension to a plain folder (Chrome's "Load unpacked" can't open one inside the app) and point it at this Luma."""
    folder = Path(target or os.environ.get("LUMA_CHROME_DIR") or Path.home() / "Luma for Chrome")
    folder.mkdir(parents=True, exist_ok=True)
    for file in Path(source).iterdir():
        if file.suffix in {".json", ".js", ".html", ".png", ".css"}:
            text = file.read_bytes()
            if file.suffix in {".js", ".html"}:
                text = text.replace(b"127.0.0.1:8095", f"127.0.0.1:{int(port)}".encode())
            (folder / file.name).write_bytes(text)
    return folder


class ChromeBridge:
    def __init__(self, store, clock=time.time):
        self.store, self.clock = store, clock
        self.commands = queue.Queue()
        self.results, self.waiting = {}, {}
        self.last_seen = 0
        self.lock = threading.Lock()

    # -- pairing ---------------------------------------------------------------
    def code(self):
        """The short code the owner types into the extension once. A new one after each pairing."""
        current = self.store.setting("chrome_code")
        if not current:
            current = "".join(secrets.choice("ABCDEFGHJKMNPQRSTUVWXYZ23456789") for _ in range(6))
            self.store.set_setting("chrome_code", current)
        return current

    def pair(self, code):
        if not code or not hmac.compare_digest(str(code).strip().upper().replace("-", ""), self.code()):
            raise ValueError("That code doesn't match. Use the one shown in Luma under Connectors.")
        token = secrets.token_urlsafe(32)
        self.store.set_setting("chrome_token", hashlib.sha256(token.encode()).hexdigest())
        self.store.set_setting("chrome_code", None)  # one use
        self.last_seen = self.clock()
        return token

    def valid(self, token):
        saved = self.store.setting("chrome_token")
        return bool(saved and token and hmac.compare_digest(hashlib.sha256(str(token).encode()).hexdigest(), saved))

    def connected(self):
        return self.clock() - self.last_seen < 60

    def status(self):
        return {"paired": bool(self.store.setting("chrome_token")), "connected": self.connected(), "code": self.code()}

    def unpair(self):
        self.store.set_setting("chrome_token", None)
        self.last_seen = 0

    # -- commands ----------------------------------------------------------------
    def send(self, kind, wait=0, **args):
        if kind not in KINDS: raise ValueError("Unknown Chrome step.")
        ident = secrets.token_hex(6)
        done = threading.Event()
        with self.lock:
            self.waiting[ident] = done
        self.commands.put({"id": ident, "kind": kind, "at": self.clock(), **args})
        if not wait:
            return {"id": ident}
        done.wait(wait)
        with self.lock:
            self.waiting.pop(ident, None)
            return self.results.pop(ident, None)

    def next(self, timeout=25):
        """The extension's open request: the next thing to do, or nothing after a while."""
        self.last_seen = self.clock()
        deadline = time.monotonic() + timeout
        try:
            while True:
                left = deadline - time.monotonic()
                if left <= 0:
                    return None
                command = self.commands.get(timeout=left)
                if self.clock() - command.get("at", 0) <= STALE:
                    return command
        except queue.Empty:
            return None
        finally:
            self.last_seen = self.clock()

    def done(self, ident, result):
        with self.lock:
            self.results[str(ident)] = result if isinstance(result, dict) else {"result": result}
            event = self.waiting.get(str(ident))
        if event: event.set()
