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


class WhatLumaAsksAbout(unittest.TestCase):
    """Nov 21, 2026. Told "my mom has surgery on Monday", Luma's check-in would have been "how did the mom has surgery
    go?"; told "I bombed my interview today", it would have asked the next evening how the interview went. Of 16 fresh
    things coming up (FIRST), 8 were noticed and 2 of those were worded wrong; of 21 near misses, 7 got a check-in.
    Built on those. SECOND was written afterwards and measured once: 6 of 16 noticed (before: 3), 0 of 12 near misses
    (before: 2). It then exposed an old guard ("is on Wednesday" read as "is on TV"); with that fixed it's 8, which is no
    longer a number nothing was fitted to. THIRD was written after that and measured once: 11 of 12, but written knowing
    which events are on the list, so it flatters. The honest picture is SECOND: about half of fresh ways are noticed."""

    FIRST = ["I have a job interview at Costco on Thursday", "my driving test is tomorrow morning", "I'm seeing the dentist on Friday at 3",
             "we close on the house next Tuesday", "my sister's wedding is this Saturday", "I've got a first date tomorrow night",
             "tomorrow I find out if I got the apartment", "my mom has surgery on Monday", "I'm meeting my landlord tomorrow about the rent",
             "Friday is my last day at work", "I'm flying to Osaka on Sunday", "got my performance review Wednesday", "my dad's funeral is on Friday",
             "I'm taking my cat to the vet tomorrow", "my visa appointment is next week", "the results of my biopsy come back Thursday"]
    NEAR = ["I need to move my car tomorrow", "I'll review the doc tomorrow", "I'll scan the receipts tonight", "the vet called today",
            "the doctor called today about my mom", "today is the last day of the sale, I need shoes", "my mom had surgery on Monday",
            "my sister had her wedding on Saturday", "I skipped my dentist appointment today", "my dad's funeral is on Friday",
            "my brother has a show he likes on tonight", "I bombed my interview today", "my mom didn't have her surgery on Monday after all",
            "we might close on the house next Tuesday", "my boss said my performance review went fine today", "my sister's wedding was this Saturday",
            "I'm not going to the concert tomorrow", "is the wedding this Saturday?", "my cat hates the vet, always has, even today",
            "I passed my driving test today", "my coworker told me his interview is tomorrow"]
    SECOND = ["my brother's graduation is on Saturday", "I've got a dentist appointment Wednesday afternoon", "we're moving on Saturday",
              "my daughter has her first recital tomorrow", "Thursday I start the new job", "I'm getting my wisdom teeth out on Friday",
              "my dad goes in for his knee operation Monday", "got a second interview with them Tuesday", "the home inspection is tomorrow morning",
              "I'm running a 10k this weekend", "my wife's ultrasound is on Wednesday", "I'm presenting to the board on Thursday",
              "tomorrow night's my first open mic", "I take my road test Friday morning", "our anniversary dinner is tomorrow night",
              "my best friend's baby shower is Sunday"]
    SECOND_NOT = ["my interview went great today", "I had my road test on Friday and passed", "my brother's graduation was on Saturday",
                  "I rescheduled the dentist for next Wednesday", "the concert tomorrow got cancelled", "do I have an appointment on Thursday?",
                  "my wife said her ultrasound went fine today", "I'm not doing the open mic tomorrow after all", "I watched a wedding show tonight",
                  "my dad never had the operation on Monday", "if I get the interview on Tuesday I'll be thrilled", "every Sunday there's a game on"]
    THIRD = ["my son's first game is on Saturday", "I've got an eye appointment Monday morning", "my girlfriend's interview is tomorrow",
             "Wednesday is my thesis defense", "I have a checkup on Friday", "my mom's flight is on Sunday", "we have a meeting with the school on Thursday",
             "my cousin's wedding is on Friday", "I'm going in for an MRI tomorrow", "my husband has a big presentation on Tuesday",
             "there's a tournament this weekend, I'm playing", "I'm giving a speech at the ceremony Saturday"]
    THIRD_NOT = ["my son's game was on Saturday", "the show is on Friday nights", "my mom's flight got cancelled for Sunday", "I already had my checkup on Friday",
                 "my husband said his presentation went badly on Tuesday", "is my cousin's wedding on Friday?", "the game is on tonight",
                 "I never have meetings on Thursday"]

    def asks(self, said):
        loops = presence.notice_open_loops(said, datetime(2026, 11, 18, 19, 0))
        return [presence.check_in_line(loop["topic"], seed) for loop in loops for seed in range(3)]

    def test_whose_it_is_and_what_its_called(self):
        want = {"my mom has surgery on Monday": "how'd your mom's surgery go?", "my sister's wedding is this Saturday": "how'd your sister's wedding go?",
                "got my performance review Wednesday": "how'd the performance review go?", "we close on the house next Tuesday": "how'd the closing on the house go?",
                "I have a job interview at Costco on Thursday": "how'd the job interview go?", "I'm going in for an MRI tomorrow": "how'd the MRI go?",
                "my husband has a big presentation on Tuesday": "how'd your husband's presentation go?",
                "my daughter has her first recital tomorrow": "how'd your daughter's first recital go?"}
        for said, line in want.items():
            self.assertEqual(self.asks(said)[0], "Hey, " + line, said)

    def test_every_check_in_is_a_sentence_someone_would_say(self):
        for said in self.FIRST + self.SECOND + self.THIRD + SomethingComingUpSaidAnyWay.COMING:
            for line in self.asks(said):
                self.assertNotRegex(line, r"(?i)\bthe (?:your|my|our|mom|dad|sister|brother)\b|\b(?:has|have|had|is|got)\b.*\bgo\?|  ", (said, line))
                self.assertRegex(line, r"(?:go\?|How'd it go\?)$", (said, line))

    def test_told_how_it_went_luma_doesnt_ask_how_it_went(self):
        for said in ("I bombed my interview today", "I passed my driving test today", "my boss said my performance review went fine today",
                     "I skipped my dentist appointment today", "my interview went great today"):
            self.assertEqual(self.asks(said), [], said)

    def test_a_funeral_is_never_asked_about_like_an_errand(self):
        self.assertEqual(self.asks("my dad's funeral is on Friday"), [])

    def test_the_numbers(self):
        count = lambda lines: sum(bool(self.asks(said)) for said in lines)  # noqa: E731
        self.assertGreaterEqual(count(self.FIRST), 12)
        self.assertGreaterEqual(count(self.SECOND), 8)      # measured once at 6; 8 after the guard it exposed was fixed
        self.assertGreaterEqual(count(self.THIRD), 11)
        self.assertEqual([said for said in self.NEAR + self.SECOND_NOT + self.THIRD_NOT if self.asks(said)], [])


class ABatteryIsntAPlace(unittest.TestCase):
    """"ugh my phone's at 2 percent" was kept as where the phone is: "Got it. Your phone is at 2 percent. Just ask where is my phone"."""

    def test_a_percent_isnt_where_something_is(self):
        from luma.agent import presence
        for said in ("ugh my phone's at 2 percent", "my phone is at 5%", "my laptop's at 12 per cent"):
            self.assertEqual(presence.notice_facts(said), [], said)
        self.assertEqual(presence.notice_facts("my keys are on the kitchen counter"), ["Your keys are on the kitchen counter"])
        self.assertEqual(presence.notice_facts("i left my wallet at 22 elm street"), ["Your wallet is at 22 elm street"])
        self.assertEqual(presence.notice_facts("my car is at the shop"), ["Your car is at the shop"])


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
