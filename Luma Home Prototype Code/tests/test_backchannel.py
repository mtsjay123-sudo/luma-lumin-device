"""Back-and-forth like a person: a soft "mm-hm" lands at a short pause inside a long turn (not at the start, not every second),
it never ends up in what they said, and talking over Luma turns on by itself only when its mic can't hear its own voice."""
import unittest

import numpy as np

from luma.audio import backchannel


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class PauseWatchTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.watch = backchannel.PauseWatch(rate=16000, chunk=512, clock=self.clock)
        self.loud = (np.ones(512) * 3000).astype(np.int16)
        self.quiet = np.zeros(512, dtype=np.int16)

    def feed(self, chunk, seconds):
        moments = 0
        for _ in range(int(seconds / self.watch.step)):
            self.clock.now += self.watch.step
            moments += self.watch.feed(chunk)
        return moments

    def test_a_pause_inside_a_long_turn(self):
        self.assertEqual(self.feed(self.loud, 2.0) + self.feed(self.quiet, 0.6), 0)  # two seconds in: too soon to say anything
        self.assertEqual(self.feed(self.loud, 3.0), 0)
        self.assertEqual(self.feed(self.quiet, 0.6), 1)  # talked five seconds, paused: once, not every chunk of the pause

    def test_not_again_right_away(self):
        self.feed(self.loud, 5.0)
        self.assertEqual(self.feed(self.quiet, 0.5), 1)
        self.assertEqual(self.feed(self.loud, 1.0) + self.feed(self.quiet, 0.5), 0)  # a second later: that'd be too much
        self.assertEqual(self.feed(self.loud, 6.0) + self.feed(self.quiet, 0.5), 1)

    def test_a_new_turn_starts_over(self):
        self.feed(self.loud, 5.0)
        self.watch.start()
        self.assertEqual(self.feed(self.quiet, 0.5), 0)


class CleanTests(unittest.TestCase):
    def test_listening_sounds_come_out(self):
        self.assertEqual(backchannel.clean("So I went to the store, mm-hm, and they were closed."), "So I went to the store, and they were closed.")
        self.assertEqual(backchannel.clean("Uh-huh. Then my boss called"), "Then my boss called")
        self.assertEqual(backchannel.clean("and then mhm she said no"), "And then she said no")

    def test_real_words_stay(self):
        for said in ["I'm hmm not sure", "Remind me to call Mom", "Huh, okay", "Text Emma I'm summing it up"]:
            self.assertEqual(backchannel.clean(said), said)

    def test_a_lone_mhm_is_an_answer(self):
        self.assertEqual(backchannel.clean("Mhm."), "Mhm.")  # "want me to send it?" "mhm": a yes, never dropped
        self.assertEqual(backchannel.clean("Uh-huh"), "Uh-huh")


class TalkOverTests(unittest.TestCase):
    def test_only_when_the_mic_cant_hear_luma(self):
        self.assertTrue(backchannel.safe_to_talk_over("AirPods Pro", "AirPods Pro"))
        self.assertTrue(backchannel.safe_to_talk_over("MacBook Pro Speakers", "ReSpeaker 4 Mic Array"))
        self.assertTrue(backchannel.safe_to_talk_over("WH-1000XM5", "MacBook Pro Microphone"))
        self.assertFalse(backchannel.safe_to_talk_over("MacBook Pro Speakers", "MacBook Pro Microphone"))
        self.assertFalse(backchannel.safe_to_talk_over("", ""))
        self.assertFalse(backchannel.safe_to_talk_over("Beatrice's Speaker", "Built-in Microphone"))


if __name__ == "__main__":
    unittest.main()
