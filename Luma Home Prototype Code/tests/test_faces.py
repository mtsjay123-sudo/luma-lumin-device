"""Knowing its people by sight (docs/PRESENCE_MASTER_PROMPT.md, 9.2): the frame in luma.agent.faces, with a stand-in
for the model. No real face has been read: the proof asked for (the right person 98 times in 100, a stranger, a photo
and a video 0 in 100) needs a licensed model and real people who've agreed. This checks what the frame guarantees
whatever model is put in.
"""
import json
import random
import tempfile
import unittest
from pathlib import Path

from luma.agent import faces, who
from luma.agent.runtime import Agent
from luma.memory.store import Store


def person(seed, wobble=0.05, n=1, rng=None):
    """Made-up 'looks' at one made-up person: a fixed direction for them, a little different each time."""
    rng = rng or random.Random(seed * 7919)
    theirs = random.Random(seed)
    base = [theirs.gauss(0, 1) for _ in range(32)]
    return [{"vector": [b + rng.gauss(0, wobble) for b in base], "live": True} for _ in range(n)]


class StandIn:
    """Not a face model: it hands back the numbers the made-up frame carries."""
    def embed(self, frame): return frame.get("vector")
    def live(self, frames): return bool(frames) and all(f.get("live") for f in frames)


class Luma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.addCleanup(self.store.close)
        self.agent = Agent(store=self.store, use_model=False)
        self.addCleanup(faces.use, None)

    def switched_on(self):
        faces.use(StandIn())
        self.store.set_setting(faces.SETTING, True)
        who.choose(self.agent, "blue kettle tuesday", "owner", name="Jay")
        who.set_greeting(self.agent, "wtw bro", "owner")
        who.lock(self.agent)


class AsLumaComes(Luma):
    def test_no_model_is_installed_and_the_switch_is_off(self):
        self.assertIsNone(faces._reader["model"])
        self.assertFalse(faces.ready(self.agent))
        self.assertIsNone(faces.look(self.agent, person(1, n=3)))
        with self.assertRaises(ValueError):
            faces.introduce(self.agent, "owner", person(1, n=6))

    def test_a_model_alone_isnt_enough_the_owner_switches_it_on(self):
        faces.use(StandIn())
        self.assertFalse(faces.ready(self.agent))
        with self.assertRaises(ValueError):
            faces.introduce(self.agent, "owner", person(1, n=6))

    def test_nothing_in_luma_installs_a_model(self):
        import re
        src = Path(__file__).resolve().parents[1] / "src" / "luma"
        callers = [p.name for p in src.rglob("*.py") if p.name != "faces.py" and re.search(r"faces\.use\(", p.read_text())]
        self.assertEqual(callers, [])


class TheFrame(Luma):
    def test_introduced_from_a_few_looks_and_only_numbers_are_kept(self):
        self.switched_on()
        with self.assertRaises(ValueError):
            faces.introduce(self.agent, "owner", person(1, n=3))                  # not enough looks
        self.assertEqual(faces.introduce(self.agent, "owner", person(1, n=6)), ["owner"])
        kept = self.store.all(faces.KIND, 10)
        self.assertEqual(len(kept), 1)
        self.assertEqual(set(kept[0]) - {"id"}, {"person", "looks", "added"})
        self.assertTrue(all(isinstance(v, float) for look in kept[0]["looks"] for v in look))
        self.assertNotIn("looks", json.dumps(faces.known(self.agent)))             # the app gets ids, never the numbers

    def test_their_person_is_let_in_and_greeted_their_way(self):
        self.switched_on()
        faces.introduce(self.agent, "owner", person(1, n=6))
        self.assertTrue(who.locked(self.agent))
        self.assertEqual(faces.look(self.agent, person(1, n=3, rng=random.Random(99))), "owner")
        self.assertFalse(who.locked(self.agent))
        self.assertEqual(self.agent.chat("yo luma", channel="room")["text"], "Wtw bro.")

    def test_a_stranger_is_someone_it_hasnt_met(self):
        self.switched_on()
        faces.introduce(self.agent, "owner", person(1, n=6))
        for stranger in range(2, 60):
            self.assertIsNone(faces.look(self.agent, person(stranger, n=3)), stranger)
        self.assertTrue(who.locked(self.agent))
        self.assertTrue(self.agent.chat("read me his texts", channel="room").get("locked"))

    def test_a_picture_or_a_screen_never_gets_in(self):
        self.switched_on()
        faces.introduce(self.agent, "owner", person(1, n=6))
        flat = [{**look, "live": False} for look in person(1, n=3)]               # the owner's face, but not the owner
        self.assertIsNone(faces.look(self.agent, flat))
        self.assertTrue(who.locked(self.agent))
        with self.assertRaises(ValueError):                                         # and nobody is introduced from a picture
            faces.introduce(self.agent, "maya", [{**look, "live": False} for look in person(3, n=6)])

    def test_two_people_too_alike_to_tell_apart_is_not_knowing(self):
        self.switched_on()
        faces.introduce(self.agent, "owner", person(1, wobble=0.02, n=6))
        twin = [{"vector": [v + 0.01 for v in look["vector"]], "live": True} for look in person(1, wobble=0.02, n=6)]
        faces.introduce(self.agent, "twin", twin)
        self.assertIsNone(faces.look(self.agent, person(1, wobble=0.02, n=3)))
        self.assertTrue(who.locked(self.agent))

    def test_one_look_is_never_enough_and_they_all_have_to_agree(self):
        self.switched_on()
        faces.introduce(self.agent, "owner", person(1, n=6))
        self.assertIsNone(faces.look(self.agent, person(1, n=2)))
        self.assertIsNone(faces.look(self.agent, person(1, n=2) + person(7, n=1)))
        self.assertIsNone(faces.look(self.agent, [{"vector": None, "live": True}] * 3))   # nobody in view

    def test_forget_me_deletes_it_and_so_does_forgetting_everything(self):
        self.switched_on()
        faces.introduce(self.agent, "owner", person(1, n=6))
        faces.introduce(self.agent, "maya", person(3, n=6))
        self.assertEqual(faces.forget(self.agent, "maya"), 1)
        self.assertEqual(faces.known(self.agent), ["owner"])
        self.agent.forget_everything()
        self.assertEqual(faces.known(self.agent), [])
        self.assertIsNone(faces.look(self.agent, person(1, n=3)))

    def test_not_in_kids_mode(self):
        self.switched_on()
        faces.introduce(self.agent, "owner", person(1, n=6))
        self.agent.set_mode("kids")
        self.assertIsNone(faces.look(self.agent, person(1, n=3)))


if __name__ == "__main__":
    unittest.main()
