"""The window's own browser and Luma's browser share sign-ins, both ways, on this computer only.
And the Overview page's numbers: measured work time, never a guess."""
import functools
import http.server
import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path

from luma.agent import insights
from luma.agent.runtime import Agent
from luma.integrations.browser import BrowserSession, clean_cookie
from luma.memory.store import Store

HAS_BROWSER = importlib.util.find_spec("playwright") is not None
SIGNED_IN = {"name": "session", "value": "abc123", "domain": ".example.com", "path": "/", "expires": 2000000000, "httpOnly": True, "secure": True, "sameSite": "Lax"}


class CookieTests(unittest.TestCase):
    def test_only_real_public_cookies_pass(self):
        self.assertEqual(clean_cookie(SIGNED_IN)["domain"], ".example.com")
        for bad in [{**SIGNED_IN, "domain": "localhost"}, {**SIGNED_IN, "domain": "192.168.1.4"}, {**SIGNED_IN, "domain": "printer.local"},
                    {**SIGNED_IN, "domain": "exa mple.com"}, {**SIGNED_IN, "name": ""}, {**SIGNED_IN, "value": "x" * 5000},
                    {**SIGNED_IN, "path": "nope"}, "a cookie", None]:
            self.assertIsNone(clean_cookie(bad), bad)
        loose = clean_cookie({**SIGNED_IN, "sameSite": "None", "secure": False, "expires": "soon"})
        self.assertEqual((loose["sameSite"], loose["expires"]), ("Lax", -1))  # SameSite=None needs https; bad expiry means session

    def test_shared_before_the_browser_opens_are_kept_for_later(self):
        with tempfile.TemporaryDirectory() as temp:
            b = BrowserSession(Path(temp) / "p")
            self.assertEqual(b.add_cookies([SIGNED_IN, {"name": "x"}]), 1)
            self.assertEqual(b.cookies(), [])  # nothing is open yet, so nothing to share back
            self.assertEqual(len(b._pending_cookies), 1)
            with self.assertRaises(ValueError):
                b.cookies("file:///etc/passwd")


@unittest.skipUnless(HAS_BROWSER, "playwright not installed")
class RealBrowserCookieTests(unittest.TestCase):
    def test_sign_in_arrives_when_chromium_opens_and_comes_back_out(self):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(Path(__file__).parent / "fixtures" / "web"))
        handler.log_message = lambda *a: None
        site = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=site.serve_forever, daemon=True).start()
        temp = tempfile.TemporaryDirectory()
        b = BrowserSession(Path(temp.name) / "p", allow_local=True)
        try:
            b.add_cookies([SIGNED_IN])
            b.open(f"http://127.0.0.1:{site.server_port}/store-jsonld.html")
            names = [c["name"] for c in b.cookies("https://www.example.com/")]
            self.assertIn("session", names)
            b.add_cookies([{**SIGNED_IN, "name": "later"}])
            self.assertIn("later", [c["name"] for c in b.cookies("https://example.com/")])
        finally:
            b.close()
            site.shutdown()
            site.server_close()
            temp.cleanup()


class InsightsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.agent = Agent(store=self.store, use_model=False, now=lambda: 1791900000.0)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_chats_and_jobs_count_as_work(self):
        self.agent.chat("remind me in 20 minutes to stretch")
        self.agent.activity.start("compare", "Comparing AirPods prices")
        self.agent.activity.current["started"] -= 90
        self.agent.activity.finish("Found it")
        d = insights.overview(self.agent)
        self.assertEqual(d["counts"]["chats"], 1)
        self.assertEqual(d["counts"]["tasks"], 1)
        self.assertGreaterEqual(d["worked"]["total"], 90)
        self.assertEqual(len(d["week"]), 7)
        self.assertEqual(d["week"][-1]["label"], "Today")
        self.assertEqual(d["recent"][0]["title"], "Comparing AirPods prices")

    def test_say_time(self):
        self.assertEqual([insights.say_time(s) for s in (0, 42, 600, 3725)], ["0s", "42s", "10m", "1h 02m"])


if __name__ == "__main__":
    unittest.main()
