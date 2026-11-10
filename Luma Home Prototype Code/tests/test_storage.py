"""Storage, like the storage page on a phone: what Luma keeps, how much room it takes, what happens when it's full,
and how room comes back. Everything is on the device; the cloud is only ever an offer of more room, never a brain."""
import json
import shutil
import subprocess
import tempfile
import threading
import unittest
from collections import namedtuple
from pathlib import Path

from luma.agent import memory_folder
from luma.agent.runtime import Agent
from luma.memory import storage
from luma.memory.store import Store

NOW = 1793116800.0
DAY = 86400
MB = 2 ** 20
Disk = namedtuple("Disk", "total used free")


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.now = NOW
        self.agent = Agent(store=self.store, use_model=False, now=lambda: self.now)
        self.disk = Disk(64 * 2 ** 30, 20 * 2 ** 30, 44 * 2 ** 30)
        self._real, self._low = storage.disk_usage, storage.LOW
        storage.disk_usage = lambda path: self.disk

    def tearDown(self):
        storage.disk_usage, storage.LOW = self._real, self._low
        self.store.close()
        self.temp.cleanup()

    def remember(self, text, days_ago=0):
        return self.store.put("memory", {"text": text, "source": "explicit_user_request", "created": NOW - days_ago * DAY})

    def fill(self, n=40, size=20000):
        """Old chats: the heavy thing a person really has."""
        for i in range(n):
            self.store.put("chat", {"thread": f"t{i}", "title": f"Chat {i}", "log": [{"role": "user", "text": "x" * size, "at": NOW - 90 * DAY}]})

    def cap(self, extra):
        """The owner's own cap, set a little above what's used now."""
        self.store.set_setting(storage.CAP, storage.room(self.agent)["used"] + extra)

    # -- how much room -------------------------------------------------------------------------------------------------
    def test_room_is_the_device_less_a_reserve(self):
        room = storage.room(self.agent)
        self.assertEqual(room["state"], "ok")
        self.assertEqual(room["left"], self.disk.free - room["reserve"])
        self.assertEqual(room["limit"], room["used"] + room["left"])
        self.assertGreater(room["used"], 0)
        self.assertIsNone(room["cap"])

    def test_a_nearly_full_device_and_a_full_one(self):
        self.disk = Disk(64 * 2 ** 30, 64 * 2 ** 30 - 300 * MB, 300 * MB)
        self.assertEqual(storage.room(self.agent)["state"], "nearly")
        self.disk = Disk(64 * 2 ** 30, 64 * 2 ** 30 - 100 * MB, 100 * MB)   # under the reserve: the device needs that to keep working
        room = storage.room(self.agent)
        self.assertEqual((room["state"], room["left"]), ("full", 0))

    def test_the_owner_can_cap_what_luma_uses(self):
        self.fill()
        used = storage.room(self.agent)["used"]
        storage.set_cap(self.agent, 1)                       # "let Luma use up to 1 GB"
        room = storage.room(self.agent)
        self.assertEqual((room["cap"], room["limit"], room["state"]), (2 ** 30, 2 ** 30, "ok"))
        self.store.set_setting(storage.CAP, used + 1000)
        self.assertEqual(storage.room(self.agent)["state"], "nearly")
        self.store.set_setting(storage.CAP, used - 1)
        self.assertEqual(storage.room(self.agent)["state"], "full")
        storage.set_cap(self.agent, None)
        self.assertEqual(storage.room(self.agent)["state"], "ok")
        for bad in (0, -1, "lots", 0.001):
            with self.assertRaises(ValueError):
                storage.set_cap(self.agent, bad)

    def test_what_is_using_the_room_by_kind(self):
        for i in range(30):
            self.remember(f"Your cousin number {i} lives in Tulsa")
        self.fill(5)
        self.store.put("diary", {"text": "A quiet day. " * 40, "day": "2026-11-01"})
        files = self.agent.files_dir
        files.mkdir(parents=True, exist_ok=True)
        (files / "abc123-plan.pdf").write_bytes(b"p" * 50000)
        self.store.put("file", {"name": "plan.pdf", "path": str(files / "abc123-plan.pdf"), "kind": "pdf", "title": "Plan", "created": NOW}, "abc123")
        from luma.control import today
        today._SIZES.clear()
        use = storage.usage(self.agent)
        kinds = {k["key"]: k for k in use["kinds"]}
        self.assertEqual(kinds["memories"]["count"], 30)
        self.assertEqual(kinds["chats"]["count"], 5)
        self.assertGreater(kinds["chats"]["bytes"], 5 * 20000)
        self.assertGreaterEqual(kinds["files"]["bytes"], 50000)
        self.assertEqual(kinds["diary"]["count"], 1)
        self.assertEqual(sum(k["bytes"] for k in use["kinds"]), use["bytes"])
        self.assertEqual(use["bytes"], storage.room(self.agent)["used"])
        self.assertEqual([k["key"] for k in use["kinds"]], [k["key"] for k in sorted(use["kinds"], key=lambda k: -k["bytes"])])  # biggest first

    def test_the_quota_says_it_in_one_place(self):
        q = self.agent.memory_quota()
        self.assertEqual((q["full"], q["state"], q["limit"]), (False, "ok", None))   # no count to buy past: the limit is room
        self.assertEqual(q["left"], storage.room(self.agent)["left"])
        self.cap(-1)
        self.assertTrue(self.agent.memory_quota()["full"])

    # -- full means full ---------------------------------------------------------------------------------------------------
    def test_when_its_full_nothing_new_is_kept_and_luma_says_so(self):
        self.cap(-1)
        self.assertEqual(self.agent.remember_fact("Your keys are on the hook"), "full")
        self.assertEqual(self.store.count("memory"), 0)
        said = self.agent.chat("remember that my sister's birthday is june 3")
        reply = said.get("text") or said.get("summary")
        self.assertIn("out of room", reply)
        self.assertTrue(said.get("memory_full"))
        self.assertNotIn("Got it", reply)
        self.assertEqual(self.store.count("memory"), 0)

    def test_an_answer_luma_asked_for_isnt_claimed_as_kept(self):
        self.agent.chat("what's my sister's name?")
        self.cap(-1)
        said = self.agent.chat("dana")
        self.assertIn("out of room", said["text"])
        self.assertNotIn("I won't forget", said["text"])

    def test_a_full_device_still_talks_and_still_cares(self):
        self.cap(-1)
        before = self.store.count("checkin")
        said = self.agent.chat("my dog died this morning")
        self.assertTrue(said["text"])
        self.assertNotIn("out of room", said["text"])            # not the moment to bring it up
        self.assertGreater(self.store.count("checkin"), before)   # the check-in for tomorrow is never what gets cut
        self.assertEqual(self.store.count("memory"), 0)

    def test_nothing_is_made_when_theres_no_room_for_it(self):
        self.cap(-1)
        with self.assertRaises(ValueError) as caught:
            self.agent._create_doc({"title": "Plan", "format": "pdf", "sections": [{"heading": "One", "paragraphs": ["Hello."]}]})
        self.assertIn("out of room", str(caught.exception))

    # -- getting room back -------------------------------------------------------------------------------------------------
    def test_deleting_gives_the_room_back_for_real(self):
        storage.LOW = 100_000     # "almost out" scaled down to this test's 800 KB of chats, so it doesn't need 200 MB of them
        self.fill()
        self.cap(2000)
        self.assertEqual(storage.room(self.agent)["state"], "nearly")
        size = self.store.file_bytes()
        cleaned = memory_folder.clean(self.agent, "old_chats")
        self.assertGreater(cleaned["freed_bytes"], 40 * 20000 * 0.9)
        self.assertLess(self.store.file_bytes(), size - 40 * 20000 * 0.9)   # the file on the device is smaller, not just emptier
        room = storage.room(self.agent)
        self.assertEqual(room["state"], "ok")
        self.assertGreater(room["left"], 40 * 20000 * 0.9)
        row = self.agent.remember_fact("Your keys are on the hook")
        self.assertIsInstance(row, dict)

    def test_forgetting_memories_gives_room_back_too(self):
        for i in range(400):
            self.remember(f"Your note number {i} says " + "remember the milk and the long drive north " * 6, days_ago=200)
        size = self.store.file_bytes()
        gone = memory_folder.forget(self.agent, older_than_days=182)
        self.assertEqual(gone["forgotten"], 400)
        self.assertLess(self.store.file_bytes(), size - 100000)

    def test_one_thing_at_a_time(self):
        self.fill(3)
        files = self.agent.files_dir
        files.mkdir(parents=True, exist_ok=True)
        (files / "abc123-big.pdf").write_bytes(b"p" * 90000)
        self.store.put("file", {"name": "big.pdf", "path": str(files / "abc123-big.pdf"), "kind": "pdf", "title": "Big plan", "created": NOW}, "abc123")
        from luma.control import today
        today._SIZES.clear()
        biggest = storage.biggest(self.agent)
        self.assertEqual((biggest[0]["kind"], biggest[0]["title"]), ("file", "Big plan"))
        self.assertGreaterEqual(biggest[0]["bytes"], 90000)
        self.assertEqual({b["kind"] for b in biggest}, {"file", "chat"})
        out = storage.remove(self.agent, "file", "abc123")
        self.assertGreaterEqual(out["freed_bytes"], 90000)
        self.assertFalse((files / "abc123-big.pdf").exists())
        self.assertIsNone(self.store.get("file", "abc123"))
        chat = next(b for b in storage.biggest(self.agent) if b["kind"] == "chat")
        storage.remove(self.agent, "chat", chat["id"])
        self.assertEqual(sum(1 for b in storage.biggest(self.agent) if b["kind"] == "chat"), 2)
        with self.assertRaises(ValueError):
            storage.remove(self.agent, "memory", "nope")      # memories go through forget, which forgets what was built from them too

    # -- Luma says it once, and never at a hard moment ----------------------------------------------------------------------
    def test_luma_says_its_nearly_full_once(self):
        self.fill()
        self.cap(2000)
        notice = self.agent._storage_notice(NOW, quiet=False)
        self.assertEqual(notice["type"], "notice")
        self.assertIn("almost out of room", notice["text"])
        self.assertNotIn("Plus", notice["text"])                  # news, never a pitch
        self.assertIsNone(self.agent._storage_notice(NOW + 60, quiet=False))
        self.cap(-1)
        full = self.agent._storage_notice(NOW + 120, quiet=False)
        self.assertIn("out of room", full["text"])
        self.assertIsNone(self.agent._storage_notice(NOW + 180, quiet=False))
        memory_folder.clean(self.agent, "old_chats")
        self.store.set_setting(storage.CAP, None)
        self.assertIsNone(self.agent._storage_notice(NOW + 240, quiet=False))
        self.fill()
        self.cap(2000)
        self.assertIsNotNone(self.agent._storage_notice(NOW + 300, quiet=False))   # it filled up again: that's news again

    def test_never_while_theyre_hurting_and_never_to_a_child(self):
        self.fill()
        self.cap(2000)
        self.agent.history.append({"role": "user", "content": "my mom died last night"})
        self.assertIsNone(self.agent._storage_notice(NOW, quiet=False))
        self.agent.history.clear()
        self.agent.set_mode("kids")
        self.assertIsNone(self.agent._storage_notice(NOW, quiet=False))
        self.agent.set_mode("friend")
        self.assertIsNotNone(self.agent._storage_notice(NOW, quiet=False))

    def test_asking_about_it_gets_the_truth_and_no_shop(self):
        said = self.agent._do_intent("luma_plus", "my memory is full, can i buy more", None)["text"]
        self.assertIn("this device", said)
        self.assertIn("Make room", said)
        self.assertNotIn("Luma Cloud", said)                      # more room in the cloud isn't open yet, so it isn't offered
        self.store.set_setting("luma_cloud_account", {"plan": "free", "storage": {"available": True}})
        self.agent.cloud.signed_in = lambda: True
        offered = self.agent._do_intent("luma_plus", "my memory is full, can i buy more", None)["text"]
        self.assertIn("Luma Cloud", offered)
        self.assertIn("your yes", offered)

    # -- the screen -----------------------------------------------------------------------------------------------------------
    def test_one_call_for_the_storage_screen(self):
        self.fill(4)
        self.remember("Your sister's name is Dana")
        page = storage.summary(self.agent)
        for key in ("used", "limit", "left", "state", "kinds", "biggest", "options", "health", "more"):
            self.assertIn(key, page)
        self.assertTrue(page["health"]["ok"])
        self.assertIsNone(page["more"])
        self.assertTrue(any(o["key"] == "old_chats" for o in page["options"]))
        self.agent.set_mode("kids")
        self.assertEqual(storage.summary(self.agent), {"kids": True})


class TheDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_sizes_by_kind(self):
        for i in range(10):
            self.store.put("memory", {"text": f"Your friend {i} likes tea", "created": NOW})
        self.store.put("chat", {"thread": "main", "log": [{"role": "user", "text": "y" * 5000}]})
        sizes = self.store.sizes()
        self.assertEqual(sizes["memory"]["count"], 10)
        self.assertGreater(sizes["chat"]["bytes"], 5000)
        self.assertGreater(sizes["memory"]["bytes"], 10 * 20)

    def test_compact_gives_space_back_and_keeps_everything_else(self):
        keep = self.store.put("memory", {"text": "Your sister's name is Dana", "created": NOW})
        rows = [self.store.put("chat", {"thread": f"t{i}", "log": [{"text": "z" * 30000}]}) for i in range(30)]
        big = self.store.file_bytes()
        for row in rows:
            self.store.delete("chat", row["id"])
        self.assertGreater(self.store.spare_bytes(), 30 * 30000 * 0.8)
        back = self.store.compact()
        self.assertGreater(back, 30 * 30000 * 0.8)
        self.assertLess(self.store.file_bytes(), big - 30 * 30000 * 0.8)
        self.assertEqual(self.store.get("memory", keep["id"])["text"], "Your sister's name is Dana")
        self.assertEqual(self.store.compact(), 0)                 # nothing spare: it doesn't rewrite the file for nothing
        self.assertEqual([m["text"] for m in self.store.search("sister", 3)["memories"]], ["Your sister's name is Dana"])

    def test_it_checks_itself(self):
        self.store.put("memory", {"text": "Your keys are on the hook", "created": NOW})
        health = self.store.health()
        self.assertEqual((health["ok"], health["problems"]), (True, []))
        self.assertEqual(health["records"], 1)

    def test_it_finds_and_clears_what_was_left_behind(self):
        kept = self.store.put("memory", {"text": "Your keys are on the hook", "created": NOW})
        with self.store.lock, self.store.db:
            self.store.db.execute("INSERT INTO keys (id, wrapped) VALUES (?, ?)", ("gone-memory", b"\x00" * 60))          # a key with nothing to open
            self.store.db.execute("INSERT INTO records (kind, id, created, updated, payload) VALUES ('vector', 'vector:gone-memory', 0, 0, ?)", (b"x" * 400,))
        health = self.store.health()
        self.assertFalse(health["ok"])
        self.assertEqual(len(health["problems"]), 2)
        fixed = self.store.repair()
        self.assertEqual(fixed["removed"], 2)
        self.assertTrue(fixed["ok"])
        self.assertEqual(self.store.get("memory", kept["id"])["text"], "Your keys are on the hook")

    def test_forgetting_leaves_nothing_behind(self):
        row = self.store.put("memory", {"text": "Your doctor is Dr. Patel on Elm Street", "created": NOW})
        self.store.delete("memory", row["id"])
        health = self.store.health()
        self.assertTrue(health["ok"], health["problems"])
        raw = (Path(self.temp.name) / "s.db").read_bytes()
        self.assertNotIn(b"Patel", raw)


def browser():
    """Node with Playwright and Chromium, the same thing the orb's browser test needs."""
    node = shutil.which("node")
    if not node:
        return False
    try:
        return subprocess.run([node, "-e", "require.resolve('playwright')"], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


class TheScreenTests(unittest.TestCase):
    """The storage screen, opened in a real browser on the phone page and on the computer."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.store.set_setting("luma_account_pending", {"email": "someone@example.com", "name": "Sam"})   # past sign-up, with a made-up account
        self.agent = Agent(store=self.store, use_model=False)
        now = self.agent.clock()
        for text in ("Your sister's name is Dana", "Mom's birthday is June 3", "Your keys are on the hook by the door"):
            self.store.put("memory", {"text": text, "source": "noticed_in_conversation", "created": now})
        for i, title in enumerate(("Trip ideas", "Dana's speech")):
            self.store.put("chat", {"thread": f"t{i}", "title": title, "log": [{"role": "user", "text": "tell me more " * 2000, "at": now - 60 * DAY}]})
        files = self.agent.files_dir
        files.mkdir(parents=True, exist_ok=True)
        (files / "aa11bb22cc33-plan.pdf").write_bytes(b"0" * 200000)
        self.store.put("file", {"name": "plan.pdf", "path": str(files / "aa11bb22cc33-plan.pdf"), "kind": "pdf", "title": "The plan", "created": now - 50 * DAY}, "aa11bb22cc33")
        from luma.control.server import make_server
        self.server = make_server(self.agent, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.control_context.stop.set()
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.temp.cleanup()

    @unittest.skipUnless(browser(), "no browser to open it in (node with Playwright and Chromium)")
    def test_in_a_real_browser(self):
        done = subprocess.run(["node", str(Path(__file__).with_name("storage_check.cjs")), self.base], capture_output=True, text=True, timeout=240)
        self.assertEqual(done.returncode, 0, done.stdout[-600:] + done.stderr[-600:])
        seen = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertEqual(seen["errors"], [])
        self.assertFalse(seen["hiddenRowShows"], "a row marked hidden is showing on the phone")
        phone = seen["phone"]
        self.assertEqual(phone["title"], "Storage")
        self.assertRegex(phone["left"], r"^\d+(\.\d)? (GB|MB|KB|bytes)$")
        self.assertEqual(phone["segments"], len(phone["kinds"]))         # one piece of the bar for each kind
        self.assertTrue(any(k.startswith("Chats (2)") for k in phone["kinds"]), phone["kinds"])
        self.assertTrue(any(k.startswith("Memories (3)") for k in phone["kinds"]), phone["kinds"])
        self.assertTrue(any("Chats older than 30 days" in o for o in phone["options"]))
        self.assertTrue(any("The plan" in o for o in phone["options"]))   # the biggest things, each with its own Delete
        after = seen["afterClear"]
        self.assertRegex(after["freed"], r"^Freed \d+(\.\d)? (MB|KB)\.$")
        self.assertFalse(any(k.startswith("Chats") for k in after["kinds"]), "the chats went, so they're off the list")
        self.assertEqual(self.store.count("chat"), 0)
        desk = seen["desktop"]
        self.assertTrue(desk["health"])
        self.assertIn("The plan", desk["biggest"])
        self.assertGreaterEqual(desk["segments"], 2)


if __name__ == "__main__":
    unittest.main()
