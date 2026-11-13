"""What a speaker in the home does, done by Luma: alarms, lists, a stopwatch, the time anywhere, how many days until
something, conversions, a coin, dice, spelling, the volume, do not disturb, sleep sounds, music and the lights.

Everything here is a plain command said to Luma, read by code, never by the brain, so it's instant and always right.
Each one answers in Luma's own voice: short, warm, like a friend who's handy, never "Okay, setting alarm."

What leaves the home, and only when the owner has turned it on:
- Music from the radio: only what they asked to play ("jazz", "NHK") goes to a free radio directory
  (radio-browser.info), behind the music switch, which is off until they turn it on. Music in their own folder needs
  nothing from outside.
- The lights and the rest of the house: only to their own Home Assistant, behind the home switch (off until they
  turn it on), and only to the devices they listed. A plain spoken command from the owner is the yes for lights,
  switches, fans, scenes, blinds and the thermostat. Doors are only ever locked and garages only ever closed by
  voice: unlocking or opening one is never done from a sentence, by anyone.

Nothing is bought or sent from here. In kids mode the alarms, lists, timers, stopwatch, sums, coin, dice, spelling
and sleep sounds work; the radio, the house and do-not-disturb changes don't.
"""
from __future__ import annotations

import math
import random
import re
import time
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from luma.memory.store import reject_payment_secrets

# -- reading a time of day ------------------------------------------------------------------------------------------
_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "a": 1, "an": 1, "half a": 0.5, "half an": 0.5, "half": 0.5, "a couple": 2, "a couple of": 2}
CLOCK = (r"(?P<clock>noon|midnight|(?P<h>\d{1,2})(?:[:.](?P<m>\d{2}))?\s*(?P<ap>a\.?m\.?|p\.?m\.?|am|pm|a|p)?"
         r"(?:\s+(?P<part>in the morning|in the afternoon|in the evening|at night|tonight|this morning|this evening|tomorrow morning))?)")
DAYNAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAYS = (r"(?P<days>every ?day|daily|every morning|every night|on weekdays|weekdays|every weekday|on weekends|weekends|every weekend"
        r"|tomorrow|today|tonight"
        r"|(?:every |on )?(?:(?:mon|tues|wednes|thurs|fri|satur|sun)days?(?:,? (?:and |& )?)?)+)")


def clock_of(match):
    """(hour, minute, meridiem known) from a CLOCK match."""
    word = match["clock"].lower()
    if word == "noon": return 12, 0, True
    if word == "midnight": return 0, 0, True
    h, m = int(match["h"]), int(match["m"] or 0)
    if not (0 <= h <= 23 and 0 <= m <= 59): raise ValueError("That isn't a time on a clock.")
    ap = (match["ap"] or "").replace(".", "").lower()
    part = (match["part"] or "").lower()
    if ap.startswith("p") or part in {"in the afternoon", "in the evening", "at night", "tonight", "this evening"}:
        if h > 12: raise ValueError("That isn't a time on a clock.")
        return (h % 12) + 12, m, True
    if ap.startswith("a") or "morning" in part:
        if h > 12: raise ValueError("That isn't a time on a clock.")
        return h % 12, m, True
    return h, m, h > 12 or h == 0


def days_of(words):
    """Which days an alarm repeats on (0 is Monday), [] for once, or "tomorrow"."""
    w = (words or "").lower()
    if not w or w in {"today", "tonight"}: return []
    if w == "tomorrow": return "tomorrow"
    if re.search(r"every ?day|daily|every morning|every night", w): return list(range(7))
    if "weekday" in w: return [0, 1, 2, 3, 4]
    if "weekend" in w: return [5, 6]
    found = [i for i, name in enumerate(DAYNAMES) if re.search(name[:3] + r"\w*days?\b", w)]
    return found


def say_clock(dt):
    return dt.strftime("%I:%M %p").lstrip("0").replace(":00 ", " ")


def say_days(days):
    if not days: return ""
    if days == list(range(7)): return "every day"
    if days == [0, 1, 2, 3, 4]: return "on weekdays"
    if days == [5, 6]: return "on weekends"
    names = [DAYNAMES[d].capitalize() + "s" for d in days]
    return "on " + (names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1])


# -- the commands ---------------------------------------------------------------------------------------------------
LEAD = r"^(?:(?:hey |ok(?:ay)? |yo )?luma,? )?(?:(?:can|could|would|will) you |please |pls |hey,? |ok(?:ay)?,? |so,? |um,? )*"
END = r"(?:,? (?:please|pls|thanks|thank you|for me|luma))*\s*[.!?]*$"

ALARM_SET = re.compile(LEAD + r"(?:set|make|create|add|put|get) (?:me )?(?:an? |my |the |another )?(?:new )?alarm (?:clock )?(?:for |at |to )?" + CLOCK
                       + r"(?:,? " + DAYS + r")?" + r"(?: (?:called|named|labell?ed|for|to) (?P<label>[\w' -]{1,40}?))?" + END, re.I)
ALARM_SET2 = re.compile(LEAD + r"(?:wake me(?: up)?|get me up) (?:at |by |around )?" + CLOCK + r"(?:,? " + DAYS + r")?" + END, re.I)
ALARM_SET3 = re.compile(LEAD + r"(?:set |make )?(?:an? |my )?" + CLOCK + r" alarm(?:,? " + DAYS + r")?" + END, re.I)
ALARM_SET4 = re.compile(LEAD + r"(?:set|make|add) (?:an? |my )?(?:new )?alarm (?:for |on )?" + DAYS + r" (?:at |for )?" + CLOCK + END, re.I)
ALARM_LIST = re.compile(LEAD + r"(?:what(?:'s| is| are)? (?:my |the )?alarms?(?: set(?: for)?| for)?(?: tomorrow)?|what alarms? (?:do i have|have i (?:got|set)|are (?:set|on))(?: set| on)?(?: for tomorrow| tomorrow)?|(?:show|list|read|tell) (?:me )?(?:all )?(?:my |the )?alarms?"
                        r"|(?:my |the )?alarms|do i have (?:an? |any )?alarms?(?: set)?(?: for tomorrow| tomorrow)?|when(?:'s| is) my (?:next )?alarm"
                        r"|what time(?: is| did i set) my alarm(?: for| set for)?|is my alarm (?:on|set))" + END, re.I)
ALARM_OFF = re.compile(LEAD + r"(?:cancel|delete|remove|turn off|switch off|clear|get rid of|disable) (?P<all>all )?(?:of )?(?:my |the |that )?"
                       r"(?:" + CLOCK + r" )?alarms?(?: for " + CLOCK.replace("?P<", "?P<x") + r")?(?: (?:for )?tomorrow)?" + END, re.I)
SNOOZE = re.compile(LEAD + r"(?:snooze|five more minutes|5 more minutes|ten more minutes|10 more minutes|just a few more minutes|few more minutes)(?: it)?" + END, re.I)
UP = re.compile(LEAD + r"(?:stop|ok(?:ay)?|i'?m up|i'?m awake|i'?m getting up|turn it off|alarm off|shut it off|got it|enough|stop the alarm|stop it)(?:,? (?:i'?m up|i'?m awake|stop|thanks))*" + END, re.I)

LIST_NAME = r"(?P<list>shopping|grocery|groceries|to[- ]?do|todo|packing|christmas|gift|wish|bucket|movie|reading|book|chores?|errands?|costco|target|[a-z][a-z']{1,15}(?: [a-z][a-z']{1,15})?)"
LIST_ADD = re.compile(LEAD + r"(?:add|put|throw|stick|pop|write) (?P<items>.+?) (?:to|on|onto|in|into|down on) (?:my |the |our |a )?" + LIST_NAME + r" list" + END, re.I)
LIST_ADD2 = re.compile(LEAD + r"(?:add to|on) (?:my |the |our )?" + LIST_NAME + r" list,? (?P<items>.+?)" + END, re.I)
LIST_READ = re.compile(LEAD + r"(?:(?:what(?:'s| is| do i have| have i got| do we have) on|(?:read|show|tell|check|open|give)(?: me)?(?: what'?s on)?) )?(?:my |the |our )?" + LIST_NAME + r" list" + END, re.I)
LIST_DROP = re.compile(LEAD + r"(?:remove|take|delete|cross|scratch|check) (?P<items>.+?) (?:off|from) (?:of )?(?:my |the |our )?" + LIST_NAME + r" list" + END, re.I)
LIST_CLEAR = re.compile(LEAD + r"(?:clear|empty|delete|wipe|reset) (?:out )?(?:my |the |our |everything on (?:my |the |our )?)?" + LIST_NAME + r" list" + END, re.I)
LIST_ALL = re.compile(LEAD + r"(?:what lists do (?:i|we) have|(?:show|read) (?:me )?(?:all )?(?:my |our )lists|my lists)" + END, re.I)

WATCH = re.compile(LEAD + r"(?P<act>start|stop|pause|reset|restart|resume)(?: (?:a|the|my))? stopwatch" + END
                   + r"|" + LEAD + r"how long (?:has|is) (?:the |my )?stopwatch(?: been)?(?: running| going| on)?" + END, re.I)

TIME_ASK = re.compile(LEAD + r"(?:what(?:'s| is)(?: the)? time|what time is it|what time(?:'s| is) it|do you (?:have|know) the time|time check|what's the time now)"
                      r"(?: right now| now)?(?: in (?P<place>[a-z .'-]{2,30}?))?(?: right now| now)?" + END, re.I)
DATE_ASK = re.compile(LEAD + r"(?:what(?:'s| is) (?:the date|today'?s date|the date today)|what day is (?:it|today)(?: today)?|what(?:'s| is) today|what's the day today"
                      r"|what (?:date|day of the week) is (?:it|today))" + END, re.I)
UNTIL = re.compile(LEAD + r"how (?:many|much) (?P<unit>days|sleeps|weeks|time)(?: are there| is (?:it|there)| do (?:i|we) have| left)? (?:left )?(?:until|till|til|'til|before|to) (?P<what>.+?)" + END, re.I)
COIN = re.compile(LEAD + r"(?:flip|toss) (?:a |the )?coin|heads or tails" + END, re.I)
DICE = re.compile(LEAD + r"roll (?:(?P<n>a|an|one|two|three|four|five|six|\d) )?(?:(?:six[- ]sided |\d+[- ]sided )?(?:dice|die)|d(?P<sides>\d{1,3})|(?P<n2>\d)d(?P<sides2>\d{1,3}))" + END, re.I)
PICK = re.compile(LEAD + r"(?:pick|give me|choose|say) (?:me )?a (?:random )?number (?:between|from) (?P<lo>-?\d{1,9}) (?:and|to) (?P<hi>-?\d{1,9})" + END, re.I)
SPELL = re.compile(LEAD + r"(?:how (?:do|would) (?:you|i|we) spell|how(?:'s| is) .{0,3}spelled|spell(?: out)?(?: the word)?|what(?:'s| is) the spelling of) [\"']?(?P<word>[a-z][a-z'-]{1,30})[\"']?(?: spelled)?" + END, re.I)

VOLUME = re.compile(LEAD + r"(?:(?P<up>volume up|turn (?:it|the volume|yourself|you) up|louder|speak up|be louder|get louder|a (?:little|bit) louder|up the volume|raise the volume)"
                    r"|(?P<down>volume down|turn (?:it|the volume|yourself|you) down|quieter|softer|be quieter|a (?:little|bit) quieter|lower the volume|lower your voice)"
                    r"|(?:set |change |put )?(?:the |your )?volume (?:to |at )?(?:level )?(?P<to>\d{1,2}|ten|max(?:imum)?|min(?:imum)?|half)(?: percent)?"
                    r"|(?P<ask>what(?:'s| is) (?:the |your )?volume(?: at)?))(?: a (?:little|bit))?" + END, re.I)
DND = re.compile(LEAD + r"(?:(?P<off>turn off|stop|end|disable|cancel) do not disturb|do not disturb off|(?:turn on |start |enable |go into |put on )?do not disturb(?: mode)?(?: on)?"
                 r"(?: for (?P<n>\d{1,3}|an?|one|two|three) (?P<unit>minutes?|hours?))?|(?:turn on |start )?(?:quiet|silent) mode)" + END, re.I)

SOUNDS = {
    "rain": r"rain(?:fall|storm| storm)?|rainy|thunder(?:storm)?|storm",
    "ocean": r"ocean|waves?|sea|beach|surf",
    "white noise": r"white noise|static|fan(?: noise)?",
    "pink noise": r"pink noise",
    "brown noise": r"brown(?:ian)? noise|brown",
    "fireplace": r"fire(?:place)?|crackling(?: fire)?|campfire",
    "stream": r"stream|brook|creek|river|water",
    "wind": r"wind|breeze",
}
SOUND = re.compile(LEAD + r"(?:play|put on|start|turn on|i (?:want|need)|let me hear|help me sleep with|can i have|give me)(?: some| the| a little| me)? (?P<what>"
                   + "|".join(f"(?:{w})" for w in SOUNDS.values()) + r")(?: sounds?| noise| sounds? to sleep| to sleep)?(?: (?:for|until) (?P<n>\d{1,3}|an?|one|two|three|half an?) (?P<unit>minutes?|hours?|hour))?" + END, re.I)
SLEEP = re.compile(LEAD + r"(?:play|put on|start)(?: some| me)? (?:sleep|relaxing|calming|ambient|nature) (?:sounds?|noise|music)|help me (?:fall asleep|sleep|relax)(?: with (?:some )?sounds?)?" + END, re.I)

STOP_SOUND = re.compile(LEAD + r"(?:stop|pause|turn off|shut off|kill|end|cut)(?: the| that| this)? ?(?:music|song|radio|sounds?|noise|rain|ocean|playing|it|playback)?" + END, re.I)
RESUME = re.compile(LEAD + r"(?:resume|unpause|keep playing|play it again|continue(?: the music| playing)?|start (?:it|the music) again)" + END, re.I)
NEXT = re.compile(LEAD + r"(?:next|skip|skip (?:this|it|this song|this one|the song)|next (?:song|station|track|one)|change the station|another (?:one|station))" + END, re.I)
NOW = re.compile(LEAD + r"(?:what(?:'s| is| song is) (?:this|playing|on)|what(?:'s| is) (?:this )?(?:song|station)|what am i listening to|who(?:'s| is) this|who sings this)" + END, re.I)
NOT_MUSIC = re.compile(r"\b(?:game|games|questions|trivia|truth|dare|would you rather|i spy|riddle|riddles|with me|joke|hide and seek|cards|chess|tag|catch|pretend|"
                       r"along|a role|the role|role|devil'?s advocate|it cool|it safe|nice|dumb|hard to get|favorites?|video|clip|the video|movie|show|episode|outside|"
                       r"a sound|sound|sounds|noise|rain|ocean|waves?|fire|white|brown|pink|it back|back|that again|music for (?:my|our) )\b", re.I)
GENRES = (r"jazz|lo-?fi|lofi|chill(?:hop)?|classical|piano|rock|pop|j-?pop|k-?pop|city pop|anime|hip[- ]?hop|rap|r&b|rnb|soul|funk|country|folk|blues|indie|"
          r"metal|punk|reggae|latin|salsa|reggaeton|edm|house|techno|electronic|dance|disco|ambient|bossa nova|oldies|80s|90s|70s|60s|2000s|christmas|gospel|"
          r"study|focus|sleep|relaxing|coffee shop|cafe|news|talk|npr|bbc|nhk|fm|am|top hits|hits|the radio")
PLAY = re.compile(LEAD + r"(?:play|put on|throw on|stream|turn on|start)(?: me)?(?: some| a little| the| a bit of| my)? (?P<what>.+?)" + END, re.I)

HOME_ON = re.compile(LEAD + r"(?:turn|switch|flip|put|shut) (?P<onoff>on|off|out) (?:the |my |all (?:of )?the |all )?(?P<thing>.+?)" + END
                     + r"|" + LEAD + r"(?:turn|switch|flip|put|shut) (?:the |my |all (?:of )?the |all )?(?P<thing2>.+?) (?P<onoff2>on|off|out)" + END
                     + r"|" + LEAD + r"(?P<thing3>(?:the )?(?:\w+ )?lights?) (?P<onoff3>on|off|out)" + END
                     + r"|" + LEAD + r"(?P<onoff4>lights out|lights on|lights off|kill the lights|hit the lights)" + END, re.I)
HOME_DIM = re.compile(LEAD + r"(?:(?P<dir>dim|brighten|raise|lower|bring (?:up|down)) (?:the |my )?(?P<thing>.+?)(?: (?:to|at) (?P<pct>\d{1,3})(?: ?%| percent)?)?"
                      r"|set (?:the |my )?(?P<thing2>.+?) (?:brightness )?(?:to|at) (?P<pct2>\d{1,3})(?: ?%| percent))" + END, re.I)
HOME_HEAT = re.compile(LEAD + r"(?:set|turn|put|change|make) (?:the |my )?(?P<thing>thermostat|heat(?:er|ing)?|a/?c|air(?: conditioning| conditioner)?|temperature|temp)(?: (?:up|down))? (?:to |at )?(?P<deg>\d{2})(?: ?°| degrees?)?(?: ?(?P<scale>f|c|fahrenheit|celsius))?" + END, re.I)
HOME_LOCK = re.compile(LEAD + r"(?P<act>lock|unlock|open|close|shut|raise|lower) (?:the |my |all (?:of )?the |all )?(?P<thing>(?:[\w' ]{0,20} )?(?:doors?|locks?|garage(?: door)?|gate|blinds|shades|curtains|windows?|shutters))" + END, re.I)
HOME_SCENE = re.compile(LEAD + r"(?:(?:turn on|activate|start|set|run|switch to) (?:the |my )?(?P<scene>[\w' -]{2,30}?) scene|(?:set|make) (?:the |it )?(?:mood|scene) (?:to |for )?(?P<scene2>[\w' -]{2,30}?))" + END, re.I)
HOME_ASK = re.compile(LEAD + r"(?:is (?:the |my )?(?P<thing>[\w' ]{2,30}?) (?P<state>locked|unlocked|on|off|open|closed)|what(?:'s| is) (?:the )?(?:temperature|temp) (?:inside|in here|in the house|at home|upstairs|downstairs))" + END, re.I)
HOME_WORDS = re.compile(r"\b(?:lights?|lamps?|fans?|plugs?|outlets?|switch(?:es)?|tv|television|heater|ac|a/c|air conditioner|thermostat|kettle|coffee maker|humidifier|"
                        r"purifier|diffuser|speaker|everything|led|leds|strip|bulbs?|porch|hallway|bedroom|kitchen|living room|bathroom|office|garage|closet)\b", re.I)

ROUTINE = re.compile(LEAD + r"(?:(?P<morning>start my day|morning routine|run my morning routine|good morning routine|let'?s start the day)|(?P<night>bedtime routine|night routine|goodnight routine|good night routine|run my (?:bedtime|night) routine|i'?m going to bed,? (?:turn|shut) (?:everything|it all) off|(?:turn|shut) everything off,? i'?m going to bed))" + END, re.I)

# -- conversions ----------------------------------------------------------------------------------------------------
UNITS = {  # to a base: meters, grams, milliliters
    "inch": ("len", 0.0254, r"inch(?:es)?|in\b|\""), "foot": ("len", 0.3048, r"foot|feet|ft"), "yard": ("len", 0.9144, r"yards?|yds?"),
    "mile": ("len", 1609.344, r"miles?|mi"), "millimeter": ("len", 0.001, r"millimet(?:er|re)s?|mm"), "centimeter": ("len", 0.01, r"centimet(?:er|re)s?|cm"),
    "meter": ("len", 1.0, r"met(?:er|re)s?|m"), "kilometer": ("len", 1000.0, r"kilomet(?:er|re)s?|km|kms|k"),
    "ounce": ("mass", 28.349523125, r"ounces?|oz"), "pound": ("mass", 453.59237, r"pounds?|lbs?"), "gram": ("mass", 1.0, r"grams?|g"),
    "kilogram": ("mass", 1000.0, r"kilograms?|kilos?|kgs?"), "stone": ("mass", 6350.29318, r"stones?"),
    "teaspoon": ("vol", 4.92892159375, r"teaspoons?|tsps?"), "tablespoon": ("vol", 14.78676478125, r"tablespoons?|tbsps?|tbs"),
    "fluid ounce": ("vol", 29.5735295625, r"fluid ounces?|fl\.? ?oz"), "cup": ("vol", 236.5882365, r"cups?"),
    "pint": ("vol", 473.176473, r"pints?"), "quart": ("vol", 946.352946, r"quarts?"), "gallon": ("vol", 3785.411784, r"gallons?"),
    "milliliter": ("vol", 1.0, r"millilit(?:er|re)s?|mls?"), "liter": ("vol", 1000.0, r"lit(?:er|re)s?|l"),
    "fahrenheit": ("temp", None, r"degrees? fahrenheit|fahrenheit|°f|f"), "celsius": ("temp", None, r"degrees? celsius|celsius|centigrade|°c|c"),
}
_UNIT = "|".join(f"(?:{p})" for _, (_, _, p) in UNITS.items())
AMOUNT = r"(?P<n>-?\d+(?:\.\d+)?|-?\d+/\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|half an?|a half|a quarter)"
CONVERT = re.compile(LEAD + r"(?:convert |what(?:'s| is| are) |how (?:much|many|long|far|heavy|big) (?:is|are) )?" + AMOUNT + r" ?(?P<from>" + _UNIT + r")(?: (?:in|to|into|as|is how many|in how many|=)) (?P<to>" + _UNIT + r")" + END, re.I)
CONVERT2 = re.compile(LEAD + r"how many (?P<to>" + _UNIT + r") (?:are |is )?(?:there )?in " + AMOUNT + r"? ?(?P<from>" + _UNIT + r")" + END, re.I)


def _unit(word):
    word = word.lower().strip()
    for name, (_, _, pattern) in UNITS.items():
        if re.fullmatch(pattern, word, re.I): return name
    return None


def _amount(word):
    if word is None: return 1.0
    w = word.lower().strip()
    if w in {"a half", "half a", "half an"}: return 0.5
    if w == "a quarter": return 0.25
    if w in _NUM: return float(_NUM[w])
    if "/" in w:
        a, b = w.split("/")
        return float(a) / float(b)
    return float(w)


def _nice(x):
    if abs(x) >= 100: return f"{x:,.0f}"
    if abs(x) >= 10: return f"{x:,.1f}".rstrip("0").rstrip(".")
    return f"{x:,.2f}".rstrip("0").rstrip(".")


def _plural(name, x):
    if name in {"fahrenheit", "celsius"}: return "degrees " + name.capitalize()
    if abs(x) == 1: return name
    return {"foot": "feet", "inch": "inches"}.get(name, name + "s")


def convert(text):
    m = CONVERT.match(text) or CONVERT2.match(text)
    if not m: return None
    a, b = _unit(m["from"]), _unit(m["to"])
    if not a or not b or a == b: return None
    ka, kb = UNITS[a][0], UNITS[b][0]
    if ka != kb:
        return {"text": f"Those don't convert: {a}s measure something different from {b}s."} if {ka, kb} <= {"len", "mass", "vol"} else None
    try: n = _amount(m["n"])
    except (ValueError, ZeroDivisionError): return None
    if ka == "temp":
        out = n * 9 / 5 + 32 if a == "celsius" else (n - 32) * 5 / 9
        return {"text": f"{_nice(n)} degrees {a.capitalize()} is about {_nice(out)} degrees {b.capitalize()}."}
    out = n * UNITS[a][1] / UNITS[b][1]
    return {"text": f"{_nice(n)} {_plural(a, n)} is about {_nice(out)} {_plural(b, out)}."}


# -- days until -----------------------------------------------------------------------------------------------------
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


def _nth_weekday(year, month, weekday, n):
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _easter(year):
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    return date(year, month, ((h + l - 7 * m + 114) % 31) + 1)


HOLIDAYS = {
    r"christmas(?: day)?|xmas": lambda y: date(y, 12, 25),
    r"christmas eve": lambda y: date(y, 12, 24),
    r"new year'?s(?: day)?|the new year|new years": lambda y: date(y, 1, 1),
    r"new year'?s eve": lambda y: date(y, 12, 31),
    r"halloween": lambda y: date(y, 10, 31),
    r"valentine'?s(?: day)?": lambda y: date(y, 2, 14),
    r"(?:the )?(?:4th|fourth) of july|july (?:4th|4|fourth)|independence day": lambda y: date(y, 7, 4),
    r"thanksgiving": lambda y: _nth_weekday(y, 11, 3, 4),
    r"mother'?s day": lambda y: _nth_weekday(y, 5, 6, 2),
    r"father'?s day": lambda y: _nth_weekday(y, 6, 6, 3),
    r"easter": _easter,
    r"st\.? patrick'?s(?: day)?|saint patrick'?s(?: day)?": lambda y: date(y, 3, 17),
    r"labor day": lambda y: _nth_weekday(y, 9, 0, 1),
    r"memorial day": lambda y: date(y, 5, 31) - timedelta(days=date(y, 5, 31).weekday()),   # the last Monday in May
    r"golden week": lambda y: date(y, 4, 29),
    r"(?:the )?summer": lambda y: date(y, 6, 21),
    r"(?:the )?winter": lambda y: date(y, 12, 21),
    r"(?:the )?spring": lambda y: date(y, 3, 20),
    r"(?:the )?(?:fall|autumn)": lambda y: date(y, 9, 22),
}


def _date_in(words, today):
    """A date said in words ("march 3", "3/14", "the 20th", "christmas"), the next one on or after today."""
    w = words.lower().strip().rstrip("?.! ")
    w = re.sub(r"^(?:it'?s |it is |the day of )", "", w)
    for pattern, make in HOLIDAYS.items():
        if re.fullmatch(pattern, w):
            d = make(today.year)
            return d if d >= today else make(today.year + 1)
    m = re.fullmatch(r"(?:(?:the )?(?P<d1>\d{1,2})(?:st|nd|rd|th)? of )?(?P<mon>" + "|".join(m[:3] + r"\w*" for m in MONTHS) + r")\.?(?: (?:the )?(?P<d2>\d{1,2})(?:st|nd|rd|th)?)?(?:,? (?P<y>\d{4}))?", w)
    if m:
        month = next(i + 1 for i, name in enumerate(MONTHS) if m["mon"].startswith(name[:3]))
        day = int(m["d1"] or m["d2"] or 1)
        year = int(m["y"]) if m["y"] else today.year
        try: d = date(year, month, day)
        except ValueError: return None
        if not m["y"] and d < today:
            d = date(year + 1, month, day)
        return d
    m = re.fullmatch(r"(?P<mo>\d{1,2})/(?P<d>\d{1,2})(?:/(?P<y>\d{2,4}))?", w)
    if m:
        year = int(m["y"]) + (2000 if m["y"] and len(m["y"]) == 2 else 0) if m["y"] else today.year
        try: d = date(year, int(m["mo"]), int(m["d"]))
        except ValueError: return None
        return d if m["y"] or d >= today else date(year + 1, d.month, d.day)
    m = re.fullmatch(r"(?:next |this )?(?P<wd>" + "|".join(DAYNAMES) + r")", w)
    if m:
        ahead = (DAYNAMES.index(m["wd"]) - today.weekday()) % 7 or 7
        return today + timedelta(days=ahead)
    return None


def _birthday(memories, who):
    """A birthday Luma was told ("my birthday is June 3", "Mom's birthday is March 9")."""
    who = (who or "my").lower()
    for row in memories:
        text = str(row.get("text", "")).lower()
        if "birthday" not in text: continue
        if who in {"my", "mine"} and not re.search(r"\b(?:my|their|the owner'?s)\b birthday|birthday is|i was born", text): continue
        if who not in {"my", "mine"} and who.rstrip("'s") not in text: continue
        if who in {"my", "mine"} and re.search(r"\b(?:mom|dad|sister|brother|wife|husband|son|daughter|friend|grandma|grandpa)'?s? birthday", text): continue
        m = re.search(r"(" + "|".join(name[:3] + r"\w*" for name in MONTHS) + r")\.? (\d{1,2})(?:st|nd|rd|th)?", text)
        if m: return m[1] + " " + m[2]
    return None


# -- what Luma says the radio is ----------------------------------------------------------------------------------------
RADIO_HOST = "https://de1.api.radio-browser.info"


def radio_search(fetch, what, limit=6):
    """Stations for what they asked (a genre, a station's name), most-listened first. Only `what` is sent."""
    from urllib.parse import quote
    what = re.sub(r"\b(?:music|radio|station|songs?|tunes)\b", "", what, flags=re.I).strip() or "hits"
    tag = what.lower().replace(" ", "")
    tag = {"lo-fi": "lofi", "jpop": "j-pop", "kpop": "k-pop", "hiphop": "hip hop", "rnb": "r&b", "thehits": "hits", "tophits": "hits", "theradio": "hits"}.get(tag, what.lower())
    rows = []
    for url in (f"{RADIO_HOST}/json/stations/bytag/{quote(tag)}?order=clickcount&reverse=true&hidebroken=true&limit={limit}",
                f"{RADIO_HOST}/json/stations/byname/{quote(what)}?order=clickcount&reverse=true&hidebroken=true&limit={limit}"):
        try: found = fetch("GET", url, {"User-Agent": "Luma/1.0"})
        except Exception: found = []
        for row in found if isinstance(found, list) else []:
            stream = str(row.get("url_resolved") or row.get("url") or "")
            if stream.startswith(("https://", "http://")) and row.get("name"):
                rows.append({"name": " ".join(str(row["name"]).split())[:80], "url": stream})
        if rows: break
    return rows


# -- the house ------------------------------------------------------------------------------------------------------
def _words(entity):
    """light.living_room_lamp -> "living room lamp"."""
    return entity.split(".", 1)[-1].replace("_", " ")


def find_devices(thing, allowed, domains=None):
    """Which of the owner's listed devices `thing` means. "the lights" means every light; "everything" every light and switch."""
    thing = re.sub(r"\b(?:the|my|all|of|please|in|on|room's|room)\b", " ", thing.lower())
    thing = " ".join(thing.split())
    pool = [e for e in allowed if not domains or e.split(".")[0] in domains]
    if thing in {"lights", "light", "the lights", "everything", "all", "it all", "everything off", "lamps"}:
        want = {"light"} if "light" in thing or "lamp" in thing else {"light", "switch", "fan"}
        return [e for e in pool if e.split(".")[0] in want]
    plural = thing.endswith("lights") or thing.endswith("lamps")
    core = re.sub(r"\b(?:lights?|lamps?)\b", "", thing).strip()
    scored = []
    for entity in pool:
        name = _words(entity)
        domain = entity.split(".")[0]
        if name == thing or name == core: scored.append((3, entity)); continue
        wanted = set(core.split()) if core else set(thing.split())
        have = set(name.split()) | ({"light", "lights", "lamp"} if domain == "light" else {domain})
        if wanted and wanted <= have:
            scored.append((2 if core else 1, entity))
    if not scored: return []
    best = max(s for s, _ in scored)
    hits = [e for s, e in scored if s == best]
    if plural or best >= 2 and len(hits) > 1 and all(e.split(".")[0] == "light" for e in hits): return hits
    return hits if len(hits) == 1 else hits[:1] if best == 3 else hits


class AtHome:
    """The everyday commands. `fetch(method, url, headers, payload=None)` reaches the network (the radio, the house);
    `player` plays sound on the Luma at home; `on(service)` says whether the owner turned a switch on."""

    SNOOZE_MIN = 9
    RING_FOR = 15 * 60    # an alarm nobody stops rings for fifteen minutes, then lets go
    RING_EVERY = 60       # and says so again each minute

    def __init__(self, store, clock=None, zone="America/New_York", player=None, fetch=None, on=None, env=None, mode=lambda: "friend",
                 rng=None, memories=None, audit=None, hush=None):
        self.store = store
        self.clock = clock or time.time
        self._zone = zone if callable(zone) else (zone if isinstance(zone, ZoneInfo) else ZoneInfo(str(zone)))
        self.player = player
        self.fetch = fetch
        self.on = on or (lambda service: False)
        self.env = env if env is not None else {}
        self.mode = mode
        self.rng = rng or random.SystemRandom()
        self.memories = memories or (lambda: [])
        self.audit = audit or (lambda *a, **k: None)
        self.hush = hush
        self.stations = []
        self.playing = None

    # -- small helpers --------------------------------------------------------------------------------------------
    @property
    def zone(self):
        zone = self._zone() if callable(self._zone) else self._zone
        return zone if isinstance(zone, ZoneInfo) else ZoneInfo(str(zone))

    def _now(self):
        return datetime.fromtimestamp(self.clock(), self.zone)

    def _kids(self):
        return self.mode() == "kids"

    def _scope(self):
        return "kids" if self._kids() else "adult"

    def _rows(self, kind):
        return [r for r in self.store.all(kind, 2000) if r.get("scope", "adult") == self._scope()]

    # -- the one way in -------------------------------------------------------------------------------------------
    def stopping(self, low):
        """"stop", "snooze", "I'm up": for a ringing alarm or what's playing, before "stop" means "hush"."""
        low = (low or "").strip().lower()
        if self.ringing():
            if SNOOZE.match(low): return self.snooze()
            if UP.match(low): return self.stop_alarm()
        if self.player and self.player.busy() and (STOP_SOUND.match(low) or re.fullmatch(LEAD + r"(?:pause|shh+|quiet|enough)" + END, low)):
            return self.stop_playing(paused=low.startswith("pause"))
        return None

    def handle(self, text, lowered=None):
        """A reply for an everyday command, or None when this isn't one."""
        text = " ".join(str(text or "").split())
        if not text or len(text) > 300: return None
        low = (lowered or text).strip().lower()
        if self.ringing():
            if SNOOZE.match(low): return self.snooze()
            if UP.match(low): return self.stop_alarm()
        m = ROUTINE.match(low)
        if m: return self.routine(m)
        for step in (self._alarm_cmd, self._list_cmd, self._watch_cmd, self._sound_cmd, self._volume_cmd, self._dnd_cmd, self._quick,
                     self._home_cmd, self._music_cmd):
            out = step(text, low)
            if out is not None: return out
        return None

    # -- alarms ---------------------------------------------------------------------------------------------------
    def _next_ring(self, hour, minute, days, after, tomorrow=False, meridiem=True):
        now = datetime.fromtimestamp(after, self.zone)
        candidates = []
        hours = [hour] if meridiem else [hour % 12, hour % 12 + 12]
        for h in hours:
            for ahead in range(0, 8):
                day = now.date() + timedelta(days=ahead)
                if tomorrow and day != now.date() + timedelta(days=1): continue
                if days and day.weekday() not in days: continue
                at = datetime(day.year, day.month, day.day, h, minute, tzinfo=self.zone)
                if at.timestamp() > after + 1: candidates.append(at); break
        if not candidates: raise ValueError("I couldn't find when that alarm would go off.")
        return min(candidates)

    def _alarm_cmd(self, text, low):
        m = ALARM_SET.match(low) or ALARM_SET2.match(low) or ALARM_SET3.match(low) or ALARM_SET4.match(low)
        if m:
            try:
                hour, minute, meridiem = clock_of(m)
            except ValueError as error:
                return {"text": str(error), "section": "alarms"}
            days = days_of(m["days"]) if "days" in m.groupdict() else []
            label = (m["label"] if "label" in m.groupdict() else None) or ""
            return self.set_alarm(hour, minute, days, label, meridiem)
        if ALARM_LIST.match(low): return self.list_alarms()
        m = ALARM_OFF.match(low)
        if m: return self.cancel_alarms(m)
        if SNOOZE.match(low) and self._last_rang_recently(): return self.snooze()
        return None

    def set_alarm(self, hour, minute, days, label="", meridiem=True):
        label = label.strip(" ,.")
        if label: reject_payment_secrets(label)
        tomorrow = days == "tomorrow"
        repeat = [] if tomorrow else sorted(set(days))
        ring = self._next_ring(hour, minute, repeat, self.clock(), tomorrow, meridiem)
        alarms = [r for r in self._rows("alarm") if r.get("on")]
        if len(alarms) >= 30: return {"text": "You've got thirty alarms already. Let's clear a few out first.", "section": "alarms"}
        for r in alarms:
            if r["hour"] == ring.hour and r["minute"] == ring.minute and r.get("days", []) == repeat:
                return {"text": f"You've already got one for {say_clock(ring)}{' ' + say_days(repeat) if repeat else ''}. It's still set.", "section": "alarms", "alarm": r}
        row = {"id": uuid.uuid4().hex[:12], "hour": ring.hour, "minute": ring.minute, "days": repeat, "label": label[:40], "on": True,
               "next": ring.timestamp(), "rang_at": None, "scope": self._scope()}
        self.store.put("alarm", row, row["id"])
        when = self._when(ring)
        what = f" for {label}" if label else ""
        if repeat:
            said = f"Alarm set{what}: {say_clock(ring)} {say_days(repeat)}. The first one's {when}."
        else:
            said = f"Alarm set{what} for {say_clock(ring)} {when}."
        left = ring.timestamp() - self.clock()
        if not repeat and 3600 * 3 < left and ring.hour < 11:
            hours = left / 3600
            said += f" That's about {_nice(round(hours * 2) / 2)} hours from now."
        return {"text": said, "section": "alarms", "alarm": row}

    def _when(self, ring):
        today = self._now().date()
        if ring.date() == today: return "today" if ring.hour < 17 else "tonight"
        if ring.date() == today + timedelta(days=1): return "tomorrow" + (" morning" if ring.hour < 12 else "")
        return "on " + ring.strftime("%A")

    def list_alarms(self):
        alarms = sorted([r for r in self._rows("alarm") if r.get("on")], key=lambda r: r["next"])
        if not alarms: return {"text": "No alarms set. Want one?", "section": "alarms", "alarms": []}
        bits = []
        for r in alarms[:6]:
            ring = datetime.fromtimestamp(r["next"], self.zone)
            bits.append(f"{say_clock(ring)} {say_days(r['days']) if r['days'] else self._when(ring)}" + (f" ({r['label']})" if r.get("label") else ""))
        head = "One alarm: " if len(alarms) == 1 else f"{len(alarms)} alarms: "
        return {"text": head + "; ".join(bits) + ("; and more" if len(alarms) > 6 else "") + ".", "section": "alarms", "alarms": alarms}

    def cancel_alarms(self, m):
        alarms = [r for r in self._rows("alarm") if r.get("on")]
        if not alarms: return {"text": "There aren't any alarms to cancel.", "section": "alarms"}
        group = m.groupdict()
        if group.get("clock") or group.get("xclock"):
            fake = {k[1:] if k.startswith("x") else k: v for k, v in group.items() if (k.startswith("x") if group.get("xclock") else not k.startswith("x"))}
            try: hour, minute, meridiem = clock_of(fake)
            except ValueError: return {"text": "Which alarm? Tell me its time.", "section": "alarms"}
            hit = [r for r in alarms if r["minute"] == minute and (r["hour"] == hour or (not meridiem and r["hour"] % 12 == hour % 12))]
            if not hit: return {"text": f"I don't see an alarm at {say_clock(datetime(2000, 1, 1, hour, minute))}. " + self.list_alarms()["text"], "section": "alarms"}
        elif group.get("all") or len(alarms) == 1 or "alarms" in m.group(0):
            hit = alarms
        else:
            soonest = min(alarms, key=lambda r: r["next"])
            hit = [soonest]
        for r in hit:
            self.store.put("alarm", {**r, "on": False, "ringing": False}, r["id"])
        if len(hit) == 1:
            ring = datetime.fromtimestamp(hit[0]["next"], self.zone)
            return {"text": f"Done, your {say_clock(ring)} alarm is off.", "section": "alarms"}
        return {"text": f"Done, all {len(hit)} alarms are off.", "section": "alarms"}

    def ringing(self):
        return next((r for r in self._rows("alarm") if r.get("ringing")), None)

    def _last_rang_recently(self):
        return any(r.get("rang_at") and self.clock() - r["rang_at"] < 30 * 60 for r in self._rows("alarm"))

    def snooze(self, minutes=None):
        minutes = minutes or self.SNOOZE_MIN
        row = self.ringing() or max((r for r in self._rows("alarm") if r.get("rang_at")), key=lambda r: r["rang_at"], default=None)
        if not row: return {"text": "Nothing's ringing.", "section": "alarms"}
        self.store.put("alarm", {**row, "ringing": False, "snooze_until": self.clock() + minutes * 60}, row["id"])
        if self.player: self._quiet_player()
        return {"text": f"Okay, {minutes} more minutes.", "section": "alarms"}

    def stop_alarm(self):
        row = self.ringing()
        if not row: return None
        self.store.put("alarm", {**row, "ringing": False, "snooze_until": None}, row["id"])
        if self.player: self._quiet_player()
        hour = self._now().hour
        return {"text": "Good morning. I'm here whenever you want to talk." if 4 <= hour < 12 else "Alarm's off.", "section": "alarms"}

    def _quiet_player(self):
        try:
            if self.playing and self.playing.get("kind") == "alarm":
                self.player.stop()
                self.playing = None
        except Exception:
            pass

    def due(self):
        """Alarms going off right now: what to say, once a minute while one rings. Called by the agent's tick."""
        now = self.clock()
        said = []
        for row in self._rows("alarm"):
            if not row.get("on") and not row.get("ringing") and not row.get("snooze_until"): continue
            if row.get("ringing"):
                if now - row["rang_at"] > self.RING_FOR:
                    self.store.put("alarm", {**row, "ringing": False}, row["id"])
                elif now - row.get("said_at", 0) >= self.RING_EVERY:
                    self.store.put("alarm", {**row, "said_at": now}, row["id"])
                    said.append(self._ring_words(row, again=True))
                continue
            if row.get("snooze_until") and now >= row["snooze_until"]:
                self.store.put("alarm", {**row, "ringing": True, "rang_at": now, "said_at": now, "snooze_until": None}, row["id"])
                said.append(self._ring_words(row, again=True))
                continue
            if row.get("on") and now >= row["next"]:
                if now - row["next"] > 3 * 3600:   # Luma was off when it should have rung: don't ring hours late
                    nxt = self._next_ring(row["hour"], row["minute"], row["days"], now) if row["days"] else None
                    self.store.put("alarm", {**row, "on": bool(nxt), "next": nxt.timestamp() if nxt else row["next"]}, row["id"])
                    continue
                nxt = self._next_ring(row["hour"], row["minute"], row["days"], now + 60) if row["days"] else None
                self.store.put("alarm", {**row, "on": bool(nxt), "next": nxt.timestamp() if nxt else row["next"], "ringing": True,
                                         "rang_at": now, "said_at": now}, row["id"])
                said.append(self._ring_words(row))
                if self.player and not self.playing:
                    try:
                        self.player.chime()
                    except Exception:
                        pass
        return [{"type": "alarm", "text": s, "created": now, "alarm": True} for s in said]

    def _ring_words(self, row, again=False):
        now = self._now()
        clock = say_clock(now)
        label = f" {row['label'][:1].upper() + row['label'][1:]}." if row.get("label") else ""
        if again: return f"It's {clock}.{label} Time to get up." if now.hour < 12 else f"It's {clock}.{label} Your alarm."
        if 4 <= now.hour < 12:
            return f"Good morning. It's {clock}.{label} Time to get up."
        return f"It's {clock}.{label} That's your alarm."

    # -- lists ----------------------------------------------------------------------------------------------------
    @staticmethod
    def list_name(word):
        w = word.lower().strip()
        if w in {"grocery", "groceries", "shopping", "food", "costco", "supermarket", "store"}: return "shopping"
        if re.fullmatch(r"to[- ]?do|todo|things to do|task", w): return "to-do"
        return re.sub(r"[^a-z' -]", "", w)[:30] or "shopping"

    @staticmethod
    def items_in(words):
        words = re.sub(r"\s+(?:and|&|plus)\s+", ", ", words.strip(), flags=re.I)
        out = []
        for bit in words.split(","):
            bit = re.sub(r"^(?:some|a|an|the|more|another|a few|a couple of|a pack of|a bag of)\s+", "", bit.strip(" .!"), flags=re.I).strip()
            if bit and bit.lower() not in {"it", "that", "this", "them"} and len(bit) <= 80:
                out.append(bit)
        return out[:20]

    def _list_cmd(self, text, low):
        if LIST_ALL.match(low): return self.all_lists()
        m = LIST_CLEAR.match(low)
        if m: return self.clear_list(self.list_name(m["list"]))
        m = LIST_DROP.match(low)
        if m: return self.drop_items(self.list_name(m["list"]), self.items_in(_keep_case(text, m.start("items"), m.end("items"))))
        m = LIST_ADD.match(low) or LIST_ADD2.match(low)
        if m and not re.fullmatch(r"(?:me|you|us|him|her|them|someone|somebody|my name|your name)", m["items"].strip()):
            return self.add_items(self.list_name(m["list"]), self.items_in(_keep_case(text, m.start("items"), m.end("items"))))
        m = LIST_READ.match(low)
        if m and (m["list"] or "").lower() not in {"what", "this", "that", "a", "the"}: return self.read_list(self.list_name(m["list"]))
        return None

    def add_items(self, name, items):
        if not items: return {"text": f"What should I put on your {name} list?", "section": "lists"}
        for item in items: reject_payment_secrets(item)
        have = {r["item"].lower() for r in self._rows("list_item") if r["list"] == name and not r.get("done")}
        added = [i for i in items if i.lower() not in have]
        if len(have) + len(added) > 300: return {"text": f"Your {name} list is full. Let's clear some of it.", "section": "lists"}
        for n, item in enumerate(added):
            row = {"id": uuid.uuid4().hex[:12], "list": name, "item": item, "done": False, "at": self.clock() + n / 1000, "scope": self._scope()}
            self.store.put("list_item", row, row["id"])
        if not added:
            return {"text": f"{_join(items)} {'is' if len(items) == 1 else 'are'} already on your {name} list.", "section": "lists"}
        tail = f" (already had {_join([i for i in items if i not in added])})" if len(added) < len(items) else ""
        return {"text": f"Added {_join(added)} to your {name} list{tail}.", "section": "lists", "list": name, "added": added}

    def read_list(self, name):
        rows = sorted([r for r in self._rows("list_item") if r["list"] == name and not r.get("done")], key=lambda r: r["at"])
        if not rows: return {"text": f"Your {name} list is empty.", "section": "lists", "list": name, "items": []}
        items = [r["item"] for r in rows]
        head = f"One thing on your {name} list: " if len(items) == 1 else f"{len(items)} things on your {name} list: "
        return {"text": head + _join(items[:25]) + (f", and {len(items) - 25} more" if len(items) > 25 else "") + ".", "section": "lists", "list": name, "items": items}

    def drop_items(self, name, items):
        rows = [r for r in self._rows("list_item") if r["list"] == name and not r.get("done")]
        gone = []
        for item in items:
            hit = next((r for r in rows if r["item"].lower() == item.lower()), None) or next((r for r in rows if item.lower() in r["item"].lower()), None)
            if hit:
                self.store.delete("list_item", hit["id"])
                rows.remove(hit)
                gone.append(hit["item"])
        if not gone: return {"text": f"I don't see {_join(items)} on your {name} list.", "section": "lists"}
        return {"text": f"Took {_join(gone)} off your {name} list.", "section": "lists", "removed": gone}

    def clear_list(self, name):
        rows = [r for r in self._rows("list_item") if r["list"] == name]
        for r in rows: self.store.delete("list_item", r["id"])
        return {"text": f"Cleared your {name} list." if rows else f"Your {name} list was already empty.", "section": "lists"}

    def all_lists(self):
        counts = {}
        for r in self._rows("list_item"):
            if not r.get("done"): counts[r["list"]] = counts.get(r["list"], 0) + 1
        if not counts: return {"text": "No lists yet. Try \"add milk to my shopping list.\"", "section": "lists"}
        return {"text": "Your lists: " + _join([f"{name} ({n})" for name, n in sorted(counts.items())]) + ".", "section": "lists", "lists": counts}

    # -- stopwatch ------------------------------------------------------------------------------------------------
    def _watch_cmd(self, text, low):
        m = WATCH.match(low)
        if not m: return None
        act = (m["act"] or "how").lower()
        key = "stopwatch:" + self._scope()
        state = self.store.setting(key, {}) or {}
        now = self.clock()
        if act in {"start", "restart", "resume"}:
            if act == "resume" and state.get("stopped") is not None:
                state = {"started": now - state["stopped"], "stopped": None}
            elif act == "start" and state.get("started") and state.get("stopped") is None:
                return {"text": f"It's already going: {_span(now - state['started'])}.", "section": "stopwatch"}
            else:
                state = {"started": now, "stopped": None}
            self.store.set_setting(key, state)
            return {"text": "Stopwatch going." if act != "resume" else "Going again.", "section": "stopwatch"}
        if not state.get("started"): return {"text": "There's no stopwatch running. Say \"start a stopwatch.\"", "section": "stopwatch"}
        ran = state["stopped"] if state.get("stopped") is not None else now - state["started"]
        if act in {"stop", "pause"}:
            self.store.set_setting(key, {"started": state["started"], "stopped": ran})
            return {"text": f"Stopped at {_span(ran)}.", "section": "stopwatch"}
        if act == "reset":
            self.store.set_setting(key, {})
            return {"text": f"Reset. It had {_span(ran)} on it.", "section": "stopwatch"}
        return {"text": f"{_span(ran)}{' and counting' if state.get('stopped') is None else ', stopped'}.", "section": "stopwatch"}

    # -- quick answers --------------------------------------------------------------------------------------------
    def _quick(self, text, low):
        m = TIME_ASK.match(low)
        if m:
            place = (m["place"] or "").strip()
            if place and place not in {"here", "this house", "the house"}:
                zone = place_zone(place)
                if not zone: return {"text": f"I don't know what time zone {place} is in. Try a city or a state.", "section": "time"}
                there = datetime.fromtimestamp(self.clock(), ZoneInfo(zone))
                here = self._now()
                gap = (there.utcoffset() - here.utcoffset()).total_seconds() / 3600
                rel = "" if not gap else f", {_nice(abs(gap))} hours {'ahead of' if gap > 0 else 'behind'} you"
                day = "" if there.date() == here.date() else (" tomorrow" if there.date() > here.date() else " yesterday")
                return {"text": f"It's {say_clock(there)}{day} in {_title(place)}{rel}.", "section": "time"}
            return {"text": f"It's {say_clock(self._now())}.", "section": "time"}
        if DATE_ASK.match(low):
            now = self._now()
            return {"text": f"It's {now.strftime('%A, %B')} {now.day}.", "section": "time"}
        m = UNTIL.match(low)
        if m: return self.until(m["what"], m["unit"])
        out = convert(low)
        if out: return {**out, "section": "convert"}
        if COIN.match(low):
            return {"text": "Heads." if self.rng.random() < 0.5 else "Tails.", "section": "games"}
        m = DICE.match(low)
        if m:
            n = m["n2"] or m["n"] or "1"
            n = int(n) if n.isdigit() else int(_NUM.get(n, 1))
            sides = int(m["sides"] or m["sides2"] or 6)
            if not (1 <= n <= 10 and 2 <= sides <= 1000): return {"text": "Up to ten dice, two to a thousand sides.", "section": "games"}
            rolls = [self.rng.randint(1, sides) for _ in range(n)]
            return {"text": (f"{rolls[0]}." if n == 1 else f"{_join([str(r) for r in rolls])}. That's {sum(rolls)}."), "section": "games", "rolls": rolls}
        m = PICK.match(low)
        if m:
            lo, hi = sorted((int(m["lo"]), int(m["hi"])))
            return {"text": f"{self.rng.randint(lo, hi)}.", "section": "games"}
        m = SPELL.match(low)
        if m and not re.fullmatch(r"(?:it|that|this|them|something|words?|my name|your name)", m["word"]):
            word = m["word"]
            return {"text": f"{word.capitalize()}: " + "-".join(c.upper() for c in word if c.isalpha()) + ".", "section": "spelling"}
        return None

    def until(self, what, unit="days"):
        today = self._now().date()
        what = what.strip().rstrip("?.! ")
        when = None
        bday = re.fullmatch(r"(?P<who>my|mom'?s|dad'?s|my (?:mom|dad|sister|brother|wife|husband|son|daughter|partner|best friend)'?s|[a-z]+'s) birthday", what.lower())
        if bday:
            who = bday["who"].replace("my ", "").replace("'s", "").replace("’s", "")
            said = _birthday(self.memories(), "my" if who in {"my", "mine"} else who)
            if not said:
                return {"text": "I don't know that birthday yet. Tell me, like \"my birthday is June 3,\" and I'll keep it.", "section": "time"}
            when = _date_in(said, today)
        else:
            when = _date_in(what, today)
        if not when: return None
        days = (when - today).days
        name = _title(what)
        if days == 0: return {"text": f"{name} is today!", "section": "time"}
        if days == 1: return {"text": f"Just one more day until {name}. It's tomorrow.", "section": "time"}
        if unit.lower() == "weeks":
            return {"text": f"{_nice(days / 7)} weeks until {name} ({days} days, on {when.strftime('%A, %B')} {when.day}).", "section": "time"}
        word = "sleeps" if unit.lower() == "sleeps" else "days"
        return {"text": f"{days} {word} until {name}. That's {when.strftime('%A, %B')} {when.day}.", "section": "time", "days": days}

    # -- volume ---------------------------------------------------------------------------------------------------
    def volume(self):
        return int(self.store.setting("volume", 8))

    def _volume_cmd(self, text, low):
        m = VOLUME.match(low)
        if not m: return None
        now = self.volume()
        if m["ask"]: return {"text": f"Volume's at {now}.", "section": "volume", "volume": now}
        if m["up"]: level = min(10, now + 2)
        elif m["down"]: level = max(1, now - 2)
        else:
            to = m["to"].lower()
            level = 10 if to in {"ten", "max", "maximum"} else 1 if to in {"min", "minimum"} else 5 if to == "half" else int(to)
            if level > 10: level = 10 if level <= 100 and level % 10 else level // 10
            level = max(0, min(10, level))
        self.store.set_setting("volume", level)
        from luma.audio import loudness
        loudness.set_level(level)
        if self.player:
            try: self.player.set_volume(level)
            except Exception: pass
        said = "Okay." if level == now else ("Louder" if level > now else "Quieter") + f": {level}."
        if level == 10 and now == 10: said = "That's as loud as I go."
        if level == 0: said = "Volume's all the way down. Say \"volume up\" to hear me again."
        return {"text": said, "section": "volume", "volume": level}

    # -- do not disturb -------------------------------------------------------------------------------------------
    def _dnd_cmd(self, text, low):
        m = DND.match(low)
        if not m: return None
        if self._kids(): return {"text": "That one's for a grown-up to change.", "section": "quiet"}
        if m["off"] or low.startswith("do not disturb off"):
            self.store.set_setting("hush_until", 0)
            return {"text": "Do not disturb is off. I'm around.", "section": "quiet"}
        n = m["n"]
        minutes = 60
        if n:
            amount = int(n) if n.isdigit() else int(_NUM.get(n, 1))
            minutes = amount * (60 if m["unit"].lower().startswith("hour") else 1)
        minutes = max(1, min(1440, minutes))
        if self.hush: self.hush(minutes)
        else: self.store.set_setting("hush_until", self.clock() + minutes * 60)
        until = datetime.fromtimestamp(self.clock() + minutes * 60, self.zone)
        return {"text": f"Do not disturb until {say_clock(until)}. Alarms and timers still go off.", "section": "quiet"}

    # -- sleep sounds ---------------------------------------------------------------------------------------------
    def _sound_cmd(self, text, low):
        m = SOUND.match(low)
        kind = None
        if m:
            what = m["what"].lower()
            kind = next(name for name, pattern in SOUNDS.items() if re.fullmatch(pattern, what))
        elif SLEEP.match(low):
            kind = "rain"
        if not kind: return None
        minutes = 60
        if m and m["n"]:
            amount = 0.5 if m["n"].lower().startswith("half") else int(m["n"]) if m["n"].isdigit() else _NUM.get(m["n"].lower(), 1)
            minutes = amount * (60 if m["unit"].lower().startswith("hour") else 1)
        minutes = max(1, min(600, int(minutes)))
        if not self.player:
            return None   # no speaker here: what Luma already does on a computer (YouTube Music) takes it
        try: self.player.sound(kind, minutes * 60)
        except Exception: return {"text": "My speaker isn't working right now, so I can't play that.", "section": "sounds"}
        self.playing = {"kind": "sound", "name": kind, "until": self.clock() + minutes * 60}
        long = "an hour" if minutes == 60 else f"{minutes // 60} hours" if minutes % 60 == 0 else f"{minutes} minutes"
        return {"text": f"{kind.capitalize()}, for {long}. Sleep well." if self._now().hour >= 20 or self._now().hour < 5 else f"{kind.capitalize()}, for {long}.",
                "section": "sounds", "sound": {"kind": kind, "minutes": minutes}}

    # -- music ----------------------------------------------------------------------------------------------------
    def _music_cmd(self, text, low):
        if self.player and self.player.busy():
            if STOP_SOUND.match(low) and not re.fullmatch(LEAD + r"stop" + END, low) or re.fullmatch(LEAD + r"stop" + END, low):
                return self.stop_playing()
            if NEXT.match(low) and self.playing and self.playing.get("kind") == "radio": return self.next_station()
            if NOW.match(low) and self.playing: return self.now_playing()
            if re.fullmatch(LEAD + r"pause(?: (?:it|the music|that))?" + END, low):
                return self.stop_playing(paused=True)
        if RESUME.match(low) and self.playing and self.player and not self.player.busy():
            return self._replay()
        m = PLAY.match(low)
        if not m: return None
        what = m["what"].strip()
        if NOT_MUSIC.search(what) and not re.search(r"\b(?:music|radio|station|songs?)\b", what): return None
        musical = re.search(r"\b(?:music|radio|station|songs?|tunes|playlist|album|by)\b", what) or re.fullmatch(r"(?:" + GENRES + r")(?: music)?", what)
        local = self._local_music(what)
        if not musical and not local: return None
        if self._kids() and not local: return {"text": "Let's ask a grown-up to put music on.", "section": "music"}
        if not self.player:
            return None   # no speaker here: what Luma already does on a computer (YouTube Music) takes it
        if local:
            try: self.player.play_files(local)
            except RuntimeError as error: return {"text": str(error), "section": "music"}
            self.playing = {"kind": "files", "name": what, "files": local}
            return {"text": f"Playing {_title(what)}." if len(local) == 1 else f"Playing {len(local)} of your songs: {_title(what)}.", "section": "music"}
        if not self.on("music"):
            return {"text": "I can put on the radio for that once you turn on Music in my settings. Only what you ask to play (like \"jazz\") goes to a free radio directory.",
                    "section": "music", "needs": "music"}
        if not self.fetch: return {"text": "The radio isn't reachable right now.", "section": "music"}
        self.stations = radio_search(self.fetch, what)
        if not self.stations: return {"text": f"I couldn't find a station for {what}. Try a genre, like jazz or city pop.", "section": "music"}
        station = self.stations.pop(0)
        try: self.player.stream(station["url"])
        except RuntimeError as error: return {"text": str(error), "section": "music"}
        self.playing = {"kind": "radio", "name": station["name"], "url": station["url"], "asked": what}
        self.audit("Played the radio", "music.radio", {"asked": what, "station": station["name"]}, "read")
        return {"text": f"Here's {station['name']}.", "section": "music", "station": station["name"]}

    def _local_music(self, what):
        """Songs in their own music folder that match what they asked (by file name). Nothing leaves the home."""
        import os
        from pathlib import Path
        folder = self.env.get("LUMA_MUSIC_DIR") or os.path.expanduser("~/Music")
        root = Path(folder)
        if not root.is_dir(): return []
        words = [w for w in re.findall(r"[a-z0-9]+", what.lower()) if w not in {"some", "my", "music", "songs", "song", "by", "the", "a", "me", "playlist", "album"}]
        if not words and not re.search(r"\bmy (?:music|songs|playlist)\b", what.lower()): return []
        found = []
        for path in root.rglob("*"):
            if len(found) >= 200: break
            if path.suffix.lower() not in {".mp3", ".m4a", ".flac", ".wav", ".ogg", ".aac", ".opus"}: continue
            name = " ".join(re.findall(r"[a-z0-9]+", str(path.relative_to(root)).lower()))
            if all(w in name for w in words): found.append(str(path))
        if found and not words:
            self.rng.shuffle(found)
        return sorted(found)[:100] if words else found[:100]

    def stop_playing(self, paused=False):
        what = self.playing
        try: self.player.stop()
        except Exception: pass
        if not paused: self.playing = None
        else: self.playing = {**(what or {}), "paused": True}
        return {"text": "Paused." if paused else "Okay.", "section": "music"}

    def _replay(self):
        what = self.playing or {}
        if what.get("kind") == "radio": self.player.stream(what["url"])
        elif what.get("kind") == "files": self.player.play_files(what["files"])
        elif what.get("kind") == "sound": self.player.sound(what["name"], max(60, int(what.get("until", 0) - self.clock())))
        else: return None
        self.playing = {k: v for k, v in what.items() if k != "paused"}
        return {"text": "Back on.", "section": "music"}

    def next_station(self):
        if not self.stations: return {"text": "That's the last one I found. Want a different kind?", "section": "music"}
        station = self.stations.pop(0)
        self.player.stream(station["url"])
        self.playing = {**self.playing, "name": station["name"], "url": station["url"]}
        return {"text": f"Here's {station['name']}.", "section": "music"}

    def now_playing(self):
        what = self.playing or {}
        if what.get("kind") == "radio": return {"text": f"That's {what['name']}, on the radio.", "section": "music"}
        if what.get("kind") == "files": return {"text": f"Your songs: {what['name']}.", "section": "music"}
        if what.get("kind") == "sound": return {"text": f"{what['name'].capitalize()} sounds.", "section": "music"}
        return {"text": "Nothing's playing.", "section": "music"}

    # -- the house ------------------------------------------------------------------------------------------------
    def allowed(self):
        names = (self.env.get("LUMA_ALLOWED_DEVICES", "") + "," + self.env.get("LUMA_ALLOWED_LIGHTS", "")).split(",")
        return sorted({n.strip() for n in names if re.fullmatch(r"(?:light|switch|fan|climate|lock|cover|scene|media_player|sensor)\.[a-z0-9_]+", n.strip())})

    def _home_ready(self):
        if self._kids(): return "kids"
        if not self.on("home_assistant"): return "off"
        if not (self.env.get("HOME_ASSISTANT_URL") and self.env.get("HOME_ASSISTANT_TOKEN") and self.allowed()): return "setup"
        return None

    def _home_cmd(self, text, low):
        # the commands, read first, so an ordinary sentence with "on" or "off" in it never reaches the house
        on = HOME_ON.match(low)
        dim = HOME_DIM.match(low)
        heat = HOME_HEAT.match(low)
        lock = HOME_LOCK.match(low)
        scene = HOME_SCENE.match(low)
        ask = HOME_ASK.match(low)
        if on:
            words = on["onoff4"] or ""
            state = "on" if (on["onoff"] or on["onoff2"] or on["onoff3"] or "").lower() == "on" or words.endswith(" on") or "hit the lights" in words else "off"
            thing = on["thing"] or on["thing2"] or on["thing3"] or "lights"
            if re.search(r"\b(?:alarm|alarms|do not disturb|mic|microphone|music|radio|rain|sounds?|noise|stopwatch|timer|volume)\b", thing): return None
            if not HOME_WORDS.search(thing) or len(thing.split()) > 5:
                on = None   # not a device: maybe "turn on movie night scene", or not about the house at all
                if not (scene or heat or lock): return None
        if dim:
            thing = dim["thing"] or dim["thing2"]
            if not thing or not re.search(r"\b(?:lights?|lamps?|bulbs?|leds?)\b", thing): return None
        elif not on and not (heat or lock or scene or ask):
            return None
        if ask and not lock and not (on or dim or heat or scene):
            thing = ask["thing"] or ""
            if thing and not (HOME_WORDS.search(thing) or re.search(r"\b(?:doors?|garage|gate|window|blinds|lock)\b", thing)): return None
        if scene and not (on or dim or heat or lock):
            name = (scene["scene"] or scene["scene2"] or "").strip()
            if name in {"do not disturb", "quiet", "silent", "kids", "friend", "study", "cofounder", "focus", "sleep", "airplane", "dark", "light"}: return None
        if lock and (lock["act"].lower() == "unlock" or (lock["act"].lower() in {"open", "raise"} and re.search(r"door|garage|gate", lock["thing"].lower()))):
            return {"text": "I don't unlock doors or open the garage from a sentence, for anyone. Use your Home Assistant app for that one.", "section": "home"}
        blocked = self._home_ready()
        if blocked == "kids": return {"text": "Ask a grown-up to do that one.", "section": "home"}
        if blocked == "off":
            return {"text": "I can do that once you connect your Home Assistant and turn on Home in my settings. Then just say it.", "section": "home", "needs": "home_assistant"}
        if blocked == "setup":
            return {"text": "Home is on, but I don't know your devices yet. Add your Home Assistant address, a token and the devices I may use in my settings.", "section": "home", "needs": "home_assistant"}
        allowed = self.allowed()
        if lock:
            act, thing = lock["act"].lower(), lock["thing"].lower()
            if act in {"unlock"} or (act in {"open", "raise"} and re.search(r"door|garage|gate", thing)):
                return {"text": "I don't unlock doors or open the garage from a sentence, for anyone. Use your Home Assistant app for that one.", "section": "home"}
            domain = {"lock"} if re.search(r"door|lock", thing) and act == "lock" else {"cover"}
            if act in {"close", "shut"} and re.search(r"door", thing) and not re.search(r"garage", thing): domain = {"cover"}
            hits = find_devices(thing, allowed, domain)
            if not hits: return self._unknown(thing, allowed)
            service = "lock/lock" if domain == {"lock"} else ("cover/open_cover" if act in {"open", "raise"} else "cover/close_cover")
            return self._call(service, hits, {}, ("Locked " if service == "lock/lock" else "Opening " if "open" in service else "Closing ") + _join([_words(h) for h in hits]) + ".")
        if heat:
            deg = int(heat["deg"])
            scale = (heat["scale"] or "").lower()[:1] or ("c" if deg < 40 else "f")
            if not (40 <= deg <= 90 if scale == "f" else 5 <= deg <= 32): return {"text": "That's outside what I'll set the thermostat to.", "section": "home"}
            hits = [e for e in allowed if e.startswith("climate.")]
            if not hits: return self._unknown("thermostat", allowed)
            return self._call("climate/set_temperature", hits[:1], {"temperature": deg}, f"Setting it to {deg}°{scale.upper()}.")
        if scene and not (on or dim):
            name = (scene["scene"] or scene["scene2"]).strip()
            hits = find_devices(name, allowed, {"scene"})
            if not hits: return self._unknown(name + " scene", allowed)
            return self._call("scene/turn_on", hits[:1], {}, f"{_title(name)}, coming up.")
        if ask and not (on or dim):
            return self._status(ask, allowed)
        if dim:
            thing = dim["thing"] or dim["thing2"]
            pct = int(dim["pct"] or dim["pct2"] or 0)
            direction = (dim["dir"] or "").lower()
            if not pct: pct = 30 if direction in {"dim", "lower", "bring down"} else 100
            pct = max(1, min(100, pct))
            hits = find_devices(thing, allowed, {"light"})
            if not hits: return self._unknown(thing, allowed)
            return self._call("light/turn_on", hits, {"brightness_pct": pct}, f"{_title(_join([_words(h) for h in hits]))} at {pct}%.")
        hits = find_devices(thing, allowed, {"light", "switch", "fan", "media_player"})
        if not hits: return self._unknown(thing, allowed)
        groups = {}
        for h in hits: groups.setdefault(h.split(".")[0], []).append(h)
        done = []
        for domain, ids in groups.items():
            out = self._call(f"{domain}/turn_{state}", ids, {}, "")
            if out.get("failed"): return out
            done += ids
        names = [_words(h) for h in done]
        if len(names) > 3 and all(h.startswith("light.") for h in done): said = f"All the lights {state}."
        else: said = f"{_title(_join(names))} {state}."
        return {"text": said, "section": "home", "devices": done}

    def _unknown(self, thing, allowed):
        names = _join([_words(e) for e in allowed[:8]])
        return {"text": f"I don't know which device \"{thing}\" is. The ones I can use: {names}.", "section": "home"}

    def _call(self, service, ids, extra, said):
        from urllib.parse import urlsplit
        base = self.env["HOME_ASSISTANT_URL"].rstrip("/")
        u = urlsplit(base)
        if u.scheme not in {"http", "https"} or u.username or u.password or u.query or u.fragment:
            return {"text": "The Home Assistant address in my settings doesn't look right.", "section": "home", "failed": True}
        if u.scheme == "http" and not _local_host(u.hostname or ""):
            return {"text": "Your Home Assistant needs an https address unless it's on your home network.", "section": "home", "failed": True}
        payload = {"entity_id": ids if len(ids) > 1 else ids[0], **extra}
        try:
            self.fetch("POST", base + "/api/services/" + service, {"Authorization": "Bearer " + self.env["HOME_ASSISTANT_TOKEN"]}, payload)
        except Exception:
            self.audit("Asked the house", "home.control", {"service": service, "devices": ",".join(ids)}, "act", action="failed")
            return {"text": "Home Assistant didn't answer, so I'm not sure that happened. Check it in the app.", "section": "home", "failed": True}
        self.audit("Asked the house", "home.control", {"service": service, "devices": ",".join(ids)}, "act", action="done", came_from="owner said it")
        return {"text": said, "section": "home", "devices": ids}

    def _status(self, ask, allowed):
        base = self.env["HOME_ASSISTANT_URL"].rstrip("/")
        thing = ask["thing"]
        if not thing:
            hits = [e for e in allowed if e.startswith("climate.")] or [e for e in allowed if e.startswith("sensor.") and "temp" in e]
        else:
            hits = find_devices(thing, allowed)
        if not hits: return self._unknown(thing or "thermostat", allowed)
        try:
            state = self.fetch("GET", base + "/api/states/" + hits[0], {"Authorization": "Bearer " + self.env["HOME_ASSISTANT_TOKEN"]})
        except Exception:
            return {"text": "Home Assistant didn't answer just now.", "section": "home"}
        value = str((state or {}).get("state", "unknown"))
        attrs = (state or {}).get("attributes") or {}
        if not thing:
            temp = attrs.get("current_temperature", value)
            return {"text": f"It's {temp} degrees inside.", "section": "home"}
        return {"text": f"{_title(_words(hits[0]))} is {value}.", "section": "home"}

    # -- routines -------------------------------------------------------------------------------------------------
    def routine(self, m):
        now = self._now()
        if m["morning"]:
            bits = [f"Morning. It's {say_clock(now)}, {now.strftime('%A')}."]
            ring = self.ringing()
            if ring: self.store.put("alarm", {**ring, "ringing": False}, ring["id"])
            todo = self.read_list("to-do")
            if todo.get("items"): bits.append(todo["text"])
            return {"text": " ".join(bits), "section": "routine", "routine": "morning", "then": ["weather", "briefing"]}
        bits = []
        if self._home_ready() is None:
            lights = [e for e in self.allowed() if e.startswith("light.")]
            if lights:
                out = self._call("light/turn_off", lights, {}, "")
                if not out.get("failed"): bits.append("Lights are off.")
        nxt = sorted([r for r in self._rows("alarm") if r.get("on")], key=lambda r: r["next"])
        if nxt:
            ring = datetime.fromtimestamp(nxt[0]["next"], self.zone)
            bits.append(f"Your alarm's set for {say_clock(ring)}.")
        else:
            bits.append("No alarm set for the morning.")
        bits.append("Sleep well. I'll be right here.")
        return {"text": " ".join(bits), "section": "routine", "routine": "night"}


# -- little helpers -------------------------------------------------------------------------------------------------
def _keep_case(text, start, end):
    """The words they said, as they said them (the match was made on lowercase of the same text)."""
    return text[start:end] if len(text) >= end else text


def _join(items):
    items = [str(i) for i in items if str(i)]
    if len(items) <= 1: return "".join(items)
    if len(items) == 2: return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _span(seconds):
    seconds = int(max(0, seconds))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    parts = [f"{h} hour{'s' if h != 1 else ''}"] if h else []
    if m: parts.append(f"{m} minute{'s' if m != 1 else ''}")
    if s or not parts: parts.append(f"{s} second{'s' if s != 1 else ''}")
    return " ".join(parts)


def _title(words):
    small = {"of", "the", "and", "in", "on", "a"}
    out = []
    for i, w in enumerate(str(words).split()):
        out.append(w if (i and w in small) or not w[:1].isalpha() or w.isupper() else w[:1].upper() + w[1:])
    return " ".join(out)


def _local_host(host):
    import ipaddress
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return host == "localhost" or host.endswith(".local") or host.endswith(".lan") or host.endswith(".home.arpa")


WORLD = {"tokyo": "Asia/Tokyo", "japan": "Asia/Tokyo", "osaka": "Asia/Tokyo", "kyoto": "Asia/Tokyo", "yokohama": "Asia/Tokyo", "okinawa": "Asia/Tokyo",
         "seoul": "Asia/Seoul", "korea": "Asia/Seoul", "south korea": "Asia/Seoul", "beijing": "Asia/Shanghai", "shanghai": "Asia/Shanghai",
         "china": "Asia/Shanghai", "hong kong": "Asia/Hong_Kong", "taipei": "Asia/Taipei", "taiwan": "Asia/Taipei", "manila": "Asia/Manila",
         "philippines": "Asia/Manila", "singapore": "Asia/Singapore", "bangkok": "Asia/Bangkok", "thailand": "Asia/Bangkok", "vietnam": "Asia/Ho_Chi_Minh",
         "india": "Asia/Kolkata", "delhi": "Asia/Kolkata", "mumbai": "Asia/Kolkata", "dubai": "Asia/Dubai", "paris": "Europe/Paris",
         "france": "Europe/Paris", "madrid": "Europe/Madrid", "spain": "Europe/Madrid", "rome": "Europe/Rome", "italy": "Europe/Rome",
         "amsterdam": "Europe/Amsterdam", "dublin": "Europe/Dublin", "ireland": "Europe/Dublin", "lisbon": "Europe/Lisbon", "moscow": "Europe/Moscow",
         "sydney": "Australia/Sydney", "melbourne": "Australia/Melbourne", "australia": "Australia/Sydney", "auckland": "Pacific/Auckland",
         "new zealand": "Pacific/Auckland", "mexico city": "America/Mexico_City", "mexico": "America/Mexico_City", "sao paulo": "America/Sao_Paulo",
         "brazil": "America/Sao_Paulo", "utc": "UTC", "gmt": "UTC", "zulu": "UTC"}


def place_zone(place):
    from luma.agent import hometime
    p = place.lower().strip().strip(".?! ")
    p = re.sub(r"^(?:the )?", "", p) if p not in {"the uk", "the bay"} else p
    return WORLD.get(p) or hometime._PLACE.get(p) or hometime._PLACE.get("the " + p)
