"""The video studios through the real projects engine: an explainer written by the brain becomes real videos (16:9 and
9:16 with chapters, captions, a script and a poster), and a video the owner added gets the edits they asked for, in
order, with the original untouched. FFmpeg runs for real; the voice is a stand-in tone so the narration has a length."""
import math
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

import work_fakes
from luma.memory.store import Store
from luma.skills import video
from luma.work import explainer
from luma.work.engine import Engine
from luma.work.projects import Projects

SCRIPT = """# What a blockchain is
A shared notebook :: A blockchain is a shared record that thousands of computers keep at once.
No one owns it :: No single company holds the master copy, so nobody can quietly change it.
# Why it matters
Trust without a middleman :: That's how strangers can trade without a bank in the middle."""


def tone_voice(text, path):
    """A stand-in voice: a soft tone as long as the line would take to say."""
    secs = max(1.0, len(text.split()) / 2.6)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(explainer.RATE)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 220 * i / explainer.RATE))) for i in range(int(secs * explainer.RATE))))
    return "luma"


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class VideoStudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.projects = Projects(self.store, root / "projects")
        self.brain = work_fakes.Brain({"work.video": {"title": "How blockchain works", "script": SCRIPT, "formats": "both"}})
        self.engine = Engine(self.projects, think=self.brain, search=work_fakes.search, read=lambda url: "", approver=lambda q: True, render=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def files(self, project):
        return {f["path"] for f in self.projects.files(project["id"])}

    def test_an_explainer_video_from_a_request(self):
        project = self.projects.create("Blockchain", "")
        with mock.patch.object(explainer, "default_voice", tone_voice):
            run = self.engine.start(project["id"], "make me an explainer video about how blockchain works")
        step = run["steps"][-1]
        self.assertEqual((step["tool"], step["state"]), ("video", "done"), step.get("checks"))
        self.assertTrue({"video/how-blockchain-works.mp4", "video/how-blockchain-works-vertical.mp4", "video/how-blockchain-works.srt",
                         "video/how-blockchain-works-script.md", "video/how-blockchain-works-poster.png"} <= self.files(project))
        folder = self.projects.folder(project["id"])
        wide, tall = video.probe(folder / "video/how-blockchain-works.mp4"), video.probe(folder / "video/how-blockchain-works-vertical.mp4")
        self.assertEqual((wide["width"], wide["height"], tall["width"], tall["height"]), (1920, 1080, 1080, 1920))
        self.assertTrue(wide["audio"] and tall["audio"])
        described = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(folder / "video/how-blockchain-works.mp4")], capture_output=True, text=True).stderr
        self.assertIn("title           : Why it matters", described, "chapters are in the file")
        self.assertIn("narrated in Luma's voice", step["summary"])
        self.assertIn("2 chapters (What a blockchain is, Why it matters)", step["summary"])
        captions = (folder / "video/how-blockchain-works.srt").read_text()
        self.assertIn("A blockchain is a shared record", captions)

    def test_the_script_is_read_the_way_luma_writes_it(self):
        chapters = explainer.parse_script("# 1. Intro\nHello there. This is two lines.\n- Big idea :: One more sentence.\n#\n", "T")
        self.assertEqual(chapters[0]["title"], "Intro")
        self.assertEqual([l["say"] for l in chapters[0]["lines"]], ["Hello there.", "This is two lines.", "One more sentence."])
        self.assertEqual([l["show"] for l in chapters[0]["lines"]], ["Intro", "Intro", "Big idea"])
        with self.assertRaises(explainer.ExplainerError):
            explainer.parse_script("   ", "T")
        times = explainer.word_times(["Hi,", "there", "friend."], 10.0, 3.0)
        self.assertAlmostEqual(times[-1][1], 13.0)
        self.assertGreater(times[0][1] - times[0][0], times[1][1] - times[1][0] - 0.2, "a comma adds a beat")

    def test_editing_the_owners_video(self):
        project = self.projects.create("My vlog", "")
        clip = self.projects.folder(project["id"]) / "vlog.mp4"
        clip.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30:duration=6",
                        "-f", "lavfi", "-i", "sine=f=440:duration=6", "-af", "volume=enable='between(t,2,4)':volume=0",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(clip)], check=True)
        before = clip.read_bytes()
        brain = work_fakes.Brain({"work.video_edit": None})
        engine = Engine(self.projects, think=brain, search=work_fakes.search, read=lambda url: "", approver=lambda q: True, render=False)
        run = engine.start(project["id"], "take the dead air out of my video and make it vertical for tiktok")
        step = run["steps"][-1]
        self.assertEqual((step["tool"], step["state"]), ("video_edit", "done"), step.get("checks"))
        result = video.probe(self.projects.folder(project["id"]) / step["data"]["result"])
        self.assertEqual((result["width"], result["height"]), (1080, 1920))
        self.assertLess(result["duration"], 5.0, "the silence came out before it went vertical")
        self.assertIn("dead air", step["summary"])
        self.assertEqual(clip.read_bytes(), before, "the original is untouched")

    def test_no_video_in_the_project_says_how_to_add_one(self):
        project = self.projects.create("Empty", "")
        engine = Engine(self.projects, think=work_fakes.Brain({"work.video_edit": None}), search=work_fakes.search, render=False)
        run = engine.start(project["id"], "make my video vertical")
        self.assertIn("Add the video to this project", str(run["steps"][-1]))


if __name__ == "__main__":
    unittest.main()
