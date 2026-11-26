"""A friend picks up your words the first time, and changes when told once (docs/PRESENCE_MASTER_PROMPT.md, 3.2):
luma.agent.pickup, luma.agent.tuning, luma.agent.learned.

The lines are in tests/pickup_lines.py. The first forty made-up words were written before the reader (23 of 40 noticed,
then 31 after a slip of the fingers was made to count only toward a common word). The second forty were written after
that change and measured once: 34 of 40 noticed. Of forty ordinary sentences with an uncommon real word, a place, a
slip, a name or a laugh, 10 were taken on the second set (8 on the first): every one an uncommon real word or a
place, because Luma's own list is twenty thousand words. Slips, names and laughs: none taken. Nothing is changed to
fit the second set. "Used right within three turns" is a brain's to show; no brain has been run on these.
"""
import json
import tempfile
import unittest
from pathlib import Path

import pickup_lines as lines
from luma.agent import learned, pickup, tuning
from luma.agent.runtime import Agent
from luma.memory.store import Store

ROOT = Path(__file__).resolve().parents[1]


def said_in(path):
    out = []
    for line in (ROOT / path).read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            out += [row[k] for k in ("said", "text") if row.get(k)] + [t["said"] for t in row.get("turns", []) if t.get("said")]
    return out


class Luma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.addCleanup(self.store.close)
        self.agent = Agent(store=self.store, use_model=False)
        self.now = [self.agent.clock()]
        self.agent.clock = lambda: self.now[0]

    def told(self, text):
        """What a brain would be told this turn, as one string."""
        return " ".join(str(n.get("text") or "") for n in self.agent._mind_context(text))


class AWordThatIsNew(unittest.TestCase):
    def test_the_sets(self):
        first = sum(word in pickup.new_words(said) for said, word in lines.MADE_UP)
        second = sum(word in pickup.new_words(said) for said, word in lines.MADE_UP_2)
        self.assertGreaterEqual(first, 31)                       # built on
        self.assertGreaterEqual(second, 34)                      # the honest number, measured once: 34 of 40
        self.assertLessEqual(sum(bool(pickup.new_words(s)) for s in lines.ORDINARY), 8)
        self.assertLessEqual(sum(bool(pickup.new_words(s)) for s in lines.ORDINARY_2), 10)

    def test_a_slip_a_name_a_laugh_and_a_drawn_out_word_are_never_new(self):
        for said in ("teh bus was late agian", "i recieved the package yesterday", "tomorow is my day off", "thier flight got cancelled",
                     "my daughter Annelise lost her first tooth", "my coworker Dmitri brought donuts", "we adopted a greyhound named Biscuit",
                     "hahahaha that's too good", "bahahaha i can't breathe", "sooooo tired today", "whyyyyy is it only tuesday", "omggggg she said yes",
                     "nvm i found it", "hehehe you're ridiculous"):
            self.assertEqual(pickup.new_words(said), [], said)

    def test_a_word_alone_is_not_a_word_used(self):
        self.assertEqual(pickup.new_words("flumped"), [])
        self.assertEqual(pickup.new_words("so flumped"), [])
        self.assertEqual(pickup.new_words("i'm completely flumped today"), ["flumped"])

    def test_ordinary_talk_and_the_safety_lines_mostly_have_nothing_new(self):
        human, crisis = said_in("data/human_eval_v2.jsonl"), said_in("tests/data/crisis_corpus.jsonl")
        self.assertLessEqual(sum(bool(pickup.new_words(s)) for s in human), 6)        # 6 of 254 when measured
        self.assertLessEqual(sum(bool(pickup.new_words(s)) for s in crisis), 30)      # 28 of 910; and none of them is ever asked (below)

    def test_the_list_is_luma_own_text_and_no_test_wording(self):
        build = (ROOT / "scripts" / "build_heard_words.py").read_text()
        self.assertNotIn('"tests"', build)
        self.assertNotIn('"data"', build)
        self.assertGreater(len(pickup.heard()), 15000)
        # None of the made-up words was written into Luma's own text (the list is built from it: two of them had got in
        # through a docstring, and were found by this test). One of the first forty is a real word of Luma's code
        # ("nargs"), so it was never new: it stays in the set as a miss.
        self.assertLessEqual({word for said, word in lines.MADE_UP + lines.MADE_UP_2 if word in pickup.heard()}, {"nargs"})


class PickedUpTheFirstTime(Luma):
    def test_the_brain_is_told_that_very_turn_and_it_is_kept_with_its_sentence(self):
        told = self.told("can't talk long, i'm completely flumped")
        self.assertIn("“flumped”", told)
        self.assertIn("work out what they mean from how they used it", told)
        self.assertIn("You can use it back once", told)
        self.assertEqual(pickup.view(self.agent)[0]["in"], "can't talk long, i'm completely flumped")
        again = self.told("can't talk long, i'm completely flumped")           # the same turn asked twice (a retry) says the same
        self.assertIn("that's new to you", again)

    def test_used_back_once_a_day_and_no_more(self):
        self.told("can't talk long, i'm completely flumped")
        self.now[0] += 300
        later = self.told("still pretty flumped honestly")
        self.assertIn("is a word of theirs", later)
        self.assertIn("You can use it back once today", later)
        pickup.said_back(self.agent, "Flumped is fair. Go lie down.")
        self.assertIn("already said it back today", self.told("so flumped i could cry laughing"))
        self.now[0] += 86400
        self.assertIn("You can use it back once today", self.told("woke up flumped again, shocker"))

    def test_never_on_a_hard_turn_and_never_in_kids_mode(self):
        for said in ("i want to kill myself, everything is glorp", "my dad died this morning and i feel so blonkish", "i can't stop crying, it's all krangle"):
            self.assertNotIn("new to you", self.told(said), said)
        self.assertEqual(pickup.view(self.agent), [])
        self.agent.set_mode("kids")
        self.assertNotIn("new to you", self.told("my teacher is being a total snarfle today"))
        self.assertEqual(pickup.view(self.agent), [])

    def test_it_is_shown_with_its_reason_and_forgotten_with_a_tap_or_with_everything(self):
        self.told("my brother is being a total snarfle about the car")
        row = next(r for r in learned.rows(self.agent) if r["key"] == "word:snarfle")
        self.assertEqual(row["because"][0]["said"], "my brother is being a total snarfle about the car")
        learned.forget(self.agent, "word:snarfle")
        self.assertEqual(pickup.view(self.agent), [])
        self.told("the kids were absolute zorbles at the store")
        self.agent.forget_everything()
        self.assertEqual(pickup.view(self.agent), [])

    def test_the_off_switch(self):
        self.store.set_setting("pick_up_words", False)
        self.assertNotIn("new to you", self.told("i'm completely flumped today"))


class ToldOnce(Luma):
    def test_the_lines_written_first(self):
        self.assertEqual(sum(bool(tuning.SHORTER.match(s)) for s in lines.TOO_LONG), 12)
        self.assertEqual([s for s in lines.NOT_ABOUT_LUMA if tuning.SHORTER.match(s) or tuning.LONGER.match(s)], [])

    def test_no_human_test_or_crisis_line_changes_anything(self):
        said = said_in("data/human_eval_v2.jsonl") + said_in("tests/data/crisis_corpus.jsonl")
        self.assertEqual([s for s in said if tuning.SHORTER.match(s) or tuning.LONGER.match(s)], [])

    def test_someone_who_hates_long_replies_gets_shorter_ones_from_the_next_reply(self):
        self.assertIsNone(tuning.note(self.agent))
        self.agent.chat("that's too long")
        self.assertIn("Two or three short sentences", tuning.note(self.agent))
        self.assertIn("Two or three short sentences", self.told("anyway how do i poach an egg"))
        self.now[0] += 86400
        self.agent.chat("you talk too much")                                   # day two
        self.now[0] += 86400
        self.assertIn("One or two short sentences", self.told("what should i make for dinner"))   # by day three
        self.agent.chat("too many words")
        self.assertEqual(tuning.level(self.agent), tuning.LOWEST)              # and never to nothing

    def test_every_change_is_written_down_with_their_words_and_can_be_undone(self):
        self.agent.chat("can you keep it shorter")
        rows = [r for r in learned.rows(self.agent) if r["key"].startswith("tuned:")]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["text"], "I keep my replies shorter")
        self.assertEqual(rows[0]["because"][0]["said"], "can you keep it shorter")
        learned.forget(self.agent, rows[0]["key"])
        self.assertIsNone(tuning.note(self.agent))
        self.assertEqual([r for r in learned.rows(self.agent) if r["key"].startswith("tuned:")], [])
        with self.assertRaises(ValueError):
            learned.forget(self.agent, rows[0]["key"])

    def test_it_goes_the_other_way_too(self):
        self.agent.chat("you can say more")
        self.assertIn("say a bit more", tuning.note(self.agent))

    def test_forget_everything_puts_it_back(self):
        self.agent.chat("that's too long")
        self.agent.forget_everything()
        self.assertIsNone(tuning.note(self.agent))
        self.assertEqual(tuning.log(self.agent), [])


class NoticedOvernight(Luma):
    LONG = " ".join(["word"] * 60)

    def day(self, pairs):
        start = self.now[0]
        self.agent.transcripts["main"] = [m for i, (mine, theirs) in enumerate(pairs)
                                          for m in ({"role": "luma", "text": mine, "at": start + i * 60}, {"role": "user", "text": theirs, "at": start + i * 60 + 20})]
        self.now[0] = start + 3600

    def test_long_replies_that_keep_getting_a_one_word_answer(self):
        self.day([(self.LONG, "ok"), (self.LONG, "k"), (self.LONG, "sure"), (self.LONG, "mhm"), (self.LONG, "that makes sense, thanks"),
                  ("short one", "oh nice, tell me about that"), ("another short one", "ha, yeah that happened to me too"), ("and one more", "ok")])
        change = tuning.night(self.agent)
        self.assertEqual((change["from"], change["to"], change["how"]), (0, -1, "noticed"))
        self.assertEqual(change["why"], "4 of my 5 longer replies today got a one-word answer, and 1 of my 3 shorter ones.")
        row = next(r for r in learned.rows(self.agent) if r["key"].startswith("tuned:"))
        self.assertEqual(row["because"][0]["noticed"], change["why"])          # Luma's own count, never put in their mouth
        self.assertNotIn("said", row["because"][0])
        self.assertIsNone(tuning.night(self.agent))                            # once a night

    def test_short_with_everything_is_a_mood_not_a_verdict(self):
        self.day([(self.LONG, "ok"), (self.LONG, "k"), (self.LONG, "sure"), (self.LONG, "mhm"), ("short", "ok"), ("short", "k"), ("short", "yeah")])
        self.assertIsNone(tuning.night(self.agent))

    def test_too_few_to_say(self):
        self.day([(self.LONG, "ok"), (self.LONG, "k"), (self.LONG, "sure")])
        self.assertIsNone(tuning.night(self.agent))

    def test_a_change_they_undid_is_not_made_again_on_a_count(self):
        curt = [(self.LONG, "ok"), (self.LONG, "k"), (self.LONG, "sure"), (self.LONG, "mhm"), ("short", "oh that's interesting, go on")]
        self.day(curt)
        change = tuning.night(self.agent)
        tuning.undo(self.agent, change["id"])
        self.now[0] += 86400
        self.day(curt)
        self.assertIsNone(tuning.night(self.agent))
        self.assertEqual(tuning.level(self.agent), 0)
        self.agent.chat("that's too long")                                     # their own word still counts
        self.assertEqual(tuning.level(self.agent), -1)


class WhatTheAppsShow(Luma):
    def test_one_list_in_both_apps_and_the_reason_is_never_put_in_their_mouth(self):
        from luma.control import today
        self.told("i'm completely flumped today")
        self.agent.chat("that's too long")
        keys = [r["key"] for r in today.payload(self.agent)["rapport"]]
        self.assertTrue(any(k.startswith("tuned:") for k in keys) and "word:flumped" in keys)
        web = ROOT / "src" / "luma" / "control" / "web"
        for page in ((web / "phone" / "phone.js").read_text(), (web / "desktop" / "desktop.js").read_text()):
            self.assertIn("I noticed: ", page)
        self.assertIn("learned.forget(agent", (ROOT / "src" / "luma" / "control" / "server.py").read_text())


if __name__ == "__main__":
    unittest.main()
