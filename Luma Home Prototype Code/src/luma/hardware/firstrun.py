"""Setting a new Luma up from a phone. The lamp has no screen, so the phone is the screen.

1. Plugged in and not online, Luma opens its own setup network ("Luma Setup 1234") and says the code out loud.
2. The phone joins it. A page opens (this module serves it; any address the phone tries leads to it). They pick the home
   Wi-Fi and type its password. The password goes to NetworkManager and nowhere else: not kept, not logged.
3. Luma joins the home Wi-Fi and says where to find it. If the password was wrong it says so and opens the setup network again.
4. At that address, the same code pairs the phone with Luma's app. Five wrong codes, or half an hour, and the door closes;
   unplugging Luma and plugging it back in opens it again while no phone is paired.

Only on a Luma device (its image sets LUMA_WIFI_SETUP=1), never on someone's laptop. Nothing here calls out to the internet.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from luma.hardware import wifi as wifi_tools
from luma.hardware.wifi import WifiError

TRIES = 5              # wrong codes before the door closes
OPEN_FOR = 30 * 60     # seconds the door stays open once Luma is on the home Wi-Fi
LIMIT = 2048           # bytes in a request: a network's name and a password are small

STYLE = """<meta name="viewport" content="width=device-width,initial-scale=1"><style>
:root{color-scheme:light dark}body{margin:0;font:17px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;background:#f6f4ef;color:#1d1d1f}
main{max-width:26rem;margin:0 auto;padding:28px 20px 40px}h1{font-size:1.6rem;margin:0 0 6px}p{margin:0 0 16px;color:#55555a}
button,input{font:inherit;width:100%;box-sizing:border-box;border-radius:14px;padding:14px 16px;border:1px solid #d5d1c7;background:#fff;color:inherit}
button{text-align:left;margin:0 0 8px;cursor:pointer}button.go{background:#1d1d1f;color:#fff;border-color:#1d1d1f;text-align:center;font-weight:600;margin-top:12px}
button small{float:right;color:#8a8a8f}.note{background:#fff3d6;border-radius:14px;padding:12px 16px;color:#5c4300}
@media(prefers-color-scheme:dark){body{background:#151516;color:#f2f2f3}p{color:#a9a9ae}button,input{background:#222224;border-color:#3a3a3d}
button.go{background:#f2f2f3;color:#151516;border-color:#f2f2f3}.note{background:#3a3000;color:#ffe9a8}}</style>"""

SETUP_PAGE = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Set up Luma</title>""" + STYLE + """
<main><h1>Hi. Let's get Luma online.</h1><p id="lead">Pick your Wi-Fi. Luma joins it and stays in your home.</p>
<div id="error" class="note" hidden></div><div id="list"><p>Looking for networks...</p></div>
<div id="form" hidden><p id="chosen"></p><input id="password" type="password" autocomplete="off" placeholder="Wi-Fi password" aria-label="Wi-Fi password">
<button class="go" id="connect">Connect Luma</button><button id="back" style="text-align:center;margin-top:8px">Pick another</button></div></main>
<script>
const $ = id => document.getElementById(id);
let picked = null;
function show(error) { $("error").hidden = !error; $("error").textContent = error || ""; }
async function load() {
  try {
    const got = await (await fetch("/networks")).json();
    show(got.error);
    const list = $("list"); list.textContent = "";
    if (!got.networks.length) { const p = document.createElement("p"); p.textContent = "No networks yet. Move Luma closer to your router."; list.append(p); }
    for (const net of got.networks) {
      const b = document.createElement("button"), s = document.createElement("small");
      b.textContent = net.ssid; s.textContent = net.secure ? "" : "open"; b.append(s);
      b.onclick = () => { picked = net; $("list").hidden = true; $("form").hidden = false; $("chosen").textContent = net.ssid;
        $("password").hidden = !net.secure; if (net.secure) $("password").focus(); };
      list.append(b);
    }
    const again = document.createElement("button"); again.textContent = "Look again"; again.style.textAlign = "center"; again.onclick = load; list.append(again);
  } catch (e) { setTimeout(load, 2000); }
}
$("back").onclick = () => { $("form").hidden = true; $("list").hidden = false; };
$("connect").onclick = async () => {
  $("connect").disabled = true; show("");
  try {
    const answer = await fetch("/join", {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ssid: picked.ssid, password: picked.secure ? $("password").value : ""})});
    const got = await answer.json();
    if (!answer.ok) { show(got.error); $("connect").disabled = false; return; }
    $("form").hidden = true; $("lead").hidden = true;
    document.querySelector("h1").textContent = "Luma is joining " + picked.ssid + ".";
    const p = document.createElement("p");
    p.textContent = "Your phone will go back to your own Wi-Fi by itself. Listen: in a moment Luma says what to do next.";
    document.querySelector("main").append(p);
  } catch (e) { show("That didn't reach Luma. Try again."); $("connect").disabled = false; }
};
load();
</script></html>"""

PAIR_PAGE = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Luma</title>""" + STYLE + """
<main><h1>Luma is on your Wi-Fi.</h1><p>Type the code Luma said when you set it up. Then this phone is Luma's app.</p>
<div id="error" class="note" hidden></div>
<input id="code" inputmode="numeric" autocomplete="one-time-code" placeholder="8 numbers" aria-label="The code Luma said">
<button class="go" id="pair">Open Luma</button>
<p style="margin-top:16px">Your phone may warn you about the next page. That's because it comes from the lamp in your home, not from a website.</p></main>
<script>
const $ = id => document.getElementById(id);
$("pair").onclick = async () => {
  const answer = await fetch("/pair", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({code: $("code").value})});
  const got = await answer.json();
  if (answer.ok && got.url) { location.href = got.url; return; }
  $("error").hidden = false; $("error").textContent = got.error;
};
</script></html>"""

DONE_PAGE = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Luma</title>""" + STYLE + """
<main><h1>This Luma is set up.</h1><p>To add this phone, unplug Luma and plug it back in while no phone is paired, or add it from Luma on a computer.</p></main></html>"""


def digits(code):
    return " ".join(str(code))


class Setup:
    """One setup, from the first page to a paired phone. `handle` is the whole web side, so it can be tried without a network."""

    def __init__(self, wifi, code, say=None, pair=None, later=None, clock=time.monotonic):
        self.wifi, self.code = wifi, str(code)
        self.say = say or (lambda text: None)
        self.pair = pair                       # pair(ip) -> the address that makes this phone Luma's app
        self.later = later or (lambda fn: threading.Timer(1.5, fn).start())   # after the answer has left: joining drops the setup network
        self.clock = clock
        self.state = "setup"                   # setup | joining | joined | done
        self.error = ""
        self.ssid = self.ip = ""
        self.port = 80
        self.tries = 0
        self.joined_at = None
        self.lock = threading.Lock()

    # -- the web side ---------------------------------------------------------------------------------------------------------
    def handle(self, method, path, raw):
        """(status, headers, body) for one request."""
        if len(raw) > LIMIT:
            return self._json(413, {"error": "That's too much to send."})
        path = path.split("?")[0]
        if method == "GET":
            if path == "/":
                page = SETUP_PAGE if self.state in ("setup", "joining") else PAIR_PAGE if self._open() else DONE_PAGE
                return 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}, page.encode()
            if path == "/networks":
                return self._json(200, self._networks())
            return 302, {"Location": "/", "Cache-Control": "no-store"}, b""   # a phone's "is this the internet?" page: no, it's Luma
        if method != "POST":
            return self._json(405, {"error": "Not that way."})
        try:
            data = json.loads(raw or b"{}")
        except ValueError:
            data = None
        if not isinstance(data, dict):
            return self._json(400, {"error": "Send that again."})
        if path == "/join":
            return self._ask_to_join(data)
        if path == "/pair":
            return self._pair(data)
        return self._json(404, {"error": "Not found."})

    @staticmethod
    def _json(status, value):
        return status, {"Content-Type": "application/json", "Cache-Control": "no-store"}, json.dumps(value).encode()

    def _networks(self):
        if self.state != "setup":
            return {"state": self.state, "networks": [], "error": ""}
        try:
            networks = self.wifi.scan()
        except WifiError as error:
            return {"state": self.state, "networks": [], "error": str(error)}
        return {"state": self.state, "networks": networks, "error": self.error}

    def _ask_to_join(self, data):
        ssid, password = data.get("ssid"), data.get("password") or ""
        if not isinstance(ssid, str) or not 1 <= len(ssid) <= 32 or "\x00" in ssid:
            return self._json(400, {"error": "Pick a Wi-Fi network from the list."})
        if not isinstance(password, str) or (password and not 8 <= len(password) <= 63):
            return self._json(400, {"error": "Wi-Fi passwords are 8 to 63 characters. Check it and try again."})
        with self.lock:
            if self.state != "setup":
                return self._json(409, {"error": "Luma is already on a Wi-Fi. Change it from Luma's app."})
            self.state, self.error = "joining", ""
        self.later(lambda: self._join(ssid, password))   # the password lives in this one call and in NetworkManager
        return self._json(200, {"ok": True})

    def _join(self, ssid, password):
        try:
            status = self.wifi.join(ssid, password)
        except WifiError as error:
            name = wifi_tools.SETUP_PREFIX + " " + self.code[-4:]
            try:
                name = self.wifi.start_setup(self.code)["ssid"]   # joining took the setup network down: bring it back, same name, same code
            except WifiError:
                pass
            self.error, self.state = str(error), "setup"
            self.say(f"{error} Join {name} again with the same code, and try once more.")
            return
        self.ssid, self.ip = ssid, str(status.get("ip") or "")
        self.joined_at, self.state = self.clock(), "joined"
        self.say(f"I'm on {ssid}. To use me from your phone, open {self.address()} in your phone's browser and type the same code.")

    def address(self):
        return self.ip + ("" if self.port == 80 else f":{self.port}")

    def _open(self):
        return self.state == "joined" and self.tries < TRIES and self.clock() - self.joined_at < OPEN_FOR

    def _pair(self, data):
        with self.lock:
            if self.state in ("setup", "joining"):
                return self._json(409, {"error": "Put Luma on your Wi-Fi first."})
            if not self._open():
                return self._json(410, {"error": "This door is closed now. Unplug Luma and plug it back in to open it again."})
            said = re.sub(r"\D", "", str(data.get("code") or ""))
            if not hmac.compare_digest(said.encode(), self.code.encode()):
                self.tries += 1
                return self._json(403, {"error": "That's not the code Luma said. Try again."})
            try:
                url = self.pair(self.ip) if self.pair else None
            except Exception:
                return self._json(503, {"error": "Luma couldn't open its app just now. Try again in a moment."})
            self.state = "done"
        return self._json(200, {"url": url})


def serve(setup, bind="", ports=(80, 8097)):
    """The setup page on the lamp itself. Port 80 where the service may use it (so a phone's own sheet opens), else 8097."""

    class Handler(BaseHTTPRequestHandler):
        def answer(self, method):
            try:
                size = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                size = LIMIT + 1
            raw = self.rfile.read(min(size, LIMIT + 1)) if method == "POST" else b""
            status, headers, body = setup.handle(method, self.path, raw)
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self): self.answer("GET")
        def do_POST(self): self.answer("POST")
        def log_message(self, *args): pass   # nothing about a setup is written anywhere

    last = None
    for port in ports:
        try:
            server = ThreadingHTTPServer((bind, port), Handler)
        except OSError as error:
            last = error
            continue
        setup.port = server.server_address[1]
        return server
    raise last


def _serve_forever(setup):
    server = serve(setup)
    threading.Thread(target=server.serve_forever, name="luma-setup-page", daemon=True).start()


def run(wifi, say, pair=None, unpaired=None, wait=45, clock=time.monotonic, sleep=time.sleep, serve=_serve_forever):
    """At boot on the device. Not online: the setup network, the page, and how to join, said to a phone. Online with no phone
    paired: the door to pair one, with a fresh code. Otherwise nothing."""
    if not wifi.available():
        return None
    opened = wifi_tools.ensure_online(wifi, None, wait=wait, clock=clock, sleep=sleep)
    if opened:
        setup = Setup(wifi, opened["code"], say=say, pair=pair)
        serve(setup)
        if say:
            say(f"I'm not on Wi-Fi yet. On your phone, join the Wi-Fi called {opened['ssid']}. The password is {digits(opened['code'])}. "
                f"A page opens: pick your Wi-Fi there. If no page opens, go to 10.42.0.1{'' if setup.port == 80 else ':' + str(setup.port)}.")
        return setup
    if not (unpaired and unpaired()):
        return None
    status = wifi.status()
    if not status.get("ip"):
        return None
    setup = Setup(wifi, f"{secrets.randbelow(10 ** 8):08d}", say=say, pair=pair)
    setup.ssid, setup.ip = status.get("ssid") or "", status["ip"]
    setup.joined_at, setup.state = setup.clock(), "joined"
    serve(setup)
    if say:
        say(f"To use me from your phone, open {setup.address()} in your phone's browser and type this code: {digits(setup.code)}.")
    return setup


def start_watch(say=None, pair=None, unpaired=None):
    """Only on a Luma device (its image sets LUMA_WIFI_SETUP=1), never on someone's laptop."""
    if os.environ.get("LUMA_WIFI_SETUP") != "1":
        return None
    thread = threading.Thread(target=run, args=(wifi_tools.Wifi(), say, pair, unpaired), name="luma-first-run", daemon=True)
    thread.start()
    return thread
