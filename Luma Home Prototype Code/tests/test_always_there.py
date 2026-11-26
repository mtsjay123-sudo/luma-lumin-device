"""Running all day and all night (docs/PRESENCE_MASTER_PROMPT.md, section 9): the three lines of that table that can
be proven without a lamp. It restarts at a bounded rate (the service file, read here, never run); its memory stays
flat (a short soak: the long one is `scripts/soak.py`, and 72 real hours need the lamp); and a factory reset destroys
the key, so nothing kept can be read afterwards.
"""
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from luma.agent import who, yeses  # noqa: E402
from luma.agent.runtime import Agent  # noqa: E402
from luma.memory import reset  # noqa: E402
from luma.memory.store import Store  # noqa: E402


class TheService(unittest.TestCase):
    unit = (ROOT / "hardware" / "luma.service").read_text()

    def value(self, key):
        found = re.findall(rf"^{key}=(.+)$", self.unit, flags=re.M)
        self.assertEqual(len(found), 1, key)
        return found[0].strip()

    def test_it_comes_back_after_a_crash_at_a_bounded_rate(self):
        self.assertEqual(self.value("Restart"), "on-failure")
        self.assertGreaterEqual(int(self.value("RestartSec")), 2)
        burst, window = int(self.value("StartLimitBurst")), int(self.value("StartLimitIntervalSec"))
        self.assertTrue(1 <= burst <= 10 and window >= 60)                  # it never spins: a few tries, then it stays down
        self.assertLess(self.unit.index("StartLimitBurst"), self.unit.index("[Service]"))   # where systemd reads it

    def test_it_starts_luma_the_way_luma_is_started_and_keeps_its_state_where_luma_looks(self):
        self.assertRegex(self.value("ExecStart"), r"/luma serve\b")
        self.assertIn("LUMA_STATE_DIR=", self.unit)
        self.assertIn('os.environ.get("LUMA_STATE_DIR"', (ROOT / "src" / "luma" / "config.py").read_text())
        self.assertIn("'serve'", (ROOT / "src" / "luma" / "cli.py").read_text())

    def test_it_can_write_its_own_state_and_nothing_else(self):
        for line in ("NoNewPrivileges=yes", "ProtectSystem=strict", "ProtectHome=yes", "PrivateTmp=yes"):
            self.assertIn(line, self.unit)
        self.assertEqual(self.value("ReadWritePaths"), "/var/lib/luma")
        self.assertNotEqual(self.value("User"), "root")


class MemoryStaysFlat(unittest.TestCase):
    def test_a_short_soak(self):
        import soak
        result = soak.soak(240)
        self.assertEqual(result["turns_that_raised"], 0)
        self.assertLess(result["grew_after_warm_up_mb"], 20, result)       # measured on 1,500 turns: 0.1 MB


class AFactoryReset(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "state"
        self.home.mkdir()
        self.store = Store(self.home / "s.db", self.home / "k")
        self.agent = Agent(store=self.store, use_model=False)
        self.agent.chat("my sister Priya lives in Tampa")
        self.store.put("memory", {"text": "They are afraid of the dentist.", "kind": "fact"})
        yeses.save_signin(self.agent, "chase.com", "jay01", "correct-horse-battery", "my bank")
        who.choose(self.agent, "blue kettle tuesday")
        (self.home / "browser-profile").mkdir()
        (self.home / "browser-profile" / "Cookies").write_bytes(b"session=logged-in-to-everything")
        (self.home / "files").mkdir()
        (self.home / "files" / "letter.txt").write_text("Dear landlord")
        (self.home / "cli.json").write_text("{}")

    def test_the_key_goes_first_and_nothing_kept_can_be_read_afterwards(self):
        self.store.db.commit()
        taken = Path(self.temp.name) / "copy-somebody-took.db"             # a copy of the database from before the reset
        shutil.copy(self.home / "s.db", taken)
        key_before = (self.home / "k").read_bytes()
        self.assertGreater(len(self.store.all("memory", 100)), 0)

        gone = reset.factory_reset(self.store)

        self.assertEqual(gone[0], "the key")
        self.assertFalse((self.home / "k").exists())
        self.assertFalse((self.home / "s.db").exists())
        for name in reset.THEIRS:
            self.assertFalse((self.home / name).exists(), name)
        raw = taken.read_bytes()
        for plain in (b"Priya", b"Tampa", b"dentist", b"correct-horse", b"kettle", b"jay01"):
            self.assertNotIn(plain, raw)                                    # it was sealed all along
        # The copy somebody took, put back without the key: Luma refuses it. With a new key: it can't be opened.
        attempt = Path(self.temp.name) / "attempt"
        attempt.mkdir()
        shutil.copy(taken, attempt / "s.db")
        with self.assertRaises(RuntimeError):
            Store(attempt / "s.db", attempt / "k")
        (attempt / "k").write_bytes(__import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key())
        opened = Store(attempt / "s.db", attempt / "k")
        self.addCleanup(opened.close)
        with self.assertRaises(Exception):
            opened.all("memory", 100)
        with self.assertRaises(Exception):
            opened.all("signin", 100)
        self.assertNotEqual(key_before, (attempt / "k").read_bytes())

    def test_what_comes_up_next_is_a_luma_that_has_met_nobody(self):
        reset.factory_reset(self.store)
        fresh = Store(self.home / "s.db", self.home / "k")
        self.addCleanup(fresh.close)
        luma = Agent(store=fresh, use_model=False)
        self.assertEqual(fresh.all("memory", 100), [])
        self.assertEqual(yeses.view(luma)["signins"], [])
        self.assertFalse(who.enabled(luma))
        self.assertEqual(luma.transcripts["main"], [])

    def test_luma_own_code_and_models_are_not_theirs(self):
        (self.home / "models").mkdir()
        (self.home / "models" / "brain.gguf").write_bytes(b"not about anyone")
        reset.factory_reset(self.store)
        self.assertTrue((self.home / "models" / "brain.gguf").exists())

    def test_a_link_in_the_folder_is_removed_never_followed(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("not Luma's to delete")
        shutil.rmtree(self.home / "files")
        (self.home / "files").symlink_to(outside, target_is_directory=True)
        reset.factory_reset(self.store)
        self.assertFalse((self.home / "files").exists())
        self.assertTrue((outside / "keep.txt").exists())


if __name__ == "__main__":
    unittest.main()
