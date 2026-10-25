"""Projects from anywhere: the terminal on this computer (with the owner-only token), the window, and
the safety rails on the HTTP side (no token, no work; previews are sandboxed; deleting needs a yes)."""
import base64
import json
import os
import stat
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import work_fakes
from luma.agent.runtime import Agent
from luma.control.server import make_server
from luma.memory.store import Store
from luma.work import terminal


def scripted_planner(messages, context, allowed, mode):
    """A brain that answers work requests the way the fakes do, and chats plainly otherwise."""
    (name, spec), = allowed.items() if len(allowed) == 1 else ((None, None),)
    if name and name.startswith("work."):
        args = work_fakes.deck_args(6) if name == "work.deck" else work_fakes.ARGS.get(name)
        return {"type": "tool", "name": name, "arguments": args} if args else {"type": "reply", "text": "no"}
    return {"type": "reply", "text": "ok"}


class TerminalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "state.db", root / "state.key")
        self.agent = Agent(store=self.store, use_model=False, planner=scripted_planner)
        self.agent.search_web = lambda q: {"results": work_fakes.search(q)}
        os.environ["LUMA_WORK_NO_BROWSER"] = "1"
        self.server = make_server(self.agent, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.server.server_port
        self.state = mock.patch("luma.config.STATE_DIR", root)
        self.state.start()

    def tearDown(self):
        self.state.stop()
        os.environ.pop("LUMA_WORK_NO_BROWSER", None)
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.temp.cleanup()

    def test_the_token_file_is_for_the_owner_only(self):
        info = Path(self.temp.name) / "cli.json"
        self.assertEqual(json.loads(info.read_text())["port"], self.port)
        self.assertEqual(stat.S_IMODE(info.stat().st_mode), 0o600)

    def test_the_terminal_runs_a_project_on_the_app_and_watches_it(self):
        remote = terminal.app_on_this_computer()
        self.assertIsNotNone(remote)
        with mock.patch.object(terminal, "say") as printed:
            run = remote.work("research the Atlanta taco truck market, build the financial projections and a 6-slide deck")
        self.assertEqual(run["state"], "done", run)
        lines = "\n".join(str(c.args[0]) if c.args else "" for c in printed.call_args_list)
        self.assertIn("Plan", lines)
        self.assertIn("Build the financial model", lines)
        self.assertIn("Done.", lines)
        projects = remote.projects()
        self.assertEqual(len(projects), 1)
        detail = remote.project(projects[0]["id"])
        self.assertTrue(any(f["path"].endswith(".pptx") for f in detail["files"]))

    def test_no_token_no_work_and_files_are_sandboxed(self):
        base = f"http://127.0.0.1:{self.port}"
        req = urllib.request.Request(base + "/api/work/run", data=json.dumps({"request": "make a game"}).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer wrong"}, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as refused:
            urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=5)
        self.assertEqual(refused.exception.code, 403)
        remote = terminal.app_on_this_computer()
        with mock.patch.object(terminal, "say"):
            remote.work("make a platformer game")
        pid = remote.projects()[0]["id"]
        token = json.loads((Path(self.temp.name) / "cli.json").read_text())["token"]
        page = urllib.request.Request(base + f"/api/work/file?id={pid}&path=game/taco-dash/index.html&view=1", headers={"Authorization": "Bearer " + token})
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(page, timeout=5) as r:
            self.assertIn("sandbox", r.headers["Content-Security-Policy"])
            self.assertIn(b"<canvas", r.read())
        escape = urllib.request.Request(base + f"/api/work/file?id={pid}&path=../../state.key", headers={"Authorization": "Bearer " + token})
        with self.assertRaises(urllib.error.HTTPError) as blocked:
            urllib.request.build_opener(urllib.request.ProxyHandler({})).open(escape, timeout=5)
        self.assertEqual(blocked.exception.code, 404)
        with self.assertRaises(ValueError):
            remote._post("delete", {"id": pid})  # no confirm, no delete
        self.assertEqual(len(remote.projects()), 1)

    def test_previews_use_a_signed_read_only_link(self):
        remote = terminal.app_on_this_computer()
        with mock.patch.object(terminal, "say"):
            remote.work("make a platformer game")
        detail = remote.project(remote.projects()[0]["id"])
        base = f"http://127.0.0.1:{self.port}" + detail["view"]
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        page = next(f["path"] for f in detail["files"] if f["path"].endswith("index.html"))
        with opener.open(base + page, timeout=5) as r:  # no cookie, no token: the signed link is the permission
            self.assertIn("sandbox", r.headers["Content-Security-Policy"])
            self.assertIn(b"<canvas", r.read())
        other = next(f["path"] for f in detail["files"] if not f["path"].endswith((".html", ".js", ".css", ".svg", ".png", ".json", ".md", ".txt", ".csv")))
        tampered = base.replace(detail["view"].split("/")[-2], "0" * 32)
        for url in (tampered + page, base + "..%2F..%2Fstate.key", base + "../../state.key", base + other):
            with self.assertRaises(urllib.error.HTTPError, msg=url) as refused:
                opener.open(url, timeout=5)
            self.assertEqual(refused.exception.code, 404)

    def test_uploads_land_in_the_project_and_get_analyzed(self):
        remote = terminal.app_on_this_computer()
        project = remote._post("create", {"name": "Sales"})["project"]
        csv_data = "region,amount\nEast,100\nWest,250\nEast,50\n"
        remote._post("upload", {"id": project["id"], "name": "sales.csv", "data": base64.b64encode(csv_data.encode()).decode()})
        self.agent.planner = lambda m, c, a, mode: {"type": "tool", "name": "work.analyze_data", "arguments": {"file": "uploads/sales.csv", "question": "sales by region", "group_by": "region", "measure": "amount"}}
        with mock.patch.object(terminal, "say"):
            run = remote.work("analyze the sales.csv spreadsheet by region", project=project["id"])
        self.assertEqual(run["state"], "done", run)
        grouped = remote.project(project["id"])["run"]["steps"][0]
        self.assertIn("amount by region", grouped["summary"])


if __name__ == "__main__":
    unittest.main()


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "state.db", root / "state.key")
        self.agent = Agent(store=self.store, use_model=False, planner=scripted_planner)
        self.agent.search_web = lambda q: {"results": work_fakes.search(q)}
        os.environ["LUMA_WORK_NO_BROWSER"] = "1"

    def tearDown(self):
        os.environ.pop("LUMA_WORK_NO_BROWSER", None)
        self.store.close()
        self.temp.cleanup()

    def test_a_big_ask_in_chat_becomes_a_project(self):
        reply = self.agent.chat("Research my taco truck idea, prepare the financial projections and build a website")
        self.assertEqual(reply.get("section"), "projects", reply)
        self.assertIn("1) Research the idea", reply["text"])
        from luma.control import work_api
        eng = work_api.engine(self.agent)
        for _ in range(100):
            if not eng.active:
                break
            time.sleep(0.1)
        status = self.agent.chat("how's my project going?")
        self.assertIn("steps done", status["text"])
        self.assertIn("finished", status["text"])

    def test_small_things_and_questions_stay_quick(self):
        from luma.control import work_api
        for text in ["make me a deck about tacos", "how do I build a website?", "what's a financial model?"]:
            with self.subTest(text=text):
                self.assertIsNone(self.agent._project_request(text, text.lower()))
