"""The weather, read live from Open-Meteo (free, no key): for the city they name, or the last one they asked about.
A forecast that can't be read is said to be missing, never guessed."""
import json
import tempfile
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store
from luma.skills import weather

PLACES = {"raleigh": {"results": [{"name": "Raleigh", "admin1": "North Carolina", "latitude": 35.78, "longitude": -78.64}]}, "zzyzxqq": {}}
CAST = {"current": {"temperature_2m": 64.2, "apparent_temperature": 60.1, "weather_code": 2, "wind_speed_10m": 5},
        "daily": {"temperature_2m_max": [71.4, 68.0], "temperature_2m_min": [52.2, 50.0], "precipitation_probability_max": [10, 60], "weather_code": [2, 61]}}


def fake(url):
    if "geocoding-api" in url:
        name = url.split("name=")[1].split("&")[0].lower()
        return json.dumps(PLACES.get(name, {})).encode()
    if "api.open-meteo.com" in url:
        return json.dumps(CAST).encode()
    raise OSError("offline")


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.store.set_setting("signed_up", True)
        self.agent = Agent(store=self.store, use_model=False)
        self.agent.weather_fetch = fake

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_today_in_a_named_city(self):
        out = self.agent.chat("what's the weather in raleigh today?")
        self.assertEqual(out["text"], "Right now in Raleigh it's 64° and partly cloudy (feels like 60°). Today: high of 71°, low of 52°, 10% chance of rain.")
        self.assertEqual(out["results"][0]["source"], "Open-Meteo")

    def test_tomorrow_remembers_the_city(self):
        self.agent.chat("weather in raleigh")
        self.assertEqual(self.agent.chat("is it gonna rain tomorrow?")["text"], "Tomorrow in Raleigh: light rain, high of 68°, low of 50°, 60% chance of rain.")

    def test_no_city_yet_means_asking(self):
        self.assertIn("Which city?", self.agent.chat("is it gonna rain tomorrow?")["text"])

    def test_no_forecast_means_no_number(self):
        self.agent.weather_fetch = lambda url: (_ for _ in ()).throw(OSError("offline"))
        out = self.agent.chat("what's the weather in raleigh?")
        self.assertIn("won't guess", out["text"])
        self.assertNotRegex(out["text"], r"\d+°")
        self.agent.weather_fetch = fake
        self.assertIn("couldn't find a place called Zzyzxqq", self.agent.chat("weather in zzyzxqq")["text"])

    def test_what_counts(self):
        self.assertTrue(weather.wants("do i need an umbrella"))
        self.assertTrue(weather.wants("how cold is it gonna be tomorrow"))
        self.assertEqual(weather.place_in("what's the weather in new york city tomorrow?"), "new york city")
        self.assertIsNone(weather.place_in("what's the weather like in the morning"))


if __name__ == "__main__":
    unittest.main()
