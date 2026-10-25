"""Luma talks like a person: slang understood (with where it comes from), the owner's own register
mirrored (never someone else's dialect), characters on request, running jokes, and an adults-only
unhinged mode that cusses but never says a slur."""
import tempfile
import unittest
from pathlib import Path

from luma.agent import banter, slang
from luma.agent.runtime import Agent
from luma.llm import prompts
from luma.memory.store import Store


class LexiconTests(unittest.TestCase):
    def test_reads_slang_with_stretched_spellings_and_knows_where_it_comes_from(self):
        found = {e.term: e for _, e in slang.find("brooo im finna crash out deadasss, that food was bussin fr")}
        self.assertTrue({"bro", "finna", "crash out", "deadass", "bussin", "fr"} <= set(found))
        self.assertIn("aave", found["bussin"].origins)
        self.assertIn("ballroom", slang.explain("slayyy").origins)
        self.assertIn("uk", slang.explain("innit").origins)
        self.assertEqual(slang.find("Please send the quarterly report by Friday."), [])

    def test_big_and_varied(self):
        size = slang.size()
        self.assertGreater(size["entries"], 450)
        self.assertGreaterEqual(size["communities"], 20)

    def test_never_says_a_slur(self):
        self.assertEqual(slang.clean("nah my nigga that was crazy"), "nah my bro that was crazy")
        self.assertNotIn("fag", slang.clean("don't be a fag about it").lower())
        self.assertEqual(slang.clean("that was fire"), "that was fire")

    def test_mirrors_their_community_only_once_it_is_clear(self):
        stats = {"n": 0}
        for m in ["yo gng wyd", "ngl im finna sleep fr", "deadass that was bussin", "on god he cappin", "bet say less"]:
            stats = slang.learn(stats, m)
            stats["n"] += 1
        note = slang.register_note(stats)
        self.assertIn("Black American English", note)
        self.assertIn("never put on an accent", note)
        plain = {"n": 0}
        for m in ["Can you check my calendar for Thursday?", "Please draft a reply to Dana.", "What's the weather tomorrow?",
                  "Remind me to call the bank.", "Thanks, that works.", "How long is the drive to Durham?"]:
            plain = slang.learn(plain, m)
            plain["n"] += 1
        self.assertIn("Keep yours out", slang.register_note(plain))

    def test_cussing_matches_only_when_allowed(self):
        stats = {"n": 0}
        for m in ["wtf is this", "that shit was crazy", "bro fuck that", "damn ok"]:
            stats = slang.learn(stats, m)
            stats["n"] += 1
        self.assertIn("cuss back", slang.register_note(stats, "unhinged"))
        self.assertNotIn("cuss back", slang.register_note(stats, "everyday"))


class CharacterTests(unittest.TestCase):
    def test_spots_requests_and_stops(self):
        self.assertEqual(banter.character_request("talk like a pirate")[1], "pirate")
        self.assertEqual(banter.character_request("be my hype man")[1], "hype")
        self.assertEqual(banter.character_request("roleplay as a medieval knight")[2], "medieval knight")
        self.assertEqual(banter.character_request("be yourself again"), ("clear",))
        self.assertIsNone(banter.character_request("act like you care"))
        self.assertIsNone(banter.character_request("talk like a normal person"))

    def test_laughs_are_laughs(self):
        for t in ("lmao", "😭😭", "bro 💀", "im dead", "LMFAOOO"):
            self.assertTrue(banter.laughed(t), t)
        self.assertFalse(banter.laughed("that is funny but what time is it"))


def recording_planner(seen):
    def planner(messages, context, allowed, mode):
        seen.append(context)
        return {"type": "reply", "text": "ok"}
    return planner


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.seen = []
        for key in ("think_first", "deliberate", "deep_mind"):
            self.store.set_setting(key, False)  # one plain reply per message, so the test sees exactly what the brain was told
        self.agent = Agent(store=self.store, use_model=True, planner=recording_planner(self.seen))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def notes(self):
        return " ".join(str(m.get("text", "")) for m in (self.seen[-1] if self.seen else []) if isinstance(m, dict))

    def test_characters_stick_until_they_say_stop(self):
        reply = self.agent.chat("talk like a pirate")
        self.assertIn("Pirate", reply["text"])
        self.agent.chat("what should I eat tonight")
        self.assertIn("pirate captain", self.notes())
        self.assertIn("Back to me", self.agent.chat("ok be yourself again")["text"])
        self.agent.chat("what should I eat tonight")
        self.assertNotIn("pirate captain", self.notes())

    def test_unhinged_is_for_adults_who_ask(self):
        self.assertIn("Settings", self.agent.chat("turn on unhinged mode")["text"])  # no birthday on file: confirm in Settings
        self.store.set_setting("account_profile", {"dob": "2012-05-01"})
        self.assertIn("adults", self.agent.chat("turn on unhinged mode")["text"])
        self.assertNotEqual(self.agent.profile.get("preset"), "unhinged")
        self.store.set_setting("account_profile", {"dob": "1998-05-01"})
        self.assertIn("Unhinged mode's on", self.agent.chat("turn on unhinged mode")["text"])
        self.assertEqual(self.agent.profile["preset"], "unhinged")
        prompt = prompts.build_personality_prompt("friend", self.agent.profile)
        self.assertIn("Cuss freely", prompt)
        self.assertIn("no slurs", prompt)
        self.assertNotIn("Cuss freely", prompts.build_personality_prompt("kids", self.agent.profile))
        self.agent.chat("ok tone it down")
        self.assertNotEqual(self.agent.profile["preset"], "unhinged")
        with self.assertRaises(ValueError):
            prompts.profile_for_preset("unhinged", None, adult_confirmed=False)

    def test_a_line_that_lands_becomes_a_running_joke(self):
        self.agent.last_reply = "Ten minutes on read isn't ghosting, that's him finding the perfect emoji."
        self.agent.chat("LMAOOO 😭")
        self.agent.chat("anyway what's up")
        self.assertIn("perfect emoji", self.notes())
        self.assertIn("Running jokes", self.notes())

    def test_explains_slang_and_learns_new_words(self):
        said = self.agent.chat("what does bussin mean")["text"]
        self.assertIn("really good", said)
        self.assertIn("Black American English", said)
        self.assertIn("Got it", self.agent.chat("zorp means cool but in a weird way")["text"])
        self.assertIn("cool but in a weird way", self.agent.chat("what does zorp mean")["text"])

    def test_slurs_from_the_brain_are_cleaned(self):
        agent = Agent(store=self.store, use_model=True, planner=lambda *a: {"type": "reply", "text": "nah my nigga you good"})
        self.assertEqual(agent.chat("am I tripping")["text"], "nah my bro you good")


if __name__ == "__main__":
    unittest.main()
