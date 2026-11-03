"""Hearing the owner over Luma's own voice: WebRTC's echo canceller takes what Luma plays back out of what the mic
hears, so the owner can talk over Luma on an ordinary speaker. Tested in a simulated room: Luma talking at 24 kHz the
way playback sends it, the room echoing it back 40 ms later with two reflections, and the owner speaking up at 4 s."""
import importlib.util
import unittest
from unittest import mock

import numpy as np

from luma.audio import echo

HAVE_APM = importlib.util.find_spec("livekit") is not None


def room(seconds=6, play_rate=24_000):
    rng = np.random.default_rng(0)
    t = np.arange(play_rate * seconds) / play_rate
    syllables = (np.sin(2 * np.pi * 3 * t) > 0) * np.abs(np.sin(2 * np.pi * 0.5 * t))
    luma = np.convolve(rng.standard_normal(len(t)), np.ones(8) / 8, "same") * syllables * 0.25   # float, -1..1, like playback
    far16 = echo._resample(luma * 32767, play_rate).astype(float)
    ir = np.zeros(800); ir[0], ir[160], ir[400] = 0.5, 0.2, 0.1
    delay = int(0.040 * echo.RATE)
    heard = np.concatenate([np.zeros(delay), np.convolve(far16, ir)[:len(far16) - delay]])
    owner = np.zeros_like(heard)
    owner[echo.RATE * 4:echo.RATE * 5] = np.sin(2 * np.pi * 220 * np.arange(echo.RATE) / echo.RATE) * 3000
    return luma, play_rate, heard, owner


@unittest.skipUnless(HAVE_APM, "the echo canceller's package isn't installed here")
class EchoCancellerTests(unittest.TestCase):
    def test_lumas_voice_comes_out_and_the_owner_stays(self):
        luma, rate, heard, owner = room()
        mic = np.clip(heard + owner, -32768, 32767).astype(np.int16)
        aec = echo.EchoCanceller(delay_ms=40, noise_suppression=False)
        block, chunk = rate // 50, 512                      # playback writes 20 ms blocks; the mic hands over 512 samples
        out, played_until = [], 0
        for start in range(0, len(mic) - chunk + 1, chunk):
            needed = int((start + chunk) / echo.RATE * rate)  # play everything up to where the mic has got to
            while played_until < min(needed, len(luma)):
                aec.played(luma[played_until:played_until + block], rate)
                played_until += block
            got = aec.clean(mic[start:start + chunk])
            self.assertEqual(len(got), chunk, "every chunk comes back whole")
            out.append(got.astype(float))
        out = np.concatenate(out)
        mic = mic[:len(out)].astype(float)
        db = lambda x: 10 * np.log10(np.mean(x ** 2) + 1e-9)  # noqa: E731
        only_echo = slice(echo.RATE * 2, echo.RATE * 4)
        self.assertGreater(db(mic[only_echo]) - db(out[only_echo]), 25, "Luma's own voice is mostly gone")
        talking = slice(echo.RATE * 4 + 1600, echo.RATE * 5)
        self.assertLess(abs(db(owner[talking]) - db(out[talking])), 3, "the owner's voice is still there")
        self.assertLess(echo.level_db(out[only_echo]), echo.TALK_OVER_FLOOR_DB, "what's left of the echo can't start a turn")
        self.assertGreater(echo.level_db(out[talking]), echo.TALK_OVER_FLOOR_DB, "the owner talking over Luma can")


class WithoutThePackageTests(unittest.TestCase):
    def test_nothing_changes_when_its_not_there(self):
        with mock.patch.object(echo, "canceller", return_value=None):
            self.assertFalse(echo.ready())
            echo.played(np.zeros(480, dtype=np.float32), 24_000)  # playback never notices

    def test_a_problem_in_the_canceller_never_stops_the_sound(self):
        broken = mock.Mock()
        broken.played.side_effect = RuntimeError("boom")
        with mock.patch.object(echo, "canceller", return_value=broken):
            echo.played(np.zeros(480, dtype=np.float32), 24_000)

    def test_resampling_keeps_the_length_right(self):
        self.assertEqual(len(echo._resample(np.zeros(480), 24_000)), 320)
        self.assertEqual(echo._resample(np.array([40000.0]), 16_000).tolist(), [32767])


class PlaybackFeedsTheCancellerTests(unittest.TestCase):
    def test_every_block_luma_plays_is_handed_over_as_its_sent(self):
        import importlib
        import sys
        written = []

        class Stream:
            def __init__(self, **kw): self.rate = kw["samplerate"]
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def write(self, block): written.append(len(block))
            def abort(self): pass

        import luma.audio as package
        fake = mock.Mock(OutputStream=Stream, query_devices=lambda *a, **k: [])
        before = package.__dict__.get("io")
        try:
            with mock.patch.dict(sys.modules, {"sounddevice": fake}):  # everything in sys.modules is put back afterwards
                sys.modules.pop("luma.audio.io", None)
                io = importlib.import_module("luma.audio.io")
                handed = []
                with mock.patch.object(io.echo, "played", side_effect=lambda pcm, rate: handed.append((len(pcm), rate))), \
                     mock.patch.object(io, "resolve_audio_device", return_value=None):
                    self.assertTrue(io.play_chunks([(np.zeros(2400, dtype=np.int16), 24_000)]))
        finally:
            if before is None: package.__dict__.pop("io", None)
            else: package.io = before
        self.assertEqual(handed, [(480, 24_000)] * 5, "the same 20 ms blocks the speaker got, in order")
        self.assertEqual(written, [480] * 5)


if __name__ == "__main__":
    unittest.main()
