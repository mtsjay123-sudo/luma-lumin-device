"""Package: the QA agent's last step. A README that lists every deliverable and how its checks went,
then everything in one zip, opened again to make sure nothing's missing."""
from __future__ import annotations

import zipfile
from datetime import date

from luma.work.studios.base import Result, Studio, check, slug

WHAT = {"deck": "PowerPoint deck", "document": "Word document", "pdf": "PDF", "spreadsheet": "Excel spreadsheet", "table": "table (CSV)", "text": "notes",
        "page": "web page", "image": "image", "cad": "OpenSCAD model", "model": "3D mesh", "code": "code", "game": "Godot project file", "data": "data"}


class Package(Studio):
    name, agent, title, tier = "package", "qa", "Package", "light"
    description = "Package every file in the project into one zip with a README. No input needed."
    fields = {}

    def fallback(self, ctx, task):
        return {}

    def make(self, ctx, args):
        project = ctx.project
        files = [f for f in ctx.files() if not f["path"].startswith("package/")]
        steps = [s for s in ctx.run_steps() if s.get("tool") != "package"]
        lines = [f"# {project['name']}", "", f"Made by Luma on {date.today():%B %d, %Y}.", "", project.get("brief") or "", "", "## What's here", ""]
        for s in steps:
            mark = "✓" if s.get("state") == "done" else "!"
            lines.append(f"### {mark} {s.get('title')}")
            if s.get("summary"):
                lines.append(s["summary"])
            failing = [c for c in s.get("checks", []) if not c["ok"]]
            if failing:
                lines.append("Needs a look: " + "; ".join(f"{c['check']} ({c['detail']})" if c.get("detail") else c["check"] for c in failing))
            lines += [f"- `{f}`" for f in s.get("files", [])] + [""]
        other = sorted({f["path"] for f in files} - {f for s in steps for f in s.get("files", [])})
        if other:
            lines += ["### Other files", ""] + [f"- `{f}`" for f in other] + [""]
        ctx.write("README.md", "\n".join(lines))
        name = f"package/{slug(project['name'], 'project')}.zip"
        target = ctx.path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        included = [f["path"] for f in ctx.files() if not f["path"].startswith("package/")]
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
            for rel in included:
                bundle.write(ctx.path(rel), rel)
        return Result(files=[name, "README.md"], summary=f"Packaged {len(included)} files into {name}.", data={"zip": name, "included": included})

    def check(self, ctx, result):
        try:
            with zipfile.ZipFile(ctx.path(result.data["zip"])) as bundle:
                names = set(bundle.namelist())
                bad = bundle.testzip()
        except (OSError, zipfile.BadZipFile) as error:
            return [check("zip opens", False, str(error))]
        missing = [f for f in result.data["included"] if f not in names]
        return [check("zip opens", bad is None, f"{bad} is damaged."), check("every file is in the zip", not missing, "Missing: " + ", ".join(missing[:5]))]
