"""Projects over HTTP: Luma's window, a paired phone, a paired laptop's terminal and this computer's
terminal all start, watch and collect project work through these few calls.

Runs happen in the background on the Luma doing the work (the device, or this computer); callers poll
the project to watch the plan and steps move. Generated files are served inside a sandbox (no scripts
reaching Luma, no cookies), and deleting needs an explicit confirm.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import mimetypes
import re
import secrets
import threading
from urllib.parse import parse_qs

UPLOAD_LIMIT = 25 * 2 ** 20
TYPES = {".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
         ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
         ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".md": "text/markdown; charset=utf-8",
         ".csv": "text/csv; charset=utf-8", ".stl": "model/stl", ".obj": "text/plain; charset=utf-8", ".scad": "text/plain; charset=utf-8",
         ".gd": "text/plain; charset=utf-8", ".godot": "text/plain; charset=utf-8", ".tscn": "text/plain; charset=utf-8", ".py": "text/plain; charset=utf-8"}
PREVIEW_CSP = ("sandbox allow-scripts allow-popups allow-forms allow-downloads; default-src 'none'; script-src 'self' 'unsafe-inline'; "
               "style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; frame-ancestors 'self'")


VIEWABLE = {".html", ".htm", ".svg", ".css", ".js", ".mjs", ".json", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".txt", ".md", ".csv"}


def view_base(agent, project_id):
    """A read-only link to one project's files for previews. A page Luma built loads its own styles, scripts and
    images by relative path, and inside the preview sandbox no cookie goes with those loads, so the link itself
    carries the permission: it's signed with a key that lives only in this run of Luma."""
    if getattr(agent, "_work_view_key", None) is None:
        agent._work_view_key = secrets.token_bytes(32)
    sig = hmac.new(agent._work_view_key, project_id.encode(), hashlib.sha256).hexdigest()[:32]
    return f"/api/work/view/{project_id}/{sig}/"


def serve_view(agent, path, send, send_bytes):
    """GET /api/work/view/<project>/<signature>/<file path>: previews only, inside the sandbox."""
    parts = path[len("/api/work/view/"):].split("/", 2)
    key = getattr(agent, "_work_view_key", None)
    if agent.mode == "kids" or len(parts) < 3 or not key or not hmac.compare_digest(view_base(agent, parts[0]), f"/api/work/view/{parts[0]}/{parts[1]}/"):
        return send({"error": "Not found"}, 404)
    from urllib.parse import unquote
    try:
        target = engine(agent).projects.path(parts[0], unquote(parts[2]))
    except ValueError:
        return send({"error": "Not found"}, 404)
    suffix = target.suffix.lower()
    if suffix not in VIEWABLE or not target.is_file():
        return send({"error": "Not found"}, 404)
    kind = {".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
            ".md": "text/plain; charset=utf-8", ".csv": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8"}.get(suffix) \
        or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if suffix in {".html", ".htm"}:
        kind = "text/html; charset=utf-8"
    return send_bytes(target.read_bytes(), kind, target.name, True, PREVIEW_CSP if suffix in {".html", ".htm", ".svg"} else None)


def engine(agent):
    if getattr(agent, "_work", None) is None:
        from luma.work.engine import for_agent
        agent._work = for_agent(agent)
    return agent._work


def slim_run(run):
    if not run:
        return None
    steps = [{k: s.get(k) for k in ("n", "title", "agent", "tool", "state", "summary", "files", "seconds", "approval")} |
             {"checks": [c for c in s.get("checks", [])], "log": (s.get("log") or [])[-3:]} for s in run.get("steps", [])]
    return {k: run.get(k) for k in ("id", "request", "state", "summary", "started", "finished")} | {"steps": steps}


def view(eng, project, detail=False, agent=None):
    runs = project.get("runs", [])
    out = {"id": project["id"], "name": project["name"], "brief": project.get("brief", ""), "created": project.get("created"), "updated": project.get("updated"),
           "working": project["id"] in eng.active, "run": slim_run(runs[-1] if runs else None), "notes": project.get("notes", []),
           "code_ok": bool(project.get("code_ok"))}
    files = eng.projects.files(project["id"])
    out["file_count"] = len(files)
    if detail:
        out["files"] = files
        out["runs"] = [slim_run(r) for r in runs[-10:]]
        if agent is not None:
            out["view"] = view_base(agent, project["id"])
    return out


def start(agent, eng, project_id, request=None, resume=None):
    def go():
        try:
            eng.start(project_id, request, resume=resume)
        except Exception as error:  # surfaced on the project, never lost in a thread
            try:
                project = eng.projects.get(project_id)
                runs = project.get("runs", [])
                if runs and runs[-1].get("state") in {"planning", "running"}:
                    runs[-1].update(state="stopped", summary="Stopped: " + str(error)[:300])
                    eng.projects.save(project, runs=runs)
            except Exception:
                pass
    threading.Thread(target=go, daemon=True, name="luma-work").start()


def name_for(request):
    words = re.sub(r"[^\w\s'-]", " ", str(request or "")).split()
    filler = {"please", "can", "you", "make", "me", "a", "an", "the", "build", "create", "for", "my", "and", "i", "want", "need", "to", "research", "this", "of"}
    keep = [w for w in words if w.lower() not in filler][:5]
    return (" ".join(keep) or "New project").title()[:60]


def get(agent, path, query, send, send_bytes, viewer="owner"):
    """GET /api/work/*: returns whatever send()/send_bytes() return."""
    if agent.mode == "kids":
        return send({"error": "Projects are available in adult mode."}, 403)
    eng = engine(agent)
    q = parse_qs(query or "")
    one = lambda key: (q.get(key) or [""])[0]
    try:
        if path == "/api/work/projects":
            from luma.llm import usage
            return send({"projects": [view(eng, p) for p in eng.projects.list()], "usage": usage.summary(agent.store), "sandboxed": __import__("luma.work.sandbox", fromlist=["x"]).contained()})
        if path == "/api/work/project":
            return send({"project": view(eng, eng.projects.get(one("id")), detail=True, agent=agent)})
        if path == "/api/work/file":
            target = eng.projects.path(one("id"), one("path"))
            if not target.is_file():
                return send({"error": "File not found"}, 404)
            suffix = target.suffix.lower()
            kind = TYPES.get(suffix) or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            inline = one("view") == "1" and suffix in {".html", ".svg", ".png", ".jpg", ".jpeg", ".md", ".txt", ".csv", ".py", ".js", ".css", ".json", ".gd", ".scad"}
            if suffix in {".md", ".txt", ".py", ".js", ".css", ".json", ".gd", ".scad", ".csv"} and inline:
                kind = "text/plain; charset=utf-8"
            return send_bytes(target.read_bytes(), kind, target.name, inline, PREVIEW_CSP if inline and suffix in {".html", ".svg"} else None)
        if path == "/api/work/export":
            project = eng.projects.get(one("id"))
            target = eng.projects.export(project["id"])
            return send_bytes(target.read_bytes(), "application/zip", target.name, False, None)
        if path == "/api/work/usage":
            from luma.llm import usage
            return send(usage.summary(agent.store))
    except ValueError as error:
        return send({"error": str(error)}, 404)
    return send({"error": "Not found"}, 404)


def post(agent, path, data, send, viewer="owner"):
    if agent.mode == "kids":
        return send({"error": "Projects are available in adult mode."}, 403)
    eng = engine(agent)
    pid = str(data.get("id") or "")
    try:
        if path == "/api/work/create":
            return send({"project": view(eng, eng.projects.create(data.get("name"), data.get("brief")))})
        if path == "/api/work/run":
            request = " ".join(str(data.get("request") or "").split())
            if not request:
                raise ValueError("Say what you want Luma to make.")
            project = eng.projects.get(pid) if pid else eng.projects.create(data.get("name") or name_for(request), data.get("brief") or request)
            if project["id"] in eng.active:
                raise ValueError("Luma is already working on this project.")
            start(agent, eng, project["id"], request)
            return send({"project": view(eng, eng.projects.get(project["id"])), "started": True})
        if path == "/api/work/resume":
            project = eng.projects.get(pid)
            runs = [r for r in project.get("runs", []) if r.get("state") in {"stopped", "waiting", "running", "planning"}]
            run_id = str(data.get("run") or (runs[-1]["id"] if runs else ""))
            if not run_id:
                raise ValueError("There's nothing unfinished to pick back up.")
            start(agent, eng, pid, None, resume=run_id)
            return send({"project": view(eng, project), "started": True})
        if path == "/api/work/stop":
            return send({"stopped": eng.stop(pid)})
        if path == "/api/work/approve":
            if viewer == "phone" and not data.get("confirm"):
                raise ValueError("Confirm on the phone to let Luma run code.")
            project = eng.allow_code(pid)
            waiting = [r for r in project.get("runs", []) if r.get("state") == "waiting"]
            if waiting and pid not in eng.active:
                start(agent, eng, pid, None, resume=waiting[-1]["id"])
            return send({"project": view(eng, eng.projects.get(pid)), "resumed": bool(waiting)})
        if path == "/api/work/note":
            return send({"project": view(eng, eng.projects.note(pid, data.get("text"), data.get("kind") or "decision"))})
        if path == "/api/work/forget":
            return send({"project": view(eng, eng.projects.forget(pid, str(data.get("note") or "")))})
        if path == "/api/work/rename":
            return send({"project": view(eng, eng.projects.rename(pid, data.get("name")))})
        if path == "/api/work/delete":
            if viewer == "phone":
                raise ValueError("Delete projects on Luma itself.")
            eng.stop(pid)
            return send(eng.projects.delete(pid, confirmed=data.get("confirm") is True))
        if path == "/api/work/upload":
            name = re.sub(r"[^\w .()-]", "_", str(data.get("name") or "file")).strip()[:120] or "file"
            raw = base64.b64decode(str(data.get("data") or ""), validate=True)
            if not raw or len(raw) > UPLOAD_LIMIT:
                raise ValueError("Files up to 25 MB can be added to a project.")
            eng.projects.write(pid, f"uploads/{name}", raw)
            return send({"project": view(eng, eng.projects.get(pid), detail=True, agent=agent)})
    except PermissionError as error:
        return send({"error": str(error)}, 403)
    except (ValueError, KeyError) as error:
        return send({"error": str(error)}, 400)
    return send({"error": "Not found"}, 404)
