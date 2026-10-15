"""What the best agents do, done here: an editable soul and memory, a grill-me interview, a 30-minute
heartbeat that only speaks up when something's new, and podcast episodes in Luma's own voice."""
import json
import tempfile
import unittest
import urllib.request
import threading
import wave
from pathlib import Path
from unittest import mock

from luma.agent.runtime import Agent
from luma.control.server import make_server
from luma.llm.prompts import build_plan_prompt
from luma.memory.store import Store


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.now = 1791900000.0
        self.agent = Agent(store=self.store, use_model=False, now=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()


class SoulTests(Base):
    def test_the_soul_reaches_the_brain(self):
        self.store.set_setting("soul", "Talk to me like a sharp older sister. No fluff.")
        context = self.agent._mind_context("hey")
        prompt = build_plan_prompt(context, {})
        self.assertIn("sharp older sister", prompt)
        self.assertIn("can't override the rules", prompt)

    def test_who_luma_has_become_reaches_the_brain_too(self):
        self.store.set_setting("self_model", "I've learned I'm at my best when I'm blunt.")
        prompt = build_plan_prompt(self.agent._mind_context("hey"), {})
        self.assertIn("at my best when I'm blunt", prompt)

    def test_kids_never_get_the_adult_soul(self):
        self.store.set_setting("soul", "Swear a lot.")
        self.agent.set_mode("kids")
        self.assertFalse(any(m.get("soul") for m in self.agent._mind_context("hi")))


class IdentityServerTests(Base):
    def setUp(self):
        super().setUp()
        self.server = make_server(self.agent, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        self.opener.open(self.base + "/desktop/").read()

    def tearDown(self):
        self.server.control_context.stop.set()
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def post(self, path, data):
        req = urllib.request.Request(self.base + path, data=json.dumps(data).encode(), headers={"Origin": self.base, "Content-Type": "application/json"})
        return json.loads(self.opener.open(req).read())

    def test_edit_the_soul_and_add_a_memory(self):
        out = self.post("/api/identity", {"soul": "Be my hype man."})
        self.assertEqual(out["identity"]["soul"], "Be my hype man.")
        added = self.post("/api/memory/add", {"text": "My mom's name is Denise."})
        self.assertEqual(self.store.get("memory", added["memory"]["id"])["text"], "My mom's name is Denise.")
        home = json.loads(self.opener.open(self.base + "/api/home").read())
        self.assertEqual(home["identity"]["soul"], "Be my hype man.")
        self.store.set_setting("self_model", "something")
        self.post("/api/identity", {"reset_self": True})
        self.assertIsNone(self.store.setting("self_model"))


class GrillMeTests(Base):
    def test_one_question_at_a_time_and_every_answer_is_kept(self):
        first = self.agent.chat("grill me about my product launch")
        self.assertTrue(first.get("asked"))
        self.assertIn("your product launch", first["text"])
        self.assertNotIn("my product launch", first["text"])
        second = self.agent.chat("It's a meal-prep app for busy nurses.")
        self.assertTrue(second["text"].endswith("?"))
        self.assertNotEqual(second["text"], first["text"].split("\n")[-1])
        self.agent.chat("skip")
        saved = [m for m in self.store.all("memory", 50) if m.get("source") == "grill"]
        self.assertEqual(len(saved), 1)
        self.assertIn("meal-prep app for busy nurses", saved[0]["text"])
        done = self.agent.chat("stop")
        self.assertIn("saved 1 thing", done["text"])
        self.assertIsNone(self.store.setting("grilling"))

    def test_a_real_request_mid_interview_still_works(self):
        self.agent.chat("interview me")
        reply = self.agent.chat("remind me in 20 minutes to call mom")
        self.assertIsNone(self.store.setting("grilling"))
        self.assertTrue(any(t["title"] == "call mom" for t in self.store.all("task", 10)), reply)

    def test_never_keeps_card_numbers(self):
        self.agent.chat("grill me")
        with self.assertRaises(ValueError):  # Luma refuses to keep the message at all
            self.agent.chat("my card is 4111 1111 1111 1111")
        self.assertFalse([m for m in self.store.all("memory", 50) if "4111" in m["text"]])


class HeartbeatTests(Base):
    def test_speaks_up_once_about_what_is_coming_due(self):
        self.agent.helpers.ensure_system()
        beat = next(r for r in self.store.all("helper", 60) if r["kind"] == "heartbeat")
        self.assertEqual(beat["every"], "every_30m")
        self.store.put("task", {"title": "Call the dentist", "due": self.now + 600, "done": False, "notified": False, "mode": "friend"})
        first = self.agent.helpers.run(beat["id"])
        self.assertIn("Call the dentist", first["card"]["body"])
        second = self.agent.helpers.run(beat["id"])
        self.assertIsNone(second.get("card"))  # already told them


class PodcastTests(Base):
    def test_an_episode_in_lumas_voice(self):
        def fake_synthesize(text, out, voice="luma", **kw):
            with wave.open(out, "w") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b"\0\0" * 24000 * 95)
        with mock.patch("luma.audio.tts.synthesize", fake_synthesize), \
             mock.patch.object(self.agent, "news_feed", return_value={"items": [{"source": "BBC", "title": "Rates held steady", "url": "u"}]}):
            reply = self.agent.chat("make me a morning podcast")
        self.assertEqual(reply["file"]["kind"], "podcast")
        self.assertEqual(reply["file"]["seconds"], 95)
        self.assertIn("BBC: Rates held steady", reply["file"]["script"])
        self.assertIn("1:35", reply.get("text") or reply["summary"])

    def test_without_a_voice_it_still_gives_the_episode(self):
        with mock.patch("luma.audio.tts.synthesize", side_effect=RuntimeError("no kokoro")):
            reply = self.agent.chat("read me the news out loud as a podcast")
        self.assertIn("voice is still downloading", reply["text"])

    def test_talking_about_podcasts_is_just_talk(self):
        self.assertIsNone(self.agent._podcast("what podcasts do you recommend", "what podcasts do you recommend"))


if __name__ == "__main__":
    unittest.main()
