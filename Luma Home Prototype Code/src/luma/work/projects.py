"""Project workspaces: a folder of files, the decisions made along the way, and every run's history.

Each project lives in its own folder under Luma's files. Everything Luma makes for it (research,
spreadsheets, decks, websites, code, games, models) is written there and nowhere else: paths are
checked so nothing can escape the folder. The project record (name, brief, decisions, runs) is kept
encrypted in Luma's store; the files stay plain so they open in Finder, Word, Keynote or a browser.
"""
from __future__ import annotations

import os
import re
import shutil
import time
import zipfile
from pathlib import Path, PurePosixPath

MAX_FILE = 50 * 2 ** 20          # one file Luma writes
MAX_PROJECT = 2 * 2 ** 30        # everything in one project
HIDDEN = ".luma"                 # Luma's own bookkeeping inside a project (search index, logs)
KINDS = {
    ".pptx": "deck", ".docx": "document", ".pdf": "pdf", ".xlsx": "spreadsheet", ".csv": "table", ".md": "text", ".txt": "text",
    ".html": "page", ".css": "code", ".js": "code", ".py": "code", ".gd": "code", ".json": "data", ".svg": "image", ".png": "image",
    ".jpg": "image", ".jpeg": "image", ".scad": "cad", ".stl": "model", ".obj": "model", ".zip": "package", ".godot": "game", ".tscn": "game",
}


def slug(text, fallback="project"):
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")[:48] or fallback


def kind_of(path):
    return KINDS.get(Path(path).suffix.lower(), "file")


class Projects:
    def __init__(self, store, root, clock=time.time):
        self.store = store
        self.root = Path(root)
        self.clock = clock

    # -- records -----------------------------------------------------------------
    def create(self, name, brief=""):
        name = " ".join(str(name or "").split())[:80] or "New project"
        project = self.store.put("project", {"name": name, "brief": " ".join(str(brief or "").split())[:4000], "created": self.clock(),
                                             "updated": self.clock(), "notes": [], "runs": [], "code_ok": False})
        self.folder(project["id"]).mkdir(parents=True, exist_ok=True)
        return project

    def get(self, ident):
        project = self.store.get("project", str(ident or ""))
        if not project:
            raise ValueError("That project doesn't exist.")
        return project

    def list(self):
        return sorted(self.store.all("project", 200), key=lambda p: -p.get("updated", 0))

    def save(self, project, **changes):
        project.update(changes, updated=self.clock())
        return self.store.put("project", project, project["id"])

    def rename(self, ident, name):
        return self.save(self.get(ident), name=" ".join(str(name).split())[:80] or "Untitled")

    def delete(self, ident, confirmed=False):
        """Deleting a project removes its files. It only happens with the owner's explicit yes."""
        if not confirmed:
            raise PermissionError("Deleting a project needs your OK.")
        project = self.get(ident)
        shutil.rmtree(self.folder(project["id"]), ignore_errors=True)
        self.store.delete("project", project["id"])
        return {"deleted": project["id"]}

    # -- project memory: decisions and preferences the owner approved ------------------------------
    def note(self, ident, text, kind="decision"):
        text = " ".join(str(text or "").split())[:600]
        if not text:
            raise ValueError("The note is empty.")
        project = self.get(ident)
        notes = [n for n in project.get("notes", []) if n["text"].casefold() != text.casefold()]
        notes.append({"id": os.urandom(4).hex(), "text": text, "kind": kind if kind in {"decision", "preference", "fact"} else "decision", "at": self.clock()})
        return self.save(project, notes=notes[-60:])

    def forget(self, ident, note_id):
        project = self.get(ident)
        return self.save(project, notes=[n for n in project.get("notes", []) if n["id"] != note_id])

    def record_run(self, ident, run):
        project = self.get(ident)
        runs = [r for r in project.get("runs", []) if r["id"] != run["id"]] + [run]
        return self.save(project, runs=runs[-30:])

    # -- files -------------------------------------------------------------------
    def folder(self, ident):
        return self.root / str(ident)

    def path(self, ident, rel):
        """The real path for a file in this project, refusing anything that would land outside it."""
        rel = str(rel or "").replace("\\", "/").strip()
        parts = PurePosixPath(rel).parts
        if not rel or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel) or any(p in {"..", ""} for p in parts) or (parts and parts[0] == HIDDEN):
            raise ValueError(f"'{rel[:80]}' isn't a file name inside the project.")
        base = self.folder(ident).resolve()
        target = (base / Path(*parts)).resolve()
        if base != target and base not in target.parents:
            raise ValueError("That file would land outside the project.")
        return target

    def write(self, ident, rel, data):
        raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
        if len(raw) > MAX_FILE:
            raise ValueError("That file is too big for one project file (50 MB).")
        if self.size(ident) + len(raw) > MAX_PROJECT:
            raise ValueError("This project is full (2 GB). Export it and start a fresh one.")
        target = self.path(ident, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".partial")
        partial.write_bytes(raw)
        partial.replace(target)
        self.save(self.get(ident))
        return target

    def read(self, ident, rel, limit=200_000):
        target = self.path(ident, rel)
        if not target.is_file():
            raise ValueError(f"There's no file called {rel} in this project.")
        return target.read_bytes()[:limit].decode("utf-8", "replace")

    def remove(self, ident, rel, confirmed=False):
        if not confirmed:
            raise PermissionError("Deleting a file needs your OK.")
        target = self.path(ident, rel)
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        return {"removed": rel}

    def files(self, ident):
        base = self.folder(ident)
        if not base.is_dir():
            return []
        out = []
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(base).as_posix()
            if not path.is_file() or rel.split("/")[0] == HIDDEN or path.name.endswith(".partial"):
                continue
            stat = path.stat()
            out.append({"path": rel, "size": stat.st_size, "kind": kind_of(rel), "modified": stat.st_mtime})
        return out

    def size(self, ident):
        base = self.folder(ident)
        return sum(p.stat().st_size for p in base.rglob("*") if p.is_file()) if base.is_dir() else 0

    def export(self, ident):
        """Every file in the project, in one zip the owner can send or keep."""
        project = self.get(ident)
        base = self.folder(ident)
        target = base / HIDDEN / f"{slug(project['name'])}.zip"
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
            for item in self.files(ident):
                bundle.write(base / item["path"], item["path"])
        return target
