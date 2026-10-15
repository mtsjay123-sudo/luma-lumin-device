"""The brain thinks in a process of its own: a crash there never takes Luma down, and Luma falls back
to something steadier on its own (graphics chip -> processor, bigger brain -> fast one, then rest)."""
import os
import threading
import time
import unittest
from unittest import mock

from luma.llm import inference, worker


class BrainProcessTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"LUMA_BRAIN_WORKER": "1", "LUMA_BRAIN_IMPL": "fake_brain", "FAKE_BRAIN": "ok", "LUMA_GPU_LAYERS": "-1"})
        self.env.start()
        self.brain = worker.Brain()

    def tearDown(self):
        self.brain.stop()
        self.env.stop()

    def plan(self, **kw):
        return self.brain.call("plan", {"messages": [{"role": "user", "content": "hi"}], "memories": [], "tools": {}, "mode": "friend"}, **kw)

    def test_answers_and_streams_from_its_own_process(self):
        heard = []
        out = self.plan(on_text=heard.append)
        self.assertEqual(out["text"], "Hi there")
        self.assertEqual("".join(heard), "Hi there")
        self.assertNotEqual(self.brain.state()["pid"], os.getpid())
        self.assertEqual(self.brain.call("rewrite", {"prompt": "yo"}), "YO")

    def test_a_crash_on_the_graphics_chip_moves_to_the_processor_and_still_answers(self):
        os.environ["FAKE_BRAIN"] = "crash_on_gpu"
        out = self.plan()
        self.assertEqual(out["gpu"], "0")
        self.assertFalse(self.brain.state()["gpu"])
        self.assertIn("processor", self.brain.state()["note"])

    def test_the_bigger_brain_steps_down_when_it_crashes(self):
        changed = []
        self.brain.gpu = False
        self.brain.override = "/models/Qwen3-30B-A3B.gguf"
        self.brain.on_change = changed.append
        os.environ["FAKE_BRAIN"] = "crash"
        with self.assertRaises(worker.BrainCrashed):
            self.plan()
        self.assertIsNone(self.brain.override)
        self.assertEqual(changed, ["small"])

    def test_it_rests_after_crashing_again_and_again(self):
        os.environ["FAKE_BRAIN"] = "crash"
        for _ in range(3):
            try:
                self.plan()
            except (worker.BrainCrashed, worker.BrainResting):
                pass
        with self.assertRaises(worker.BrainResting):
            self.plan()
        self.assertGreater(self.brain.state()["resting"], 0)

    def test_stopping_mid_thought(self):
        os.environ["FAKE_BRAIN"] = "slow"
        stop = threading.Event()
        threading.Timer(0.4, stop.set).start()
        started = time.time()
        with self.assertRaises(inference.GenerationCancelled):
            self.plan(cancel_event=stop)
        self.assertLess(time.time() - started, 3.5)
        os.environ["FAKE_BRAIN"] = "ok"
        self.assertEqual(self.plan()["text"], "Hi there")  # and the same process keeps going

    def test_ordinary_errors_stay_ordinary(self):
        os.environ["FAKE_BRAIN"] = "error"
        with self.assertRaises(ValueError):
            self.plan()
        self.assertTrue(self.brain.state()["running"])


class FriendlyFailureTests(unittest.TestCase):
    def test_a_missing_model_is_explained_not_crashed(self):
        from luma.llm import brain
        with mock.patch.object(inference, "plan", side_effect=FileNotFoundError("Model not found")), \
             mock.patch.object(brain, "health", return_value={"ok": False, "reason": "model", "say": "My brain's model file is missing. Use Repair in Settings and I'll download it again."}), \
             mock.patch.object(brain, "cloud_on", return_value=False):
            with self.assertRaisesRegex(brain.BrainUnavailable, "Repair"):
                brain.plan([{"role": "user", "content": "hi"}], [], {}, "friend")


if __name__ == "__main__":
    unittest.main()
