"""Luma says things the way people say them: shorthand in full, laughs as laughs, and real pauses."""
import unittest
from unittest.mock import patch

import numpy as np

from luma.audio import speakable, tts


class SpeakableTests(unittest.TestCase):
    def test_texting_shorthand_is_said_in_full(self):
        self.assertEqual(speakable.say_it("ngl gng how hard you want me to think about this"),
                         "Not gonna lie, gang, how hard you want me to think about this")
        self.assertEqual(speakable.say_it("idk fr, ion know what he was thinking"), "I don't know for real, I don't know what he was thinking")
        self.assertEqual(speakable.say_it("U good?"), "You good?")
        self.assertEqual(speakable.say_it("tbh I think so"), "To be honest, I think so")

    def test_ordinary_letters_are_left_alone(self):
        for text in ["The U.S. economy grew", "Model FR-8 is ready", "Plan DEF is next"]:
            self.assertEqual(speakable.say_it(text), text)

    def test_laughs_and_sighs(self):
        self.assertIn(speakable.LAUGH, speakable.say_it("that's crazy 😭😭 lmaooo"))
        self.assertEqual(speakable.say_it("that's crazy 😭😭 lmaooo").count(speakable.LAUGH), 1)  # one laugh, not three
        self.assertIn(speakable.SIGH, speakable.say_it("smh he did it again"))
        self.assertEqual(speakable.say_it("good morning ☀️🌸"), "Good morning")

    def test_an_expressive_voice_laughs_and_the_plain_one_takes_a_beat(self):
        text = "honestly that's the whole story lol. Anyway, you good?"
        plain = tts.speech_plan(text)
        expressive = tts.speech_plan(text, expressive=True)
        self.assertNotIn("[laugh]", " ".join(p for p, _ in plain))
        self.assertIn(("[laugh]"), [p for p, _ in expressive])
        self.assertGreater(plain[0][1], 400)  # the beat where the laugh would be

    def test_people_pause_where_people_pause(self):
        plan = tts.speech_plan("Okay so, the Fed held rates steady today. Stocks went up a little... that's it.\n\nWant more?")
        words = [p for p, _ in plan]
        self.assertEqual(words[0], "Okay so,")
        self.assertLess(plan[0][1], 250)                       # a quick beat after the opener
        ellipsis = next(ms for p, ms in plan if p.endswith("a little"))
        self.assertGreater(ellipsis, 450)                      # a longer one at the "..."
        paragraph = next(ms for p, ms in plan if p.endswith("that's it."))
        self.assertGreater(paragraph, 520)                     # the most between paragraphs
        self.assertEqual(plan, tts.speech_plan("Okay so, the Fed held rates steady today. Stocks went up a little... that's it.\n\nWant more?"))

    def test_pauses_are_real_silence_in_the_audio(self):
        with patch.object(tts, "_samples", return_value=(np.ones(2400, dtype=np.int16), 24000)):
            pcm, rate = tts._with_pause(tts._samples("x", "luma", None), 500)
        self.assertEqual(len(pcm), 2400 + 12000)
        self.assertFalse(pcm[2400:].any())

    def test_only_an_emoji_has_nothing_to_say(self):
        with self.assertRaises(ValueError):
            tts.speech_plan("😂😂")


if __name__ == "__main__":
    unittest.main()
