"""Luma says its reply the way you said yours: gentler and slower when you're hurting, lighter when you're laughing."""
import unittest
from unittest import mock

from luma.audio import feel, tts


class FeelTests(unittest.TestCase):
    def tearDown(self):
        feel.reset()

    def test_it_matches_how_they_said_it(self):
        self.assertEqual(feel.set_from("my grandma passed away this morning", now=100.0), "grief")
        self.assertLess(feel.pace(1.0, now=101.0), 0.95)
        self.assertGreater(feel.pause(400, now=101.0), 500)
        self.assertEqual(feel.set_from("LMAOOO bro that's crazy 😭", now=200.0), "laughing")
        self.assertGreater(feel.pace(1.0, now=201.0), 1.0)
        self.assertLess(feel.pause(400, now=201.0), 400)
        feel.set_from("set a timer for ten minutes", now=300.0)
        self.assertEqual(feel.pause(400, now=301.0), 380)

    def test_it_goes_back_to_normal_after_the_reply(self):
        feel.set_from("i'm so sad, we broke up", now=0.0)
        self.assertNotEqual(feel.mood(now=10.0), "neutral")
        self.assertEqual(feel.mood(now=feel.LASTS + 1), "neutral", "a reminder an hour later isn't said in a sad voice")
        self.assertEqual(feel.pace(1.03, now=feel.LASTS + 1), 1.03)

    def test_it_stays_in_the_range_the_voice_can_do(self):
        feel.set_mood("grief", now=0.0)
        self.assertEqual(feel.pace(0.5, now=1.0), 0.5)
        feel.set_mood("laughing", now=0.0)
        self.assertEqual(feel.pace(1.5, now=1.0), 1.5)
        feel.set_mood("not a mood", now=0.0)
        self.assertEqual(feel.mood(now=1.0), "neutral")

    def test_the_spoken_reply_takes_it_on(self):
        text = "I'm so sorry. That's a lot to carry. I'm right here, take your time."
        normal = tts.speech_plan(text, natural=False)
        feel.set_mood("grief")
        gentle = tts.speech_plan(text, natural=False)
        self.assertEqual([w for w, _ in normal], [w for w, _ in gentle], "only the delivery changes, never the words")
        self.assertGreater(sum(ms for _, ms in gentle), sum(ms for _, ms in normal))

        class Kokoro:
            def create(self, text, voice, speed, lang):
                self.speed = speed
                import numpy as np
                return np.full(2400, 0.1, dtype=np.float32), 24000
        engine = Kokoro()
        with mock.patch.object(tts, "_get_kokoro", return_value=engine), mock.patch("luma.audio.natural.speaking", return_value=False):
            tts._samples("Take your time.", "luma", None, speed=1.0)
        self.assertLess(engine.speed, 0.95, "the classic voice slows down a little for them")


if __name__ == "__main__":
    unittest.main()
