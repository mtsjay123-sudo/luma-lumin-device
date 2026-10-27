"""Requests wrapped in slang still get done right: the slang isn't part of the reminder, the text goes to the
right person without a "that", the reason can come before "remind me", and a new request after Luma asks a
follow-up question isn't stuffed into the old one."""
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store


class SlangTalkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.agent = Agent(store=self.store, use_model=False)
        self.agent.contacts.save({"name": "Mom", "phone": "+19195550111", "aliases": "my mom, mom"})
        self.agent.contacts.save({"name": "Jordan", "phone": "+19195550122", "aliases": ""})

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def titles(self):
        return [t["title"] for t in self.agent._run("tasks.list", {})["tasks"]]

    def test_slang_tags_stay_out_of_reminders(self):
        reply = self.agent.chat("can u remind me abt the dentist tmrw no cap")["text"]
        self.assertNotIn("cap", reply)
        self.agent.chat("remind me to call grandma tmrw fr")
        self.assertEqual(sorted(self.titles()), ["Call grandma", "The dentist"])

    def test_the_reason_can_come_first(self):
        self.assertRegex(self.agent.chat("finna go to the gym remind me at 6")["text"], r"go to the gym (?:tomorrow )?at 6")  # "tomorrow" after 6 PM
        self.assertIn("Go to the gym", self.titles())

    def test_a_text_without_that(self):
        reply = self.agent.chat("yo text my mom im pullin up in 5")
        self.assertIn("Mom", reply["text"])
        self.assertIn("pullin up in 5", reply["text"])
        self.assertIn("what should it say", self.agent.chat("text jordan back later")["text"].lower())  # not a message to send
        self.assertIn("sister", self.agent.chat("text my sister happy bday")["text"])  # someone new: Luma asks for the number

    def test_a_new_request_after_a_question_starts_fresh(self):
        self.assertIn("What should I remind you about", self.agent.chat("remind me at 6")["text"])
        reply = self.agent.chat("play some drake fr")["text"]
        self.assertIn("Playing drake on", reply)
        self.assertEqual(self.titles(), [])
        self.agent.chat("remind me at 6")
        self.assertRegex(self.agent.chat("call mom")["text"], r"call mom (?:tomorrow )?at 6")  # an answer is still an answer

    def test_questions_about_what_they_told_luma(self):
        self.assertEqual(self.agent.chat("my mom's birthday is June 3")["text"], "Got it. Your mom's birthday is June 3.")
        self.assertEqual(self.agent.chat("when is my moms bday?")["text"], "Your mom's birthday is June 3.")
        self.assertIn("don't know your dads birthday yet", self.agent.chat("whats my dads birthday")["text"])  # never Mom's by mistake
        self.assertNotIn("don't know", self.agent.chat("what's my schedule today")["text"])  # a lookup, not a memory
        self.assertEqual(self.agent.chat("my sister's name is dana")["text"], "Got it. Your sister's name is Dana.")  # typed in lowercase
        self.assertEqual(self.agent.chat("whats my sisters name")["text"], "Your sister's name is Dana.")
        from luma.agent.presence import notice_facts
        self.assertEqual(notice_facts("my mom is tired"), [])  # not a name

    def test_jokes_are_told_as_written_and_not_repeated(self):
        from luma.agent import humor_bank, jokes
        bits = {text for _, _, text, grown in humor_bank.all_bits() if not grown}
        first = self.agent.chat("tell me a joke")["text"]
        self.assertIn(first, bits, "Luma's own material, told exactly as written")
        second = self.agent.chat("another one")["text"]
        self.assertIn(second, bits)
        told = [self.agent.chat("tell me a joke")["text"] for _ in range(60)]
        self.assertEqual(len(set(told + [first, second])), 62, "never the same one twice")
        self.assertIn(self.agent.chat("tell me a dad joke")["text"], jokes.JOKES, "the classic puns are still there for a dad joke")
        self.assertFalse(jokes.asked("another one", 0, 100))  # "another one" alone isn't a joke request

    def test_a_plain_hello_gets_a_plain_hello_back(self):
        self.agent.use_model = True  # even with the brain on: it's instant and in their register
        reply = self.agent.chat("yo what's good luma")["text"]
        self.assertTrue(reply.startswith(("Yo", "Ayy", "What's good")), reply)
        self.assertRegex(self.agent.chat("hey luma")["text"], r"^(?:Up late|Morning|Hey|Evening)")

    def test_luma_talks_music_but_never_claims_a_body(self):
        from luma.agent.runtime import SENSED
        for fine in ["I heard the second verse goes crazy", "I know that album, the hook on track 3 is everything", "I hear you, that sucks",
                     "I'm listening to you", "the bridge is where she really goes off"]:
            self.assertFalse(SENSED.search(fine), fine)  # songs are written out: Luma can talk lyrics like a friend
        for claim in ["I was actually listening to it while making coffee", "I've been to Tokyo", "Ive been to that spot", "I ate the whole thing"]:
            self.assertTrue(SENSED.search(claim), claim)
        self.agent.planner = lambda *a: {"type": "reply", "text": "Nah 😭 the second verse carries that whole album though."}
        self.assertEqual(self.agent._without_senses("I played it on my commute, the second verse carries it.", "ngl that album kinda mid"),
                         "Nah 😭 the second verse carries that whole album though.")
        self.agent.planner = lambda *a: {"type": "reply", "text": "I ate there twice, it's great."}  # a rewrite that still claims it
        self.assertEqual(self.agent._without_senses("I ate there twice. The tacos are what everyone talks about though!", "you tried that spot?"),
                         "The tacos are what everyone talks about though!")

    def test_have_you_seen_it_gets_a_real_answer(self):
        self.assertRegex(self.agent.chat("you seen the new spiderman movie?")["text"], r"newer than what I know|caught up")  # may be past what it knows
        self.assertRegex(self.agent.chat("have you heard sos by sza")["text"], r"(?i)know it")  # a known song: it talks about it
        self.assertRegex(self.agent.chat("yo u tried the new popeyes sandwich")["text"], r"taste|eat")
        self.assertNotIn("watch", self.agent.chat("you seen my keys?")["text"].lower())  # that's a where-is question
        self.agent.use_model = True
        self.agent.planner = lambda *a: {"type": "reply", "text": "Kill Bill goes crazy, the hook is so petty lol"}
        self.assertIn("Kill Bill", self.agent.chat("have you heard sos by sza")["text"])  # with the brain on, it talks the lyrics itself

    def test_a_friend_who_can_hold_the_hard_stuff(self):
        from luma.agent import mind
        line = "That's a lot to carry, and you're not alone in this. I'm here for you. What happened?"
        self.assertEqual(mind.without_disclaimers(line, "i feel like everything is falling apart"), line)  # support stays
        self.assertNotIn("work so hard", mind.without_disclaimers("I know you work so hard. Want to talk money?", "im stressed about money"))
        reply = self.agent.chat("honestly i just want to die")["text"]
        self.assertIn("988", reply)
        self.assertNotIn("988", self.agent.chat("you seen suicide squad")["text"])
        self.assertNotIn("988", self.agent.chat("i hurt myself at the gym lol")["text"])

    def test_the_slang_archive_is_part_of_how_luma_talks(self):
        from luma.agent import slang
        size = slang.size()
        self.assertGreater(size["entries"], 1000)
        self.assertGreaterEqual(size["communities"], 45)
        for word, where in [("wahala", "africa"), ("kilig", "filipino"), ("yinz", "northeast"), ("chur", "aus"), ("jawn", "philly"), ("guey", "latino")]:
            self.assertIn(where, slang.explain(word).origins, word)
        self.assertEqual(slang.signals("I had cheese and wine at the house, the tank is green and cool")["terms"], [])  # everyday words aren't slang
        reply = self.agent.chat("what does wahala mean")["text"]
        self.assertIn("trouble", reply)
        self.assertIn("Like: “", reply)  # with the archive's own example
        self.assertIn("don't use it myself", self.agent.chat("what does fob mean")["text"])  # labels for people: explained, not said

    def test_luma_reads_the_lyrics_before_it_quotes_them(self):
        self.agent.use_model = True
        searched, real = [], self.agent.propose
        def propose(name, args):
            if name == "web.search":
                searched.append(args["query"])
                return {"results": [{"title": "Kendrick Lamar – Like That (verse) lyrics", "url": "https://example.com/like-that", "snippet": "the big three verse"}],
                        "summary": "Found the lyrics."}
            return real(name, args)
        self.agent.propose = propose
        self.agent.planner = lambda *a: {"type": "reply", "text": "That verse is him calling out the whole big three, and the flow is cold."}
        reply = self.agent.chat("what you think of kendrick's verse on like that")["text"]
        self.assertTrue(searched and "lyrics" in searched[0])  # it read the lyrics first
        self.assertIn("big three", reply)
        # a quote that isn't in what the search found comes out; with no web at all, it doesn't pretend to have looked
        def brain(messages, *a):
            if "misremembering" in messages[-1]["content"]:
                return {"type": "reply", "text": "The flow on that verse is slick, he sounds so sure of himself."}
            return {"type": "reply", "text": "honestly the flow is slick. The line 'you don’t need to know me to love me' hits hard."}
        self.agent.planner = brain
        self.assertNotIn("love me", self.agent.chat("what you think of kendrick's verse on like that")["text"])
        def offline(name, args):
            if name == "web.search":
                return {"results": [], "summary": "I couldn't reach the web just now."}
            return real(name, args)
        self.agent.propose = offline
        reply = self.agent.chat("what you think of kendrick's verse on like that")["text"]
        self.assertNotIn("love me", reply)  # the brain's guess, quotes taken out
        self.assertIn("flow", reply)
        self.agent.propose = real
        # without a look-up, a quoted line it may have misremembered comes out, and the take stays
        self.agent.planner = lambda *a: {"type": "reply", "text": "The flow on that verse is crazy, he sounds so calm."}
        self.assertEqual(self.agent._without_made_up_lyrics("He says “I don't need no love, I just need the truth” and it hits.", "kendrick verse"),
                         "The flow on that verse is crazy, he sounds so calm.")
        from luma.agent.runtime import QUOTED
        for quoted in ["The line 'I'm not trying to be the hero, I just want to be seen' hits hard", "he goes “motherf the big three, it's just big me”",
                       'he said "I don\'t need no love" on it', "the line ‘I’m not the hero, I’m just seen’ though"]:
            self.assertTrue(QUOTED.search(quoted), quoted)
        for fine in ["that verse on 'Like That' is crazy", "he's calm, it's cold, they're shook", "“Like That” slaps"]:
            self.assertFalse(QUOTED.search(fine), fine)
        self.agent.planner = lambda *a: {"type": "reply", "text": "He says “I just need the truth” fr."}  # a rewrite that still quotes
        self.assertEqual(self.agent._without_made_up_lyrics("He says “I don't need no love, I just need the truth”. The beat is insane though.", "kendrick verse"),
                         "The beat is insane though.")

    def test_that_album_with_no_album_named_gets_which_one(self):
        reply = self.agent.chat("ngl that album kinda mid")["text"]
        self.assertIn("which album", reply.lower())  # a friend asks; it never invents "the intro had that raw energy"
        self.assertNotRegex(reply, r"[?!] [a-z]")  # a new sentence starts with a capital
        self.assertRegex(self.agent.chat("this song goes so hard")["text"].lower(), r"which song")
        self.assertIsNone(self.agent._which_one("ngl that album by sza kinda mid", "ngl that album by sza kinda mid"))  # named: the brain talks about it
        self.agent.history = [{"role": "user", "content": "you heard the new sza album?"}, {"role": "assistant", "content": "Yeah, what you think?"}]
        self.assertIsNone(self.agent._which_one("that album kinda mid", "that album kinda mid"))  # they've been on one: it's that one
        self.agent.use_model = True  # naming it after "which album?": the take stays, a quoted line it may have misremembered goes
        def brain(messages, *a):
            if "misremembering" in messages[-1]["content"]:
                return {"type": "reply", "text": "SOS? Nah, that one's not mid at all. Kill Bill alone carries it."}
            return {"type": "reply", "text": "SOS? Nah, not mid. When she sings 'I might kill my ex, not the best idea' I lose it."}
        self.agent.planner = brain
        self.assertNotIn("'", self.agent.chat("sos by sza")["text"].replace("one's", ""))
        self.agent.use_model = False
        self.agent.history = self.agent.threads["main"] = []  # a fresh conversation, with someone who writes in full sentences
        self.store.set_setting("their_style", None)
        self.assertEqual(self.agent.chat("That album is a bit overrated.")["text"], "Which album do you mean? Tell me and I'll give you my honest take.")

    def test_one_specific_thing_it_may_not_know_gets_looked_up(self):
        from luma.agent.runtime import ProviderError
        asked = []
        found = {"text": "Couldn't find anything on a band called Glass Pelican.", "results": [{"title": "x", "url": "https://a.com", "snippet": ""}]}
        self.agent.look_it_up = lambda text, ev=None: asked.append(text) or found
        for question in ["what do you think of glass pelican's new record?", "is the zentrix pro 9 phone worth it?", "what's the plot of the movie silver lanterns?",
                         "what's the best dish at marlowe's kitchen on 5th street?", "have you read the copper orchard by mira tannenbaum?"]:
            self.assertIs(self.agent.chat(question), found, question)  # the web, never a track list from memory
        self.assertEqual(len(asked), 5)
        for talk in ["my new phone is broken", "is it worth it to wake up early?", "have you read my message?", "i have beef with my roommate"]:
            self.assertIsNone(self.agent._look_first(talk, talk), talk)
        self.agent.look_it_up = lambda text, ev=None: {"text": "", "results": []}  # nothing came back: it says so instead of guessing
        reply = self.agent.chat("what do you think of glass pelican's new record?")["text"]
        self.assertRegex(reply, r"couldn't (?:look|check)")
        self.assertTrue(reply.endswith("?"))
        def offline(text, ev=None):
            raise ProviderError("no internet")
        self.agent.look_it_up = offline
        self.store.set_setting("their_style", None)  # someone who writes in full sentences
        self.assertIn("rather not guess", self.agent.chat("Is the Zentrix Pro 9 worth it?")["text"])
        self.agent.enable("web_search", False)
        self.agent.look_it_up = lambda *a: self.fail("web is off")
        self.assertRegex(self.agent.chat("thoughts on the new hyperion app?")["text"], r"couldn't (?:look|check)")

    def test_slang_is_conversation_not_a_command(self):
        before = self.agent.store.setting("hush_until", 0)
        self.agent.chat("ngl i need a drink")
        self.assertEqual(self.agent.store.setting("hush_until", 0), before)


if __name__ == "__main__":
    unittest.main()
