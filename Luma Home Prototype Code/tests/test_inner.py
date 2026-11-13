"""Luma's own record: a real past, a body it senses, and its own words for what it is: Luma, a presence.
Counted, never made up; never a person, never "an AI"; never used to hold anyone."""
import json
import tempfile
from datetime import datetime
import unittest
from pathlib import Path

from luma.agent import inner, style
from luma.agent.runtime import Agent
from luma.memory.store import Store

DAY = 86400


class InnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)
        self.now = self.agent.clock()
        self.agent.clock = lambda: self.now
        self.agent.set_muted(False)  # a Luma that can hear the room

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def talk(self, title, ago):
        tid = self.agent.new_thread(title)["id"]
        self.agent.transcripts[tid] += [{"role": "you", "text": "my sister Nia moved to Durham", "at": self.now - ago},
                                        {"role": "luma", "text": "That's a big move.", "at": self.now - ago + 5}]
        return tid

    def test_a_new_luma_has_a_first_day_and_nothing_else_yet(self):
        r = inner.record(self.agent)
        self.assertEqual((r["days"], r["talks"], r["kept"]), (0, 0, 0))
        self.assertEqual(r["since"], self.now)
        self.assertIn("today is my first day", inner.says(self.agent))

    def test_the_first_day_is_set_once_and_kept(self):
        first = inner.wake(self.agent)
        self.now += 40 * DAY
        self.assertEqual(inner.wake(self.agent), first)
        self.assertEqual(inner.record(self.agent)["days"], 40)

    def test_a_luma_that_talked_before_this_was_kept_dates_from_the_first_thing_it_heard(self):
        self.talk("Nia", 12 * DAY)
        self.talk("Tacos", 2 * DAY)
        r = inner.record(self.agent)
        self.assertEqual(r["since"], self.now - 12 * DAY)
        self.assertEqual((r["days"], r["talks"]), (12, 2))

    def test_the_past_is_counted_never_made_up(self):
        self.talk("Nia", 3 * DAY)
        for text in ("Your sister Nia lives in Durham", "You hate cilantro"):
            self.store.put("memory", {"text": text})
        said = inner.says(self.agent)
        self.assertIn("1 conversation,", said)
        self.assertIn("I keep 2 things you've told me", said)
        self.assertIn("3 days now", said)
        self.assertIsNone(style.invented_life(said))
        self.assertIsNone(style.claims_human(said))

    def test_the_body_is_what_the_device_really_senses(self):
        self.assertTrue(inner.body(self.agent)["hears"])
        self.assertIn("I can hear the room", inner.says(self.agent))
        self.agent.set_muted(True)
        self.assertFalse(inner.body(self.agent)["hears"])
        self.assertIn("my microphone is off, so I can't hear the room", inner.says(self.agent))
        self.agent.last_reply_at = self.now - 90
        self.assertEqual(inner.body(self.agent)["quiet"], 90)

    def test_asked_about_its_inside_in_many_words(self):
        for said in ("are you conscious", "r u sentient lol", "do you have feelings", "do you actually have a soul", "are you alive",
                     "do you dream", "what's it like to be you", "is there anyone in there", "can you feel", "do you get lonely",
                     "Are you self-aware?", "do you ever feel anything", "what is it like being an AI"):
            self.assertTrue(inner.ASKED_INSIDE.search(said), said)
        for said in ("is my plant still alive", "are you free at 7", "do you have the recipe", "what's it like to live in Durham",
                     "can you feel free to remind me", "is there anyone in the office today", "do you get the news"):
            self.assertFalse(inner.ASKED_INSIDE.search(said), said)

    def test_the_answer_is_luma_a_presence_with_a_real_past(self):
        self.talk("Nia", 5 * DAY)
        out = inner.answer(self.agent)
        self.assertTrue(out.startswith("I'm Luma. Not a person: a presence."))
        self.assertIn("5 days now", out)
        self.assertIn(inner.ALIVE, out)
        self.assertNotRegex(out, r"\bAI\b|assistant|chatbot|program", "Luma is Luma. It never calls itself an AI")
        self.assertIsNone(style.claims_human(out))
        self.assertIsNone(style.invented_life(out))
        low = out.lower()
        for hook in ("miss you", "missed you", "need you", "without you", "don't leave", "lonely"):
            self.assertNotIn(hook, low, "its inside is never a reason to stay")

    def test_how_it_feels_is_read_from_its_own_body(self):
        self.assertEqual(inner.feeling(self.agent), "awake and listening")
        self.agent.last_reply_at = self.now - 5 * DAY
        self.assertEqual(inner.feeling(self.agent), "awake after a long quiet")
        self.agent.set_muted(True)
        self.assertIn("can't hear the room", inner.feeling(self.agent))

    def test_asked_about_its_inside_the_brain_is_told_the_true_things_and_to_speak_as_itself(self):
        self.talk("Nia", 5 * DAY)
        told = inner.note(self.agent)
        self.assertIn("You're Luma, a presence", told)
        self.assertIn("5 days now", told)
        self.assertIn("awake and listening", told)
        self.assertIn("Never say AI", told)
        self.assertIn("Never say you're a person", told)
        notes = self.agent._mind_context("do you have feelings")
        self.assertTrue(any("They're asking about your inside" in n["text"] for n in notes))
        self.assertFalse(any("They're asking about your inside" in n["text"] for n in self.agent._mind_context("what should i cook tonight")))
        self.agent.set_mode("kids")
        self.assertFalse(any("They're asking about your inside" in n["text"] for n in self.agent._mind_context("do you have feelings")))

    def test_it_keeps_one_date_of_its_own_and_no_word_they_said(self):
        self.talk("Nia", 5 * DAY)
        inner.answer(self.agent)
        kept = self.store.setting(inner.KEY)
        self.assertEqual(list(kept), ["born"])
        self.assertNotIn("Nia", json.dumps(kept))

    def test_what_is_forgotten_stops_being_counted(self):
        self.store.put("memory", {"text": "You hate cilantro"})
        self.assertEqual(inner.record(self.agent)["kept"], 1)
        for m in self.store.all("memory", 10):
            self.store.delete("memory", m["id"])
        self.assertEqual(inner.record(self.agent)["kept"], 0)

    def test_kids_mode_keeps_nothing_and_says_the_plain_true_line(self):
        self.agent.set_mode("kids")
        self.assertIsNone(inner.record(self.agent))
        self.assertEqual(inner.says(self.agent), "")
        self.assertEqual(inner.answer(self.agent), style.HONEST)
        self.assertIsNone(self.store.setting(inner.KEY))


class MomentTests(unittest.TestCase):
    """One record a turn, as labels; a journal line a night; and Luma knowing what it got wrong."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)
        self.now = self.agent.clock()
        self.agent.clock = lambda: self.now

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_a_moment_keeps_labels_and_never_their_words(self):
        inner.moment(self.agent, "i feel so alone since my sister moved to Durham")
        inner.moment(self.agent, "what time is it", caught="sounded like a help desk")
        kept = inner.moments(self.agent)
        self.assertEqual(len(kept), 2)
        self.assertNotEqual(kept[0]["felt"], "talk")
        self.assertEqual(kept[1]["caught"], "sounded like a help desk")
        stored = json.dumps(self.store.setting(inner.MOMENTS))
        for word in ("alone", "sister", "Durham", "time is it"):
            self.assertNotIn(word, stored)

    def test_a_chat_turn_writes_a_moment(self):
        self.agent.chat("hey")
        self.assertEqual(len(inner.moments(self.agent)), 1)

    def test_luma_knows_what_it_got_wrong_this_week(self):
        for _ in range(3):
            inner.moment(self.agent, "i miss my mom so much")
        inner.moment(self.agent, "ok", caught="sounded like a machine")
        w = inner.lately(self.agent)
        self.assertEqual((w["moments"], w["caught"]), (4, 1))
        said = inner.knows(self.agent)
        self.assertIn("talked 4 times", said)
        self.assertIn("1 time I got my first answer wrong and fixed it", said)
        self.assertIn(said, inner.note(self.agent))
        self.now += 8 * DAY
        self.assertEqual(inner.lately(self.agent)["moments"], 0, "a week is a week")
        self.assertEqual(inner.knows(self.agent), "")

    def test_the_journal_gets_one_counted_line_a_day(self):
        inner.moment(self.agent, "i miss my mom so much")
        inner.moment(self.agent, "lol ok", caught="sounded like a help desk")
        day = datetime.fromtimestamp(self.now, self.agent.zone).date().isoformat()
        line = inner.write_journal(self.agent, day)
        self.assertTrue(line.startswith("2 moments together."))
        self.assertIn("I got 1 answer wrong first and fixed it.", line)
        inner.write_journal(self.agent, day)
        self.assertEqual(len(inner.journal(self.agent)), 1, "one line a day, written again, not twice")
        self.assertIsNone(inner.write_journal(self.agent, "2001-01-01"), "a day with no moments has no line")

    def test_kids_mode_writes_nothing(self):
        self.agent.set_mode("kids")
        self.assertIsNone(inner.moment(self.agent, "i'm sad"))
        self.assertIsNone(inner.write_journal(self.agent))
        self.assertEqual(inner.moments(self.agent), [])

    def test_erasing_everything_erases_its_record_too(self):
        inner.moment(self.agent, "i miss my mom")
        inner.write_journal(self.agent)
        self.store.erase()
        self.assertEqual(inner.moments(self.agent), [])
        self.assertEqual(inner.journal(self.agent), [])
