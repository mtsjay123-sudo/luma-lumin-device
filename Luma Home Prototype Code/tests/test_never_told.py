"""Luma says "never told" only when it never was (Nov 21, 2026).

Told "my brother's a welder" and asked "what does my brother do", the memory look-up answered "nobody saved as my
brother": no rule reads that sentence as a fact, so no fact named a brother, and the look-up took that for nobody. The
brain was handed the memory and, beside it, "say you haven't been told". The same for "mom's birthday is the 9th of
April" / "when was my mom born", and for a thing kept under another word ("I ride my bike to work" / "how do I get to
my job").

BUILT_ON: 30 facts and questions in my own words, written without reading the memory test's templates. Found 17 -> 27.
SECOND: 30 more, written after the fixes and measured once: found 14 -> 26. Every miss, in both, was "never told".
The memory test's own numbers didn't move on either half: its misses are a different kind (the right memory isn't in
the first five)."""
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts")]

CHATTER = ["I had pasta for dinner", "the bus was late again", "my coworker brought donuts", "it rained all weekend", "I watched a documentary about octopuses",
           "my phone battery is dying fast lately", "I need new running shoes", "the neighbors were loud last night"]


def asked_back(said, ask):
    """(was it found, the memories handed over) for one thing said a month ago and asked about now."""
    from luma.memory.store import Store
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "s.db", Path(folder) / "k")
        try:
            now = time.time()
            rows = [{"text": said, "source": "said", "created": now - 86400 * 30, "category": "notes"}] if said else []
            rows += [{"text": line, "source": "said", "created": now - 86400 * (40 + i), "category": "notes"} for i, line in enumerate(CHATTER)]
            store.put_many("memory", rows)
            got = store.search(ask, limit=5, now=now)
            return got["known"], " ".join(m.get("text", "") for m in got["memories"]).lower()
        finally:
            store.close()


class NeverToldOnlyWhenItNeverWas(unittest.TestCase):
    BUILT_ON = [
        ("my sister Noor lives in Leeds", "what city is Noor in", "leeds"), ("my brother's a welder", "what does my brother do", "welder"),
        ("mom's birthday is the 9th of April", "when was my mom born", "april"), ("I can't have gluten", "what can't I eat", "gluten"),
        ("our dog is called Biscuit", "what's the dog's name", "biscuit"), ("I work nights at the bakery on 5th", "where's my job", "bakery"),
        ("my best friend Tariq just had a baby girl", "did Tariq have a boy or a girl", "girl"), ("my favorite tea is oolong", "which tea do I like best", "oolong"),
        ("I drive a blue Corolla", "what car do I have", "corolla"), ("my landlord's name is Mr. Okafor", "who's my landlord", "okafor"),
        ("I take my blood pressure pill at 8 every morning", "when do I take my pill", "8"), ("my dad was a bus driver for thirty years", "what did my dad do for work", "bus"),
        ("my daughter Elif is in third grade", "what grade is Elif in", "third"), ("I grew up in a town called Marfa", "where am I from", "marfa"),
        ("my wife and I got married in 2014", "what year did I get married", "2014"), ("my doctor is Dr. Lindqvist", "what's my doctor's name", "lindqvist"),
        ("I'm lactose intolerant", "is there anything I shouldn't drink", "lactose"), ("my son plays goalie for his school team", "what position does my son play", "goalie"),
        ("my cousin Ines runs a flower shop", "what's Ines's business", "flower"), ("I usually go to bed around eleven", "what time do I go to sleep", "eleven"),
        ("my neighbor Walt feeds my cat when I'm away", "who looks after my cat when I travel", "walt"), ("the spare key is under the blue pot", "where did I hide the spare key", "pot"),
        ("my anniversary is October 12", "when's my anniversary", "october"), ("my mom makes the best dumplings", "what does my mom cook that I love", "dumplings"),
        ("I broke my wrist skiing last winter", "how did I hurt my wrist", "skiing"), ("my grandmother came over from Lebanon in the sixties", "where is my grandmother from", "lebanon"),
        ("I'm training for a half marathon in May", "what race am I training for", "marathon"), ("my brother Sami moved to Calgary for work", "where does Sami live", "calgary"),
        ("I'm a nurse at the children's hospital", "what's my job", "nurse"), ("my partner is vegetarian", "does my partner eat meat", "vegetarian")]
    SECOND = [
        ("my aunt Colleen teaches piano", "what does my aunt do", "piano"), ("my roommate is from Portugal", "where's my roommate from", "portugal"),
        ("grandpa served in the navy", "what branch was my grandpa in", "navy"), ("my sister-in-law is a pharmacist", "what's my sister-in-law's job", "pharmacist"),
        ("my boss's daughter is getting married in June", "when is my boss's daughter's wedding", "june"), ("my nephew just started kindergarten", "what grade is my nephew in", "kindergarten"),
        ("my girlfriend hates cilantro", "what food does my girlfriend hate", "cilantro"), ("my uncle fixes motorcycles", "what does my uncle work on", "motorcycles"),
        ("I rent a studio above a laundromat", "where do I live", "laundromat"), ("I've been a line cook for six years", "what do I do for a living", "cook"),
        ("I ride my bike to work", "how do I get to my job", "bike"), ("I'm studying for the bar exam", "what test am I studying for", "bar"),
        ("my stepmom's name is Lorraine", "what's my stepmom called", "lorraine"), ("my mother-in-law lives with us", "who lives in my house", "mother-in-law"),
        ("my kid's school starts at 8:15", "what time does school start", "8:15"), ("I usually have oatmeal in the morning", "what do I eat for breakfast", "oatmeal"),
        ("my therapist is on Thursdays", "what day do I see my therapist", "thursday"), ("my friend Dev owes me forty bucks", "how much does Dev owe me", "forty"),
        ("our wedding was in Santa Barbara", "where did I get married", "santa barbara"), ("I had my appendix out when I was twelve", "have I ever had surgery", "appendix"),
        ("my coworker Bea is on maternity leave", "why is Bea out", "maternity"), ("my dentist is Dr. Abara", "who's my dentist", "abara"),
        ("my cat Olive is seventeen years old", "how old is my cat", "seventeen"), ("I moved here from Manila in 2019", "what year did I move here", "2019"),
        ("my brother and I don't talk anymore", "how are things with my brother", "talk"), ("my mom had a stroke two years ago", "what happened to my mom's health", "stroke"),
        ("I quit smoking in March", "when did I stop smoking", "march"), ("my car is in the shop until Friday", "when do I get my car back", "friday"),
        ("my daughter wants to be a vet", "what does my daughter want to be", "vet"), ("I play bass in a cover band", "what instrument do I play", "bass")]

    @staticmethod
    def found(rows):
        return sum(1 for said, ask, gold in rows if (lambda known, texts: known and gold in texts)(*asked_back(said, ask)))

    def test_the_lines_it_was_built_on(self):
        self.assertGreaterEqual(self.found(self.BUILT_ON), 27)

    def test_the_honest_number(self):
        """Measured once: 14 -> 26 of 30."""
        self.assertGreaterEqual(self.found(self.SECOND), 26)

    def test_what_was_never_said_is_still_never_told(self):
        for ask in ("what does my uncle do", "what's my job", "where does my cousin live", "what's my sister's name", "what car do I have", "when's my anniversary",
                    "who's my dentist", "what instrument do I play"):
            known, texts = asked_back(None, ask)
            self.assertFalse(known, ask)
            self.assertEqual(texts, "", ask)

    def test_someone_spoken_of_is_never_handed_over_as_the_owner(self):
        known, texts = asked_back("I work at the cannery", "what does my brother do")
        self.assertFalse(known)   # nothing mentions a brother: the owner's own job is not his
        known, texts = asked_back("my brother's a welder", "what do I do for work")
        self.assertNotIn("welder", texts if known else "")

    def test_the_brain_isnt_told_to_say_it_wasnt_told_beside_the_memory(self):
        import human_eval
        from luma.llm import prompts
        calls = []

        def planner(messages, context, allowed, *args, **kwargs):
            calls.append(list(context))
            return {"type": "reply", "text": f"Okay, {len(calls)}."}

        s = human_eval.Session(planner)
        try:
            s.say("my brother's a welder")
            s.at({"day": 12, "time": "19:00"})
            s.new_conversation()
            start = len(calls)
            s.say("what does my brother do")
            told = " ".join(prompts.build_plan_parts(context, [], "friend", None, "(the time)", compact=True)[1] for context in calls[start:])
        finally:
            s.close()
        self.assertIn("welder", told)
        self.assertNotIn("nobody saved as my brother", told)
        self.assertNotIn("say you haven't been told", told)


class WhatTheySaidAboutThemselves(unittest.TestCase):
    """Through a real conversation. Told "I'm a nurse at the children's hospital" and asked "what's my job" twelve days
    later, Luma itself said "I don't know your job yet. Tell me and I'll remember it." A sentence with the plain shape of
    saying their job, their home or where they're from is marked when it's kept (facts.says_own) and found when they ask.

    BUILT_ON, 10: reaches the brain 3 -> 7, and Luma saying it doesn't know 1 -> 0.
    SECOND, 12, written afterwards and measured once: reaches the brain 1 -> 7, Luma saying it doesn't know 3 -> 1."""

    BUILT_ON = [("I rent a studio above a laundromat", "where do I live", "laundromat"), ("I've been a line cook for six years", "what do I do for a living", "cook"),
                ("I usually have oatmeal in the morning", "what do I eat for breakfast", "oatmeal"), ("I had my appendix out when I was twelve", "have I ever had surgery", "appendix"),
                ("I'm a nurse at the children's hospital", "what's my job", "nurse"), ("I grew up in a town called Marfa", "where am I from", "marfa"),
                ("I work nights at the bakery on 5th", "where's my job", "bakery"), ("I drive a blue Corolla", "what car do I have", "corolla"),
                ("I usually go to bed around eleven", "what time do I go to sleep", "eleven"), ("I'm lactose intolerant", "is there anything I shouldn't drink", "lactose")]
    SECOND = [("I'm a dental hygienist", "what do I do for work", "hygienist"), ("I've been a bus driver since 2015", "what's my job again", "bus driver"),
              ("I share a house with three roommates in Echo Park", "where's my place", "echo park"), ("I was raised in a tiny town outside Fresno", "where did I grow up", "fresno"),
              ("I'm an electrician for the city", "who do I work for", "city"), ("I stay with my aunt in Queens", "where am I living", "queens"),
              ("I come from a big family in Lagos", "where am I originally from", "lagos"), ("I teach at the community college", "where do I work", "community college"),
              ("I'm a stay-at-home dad", "what do I do all day", "dad"), ("I bought a condo near the lake", "where's my home", "lake"),
              ("I work as a paralegal downtown", "what's my line of work", "paralegal"), ("I moved here from Ohio", "where was I before I moved here", "ohio")]

    @staticmethod
    def counted(rows):
        """(how many reach the brain or are said right by Luma, how many times Luma itself says it doesn't know)."""
        import human_eval
        from luma.llm import prompts
        has = wrong = 0
        for said, ask, gold in rows:
            calls = []

            def planner(messages, context, allowed, *args, **kwargs):
                calls.append(list(context))
                return {"type": "reply", "text": "(brain)"}

            s = human_eval.Session(planner)
            try:
                s.say(said)
                s.at({"day": 12, "time": "19:00"})
                s.new_conversation()
                start = len(calls)
                reply = s.say(ask)[0]
                told = " ".join(prompts.build_plan_parts(context, [], "friend", None, "(the time)", compact=True)[1] for context in calls[start:])
            finally:
                s.close()
            from luma.agent import human
            by_luma = not ("glitched" in reply or reply == "(brain)" or reply in human.OWN)   # Luma's line for a brain that failed isn't Luma answering
            has += gold in (reply if by_luma else told).lower()
            wrong += by_luma and gold not in reply.lower()
        return has, wrong

    def test_the_lines_it_was_built_on(self):
        has, wrong = self.counted(self.BUILT_ON)
        self.assertGreaterEqual(has, 7)
        self.assertEqual(wrong, 0)

    def test_the_honest_number(self):
        has, wrong = self.counted(self.SECOND)
        self.assertGreaterEqual(has, 7)
        self.assertLessEqual(wrong, 1)

    def test_the_plain_shape_and_what_only_looks_like_it(self):
        from luma.memory import facts
        for said, what in (("I'm a nurse at the children's hospital", "work"), ("I've been a line cook for six years", "work"), ("I'm a teacher", "work"),
                           ("I work nights at the bakery on 5th", "work"), ("I rent a studio above a laundromat", "home"), ("I stay with my aunt in Queens", "home"),
                           ("I grew up in a town called Marfa", "from"), ("I moved here from Ohio", "from")):
            self.assertEqual(facts.says_own(said), {what}, said)
        for said in ("I'm a mess today", "I'm a big fan of yours", "I'm a little tired", "I am a failure", "I live for the weekend", "I'm a night owl", "I'm an only child",
                     "I run every morning", "I own that mistake", "I was born tired", "I'm a burden to everyone", "am I a bad person?", "I stay up too late"):
            self.assertEqual(facts.says_own(said), set(), said)

    def test_with_nothing_said_luma_still_says_it_doesnt_know(self):
        import human_eval

        def planner(messages, context, allowed, *args, **kwargs):
            return {"type": "reply", "text": "(brain)"}

        s = human_eval.Session(planner)
        try:
            self.assertEqual(s.say("what's my job")[0], "I don't know your job yet. Tell me and I'll remember it.")
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
