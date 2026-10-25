"""Luma in the terminal: `luma work "build me a pitch deck and a website for my taco truck"`.

The work runs on whichever Luma is around: your Luma device (--device, over Luma Link), the Luma app
already running on this computer, or, if neither, Luma itself started right here in the terminal. You
see the plan, each specialist's step as it happens, and the checks; anything risky asks y/n here (or
--yes to allow it up front). Ctrl-C stops cleanly and `luma resume` picks it back up. Work done on the
device downloads its package into the current folder when it finishes.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DONE_STATES = {"done", "stopped", "failed"}


class Paint:
    def __init__(self, stream=sys.stdout):
        self.on = stream.isatty() and not os.environ.get("NO_COLOR")

    def __call__(self, text, code):
        return f"\033[{code}m{text}\033[0m" if self.on else text

    def dim(self, t): return self(t, "2")
    def bold(self, t): return self(t, "1")
    def ok(self, t): return self(t, "32")
    def warn(self, t): return self(t, "33")
    def bad(self, t): return self(t, "31")
    def accent(self, t): return self(t, "35")


paint = Paint()
MARK = {"done": paint.ok("✓"), "attention": paint.warn("!"), "waiting": paint.warn("…"), "stopped": paint.dim("■"), "skipped": paint.dim("–"),
        "running": paint.accent("▸"), "pending": paint.dim("·")}


def say(line=""):
    print(line, flush=True)


def ask_yes(question, assume_yes):
    if assume_yes:
        say(paint.dim("  (allowed by --yes) ") + question)
        return True
    if not sys.stdin.isatty():
        say(paint.warn("  Waiting for your OK: ") + question + paint.dim("  Run again with --yes to allow it."))
        return False
    answer = input(paint.warn("  ? ") + question + " [y/N] ").strip().lower()
    return answer in {"y", "yes"}


class Renderer:
    """Prints a run as it moves: the plan once, then each step's state changes and progress lines."""

    def __init__(self):
        self.seen_plan, self.states, self.logs = None, {}, {}

    def plan(self, steps):
        key = json.dumps([(s["n"], s["title"]) for s in steps])
        if key == self.seen_plan:
            return
        self.seen_plan = key
        say(paint.bold("Plan"))
        for s in steps:
            say(f"  {s['n']:>2}  {s['title']:<42} {paint.dim(s['agent'] + ' agent')}")
        say()

    def step(self, s):
        state = s.get("state")
        if self.states.get(s["n"]) == state:
            for line in (s.get("log") or [])[-3:]:
                if line not in self.logs.setdefault(s["n"], set()):
                    self.logs[s["n"]].add(line)
                    say(paint.dim(f"      {line}"))
            return
        self.states[s["n"]] = state
        if state == "running":
            say(f"{MARK['running']} {s['n']:>2}  {s['title']}  {paint.dim('· ' + s['agent'] + ' agent working')}")
        elif state in {"done", "attention", "waiting", "stopped"}:
            extra = f"{s.get('seconds')}s" if s.get("seconds") is not None else ""
            files = s.get("files") or []
            say(f"{MARK[state]} {s['n']:>2}  {s['title']}  {paint.dim(extra + (f' · {len(files)} file' + ('s' if len(files) != 1 else '') if files else ''))}")
            if s.get("summary") and state != "running":
                say(paint.dim(f"      {s['summary'][:220]}"))
            for c in s.get("checks") or []:
                if not c["ok"]:
                    say((paint.warn if c.get("blocking", True) else paint.dim)(f"      {'needs a look' if c.get('blocking', True) else 'note'}: {c['check']}" + (f" — {c['detail'][:160]}" if c.get("detail") else "")))


def finish(run, where, folder=None):
    say()
    state = run.get("state")
    color = paint.ok if state == "done" else paint.warn
    say(color(paint.bold({"done": "Done.", "stopped": "Stopped.", "waiting": "Waiting for you."}.get(state, state or "") + " ")) + (run.get("summary") or ""))
    if folder:
        say(paint.dim("Files: ") + str(folder))
    if state in {"stopped", "waiting"}:
        say(paint.dim("Pick it back up any time: ") + f"luma resume {where}")


# -- where the work runs ---------------------------------------------------------------
class Local:
    """Luma started right here in the terminal."""
    label = "in this terminal"

    def __init__(self, assume_yes=False, use_model=True):
        from luma.agent.runtime import Agent
        from luma.work.engine import for_agent
        self.agent = Agent(use_model=use_model)
        self.engine = for_agent(self.agent, approver=lambda q: ask_yes(q, assume_yes))

    def projects(self):
        from luma.control.work_api import view
        return [view(self.engine, p) for p in self.engine.projects.list()]

    def project(self, ident):
        from luma.control.work_api import view
        return view(self.engine, self.find(ident), detail=True)

    def find(self, ident):
        projects = self.engine.projects.list()
        match = next((p for p in projects if p["id"] == ident), None) or next((p for p in projects if p["name"].lower().startswith(str(ident).lower())), None)
        if not match:
            raise ValueError(f"No project called {ident}.")
        return match

    def work(self, request, project=None, resume=False):
        from luma.control.work_api import name_for
        target = self.find(project) if project else (None if resume else self.engine.projects.create(name_for(request), request))
        if resume:
            target = target or self.find(request)
            unfinished = [r for r in target.get("runs", []) if r.get("state") in {"stopped", "waiting", "running", "planning"}]
            if not unfinished:
                raise ValueError("There's nothing unfinished in that project.")
        say(paint.accent("◆ Luma") + f" · {paint.bold(target['name'])} " + paint.dim(f"({self.label})"))
        renderer = Renderer()
        cancel, result = threading.Event(), {}

        def listen(event):
            if event.get("project") != target["id"]:
                return
            if event["type"] == "plan":
                renderer.plan(event["steps"])
            elif event["type"] == "step":
                run = (self.engine.projects.get(target["id"]).get("runs") or [{}])[-1]
                step = next((s for s in run.get("steps", []) if s["n"] == event["step"]), None)
                if step:
                    renderer.step(step)
            elif event["type"] == "progress" and event.get("message"):
                say(paint.dim(f"      {event['message']}"))
        self.engine.listeners.append(listen)

        def go():
            try:
                result["run"] = self.engine.start(target["id"], request, cancel=cancel, resume=unfinished[-1]["id"] if resume else None)
            except Exception as error:
                result["error"] = error
        worker = threading.Thread(target=go, daemon=True)
        worker.start()
        try:
            while worker.is_alive():
                worker.join(0.3)
        except KeyboardInterrupt:
            say(paint.warn("\nStopping after this step…"))
            cancel.set()
            worker.join()
        if "error" in result:
            raise result["error"]
        finish(result["run"], target["id"], self.engine.projects.folder(target["id"]))
        return result["run"]

    def stop(self, ident):
        return {"stopped": self.engine.stop(self.find(ident)["id"])}

    def approve(self, ident):
        self.engine.allow_code(self.find(ident)["id"])
        return {"approved": True}


class Remote:
    """Luma running somewhere else: the app on this computer, or your Luma device."""

    def __init__(self, label, get, post, download=None):
        self.label, self._get, self._post, self.download = label, get, post, download

    def projects(self):
        return self._get("projects", {})["projects"]

    def find(self, ident):
        projects = self.projects()
        match = next((p for p in projects if p["id"] == ident), None) or next((p for p in projects if p["name"].lower().startswith(str(ident).lower())), None)
        if not match:
            raise ValueError(f"No project called {ident}.")
        return match

    def project(self, ident):
        return self._get("project", {"id": self.find(ident)["id"]})["project"]

    def work(self, request, project=None, resume=False, assume_yes=False):
        if resume:
            target = self.find(project or request)
            started = self._post("resume", {"id": target["id"]})["project"]
        else:
            body = {"request": request}
            if project:
                body["id"] = self.find(project)["id"]
            started = self._post("run", body)["project"]
        pid = started["id"]
        say(paint.accent("◆ Luma") + f" · {paint.bold(started['name'])} " + paint.dim(f"({self.label})"))
        renderer, asked, last_run = Renderer(), set(), None
        try:
            while True:
                time.sleep(1.0)
                project = self._get("project", {"id": pid})["project"]
                run = project.get("run") or {}
                if run.get("steps"):
                    renderer.plan(run["steps"])
                    for s in run["steps"]:
                        renderer.step(s)
                if run.get("state") == "waiting" and run.get("id") not in asked:
                    asked.add(run.get("id"))
                    waiting = next((s for s in run.get("steps", []) if s.get("state") == "waiting"), {})
                    if ask_yes(waiting.get("summary") or "Allow this step?", assume_yes):
                        self._post("approve", {"id": pid, "confirm": True})
                        continue
                    finish(run, pid)
                    return run
                if run.get("state") in DONE_STATES and not project.get("working"):
                    last_run = run
                    break
        except KeyboardInterrupt:
            say(paint.warn("\nStopping after this step…"))
            self._post("stop", {"id": pid})
            return {"state": "stopped"}
        saved = self.download(pid, project) if self.download and last_run.get("state") == "done" else None
        finish(last_run, pid, saved)
        return last_run

    def stop(self, ident):
        return self._post("stop", {"id": self.find(ident)["id"]})

    def approve(self, ident):
        return self._post("approve", {"id": self.find(ident)["id"], "confirm": True})


def app_on_this_computer():
    """The Luma app's server, if it's running here: its port and token come from a file only this account can read."""
    from luma.config import STATE_DIR
    try:
        info = json.loads((STATE_DIR / "cli.json").read_text())
    except (OSError, ValueError):
        return None
    base, token = f"http://127.0.0.1:{int(info['port'])}", info["token"]

    def call(method, name, data=None, params=None):
        url = f"{base}/api/work/{name}" + ("?" + urllib.parse.urlencode(params) if params else "")
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json",
                                                                              "Host": f"127.0.0.1:{int(info['port'])}"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # straight to this computer, never through a proxy
        try:
            with opener.open(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as error:
            raise ValueError(json.loads(error.read() or b"{}").get("error") or f"Luma answered {error.code}") from None
    try:
        call("GET", "projects")
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return Remote("on this computer's Luma app", lambda n, p: call("GET", n, params=p), lambda n, d: call("POST", n, d))


def device():
    """Your Luma device, over Luma Link (pair this computer from the Luma app first)."""
    from types import SimpleNamespace
    from luma.config import STATE_DB_PATH, STATE_KEY_PATH
    from luma.control.link import LinkClient
    from luma.memory.store import Store
    store = Store(STATE_DB_PATH, STATE_KEY_PATH)
    client = LinkClient(SimpleNamespace(store=store, clock=time.time))
    if not client.device():
        raise ValueError("This computer isn't paired with a Luma device yet. Open Luma, go to Settings → Your Luma device, and pair it.")
    name = client.device().get("name") or "Luma"

    def get(n, params):
        return client.call("GET", f"/link/work/{n}" + ("?" + urllib.parse.urlencode(params) if params else ""), timeout=30)

    def post(n, data):
        return client.call("POST", f"/link/work/{n}", data, timeout=30)

    def download(pid, project):
        """Bring the finished package from the device into the current folder."""
        from luma.control.link import pinned_request  # noqa: F401  (same pinned connection as every call)
        package = next((f["path"] for f in project.get("files", []) if f["path"].startswith("package/") and f["path"].endswith(".zip")), None)
        if not package:
            details = get("project", {"id": pid})["project"]
            package = next((f["path"] for f in details.get("files", []) if f["path"].startswith("package/") and f["path"].endswith(".zip")), None)
        if not package:
            return None
        raw = client.call_bytes("GET", "/link/work/file?" + urllib.parse.urlencode({"id": pid, "path": package}), timeout=120)
        target = Path.cwd() / Path(package).name
        target.write_bytes(raw)
        return target
    return Remote(f"on {name}", get, post, download)


def pick(on_device=False, assume_yes=False, use_model=True):
    if on_device:
        return device()
    return app_on_this_computer() or Local(assume_yes=assume_yes, use_model=use_model)


def show_projects(target):
    projects = target.projects()
    if not projects:
        say("No projects yet. Start one: luma work \"research my idea and make a 10-slide deck\"")
        return
    for p in projects:
        run = p.get("run") or {}
        state = "working" if p.get("working") else run.get("state") or "new"
        say(f"{MARK.get(state, '·')} {p['name']:<36} {paint.dim(p['id'])}  {state:<9} {p.get('file_count', 0)} files")


def show_project(target, ident):
    p = target.project(ident)
    say(paint.bold(p["name"]) + paint.dim(f"  {p['id']}"))
    if p.get("brief"):
        say(paint.dim(p["brief"][:300]))
    run = p.get("run")
    if run:
        say()
        say(paint.bold("Last run: ") + (run.get("request") or "")[:200])
        r = Renderer()
        for s in run.get("steps", []):
            r.step(s)
        say(paint.dim(run.get("summary") or ""))
    if p.get("notes"):
        say()
        say(paint.bold("Decisions"))
        for n in p["notes"]:
            say(f"  - {n['text']}")
    say()
    say(paint.bold(f"Files ({len(p.get('files', []))})"))
    for f in p.get("files", [])[:80]:
        say(f"  {f['path']:<60} {paint.dim(f['kind'])}")
