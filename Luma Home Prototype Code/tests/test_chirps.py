"""Luma's own sounds (luma.audio.chirps): short, quiet, never on a safety reply or with someone hurting, off by default."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from luma.audio import chirps  # noqa: E402


class TheSounds(unittest.TestCase):
    def test_each_is_short_quiet_and_starts_and_ends_without_a_click(self):
        self.assertEqual(sorted(chirps.SOUNDS), ["curious", "delight", "hello", "night", "soft", "yes"])
        for name in chirps.SOUNDS:
            s = chirps.sound(name)
            self.assertEqual(s.dtype, np.float32)
            self.assertLess(len(s) / chirps.RATE, 1.05, name)
            self.assertGreater(len(s) / chirps.RATE, 0.15, name)
            self.assertLessEqual(float(np.abs(s).max()), chirps.LOUD + 1e-6, name)     # under the voice; the alarm's chime is 0.4
            self.assertLess(abs(float(s[0])), 0.01, name)
            self.assertLess(abs(float(s[-1])), 0.01, name)
            self.assertTrue(np.isfinite(s).all())
        self.assertEqual(len(chirps.sound("no such sound")), 0)

    def test_a_done_sound_rises_and_a_rough_day_sound_falls(self):
        first = lambda name: chirps.SOUNDS[name][0][0][0]   # noqa: E731
        last = lambda name: chirps.SOUNDS[name][0][-1][1]   # noqa: E731
        for name in ("yes", "delight", "curious"):
            self.assertGreater(last(name), first(name), name)
        for name in ("soft", "night"):
            self.assertLess(last(name), first(name), name)


class WhenThereIsOne(unittest.TestCase):
    def test_what_each_is_for(self):
        self.assertEqual(chirps.for_reply("Goodnight. Sleep well.", "neutral"), "night")
        self.assertEqual(chirps.for_reply("Good morning. Sleep okay?", "neutral"), "hello")
        self.assertEqual(chirps.for_reply("You got cut off after “and then”. Then what?", "neutral"), "curious")
        done = [f"Got it. I'll remind you to call {name} at {hour}." for name in ("Sam", "Mom", "Dana", "Lee", "Kai", "Noor") for hour in ("five", "six", "seven", "noon", "nine")]
        got = [chirps.for_reply(line, "task") for line in done]
        self.assertTrue(set(got) <= {"yes", None})
        self.assertTrue(0.35 <= got.count("yes") / len(got) <= 0.85, got.count("yes"))    # most times, not every time
        glad = [f"Ha, that's the best thing I've heard all {day}. Tell me everything." for day in ("day", "week", "month", "morning", "evening", "year", "night", "weekend", "afternoon", "season")]
        self.assertTrue(set(chirps.for_reply(line, "laughing") for line in glad) <= {"delight", None})
        self.assertIsNone(chirps.for_reply("I'd go with the blue one, it goes with more.", "neutral"))    # ordinary talk gets none

    def test_never_on_a_safety_reply_and_never_with_someone_hurting(self):
        for line in ("I'm really glad you told me. Are you safe right now? You can call or text 988 any time.",
                     "Got it. I'm staying right here with you. Call 988 or text it.", "Okay, I'll stay. If it gets worse, 119 or 0570-064-556 will answer."):
            for mood in ("neutral", "task", "laughing", "venting"):
                self.assertIsNone(chirps.for_reply(line, mood), line)
        for mood in ("grief", "upset", "serious"):
            for line in ("Got it. I'll remind you at six.", "Good morning.", "Goodnight.", "Ha, that's great."):
                self.assertIsNone(chirps.for_reply(line, mood), (mood, line))

    def test_the_same_reply_always_gets_the_same_answer(self):
        for line in ("Got it. I'll remind you at six.", "Done. It's on your list.", "Saved."):
            self.assertEqual(chirps.for_reply(line, "task"), chirps.for_reply(line, "task"))


class BeforeTheWords(unittest.TestCase):
    def agent(self, on):
        return SimpleNamespace(store=SimpleNamespace(setting=lambda key, default=None: on if key == "own_sounds" else default), mode="friend")

    def test_off_until_the_owner_says_so(self):
        from luma import orchestrator
        played = []
        text = "Goodnight. Sleep well."
        self.assertEqual(orchestrator._own_sound_first(text, self.agent(False), lambda: False, play=lambda blocks, stop: played.append(list(blocks))), text)
        self.assertEqual(played, [])

    def test_on_its_played_first_and_every_word_is_still_said(self):
        from luma import orchestrator
        from luma.audio import feel
        feel.reset()
        played = []
        play = lambda blocks, stop: played.append(list(blocks))   # noqa: E731
        text = "Goodnight. Sleep well."
        self.assertEqual(orchestrator._own_sound_first(text, self.agent(True), lambda: False, play=play), text)
        self.assertEqual(len(played), 1)
        self.assertEqual(len(played[0][0]), len(chirps.sound("night")))
        phrases = orchestrator._own_sound_first(iter(["Goodnight.", "Sleep well."]), self.agent(True), lambda: False, play=play)
        self.assertEqual(list(phrases), ["Goodnight.", "Sleep well."])     # the first phrase is put back
        self.assertEqual(len(played), 2)
        self.assertEqual(list(orchestrator._own_sound_first(iter([]), self.agent(True), lambda: False, play=play)), [])

    def test_nothing_is_played_once_theyve_cut_in_and_a_broken_speaker_loses_no_reply(self):
        from luma import orchestrator
        played = []
        text = "Goodnight. Sleep well."
        self.assertEqual(orchestrator._own_sound_first(text, self.agent(True), lambda: True, play=lambda blocks, stop: played.append(1)), text)
        self.assertEqual(played, [])

        def broken(blocks, stop):
            raise OSError("no sound device")

        self.assertEqual(orchestrator._own_sound_first(text, self.agent(True), lambda: False, play=broken), text)


class SaidOutLoud(unittest.TestCase):
    def setUp(self):
        from luma.agent import athome
        from luma.memory.store import Store
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.played = []
        player = SimpleNamespace(play_samples=lambda sounds, gap=0.0: self.played.append(len(sounds)), busy=lambda: False, stop=lambda: None)
        self.home = athome.AtHome(self.store, player=player) if hasattr(athome, "AtHome") else None

    def tearDown(self):
        self.temp.cleanup()

    def test_hear_them_turn_them_on_turn_them_off(self):
        from luma.agent import athome
        for line in ("let me hear your sounds", "what do you sound like", "play me your chirps"):
            self.assertTrue(athome.HEAR_SOUNDS.match(line), line)
        for line in ("use your sounds", "turn on your chirps"):
            self.assertTrue(athome.USE_SOUNDS.match(line), line)
        for line in ("stop using your sounds", "no more chirps", "stop beeping"):
            self.assertTrue(athome.NO_SOUNDS.match(line), line)
        for line in ("play some rain sounds", "what does a whale sound like", "turn off the sound", "stop the music", "use your head", "that sounds good"):
            self.assertFalse(athome.HEAR_SOUNDS.match(line) or athome.USE_SOUNDS.match(line) or athome.NO_SOUNDS.match(line), line)
        if self.home is None:
            self.skipTest("the home-speaker class has another name here")
        self.assertFalse(self.store.setting("own_sounds", False))            # off to begin with
        out = self.home.handle("let me hear your sounds")
        self.assertEqual(self.played, [len(chirps.SOUNDS)])
        self.assertIn("use your sounds", out["text"])
        self.assertIn("now and then", self.home.handle("use your sounds")["text"])
        self.assertTrue(self.store.setting("own_sounds", False))
        self.assertEqual(self.home.handle("stop using your sounds")["text"], "Okay, just words from now on.")
        self.assertFalse(self.store.setting("own_sounds", False))


if __name__ == "__main__":
    unittest.main()
