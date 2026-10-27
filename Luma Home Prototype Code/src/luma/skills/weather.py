"""The weather, read live from Open-Meteo: free, no account, no API key.

The place comes from what they said ("weather in Raleigh") or the last city they asked about. The forecast is read right
then, never remembered, and one that can't be read is said to be missing, never guessed.
"""
from __future__ import annotations

import json
import re
import urllib.parse

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1&language=en&format=json"
FORECAST = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,weather_code,"
            "wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"
            "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=2")

ASKS = re.compile(r"\b(?:weather|forecast|temperature outside|how (?:hot|cold|warm|nice) (?:is it|will it be|is it gonna be|is it going to be)(?: outside)?|"
                  r"(?:is it|will it|gonna|going to|finna) (?:rain|snow|storm|be (?:hot|cold|warm|nice))|rain(?:ing)? (?:today|tomorrow|tonight|later)|"
                  r"need an? (?:umbrella|jacket|coat))\b", re.I)
PLACE = re.compile(r"\b(?:in|for|at|near|around|out in)\s+(?P<place>(?!the (?:morning|afternoon|evening|week)|here\b|my area\b)[a-z][a-z .'-]{1,40}?)"
                   r"(?:\s+(?:today|tonight|tomorrow|this (?:week|weekend|morning|afternoon|evening)|right now|now|rn|later))?\s*\??\s*$", re.I)
WHEN_TOMORROW = re.compile(r"\btomorrow|tmrw|tmr\b", re.I)

# WMO weather codes, as a person would say them.
CODES = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "cloudy", 45: "foggy", 48: "foggy", 51: "drizzly", 53: "drizzly", 55: "drizzly",
         56: "freezing drizzle", 57: "freezing drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
         71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow", 80: "rain showers", 81: "rain showers", 82: "heavy showers",
         85: "snow showers", 86: "snow showers", 95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail"}


def wants(text):
    return bool(ASKS.search(str(text or "")))


def place_in(text):
    m = PLACE.search(str(text or "").strip())
    return " ".join(m["place"].split()).strip(" .'-") if m else None


def _get(url, fetch=None):
    from luma.skills.markets import _get as get
    return json.loads(get(url, fetch).decode("utf-8", "replace") or "{}")


def find(place, fetch=None):
    """{'name': 'Raleigh', 'region': 'North Carolina', 'lat': .., 'lon': ..} or None."""
    hits = (_get(GEOCODE.format(q=urllib.parse.quote(place)), fetch).get("results") or [])
    if not hits:
        return None
    h = hits[0]
    return {"name": h.get("name") or place.title(), "region": h.get("admin1") or h.get("country") or "", "lat": h["latitude"], "lon": h["longitude"]}


def forecast(spot, fetch=None):
    data = _get(FORECAST.format(lat=spot["lat"], lon=spot["lon"]), fetch)
    now, daily = data.get("current") or {}, data.get("daily") or {}
    if "temperature_2m" not in now or not daily.get("temperature_2m_max"):
        return None
    return {"now": now, "daily": daily}


def say(spot, cast, tomorrow=False):
    """'Right now in Raleigh it's 64° and partly cloudy (feels like 62°). Today: high of 71°, low of 52°, 10% chance of rain.'"""
    daily, i = cast["daily"], 1 if tomorrow else 0
    high, low = round(daily["temperature_2m_max"][i]), round(daily["temperature_2m_min"][i])
    rain = (daily.get("precipitation_probability_max") or [None, None])[i]
    sky = CODES.get((daily.get("weather_code") or [None, None])[i], "")
    day = (f"Tomorrow in {spot['name']}: " if tomorrow else "Today: ") + (f"{sky}, " if sky and tomorrow else "") + f"high of {high}°, low of {low}°"
    day += f", {rain}% chance of rain." if rain is not None else "."
    if tomorrow:
        return day
    now = cast["now"]
    temp, feels = round(now["temperature_2m"]), round(now.get("apparent_temperature", now["temperature_2m"]))
    sky_now = CODES.get(now.get("weather_code"), "")
    lead = f"Right now in {spot['name']} it's {temp}°" + (f" and {sky_now}" if sky_now else "") + (f" (feels like {feels}°)" if abs(feels - temp) >= 3 else "") + ". "
    return lead + day
