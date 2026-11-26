"""Both apps, walked in a real browser at six sizes, light and dark (tests/app_walk.cjs). A Luma with a few days of
made-up life is served, and every screen is opened: nothing may error, fail to load, run off the screen, sit under the
floating ask bar at the end of a page, or be too small for a thumb; and the apps must say a few things right (one
memory count, a task's real days, no model's name where a customer reads, no passing remark as a memory card, and on
the phone how they've asked to be met, in their own words, each line forgettable).

Skipped where node can't drive a browser (the same rule as tests/test_orb.py)."""
import json
import os
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


GOOD = HERE / "data" / "app_walk_good.json"
CLOSE = 48                                         # squares of 1,024: two walks of a still screen differ by 11 at most
LIVE = ("sheet #chain-list", "sheet #deck")        # screens that show what was said


def apart(a, b):
    """How many of two pictures' squares differ."""
    return bin(int(a, 16) ^ int(b, 16)).count("1")


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
        cls.report = cls.walk()

    @classmethod
    def walk(cls):
        out = subprocess.run([shutil.which("node"), str(HERE / "app_walk.cjs"), f"http://127.0.0.1:{cls.server.server_port}"],
                             capture_output=True, text=True, timeout=900)
        return json.loads(out.stdout.strip().splitlines()[-1]) if out.stdout.strip() else {"screens": 0, "problems": [{"kind": "no report", "text": out.stderr[-300:]}]}

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

    def test_nothing_is_hard_to_use(self):
        """On every screen: each thing to press has a name a screen reader can say, on the phone it's big enough for a
        thumb (44 px each way), every picture has words, and words stand out from what's behind them (4.5 to 1; 3 to 1
        when large). Where a picture, a gradient or frosted glass is behind the words the check can't say and doesn't."""
        self.assertEqual(self.report.get("access"), [], self.report.get("access", [])[:10])

    def test_the_checks_can_see(self):
        """An empty list means nothing only if the checks can find something. On one screen the walk breaks things on
        purpose and each check has to notice. What the pictures don't see is written down too: the dock gone moves no
        square of a whole page's picture (the layout check is what guards the dock)."""
        sees = self.report["sees"]
        self.assertEqual(sees["access"], ["a picture with no words for it", "nothing to call it", "smaller than a thumb", "words too faint"])
        self.assertGreater(sees["looks"]["a panel gone"], 4 * CLOSE, sees)
        self.assertGreater(sees["looks"]["the stage gone"], 4 * CLOSE, sees)
        self.assertLessEqual(sees["back"], CLOSE, sees)

    def test_each_screen_looks_as_it_did(self):
        """Each screen's picture against the last one a person accepted (tests/data/app_walk_good.json): 1,024 squares,
        lighter or darker, and no more than CLOSE of them may have changed. A screen that shows what was said changes
        with every walk (Luma's own line, the time), so it's opened and checked for layout but its picture isn't
        compared. After a change to how a screen looks, on purpose: LUMA_APP_WALK_ACCEPT=1 walks twice and writes the
        file again; say so in the commit."""
        looks = self.report["looks"]
        if os.environ.get("LUMA_APP_WALK_ACCEPT") == "1":
            again = self.walk()["looks"]
            kept = {name: (look if look and again.get(name) and not any(live in name for live in LIVE) and apart(look, again[name]) <= CLOSE // 3 else None)
                    for name, look in sorted(looks.items())}
            GOOD.write_text(json.dumps({"browser": self.report["browser"], "looks": kept}, indent=0) + "\n")
            return
        good = json.loads(GOOD.read_text())
        if good["browser"] != self.report["browser"]:
            self.skipTest(f"the good pictures were taken in browser {good['browser']}, this is {self.report['browser']}: another browser draws letters a little differently")
        self.assertEqual(sorted(good["looks"]), sorted(looks), "the screens walked aren't the screens in the good file")
        moved = {name: apart(look, looks[name]) for name, look in good["looks"].items() if look and looks.get(name)}
        self.assertEqual({name: n for name, n in moved.items() if n > CLOSE}, {}, "these screens don't look as they did (squares changed, of 1,024)")
        self.assertGreaterEqual(len(moved), 60, len(moved))


if __name__ == "__main__":
    unittest.main()
