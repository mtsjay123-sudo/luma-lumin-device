"""The huge brain: an open model of hundreds of billions of parameters, run on this Mac by colibri.

colibri (github.com/JustVugg/colibri, Apache 2.0) runs very large mixture-of-experts models on an
ordinary computer: the part of the model every word needs stays in memory and the experts are read
from the SSD when the model asks for them. On a Mac Studio with enough memory the whole of GLM-5.2
(744B) fits and nothing streams. Luma doesn't carry colibri's code: it installs colibri with colibri's
own setup, starts it in the background, and talks to it over its local OpenAI-compatible address
(http://127.0.0.1:8000/v1). Nothing leaves this computer.

It is slow next to the fast brain (about 0.4 to 2 words a second for GLM-5.2 on a big Mac, by
colibri's own measurements), so Luma keeps talking with the fast brain and hands the huge one the
work worth waiting for: projects, research write-ups, and the final answer on a hard question.
Same contract as the other brains: a dict that's either a reply or one tool proposal.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from luma.llm.prompts import build_plan_prompt, normalize_profile

REPO = "https://github.com/JustVugg/colibri"
DEFAULT_BASE = "http://127.0.0.1:8000/v1"
WHOLE_GLM_RAM_GB = 480  # GLM-5.2's 429 GB download fits in memory with room for the system: nothing streams
WHOLE_GLM_DISK_GB = 450

installing = {"running": False, "step": None, "error": None}
_ready = {"at": 0.0, "model": None, "base": None}


class NotRunning(Exception):
    """colibri isn't answering on this computer."""


def home():
    return Path(os.environ.get("LUMA_COLIBRI_DIR") or Path.home() / "colibri")


def _coli():
    return home() / "c" / "coli"


def installed():
    return _coli().exists()


def pick_model(ram_gb, disk_free_gb):
    """Which model to ask colibri's setup for. With the memory for all of GLM-5.2, the reference model whole; otherwise
    colibri's own recommendation for this machine (the most capable model that runs here), so nothing is guessed."""
    if ram_gb >= WHOLE_GLM_RAM_GB and disk_free_gb >= WHOLE_GLM_DISK_GB:
        return "glm-5.2"
    return None


def _run(args, timeout=20):
    return subprocess.run([sys.executable, str(_coli())] + list(args), cwd=str(home()), capture_output=True, text=True, timeout=timeout)


def server_status():
    """What `coli status --json` says: {"state": ready|loading|stopped|..., "base": ..., "model": ..., "tok_s": ...}."""
    if not installed():
        return {"state": "not installed"}
    try:
        out = _run(["status", "--json"])
        data = json.loads(out.stdout or "{}")
    except (OSError, subprocess.SubprocessError, ValueError):
        return {"state": "unknown"}
    server = data.get("server") or {}
    urls = server.get("urls") or {}
    return {"state": server.get("state") or "stopped", "base": (urls.get("openai_base_url") or DEFAULT_BASE).rstrip("/"),
            "model": server.get("model_id"), "tok_s": server.get("tokens_per_second")}


def base():
    return (os.environ.get("LUMA_COLIBRI_BASE") or _ready["base"] or DEFAULT_BASE).rstrip("/")


def ready(max_age=20):
    """The model id colibri is serving right now, or None. Asked of the server itself (GET /v1/models), and remembered
    for a few seconds so routing a reply never waits on it."""
    if time.time() - _ready["at"] < max_age:
        return _ready["model"]
    model = None
    try:
        with urllib.request.urlopen(base() + "/models", timeout=1.5) as r:
            data = json.load(r)
        models = data.get("data") or []
        model = (models[0] or {}).get("id") if models else None
    except (urllib.error.URLError, OSError, ValueError, TimeoutError, AttributeError):
        model = None
    _ready.update(at=time.time(), model=model)
    return model


def forget():
    _ready.update(at=0.0, model=None)


def _post(path, body, timeout=900):
    req = urllib.request.Request(base() + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer local"}, method="POST")
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"colibri said {error.code}: {detail}") from error
    except (urllib.error.URLError, OSError, TimeoutError) as error:
        forget()
        raise NotRunning("The huge brain isn't answering on this computer.") from error


def _history(messages, limit=40):
    recent = [{"role": m["role"], "content": m["content"]} for m in messages
              if m.get("role") in {"user", "assistant"} and isinstance(m.get("content"), str) and m["content"].strip()][-limit:]
    while recent and recent[0]["role"] != "user":
        recent.pop(0)
    return recent


def _stream(response, cancel_event=None, on_delta=None):
    """Read an OpenAI-style server-sent stream, handing each piece of text on as it arrives."""
    from luma.llm.inference import GenerationCancelled
    text = []
    with response:
        for raw in response:
            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelled("Conversation interrupted.")
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                delta = (json.loads(data).get("choices") or [{}])[0].get("delta") or {}
            except (ValueError, AttributeError, IndexError):
                continue
            piece = delta.get("content")
            if isinstance(piece, str) and piece:
                text.append(piece)
                if on_delta is not None:
                    on_delta(piece)
    return "".join(text)


def plan(messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None):
    """Same contract as luma.llm.inference.plan. Streams, so the words show up (and can be spoken) as they're written."""
    from luma.llm.kimi import _json_object
    from luma.llm.streaming import ReplyTextStream
    model = ready()
    if not model:
        raise NotRunning("The huge brain isn't running on this computer.")
    profile = normalize_profile(profile)
    now = datetime.now(ZoneInfo(os.environ.get("LUMA_TIMEZONE", "America/New_York"))).isoformat()
    recent = _history(messages)
    if not recent:
        raise ValueError("Nothing to answer yet.")
    body = {"model": model, "stream": True, "max_tokens": 2048, "temperature": 0.6,
            "messages": [{"role": "system", "content": build_plan_prompt(memories, tools, mode, profile, now)}] + recent,
            "response_format": {"type": "json_object"}}
    stream = ReplyTextStream(on_text) if on_text is not None else None
    raw = _stream(_post("/chat/completions", body), cancel_event, stream.feed if stream else None)
    if not raw.strip():
        raise ValueError("Local model returned no usable reply.")
    return _json_object(raw)


def rewrite(prompt, max_tokens=300, cancel_event=None):
    model = ready()
    if not model:
        raise NotRunning("The huge brain isn't running on this computer.")
    body = {"model": model, "stream": True, "max_tokens": max(max_tokens, 256), "temperature": 0.2,
            "messages": [{"role": "system", "content": "You rewrite messages into clear instructions. Answer with the rewrite only."},
                         {"role": "user", "content": prompt}]}
    return _stream(_post("/chat/completions", body, timeout=300), cancel_event).strip()


# -- getting it onto this Mac ---------------------------------------------------
def _disk_free_gb(path):
    try:
        probe = path if path.exists() else path.parent
        return shutil.disk_usage(probe).free / 2 ** 30
    except OSError:
        return 0.0


def install(ram_gb, log=None):
    """Clone colibri, run its own setup (it checks the machine, builds the engine and downloads the model, resuming if
    stopped), then start it in the background. Runs on its own thread; `installing` says where it is."""
    if installing["running"]:
        return dict(installing)
    model = pick_model(ram_gb, _disk_free_gb(Path.home()))
    installing.update(running=True, step="Getting colibri", error=None)

    def work():
        target = home()
        logfile = Path(log or target.parent / "colibri-luma-setup.log")
        try:
            with open(logfile, "a", encoding="utf-8") as out:
                if not installed():
                    if not shutil.which("git"):
                        raise RuntimeError("This Mac needs git first. Install the Xcode command line tools (xcode-select --install).")
                    subprocess.run(["git", "clone", "--depth", "1", REPO, str(target)], stdout=out, stderr=out, check=True, timeout=1800)
                installing["step"] = "Building it and downloading the model (this can take hours; it resumes if stopped)"
                setup = ["setup", "--yes", "--no-start"] + (["--model", model] if model else [])
                subprocess.run([sys.executable, str(_coli())] + setup, cwd=str(target), stdout=out, stderr=out, check=True)
                installing["step"] = "Starting it"
                start()
        except Exception as error:  # a failed step is said plainly; the next run of the same setup picks up where it stopped
            installing["error"] = f"{installing['step']} didn't finish: {error}"[:300]
        finally:
            installing.update(running=False, step=None if not installing["error"] else installing["step"])

    threading.Thread(target=work, daemon=True, name="colibri-install").start()
    return dict(installing)


def start():
    """Start colibri's server in the background (it keeps its own log). Safe to call when it's already running."""
    if not installed():
        return False
    try:
        _run(["start", "--background", "--no-browser"], timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    where = server_status().get("base")
    if where:
        _ready["base"] = where  # it moves to another port when 8000 is taken
    forget()
    return True


def stop():
    if installed():
        try:
            _run(["stop"], timeout=60)
        except (OSError, subprocess.SubprocessError):
            pass
    forget()
