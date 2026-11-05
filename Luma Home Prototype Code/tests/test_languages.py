"""Luma talks in the owner's language: it hears which one they speak, answers in it, and says it in a voice made for it,
and its own lines (thinking out loud, sorry for cutting in) come in that language too. English stays the default, and
Spanglish, Taglish and friends stay English with their words."""
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from luma.agent import language


class LanguageTests(unittest.TestCase):
    def tearDown(self):
        language.configure("en")
        language._state.update(heard=None, heard_at=0.0)

    def test_the_choices(self):
        self.assertEqual(language.configure("auto"), "auto")
        self.assertIsNone(language.stt_language(), "follow me: speech-to-text works out the language")
        self.assertEqual(language.configure("es"), "es")
        self.assertEqual(language.stt_language(), "es")
        with self.assertRaises(ValueError):
            language.configure("klingon")

    def test_reading_a_typed_message(self):
        self.assertEqual(language.detect_text("hola, qué tal? estoy muy cansada hoy y no quiero cocinar"), "es")
        self.assertEqual(language.detect_text("je suis fatigué aujourd'hui, c'est la vie"), "fr")
        self.assertEqual(language.detect_text("oggi sono molto stanco, non ho voglia di cucinare"), "it")
        self.assertEqual(language.detect_text("hoje eu estou muito cansado e não quero cozinhar"), "pt")
        self.assertEqual(language.detect_text("今日はとても疲れたよ"), "ja")
        self.assertEqual(language.detect_text("我今天很累"), "zh")
        self.assertEqual(language.detect_text("मैं आज बहुत थका हूँ"), "hi")
        self.assertIsNone(language.detect_text("wey, after the festival vamos a janguear at the beach"), "Spanglish stays English")
        self.assertIsNone(language.detect_text("hola"), "one word isn't a language")
        self.assertIsNone(language.detect_text("what should i cook tonight"))

    def test_each_turn_has_a_language(self):
        self.assertEqual(language.for_turn("hola, qué tal? estoy muy cansada hoy"), "en", "English unless they choose otherwise")
        language.configure("auto")
        self.assertEqual(language.for_turn("hola, qué tal? estoy muy cansada hoy"), "es")
        language.heard("fr", 0.93)
        self.assertEqual(language.for_turn("ok"), "fr", "what speech-to-text heard counts for the turn")
        language.heard("de", 0.4)
        self.assertEqual(language.for_turn("what's up"), "en", "not sure enough, and a language Luma doesn't speak yet")
        language.configure("it")
        self.assertEqual(language.for_turn("what's up"), "it", "one language chosen: always that one")

    def test_the_brain_is_told_and_the_voice_follows(self):
        self.assertEqual(language.note("en"), "")
        self.assertIn("Answer in Spanish", language.note("es"))
        self.assertEqual(language.voice("es"), ("ef_dora", "es"))
        self.assertEqual(language.voice("ja"), ("jf_alpha", "ja"))
        language.configure("auto")
        language.for_turn("hola, qué tal? estoy muy cansada hoy y no quiero cocinar")
        self.assertEqual(language.of_reply("Claro, te entiendo. Pide algo rico y descansa."), "es")
        self.assertEqual(language.of_reply("Got it. I'll remind you to call the dentist tomorrow at 9."), "en",
                         "Luma's own built-in lines are English, so the English voice says them")
        self.assertEqual(language.of_reply("Claro."), "es")

    def test_its_own_lines_in_their_language(self):
        language.configure("auto")
        language.for_turn("hola, qué tal? estoy muy cansada hoy y no quiero cocinar")
        self.assertIn(language.filler("¿cuánto cuesta un ps5?"), language.PHRASES["checking"]["es"])
        self.assertIn(language.filler("¿qué piensas, debería cambiar de trabajo?"), language.PHRASES["thinking"]["es"])
        from luma.agent import turntaking
        self.assertIn(turntaking.sorry("x"), language.PHRASES["sorry"]["es"])
        language.configure("en")
        language.for_turn("how much is a ps5 right now")
        self.assertIn(language.filler("how much is a ps5 right now"), language.PHRASES["checking"]["en"])
        self.assertIn(language.filler("should i switch jobs?"), language.PHRASES["thinking"]["en"])
        said = language.filler("should i switch jobs?", seed="a")
        self.assertNotEqual(language.filler("should i switch jobs?", seed="a", avoid=(said,)), said, "not the one it just said")


class InTheConversationTests(unittest.TestCase):
    def tearDown(self):
        language.configure("en")

    def test_the_brain_hears_it_in_every_mode_and_the_app_sees_the_choice(self):
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        from luma.llm import prompts
        seen = {}
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                store.set_setting("language", "auto")
                agent = Agent(store=store, use_model=True, planner=lambda m, c, allowed, mode: seen.update(c=c) or {"type": "reply", "text": "¡Claro!"})
                agent.chat("hola, qué tal? estoy muy cansada hoy y no quiero cocinar nada")
                self.assertTrue(any(n.get("language") and "Spanish" in n["text"] for n in seen["c"]))
                steady, turn = prompts.build_plan_parts(seen["c"], {}, "kids", prompts.normalize_profile(None), "now")
                self.assertIn("Answer in Spanish", turn, "kids get their language too, though no memories")
                self.assertEqual(agent.status()["language"], "auto")
                self.assertTrue(agent.status()["thinking_out_loud"])
            finally:
                store.close()

    def test_speech_to_text_follows_the_choice(self):
        import importlib
        import sys
        import luma.audio as package
        before, had = sys.modules.get("luma.audio.stt"), package.__dict__.get("stt")
        try:
            with mock.patch.dict(sys.modules, {"faster_whisper": types.SimpleNamespace(WhisperModel=object)}):
                sys.modules.pop("luma.audio.stt", None)
                stt = importlib.import_module("luma.audio.stt")
                self._check_stt(stt)
        finally:
            if before is None: sys.modules.pop("luma.audio.stt", None)
            else: sys.modules["luma.audio.stt"] = before
            if had is None: package.__dict__.pop("stt", None)
            else: package.stt = had

    def _check_stt(self, stt):
        calls = []

        class Model:
            def __init__(self, name): self.name = name
            def transcribe(self, audio, **options):
                calls.append((self.name, options.get("language")))
                return iter([types.SimpleNamespace(text="hola, qué tal")]), types.SimpleNamespace(language="es", language_probability=0.97)

        wav = Path(tempfile.mkdtemp()) / "c.wav"
        import wave
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes((np.ones(16000) * 500).astype("<i2").tobytes())
        with mock.patch.object(stt, "_load", side_effect=Model), mock.patch.object(stt, "_model", None), mock.patch.object(stt, "_multi", None):
            stt.transcribe_clip(wav.read_bytes(), ".wav")
            self.assertEqual(calls[-1], ("base.en", "en"), "English: the English model, told it's English")
            language.configure("auto")
            stt.transcribe_clip(wav.read_bytes(), ".wav")
            self.assertEqual(calls[-1], ("base", None), "follow me: the multilingual model works it out")
            self.assertEqual(language.for_turn("hola, qué tal"), "es")

    def test_the_classic_voice_speaks_their_language(self):
        from luma.audio import tts
        made = []

        class Engine:
            def create(self, text, voice, speed, lang):
                made.append((voice, lang))
                return np.ones(2400, dtype=np.float32) * 0.1, 24000

        language.configure("auto")
        language.for_turn("hola, qué tal? estoy muy cansada hoy y no quiero cocinar")
        with mock.patch.object(tts, "_get_kokoro", return_value=Engine()), mock.patch("luma.audio.natural.speaking", return_value=False):
            tts._samples("Claro, te entiendo. Pide algo rico y descansa.", "luma", None)
            tts._samples("Got it. I'll remind you to call the dentist tomorrow at 9.", "luma", None)
        self.assertEqual(made, [("ef_dora", "es"), ("af_heart", "en-us")])


class ThinkingOutLoudTests(unittest.TestCase):
    def stream(self, said, setting=True, recent=False):
        from luma import orchestrator
        spoken = []
        agent = types.SimpleNamespace(store=types.SimpleNamespace(setting=lambda k, d=None: setting if k == "thinking_out_loud" else d), speaking=False)
        if recent:
            agent._filler_at = time.monotonic()
        stream = orchestrator.SpeechStream(agent, threading.Event(), speaker=lambda text, *a, **k: spoken.append(text))
        return stream.think_out_loud(said), spoken

    def test_a_slow_answer_gets_one_short_line(self):
        from luma import orchestrator
        with mock.patch.object(orchestrator, "FILLER_AFTER", 0.05):
            stream, spoken = self.stream("how much is a ps5 right now")
            time.sleep(0.2)
            stream.finish()
        self.assertEqual(len(spoken), 1)
        self.assertIn(spoken[0], language.PHRASES["checking"]["en"])

    def test_no_line_when_the_answer_comes_in_time_or_its_off(self):
        from luma import orchestrator
        with mock.patch.object(orchestrator, "FILLER_AFTER", 0.05):
            stream, spoken = self.stream("should i switch jobs?")
            stream.feed("Honestly")
            time.sleep(0.15)
            stream.finish(wait=False)
            self.assertEqual(spoken, [], "the words are already coming")
            stream, spoken = self.stream("should i switch jobs?")
            stream.finish()
            time.sleep(0.15)
            self.assertEqual(spoken, [], "the answer was done first")
            stream, spoken = self.stream("should i switch jobs?", setting=False)
            time.sleep(0.15)
            self.assertEqual(spoken, [], "Think out loud is off")
        with mock.patch.object(orchestrator, "FILLER_AFTER", 0.05), mock.patch.object(orchestrator, "FILLER_AGAIN", 0.4):
            stream, spoken = self.stream("should i switch jobs?", recent=True)
            time.sleep(0.15)
            self.assertEqual(spoken, [], "it just said one, so it waits longer this time")
            stream.finish()


if __name__ == "__main__":
    unittest.main()
