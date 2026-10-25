"""The execution engine end to end: a request becomes a plan, specialists build real files, checks catch
problems and send them back, runs survive interruptions, and risky steps wait for the owner."""
import json
import os
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import work_fakes
from luma.memory.store import Store
from luma.work import engine as work_engine
from luma.work.engine import Engine, detect
from luma.work.projects import Projects

VISION = ("Research this business idea, analyze competitors, prepare the financial projections, create a 20-slide PowerPoint, "
          "build a branded website, generate the graphics, test the site, and package all the files for me.")


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.projects = Projects(self.store, root / "projects")
        self.brain = work_fakes.Brain()
        self.engine = Engine(self.projects, think=self.brain, search=work_fakes.search, read=lambda url: "", approver=lambda q: True, render=False)
        self.events = []
        self.engine.listeners.append(self.events.append)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def run_request(self, request, name="Taco Rocket"):
        self.project = self.projects.create(name, "A taco truck for downtown Atlanta")
        return self.engine.start(self.project["id"], request)

    def files(self):
        return {f["path"] for f in self.projects.files(self.project["id"])}


class PlanTests(unittest.TestCase):
    def test_spots_every_deliverable_in_order(self):
        self.assertEqual(detect(VISION), ["research", "financial_model", "graphics", "deck", "website", "package"])
        self.assertEqual(detect("make me a platformer game"), ["game"])
        self.assertEqual(detect("design a 3D printable bracket for my shelf"), ["model3d"])
        self.assertEqual(detect("analyze my sales.csv and write a report"), ["analyze_data", "document"])
        self.assertEqual(detect("build a landing page for my bakery"), ["website"])  # a site isn't a coding project
        self.assertEqual(detect("write a python script that renames my photos"), ["code"])
        self.assertEqual(detect("a coffee cart financial model and a one-page Word summary"), ["financial_model", "document"])

    def test_each_step_gets_what_it_needs(self):
        steps = work_engine.plan_from(VISION, detect(VISION))
        by_tool = {s["tool"]: s for s in steps}
        self.assertEqual(by_tool["financial_model"]["needs"], [by_tool["research"]["n"]])
        self.assertEqual(set(by_tool["deck"]["needs"]), {by_tool["research"]["n"], by_tool["financial_model"]["n"], by_tool["graphics"]["n"]})
        self.assertEqual(by_tool["package"]["needs"], [s["n"] for s in steps[:-1]])
        self.assertEqual({s["agent"] for s in steps}, {"research", "data", "design", "document", "qa"})


class VisionTests(Base):
    def test_the_blueprint_request_is_planned_executed_verified_and_delivered(self):
        run = self.run_request(VISION)
        self.assertEqual(run["state"], "done", run.get("summary"))
        self.assertTrue(all(s["state"] == "done" for s in run["steps"]), [(s["title"], s.get("checks")) for s in run["steps"] if s["state"] != "done"])
        files = self.files()
        for wanted in ["research/taco-truck-market-in-atlanta.md", "research/taco-truck-market-in-atlanta.docx", "finance/taco-rocket-model.xlsx",
                       "deck/taco-rocket-pitch.pptx", "site/taco-rocket/index.html", "site/taco-rocket/menu.html", "graphics/taco-rocket-logo.svg",
                       "package/taco-rocket.zip", "README.md"]:
            self.assertIn(wanted, files)
        bundle = zipfile.ZipFile(self.projects.path(self.project["id"], "package/taco-rocket.zip"))
        self.assertIn("deck/taco-rocket-pitch.pptx", bundle.namelist())
        research = run["steps"][0]["data"]
        self.assertTrue(all(set(f["sources"]) <= {s["id"] for s in research["sources"]} for f in research["findings"]))  # the made-up citation was dropped
        self.assertEqual(len(research["conflicts"]), 1)
        deck_prompt = next(c["prompt"] for c in self.brain.calls if c["name"] == "work.deck")
        self.assertIn("Result of step 2 (Build the financial model)", deck_prompt)  # the model's numbers reach the deck
        self.assertIn("document agent", deck_prompt)
        self.assertEqual({c["tier"] for c in self.brain.calls if c["name"] == "work.graphics"}, {"standard"})
        log = (self.projects.folder(self.project["id"]) / ".luma" / "runs" / f"{run['id']}.jsonl").read_text().splitlines()
        self.assertEqual(len(log), len(run["steps"]))  # every step is in the run log
        self.assertEqual(self.projects.get(self.project["id"])["runs"][-1]["state"], "done")

    def test_the_spreadsheet_is_live(self):
        self.run_request("prepare the financial projections")
        from openpyxl import load_workbook
        book = load_workbook(str(self.projects.path(self.project["id"], "finance/taco-rocket-model.xlsx")))
        self.assertEqual(book["Monthly"]["C2"].value, "=B2*Assumptions!$B$2")
        self.assertTrue(str(book["Yearly"]["B2"].value).startswith("=SUM(Monthly!C2:C13)"))


class QualityTests(Base):
    def test_failing_checks_go_back_to_the_specialist_with_the_reason(self):
        broken = {"folder": "calc", "test_command": "python -m unittest -v", "run_command": "",
                  "files": [{"path": "calc.py", "content": "def total(p):\n    return sum(p)\n"},
                            {"path": "test_calc.py", "content": "import unittest\nfrom calc import total\nclass T(unittest.TestCase):\n    def test_tip(self):\n        self.assertEqual(total([10]), 11.8)\n"}]}
        fixed = work_fakes.ARGS["work.code"]
        self.brain.overrides["work.code"] = lambda n: broken if n == 1 else fixed
        run = self.run_request("write a python script that adds up an order with tip")
        step = run["steps"][0]
        self.assertEqual(step["state"], "done", step.get("checks"))
        retry = [c for c in self.brain.calls if c["name"] == "work.code"][1]["prompt"]
        self.assertIn("tests pass", retry)
        self.assertIn("AssertionError", retry)  # the actual failure output went back

    def test_a_step_that_still_fails_is_flagged_not_hidden(self):
        self.brain.overrides["work.game"] = {"title": "Walls", "genre": "topdown", "goal": "", "player_color": "", "accent_color": "",
                                             "level": ["##########", "#P  #   G#", "#   #    #", "##########"]}
        run = self.run_request("make a top-down game")
        self.assertEqual(run["steps"][0]["state"], "attention")
        self.assertIn("the goal can be reached", json.dumps(run["steps"][0]["checks"]))
        self.assertIn("Needs a look", run["summary"])

    def test_no_brain_still_delivers_what_it_can(self):
        engine = Engine(self.projects, think=None, search=work_fakes.search, render=False)
        project = self.projects.create("Solo")
        run = engine.start(project["id"], "research the Atlanta food truck market and write a report")
        research, report, package = run["steps"]  # two deliverables get packaged too
        self.assertEqual(research["state"], "done")  # cited snippets, marked low confidence
        self.assertEqual(report["state"], "attention")  # a document needs a writer
        self.assertIn("No brain answered", report["summary"])


class SafetyTests(Base):
    def test_code_waits_for_the_owner_where_it_cant_be_sandboxed(self):
        self.engine.approver = None
        with mock.patch.object(work_engine.sandbox, "contained", return_value=False):
            run = self.run_request("write a python script that adds up an order with tip")
            self.assertEqual(run["state"], "waiting")
            self.assertEqual(run["steps"][0]["state"], "waiting")
            self.assertIn("needs your OK", run["steps"][0]["summary"])
            self.engine.allow_code(self.project["id"])
            resumed = self.engine.start(self.project["id"], None, resume=run["id"])
        self.assertEqual(resumed["state"], "done")
        self.assertEqual(resumed["steps"][0]["state"], "done")

    def test_an_interrupted_run_picks_up_where_it_stopped(self):
        stop = threading.Event()
        def stop_after_research(event):
            if event.get("type") == "step" and event.get("state") == "done" and event.get("step") == 1:
                stop.set()
        self.engine.listeners.append(stop_after_research)
        self.project = self.projects.create("Taco Rocket")
        run = self.engine.start(self.project["id"], "research the market, then build the financial projections", cancel=stop)
        self.assertEqual(run["state"], "stopped")
        self.assertEqual([s["state"] for s in run["steps"]], ["done", "pending", "pending"])
        calls = len(self.brain.calls)
        self.engine.listeners.remove(stop_after_research)
        again = self.engine.start(self.project["id"], None, resume=run["id"])
        self.assertEqual([s["state"] for s in again["steps"]], ["done", "done", "done"])
        self.assertFalse(any(c["name"] == "work.research" for c in self.brain.calls[calls:]))  # research wasn't redone

    def test_one_run_per_project_at_a_time(self):
        self.project = self.projects.create("Busy")
        self.engine.active[self.project["id"]] = threading.Event()
        with self.assertRaises(ValueError):
            self.engine.start(self.project["id"], "make a game")


@unittest.skipUnless(os.environ.get("LUMA_WORK_BROWSER_TESTS") == "1" or __import__("importlib").util.find_spec("playwright"), "needs a browser")
class BrowserTests(Base):
    def test_sites_and_games_are_tested_in_a_real_browser(self):
        self.engine.render = Engine._browser_ok()
        if not self.engine.render:
            self.skipTest("no browser")
        try:
            run = self.run_request("build the website and a platformer game")
        except Exception as error:  # a sandbox without a usable Chromium
            self.skipTest(str(error))
        site, game = run["steps"][0], run["steps"][1]
        if site["data"].get("browser", {}).get("unavailable"):
            self.skipTest("Chromium couldn't start here")
        self.assertEqual(site["state"], "done", site["checks"])
        self.assertIn("fits a phone screen", [c["check"] for c in site["checks"]])
        self.assertTrue(any(f.startswith("previews/") for f in site["files"]))
        self.assertEqual(game["state"], "done", game["checks"])
        self.assertTrue(game["data"]["played"]["moved"])


if __name__ == "__main__":
    unittest.main()
