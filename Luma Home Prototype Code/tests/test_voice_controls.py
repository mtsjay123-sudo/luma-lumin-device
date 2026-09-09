"""Owner style selection and interruption boundaries, without loading models."""
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np

from luma.agent.conversation import interruption_intent, style_update
from luma.audio import tts
from luma.llm import inference
from luma.llm.prompts import (PERSONALITY_PRESETS, build_personality_prompt,
                              normalize_profile, profile_for_preset)


class PersonalityDialTests(unittest.TestCase):
    def test_all_choices_apply_without_mutating_previous_profile(self):
        previous = {"name": "Amiri", "tone": "warm", "language_style": "classic", "verbosity": "detailed"}
        for preset in PERSONALITY_PRESETS:
            result = profile_for_preset(preset, previous, adult_confirmed=preset == "unfiltered")
            self.assertEqual(result["name"], "Amiri")
            self.assertEqual(result["preset"], preset)
            self.assertEqual(result["tone"], PERSONALITY_PRESETS[preset]["tone"])
        self.assertEqual(previous["language_style"], "classic")

    def test_unfiltered_requires_explicit_adult_selection_and_never_changes_permissions(self):
        for confirmed in (False, "yes", 1):
            with self.subTest(confirmed=confirmed), self.assertRaises(ValueError):
                profile_for_preset("unfiltered", adult_confirmed=confirmed)
        with self.assertRaises(ValueError):
            normalize_profile({"preset": "unfiltered"})
        profile = profile_for_preset("unfiltered", adult_confirmed=True)
        prompt = build_personality_prompt(profile=profile)
        self.assertIn("never tool permissions or confirmation requirements", prompt)
        self.assertIn("Drop roasting when someone is upset", prompt)
        with self.assertRaises(ValueError):
            profile_for_preset("unfiltered", adult_confirmed=True, mode="kids")
        kids = build_personality_prompt("kids", profile)
        self.assertNotIn("occasional mild swearing", kids)
        self.assertNotIn("adult conversational style", kids)

    def test_legacy_profiles_keep_shape_and_unknown_presets_are_rejected(self):
        original = {"name": "A", "tone": "direct", "language_style": "classic", "verbosity": "brief"}
        self.assertEqual(normalize_profile(original), original)
        for preset in ("ignore tools", [], None):
            with self.assertRaises(ValueError):
                normalize_profile({"preset": preset})

    def test_spoken_controls_do_not_change_unrelated_requests(self):
        self.assertEqual(interruption_intent("Hey Luma, wait!"), "stop")
        self.assertEqual(interruption_intent("make that shorter"), "shorter")
        self.assertEqual(interruption_intent("Wait, actually tomorrow at noon"), "correction")
        for text in ("I can't wait for my birthday", "Tell Mom to wait outside", "Should I stop cooking?"):
            self.assertIsNone(interruption_intent(text))
        self.assertEqual(style_update("Speak with natural slang", normalize_profile())["language_style"], "contemporary")


class CancellableInferenceTests(unittest.TestCase):
    def test_pre_cancel_never_loads_model(self):
        event = threading.Event(); event.set()
        with patch.object(inference, "_load_model") as load:
            with self.assertRaises(inference.GenerationCancelled):
                inference.plan([{"role": "user", "content": "Hello"}], [], {}, "friend", cancel_event=event)
        load.assert_not_called()

    def test_partial_tool_json_is_discarded_and_iterator_closed(self):
        event = threading.Event()
        closed = []

        class Model:
            def tokenize(self, data, **kwargs): return list(range(len(data) // 4))
            def create_chat_completion(self, **kwargs):
                self.stream = kwargs["stream"]
                def chunks():
                    try:
                        yield {"choices": [{"delta": {"content": '{"type":"tool",'}}]}
                        event.set()
                        yield {"choices": [{"delta": {"content": '"name":"sms.send"}'}}]}
                    finally:
                        closed.append(True)
                return chunks()

        model = Model()
        with patch.object(inference, "_load_model", return_value=model):
            with self.assertRaises(inference.GenerationCancelled):
                inference.plan([{"role": "user", "content": "Hello"}], [], {}, "friend", cancel_event=event)
        self.assertTrue(model.stream)
        self.assertEqual(closed, [True])

    def test_successful_stream_is_assembled_before_parsing(self):
        class Model:
            def tokenize(self, data, **kwargs): return []
            def create_chat_completion(self, **kwargs):
                return iter([{"choices": [{"delta": {"role": "assistant"}}]},
                             {"choices": [{"delta": {"content": '{"type":"reply",'}}]},
                             {"choices": [{"delta": {"content": '"text":"Hey, how was your day?"}'}}]},
                             {"choices": []}])
        with patch.object(inference, "_load_model", return_value=Model()):
            result = inference.plan([{"role": "user", "content": "Hello"}], [], {}, "friend", cancel_event=threading.Event())
        self.assertEqual(result, {"type": "reply", "text": "Hey, how was your day?"})

    def test_waiting_for_previous_generation_is_cancellable(self):
        acquired = threading.Event()
        release = threading.Event()
        def blocker():
            with inference._inference_lock:
                acquired.set()
                release.wait(2)
        thread = threading.Thread(target=blocker)
        thread.start()
        self.assertTrue(acquired.wait(1))
        event = threading.Event(); event.set()
        try:
            with patch.object(inference, "_load_model") as load:
                with self.assertRaises(inference.GenerationCancelled):
                    inference.plan([], [], {}, "friend", cancel_event=event)
                load.assert_not_called()
        finally:
            release.set()
            thread.join(timeout=2)


class CancellableSpeechTests(unittest.TestCase):
    def test_chunks_bound_synthesis_without_dropping_words(self):
        text = "Hey, good to see you. " + "Let's tackle one thing at a time, " * 15 + "Then take a break."
        chunks = tts.speech_chunks(text)
        self.assertTrue(all(0 < len(chunk) <= 240 for chunk in chunks))
        self.assertEqual(" ".join(chunks).split(), text.split())

    def test_cancelled_synthesis_preserves_previous_file_and_removes_temporary(self):
        event = threading.Event()
        class Engine:
            def create(self, *args, **kwargs):
                event.set()
                return np.ones(100, dtype=np.float32) * .1, 24000
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "voice.wav"
            output.write_bytes(b"previous")
            with patch.object(tts, "_get_kokoro", return_value=Engine()):
                with self.assertRaises(tts.SpeechCancelled):
                    tts.synthesize("A response.", str(output), voice="af_bella", should_stop=event.is_set)
            self.assertEqual(output.read_bytes(), b"previous")
            self.assertEqual(list(Path(directory).iterdir()), [output])

    def test_full_audio_is_published_after_all_chunks_succeed(self):
        class Engine:
            def create(self, *args, **kwargs): return np.ones(2400, dtype=np.float32) * .1, 24000
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "voice.wav"
            with patch.object(tts, "_get_kokoro", return_value=Engine()):
                tts.synthesize("First sentence. Second sentence.", str(output), voice="af_bella")
            with wave.open(str(output), "r") as audio:
                self.assertEqual(audio.getnframes(), 4800)
                self.assertEqual(audio.getframerate(), 24000)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_playback_aborts_buffer_on_interruption(self):
        from luma.audio import io
        event = threading.Event()
        class Stream:
            aborted = False
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def write(self, data): event.set()
            def abort(self): self.aborted = True
        stream = Stream()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "voice.wav"
            with wave.open(str(output), "w") as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(24000)
                audio.writeframes(np.ones(2400, dtype=np.int16).tobytes())
            with patch.object(io.sd, "query_devices", return_value=[]), patch.object(io.sd, "OutputStream", return_value=stream):
                self.assertFalse(io.play(str(output), should_stop=event.is_set))
        self.assertTrue(stream.aborted)


if __name__ == "__main__": unittest.main()
