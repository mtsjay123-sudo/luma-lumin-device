"""Luma Desktop's page is served by the local runtime and signs the window in like the main controls."""
import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from luma.agent.runtime import Agent
from luma.control.server import ROOT, make_server
from luma.memory.store import Store


class DesktopPageTests(unittest.TestCase):
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

    def test_desktop_page_signs_in_and_can_talk(self):
        with self.get("/desktop/") as r:
            self.assertIn("luma_owner=", r.headers["Set-Cookie"])
            page = r.read().decode()
        self.assertIn('id="mascot"', page)
        for asset in ["/desktop/desktop.js", "/desktop/desktop.css"]:
            with self.get(asset) as r:
                self.assertEqual(r.status, 200)
        request = urllib.request.Request(self.base + "/api/chat", data=json.dumps({"text": "remind me in 20 minutes to stretch"}).encode(),
                                         headers={"Origin": self.base, "Content-Type": "application/json"})
        with self.client.open(request) as r:
            reply = json.load(r)
            self.assertIn("remind you", reply.get("text") or reply["summary"])

    def test_bare_path_redirects_and_logo_falls_back_to_the_mascot(self):
        with self.get("/desktop") as r:
            self.assertTrue(r.url.endswith("/desktop/"))
        custom = ROOT / "desktop" / "brand" / "logo.png"
        if not custom.exists():
            with self.get("/desktop/logo") as r:
                self.assertEqual(r.headers["Content-Type"], "image/svg+xml")

    def test_state_lists_decks_with_their_slide_outline(self):
        self.agent._create_deck({"title": "Walkies", "slides": [
            {"layout": "bullets", "title": "Problem", "bullets": ["Dogs wait all day", "Owners work late"]},
            {"layout": "big_number", "title": "Market", "number": "$4B", "caption": "US dog walking"},
            {"layout": "quote", "quote": "I'd pay for this tomorrow.", "attribution": "A tenant"},
        ]})
        self.get("/desktop/").close()
        with self.get("/api/state") as r:
            deck = json.load(r)["files"][0]
        self.assertEqual(deck["title"], "Walkies")
        self.assertEqual([s["layout"] for s in deck["outline"]], ["bullets", "big_number", "quote"])
        self.assertEqual(deck["outline"][1]["big"], "$4B")
        self.assertEqual(deck["outline"][2]["points"], ["— A tenant"])


if __name__ == "__main__":
    unittest.main()
