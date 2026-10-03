"""Luma starts talking at the first sentence instead of waiting for the whole reply."""
import json
import sys
import threading
import time
import types
import unittest
from unittest.mock import patch

from luma.llm.streaming import ReplyTextStream, SentenceBuffer


def chunks_of(text, size):
    return [text[i:i + size] for i in range(0, len(text), size)]


class ReplyStreamTests(unittest.TestCase):
    def collect(self, raw, size):
        out = []
        stream = ReplyTextStream(out.append)
        for chunk in chunks_of(raw, size):
            stream.feed(chunk)
        return "".join(out)

    def test_reply_text_streams_out_of_the_json_at_any_chunk_size(self):
        text = 'Rough one? Tell me "everything" \\ or nothing.\nI\'m here — café ☕ at 7 🥹'
        raw = json.dumps({"type": "reply", "text": text}, ensure_ascii=False)
        raw_ascii = json.dumps({"type": "reply", "text": text})
        for size in (1, 2, 3, 5, 64):
            with self.subTest(size=size):
                self.assertEqual(self.collect(raw, size), text)
                # Escaped emoji halves are dropped; they aren't spoken anyway.
                self.assertEqual(self.collect(raw_ascii, size), text.replace("🥹", ""))

    def test_tool_proposals_never_stream(self):
        raw = json.dumps({"type": "tool", "name": "messages.prepare", "arguments": {"recipient": "Maya", "body": "text that must not be read aloud"}})
        self.assertEqual(self.collect(raw, 3), "")


class SentenceBufferTests(unittest.TestCase):
    def test_first_sentence_is_released_early_then_phrases_are_grouped(self):
        buffer = SentenceBuffer()
        ready = []
        for piece in chunks_of("Rough one? Tell me about it. I can also just keep you company tonight. Or we can plan tomorrow.", 4):
            ready += buffer.feed(piece)
        ready += buffer.flush()
        self.assertEqual(ready[0], "Rough one?")
        self.assertEqual(" ".join(ready), "Rough one? Tell me about it. I can also just keep you company tonight. Or we can plan tomorrow.")
        self.assertTrue(all(len(p) >= 10 for p in ready))

    def test_decimals_and_times_are_not_split(self):
        buffer = SentenceBuffer()
        ready = buffer.feed("It costs $12.50 and opens at 9.30 tomorrow. ") + buffer.feed("See you") + buffer.flush()
        self.assertEqual(ready, ["It costs $12.50 and opens at 9.30 tomorrow.", "See you"])


class PlanStreamingTests(unittest.TestCase):
    def test_plan_emits_reply_words_while_generating(self):
        from luma.llm import inference
        raw = json.dumps({"type": "reply", "text": "Black. It hides scuffs and still looks sharp."})
        seen_at = []

        class FakeModel:
            def tokenize(self, data, add_bos=False):
                return data.split()

            def create_chat_completion(self, stream=False, **kwargs):
                assert stream
                for piece in chunks_of(raw, 6):
                    yield {"choices": [{"delta": {"content": piece}}]}
                    seen_at.append(len(heard))

        heard = []
        with patch.object(inference, "_load_model", return_value=FakeModel()):
            result = inference.plan([{"role": "user", "content": "black or white?"}], [], {}, "friend", on_text=heard.append)
        self.assertEqual(result["text"], "Black. It hides scuffs and still looks sharp.")
        self.assertEqual("".join(heard), result["text"])
        self.assertTrue(any(0 < n < len(heard) for n in seen_at), "words arrived before generation finished")


class SpeechStreamTests(unittest.TestCase):
    def test_speaking_starts_before_the_reply_is_finished(self):
        from luma import orchestrator
        spoken, started = [], threading.Event()

        def fake_speaker(phrases, agent, cancel_event=None, allow_muted=False):
            for phrase in phrases:
                spoken.append(phrase)
                started.set()

        agent = types.SimpleNamespace(on_result=None)
        stream = orchestrator.SpeechStream(agent, threading.Event(), speaker=fake_speaker)
        stream.feed("Rough one? ")
        stream.feed("Tell")
        self.assertTrue(started.wait(1), "first sentence plays while the model is still writing")
        stream.feed(" me about it.")
        self.assertTrue(stream.finish())
        self.assertEqual(spoken, ["Rough one?", "Tell me about it."])

    def test_nothing_streamed_means_the_caller_speaks_normally(self):
        from luma import orchestrator
        stream = orchestrator.SpeechStream(types.SimpleNamespace(), threading.Event(), speaker=lambda *a, **k: None)
        self.assertFalse(stream.finish())


if __name__ == "__main__":
    unittest.main()


class TtsStreamTests(unittest.TestCase):
    def test_speak_stream_plays_each_phrase_as_it_arrives(self):
        try:
            import sounddevice  # noqa: F401
        except OSError:
            sys.modules["sounddevice"] = types.SimpleNamespace()  # no audio hardware here
        import numpy as np
        from luma.audio import io, tts
        played, second_ready = [], threading.Event()

        def phrases():
            yield "Rough one?"
            self.assertTrue(second_ready.wait(2), "first phrase was synthesized before the second existed")
            yield "Tell me about it."

        def fake_samples(text, voice, should_stop, speed=None):
            if text == "Rough one?": second_ready.set()
            return np.full(10, 1000, dtype=np.int16), 24000

        def fake_play(chunks, should_stop=None):
            for pcm, rate in chunks: played.append(len(pcm))
            return True

        with patch.object(tts, "_samples", side_effect=fake_samples) as synth, patch.object(io, "play_chunks", side_effect=fake_play):
            self.assertTrue(tts.speak_stream(phrases()))
        self.assertEqual([c.args[0] for c in synth.call_args_list], ["Rough one?", "Tell me about it."])
        self.assertEqual(played, [10, 10])
