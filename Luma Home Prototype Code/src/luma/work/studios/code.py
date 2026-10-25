"""Code: write a program's files, run its tests in the sandbox, and fix what fails.

The coding agent writes whole files (with tests). They're saved inside the project, compiled, then
run in the sandbox (no network, nothing outside the project). If a test fails, the engine hands the
error output back to the coding agent for another try.
"""
from __future__ import annotations

import re

from luma.work import sandbox
from luma.work.studios.base import Result, Studio, check, slug, text

ALLOWED = (".py", ".js", ".mjs", ".json", ".md", ".txt", ".html", ".css", ".csv", ".toml", ".yaml", ".yml", ".sql", ".sh", ".gd", ".cfg", ".ini")


class Code(Studio):
    name, agent, title = "code", "coding", "Code"
    retries = 3
    description = ("Write a complete, working program as files. folder: a short name for it. files: every file with its full content (no '...'), "
                   "including tests. Python uses only the standard library and tests with unittest (test_*.py); JavaScript uses only Node's built-ins "
                   "and tests with node:test. test_command: how to run the tests, like 'python -m unittest -v' or 'node --test'. run_command: how to run it once "
                   "as a demo (or empty). If a previous attempt failed, fix the cause shown in the error.")
    fields = {"folder": "string", "files": "files", "test_command": "text", "run_command": "text"}

    def make(self, ctx, args):
        folder = "code/" + slug(args.get("folder") or ctx.project.get("name"), "app")
        files = []
        for f in (args.get("files") or [])[:16]:
            path = str(f.get("path") or "").strip().lstrip("./")
            content = str(f.get("content") or "")
            if not path or not path.lower().endswith(ALLOWED):
                raise ValueError(f"'{path[:60]}' isn't a file type Luma writes for code.")
            if re.search(r"^\s*(?:\.\.\.|# \.\.\.|// \.\.\.)\s*$", content, re.M):
                raise ValueError(f"{path} has '...' where code should be. Write every file in full.")
            ctx.write(f"{folder}/{path}", content)
            files.append(f"{folder}/{path}")
        if not files:
            raise ValueError("There are no files to write.")
        compiled = {}
        for rel in files:
            if rel.endswith(".py"):
                try:
                    compile(ctx.read_text(rel), rel, "exec")
                    compiled[rel] = ""
                except SyntaxError as error:
                    compiled[rel] = f"line {error.lineno}: {error.msg}"
        runs = {}
        commands = [("tests", text(args.get("test_command"), 300)), ("run", text(args.get("run_command"), 300))]
        js = [rel for rel in files if rel.endswith((".js", ".mjs"))]
        if js and sandbox.node_path():
            commands.insert(0, ("syntax", "node --check " + " ".join(f[len(folder) + 1:] for f in js[:8])))
        if any(cmd for _, cmd in commands) and not ctx.allow_code():
            raise PermissionError("Running code in this project needs your OK.")
        for label, command in commands:
            if not command:
                continue
            ctx.progress(f"Running {label}: {command}")
            try:
                runs[label] = sandbox.run(command, ctx.path(folder), timeout=120)
            except ValueError as error:
                runs[label] = {"ok": False, "code": None, "stdout": "", "stderr": str(error), "timed_out": False, "contained": "refused"}
        tests = runs.get("tests")
        status = ("tests pass" if tests and tests["ok"] else "tests fail" if tests else "no tests")
        return Result(files=files, summary=f"{folder}: {len(files)} files, {status}.",
                      data={"folder": folder, "compiled": compiled, "runs": {k: {kk: v.get(kk) for kk in ("ok", "code", "stdout", "stderr", "timed_out", "contained")} for k, v in runs.items()}})

    def check(self, ctx, result):
        d = result.data
        out = [check("every Python file compiles", not any(d["compiled"].values()), "; ".join(f"{k}: {v}" for k, v in d["compiled"].items() if v))]
        for label, run in d["runs"].items():
            detail = (run.get("stderr") or run.get("stdout") or "")[-1200:]
            out.append(check({"tests": "tests pass", "run": "it runs", "syntax": "JavaScript parses"}[label], run.get("ok"), detail, limit=1500, tail=True))
        if "tests" not in d["runs"]:
            out.append(check("has tests", False, "There's no test command, so nothing proves it works.", blocking=False))
        return out
