"""Luma for Chrome: the extension pairs once with a code, then Luma opens tabs, plays music in the back and reads the page."""
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from luma.agent.runtime import Agent
from luma.control.server import ROOT, make_server
from luma.integrations.chrome_bridge import ChromeBridge, install
from luma.memory.store import Store

EXT = "chrome-extension://abcdefghijklmnopabcdefghijklmnop"


class ChromeBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name)
        self.store = Store(path / "state.db", path / "key")
        self.now = 1000.0
        self.bridge = ChromeBridge(self.store, clock=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_code_pairs_once_and_token_is_checked(self):
        code = self.bridge.code()
        self.assertEqual(len(code), 6)
        with self.assertRaises(ValueError):
            self.bridge.pair("WRONG1")
        token = self.bridge.pair(code.lower())
        self.assertTrue(self.bridge.valid(token))
        self.assertFalse(self.bridge.valid("nope"))
        self.assertNotEqual(self.bridge.code(), code)  # one use
        with self.assertRaises(ValueError):
            self.bridge.pair(code)
        self.bridge.unpair()
        self.assertFalse(self.bridge.valid(token))

    def test_results_come_back_to_whoever_asked(self):
        def extension():
            command = self.bridge.next(timeout=2)
            self.bridge.done(command["id"], {"title": "Lofi", "text": "beats to study to"})
        threading.Thread(target=extension, daemon=True).start()
        got = self.bridge.send("read", wait=3)
        self.assertEqual(got["title"], "Lofi")

    def test_nothing_old_runs_by_surprise(self):
        self.bridge.send("open", url="https://example.com/")
        self.now += 120
        self.assertIsNone(self.bridge.next(timeout=0.2))

    def test_install_points_the_extension_at_this_luma(self):
        folder = install(ROOT / "chrome", 9123, Path(self.temp.name) / "ext")
        manifest = json.loads((folder / "manifest.json").read_text())
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertIn("127.0.0.1:9123", (folder / "background.js").read_text())
        self.assertIn("127.0.0.1:9123", (folder / "popup.js").read_text())
        self.assertNotIn("8095", (folder / "background.js").read_text())


class ChromeServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name)
        self.store = Store(path / "state.db", path / "key")
        self.agent = Agent(store=self.store, use_model=False)
        self.server = make_server(self.agent, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.control_context.stop.set()
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.temp.cleanup()

    def call(self, path, data=None, origin=EXT):
        headers = {"Content-Type": "application/json"}
        if origin: headers["Origin"] = origin
        request = urllib.request.Request(self.base + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_web_pages_cannot_pair(self):
        status, body = self.call("/api/ext/pair", {"code": self.agent.chrome.code()}, origin="https://evil.example")
        self.assertEqual(status, 403)
        self.assertNotIn("token", body)

    def test_pair_then_take_a_step_and_answer_it(self):
        status, body = self.call("/api/ext/pair", {"code": "XXXXXX"})
        self.assertEqual(status, 403)
        status, body = self.call("/api/ext/pair", {"code": self.agent.chrome.code()})
        self.assertEqual(status, 200)
        token = body["token"]
        self.assertEqual(self.call("/api/ext/next?token=bad")[0], 403)
        answer = {}
        threading.Thread(target=lambda: answer.update(self.agent.chrome.send("tabs", wait=10) or {}), daemon=True).start()
        status, body = self.call(f"/api/ext/next?token={token}")
        self.assertEqual(body["command"]["kind"], "tabs")
        self.assertTrue(self.agent.chrome.connected())
        status, _ = self.call(f"/api/ext/done?token={token}", {"id": body["command"]["id"], "result": {"tabs": [{"title": "YouTube"}]}})
        self.assertEqual(status, 200)
        for _ in range(50):
            if answer: break
            time.sleep(0.05)
        self.assertEqual(answer["tabs"][0]["title"], "YouTube")


class LumaUsesChromeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name)
        self.store = Store(path / "state.db", path / "key")
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def online(self):
        self.agent.chrome.last_seen = self.agent.clock()

    def queued(self):
        return self.agent.chrome.commands.get_nowait()

    def test_music_plays_in_a_chrome_tab_in_the_back(self):
        self.online()
        reply = self.agent.chat("play me some drake")
        self.assertEqual(reply.get("chrome"), "play")
        self.assertNotIn("open_url", reply)
        self.assertIn("Chrome", reply["text"])
        for _ in range(40):
            if not self.agent.chrome.commands.empty(): break
            time.sleep(0.05)
        self.assertEqual(self.queued()["query"], "drake")

    def test_remembers_whats_playing_and_says_when_it_couldnt(self):
        self.online()

        def extension(result):
            command = self.agent.chrome.next(timeout=3)
            self.agent.chrome.done(command["id"], result)
        worker = threading.Thread(target=extension, args=({"playing": "Lofi Girl - beats to relax"},), daemon=True)
        worker.start()
        self.agent.chat("play some lofi")
        worker.join(3)
        for _ in range(40):
            if self.agent.now_playing: break
            time.sleep(0.05)
        self.assertIn("Lofi Girl", self.agent.chat("what's playing?")["text"])
        worker = threading.Thread(target=extension, args=({"error": "YouTube didn't load."},), daemon=True)
        worker.start()
        self.agent.chat("play some jazz")
        worker.join(3)
        for _ in range(40):
            if self.agent.feed.list(5): break
            time.sleep(0.05)
        self.assertIn("didn't start", self.agent.feed.list(5)[0]["title"])

    def test_music_without_chrome_still_plays(self):
        reply = self.agent.chat("play some lofi")
        self.assertIn("music.youtube.com", reply["open_url"])

    def test_open_youtube_and_search_google_in_chrome(self):
        self.online()
        reply = self.agent.chat("open youtube")
        self.assertEqual(reply["text"], "Opened YouTube in Chrome.")
        self.assertEqual(self.queued()["url"], "https://www.youtube.com/")
        self.agent.chat("search pasta recipes on google")
        self.assertIn("google.com/search?q=pasta+recipes", self.queued()["url"])
        self.agent.chat("go to nytimes.com")
        self.assertEqual(self.queued()["url"], "https://nytimes.com")

    def test_asks_to_add_the_extension_when_its_not_there(self):
        reply = self.agent.chat("open youtube in chrome")
        self.assertEqual(reply.get("open"), "apps")
        self.assertIn("Luma for Chrome", reply["text"])

    def test_reads_the_page_thats_open(self):
        self.online()

        def extension():
            command = self.agent.chrome.next(timeout=3)
            self.agent.chrome.done(command["id"], {"title": "Pasta Carbonara", "url": "https://example.com/carbonara", "text": "Eggs, pecorino, guanciale and black pepper."})
        threading.Thread(target=extension, daemon=True).start()
        reply = self.agent.chat("what's on this page?")
        self.assertIn("Pasta Carbonara", reply["text"])
        self.assertIn("guanciale", reply["text"])

    def test_ordinary_open_requests_are_left_alone(self):
        self.online()
        self.agent.chat("open the door")
        self.assertTrue(self.agent.chrome.commands.empty())

    def test_home_shows_the_chrome_card_state(self):
        from luma.control.server import home_payload
        chrome = home_payload(self.agent)["connections"]["chrome"]
        self.assertEqual(set(chrome), {"paired", "connected", "code"})


if __name__ == "__main__":
    unittest.main()
