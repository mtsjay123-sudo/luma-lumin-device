"""Luma's video hands, run for real with FFmpeg on a made-up clip: a test pattern with a tone, two seconds of silence
in the middle, then the tone again. Every edit makes a new file next to the original and leaves the original alone."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from luma.skills import video

HAVE_FFMPEG = bool(shutil.which("ffmpeg"))


@unittest.skipUnless(HAVE_FFMPEG, "needs ffmpeg")
class VideoToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.clip = Path(cls.temp.name) / "clip.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=6",
                        "-f", "lavfi", "-i", "sine=f=440:duration=6", "-af", "volume=enable='between(t,2,4)':volume=0",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(cls.clip)], check=True)
        cls.before = cls.clip.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def tearDown(self):
        self.assertEqual(self.clip.read_bytes(), self.before, "the original is never touched")

    def test_it_reads_what_a_file_holds(self):
        info = video.probe(self.clip)
        self.assertAlmostEqual(info["duration"], 6.0, delta=0.2)
        self.assertEqual((info["width"], info["height"], info["video"], info["audio"]), (640, 360, True, True))
        with self.assertRaises(video.VideoError):
            video.probe(Path(self.temp.name) / "nope.mp4")

    def test_vertical_for_tiktok_and_reels(self):
        out = video.vertical(self.clip)
        self.assertEqual(out.name, "clip-vertical.mp4")
        info = video.probe(out)
        self.assertEqual((info["width"], info["height"]), (1080, 1920))
        self.assertTrue(info["audio"], "the sound comes along")
        self.assertEqual(video.vertical(self.clip, fit="crop").name, "clip-vertical-2.mp4", "never over an earlier edit either")

    def test_trim(self):
        out = video.trim(self.clip, "0:01", 3.5)
        self.assertAlmostEqual(video.probe(out)["duration"], 2.5, delta=0.15)
        with self.assertRaises(video.VideoError):
            video.trim(self.clip, 4, 2)

    def test_dead_air_comes_out(self):
        quiet = video.quiet_spans(self.clip)
        self.assertEqual(len(quiet), 1)
        self.assertAlmostEqual(quiet[0][0], 2.0, delta=0.1)
        out, cut = video.remove_dead_air(self.clip)
        self.assertAlmostEqual(cut, 1.7, delta=0.25, msg="two seconds of silence, minus a little air on each side")
        self.assertAlmostEqual(video.probe(out)["duration"], 6 - cut, delta=0.25)

    def test_even_sound(self):
        out = video.loudness(self.clip)
        info = video.probe(out)
        self.assertTrue(info["video"] and info["audio"])
        self.assertAlmostEqual(info["duration"], 6.0, delta=0.2)

    def test_captions_from_lines(self):
        out, srt = video.captions(self.clip, lines=[(0.0, 1.8, "This is Luma."), (4.0, 5.8, "Captions, made here.")])
        self.assertIn("00:00:04,000 --> 00:00:05,800\nCaptions, made here.", srt.read_text())
        self.assertTrue(video.probe(out)["video"])

    def test_caption_lines_are_short_and_end_at_sentences(self):
        words = [(i * 0.3, i * 0.3 + 0.25, w) for i, w in enumerate("Blockchains keep a shared record. Every block points back to the one before it.".split())]
        lines = video.caption_lines(words)
        self.assertEqual(lines[0][2], "Blockchains keep a shared record.")
        self.assertTrue(all(len(text) <= 38 for _, _, text in lines))

    def test_contact_sheet(self):
        out = video.contact_sheet(self.clip)
        self.assertEqual(out.suffix, ".jpg")
        self.assertGreater(out.stat().st_size, 2000)

    def test_times_in_plain_words(self):
        self.assertEqual(video.seconds("1:05"), 65.0)
        self.assertEqual(video.seconds("1:02:03.5"), 3723.5)
        with self.assertRaises(video.VideoError):
            video.seconds("soon")


if __name__ == "__main__":
    unittest.main()
