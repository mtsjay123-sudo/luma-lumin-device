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


class LinkBase(unittest.TestCase):
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


class LinkTests(LinkBase):
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


class LinkWorkTests(LinkBase):
    """A paired laptop's terminal runs projects on the device and takes the package home."""

    def test_the_laptop_terminal_runs_a_project_on_the_device(self):
        import os as _os
        import zipfile
        import work_fakes
        from test_work_terminal import scripted_planner
        from luma.work import terminal
        self.device.planner = scripted_planner
        _os.environ["LUMA_WORK_NO_BROWSER"] = "1"
        self.pair()
        here = _os.getcwd()
        _os.chdir(self.temp.name)
        try:
            with mock.patch("luma.config.STATE_DB_PATH", self.laptop_store.db_path), \
                 mock.patch("luma.config.STATE_KEY_PATH", Path(self.temp.name) / "laptop" / "k"), \
                 mock.patch.object(terminal, "say"):
                remote = terminal.device()
                self.assertIn(self.device.link_host.name(), remote.label)
                run = remote.work("make a platformer game and a 3D printable phone stand")
        finally:
            _os.chdir(here)
            _os.environ.pop("LUMA_WORK_NO_BROWSER", None)
        self.assertEqual(run["state"], "done", run)
        downloaded = list(Path(self.temp.name).glob("*.zip"))
        self.assertEqual(len(downloaded), 1)
        self.assertIn("game/taco-dash/index.html", zipfile.ZipFile(downloaded[0]).namelist())

    def test_an_unpaired_computer_gets_nothing(self):
        import json as _json
        with self.assertRaises(luma_link.LinkError):
            luma_link.pinned_request("127.0.0.1", self.port, self.device.link_host.fingerprint or "x", "GET", "/link/work/projects", token="not-a-token")


class ComputerBrainTests(LinkBase):
    """The device thinks with the paired computer's brain: a $250 to $400 board's own takes 7 s or more to start talking."""

    def tearDown(self):
        from luma.llm import brain
        brain.use_computer(None)
        super().tearDown()

    def test_the_device_thinks_on_the_paired_computer(self):
        from luma.llm import brain, inference
        self.pair()
        brain.init(self.device_store)
        asked = []

        def laptop_brain(messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None):
            asked.append((threading.current_thread().name, messages[-1]["content"], mode))
            return {"type": "reply", "text": "Pasta tonight, easy and quick."}

        def one_round():
            job = self.laptop.link.call("GET", "/link/hands/next", timeout=40).get("job")
            self.laptop.link.call("POST", "/link/hands/done", {"id": job["id"], "result": self.laptop.link._do(job)})

        with mock.patch.object(inference, "plan", side_effect=laptop_brain):
            worker = threading.Thread(target=one_round, daemon=True, name="laptop-hands")
            worker.start()
            for _ in range(60):
                if self.device.link_host.connected(): break
                time.sleep(0.05)
            self.assertTrue(brain.computer_on(), "the link turned it on for the device")
            out = brain.plan([{"role": "user", "content": "what should i cook tonight"}], [], {}, "friend")
            worker.join(10)
        self.assertEqual(out["text"], "Pasta tonight, easy and quick.")
        self.assertEqual(asked, [("laptop-hands", "what should i cook tonight", "friend")], "thought out on the computer, once")
        self.assertEqual(self.device_store.setting("hands_log") or [], [], "not in what the phone shows Luma asked the computer to do")
        self.assertEqual(self.laptop.link.computer.log(), [], "nor in the computer's own log: it touched nothing there")


class ComputerBrainUnitTests(unittest.TestCase):
    class Host:
        def __init__(self, answer):
            self.answer, self.sent = answer, []

        def connected(self):
            return True

        def send(self, kind, wait=0, cancel=None, log=True, **args):
            self.sent.append((kind, log, args))
            return self.answer

    def setUp(self):
        from luma.llm import brain
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        brain.init(self.store)

    def tearDown(self):
        from luma.llm import brain
        brain.use_computer(None)
        self.store.close()
        self.temp.cleanup()

    def test_an_away_computer_hands_the_turn_to_the_next_brain(self):
        from luma.llm import brain, inference
        local = {"type": "reply", "text": "From the device's own brain."}
        for answer in (None, {"error": "Luma is paused on this computer. Resume it there to keep going."}, {"proposal": "nonsense"}):
            brain.use_computer(self.Host(answer))
            with mock.patch.object(inference, "plan", return_value=local):
                self.assertEqual(brain.plan([{"role": "user", "content": "hi"}], [], {}, "friend"), local)
            self.assertIn("another one did", self.store.setting("brain_computer_error"))

    def test_a_tool_from_the_computer_comes_back_for_the_device_to_run(self):
        from luma.llm import brain, inference
        tool = {"type": "tool", "name": "reminder.create", "arguments": {"text": "call mom", "when": "5pm"}}
        host = self.Host({"proposal": tool})
        brain.use_computer(host)
        with mock.patch.object(inference, "plan", side_effect=AssertionError("the device's own brain isn't needed")):
            self.assertEqual(brain.plan([{"role": "user", "content": "remind me at 5 to call mom"}], [], {"reminder.create": {}}, "kids"), tool)
        kind, logged, args = host.sent[0]
        self.assertEqual((kind, logged, args["mode"]), ("brain.plan", False, "kids"), "kids mode goes along, and it isn't logged as hands")
        host.answer = {"text": "Find the cheapest AirPods."}
        self.assertEqual(brain.rewrite("findd cheapest airpods"), "Find the cheapest AirPods.", "the quick rewrite too")

    def test_the_owner_can_keep_thinking_on_the_device(self):
        from luma.llm import brain, inference
        host = self.Host({"proposal": {"type": "reply", "text": "From the computer."}})
        brain.use_computer(host)
        self.store.set_setting("brain_use_computer", False)
        with mock.patch.object(inference, "plan", return_value={"type": "reply", "text": "Here."}):
            self.assertEqual(brain.plan([{"role": "user", "content": "hi"}], [], {}, "friend")["text"], "Here.")
        self.assertEqual(host.sent, [])

    def test_a_board_thinking_on_its_computer_isnt_slow(self):
        from luma.llm import brain
        with mock.patch.dict("os.environ", {"LUMA_DEVICE_TIER": "budget"}):
            self.assertTrue(brain.slow_here())
            brain.use_computer(self.Host(None))
            self.assertFalse(brain.slow_here(), "think first and a second look come back: the computer's brain is fast")

    def test_the_computer_lends_its_brain_but_never_passes_the_turn_on(self):
        from luma.llm import brain
        agent = Agent(store=self.store, use_model=False)
        seen = []
        with mock.patch.object(brain, "plan", side_effect=lambda *a, **k: seen.append(k) or {"type": "reply", "text": "ok"}):
            out = agent.link._do({"kind": "brain.plan", "messages": [{"role": "user", "content": "hi"}], "memories": [], "tools": {}, "mode": "friend"})
            self.assertEqual(out, {"proposal": {"type": "reply", "text": "ok"}})
            self.assertIs(seen[0]["use_computer_brain"], False)
            self.store.set_setting("lend_brain", False)
            self.assertIn("isn't lending", agent.link._do({"kind": "brain.plan", "messages": []})["error"])
            self.store.set_setting("lend_brain", True)
            agent.link.computer._save(paused=True)
            self.assertIn("paused", agent.link._do({"kind": "brain.plan", "messages": []})["error"])

    def test_a_computer_that_just_went_to_sleep_isnt_asked(self):
        from luma.llm import brain
        agent = Agent(store=self.store, use_model=False)
        host = luma_link.LinkHost(agent)
        brain.use_computer(host)
        host.hands_seen = agent.clock() - 30
        self.assertTrue(host.connected(), "its hands still count for a minute")
        self.assertFalse(brain.computer_on(), "but a turn won't wait 20 seconds on it")
        host.hands_seen = agent.clock()
        self.assertTrue(brain.computer_on())

    def test_waiting_on_the_computer_stops_when_they_interrupt(self):
        agent = Agent(store=self.store, use_model=False)
        host = luma_link.LinkHost(agent)
        stop = threading.Event()
        threading.Timer(0.3, stop.set).start()
        began = time.monotonic()
        self.assertIsNone(host.send("brain.plan", wait=10, cancel=stop, log=False, messages=[]))
        self.assertLess(time.monotonic() - began, 2)
        self.assertEqual(self.store.setting("hands_log") or [], [])
