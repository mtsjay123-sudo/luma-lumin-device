"""Live view: Luma sees through the owner's camera right now. Questions about what's in front of the camera are answered
from the newest picture (with the last few seconds remembered); "tell me when..." makes Luma watch and speak up once,
after two looks in a row agree; anything else is an ordinary reply. Pictures are kept in memory only, briefly, and
gone the moment the camera stops. Kids mode keeps it closed. Luma's eyes are a stand-in here."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from luma.agent.live_view import LiveView
from luma.agent.runtime import Agent
from luma.memory.store import Store

FRAME = b"\xff\xd8\xff\xe0" + b"\x00" * 2000


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now


class LiveViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.agent = Agent(store=self.store, use_model=False)
        self.clock = Clock()
        self.agent.live = LiveView(clock=self.clock)
        self.asked = []
        self.answers = []

        def look(image, question, quick=False):
            self.asked.append(question)
            return self.answers.pop(0) if self.answers else "A pot of pasta on the stove, water just starting to bubble."
        self.look = mock.patch.object(self.agent, "_look", side_effect=look)
        self.look.start()

    def tearDown(self):
        self.look.stop()
        self.store.close()
        self.temp.cleanup()

    def test_a_question_about_what_the_camera_sees_is_answered_from_the_picture(self):
        out = self.agent.live_frame(FRAME, "what am I looking at?")
        self.assertEqual(out["text"], "A pot of pasta on the stove, water just starting to bubble.")
        self.assertIn("live picture from my camera, right now", self.asked[-1])
        self.clock.now += 5
        self.answers.append("Now it's boiling hard.")
        self.agent.live_frame(FRAME, "what about now?")
        self.assertIn("A few seconds ago you saw: A pot of pasta", self.asked[-1], "the last half minute is remembered")
        said = [m["text"] for m in self.agent.transcripts["main"]]
        self.assertEqual(said[-2:], ["what about now?", "Now it's boiling hard."], "it's all in the chat")

    def test_other_requests_with_the_camera_on_are_ordinary_replies(self):
        with mock.patch.object(self.agent, "chat", return_value={"text": "Timer's set for 10 minutes."}) as chat:
            out = self.agent.live_frame(FRAME, "set a timer for 10 minutes")
        chat.assert_called_once()
        self.assertEqual(out["text"], "Timer's set for 10 minutes.")
        self.assertFalse(self.asked, "no look needed")

    def test_watching_speaks_up_once_after_two_looks_agree(self):
        out = self.agent.live_frame(FRAME, "tell me when the pasta boils over")
        self.assertIn("I'm watching. I'll speak up the moment the pasta boils over", out["text"])
        self.assertEqual(out["watching"], "the pasta boils over")
        self.answers += ["no, it's simmering.", "Yes, foam is spilling over the edge.", "no.", "Yes, it's boiling over.", "Yes, it's boiling over onto the stove."]
        self.assertNotIn("alert", self.agent.live_frame(FRAME))
        self.assertNotIn("alert", self.agent.live_frame(FRAME), "one yes isn't enough")
        self.assertNotIn("alert", self.agent.live_frame(FRAME), "a no resets it")
        self.assertNotIn("alert", self.agent.live_frame(FRAME))
        out = self.agent.live_frame(FRAME)
        self.assertEqual(out["alert"], "Heads up! It's boiling over onto the stove.")
        self.assertIsNone(self.agent.live.watch, "told once, not every two seconds")
        self.assertEqual(self.agent.live_frame(FRAME), {"live": True, "watching": None})

    def test_watch_something_without_a_when(self):
        out = self.agent.live_frame(FRAME, "keep an eye on the oven")
        self.assertIn("the moment anything's not right with the oven", out["text"])
        self.assertIn("needs attention", self.agent.live.watch["for"])
        out = self.agent.live_frame(FRAME, "never mind, stop watching")
        self.assertEqual(out["text"], "Okay, I stopped watching.")
        self.assertIsNone(self.agent.live.watch)

    def test_pictures_are_brief_and_gone_when_the_camera_stops(self):
        for _ in range(20):
            self.agent.live.add(FRAME)
        self.assertLessEqual(len(self.agent.live.frames), 12)
        self.clock.now += 31
        self.assertIsNone(self.agent.live.latest(), "half a minute later it's forgotten")
        self.agent.live.add(FRAME)
        self.agent.live_frame(FRAME, "tell me when the kettle boils")
        self.agent.live_stop()
        self.assertFalse(self.agent.live.frames)
        self.assertIsNone(self.agent.live.watch)
        self.assertIsNone(self.agent.live.recently_said())

    def test_only_camera_pictures_and_never_in_kids_mode(self):
        with self.assertRaises(ValueError):
            self.agent.live_frame(b"GIF89a....", "what's this?")
        self.store.set_setting("mode", "kids")
        out = self.agent.live_frame(FRAME, "what's this?")
        self.assertFalse(out["live"])
        self.assertFalse(self.agent.live.frames)
        self.assertFalse(self.asked)


if __name__ == "__main__":
    unittest.main()
