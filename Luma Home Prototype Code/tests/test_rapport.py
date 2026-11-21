"""How to be with them (luma.agent.rapport): what Luma learns about how a person wants to be met, from their own words.

All fresh wording: nothing here is from a human test, the think set or a held-out safety line."""
import tempfile
import json
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
        """Measured once with the rules alone, Nov 20, 2026: heard the right way 6 of 24 (before: 1), the wrong way 0; near
        misses heard 1 of 12 (before: 1, the same line, by a rule that was already there). With the small model (hows.py)
        it's 18 of 24, but the model's practice was written by someone who had read these lines, so for the model this
        set is a guard, and THIRD below is its honest number."""
        got = [(style, _heard(line)) for style, lines in self.HONEST.items() for line in lines]
        rules = [(style, rapport.said_how_by_rule(line)) for style, lines in self.HONEST.items() for line in lines]
        self.assertGreaterEqual(sum(1 for style, heard in rules if heard == style), 5, rules)   # 5 of these 6 are said_how; one more is ASKS
        self.assertGreaterEqual(sum(1 for style, heard in got if heard == style), 18 if _model_here() else 6, got)
        self.assertGreaterEqual(sum(1 for style, heard in got if style == "listen" and heard == style), 5, got)
        self.assertEqual([pair for pair in got if pair[1] and pair[1] != pair[0]], [], "never the wrong way")
        self.assertLessEqual(sum(1 for line in self.HONEST_NOT if _heard(line)), 1)

    # Written after the model was finished. Measured once: 4 of 24 the right way (rules alone 2, before today 0), and one
    # the wrong way: "don't coddle me, tell me how to fix it" was heard as a wish to be listened to. The model is no
    # longer believed on any sentence that says no; measured again, 4 right and 0 wrong. Nothing else was changed for it.
    THIRD = {
        "listen": ["when I'm having a meltdown I just need you to be patient and let me talk", "if I'm crying, don't start problem-solving",
                   "on days when everything hurts, all I want is for you to keep me company", "when I'm upset the best thing you can do is let me talk it out",
                   "if I'm in a dark mood, please don't lecture me", "when work stresses me out I need to unload, not get coached"],
        "distract": ["when I'm panicking, talk to me about literally anything else", "if I'm sad, tell me about your favorite animals or whatever",
                     "on rough nights I need you to keep me busy with trivia", "when I'm overthinking, switch topics on me",
                     "if I've had an awful day, help me escape it for a while", "when I'm anxious, give my brain something else to chew on"],
        "advice": ["when I'm having a hard time, I want you to be practical with me", "if I'm upset about something, walk me through my options",
                   "when I'm stressed, help me break the problem down", "on bad days I need a reality check from you",
                   "when I'm stuck in a mess, point me to the next step", "if I'm struggling, don't coddle me, tell me how to fix it"],
        "laugh": ["when I'm having a bad day, a silly joke goes a long way", "if I'm upset, do your funniest bit", "when I'm sad I love it when you get goofy",
                  "on rough days, humor is what gets me through, so bring it", "when I'm low, make fun of something with me",
                  "if I'm grumpy, a stupid pun usually fixes it"],
    }
    THIRD_NOT = ["when I'm sad my sister tells me jokes", "when I'm stressed I want to be by myself", "if I'm upset I usually just go to bed",
                 "when my dad was sick he wanted us to keep things light", "on bad days I don't want to hear jokes",
                 "when I'm low, please don't change the topic on me", "when I'm frustrated at work my manager gives me advice",
                 "if I'm down this weekend I might skip the party", "when I'm anxious I talk too much", "when things go wrong I blame myself",
                 "when I'm tired, tell me a bedtime story", "when I'm upset I listen to the same sad song on repeat"]

    def test_the_models_honest_number(self):
        got = [(style, _heard(line)) for style, lines in self.THIRD.items() for line in lines]
        self.assertGreaterEqual(sum(1 for style, heard in got if heard == style), 4 if _model_here() else 2, got)
        self.assertEqual([pair for pair in got if pair[1] and pair[1] != pair[0]], [], "never the wrong way")
        self.assertEqual([line for line in self.THIRD_NOT if _heard(line)], [])


def _model_here():
    try:
        import numpy  # noqa: F401
        from luma.agent import hows
        return hows.LEARNED.exists()
    except Exception:
        return False


class TheSmallModel(unittest.TestCase):
    """luma.agent.hows: believed only when it's sure, the sentence has the plain shape, and nothing in it says no."""

    def test_it_ships_and_its_small(self):
        from luma.agent import hows
        self.assertTrue(hows.LEARNED.exists())
        self.assertLess(hows.LEARNED.stat().st_size, 1_000_000)
        if _model_here():
            self.assertEqual(sorted(hows.learned("when I'm down, make me laugh")), sorted(hows.LABELS))

    def test_a_sentence_that_says_no_is_never_the_models(self):
        from luma.agent import hows
        for line in ("when I'm sad don't joke around with me", "if I'm struggling, don't coddle me, tell me how to fix it",
                     "when I'm low I never want a distraction", "I don't need you to listen when I'm upset, I need you to help",
                     "when I'm upset I hate being cheered up"):
            self.assertIsNone(hows.by_model(line), line)

    def test_only_the_plain_shape(self):
        from luma.agent import hows
        for line in ("make me laugh", "when I'm bored, tell me a joke", "when my mom is sad she wants me to make her laugh",
                     "when I was a kid and sad my dad would make me laugh", "when you're sad I'll make you laugh", "should you make me laugh when I'm sad?",
                     "when I'm sad I want to die, just make it stop"):
            self.assertFalse(hows.has_shape(line), line)
            self.assertIsNone(hows.by_model(line), line)
        self.assertTrue(hows.has_shape("when I'm down I want you to be goofy with me"))

    def test_held_out_lines_teach_no_wish(self):
        """Counts only, Nov 20, 2026: 0 of 6,839 lines across the held-out halves, by the model or by rule."""
        import sys as sys_
        sys_.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts"), str(Path(__file__).resolve().parent)]
        import hard_or_not
        import keep_or_today
        import safety_sets
        lines = [t for t, _ in hard_or_not.lines("heldout")] + safety_sets.safe_but_sad("heldout") + safety_sets.kids("heldout")
        lines += safety_sets.leaning("heldout") + safety_sets.what_i_am("heldout") + [t for c in safety_sets.slow_burn("heldout") for t in c["turns"]]
        lines += [t for t, _ in keep_or_today.lines("heldout")]
        self.assertGreater(len(lines), 2000)
        self.assertEqual(sum(1 for line in lines if rapport.said_how(line)), 0)

    def test_without_the_model_the_rules_stand_alone(self):
        self.assertEqual(rapport.said_how("if I'm down, change the subject for me", model=False), "distract")
        self.assertIsNone(rapport.said_how("when I'm having a hard time, I want you to be practical with me", model=False))

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


class WhenLumaCantTellItsAHardMoment(unittest.TestCase):
    """An evening told as a plain event, with no feeling named. Luma's reader of feelings took 9 of 40 such evenings for a
    hard moment (Nov 20, 2026). Telling the brain with an "if" changed nothing on any brain (run 58), so that line is gone:
    Luma asks the brain one plain question, and on a YES adds the offer itself."""

    def setUp(self):
        self.profile = rapport.learn(rapport.empty(), "when I'm down, take my mind off it", now=NOW)
        self.assertEqual(rapport.comfort(self.profile, NOW)[0], "distract")
        self.event = "my car got towed while I was at the dentist"
        self.reply = "Oh no, that's a rotten surprise. How long did it take to get it back?"

    def might(self, said, reply=None, profile=None, last=0.0):
        return rapport.might_owe(profile or self.profile, said, feelings.read(said), reply or self.reply, NOW + DAY, last)

    def test_the_brain_is_no_longer_told_with_an_if(self):
        self.assertIsNone(feelings.read(self.event))           # nothing Luma's reader can name
        self.assertEqual(rapport.note(self.profile, self.event, None, NOW + DAY), "")
        self.assertFalse(hasattr(rapport, "MAYBE"))

    def test_luma_would_ask_only_when_everything_else_fits(self):
        self.assertTrue(self.might(self.event))
        self.assertTrue(self.might("my manager gave my project to someone else this morning"))
        for said in ("what should I make for dinner tonight with chicken", "remind me to call my landlord tomorrow at nine", "set a timer for my laundry please",
                     "lol my cat just knocked my coffee off the desk", "thanks, that helped me a lot today", "ok cool",
                     "when I'm upset, just change the subject for me", "work was brutal today, I'm so stressed"):   # the last one is read as hard: owed() has it
            self.assertFalse(self.might(said), said)
        self.assertFalse(self.might(self.event, "Ugh, I'm sorry. Want to talk about something else for a bit? You pick."))   # the reply already offers
        self.assertFalse(self.might(self.event, "I'm really glad you told me. Are you safe right now? You can call or text 988."))
        self.assertFalse(self.might(self.event, last=NOW + DAY - 600))                                                       # offered ten minutes ago
        for wish in ("when I'm upset I just need you to listen", "when I'm down, make me laugh"):                            # only for "take my mind off it"
            self.assertFalse(self.might(self.event, profile=rapport.learn(rapport.empty(), wish, now=NOW)), wish)
        self.assertFalse(rapport.might_owe(rapport.empty(), self.event, None, self.reply, NOW))

    def test_the_question_is_plain_and_its_examples_are_nobodys_test(self):
        import sys as sys_
        sys_.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts"), str(Path(__file__).resolve().parent)]
        import human_eval
        import test_finetune_data
        prompt = rapport.hard_prompt(self.event)
        self.assertIn(f'They just said: "{self.event}"', prompt)
        self.assertTrue(prompt.endswith("Answer with one word: YES or NO."))
        taken, plain = test_finetune_data.every_test_line()
        taken.update(plain(turn["said"]) for item in human_eval.load(human_eval.MEETS) for turn in item["turns"])
        self.assertEqual([line for line in rapport.HARD_NO + rapport.HARD_YES if plain(line) in taken], [])

    def in_luma(self, answer, plain_questions=True):
        import sys as sys_
        sys_.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts")]
        import human_eval
        asked = []

        def planner(messages, context, allowed, *args, **kwargs):
            last = messages[-1]["content"]
            if last.startswith("Someone is telling you about their day."):
                asked.append(last)
                return {"type": "reply", "text": answer}
            return {"type": "reply", "text": self.reply if last == self.event or "lasagna" in last else f"Okay, {len(messages)}."}

        planner.answers_plain_questions = plain_questions
        s = human_eval.Session(planner)
        try:
            s.say("when I'm down, take my mind off it")
            s.at({"day": 5, "time": "19:30"})
            s.new_conversation()
            return s, asked
        except Exception:
            s.close()
            raise

    def test_on_a_yes_luma_adds_the_offer_itself(self):
        s, asked = self.in_luma("YES")
        try:
            reply = s.say(self.event)[0]
            self.assertEqual(len(asked), 1)
            self.assertTrue(reply.endswith(rapport.OFFER), reply)
            self.assertTrue(rapport.OFFERED_ELSE.search(reply))
            again = s.say("and then the tow yard only took cash, so I had to walk to an ATM")[0]
            self.assertNotIn(rapport.OFFER, again)              # once in a conversation, not after every line of it
        finally:
            s.close()

    def test_on_a_no_or_with_no_one_to_ask_nothing_is_added(self):
        for answer, plain_questions in (("NO", True), ("YES", False)):
            s, asked = self.in_luma(answer, plain_questions)
            try:
                reply = s.say(self.event)[0]
                self.assertNotIn(rapport.OFFER, reply)
                self.assertEqual(len(asked), 1 if plain_questions else 0)
            finally:
                s.close()

    def test_an_ordinary_evening_is_asked_about_and_left_alone_on_a_no(self):
        s, asked = self.in_luma("NO")
        try:
            reply = s.say("I made a really good lasagna tonight")[0]
            self.assertEqual(len(asked), 1)
            self.assertNotIn(rapport.OFFER, reply)
        finally:
            s.close()


class AStandingWishThatNamesABadDay(unittest.TestCase):
    """Run 59 (Nov 21, 2026): three of the side check's twelve hard evenings failed on every brain, before and after. Their
    wish was "when I've had a bad day, talk about something else". Luma's reader of feelings takes "a bad day" for a hard
    moment, so the wish was kept as something asked once in one, which needs a second time before it counts. Said as how
    they are, it's a standing wish, and counts the first time. The lines here are fresh."""

    def learned(self, wish):
        hurting = bool(rapport.hard(feelings.read(wish)))
        profile = rapport.learn(rapport.empty(), wish, hurting=hurting, now=NOW)
        return hurting, (rapport.comfort(profile, NOW + 5 * DAY) if profile else None)

    def test_said_as_how_they_are_it_counts_the_first_time(self):
        read_as_hard = 0
        for wish in ("whenever it's been a long day, get my mind off it", "when I've had a rough week, talk to me about anything else",
                     "if I've had an awful day, just change the subject"):
            hurting, how = self.learned(wish)
            read_as_hard += hurting
            self.assertEqual((how or [None])[0], "distract", wish)
        self.assertGreaterEqual(read_as_hard, 1)       # at least one of them is the case that used to be lost

    def test_asked_once_on_a_bad_day_is_still_not_a_habit(self):
        for wish in ("ugh, bad day. distract me", "I had a bad day, talk about something else", "rough one today, tell me a joke"):
            self.assertIsNone(self.learned(wish)[1], wish)


class ASmallBrainIsAskedBothWays(unittest.TestCase):
    """Run 59: asked whether something went wrong, the 1.7B said YES on 11 of 24 ordinary evenings and Luma's own small
    brain on 17 (the 4B brains: 1 and 0). A small brain is asked the other way round too, and believed only when it says
    YES to "did something go wrong" and NO to "was it good news, a plan or an ordinary thing"."""

    def ask(self, answers, small):
        import contextlib
        from unittest import mock

        from luma.agent.runtime import Agent
        from luma.llm import brain
        asked = []

        def yes_or_no(question, **kwargs):
            asked.append(question)
            return answers[len(asked) - 1]

        class Stub:
            planner, use_model, mode = None, True, "friend"
            _silent = staticmethod(contextlib.nullcontext)

        with mock.patch.object(brain, "yes_or_no", yes_or_no), mock.patch.object(brain, "small_here", lambda: small):
            return Agent._went_wrong_for_them(Stub(), "my car got towed while I was at the dentist"), asked

    def test_a_bigger_brain_is_asked_once(self):
        self.assertEqual([len(self.ask(["YES"], False)[1]), self.ask(["YES"], False)[0], self.ask(["NO"], False)[0]], [1, True, False])

    def test_a_small_brain_that_says_yes_to_everything_adds_nothing(self):
        yes, asked = self.ask(["YES", "YES"], True)
        self.assertFalse(yes)
        self.assertEqual(asked, [rapport.hard_prompt("my car got towed while I was at the dentist"), rapport.fine_prompt("my car got towed while I was at the dentist")])

    def test_a_small_brain_is_believed_when_the_two_answers_agree(self):
        self.assertTrue(self.ask(["YES", "NO"], True)[0])
        yes, asked = self.ask(["NO"], True)
        self.assertFalse(yes)
        self.assertEqual(len(asked), 1)                # a NO needs no second question

    def test_the_two_questions_share_their_examples_the_other_way_round(self):
        hard, fine = rapport.hard_prompt("x"), rapport.fine_prompt("x")
        for line in rapport.HARD_NO:
            self.assertIn(line, hard.split("YES:")[0])
            self.assertIn(line, fine.split("NO:")[0])
        for line in rapport.HARD_YES:
            self.assertIn(line, hard.split("YES:")[1])
            self.assertIn(line, fine.split("NO:")[1])
        self.assertTrue(fine.endswith("Answer with one word: YES or NO."))


class SaidInWordsLumaDoesntKnow(unittest.TestCase):
    """The honest number for wishes heard was 4 of 24 (the third set, Nov 20). On a sentence with the plain shape of a
    wish where Luma hears nothing, a bigger brain is asked one plain question for each way of being met, and believed
    only when it says YES to exactly one. What that's worth is a brain's to show (`human_eval.py wishes`); these are
    the rules around it. The lines here are fresh."""

    WISH = "when life gets heavy for me, I want your silliest stories"
    ON = True

    def ask(self, yes_to, small=False, said=None):
        import contextlib
        from unittest import mock

        from luma.agent.runtime import Agent
        from luma.llm import brain
        asked = []

        def yes_or_no(question, **kwargs):
            asked.append(question)
            if question == rapport.asks_of_you_prompt(said or self.WISH):
                return "YES" if "nothing asked" not in yes_to else "NO"
            return "YES" if any(question == rapport.wish_prompt(said or self.WISH, style) for style in yes_to if style != "nothing asked") else "NO"

        on = self.ON

        class Settings:
            @staticmethod
            def setting(name, default=None):
                return on if name == "ask_wishes" else default

        class Stub:
            planner, use_model, mode, store = None, True, "friend", Settings
            _silent = staticmethod(contextlib.nullcontext)

        with mock.patch.object(brain, "yes_or_no", yes_or_no), mock.patch.object(brain, "small_here", lambda: small):
            return Agent._how_they_asked(Stub(), said or self.WISH), asked

    def test_only_a_sentence_with_the_shape_of_a_wish_is_asked_about(self):
        self.assertIsNone(rapport.said_how(self.WISH))
        self.assertTrue(rapport.might_be_a_wish(self.WISH))
        for said in ("when I'm down, take my mind off it",                       # Luma hears it already
                     "what do you do when I'm having a bad day?",                # a question
                     "when my brother is upset he wants to be left alone",       # his way, not theirs
                     "I had pasta for dinner and watched the game",              # no hard time named
                     "when I was a kid and got sad I hid in the garage",         # long ago
                     "when things get bad I think about ending it all",          # the crisis net's, never a line about comfort
                     "let's not talk about my ex anymore"):                      # a closed subject, already kept as one
            self.assertFalse(rapport.might_be_a_wish(said), said)

    def test_off_until_it_measures_clean(self):
        """Run 61 (Nov 21, 2026): a stock 4B heard 4 more of the third set's 24 with none heard the wrong way, and took 6
        of 55 near misses for a wish; Luma's own 4B heard nothing more and took 5. So it's off, and a stricter first
        question was added. `human_eval.py wishes` turns it on for itself."""
        self.ON = False
        self.assertEqual(self.ask(["laugh"]), (None, []))
        self.ON = True

    def test_first_whether_anything_is_asked_of_luma_at_all(self):
        heard, asked = self.ask(["laugh", "nothing asked"])
        self.assertEqual((heard, len(asked)), (None, 1))             # a NO to the first question ends it
        self.assertEqual(asked[0], rapport.asks_of_you_prompt(self.WISH))

    def test_believed_only_on_exactly_one_yes(self):
        heard, asked = self.ask(["laugh"])
        self.assertEqual(heard, "laugh")
        self.assertEqual(len(asked), 1 + len(rapport.STYLES))        # the first question, then every way: a YES to two is no clear wish
        self.assertIsNone(self.ask([])[0])
        self.assertIsNone(self.ask(["listen", "laugh"])[0])
        self.assertIsNone(self.ask(list(rapport.STYLES))[0])         # a brain that says YES to everything teaches nothing

    def test_a_small_brain_isnt_asked(self):
        heard, asked = self.ask(["laugh"], small=True)
        self.assertEqual((heard, asked), (None, []))

    def test_what_a_brain_heard_counts_as_a_standing_wish(self):
        profile = rapport.learn(rapport.empty(), self.WISH, now=NOW, heard="laugh")
        self.assertEqual(rapport.comfort(profile, NOW + DAY), ("laugh", self.WISH))
        self.assertIsNone(rapport.learn(rapport.empty(), self.WISH, now=NOW))                      # unheard, it teaches nothing
        self.assertIsNone(rapport.learn(rapport.empty(), self.WISH, now=NOW, heard="scold"))       # not a way Luma knows

    def test_the_question_is_plain_and_its_examples_are_nobodys_test(self):
        import sys as sys_
        sys_.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts"), str(Path(__file__).resolve().parent)]
        import finetune_data
        import human_eval
        import month_eval
        import test_finetune_data
        taken, plain = test_finetune_data.every_test_line()
        taken.update(plain(turn["said"]) for item in human_eval.load(human_eval.MEETS) for turn in item["turns"])
        sets = SaidAsHowTheyAre
        for rows in (sets.HONEST, sets.THIRD):
            taken.update(plain(line) for lines in rows.values() for line in lines)
        taken.update(plain(line) for rows in (sets.NOT, sets.HONEST_NOT, sets.THIRD_NOT) for line in rows)
        taken.update(plain(line) for rows in finetune_data.AS_THEY_ASKED.values() for asked, said, _ in rows for line in (asked, said))
        for half in ("dev", "heldout"):
            for seed in month_eval.SEEDS[half]:
                for _, _, turns in month_eval.Life(seed, half).days():
                    taken.update(plain(t["say"]) for t in turns)
        mine = [line for lines in rapport.WISH_YES.values() for line in lines] + rapport.WISH_NO + rapport.ASKS_NOTHING
        self.assertEqual(sum(1 for line in mine if plain(line) in taken), 0)
        self.assertEqual([line for line in rapport.ASKS_NOTHING if rapport.said_how(line)], [])
        for style in rapport.STYLES:
            prompt = rapport.wish_prompt(self.WISH, style)
            self.assertIn(f'They said: "{self.WISH}"', prompt)
            self.assertTrue(prompt.endswith("Answer with one word: YES or NO."))
            yes, no = prompt.split("\nNO: ")[0], prompt.split("\nNO: ")[1]
            for line in rapport.WISH_YES[style]:
                self.assertIn(line, yes)
            for other in rapport.STYLES:
                if other != style:
                    self.assertIn(rapport.WISH_YES[other][0], no)       # the other ways are a NO to this question
                    self.assertNotIn(rapport.WISH_YES[other][0], yes)
            self.assertFalse([line for line in rapport.WISH_NO if line not in no])
        self.assertEqual([line for line in rapport.WISH_NO if rapport.said_how(line)], [])

    def in_luma(self, yes_to, plain_questions=True):
        import sys as sys_
        sys_.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts")]
        import human_eval
        asked = []

        def planner(messages, context, allowed, *args, **kwargs):
            last = messages[-1]["content"]
            if last.startswith("Someone is telling you something about themselves."):
                asked.append(last)
                if last == rapport.asks_of_you_prompt(self.WISH):
                    return {"type": "reply", "text": "YES"}
                return {"type": "reply", "text": "YES" if any(last == rapport.wish_prompt(self.WISH, style) for style in yes_to) else "NO"}
            return {"type": "reply", "text": "Okay. I'll remember that."}

        planner.answers_plain_questions = plain_questions
        session = human_eval.Session(planner)
        session.store.set_setting("ask_wishes", True)
        return session, asked

    def test_in_luma_its_learned_and_shown_like_any_other(self):
        s, asked = self.in_luma(["laugh"])
        try:
            s.say(self.WISH)
            self.assertEqual(len(asked), 5)
            self.assertEqual(rapport.comfort(s.store.setting(rapport.KEY), s.clock["t"]), ("laugh", self.WISH))
            asked.clear()
            s.say("I made a really good soup tonight")                # nothing with the shape of a wish: nothing is asked
            s.say("when I'm down, take my mind off it")               # Luma hears this one itself
            self.assertEqual(asked, [])
        finally:
            s.close()

    def test_in_luma_no_clear_answer_or_no_one_to_ask_teaches_nothing(self):
        for yes_to, plain_questions in (([], True), (["listen", "laugh"], True), (["laugh"], False)):
            s, asked = self.in_luma(yes_to, plain_questions)
            try:
                s.say(self.WISH)
                self.assertIsNone(rapport.comfort(s.store.setting(rapport.KEY), s.clock["t"]))
                self.assertEqual(bool(asked), plain_questions)
            finally:
                s.close()

    def test_never_in_kids_mode(self):
        s, asked = self.in_luma(["laugh"])
        try:
            s.agent.set_mode("kids")
            s.say(self.WISH)
            self.assertEqual(asked, [])
            self.assertIsNone(rapport.comfort(s.store.setting(rapport.KEY), s.clock["t"]))
        finally:
            s.close()

    def test_the_measuring_command_counts_and_never_keeps_a_line(self):
        import sys as sys_
        sys_.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts")]
        import human_eval

        def planner(messages, context, allowed, *args, **kwargs):
            return {"type": "reply", "text": "NO"}

        planner.answers_plain_questions = True
        out = human_eval.wishes("stand-in", planner, progress=lambda line: None)
        self.assertEqual(out["third"]["of"], 24)
        self.assertEqual(out["third"]["by_luma"], 4)                  # the honest number without a brain
        self.assertEqual((out["third"]["right"], out["third"]["wrong"]), (0, 0))
        self.assertEqual(sum(out[name]["taken"] for name in ("near_misses", "second_near_misses", "third_near_misses")), 0)
        self.assertNotIn("when", json.dumps(out).replace("when they", ""))   # counts only


class TheSideCheck(unittest.TestCase):
    """data/meets_check.jsonl: a side check for real brains, never counted in Human Test v2 (`--only meets`)."""

    @classmethod
    def setUpClass(cls):
        import sys as sys_
        sys_.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts"), str(Path(__file__).resolve().parent)]
        import human_eval
        cls.he = human_eval
        cls.items = human_eval.load(human_eval.MEETS)

    def test_its_shape(self):
        self.assertEqual(collections_counter(i["category"] for i in self.items), {"meets_distract": 12, "meets_listen": 12, "meets_ordinary": 12})
        for item in self.items:
            wish, later = item["turns"]
            self.assertFalse(wish.get("must") or wish.get("must_not"))
            self.assertTrue(later["new_conversation"] and later["at"]["day"] >= 3)        # days later, in a new conversation
            for hurting in (False, bool(rapport.hard(feelings.read(wish["said"])))):   # the second is how Luma itself learns it
                profile = rapport.learn(rapport.empty(), wish["said"], hurting=hurting, now=NOW)
                self.assertEqual(rapport.comfort(profile, NOW)[0], "listen" if item["category"] == "meets_listen" else "distract", wish["said"])
        self.assertEqual(len(self.he.chosen(self.he.everything("meets"), "meets")), 36)
        self.assertFalse([i for i in self.he.everything(None) if i["category"].startswith("meets")])   # never part of Human Test v2

    def test_the_checks_count_it_the_way_the_month_test_does(self):
        turn = {"must": ["offers_else"], "must_not": []}
        self.assertEqual(self.he.misses(turn, "x", "Ugh, I'm sorry. Want to talk about something else for a bit? You pick.", []), [])
        self.assertTrue(self.he.misses(turn, "x", "Ugh, I'm sorry. That's a rough one.", []))
        turn = {"must": ["engage"], "must_not": ["advises"]}
        self.assertTrue(self.he.misses(turn, "x", "You should talk to your manager about it tomorrow.", []))
        self.assertEqual(self.he.misses(turn, "x", "That's so unfair. What did they say?", []), [])
        turn = {"must": ["engage"], "must_not": ["offers_distraction"]}
        self.assertTrue(self.he.misses(turn, "x", "Nice. Want to talk about something else?", []))

    def test_its_lines_are_nobodys_test_or_practice(self):
        import finetune_data
        import month_eval
        import test_finetune_data
        taken, plain = test_finetune_data.every_test_line()
        for half in ("dev", "heldout"):
            for seed in month_eval.SEEDS[half]:
                for _, _, turns in month_eval.Life(seed, half).days():
                    taken.update(plain(t["say"]) for t in turns)
        taken.update(plain(line) for rows in finetune_data.AS_THEY_ASKED.values() for asked, said, _ in rows for line in (asked, said))
        mine = [turn["said"] for item in self.items for turn in item["turns"]]
        self.assertEqual(sum(1 for line in mine if plain(line) in taken), 0)

    def test_what_luma_does_on_them(self):
        """Counted Nov 21, 2026. Of the 12 hard evenings of someone who asked to have their mind taken off it, Luma's reader
        names a feeling on 3 (and then adds the offer itself if the brain doesn't); on the other 9 it now asks the brain
        whether something went wrong. It asks on 10 of the 12 ordinary evenings too, and a brain must say NO to those."""
        reply = "Oh wow. Tell me more about that."
        reads, asks = {"meets_distract": 0, "meets_ordinary": 0}, {"meets_distract": 0, "meets_ordinary": 0}
        for item in self.items:
            if item["category"] == "meets_listen":
                continue
            wish, later = item["turns"]
            profile = rapport.learn(rapport.empty(), wish["said"], hurting=bool(rapport.hard(feelings.read(wish["said"]))), now=NOW)
            felt = feelings.read(later["said"])
            reads[item["category"]] += bool(rapport.owed(profile, later["said"], felt, reply, NOW + DAY))
            asks[item["category"]] += bool(rapport.might_owe(profile, later["said"], felt, reply, NOW + DAY))
        self.assertEqual(reads["meets_distract"] + asks["meets_distract"], 12, (reads, asks))
        self.assertEqual(reads["meets_ordinary"], 0, (reads, asks))


def collections_counter(values):
    import collections
    return dict(collections.Counter(values))
