"""The voice check scores what Whisper heard against what Luma meant to say, without counting
different spellings of the same words ("24th" and "twenty-fourth", "gotcha" and "gotchu") as mistakes."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("voice_check", Path(__file__).resolve().parents[1] / "scripts" / "voice_check.py")
voice_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice_check)


class VoiceCheckTests(unittest.TestCase):
    def test_same_words_written_differently(self):
        self.assertEqual(voice_check.word_error_rate("It's Saturday, October twenty-fourth.", "It's Saturday, October 24th."), 0)
        self.assertEqual(voice_check.word_error_rate("If you just want my answer right now, I gotchu.", "if you just want my answer right now, I got you"), 0)
        self.assertEqual(voice_check.word_error_rate("Hmm, okay. Bet.", "OK. Bet!"), 0)

    def test_skipped_and_extra_words_count(self):
        self.assertAlmostEqual(voice_check.word_error_rate("take your time I'm right here", "take your time"), 0.5)
        self.assertGreater(voice_check.word_error_rate("bet", "bet bet bet bet and then some more words"), 1)


if __name__ == "__main__":
    unittest.main()
