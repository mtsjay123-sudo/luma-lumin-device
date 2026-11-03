"""Talking like a friend: Luma goes quiet the moment it's talked over, says sorry and answers the whole thought when it
jumped in too early, says "mm-hm" when someone pauses mid-thought, checks what they mean after they've said a lot
(only when it isn't clear), and takes a soft breath before a long sentence."""
import importlib
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from luma.agent import turntaking
from luma.audio import breath, turn


class CutOffTests(unittest.TestCase):
    def test_jumping_in_too_early_is_noticed(self):
        self.assertTrue(turntaking.cut_them_off(0.8, "So I was thinking about the trip.", "and whether we should leave Friday instead"))
        self.assertTrue(turntaking.cut_them_off(3.0, "Remind me to call", "my sister tomorrow at noon"), "a sentence left hanging")
        self.assertTrue(turntaking.cut_them_off(3.0, "I want to switch jobs.", "but I'm scared of the pay cut"), "they carried on with 'but'")

    def test_a_new_request_or_a_late_interruption_is_just_that(self):
        self.assertFalse(turntaking.cut_them_off(3.0, "Tell me about the Fed.", "what time is it"))
        self.assertFalse(turntaking.cut_them_off(0.5, "Tell me about the Fed.", "Luma, set a timer for ten minutes"))
        self.assertFalse(turntaking.cut_them_off(9.0, "Tell me a story.", "and make it funny"), "Luma was well into it: an interruption")
        self.assertFalse(turntaking.cut_them_off(None, "Hi.", "and also"), "Luma wasn't talking")

    def test_the_whole_thought_comes_back_together(self):
        self.assertEqual(turntaking.together("Remind me to call", "my sister tomorrow."), "Remind me to call, my sister tomorrow.")
        self.assertEqual(turntaking.together("I want to switch jobs.", "But I'm scared of the pay cut."),
                         "I want to switch jobs but I'm scared of the pay cut.")

    def test_a_quick_sorry_the_same_for_the_same_words(self):
        said = turntaking.sorry("trip friday")
        self.assertIn(said, turntaking.SORRY)
        self.assertEqual(said, turntaking.sorry("trip friday"))

    def test_after_saying_a_lot_luma_checks_only_if_it_isnt_clear(self):
        long = " ".join(["so my manager keeps moving my deadlines and I don't know if I should say something"] * 6) + "?"
        note = turntaking.turn_note(long)
        self.assertIn("Wait, just so I've got it", note)
        self.assertIn("If it is clear, just answer", note)
        self.assertIn("Never repeat everything back", note)
        self.assertEqual(turntaking.turn_note("what's the weather tomorrow?"), "")

    def test_the_note_reaches_the_brain(self):
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                agent = Agent(store=store, use_model=False)
                notes = agent._mind_context(" ".join(["I keep going back and forth about moving to Denver for the job"] * 8))
                self.assertTrue(any("just so I've got it" in n["text"] for n in notes))
            finally:
                store.close()


class BreathTests(unittest.TestCase):
    def voice(self, seconds=1.5, rate=24_000):
        t = np.arange(int(rate * seconds)) / rate
        return (np.sin(2 * np.pi * 180 * t) * 9000).astype(np.int16)

    def test_only_before_a_long_sentence_after_a_real_pause(self):
        long = "I think the second one is better because it's lighter and it lasts longer"
        self.assertTrue(breath.wanted(long, 300, 5))
        self.assertFalse(breath.wanted("Okay, got it.", 300, 5), "short phrases don't need the air")
        self.assertFalse(breath.wanted(long, 120, 5), "not in the middle of a thought")
        self.assertFalse(breath.wanted(long, 300, 1), "not twice in a row")

    def test_a_soft_inhale_well_under_the_voice(self):
        rate = 24_000
        near = self.voice()
        air = breath.inhale(rate, near, seed="hello")
        self.assertEqual(len(air), int(rate * breath.MS / 1000))
        voice_db = 20 * np.log10(np.sqrt(np.mean(near.astype(float) ** 2)))
        air_db = 20 * np.log10(np.sqrt(np.mean(air.astype(float) ** 2)))
        self.assertAlmostEqual(voice_db - air_db, breath.BELOW_VOICE_DB, delta=1.5)
        spectrum = np.abs(np.fft.rfft(air.astype(float)))
        centroid = float((np.fft.rfftfreq(len(air), 1 / rate) * spectrum).sum() / spectrum.sum())
        self.assertTrue(600 < centroid < 3000, centroid)
        self.assertTrue((air == breath.inhale(rate, near, seed="hello")).all(), "the same words, the same breath")
        self.assertLess(abs(int(air[0])) + abs(int(air[-1])), 200, "it fades in and out, no click")

    def test_never_before_the_first_words_or_in_an_expressive_voice(self):
        from luma.audio import tts
        long = "I think the second one is better because it's lighter and it lasts longer"
        pcm = self.voice()
        with mock.patch.object(tts, "expressive_now", return_value=False):
            out, since = tts._breathe(long, pcm, 24_000, 300, 5, first=True)
            self.assertEqual(len(out), len(pcm), "the first words never wait for a breath")
            out, since = tts._breathe(long, pcm, 24_000, 300, 5)
            self.assertGreater(len(out), len(pcm))
            self.assertEqual(since, 0)
        with mock.patch.object(tts, "expressive_now", return_value=True):
            self.assertEqual(len(tts._breathe(long, pcm, 24_000, 300, 5)[0]), len(pcm), "expressive voices breathe on their own")


class ListeningTests(unittest.TestCase):
    """The real listening loop, with a scripted mic and VAD."""

    def run_loop(self, events, chunks, decisions, speaking=False, **hooks):
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
                    for _ in range(chunks):
                        self.callback(np.full((512, 1), 1000, dtype=np.int16), 512, None, None)
                        threading.Event().wait(0.002)
                    threading.Event().wait(0.3)
                    stop.set()
                threading.Thread(target=feed, daemon=True).start()
                return self
            def __exit__(self, *a): return False

        fakes = {"sounddevice": types.SimpleNamespace(InputStream=InputStream, query_devices=lambda *a, **k: []),
                 "torch": types.SimpleNamespace(from_numpy=lambda a: a),
                 "silero_vad": types.SimpleNamespace(VADIterator=lambda *a, **k: VAD(), load_silero_vad=lambda: object())}
        heard, answers = [], iter(decisions)
        import luma.audio as package
        before = package.__dict__.get("vad")
        try:
            with mock.patch.dict(sys.modules, fakes):
                sys.modules.pop("luma.audio.vad", None)
                vad = importlib.import_module("luma.audio.vad")
                vad.set_speaking(speaking)
                with mock.patch.object(turn, "model", return_value=object()), mock.patch.object(turn, "finished", lambda audio: next(answers, True)), \
                        mock.patch("luma.audio.echo.canceller", return_value=None), mock.patch.object(vad, "resolve_audio_device", return_value=None):
                    vad.start_listening(lambda path: heard.append(path), stop, allow_barge_in=True, **hooks)
                vad.set_speaking(False)
        finally:
            if before is None: package.__dict__.pop("vad", None)
            else: package.vad = before
        for path in heard:
            Path(path).unlink()
        return heard

    def test_mm_hm_when_they_pause_mid_thought_after_talking_a_while(self):
        said = []
        heard = self.run_loop({3: {"start": 0}, 110: {"end": 0}, 113: {"start": 0}, 120: {"end": 0}}, 130, [False, True],
                              on_pause=lambda: said.append("mm-hm"))
        self.assertEqual(said, ["mm-hm"], "once, at the pause the model heard as unfinished")
        self.assertEqual(len(heard), 1, "and it's still one turn")

    def test_no_mm_hm_for_a_short_pause_early_on(self):
        said = []
        self.run_loop({3: {"start": 0}, 20: {"end": 0}, 23: {"start": 0}, 30: {"end": 0}}, 40, [False, True], on_pause=lambda: said.append("mm-hm"))
        self.assertEqual(said, [])

    def test_luma_goes_quiet_the_moment_its_talked_over(self):
        stopped = []
        self.run_loop({3: {"start": 0}, 20: {"end": 0}}, 30, [True], speaking=True, on_barge_in=lambda: stopped.append(True))
        self.assertEqual(stopped, [True])


if __name__ == "__main__":
    unittest.main()
