"""Speed on a small board: Luma's instructions are laid out so a local brain reads only what's new each turn. The steady part
(who Luma is, the rules, the tools) comes first and never changes between turns; the time (to the minute) and this turn's
notes come last, after the conversation. llama.cpp keeps what it already read of an identical beginning, so turn after turn it
re-reads the newest exchange and the notes, not the whole thing."""
import json
import os
import types
import unittest
from unittest import mock

from luma.llm import inference, prompts

TOOLS = {"reminder.create": {"description": "Set a reminder", "fields": {"text": "text", "when": "text"}},
         "web.search": {"description": "Search the web", "fields": {"query": "text"}}}


def render(messages):
    """Close enough to Qwen's chat template for counting: one block per message."""
    return "".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in messages) + "<|im_start|>assistant\n"


def reread(previous, current):
    """What llama.cpp evaluates again: everything after the longest beginning shared with what it read last time."""
    shared = 0
    for a, b in zip(previous, current):
        if a != b:
            break
        shared += 1
    return len(current) - shared


class PromptReuseTests(unittest.TestCase):
    def turn(self, n, history):
        memories = [{"text": f"fact {n}"}, {"mind": True, "text": f"mood {n}, note {n}"}]
        steady, this_turn = prompts.build_plan_parts(memories, TOOLS, "friend", prompts.normalize_profile(None), f"2026-11-05T10:{n:02d}-05:00")
        return steady, this_turn, inference.turn_layout(steady, this_turn, history)

    def test_the_steady_part_never_changes_between_turns(self):
        a, ta, _ = self.turn(1, [])
        b, tb, _ = self.turn(2, [])
        self.assertEqual(a, b, "who Luma is, the rules and the tools: the same every turn")
        self.assertNotEqual(ta, tb)
        self.assertIn("Current local date and time", tb)
        self.assertNotIn("Current local date and time", b)
        self.assertIn("Available tools", a)
        self.assertNotIn("fact 2", b, "what it remembers this turn goes in this turn's part")

    def test_each_turn_rereads_only_the_newest_exchange(self):
        history, last, old_layout = [], None, None
        rereads, old_rereads = [], []
        for n in range(1, 11):
            history.append({"role": "user", "content": f"message number {n}, about something that happened today " * 3})
            steady, this_turn, layout = self.turn(n, history)
            text = render(layout)
            # the old layout: the time (to the microsecond) right after the rules, then the tools, notes and the conversation
            time_line, notes = this_turn.split("\n\n", 1)
            before = steady.replace(prompts.ACTION_CONTRACT, prompts.ACTION_CONTRACT + "\n\n" + time_line + f":{n:02d}.{n:06d}", 1)
            whole = render([{"role": "system", "content": before + "\n\n" + notes}] + history)
            if last is not None:
                rereads.append(reread(last, text))
                old_rereads.append(reread(old_layout, whole))
            reply = f"reply {n}, a couple of sentences back to them like a friend would say it. " * 2
            last, old_layout = text + reply + "<|im_end|>\n", whole + reply + "<|im_end|>\n"
            history.append({"role": "assistant", "content": reply})
        self.assertLessEqual(max(rereads), min(rereads) * 1.3, f"the same small amount every turn, however long the talk: {rereads}")
        self.assertTrue(all(b > a for a, b in zip(old_rereads, old_rereads[1:])), "before, it grew with every message")
        self.assertGreater(old_rereads[-1], rereads[-1] * 4, (old_rereads[-1], rereads[-1]))

    def test_the_brain_gets_the_new_layout_and_one_system_prompt_if_its_template_refuses(self):
        seen = []

        class Model:
            def tokenize(self, data, add_bos=False):
                return data.split()

            def create_chat_completion(self, **kwargs):
                seen.append(kwargs["messages"])
                if len(seen) == 1 and refuse:
                    raise ValueError("Conversation roles must alternate user/assistant/user/assistant")
                return {"choices": [{"message": {"content": json.dumps({"type": "reply", "text": "hey"})}}]}

        for refuse in (False, True):
            seen.clear()
            with mock.patch.object(inference, "_load_model", return_value=Model()), mock.patch.dict(os.environ, {"LUMA_TIMEZONE": "UTC"}):
                out = inference._plan_here([{"role": "user", "content": "hi"}], [{"text": "likes tea"}], TOOLS, "friend")
            self.assertEqual(out["text"], "hey")
            first = seen[0]
            self.assertEqual([m["role"] for m in first], ["system", "system", "user"], "this turn's notes just before the newest message")
            self.assertIn("Current local date and time", first[1]["content"])
            self.assertRegex(first[1]["content"], r"T\d\d:\d\d(?:[+-]\d\d:\d\d|Z)", "to the minute, no seconds")
            if refuse:
                self.assertEqual([m["role"] for m in seen[1]], ["system", "user"], "the old single prompt when the template won't take two")
                self.assertIn("Current local date and time", seen[1][0]["content"])



class SmallBoardTests(unittest.TestCase):
    def test_the_newest_message_comes_last_so_small_brains_answer_it(self):
        history = [{"role": "user", "content": "ngl today was long"}, {"role": "assistant", "content": "Oof. What happened?"},
                   {"role": "user", "content": "what should i cook tonight?"}]
        layout = inference.turn_layout("steady", "notes", history)
        self.assertEqual(layout[-1], history[-1], "the device lab's 1.7B answered the first message five times with it otherwise")
        self.assertEqual(layout[-2], {"role": "system", "content": "notes"})
        self.assertEqual(layout[:3], [{"role": "system", "content": "steady"}] + history[:2])

    def test_a_budget_device_reads_the_gist_of_each_note(self):
        notes = [{"text": "fact " * 200}, {"text": "another " * 200}, {"text": "third " * 200}, {"mind": True, "text": "mood " * 300},
                 {"humor": True, "text": "joke back " * 300}, {"guess": True, "text": "they might want " * 50}, {"skill": True, "text": "skill " * 2000}]
        _, full = prompts.build_plan_parts(notes, {}, "friend", prompts.normalize_profile(None), "now")
        _, small = prompts.build_plan_parts(notes, {}, "friend", prompts.normalize_profile(None), "now", compact=True)
        self.assertLess(len(small), len(full) / 4, (len(small), len(full)))
        self.assertIn("Current local date and time", small)
        self.assertNotIn("third", small, "two facts, not three")
        self.assertNotIn("they might want", small)

    def test_it_reads_the_steady_part_once_at_start_up(self):
        seen = []

        class Model:
            def tokenize(self, data, add_bos=False): return data.split()
            def create_chat_completion(self, **kwargs):
                seen.append(kwargs["messages"])
                return {"choices": [{"message": {"content": json.dumps({"type": "reply", "text": "hey"})}}]}

        with mock.patch.object(inference, "_load_model", return_value=Model()), mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": "budget", "LUMA_TIMEZONE": "UTC"}):
            steady, _ = prompts.build_plan_parts([], {}, "friend", prompts.normalize_profile(None), "", compact=True)
            self.assertEqual(inference.warm(steady), {"warmed": True})
            inference._plan_here([{"role": "user", "content": "hi"}], [], {}, "friend")
        self.assertEqual(seen[0][0], seen[1][0], "the first real turn begins exactly where the warm-up left off")

    def test_qwen3s_small_brains_answer_straight_instead_of_thinking_first(self):
        class Brain:
            chat_handler = None

            def __init__(self, template, fmt="chat_template.default"):
                self.metadata, self.chat_format, self.seen = {"tokenizer.chat_template": template}, fmt, []
                self._chat_handlers = {"chat_template.default": lambda **kw: self.seen.append(kw) or {"choices": []}}

        hybrid = "{%- if enable_thinking is defined and enable_thinking is false %}{{- '<think>\\n\\n</think>\\n\\n' }}{%- endif %}"
        small = inference._answering_straight(Brain(hybrid))
        small.chat_handler(llama=small, messages=[{"role": "user", "content": "hi"}])
        self.assertIs(small.seen[-1]["enable_thinking"], False, "the 0.6B and 1.7B are told to answer straight away")
        instruct = inference._answering_straight(Brain("{{- '<|im_start|>assistant\\n' }}"))
        self.assertIsNone(instruct.chat_handler, "the 4B Instruct never thinks first: left as it is")
        chosen = inference._answering_straight(Brain(hybrid, fmt="chatml"))
        self.assertIsNone(chosen.chat_handler, "a chat format the owner chose is theirs")

    def test_a_quick_side_request_keeps_the_steady_part(self):
        seen, answers = [], []

        class Model:
            def tokenize(self, data, add_bos=False): return data.split()
            def create_chat_completion(self, **kwargs):
                seen.append(kwargs["messages"])
                if answers and answers[0] == "refuse":
                    answers.pop(0)
                    raise ValueError("Conversation roles must alternate user/assistant/user/assistant")
                return {"choices": [{"message": {"content": answers.pop(0) if answers else "Find the cheapest AirPods."}}]}

        with mock.patch.object(inference, "_load_model", return_value=Model()), mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": "budget", "LUMA_TIMEZONE": "UTC"}):
            steady, _ = prompts.build_plan_parts([], {}, "friend", prompts.normalize_profile(None), "", compact=True)
            inference.warm(steady)
            self.assertEqual(inference._rewrite_here("findd cheapest airpods"), "Find the cheapest AirPods.")
            self.assertEqual(seen[-1][0], seen[0][0], "a rewrite starts where the brain already is, so the next reply doesn't read it all again")
            self.assertEqual([m["role"] for m in seen[-1]], ["system", "system", "user"])
            answers.append(json.dumps({"type": "reply", "text": "Text Mom: I'm on my way."}))
            self.assertEqual(inference._rewrite_here("txt mom im omw"), "Text Mom: I'm on my way.", "the reply format answered anyway")
            answers.append("refuse")
            self.assertEqual(inference._rewrite_here("findd cheapest airpods"), "Find the cheapest AirPods.")
            self.assertEqual([m["role"] for m in seen[-1]], ["system", "user"], "its own short instructions when the template takes one")
        with mock.patch.object(inference, "_load_model", return_value=Model()), mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": ""}):
            inference._rewrite_here("findd cheapest airpods")
            self.assertEqual([m["role"] for m in seen[-1]], ["system", "user"], "a fast computer keeps the rewrite short")


class DeviceLabTests(unittest.TestCase):
    """The device lab picks the brain that answers every message in time, not the fastest one that doesn't."""

    def lab(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location("luma_lab", Path(__file__).resolve().parents[1] / "scripts" / "luma_lab.py")
        lab = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lab)
        return lab

    def test_a_reply_that_doesnt_answer_counts_as_missed(self):
        lab = self.lab()
        long_day = "I believe it. Want me to remember today was long, so you can breathe easier tomorrow?"
        self.assertEqual(lab.missed("I lost my train of thought on that one. Say it again?", []), "fell back")
        self.assertEqual(lab.missed("Mmm, I believe it. Want me to remember today was long, so you can breathe easier tomorrow?", [long_day]),
                         "said an earlier reply again", "the device lab's own-brain answer to 'what about dessert'")
        self.assertIsNone(lab.missed("Brownies from a box. Ten minutes, done.", [long_day]))

    def test_the_summary_picks_a_brain_that_answers_everything(self):
        import tempfile
        from pathlib import Path
        lab = self.lab()
        turn = lambda missed=None: {"said": "x", "reply": "y", "first_words": 1.0, "seconds": 2.0, "missed": missed}
        fast = {"brain": "small", "size_gb": 1.1, "first_sound_seconds": 3.0, "answered": 3, "turns": [turn(), turn("fell back"), turn("fell back"), turn(), turn()]}
        good = {"brain": "middle", "size_gb": 2.0, "first_sound_seconds": 3.9, "answered": 5, "turns": [turn()] * 5}
        with tempfile.TemporaryDirectory() as root:
            paths = []
            for row in (fast, good):
                paths.append(Path(root) / f"{row['brain']}.json")
                paths[-1].write_text(json.dumps({"device": row}))
            said = lab.device_summary([str(p) for p in paths])
        self.assertIn("**The device's brain:** middle", said)
        self.assertIn("| 3 of 5 |", said)
        self.assertIn("**(fell back)**", said)


class OneTripTests(unittest.TestCase):
    """On a slow brain (a $250 device's) an everyday question is one trip through the brain, not five."""

    def test_a_budget_device_answers_in_one_trip_unless_the_owner_wants_more(self):
        import tempfile
        from pathlib import Path
        from luma.agent.runtime import Agent
        from luma.llm import brain
        from luma.memory.store import Store
        calls = []
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                store.set_setting("signed_up", True)
                agent = Agent(store=store, use_model=True)
                brain.init(store)
                fake = lambda self, m, c, allowed, ev, profile=None, tier=None: calls.append(1) or {"type": "reply", "text": "Pasta, easy and quick."}
                with mock.patch.object(Agent, "call_planner", fake):
                    counts = {}
                    for tier in ("", "budget"):
                        with mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": tier}):
                            n = len(calls)
                            agent.chat("what should i cook tonight? something easy")
                            counts[tier] = len(calls) - n
                    self.assertGreater(counts[""], 1, "a fast computer still thinks first and takes a second look")
                    self.assertEqual(counts["budget"], 1)
                    with mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": "budget"}):
                        self.assertFalse(agent.status()["think_first"], "the app shows what's really happening")
                        store.set_setting("think_first", True)
                        n = len(calls)
                        agent.chat("what should i cook tonight? something easy")
                        self.assertEqual(len(calls) - n, 2, "they switched think-first on themselves")
                        with mock.patch.object(brain, "cloud_on", return_value=True):
                            self.assertFalse(brain.slow_here(), "the cloud brain thinks fast")
            finally:
                store.close()

    def test_a_brain_timed_slow_here_counts_as_slow(self):
        from luma.llm import brain
        store = types.SimpleNamespace(setting=lambda k, d=None: {"brain_speed": {"fast": [9.0, 10.0, 11.0]}}.get(k, d))
        with mock.patch.object(brain, "_store", store), mock.patch.object(brain, "cloud_on", return_value=False), \
                mock.patch.object(brain, "inference_model_is_big", return_value=False), mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": ""}):
            self.assertTrue(brain.slow_here())
        store = types.SimpleNamespace(setting=lambda k, d=None: {"brain_speed": {"fast": [40.0, 42.0]}}.get(k, d))
        with mock.patch.object(brain, "_store", store), mock.patch.object(brain, "cloud_on", return_value=False), \
                mock.patch.object(brain, "inference_model_is_big", return_value=False), mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": ""}):
            self.assertFalse(brain.slow_here())

if __name__ == "__main__":
    unittest.main()
