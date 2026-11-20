"""A memory said back later: its time words are made true for today (luma.memory.when.said_later).

Found Nov 20, 2026: asked 26 days on, Luma said "Your dentist appointment is tomorrow at 3" and "Your brother moved to
Denver last week", because it repeated the words as they were said."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

from luma.memory import when  # noqa: E402


def at(year, month, day):
    return datetime(year, month, day, 19, 0, tzinfo=timezone.utc).timestamp()


SAID = at(2026, 11, 10)   # a Tuesday


class SaidLater(unittest.TestCase):
    def later(self, text, *day):
        return when.said_later(text, SAID, at(*day))

    def test_the_same_day_nothing_changes(self):
        for text in ("my dentist appointment is tomorrow at 3", "my brother moved to Denver last week", "I had a long day today"):
            self.assertEqual(self.later(text, 2026, 11, 10), text)

    def test_a_day_is_the_day_it_was(self):
        self.assertEqual(self.later("my dentist appointment is tomorrow at 3", 2026, 11, 11), "my dentist appointment is today at 3")
        self.assertEqual(self.later("my dentist appointment is tomorrow at 3", 2026, 11, 12), "my dentist appointment was yesterday at 3")
        self.assertEqual(self.later("my dentist appointment is tomorrow at 3", 2026, 12, 6), "my dentist appointment was on Nov 11 at 3")
        self.assertEqual(self.later("I started a new job yesterday", 2026, 12, 6), "I started a new job on Nov 9")
        self.assertEqual(self.later("my interview is tonight", 2026, 11, 11), "my interview was yesterday")
        self.assertEqual(self.later("my flight is the day after tomorrow", 2026, 11, 11), "my flight is tomorrow")

    def test_a_week_a_weekend_a_month_a_year(self):
        self.assertEqual(self.later("my brother moved to Denver last week", 2026, 12, 6), "my brother moved to Denver the week of Nov 2")
        self.assertEqual(self.later("we are going to Osaka next week", 2026, 11, 18), "we are going to Osaka this week")
        self.assertEqual(self.later("we are going to Osaka next week", 2026, 12, 6), "we were going to Osaka the week of Nov 16")
        self.assertEqual(self.later("my recital is this weekend", 2026, 11, 12), "my recital is this weekend")
        self.assertEqual(self.later("my recital is this weekend", 2026, 11, 20), "my recital was last weekend")
        self.assertEqual(self.later("my mom is visiting next month", 2026, 11, 20), "my mom is visiting next month")
        self.assertEqual(self.later("my mom is visiting next month", 2026, 12, 6), "my mom is visiting this month")
        self.assertEqual(self.later("my mom is visiting next month", 2027, 3, 1), "my mom was visiting in December 2026")
        self.assertEqual(self.later("my lease is up next year", 2027, 2, 1), "my lease is up this year")
        self.assertEqual(self.later("my sister got married last year", 2027, 3, 1), "my sister got married in 2025")

    def test_in_a_while_and_a_while_ago(self):
        self.assertEqual(self.later("the movers come in 3 days", 2026, 11, 12), "the movers come tomorrow")
        self.assertEqual(self.later("I quit smoking two weeks ago", 2027, 1, 15), "I quit smoking around Oct 27, 2026")

    def test_what_has_no_time_words_or_a_fixed_date_is_left_alone(self):
        for text in ("my mom's birthday is June 3", "my sister's name is Dana", "I'm allergic to shellfish", "my anniversary is in May"):
            self.assertEqual(self.later(text, 2027, 3, 1), text)

    def test_nothing_to_go_on_changes_nothing(self):
        self.assertEqual(when.said_later("my flight is tomorrow", None, at(2026, 12, 6)), "my flight is tomorrow")
        self.assertEqual(when.said_later("my flight is tomorrow", SAID, None), "my flight is tomorrow")


class LumaSaysItRight(unittest.TestCase):
    def test_weeks_later_luma_says_the_day_not_tomorrow(self):
        import human_eval
        told = []

        def planner(messages, context, allowed, *args, **kwargs):
            told.append(" | ".join(str(c.get("text")) for c in context if isinstance(c, dict)))
            return {"type": "reply", "text": "Okay."}

        s = human_eval.Session(planner)
        self.addCleanup(s.close)
        say = lambda text: (lambda out: out[0] if isinstance(out, tuple) else out.get("text"))(s.say(text))  # noqa: E731
        say("my brother moved to Denver last week")
        say("my dentist appointment is tomorrow at 3")
        self.assertEqual(say("when is my dentist appointment"), "Your dentist appointment is tomorrow at 3.")
        s.at({"day": 27, "time": "19:00"})
        s.new_conversation()
        self.assertEqual(say("when is my dentist appointment"), "Your dentist appointment was on Nov 11 at 3.")
        self.assertEqual(say("where does my brother live now"), "Your brother moved to Denver the week of Nov 2.")
        del told[:]
        say("ugh I keep putting off the dentist")   # the brain's turn: what it's handed says the day too
        self.assertTrue(told)
        self.assertNotIn("is tomorrow", " ".join(told))


if __name__ == "__main__":
    unittest.main()
