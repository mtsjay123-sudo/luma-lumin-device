"""Someone else on the Wi-Fi can't read anything or talk as the owner.

The lamp answers phones on the home network. Every route its web server knows is asked for here by a phone that was
never paired: with no cookie, with a made-up phone cookie and with a made-up owner cookie, as a read and as a write.
Nothing private may come back, and nothing may be accepted. The routes are read out of the server's own source, so a
new route is swept the day it's added.
"""
from __future__ import annotations

import http.cookiejar
import json
import re
import ssl
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from luma.agent.runtime import Agent
from luma.control.pairing import ensure_local_certificate
from luma.control.server import make_server
from luma.memory.store import Store

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ("Zelphine", "bloodwork")           # words only this home's memories hold
OPEN = {"/api/session"}                        # says whether this phone is paired, and nothing else
REFUSED = {400, 401, 403, 404, 405}


def routes():
    source = "".join(path.read_text() for path in sorted((ROOT / "src" / "luma" / "control").glob("*.py")))
    return sorted(set(re.findall(r"""['"](/api/[A-Za-z0-9_/\-]+)['"]""", source)))


class AStrangerOnTheWifi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        path = Path(cls.temp.name)
        cls.store = Store(path / "state.db", path / "key")
        cls.agent = Agent(store=cls.store, use_model=False)
        cls.agent.chat("my sister's name is Zelphine")
        cls.agent.chat("my doctor said my bloodwork is off, keep that private")
        cls.owner = make_server(cls.agent, 0)
        cls.ctx = cls.owner.control_context
        cls.phone = make_server(cls.agent, 0, context=cls.ctx, phone_host="127.0.0.1")
        cert, key = ensure_local_certificate(path / "tls", "192.168.10.10")
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        cls.phone.socket = tls.wrap_socket(cls.phone.socket, server_side=True)
        cls.trust = ssl.create_default_context(cafile=str(cert))
        for server in (cls.owner, cls.phone):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        cls.base = f"https://127.0.0.1:{cls.phone.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.ctx.stop.set()
        for server in (cls.owner, cls.phone):
            server.shutdown()
            server.server_close()
        cls.store.close()
        cls.temp.cleanup()

    def ask(self, path, data=None, cookie=None, host=None, opener=None):
        headers = {"Origin": self.base, "Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        if host:
            headers["Host"] = host
        request = urllib.request.Request(self.base + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        opener = opener or urllib.request.build_opener(urllib.request.HTTPSHandler(context=self.trust))
        try:
            with opener.open(request, timeout=15) as reply:
                return reply.status, reply.read(8000).decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            return error.code, error.read(4000).decode("utf-8", "replace")

    def test_every_route_refuses_a_phone_that_was_never_paired(self):
        found = routes()
        self.assertGreater(len(found), 100, "the sweep found the server's routes")
        wrong = []
        for path in found:
            for data in (None, {}):
                for cookie in (None, "luma_phone=made-up", "luma_owner=made-up"):
                    status, body = self.ask(path, data, cookie)
                    leaked = [word for word in PRIVATE if word in body]
                    if leaked or (status not in REFUSED and path not in OPEN):
                        wrong.append((path, "write" if data is not None else "read", cookie, status, leaked))
        self.assertEqual(wrong, [])

    def test_the_one_open_route_says_only_whether_this_phone_is_paired(self):
        status, body = self.ask("/api/session")
        self.assertEqual(status, 200)
        said = json.loads(body)
        self.assertEqual(said.get("paired"), False)
        self.assertLessEqual(set(said), {"viewer", "paired", "build", "pid"})

    def test_a_page_on_another_site_cant_reach_it_by_its_own_name(self):
        for path in ("/api/session", "/api/today", "/api/chat"):
            status, body = self.ask(path, host="evil.example")
            self.assertEqual(status, 403, path)
            self.assertFalse([word for word in PRIVATE if word in body])

    def test_a_paired_phone_is_let_in_so_the_sweep_is_asking_a_live_server(self):
        client = urllib.request.build_opener(urllib.request.HTTPSHandler(context=self.trust), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        invite = self.ctx.pairing.create_invite()
        status, _ = self.ask("/api/phone/pair", {"token": invite["token"], "name": "Their own phone"}, opener=client)
        self.assertEqual(status, 200)
        status, body = self.ask("/api/today", opener=client)
        self.assertEqual(status, 200)
        self.assertIn("memory", json.loads(body))


if __name__ == "__main__":
    unittest.main()
