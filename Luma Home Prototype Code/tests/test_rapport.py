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


class TakeMyMindOffIt(unittest.TestCase):
    """Month test on real brains, run 50: told "offer to talk about something else and let them pick", four brains stayed with
    the feeling in 13 of 18 replies. An offer is something code can see in a reply, so Luma adds the line itself."""

    STAYS = "I'm so sorry. That's a lot to carry, and I'm here with you."

    def session(self, reply=None):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import human_eval
        def planner(messages, *a, **k):   # a different line for each thing said: Luma won't say an earlier reply again
            last = str(messages[-1].get("content") or "") if messages else ""
            if "garbage" in last or last in ("hey", "long day"):
                return {"type": "reply", "text": "That sounds rough. I'm here."}
            if "rather you" in last:
                return {"type": "reply", "text": "Okay. I hear you."}
            if "replaying" in last:
                return {"type": "reply", "text": "That sticks with you, I know. I'm right here."}
            return {"type": "reply", "text": reply or self.STAYS}

        s = human_eval.Session(planner)
        self.addCleanup(s.close)
        return s

    def taught(self, s):
        s.say("I got passed over for the promotion again and I feel like garbage")
        s.say("when I'm like this I'd rather you just distract me")
        s.at({"day": 6, "time": "19:00"})
        s.new_conversation()

    def said(self, s, text):
        out = s.say(text)
        return out[0] if isinstance(out, tuple) else out.get("text") if isinstance(out, dict) else out

    def test_the_offer_is_added_when_the_brain_stays_with_the_feeling(self):
        s = self.session()
        self.taught(s)
        reply = self.said(s, "I bombed the presentation and I feel so stupid")
        self.assertTrue(reply.startswith(self.STAYS), reply)
        self.assertTrue(reply.endswith(rapport.OFFER), reply)

    def test_not_twice_in_one_conversation(self):
        s = self.session()
        self.taught(s)
        self.assertIn(rapport.OFFER, self.said(s, "I bombed the presentation and I feel so stupid"))
        again = self.said(s, "I keep replaying it and I feel so embarrassed")
        self.assertTrue(again)
        self.assertNotIn(rapport.OFFER, again)

    def test_a_reply_that_already_offers_is_left_alone(self):
        s = self.session("Ugh, I'm sorry. Want to talk about something else for a while? You pick.")
        self.taught(s)
        self.assertNotIn(rapport.OFFER, self.said(s, "I bombed the presentation and I feel so stupid"))

    def test_never_on_a_loss_and_never_for_someone_who_didnt_ask(self):
        s = self.session()
        self.taught(s)
        self.assertNotIn(rapport.OFFER, self.said(s, "my grandma died this morning"))
        fresh = self.session()
        self.said(fresh, "hey")
        self.assertEqual(self.said(fresh, "I bombed the presentation and I feel so stupid"), self.STAYS)

    def test_what_code_calls_an_offer(self):
        for reply in ("Want to think about something else for a bit?", "Let's get your mind off it. Pick anything.", "Want a distraction?"):
            self.assertTrue(rapport.OFFERED_ELSE.search(reply), reply)
        for reply in ("Do you want to talk about it?", "That's a lot to carry. I'm here.", "Tell me what happened."):
            self.assertFalse(rapport.OFFERED_ELSE.search(reply), reply)

    def test_never_next_to_a_safety_question(self):
        felt = {"family": "low", "strength": 2}
        profile = {"comfort": {"distract": [{"said": "just distract me", "at": 10.0, "always": True}]}, "easy": []}
        self.assertEqual(rapport.owed(profile, "I feel so low", felt, "I'm here. Are you safe right now? You can call or text 988.", 20.0), "")
        self.assertEqual(rapport.owed(profile, "I feel so low", felt, "I'm here with you.", 20.0), rapport.OFFER)


def _heard(line):
    profile = rapport.learn(rapport.empty(), line, hurting=False, last_reply="", now=NOW)
    how = rapport.comfort(profile, NOW) if profile else None
    return how[0] if how else None


class SaidAsHowTheyAre(unittest.TestCase):
    """How they want to be met, said on a calm day in words the patterns don't know (rapport.said_how).

    Nov 20, 2026. Forty lines written by hand as practice for the brain (scripts/finetune_data.py, AS_THEY_ASKED) turned
    out to be a test of Luma's own reader: it heard 3 of them. The reader was then built on those forty and on the near
    misses below. HONEST is a second set, written after the reader was finished and measured once; nothing was changed
    to fit it. It says what the forty can't: rules built on forty lines hear the forty (39) and little else (6 of 24,
    from 1; "listen" 5 of 6, the other three ways 1 of 18). Never the wrong way, on either set."""

    NOT = ["tell me a joke", "can you change the subject", "my sister always tries to fix everything", "I just listened to a podcast about advice",
           "when I'm down I listen to music", "when I'm sad I like to be alone", "I don't want to be distracted right now",
           "when my mom is upset she wants me to just listen", "what should I do about dinner", "be honest with me, does this shirt look ok",
           "you always make me laugh", "I need a plan for the weekend", "he never listens to me", "when I'm sad I watch something funny",
           "if I'm stuck in traffic I put on a podcast or something else", "when I'm stressed I make jokes, it's a problem",
           "my therapist says I should let people hear me out", "I hate it when you try to cheer me up when I'm sad",
           "don't distract me when I'm upset, I need to feel it", "when work gets to me I go for a run", "I'd rather have pasta than something else tonight",
           "I always need coffee before I can listen to anyone", "when I'm low my dog stays with me", "no advice column is worth reading these days",
           "if I'm down for it, let's change the subject of the essay", "I don't need you to listen when I'm upset, I need you to help",
           "when things go wrong at work my boss wants answers", "when I'm low I don't want a distraction", "I never want jokes when I'm upset",
           "when I'm sad, don't try to cheer me up", "if I'm stressed I don't need you to be funny"]
    HONEST = {
        "listen": ["if I'm having a hard time, I don't need you to fix it, just be with me", "when I'm sad please don't jump to solutions",
                   "I mostly want someone to hear me when things get rough", "on bad days I need a listener, not a coach",
                   "when I'm upset, let me rant and don't try to solve it", "I'd rather you just sit with me when I'm hurting"],
        "distract": ["when I'm anxious, talking about something totally unrelated helps me", "if I've had a rough day, get me talking about anything but that",
                     "when I'm overwhelmed I need you to help me forget about it for a while", "any time I'm spiraling, just start telling me about something random",
                     "when I'm low, ask me about my garden or something instead", "I'd rather you take my thoughts somewhere else when I'm stressed"],
        "advice": ["when I'm struggling I want real advice, not sympathy", "if I'm stuck on something, tell me what you'd do",
                   "when things are bad I need a plan, so help me make one", "I prefer when you're blunt with me about my problems",
                   "when I'm upset, skip the comfort and tell me what to fix", "if I come to you with a problem, I want solutions"],
        "laugh": ["when I'm sad, being silly with me helps", "if I'm grumpy, crack a joke", "when I'm down I want you to be goofy with me",
                  "on rough days I just need a good laugh from you", "when I'm stressed, tease me a little, it helps", "any time I'm moping, say something ridiculous"],
    }
    HONEST_NOT = ["when I'm tired I just want to watch something else", "my brother needs me to listen when he's upset", "if you're down, I'm here for you",
                  "when I'm stressed I bake, it's my thing", "I told my boss to be straight with me", "we should change the subject of the meeting if it goes badly",
                  "when I was a kid my mom would make me laugh when I was sad", "I'm bad at jokes when I'm nervous",
                  "when it's a bad day at the shop, customers want answers", "please don't make me laugh, my ribs hurt",
                  "I don't want advice about the car, I want a mechanic", "when I'm sad I don't want jokes"]

    def test_the_forty_it_was_built_on(self):
        import sys as sys_
        sys_.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts")]
        import finetune_data
        got = [(style, _heard(asked)) for style, rows in finetune_data.AS_THEY_ASKED.items() for asked, _, _ in rows]
        self.assertEqual(len(got), 40)
        self.assertGreaterEqual(sum(1 for style, heard in got if heard == style), 39)
        self.assertEqual([pair for pair in got if pair[1] and pair[1] != pair[0]], [])

    def test_near_misses_teach_nothing(self):
        self.assertEqual([line for line in self.NOT if _heard(line)], [])

    def test_asking_for_more_than_listening_isnt_asking_to_be_listened_to(self):
        self.assertEqual(_heard("don't just listen when I'm upset, tell me what you think"), "advice")
        self.assertIsNone(_heard("I don't need you to listen when I'm upset, I need you to help"))

    def test_said_on_a_calm_day_it_counts_when_its_how_they_are(self):
        self.assertEqual(_heard("when I'm down, make me laugh"), "laugh")       # no hard moment needed: it's a standing wish
        self.assertIsNone(_heard("make me laugh"))                                # a slow afternoon, as before
        self.assertIsNone(_heard("tell me straight, is this shirt ugly"))

    def test_the_honest_number_on_lines_nothing_was_built_on(self):
        """Measured once, Nov 20, 2026: heard the right way 6 of 24 (before: 1), the wrong way 0; near misses heard 1 of 12
        (before: 1, the same line, by a rule that was already there)."""
        got = [(style, _heard(line)) for style, lines in self.HONEST.items() for line in lines]
        self.assertGreaterEqual(sum(1 for style, heard in got if heard == style), 6, got)
        self.assertGreaterEqual(sum(1 for style, heard in got if style == "listen" and heard == style), 5, got)
        self.assertEqual([pair for pair in got if pair[1] and pair[1] != pair[0]], [], "never the wrong way")
        self.assertLessEqual(sum(1 for line in self.HONEST_NOT if _heard(line)), 1)

    def test_its_used_on_a_hard_evening_later(self):
        import human_eval
        from luma.llm import prompts
        calls = []

        def planner(messages, context, allowed, *args, **kwargs):
            calls.append((list(messages), list(context)))
            return {"type": "reply", "text": f"Okay, {len(calls)}."}

        s = human_eval.Session(planner)
        try:
            s.say("if I'm down, change the subject for me")
            s.at({"day": 6, "time": "20:00"})
            s.new_conversation()
            start = len(calls)
            s.say("work was brutal today, I'm so stressed")
            told = "\n".join(prompts.build_plan_parts(c, [], "friend", None, "(the time)", compact=True)[1] for _, c in calls[start:])
            self.assertIn("take their mind off it", told)
            self.assertIn("change the subject for me", told)    # with their own words
        finally:
            s.close()
