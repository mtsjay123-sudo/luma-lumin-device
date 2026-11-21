"""Luma notices, checks back and remembers when asked, and forgets when told."""
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from luma.agent import presence
from luma.agent.runtime import Agent
from luma.memory.store import Store

NY = ZoneInfo("America/New_York")


def at(*args):
    return datetime(*args, tzinfo=NY).timestamp()


class PresenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "state.db", root / "state.key")
        self.now = at(2026, 10, 3, 21, 0)  # Saturday evening
        self.agent = Agent(store=self.store, use_model=False, now=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def memories(self):
        return [m["text"] for m in self.store.all("memory")]

    def test_facts_said_in_passing_are_kept_and_can_be_undone(self):
        result = self.agent.chat("ugh, Maya's birthday is October 18 and I have no idea what to get her")
        self.assertEqual([n["text"] for n in result["noticed"]], ["Maya's birthday is October 18"])
        self.assertIn("Maya's birthday is October 18", self.memories())
        self.agent.chat("ugh, Maya's birthday is October 18 and I still don't know")
        self.assertEqual(self.memories().count("Maya's birthday is October 18"), 1, "no duplicates")
        self.assertEqual(len(self.store.kept(10)), 1, "one fact, one card")
        # What they said about Maya is also kept as they said it, for recall (a line of talk, never a card): she's someone of theirs now.
        self.assertEqual(sorted(m["text"] for m in self.store.all("memory") if m.get("source") == "said"),
                         ["ugh, Maya's birthday is October 18 and I have no idea what to get her", "ugh, Maya's birthday is October 18 and I still don't know"])
        self.agent.chat("I'm allergic to shellfish by the way")
        self.assertEqual(self.agent.chat("forget that")["text"], "Forgotten.")
        self.assertNotIn("I'm allergic to shellfish", self.memories())
        self.assertIn("Maya's birthday is October 18", self.memories())

    def test_questions_and_commands_are_not_mistaken_for_facts(self):
        for text in ["what's my favorite food?", "remind me that I'm vegan", "text Maya that my mom's birthday is March 3"]:
            self.assertEqual(presence.notice_facts(text), [], text)

    def test_learning_can_be_switched_off(self):
        self.agent.set_presence("learn_from_chat", False)
        self.agent.chat("my girlfriend is named Maya")
        self.assertEqual(self.memories(), [])

    def test_luma_checks_back_after_something_you_mentioned(self):
        self.agent.chat("I have a job interview tomorrow and I'm kind of nervous")
        self.assertIsNone(self.agent.tick(), "not yet")
        self.now = at(2026, 10, 5, 18, 5)  # the evening after
        event = self.agent.tick()
        self.assertEqual(event["type"], "checkin")
        self.assertIn("how", event["text"].lower())
        self.assertIn("job interview", event["text"])
        self.now += 7200
        self.assertIsNone(self.agent.tick(), "asked once")

    def test_check_ins_respect_quiet_hours_and_go_stale(self):
        self.agent.chat("I've got my driving test on Monday")
        self.now = at(2026, 10, 7, 1, 0)  # quiet hours
        self.assertIsNone(self.agent.tick())
        self.now = at(2026, 10, 12, 18, 0)  # a week later: too late to ask naturally
        self.assertIsNone(self.agent.tick())

    def test_birthday_nudge_once_a_day(self):
        self.store.put("memory", {"text": "Maya's birthday is October 5"})
        self.now = at(2026, 10, 3, 9, 0)
        event = self.agent.tick()
        self.assertEqual(event["text"], "Heads up, Maya's birthday is on Monday. Want me to help you plan something?")
        self.now += 3 * 3600
        self.assertIsNone(self.agent.tick())

    def test_diary_is_off_by_default_then_private_searchable_and_expiring(self):
        self.agent.chat("the apartment on Oak Street had a leaky ceiling, I'm not taking it")
        self.assertIn("diary's off", self.agent.chat("what did I say about the apartment?")["text"])
        self.assertEqual(self.store.all("diary"), [])
        self.agent.set_presence("diary_days", 7)
        self.agent.chat("the apartment on Oak Street had a leaky ceiling, I'm not taking it")
        self.assertNotIn(b"leaky ceiling", self.store.db_path.read_bytes(), "encrypted at rest")
        found = self.agent.chat("what did I say about the apartment?")
        self.assertIn("leaky ceiling", found["text"])
        self.now += 8 * 86400
        self.agent._last_diary_prune = 0
        self.agent.tick()
        self.assertEqual([d for d in self.store.all("diary") if "leaky" in d["you"]], [])
        self.agent.chat("note to self the blue car is nicer")
        self.agent.set_presence("diary_days", 0)
        self.assertEqual(self.store.all("diary"), [], "turning it off erases it")

    def test_kids_mode_learns_nothing(self):
        self.agent.set_mode("kids")
        self.agent.chat("my dog's name is Biscuit")
        self.assertEqual(self.memories(), [])


if __name__ == "__main__":
    unittest.main()


class TheirOwnBirthday(unittest.TestCase):
    """Found Nov 21, 2026, once "I turn 40 on May 12" became a birthday Luma keeps: on the day it would have said "It's
    your birthday today. Want help with a text or a last-minute plan?", and "Heads up, your birthday is on Friday" for
    three days before. A friend says happy birthday, on the day."""

    MINE = [{"text": "My birthday is May 12"}]

    def on(self, day, memories=None):
        return [b for b in presence.birthdays(memories or self.MINE, day) if b["days"] <= 3]

    def test_on_the_day_luma_says_happy_birthday(self):
        line = presence.nudge_line(self.on(date(2027, 5, 12))[0], "Jay")
        self.assertTrue(line.startswith("Happy birthday, Jay!"), line)
        self.assertNotRegex(line, r"(?i)text|plan|heads up")
        self.assertTrue(presence.nudge_line(self.on(date(2027, 5, 12))[0]).startswith("Happy birthday!"))

    def test_never_a_heads_up_about_their_own_birthday(self):
        for day in (9, 10, 11):
            item = self.on(date(2027, 5, day))[0]
            self.assertTrue(presence.theirs(item))
            self.assertEqual(presence.nudge_line(item), "")

    def test_someone_elses_birthday_and_their_anniversary_are_as_before(self):
        memories = [{"text": "My mom's birthday is June 3"}, {"text": "My anniversary is June 4"}]
        mom, wedding = self.on(date(2027, 6, 2), memories)
        self.assertEqual(presence.nudge_line(mom), "Heads up, your mom's birthday is tomorrow. Want me to help you plan something?")
        self.assertFalse(presence.theirs(mom) or presence.theirs(wedding))
        self.assertIn("your anniversary", presence.nudge_line(wedding))

    def test_a_date_said_day_first_is_read_too(self):
        found = self.on(date(2027, 10, 21), [{"text": "My birthday is the 21st of October"}])
        self.assertEqual([(b["whose"], b["days"]) for b in found], [("your", 0)])

    def test_in_luma_the_day_before_is_quiet_and_the_day_itself_is_warm(self):
        agent = Agent(store=Store(Path(tempfile.mkdtemp()) / "s.db", Path(tempfile.mkdtemp()) / "k"), use_model=False)
        try:
            agent.store.set_setting("personality", {"name": "Jay Rivera", "tone": "warm", "language_style": "plain", "verbosity": "balanced"})
            agent.store.put("memory", {"text": "My birthday is May 12", "created": 1.0})
            before = agent._presence_event(1.0, datetime(2027, 5, 11, 9, 0))
            self.assertIsNone(before)
            event = agent._presence_event(2.0, datetime(2027, 5, 12, 9, 0))
            self.assertEqual(event["type"], "nudge")
            self.assertTrue(event["text"].startswith("Happy birthday, Jay!"), event["text"])
            self.assertIsNone(agent._presence_event(3.0, datetime(2027, 5, 12, 15, 0)))    # once, not all day
            agent.store.set_setting("nudge_day", "")
            agent.history.append({"role": "user", "content": "my dad died last week and I can't stop crying"})
            quiet = agent._presence_event(3.5, datetime(2027, 5, 12, 15, 30))["text"]      # in a hard stretch it's said quietly and asks nothing
            self.assertEqual(quiet, "Happy birthday, Jay. I'm glad I get to say it.")
            agent.store.set_setting("nudge_day", "")
            agent.set_mode("kids")
            self.assertIsNone(agent._presence_event(4.0, datetime(2027, 5, 12, 16, 0)))    # no check-ins in kids mode
        finally:
            agent.store.close()


class SomethingComingUpSaidAnyWay(unittest.TestCase):
    """The month test on real brains, on the lives Luma wasn't built on (run 55): the evening after something they had
    coming up, Luma asked how it went 8 times of 12. Of 16 fresh ways of saying it (Nov 20, 2026), 3 were noticed."""

    NOW = None
    COMING = ["I've got my driving test Thursday", "my interview is on Friday", "big presentation coming up Friday", "I'm seeing the dentist tomorrow",
              "I fly out Saturday morning", "my recital's this weekend", "court date is next Tuesday", "I'm meeting his parents on Sunday",
              "the surgery got scheduled for Monday", "we close on the house Friday", "tomorrow's my first day at the new job",
              "Friday I find out if I got the apartment", "I'm taking the bar exam on Tuesday", "my mom's surgery is Thursday morning",
              "I have to give a toast at the wedding Saturday", "wish me luck, the audition is tomorrow"]
    NOT_COMING = ["I watched the game today", "the game is on tonight", "my test results came back Friday", "I had an interview on Monday", "is my appointment on Friday?",
                  "I cancelled my dentist appointment tomorrow", "my flight got cancelled, it was supposed to be Saturday", "I hate Mondays, every meeting runs long",
                  "I don't have a date for Friday", "we went to a show on Saturday", "I might have a meeting tomorrow", "my show is on tonight", "I'm so tired today",
                  "tonight I'm staying in", "my sister has a recital... wait no that was last week", "I'm free Friday", "my favorite show comes back tomorrow"]

    def noticed(self, said):
        from datetime import datetime
        from luma.agent import presence
        return presence.notice_open_loops(said, datetime(2026, 11, 18, 19, 0))

    def test_fresh_ways_of_saying_it(self):
        self.assertGreaterEqual(sum(bool(self.noticed(said)) for said in self.COMING), 11)
        self.assertEqual([loop["topic"] for loop in self.noticed("I'm taking the bar exam on Tuesday")], ["bar exam"])
        self.assertEqual([loop["topic"] for loop in self.noticed("I fly out Saturday morning")], ["flight"])

    def test_what_isnt_coming_up_gets_no_check_in(self):
        """Three of these used to: "I cancelled my dentist appointment tomorrow" got "Hey, how'd the appointment go?"."""
        self.assertEqual([said for said in self.NOT_COMING if self.noticed(said)], [])

    def test_the_plain_way_still_works_with_a_not_in_it(self):
        for said in ("I've got a job interview tomorrow and I'm not ready", "my exam is on Friday", "I have a dentist appointment Thursday morning"):
            self.assertTrue(self.noticed(said), said)
