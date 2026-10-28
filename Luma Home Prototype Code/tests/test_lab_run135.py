"""What the real-Mac lab (run 135) caught, fixed: a funny story about a meeting got the calendar, and one that named a stock got
a price check (someone laughing or venting gets a friend, not a tool); the weather went missing when Open-Meteo couldn't be
read (wttr.in stands behind it); a garbled or empty brain reply asked them to say it again (it thinks once more first);
"roast my outfit" got a joke about something else; and the brain kept copying the example from its own humor notes."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from luma.agent import humor, humor_bank
from luma.agent.runtime import Agent, just_talking
from luma.llm import inference
from luma.memory.store import Store

WTTR = {"current_condition": [{"temp_F": "64", "FeelsLikeF": "60", "weatherDesc": [{"value": "Partly cloudy "}]}],
        "nearest_area": [{"areaName": [{"value": "Raleigh"}], "region": [{"value": "North Carolina"}]}],
        "weather": [{"maxtempF": "71", "mintempF": "52", "hourly": [{"chanceofrain": "0", "weatherDesc": [{"value": "Sunny"}]},
                                                                    {"chanceofrain": "10", "weatherDesc": [{"value": "Partly cloudy"}]}]},
                    {"maxtempF": "68", "mintempF": "50", "hourly": [{"chanceofrain": "20", "weatherDesc": [{"value": "Cloudy"}]},
                                                                    {"chanceofrain": "60", "weatherDesc": [{"value": "Light rain"}]}]}]}
PLACES = {"raleigh": {"results": [{"name": "Raleigh", "admin1": "North Carolina", "latitude": 35.78, "longitude": -78.64}]}, "zzyzxqq": {}}


class LabRun135Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def agent(self, planner=None):
        return Agent(store=self.store, use_model=planner is not None, planner=planner)

    def test_a_story_is_not_a_request(self):
        for said in ("lmao my boss scheduled a meeting at 4:59 on a friday", "ugh my boss keeps scheduling meetings at 5",
                     "i'm dead 😂 my coworker bought GAF stock because he thought it was a meme", "my dog died last week"):
            self.assertTrue(just_talking(said), said)
        for said in ("lol remind me to call mom at 5", "lmao what's on my calendar tomorrow", "haha can you check the weather",
                     "ugh, text my sister that i'm running late", "lmao my mom just called, remind me to call her back",
                     "schedule a meeting with sam tomorrow at 3", "what's the weather in raleigh"):
            self.assertFalse(just_talking(said), said)

    def test_a_funny_story_gets_no_tools(self):
        agent = self.agent()
        out = agent.chat("lmao my boss scheduled a meeting at 4:59 on a friday")
        self.assertNotIn("calendar", out["text"].lower())
        self.assertFalse(just_talking("lmao my boss scheduled a meeting at 4:59 on a friday, how much is that worth in overtime"),
                         "a question in the story still gets its look-up")
        allowed = agent.available_tools("lmao my boss scheduled a meeting at 4:59 on a friday")
        self.assertFalse(set(allowed) - {"memory.recall", "memory.remember"}, allowed)

    def test_a_stock_in_a_story_isnt_a_price_check(self):
        agent = self.agent()
        checked = []
        agent.market_fetch = lambda url: checked.append(url) or b"{}"
        out = agent.chat("i'm dead 😂 my coworker bought GAF stock because he thought it was a meme")
        self.assertFalse(checked)
        self.assertNotIn("price", out["text"].lower())
        self.assertTrue(agent.use_markets("how's tesla stock doing today?") or not agent.integration_on("web_search"))

    def test_the_weather_comes_from_wttr_when_open_meteo_is_down(self):
        agent = self.agent()
        asked = []

        def fetch(url):
            asked.append(url)
            if "geocoding-api" in url:
                return json.dumps(PLACES.get(url.split("name=")[1].split("&")[0].lower(), {})).encode()
            if "wttr.in" in url:
                return json.dumps(WTTR).encode()
            raise OSError("open-meteo is down")
        agent.weather_fetch = fetch
        out = agent.chat("what's the weather in raleigh right now?")
        self.assertEqual(out["text"], "Right now in Raleigh it's 64° and partly cloudy (feels like 60°). Today: high of 71°, low of 52°, 10% chance of rain.")
        self.assertEqual(out["results"][0]["source"], "wttr.in")
        self.assertIn("wttr.in/35.78,-78.64?format=j1", asked[-1], "the place Open-Meteo already found")
        self.assertEqual(agent.chat("is it gonna rain tomorrow?")["text"], "Tomorrow in Raleigh: light rain, high of 68°, low of 50°, 60% chance of rain.")
        self.assertIn("couldn't find a place called Zzyzxqq", agent.chat("weather in zzyzxqq")["text"], "a place that isn't there isn't asked about twice")

        def all_down(url):
            asked.append(url)
            if "wttr.in" in url:
                return json.dumps(WTTR).encode()
            raise OSError("offline")
        agent.weather_fetch = all_down
        out = agent.chat("weather in new york")
        self.assertTrue(out["text"].startswith("Right now in New York it's 64°"), out["text"])
        self.assertIn("wttr.in/new+york?format=j1", asked[-1], "no map lookup either: wttr.in finds the place itself")

    def test_wttr_alone_names_the_place_they_said(self):
        from luma.skills import weather
        spot, cast = weather.from_wttr(None, "new york", lambda url: json.dumps(WTTR).encode())
        self.assertEqual(spot["name"], "New York")
        self.assertEqual(cast["now"]["sky"], "partly cloudy")
        spot, cast = weather.from_wttr(None, "nowhere", lambda url: b"{}")
        self.assertIsNone(cast)

    def test_a_garbled_reply_gets_a_second_thought_not_a_retry_request(self):
        def planner(*a, **k):  # the graphics chip garbles; the processor is fine
            return {"type": "reply", "text": "Honestly? The ending was rushed, but the last scene still got me."
                    if os.environ.get("LUMA_GPU_LAYERS") == "0" else "+A57#8++&B"}
        agent = self.agent(planner)
        with mock.patch.dict(os.environ, {"LUMA_GPU_LAYERS": "-1"}), mock.patch.object(inference, "_llm", object()):
            out = agent.chat("did you like the ending of that show my friend told me about")
            self.assertEqual(out["text"], "Honestly? The ending was rushed, but the last scene still got me.")
            self.assertEqual(os.environ["LUMA_GPU_LAYERS"], "0", "and it thinks on the processor from here on")

    def test_an_empty_brain_gets_a_second_thought(self):
        tries = []

        def planner(*a, **k):
            tries.append(1)
            if len(tries) == 1:
                raise ValueError("Local model returned no usable reply.")
            return {"type": "reply", "text": "Okay, I'm with you. What happened after that?"}
        out = self.agent(planner).chat("so what do you think about all that")
        self.assertEqual(out["text"], "Okay, I'm with you. What happened after that?")

    def test_a_roast_uses_what_they_said(self):
        agent = self.agent()
        first = agent.chat("roast my outfit, i'm wearing crocs with socks")["text"]
        self.assertIn("rocs with socks", first)
        second = agent.chat("roast my outfit, i'm wearing crocs with socks")["text"]
        self.assertIn("rocs with socks", second)
        self.assertNotEqual(first, second)
        self.assertIn("evidence", agent.chat("roast my outfit")["text"])
        self.assertIn("Your dad's old cargo shorts", humor.roast("roast my fit, wearing my dad's old cargo shorts"))
        self.assertIn("Not you", humor.roast("roast my look, it's my big nose"))

    def test_the_humor_notes_have_no_line_to_copy(self):
        self.assertNotIn("Camry", " ".join(humor_bank.TECHNIQUES.values()))


if __name__ == "__main__":
    unittest.main()
