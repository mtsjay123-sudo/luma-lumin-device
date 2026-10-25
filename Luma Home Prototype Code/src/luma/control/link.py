"""Luma Link: your Luma device and your laptop, one Luma, over Wi-Fi.

The device is its own computer: it runs Luma on its own, keeps its own memory, and
works whether or not the laptop is around. When they're on the same Wi-Fi:

  * the laptop finds the device (a small broadcast, no setup) and pairs once with a
    6-digit code the device shows and says out loud;
  * Luma's window on the laptop opens the device's Luma directly (HTTPS, the device's
    own certificate pinned at pairing, like AirPlay or a paired Bluetooth device),
    and falls back to the laptop's own Luma whenever the device isn't reachable;
  * the two keep their memories in sync both ways;
  * the laptop is the device's hands: things only the laptop can do (open a tab in
    your own Chrome, play music there, read the page you're on) the device asks the
    laptop to do, and it happens right away.

Nothing goes through a cloud. Tokens are kept hashed on the device and encrypted on
the laptop.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import http.client
import json
import os
import queue
import secrets
import socket
import ssl
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

LINK_PORT = 8097
DISCOVERY_PORT = 8098
MAGIC = b"LUMA-DISCOVER-1"


class LinkError(ValueError):
    """A Luma Link step that didn't work, said plainly."""


# -- the device's own certificate (pinned by fingerprint, so no certificate authority is involved) -------
def certificate(directory, hosts=()):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    import ipaddress
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    cert_path, key_path = directory / "link-cert.pem", directory / "link-key.pem"
    if cert_path.exists() and key_path.exists():
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        if cert.not_valid_after_utc - datetime.now(timezone.utc) > timedelta(days=30):
            return cert_path, key_path
    key = ec.generate_private_key(ec.SECP256R1())
    names = [x509.DNSName("luma.local"), x509.DNSName("localhost")]
    for h in {"127.0.0.1", *hosts}:
        try: names.append(x509.IPAddress(ipaddress.ip_address(h)))
        except ValueError: pass
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Luma")])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=3 * 365))
            .add_extension(x509.SubjectAlternativeName(names), critical=False).sign(key, hashes.SHA256()))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    os.chmod(key_path, 0o600)
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path


def fingerprints(cert_path):
    """(hex for Luma, 'sha256/base64' the way Electron reports it)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    der = x509.load_pem_x509_certificate(Path(cert_path).read_bytes()).public_bytes(serialization.Encoding.DER)
    digest = hashlib.sha256(der).digest()
    return digest.hex(), "sha256/" + base64.b64encode(digest).decode()


def pinned_request(host, port, fingerprint, method, path, body=None, token=None, timeout=10, raw=False):
    """HTTPS to the device, trusting only the certificate it had when it was paired. raw=True returns the bytes (a file)."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # verified right below, by the pinned fingerprint, before anything is sent
    conn = http.client.HTTPSConnection(host, int(port), timeout=timeout, context=context)
    try:
        conn.connect()
        der = conn.sock.getpeercert(binary_form=True)
        if not der or not hmac.compare_digest(hashlib.sha256(der).hexdigest(), str(fingerprint)):
            raise LinkError("That isn't the Luma you paired with (its security key is different). Pair again.")
        headers = {"Content-Type": "application/json", "Host": f"{host}:{port}"}
        if token: headers["Authorization"] = "Bearer " + token
        conn.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=headers)
        response = conn.getresponse()
        data = response.read()
        if raw and response.status < 400:
            return data
        try: payload = json.loads(data or b"{}")
        except ValueError: payload = {}
        if response.status >= 400:
            raise LinkError(payload.get("error") or f"Your Luma device answered {response.status}.")
        return payload
    except (OSError, http.client.HTTPException) as error:
        raise LinkError("Can't reach your Luma device right now.") from error
    finally:
        conn.close()


# -- the device side ------------------------------------------------------------------------
class LinkHost:
    """On the device (or any Luma that lets other computers connect): pairing, sessions, memory sync, and the laptop as hands."""

    def __init__(self, agent):
        self.agent, self.store, self.clock = agent, agent.store, agent.clock
        self.lock = threading.Lock()
        self.tickets = {}
        self.jobs, self.results, self.waiting = queue.Queue(), {}, {}
        self.hands_seen = 0
        self.fingerprint = None
        self.port = None
        self.announce = None  # on the device: speak the pairing code when a computer looks for it
        self.announced = -1e9

    # who this Luma is
    def ident(self):
        current = self.store.setting("link_id")
        if not current:
            current = secrets.token_hex(6)
            self.store.set_setting("link_id", current)
        return current

    def name(self):
        return self.store.setting("link_name") or (socket.gethostname().split(".")[0] or "Luma")

    # pairing
    def code(self):
        rec = self.store.setting("link_code") or {}
        if not rec.get("code") or self.clock() - rec.get("at", 0) > 600:
            rec = {"code": f"{secrets.randbelow(1000000):06d}", "at": self.clock()}
            self.store.set_setting("link_code", rec)
        return rec["code"]

    def pair(self, code, name):
        rec = self.store.setting("link_code") or {}
        if not rec.get("code") or self.clock() - rec.get("at", 0) > 600 or not hmac.compare_digest(str(code or "").strip().replace(" ", ""), rec["code"]):
            raise LinkError("That code doesn't match. Use the 6 digits your Luma is showing right now.")
        token = secrets.token_urlsafe(32)
        peers = dict(self.store.setting("link_peers") or {})
        pid = secrets.token_hex(5)
        peers[pid] = {"name": " ".join(str(name or "Laptop").split())[:40], "hash": hashlib.sha256(token.encode()).hexdigest(), "created": self.clock(), "seen": self.clock()}
        self.store.set_setting("link_peers", peers)
        self.store.set_setting("link_code", None)  # one use
        return {"token": token, "device": {"id": self.ident(), "name": self.name()}}

    def peer(self, token):
        if not token:
            return None
        digest = hashlib.sha256(str(token).encode()).hexdigest()
        for pid, p in (self.store.setting("link_peers") or {}).items():
            if hmac.compare_digest(p.get("hash", ""), digest):
                return {**p, "id": pid}
        for s in (self.store.setting("link_sessions") or {}).values():
            if hmac.compare_digest(s.get("hash", ""), digest) and s.get("expires", 0) > self.clock():
                peers = self.store.setting("link_peers") or {}
                if s.get("peer") in peers:
                    return {**peers[s["peer"]], "id": s["peer"]}
        return None

    def peers(self):
        return [{"id": pid, "name": p.get("name"), "created": p.get("created"), "seen": p.get("seen")} for pid, p in (self.store.setting("link_peers") or {}).items()]

    def revoke(self, pid):
        peers = dict(self.store.setting("link_peers") or {})
        peers.pop(str(pid), None)
        self.store.set_setting("link_peers", peers)
        sessions = {k: v for k, v in (self.store.setting("link_sessions") or {}).items() if v.get("peer") != pid}
        self.store.set_setting("link_sessions", sessions)

    # the laptop's window coming in: a one-minute, one-use ticket becomes a 30-day session cookie
    def ticket(self, pid):
        t = secrets.token_urlsafe(24)
        with self.lock:
            self.tickets = {k: v for k, v in self.tickets.items() if v[1] > self.clock()}
            self.tickets[t] = (pid, self.clock() + 60)
        return t

    def redeem(self, ticket):
        with self.lock:
            pid, expires = self.tickets.pop(str(ticket or ""), (None, 0))
        if not pid or self.clock() > expires:
            return None
        session = secrets.token_urlsafe(32)
        sessions = {k: v for k, v in (self.store.setting("link_sessions") or {}).items() if v.get("expires", 0) > self.clock()}
        sessions[secrets.token_hex(6)] = {"hash": hashlib.sha256(session.encode()).hexdigest(), "peer": pid, "expires": self.clock() + 30 * 86400}
        self.store.set_setting("link_sessions", sessions)
        return session

    # the laptop as the device's hands
    def connected(self):
        return self.clock() - self.hands_seen < 60

    def send(self, kind, wait=0, **args):
        ident = secrets.token_hex(6)
        done = threading.Event()
        with self.lock:
            self.waiting[ident] = done
        self.jobs.put({"id": ident, "kind": kind, "at": self.clock(), **args})
        if not wait:
            return {"id": ident}
        done.wait(wait)
        with self.lock:
            self.waiting.pop(ident, None)
            return self.results.pop(ident, None)

    def next(self, timeout=25):
        self.hands_seen = self.clock()
        deadline = time.monotonic() + timeout
        try:
            while True:
                left = deadline - time.monotonic()
                if left <= 0:
                    return None
                job = self.jobs.get(timeout=left)
                if self.clock() - job.get("at", 0) <= 30:
                    return job
        except queue.Empty:
            return None
        finally:
            self.hands_seen = self.clock()

    def done(self, ident, result):
        with self.lock:
            self.results[str(ident)] = result if isinstance(result, dict) else {"result": result}
            event = self.waiting.get(str(ident))
        if event: event.set()

    # one memory, two places
    def sync(self, incoming):
        for m in (incoming or [])[:2000]:
            text = " ".join(str((m or {}).get("text") or "").split())[:500]
            if text:
                try: self.agent.remember_fact(text, source=str(m.get("source") or "synced")[:40], created=float(m.get("created") or self.clock()))
                except (ValueError, TypeError): pass
        return [{"text": m["text"], "created": m.get("created"), "source": m.get("source")} for m in self.store.all("memory", 5000)]

    # found on the Wi-Fi
    def start_discovery(self, port=DISCOVERY_PORT, bind=""):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind, port))

        def answer():
            while True:
                try:
                    data, sender = sock.recvfrom(256)
                except OSError:
                    return
                if data.strip() == MAGIC and self.port:
                    reply = {"luma": 1, "id": self.ident(), "name": self.name(), "port": self.port, "fingerprint": self.fingerprint}
                    try: sock.sendto(json.dumps(reply).encode(), sender)
                    except OSError: pass
                    # A computer is looking for this Luma: say the pairing code out loud (the device may have no screen).
                    if self.announce and time.monotonic() - self.announced > 120:
                        self.announced = time.monotonic()
                        threading.Thread(target=self.announce, args=(self.code(),), daemon=True).start()

        threading.Thread(target=answer, name="luma-link-discovery", daemon=True).start()
        return sock


# -- the laptop side -----------------------------------------------------------------------
class LinkClient:
    """On the laptop: find the device, pair, open it in Luma's window, keep memories in sync, and be its hands."""

    def __init__(self, agent):
        self.agent, self.store, self.clock = agent, agent.store, agent.clock
        self._online = (0, False)
        self.threads = []
        self.stop = threading.Event()

    def device(self):
        d = self.store.setting("link_device")
        return {k: d[k] for k in ("host", "port", "fingerprint", "name", "id") if k in d} if d else None

    def _token(self):
        d = self.store.setting("link_device") or {}
        return base64.b64decode(d["token_b64"]).decode() if d.get("token_b64") else None

    def discover(self, timeout=1.2, targets=(), port=DISCOVERY_PORT):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.2)
        found = {}
        try:
            for target in ["255.255.255.255", *targets]:
                try: sock.sendto(MAGIC, (target, port))
                except OSError: pass
            end = time.monotonic() + timeout
            while time.monotonic() < end:
                try:
                    data, (host, _) = sock.recvfrom(2048)
                except socket.timeout:
                    continue
                try: info = json.loads(data)
                except ValueError: continue
                if info.get("luma") == 1 and info.get("fingerprint") and info.get("port"):
                    found[info.get("id") or host] = {"id": info.get("id"), "name": str(info.get("name") or "Luma")[:40], "host": host,
                                                     "port": int(info["port"]), "fingerprint": str(info["fingerprint"])}
        finally:
            sock.close()
        return list(found.values())

    def pair(self, host, port, fingerprint, code):
        name = socket.gethostname().split(".")[0] or "Laptop"
        out = pinned_request(host, port, fingerprint, "POST", "/link/pair", {"code": str(code), "name": name})
        token = out.get("token")
        if not token:
            raise LinkError("Your Luma didn't finish pairing. Try again.")
        device = out.get("device") or {}
        self.store.set_setting("link_device", {"host": host, "port": int(port), "fingerprint": fingerprint, "name": device.get("name") or "Luma",
                                               "id": device.get("id"), "token_b64": base64.b64encode(token.encode()).decode(), "paired": self.clock()})
        self._online = (0, False)
        self.start()
        return self.device()

    def forget(self):
        self.store.set_setting("link_device", None)
        self.stop.set()

    def call(self, method, path, body=None, timeout=10):
        d = self.store.setting("link_device")
        if not d:
            raise LinkError("No Luma device is paired with this computer.")
        return pinned_request(d["host"], d["port"], d["fingerprint"], method, path, body, token=self._token(), timeout=timeout)

    def call_bytes(self, method, path, timeout=60):
        """A file from the device (a project's package), over the same pinned connection."""
        d = self.store.setting("link_device")
        if not d:
            raise LinkError("No Luma device is paired with this computer.")
        return pinned_request(d["host"], d["port"], d["fingerprint"], method, path, None, token=self._token(), timeout=timeout, raw=True)

    def online(self):
        at, ok = self._online
        if self.clock() - at < 10:
            return ok
        try: ok = bool(self.call("GET", "/link/ping", timeout=2).get("ok"))
        except LinkError: ok = False
        self._online = (self.clock(), ok)
        return ok

    def enter(self):
        """A one-use way in for Luma's window, and the fingerprint the window should trust."""
        d = self.store.setting("link_device") or {}
        ticket = self.call("POST", "/link/ticket", {}).get("ticket")
        if not ticket:
            raise LinkError("Your Luma didn't let this computer in. Pair again.")
        raw = bytes.fromhex(d["fingerprint"])
        return {"url": f"https://{d['host']}:{d['port']}/link/enter?ticket={ticket}", "origin": f"https://{d['host']}:{d['port']}",
                "fingerprint": "sha256/" + base64.b64encode(raw).decode()}

    def sync_memories(self):
        local = [{"text": m["text"], "created": m.get("created"), "source": m.get("source")} for m in self.store.all("memory", 5000)]
        theirs = self.call("POST", "/link/memory/sync", {"memories": local}, timeout=20).get("memories") or []
        added = 0
        for m in theirs:
            text = " ".join(str(m.get("text") or "").split())[:500]
            if not text: continue
            try:
                row = self.agent.remember_fact(text, source=str(m.get("source") or "synced")[:40], created=float(m.get("created") or self.clock()))
                added += bool(row and row != "full")
            except (ValueError, TypeError):
                pass
        return added

    # background: memory sync every minute, and the hands loop
    def start(self):
        if not self.store.setting("link_device") or any(t.is_alive() for t in self.threads):
            return
        self.stop = threading.Event()

        def syncing():
            while not self.stop.is_set() and self.store.setting("link_device"):
                try:
                    if self.online(): self.sync_memories()
                except Exception:
                    pass
                self.stop.wait(60)

        def hands():
            while not self.stop.is_set() and self.store.setting("link_device"):
                try:
                    job = self.call("GET", "/link/hands/next", timeout=40).get("job")
                except LinkError:
                    self.stop.wait(15)
                    continue
                if not job:
                    continue
                try: result = self._do(job)
                except Exception as error: result = {"error": str(error)[:200]}
                try: self.call("POST", "/link/hands/done", {"id": job.get("id"), "result": result})
                except LinkError: pass

        self.threads = [threading.Thread(target=syncing, name="luma-link-sync", daemon=True), threading.Thread(target=hands, name="luma-link-hands", daemon=True)]
        for t in self.threads: t.start()

    def _do(self, job):
        """Something only this computer can do, asked for by the device."""
        kind = job.get("kind")
        chrome = self.agent.chrome
        if kind in {"open", "play", "read", "tabs"} and chrome.connected():
            return chrome.send(kind, wait=20 if kind in {"read", "tabs", "play"} else 0, **{k: v for k, v in job.items() if k not in {"id", "kind", "at"}}) or {"ok": True}
        if kind == "open":
            url = str(job.get("url") or "")
            if not url.startswith(("https://", "http://")):
                return {"error": "Only web addresses."}
            import subprocess, sys
            opener = ["open", url] if sys.platform == "darwin" else ["xdg-open", url]
            subprocess.Popen(opener, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"opened": url}
        if kind == "play":
            from urllib.parse import quote_plus
            return self._do({"kind": "open", "url": "https://music.youtube.com/search?q=" + quote_plus(str(job.get("query") or "music"))})
        return {"error": "This computer can't do that one."}
