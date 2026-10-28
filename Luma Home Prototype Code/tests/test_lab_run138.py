"""What the real-Mac lab (runs 138 and 140) caught, fixed: a story still got a stock check because the brain's rewrite pass
turned "lmao my boss scheduled a meeting at 4:59" into one (stories skip that pass); "NAHHH😭😭" was thrown away as garbled; a
reply of just "..." (the placeholder from the reply format, copied) counted as an answer; and a graphics chip that turned the
first full-length reply into symbols got a second try on the same chip (now: the processor, and a start-up check long enough
to catch it)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from luma.agent.runtime import Agent
from luma.llm import inference
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

    def test_symbols_instead_of_a_reply_move_the_second_try_to_the_processor(self):
        tries = []

        def planner(messages, *a, **k):
            if messages[-1]["content"] == "lmao my boss scheduled a meeting at 4:59 on a friday":  # the reply itself, not a side pass
                tries.append(os.environ.get("LUMA_GPU_LAYERS"))
                if len(tries) == 1:
                    raise ValueError("The local model returned an invalid proposal (garbled). No action was taken.")
            return {"type": "reply", "text": "4:59 on a Friday is a power move. Evil, but a power move."}
        agent = Agent(store=self.store, use_model=True, planner=planner)
        with mock.patch.dict(os.environ, {"LUMA_GPU_LAYERS": "-1"}), mock.patch.object(inference, "_llm", object()):
            out = agent.chat("lmao my boss scheduled a meeting at 4:59 on a friday")
            self.assertEqual(out["text"], "4:59 on a Friday is a power move. Evil, but a power move.")
            self.assertEqual(tries, ["-1", "0"])

    def test_a_cut_off_answer_is_not_blamed_on_the_chip(self):
        tries = []

        def planner(messages, *a, **k):
            if messages[-1]["content"] == "so then my cousin shows up late":
                tries.append(os.environ.get("LUMA_GPU_LAYERS"))
                if len(tries) == 1:
                    raise ValueError("The local model returned an invalid proposal. No action was taken.")
            return {"type": "reply", "text": "Okay, what happened next?"}
        agent = Agent(store=self.store, use_model=True, planner=planner)
        with mock.patch.dict(os.environ, {"LUMA_GPU_LAYERS": "-1"}):
            self.assertEqual(agent.chat("so then my cousin shows up late")["text"], "Okay, what happened next?")
            self.assertEqual(tries, ["-1", "-1"])

    def test_the_start_up_check_asks_behind_the_full_instructions(self):
        asked = []

        class Model:
            def create_chat_completion(self, messages, **k):
                asked.append(messages)
                return {"choices": [{"message": {"content": "+A57#8++&B"}}]}
        self.assertFalse(inference._sane(Model()))
        self.assertGreater(len(asked[0][0]["content"]), 1500)
        self.assertEqual(asked[0][-1]["content"], "Say hello in a few words.")

    def test_a_garbled_first_thought_moves_the_reply_to_the_processor(self):
        def planner(messages, *a, **k):
            if str(messages[-1]["content"]).startswith("Your mood right now"):  # the thought before the reply
                return {"type": "reply", "text": "+A57#8++&B"}
            return {"type": "reply", "text": "That's a power move. Evil, but a power move."}
        agent = Agent(store=self.store, use_model=True, planner=planner)
        with mock.patch.dict(os.environ, {"LUMA_GPU_LAYERS": "-1"}), mock.patch.object(inference, "_llm", object()):
            out = agent.chat("lmao my boss scheduled a meeting at 4:59 on a friday")
            self.assertEqual(out["text"], "That's a power move. Evil, but a power move.")
            self.assertEqual(os.environ["LUMA_GPU_LAYERS"], "0")

    def test_a_garbled_second_look_keeps_the_first_answer(self):
        agent = Agent(store=self.store, use_model=True, planner=lambda *a, **k: {"type": "reply", "text": "+A57#8++&B"})
        with mock.patch.dict(os.environ, {"LUMA_GPU_LAYERS": "-1"}), mock.patch.object(inference, "_llm", object()):
            self.assertEqual(agent.correct("Fair, that's a long day.", "today was so long"), "Fair, that's a long day.")
            self.assertEqual(os.environ["LUMA_GPU_LAYERS"], "0")


if __name__ == "__main__":
    unittest.main()
