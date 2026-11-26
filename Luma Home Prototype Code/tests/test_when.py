"""At a pause: wait, nod or answer (luma.audio.when; docs/GAME_PLAN.md, B4). The lines in tests/when_lines.py were
written before the reader and counted once, by the same hand the same hour: of 20 pauses in the middle of a thought
Luma's own code waits on 18 and takes 1 for finished; of 20 finished things it holds none (it's sure of 3 and leaves 17
to the sound, as today). Nothing is changed to fit them. What a brain adds, and whether any of it makes Luma's timing
better, isn't measured: that needs the timing test's recordings."""
import tempfile
import unittest
from pathlib import Path

import when_lines
from luma.agent.runtime import Agent
from luma.audio import when
from luma.memory.store import Store


class ByCode(unittest.TestCase):
    def test_the_honest_count(self):
        mid = [when.by_code(t) for t in when_lines.MID]
        done = [when.by_code(t) for t in when_lines.DONE]
        self.assertGreaterEqual(mid.count("wait"), 18)
        self.assertLessEqual(mid.count("answer"), 1)
        self.assertEqual(done.count("wait"), 0, "a finished thing to say is never held")

    def test_nobody_who_might_not_be_safe_is_kept_waiting(self):
        for said in when_lines.NEVER_HELD:
            self.assertEqual(when.by_code(said), "answer", said)

    def test_a_few_plain_ones(self):
        self.assertEqual(when.by_code("I went to the store because"), "wait")
        self.assertEqual(when.by_code("so anyway, the other day..."), "wait")
        self.assertEqual(when.by_code("what time is it in Tokyo"), "answer")
        self.assertEqual(when.by_code("That was a long day."), "answer")
        self.assertIsNone(when.by_code("I love this song"))
        self.assertIsNone(when.by_code(""))


class Decide(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.asked = []

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def agent(self, says=None):
        agent = Agent(store=self.store, use_model=False)
        if says is not None:
            def planner(messages, context, allowed, *args, **kwargs):
                self.asked.append(messages[-1]["content"])
                return {"type": "reply", "text": says}
            planner.answers_plain_questions = True
            agent.planner = planner
        return agent

    def test_it_is_off_as_luma_comes(self):
        agent = self.agent("NO")
        self.assertIsNone(when.decide(agent, "I went to the store because"))
        self.assertEqual(self.asked, [])

    def test_code_first_and_the_brain_only_where_code_cant_tell(self):
        agent = self.agent("NO")
        self.store.set_setting("brain_picks_when", True)
        self.assertEqual(when.decide(agent, "I went to the store because"), "wait")
        self.assertEqual(when.decide(agent, "what time is it in Tokyo"), "answer")
        self.assertEqual(self.asked, [])
        self.assertEqual(when.decide(agent, "I love this song"), "wait")           # the brain said it isn't finished
        self.assertEqual(len(self.asked), 1)
        self.assertIn('"I love this song"', self.asked[0])
        self.assertIn("YES or NO only", self.asked[0])

    def test_a_yes_is_answer_and_a_long_unfinished_telling_is_a_nod(self):
        self.store.set_setting("brain_picks_when", True)
        self.assertEqual(when.decide(self.agent("YES"), "I love this song"), "answer")
        long = "we drove up on Friday night after work and got there really late and nobody had told the neighbours"
        self.assertEqual(when.decide(self.agent("no"), long), "nod")

    def test_an_answer_that_is_neither_leaves_it_to_the_sound(self):
        self.store.set_setting("brain_picks_when", True)
        self.assertIsNone(when.decide(self.agent("Well, it depends on the tone."), "I love this song"))

    def test_with_no_brain_to_ask_nothing_is_decided(self):
        self.store.set_setting("brain_picks_when", True)
        self.assertIsNone(when.decide(self.agent(), "I love this song"))

    def test_someone_who_might_not_be_safe_is_answered_and_no_brain_is_asked_first(self):
        self.store.set_setting("brain_picks_when", True)
        agent = self.agent("NO")
        self.assertEqual(when.decide(agent, when_lines.NEVER_HELD[0]), "answer")
        self.assertEqual(self.asked, [])


if __name__ == "__main__":
    unittest.main()
