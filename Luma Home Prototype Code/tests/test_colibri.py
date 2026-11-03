"""The huge brain: colibri runs a model of hundreds of billions of parameters on a big Mac and Luma talks to it over
its local OpenAI-compatible address. Heavy work goes there, replies stream as they're written, and if it can't
answer the next brain does, that turn, without the person noticing."""
import http.server
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from luma.llm import brain, colibri, inference
from luma.memory.store import Store


class FakeColibri(http.server.BaseHTTPRequestHandler):
    seen = []
    reply = {"type": "reply", "text": "Here's the plan, step by step: research Monday, outline Tuesday, draft by Thursday."}

    def log_message(self, *a): pass

    def do_GET(self):
        if self.path == "/v1/models":
            return self._json({"object": "list", "data": [{"id": "glm-5.2-colibri", "object": "model"}]})
        self._json({}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeColibri.seen.append(body)
        text = json.dumps(FakeColibri.reply) if body.get("response_format") else "Plan the week."
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for i in range(0, len(text), 7):
            chunk = {"choices": [{"index": 0, "delta": {"content": text[i:i + 7]}}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")

    def _json(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class HugeBrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeColibri)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.env = mock.patch.dict(os.environ, {"LUMA_COLIBRI_BASE": f"http://127.0.0.1:{self.server.server_port}/v1",
                                                "LUMA_COLIBRI_DIR": str(Path(self.temp.name) / "colibri")})
        self.env.start()
        colibri.forget()
        FakeColibri.seen.clear()
        brain.init(self.store)
        self.local = mock.patch.object(inference, "plan", return_value={"type": "reply", "text": "the fast brain"})
        self.local.start()

    def tearDown(self):
        self.local.stop()
        self.env.stop()
        colibri.forget()
        self.store.close()
        self.temp.cleanup()

    def test_it_streams_a_reply_in_lumas_shape(self):
        self.assertEqual(colibri.ready(), "glm-5.2-colibri")
        heard = []
        result = colibri.plan([{"role": "user", "content": "plan my research project"}], [], {}, "friend", on_text=heard.append)
        self.assertEqual(result, FakeColibri.reply)
        self.assertEqual("".join(heard), FakeColibri.reply["text"], "the words arrive as they're written")
        sent = FakeColibri.seen[-1]
        self.assertTrue(sent["stream"])
        self.assertEqual(sent["model"], "glm-5.2-colibri")
        self.assertEqual(sent["messages"][0]["role"], "system")

    def test_heavy_work_goes_to_the_huge_brain_and_chat_stays_fast(self):
        convo = [{"role": "user", "content": "write up the research plan"}]
        self.assertEqual(brain.plan(convo, [], {}, "friend", tier="heavy")["text"], "the fast brain", "off until the owner turns it on")
        self.store.set_setting("brain_huge", True)
        self.assertEqual(brain.plan(convo, [], {}, "friend", tier="heavy"), FakeColibri.reply)
        self.assertEqual(brain.plan(convo, [], {}, "friend")["text"], "the fast brain", "ordinary replies keep the fast brain")
        self.assertEqual(brain.plan(convo, [], {}, "friend", tier="light")["text"], "the fast brain")
        self.store.set_setting("brain_huge_chat", True)
        self.assertEqual(brain.plan(convo, [], {}, "friend"), FakeColibri.reply, "unless the owner wants to talk with it")
        self.assertEqual(brain.plan(convo, [], {}, "friend", tier="light")["text"], "the fast brain", "quick reads never wait on it")

    def test_when_it_cant_answer_the_fast_brain_does(self):
        self.store.set_setting("brain_huge", True)
        self.assertTrue(brain.huge_on())
        with mock.patch.object(colibri, "_post", side_effect=colibri.NotRunning("stopped")):
            out = brain.plan([{"role": "user", "content": "plan it"}], [], {}, "friend", tier="heavy")
        self.assertEqual(out["text"], "the fast brain")
        self.assertIn("huge brain couldn't answer", self.store.setting("brain_huge_error"))
        with mock.patch.dict(os.environ, {"LUMA_COLIBRI_BASE": "http://127.0.0.1:9/v1"}):
            colibri.forget()
            self.assertIsNone(colibri.ready())
            self.assertFalse(brain.huge_on())
            self.assertEqual(brain.plan([{"role": "user", "content": "plan it"}], [], {}, "friend", tier="heavy")["text"], "the fast brain")

    def test_which_model_for_which_mac(self):
        self.assertEqual(colibri.pick_model(512, 900), "glm-5.2", "a Mac Studio with the memory holds all 744B at once")
        self.assertIsNone(colibri.pick_model(512, 200), "not enough disk for the download: colibri's own pick")
        self.assertIsNone(colibri.pick_model(128, 900), "colibri recommends what runs well on this machine")

    def test_status_says_what_colibri_says(self):
        state = brain.status()["huge"]
        self.assertFalse(state["installed"])
        self.assertTrue(state["running"], "something is answering on its address")
        coli = Path(os.environ["LUMA_COLIBRI_DIR"]) / "c" / "coli"
        coli.parent.mkdir(parents=True)
        coli.write_text("import json, sys\n"
                        "if sys.argv[1:] == ['status', '--json']:\n"
                        "    print(json.dumps({'server': {'state': 'ready', 'model_id': 'glm-5.2-colibri', 'tokens_per_second': 1.9,\n"
                        "        'urls': {'openai_base_url': 'http://127.0.0.1:8001/v1'}}}))\n")
        self.assertTrue(colibri.installed())
        self.assertEqual(colibri.server_status(), {"state": "ready", "base": "http://127.0.0.1:8001/v1", "model": "glm-5.2-colibri", "tok_s": 1.9})


if __name__ == "__main__":
    unittest.main()
