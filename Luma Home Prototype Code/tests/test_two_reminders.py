"""Two reminders said in one breath are two reminders.

"remind me at 5 to call sam and then at 6 to feed the cat" made one reminder: "call Sam and then at 6 to feed the cat", at
5. Found on Nov 22, 2026, while checking run 81. Now a second time with its own thing to do ("and at 6 to feed the cat"),
or a second "remind me", is its own reminder; a day said once ("tomorrow at 9 ... and at noon ...") holds for both. One
reminder with "and" in what's to be done ("call mom and dad", "buy eggs and milk") stays one.

Both pairs of sets were written before the splitter. A is what it was built on (0 → 8 of 8 made two, 8 of 8 singles left as
one). B was measured once: 1 → 6 of 8 made two, and none of the eight single reminders was split."""
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store

TWO_A = [
    "remind me at 5 to call sam and then at 6 to feed the cat",
    "remind me at 5 to call sam and at 6 to feed the cat",
    "remind me to call sam at 5 and remind me to feed the cat at 6",
    "remind me tomorrow at 9 to pay rent and at noon to call the bank",
    "remind me to take the bins out tonight and remind me to water the plants tomorrow",
    "remind me in 20 minutes to flip the chicken and in an hour to take it out",
    "remind me at 8am to take my meds, and at 8pm to take them again",
    "remind me friday to send the invoice and then monday to follow up",
]
ONE_A = [
    "remind me to buy eggs and milk at 5",
    "remind me at 5 to call mom and dad",
    "remind me to pick up the kids and then go to the store at 3",
    "remind me at 7 to stretch and then meditate",
    "remind me tomorrow to call the vet and ask about the shots",
    "remind me at noon to eat lunch and take a walk",
    "remind me to text jay and then call him at 6",
    "remind me at 9 to go to bed on time for once",
]
TWO_B = [
    "remind me at 7 to stretch and at 9 to go to bed",
    "remind me to call the dentist at 10 and then remind me to book the car in at 2",
    "remind me tomorrow morning to pack lunch and tomorrow night to iron my shirt",
    "remind me at 3 to pick up the kids, then at 5 to start dinner",
    "remind me in ten minutes to check the oven and in thirty to take the bread out",
    "remind me monday to email the landlord and wednesday to pay the water bill",
    "remind me at 6am to run and also at 7 to shower",
    "ping me at 4 to leave for the airport and at 4:30 to call the cab",
]
ONE_B = [
    "remind me to grab bread and butter at 6",
    "remind me at 8 to call grandma and wish her happy birthday",
    "remind me tonight to charge my phone and laptop",
    "remind me at 2 to send the report and cc dana",
    "remind me to feed the cat and then the fish at 7",
    "remind me tomorrow to return the shoes and get a refund",
    "remind me at 10 to turn off the oven and lock up",
    "remind me friday at 5 to pick up the cake and candles",
]


class TwoReminders(unittest.TestCase):
    def made(self, said):
        """The reminders one message makes, on a fresh Luma with no brain."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        out = agent.chat(said)
        return sorted(store.all("task", 1000), key=lambda r: r["due"]), str(out.get("text") or "")

    def count(self, rows):
        return [len(self.made(said)[0]) for said in rows]

    def test_two_said_in_one_breath_are_two(self):
        self.assertEqual(self.count(TWO_A), [2] * len(TWO_A))

    def test_one_with_and_in_it_stays_one(self):
        self.assertEqual(self.count(ONE_A), [1] * len(ONE_A))

    def test_on_the_sets_measured_once(self):
        self.assertGreaterEqual(sum(n == 2 for n in self.count(TWO_B)), TWO_B_FLOOR)
        self.assertEqual(sum(n != 1 for n in self.count(ONE_B)), 0)

    def test_each_gets_its_own_thing_and_its_own_time(self):
        rows, said = self.made("remind me at 5 to call sam and then at 6 to feed the cat")
        self.assertEqual([r["title"] for r in rows], ["Call Sam", "Feed the cat"])
        self.assertEqual(round((rows[1]["due"] - rows[0]["due"]) / 60), 60)
        self.assertIn("2 things", said)

    def test_a_day_said_once_holds_for_both(self):
        rows, _ = self.made("remind me tomorrow at 9 to pay rent and at noon to call the bank")
        self.assertEqual([r["title"] for r in rows], ["Pay rent", "Call the bank"])
        self.assertEqual(round((rows[1]["due"] - rows[0]["due"]) / 3600), 3)   # 9 and noon on the same day

    def test_never_in_kids_mode(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        store.set_setting("mode", "kids")
        agent = Agent(store=store, use_model=False)
        agent.chat("remind me at 5 to call sam and then at 6 to feed the cat")
        self.assertEqual(store.all("task", 1000), [])


TWO_B_FLOOR = 6   # measured once: 6 of 8 (1 of 8 before); none of the eight single reminders was split


if __name__ == "__main__":
    unittest.main()
