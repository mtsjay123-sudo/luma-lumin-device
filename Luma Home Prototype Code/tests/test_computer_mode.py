"""Computer mode and skill notes.

Computer mode: the device uses a paired computer as its hands, but only in the ways the person at that computer
turned on there: folders they shared, opening apps, and (off by default) looking at the screen. Keys and passwords
are never read, nothing outside the shared folders is reachable, Pause stops everything, and every request is logged
on both sides.

Skill notes: SKILL.md folders (the Claude Code / Hermes format) become guidance for a matching turn, can't add
tools, and are only added after the owner's yes."""
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from luma.agent.runtime import Agent
from luma.agent import skill_notes
from luma.control.computer import Computer
from luma.control.server import make_server
from luma.llm.prompts import build_plan_prompt
from luma.memory.store import Store

from test_link import LinkBase

SKILL = """---
name: weekly-review
description: Run a calm weekly review of goals, wins and next week's plan
version: 1.0.0
license: MIT
metadata:
  hermes:
    tags: [planning, review, productivity]
---
# Weekly review
1. Ask what went well this week.
2. Ask what's left over.
3. Pick three things for next week.
"""


def home_is(test, root):
    """Shared folders must be inside the home folder, so the test's temp folder plays home."""
    patcher = mock.patch("pathlib.Path.home", return_value=Path(root).resolve())
    patcher.start()
    test.addCleanup(patcher.stop)


class ComputerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        home_is(self, root)
        self.store = Store(root / "s.db", root / "k")
        self.computer = Computer(self.store, time.time)
        self.shared = root / "Documents"
        (self.shared / "work").mkdir(parents=True)
        (self.shared / "work" / "Resume 2026.txt").write_text("Jay Doe\nProduct designer")
        (self.shared / "resume-old.txt").write_text("old")
        (self.shared / ".hidden-resume.txt").write_text("hidden")
        (self.shared / ".ssh").mkdir()
        (self.shared / ".ssh" / "id_rsa").write_text("PRIVATE KEY")
        (self.shared / "passwords resume.txt").write_text("hunter2")
        (self.shared / "photo.bin").write_bytes(b"\x00\x01binary")
        (self.shared / "proj" / ".git").mkdir(parents=True)
        (self.shared / "proj" / ".git" / "config").write_text("url = https://token@github.com/x/y")
        self.outside = root / "outside.txt"
        self.outside.write_text("not shared")
        (self.shared / "sneaky.txt").symlink_to(self.outside)
        (self.shared / "resume-link.txt").symlink_to(self.outside)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_nothing_is_shared_until_the_person_here_turns_it_on(self):
        self.assertEqual(self.computer.settings(), {"folders": [], "apps": False, "screen": False, "control": False, "paused": False})
        self.assertIn("No folders are shared", self.computer.do({"kind": "files.find", "query": "resume"})["error"])
        self.assertIn("Opening apps is off", self.computer.do({"kind": "app.open", "name": "Spotify"})["error"])
        self.assertIn("Looking at the screen is off", self.computer.do({"kind": "screen.look"})["error"])
        self.assertIn("can't do that", self.computer.do({"kind": "files.delete", "path": str(self.shared)})["error"])

    def test_find_and_read_only_inside_shared_folders_and_never_secrets(self):
        self.computer.grant(str(self.shared))
        found = self.computer.do({"kind": "files.find", "query": "resume"})["files"]
        names = {f["name"] for f in found}
        self.assertEqual(names, {"Resume 2026.txt", "resume-old.txt"})  # not hidden files, not the passwords file
        read = self.computer.do({"kind": "files.read", "path": str(self.shared / "work" / "Resume 2026.txt")})
        self.assertIn("Product designer", read["text"])
        for path in [self.outside, self.shared / "sneaky.txt", self.shared / ".ssh" / "id_rsa", self.shared / "passwords resume.txt",
                     self.shared / "work" / ".." / ".." / "outside.txt", self.shared / ".hidden-resume.txt", self.shared / "proj" / ".git" / "config"]:
            self.assertIn("isn't in a folder you've shared", self.computer.do({"kind": "files.read", "path": str(path)})["error"], path)
        self.assertIn("not a text file", self.computer.do({"kind": "files.read", "path": str(self.shared / "photo.bin")})["error"])

    def test_some_folders_can_never_be_shared(self):
        (Path(self.temp.name) / "Library" / "Notes").mkdir(parents=True)
        for bad in [str(Path.home()), "/", str(Path.home().parent), "/etc", str(self.shared / ".ssh"), str(self.shared / "proj" / ".git"),
                    str(Path(self.temp.name) / "Library" / "Notes"), str(self.shared / "nope")]:
            with self.assertRaises(ValueError, msg=bad):
                self.computer.grant(bad)
        self.computer.grant(str(self.shared))
        self.computer.grant(str(self.shared))  # twice is still once
        self.assertEqual(self.computer.settings()["folders"], [str(self.shared.resolve())])
        self.computer.revoke(str(self.shared.resolve()))
        self.assertEqual(self.computer.settings()["folders"], [])

    def test_app_names_are_checked_before_anything_runs(self):
        self.computer.allow("apps", True)
        for name in ["", "Spotify; rm -rf ~", "x&calc", "a|b", "it's", "evil.bat", "../../bin/sh", "-a", "x" * 80]:
            self.assertIn("app's name", self.computer.do({"kind": "app.open", "name": name})["error"])

    def test_pause_stops_everything_and_the_log_keeps_it(self):
        agent = Agent(store=self.store, use_model=False)
        computer = agent.link.computer
        computer.grant(str(self.shared))
        self.assertTrue(agent.link._do({"kind": "files.find", "query": "resume"})["files"])
        computer.pause(True)
        for job in [{"kind": "files.find", "query": "resume"}, {"kind": "open", "url": "https://example.com"}, {"kind": "play", "query": "lofi"}]:
            self.assertIn("paused", agent.link._do(job)["error"])
        computer.pause(False)
        log = computer.log()
        self.assertEqual([e["kind"] for e in log], ["files.find", "pause", "files.find", "open", "play", "resume"])
        self.assertEqual([e["ok"] for e in log], [True, True, False, False, False, True])

    def test_the_agent_uses_its_own_computer_when_it_runs_right_here(self):
        agent = Agent(store=self.store, use_model=False)
        agent.link.computer.grant(str(self.shared))
        self.assertTrue(agent.computer_ready())
        self.assertIn("computer.find", agent.available_tools("find my resume on my laptop"))
        got = agent._run("computer.find", {"query": "resume"})
        self.assertIn("Found 2", got["summary"])
        read = agent._run("computer.read", {"path": got["files"][0]["path"]})
        self.assertTrue(read["text"])
        self.assertIn("Opening apps is off", agent._run("computer.open_app", {"name": "Spotify"})["summary"])
        agent.store.set_setting("mode", "kids")
        self.assertFalse(agent.computer_ready())
        with self.assertRaises(ValueError):
            agent.propose("computer.find", {"query": "resume"})

    def test_clicking_and_typing_in_apps_is_off_until_turned_on_and_mac_only(self):
        ran = []
        run = lambda *a, **k: ran.append(a) or self.fail("nothing runs while it's off")
        with self.assertRaisesRegex(ValueError, "Clicking and typing in apps is off"):
            self.computer._ui({"kind": "ui.read", "app": "Notes"}, run=run)
        self.computer.allow("control", True)
        with mock.patch("luma.control.computer.sys.platform", "linux"), self.assertRaisesRegex(ValueError, "works on a Mac"):
            self.computer._ui({"kind": "ui.read", "app": "Notes"}, run=run)
        self.assertEqual(ran, [])

    def test_it_reads_an_app_window_and_acts_only_on_what_it_saw(self):
        from luma.control.computer import UI_SCRIPT
        self.computer.allow("control", True)
        calls = []
        replies = [{"app": "Notes", "window": "Groceries", "elements": [{"ref": 12, "role": "Button", "label": "New Note"}, {"ref": 30, "role": "TextArea", "label": "Note", "value": "eggs"}]},
                   {"app": "Notes", "pressed": "New Note"}, {"error": "changed", "app": "Notes"}, {"error": "password", "app": "Notes"}]
        def run(argv, **kw):
            calls.append(argv)
            return mock.Mock(returncode=0, stdout=json.dumps(replies[len(calls) - 1]), stderr="")
        with mock.patch("luma.control.computer.sys.platform", "darwin"):
            seen = self.computer._ui({"kind": "ui.read", "app": "Notes"}, run=run)
            self.assertEqual(seen["elements"][0]["label"], "New Note")
            self.assertEqual(calls[0][:5], ["osascript", "-l", "JavaScript", "-e", UI_SCRIPT])
            job = json.loads(calls[0][5])  # the request travels as data, never spliced into the script
            self.assertEqual((job["kind"], job["app"]), ("ui.read", "Notes"))
            self.assertEqual(self.computer._ui({"kind": "ui.press", "app": "Notes", "ref": 12, "role": "Button", "label": "New Note"}, run=run)["pressed"], "New Note")
            self.assertEqual({k: json.loads(calls[1][5])[k] for k in ("ref", "role", "label")}, {"ref": 12, "role": "Button", "label": "New Note"})
            with self.assertRaisesRegex(ValueError, "changed since I looked"):
                self.computer._ui({"kind": "ui.press", "app": "Notes", "ref": 12, "role": "Button", "label": "New Note"}, run=run)
            with self.assertRaisesRegex(ValueError, "never type into password fields"):
                self.computer._ui({"kind": "ui.type", "app": "Notes", "ref": 3, "role": "TextField", "label": "Password", "text": "x"}, run=run)
            for app in ["Terminal", "iTerm2", "1Password 7", "Keychain Access", "System Settings", "Luma"]:
                with self.assertRaisesRegex(ValueError, "don't click or type in that app"):
                    self.computer._ui({"kind": "ui.read", "app": app}, run=run)
            with self.assertRaisesRegex(ValueError, "Look at the window first"):
                self.computer._ui({"kind": "ui.press", "app": "Notes", "ref": "12", "role": "Button", "label": "New Note"}, run=run)
            with self.assertRaisesRegex(ValueError, "app's name"):
                self.computer._ui({"kind": "ui.read", "app": "Notes; rm -rf ~"}, run=run)
            denied = lambda argv, **kw: mock.Mock(returncode=1, stdout="", stderr="execution error: osascript is not allowed assistive access. (-25211)")
            with self.assertRaisesRegex(ValueError, "Accessibility"):
                self.computer._ui({"kind": "ui.read", "app": "Notes"}, run=denied)
        self.assertEqual(len(calls), 4)

    def test_every_click_and_keystroke_waits_for_a_yes(self):
        agent = Agent(store=self.store, use_model=False)
        agent.link.computer.allow("control", True)
        self.assertIn("computer.ui_press", agent.available_tools("in notes click new note"))
        self.assertNotIn("computer.ui_press", agent.available_tools("what's the weather"))
        did = []
        agent.link.computer.do = lambda job: did.append(job) or {"app": "Notes", "pressed": job.get("label"), "typed": job.get("label")}
        pending = agent.propose("computer.ui_press", {"app": "Notes", "ref": 12, "role": "Button", "label": "New Note"})
        self.assertEqual(pending["state"], "pending")
        self.assertEqual(pending["text"], "Want me to press “New Note” in Notes?")
        self.assertEqual(pending["review"], {"app": "Notes", "does": "press “New Note”"})
        self.assertEqual(did, [], "nothing happens before the yes")
        done = agent.confirm(pending["action"], pending["confirm_token"])
        self.assertEqual(did[0], {"kind": "ui.press", "app": "Notes", "ref": 12, "role": "Button", "label": "New Note"})
        self.assertIn("Pressed “New Note” in Notes", json.dumps(done, ensure_ascii=False))
        typed = agent.propose("computer.ui_type", {"app": "Notes", "ref": 30, "role": "TextArea", "label": "Note", "text": "milk"})
        self.assertEqual(typed["text"], "Want me to type “milk” into “Note” in Notes?")
        self.assertEqual(len(did), 1)
        agent.rules.set("computer_act", "block")
        with self.assertRaises(ValueError):
            agent.propose("computer.ui_press", {"app": "Notes", "ref": 12, "role": "Button", "label": "New Note"})
        with self.assertRaises(ValueError):
            agent.rules.set("computer_act", "allow")  # never skips the yes
        agent.store.set_setting("mode", "kids")
        self.assertFalse(agent.computer_ready())

    def test_a_bad_request_is_logged_as_failed_not_lost(self):
        agent = Agent(store=self.store, use_model=False)
        agent.link.computer.grant(str(self.shared))
        self.assertTrue(agent.link._do({"kind": "files.find", "query": "resume", "limit": ["x"]})["error"])
        with mock.patch.object(agent.link, "_work", side_effect=RuntimeError("boom")):
            self.assertEqual(agent.link._do({"kind": "open", "url": "https://example.com"}), {"error": "boom"})
        self.assertEqual([(e["kind"], e["ok"]) for e in agent.link.computer.log()], [("files.find", False), ("open", False)])

    def test_questions_about_the_screen_still_get_the_computer(self):
        agent = Agent(store=self.store, use_model=False)
        self.assertIn("computer.look", agent.available_tools("what's on my screen?"))
        self.assertIn("computer.find", agent.available_tools("what files are in my downloads folder"))

    def test_find_gives_the_model_paths_it_can_read_next(self):
        agent = Agent(store=self.store, use_model=False)
        agent.link.computer.grant(str(self.shared))
        got = agent._run("computer.find", {"query": "resume 2026"})
        seen = agent._observation_prompt("find my resume", "computer.find", got)
        self.assertIn(json.dumps(str(self.shared.resolve() / "work" / "Resume 2026.txt"))[1:-1], seen)

    def test_find_my_file_on_my_laptop_works_without_the_brain(self):
        agent = Agent(store=self.store, use_model=False)
        self.assertIn("No folders are shared", agent.chat("find my resume on my laptop")["text"])
        agent.link.computer.grant(str(self.shared))
        self.assertIn("Resume 2026.txt", agent.chat("yo where's my resume on my computer")["text"])

    def test_the_owner_can_block_it_in_rules(self):
        agent = Agent(store=self.store, use_model=False)
        agent.rules.set("computer", "block")
        with self.assertRaises(ValueError):
            agent.propose("computer.find", {"query": "resume"})


class ComputerOverLink(LinkBase):
    def test_the_device_finds_a_file_on_the_paired_laptop(self):
        home_is(self, Path(self.temp.name) / "laptop")
        self.pair()
        shared = Path(self.temp.name) / "laptop" / "Documents"
        shared.mkdir()
        (shared / "taxes 2025.txt").write_text("refund: $412")
        self.laptop.link.computer.grant(str(shared))
        self.assertFalse(self.device.computer_ready())
        self.assertNotIn("computer.find", self.device.available_tools("find my taxes file on my laptop"))
        self.assertIn("isn't connected", self.device._run("computer.find", {"query": "taxes"})["summary"])

        def one_round():
            job = self.laptop.link.call("GET", "/link/hands/next", timeout=40).get("job")
            self.laptop.link.call("POST", "/link/hands/done", {"id": job["id"], "result": self.laptop.link._do(job)})
        worker = threading.Thread(target=one_round, daemon=True)
        worker.start()
        for _ in range(50):
            if self.device.link_host.connected(): break
            time.sleep(0.05)
        self.assertTrue(self.device.computer_ready())
        self.assertIn("computer.find", self.device.available_tools("find my taxes file on my laptop"))
        got = self.device._run("computer.find", {"query": "taxes"})
        worker.join(10)
        self.assertIn("taxes 2025.txt", got["summary"])
        # both sides keep a record: the laptop's log, and the device's (which the phone shows)
        self.assertEqual(self.laptop.link.computer.log()[-1]["kind"], "files.find")
        recent = self.device.link_host.recent(1)[0]
        self.assertEqual((recent["kind"], recent["what"], recent["ok"]), ("files.find", "taxes", True))
        from luma.control import today
        self.assertEqual(today.device(self.device)["computer"]["recent"][0]["kind"], "files.find")


class SkillNoteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        os.environ["LUMA_SKILLS_DIR"] = str(root / "skills")
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        os.environ.pop("LUMA_SKILLS_DIR", None)
        self.store.close()
        self.temp.cleanup()

    def test_reads_the_hermes_and_claude_format(self):
        skill = skill_notes.parse(SKILL)
        self.assertEqual((skill["name"], skill["version"]), ("weekly-review", "1.0.0"))
        self.assertEqual(skill["tags"], ["planning", "review", "productivity"])
        self.assertTrue(skill["body"].startswith("# Weekly review"))
        for bad in ["no front matter", "---\nname: x\n---\nbody", "---\ndescription: d\n---\nbody", "---\nname: Bad Name!\ndescription: d\n---\nbody",
                    "---\nname: ok\ndescription: d\n---\n", "---\nname: ok\ndescription: d\n---\n" + "x" * 70000]:
            with self.assertRaises(ValueError, msg=bad[:30]):
                skill_notes.parse(bad)

    def test_adding_a_skill_waits_for_a_yes_then_guides_matching_turns(self):
        with self.assertRaises(ValueError):
            self.agent.propose("skills.install", {"content": "not a skill"})
        pending = self.agent.propose("skills.install", {"content": SKILL})
        self.assertEqual(pending["state"], "pending")
        self.assertEqual(pending["review"]["skill"], "weekly-review")
        self.assertEqual(self.agent.skill_notes.list(), [])  # nothing until they say yes
        self.assertNotIn("skills.install", self.agent.available_tools("install the weekly review skill"))  # never the model's to offer
        self.agent.confirm(pending["action"], pending["confirm_token"])
        self.assertEqual([s["name"] for s in self.agent.skill_notes.list()], ["weekly-review"])

        context = self.agent._mind_context("can we do my weekly review and plan next week")
        notes = [m["text"] for m in context if m.get("skill")]
        self.assertEqual(len(notes), 1)
        self.assertIn("Pick three things for next week", notes[0])
        self.assertFalse([m for m in self.agent._mind_context("what's the weather") if m.get("skill")])
        prompt = build_plan_prompt(context, {}, "friend", None, "now")
        self.assertIn("can't give you new tools", prompt)
        self.assertIn("Pick three things for next week", prompt)
        self.assertNotIn("Pick three things", build_plan_prompt(context, {}, "kids", None, "now"))

        self.agent.store.set_setting("mode", "kids")
        self.assertFalse([m for m in self.agent._mind_context("weekly review plan next week") if m.get("skill")])
        self.agent.store.set_setting("mode", "friend")
        self.agent.skill_notes.remove("weekly-review")
        self.assertEqual(self.agent.skill_notes.list(), [])

    def test_a_broken_skill_on_disk_is_skipped_not_fatal(self):
        bad = self.agent.skill_notes.folder / "broken"
        bad.mkdir(parents=True)
        (bad / "SKILL.md").write_text("garbage")
        odd = self.agent.skill_notes.folder / "odd"
        odd.mkdir()
        (odd / "SKILL.md").write_text("---\nname: odd\ndescription: weekly review odd one\nmetadata:\n  hermes: [a]\n---\nbody")
        self.assertEqual(skill_notes.parse((odd / "SKILL.md").read_text())["tags"], [])
        (odd / "SKILL.md").write_text("---\nname: odd\ndescription: d\nmetadata: [x]\n---\nbody")
        self.assertTrue(self.agent._mind_context("weekly review please") is not None)
        self.agent.skill_notes.install(SKILL)
        self.assertEqual(sorted(s["name"] for s in self.agent.skill_notes.list()), ["odd", "weekly-review"])

    def test_a_skill_in_a_differently_named_folder_can_still_be_removed(self):
        where = self.agent.skill_notes.folder / "my-folder"
        where.mkdir(parents=True)
        (where / "SKILL.md").write_text(SKILL)
        self.assertEqual(self.agent.skill_notes.remove("weekly-review"), {"removed": "weekly-review"})
        self.assertFalse(where.exists())

    def test_short_names_only_match_whole_words(self):
        self.agent.skill_notes.install("---\nname: art\ndescription: Help with drawing and painting\n---\nSketch first.")
        self.assertEqual(self.agent.skill_notes.match("can you start the party playlist"), [])
        self.assertEqual([s["name"] for s in self.agent.skill_notes.match("ideas for a painting and drawing")], ["art"])


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        os.environ["LUMA_SKILLS_DIR"] = str(root / "skills")
        home_is(self, root)
        self.agent = Agent(store=self.store, use_model=False)
        self.server = make_server(self.agent, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.folder = root / "Shared"
        self.folder.mkdir()

    def tearDown(self):
        os.environ.pop("LUMA_SKILLS_DIR", None)
        self.server.control_context.stop.set()
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.temp.cleanup()

    def call(self, path, data=None, owner=True):
        headers = {"Content-Type": "application/json", "Origin": self.base}
        if owner: headers["Cookie"] = "luma_owner=" + self.server.control_context.owner_session
        request = urllib.request.Request(self.base + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_computer_settings_are_owner_only(self):
        self.assertIn(self.call("/api/computer", owner=False)[0], {401, 403})
        status, body = self.call("/api/computer", {"action": "grant", "folder": str(self.folder)})
        self.assertEqual(status, 200)
        self.assertEqual(body["folders"], [str(self.folder.resolve())])
        status, body = self.call("/api/computer", {"action": "allow", "what": "screen", "on": True})
        self.assertTrue(body["screen"])
        status, body = self.call("/api/computer", {"action": "pause"})
        self.assertTrue(body["paused"])
        self.assertEqual(self.call("/api/computer", {"action": "explode"})[0], 400)
        self.agent.store.set_setting("mode", "kids")
        self.assertEqual(self.call("/api/computer")[0], 403)

    def test_skills_add_through_an_approval(self):
        status, body = self.call("/api/skills/add", {"content": SKILL})
        self.assertEqual((status, body["state"], body["tool"]), (200, "pending", "skills.install"))
        self.assertEqual(self.call("/api/skills")[1]["skills"], [])
        self.agent.confirm(body["action"], body["confirm_token"])
        self.assertEqual([s["name"] for s in self.call("/api/skills")[1]["skills"]], ["weekly-review"])
        self.assertEqual(self.call("/api/skills/remove", {"name": "weekly-review"})[1], {"removed": "weekly-review"})
        self.assertEqual(self.call("/api/skills/add", {"content": "nope"})[0], 400)


if __name__ == "__main__":
    unittest.main()
