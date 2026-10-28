"""What the real-Mac lab (run 138) caught, fixed: a story still got a stock check because the brain's rewrite pass turned
"lmao my boss scheduled a meeting at 4:59" into one (stories skip that pass); "NAHHH😭😭" was thrown away as garbled; and a
reply of just "..." (the placeholder from the reply format, copied) counted as an answer."""
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.llm.inference import garbled
from luma.memory.store import Store


class LabRun138Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_a_story_isnt_rewritten_into_a_job(self):
        rewrites = []

        def planner(messages, *a, **k):
            if "Rewrite the LAST message" in str(messages[-1].get("content")):
                rewrites.append(messages[-1]["content"])
                return {"type": "reply", "text": "Check the GAF stock price."}
            return {"type": "reply", "text": "4:59 on a Friday is a power move. Evil, but a power move."}
        planner.understands = True
        agent = Agent(store=self.store, use_model=True, planner=planner)
        agent.market_fetch = lambda url: self.fail("no price check for a story")
        out = agent.chat("lmao my boss scheduled a meeting at 4:59 on a friday")
        self.assertEqual(out["text"], "4:59 on a Friday is a power move. Evil, but a power move.")
        self.assertFalse(rewrites)
        agent.chat("need you to handle the stuff for friday")
        self.assertTrue(rewrites, "a real request still gets the rewrite pass")

    def test_a_word_with_an_emoji_is_a_reply(self):
        for said in ("NAHHH😭😭", "bruhhh💀", "nahhh😭", "yikes…😬", "LMAOOOO😭😭😭"):
            self.assertFalse(garbled(said), said)
        for junk in ("BBEC&7%.G", "+A57#8++&B", "#8++&B+,#$C8"):
            self.assertTrue(garbled(junk), junk)

    def test_three_dots_alone_get_a_second_thought(self):
        said = iter(["...", "Honestly I haven't seen it. Which show? I'll tell you if I know it."])
        agent = Agent(store=self.store, use_model=True, planner=lambda *a, **k: {"type": "reply", "text": next(said)})
        self.assertEqual(agent.chat("did you like the ending?")["text"], "Honestly I haven't seen it. Which show? I'll tell you if I know it.")


if __name__ == "__main__":
    unittest.main()
