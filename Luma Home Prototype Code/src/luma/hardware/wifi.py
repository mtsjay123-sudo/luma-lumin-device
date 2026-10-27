"""The Luma device on the home Wi-Fi, through NetworkManager (nmcli), which Raspberry Pi OS and Jetson images use.

See which network it's on and how strong, list the networks around it, and join one with the password the owner
types on their own phone or computer. The password goes straight to NetworkManager, which keeps it the way any
computer keeps Wi-Fi passwords; Luma never writes it down or logs it.

If the device boots and can't get online, it opens its own setup network ("Luma Setup 1234", protected with a code
it says out loud). A computer joins it, Luma Desktop finds the device there and pairs, and the home Wi-Fi is picked in
Settings.
"""
from __future__ import annotations

import os
import re
import secrets
import shutil
import subprocess
import threading
import time

NMCLI = "nmcli"
SETUP_PREFIX = "Luma Setup"


class WifiError(ValueError):
    """A Wi-Fi step that didn't work, said plainly."""


def _split(line):
    """nmcli -t output: fields split on ':' (a '\\:' inside a value is a real colon)."""
    return [part.replace("\\:", ":") for part in re.split(r"(?<!\\):", line)]


class Wifi:
    def __init__(self, run=None, which=None):
        self.run = run or (lambda argv, **kw: subprocess.run(argv, capture_output=True, text=True, timeout=kw.get("timeout", 30), check=False))
        self.which = which or shutil.which

    def available(self):
        return bool(self.which(NMCLI))

    def _nm(self, *args, timeout=30):
        if not self.available():
            raise WifiError("This Luma can't manage Wi-Fi here (NetworkManager isn't installed).")
        try:
            done = self.run([NMCLI, *args], timeout=timeout)
        except (OSError, subprocess.TimeoutExpired):
            raise WifiError("Wi-Fi didn't answer in time. Try again in a moment.")
        return done

    def status(self):
        """{'connected': True, 'ssid': 'Home', 'signal': 72, 'ip': '192.168.1.40', 'setup': False}"""
        if not self.available():
            return {"available": False, "connected": False}
        done = self._nm("-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi")
        active = next((_split(l) for l in (done.stdout or "").splitlines() if l.startswith("yes:")), None)
        wired = self._nm("-t", "-f", "TYPE,STATE", "dev")
        ethernet = any(_split(l)[:2] == ["ethernet", "connected"] for l in (wired.stdout or "").splitlines())
        ip = ""
        addr = self._nm("-t", "-f", "IP4.ADDRESS", "dev", "show")
        for line in (addr.stdout or "").splitlines():
            m = re.search(r"IP4\.ADDRESS\[\d+\]:(\d+\.\d+\.\d+\.\d+)", line)
            if m and not m.group(1).startswith("127."):
                ip = m.group(1)
                break
        ssid = active[1] if active else ""
        return {"available": True, "connected": bool(active) or ethernet, "ssid": ssid, "signal": int(active[2]) if active and active[2].isdigit() else None,
                "ethernet": ethernet, "ip": ip, "setup": ssid.startswith(SETUP_PREFIX)}

    def scan(self):
        """Networks around the device, strongest first, each once."""
        done = self._nm("-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes", timeout=40)
        best = {}
        for line in (done.stdout or "").splitlines():
            ssid, signal, security = (_split(line) + ["", "", ""])[:3]
            if not ssid or ssid.startswith(SETUP_PREFIX):
                continue
            signal = int(signal) if signal.isdigit() else 0
            if ssid not in best or signal > best[ssid]["signal"]:
                best[ssid] = {"ssid": ssid, "signal": signal, "secure": bool(security.strip() and security.strip() != "--")}
        return sorted(best.values(), key=lambda n: -n["signal"])[:30]

    def join(self, ssid, password=""):
        """Join a network. The password only ever goes to NetworkManager."""
        ssid = str(ssid or "")
        if not 1 <= len(ssid) <= 32 or "\x00" in ssid:
            raise WifiError("Pick a Wi-Fi network from the list.")
        password = str(password or "")
        if password and not 8 <= len(password) <= 63:
            raise WifiError("Wi-Fi passwords are 8 to 63 characters. Check it and try again.")
        self.stop_setup()
        args = ["dev", "wifi", "connect", ssid] + (["password", password] if password else [])
        done = self._nm(*args, timeout=60)
        if done.returncode != 0:
            said = (done.stderr or done.stdout or "").lower()
            if "secrets were required" in said or "password" in said or "802-11-wireless-security" in said:
                raise WifiError(f"That password didn't work for {ssid}. Check it and try again.")
            if "no network with ssid" in said:
                raise WifiError(f"I can't see {ssid} from here. Move me closer to the router, or check the name.")
            raise WifiError(f"I couldn't join {ssid}. Try again in a moment.")
        return self.status()

    def start_setup(self, code=None):
        """Luma's own setup network, so a phone can reach it before it's on the home Wi-Fi. Returns its name and code."""
        code = code or f"{secrets.randbelow(10 ** 8):08d}"
        name = f"{SETUP_PREFIX} {code[-4:]}"
        done = self._nm("dev", "wifi", "hotspot", "ssid", name, "password", code, timeout=40)
        if done.returncode != 0:
            raise WifiError("I couldn't open my setup network.")
        return {"ssid": name, "code": code}

    def stop_setup(self):
        done = self._nm("-t", "-f", "NAME,TYPE", "con", "show", "--active")
        for line in (done.stdout or "").splitlines():
            name = _split(line)[0]
            if name == "Hotspot" or name.startswith(SETUP_PREFIX):
                self._nm("con", "down", name)


def ensure_online(wifi, say=None, wait=45, clock=time.monotonic, sleep=time.sleep):
    """At boot on the device: give the home Wi-Fi a moment, and if there's still no way online, open the setup network and say how to join."""
    if not wifi.available():
        return None
    end = clock() + wait
    while clock() < end:
        if wifi.status().get("connected"):
            return None
        sleep(5)
    setup = wifi.start_setup()
    if say:
        digits = " ".join(setup["code"])
        say(f"I'm not on Wi-Fi yet. On your computer, join the Wi-Fi network {setup['ssid']} with the code {digits}, open Luma Desktop, "
            "and pick your home Wi-Fi in Settings.")
    return setup


def start_watch(say=None):
    """Only on a Luma device (its image sets LUMA_WIFI_SETUP=1), never on someone's laptop."""
    if os.environ.get("LUMA_WIFI_SETUP") != "1":
        return None
    thread = threading.Thread(target=ensure_online, args=(Wifi(), say), name="luma-wifi", daemon=True)
    thread.start()
    return thread
