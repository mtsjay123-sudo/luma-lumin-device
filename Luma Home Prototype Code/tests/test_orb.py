"""Luma's liquid orb: the one drawing of Luma that the talk screen, the first slides, the small avatars and the logo share.

The file is src/luma/control/web/orb.js. These tests hold it to what it promises: both apps get it and load it
before their own code, it never loads or sends anything, it knows every mood the apps ask for, the logo is a picture
of it, and (in a real browser, when there is one) it really draws, pours from mood to mood, cleans up after itself,
shares one drawing surface between the small ones, and holds still for someone who asked for less motion.
"""
import http.cookiejar
import json
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from luma.agent.runtime import Agent
from luma.control.server import ROOT, make_server
from luma.memory.store import Store

HERE = Path(__file__).resolve().parent
ORB = ROOT / "orb.js"
CHECK = HERE / "orb_check.cjs"
MOODS = ["idle", "listening", "waiting", "thinking", "speaking"]


def browser():
    """Whether node can drive a browser here (Playwright with Chromium). Without one, the browser tests skip."""
    node = shutil.which("node")
    if not node:
        return False
    try:
        return subprocess.run([node, "-e", "require.resolve('playwright')"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class Served(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name)
        self.store = Store(path / "state.db", path / "key")
        self.agent = Agent(store=self.store, use_model=False)
        self.server = make_server(self.agent, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def tearDown(self):
        self.server.control_context.stop.set()
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.temp.cleanup()

    def get(self, path):
        return self.client.open(urllib.request.Request(self.base + path))

    def test_both_apps_get_the_orb_and_load_it_before_their_own_code(self):
        with self.get("/orb.js") as r:
            self.assertEqual(r.status, 200)
            self.assertIn("javascript", r.headers["Content-Type"])
            self.assertEqual(r.read(), ORB.read_bytes())
        for page, app in (("/desktop/", "/desktop/desktop.js"), ("/phone/", "/phone/phone.js")):
            with self.get(page) as r:
                html = r.read().decode()
            self.assertIn('<script src="/orb.js"></script>', html, page)
            self.assertLess(html.index('src="/orb.js"'), html.index(f'src="{app}"'), page)

    def test_the_pages_have_a_place_for_it(self):
        with self.get("/desktop/") as r:
            desktop = r.read().decode()
        self.assertIn('id="ts-orb"', desktop)      # the talk screen
        self.assertIn('id="su-orb"', desktop)      # the sign-up slides
        self.assertIn('class="dc-orb"', desktop)   # the chat bar that follows you to other pages
        with self.get("/phone/phone.js") as r:
            phone = r.read().decode()
        self.assertIn("t-luma", phone)             # the first slide of the tour
        self.assertIn("t-orb", phone)              # and what's shown if a phone can't draw it

    def test_the_logo_is_a_picture_of_the_orb(self):
        with self.get("/desktop/logo") as r:
            self.assertEqual(r.headers["Content-Type"], "image/png")
            logo = r.read()
        self.assertEqual(logo, (ROOT / "desktop" / "brand" / "logo.png").read_bytes())
        self.assertEqual(logo[:8], b"\x89PNG\r\n\x1a\n")
        self.assertLess(len(logo), 200_000)        # a logo, not a photograph
        with self.get("/phone/icon.png") as r:
            self.assertEqual(r.headers["Content-Type"], "image/png")
            self.assertEqual(r.read()[:8], b"\x89PNG\r\n\x1a\n")
        with self.get("/phone/manifest.webmanifest") as r:
            manifest = json.load(r)
        self.assertEqual([icon["src"] for icon in manifest["icons"]], ["/phone/icon.png"])
        with self.get("/phone/") as r:
            self.assertIn('<link rel="apple-touch-icon" href="/phone/icon.png" />', r.read().decode())

    def test_a_phone_on_the_home_network_gets_it_too(self):
        # The orb is part of the phone app, so it's served like the phone app's own files: no sign-in needed to
        # fetch the drawing code, and nothing in it is private.
        with urllib.request.urlopen(self.base + "/orb.js") as r:
            self.assertEqual(r.status, 200)
            self.assertIsNone(r.headers.get("Set-Cookie"))

    @unittest.skipUnless(browser(), "no browser to open it in (node with Playwright and Chromium)")
    def test_in_a_real_browser(self):
        done = subprocess.run(["node", str(CHECK), self.base], capture_output=True, text=True, timeout=240)
        self.assertEqual(done.returncode, 0, done.stdout[-600:] + done.stderr[-600:])
        seen = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertEqual(seen["errors"], [])
        self.assertEqual(seen["moods"], MOODS)
        self.assertEqual(seen["asked"], [], "the orb asked the network for something")

        # It really draws: the shader works, the ball is there, and its box's corners are empty.
        self.assertTrue(seen["liquid"] and seen["bigLiquid"], "the shader didn't run; only the plain orb drew")
        self.assertGreater(seen["big"]["lit"], 0.2)
        self.assertLess(seen["big"]["corner"], 8)

        # Each mood looks like itself, and no two look the same.
        looks = seen["looks"]
        self.assertEqual(len({look["print"] for look in looks.values()}), len(MOODS))
        warm = lambda look: look["tone"][0] - look["tone"][2]
        self.assertLess(looks["listening"]["middle"], 30, "listening should open its middle into a ring")
        self.assertLess(seen["ring"]["middle"], 30)
        self.assertLess(warm(looks["listening"]), -20)      # cool while it listens
        self.assertGreater(warm(looks["speaking"]), 10)     # warm while it speaks
        self.assertGreater(warm(looks["waiting"]), 10)
        self.assertGreater(looks["thinking"]["tone"][2], looks["thinking"]["tone"][1] + 20)   # violet while it thinks
        self.assertGreater(looks["speaking"]["lit"], looks["idle"]["lit"] + 0.05, "its voice should make it glow")

        # With no WebGL it still draws something.
        self.assertFalse(seen["plainLiquid"])
        self.assertGreater(seen["plain"]["lit"], 0.15)

        # The small ones and the stills share one drawing surface: with the big orb's own, that's two in all.
        self.assertEqual(seen["smallSurfaces"], 0)
        self.assertEqual(seen["surfaces"], 2)
        self.assertEqual(seen["surfacesAfterStills"], 2)
        self.assertGreater(seen["small"]["lit"], 0.4)
        self.assertEqual(len(seen["stills"]), len(MOODS))
        self.assertTrue(all(still.startswith("data:image/png;base64,") for still in seen["stills"]))
        self.assertEqual(len(set(seen["stills"])), len(MOODS))

        # It cleans up after itself, and it waits for a place that isn't on the page yet.
        self.assertEqual(seen["closed"], {"gone": True, "canvases": 0})
        self.assertTrue(seen["removed"])
        self.assertFalse(seen["late"]["gone"])
        self.assertGreater(seen["late"]["lit"], 0.4)

        # For someone who asked for less motion it holds still, and still changes with the mood.
        self.assertGreater(seen["calm"]["lit"], 0.2)
        self.assertTrue(seen["calm"]["held"], "it kept moving for someone who asked for less motion")
        self.assertTrue(seen["calm"]["changed"])

        # In the real apps: it's on the first slides, it leaves with the tour, and the pages' own rules refuse nothing.
        self.assertEqual(seen["desktop"]["orb"], True)
        self.assertEqual(seen["desktop"]["signup"], 1)
        self.assertTrue(seen["desktop"]["talkPlace"])
        self.assertEqual(seen["desktop"]["logo"], "image/png")
        self.assertEqual(seen["desktop"]["refused"], [])
        self.assertEqual(seen["phone"], {"orb": True, "tour": 1, "afterTour": 0, "state": 1, "wide": False, "refused": []})


class TheFile(unittest.TestCase):
    def setUp(self):
        self.text = ORB.read_text()

    def test_it_never_loads_or_sends_anything(self):
        # Private by default: a drawing has no business with the network, storage, or where the person is.
        for word in ("fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon", "import(", "importScripts", "localStorage", "sessionStorage",
                     "indexedDB", "document.cookie", "navigator.", "eval(", "new Function", "http://", "https://", "<script", "innerHTML", ".src ="):
            self.assertNotIn(word, self.text, word)

    def test_it_knows_every_mood_the_apps_ask_for(self):
        block = self.text[self.text.index("const MOODS = {"):self.text.index("const NUMBERS")]
        self.assertEqual(re.findall(r"^    (\w+): \{", block, re.M), MOODS)
        desktop = (ROOT / "desktop" / "desktop.js").read_text()
        phone = (ROOT / "phone" / "phone.js").read_text()
        aura = desktop[desktop.index("const auraMood = "):]
        aura = aura[:aura.index("\n")]
        asked = set(re.findall(r'"(\w+)"', aura)) - {"speaking", "talk"} | {"speaking"}
        asked |= set(re.findall(r'"(\w+)"', desktop[desktop.index("const SU_MOODS = {"):desktop.index("function suOrb")])) - {"hello", "name", "birthday", "contact", "people", "world", "done"}
        asked |= set(re.findall(r'const round = \[([^\]]+)\]', phone)[0].replace('"', "").replace(" ", "").split(","))
        self.assertTrue(asked, "found no moods to check")
        self.assertLessEqual(asked, set(MOODS), asked - set(MOODS))

    def test_every_mood_has_every_number_and_color(self):
        block = self.text[self.text.index("const MOODS = {"):self.text.index("const NUMBERS")]
        numbers = re.findall(r'"(\w+)"', self.text[self.text.index("const NUMBERS = ["):self.text.index("const COLORS")])
        colors = re.findall(r'"(\w+)"', self.text[self.text.index("const COLORS = ["):self.text.index("const UNIFORMS")])
        self.assertEqual(numbers, ["flow", "turb", "swirl", "hollow", "bright", "iri"])
        self.assertEqual(colors, ["deep", "mid", "lite", "glint"])
        lines = [line for line in block.splitlines() if re.match(r"    \w+: \{", line)]
        self.assertEqual(len(lines), len(MOODS))
        for line in lines:
            for key in numbers:
                self.assertRegex(line, rf"\b{key}: -?\d", line[:30])
            for key in colors:
                found = re.search(rf"\b{key}: \[([^\]]+)\]", line)
                self.assertIsNotNone(found, line[:30] + " " + key)
                parts = [float(v) for v in found.group(1).split(",")]
                self.assertEqual(len(parts), 3)
                self.assertTrue(all(0 <= v <= 1 for v in parts), parts)

    def test_the_shader_gets_every_value_it_asks_for(self):
        shader = self.text[self.text.index("const FRAGMENT = `"):self.text.index("}`;")]
        wanted = set()
        for line in re.findall(r"^uniform \w+ ([^;]+);", shader, re.M):
            wanted |= {name.strip() for name in line.split(",")}
        given = set(re.findall(r'"(u[A-Z]\w*)"', self.text[self.text.index("const UNIFORMS = ["):self.text.index("const VERTEX")]))
        self.assertEqual(wanted, given)
        for name in given:
            self.assertIn(f"where.{name}", self.text, name)

    def test_the_apps_fall_back_when_it_is_missing(self):
        # A page that didn't get orb.js (or can't draw it) must still work: every use is behind a check.
        desktop = (ROOT / "desktop" / "desktop.js").read_text()
        phone = (ROOT / "phone" / "phone.js").read_text()
        for text, name in ((desktop, "desktop"), (phone, "phone")):
            for at in (m.start() for m in re.finditer(r"LumaOrb\.(mount|still)\(", text)):
                before = text[max(0, at - 700):at]
                self.assertRegex(before, r"window\.LumaOrb", f"{name}: a use of the orb with no check that it's there")
        self.assertIn('o.append(el("i"), el("i"), el("i"))', desktop)      # the soft blobs it replaces are still there
        self.assertIn('<div class="t-orb">', phone)                         # and the phone tour's warm ball

    def test_the_old_pictures_are_still_there_to_fall_back_on(self):
        self.assertTrue((ROOT / "desktop" / "brand" / "logo.svg").is_file())
        self.assertTrue((ROOT / "desktop" / "mascot.svg").is_file())


if __name__ == "__main__":
    unittest.main()
