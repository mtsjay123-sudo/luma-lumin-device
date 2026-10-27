"""Memory comes first. When Luma doesn't know something about you it says so, asks, and keeps your answer. Everything it
remembers sits in one folder on the device, sorted by kind, and from the phone or the computer you can forget one memory,
a whole kind, or the old ones, and make room on the device so new memories fit without moving to the cloud."""
import tempfile
import unittest
from pathlib import Path

from luma.agent import memory_folder
from luma.agent.runtime import Agent
from luma.memory.store import Store

NOW = 1793116800.0
DAY = 86400


class MemoryFolderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.now = NOW
        self.agent = Agent(store=self.store, use_model=False, now=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def remember(self, text, days_ago=0):
        return self.store.put("memory", {"text": text, "source": "explicit_user_request", "created": NOW - days_ago * DAY})

    def test_it_says_it_doesnt_know_then_keeps_the_answer(self):
        asked = self.agent.chat("what's my sister's name?")["text"]
        self.assertIn("I don't know your sister's name yet", asked)
        saved = self.agent.chat("dana")
        self.assertEqual(saved["text"], "Got it. Your sister's name is Dana. I won't forget.")
        self.assertEqual(self.agent.chat("what's my sister's name?")["text"], "Your sister's name is Dana.")
        self.agent.chat("when's my dad's birthday?")
        self.assertIn("June 3", self.agent.chat("it's june 3rd lol")["text"])
        self.assertIn("June 3", self.agent.chat("when's my dad's birthday?")["text"])

    def test_a_new_question_or_a_no_isnt_saved_as_the_answer(self):
        self.agent.chat("what's my best friend's name?")
        self.agent.chat("what's the weather like?")
        self.assertFalse([m for m in self.store.all("memory", 50) if "best friend" in m["text"].lower()])
        self.agent.chat("what's my favorite movie?")
        self.assertIn("No worries", self.agent.chat("idk")["text"])
        self.agent.chat("what's my favorite song?")
        self.now += 900  # they came back much later: "ok" isn't an answer to that
        self.agent.chat("ok")
        self.assertFalse([m for m in self.store.all("memory", 50) if "favorite" in m["text"].lower()])

    def test_the_folder_sorts_memories_the_way_people_think(self):
        self.remember("Mom's birthday is June 3")
        self.remember("My sister's name is Dana")
        self.remember("I'm allergic to peanuts")
        self.remember("My spare keys are in the kitchen drawer")
        got = memory_folder.folder(self.agent)
        kinds = {k["kind"]: [i["text"] for i in k["items"]] for k in got["kinds"]}
        self.assertEqual(kinds["Dates"], ["Mom's birthday is June 3"])
        self.assertIn("My sister's name is Dana", kinds["People"])
        self.assertIn("My spare keys are in the kitchen drawer", kinds["Places"])
        self.assertEqual((got["used"], got["limit"], got["plan"]), (4, 200, "free"))
        self.assertGreater(got["bytes"], 0)

    def test_forget_one_a_kind_or_the_old_ones(self):
        a = self.remember("My sister's name is Dana")
        self.remember("Mom's birthday is June 3", days_ago=200)
        self.remember("I love sushi", days_ago=120)
        self.remember("I hate cilantro", days_ago=1)
        self.assertEqual(memory_folder.forget(self.agent, ids=[a["id"]])["forgotten"], 1)
        self.assertEqual(memory_folder.forget(self.agent, older_than_days=90)["forgotten"], 2)
        left = [m["text"] for m in self.store.all("memory", 50)]
        self.assertEqual(left, ["I hate cilantro"])
        self.assertEqual(memory_folder.forget(self.agent, kind="Likes")["forgotten"], 1)
        with self.assertRaises(ValueError):
            memory_folder.forget(self.agent)  # never "forget everything" by accident
        with self.assertRaises(ValueError):
            memory_folder.forget(self.agent, kind="Secrets")

    def test_a_full_memory_frees_up_when_old_ones_go(self):
        for i in range(self.agent.FREE_MEMORIES):
            self.remember(f"note number {i}", days_ago=400)
        self.agent.chat("what's my cousin's name?")
        self.assertIn("memory's full", self.agent.chat("tasha")["text"])
        memory_folder.forget(self.agent, older_than_days=365)
        self.agent.chat("what's my cousin's name?")
        self.assertIn("Your cousin's name is Tasha", self.agent.chat("tasha")["text"])

    def test_making_room_on_the_device(self):
        self.store.set_setting("news", {"fetched": NOW, "items": [{"title": "x" * 400, "url": "https://a.com", "source": "A"}] * 20})
        self.store.put("chat", {"thread": "old1", "mode": "friend", "title": "Old", "log": [{"role": "you", "text": "hi " * 300, "at": NOW - 60 * DAY}]}, id="chat:friend:old1")
        self.store.put("chat", {"thread": "new1", "mode": "friend", "title": "New", "log": [{"role": "you", "text": "hey", "at": NOW - DAY}]}, id="chat:friend:new1")
        self.remember("My sister's name is Dana")
        room = memory_folder.space(self.agent)
        keys = [o["key"] for o in room["options"]]
        self.assertIn("news", keys)
        self.assertIn("old_chats", keys)
        self.assertEqual(room["memories"]["used"], 1)
        done = memory_folder.clean(self.agent, "old_chats")
        self.assertGreater(done["freed_bytes"], 0)
        self.assertIsNone(self.store.get("chat", "chat:friend:old1"))
        self.assertIsNotNone(self.store.get("chat", "chat:friend:new1"), "recent chats stay")
        self.assertEqual(len(self.store.all("memory", 10)), 1, "memories never go with chats")
        with self.assertRaises(ValueError):
            memory_folder.clean(self.agent, "everything")

    def test_how_much_room_and_clearing_the_safe_stuff_from_the_chat(self):
        self.store.set_setting("news", {"fetched": NOW, "items": [{"title": "headline " * 40, "url": "https://a.com", "source": "A"}] * 30})
        out = self.agent.chat("how much space do you have left?")
        self.assertIn("news and posts i've read", out["text"])
        self.assertIn("Clear the news you've read", out["choices"])
        cleared = self.agent.chat("Clear the news you've read")
        self.assertIn("freed about", cleared["text"])
        self.assertEqual(self.store.setting("news")["items"], [])
        self.assertIsNone(self.agent._make_room("clear my memories"), "memories are cleared in the folder, one by one")


if __name__ == "__main__":
    unittest.main()
