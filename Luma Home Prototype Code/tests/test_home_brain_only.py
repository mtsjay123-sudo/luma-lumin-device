"""Luma thinks at home. The cloud brain is parked: nothing in the cloud answers a turn, with Luma Plus or with the owner's
own key, unless LUMA_CLOUD_BRAIN=1 brings it back. The cloud's one job is more room for memories."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from luma.llm import brain, plus
from luma.memory.store import Store


class FakeCloud:
    """A signed-in Luma Cloud whose account has Plus, with the brain set up there and the yes on record."""
    def connected(self): return True
    def clock(self): return 1793116800.0
    def brain_relay(self): return "https://cloud.example/api/luma/brain", "token"
    def brain_consent(self, on, words=None): return {"consent": bool(on)}


class HomeBrainOnly(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.addCleanup(self.store.close)
        was_store, was_plus = brain._store, dict(brain._plus)
        self.addCleanup(lambda: (setattr(brain, "_store", was_store), brain._plus.update(was_plus)))
        brain._store = self.store
        brain.use_plus(FakeCloud())
        # everything that used to turn a cloud brain on: the owner's own key, and Plus with the yes
        self.store.set_setting("brain_cloud", True)
        self.store.set_setting("brain_cloud_key", "sk-not-a-real-key")
        self.store.set_setting(plus.SETTING, True)
        self.store.set_setting(plus.ACCOUNT, {"plan": "plus", "brain": {"available": True, "consent": True, "words": plus.WORDS, "left_share": 0.8}})
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("LUMA_CLOUD_BRAIN", None)

    def test_no_cloud_brain_answers(self):
        self.assertFalse(brain.cloud_allowed())
        self.assertIsNone(brain.cloud_route())
        self.assertFalse(brain.cloud_on())
        self.assertFalse(brain.plus_on())
        for tier in (None, "light", "standard", "heavy"):
            self.assertFalse(brain.use_cloud(tier), tier)

    def test_the_app_is_told_so_and_offers_nothing(self):
        state = brain.status()
        self.assertTrue(state["cloud"]["parked"])
        self.assertFalse(state["cloud"]["on"])
        self.assertNotIn("Super Intelligence", state["thinking_with"])
        view = state["plus"]
        for key in ("available", "on", "can_turn_on", "ask"):
            self.assertFalse(view[key], key)
        self.assertIsNone(view["screen"])           # the yes screen is never shown for something that's switched off

    def test_a_yes_is_refused_while_its_parked(self):
        with self.assertRaises(ValueError) as caught:
            brain.set_plus(on=True)
        self.assertIn("at home", str(caught.exception))
        brain.set_plus(on=False)                    # turning it off always works

    def test_the_switch_brings_it_back(self):
        os.environ["LUMA_CLOUD_BRAIN"] = "1"
        self.assertTrue(brain.cloud_allowed())
        self.assertEqual(brain.cloud_route(), "plus")
        self.store.set_setting(plus.SETTING, False)
        self.assertEqual(brain.cloud_route(), "own")
        self.assertFalse(brain.status()["cloud"].get("parked"))


if __name__ == "__main__":
    unittest.main()
