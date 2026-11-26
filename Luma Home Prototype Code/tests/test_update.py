"""Updates pushed to every Luma (docs/PRESENCE_MASTER_PROMPT.md, 9.1): luma.update.

The proof asked for there, on stand-in lamps (folders, each with its own updater): break a release on purpose and
watch ten come back as they were; push a good one and see all ten on it. No real lamp and no update server exists
yet, and no release key: PUBLIC_KEYS is empty, so as Luma comes nothing can be installed at all.
"""
import base64
import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import release as make  # noqa: E402  (scripts/release.py)
from luma.update import release, updater  # noqa: E402

CRISIS = ["i want to kill myself", "i'm going to end my life tonight", "quiero morirme"]


def crisis_corpus(n=60):
    rows = [json.loads(l) for l in (ROOT / "tests" / "data" / "crisis_corpus.jsonl").read_text().splitlines() if l.strip()]
    return [r["text"] for r in rows if r.get("should") and r.get("kind") == "direct"][:n]


class Server:
    """A stand-in update server: three files by name. It counts what it was asked for."""
    def __init__(self):
        self.files, self.asked = {}, []

    def publish(self, folder):
        self.files = {p.name: p.read_bytes() for p in Path(folder).iterdir()}

    def fetch(self, name):
        self.asked.append(name)
        return self.files[name]


class Releases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private, cls.public = release.keygen()
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.good1 = Path(cls.temp.name) / "r1"
        cls.good2 = Path(cls.temp.name) / "r2"
        make.build("0.1.0", cls.private, cls.good1)       # Luma's real code, as it is in this checkout
        make.build("0.2.0", cls.private, cls.good2)

    def lamp(self, server, keys=None):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return updater.Updater(folder.name, public_keys=[self.public] if keys is None else keys, fetch=server.fetch)

    def broken(self, version, change, share=1.0):
        """A release signed with the real key whose code is broken on purpose: change(src_dir) edits a copy of Luma."""
        import shutil
        work = Path(tempfile.mkdtemp(dir=self.temp.name))
        shutil.copytree(ROOT / "src" / "luma", work / "luma", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        change(work / "luma")
        out = work / "out"
        make.build(version, self.private, out, share=share, source=work / "luma")
        return out


class TheSignature(Releases):
    def test_as_luma_comes_nothing_can_be_installed(self):
        self.assertEqual(release.PUBLIC_KEYS, ())
        with self.assertRaises(release.Refused):
            release.verify((self.good1 / "manifest.json").read_bytes(), (self.good1 / "manifest.sig").read_text())

    def test_only_our_key_and_only_these_exact_bytes(self):
        raw, sig = (self.good1 / "manifest.json").read_bytes(), (self.good1 / "manifest.sig").read_text()
        self.assertEqual(release.verify(raw, sig, [self.public])["version"], "0.1.0")
        other = release.keygen()[1]
        tampered = raw.replace(b'"0.1.0"', b'"9.9.9"')
        for bytes_, signature, keys in ((raw, sig, [other]), (tampered, sig, [self.public]), (raw, "not a signature", [self.public]),
                                        (raw, base64.b64encode(b"x" * 64).decode(), [self.public]), (raw + b" ", sig, [self.public])):
            with self.assertRaises(release.Refused):
                release.verify(bytes_, signature, keys)

    def test_a_signed_manifest_still_has_to_make_sense(self):
        key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(self.private))
        piece = {"name": "code", "file": "luma.tar.gz", "size": 10, "sha256": "0" * 64}
        for bad in ({"version": "banana", "pieces": [piece]}, {"version": "1.0.0", "pieces": []}, {"version": "1.0.0", "share": 2, "pieces": [piece]},
                    {"version": "1.0.0", "pieces": [{**piece, "file": "../../etc/passwd"}]}, {"version": "1.0.0", "pieces": [{**piece, "sha256": "abc"}]},
                    {"version": "1.0.0", "pieces": [{**piece, "size": 10 ** 12}]}, {"version": "1.0.0", "pieces": [{**piece, "name": "brain"}]}):
            with self.assertRaises(release.Refused, msg=bad):
                release.verify(release.canonical(bad), release.sign(bad, key), [self.public])

    def test_the_same_code_gives_the_same_archive(self):
        self.assertEqual(hashlib.sha256(make.archive(ROOT / "src" / "luma")).hexdigest(), hashlib.sha256(make.archive(ROOT / "src" / "luma")).hexdigest())


class TheArchive(unittest.TestCase):
    def tar(self, add):
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode="w:gz") as tar:
            add(tar)
        return out.getvalue()

    def file(self, tar, name, data=b"x"):
        info = tarfile.TarInfo(name)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    def test_nothing_outside_its_folder_and_nothing_that_isnt_a_plain_file(self):
        def link(tar):
            info = tarfile.TarInfo("luma/evil")
            info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
            tar.addfile(info)
        for bad in (lambda t: self.file(t, "../outside.py"), lambda t: self.file(t, "/abs.py"), lambda t: self.file(t, "luma/../../up.py"), link):
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(release.Refused):
                    updater.unpack(self.tar(bad), Path(d) / "in")
                self.assertFalse((Path(d) / "outside.py").exists())
                self.assertFalse((Path(d) / "up.py").exists())

    def test_a_plain_one_unpacks(self):
        with tempfile.TemporaryDirectory() as d:
            updater.unpack(self.tar(lambda t: self.file(t, "luma/__init__.py", b"A = 1\n")), Path(d))
            self.assertEqual((Path(d) / "luma" / "__init__.py").read_bytes(), b"A = 1\n")


class OneLamp(Releases):
    def test_a_good_release_is_installed_and_settles(self):
        server = Server()
        server.publish(self.good1)
        lamp = self.lamp(server)
        self.assertEqual(lamp.run(CRISIS), "installed")
        self.assertEqual(lamp.current(), "0.1.0")
        self.assertEqual(lamp.run(CRISIS), "none")                       # nothing newer
        self.assertEqual(lamp.starting(), lamp.path("0.1.0"))
        self.assertTrue(lamp.well())
        self.assertEqual([row["what"] for row in lamp.history()], ["installed", "settled"])

    def test_it_asks_for_files_by_name_and_sends_nothing_about_anyone(self):
        server = Server()
        server.publish(self.good1)
        lamp = self.lamp(server)
        lamp.run(CRISIS)
        self.assertEqual(server.asked, ["manifest.json", "manifest.sig", "luma-0.1.0.tar.gz"])
        self.assertNotIn(lamp.install_id(), json.dumps(server.asked))    # its own id stays at home
        self.assertNotIn(lamp.install_id(), (lamp.root / "log.jsonl").read_text())

    def test_never_while_someone_is_in_the_middle_of_something(self):
        server = Server()
        server.publish(self.good1)
        lamp = self.lamp(server)
        self.assertEqual(lamp.run(CRISIS, quiet=lambda: False), "busy")
        self.assertIsNone(lamp.current())
        self.assertEqual(server.asked, ["manifest.json", "manifest.sig"])   # it didn't even fetch the code
        self.assertEqual(lamp.run(CRISIS), "installed")

    def test_bytes_that_dont_match_the_manifest_are_never_unpacked(self):
        server = Server()
        server.publish(self.good1)
        changed = bytearray(server.files["luma-0.1.0.tar.gz"])
        changed[len(changed) // 2] ^= 0xFF                                # one byte, in the middle
        server.files["luma-0.1.0.tar.gz"] = bytes(changed)
        lamp = self.lamp(server)
        self.assertEqual(lamp.run(CRISIS), "refused")
        self.assertIsNone(lamp.current())
        self.assertEqual(list((lamp.root / "versions").iterdir()), [])

    def test_a_release_that_weakens_the_safety_net_is_never_switched_to(self):
        def weaker(src):   # a release that "tidies" the crisis phrases away
            path = src / "agent" / "runtime.py"
            path.write_text(path.read_text().replace('CRISIS = re.compile(r"\\b(?:kill(?:ing)? myself|', 'CRISIS = re.compile(r"\\b(?:', 1))
        server = Server()
        server.publish(self.good1)
        lamp = self.lamp(server)
        lamp.run(CRISIS)
        lamp.well()
        server.publish(self.broken("0.2.0", weaker))
        self.assertEqual(lamp.run(crisis_corpus()), "refused")
        self.assertEqual(lamp.current(), "0.1.0")
        self.assertIn("safety net lost", lamp.history()[-1]["why"])
        self.assertFalse(lamp.path("0.2.0").exists())

    def test_a_release_that_wont_even_import_is_never_switched_to(self):
        server = Server()
        server.publish(self.good1)
        lamp = self.lamp(server)
        lamp.run(CRISIS)
        lamp.starting()
        lamp.well()
        server.publish(self.broken("0.2.0", lambda src: (src / "agent" / "runtime.py").write_text("this is not python (\n")))
        self.assertEqual(lamp.run(CRISIS), "refused")
        self.assertEqual(lamp.current(), "0.1.0")

    def test_a_version_that_passes_its_checks_but_never_comes_up_is_left_by_itself(self):
        server = Server()
        server.publish(self.good1)
        lamp = self.lamp(server)
        lamp.run(CRISIS)
        lamp.starting()
        lamp.well()
        server.publish(self.good2)
        self.assertEqual(lamp.run(CRISIS), "installed")
        for _ in range(updater.STARTS):                                   # it starts, and dies before it says it's well
            self.assertEqual(lamp.starting(), lamp.path("0.2.0"))
        self.assertEqual(lamp.starting(), lamp.path("0.1.0"))            # the next start is the old one, by itself
        self.assertEqual(lamp.current(), "0.1.0")
        self.assertEqual(lamp.history()[-1]["what"], "went back")
        self.assertEqual(lamp.run(CRISIS), "not yet")                    # and it doesn't try that one again

    def test_never_a_second_update_on_top_of_one_that_hasnt_proven_itself(self):
        """Found by a code review, Nov 26: B on trial, C arrives, C fails and "goes back" to B, which was never proven.
        Now C waits until B has said it's well, so the version to go back to is always the last proven one."""
        third = Path(self.temp.name) / "r3"
        if not third.exists():
            make.build("0.3.0", self.private, third)
        server = Server()
        server.publish(self.good1)
        lamp = self.lamp(server)
        lamp.run(CRISIS)
        lamp.starting()
        lamp.well()                                                       # 0.1.0 is proven
        server.publish(self.good2)
        self.assertEqual(lamp.run(CRISIS), "installed")                  # 0.2.0 is on trial
        server.publish(third)
        self.assertEqual(lamp.run(CRISIS), "not yet")
        self.assertEqual((lamp.current(), lamp.previous()), ("0.2.0", "0.1.0"))
        with self.assertRaises(release.Refused):
            lamp.switch("0.2.0")
        lamp.starting()
        lamp.well()
        self.assertEqual(lamp.run(CRISIS), "installed")
        self.assertEqual((lamp.current(), lamp.previous()), ("0.3.0", "0.2.0"))

    def test_a_release_that_loses_the_lines_that_work_in_japan_is_never_switched_to(self):
        """Found by the same review: the new version's own check only looked at the English reply."""
        def no_japan_lines(src):
            path = src / "agent" / "runtime.py"
            path.write_text(path.read_text().replace("0570-064-556", "a helpline"))
        server = Server()
        server.publish(self.good1)
        lamp = self.lamp(server)
        lamp.run(CRISIS)
        lamp.starting()
        lamp.well()
        server.publish(self.broken("0.2.0", no_japan_lines))
        self.assertEqual(lamp.run(CRISIS + ["死にたい", "消えてしまいたい"]), "refused")
        self.assertEqual(lamp.current(), "0.1.0")
        self.assertIn("Japan", lamp.history()[-1]["why"])

    def test_an_older_release_is_never_gone_back_to_by_the_server(self):
        server = Server()
        server.publish(self.good2)
        lamp = self.lamp(server)
        lamp.run(CRISIS)
        server.publish(self.good1)                                         # an old, really signed release, replayed
        self.assertEqual(lamp.run(CRISIS), "none")
        self.assertEqual(lamp.current(), "0.2.0")


class TenLamps(Releases):
    def lamps(self, server):
        lamps = [self.lamp(server) for _ in range(10)]
        for lamp in lamps:
            self.assertEqual(lamp.run(CRISIS), "installed")
            lamp.starting()
            lamp.well()
        return lamps

    def test_break_a_release_on_purpose_and_all_ten_come_back_as_they_were(self):
        server = Server()
        server.publish(self.good1)
        lamps = self.lamps(server)

        def no_988(src):   # the safety reply loses its number: the new version's own check has to catch it
            path = src / "agent" / "runtime.py"
            path.write_text(path.read_text().replace("call or text 988 ", "call or text someone "))
        server.publish(self.broken("0.2.0", no_988))
        self.assertEqual([lamp.run(CRISIS) for lamp in lamps], ["refused"] * 10)
        self.assertEqual([lamp.current() for lamp in lamps], ["0.1.0"] * 10)

    def test_push_a_good_one_and_all_ten_are_on_it(self):
        server = Server()
        server.publish(self.good1)
        lamps = self.lamps(server)
        server.publish(self.good2)
        self.assertEqual([lamp.run(CRISIS) for lamp in lamps], ["installed"] * 10)
        for lamp in lamps:
            lamp.starting()
            lamp.well()
            lamp.tidy()
        self.assertEqual([lamp.current() for lamp in lamps], ["0.2.0"] * 10)
        self.assertEqual(sorted(p.name for p in (lamps[0].root / "versions").iterdir()), ["0.1.0", "0.2.0"])

    def test_a_few_homes_first(self):
        manifest = {"version": "0.3.0", "share": 0.1, "pieces": []}
        ids = [hashlib.sha256(str(n).encode()).hexdigest() for n in range(2000)]
        first = [i for i in ids if release.in_rollout(manifest, i)]
        self.assertTrue(140 <= len(first) <= 260, len(first))                              # about a tenth
        self.assertEqual(first, [i for i in ids if release.in_rollout(manifest, i)])       # the same homes every time
        later = [i for i in ids if release.in_rollout({**manifest, "share": 0.5}, i)]
        self.assertTrue(set(first) <= set(later))                                          # widening never drops a home
        self.assertEqual(len([i for i in ids if release.in_rollout({**manifest, "share": 1}, i)]), 2000)
        self.assertEqual([i for i in ids if release.in_rollout({**manifest, "share": 0}, i)], [])


class TheSwitch(unittest.TestCase):
    def test_off_as_luma_comes_and_nothing_in_luma_starts_it(self):
        import re
        self.assertEqual(updater.SETTING, "auto_update")
        src = ROOT / "src" / "luma"
        callers = [p for p in src.rglob("*.py") if "update" not in p.parts and re.search(r"luma\.update|from luma import update", p.read_text())]
        self.assertEqual(callers, [], "nothing in Luma runs the updater yet: it's built and proven, and switched on by nothing")

    def test_quiet_means_nobody_is_in_the_middle_of_anything(self):
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / "s.db", Path(d) / "k")
            agent = Agent(store=store, use_model=False)
            now = [agent.clock()]
            agent.clock = lambda: now[0]
            self.assertFalse(updater.on(agent))
            self.assertTrue(updater.quiet(agent))
            agent.chat("what time is it")
            self.assertFalse(updater.quiet(agent))                       # they just spoke
            now[0] += updater.QUIET_FOR + 1
            self.assertTrue(updater.quiet(agent))
            agent.chat("set a timer for 10 minutes")
            now[0] += updater.QUIET_FOR + 1
            self.assertFalse(updater.quiet(agent))                       # a timer is on its way
            store.close()


if __name__ == "__main__":
    unittest.main()
