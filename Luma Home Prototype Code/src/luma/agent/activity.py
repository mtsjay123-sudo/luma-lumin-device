"""What Luma is doing right now, so you can watch and steer it.

A long job (comparing prices across stores, a helper's scheduled run) reports
its steps, a live picture of Luma's browser, and its results here. The desktop
polls it and offers Pause, Stop and Take over; the job checks those between steps.
"""
from __future__ import annotations

import base64
import secrets
import threading
import time


class Stopped(Exception):
    """The owner pressed Stop."""


class Activity:
    def __init__(self, clock=time.time):
        self.clock = clock
        self.lock = threading.Lock()
        self._resume = threading.Event()
        self._resume.set()
        self._stop = threading.Event()
        self.current = None
        self._image = None
        self.recent = []  # finished jobs, newest first
        self.on_finish = None  # told about each finished job (how long it took goes on the Overview page)

    def start(self, kind, title, background=False):
        """background jobs (a helper's scheduled run) give way as soon as the owner asks for something."""
        with self.lock:
            self._stop.clear()
            self._resume.set()
            self._image = None
            self.current = {"id": secrets.token_hex(6), "kind": kind, "title": title, "state": "running", "started": self.clock(), "background": bool(background),
                            "steps": [], "url": None, "page_title": None, "results": None, "summary": None, "shot": 0}
            return self.current["id"]

    def step(self, text, *, done=False):
        with self.lock:
            if not self.current: return
            steps = self.current["steps"]
            if steps and not steps[-1]["done"]:
                steps[-1]["done"] = True
            steps.append({"text": str(text)[:160], "done": done, "at": self.clock()})
            del steps[:-12]
        self.check()

    def shot(self, jpeg_b64, url=None, title=None):
        with self.lock:
            if not self.current: return
            self._image = base64.b64decode(jpeg_b64) if jpeg_b64 else None
            self.current.update(url=url, page_title=(title or "")[:160], shot=self.current["shot"] + 1)

    def results(self, items):
        with self.lock:
            if self.current: self.current["results"] = items

    def finish(self, summary, state="done"):
        with self.lock:
            if not self.current: return
            for step in self.current["steps"]: step["done"] = True
            self.current.update(state=state, summary=str(summary)[:400], finished=self.clock())
            self.recent = ([dict(self.current)] + self.recent)[:10]
            job = dict(self.current)
        if self.on_finish:
            try:
                self.on_finish(job)
            except Exception:
                pass

    # -- the owner's controls ---------------------------------------------------
    def pause(self):
        with self.lock:
            if self.current and self.current["state"] == "running":
                self.current["state"] = "paused"
                self._resume.clear()
        return self.view()

    def resume(self):
        with self.lock:
            if self.current and self.current["state"] == "paused":
                self.current["state"] = "running"
        self._resume.set()
        return self.view()

    def stop(self):
        self._stop.set()
        self._resume.set()
        with self.lock:
            if self.current and self.current["state"] in {"running", "paused"}:
                self.current["state"] = "stopping"
        return self.view()

    def check(self):
        """Called by the job between steps: waits while paused, raises if stopped."""
        while not self._resume.wait(0.5):
            if self._stop.is_set(): break
        if self._stop.is_set():
            raise Stopped()

    # -- for the screen ---------------------------------------------------------
    def view(self):
        with self.lock:
            return dict(self.current) if self.current else None

    def image(self):
        with self.lock:
            return self._image

    def background_running(self):
        with self.lock:
            return bool(self.current and self.current.get("background") and self.current["state"] in {"running", "paused"})

    def busy(self):
        with self.lock:
            return bool(self.current and self.current["state"] in {"running", "paused", "stopping"})
