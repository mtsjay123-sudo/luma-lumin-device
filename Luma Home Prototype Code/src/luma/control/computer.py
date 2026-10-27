"""Computer mode: what Luma may do on this computer when the device asks.

The device is the brain; a paired computer is its hands. Opening a web page or
playing music needs nothing set up. Everything else is off until the person at
this computer turns it on, here, and only here:

  * look in folders they picked (find files by name, read text files),
  * open apps by name,
  * look at the screen (off unless they switch it on),
  * click and type in apps (on a Mac, through its accessibility system; off unless they switch it on, and the device asks
    the owner before every click and every bit of typing).

Some things are never done from here at all: anything under a folder that holds
keys, passwords or wallets, any file outside the picked folders (symlinks
included), changing or deleting files, typing into password fields, and
clicking or typing in apps that run commands or hold passwords (Terminal,
Keychain, password managers, System Settings). Every request is written to a log on
this computer, and Pause stops all of it at once until they resume.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

KINDS = {"files.find", "files.read", "app.open", "screen.look", "ui.read", "ui.press", "ui.type"}
# never read from, or even list, anything that looks like keys, passwords or wallets
SECRET = re.compile(r"(?:^|[/\\])(?:\.ssh|\.gnupg|\.aws|\.azure|\.kube|\.docker|\.netrc|\.npmrc|\.pypirc|\.env(?:\.[\w-]+)?|keychains?|"
                    r"id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?|[^/\\]*\.(?:pem|key|p12|pfx|kdbx|keychain-db)|[^/\\]*(?:password|passwd|secret|wallet|credential)[^/\\]*)(?:$|[/\\])", re.I)
# no quotes, &, ;, | or slashes (nothing a shell could read as a command), and no dots, so "evil.bat" can't be opened as an app
APP_NAME = re.compile(r"\w[\w +-]{0,59}")
TEXT_LIMIT = 60_000
FILE_LIMIT = 2_000_000
WALK_LIMIT = 20_000
LOG_LIMIT = 200
# Typing here could run a command or touch passwords, so Luma never clicks or types in these.
OFF_LIMITS = re.compile(r"^(?:terminal|iterm2?|warp|alacritty|kitty|hyper|ghostty|script editor|automator|shortcuts|console|activity monitor|"
                        r"keychain access|passwords|1password(?: \d+)?|bitwarden|lastpass|dashlane|keeper|enpass|"
                        r"system settings|system preferences|disk utility|migration assistant|boot camp assistant|installer|luma(?: desktop)?)$", re.I)
UI_LIMIT = 150  # elements described per window
# The accessibility tree of one window, read and acted on through System Events. The job comes in as JSON in argv; nothing
# from it is ever spliced into the script. Password fields are never read or typed into. Refs are positions in the window's
# element list; press and type check the element is still the one the owner approved (same role and label) before acting.
UI_SCRIPT = r"""
function run(argv) {
  var job = JSON.parse(argv[0]);
  var se = Application("System Events");
  var procs = job.app ? se.applicationProcesses.whose({name: job.app}) : se.applicationProcesses.whose({frontmost: true});
  if (procs.length === 0) return JSON.stringify({error: "not_running"});
  var proc = procs[0];
  var app = proc.name();
  if (!job.app && /^(?:luma|electron)/i.test(app)) return JSON.stringify({error: "which_app", app: app});
  if (job.blocked && new RegExp(job.blocked, "i").test(app)) return JSON.stringify({error: "off_limits", app: app});
  var wins = proc.windows();
  if (wins.length === 0) return JSON.stringify({error: "no_window", app: app});
  var all = wins[0].entireContents();
  function str(f) { try { var v = f(); return v === null || v === undefined ? "" : String(v); } catch (e) { return ""; } }
  function label(el) { return (str(function () { return el.name(); }) || str(function () { return el.description(); }) || str(function () { return el.title(); })).slice(0, 120); }
  function secure(el) { return /Secure/.test(str(function () { return el.subrole(); })) || /password/i.test(label(el)); }
  if (job.kind === "ui.read") {
    var keep = /^AX(?:Button|TextField|TextArea|SearchField|ComboBox|CheckBox|RadioButton|PopUpButton|MenuButton|Link|Tab|StaticText|Heading|MenuItem|Cell)$/;
    var out = [];
    for (var i = 0; i < all.length && out.length < job.limit && i < 3000; i++) {
      var el = all[i], role = str(function () { return el.role(); });
      if (!keep.test(role)) continue;
      var item = {ref: i, role: role.replace(/^AX/, ""), label: label(el)};
      if (/TextField|TextArea|SearchField|ComboBox|StaticText|CheckBox/.test(role)) item.value = secure(el) ? "" : str(function () { return el.value(); }).slice(0, 200);
      if (secure(el)) item.secure = true;
      if (str(function () { return el.enabled(); }) === "false") item.disabled = true;
      if (!item.label && !item.value) continue;
      out.push(item);
    }
    return JSON.stringify({app: app, window: str(function () { return wins[0].name(); }).slice(0, 120), elements: out});
  }
  var el = all[job.ref];
  if (!el) return JSON.stringify({error: "changed", app: app});
  var role = str(function () { return el.role(); }).replace(/^AX/, "");
  if (role !== job.role || label(el) !== job.label) return JSON.stringify({error: "changed", app: app});
  if (job.kind === "ui.press") {
    try { el.actions["AXPress"].perform(); } catch (e) { return JSON.stringify({error: "cant_press", app: app}); }
    return JSON.stringify({app: app, pressed: job.label});
  }
  if (job.kind === "ui.type") {
    if (secure(el)) return JSON.stringify({error: "password", app: app});
    try { el.focused = true; } catch (e) {}
    try { el.value = job.text; } catch (e) {}
    if (str(function () { return el.value(); }) !== job.text) {
      proc.frontmost = true;
      delay(0.2);
      se.keystroke(job.text);
    }
    return JSON.stringify({app: app, typed: job.label});
  }
  return JSON.stringify({error: "unknown"});
}
"""
UI_ERRORS = {
    "not_running": "That app isn't open on this computer.", "no_window": "That app has no window open right now.",
    "which_app": "Which app should I look at? Tell me its name, like Notes or Mail.",
    "off_limits": "I don't click or type in that app: it can run commands or holds passwords.",
    "changed": "That window changed since I looked. I'll look again before doing anything.",
    "cant_press": "That didn't press. It may not be a button I can use.", "password": "I never type into password fields. Type that one yourself.",
}


class Computer:
    def __init__(self, store, clock):
        self.store, self.clock = store, clock

    # settings, changed only from this computer
    def settings(self):
        saved = self.store.setting("computer_mode") or {}
        return {"folders": [f for f in saved.get("folders", []) if isinstance(f, str)], "apps": bool(saved.get("apps", False)),
                "screen": bool(saved.get("screen", False)), "control": bool(saved.get("control", False)), "paused": bool(saved.get("paused", False))}

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
        if what not in {"apps", "screen", "control"}:
            raise ValueError("Choose apps, screen or control.")
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
        what = job.get("url") or job.get("query") or job.get("path") or job.get("name") or job.get("label") or job.get("app") or ""
        self._record(str(job.get("kind"))[:20], what, not (isinstance(result, dict) and result.get("error")))

    # the work
    def do(self, job):
        kind = job.get("kind")
        if self.settings()["paused"]:
            return {"error": "Luma is paused on this computer. Resume it there to keep going."}
        handler = {"files.find": self._find, "files.read": self._read, "app.open": self._open_app, "screen.look": self._look,
                   "ui.read": self._ui, "ui.press": self._ui, "ui.type": self._ui}.get(kind)
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

    def _ui(self, job, run=subprocess.run):
        """Read an app window's buttons and fields, or press or type in one the owner approved. Mac only for now."""
        if not self.settings()["control"]:
            raise ValueError("Clicking and typing in apps is off on this computer. Turn it on in Luma Desktop: Settings, then What Luma can do on this computer.")
        if sys.platform != "darwin":
            raise ValueError("Clicking and typing in apps works on a Mac for now.")
        kind, app = job.get("kind"), str(job.get("app") or "").strip()
        if app and not APP_NAME.fullmatch(app):
            raise ValueError("Tell me the app's name, like Notes or Mail.")
        if app and OFF_LIMITS.match(app):
            raise ValueError(UI_ERRORS["off_limits"])
        task = {"kind": kind, "app": app, "limit": UI_LIMIT, "blocked": OFF_LIMITS.pattern}
        if kind in {"ui.press", "ui.type"}:
            if type(job.get("ref")) is not int or job["ref"] < 0 or not str(job.get("label") or "") or not str(job.get("role") or ""):
                raise ValueError("Look at the window first, then pick something from it.")
            task.update(ref=job["ref"], label=str(job["label"])[:120], role=str(job["role"])[:40])
        if kind == "ui.type":
            text = str(job.get("text") or "")
            if not text or len(text) > 2000 or "\x00" in text:
                raise ValueError("Tell me what to type (up to 2,000 characters).")
            task["text"] = text
        try:
            done = run(["osascript", "-l", "JavaScript", "-e", UI_SCRIPT, json.dumps(task)], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            raise ValueError("That app didn't answer in time.")
        if done.returncode != 0:
            if "-1719" in (done.stderr or "") or "-25211" in (done.stderr or "") or "assistive" in (done.stderr or "").lower():
                raise ValueError("macOS needs to let Luma use this computer: System Settings, Privacy & Security, Accessibility, then turn on Luma.")
            raise ValueError("I couldn't reach that app.")
        try:
            got = json.loads(done.stdout.strip() or "{}")
        except ValueError:
            raise ValueError("I couldn't read that app's window.")
        if got.get("error"):
            raise ValueError(UI_ERRORS.get(got["error"], "That didn't work in that app."))
        return got
