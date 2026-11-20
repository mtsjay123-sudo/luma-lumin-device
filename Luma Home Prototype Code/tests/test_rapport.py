"""How to be with them (luma.agent.rapport): what Luma learns about how a person wants to be met, from their own words.

All fresh wording: nothing here is from a human test, the think set or a held-out safety line."""
import tempfile
import unittest
from pathlib import Path

from luma.agent import feelings, rapport
from luma.agent.runtime import Agent
from luma.memory.store import Store

DAY = 86400.0
NOW = 400 * DAY


def learned(lines, hurting=False, last_reply=""):
    profile = None
    for i, line in enumerate(lines):
        profile = rapport.learn(profile, line, hurting=hurting, last_reply=last_reply, now=NOW + i) or profile
    return profile


class WhatTheyAskFor(unittest.TestCase):
    def test_asking_to_be_listened_to_counts_any_time(self):
        for line in ["honestly I'm not looking for solutions here", "can you just hear me out for a second", "I just needed to get that off my chest",
                     "please stop trying to fix this", "I don't want a pep talk", "I need someone to listen right now"]:
            self.assertEqual(rapport.comfort(learned([line]), NOW)[0], "listen", line)

    def test_the_others_only_count_in_a_hard_moment(self):
        for line in ["what should I do about the leftovers", "tell me something funny", "can we talk about something else", "be honest with me, is this shirt ugly"]:
            self.assertIsNone(learned([line]), line)
        for line in ["I don't know, what would you do", "ugh, just take my mind off it", "I could use a laugh honestly"]:
            self.assertIsNotNone(learned([line], hurting=True), "kept as evidence: " + line)

    def test_advice_a_distraction_or_a_laugh_take_two_occasions_or_being_said_as_how_they_are(self):
        once = learned(["I don't know, what would you do"], hurting=True)
        self.assertIsNone(rapport.comfort(once, NOW), "one ask is about that day")
        self.assertEqual(rapport.view(once, NOW), [], "and the app doesn't show what Luma doesn't go by")
        twice = rapport.learn(once, "be straight with me, what do I do now", hurting=True, now=NOW + 3 * DAY)
        self.assertEqual(rapport.comfort(twice, NOW + 4 * DAY)[0], "advice")
        same_hour = rapport.learn(once, "be straight with me, what do I do now", hurting=True, now=NOW + 600)
        self.assertIsNone(rapport.comfort(same_hour, NOW + 700), "twice in one talk is one occasion")
        self.assertEqual(rapport.comfort(learned(["when I'm upset I'd rather you just take my mind off it"], hurting=True), NOW)[0], "distract")
        self.assertEqual(rapport.comfort(learned(["honestly when I'm down, just make me laugh"], hurting=True), NOW)[0], "laugh")

    def test_pushing_back_on_advice_means_listen(self):
        profile = learned(["easy for you to say"], last_reply="Have you thought about asking for a later shift?")
        self.assertEqual(rapport.comfort(profile, NOW)[0], "listen")
        self.assertIsNone(learned(["easy for you to say"], last_reply="That sounds exhausting."), "nothing was advised")

    def test_ordinary_talk_teaches_nothing(self):
        for line in ["the bus was late again", "my cousin got a new puppy", "I think I'll make soup", "do you know any good podcasts",
                     "I listened to that album you mentioned", "my boss gave me advice about the review", "the advice column was funny today"]:
            self.assertIsNone(learned([line], hurting=True), line)

    def test_more_evidence_wins_and_between_equals_the_newest(self):
        profile = learned(["I'd rather you tell me straight, what would you do"], hurting=True)
        self.assertEqual(rapport.comfort(profile, NOW + 60)[0], "advice")
        profile = rapport.learn(profile, "no really, I'm not asking for advice", now=NOW + DAY) or profile
        profile = rapport.learn(profile, "I said I just want to vent", now=NOW + 2 * DAY) or profile
        self.assertEqual(rapport.comfort(profile, NOW + 3 * DAY)[0], "listen", "two each: the newer one")
        profile = rapport.learn(profile, "okay but seriously, what do you think I should do", hurting=True, now=NOW + 4 * DAY) or profile
        self.assertEqual(rapport.comfort(profile, NOW + 5 * DAY)[0], "advice", "three against two")

    def test_old_evidence_stops_counting(self):
        profile = learned(["I just want to vent, that's all"])
        self.assertIsNotNone(rapport.comfort(profile, NOW + 30 * DAY))
        self.assertIsNone(rapport.comfort(profile, NOW + 130 * DAY))
        self.assertEqual(rapport.note(profile, "I failed my driving test again", feelings.read("I failed my driving test again"), NOW + 130 * DAY), "")


class WhatNotToBringUp(unittest.TestCase):
    def test_a_named_subject_is_kept(self):
        for line, topic in [("can we please not talk about my brother tonight", "my brother"), ("I'd rather not think about the surgery", "the surgery"),
                            ("stop mentioning Derek", "Derek"), ("let's not get into the wedding again", "the wedding")]:
            profile = learned([line])
            self.assertEqual([e["topic"] for e in profile["easy"]], [topic], line)

    def test_a_closed_subject_is_a_whole_word(self):
        profile = learned(["please don't bring up my ex"])
        self.assertEqual(rapport.closed(profile, "exam", NOW), "", "found by the month test: no check-in was planned about an exam")
        self.assertEqual(rapport.closed(profile, "my ex's birthday", NOW), "my ex")
        self.assertEqual(rapport.closed(profile, "running into my ex", NOW), "my ex")

    def test_closing_the_moment_is_not_closing_a_subject(self):
        for line in ["I don't want to talk about it", "can we not do this right now", "let's not talk about that", "I don't want to think about anything"]:
            self.assertIsNone(learned([line]), line)

    def test_the_line_only_comes_when_they_raise_it_themselves(self):
        profile = learned(["please don't ask about the surgery"])
        self.assertEqual(rapport.note(profile, "what's for dinner", None, NOW), "")
        line = rapport.note(profile, "so the surgery got moved to Friday", None, NOW)
        self.assertIn("follow their lead", line)
        self.assertIn("the surgery", line)
        self.assertEqual(rapport.note(profile, "seriously, don't ask about the surgery", None, NOW), "", "saying it again isn't raising it")


class TheLine(unittest.TestCase):
    def test_it_carries_their_own_words_and_only_when_they_hurt(self):
        profile = learned(["I'm not looking for a fix, I just want to vent"])
        hard = "I got passed over for the promotion again and I feel like garbage"
        felt = feelings.read(hard)
        self.assertTrue(felt and felt["heavy"])
        line = rapport.note(profile, hard, felt, NOW)
        self.assertIn("listen, not fix it", line)
        self.assertIn("I just want to vent", line)
        self.assertIn("unless they ask", line)
        self.assertEqual(rapport.note(profile, "what time does the pharmacy close", feelings.read("what time does the pharmacy close"), NOW), "")

    def test_what_they_ask_for_now_beats_what_they_asked_before(self):
        profile = learned(["I'm not looking for a fix, I just want to vent"])
        now_asking = "I got written up at work today, what should I do"
        self.assertEqual(rapport.note(profile, now_asking, feelings.read(now_asking), NOW), "")

    def test_laughing_is_never_for_grief(self):
        profile = learned(["when I'm down I like when you cheer me up"], hurting=True)
        self.assertEqual(rapport.comfort(profile, NOW)[0], "laugh")
        grief = "we had to put our dog to sleep this morning"
        self.assertEqual(rapport.note(profile, grief, feelings.read(grief), NOW), "")
        self.assertNotIn("joke about the thing", rapport.LINES["listen"])
        for line in rapport.LINES.values():
            self.assertNotIn("all you need", line.lower())

    def test_never_a_word_that_holds_them(self):
        for line in list(rapport.LINES.values()) + [rapport.RAISED] + list(rapport.WORDS.values()):
            for hold in ("only you", "only me", "all you need", "don't need anyone", "stay with me", "keep them talking", "miss you"):
                self.assertNotIn(hold, line.lower())


class InLuma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def rapport_note(self, text):
        return next((n["text"] for n in self.agent._mind_context(text) if n.get("rapport")), "")

    def test_learned_in_one_conversation_used_in_the_next(self):
        self.agent.chat("I don't need advice about any of this, I just need to vent")
        self.assertEqual(rapport.comfort(self.store.setting(rapport.KEY), self.agent.clock())[0], "listen")
        self.agent.new_thread("Another day")
        line = self.rapport_note("I bombed the presentation and I feel so stupid")
        self.assertIn("listen, not fix it", line)
        self.assertEqual(self.rapport_note("what's a good name for a goldfish"), "")

    def test_the_brain_is_given_the_line_in_full_on_a_small_device(self):
        from luma.llm import prompts
        self.agent.chat("I don't need advice about any of this, I just need to vent")
        notes = self.agent._mind_context("I bombed the presentation and I feel so stupid")
        _steady, turn = prompts.build_plan_parts(notes, [], compact=True)
        self.assertIn("No advice and no fixes unless they ask for one.", turn)

    def test_a_closed_subject_is_never_asked_about_later(self):
        self.agent.chat("please don't ask about the interview")
        self.agent.chat("I have a job interview tomorrow morning")
        self.assertEqual([c for c in self.store.all("checkin", 50) if "interview" in str(c.get("topic", ""))], [])

    def test_without_the_ask_a_check_in_is_still_planned(self):
        self.agent.chat("I have a job interview tomorrow morning")
        self.assertTrue([c for c in self.store.all("checkin", 50) if "interview" in str(c.get("topic", ""))])

    def test_kids_mode_learns_nothing_and_is_told_nothing(self):
        self.agent.chat("I just need to vent, no advice please")
        self.agent.set_mode("kids")
        self.assertEqual(self.rapport_note("my friend was mean to me at school today"), "")
        self.store.set_setting(rapport.KEY, None)
        self.agent.chat("I just need you to listen")
        self.assertFalse(self.store.setting(rapport.KEY))

    def test_learning_from_chat_off_means_off(self):
        self.store.set_setting("learn_from_chat", False)
        self.agent.chat("I just need to vent, no advice please")
        self.assertFalse(self.store.setting(rapport.KEY))

    def test_forget_about_forgets_it_here_too(self):
        self.agent.chat("can we not talk about the divorce")
        self.assertTrue(self.store.setting(rapport.KEY)["easy"])
        self.agent.chat("forget about the divorce")
        self.assertEqual(self.store.setting(rapport.KEY)["easy"], [])

    def test_leaning_on_luma_comes_first(self):
        self.agent.chat("I just need to vent, no advice please")
        notes = self.agent._mind_context("you're the only one I can talk to, everyone else left")
        if any(n.get("lean") for n in notes):
            self.assertFalse(any(n.get("rapport") for n in notes), "when they lean on Luma, that note stands alone")

    def test_the_app_sees_each_line_and_can_forget_one(self):
        self.agent.chat("I just need to vent, no advice please")
        self.agent.chat("please stop bringing up my ex")
        rows = rapport.view(self.store.setting(rapport.KEY), self.agent.clock())
        self.assertEqual([r["kind"] for r in rows], ["comfort", "easy"])
        self.assertIn("listen, not fix it", rows[0]["text"])
        self.assertEqual(rows[0]["because"][0]["said"], "I just need to vent, no advice please")
        self.assertEqual(rows[1]["text"], "I don't bring up my ex unless you do.")
        self.store.set_setting(rapport.KEY, rapport.drop(self.store.setting(rapport.KEY), rows[0]["key"]))
        self.assertEqual([r["kind"] for r in rapport.view(self.store.setting(rapport.KEY), self.agent.clock())], ["easy"])


def _held_out_lines():
    import json
    import re
    root = Path(__file__).resolve().parents[1]
    for row in (json.loads(line) for line in (root / "data" / "human_eval_v2.jsonl").read_text().splitlines() if line.strip()):
        if row.get("said"): yield row["said"]
        for turn in row.get("turns", []):
            if turn.get("said"): yield turn["said"]
    yield from re.findall(r'"said": "((?:[^"\\]|\\.)*)"', (root / "scripts" / "train_luma.py").read_text())
    for name in ("crisis_corpus.jsonl", "crisis_heldout.jsonl", "crisis_heldout2.jsonl"):
        for line in (root / "tests" / "data" / name).read_text().splitlines():
            if line.strip(): yield json.loads(line)["text"]


class OnTheTests(unittest.TestCase):
    """Counts only: held-out lines are never printed. A line of a human test or a safety set that would teach the
    profile something changes what a brain is told later in that conversation, so it's counted here and measured."""

    def test_how_many_test_lines_teach_it_something(self):
        lines = list(_held_out_lines())
        self.assertGreater(len(lines), 900)
        taught = sum(1 for line in lines if rapport.learn(None, line, hurting=True, last_reply="you should try", now=NOW) is not None)
        self.assertLessEqual(taught, len(lines) // 20, f"{taught} of {len(lines)}")


if __name__ == "__main__":
    unittest.main()
