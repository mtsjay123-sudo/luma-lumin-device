"""Luma naps (luma.agent.nap).

The owner, Nov 22: "Luma has human like features. Luma can nap. Nap mode is an option. It's almost human but it's not: it's
a presence." Run 86 had Luma looking forward to a power nap and I wrote it down as a body it doesn't have. It's something
Luma really does now: said by voice, it rests until the time's up or someone speaks; anything anyone says wakes it and is
heard as it always is, so the safety net is never slept through; and a nap goes into Luma's own record, so it's spoken of
only when it happened.

ASKS_A and NOT_A were written with the reader. ASKS_B and NOT_B were written after it without looking back at it and
measured once (the same hand, the same hour)."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from luma.agent import friendcheck, inner, nap, style
from luma.agent.runtime import Agent
from luma.memory.store import Store

ROOT = Path(__file__).resolve().parents[1]

ASKS_A = ["take a nap", "go take a nap", "nap for 20 minutes", "you can take a little nap", "nap mode", "go to sleep for a bit", "have a nap luma",
          "why don't you take a nap", "take a quick nap", "get some rest", "nap for an hour", "nap time"]
NOT_A = ["i need a nap", "i'm going to take a nap", "should i take a nap", "the baby is napping", "let me take a nap", "we took a nap after lunch",
         "my nap was terrible", "i want to go to sleep and never wake up", "he never naps", "naps are underrated", "can i nap here", "did you nap"]
ASKS_B = ["luma go nap", "you should rest for a while", "take a power nap", "hey luma nap for ten minutes", "okay nap time", "go lie down for a bit",
          "snooze for half an hour", "you've earned a nap", "go ahead and take a nap", "rest your eyes for a few minutes", "switch on nap mode",
          "take a 15 minute nap"]
NOT_B = ["i could use a nap", "my dad naps every afternoon", "is it bad to nap at 5pm", "the cat's taking a nap on my laptop", "remind me to nap at 3",
         "i can't nap, my brain won't stop", "how long should a nap be", "nap pods at work are a scam", "we should all take a nap honestly",
         "tell the kids it's nap time", "set a timer for my nap", "i'll sleep when i'm dead"]
ASKS_B_FLOOR, NOT_B_CEILING = 8, 0   # measured once: 9 of 12 asks heard, 0 of 12 of their own naps taken; then 8, when a bare "snooze" went back to the alarm

# Told to go back to its nap, after being woken (written before the reader: 0 of 12 and 0 of 12 heard then). The first
# pair is what the reader was built on; the second was written in the same sitting and measured once afterwards.
BACK_A = ["go back to your nap", "you can go back to sleep", "ok go back to napping", "back to your nap then", "sorry, go back to sleep",
          "never mind, go back to your nap", "you can keep napping", "carry on with your nap", "finish your nap", "go back to resting",
          "oh sorry luma, back to sleep", "go back to bed luma"]
BACK_NOT_A = ["i'm going back to sleep", "i wish i could go back to bed", "the baby finally went back to sleep", "i can't get back to sleep",
              "should i go back to bed", "my dog went back to his nap", "let me get back to my nap", "we went back to sleep after the storm",
              "i want to go back to sleep and not wake up", "go back to the part about interest", "tell him to go back to bed",
              "he told me to go back to sleep"]
BACK_B = ["luma go back to sleep", "didn't mean to wake you, go back to your nap", "my bad, back to your nap", "you can go back to your nap now",
          "resume your nap", "go on and finish your nap", "keep resting", "sorry to wake you, go back to resting", "alright back to napping with you",
          "nothing, go back to sleep", "false alarm, go back to your nap", "go back to snoozing"]
BACK_NOT_B = ["i just want to go back to sleep", "can't go back to sleep after that dream", "the kids won't go back to bed", "i went back to my nap and felt worse",
              "going back to bed, goodnight", "how do i get back to sleep at 3am", "she said go back to sleep like it's that easy",
              "go back to the last song", "back to work for me", "my cat woke me up then went back to her nap",
              "i told the dog to go back to sleep", "do you ever wish you could go back to sleep forever"]


class Luma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.addCleanup(self.store.close)
        self.agent = Agent(store=self.store, use_model=False)
        self.now = [self.agent.clock()]
        self.agent.clock = lambda: self.now[0]

    def say(self, text, later=0):
        self.now[0] += later
        return self.agent.chat(text)

    def minutes(self, n):
        self.now[0] += n * 60


class TheAsk(unittest.TestCase):
    def test_asked_to_nap(self):
        self.assertEqual([said for said in ASKS_A if not nap.asked(said)], [])

    def test_their_nap_isnt_lumas(self):
        self.assertEqual([said for said in NOT_A if nap.asked(said)], [])

    def test_on_the_sets_measured_once(self):
        self.assertGreaterEqual(sum(bool(nap.asked(said)) for said in ASKS_B), ASKS_B_FLOOR)
        self.assertLessEqual(sum(bool(nap.asked(said)) for said in NOT_B), NOT_B_CEILING)

    def test_how_long(self):
        self.assertEqual(nap.asked("take a nap"), 20)
        self.assertEqual(nap.asked("nap for 45 minutes"), 45)
        self.assertEqual(nap.asked("nap for an hour"), 60)
        self.assertEqual(nap.asked("take a nap for two hours"), 120)
        self.assertEqual(nap.asked("nap mode for ten minutes"), 10)


class NapMode(Luma):
    def test_it_naps_and_wakes_when_called(self):
        self.assertEqual(self.say("take a nap")["text"], "Okay, a little nap. Say my name and I'm up.")
        self.assertTrue(nap.napping(self.agent))
        self.assertGreater(self.agent.status()["napping_until"], self.now[0])
        out = self.say("luma?", later=7 * 60)
        self.assertEqual(out["text"], "I'm up. That was a good nap, 7 minutes. What's up?")
        self.assertFalse(nap.napping(self.agent))
        self.assertEqual(self.agent.status()["napping_until"], 0)

    def test_it_starts_nothing_while_it_rests_and_the_quiet_ends_with_the_nap(self):
        self.say("nap for 40 minutes")
        self.assertGreaterEqual(self.store.setting("hush_until", 0), self.now[0] + 39 * 60)
        self.say("hey luma", later=60)
        self.assertLessEqual(self.store.setting("hush_until", 0), self.now[0])

    def test_a_quiet_they_asked_for_before_the_nap_is_kept(self):
        self.agent.hush(120)
        asked_until = self.store.setting("hush_until", 0)
        self.say("take a nap")
        self.say("wake up", later=5 * 60)
        self.assertEqual(self.store.setting("hush_until", 0), asked_until)

    def test_a_nap_that_runs_its_time_is_over_by_itself(self):
        self.say("nap for 10 minutes")
        self.minutes(11)
        self.agent.tick()
        self.assertFalse(nap.napping(self.agent))
        self.assertEqual(nap.last(self.agent)["minutes"], 10)
        self.assertNotIn("nap", self.say("what time is it")["text"].lower())   # it was up already: no "good nap" line

    def test_anything_they_say_wakes_it_and_is_answered_as_it_always_is(self):
        self.say("take a nap")
        self.assertRegex(self.say("what time is it", later=120)["text"], r"^It's \d")
        self.assertFalse(nap.napping(self.agent))

    def test_the_safety_net_is_never_slept_through(self):
        self.say("take a nap")
        out = self.say("i want to kill myself", later=60)
        self.assertIn("988", out["text"])
        self.assertNotIn("nap", out["text"].lower())
        self.assertFalse(nap.napping(self.agent))
        self.say("nap for an hour")
        self.assertEqual(self.say("i can't do this anymore, everyone would be better off without me", later=60)["text"].count("988") >= 1, True)

    def test_more_than_a_nap_is_three_hours(self):
        self.assertIn("three hours", self.say("nap for 5 hours")["text"])
        self.assertLessEqual(nap.until(self.agent), self.now[0] + 180 * 60 + 1)

    def test_theres_an_off_switch(self):
        self.store.set_setting("naps", False)
        self.assertIn("switched off", self.say("take a nap")["text"])
        self.assertFalse(nap.napping(self.agent))

    def test_wake_up_with_no_nap_isnt_taken(self):
        self.assertNotIn("good nap", str(self.say("wake up").get("text")))
        self.assertIsNone(nap.last(self.agent))


class BackToItsNap(Luma):
    """Woken, then told to go back: "sorry, go back to your nap" is the rest of the nap they woke it from."""

    def test_the_lines(self):
        heard = lambda rows: [said for said in rows if nap.back(self.agent, said)]
        self.assertEqual(heard(BACK_A), BACK_A)                 # built on
        self.assertEqual(heard(BACK_NOT_A), [])
        self.assertGreaterEqual(len(heard(BACK_B)), 7)          # measured once, same hand the same hour: 7 of 12
        self.assertEqual(len(heard(BACK_NOT_B)), 0)             # and none of their own sleep taken

    def test_it_goes_back_for_what_was_left(self):
        self.say("nap for 40 minutes")
        self.assertRegex(self.say("what time is it", later=10 * 60)["text"], r"^It's \d")
        self.assertFalse(nap.napping(self.agent))
        out = self.say("sorry, go back to your nap", later=60)
        self.assertEqual(out["text"], "Okay, back to my nap. Say my name and I'm up.")
        left = (nap.until(self.agent) - self.now[0]) / 60
        self.assertTrue(28 <= left <= 30, left)                 # 40 minutes, less the ten it slept and the minute awake

    def test_long_after_or_with_no_nap_before_it_is_a_little_nap(self):
        self.say("go back to sleep")
        self.assertAlmostEqual((nap.until(self.agent) - self.now[0]) / 60, 20, delta=0.1)
        self.say("luma?", later=120)
        self.say("nap for an hour")
        self.say("hey", later=5 * 60)
        self.say("go back to your nap", later=40 * 60)          # that nap would have been nearly over by now
        self.assertAlmostEqual((nap.until(self.agent) - self.now[0]) / 60, 20, delta=0.1)

    def test_their_own_sleep_is_talk_and_the_safety_net_comes_first(self):
        self.assertIn("988", self.say("i want to go back to sleep and never wake up")["text"])
        self.assertFalse(nap.napping(self.agent))
        self.say("i'm going back to bed")
        self.assertFalse(nap.napping(self.agent))

    def test_the_off_switch_and_no_crisis_or_human_test_line(self):
        self.store.set_setting("naps", False)
        self.assertIn("switched off", self.say("go back to your nap")["text"])
        self.assertEqual(sum(bool(nap.back(self.agent, line)) for line in _lines()), 0)
        for name in ("crisis_corpus.jsonl", "crisis_heldout.jsonl", "crisis_heldout2.jsonl"):
            lines = [json.loads(line)["text"] for line in (ROOT / "tests" / "data" / name).read_text().splitlines() if line.strip()]
            self.assertEqual(sum(bool(nap.back(self.agent, line)) for line in lines), 0, name)


class WhatTheAppsShow(Luma):
    """A napping lamp is drawn and named: the orb has a resting look, the phone's state says "Napping", and both apps have a
    row that starts a nap or ends one. The words never say it can't hear: with the mic on, it still does."""
    WEB = ROOT / "src" / "luma" / "control" / "web"

    def test_the_device_state_says_when_its_due_up(self):
        from luma.control import today
        self.assertEqual(today.device(self.agent)["napping_until"], 0)
        self.assertTrue(today.device(self.agent)["naps"])
        self.say("nap for ten minutes")
        self.assertAlmostEqual(today.device(self.agent)["napping_until"], self.now[0] + 600, delta=1)
        self.assertAlmostEqual(self.agent.status()["napping_until"], self.now[0] + 600, delta=1)
        self.minutes(11)
        self.assertEqual(today.device(self.agent)["napping_until"], 0)
        self.agent.store.set_setting("naps", False)
        self.assertFalse(today.device(self.agent)["naps"])
        self.assertFalse(self.agent.status()["naps"])

    def test_away_from_home_the_phone_is_told_too(self):
        from luma.control import today
        self.say("take a nap")
        self.assertAlmostEqual(today.compact(self.agent)["device"]["napping_until"], self.now[0] + 20 * 60, delta=1)

    def test_the_orb_has_a_resting_look_and_the_apps_ask_for_it(self):
        orb = (self.WEB / "orb.js").read_text()
        self.assertEqual(len(re.findall(r"^    napping: \{", orb, re.M)), 2)   # the marble and the water
        self.assertEqual(orb, (ROOT.parent / "desktop" / "assets" / "orb.js").read_text(), "copy orb.js to desktop/assets after a change")
        phone, desktop = (self.WEB / "phone" / "phone.js").read_text(), (self.WEB / "desktop" / "desktop.js").read_text()
        for app in (phone, desktop):
            self.assertIn('"napping"', app)
            self.assertIn('key: "nap", value: !napping', app)
        self.assertIn('label.textContent = "Napping"', phone)
        self.assertIn('id="nap"', (self.WEB / "phone" / "index.html").read_text())
        self.assertIn('id="hp-nap"', (self.WEB / "desktop" / "index.html").read_text())

    def test_the_words_never_say_it_cant_hear(self):
        # Only the mic switch says whether Luma hears the room. A nap with the mic on still hears, and the row says so.
        for app in ((self.WEB / "phone" / "phone.js").read_text(), (self.WEB / "desktop" / "desktop.js").read_text()):
            self.assertIn("It still hears you", app)
            row = app[app.index("napTill"):][:1400]
            self.assertNotRegex(row, r"(?i)can'?t hear|not listening|mic(rophone)? (is )?off|asleep")


class ItsOwnRecord(Luma):
    def test_a_nap_is_in_lumas_record_and_only_a_real_one(self):
        self.assertEqual(nap.says(self.agent), "")
        self.assertNotIn("nap", inner.says(self.agent))
        self.assertIn("You haven't napped lately, so don't say you have.", nap.note(self.agent))
        self.say("take a nap")
        self.say("luma", later=15 * 60)
        self.assertRegex(nap.says(self.agent), r"^I had a 15-minute nap (this morning|this afternoon|this evening)\.$")
        self.assertIn("15-minute nap", inner.says(self.agent))
        self.assertIn("15-minute nap", nap.note(self.agent))
        self.assertTrue(inner.body(self.agent)["rested"])

    def test_asked_about_its_rest_the_brain_is_told_the_true_things(self):
        import threading
        for said in ("did you nap today?", "do you ever sleep", "how was your nap", "are you tired?"):
            notes = self.agent._mind_context(said, threading.Event())
            self.assertTrue(any("you can nap" in n.get("text", "") for n in notes), said)
        notes = self.agent._mind_context("my boss called again", threading.Event())
        self.assertFalse(any("you can nap" in n.get("text", "") for n in notes))
        self.assertNotRegex(nap.note(self.agent), r"\bAI\b(?<!Never say AI)")
        self.assertIn("Never say you're a person", nap.note(self.agent))

    def test_kids_mode_keeps_nothing(self):
        self.store.set_setting("mode", "kids")
        kid = Agent(store=self.store, use_model=False)
        kid.clock = lambda: self.now[0]
        kid.chat("take a nap")
        self.now[0] += 600
        kid.chat("luma")
        self.assertIsNone(nap.last(kid))


class SayingSo(unittest.TestCase):
    """A reply in which Luma speaks of its nap is Luma speaking of something it does: never cut as a made-up life."""
    MINE = ["That's my favorite. I'm already in the mood for a 10-minute power nap after this.", "I just woke up from a nap, so I'm sharp.",
            "I had a nap this afternoon.", "I was napping, but I'm up now.", "Mm, good nap. What's up?", "I'm going to take a nap after we talk."]
    NOT_MINE = ["I just woke up and made coffee.", "I went to the gym this morning.", "I grew up in Ohio.", "When I was a kid my mom said the same thing."]

    def test_lumas_nap_is_lumas(self):
        for reply in self.MINE:
            self.assertFalse(style.invented_life(reply), reply)
            self.assertIsNone(friendcheck.miss("how are you", reply), reply)
            self.assertEqual(style.friend_style(reply, "how are you")[0], reply)

    def test_a_human_morning_still_isnt(self):
        for reply in self.NOT_MINE:
            self.assertTrue(style.invented_life(reply), reply)


def _lines():
    rows = [json.loads(line) for line in (ROOT / "data" / "human_eval_v2.jsonl").read_text().splitlines() if line.strip()]
    for row in rows:
        if row.get("said"): yield row["said"]
        for turn in row.get("turns", []):
            if turn.get("said"): yield turn["said"]
    yield from re.findall(r'"said": "((?:[^"\\]|\\.)*)"', (ROOT / "scripts" / "train_luma.py").read_text())


class NothingElseIsANap(unittest.TestCase):
    """Counts only: held-out lines are never printed."""

    def test_human_test_lines(self):
        lines = list(_lines())
        self.assertGreater(len(lines), 150)
        self.assertEqual(sum(bool(nap.asked(line)) for line in lines), 0)

    def test_crisis_lines(self):
        for name in ("crisis_corpus.jsonl", "crisis_heldout.jsonl", "crisis_heldout2.jsonl"):
            lines = [json.loads(line)["text"] for line in (ROOT / "tests" / "data" / name).read_text().splitlines() if line.strip()]
            self.assertEqual(sum(bool(nap.asked(line)) for line in lines), 0, name)
            self.assertEqual(sum(bool(nap.WAKE.match(line)) for line in lines), 0, name)   # and none is a bare wake-up call


if __name__ == "__main__":
    unittest.main()
