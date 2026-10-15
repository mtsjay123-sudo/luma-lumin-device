"""Luma Link: the device and the laptop find each other on Wi-Fi, pair once with a code, and then work as one Luma.
The laptop's window opens the device's Luma over pinned HTTPS, memories sync both ways, and the laptop is the
device's hands for things only it can do."""
import http.cookiejar
import json
import ssl
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from luma.agent.runtime import Agent
from luma.control import link as luma_link
from luma.control.server import make_server, start_link, stop_link
from luma.memory.store import Store


def free_udp_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / "device").mkdir(); (root / "laptop").mkdir()
        self.device_store = Store(root / "device" / "s.db", root / "device" / "k")
        self.laptop_store = Store(root / "laptop" / "s.db", root / "laptop" / "k")
        self.device = Agent(store=self.device_store, use_model=False)
        self.laptop = Agent(store=self.laptop_store, use_model=False)
        self.device_server = make_server(self.device, 0)
        self.ctx = self.device_server.control_context
        self.udp = free_udp_port()
        self.status = start_link(self.ctx, bind="127.0.0.1", port=0, discovery_port=self.udp)
        self.port = self.device.link_host.port

    def tearDown(self):
        self.laptop.link.stop.set()
        stop_link(self.ctx)
        self.ctx.stop.set()
        self.device_server.server_close()
        self.device_store.close(); self.laptop_store.close()
        self.temp.cleanup()

    def pair(self):
        found = self.laptop.link.discover(timeout=1.0, targets=["127.0.0.1"], port=self.udp)
        self.assertEqual(len(found), 1)
        d = found[0]
        with mock.patch.object(self.laptop.link, "start"):
            return self.laptop.link.pair(d["host"], d["port"], d["fingerprint"], self.device.link_host.code())

    def test_find_and_pair_with_the_code_it_shows(self):
        found = self.laptop.link.discover(timeout=1.0, targets=["127.0.0.1"], port=self.udp)
        d = found[0]
        self.assertEqual(d["port"], self.port)
        with self.assertRaises(luma_link.LinkError):
            self.laptop.link.pair(d["host"], d["port"], d["fingerprint"], "000000" if self.device.link_host.code() != "000000" else "111111")
        with mock.patch.object(self.laptop.link, "start"):
            device = self.laptop.link.pair(d["host"], d["port"], d["fingerprint"], self.device.link_host.code())
        self.assertEqual(device["name"], self.device.link_host.name())
        self.assertNotIn("token_b64", device)
        self.assertTrue(self.laptop.link.online())
        self.assertEqual(len(self.device.link_host.peers()), 1)

    def test_a_different_device_is_refused(self):
        self.pair()
        cfg = dict(self.laptop_store.setting("link_device"))
        cfg["fingerprint"] = "00" * 32
        self.laptop_store.set_setting("link_device", cfg)
        with self.assertRaisesRegex(luma_link.LinkError, "isn't the Luma you paired with"):
            self.laptop.link.call("GET", "/link/ping")

    def test_memories_sync_both_ways(self):
        self.pair()
        self.laptop.chat("I left my keys on the counter")
        self.device.chat("I hate cilantro")
        self.laptop.link.sync_memories()
        laptop = [m["text"] for m in self.laptop_store.all("memory", 50)]
        device = [m["text"] for m in self.device_store.all("memory", 50)]
        self.assertIn("You hate cilantro", laptop)
        self.assertIn("Your keys are on the counter", device)

    def test_the_laptop_window_opens_the_devices_luma(self):
        self.pair()
        entry = self.laptop.link.enter()
        self.assertTrue(entry["fingerprint"].startswith("sha256/"))
        jar = http.cookiejar.CookieJar()
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); tls.check_hostname = False; tls.verify_mode = ssl.CERT_NONE  # the test plays the pinned window
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=tls), urllib.request.HTTPCookieProcessor(jar))
        page = opener.open(entry["url"]).read().decode()
        self.assertIn("<title>", page)
        origin = entry["origin"]
        req = urllib.request.Request(origin + "/api/chat", data=json.dumps({"text": "I left my wallet in the car"}).encode(),
                                     headers={"Origin": origin, "Content-Type": "application/json"})
        reply = json.loads(opener.open(req).read())
        self.assertIn("wallet is in the car", reply["text"])
        self.assertIn("Your wallet is in the car", [m["text"] for m in self.device_store.all("memory", 10)])
        with self.assertRaises(urllib.error.HTTPError) as used:
            opener.open(entry["url"])  # a ticket works once
        self.assertEqual(used.exception.code, 403)
        bad = urllib.request.Request(origin + "/api/chat", data=b'{"text":"hi"}', headers={"Origin": "https://evil.example", "Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as blocked:
            opener.open(bad)
        self.assertEqual(blocked.exception.code, 403)

    def test_strangers_get_nothing(self):
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); tls.check_hostname = False; tls.verify_mode = ssl.CERT_NONE
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=tls))
        for path in ["/api/home", "/link/hands/next"]:
            with self.assertRaises(urllib.error.HTTPError) as no:
                opener.open(f"https://127.0.0.1:{self.port}{path}")
            self.assertIn(no.exception.code, {401, 403})

    def test_the_laptop_is_the_devices_hands(self):
        self.pair()
        done = []
        with mock.patch.object(self.laptop.link, "_do", side_effect=lambda job: done.append(job) or {"opened": job.get("url")}):
            def one_round():
                job = self.laptop.link.call("GET", "/link/hands/next", timeout=40).get("job")
                self.laptop.link.call("POST", "/link/hands/done", {"id": job["id"], "result": self.laptop.link._do(job)})
            worker = threading.Thread(target=one_round, daemon=True)
            worker.start()
            for _ in range(50):
                if self.device.link_host.connected(): break
                time.sleep(0.05)
            self.assertTrue(self.device._hands() is self.device.link_host)
            reply = self.device.chat("open youtube")
            worker.join(10)
        self.assertEqual(reply["text"], "Opened YouTube in Chrome.")
        self.assertEqual(done[0]["url"], "https://www.youtube.com/")


if __name__ == "__main__":
    unittest.main()
