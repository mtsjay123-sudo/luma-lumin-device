"""Can Luma do the big jobs? Runs whole projects end to end and grades every step.

    .venv/bin/python scripts/work_eval.py                 # your local model (LUMA_MODEL_PATH in .env)
    .venv/bin/python scripts/work_eval.py --only vision   # just the business-idea project
    .venv/bin/python scripts/work_eval.py --offline       # no model: proves the pipeline with scripted answers
    .venv/bin/python scripts/work_eval.py --save report.json --keep ./eval-output

Everything runs in a throwaway profile: your real projects, memories and settings are untouched,
nothing is sent or bought, and no paid API is used. Code runs in the project sandbox. Each project
passes only when every step finished and every blocking check passed (files open in Word, PowerPoint
and Excel; the website loads on a phone with no broken links; tests pass; the game moves; the 3D mesh
is watertight).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SCENARIOS = [
    ("vision", "Research this business idea: a taco truck for downtown Atlanta offices. Analyze competitors, prepare the financial "
               "projections, create a 20-slide PowerPoint, build a branded website, generate the graphics, test the site, and "
               "package all the files for me."),
    ("code", "Write a Python command-line tool that converts temperatures between Celsius, Fahrenheit and Kelvin, with unit tests."),
    ("game", "Make a small platformer game called Moon Hop with three levels."),
    ("model3d", "Design a 3D printable phone stand."),
    ("data", "Build a financial model for a coffee cart: $5.50 average order, 140 orders a day at the start growing 4% a month, "
             "$38,000 to start, and a one-page Word summary of it."),
]


def grade(name, project, run, seconds):
    steps = run.get("steps", []) if run else []
    checks = [c for s in steps for c in s.get("checks", [])]
    failed = [f"{s['title']}: {c.get('check')}" + (f" ({c.get('detail')[:120]})" if c.get("detail") else "")
              for s in steps for c in s.get("checks", []) if not c.get("ok") and c.get("blocking", True)]
    files = sorted({f for s in steps for f in s.get("files", [])})
    return {"name": name, "state": (run or {}).get("state", "no run"), "passed": bool(run) and run.get("state") == "done" and not failed,
            "steps": [{"title": s["title"], "agent": s.get("agent"), "state": s["state"], "seconds": s.get("seconds"), "summary": s.get("summary", "")} for s in steps],
            "checks_passed": sum(1 for c in checks if c.get("ok")), "checks": len(checks), "failed": failed, "files": files,
            "seconds": round(seconds, 1), "summary": (run or {}).get("summary", ""), "project": project["id"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", help="run scenarios whose name contains this text")
    parser.add_argument("--offline", action="store_true", help="no model: scripted answers prove the pipeline works")
    parser.add_argument("--save", help="write the full report as JSON")
    parser.add_argument("--keep", help="copy every project's files here to look at afterwards")
    args = parser.parse_args()

    from luma.memory.store import Store
    from luma.work.engine import Engine, for_agent
    from luma.work.projects import Projects

    reports = []
    with tempfile.TemporaryDirectory() as temp:
        store = Store(Path(temp) / "state.db", Path(temp) / "state.key")
        if args.offline:
            sys.path.insert(0, str(ROOT / "tests"))
            import work_fakes
            engine = Engine(Projects(store, Path(temp) / "files" / "projects"), think=work_fakes.Brain(), search=work_fakes.search,
                            read=lambda url: "", approver=lambda question: True)
            print("Checking Luma's project engine with scripted answers (no model, nothing is sent)\n")
        else:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
            from luma.agent.runtime import Agent
            from luma.config import LLAMA_MODEL_PATH
            if not LLAMA_MODEL_PATH.exists():
                sys.exit(f"No local model at {LLAMA_MODEL_PATH}. Set LUMA_MODEL_PATH in .env first, or use --offline.")
            agent = Agent(store=store, use_model=True)
            engine = for_agent(agent, approver=lambda question: True)
            print(f"Checking Luma's projects with {LLAMA_MODEL_PATH.name} (throwaway profile, nothing is sent)\n")

        for name, request in SCENARIOS:
            if args.only and args.only.lower() not in name:
                continue
            project = engine.projects.create(name.title(), request)
            engine.allow_code(project["id"])  # the eval says yes to sandboxed code up front
            print(f"▸ {name}: {request[:90]}{'…' if len(request) > 90 else ''}")
            started = time.monotonic()
            try:
                run = engine.start(project["id"], request)
            except Exception as error:
                run = {"state": "error", "summary": str(error)[:300], "steps": []}
            report = grade(name, project, run, time.monotonic() - started)
            reports.append(report)
            for s in report["steps"]:
                mark = {"done": "✓", "attention": "!", "waiting": "…", "stopped": "■"}.get(s["state"], "·")
                print(f"   {mark} {s['title']} ({s['agent']}, {s['seconds'] or 0}s) {s['summary'][:100]}")
            for f in report["failed"]:
                print(f"     ✗ {f}")
            print(f"   {'PASS' if report['passed'] else 'FAIL'} · {report['checks_passed']}/{report['checks']} checks · "
                  f"{len(report['files'])} files · {report['seconds']}s\n")
            if args.keep:
                target = Path(args.keep) / name
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(engine.projects.folder(project["id"]), target, ignore=shutil.ignore_patterns(".luma"))
        store.close()

    passed = sum(r["passed"] for r in reports)
    print(f"{passed} of {len(reports)} projects passed.")
    if args.save:
        Path(args.save).write_text(json.dumps({"offline": args.offline, "when": time.strftime("%Y-%m-%d %H:%M"), "projects": reports}, indent=2))
        print(f"Report saved to {args.save}")
    sys.exit(0 if reports and passed == len(reports) else 1)


if __name__ == "__main__":
    main()
