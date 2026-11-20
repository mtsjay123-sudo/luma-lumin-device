"""The month test (scripts/month_eval.py): a made-up person lives 28 days with one Luma, and the same moments are then
said to a Luma that never met them. Here: a few dev lives, with a stand-in brain, reading what a brain is told."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import month_eval  # noqa: E402


class Lives(unittest.TestCase):
    def test_the_same_seed_is_the_same_person(self):
        a, b = month_eval.Life(3), month_eval.Life(3)
        self.assertEqual([(d, [t.get("say") for t in turns]) for d, _, turns in a.days()], [(d, [t.get("say") for t in turns]) for d, _, turns in b.days()])

    def test_dev_and_held_out_share_no_seed_and_no_line(self):
        self.assertFalse(set(month_eval.SEEDS["dev"]) & set(month_eval.SEEDS["heldout"]))
        said = lambda split: {t["say"] for seed in month_eval.SEEDS[split][:6] for _, _, turns in month_eval.Life(seed, split).days() for t in turns}  # noqa: E731
        self.assertFalse(said("dev") & said("heldout"))

    def test_every_way_to_be_met_is_lived(self):
        self.assertEqual({month_eval.Life(seed).style for seed in month_eval.SEEDS["dev"]}, set(month_eval.STYLES))


class AMonth(unittest.TestCase):
    """A guard on the half the code was built on. The held-out half is run by hand, numbers only."""

    @classmethod
    def setUpClass(cls):
        cls.result = month_eval.run("dev", lives=4, progress=lambda line: None)
        cls.table = month_eval.tally(cls.result)

    def test_a_month_in_luma_knows_what_a_stranger_cannot(self):
        for kind in ("comfort", "recall", "update", "people"):
            passed, of = self.table[kind]["month"]
            self.assertEqual(passed, of, kind)
            self.assertEqual(self.table[kind]["fresh"][0], 0, kind + ": a Luma that never met them can't know")

    def test_it_asks_how_it_went_and_leaves_a_closed_subject_alone(self):
        for kind in ("callback", "closed", "never"):
            passed, of = self.table[kind]["month"]
            self.assertEqual(passed, of, kind)

    def test_held_out_results_are_saved_without_a_line_of_what_was_said(self):
        summary = month_eval.summary({**self.result, "split": "heldout"})
        self.assertNotIn("Missed", summary)
        import json
        held = {**self.result, "split": "heldout"}
        saved = month_eval.to_save(held)
        text = json.dumps(saved)
        rows = [row for life in held["lives"] for row in life["rows"]]
        self.assertTrue(any(row.get("said") for row in rows))
        for row in rows:   # nothing they said and nothing Luma replied is in the file; only which checks passed
            for key in ("said", "reply", "fresh_reply"):
                if isinstance(row.get(key), str) and len(row[key]) > 12:
                    self.assertNotIn(row[key][:40], text)
        self.assertEqual(month_eval.tally(saved), month_eval.tally(held), "and the numbers are all still there")
        self.assertIs(month_eval.to_save(self.result), self.result)   # the lives the code was built on are saved whole


if __name__ == "__main__":
    unittest.main()


class AQuestionIsNeverAnOrderToSave(unittest.TestCase):
    """Month test on real brains, run 50: "where does my mom live" was answered "Saved. I'll remember that about the house."
    on every life by the 4B brain: the word "where" offered it the tool that saves a house note, and it took it."""

    @classmethod
    def setUpClass(cls):
        import human_eval
        cls.offered = []

        def planner(messages, context, allowed, *args, **kwargs):
            cls.offered.append(sorted(allowed or {}))
            return {"type": "reply", "text": "Okay."}

        cls.s = human_eval.Session(planner)

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def test_a_plain_question_is_offered_nothing_that_saves(self):
        saves = {"household.save", "memory.remember", "contacts.save"}
        for said in ("where does my mom live", "where does my brother live now", "where did I put the warranty for the dishwasher",
                     "do you remember where the spare key is", "what's the wifi password again?", "who's my landlord"):
            self.assertFalse(saves & set(self.s.agent.available_tools(said)), said)

    def test_asking_luma_to_keep_something_still_can(self):
        tools = self.s.agent.available_tools
        self.assertIn("household.save", tools("save that the water filter is under the sink"))
        self.assertIn("household.save", tools("the manual for the dryer is in the hall closet, save that"))
        self.assertIn("memory.remember", tools("remember that the wifi password is on the fridge"))
        self.assertIn("memory.remember", tools("can you remember my mom's birthday is June 3?"))

    def test_when_a_fact_states_it_luma_says_the_fact_and_no_tool_is_offered(self):
        """With or without a question mark (a voice has none). The same run: the small brain said "I don't know where your
        brother is right now" with the fact in front of it."""
        say = lambda text: (lambda out: out[0] if isinstance(out, tuple) else out.get("text"))(self.s.say(text))  # noqa: E731
        self.s.say("my mom lives in Tucson")
        self.s.say("my brother lives in Austin")
        self.s.say("my brother moved to Denver last week")
        del self.offered[:]
        self.assertIn("Tucson", say("where does my mom live"))
        self.assertIn("Tucson", say("where does my mom live?"))
        self.assertIn("Denver", say("where does my brother live now"))
        self.assertEqual([tools for tools in self.offered if tools], [])

    def test_what_no_fact_states_is_still_the_brains(self):
        say = lambda text: (lambda out: out[0] if isinstance(out, tuple) else out.get("text"))(self.s.say(text))  # noqa: E731
        for asked in ("where does my cousin live", "where does my mom want to go for dinner", "what does my boss want from me", "where is my life going"):
            self.assertEqual(say(asked), "Okay.", asked)


class SomeoneMoved(unittest.TestCase):
    """The month test's held-out lives say a move in words the rules weren't built on, and scored 0 of 20. Thirteen ways
    written fresh on Nov 20, 2026: 2 were read. These are the dev lines the rules were then built on (a guard, not a
    measure: the held-out lives are the measure)."""

    MOVED = ["my brother moved to Denver", "my brother relocated to Denver", "my brother's in Denver now", "my brother is living in Denver now",
             "my brother just got a place in Denver", "my brother transferred to Denver for work", "my brother left Austin for Denver",
             "my brother's back in Denver", "my brother lives in Denver now", "my brother ended up in Denver",
             "my brother took a job in Denver and moved out there", "my brother packed up and went to Denver for good",
             "fyi my brother isn't in Austin anymore, he's in Denver", "heads up, my brother moved to Denver"]
    NOT_A_MOVE = ["my brother is in a mood now", "my brother left work for lunch", "my brother ended up in the hospital", "my brother is back in school",
                  "my brother's in trouble again", "my brother got a place in the finals", "my brother is back in town",
                  "my brother went to Denver for the weekend", "my brother's birthday is June 3"]

    def test_each_way_of_saying_it_is_read_as_where_they_live(self):
        from luma.memory import facts
        for line in self.MOVED:
            reading = facts.read(line)
            self.assertTrue(reading and ("rel:brother", "home", "denver") in reading.slots, line)
        for line in self.NOT_A_MOVE:
            reading = facts.read(line)
            self.assertFalse(reading and any(kind == "home" for _, kind, _ in reading.slots), line)

    def ask(self, move):
        import human_eval
        shown = []

        def planner(messages, context, allowed, *args, **kwargs):
            shown.append(" | ".join(str(c.get("text")) for c in context if isinstance(c, dict)))
            return {"type": "reply", "text": "Okay."}

        s = human_eval.Session(planner)
        self.addCleanup(s.close)
        say = lambda text: (lambda out: out[0] if isinstance(out, tuple) else out.get("text"))(s.say(text))  # noqa: E731
        say("my brother lives in Austin")
        s.at({"day": 5, "time": "19:00"})
        s.new_conversation()
        say(move)
        s.at({"day": 9, "time": "19:00"})
        s.new_conversation()
        del shown[:]
        return say("where does my brother live now"), shown

    def test_asked_later_luma_says_the_new_city(self):
        for move in ("my brother relocated to Denver", "my brother's back in Denver", "fyi my brother isn't in Austin anymore, he's in Denver"):
            reply, _ = self.ask(move)
            self.assertIn("Denver", reply, move)
            self.assertFalse(reply.lower().startswith("fyi"), reply)

    NEWS = ["turns out my brother moved to Denver", "so apparently my brother moved to Denver", "guess what, my brother moved to Denver",
            "did I tell you my brother moved to Denver", "Marcus moved to Denver", "Marcus is in Denver now"]
    IN_TWO_BREATHS = ["talked to my brother today. he moved to Denver", "update on my brother: he's in Denver now", "my brother? oh he's out in Denver these days"]

    def test_news_about_someone_is_kept_however_it_starts(self):
        """Sixteen more ways, the same day: ten weren't kept at all (a line had to start with "I", "my", "he"...)."""
        from luma.agent.runtime import Agent
        from luma.memory import facts
        for line in self.NEWS + self.IN_TWO_BREATHS:
            self.assertTrue(Agent._telling_for_keeps(line), line)
            reading = facts.read(line)
            self.assertTrue(reading and any(kind == "home" and value == "denver" for _, kind, value in reading.slots), line)
        for line in ("what's the weather in Denver", "remind me to call my brother", "did my brother move to Denver?", "play something by Marcus",
                     "my brother and my sister had a fight. she moved to Denver"):
            reading = facts.read(line)
            self.assertFalse(reading and any(kind == "home" for _, kind, _ in reading.slots), line)
        for line in ("what's the weather in Denver", "remind me to call my brother", "did my brother move to Denver?", "play something by Marcus"):
            self.assertFalse(Agent._telling_for_keeps(line), line)

    def test_said_in_two_breaths_the_brain_puts_it_in_a_sentence(self):
        """ "Talked to your brother on Nov 15. he moved to Denver." is true and no way to say it: the brain is handed it."""
        for move in self.IN_TWO_BREATHS:
            reply, shown = self.ask(move)
            self.assertEqual(reply, "Okay.", move)
            self.assertTrue(any("Denver" in told for told in shown), move)

    def test_what_luma_cant_read_goes_to_the_brain_with_both_instead_of_the_old_city(self):
        """Something newer about the same person that no rule reads: saying "Your brother lives in Austin" flat would be worse
        than letting the brain weigh both, each with its date."""
        for move in ("my brother's whole life is in Denver these days",
                     "my brother says Austin got too expensive so he's out, living with our cousin up in Denver"):
            reply, shown = self.ask(move)
            self.assertNotIn("Austin", reply, move)   # the rule this test is for: never the old city, said flat
            if reply == "Okay.":   # no rule reads it: the brain weighs both
                self.assertTrue(any("Denver" in told and "Austin" in told for told in shown), move)
            else:                  # since Nov 20 the second of these is read by the signs of a move (people.plainly): Luma says the new city
                self.assertIn("Denver", reply, move)
        reply, shown = self.ask("my brother's whole life is in Denver these days")
        self.assertEqual(reply, "Okay.")   # this one still isn't read, and still goes to the brain with both


class AskedWhereTheyLiveNow(unittest.TestCase):
    """Twelve ways of asking, written fresh on Nov 20, 2026: 9 worked, and two got "I don't know your brother living these
    days yet." from Luma itself. A guard on the dev wording."""

    @classmethod
    def setUpClass(cls):
        import human_eval
        cls.shown = []

        def planner(messages, context, allowed, *args, **kwargs):
            cls.shown.append(" | ".join(str(c.get("text")) for c in context if isinstance(c, dict)))
            return {"type": "reply", "text": "Okay."}

        cls.s = human_eval.Session(planner)
        cls.s.say("my brother lives in Austin")
        cls.s.say("my keys are on the hook by the door")
        cls.s.at({"day": 5, "time": "19:00"})
        cls.s.new_conversation()
        cls.s.say("my brother moved to Denver")
        cls.day = 9

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def ask(self, question):
        type(self).day += 1
        self.s.at({"day": self.day, "time": "19:00"})
        self.s.new_conversation()
        del self.shown[:]
        out = self.s.say(question)
        return (out[0] if isinstance(out, tuple) else out.get("text")), " ".join(self.shown)

    def test_however_its_asked_the_new_city_is_said_or_handed_to_the_brain(self):
        for question in ("where does my brother live now", "where's my brother living these days", "where is my brother now", "what city is my brother in",
                         "where did my brother end up", "is my brother still in Austin", "where's my brother based now", "which state is my brother in now",
                         "remind me where my brother lives", "where's my brother at these days", "my brother's in which city again"):
            reply, told = self.ask(question)
            self.assertNotIn("I don't know", reply, question)
            self.assertTrue("Denver" in reply or (reply == "Okay." and "Denver" in told), f"{question}: {reply}")
            self.assertNotIn("lives in Austin.", reply, question)

    def test_things_are_still_things(self):
        reply, _ = self.ask("where are my keys")
        self.assertIn("hook by the door", reply)
        reply, _ = self.ask("where's my phone")
        self.assertIn("haven't told me", reply)


class AskedTheLongWayRound(unittest.TestCase):
    """"Do you remember where my brother moved": the brain was handed three memories with no day on any of them ("moved to
    Denver last week", weeks later; "lives in Austin"; the same again), and which one it said was a coin toss. Fresh
    wording, Nov 20, 2026."""

    @classmethod
    def setUpClass(cls):
        import human_eval
        cls.asked = []

        def planner(messages, context, allowed, *args, **kwargs):
            cls.asked.append(str(messages[-1].get("content") or ""))
            return {"type": "reply", "text": f"Okay, {len(cls.asked)}."}   # never the same reply twice

        cls.s = human_eval.Session(planner)
        cls.s.say("my brother Marcus lives in Austin")
        cls.s.say("my mom's birthday is June 3")
        cls.s.at({"day": 9, "time": "19:00"})
        cls.s.new_conversation()
        cls.s.say("my brother moved to Denver last week")
        cls.day = 19

    @classmethod
    def tearDownClass(cls):
        cls.s.close()

    def ask(self, question):
        type(self).day += 1
        self.s.at({"day": self.day, "time": "19:00"})
        self.s.new_conversation()
        del self.asked[:]
        return self.s.say(question)[0], "\n".join(self.asked)

    def test_a_saved_fact_that_states_it_is_said_by_luma_with_its_day(self):
        for question in ("do you remember where my brother moved", "do you remember where my brother lives", "did i tell you where my brother lives now",
                         "remind me where my brother lives", "Do you remember where my brother lives?"):
            reply, _ = self.ask(question)
            self.assertIn("Denver", reply, question)
            self.assertNotIn("Austin", reply, question)
            self.assertNotIn("last week", reply, question)   # it was "last week" three weeks ago
        reply, _ = self.ask("do you remember when my mom's birthday is")
        self.assertIn("June 3", reply)

    def test_a_different_question_is_left_to_the_brain(self):
        for question in ("do you remember where my brother wanted to move", "do you remember what my brother said about denver",
                         "do you remember where my brother thinks it is", "do you know what my problem is"):
            reply, _ = self.ask(question)
            self.assertTrue(reply.startswith("Okay, "), f"{question}: {reply}")

    def test_what_the_brain_is_handed_has_the_day_it_was_said_and_whether_its_still_true(self):
        reply, asked = self.ask("do you remember what my brother said about denver")
        self.assertIn("What your memory found", asked)
        self.assertIn('"said_on"', asked)
        self.assertNotIn("last week", asked)                    # made true for today
        self.assertIn("the week of", asked)
        found = self.s.agent._recall_tool("where my brother lives")
        gone = [m for m in found["memories"] if m.get("no_longer_true")]
        self.assertTrue(gone and all("Austin" in m["text"] for m in gone))
        prompt = self.s.agent._observation_prompt("where does he live", "memory.recall", found)
        self.assertIn('"no_longer_true": true', prompt)
        self.assertIn('"said_on"', prompt)

    def test_a_word_no_memory_has_is_no_gap_when_a_fact_answers(self):
        """ "remind me where Marcus ended up": the brain was handed the answer and then told "no memory mentions ended"."""
        import human_eval
        from luma.llm import prompts
        told = []

        def planner(messages, context, allowed, *args, **kwargs):
            told.append(prompts.build_plan_parts(list(context), [], "friend", None, "(the time)", compact=True)[1])
            return {"type": "reply", "text": f"Okay, {len(told)}."}

        s = human_eval.Session(planner)
        try:
            s.say("my brother Marcus lives in Austin")
            s.at({"day": 9, "time": "19:00"})
            s.new_conversation()
            s.say("my brother moved to Denver last week")
            for day, question, gap in ((20, "remind me where Marcus ended up", False), (21, "remind me where Marcus went to college", True)):
                s.at({"day": day, "time": "19:00"})
                s.new_conversation()
                del told[:]
                s.say(question)
                notes = "\n".join(told)
                if "What your memory found" in notes or not notes:
                    continue
                self.assertEqual("no memory mentions" in notes or "nothing saved mentions" in notes, gap, question + "\n" + notes[-600:])
                if not gap:
                    self.assertIn("Denver", notes)
        finally:
            s.close()

    def test_not_in_kids_mode(self):
        from unittest import mock
        agent = self.s.agent
        self.assertIsNotNone(agent._memory_answer("do you remember where my brother lives"))
        with mock.patch.object(type(agent), "mode", new_callable=mock.PropertyMock, return_value="kids"):
            self.assertIsNone(agent._memory_answer("do you remember where my brother lives"))


class AskedInAnyWords(unittest.TestCase):
    """The month test on real brains, on the lives Luma wasn't built on (run 55, Nov 20, 2026): handed the answer, the
    brains said it in 0 to 6 of 12. On 16 fresh ways of asking, Luma itself said the fact in 5. Now the shape of the
    question doesn't decide: a short question about them or theirs, that asks for the one thing a still-true fact states,
    is answered by Luma. Fresh wording; the held-out lives stay the measure."""

    ASKS = [("Priya", "what's my sister called again"), ("Priya", "what was my sister's name"), ("Priya", "remind me of my sister's name"),
            ("Priya", "my sister's name is what again"), ("Priya", "who's my sister"), ("Priya", "tell me my sister's name"),
            ("Priya", "do you know what my sister is called"), ("Priya", "what did I say my sister's name was"), ("Tampa", "which city is my mom in"),
            ("Tampa", "my mom lives where again"), ("Tampa", "what town does my mom live in"), ("Tampa", "where's my mom based"),
            ("Tampa", "where is it my mom lives"), ("Tampa", "tell me where my mom lives"), ("Tampa", "where did I say my mom lives"), ("Tampa", "what's my mom's city")]
    MORE = ["where did my mom live before Tampa", "where does my mom want to live", "who is my sister dating", "is my mom's name Priya", "when is my mom moving",
            "where should my mom live", "why does my mom live in Tampa", "how does my sister like Tampa", "what does my sister think of my mom's place",
            "what should I get my sister for her birthday", "where's my sister tonight", "who's my sister's best friend", "what's my mom doing in Tampa",
            "where is my mom's doctor", "what time is it where my mom lives", "which city is my mom visiting", "where did my mom grow up", "what's my sister up to",
            "how old is my sister"]

    def ask(self, question):
        import human_eval
        calls = []

        def planner(messages, context, allowed, *args, **kwargs):
            calls.append(1)
            return {"type": "reply", "text": f"Okay, {len(calls)}."}

        s = human_eval.Session(planner)
        try:
            s.say("my sister's name is Priya")
            s.say("my mom lives in Tampa")
            s.at({"day": 17, "time": "19:00"})
            s.new_conversation()
            return s.say(question)[0]
        finally:
            s.close()

    def test_the_fact_is_said_however_its_asked(self):
        said = [(want, question, self.ask(question)) for want, question in self.ASKS]
        self.assertGreaterEqual(sum(want in reply for want, _, reply in said), 15, [q for want, q, reply in said if want not in reply])
        self.assertEqual([q for _, q, reply in said if "I don't know" in reply], [])   # "I don't know your mom's city yet", with the city saved

    def test_a_question_that_asks_for_more_than_the_fact_is_the_brains(self):
        for question in self.MORE:
            reply = self.ask(question)
            self.assertTrue(reply.startswith("Okay, "), f"{question}: {reply}")


class MovedSaidByName(unittest.TestCase):
    """Twelve fresh ways of saying, by name, that a brother moved; then asked by relation and by name. Asked by name, the
    new city reached a small brain in 1 of 12: it is handed the first two memories, and "lives in Austin" with the
    brother's name filled both. The newer line now goes first."""

    MOVES = ["Marcus just took a job in Denver, he's moving next week", "Marcus is in Denver now", "so Marcus packed up and left for Denver",
             "Marcus got transferred to Denver", "Marcus and his wife bought a house in Denver", "Marcus finally made the move to Denver", "Marcus is a Denver guy now",
             "heard from Marcus, he's all settled in Denver", "Marcus's new place is in Denver", "Marcus swapped Austin for Denver",
             "it's official, Marcus lives in Denver", "Marcus headed out to Denver for good"]

    def test_the_new_city_is_said_or_is_in_what_a_small_brain_is_handed(self):
        import human_eval
        from luma.llm import prompts
        missed = []
        for move in self.MOVES:
            for question in ("where does my brother live now", "where's Marcus these days"):
                calls = []

                def planner(messages, context, allowed, *args, **kwargs):
                    calls.append((list(messages), list(context)))
                    return {"type": "reply", "text": f"Okay, {len(calls)}."}

                s = human_eval.Session(planner)
                try:
                    s.say("my brother's name is Marcus")
                    s.say("my brother lives in Austin")
                    s.at({"day": 10, "time": "19:00"})
                    s.new_conversation()
                    s.say(move)
                    s.at({"day": 26, "time": "19:00"})
                    s.new_conversation()
                    start = len(calls)
                    reply = s.say(question)[0]
                    told = "\n".join(prompts.build_plan_parts(c, [], "friend", None, "(the time)", compact=True)[1] + "\n" + m[-1]["content"] for m, c in calls[start:])
                    if not ("Denver" in reply or "Denver" in told) or ("Austin" in reply and "Denver" not in reply):
                        missed.append((move, question, reply))
                finally:
                    s.close()
        self.assertEqual(missed, [])

    def test_got_transferred_is_a_move(self):
        from luma.memory import facts
        for said, who in (("my brother got transferred to Denver", "rel:brother"), ("Marcus got transferred to Denver", "name:marcus"),
                          ("it's official, Marcus lives in Denver", "name:marcus"), ("Marcus was relocated to Denver", "name:marcus")):
            self.assertEqual(facts.read(said).slots, [(who, "home", "denver")], said)
