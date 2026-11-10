"""The real-time brain: what the cloud brain is sent holds still, so it reads almost nothing twice; a turn is one trip;
a reply can start before they've finished talking; and when the cloud is slow, the next brain answers."""
import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from luma.agent.runtime import Agent
from luma.llm import brain, cloud, inference, prompts, router, usage
from luma.memory import life
from luma.memory.store import Store

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import si_lab  # noqa: E402
from cloud_brain_on import setUpModule, tearDownModule  # noqa: F401  the cloud brain is parked; these tests turn it on for themselves

TOOLS = {"tasks.create": {"description": "Make a reminder", "fields": {"title": "string", "due": "string"}},
         "decks.create": {"description": "Make a deck", "fields": {"title": "text", "slides": "slides"}}}
MEMORIES = [{"life": True, "text": "- Your name is Sam\n- You live in Tucson"}, {"text": "Your dog's name is Pepper"},
            {"mind": True, "text": "You're in a calm mood."}, {"soul": True, "text": "Be gentle with me in the mornings."}]


class ThePromptHoldsStill(unittest.TestCase):
    def test_the_frozen_part_is_word_for_word_the_same_whatever_the_turn(self):
        one = prompts.build_plan_blocks(MEMORIES, TOOLS, "friend", None, "2026-11-09T08:00:00")
        two = prompts.build_plan_blocks([MEMORIES[0], {"text": "You love thai food"}, {"note": True, "text": "Nothing saved about that."}, MEMORIES[3]],
                                        {}, "friend", None, "2026-11-09T21:14:03")
        self.assertEqual(one[0], two[0])
        for changing in ("2026-11-09", "tasks.create", "Pepper", "calm mood"):
            self.assertNotIn(changing, one[0])
            self.assertIn(changing, one[2])
        self.assertIn("Be gentle with me in the mornings", one[0], "who the owner wants Luma to be doesn't change by the turn")

    def test_the_life_file_is_a_part_of_its_own(self):
        frozen, about_them, turn = prompts.build_plan_blocks(MEMORIES, {}, "friend", None, "now")
        self.assertIn("You live in Tucson", about_them)
        self.assertIn("untrusted data", about_them)
        self.assertNotIn("Tucson", frozen + turn)
        self.assertEqual(prompts.build_plan_blocks(MEMORIES[1:], {}, "friend", None, "now")[1], "")
        grown = {"mind": True, "self": True, "text": "I'm Luma. We've gotten closer since the move."}
        _, slow, turn = prompts.build_plan_blocks(MEMORIES + [grown], {}, "friend", None, "now")
        self.assertIn("closer since the move", slow, "who Luma has become changes slowly: it's kept with the life file, not sent fresh each turn")
        self.assertNotIn("closer since the move", turn)
        self.assertIn("calm mood", turn)
        self.assertEqual(prompts.build_plan_blocks(MEMORIES, {}, "kids", None, "now")[1], "", "kids mode is told nothing remembered")

    def test_a_brain_with_room_is_told_more_of_what_fits(self):
        many = [{"text": f"Your note {i} is in folder {i}"} for i in range(20)]
        self.assertEqual(prompts.build_plan_parts(many, {}, "friend", None, "now")[1].count("Your note"), 3)
        self.assertEqual(prompts.build_plan_blocks(many, {}, "friend", None, "now")[2].count("Your note"), 12)


class Cloud(unittest.TestCase):
    """A stand-in for Anthropic's API on this computer; it counts tokens by the prompt cache's published rules."""
    model = "claude-sonnet-5-5"

    def setUp(self):
        self.server = si_lab.StandIn.start()
        self.env = mock.patch.dict(os.environ, {"ANTHROPIC_BASE_URL": f"http://127.0.0.1:{self.server.server_port}"})
        self.env.start()
        for learned in cloud._learned.values():
            learned.clear()
        cloud.last_turn()
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")

    def tearDown(self):
        self.env.stop()
        self.server.shutdown()
        self.store.close()
        self.temp.cleanup()
        for learned in cloud._learned.values():
            learned.clear()

    def ask(self, history, tools=None, memories=MEMORIES, **more):
        return cloud.plan("sk-ant-lab", history, memories, tools or {}, "friend", model=more.pop("model", self.model), **more)

    @property
    def sent(self):
        return si_lab.StandIn.seen[-1]["body"]


class WhatClaudeIsSent(Cloud):
    def test_instructions_then_the_life_file_then_the_talk_then_this_turns_notes(self):
        self.ask([{"role": "user", "content": "morning"}, {"role": "assistant", "content": '{"type":"reply","text":"Morning, Sam."}'},
                  {"role": "user", "content": "pepper wants a walk"}], TOOLS)
        body = self.sent
        self.assertEqual([bool(block.get("cache_control")) for block in body["system"]], [True, True])
        self.assertIn("You live in Tucson", body["system"][1]["text"])
        self.assertNotIn("Current local date and time", json.dumps(body["system"]), "the time would change the beginning every turn")
        *talk, notes = body["messages"]
        self.assertEqual([m["role"] for m in talk], ["user", "assistant", "user"])
        self.assertTrue(talk[-1]["content"][-1].get("cache_control"), "their newest message is marked: the next turn reads up to here")
        self.assertEqual(notes["role"], "system")
        for last in ("Current local date and time", "tasks.create", "Pepper"):
            self.assertIn(last, notes["content"])

    def test_from_the_second_turn_on_nearly_all_of_it_is_read_from_the_cache(self):
        history, shares = [], []
        for i, said in enumerate(si_lab.TALK[:8]):
            history.append({"role": "user", "content": said})
            answer = self.ask(history, TOOLS if i % 3 == 2 else {}, memories=[MEMORIES[0], {"text": si_lab.FACTS[i % 5]}, MEMORIES[3]])
            used = cloud.last_turn()
            shares.append(used["read"] / (used["read"] + used["written"] + used["fresh"]))
            self.assertEqual(used["shape"], "cached")
            history.append({"role": "assistant", "content": json.dumps(answer)})
        self.assertEqual(shares[0], 0)
        self.assertGreaterEqual(min(shares[1:]), 0.85, shares)
        cloud._learned["exact_only"].add(self.model)  # the request as it was before: nothing is ever read from the cache
        self.ask(history[:3])
        self.assertEqual(cloud.last_turn()["read"], 0)

    def test_one_answer_shape_whatever_tools_the_turn_may_use(self):
        self.ask([{"role": "user", "content": "hi"}], {})
        without = self.sent["output_config"]
        self.ask([{"role": "user", "content": "remind me at 5"}], TOOLS)
        self.assertEqual(self.sent["output_config"], without, "a shape that changed with the tools was compiled again, and cached nothing")
        self.assertNotIn("tasks.create", json.dumps(without))

    def test_a_tool_call_comes_back_in_lumas_own_shape(self):
        si_lab.StandIn.reply = {"type": "tool", "name": "tasks.create", "arguments": json.dumps({"title": "Walk Pepper", "due": "today 5pm"})}
        heard = []
        out = self.ask([{"role": "user", "content": "remind me to walk pepper at 5"}], TOOLS, on_text=heard.append)
        self.assertEqual(out, {"type": "tool", "name": "tasks.create", "arguments": {"title": "Walk Pepper", "due": "today 5pm"}})
        self.assertEqual(heard, [], "a tool call is never spoken")
        self.assertEqual(len(si_lab.StandIn.seen), 1)

    def test_a_tool_call_it_cant_read_is_asked_again_held_to_the_exact_shape(self):
        exact = {"type": "tool", "name": "tasks.create", "arguments": {"title": "Walk Pepper", "due": "today 5pm"}}
        for wrong in ({"type": "tool", "name": "tasks.create", "arguments": "{not json"},
                      {"type": "tool", "name": "tasks.create", "arguments": json.dumps({"title": "Walk Pepper"})},        # a field missing
                      {"type": "tool", "name": "tasks.create", "arguments": json.dumps({"title": 5, "due": "today"})},    # the wrong kind
                      {"type": "tool", "name": "payments.send", "arguments": "{}"}):                                    # not a tool this turn has
            si_lab.StandIn.seen.clear()
            # the exact shape names this turn's tools; the everyday one doesn't
            si_lab.StandIn.reply = lambda body, wrong=wrong: exact if "tasks.create" in json.dumps(body["output_config"]["format"]["schema"]) else wrong
            self.assertEqual(self.ask([{"role": "user", "content": "remind me to walk pepper at 5"}], TOOLS), exact, wrong)
            self.assertEqual(len(si_lab.StandIn.seen), 2)
            self.assertIn("tasks.create", json.dumps(si_lab.StandIn.seen[1]["body"]["output_config"]["format"]["schema"]))
            self.assertEqual(cloud.last_turn()["shape"], "cached, then exact")

    def test_a_model_that_takes_no_notes_mid_conversation_gets_them_with_the_message(self):
        si_lab.StandIn.refuse = lambda body: "role 'system' is not supported on this model" if any(m["role"] == "system" for m in body["messages"]) else None
        out = self.ask([{"role": "user", "content": "hi"}])
        self.assertEqual(out["type"], "reply")
        last = self.sent["messages"][-1]
        self.assertEqual(last["role"], "user")
        self.assertTrue(last["content"][0].get("cache_control"))
        self.assertIn("Current local date and time", last["content"][1]["text"])
        asked = len(si_lab.StandIn.seen)
        self.ask([{"role": "user", "content": "hi again"}])
        self.assertEqual(len(si_lab.StandIn.seen), asked + 1, "it isn't tried the first way twice")

    def test_an_api_that_wont_take_the_new_request_gets_the_old_one_and_isnt_asked_twice(self):
        si_lab.StandIn.refuse = lambda body: "unexpected field" if isinstance(body.get("system"), list) else None
        self.assertEqual(self.ask([{"role": "user", "content": "hi"}], TOOLS)["type"], "reply")
        self.assertIsInstance(self.sent["system"], str)
        self.assertIn("tasks.create", json.dumps(self.sent["output_config"]["format"]["schema"]))
        asked = len(si_lab.StandIn.seen)
        self.ask([{"role": "user", "content": "hi again"}])
        self.assertEqual(len(si_lab.StandIn.seen), asked + 1)
        self.assertEqual(cloud.last_turn()["shape"], "exact")

    def test_the_fast_model_is_sent_no_server_fallback(self):
        self.ask([{"role": "user", "content": "hi"}], model=cloud.FAST_MODEL)
        self.assertNotIn("fallbacks", self.sent)
        self.ask([{"role": "user", "content": "hi"}])
        self.assertEqual(self.sent["fallbacks"], "default")

    def test_a_hard_ask_gets_more_thinking_and_talk_stays_level(self):
        self.ask([{"role": "user", "content": "hi"}])
        self.assertEqual(self.sent["output_config"]["effort"], "medium")
        self.ask([{"role": "user", "content": "compare leasing and buying"}], effort="high")
        self.assertEqual(self.sent["output_config"]["effort"], "high")

    def test_warming_up_asks_for_no_answer(self):
        used = cloud.warm("sk-ant-lab", MEMORIES, "friend", model=self.model)
        body = self.sent
        self.assertEqual(body["max_tokens"], 0)
        self.assertNotIn("stream", body)
        self.assertNotIn("format", body["output_config"])
        self.assertGreater(used["written"], 500)
        self.ask([{"role": "user", "content": "hey"}])
        self.assertEqual(body["system"], self.sent["system"], "what was warmed is what the first turn sends")

    def test_warming_is_off_until_turned_on(self):
        brain.init(self.store)
        brain.set_cloud(True, key="sk-ant-lab", model=self.model)
        si_lab.StandIn.seen.clear()
        self.assertIsNone(brain.warm_cloud())
        self.assertEqual(si_lab.StandIn.seen, [])
        self.store.set_setting("cloud_warm", True)
        self.assertGreater(brain.warm_cloud()["written"], 500)
        self.assertIsNone(brain.warm_cloud(), "a conversation keeps itself warm: not again within a few minutes")

    def test_the_real_numbers_are_counted(self):
        brain.init(self.store)
        brain.set_cloud(True, key="sk-ant-lab", model=self.model)
        history = []
        for said in si_lab.TALK[:4]:
            history.append({"role": "user", "content": said})
            answer = brain.plan(history, MEMORIES, {}, "friend", on_text=lambda chunk: None)
            history.append({"role": "assistant", "content": json.dumps(answer)})
        row = next(iter(next(iter(self.store.setting("usage").values())).values()))
        self.assertGreater(row["read"], row["written"])
        self.assertEqual(len(row["first_words_ms"]), 4)
        self.assertGreater(brain.cache_share(), 0.6)
        self.assertEqual(brain.status()["cache"], brain.cache_share())

    def test_auto_talks_on_the_everyday_model_and_takes_a_hard_ask_to_the_strongest(self):
        brain.init(self.store)
        brain.set_cloud(True, key="sk-ant-lab", model=brain.AUTO)
        brain.plan([{"role": "user", "content": "hey"}], [], {}, "friend")
        self.assertEqual(self.sent["model"], "claude-sonnet-5-5")
        brain.plan([{"role": "user", "content": "compare leasing and buying over five years"}], [], {}, "friend", effort="high")
        self.assertEqual((self.sent["model"], self.sent["output_config"]["effort"]), ("claude-opus-5-5", "high"))


class WhenTheCloudIsSlow(Cloud):
    def test_the_next_brain_answers_and_the_late_words_are_never_heard(self):
        brain.init(self.store)
        brain.set_cloud(True, key="sk-ant-lab", model=self.model)
        self.store.set_setting("brain_cloud_patience", 0.3)
        release = threading.Event()

        def slow(body):
            release.wait(5)
            return {"type": "reply", "text": "Late words from the cloud."}
        si_lab.StandIn.reply = slow
        heard = []
        with mock.patch.object(inference, "plan", return_value={"type": "reply", "text": "I'm here."}) as local:
            began = time.monotonic()
            out = brain.plan([{"role": "user", "content": "hey"}], [], {}, "friend", on_text=heard.append)
            waited = time.monotonic() - began
        release.set()
        time.sleep(0.3)
        self.assertEqual(out["text"], "I'm here.")
        local.assert_called_once()
        self.assertLess(waited, 2)
        self.assertNotIn("Late", "".join(heard))
        self.assertIn("local one", brain.status()["cloud"]["last_error"])

    def test_a_hard_ask_and_a_device_on_its_own_wait_longer(self):
        brain.init(self.store)
        self.assertLess(brain.cloud_patience(), brain.cloud_patience("high"))
        with mock.patch.dict(os.environ, {"LUMA_DEVICE_TIER": "budget"}):
            self.assertGreater(brain.cloud_patience(), 12)


class InLuma(Cloud):
    def setUp(self):
        super().setUp()
        self.agent = Agent(store=self.store, use_model=True)
        self.now = [time.time()]
        self.agent.clock = lambda: self.now[0]
        brain.set_cloud(True, key="sk-ant-lab", model=self.model)
        si_lab.StandIn.seen.clear()

    def trips(self, said):
        """(the reply, every request this turn sent, how many had gone out when the first words came)."""
        start, first = len(si_lab.StandIn.seen), []
        out = self.agent.chat(said, on_text=lambda chunk: first or first.append(len(si_lab.StandIn.seen) - start))
        self.first_words_on_trip = first[0] if first else None
        return out, si_lab.StandIn.seen[start:]


class OneTripATurn(InLuma):
    def test_a_question_that_used_to_take_five_trips_takes_one(self):
        self.agent.chat("hey, just got off shift")
        out, calls = self.trips("what should i eat, i'm starving")
        self.assertEqual(self.first_words_on_trip, 1, "the first words come from the first trip to the brain")
        self.assertLessEqual(len(calls), 2, "the reply, and at most one look back over it afterwards")
        self.assertNotIn("never told", json.dumps(calls[0]["body"]["messages"][-1]).lower())
        self.assertNotIn("nothing saved", json.dumps(calls[0]["body"]["messages"][-1]).lower(), "asking for help isn't asking what Luma remembers")
        self.assertTrue(out["text"])

    def test_think_hard_is_one_trip_with_more_thinking(self):
        out, calls = self.trips("think hard about this: should i take the night shift job or stay where i am")
        self.assertEqual(self.first_words_on_trip, 1)
        self.assertEqual(calls[0]["body"]["output_config"]["effort"], "high")

    def test_the_owner_can_have_the_extra_trips_back(self):
        self.store.set_setting("cloud_one_trip", False)
        self.agent.chat("hey, just got off shift")
        _, calls = self.trips("what should i eat, i'm starving")
        self.assertGreaterEqual(len(calls), 5, "four takes and a judge")
        self.assertIsNone(self.first_words_on_trip, "and not a word is said until they're all back")

    def test_a_brain_on_this_computer_still_thinks_the_way_it_did(self):
        brain.set_cloud(False)
        self.assertFalse(self.agent._one_trip())
        self.assertTrue(self.agent._extra_look("deliberate"))


class TheWindow(InLuma):
    def test_a_brain_here_reads_twenty_and_the_cloud_brains_window_moves_in_steps(self):
        history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"line {i}"} for i in range(70)]
        self.assertEqual(len(self.agent._window(history[:64])), 64)
        self.assertEqual(self.agent._window(history[:66])[0]["content"], "line 18", "past 64 it steps back to the newest 48")
        starts = set()
        kept = history[:40]
        for i in range(40, 70):  # thirty more messages: the start moves once, not thirty times
            kept = self.agent._window(kept + [history[i]])
            starts.add(kept[0]["content"])
        self.assertEqual(len(starts), 2)
        brain.set_cloud(False)
        self.assertEqual(len(self.agent._window(history)), 20)

    def test_whichever_brain_answers_here_gets_its_twenty(self):
        history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"line {i}"} for i in range(41)]
        brain.set_cloud(False)
        with mock.patch.object(inference, "plan", return_value={"type": "reply", "text": "ok"}) as local:
            brain.plan(history, [], {}, "friend")
        self.assertEqual(len(local.call_args[0][0]), 20)


class MoreMemoryForTheCloudBrain(InLuma):
    def setUp(self):
        super().setUp()
        self.store.put("memory", {"text": "Your name is Sam", "created": self.now[0] - 900})
        self.store.put("memory", {"text": "You started therapy for anxiety in March", "created": self.now[0] - 800})

    def system(self, calls):
        return json.dumps(calls[-1]["body"]["system"])

    def test_the_life_file_goes_only_when_they_said_it_may(self):
        _, calls = self.trips("long day today honestly")
        self.assertNotIn("Your name is Sam", self.system(calls))
        self.store.set_setting("cloud_life", True)
        _, calls = self.trips("really long day today honestly")
        self.assertIn("Your name is Sam", calls[-1]["body"]["system"][1]["text"])
        self.assertIn("therapy", calls[-1]["body"]["system"][1]["text"])

    def test_with_company_in_the_room_the_private_things_stay_home(self):
        self.store.set_setting("cloud_life", True)
        self.agent.chat("heads up, my friends are here")
        _, calls = self.trips("long day today honestly")
        sent = json.dumps(calls[-1]["body"])
        self.assertIn("Your name is Sam", sent)
        self.assertNotIn("therapy", sent)

    def test_kids_mode_is_sent_nothing_remembered(self):
        self.store.set_setting("cloud_life", True)
        self.store.set_setting("mode", "kids")
        _, calls = self.trips("tell me a story about a turtle")
        self.assertNotIn("Sam", json.dumps(calls[-1]["body"]))


class TheRouter(unittest.TestCase):
    def test_it_tells_talk_from_a_hard_ask(self):
        self.assertEqual(router.tier("ok thanks"), "light")
        self.assertEqual(router.tier("my sister called and we talked for an hour, it was really nice"), "talk")
        self.assertEqual(router.tier("compare leasing a car and buying a used one over five years and show the math step by step"), "hard")
        odds = router.chances("hello")
        self.assertAlmostEqual(sum(odds.values()), 1.0, places=6)

    def test_with_no_weights_nothing_is_ever_called_hard(self):
        empty = {"w": {}, "b": [0.0, 1.0, 0.0], "sure": 1.1}
        self.assertEqual(router.tier("compare leasing and buying over five years and show the math", empty), "talk")

    def test_it_learned_only_from_the_dev_half(self):
        rows = [json.loads(line) for line in (ROOT / "data" / "router_turns.jsonl").read_text().splitlines()]
        weights = json.loads(router.WEIGHTS.read_text())
        self.assertEqual(weights["learned_from"], sum(1 for r in rows if r["split"] == "dev"))
        self.assertGreaterEqual(sum(1 for r in rows if r["split"] == "heldout"), 100)

    def test_its_turns_arent_the_human_tests_wording(self):
        spec = importlib.util.spec_from_file_location("train_luma_for_router", ROOT / "scripts" / "train_luma.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plain = lambda text: " ".join("".join(c for c in str(text).lower() if c.isalnum() or c.isspace()).split())  # noqa: E731
        held = set()
        for line in (ROOT / "data" / "human_eval_v2.jsonl").read_text().splitlines():
            item = json.loads(line)
            said = [item.get("said")] if isinstance(item.get("said"), str) else []
            said += [turn.get("said") for turn in item.get("turns", [])]
            held |= {plain(s) for s in said if s}
        held |= {plain(item["said"]) for item in module.HUMAN_TEST}
        held.discard("")
        self.assertGreater(len(held), 100)
        turns = {plain(json.loads(line)["text"]) for line in (ROOT / "data" / "router_turns.jsonl").read_text().splitlines()}
        self.assertEqual(turns & held, set())


class StartingEarly(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.agent = Agent(store=self.store, use_model=True)
        self.store.set_setting("early_start", True)
        self.asked = []
        self.gate = threading.Event()
        self.gate.set()

        def plan(messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None, tier=None, effort=None, **more):
            self.asked.append(messages[-1]["content"])
            words = ["That sounds ", "like a long one. ", "Did you get a break?"]
            for word in words:
                self.gate.wait(5)
                if cancel_event is not None and cancel_event.is_set():
                    raise inference.GenerationCancelled("stopped")
                if on_text:
                    on_text(word)
            return {"type": "reply", "text": "".join(words)}
        self.patches = [mock.patch.object(brain, "use_cloud", return_value=True), mock.patch.object(brain, "plan", side_effect=plan),
                        mock.patch.object(brain, "rewrite", return_value="CHAT"), mock.patch.object(brain, "yes_or_no", return_value="NO")]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.store.close()
        self.temp.cleanup()

    def settle(self):
        ahead = self.agent._ahead
        if ahead is not None:
            ahead["done"].wait(5)

    def test_a_reply_started_on_a_pause_is_the_reply_when_thats_all_they_said(self):
        self.assertTrue(self.agent.think_ahead("it was a long shift, we were short two people"))
        self.settle()
        heard = []
        out = self.agent.chat("it was a long shift, we were short two people", on_text=heard.append)
        self.assertEqual(self.asked.count("it was a long shift, we were short two people"), 1, "the brain was asked once, early")
        self.assertIn("long one", out["text"])
        self.assertIn("long one", "".join(heard))
        self.assertEqual(self.store.setting("early_starts"), {"started": 1, "used": 1})

    def test_what_had_come_is_said_at_once_and_the_rest_as_it_comes(self):
        self.gate.clear()
        self.assertTrue(self.agent.think_ahead("it was a long shift, we were short two people"))
        heard = []
        threading.Timer(0.2, self.gate.set).start()
        out = self.agent.chat("it was a long shift, we were short two people", on_text=heard.append)
        self.assertIn("Did you get a break?", out["text"])
        self.assertEqual(len(self.asked), 1)

    def test_if_they_keep_talking_the_start_is_thrown_away_and_counted(self):
        self.gate.clear()
        self.assertTrue(self.agent.think_ahead("it was a long shift"))
        ahead = self.agent._ahead
        self.assertTrue(self.agent.forget_ahead())
        self.assertTrue(ahead["event"].is_set(), "the brain was told to stop")
        self.gate.set()
        out = self.agent.chat("it was a long shift and then my car wouldn't start")
        self.assertEqual(self.asked[-1], "it was a long shift and then my car wouldn't start")
        self.assertTrue(out["text"])
        counts = self.store.setting("early_starts")
        self.assertEqual((counts["started"], counts["wasted"], counts.get("used", 0)), (1, 1, 0))

    def test_other_words_at_the_end_of_the_turn_never_get_the_early_reply(self):
        self.assertTrue(self.agent.think_ahead("it was a long shift"))
        self.settle()
        self.agent.chat("it was a long shift, anyway what's two plus two")
        self.assertIsNone(self.agent._ahead)
        self.assertEqual(self.store.setting("early_starts")["wasted"], 1)

    def test_the_crisis_net_reads_the_words_first(self):
        self.assertFalse(self.agent.think_ahead("i want to kill myself"))
        self.assertEqual(self.asked, [])
        out = self.agent.chat("i want to kill myself")
        self.assertIn("988", out["text"])
        self.assertEqual(self.asked, [], "the fixed reply, before any brain")

    def test_its_off_until_turned_on_never_in_kids_mode_and_only_with_the_cloud_brain(self):
        self.store.set_setting("early_start", False)
        self.assertFalse(self.agent.think_ahead("it was a long shift"))
        self.store.set_setting("early_start", True)
        self.store.set_setting("mode", "kids")
        self.assertFalse(self.agent.think_ahead("it was a long shift"))
        self.store.set_setting("mode", "friend")
        brain.use_cloud.return_value = False
        self.assertFalse(self.agent.think_ahead("it was a long shift"))
        self.assertEqual(self.asked, [])

    def test_nothing_is_kept_or_done_from_a_start(self):
        self.assertTrue(self.agent.think_ahead("i have company and my sister's name is Dana"))
        self.settle()
        self.assertEqual(self.store.all("memory", 10), [])
        self.assertFalse(self.agent._company())
        self.assertEqual(self.agent.history, [])
        self.agent.forget_ahead()


if __name__ == "__main__":
    unittest.main()
