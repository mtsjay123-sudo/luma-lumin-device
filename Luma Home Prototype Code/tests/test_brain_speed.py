"""The brain is judged on the computer it runs on. Every real reply is timed there, and if the bigger brain can't keep up
with a conversation on this Mac, Luma goes back to the fast one by itself (never over the owner's own choice). A brain
that runs but comes out as symbols ('+A57') is caught, and never shown as an answer."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from luma.llm import brain, inference
from luma.memory.store import Store


class BrainSpeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.old = brain._store
        brain._store = self.store
        self.applied = []
        self.patch = mock.patch.object(brain, "_apply_local", lambda: self.applied.append(self.store.setting("brain_local")))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        brain._store = self.old
        self.store.close()
        self.temp.cleanup()

    def test_a_bigger_brain_too_slow_here_steps_aside(self):
        with mock.patch.object(brain, "inference_model_is_big", lambda: True):
            for _ in range(brain.SPEED_SAMPLES - 1):
                brain.note_speed(60, 20)  # 3 tokens a second
            self.assertEqual(self.store.setting("brain_local", "auto"), "auto", "not decided on a handful of replies")
            brain.note_speed(60, 20)
        self.assertEqual(self.store.setting("brain_local"), "auto_fast")
        self.assertEqual(self.applied, ["auto_fast"])
        self.assertIn("too slow to talk", self.store.setting("brain_note"))
        self.assertEqual(brain.speed()["big"], 3.0)

    def test_a_brain_that_keeps_up_stays_and_the_owners_choice_wins(self):
        with mock.patch.object(brain, "inference_model_is_big", lambda: True):
            for _ in range(brain.SPEED_SAMPLES):
                brain.note_speed(300, 10)  # 30 tokens a second
            self.assertEqual(self.store.setting("brain_local", "auto"), "auto")
            self.store.set_setting("brain_local", "big_please")  # anything they picked themselves
            for _ in range(brain.SPEED_SAMPLES):
                brain.note_speed(30, 10)
            self.assertEqual(self.store.setting("brain_local"), "big_please")
        brain.note_speed(5, 10)  # too short to time
        self.assertNotIn("fast", brain.speed())

    def test_switching_back_times_it_afresh(self):
        self.store.set_setting("brain_speed", {"big": [2.0] * 6, "fast": [25.0]})
        self.store.set_setting("brain_local", "auto_fast")
        brain.use_small(False)
        self.assertEqual(self.store.setting("brain_local"), "auto")
        self.assertEqual(brain.speed(), {"fast": 25.0})


class GarbledTests(unittest.TestCase):
    def test_symbols_are_not_an_answer(self):
        for text in ["+A57", "#8++&B+,#$C84=G'#E74F5A", "/6>C", "':=.1>545&;><'>8H6=!"]:
            self.assertTrue(inference.garbled(text), text)
        for text in ["I'd go with the black one.", "😭😭", "Bitcoin is at $79,623.21, down 0.47% in the last 24 hours.", "ok", "Got it. 9 AM."]:
            self.assertFalse(inference.garbled(text), text)

    def test_a_brain_that_comes_out_garbled_moves_to_the_processor(self):
        made = []

        class Fake:
            def __init__(self, n_gpu_layers=-1, **kw):
                made.append(n_gpu_layers)
                self.layers = n_gpu_layers

            def create_chat_completion(self, **kw):
                return {"choices": [{"message": {"content": "+A57#8" if self.layers else "Hey there, hello!"}}]}

        fake_module = mock.Mock(Llama=Fake)
        with mock.patch.dict("sys.modules", {"llama_cpp": fake_module}), mock.patch.object(inference, "_llm", None), \
                mock.patch.object(Path, "exists", lambda self: True), mock.patch.dict("os.environ", {"LUMA_GPU_LAYERS": "-1"}):
            model = inference._load_model()
            self.assertEqual(made, [-1, 0])
            self.assertEqual(model.layers, 0)
            self.assertIn("processor", inference.note)


if __name__ == "__main__":
    unittest.main()
