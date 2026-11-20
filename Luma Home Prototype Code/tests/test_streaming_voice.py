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
        # Each phrase plays as it arrives, followed by a natural pause: a little longer after a question.
        self.assertEqual(len(played), 2)
        self.assertTrue(all(n > 10 for n in played))
        self.assertGreater(played[0], played[1])


class FirstClauseTests(unittest.TestCase):
    """The voice may start at the reply's first clause instead of its first whole sentence (off unless turned on)."""

    def said(self, text, **kwargs):
        buffer, out = SentenceBuffer(**kwargs), []
        for char in text:
            out += buffer.feed(char)
        return out + buffer.flush()

    def test_off_by_default_nothing_changes(self):
        self.assertEqual(self.said("Oh no, that's awful. Tell me what happened."), ["Oh no, that's awful.", "Tell me what happened."])

    def test_the_first_clause_is_spoken_first_and_only_the_first(self):
        got = self.said("Oh no, that's awful, truly. Tell me what happened, all of it, start to finish, slowly.", first_clause=True)
        self.assertEqual(got[0], "Oh no,")
        self.assertEqual(got[1], "that's awful, truly.", "after the first clause, whole sentences again")
        self.assertEqual(" ".join(got), "Oh no, that's awful, truly. Tell me what happened, all of it, start to finish, slowly.")

    def test_never_inside_a_number_or_after_one_short_word(self):
        self.assertEqual(self.said("That's 1,000 steps already. Nice.", first_clause=True)[0], "That's 1,000 steps already.")
        self.assertEqual(self.said("So, how did it go? Tell me.", first_clause=True)[0], "So, how did it go?")
        self.assertEqual(self.said("I, for one, am proud of you. Really.", first_clause=True)[0], "I, for one,")

    def test_nothing_is_lost_or_said_twice(self):
        import json
        import random
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import finetune_data
        texts = set()

        def walk(node):
            if isinstance(node, dict):
                if node.get("role") == "assistant" and isinstance(node.get("content"), str):
                    try:
                        data = json.loads(node["content"])
                        if isinstance(data, dict) and data.get("type") == "reply" and isinstance(data.get("text"), str):
                            texts.add(data["text"])
                    except ValueError:
                        if len(node["content"]) < 400:
                            texts.add(node["content"])  # a reply written out plainly
                for value in node.values():
                    walk(value)
            elif isinstance(node, (list, tuple)):
                for value in node:
                    walk(value)

        walk(finetune_data.examples(random.Random(7)))
        texts = sorted(t for t in texts if len(t.split()) >= 4)
        self.assertGreater(len(texts), 1000)
        squash = lambda s: "".join(s.split())  # noqa: E731
        sooner = 0
        for text in texts:
            early, whole = self.said(text, first_clause=True), self.said(text)
            self.assertEqual(squash("".join(early)), squash(text))
            sooner += len(early[0]) < len(whole[0])
        self.assertGreater(sooner, len(texts) // 3, f"{sooner} of {len(texts)} of Luma's practice replies start sooner")
