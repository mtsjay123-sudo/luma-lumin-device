"""A backup the owner keeps, and getting a Luma back from it (luma.memory.backup; docs/GAME_PLAN.md, E3)."""
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory import backup, reset
from luma.memory.store import Store

PASS = "four quiet green lamps"


class Home(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.store = Store(self.home / "s.db", self.home / "k")
        self.agent = Agent(store=self.store, use_model=False)
        self.agent.chat("my sister's name is Dana")
        self.agent.chat("remember that the spare key is under the blue pot")
        self.store.set_setting("volume", 4)
        self.file = Path(self.temp.name) / "out" / "luma.backup"

    def tearDown(self):
        try:
            self.store.close()
        except Exception:
            pass

    def fresh(self, name="new"):
        return Path(self.temp.name) / name / "s.db", Path(self.temp.name) / name / "k"


class MakingOne(Home):
    def test_it_is_one_file_that_says_nothing_without_the_passphrase(self):
        out = backup.make(self.store, PASS, self.file)
        raw = self.file.read_bytes()
        self.assertTrue(raw.startswith(backup.MAGIC))
        for word in (b"Dana", b"blue pot", b"spare key", self.store.key_path.read_bytes().strip()):
            self.assertNotIn(word, raw)
        self.assertEqual(oct(self.file.stat().st_mode & 0o777), "0o600")
        self.assertGreater(out["records"], 0)
        self.assertIn("the files you gave Luma", out["not_in_it"])            # nobody thinks those came along
        for wrong in ("four quiet green lamp", "", "FOUR QUIET GREEN LAMPS"):
            with self.assertRaises(backup.Refused):
                backup.look(self.file, wrong)
        self.assertEqual(backup.look(self.file, PASS)["records"], out["records"])

    def test_a_weak_passphrase_is_refused_and_an_older_backup_is_never_written_over(self):
        for weak in ("", "luma", "password", "aaaaaaaaaaaaaaaa", "cat dog pig"):
            with self.assertRaises(backup.Refused, msg=weak):
                backup.make(self.store, weak, self.file)
        self.assertFalse(self.file.exists())
        backup.make(self.store, PASS, self.file)
        with self.assertRaisesRegex(backup.Refused, "already a file"):
            backup.make(self.store, PASS, self.file)

    def test_luma_goes_on_working_while_it_is_made(self):
        backup.make(self.store, PASS, self.file)
        self.assertIn("Dana", self.agent.chat("what's my sister's name again?")["text"])
        self.assertTrue(self.store.health()["ok"])


class GettingItBack(Home):
    def test_a_new_luma_knows_what_the_old_one_knew(self):
        made = backup.make(self.store, PASS, self.file)
        db, key = self.fresh()
        out = backup.restore(self.file, PASS, db, key)
        self.assertEqual((out["ok"], out["records"]), (True, made["records"]))
        self.assertEqual(oct(key.stat().st_mode & 0o777), "0o600")
        store = Store(db, key)
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        self.assertIn("Dana", agent.chat("what's my sister's name again?")["text"])
        self.assertEqual(store.setting("volume"), 4)
        self.assertTrue(store.health()["ok"])

    def test_after_everything_is_erased_the_backup_brings_it_back_on_the_same_lamp(self):
        backup.make(self.store, PASS, self.file)
        db, key = self.store.db_path, self.store.key_path
        reset.factory_reset(self.store)
        self.assertFalse(key.exists())
        backup.restore(self.file, PASS, db, key)
        self.store = Store(db, key)
        self.assertIn("Dana", Agent(store=self.store, use_model=False).chat("what's my sister's name again?")["text"])

    def test_never_onto_a_home_that_is_there(self):
        backup.make(self.store, PASS, self.file)
        with self.assertRaisesRegex(backup.Refused, "already has a home"):
            backup.restore(self.file, PASS, self.store.db_path, self.store.key_path)
        self.assertIn("Dana", self.agent.chat("what's my sister's name again?")["text"])      # and nothing was touched

    def test_the_wrong_passphrase_or_a_changed_file_restores_nothing(self):
        backup.make(self.store, PASS, self.file)
        db, key = self.fresh()
        with self.assertRaises(backup.Refused):
            backup.restore(self.file, "four quiet green lamp", db, key)
        raw = bytearray(self.file.read_bytes())
        raw[len(raw) // 2] ^= 1
        changed = self.file.with_name("changed.backup")
        changed.write_bytes(bytes(raw))
        with self.assertRaises(backup.Refused):
            backup.restore(changed, PASS, db, key)
        with self.assertRaisesRegex(backup.Refused, "isn't a Luma backup"):
            other = self.file.with_name("notes.txt"); other.write_text("hello"); backup.restore(other, PASS, db, key)
        self.assertFalse(key.exists())
        self.assertFalse(db.exists())

    def test_what_was_forgotten_before_the_backup_is_not_in_it(self):
        self.agent.chat("forget about the spare key")
        backup.make(self.store, PASS, self.file)
        db, key = self.fresh()
        backup.restore(self.file, PASS, db, key)
        store = Store(db, key)
        self.addCleanup(store.close)
        self.assertEqual([m for m in store.memories() if "blue pot" in str(m)], [])


if __name__ == "__main__":
    unittest.main()
