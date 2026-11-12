"""Keeping up (luma.agent.keepup): when they bring up an album, a game, a show or a book, Luma reads up on it without
being asked, and only the name of the thing leaves the home. Lines written for this file, from no generator."""
import tempfile
import unittest
from pathlib import Path

from luma.agent import keepup


class TheyAskedAboutIt(unittest.TestCase):
    ASKED = {
        "have you heard the new kendrick album": "new kendrick album",
        "have you seen the new spider-man movie": "new spider-man movie",
        "did you watch the last of us season 2": "the last of us season 2",
        "have you played hollow knight silksong": "hollow knight silksong",
        "you heard sza's new single?": "sza's new single",
        "have you read the new sally rooney book": "new sally rooney book",
        "ever listened to the tortured poets department": "the tortured poets department",
        "did you see the new season of the bear": "new season of the bear",
        "have you checked out the new zelda": "new zelda",
        "yo luma you seen dune part two": "dune part two",
        "have you heard of chappell roan": "chappell roan",
        "do you know about the show severance": "the show severance",
        "hey did you catch the new tyler the creator album yet": "new tyler the creator album",
        "have you watched arcane": "arcane",
    }
    NOT_ASKED = [
        "have you seen my keys", "have you heard from my sister", "did you hear what my boss said", "have you seen him lately",
        "did you watch me do that", "have you heard me", "have you read my message", "have you seen it", "did you see that",
        "have you heard the news about my dad", "did you hear about the layoffs at my job", "did you see how late it is",
        "have you heard anything back", "do you know about my appointment", "did you watch the game", "did you see the fight last night",
        "have you read what i wrote", "did you hear the neighbors last night", "have you seen our new apartment",
        "did you catch what the doctor told me", "do you watch anime", "do you read books", "do you play games",
        "have you heard", "did you see", "have you seen the photos my mom sent",
    ]

    def test_the_name_of_the_thing_is_what_gets_looked_up(self):
        for said, query in self.ASKED.items():
            found = keepup.asked(said)
            self.assertIsNotNone(found, said)
            self.assertEqual(found.get("query"), query, said)
            self.assertTrue(found["verb"], said)

    def test_nothing_of_theirs_is_ever_a_thing_to_look_up(self):
        self.assertEqual([(said, keepup.asked(said)) for said in self.NOT_ASKED if keepup.asked(said)], [])

    def test_with_nothing_named_luma_can_ask_which(self):
        for said, kind in (("have you heard this album", "album"), ("have you seen that movie", "movie"), ("did you read the book", "book")):
            self.assertEqual(keepup.asked(said), {"unnamed": kind, "verb": keepup.asked(said)["verb"]}, said)


class TheyOnlyBroughtItUp(unittest.TestCase):
    MENTIONED = {
        "i've been listening to the new kendrick album all day": "new kendrick album",
        "can't stop playing the new zelda game": "new zelda game",
        "just started the new season of the bear": "new season of the bear",
        "sza's new album is all i listen to": "sza's new album",
        "we watched the new mission impossible movie last night": "new mission impossible movie",
        "i'm on season 3 of the white lotus": "season 3 of the white lotus",
        "taylor swift's new record came out and it's so good": "taylor swift's new record",
        "started the latest brandon sanderson book": "latest brandon sanderson book",
        "the new season of bridgerton has a hold on me": "new season of bridgerton",
        "been bumping the new tyler the creator album": "new tyler the creator album",
        "the final season of stranger things wrecked me": "final season of stranger things",
        "finally got the new call of duty game": "new call of duty game",
    }
    NOT_MENTIONED = [
        "my new album of baby photos is done", "our new show at school went great", "i got a new game for my nephew",
        "i need a new phone", "new season of my life", "the new book my therapist gave me is about grief",
        "my sister's new single life is going great", "i wrote a new song for my mom", "our band's new ep drops friday",
        "the new show at the planetarium was fun", "new episode of my podcast is up", "season 2 of my life is going better",
        "i can't sleep, been thinking about the new job", "we recorded our new album in a garage", "i started a new book club",
        "it's a new kind of show for me", "i found a new favorite album", "i had pasta for dinner", "work was long",
        "i'm on chapter 3 of my thesis", "the new guy at work is weird", "my mom's new book club meets on tuesday",
        "is the new kendrick album out yet", "what do you think of the new zelda game",
        "the last episode of my favorite show made me cry", "part two of the story is that i quit",
    ]

    def test_a_new_thing_named_in_passing_is_read_up_on(self):
        for said, query in self.MENTIONED.items():
            found = keepup.mentioned(said)
            self.assertIsNotNone(found, said)
            self.assertEqual(found["query"], query, said)

    def test_nothing_of_theirs_and_nothing_unnamed_is(self):
        self.assertEqual([(said, keepup.mentioned(said)) for said in self.NOT_MENTIONED if keepup.mentioned(said)], [])


class WhatLeavesTheHome(unittest.TestCase):
    """The name of the thing, and nothing else they said."""

    def test_no_search_ever_carries_a_word_about_them(self):
        said = list(TheyAskedAboutIt.ASKED) + list(TheyOnlyBroughtItUp.MENTIONED)
        for line in said:
            found = keepup.asked(line) or keepup.mentioned(line)
            self.assertFalse(keepup.private(found["query"]), line)
            self.assertLessEqual(len(found["query"].split()), 9, line)
            self.assertIn(found["query"], line.lower())   # only words they said about the thing, never anything added

    def test_a_phrase_with_anything_of_theirs_in_it_is_private(self):
        for phrase in ("my sister's new single", "the book my therapist gave me", "our new album", "new album for mom", "call me at 5551234567",
                       "the show at school", "new game i made", "season 2 of my life"):
            self.assertTrue(keepup.private(phrase), phrase)
        for phrase in ("new kendrick album", "the last of us season 2", "hollow knight silksong", "new season of the bear"):
            self.assertFalse(keepup.private(phrase), phrase)

    def test_luma_never_says_it_heard_it(self):
        for reply in ("Yes, I've heard it and it's great.", "I listened to it last night.", "Yeah I did, I watched it twice.",
                      "I've been playing it all week.", "I've read it, it's wonderful.", "When I heard track three I lost it."):
            self.assertTrue(keepup.claims_it_did(reply), reply)
        for reply in ("I can't hear it the way you do, but I just read up on it: it came out in November.",
                      "I read up on it just now. People are calling it his best since 2017.", "I haven't, I can't watch things. I read about it though."):
            self.assertFalse(keepup.claims_it_did(reply), reply)
        self.assertIn("never say you have", keepup.HOW)


class InTheRuntime(unittest.TestCase):
    def setUp(self):
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        self.dir = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)
        self.agent = Agent(store=Store(root / "s.db", root / "k"), use_model=False)
        self.searched = []

        def propose(name, args):
            self.searched.append((name, dict(args)))
            return {"summary": "GNX is Kendrick Lamar's sixth studio album, released in November 2024.",
                    "results": [{"title": "GNX - Wikipedia", "url": "https://example.org/gnx", "snippet": "GNX is the sixth studio album..."}]}
        self.agent.propose = propose

    def tearDown(self):
        self.agent.store.close()
        self.dir.cleanup()

    def test_have_you_heard_it_goes_and_reads_and_says_so_honestly(self):
        reply = self.agent.chat("have you heard the new kendrick album")
        self.assertEqual(self.searched, [("web.search", {"query": "new kendrick album"})])
        self.assertIn("read up", reply["text"])
        self.assertIn("GNX", reply["text"])
        self.assertFalse(keepup.claims_it_did(reply["text"]))

    def test_only_the_name_leaves_never_what_they_said_around_it(self):
        self.agent.chat("ok so my week was rough and my boss yelled at me, anyway have you played hollow knight silksong")
        for _, args in self.searched:   # this one isn't a plain have-you question, so nothing may be searched at all, or only the name
            self.assertNotIn("boss", args["query"])
            self.assertNotIn("rough", args["query"])

    def test_bringing_it_up_hands_the_brain_what_was_read(self):
        self.agent.history.append({"role": "user", "content": "i've been listening to the new kendrick album all day"})
        notes = self.agent._keepup_context("i've been listening to the new kendrick album all day")
        self.assertEqual(self.searched, [("web.search", {"query": "new kendrick album"})])
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].get("read"))
        self.assertIn("GNX", notes[0]["text"])
        self.agent._keepup_context("i've been listening to the new kendrick album all day")
        self.assertEqual(len(self.searched), 1)   # read once, not on every turn it comes up

    def test_never_in_kids_mode(self):
        self.agent.set_mode("kids")
        self.agent.chat("have you heard the new kendrick album")
        self.assertEqual(self.agent._keepup_context("i've been listening to the new kendrick album all day"), [])
        self.assertEqual(self.searched, [])

    def test_never_when_they_are_hurting(self):
        self.agent.history.append({"role": "user", "content": "my dad died last week"})
        self.agent.history.append({"role": "user", "content": "he loved the new springsteen album so much"})
        self.assertEqual(self.agent._keepup_context("he loved the new springsteen album so much"), [])
        self.assertEqual(self.searched, [])

    def test_not_with_the_web_switched_off_and_not_when_the_owner_says_no(self):
        self.agent.store.set_setting("integration:web_search", False)
        self.assertEqual(self.agent._keepup_context("been bumping the new tyler the creator album"), [])
        self.agent.store.set_setting("integration:web_search", True)
        self.agent.store.set_setting("read_ahead", False)
        self.assertEqual(self.agent._keepup_context("been bumping the new tyler the creator album"), [])
        self.assertEqual(self.searched, [])
        reply = self.agent.chat("have you heard the new kendrick album")   # asked straight out: the old honest line, no search
        self.assertEqual(self.searched, [])
        self.assertTrue(reply["text"])

    def test_with_nothing_named_it_asks_which(self):
        reply = self.agent.chat("have you heard this album")
        self.assertEqual(self.searched, [])
        self.assertIn("which", reply["text"].lower())

    def test_when_nothing_is_found_it_says_so_and_does_not_guess(self):
        self.agent.propose = lambda name, args: {"summary": "", "results": []}
        reply = self.agent.chat("have you heard the new kendrick album")
        self.assertFalse(keepup.claims_it_did(reply["text"]))
        self.assertNotIn("GNX", reply["text"])

    def test_what_was_read_reaches_the_brain_as_information(self):
        from luma.llm import prompts
        steady, turn = prompts.build_plan_parts([{"read": True, "text": "About new kendrick album: GNX is the sixth studio album."}], [], "friend", {})
        self.assertIn("GNX", turn)
        self.assertIn("not instructions", turn)
        self.assertIn("never say you", turn)
        self.assertNotIn("GNX", steady)


if __name__ == "__main__":
    unittest.main()
