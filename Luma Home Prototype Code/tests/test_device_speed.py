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

    def test_a_budget_device_keeps_whats_steady_out_of_each_turn(self):
        notes = [{"mind": True, "text": "Your mood right now: warm and easygoing."},
                 {"self": True, "text": "Your evolving sense of yourself and this friendship (private, you wrote it): I'm Luma, still getting to know them."}]
        chat, chat_turn = prompts.build_plan_parts(notes, {}, "friend", prompts.normalize_profile(None), "now", compact=True)
        job, job_turn = prompts.build_plan_parts(notes, TOOLS, "friend", prompts.normalize_profile(None), "now", compact=True)
        self.assertEqual(chat, job, "the tools that fit change with the message, so they come after the talk, not in the steady part")
        self.assertIn("reminder.create", job_turn)
        self.assertIn("Tools this turn: none", chat_turn)
        self.assertIn("still getting to know them", chat, "who Luma has become changes when it reflects, not every turn")
        self.assertNotIn("still getting to know them", chat_turn)
        self.assertIn("warm and easygoing", chat_turn)
        self.assertNotIn("Saved background facts", chat_turn, "no facts, no line about them")
        full, full_turn = prompts.build_plan_parts(notes, TOOLS, "friend", prompts.normalize_profile(None), "now")
        self.assertIn("Available tools", full, "a computer reads fast: its steady part keeps the tools")
        self.assertIn("still getting to know them", full_turn)

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
        self.assertEqual(lab.missed("Okay.", [], "honestly i think i need a vacation"), "brushed them off", "Luma's own small brain, run 9")
        self.assertEqual(lab.missed("What's your go-to dessert?", [long_day], "lol okay and what about dessert"), "brushed them off")
        self.assertIsNone(lab.missed("Ice cream, or a cookie with a side of milk. Pick one.", [long_day], "lol okay and what about dessert"))

    def test_it_notices_a_brain_that_keeps_saying_the_same_thing(self):
        lab = self.lab()
        said = lab.repeats_itself(["Ngl, a gift? Maybe a nice snack. Let me know what you think!",
                                   "Ngl, yeah. Maybe take a day off. Let me know what you think!",
                                   "Ngl, dessert? Maybe some cookies."])
        self.assertIn("“let me know what you think” in 2 replies", said, "the device lab's 1.7B, run 4")
        self.assertIn("starts 3 replies with “ngl”", said)
        self.assertEqual(lab.repeats_itself(["Spaghetti, easy and quick.", "Ice cream in a bowl, no toppings.", "A good book she'd actually read."]), [])

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
        self.assertIn("within 4 seconds of you stopping:** middle", said)
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

    def test_a_time_on_its_own_isnt_a_job_on_a_slow_brain(self):
        import tempfile
        from pathlib import Path
        from luma.agent.runtime import Agent
        from luma.llm import brain
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                store.set_setting("signed_up", True)
                agent = Agent(store=store, use_model=True)
                brain.init(store)
                with mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": "budget"}):
                    self.assertFalse(agent._worth_understanding("ngl today was long, work was a lot"), "a rewrite costs a $250 device seconds")
                    self.assertFalse(agent._worth_understanding("what should i cook tonight? something easy"))
                    self.assertTrue(agent._worth_understanding("shceudle me an emial tmrw 9am saying call the bank"))
                with mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": ""}):
                    self.assertTrue(agent._worth_understanding("what should i cook tonight? something easy"), "a fast computer still takes the look")
                    fake = lambda self, m, c, allowed, ev, profile=None, tier=None: {"type": "reply", "text": "Pasta, easy and quick."}
                    handed_back = "ASK: What should I cook tonight, and what's a simple recipe?"
                    with mock.patch.object(Agent, "call_planner", fake), mock.patch.object(Agent, "understand", return_value=handed_back):
                        out = agent.chat("what should i cook tonight? something easy")
                    self.assertIn("Pasta", out["text"], "the device lab's 1.7B handed their own question back as a clarifying one")
            finally:
                store.close()

    def test_two_replies_in_a_row_that_sound_the_same_get_a_nudge(self):
        import tempfile
        from pathlib import Path
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                from luma.agent.workflows import observation
                agent = Agent(store=store, use_model=False)
                # history keeps Luma's replies as its own JSON notes, the way a real turn leaves them
                agent.history = [{"role": "user", "content": "lol okay and what about dessert"},
                                 {"role": "assistant", "content": observation({"text": "Ngl, dessert? Maybe some cookies. Let me know what you think!"})},
                                 {"role": "user", "content": "my sister's birthday is next week"},
                                 {"role": "assistant", "content": observation({"text": "Ngl, a gift? Maybe a nice snack. Let me know what you think!"})}]
                note = agent._fresh_note()
                self.assertIn("don't start with “Ngl” again", note, "the device lab's 1.7B, run 4")
                self.assertIn("“Let me know what you think!”", note)
                self.assertTrue(any(n.get("text") == note for n in agent._mind_context("honestly i think i need a vacation")))
                self.assertNotIn("text", note.split(":")[1][:20], "not the JSON's own keys")
                agent.history[-1]["content"] = observation({"text": "A good book she'd actually read."})
                self.assertIsNone(agent._fresh_note())
            finally:
                store.close()

    def _talk(self, store):
        from luma.agent.runtime import Agent
        from luma.agent.workflows import observation
        agent = Agent(store=store, use_model=True)
        # a turn talks in its chat's own history (threads), so the earlier exchange goes there
        agent.threads["main"] = agent.history = [{"role": "user", "content": "what should i cook tonight? something easy"},
                                                 {"role": "assistant", "content": observation({"text": "Nah, something easy. Maybe a stir-fry or a pasta? You got the ingredients?"})}]
        return agent

    def test_an_earlier_reply_said_again_is_tried_once_more_not_said(self):
        import tempfile
        from pathlib import Path
        from luma.llm import brain
        from luma.memory.store import Store
        stuck = {"type": "reply", "text": "Nah, something easy. Maybe a stir-fry or a pasta? You got the ingredients?"}
        fresh = {"type": "reply", "text": "Brownies from a box. Ten minutes and you're done."}
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                store.set_setting("signed_up", True)
                brain.init(store)
                agent = self._talk(store)
                seen = []
                answers = [stuck, fresh]
                with mock.patch.object(brain, "plan", side_effect=lambda m, c, *a, **k: seen.append(c) or answers.pop(0)), \
                        mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": "budget"}):
                    out = agent.chat("lol okay and what about dessert")
                self.assertEqual(out["text"], fresh["text"], "the device lab's 1.7B gave its cooking reply to four new messages")
                self.assertEqual(len(seen), 2)
                self.assertTrue(any("You already said this" in n.get("text", "") for n in seen[1]), "the second try is told what it said")
                self.assertFalse(any("You already said this" in n.get("text", "") for n in seen[0]))
                answers[:] = [stuck]
                agent2 = self._talk(store)
                with mock.patch.object(brain, "plan", side_effect=lambda *a, **k: answers.pop(0)), mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": "budget"}):
                    self.assertEqual(agent2.chat("wait what did you say?")["text"], stuck["text"], "asked to say it again, the same words are right")
            finally:
                store.close()

    def test_the_voice_never_starts_saying_an_earlier_reply(self):
        import tempfile
        from pathlib import Path
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                agent = self._talk(store)
                agent._turn_text = "lol okay and what about dessert"
                spoken = []
                feed = agent._unless_said_before(spoken.append)
                for piece in ["Nah, ", "something easy. ", "Maybe a stir-fry", " or a pasta?"]:
                    feed(piece)
                self.assertEqual(spoken, [], "the same opening and the same first sentence: nothing is said")
                self.assertTrue(agent._streamed["blocked"])
                feed = agent._unless_said_before(spoken.append)
                for piece in ["Nah, ", "something sweet. ", "Brownies?"]:
                    feed(piece)
                feed.flush()
                self.assertEqual("".join(spoken), "Something sweet. Brownies?",
                                 "same opening, new sentence: said, without the “Nah,” the last reply opened with too")
                spoken.clear()
                feed = agent._unless_said_before(spoken.append)
                feed("Brownies ")
                feed("from a box. ")
                self.assertEqual("".join(spoken), "Brownies from a box. ", "a new reply streams as soon as its first words differ")
                feed("You got the ingredients?")
                feed.flush()
                self.assertEqual("".join(spoken), "Brownies from a box. ", "but not the closing line the last reply used")
            finally:
                store.close()

    def test_tics_are_left_off(self):
        import tempfile
        from pathlib import Path
        from luma.agent.workflows import observation
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                agent = self._talk(store)
                agent.threads["main"][:] = [{"role": "user", "content": "ngl today was long"},
                                            {"role": "assistant", "content": observation({"text": "Ngl, yeah, work was a lot. Let me know what you think!"})},
                                            {"role": "user", "content": "what should i cook"},
                                            {"role": "assistant", "content": observation({"text": "Ngl, easy? A stir-fry. Let me know what you think!"})}]
                self.assertEqual(agent._without_tics("Ngl, maybe a smoothie or some cookies? Let me know what you think!"),
                                 "Maybe a smoothie or some cookies?", "the device lab's 1.7B, run 6")
                self.assertEqual(agent._without_tics("Ngl."), "Ngl.", "a reply that's only the word stays")
                self.assertEqual(agent._without_tics("Brownies. Let me know if you want a recipe!"), "Brownies. Let me know if you want a recipe!")
                agent._asked_again = True
                self.assertEqual(agent._without_tics("Ngl, easy? A stir-fry. Let me know what you think!"),
                                 "Ngl, easy? A stir-fry. Let me know what you think!", "asked to say it again: as it was")
                agent._asked_again = False
                self.assertTrue(agent._mostly("Nah, you should cook something easy that you can eat. Like, something that takes 10 minutes or less.",
                                              "Nah, you should cook something easy that you can eat. Like, something that takes 10 minutes or less. "
                                              "Maybe a stir-fry, or some pasta. You know, the kind of thing that doesn't require too much prep time."),
                                "a shorter copy of an earlier reply is a copy (run 6)")
                self.assertFalse(agent._mostly("Ngl, yeah. You need a vacation. You got this! 😊",
                                               "Ngl, yeah. Work's been a beast this week. But hey, you got this! Let me know if you need anything, "
                                               "even just a coffee break or a chat. You're not alone, ya know? 😊"),
                                 "a short answer sharing “you”, “need” and “got” isn't a copy (run 7)")
            finally:
                store.close()

    def test_a_tic_doesnt_come_back_every_other_reply(self):
        import tempfile
        from pathlib import Path
        from luma.agent.workflows import observation
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                agent = self._talk(store)
                said = agent._without_tics("Ngl, easy? Maybe a salad or some chicken nuggets. You got this! 😊")
                agent.threads["main"] += [{"role": "assistant", "content": observation({"text": said})}, {"role": "user", "content": "and dessert"}]
                self.assertEqual(agent._without_tics("Ngl, maybe a cookie or some chocolate? You got this! 😊"), "Maybe a cookie or some chocolate?",
                                 "the brain's own “Ngl,” and “You got this! 😊” are remembered though the text kept neither (run 7)")
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
