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
                # A fresh opener: urlopen keeps the first one it built, and an earlier test may have built it with a proxy.
                urllib.request.build_opener().open("https://example.com", timeout=3)
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


class EachSwitchAlone(unittest.TestCase):
    """docs/GAME_PLAN.md, E4: "each switch turned on alone opens only its own host". Not covered here: the browser
    inside Luma (its tools aren't installed where the tests run) and the news feeds."""

    @classmethod
    def setUpClass(cls):
        cls.out = egress_check.alone()

    def test_each_one_reaches_only_its_own_host(self):
        self.assertEqual(self.out["leaks"], {})
        for name, hosts in self.out["alone"].items():
            self.assertTrue(hosts, name + " reached for nothing, so this proved nothing")     # each really did try

    def test_the_ones_that_can_be_tried_here_were_tried(self):
        tried = set(self.out["alone"])
        for name in ("weather (the web switch, as it comes)", "a coin's price (the web switch)", "a share's price (the web switch)",
                     "the radio (Music)", "the house (Home)"):
            self.assertIn(name, tried)

    def test_with_everything_off_asking_reaches_nothing(self):
        self.assertEqual(self.out["everything_off"], [])


if __name__ == "__main__":
    unittest.main()
