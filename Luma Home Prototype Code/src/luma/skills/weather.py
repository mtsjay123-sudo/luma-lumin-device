"""The weather, read live from Open-Meteo (wttr.in when it's down): free, no account, no API key.

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
WTTR = "https://wttr.in/{q}?format=j1"
WHEN_TOMORROW = re.compile(r"\btomorrow|tmrw|tmr\b", re.I)

# WMO weather codes, as a person would say them.
CODES = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "cloudy", 45: "foggy", 48: "foggy", 51: "drizzly", 53: "drizzly", 55: "drizzly",
         56: "freezing drizzle", 57: "freezing drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
         71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow", 80: "rain showers", 81: "rain showers", 82: "heavy showers",
         85: "snow showers", 86: "snow showers", 95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail"}


# The word alone isn't a question. "this weather is making me so sad", "I hate cold weather", "the weather was perfect for
# the funeral" each got "Which city?" or a forecast. Said about how it is, was or feels, it's talk, unless it's also asked.
WEATHER_ASKED = re.compile(r"(?:\bwhat(?:'s| is|s)?|\bhow(?:'s| is|s)?|\bcheck|\btell me|\bshow me|\bgive me|\bget me|\bknow|\blook up|\bpull up|\bcan you|\bcould you)\b.{0,25}\bweather\b|"
                           r"\bweather (?:in|for|at|near|around|report|update|forecast)\b|\bweather\s*\?|^\W*(?:the |today'?s |tomorrow'?s )?weather(?: (?:today|tomorrow|tonight|now|rn|outside|like))?\W*$", re.I)
WEATHER_TALK = re.compile(r"\b(?:mood|sad|depress\w*|miss(?:ing)?|hate|hated|love|loved|lonely|cry(?:ing)?|funeral|reminds?|making me|makes me|made me|match(?:es|ing|ed)?|feels?|feeling|felt|"
                          r"perfect|ruined|was|were|has been|had been|have been|been|nice|beautiful|gorgeous|lovely|awful|terrible|crazy|weird|gloomy|miserable|"
                          r"(?:this|that|hot|cold|bad|good|rainy|sunny|grey|gray) weather|under the weather|bleak|grim)\b", re.I)


# A figure of speech is never a forecast: "the forecast for my love life is bleak", "I need an umbrella for my life lol",
# "I'm going to snow myself in and hibernate" each went looking for the weather in "My Love Life Is Bleak".
FIGURE = re.compile(r"\b(?:my (?:love |whole |entire |social |dating |sex )?life|myself|my (?:heart|soul|head|mood|feelings|marriage|career|future|relationship|bank account|week|day)|"
                    r"(?:i'm|i am|im|we're|we are) (?:gonna|going to|finna) (?:rain|snow|storm))\b", re.I)


def wants(text):
    text = str(text or "")
    found = ASKS.search(text)
    if not found:
        return False
    if WEATHER_ASKED.search(text):
        return True
    if FIGURE.search(text):
        return False
    return found.group(0).lower() not in ("weather", "forecast") or not WEATHER_TALK.search(text)


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


def from_wttr(spot, place, fetch=None):
    """The same forecast from wttr.in, for when Open-Meteo can't be read: (spot, cast), or (spot, None)."""
    where = f"{spot['lat']},{spot['lon']}" if spot else urllib.parse.quote(" ".join(place.split()).replace(" ", "+"), safe="+")
    data = _get(WTTR.format(q=where), fetch)
    now, days = (data.get("current_condition") or [{}])[0], data.get("weather") or []
    if "temp_F" not in now or not days:
        return spot, None
    def sky(desc):
        return " ".join(str(((desc or [{}])[0]).get("value") or "").split()).lower()
    def rain(day):
        chances = [int(h.get("chanceofrain") or 0) for h in day.get("hourly") or []]
        return max(chances) if chances else None
    def noon(day):
        hours = day.get("hourly") or []
        return sky(hours[len(hours) // 2].get("weatherDesc")) if hours else ""
    if not spot:
        area = (data.get("nearest_area") or [{}])[0]
        region = ((area.get("region") or [{}])[0]).get("value") or ""
        spot = {"name": place.title(), "region": region, "lat": None, "lon": None}
    cast = {"now": {"temperature_2m": float(now["temp_F"]), "apparent_temperature": float(now.get("FeelsLikeF") or now["temp_F"]), "sky": sky(now.get("weatherDesc"))},
            "daily": {"temperature_2m_max": [float(d["maxtempF"]) for d in days], "temperature_2m_min": [float(d["mintempF"]) for d in days],
                      "precipitation_probability_max": [rain(d) for d in days], "sky": [noon(d) for d in days]},
            "source": "wttr.in"}
    return spot, cast


def say(spot, cast, tomorrow=False):
    """'Right now in Raleigh it's 64° and partly cloudy (feels like 62°). Today: high of 71°, low of 52°, 10% chance of rain.'"""
    daily, i = cast["daily"], 1 if tomorrow else 0
    high, low = round(daily["temperature_2m_max"][i]), round(daily["temperature_2m_min"][i])
    rain = (daily.get("precipitation_probability_max") or [None, None])[i]
    sky = (daily.get("sky") or [None, None])[i] or CODES.get((daily.get("weather_code") or [None, None])[i], "")
    day = (f"Tomorrow in {spot['name']}: " if tomorrow else "Today: ") + (f"{sky}, " if sky and tomorrow else "") + f"high of {high}°, low of {low}°"
    day += f", {rain}% chance of rain." if rain is not None else "."
    if tomorrow:
        return day
    now = cast["now"]
    temp, feels = round(now["temperature_2m"]), round(now.get("apparent_temperature", now["temperature_2m"]))
    sky_now = now.get("sky") or CODES.get(now.get("weather_code"), "")
    lead = f"Right now in {spot['name']} it's {temp}°" + (f" and {sky_now}" if sky_now else "") + (f" (feels like {feels}°)" if abs(feels - temp) >= 3 else "") + ". "
    return lead + day
