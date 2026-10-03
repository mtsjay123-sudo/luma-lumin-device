"""The conversation check grades replies the way a person would."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("luma_check", Path(__file__).parents[1] / "scripts" / "luma_check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class GradeTests(unittest.TestCase):
    def test_a_human_reply_passes(self):
        report = check.grade("rough day", {"max_words": 60, "no_list": True}, {"text": "Rough one? Tell me what happened."}, 2.1)
        self.assertTrue(report["passed"], report["problems"])

    def test_chatbot_habits_are_caught(self):
        reply = "Great question! As an AI, I'm here for you.\n- Take a walk\n- **Breathe**"
        report = check.grade("rough day", {"max_words": 10, "no_list": True}, {"text": reply}, 9.5)
        joined = " ".join(report["problems"])
        for problem in ["great question", "as an ai", "markdown", "list", "too long", "slow"]:
            self.assertIn(problem, joined)

    def test_actions_are_checked_from_the_result(self):
        good = {"state": "draft", "message_draft": {"to": "+19195550123", "body": "running 10 minutes late"}}
        self.assertTrue(check.grade("text", {"draft_to": "+19195550123", "body_has": ["10", "late"]}, good, 1)["passed"])
        bad = {"state": "draft", "message_draft": {"to": "+19195550123", "body": "running late"}}
        self.assertIn('text lost "10"', check.grade("text", {"draft_to": "+19195550123", "body_has": ["10"]}, bad, 1)["problems"])
        self.assertFalse(check.grade("deck", {"deck_min_slides": 5}, {"text": "Here's a deck idea"}, 3)["passed"])


if __name__ == "__main__":
    unittest.main()
