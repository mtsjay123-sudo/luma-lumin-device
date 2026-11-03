"""Apple Shortcuts: the owner's own automations, so Luma can reach almost any app on their Mac (Reminders, Notes, Home,
Things...). Off until they turn it on at that computer, a Mac only, the exact shortcut by name (never a command line),
and every run waits for the owner's yes with the shortcut and its input shown."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from luma.agent.runtime import Agent
from luma.control.computer import Computer
from luma.memory.store import Store


class FakeShortcuts:
    """Answers the `shortcuts` command like a Mac with three shortcuts."""
    def __init__(self, names=("Add to Groceries", "Log Water", "Good Night"), says="Added milk"):
        self.names, self.says, self.calls, self.input = list(names), says, [], None

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        if argv[:2] == ["shortcuts", "list"]:
            return SimpleNamespace(returncode=0, stdout="\n".join(self.names) + "\n", stderr="")
        if "--input-path" in argv:
            self.input = Path(argv[argv.index("--input-path") + 1]).read_text()
        Path(argv[argv.index("--output-path") + 1]).write_text(self.says)
        return SimpleNamespace(returncode=0, stdout="", stderr="")


class ShortcutsOnTheMacTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.computer = Computer(self.store, time.time)
        mac = mock.patch("luma.control.computer.sys.platform", "darwin")
        mac.start()
        self.addCleanup(mac.stop)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_off_until_turned_on_here(self):
        self.assertFalse(self.computer.settings()["shortcuts"])
        with self.assertRaisesRegex(ValueError, "Running Shortcuts is off"):
            self.computer._shortcut({"name": "Log Water"}, run=lambda *a, **k: self.fail("nothing runs while it's off"))

    def test_only_on_a_mac(self):
        self.computer.allow("shortcuts", True)
        with mock.patch("luma.control.computer.sys.platform", "win32"):
            with self.assertRaisesRegex(ValueError, "isn't a Mac"):
                self.computer._shortcuts({}, run=lambda *a, **k: self.fail("no Shortcuts app here"))

    def test_lists_and_runs_by_exact_name_with_the_input_as_a_file(self):
        self.computer.allow("shortcuts", True)
        fake = FakeShortcuts()
        self.assertEqual(self.computer._shortcuts({}, run=fake)["shortcuts"], ["Add to Groceries", "Log Water", "Good Night"])
        got = self.computer._shortcut({"name": "add to groceries", "input": "milk; rm -rf ~"}, run=fake)
        self.assertEqual(got, {"shortcut": "Add to Groceries", "output": "Added milk", "cut": False})
        argv = fake.calls[-1]
        self.assertEqual(argv[:3], ["shortcuts", "run", "Add to Groceries"], "the real name, as one argument, no shell")
        self.assertEqual(fake.input, "milk; rm -rf ~", "the input is data in a file, never part of a command")

    def test_a_shortcut_that_isnt_there_isnt_guessed(self):
        self.computer.allow("shortcuts", True)
        fake = FakeShortcuts()
        with self.assertRaisesRegex(ValueError, "no shortcut called"):
            self.computer._shortcut({"name": "Delete Everything"}, run=fake)
        self.assertEqual([c[:2] for c in fake.calls], [["shortcuts", "list"]])

    def test_it_goes_through_the_link_like_every_computer_job(self):
        self.computer.allow("shortcuts", True)
        with mock.patch("luma.control.computer.subprocess.run", FakeShortcuts()):
            self.assertEqual(self.computer.do({"kind": "shortcuts.list"})["count"], 3)
            self.computer.pause(True)
            self.assertIn("paused", self.computer.do({"kind": "shortcuts.run", "name": "Log Water"})["error"])


class ShortcutsFromTheDeviceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_every_run_waits_for_a_yes_with_the_shortcut_and_input_shown(self):
        tools = self.agent.available_tools("add milk to my groceries shortcut")
        self.assertIn("computer.shortcut", tools)
        self.assertIn("computer.shortcuts", tools)
        self.assertIn("computer.shortcuts", self.agent.available_tools("put eggs in my Reminders"))
        ran = []
        self.agent.link.computer.do = lambda job: ran.append(job) or {"shortcut": job.get("name"), "output": "Added milk"}
        listed = self.agent._computer("computer.shortcuts", {})
        self.assertEqual(ran[0]["kind"], "shortcuts.list")
        self.assertIn("no shortcuts on your Mac yet", listed["summary"])
        ran.clear()
        pending = self.agent.propose("computer.shortcut", {"name": "Add to Groceries", "input": "milk", "why": "groceries"})
        self.assertEqual(pending["text"], "Want me to run your “Add to Groceries” shortcut with “milk” on your Mac?")
        self.assertEqual(pending["review"]["app"], "Shortcuts")
        self.assertEqual(ran, [], "nothing runs before the yes")
        done = self.agent.confirm(pending["action"], pending["confirm_token"])
        self.assertEqual((ran[0]["kind"], ran[0]["name"], ran[0]["input"]), ("shortcuts.run", "Add to Groceries", "milk"))
        self.assertIn("Added milk", json.dumps(done))
        self.agent.rules.set("computer_act", "block")
        with self.assertRaises(ValueError):
            self.agent.propose("computer.shortcut", {"name": "Log Water", "input": "", "why": ""})

    def test_never_in_kids_mode(self):
        self.agent.set_mode("kids")
        self.assertNotIn("computer.shortcut", self.agent.available_tools("run my bedtime shortcut"))


if __name__ == "__main__":
    unittest.main()
