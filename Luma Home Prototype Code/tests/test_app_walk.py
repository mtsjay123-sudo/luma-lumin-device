"""Both apps, walked in a real browser at six sizes, light and dark (tests/app_walk.cjs). A Luma with a few days of
made-up life is served, and every screen is opened: nothing may error, fail to load, run off the screen, sit under the
floating ask bar at the end of a page, or be too small for a thumb; and the apps must say a few things right (one
memory count, a task's real days, no model's name where a customer reads, no passing remark as a memory card).

Skipped where node can't drive a browser (the same rule as tests/test_orb.py)."""
import json
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.control.server import make_server
from luma.memory.store import Store

HERE = Path(__file__).resolve().parent


def browser():
    node = shutil.which("node")
    if not node:
        return False
    try:
        return subprocess.run([node, "-e", "require.resolve('playwright')"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


@unittest.skipUnless(browser(), "node with Playwright isn't here")
class AppWalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        cls.store = Store(root / "s.db", root / "k")
        cls.store.set_setting("signed_up", True)
        cls.store.set_setting("luma_account_pending", {"email": "sam@example.invalid", "name": "Sam"})  # past the account screen
        cls.agent = Agent(store=cls.store, use_model=False)
        for line in ["my sister's name is Dana", "my mom's birthday is June 3", "I left my keys on the hook by the door", "I'm allergic to shellfish",
                     "add milk and eggs to my shopping list", "every weekday at 8, tell me what's on my to-do list", "I had such a long day at work",
                     "I don't need advice, I just need to vent", "please don't bring up my ex again"]:
            cls.agent.chat(line)
        cls.server = make_server(cls.agent, 0)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        out = subprocess.run([shutil.which("node"), str(HERE / "app_walk.cjs"), f"http://127.0.0.1:{cls.server.server_port}"],
                             capture_output=True, text=True, timeout=900)
        cls.report = json.loads(out.stdout.strip().splitlines()[-1]) if out.stdout.strip() else {"screens": 0, "problems": [{"kind": "no report", "text": out.stderr[-300:]}]}

    @classmethod
    def tearDownClass(cls):
        cls.server.control_context.stop.set()
        cls.server.shutdown()
        cls.server.server_close()
        cls.store.close()
        cls.temp.cleanup()

    def test_every_screen_was_opened(self):
        self.assertGreaterEqual(self.report["screens"], 2 * (3 * 4 + 3 * 9) - 6, self.report["screens"])

    def test_nothing_is_wrong_on_any_of_them(self):
        self.assertEqual(self.report["problems"], [])


if __name__ == "__main__":
    unittest.main()
