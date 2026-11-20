"""What leaves the home (scripts/egress_check.py): every connection Luma tries to make is recorded and refused.

With its settings as they come, an ordinary conversation and a day of Luma's own background work reach for nothing
outside this machine. This covers the conversation path, the background tick and the scheduled helpers; the lamp's whole
service still gets a day with a packet capture before anyone says "nothing leaves"."""
import sys
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import egress_check  # noqa: E402


class TheWatch(unittest.TestCase):
    def test_it_sees_and_refuses_a_real_attempt(self):
        with egress_check.Watch() as watch:
            with self.assertRaises(Exception):
                urllib.request.urlopen("https://example.com", timeout=3)
            self.assertEqual(watch.take(), ["example.com:443"])

    def test_this_machine_is_not_outside(self):
        with egress_check.Watch() as watch:
            watch._note("127.0.0.1", 8080)
            watch._note("localhost", 80)
            self.assertEqual(watch.take(), [])


class ADay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = egress_check.run()

    def test_talking_reaches_for_nothing(self):
        self.assertEqual(self.out["talk"], [])

    def test_a_day_of_background_work_reaches_for_nothing(self):
        self.assertEqual(self.out["background"], [])


if __name__ == "__main__":
    unittest.main()
