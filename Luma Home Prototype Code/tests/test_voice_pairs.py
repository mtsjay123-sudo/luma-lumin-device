"""The fifty pairs for a blind listen (scripts/voice_audition.py, --pairs; docs/GAME_PLAN.md, B6), with a stand-in for
the voice. Whether the toned one sounds better is for ears: nothing here says so."""
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import voice_audition  # noqa: E402
from luma.agent import style  # noqa: E402


def stand_in(words, pace=1.0):
    """A tone as long as the words would take at this pace."""
    n = int(len(words) * 0.06 * voice_audition.RATE / pace)
    return (0.2 * np.sin(np.arange(n) * 0.05)).astype(np.float32)


class ThePairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name) / "pairs"
        cls.key = voice_audition.pairs(stand_in, cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_fifty_pairs_ten_for_each_moment(self):
        self.assertEqual(len(voice_audition.PAIRS), 50)
        moods = [mood for mood, _ in voice_audition.PAIRS]
        self.assertEqual({m: moods.count(m) for m in set(moods)}, {"grief": 10, "upset": 10, "venting": 10, "playful": 10, "laughing": 10})
        self.assertEqual(len(list(self.out.glob("pair-*.wav"))), 50)

    def test_which_comes_first_is_shuffled_and_the_sheet_doesnt_say(self):
        firsts = list(self.key.values())
        self.assertGreater(firsts.count("a"), 15)
        self.assertGreater(firsts.count("b"), 15)
        sheet = (self.out / "SHEET.md").read_text()
        self.assertNotRegex(sheet, r"(?i)grief|upset|venting|playful|laughing|toned first|flat first")
        self.assertEqual(json.loads((self.out / "KEY.json").read_text())["toned"], self.key)

    def test_the_two_sayings_really_differ(self):
        """Someone hurting is spoken to more slowly; a laugh is answered quicker."""
        def seconds(text, mood):
            return len(voice_audition.said(stand_in, text, mood, False, True)) / voice_audition.RATE
        mood, text = voice_audition.PAIRS[0]
        self.assertGreater(seconds(text, mood), seconds(text, "neutral") * 1.05)
        mood, text = voice_audition.PAIRS[-1]
        self.assertLess(seconds(text, mood), seconds(text, "neutral") * 0.98)
        with wave.open(str(self.out / "pair-01.wav")) as f:
            self.assertGreater(f.getnframes() / f.getframerate(), 3)

    def test_nothing_luma_says_in_them_claims_a_life(self):
        for _, text in voice_audition.PAIRS:
            self.assertFalse(style.claims_human(text), text)
            self.assertNotRegex(text.lower(), r"\bmy (?:mom|dad|sister|brother|evening|day|job|house|dog|cat)\b", text)

    def test_the_tally(self):
        key = {"toned": {"01": "a", "02": "b", "03": "a", "04": "b", "05": "a"}}
        t = voice_audition.tally(key, "a b a - b".split())
        self.assertEqual((t["won"], t["of"], t["no_difference"], t["share"], t["passed"]), (3, 5, 1, 60, True))
        self.assertFalse(voice_audition.tally(key, "a b - - b".split())["passed"])
        with self.assertRaises(SystemExit):
            voice_audition.tally(key, ["a"])


if __name__ == "__main__":
    unittest.main()
