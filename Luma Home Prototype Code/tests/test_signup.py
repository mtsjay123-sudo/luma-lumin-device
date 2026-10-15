"""Everyone signs up once: name, birthday (and their sign), how to reach them, their people and favorites.
All of it becomes memories they can see on the first day."""
import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from luma.agent import presence
from luma.agent.runtime import Agent
from luma.control.server import make_server
from luma.memory.store import Store

NOW = 1791900000.0  # Tue 13 Oct 2026

FORM = {"first": "Maya", "last": "Rivers", "dob": "1998-06-02", "email": "maya@example.com", "phone": "+19195550123",
        "relationship": "dating", "partner": {"name": "Jay", "relation": "boyfriend", "birthday": "09-17"},
        "people": [{"name": "Lena", "relation": "Mom", "birthday": "03-08"}],
        "work": "a nurse at Duke", "home": "Raleigh", "music": "SZA and old R&B", "food": "tacos",
        "interests": ["Fashion", "Fitness"], "goals": "run a half marathon"}


class SignupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.agent = Agent(store=self.store, use_model=False, now=lambda: NOW)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def memories(self):
        return [m["text"] for m in self.store.all("memory", 200)]

    def test_zodiac_edges(self):
        z = Agent.zodiac
        self.assertEqual(z(6, 2), "Gemini")
        self.assertEqual(z(5, 20), "Taurus")
        self.assertEqual(z(5, 21), "Gemini")
        self.assertEqual(z(1, 1), "Capricorn")
        self.assertEqual(z(1, 20), "Aquarius")
        self.assertEqual(z(12, 21), "Sagittarius")
        self.assertEqual(z(12, 22), "Capricorn")
        self.assertEqual(z(3, 20), "Pisces")
        self.assertEqual(z(10, 23), "Scorpio")

    def test_signup_becomes_memories_right_away(self):
        self.assertFalse(self.agent.signup_status()["done"])
        result = self.agent.complete_signup(FORM)
        self.assertEqual(result["sign"], "Gemini")
        texts = self.memories()
        for line in ["Your name is Maya Rivers", "You're a Gemini, born June 2, 1998", "You're dating Jay", "Lena is your mom",
                     "You work as a nurse at Duke", "You live in Raleigh", "Your favorite food is tacos", "Your goal: run a half marathon",
                     "Your birthday is June 2", "Jay's birthday is September 17", "Lena's birthday is March 8"]:
            self.assertIn(line, texts)
        self.assertNotIn("Jay is your boyfriend", texts)  # "You're dating Jay" says it already
        self.assertEqual(self.agent.signup_status(), {"done": True, "first": "Maya", "sign": "Gemini"})
        self.assertEqual(self.agent.about["people"][0]["name"], "Jay")
        whose = {b["whose"] for b in presence.birthdays(self.store.all("memory", 200), presence.date(2026, 10, 13))}
        self.assertIn("your", whose)  # "Your birthday is June 2" still reads as theirs

    def test_signing_up_again_replaces_not_doubles(self):
        self.agent.complete_signup(FORM)
        self.agent.complete_signup({**FORM, "home": "Durham"})
        texts = self.memories()
        self.assertIn("You live in Durham", texts)
        self.assertNotIn("You live in Raleigh", texts)
        self.assertEqual(texts.count("Your name is Maya Rivers"), 1)

    def test_bad_forms_are_refused_plainly(self):
        for change, words in [({"first": ""}, "first name"), ({"dob": "2020-01-01"}, "under 13"), ({"dob": "June 2"}, "date of birth"),
                              ({"email": "maya@"}, "email"), ({"phone": "555"}, "phone")]:
            with self.assertRaises(ValueError) as caught:
                self.agent.complete_signup({**FORM, **change})
            self.assertIn(words, str(caught.exception))
        self.assertFalse(self.agent.signup_status()["done"])


class SignupServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name)
        self.store = Store(path / "state.db", path / "key")
        self.agent = Agent(store=self.store, use_model=False)
        self.server = make_server(self.agent, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.client.open(self.base + "/desktop/").read()

    def tearDown(self):
        self.server.control_context.stop.set()
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.temp.cleanup()

    def post(self, path, body):
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Origin": self.base, "Content-Type": "application/json"})
        with self.client.open(request) as r:
            return json.load(r)

    def test_home_says_whether_to_show_signup_and_the_form_saves(self):
        with self.client.open(self.base + "/api/home") as r:
            self.assertFalse(json.load(r)["signup"]["done"])
        with self.assertRaises(urllib.error.HTTPError) as bad:
            self.post("/api/signup", {**FORM, "email": "nope"})
        self.assertEqual(bad.exception.code, 400)
        saved = self.post("/api/signup", FORM)
        self.assertEqual(saved["sign"], "Gemini")
        self.assertGreaterEqual(len(saved["memories"]), 10)
        with self.client.open(self.base + "/api/home") as r:
            self.assertTrue(json.load(r)["signup"]["done"])


if __name__ == "__main__":
    unittest.main()
