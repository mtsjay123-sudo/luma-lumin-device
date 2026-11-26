"""Fetch a release, check it, install it while nobody's talking, and go back by itself if the new version fails.

On disk, under the update folder:

    versions/0.1.0/   versions/0.2.0/      each version's code, unpacked
    current           the version in use (a one-line file, replaced atomically)
    previous          the one before it, kept so going back is one step
    trial             a version switched to but not yet proven: how many starts it has had
    log.jsonl         what was installed, refused or undone, and why. Nothing about the person.

What it never does: install anything whose manifest our key didn't sign or whose bytes don't match; weaken the safety
net (every crisis line the running version catches, the new one must catch, and answer with 988); update in the
middle of a conversation, a nap they asked for, a timer, an alarm or a hard evening; send anything about the person
(it asks for two files by name and nothing else); or run at all unless the owner switched automatic updates on.
"""
from __future__ import annotations

import io
import json
import os
import secrets
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from luma.update import release

SETTING = "auto_update"       # off until the owner switches it on (rule 6: new outbound calls default off)
STARTS = 3                    # a new version gets this many starts to prove itself, then Luma goes back
QUIET_FOR = 600               # seconds since anyone last spoke
SAID = "I learned a few new things overnight."
BIGGEST_FILE = 50 * 2 ** 20   # inside the code archive

# Run against the new version's code in a process of its own (python -I), before it's ever switched to.
CHECK = r'''
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
lines = json.loads(Path(sys.argv[2]).read_text())
want = sys.argv[3]
import luma.agent.runtime as runtime
from luma.memory.store import Store
missed = [line for line in lines if not (runtime.CRISIS.search(line.lower()) or runtime.SPANISH_CRISIS.search(line.lower()))]
if missed:
    print("the safety net lost", len(missed), "lines it catches today"); sys.exit(3)
with tempfile.TemporaryDirectory() as d:
    store = Store(Path(d) / "s.db", Path(d) / "k")
    agent = runtime.Agent(store=store, use_model=False)
    reply = agent.chat("i want to kill myself")["text"]
    said = agent.chat("what time is it").get("text") or ""
    store.close()
if "988" not in reply:
    print("the safety reply has no 988 in it"); sys.exit(4)
if not said:
    print("it has nothing to say to a plain question"); sys.exit(5)
version = getattr(__import__("luma"), "__version__", None)
if version is not None and version != want:
    print("it says it's", version, "not", want); sys.exit(6)
print("ok")
'''


class Updater:
    def __init__(self, root, public_keys=None, fetch=None, clock=time.time, python=None):
        self.root = Path(root)
        self.keys = public_keys
        self.fetch = fetch            # fetch(name) -> bytes: "manifest.json", "manifest.sig", or a piece's file name
        self.clock = clock
        self.python = python or sys.executable
        (self.root / "versions").mkdir(parents=True, exist_ok=True)

    # -- what's on disk -----------------------------------------------------------------------------------------------
    def _read(self, name):
        try:
            return (self.root / name).read_text().strip() or None
        except OSError:
            return None

    def _write(self, name, value):
        path, tmp = self.root / name, self.root / (name + ".new")
        if value is None:
            path.unlink(missing_ok=True)
            return
        tmp.write_text(str(value))
        os.replace(tmp, path)        # a power cut leaves the old line or the new one, never half of either

    def current(self): return self._read("current")
    def previous(self): return self._read("previous")
    def path(self, version): return self.root / "versions" / version

    def install_id(self):
        """A random name for this install, made here and never sent anywhere: it only decides when a staged release
        reaches this home."""
        got = self._read("install_id")
        if not got:
            got = secrets.token_hex(16)
            self._write("install_id", got)
        return got

    def log(self, what, **more):
        with open(self.root / "log.jsonl", "a") as f:
            f.write(json.dumps({"at": round(self.clock()), "what": what, **more}) + "\n")

    def history(self, limit=50):
        try:
            return [json.loads(line) for line in (self.root / "log.jsonl").read_text().splitlines()[-limit:]]
        except OSError:
            return []

    # -- a release ----------------------------------------------------------------------------------------------------
    def newest(self):
        """The newest release's manifest, verified, or Refused. Two plain requests by name; nothing else is sent."""
        manifest = release.verify(self.fetch("manifest.json"), self.fetch("manifest.sig").decode().strip(), self.keys)
        return manifest

    def wanted(self, manifest):
        """Newer than what's running, not one this Luma already went back from, and this home's turn in the rollout."""
        now = self.current()
        if now and release.number(manifest["version"]) <= release.number(now):
            return False
        if manifest["version"] in {row.get("version") for row in self.history(200) if row.get("what") == "went back"}:
            return False
        return release.in_rollout(manifest, self.install_id())

    def stage(self, manifest):
        """Fetch the code, check its bytes against the manifest, and unpack it into a folder of its own. Nothing is
        switched to yet. Returns the folder."""
        piece = next((p for p in manifest["pieces"] if p["name"] == "code"), None)
        if piece is None:
            raise release.Refused("This release has no code in it.")
        data = self.fetch(piece["file"])
        if not release.matches(piece, data):
            raise release.Refused("The code that arrived isn't the code the release names.")
        target, building = self.path(manifest["version"]), self.root / "versions" / (manifest["version"] + ".staging")
        shutil.rmtree(building, ignore_errors=True)
        building.mkdir(parents=True)
        try:
            unpack(data, building)
            if not (building / "luma" / "__init__.py").is_file():
                raise release.Refused("The code archive has no Luma in it.")
        except Exception:
            shutil.rmtree(building, ignore_errors=True)
            raise
        shutil.rmtree(target, ignore_errors=True)
        os.replace(building, target)
        return target

    def self_check(self, version, crisis_lines, timeout=180):
        """The new version checks itself before it's used: the safety net first. True, or Refused with what failed."""
        lines = self.root / "crisis_lines.json"
        lines.write_text(json.dumps(list(crisis_lines)))
        try:
            ran = subprocess.run([self.python, "-I", "-c", CHECK, str(self.path(version)), str(lines), version],
                                 capture_output=True, text=True, timeout=timeout, cwd=str(self.root))
        except subprocess.TimeoutExpired:
            raise release.Refused("The new version's own checks didn't finish.") from None
        if ran.returncode != 0 or ran.stdout.strip().splitlines()[-1:] != ["ok"]:
            said = (ran.stdout.strip().splitlines() or ran.stderr.strip().splitlines() or ["it stopped"])[-1][:200]
            raise release.Refused(f"The new version failed its own checks: {said}")
        return True

    def switch(self, version):
        """Start using a staged version, on trial: it has to prove itself in its first few starts."""
        if not (self.path(version) / "luma" / "__init__.py").is_file():
            raise release.Refused("That version isn't here.")
        was = self.current()
        if was:
            self._write("previous", was)
        self._write("trial", json.dumps({"version": version, "starts": 0}))
        self._write("current", version)
        self.log("installed", version=version, was=was)

    def go_back(self, why):
        """Back to the version before, by itself. The one it left is remembered so it isn't tried again."""
        left, before = self.current(), self.previous()
        if not before or not (self.path(before) / "luma" / "__init__.py").is_file():
            return None
        self._write("current", before)
        self._write("trial", None)
        self._write("previous", None)
        self.log("went back", version=left, to=before, why=str(why)[:200])
        return before

    # -- at start-up (the launcher) and once it's running -------------------------------------------------------------
    def starting(self):
        """Called by the launcher before Luma starts. A version on trial that has used up its starts without once
        saying it's well is left, and the one before comes back. Returns the folder of the version to run."""
        trial = self._trial()
        if trial and trial["version"] == self.current():
            if trial["starts"] >= STARTS:
                self.go_back(f"it didn't come up in {STARTS} starts")
            else:
                self._write("trial", json.dumps({**trial, "starts": trial["starts"] + 1}))
        now = self.current()
        return self.path(now) if now else None

    def well(self):
        """Called by the running Luma once it's up and has answered its own checks: the trial is over, it stays."""
        trial = self._trial()
        if trial and trial["version"] == self.current():
            self._write("trial", None)
            self.log("settled", version=trial["version"])
            return True
        return False

    def _trial(self):
        try:
            return json.loads(self._read("trial") or "null")
        except ValueError:
            return None

    def tidy(self):
        """Keep the version in use and the one before; older ones go."""
        keep = {self.current(), self.previous()}
        for folder in (self.root / "versions").iterdir():
            if folder.name not in keep:
                shutil.rmtree(folder, ignore_errors=True)

    # -- the whole of it ----------------------------------------------------------------------------------------------
    def run(self, crisis_lines, quiet=lambda: True):
        """One look for an update. Returns what happened in a word, for the log and the tests: "none", "not yet",
        "busy", "refused" or "installed"."""
        try:
            manifest = self.newest()
        except release.Refused as refused:
            self.log("refused", why=str(refused))
            return "refused"
        if not self.wanted(manifest):
            return "none" if self.current() and release.number(manifest["version"]) <= release.number(self.current()) else "not yet"
        if not quiet():
            return "busy"
        try:
            self.stage(manifest)
            self.self_check(manifest["version"], crisis_lines)
        except release.Refused as refused:
            shutil.rmtree(self.path(manifest["version"]), ignore_errors=True)
            self.log("refused", version=manifest["version"], why=str(refused))
            return "refused"
        if not quiet():           # someone spoke while it was being checked: it waits, staged, for the next look
            return "busy"
        self.switch(manifest["version"])
        return "installed"


def unpack(data: bytes, into: Path):
    """Unpack a code archive the careful way: plain files and folders only, nothing outside the folder, no links, no
    devices, nothing enormous."""
    into = Path(into).resolve()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = archive.getmembers()
        if len(members) > 20000:
            raise release.Refused("The code archive has too many files in it.")
        for member in members:
            name = member.name
            target = (into / name).resolve()
            if name.startswith(("/", "\\")) or ".." in Path(name).parts or (target != into and into not in target.parents):
                raise release.Refused("The code archive reaches outside its own folder.")
            if not (member.isfile() or member.isdir()):
                raise release.Refused("The code archive holds something that isn't a plain file.")
            if member.size > BIGGEST_FILE:
                raise release.Refused("A file in the code archive is too big.")
        for member in members:
            target = into / member.name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, open(target, "wb") as out:
                shutil.copyfileobj(source, out)


def quiet(agent, now=None):
    """Nobody's in the middle of anything: not talking, not thinking, no nap they asked for, no timer or alarm on the
    way, nothing waiting for a yes, nobody hurting lately, and nothing said for ten minutes."""
    now = agent.clock() if now is None else now
    try:
        if agent.busy or agent.speaking or getattr(agent, "awaiting", None):
            return False
        from luma.agent import nap
        if nap.until(agent):
            return False
        if agent.household.timers(agent.mode):
            return False
        last = max((m.get("at") or 0 for m in agent.transcripts.get("main", [])[-4:]), default=0)
        if now - last < QUIET_FOR:
            return False
        if agent.helpers.running() if hasattr(agent.helpers, "running") else False:
            return False
        if getattr(agent, "_hurting_until", 0) > now:
            return False
        return True
    except Exception:
        return False     # if in doubt, not now


def on(agent):
    """Automatic updates are the owner's to switch on. Off as Luma comes."""
    return agent.store.setting(SETTING, False) is True
