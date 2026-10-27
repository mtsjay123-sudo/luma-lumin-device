"""Luma's brain in a process of its own.

The local model runs native code (llama.cpp on the GPU). When native code crashes —
out of memory, a graphics driver fault, a model too big for this computer — it takes
its whole process with it. So the model lives here, in a child process, and the rest
of Luma (the window, memories, reminders, everything) keeps running if it falls over.

When the brain process dies in the middle of a thought, Luma restarts it on a safer
footing and tries once more, so the person usually just gets their answer a moment
later:
  1. first crash on the graphics chip: think on the CPU instead
  2. crash with the bigger brain: go back to the fast one
  3. still crashing: rest for a few minutes and say plainly what's wrong
"""
from __future__ import annotations

import multiprocessing as mp
import os
import threading
import time
from pathlib import Path

CALLS = ("plan", "rewrite", "generate", "look")


class BrainCrashed(RuntimeError):
    """The brain process stopped in the middle of a thought (it's been restarted)."""


class BrainResting(RuntimeError):
    """The brain kept crashing; it's resting before trying again."""


def _child(conn, env):
    """Runs in the brain process: load the model when asked, answer calls, stop a thought when told."""
    os.environ.update(env)
    from luma.llm import inference
    cancel = threading.Event()
    inbox = []
    lock = threading.Lock()

    def listen():
        while True:
            try:
                message = conn.recv()
            except (EOFError, OSError):
                os._exit(0)  # Luma went away: so does its brain
            if message[0] == "cancel":
                cancel.set()
            else:
                with lock:
                    inbox.append(message)

    threading.Thread(target=listen, daemon=True).start()
    if env.get("LUMA_BRAIN_OVERRIDE"):
        inference.use_model_path(Path(env["LUMA_BRAIN_OVERRIDE"]))
    while True:
        with lock:
            message = inbox.pop(0) if inbox else None
        if message is None:
            time.sleep(0.01)
            continue
        if message[0] == "ping":
            conn.send(("ok", {"pid": os.getpid()}))
            continue
        _, op, kwargs, streaming = message
        cancel.clear()
        try:
            if streaming:
                kwargs["on_text"] = lambda text: conn.send(("delta", text))
            kwargs["cancel_event"] = cancel
            impl = os.environ.get("LUMA_BRAIN_IMPL")  # tests stand a fake brain in here
            if impl:
                import importlib
                home = importlib.import_module(impl)
            elif op == "look":
                from luma.skills import vision as home
            else:
                home = inference
            result = getattr(home, "_" + op + "_here")(**kwargs)
            conn.send(("ok", result))
        except inference.GenerationCancelled as error:
            conn.send(("err", "cancelled", str(error)))
        except Exception as error:  # an ordinary Python error: the brain is fine, this answer isn't
            conn.send(("err", type(error).__name__, str(error)[:500]))


class Brain:
    """The parent's handle on the brain process."""
    def __init__(self):
        self.proc = None
        self.conn = None
        self.lock = threading.RLock()
        self.gpu = os.environ.get("LUMA_GPU_LAYERS", "-1") != "0"
        from luma.llm import inference
        self.override = inference._override  # the bigger brain's file, when chosen
        self.crashes = []  # (time, what it was doing, exit code, settings)
        self.resting_until = 0.0
        self.note = ""
        self.on_change = None  # told when the brain had to fall back to something smaller

    # -- the process ------------------------------------------------------
    def _env(self):
        env = {"LUMA_BRAIN_CHILD": "1"}
        if not self.gpu:
            env["LUMA_GPU_LAYERS"] = "0"
        if self.override:
            env["LUMA_BRAIN_OVERRIDE"] = str(self.override)
        return env

    def _start(self):
        ctx = mp.get_context("spawn")  # a clean process: no threads or locks copied from this one
        parent, child = ctx.Pipe()
        self.proc = ctx.Process(target=_child, args=(child, self._env()), name="luma-brain", daemon=True)
        self.proc.start()
        child.close()
        self.conn = parent

    def _alive(self):
        return self.proc is not None and self.proc.is_alive()

    def stop(self):
        with self.lock:
            if self.proc is not None:
                try:
                    self.proc.kill()
                    self.proc.join(2)
                except Exception:
                    pass
            self.proc = self.conn = None

    def use_model_path(self, path):
        """The bigger brain (or None for the fast one): the next thought loads it fresh."""
        with self.lock:
            if (path or None) != self.override:
                self.override = path or None
                self.stop()

    # -- a thought ----------------------------------------------------------
    def call(self, op, kwargs, cancel_event=None, on_text=None):
        if op not in CALLS:
            raise ValueError(op)
        for attempt in (1, 2):
            try:
                return self._call_once(op, dict(kwargs), cancel_event, on_text)
            except BrainCrashed:
                if attempt == 2 or time.time() < self.resting_until:
                    raise
        raise BrainCrashed("My brain stopped unexpectedly.")

    def _call_once(self, op, kwargs, cancel_event, on_text):
        from luma.llm.inference import GenerationCancelled
        while not self.lock.acquire(timeout=0.05):  # waiting on another thought: still stoppable
            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelled("Conversation interrupted.")
        try:
            return self._call_locked(op, kwargs, cancel_event, on_text)
        finally:
            self.lock.release()

    def _call_locked(self, op, kwargs, cancel_event, on_text):
        from luma.llm.inference import GenerationCancelled
        if True:
            if time.time() < self.resting_until:
                raise BrainResting(self.note or "My brain is resting after a few crashes. Try again in a few minutes.")
            if not self._alive():
                self._start()
            conn, proc = self.conn, self.proc
            conn.send(("call", op, kwargs, on_text is not None))
            told_to_stop = False
            while True:
                if cancel_event is not None and cancel_event.is_set() and not told_to_stop:
                    try:
                        conn.send(("cancel",))
                    except OSError:
                        pass
                    told_to_stop = True
                try:
                    ready = conn.poll(0.05)
                except (EOFError, OSError):
                    ready = False
                if ready:
                    try:
                        message = conn.recv()
                    except (EOFError, OSError):
                        message = None
                    if message is not None:
                        if message[0] == "delta":
                            if on_text is not None:
                                on_text(message[1])
                            continue
                        if message[0] == "ok":
                            return message[1]
                        if message[1] == "cancelled":
                            raise GenerationCancelled(message[2])
                        raise _rebuild(message[1], message[2])
                if not proc.is_alive():
                    self._crashed(op, proc.exitcode)
                    raise BrainCrashed("My brain stopped unexpectedly.")

    def to_processor(self):
        """Its answers came out garbled on the graphics chip: the next thought starts a fresh brain process on the processor."""
        with self.lock:
            if not self.gpu:
                return
            self.gpu = False
            self.note = "My brain came out garbled on the graphics chip, so I switched to thinking on the processor. It's a bit slower but right."
            self.stop()

    def _crashed(self, op, code):
        now = time.time()
        self.crashes = [c for c in self.crashes if now - c["at"] < 900] + [{"at": now, "op": op, "code": code, "gpu": self.gpu, "big": bool(self.override)}]
        self.proc = self.conn = None
        if self.gpu:
            self.gpu = False
            self.note = "My brain crashed on the graphics chip, so I switched to thinking on the processor. It's a bit slower but steady."
        elif self.override:
            self.override = None
            self.note = "The bigger brain needs more free memory than this computer has right now, so I went back to the fast one."
            if self.on_change:
                try:
                    self.on_change("small")
                except Exception:
                    pass
        elif len(self.crashes) >= 3:
            self.resting_until = now + 300
            self.note = ("My brain keeps crashing on this computer, so it's resting for 5 minutes. "
                         "Closing other big apps usually helps; the cloud brain in Settings never has this problem.")

    def state(self):
        return {"running": self._alive(), "pid": self.proc.pid if self._alive() else None, "gpu": self.gpu, "big": bool(self.override),
                "crashes": len(self.crashes), "resting": max(0, round(self.resting_until - time.time())), "note": self.note}


def _rebuild(name, message):
    """The brain's ordinary errors arrive as the same kinds of errors Luma already handles."""
    known = {"ValueError": ValueError, "FileNotFoundError": FileNotFoundError, "RuntimeError": RuntimeError, "MemoryError": MemoryError}
    return known.get(name, RuntimeError)(message)


_brain = None
_brain_lock = threading.Lock()


def enabled():
    """The brain gets its own process when Luma is serving (not in tests, not inside the brain itself)."""
    return os.environ.get("LUMA_BRAIN_WORKER") == "1" and os.environ.get("LUMA_BRAIN_CHILD") != "1"


def brain():
    global _brain
    with _brain_lock:
        if _brain is None:
            _brain = Brain()
        return _brain
