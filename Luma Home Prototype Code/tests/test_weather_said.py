"""The weather said as a remark is talk, never a look-up (luma.agent.runtime.WEATHER_REMARK, in told_not_asked). Found by
the stress test on Nov 26, 2026: "WICKED COLD TODAY" got "I need my browser tools to look things up", and with web
search on it would have been sent out word for word. The lines are in tests/weather_said_lines.py, written before the
reader: built on, 0 → 12 of 12; the second twelve, counted once by the same hand the same hour, 0 → 11 of 12; asks
taken for remarks 0 of 12."""
import unittest

import weather_said_lines as L
from luma.agent import runtime


class TheWeatherSaid(unittest.TestCase):
    def test_built_on(self):
        self.assertEqual([t for t in L.SAID if not runtime.told_not_asked(t)], [])
        self.assertEqual([t for t in L.ASKED if runtime.told_not_asked(t)], [])

    def test_the_honest_number_is_no_worse_than_measured(self):
        self.assertGreaterEqual(sum(runtime.told_not_asked(t) for t in L.SAID_2), 11)   # counts only


if __name__ == "__main__":
    unittest.main()
