"""Computer mode: what Luma may do on this computer when the device asks.

The device is the brain; a paired computer is its hands. Opening a web page or
playing music needs nothing set up. Everything else is off until the person at
this computer turns it on, here, and only here:

  * look in folders they picked (find files by name, read text files),
  * open apps by name,
  * look at the screen (off unless they switch it on).

Some things are never done from here at all: anything under a folder that holds
keys, passwords or wallets, any file outside the picked folders (symlinks
included), and changing or deleting files. Every request is written to a log on
this computer, and Pause stops all of it at once until they resume.
"""
from __future__ import annotations

import base64
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

KINDS = {"files.find", "files.read", "app.open", "screen.look"}
# never read from, or even list, anything that looks like keys, passwords or wallets
SECRET = re.compile(r"(?:^|[/\\])(?:\.ssh|\.gnupg|\.aws|\.azure|\.kube|\.docker|\.netrc|\.npmrc|\.pypirc|\.env(?:\.[\w-]+)?|keychains?|"
                    r"id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?|[^/\\]*\.(?:pem|key|p12|pfx|kdbx|keychain-db)|[^/\\]*(?:password|passwd|secret|wallet|credential)[^/\\]*)(?:$|[/\\])", re.I)
# no quotes, &, ;, | or slashes (nothing a shell could read as a command), and no dots, so "evil.bat" can't be opened as an app
APP_NAME = re.compile(r"\w[\w +-]{0,59}")
TEXT_LIMIT = 60_000
FILE_LIMIT = 2_000_000
WALK_LIMIT = 20_000
LOG_LIMIT = 200


class Computer:
    def __init__(self, store, clock):
        self.store, self.clock = store, clock

    # settings, changed only from this computer
    def settings(self):
        saved = self.store.setting("computer_mode") or {}
        return {"folders": [f for f in saved.get("folders", []) if isinstance(f, str)], "apps": bool(saved.get("apps", False)),
                "screen": bool(saved.get("screen", False)), "paused": bool(saved.get("paused", False))}

    def _save(self, **changes):
        self.store.set_setting("computer_mode", {**self.settings(), **changes})
        return self.status()

    def status(self):
        return {**self.settings(), "log": self.log()[-30:]}

    def grant(self, folder):
        path = Path(os.path.expanduser(str(folder or "").strip())).resolve()
        if not str(folder or "").strip() or not path.is_dir():
            raise ValueError("Pick a folder that exists on this computer.")
        home = Path.home().resolve()
        drives = [Path(p) for p in ("/Volumes", "/media", "/mnt") if Path(p).is_dir()]
        if not any(root in path.parents for root in [home] + drives):
            raise ValueError("Pick a folder inside your home folder, like Documents, or on an external drive.")
        inner = path.relative_to(home).parts if home in path.parents else path.parts[2:]
        if SECRET.search(str(path)) or any(p.startswith(".") for p in inner) or (inner and inner[0] in {"Library", "AppData"}):
            raise ValueError("That folder holds app data, keys or passwords, so Luma stays out of it.")
        folders = [f for f in self.settings()["folders"] if f != str(path)] + [str(path)]
        return self._save(folders=folders[-12:])

    def revoke(self, folder):
        return self._save(folders=[f for f in self.settings()["folders"] if f != str(folder)])

    def allow(self, what, on):
        if what not in {"apps", "screen"}:
            raise ValueError("Choose apps or screen.")
        return self._save(**{what: bool(on)})

    def pause(self, on=True):
        self._record("pause" if on else "resume", "Paused here" if on else "Resumed", True)
        return self._save(paused=bool(on))

    # the log
    def log(self):
        return list(self.store.setting("computer_log") or [])

    def _record(self, kind, what, ok):
        entries = self.log() + [{"kind": kind, "what": str(what)[:160], "ok": bool(ok), "at": self.clock()}]
        self.store.set_setting("computer_log", entries[-LOG_LIMIT:])

    def record(self, job, result):
        """Called for every request from the device, including the ones Chrome handles."""
        what = job.get("url") or job.get("query") or job.get("path") or job.get("name") or ""
        self._record(str(job.get("kind"))[:20], what, not (isinstance(result, dict) and result.get("error")))

    # the work
    def do(self, job):
        kind = job.get("kind")
        if self.settings()["paused"]:
            return {"error": "Luma is paused on this computer. Resume it there to keep going."}
        handler = {"files.find": self._find, "files.read": self._read, "app.open": self._open_app, "screen.look": self._look}.get(kind)
        if not handler:
            return {"error": "This computer can't do that one."}
        try:
            return handler(job)
        except (OSError, ValueError, TypeError) as error:
            return {"error": str(error)[:200] or "That didn't work on this computer."}

    def _folders(self):
        roots = []
        for f in self.settings()["folders"]:
            path = Path(f).resolve()
            if path.is_dir(): roots.append(path)
        if not roots:
            raise ValueError("No folders are shared with Luma on this computer yet. Share one in Luma Desktop: Settings, then What Luma can do on this computer.")
        return roots

    def inside(self, path):
        """The real file this path points to, if it's in a shared folder and not a secret; otherwise None."""
        try:
            real = Path(os.path.expanduser(str(path))).resolve()
        except (OSError, RuntimeError):
            return None
        if SECRET.search(str(real)):
            return None
        for root in self._folders():
            if real == root or root in real.parents:
                return None if any(p.startswith(".") for p in real.relative_to(root).parts) else real
        return None

    def _find(self, job):
        words = [w for w in re.findall(r"[\w.-]+", str(job.get("query") or "").casefold()) if w][:6]
        if not words:
            raise ValueError("Tell me part of the file's name.")
        limit = max(1, min(int(job.get("limit") or 12), 30))
        found, seen = [], 0
        for root in self._folders():
            for here, dirs, files in os.walk(root, followlinks=False):
                dirs[:] = [d for d in dirs if not d.startswith(".") and not SECRET.search("/" + d + "/")]
                for name in files:
                    seen += 1
                    if name.startswith(".") or SECRET.search("/" + name):
                        continue
                    if all(w in name.casefold() for w in words):
                        path = Path(here) / name
                        if path.is_symlink():
                            continue  # it may point outside the shared folder
                        try: st = path.stat()
                        except OSError: continue
                        found.append({"name": name, "path": str(path), "folder": root.name, "size": st.st_size, "modified": st.st_mtime})
                if seen > WALK_LIMIT or len(found) >= limit:
                    break
            if seen > WALK_LIMIT or len(found) >= limit:
                break
        found.sort(key=lambda f: -f["modified"])
        return {"files": found[:limit], "looked_through": seen}

    def _read(self, job):
        real = self.inside(job.get("path") or "")
        if real is None:
            raise ValueError("That file isn't in a folder you've shared with Luma.")
        if not real.is_file():
            raise ValueError("I couldn't find that file.")
        if real.stat().st_size > FILE_LIMIT:
            raise ValueError("That file is too big to read here.")
        data = real.read_bytes()
        if b"\0" in data[:4096]:
            raise ValueError("That's not a text file, so I can't read it here.")
        text = data.decode("utf-8", errors="replace")
        return {"name": real.name, "path": str(real), "text": text[:TEXT_LIMIT], "cut": len(text) > TEXT_LIMIT}

    def _open_app(self, job):
        if not self.settings()["apps"]:
            raise ValueError("Opening apps is off on this computer. Turn it on in Luma Desktop: Settings, then What Luma can do on this computer.")
        name = str(job.get("name") or "").strip()
        if not APP_NAME.fullmatch(name):
            raise ValueError("Tell me the app's name, like Spotify or Notes.")
        if os.name == "nt":
            try: os.startfile(name)  # ShellExecute: finds registered apps by name, no shell in between
            except OSError: raise ValueError(f"I couldn't find an app called {name} on this computer.")
            return {"opened": name}
        cmd = ["open", "-a", name] if sys.platform == "darwin" else ["gtk-launch", name.lower()]
        try:
            done = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            raise ValueError(f"I couldn't open {name} on this computer.")
        if done.returncode != 0:
            raise ValueError(f"I couldn't find an app called {name} on this computer.")
        return {"opened": name}

    def _look(self, job):
        if not self.settings()["screen"]:
            raise ValueError("Looking at the screen is off on this computer. Turn it on in Luma Desktop: Settings, then What Luma can do on this computer.")
        shot = Path(tempfile.mkdtemp(prefix="luma-look-")) / "screen.png"
        try:
            if sys.platform == "darwin":
                subprocess.run(["screencapture", "-x", "-t", "png", str(shot)], timeout=15, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                from PIL import ImageGrab
                ImageGrab.grab().save(shot)
            from PIL import Image
            with Image.open(shot) as im:
                im.thumbnail((1600, 1600))
                im.convert("RGB").save(shot.with_suffix(".jpg"), quality=80)
            return {"image_b64": base64.b64encode(shot.with_suffix(".jpg").read_bytes()).decode(), "mime": "image/jpeg"}
        except (ImportError, OSError, subprocess.SubprocessError):
            raise ValueError("I couldn't see the screen on this computer.")
        finally:
            for p in (shot, shot.with_suffix(".jpg")):
                p.unlink(missing_ok=True)
            shot.parent.rmdir()
