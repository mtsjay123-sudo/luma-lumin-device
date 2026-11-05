"""Luma never forgets: every memory is kept on the device (no limit), filed by what it's about, and found again
however old it is: "where are my keys" finds where the keys are, not every memory that says "my"."""
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory import segments
from luma.memory.store import Store


class SegmentTests(unittest.TestCase):
    def test_each_memory_lands_in_the_right_place(self):
        for text, bucket in [("Your keys are in the kitchen drawer", "places"), ("You left your passport in the blue suitcase", "places"),
                             ("Your mom's birthday is June 3", "dates"), ("You're allergic to peanuts", "health"), ("You love sushi", "likes"),
                             ("Your sister Lena lives in Austin", "people"), ("Your goal is to run a half marathon", "goals"),
                             ("Your name is Jay Price", "you"), ("The wifi password is on the router", "places"), ("Trash day is Tuesday", "dates"), ("Your dentist appointment is on Friday", "dates"), ("Your coffee order is an oat latte", "notes")]:
            self.assertEqual(segments.category(text), bucket, text)

    def test_questions_look_in_the_right_bucket_first(self):
        mems = [{"text": "Your keys are on the hook by the door", "created": 1, "category": "places"},
                {"text": "You keep your car keys' spare with your mom", "created": 2},
                {"text": "My keys guy is Sam at the hardware store", "created": 3, "category": "people"}]
        self.assertEqual(segments.recall("where are my keys?", mems)[0]["text"], "Your keys are on the hook by the door")
        self.assertEqual(segments.words("Where are my keys?"), {"key"})
        self.assertEqual(segments.recall("where did I put it", mems), [], "nothing that matters to match on")


class NeverForgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.agent = Agent(store=self.store, use_model=False, now=lambda: 1791900000.0)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_no_limit_on_the_device_and_the_oldest_memory_is_still_found(self):
        self.assertEqual(self.agent.remember_fact("Your passport is in the top desk drawer")["category"], "places")
        for i in range(1300):
            self.store.put("memory", {"text": f"Note {i}: my day was fine and my coffee was good", "source": "noticed", "created": 1000 + i})
        quota = self.agent.memory_quota()
        self.assertIsNone(quota["limit"])
        self.assertFalse(quota["full"])
        self.assertNotEqual(self.agent.remember_fact("Your favorite color is green"), "full", "no memory is ever turned away for space")
        found = self.store.recall("where's my passport")
        self.assertEqual(found[0]["text"], "Your passport is in the top desk drawer", "over a thousand memories later, still found")

    def test_a_new_memory_is_found_right_away_and_a_forgotten_one_is_gone(self):
        self.store.recall("anything")  # fills the cache
        row = self.agent.remember_fact("Your bike lock code is in your notes app")
        self.assertEqual(self.store.recall("bike lock")[0]["id"], row["id"])
        self.store.delete("memory", row["id"])
        self.assertEqual(self.store.recall("bike lock"), [])

    def test_where_things_are_moves_when_they_move(self):
        self.agent.remember_fact("Your keys are in the kitchen drawer")
        self.agent.remember_fact("Your keys are on the hook by the door")
        found = self.store.recall("where are my keys")
        self.assertEqual([m["text"] for m in found], ["Your keys are on the hook by the door"])


if __name__ == "__main__":
    unittest.main()
