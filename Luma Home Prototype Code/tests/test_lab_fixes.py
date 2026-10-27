"""What the real-Mac lab (run 113) caught, fixed: checking Gmail through the apps hub reads it directly (the 4B brain picked
the wrong action ten times out of ten); "how much is a PS5 right now" goes to a store check instead of the brain's memory;
gas prices get looked up; a brain that comes back empty gets a person's answer, not an error; a garbled reply moves the
brain to the processor; index pages ("... Archives - The Shade Room") aren't stories."""
import os
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from luma.agent.runtime import Agent
from luma.llm import inference
from luma.memory.store import Store

HUB = Path(__file__).resolve().parent / "fixtures" / "mcp" / "apps_hub.py"


class LabFixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def agent(self, planner=None):
        agent = Agent(store=self.store, use_model=planner is not None, planner=planner)
        return agent

    def test_checking_gmail_through_the_hub_reads_it_directly(self):
        def wrong_action(*a, **k):
            return {"type": "reply", "text": "Review these exact details. Confirm locally to continue; nothing has been sent or ordered."}
        for planner in (None, wrong_action):
            agent = self.agent(planner)
            try:
                agent.connectors.add("Apps", command=f"{shlex.quote(sys.executable)} {shlex.quote(str(HUB))}")
                agent.enable("connectors", True)
                agent.chat("connect my gmail")
                out = agent.chat("check my gmail")
                self.assertIn("Lunch Friday?", out["text"] + str(out.get("emails")))
                self.assertEqual(out["emails"][0]["from"], "Sam")
                self.assertNotIn("Confirm locally", out["text"])
            finally:
                agent.connectors.close()

    def test_a_price_is_checked_not_remembered(self):
        agent = self.agent(lambda *a, **k: {"type": "reply", "text": "A PS5 is usually around $499 right now."})
        checked = []
        agent.shop = lambda query, **k: checked.append(query) or {"text": f"I checked the stores for {query}.", "offers": []}
        out = agent.chat("how much is a ps5 right now?")
        self.assertEqual(checked, ["ps5"])
        self.assertNotIn("$499", out["text"])

    def test_gas_prices_get_looked_up(self):
        agent = self.agent(lambda *a, **k: {"type": "reply", "text": "Gas is about $3.19 near you."})
        looked = []
        agent.look_it_up = lambda text, *a, **k: looked.append(text) or {"text": "", "results": []}
        out = agent.chat("how much is gas near me?")
        self.assertTrue(looked)
        self.assertNotIn("3.19", out["text"])

    def test_an_empty_brain_gets_a_person_not_an_error(self):
        def empty(*a, **k):
            raise ValueError("Local model returned no usable reply.")
        agent = self.agent(empty)
        self.assertIn(agent.chat("so what do you think about all that")["text"],
                      {"I lost my train of thought on that one. Say it again?", "I turned it over a few ways but couldn't get a good hold on it. Tell me a bit more?"})
        self.assertIn("rather not quote lyrics from memory", agent.chat("what's the first line of the lyrics to bohemian rhapsody")["text"])

    def test_a_garbled_reply_moves_the_brain_to_the_processor(self):
        agent = self.agent(lambda *a, **k: {"type": "reply", "text": "+A57#8++&B"})
        with mock.patch.dict(os.environ, {"LUMA_GPU_LAYERS": "-1"}), mock.patch.object(inference, "_llm", object()):
            out = agent.chat("did you like the ending of that show my friend told me about")
            self.assertEqual(out["text"], "Sorry, my brain glitched on that one. Say it again?")
            self.assertEqual(os.environ["LUMA_GPU_LAYERS"], "0")
            self.assertIsNone(inference._llm, "reloaded on the processor next time")

    def test_index_pages_are_not_stories(self):
        from luma.skills.news import JUNK_TITLE
        self.assertTrue(JUNK_TITLE.search("Papoose freestyle Eazy The Block Captain Archives - The Shade Room"))
        self.assertFalse(JUNK_TITLE.search("Archive footage shows new details"))


if __name__ == "__main__":
    unittest.main()
