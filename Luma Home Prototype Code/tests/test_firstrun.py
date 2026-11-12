"""Setting a new Luma up from a phone (src/luma/hardware/firstrun.py): the lamp has no screen, so the phone is the screen.

The lamp opens its own setup network and says the code. The phone joins, a page opens, they pick the home Wi-Fi. Luma joins
it and says where to find it. There the same code pairs the phone with Luma's app. No real network here: a made-up Wi-Fi."""
import json
import threading
import unittest
import urllib.request

from luma.hardware import firstrun
from luma.hardware.wifi import WifiError


class FakeWifi:
    def __init__(self, ok=True, ip="192.168.1.40"):
        self.ok, self.ip, self.joins, self.setups = ok, ip, [], []

    def scan(self):
        return [{"ssid": "Home", "signal": 80, "secure": True}, {"ssid": "Cafe <Free>", "signal": 30, "secure": False}]

    def join(self, ssid, password=""):
        self.joins.append((ssid, password))
        if not self.ok:
            raise WifiError(f"That password didn't work for {ssid}. Check it and try again.")
        return {"connected": True, "ssid": ssid, "ip": self.ip}

    def start_setup(self, code=None):
        self.setups.append(code)
        return {"ssid": f"Luma Setup {code[-4:]}", "code": code}


def body(answer):
    return json.loads(answer[2])


class TheSetupPage(unittest.TestCase):
    def setUp(self):
        self.wifi, self.said, self.paired = FakeWifi(), [], []
        self.setup = firstrun.Setup(self.wifi, "48291537", say=self.said.append, pair=lambda ip: self.paired.append(ip) or f"https://{ip}:8096/#pair=li_x",
                                    later=lambda fn: fn())

    def post(self, path, data):
        return self.setup.handle("POST", path, json.dumps(data).encode())

    def test_any_page_a_phone_asks_for_leads_to_the_setup_page(self):
        """A phone that joins a Wi-Fi with no internet asks for a test page; anything but the answer it expects opens the sheet."""
        for path in ("/hotspot-detect.html", "/generate_204", "/anything"):
            status, headers, _ = self.setup.handle("GET", path, b"")
            self.assertEqual((status, headers["Location"]), (302, "/"), path)
        status, headers, page = self.setup.handle("GET", "/", b"")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        text = page.decode()
        self.assertIn("Pick your Wi-Fi", text)
        self.assertNotIn("http://", text.replace("http://www.w3.org", ""), "nothing is fetched from anywhere: the phone has no internet here")
        self.assertNotIn("https://", text)
        self.assertNotIn("48291537", text, "the code is said out loud, never shown")

    def test_it_lists_the_networks_around_the_lamp(self):
        got = body(self.setup.handle("GET", "/networks", b""))
        self.assertEqual([n["ssid"] for n in got["networks"]], ["Home", "Cafe <Free>"])
        self.assertEqual(got["state"], "setup")

    def test_the_password_goes_to_the_wifi_and_nowhere_else(self):
        answer = self.post("/join", {"ssid": "Home", "password": "correct horse"})
        self.assertEqual(answer[0], 200)
        self.assertEqual(self.wifi.joins, [("Home", "correct horse")])
        self.assertEqual(self.setup.state, "joined")
        self.assertNotIn("correct horse", json.dumps(self.setup.__dict__, default=str), "Luma keeps no copy")
        self.assertNotIn("correct horse", " ".join(self.said))
        self.assertIn("Home", self.said[-1])
        self.assertIn("192.168.1.40", self.said[-1], "it says where to find it")
        self.assertIn("same code", self.said[-1])

    def test_a_wrong_password_reopens_the_setup_network_with_the_same_code(self):
        self.wifi.ok = False
        self.post("/join", {"ssid": "Home", "password": "wrong password"})
        self.assertEqual(self.setup.state, "setup")
        self.assertEqual(self.wifi.setups, ["48291537"])
        self.assertIn("password didn't work", self.said[-1])
        self.assertIn("Luma Setup 1537", self.said[-1])
        self.assertIn("password didn't work", body(self.setup.handle("GET", "/networks", b""))["error"])

    def test_a_bad_request_is_refused_before_anything_is_tried(self):
        for data in ({"ssid": "", "password": "correct horse"}, {"ssid": "Home", "password": "short"}, {"ssid": "x" * 40}, []):
            self.assertEqual(self.post("/join", data)[0], 400, data)
        self.assertEqual(self.setup.handle("POST", "/join", b"not json")[0], 400)
        self.assertEqual(self.setup.handle("POST", "/join", b"x" * 5000)[0], 413)
        self.assertEqual(self.wifi.joins, [])

    def test_on_the_home_wifi_the_same_code_pairs_the_phone(self):
        self.post("/join", {"ssid": "Home", "password": "correct horse"})
        page = self.setup.handle("GET", "/", b"")[2].decode()
        self.assertIn("code Luma said", page)
        self.assertEqual(self.post("/join", {"ssid": "Other", "password": "correct horse"})[0], 409, "the Wi-Fi is set: this page can't change it")
        self.assertEqual(self.post("/pair", {"code": "00000000"})[0], 403)
        got = self.post("/pair", {"code": "4829 1537"})
        self.assertEqual(got[0], 200)
        self.assertEqual(body(got)["url"], "https://192.168.1.40:8096/#pair=li_x")
        self.assertEqual(self.paired, ["192.168.1.40"])
        self.assertEqual(self.post("/pair", {"code": "48291537"})[0], 410, "one phone this way; more from Luma's app")

    def test_five_wrong_codes_and_the_door_closes(self):
        self.post("/join", {"ssid": "Home", "password": "correct horse"})
        for _ in range(5):
            self.assertEqual(self.post("/pair", {"code": "11111111"})[0], 403)
        self.assertEqual(self.post("/pair", {"code": "48291537"})[0], 410, "even the right code, after five wrong ones")
        self.assertEqual(self.paired, [])

    def test_the_door_closes_by_itself_after_half_an_hour(self):
        now = [0.0]
        setup = firstrun.Setup(self.wifi, "48291537", pair=lambda ip: "u", later=lambda fn: fn(), clock=lambda: now[0])
        setup.handle("POST", "/join", json.dumps({"ssid": "Home", "password": "correct horse"}).encode())
        now[0] = 31 * 60
        self.assertEqual(setup.handle("POST", "/pair", json.dumps({"code": "48291537"}).encode())[0], 410)

    def test_nobody_pairs_before_the_wifi_is_set(self):
        self.assertEqual(self.post("/pair", {"code": "48291537"})[0], 409)


class OverTheAir(unittest.TestCase):
    def test_a_real_request_gets_the_page_and_nothing_is_logged(self):
        setup = firstrun.Setup(FakeWifi(), "48291537", later=lambda fn: fn())
        server = firstrun.serve(setup, bind="127.0.0.1", ports=(0,))
        try:
            port = server.server_address[1]
            threading.Thread(target=server.serve_forever, daemon=True).start()
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as page:
                self.assertIn("Pick your Wi-Fi", page.read().decode())
            request = urllib.request.Request(f"http://127.0.0.1:{port}/join", json.dumps({"ssid": "Home", "password": "correct horse"}).encode(),
                                             {"Content-Type": "application/json"})
            with urllib.request.urlopen(request) as answer:
                self.assertTrue(json.loads(answer.read())["ok"])
            self.assertEqual(setup.state, "joined")
        finally:
            server.shutdown()
            server.server_close()

    def test_first_run_says_it_to_a_phone_and_opens_the_page(self):
        class Offline(FakeWifi):
            def available(self): return True
            def status(self): return {"connected": False}
            def start_setup(self, code=None):
                self.setups.append(code)
                return {"ssid": "Luma Setup 1537", "code": "48291537"}
        said, served = [], []
        clock = iter(range(0, 1000, 10))
        setup = firstrun.run(Offline(), said.append, wait=30, clock=lambda: next(clock), sleep=lambda s: None, serve=served.append)
        self.assertIsInstance(setup, firstrun.Setup)
        self.assertEqual(served, [setup])
        self.assertIn("On your phone", said[0])
        self.assertIn("Luma Setup 1537", said[0])
        self.assertIn("4 8 2 9 1 5 3 7", said[0])
        self.assertNotIn("computer", said[0])

    def test_already_online_there_is_nothing_to_set_up(self):
        class Online(FakeWifi):
            def available(self): return True
            def status(self): return {"connected": True}
        self.assertIsNone(firstrun.run(Online(), None, wait=30, clock=lambda: 0, sleep=lambda s: None, serve=self.fail))


if __name__ == "__main__":
    unittest.main()
