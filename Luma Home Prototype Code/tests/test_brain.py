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


class FakeAnthropic(http.server.BaseHTTPRequestHandler):
    seen = []
    reply = {"type": "reply", "text": "Booked it in my head: Tuesday at 3. Want me to put it on your calendar?"}
    status = 200

    def log_message(self, *a): pass

    def do_GET(self):
        if self.path.startswith("/v1/models/"):
            if self.headers.get("x-api-key") != "sk-ant-good":
                return self._json({"type": "error", "error": {"type": "authentication_error", "message": "invalid x-api-key"}}, 401)
            return self._json({"type": "model", "id": self.path.rsplit("/", 1)[1], "display_name": "Claude", "created_at": "2026-01-01T00:00:00Z"})
        self._json({}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeAnthropic.seen.append({"body": body, "beta": self.headers.get("anthropic-beta"), "key": self.headers.get("x-api-key")})
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
