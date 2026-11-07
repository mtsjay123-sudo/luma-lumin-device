"""Memory by meaning: "that thing my mom likes" finds "Mom loves lavender candles" even with no word in common."""
import tempfile
import unittest
from pathlib import Path

from luma.memory import meaning
from luma.memory.store import Store

# A stand-in for the embedding model: things that mean the same land on the same direction.
TOPICS = {"mom": ("mom", "mother", "her"), "scent": ("lavender", "candles", "smells", "scent"), "likes": ("likes", "loves", "into"),
          "car": ("car", "parked", "parking", "garage"), "keys": ("keys",), "dog": ("dog", "puppy", "biscuit")}


def fake(text):
    text = text.lower().split("query:")[-1]
    return [float(sum(w in text for w in words)) for words in TOPICS.values()] + [0.2]


class MeaningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        meaning.embedder = fake
        meaning._cache.clear()
        for text in ["Mom loves lavender candles", "Your car is parked on level 3 of the garage", "Your dog Biscuit hates baths"]:
            self.store.put("memory", {"text": text, "category": "notes"})
        meaning.catch_up(self.store, self.store.memories(), wait=True)

    def tearDown(self):
        meaning.embedder = None
        meaning._cache.clear()
        self.store.close()
        self.temp.cleanup()

    def test_it_finds_a_memory_said_in_other_words(self):
        found = [m["text"] for m in self.store.recall("what's that thing my mother is into?")]
        self.assertIn("Mom loves lavender candles", found)
        self.assertNotIn("Your dog Biscuit hates baths", found, "only memories that mean the same thing")

    def test_words_still_come_first(self):
        found = [m["text"] for m in self.store.recall("where did i park the car")]
        self.assertEqual(found[0], "Your car is parked on level 3 of the garage")

    def test_what_it_means_is_encrypted_and_forgotten_with_the_memory(self):
        raw = (Path(self.temp.name) / "s.db").read_bytes()
        self.assertNotIn(b"lavender", raw)
        mom = next(m for m in self.store.memories() if "lavender" in m["text"])
        self.assertIsNotNone(self.store.get("vector", "vector:" + mom["id"]))
        self.store.delete("memory", mom["id"])
        self.assertIsNone(self.store.get("vector", "vector:" + mom["id"]))
        self.assertNotIn("Mom loves lavender candles", [m["text"] for m in self.store.recall("what's my mother into")])

    def test_without_the_model_it_recalls_by_words_like_before(self):
        meaning.embedder = None
        meaning._cache.clear()
        self.assertFalse(meaning.available(self.store) and meaning.model_path())
        self.assertEqual([m["text"] for m in self.store.recall("what's that thing my mother is into?")], [])
        self.assertEqual(self.store.recall("where's my car")[0]["text"], "Your car is parked on level 3 of the garage")

    def test_it_can_be_turned_off(self):
        self.store.set_setting("memory_by_meaning", False)
        self.assertEqual(self.store.recall("what's that thing my mother is into?"), [])

    def test_a_changed_memory_gets_its_meaning_worked_out_again(self):
        car = next(m for m in self.store.memories() if "car" in m["text"])
        self.store.put("memory", {**car, "text": "Your puppy sleeps in the garage"}, car["id"])
        meaning._cache.clear()
        first = [m["text"] for _, m in meaning.close(self.store, "where does my dog sleep", self.store.memories(), wait=True)]
        self.assertNotIn("Your car is parked on level 3 of the garage", first, "the old meaning is never used for the new words")
        found = [m["text"] for _, m in meaning.close(self.store, "where does my dog sleep", self.store.memories())]
        self.assertIn("Your puppy sleeps in the garage", found)


if __name__ == "__main__":
    unittest.main()
