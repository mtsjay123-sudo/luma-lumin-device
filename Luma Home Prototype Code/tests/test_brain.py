"""Luma's brain: the cloud brain (Claude, with the owner's own key) answers in Luma's own shape, falls back to the
local one when it can't, and the bigger local model is picked to fit the computer."""
import http.server
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from luma.llm import brain, cloud, inference
from luma.memory.store import Store
from cloud_brain_on import setUpModule, tearDownModule  # noqa: F401  the cloud brain is parked; these tests turn it on for themselves


class FakeAnthropic(http.server.BaseHTTPRequestHandler):
    seen = []
    reply = {"type": "reply", "text": "Booked it in my head: Tuesday at 3. Want me to put it on your calendar?"}
    status = 200

    def log_message(self, *a): pass

    def _key(self):
        """The key the request carries: newer versions of the SDK send it as a bearer token."""
        bearer = self.headers.get("authorization") or ""
        return self.headers.get("x-api-key") or (bearer[7:] if bearer.lower().startswith("bearer ") else "")

    def do_GET(self):
        if self.path.startswith("/v1/models/"):
            if self._key() != "sk-ant-good":
                return self._json({"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key"}}, 401)
            return self._json({"type": "model", "id": self.path.rsplit("/", 1)[1], "display_name": "Claude", "created_at": "2026-01-01T00:00:00Z"})
        self._json({}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeAnthropic.seen.append({"body": body, "beta": self.headers.get("anthropic-beta"), "key": self._key()})
        if FakeAnthropic.status != 200:
            return self._json({"type": "error", "error": {"type": "overloaded_error", "message": "busy"}}, FakeAnthropic.status)
        text = json.dumps(FakeAnthropic.reply)
        message = {"id": "msg_1", "type": "message", "role": "assistant", "model": body["model"], "content": [],
                   "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 0}}
        if not body.get("stream"):
            return self._json({**message, "content": [{"type": "text", "text": text}], "stop_reason": "end_turn"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        events = [("message_start", {"type": "message_start", "message": message}),
                  ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}})]
        events += [("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[i:i + 9]}}) for i in range(0, len(text), 9)]
        events += [("content_block_stop", {"type": "content_block_stop", "index": 0}),
                   ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": 30}}),
                   ("message_stop", {"type": "message_stop"})]
        for name, data in events:
            self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode())
            self.wfile.flush()

    def _json(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


TOOLS = {"tasks.create": {"description": "Make a reminder", "fields": {"title": "string", "due": "string"}},
         "decks.create": {"description": "Make a deck", "fields": {"title": "text", "slides": "slides"}}}


class CloudBrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeAnthropic)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.env = mock.patch.dict(os.environ, {"ANTHROPIC_BASE_URL": f"http://127.0.0.1:{self.server.server_port}"})
        self.env.start()
        FakeAnthropic.seen.clear()
        FakeAnthropic.status = 200
        brain.init(self.store)

    def tearDown(self):
        self.env.stop()
        self.store.close()
        self.temp.cleanup()

    def test_turning_it_on_checks_the_key(self):
        with self.assertRaises(ValueError):
            brain.set_cloud(True, key="not-a-key")
        with self.assertRaises(ValueError):
            brain.set_cloud(True, key="sk-ant-bad")
        self.assertFalse(brain.cloud_on())
        state = brain.set_cloud(True, key="sk-ant-good")
        self.assertTrue(state["cloud"]["on"])
        self.assertEqual(state["thinking_with"], "Claude Opus 5.5 (smartest)")
        self.assertNotIn("sk-ant-good", json.dumps(state))  # the key never goes back to the page

    def test_cloud_answers_in_lumas_shape_and_streams_the_words(self):
        brain.set_cloud(True, key="sk-ant-good")
        heard = []
        result = brain.plan([{"role": "assistant", "content": "hi"}, {"role": "user", "content": "remind me tuesday at 3"}], [], TOOLS, "friend", on_text=heard.append)
        self.assertEqual(result, FakeAnthropic.reply)
        self.assertIn("Tuesday at 3", "".join(heard))
        sent = FakeAnthropic.seen[-1]
        body = sent["body"]
        self.assertEqual(body["model"], "claude-opus-5-5")
        self.assertEqual(body["fallbacks"], "default")
        self.assertIn("server-side-fallback-2026-07-01", sent["beta"])
        self.assertEqual(body["messages"][0]["role"], "user")  # history starts on the owner's turn
        schema = json.dumps(body["output_config"]["format"]["schema"])
        self.assertIn("anyOf", schema)
        self.assertNotIn("oneOf", schema)
        self.assertNotIn("minItems", schema)
        self.assertNotIn("maxItems", schema)

    def test_falls_back_to_the_local_brain_when_the_cloud_cant(self):
        brain.set_cloud(True, key="sk-ant-good")
        FakeAnthropic.status = 529
        with mock.patch.object(inference, "plan", return_value={"type": "reply", "text": "local"}) as local:
            result = brain.plan([{"role": "user", "content": "hey"}], [], {}, "friend")
        self.assertEqual(result["text"], "local")
        local.assert_called_once()
        self.assertIn("local one", brain.status()["cloud"]["last_error"])

    def test_off_means_nothing_leaves_this_computer(self):
        brain.set_cloud(True, key="sk-ant-good")
        brain.set_cloud(False)
        FakeAnthropic.seen.clear()
        with mock.patch.object(inference, "plan", return_value={"type": "reply", "text": "local"}):
            brain.plan([{"role": "user", "content": "hey"}], [], {}, "friend")
        self.assertEqual(FakeAnthropic.seen, [])

    def test_quick_rewrite_uses_the_cloud_too(self):
        brain.set_cloud(True, key="sk-ant-good")
        FakeAnthropic.reply = {"type": "reply", "text": "x"}
        self.assertIn('"reply"', brain.rewrite("sched email to sam 3pm"))
        self.assertEqual(FakeAnthropic.seen[-1]["body"]["output_config"]["effort"], "low")
        FakeAnthropic.reply = CloudBrainTests_reply


CloudBrainTests_reply = FakeAnthropic.reply


class FakeMoonshot(http.server.BaseHTTPRequestHandler):
    """Moonshot's OpenAI-style API: /v1/models and /v1/chat/completions."""
    seen = []
    status = 200
    content = '```json\n{"type": "reply", "text": "Bet, Tuesday at 3. Want it on your calendar?"}\n```'

    def log_message(self, *a): pass

    def _authed(self):
        return self.headers.get("Authorization") == "Bearer sk-moon-good"

    def do_GET(self):
        if self.path == "/v1/models":
            return self._json({"data": [{"id": "kimi-k3.1-pro"}]} if self._authed() else {"error": {"message": "Invalid Authentication"}}, 200 if self._authed() else 401)
        self._json({}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeMoonshot.seen.append(body)
        if not self._authed():
            return self._json({"error": {"message": "Invalid Authentication"}}, 401)
        if FakeMoonshot.status != 200:
            return self._json({"error": {"message": "rate limited"}}, FakeMoonshot.status)
        self._json({"id": "x", "object": "chat.completion", "model": body["model"],
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": FakeMoonshot.content}, "finish_reason": "stop"}]})

    def _json(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class KimiBrainTests(unittest.TestCase):
    """Kimi K3.1 Pro: the open model too big for a Mac, as a cloud brain on the owner's own Moonshot key."""
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeMoonshot)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.env = mock.patch.dict(os.environ, {"LUMA_KIMI_BASE": f"http://127.0.0.1:{self.server.server_port}/v1"})
        self.env.start()
        FakeMoonshot.seen.clear()
        FakeMoonshot.status = 200
        brain.init(self.store)

    def tearDown(self):
        self.env.stop()
        self.store.close()
        self.temp.cleanup()

    def test_turning_it_on_checks_the_moonshot_key(self):
        with self.assertRaises(ValueError):
            brain.set_cloud(True, key="sk-ant-good", model="kimi-k3.1-pro")  # an Anthropic key isn't a Moonshot key
        with self.assertRaises(ValueError):
            brain.set_cloud(True, key="sk-moon-bad", model="kimi-k3.1-pro")
        state = brain.set_cloud(True, key="sk-moon-good", model="kimi-k3.1-pro")
        self.assertTrue(state["cloud"]["on"])
        self.assertEqual(state["cloud"]["provider"], "kimi")
        self.assertIn("Kimi K3.1 Pro", state["thinking_with"])
        self.assertEqual(state["cloud"]["keys"], {"anthropic": False, "kimi": True})
        self.assertNotIn("sk-moon-good", json.dumps(state))

    def test_answers_in_lumas_shape(self):
        brain.set_cloud(True, key="sk-moon-good", model="kimi-k3.1-pro")
        heard = []
        result = brain.plan([{"role": "assistant", "content": "hi"}, {"role": "user", "content": "remind me tuesday at 3"}], [], TOOLS, "friend", on_text=heard.append)
        self.assertEqual(result, {"type": "reply", "text": "Bet, Tuesday at 3. Want it on your calendar?"})  # out of its code fence
        self.assertIn("Tuesday at 3", "".join(heard))
        body = FakeMoonshot.seen[-1]
        self.assertEqual(body["model"], "kimi-k3.1-pro")
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertEqual(body["messages"][1], {"role": "user", "content": "remind me tuesday at 3"})  # history starts on the owner's turn

    def test_falls_back_to_the_local_brain(self):
        brain.set_cloud(True, key="sk-moon-good", model="kimi-k3.1-pro")
        FakeMoonshot.status = 429
        with mock.patch.object(inference, "plan", return_value={"type": "reply", "text": "local"}) as local:
            result = brain.plan([{"role": "user", "content": "hey"}], [], {}, "friend")
        self.assertEqual(result["text"], "local")
        local.assert_called_once()
        self.assertIn("busy or out of credit", brain.status()["cloud"]["last_error"])

    def test_each_companys_key_is_kept_apart(self):
        brain.set_cloud(True, key="sk-moon-good", model="kimi-k3.1-pro")
        self.store.set_setting("brain_cloud_key", "sk-ant-other")
        self.assertEqual(brain.cloud_key(), "sk-moon-good")
        brain.forget_key()
        self.assertFalse(brain.cloud_on())
        self.assertEqual(self.store.setting("brain_cloud_key"), "sk-ant-other")  # forgetting Kimi's key leaves Claude's

    def test_photos_dont_go_to_kimi(self):
        from luma.agent.runtime import Agent
        brain.set_cloud(True, key="sk-moon-good", model="kimi-k3.1-pro")
        agent = Agent(store=self.store, use_model=False)
        with mock.patch.object(cloud, "look") as look:
            agent.see(b"\x89PNG\r\n\x1a\n" + b"0" * 100, "what's this")
        look.assert_not_called()


class BiggerLocalBrainTests(unittest.TestCase):
    FILES = [{"path": "Qwen_Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf", "size": 18_600_000_000},
             {"path": "Qwen_Qwen3-30B-A3B-Instruct-2507-IQ4_XS.gguf", "size": 16_400_000_000},
             {"path": "Qwen_Qwen3-30B-A3B-Instruct-2507-Q3_K_M.gguf", "size": 14_700_000_000},
             {"path": "Qwen_Qwen3-30B-A3B-Instruct-2507-IQ3_XS.gguf", "size": 12_600_000_000}]

    def test_picks_the_best_that_fits(self):
        self.assertIn("Q4_K_M", brain.pick(self.FILES, 64)["path"])
        self.assertIn("IQ4_XS", brain.pick(self.FILES, 32)["path"])
        self.assertIn("IQ3_XS", brain.pick(self.FILES, 24)["path"])
        self.assertIsNone(brain.pick(self.FILES, 16))

    def test_a_mac_studio_gets_the_biggest_brain_that_fits_in_all_its_pieces(self):
        G = 2 ** 30
        files = [{"path": f"UD-Q4_K_XL/Qwen3.5-397B-A17B-UD-Q4_K_XL-0000{i}-of-00005.gguf", "size": (20 if i == 5 else 50) * G} for i in range(1, 6)]
        files += [{"path": f"Q3_K_M/Qwen3.5-397B-A17B-Q3_K_M-0000{i}-of-00004.gguf", "size": (40 if i == 4 else 45) * G} for i in range(1, 5)]
        files.append({"path": "mmproj-F16.gguf", "size": G})
        best = brain.pick_parts(files, 512)
        self.assertEqual(len(best), 5)
        self.assertTrue(all("UD-Q4_K_XL" in f["path"] for f in best))
        self.assertTrue(all("Q3_K_M" in f["path"] for f in brain.pick_parts(files, 256)))
        self.assertIsNone(brain.pick_parts(files, 128))
        self.assertEqual(brain.big_label(Path("/m/Qwen3.5-397B-A17B-UD-Q4_K_XL-00001-of-00005.gguf")), "Qwen3.5 397B")

    def test_a_64_gb_mac_gets_qwen36_when_its_engine_can_run_it(self):
        files = [{"path": f"Qwen3.6-35B-A3B-{q}.gguf", "size": int(gb * 1e9)}
                 for q, gb in [("Q8_0", 37.2), ("Q6_K", 28.9), ("Q5_K_M", 24.9), ("Q4_K_M", 21.4), ("IQ4_XS", 18.9), ("Q3_K_M", 16.9)]]
        files += [{"path": "Qwen3.6-35B-A3B-UD-Q6_K_XL.gguf", "size": int(30e9)}, {"path": "mmproj-F16.gguf", "size": int(0.9e9)}]
        self.assertEqual(brain.pick(files, 64)["path"], "Qwen3.6-35B-A3B-Q6_K.gguf", "the best quality in half of 64 GB")
        self.assertEqual(brain.pick(files, 48)["path"], "Qwen3.6-35B-A3B-Q5_K_M.gguf")
        self.assertEqual(brain.pick(files, 36)["path"], "Qwen3.6-35B-A3B-IQ4_XS.gguf")
        self.assertEqual(brain.pick(files, 32)["path"], "Qwen3.6-35B-A3B-Q3_K_M.gguf")
        with mock.patch.object(brain, "engine", return_value=(0, 3, 36)):
            self.assertEqual(brain.bigger_repos()[0], "unsloth/Qwen3.6-35B-A3B-GGUF")
            self.assertEqual(brain.bigger_name(), "Qwen3.6 35B")
        for old in [(0, 3, 16), ()]:  # an engine that doesn't know Qwen3.5's design, or none at all: the 30B, which always loads
            with mock.patch.object(brain, "engine", return_value=old):
                self.assertTrue(brain.bigger_repos())
                self.assertFalse(any("Qwen3.6" in r for r in brain.bigger_repos()))
                self.assertEqual(brain.bigger_name(), "Qwen3 30B")
        with mock.patch("importlib.metadata.version", return_value="0.3.36"):
            self.assertEqual(brain.engine(), (0, 3, 36))
        self.assertEqual(brain.big_label(Path("/m/Qwen3.6-35B-A3B-Q6_K.gguf")), "Qwen3.6 35B")
        self.assertEqual(brain.big_label(Path("/m/Qwen3-235B-A22B-Instruct-2507-UD-Q3_K_XL-00001-of-00003.gguf")), "Qwen3 235B")
        self.assertEqual(brain.big_label(Path("/m/Qwen_Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf")), "Qwen3 30B")

    def test_a_mac_with_the_30b_can_move_up_to_the_35b(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(brain, "models_dir", return_value=Path(d)), \
                mock.patch.object(brain, "ram_gb", return_value=64), mock.patch.object(brain, "status", return_value={}), \
                mock.patch.object(brain.threading, "Thread") as thread:
            old = Path(d) / "Qwen_Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf"
            old.write_bytes(b"GGUF")
            (Path(d) / (old.name + ".ok")).write_text("x")
            with mock.patch.object(brain, "engine", return_value=(0, 3, 16)):
                brain.fetch_bigger()
                thread.assert_not_called()
            with mock.patch.object(brain, "engine", return_value=(0, 3, 36)):
                brain.fetch_bigger()
                thread.assert_called_once()
            brain.fetching["running"] = False

    def test_a_64_gb_mac_can_hold_a_122b_brain_at_three_bits(self):
        files = [{"path": f"Qwen3.5-122B-A10B-{q}.gguf", "size": int(gb * 1e9)} for q, gb in
                 [("UD-Q4_K_XL", 75.0), ("UD-Q3_K_XL", 58.0), ("UD-IQ3_XXS", 44.7), ("UD-Q2_K_XL", 47.0), ("UD-IQ2_M", 39.1), ("UD-IQ2_XXS", 36.6)]]
        self.assertEqual([f["path"] for f in brain.pick_parts(files, 64)], ["Qwen3.5-122B-A10B-UD-IQ3_XXS.gguf"])
        self.assertIsNone(brain.pick_parts(files, 48), "not on 48 GB: it wouldn't leave the Mac room to breathe")
        with mock.patch.object(brain, "engine", return_value=(0, 3, 36)):
            self.assertEqual(brain.studio_name(64), "Qwen3.5 122B")
            self.assertEqual(brain.studio_name(128), "Qwen3 235B")
            self.assertIsNone(brain.studio_name(48))
        with mock.patch.object(brain, "engine", return_value=(0, 3, 16)):
            self.assertIsNone(brain.studio_name(64), "an engine too old for Qwen3.5's design isn't offered it")
            self.assertEqual(brain.studio_name(128), "Qwen3 235B")
        self.assertEqual(brain.big_label(Path("/m/Qwen3.5-122B-A10B-UD-IQ3_XXS.gguf")), "Qwen3.5 122B")

    def test_a_brain_too_slow_to_talk_steps_down_to_the_next_one_not_the_small_one(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            for name in ("Qwen3.5-122B-A10B-UD-IQ3_XXS.gguf", "Qwen3.6-35B-A3B-Q6_K.gguf"):
                (folder / name).write_bytes(b"GGUF")
                (folder / (name + ".ok")).write_text("x")
            store = Store(folder / "s.db", folder / "k")
            try:
                with mock.patch.object(brain, "models_dir", return_value=folder), mock.patch.object(brain, "_store", store), \
                        mock.patch.object(brain, "inference_model_is_big", return_value=True), mock.patch.object(brain, "_apply_local"):
                    self.assertIn("122B", brain.big_model_path(skip=brain._slow()).name, "the big one first")
                    for _ in range(brain.SPEED_SAMPLES):
                        brain.note_speed(40, 10.0)  # 4 words a second: too slow to talk with
                    self.assertEqual(store.setting("brain_local", "auto"), "auto")
                    self.assertIn("35B-A3B", brain.big_model_path(skip=brain._slow()).name)
                    self.assertIn("switched to Qwen3.6 35B", store.setting("brain_note"))
                    for _ in range(brain.SPEED_SAMPLES):
                        brain.note_speed(40, 10.0)
                    self.assertEqual(store.setting("brain_local"), "auto_fast", "nothing smaller left but the fast one")
                    brain.use_small(False)
                    self.assertIn("122B", brain.big_model_path(skip=brain._slow()).name, "choosing the bigger brain again starts over")
            finally:
                store.close()

    def test_small_computers_are_pointed_at_the_cloud_brain(self):
        with mock.patch.object(brain, "ram_gb", return_value=16):
            with self.assertRaisesRegex(ValueError, "cloud brain"):
                brain.fetch_bigger()

    def test_switching_models_reloads_on_the_next_message(self):
        sentinel = object()
        with mock.patch.object(inference, "_llm", sentinel), mock.patch.object(inference, "_llm_path", Path("/small.gguf")):
            inference.use_model_path(Path("/big.gguf"))
            self.assertIsNone(inference._llm)
        inference.use_model_path(None)


if __name__ == "__main__":
    unittest.main()
