"""Knowing when the owner is done talking, not just quiet (Pipecat's Smart Turn v3): the audio goes to the model exactly
the way it was trained (checked against transformers' Whisper feature extractor when it's installed), a pause that
the model calls unfinished holds the turn open for the rest, and without the model Luma uses its old silence timer."""
import importlib
import importlib.util
import sys
import tempfile
import threading
import types
import unittest
import wave
from pathlib import Path
from unittest import mock

import numpy as np

from luma.audio import turn

HAVE_TRANSFORMERS = importlib.util.find_spec("transformers") is not None
HAVE_ONNX = importlib.util.find_spec("onnx") is not None and importlib.util.find_spec("onnxruntime") is not None


def voice(seconds, pitch=180):
    t = np.arange(int(16_000 * seconds)) / 16_000
    rng = np.random.default_rng(1)
    return (np.sin(2 * np.pi * pitch * t) * 0.3 * np.abs(np.sin(2 * np.pi * 2 * t)) + rng.standard_normal(len(t)) * 0.02).astype(np.float32)


class FeaturesTests(unittest.TestCase):
    def test_the_last_8_seconds_with_silence_padded_at_the_start(self):
        short = turn.prepare(np.ones(16_000, dtype=np.float32))
        self.assertEqual(len(short), 128_000)
        self.assertTrue((short[:112_000] == 0).all() and (short[-16_000:] == 1).all(), "the speech sits at the end")
        long = turn.prepare(np.linspace(0, 1, 200_000, dtype=np.float32))
        self.assertEqual(len(long), 128_000)
        self.assertEqual(float(long[-1]), 1.0, "the end of what they said is kept, the start is what's cut")
        self.assertAlmostEqual(float(turn.prepare(np.array([16384], dtype=np.int16))[-1]), 0.5, "16-bit samples become -1..1")

    def test_the_shape_the_model_takes(self):
        self.assertEqual(turn.features(voice(2)).shape, (1, 80, 800))

    @unittest.skipUnless(HAVE_TRANSFORMERS, "transformers isn't installed here to compare with")
    def test_matches_whispers_own_feature_extractor(self):
        from transformers import WhisperFeatureExtractor
        extractor = WhisperFeatureExtractor(chunk_length=8)
        for seconds in (1.3, 5.0, 9.5):
            audio = voice(seconds)
            theirs = extractor(turn.prepare(audio), sampling_rate=16_000, return_tensors="np", padding="max_length", max_length=128_000,
                               truncation=True, do_normalize=True).input_features.astype(np.float32)
            self.assertLess(float(np.abs(theirs - turn.features(audio)).max()), 1e-4, seconds)


@unittest.skipUnless(HAVE_ONNX, "onnx isn't installed here to build a stand-in model")
class ModelTests(unittest.TestCase):
    def test_reads_the_models_probability(self):
        import onnx
        from onnx import TensorProto, helper
        graph = helper.make_graph(
            [helper.make_node("ReduceMean", ["input_features"], ["m"], keepdims=0), helper.make_node("Sigmoid", ["m"], ["p"]),
             helper.make_node("Reshape", ["p", "shape"], ["out"])],
            "stand_in", [helper.make_tensor_value_info("input_features", TensorProto.FLOAT, [1, 80, 800])],
            [helper.make_tensor_value_info("out", TensorProto.FLOAT, [1, 1])],
            initializer=[helper.make_tensor("shape", TensorProto.INT64, [2], [1, 1])])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        model.ir_version = 8  # one every onnxruntime can load
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "smart-turn-v3.2-cpu.onnx"
            onnx.save(model, str(path))
            smart = turn.SmartTurn(path)
            p = smart.probability(voice(2))
            expected = 1 / (1 + np.exp(-float(turn.features(voice(2)).mean())))
            self.assertAlmostEqual(p, expected, places=4)
            self.assertEqual(smart.complete(voice(2)), expected > 0.5)


class EndingTests(unittest.TestCase):
    def test_an_unfinished_pause_holds_the_turn_open_then_gives_up(self):
        now = [0.0]
        ending = turn.Ending(decide=lambda audio: False, hold=1.6, clock=lambda: now[0])
        self.assertFalse(ending.paused(voice(1)))
        now[0] = 1.0
        self.assertFalse(ending.timed_out())
        now[0] = 1.7
        self.assertTrue(ending.timed_out(), "never waits forever")

    def test_speaking_again_carries_on_the_same_turn(self):
        ending = turn.Ending(decide=lambda audio: False)
        ending.paused(voice(1))
        ending.resumed()
        self.assertIsNone(ending.holding)

    def test_finished_or_no_model_ends_the_turn_now(self):
        self.assertTrue(turn.Ending(decide=lambda audio: True).paused(voice(1)))
        self.assertTrue(turn.Ending(decide=lambda audio: None).paused(voice(1)), "no model: the old timer already waited")


class DownloadTests(unittest.TestCase):
    def test_keeps_the_first_real_model_file_it_finds(self):
        tried = []

        class Response:
            def __init__(self, data): self.data = data
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, n): return self.data

        def opener(request, timeout):
            tried.append(request.full_url.rsplit("/", 1)[-1])
            if len(tried) == 1:
                raise OSError("404")
            return Response(b"\x08" + b"\x00" * 8_000_000)

        with tempfile.TemporaryDirectory() as root, mock.patch.object(turn, "folder", return_value=Path(root)), \
                mock.patch.dict("os.environ", {"LUMA_NO_DOWNLOADS": ""}):
            done = threading.Event()
            with mock.patch.object(turn.threading, "Thread", side_effect=lambda target, daemon: types.SimpleNamespace(start=lambda: (target(), done.set()))):
                turn.fetch_in_background(opener=opener)
            self.assertTrue(done.is_set())
            self.assertEqual(tried, turn.FILES[:2])
            self.assertEqual(turn.model_path(), Path(root) / turn.FILES[1])


class ListeningLoopTests(unittest.TestCase):
    """The real listening loop, with a scripted mic and VAD: "remind me to call..." (pause) "...my sister" is one turn."""

    def test_a_mid_thought_pause_doesnt_cut_them_off(self):
        events = {3: {"start": 0}, 8: {"end": 0}, 11: {"start": 0}, 16: {"end": 0}}
        calls = {"n": 0}

        class VAD:
            def __call__(self, x):
                calls["n"] += 1
                return events.get(calls["n"])
            def reset_states(self): pass

        stop = threading.Event()

        class InputStream:
            def __init__(self, callback, **kw): self.callback = callback
            def __enter__(self):
                def feed():
                    for _ in range(24):
                        self.callback(np.full((512, 1), 1000, dtype=np.int16), 512, None, None)
                        threading.Event().wait(0.004)
                    threading.Event().wait(0.3)
                    stop.set()
                threading.Thread(target=feed, daemon=True).start()
                return self
            def __exit__(self, *a): return False

        fakes = {"sounddevice": types.SimpleNamespace(InputStream=InputStream, query_devices=lambda *a, **k: []),
                 "torch": types.SimpleNamespace(from_numpy=lambda a: a),
                 "silero_vad": types.SimpleNamespace(VADIterator=lambda *a, **k: VAD(), load_silero_vad=lambda: object())}
        heard, decisions = [], iter([False, True])  # the first pause sounds unfinished, the second finished
        import luma.audio as package
        before = package.__dict__.get("vad")
        try:
            with mock.patch.dict(sys.modules, fakes):  # everything in sys.modules is put back afterwards
                sys.modules.pop("luma.audio.vad", None)
                vad = importlib.import_module("luma.audio.vad")
                with mock.patch.object(turn, "model", return_value=object()), mock.patch.object(turn, "finished", lambda audio: next(decisions)), \
                        mock.patch("luma.audio.echo.canceller", return_value=None), \
                        mock.patch.object(vad, "resolve_audio_device", return_value=None):
                    vad.start_listening(lambda path: heard.append(path), stop)
        finally:
            if before is None: package.__dict__.pop("vad", None)
            else: package.vad = before
        self.assertEqual(len(heard), 1, "one turn, not two")
        with wave.open(heard[0]) as w:
            self.assertGreaterEqual(w.getnframes(), 12 * 512, "both halves of what they said")
        Path(heard[0]).unlink()


if __name__ == "__main__":
    unittest.main()
