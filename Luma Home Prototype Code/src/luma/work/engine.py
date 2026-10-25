"""The execution engine: Luma plans the work, hands each step to a specialist agent, checks it, and delivers.

A request becomes a plan of steps. Luma (the orchestrator) spots the deliverables it asks for (research,
a financial model, a deck, a website, graphics, code, a game, a 3D model, a package) and orders them so
each specialist gets what it needs from the steps before it: the research feeds the model, the model's
numbers feed the deck's charts, the brand colors feed the website. Unusual requests are planned by the
brain instead.

Each step: the specialist (research, data, document, design, coding or QA agent) fills in its studio's
structured output; the studio builds real files; its checks run; anything that fails goes back to the
specialist with the reason, and it tries again. Progress is saved after every step, so a run that's
interrupted (Luma restarted, the laptop closed) picks up where it stopped. Steps are rebuilt from scratch
when resumed, which is safe: studios only write files inside the project. Running code needs the owner's
OK wherever the operating system can't sandbox it.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time

from luma.work import knowledge, sandbox
from luma.work.studios import registry
from luma.work.studios.base import check

ROLES = {
    "research": "You are Luma's research agent. Find what's true from real sources, cite them by number, and say where they disagree. Never invent a number or a source.",
    "data": "You are Luma's data agent. Build on the research and the owner's files. Use real numbers where you have them and state every assumption plainly.",
    "document": "You are Luma's document agent. Write finished, specific, persuasive content someone could read today, using the real findings and numbers from earlier steps. No placeholders.",
    "design": "You are Luma's design agent. Clean, modern and on-brand: use the brand name and colors decided earlier and real words from the research, never generic filler.",
    "coding": "You are Luma's coding agent. Write complete, working, tested files. When something failed, fix the cause shown in the error; never hide or skip the error.",
    "qa": "You are Luma's QA agent. Make sure every deliverable opens and does what was asked.",
}
AGENT_FOR = {"research": "research", "analyze_data": "data", "financial_model": "data", "document": "document", "deck": "document", "website": "design",
             "graphics": "design", "model3d": "design", "code": "coding", "game": "coding", "package": "qa"}
DETECT = [
    ("research", r"\bresearch|\bcompetitors?\b|\bcompetition\b|\bmarket\b|\blook into\b|\bfind out\b|\bsources?\b|\banaly[sz]e (?:the |this |my )?(?:idea|business|market|industry)", "Research the idea and the competition"),
    ("analyze_data", r"\b(?:analy[sz]e|summari[sz]e|crunch|dig into)\b.{0,40}\b(?:spreadsheet|csv|excel|xlsx|data|table|sales|numbers)\b|\.(?:csv|xlsx)\b", "Analyze the data"),
    ("financial_model", r"\bfinancials?\b|\bprojections?\b|\bforecast|\bp&l\b|profit and loss|revenue model|unit economics|break.?even|budget model", "Build the financial model"),
    ("graphics", r"\bgraphics?\b|\blogo\b|\bbrand(?:ing)?\b|social (?:media )?posts?|\bbanners?\b|\bmockups?\b|\bicons?\b|visual assets", "Design the brand graphics"),
    ("document", r"\breport\b|business plan|\bdocument\b|\bdocx\b|\bword (?:doc|file|summary|version)|\bpdf\b|\bmemo\b|\bproposal\b|one.?pager|one.?page (?:summary|brief|report)|executive summary|white ?paper|write.?up", "Write the document"),
    ("deck", r"\b\d{1,2}[- ]slides?\b|\bdeck\b|power ?point|\bpptx\b|\bpresentation\b|\bslides\b|\bpitch\b", "Create the PowerPoint deck"),
    ("website", r"\bwebsite\b|\bweb ?site\b|landing page|web page|homepage|\bsite\b", "Build the website"),
    ("code", r"\bscript\b|\bprogram\b|\bpython\b|\bjavascript\b|\bapi\b|\bcli\b|\bbot\b|\bautomation\b|\bbackend\b|\b(?:write|build|code) (?:me )?(?:an? )?(?:app|tool|calculator|converter)\b", "Write and test the code"),
    ("game", r"\bgame\b|\bplatformer\b|\bgodot\b|\bunity\b|\bunreal\b|\bplayable\b", "Build the game"),
    ("model3d", r"\b3d\b|\b3-d\b|\bcad\b|\bblender\b|\bopenscad\b|\bstl\b|\bprintable\b|\benclosure\b|\bbracket\b", "Design the 3D model"),
    ("package", r"\bpackage\b|\bzip\b|\bbundle\b|all (?:the |of the )?files|deliver (?:it|them|everything)", "Package everything"),
]
ORDER = [tool for tool, _, _ in DETECT]
NEEDS = {"research": [], "analyze_data": [], "financial_model": ["research", "analyze_data"], "graphics": ["research"],
         "document": ["research", "analyze_data", "financial_model"], "deck": ["research", "analyze_data", "financial_model", "graphics"],
         "website": ["research", "graphics", "financial_model"], "code": ["research"], "game": [], "model3d": [], "package": None}
STATES = ("pending", "running", "done", "attention", "waiting", "skipped", "stopped")


def detect(request):
    """The deliverables a request asks for, in a sensible order."""
    lowered = request.lower()
    found = [tool for tool, pattern, _ in DETECT if re.search(pattern, lowered)]
    if "code" in found and ("website" in found or "game" in found) and not re.search(r"\b(?:script|program|python|api|cli|bot|backend)\b", lowered):
        found.remove("code")
    if "research" in found and found == ["research"] and re.search(r"\breport\b|\bwrite\b", lowered):
        found.append("document")
    return found


def plan_from(request, tools):
    titles = {tool: title for tool, _, title in DETECT}
    if len([t for t in tools if t != "package"]) >= 2 and "package" not in tools:
        tools = tools + ["package"]
    steps = []
    for tool in ORDER:
        if tool not in tools:
            continue
        needs = [s["n"] for s in steps] if NEEDS[tool] is None else [s["n"] for s in steps if s["tool"] in NEEDS[tool]]
        steps.append({"n": len(steps) + 1, "title": titles[tool], "agent": AGENT_FOR[tool], "tool": tool, "task": request, "needs": needs, "state": "pending"})
    return steps


def compact(data, limit=3500):
    """An earlier step's results, short enough to hand to the next specialist."""
    if not data:
        return ""
    keep = dict(data)
    if "findings" in keep:
        keep["findings"] = [{"claim": f["claim"], "sources": f["sources"]} for f in keep["findings"][:12]]
        keep["sources"] = [f"[{s['id']}] {s['title']}" for s in keep.get("sources", [])[:12]]
    for noisy in ("profile", "level", "browser", "played", "renders", "runs", "compiled", "included"):
        keep.pop(noisy, None)
    out = json.dumps(keep, ensure_ascii=False, default=str)
    return out if len(out) <= limit else out[:limit] + "…"


class Context:
    """What a studio can use while it works on one step."""

    def __init__(self, engine, project, run, step, cancel):
        self.engine, self.project, self.run, self.step, self.cancel = engine, project, run, step, cancel
        self.request, self.task = run["request"], step.get("task") or run["request"]
        self.folder = engine.projects.folder(project["id"])
        self.can_render = engine.render

    # brains and the web
    def ask(self, prompt, fields, name, tier="heavy"):
        if self.cancel.is_set():
            raise InterruptedError("Stopped.")
        return self.engine.think(ROLES.get(self.step["agent"], "") + "\n\n" + prompt, fields, name, tier, self.cancel)

    def search(self, query):
        return self.engine.search(query) if self.engine.search else []

    def read(self, url):
        return self.engine.read(url) if self.engine.read else ""

    def knowledge(self, query):
        return knowledge.Index(self.folder).refresh().search(query, limit=4)

    def progress(self, message):
        self.engine.emit({"type": "progress", "project": self.project["id"], "run": self.run["id"], "step": self.step["n"], "message": str(message)[:300]})
        self.step.setdefault("log", []).append(str(message)[:300])
        self.step["log"] = self.step["log"][-20:]

    # files in the project
    def path(self, rel):
        return self.engine.projects.path(self.project["id"], rel)

    def write(self, rel, data):
        return self.engine.projects.write(self.project["id"], rel, data)

    def exists(self, rel):
        try:
            return self.path(rel).is_file()
        except ValueError:
            return False

    def read_text(self, rel):
        return self.engine.projects.read(self.project["id"], rel, limit=2_000_000)

    def files(self):
        return self.engine.projects.files(self.project["id"])

    # what came before
    def input(self, tool):
        done = [s for s in self.run["steps"] if s["tool"] == tool and s.get("state") in {"done", "attention"} and s.get("data")]
        return done[-1]["data"] if done else None

    def has_input(self, tool):
        return self.input(tool) is not None

    def run_steps(self):
        return self.run["steps"]

    # risky things wait for the owner
    def allow_code(self):
        return self.engine.code_allowed(self.project["id"])


class Engine:
    def __init__(self, projects, think=None, search=None, read=None, render=True, approver=None, clock=time.time, studios=None):
        self.projects = projects
        self._think = think          # (prompt, fields, name, tier, cancel) -> dict | None
        self.search = search         # (query) -> [{"title","url","snippet","excerpt"}]
        self.read = read             # (url) -> page text
        self.render = render and self._browser_ok()
        self.approver = approver     # (question) -> bool, for a person at a terminal
        self.clock = clock
        self.studios = studios or registry()
        self.listeners = []
        self.active = {}             # project id -> cancel event
        self.lock = threading.Lock()

    @staticmethod
    def _browser_ok():
        if os.environ.get("LUMA_WORK_NO_BROWSER") == "1":
            return False
        import importlib.util
        return importlib.util.find_spec("playwright") is not None

    # -- events ------------------------------------------------------------------
    def emit(self, event):
        for listener in list(self.listeners):
            try:
                listener(event)
            except Exception:
                pass

    def think(self, prompt, fields, name, tier, cancel):
        if not self._think:
            return None
        try:
            return self._think(prompt, fields, name, tier, cancel)
        except InterruptedError:
            raise
        except Exception as error:
            self.emit({"type": "progress", "message": f"The brain couldn't answer: {str(error)[:160]}"})
            return None

    def code_allowed(self, project_id):
        if sandbox.contained():
            return True
        project = self.projects.get(project_id)
        if project.get("code_ok"):
            return True
        if self.approver and self.approver("Luma wants to run the code it wrote for this project. This computer can't fully sandbox it "
                                           "(it runs with no keys and time limits, but could reach the network). Allow code runs for this project?"):
            self.projects.save(project, code_ok=True)
            return True
        return False

    def allow_code(self, project_id):
        return self.projects.save(self.projects.get(project_id), code_ok=True)

    # -- planning ------------------------------------------------------------------
    def plan(self, project, request, cancel=None):
        tools = detect(request)
        if tools:
            return plan_from(request, tools)
        answer = self.think(
            "Plan this project as a few steps. Each step names which specialist does it (agent), which studio tool it uses, what exactly to do (task), "
            "and the numbers of earlier steps it needs. Studios: research (web research with citations), analyze_data (a spreadsheet in the project), "
            "financial_model, document, deck, website, code, game, model3d, graphics, package (zip everything; last).\n"
            f"Project: {project['name']}. {project.get('brief', '')}\nRequest: {request}",
            {"steps": "plan"}, "work.plan", "heavy", cancel or threading.Event())
        steps = []
        for raw in (answer or {}).get("steps") or []:
            tool = raw.get("tool")
            if tool not in self.studios:
                continue
            n = len(steps) + 1
            steps.append({"n": n, "title": str(raw.get("title") or self.studios[tool].title)[:90], "agent": AGENT_FOR[tool], "tool": tool,
                          "task": str(raw.get("task") or request)[:1500], "needs": [int(x) for x in raw.get("needs") or [] if isinstance(x, int) and 0 < x < n],
                          "state": "pending"})
        return steps[:12] or plan_from(request, ["research", "document"])

    # -- running -------------------------------------------------------------------
    def start(self, project_id, request, cancel=None, resume=None):
        """Plan (or pick up) a run and work through it. Returns the finished run."""
        project = self.projects.get(project_id)
        cancel = cancel or threading.Event()
        with self.lock:
            if project_id in self.active:
                raise ValueError("Luma is already working on this project. Stop it first, or wait.")
            self.active[project_id] = cancel
        try:
            if resume:
                run = next((r for r in project.get("runs", []) if r["id"] == resume), None)
                if not run:
                    raise ValueError("That run doesn't exist.")
                run.update(state="running", resumed=self.clock())
            else:
                run = {"id": os.urandom(4).hex(), "request": " ".join(str(request).split())[:4000], "state": "planning", "started": self.clock(), "steps": []}
                self._save(project_id, run)
                self.emit({"type": "planning", "project": project_id, "run": run["id"]})
                run["steps"] = self.plan(project, run["request"], cancel)
                run["state"] = "running"
            self._save(project_id, run)
            self.emit({"type": "plan", "project": project_id, "run": run["id"], "steps": [{k: s[k] for k in ("n", "title", "agent", "tool")} for s in run["steps"]]})
            for step in run["steps"]:
                if cancel.is_set():
                    break
                if step.get("state") in {"done", "skipped"}:
                    continue
                self._step(project_id, run, step, cancel)
                if step["state"] == "waiting":
                    run["state"] = "waiting"
                    run["summary"] = step.get("summary")
                    self._save(project_id, run)
                    self.emit({"type": "waiting", "project": project_id, "run": run["id"], "step": step["n"], "message": step.get("summary")})
                    return run
            if cancel.is_set():
                run["state"] = "stopped"
                for step in run["steps"]:
                    if step["state"] in {"pending", "running"}:
                        step["state"] = "stopped" if step["state"] == "running" else step["state"]
                run["summary"] = "Stopped. Finished steps are kept; pick it back up any time."
            else:
                run["state"] = "done"
                run["summary"] = self._summary(run)
            run["finished"] = self.clock()
            self._save(project_id, run)
            self.emit({"type": "done", "project": project_id, "run": run["id"], "state": run["state"], "summary": run["summary"]})
            return run
        finally:
            with self.lock:
                self.active.pop(project_id, None)

    def stop(self, project_id):
        event = self.active.get(project_id)
        if event:
            event.set()
        return bool(event)

    def _step(self, project_id, run, step, cancel):
        studio = self.studios[step["tool"]]
        project = self.projects.get(project_id)
        ctx = Context(self, project, run, step, cancel)
        step.update(state="running", started=self.clock(), checks=[], files=[], log=[])
        self._save(project_id, run)
        self.emit({"type": "step", "project": project_id, "run": run["id"], "step": step["n"], "state": "running", "title": step["title"], "agent": step["agent"]})
        started = time.time()
        args, failures, result = None, [], None
        try:
            for attempt in range(getattr(studio, "retries", 1) + 1):
                if cancel.is_set():
                    break
                if attempt == 0 or (args is not None and failures):
                    fresh = self._ask_studio(ctx, studio, step, run, failures if attempt else None)
                    if fresh is None and attempt:
                        break  # no brain to fix it: keep what we have
                    args = fresh if fresh is not None else (args if args is not None else studio.fallback(ctx, step["task"]))
                if args is None:
                    failures = [check("a brain to do this step", False, "No brain answered, and this step can't be done without one. Turn on the local model or a cloud brain.")]
                    break
                try:
                    result = studio.make(ctx, args)
                    result.checks = studio.check(ctx, result)
                    failures = result.failures()
                except PermissionError as error:
                    step.update(state="waiting", summary=str(error), approval="code")
                    self._log(project_id, run, step, "waiting", time.time() - started, False, str(error))
                    return
                except (ValueError, KeyError, TypeError) as error:
                    failures = [check("valid input", False, str(error)[:300])]
                    result = None
                ctx.progress(("Checks passed" if not failures else "Checks failed: " + "; ".join(f["check"] for f in failures)) + (f" (try {attempt + 1})" if attempt else ""))
                if not failures:
                    break
        except InterruptedError:
            step.update(state="stopped", summary="Stopped while working on this.")
            return
        except Exception as error:  # a bug or a missing library shouldn't sink the whole run
            failures = [check("finished without errors", False, f"{type(error).__name__}: {str(error)[:300]}")]
        if result is not None:
            step.update(files=result.files, summary=result.summary, data=self._trim(result.data), checks=result.checks)
        else:
            step.update(checks=failures, summary="Couldn't finish: " + "; ".join(f["detail"] or f["check"] for f in failures)[:400])
        step["state"] = "done" if result is not None and not failures else ("stopped" if cancel.is_set() else "attention")
        step["seconds"] = round(time.time() - started, 1)
        self._log(project_id, run, step, step["state"], step["seconds"], step["state"] == "done", step.get("summary", ""))
        self._save(project_id, run)
        self.emit({"type": "step", "project": project_id, "run": run["id"], "step": step["n"], "state": step["state"], "title": step["title"],
                   "summary": step.get("summary"), "files": step.get("files", []), "checks": step.get("checks", [])})

    def _ask_studio(self, ctx, studio, step, run, failures):
        if not studio.fields:
            return studio.fallback(ctx, step["task"])
        project = ctx.project
        earlier = [s for s in run["steps"] if s["n"] in step.get("needs", []) and s.get("data")]
        notes = [n["text"] for n in project.get("notes", [])]
        prompt = [f"Project: {project['name']}." + (f" {project['brief']}" if project.get("brief") else ""), f"The whole request: {run['request']}"]
        if notes:
            prompt.append("Decisions the owner approved (follow them): " + "; ".join(notes))
        for s in earlier:
            prompt.append(f"Result of step {s['n']} ({s['title']}): {s.get('summary', '')}\n{compact(s.get('data'))}")
        prompt.append(f"Your step: {step['title']}. {step['task'] if step['task'] != run['request'] else ''}".strip())
        prompt.append(studio.description)
        if failures:
            prompt.append("The last attempt didn't pass these checks; fix exactly these: " + "; ".join(f"{f['check']}: {f['detail']}" for f in failures))
        prompt.append(f"Answer by calling work.{studio.name} with every field filled in.")
        return ctx.ask("\n\n".join(prompt), studio.fields, f"work.{studio.name}", studio.tier)

    @staticmethod
    def _trim(data, limit=24000):
        text = json.dumps(data, ensure_ascii=False, default=str)
        if len(text) <= limit:
            return json.loads(text)
        keep = {k: v for k, v in data.items() if k not in {"profile", "level", "browser", "played", "runs", "included", "renders"}}
        text = json.dumps(keep, ensure_ascii=False, default=str)
        return json.loads(text) if len(text) <= limit else {"note": "too large to keep", "keys": list(data)[:20]}

    def _summary(self, run):
        done = [s for s in run["steps"] if s["state"] == "done"]
        attention = [s for s in run["steps"] if s["state"] == "attention"]
        package = next((f for s in done if s["tool"] == "package" for f in s.get("files", []) if f.endswith(".zip")), None)
        parts = [f"Finished {len(done)} of {len(run['steps'])} steps."]
        if attention:
            parts.append("Needs a look: " + "; ".join(f"{s['title']} ({(s.get('summary') or '')[:120]})" for s in attention))
        if package:
            parts.append(f"Everything is packaged in {package}.")
        return " ".join(parts)

    def _save(self, project_id, run):
        self.projects.record_run(project_id, run)

    def _log(self, project_id, run, step, event, seconds, ok, detail):
        """One line per step in the project's run log: what ran, how long, whether it passed (for monitoring)."""
        try:
            folder = self.projects.folder(project_id) / ".luma" / "runs"
            folder.mkdir(parents=True, exist_ok=True)
            with open(folder / f"{run['id']}.jsonl", "a") as log:
                log.write(json.dumps({"at": self.clock(), "step": step["n"], "tool": step["tool"], "agent": step["agent"], "event": event,
                                      "seconds": round(seconds, 2), "ok": ok, "detail": str(detail)[:300]}) + "\n")
        except OSError:
            pass


def for_agent(agent, approver=None):
    """An engine wired to a running Luma: its brain (picked by how hard each step is), its web search and its browser."""
    from luma.work.projects import Projects
    projects = Projects(agent.store, agent.files_dir / "projects", agent.clock)

    def think(prompt, fields, name, tier, cancel):
        if not agent.use_model and agent.planner is None:
            return None
        answer = agent.call_planner([{"role": "user", "content": prompt}], [], {name: {"description": "Fill this in for the current step.", "fields": fields}},
                                    cancel or threading.Event(), tier=tier)
        if isinstance(answer, dict) and answer.get("type") == "tool" and answer.get("name") == name and isinstance(answer.get("arguments"), dict):
            return answer["arguments"]
        return None

    def search(query):
        if not agent.integration_on("web_search") or agent.rules.for_tool("web.search")[1] == "block":
            raise ValueError("Web search is off in Luma's settings.")
        return (agent.search_web(query) or {}).get("results", [])

    def read(url):
        return (agent.browser.open(url) or {}).get("text", "")

    return Engine(projects, think=think, search=search, read=read, approver=approver, clock=agent.clock)
