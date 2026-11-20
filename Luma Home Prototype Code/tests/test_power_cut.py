"""The power goes out while Luma is writing a memory.

A second process keeps memories as fast as it can and says each one's id only after the store has said it's kept. It
is killed outright (no goodbye, no flush: what a pulled plug does to a process) at a different moment each round.
Then the store is opened again, the way the lamp would at the next start:
- the database's own check passes;
- every memory the writer was told was kept is there, whole and readable;
- nothing half-written is left behind (no key without a record, no record that won't open);
- and Luma can keep writing to it and find what's in it.

A pulled plug also cuts the disk's own cache, which a killed process can't imitate; that part needs the real device.
"""
from __future__ import annotations

import os
import random
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from luma.memory.store import Store  # noqa: E402

WRITER = """
import sys
sys.path.insert(0, sys.argv[3])
from luma.memory.store import Store
store = Store(sys.argv[1], sys.argv[2])
start = int(sys.argv[4])
i = 0
while True:
    kept = store.put("memory", {"text": f"round {start} line {i}: my cousin's dog is called Biscuit number {i}, " + "and so on " * 20, "source": "said"})
    print(kept["id"], flush=True)   # only after the store said it was kept
    if i % 7 == 0:
        store.set_setting("last_line", i)
    if i % 11 == 0 and i:
        store.delete("memory", kept["id"])
        print("-" + kept["id"], flush=True)
    i += 1
"""


class PowerCut(unittest.TestCase):
    ROUNDS = 8

    def test_killed_mid_write_again_and_again_nothing_confirmed_is_lost(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        db, key = Path(temp.name) / "state.db", Path(temp.name) / "state.key"
        Store(db, key).close()
        rng = random.Random(20261120)
        confirmed, deleted = set(), set()
        for round_ in range(self.ROUNDS):
            writer = subprocess.Popen([sys.executable, "-c", WRITER, str(db), str(key), str(ROOT / "src"), str(round_)],
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            wanted = rng.randint(15, 140)
            try:
                for _ in range(wanted):
                    line = writer.stdout.readline().strip()
                    if not line:
                        break
                    (deleted if line.startswith("-") else confirmed).add(line.lstrip("-"))
            finally:
                os.kill(writer.pid, signal.SIGKILL)   # mid-write, as often as not
                writer.wait(10)
                writer.stdout.close()
            store = Store(db, key)
            try:
                health = store.health()
                self.assertTrue(health.get("ok"), f"round {round_}: {health}")
                there = {m["id"]: m for m in store.all("memory", 100000)}
                missing = (confirmed - deleted) - set(there)
                self.assertEqual(missing, set(), f"round {round_}: {len(missing)} confirmed memories gone")
                self.assertTrue(all(isinstance(m.get("text"), str) and ("Biscuit" in m["text"] or "after power cut" in m["text"]) for m in there.values()), "every memory opens and reads")
                self.assertEqual(deleted & set(there), set(), "what was confirmed forgotten stays forgotten")
                extra = {i for i in there if i not in confirmed and "after power cut" not in there[i]["text"]}
                self.assertLessEqual(len(extra), 1, "at most the one being written when the power went")
                confirmed |= extra   # if it's there and whole, it stays
                found = store.search("what's my cousin's dog called", limit=3)
                self.assertTrue(found["memories"] or found["related"], "and it can be searched")
                store.put("memory", {"text": f"after power cut {round_}: still here"})
            finally:
                store.close()
        final = Store(db, key)
        try:
            self.assertEqual(sum("after power cut" in m["text"] for m in final.all("memory", 100000)), self.ROUNDS)
            self.assertGreater(len(confirmed), 100)
        finally:
            final.close()


if __name__ == "__main__":
    unittest.main()
