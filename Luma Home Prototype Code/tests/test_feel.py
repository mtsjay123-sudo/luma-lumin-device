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

    def test_no_thinking_sounds_when_theyre_hurting(self):
        from luma.audio import speakable
        text = "The green one is probably better for you since it lasts longer and it is a lot quieter at night."
        self.assertNotEqual(speakable.think_aloud(text), text, "a sentence that gets a thinking sound")
        self.assertNotEqual(" ".join(w for w, _ in tts.speech_plan(text)), " ".join(w for w, _ in tts.speech_plan(text, natural=False)))
        feel.set_mood("grief")
        self.assertEqual([w for w, _ in tts.speech_plan(text)], [w for w, _ in tts.speech_plan(text, natural=False)])

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


class AStumbleNowAndThen(unittest.TestCase):
    """Starting a sentence twice, or a breath before the part that matters (speakable.stumble). Rare, one per reply at
    most, never on anything crisp or hard, and the words themselves never change."""

    @classmethod
    def setUpClass(cls):
        import random
        from luma.audio import speakable
        cls.sp = speakable
        starts = ["I think", "I'd go with", "It's", "That's", "You could try", "We could do", "There's", "This is", "Honestly it's", "The thing is it's", "Maybe it's"]
        mids = ["a pretty good plan for the weekend", "the kind of thing that takes a while to settle", "not as bad as it sounded at first",
                "worth trying once before you decide", "a lot to carry on a regular tuesday", "the better of the two if money is tight"]
        tails = [", but the other one has its charm too", ", because you already did the hard part", ", though it depends on how tired you are",
                 " and you can always change your mind later", ", which is honestly what most people forget", ""]
        rng = random.Random(1)
        cls.lines = sorted({f"{rng.choice(starts)} {rng.choice(mids)}{rng.choice(tails)}." for _ in range(3000)})
        cls.out = [(line, speakable.think_aloud(line)) for line in cls.lines]

    @staticmethod
    def kind(line, out):
        import re
        if out == line:
            return "clean"
        if re.match(r"^(\S+)(?:,|\.\.\.) \1\b", out, re.I):
            return "twice"
        if re.match(r"(?i)^(?:hmm|mm|uh|okay so)", out) or ", um," in out or "... uh," in out or ", like," in out:
            return "sound"
        return "breath"

    def test_its_rare_and_most_replies_are_said_clean(self):
        import collections
        got = collections.Counter(self.kind(line, out) for line, out in self.out)
        n = len(self.out)
        self.assertGreater(got["twice"], 0)
        self.assertGreater(got["breath"], 0)
        self.assertLess(got["twice"] / n, 0.08, got)          # about one reply in fourteen that could take it, at most
        self.assertLess(got["breath"] / n, 0.09, got)
        self.assertGreater(got["clean"] / n, 0.5, got)

    def test_one_at_most_and_the_words_never_change(self):
        import re
        plain = lambda t: re.sub(r"[^a-z' ]", " ", t.lower()).split()  # noqa: E731
        for line, out in self.out:
            kind = self.kind(line, out)
            if kind == "twice":
                self.assertEqual(plain(out)[1:], plain(line), out)      # the first word said again, nothing else
            elif kind == "breath":
                self.assertEqual(plain(out), plain(line), out)          # only a longer pause
                self.assertEqual(out.count("..."), line.count("...") + 1, out)
            self.assertLessEqual(len(re.findall(r"\b(?:um|uh|hmm+|mm)\b", out, re.I)) + (kind in ("twice", "breath")), 1, out)

    def test_the_same_words_are_always_said_the_same_way(self):
        for line, out in self.out[:200]:
            self.assertEqual(self.sp.think_aloud(line), out)

    def test_never_on_a_reminder_a_number_a_safety_reply_or_a_hard_moment(self):
        from unittest import mock
        from luma.audio import tts
        crisp = ["Got it. I'll remind you to call your sister tomorrow evening after work, okay.",
                 "I'm really glad you told me. Are you safe right now? You can call or text 988 any time, and I'm staying right here.",
                 "It's 42 degrees and raining in Chicago for the rest of the day today, so bring a coat.",
                 "Your mom's birthday is June 3, and you said she wants the blue scarf this year."]
        for line in crisp:
            self.assertEqual(self.sp.think_aloud(line), line)
            self.assertIsNone(self.sp.stumble(line) if self.sp.CRISP.match(line) else None)
        stumbled = next(line for line, out in self.out if self.kind(line, out) == "twice")
        with mock.patch("luma.audio.feel.mood", return_value="grief"):    # with someone hurting, nothing is added
            self.assertEqual(" ".join(w for w, _ in tts.speech_plan(stumbled)), " ".join(w for w, _ in tts.speech_plan(stumbled, natural=False)))
