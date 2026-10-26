import re
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

    def test_thinking_sounds_come_now_and_then_where_a_person_would(self):
        crisp = ["Got it. I'll remind you to hit the gym at six tonight, right on time.", "I'm really glad you told me, call or text 988 right now please.",
                 "Here's the text for Mom: im pullin up in five, ready for you to send."]
        for line in crisp:
            self.assertEqual(speakable.think_aloud(line), line)  # confirmations and hard moments stay crisp
        colors = ["black", "white", "blue", "green", "red", "gray", "navy", "tan", "olive", "cream", "pink", "brown", "silver", "gold",
                  "purple", "orange", "yellow", "beige", "maroon", "teal", "coral", "plum", "rust", "sage", "khaki", "ivory", "denim", "mint",
                  "lilac", "peach", "sand", "slate", "wine", "copper", "pearl", "smoke", "moss", "clay", "ash", "honey"]
        opinions = [f"I'd go with the {c} one, it goes with everything you already wear a lot." for c in colors]
        thought = [speakable.think_aloud(o) for o in opinions]
        changed = [t for t, o in zip(thought, opinions) if t != o]
        self.assertTrue(0.15 * len(opinions) <= len(changed) <= 0.55 * len(opinions), len(changed))  # now and then, not every line
        for t in changed:
            self.assertEqual(len(re.findall(r"(?i)\b(?:hmm+|uh|um|mm)\b|okay so", t)), 1, t)  # one per reply, at most
        self.assertEqual(thought, [speakable.think_aloud(o) for o in opinions])  # the same words always sound the same
        original = opinions[thought.index(changed[0])]
        self.assertRegex(" ".join(w for w, _ in tts.speech_plan(original)), r"(?i)\b(?:hmm+|uh|um|mm)\b|okay so")
        plain = tts.speech_plan(original, natural=False)
        self.assertNotRegex(" ".join(w for w, _ in plain), r"(?i)\b(?:hmm+|uh|um|mm)\b|okay so")

if __name__ == "__main__":
    unittest.main()
