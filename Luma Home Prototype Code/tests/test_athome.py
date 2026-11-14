"""What a speaker in the home does (alarms, lists, the time anywhere, conversions, volume, sleep sounds, music, the
lights), done by Luma: each command answered by code, in her own words, and nothing else she hears mistaken for one."""
import json
import random
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from luma.agent import athome
from luma.agent.athome import AtHome
from luma.memory.store import Store

TOKYO = ZoneInfo("Asia/Tokyo")
ROOT = Path(__file__).resolve().parents[1]


class FakePlayer:
    def __init__(self):
        self.calls = []
        self.on = False

    def busy(self): return self.on
    def set_volume(self, level): self.calls.append(("volume", level))
    def stop(self): self.calls.append(("stop",)); self.on = False
    def chime(self): self.calls.append(("chime",))
    def sound(self, kind, seconds): self.calls.append(("sound", kind, seconds)); self.on = True
    def stream(self, url): self.calls.append(("stream", url)); self.on = True
    def play_files(self, paths): self.calls.append(("files", list(paths))); self.on = True


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.store = Store(self.dir / "l.db", self.dir / "k.key")
        self.t = [datetime(2026, 11, 13, 22, 0, tzinfo=TOKYO).timestamp()]
        self.mode = "friend"
        self.switches = set()
        self.sent = []
        self.player = FakePlayer()
        self.env = {}
        self.home = AtHome(self.store, clock=lambda: self.t[0], zone=TOKYO, player=self.player, fetch=self.fetch, on=lambda s: s in self.switches,
                           env=self.env, mode=lambda: self.mode, rng=random.Random(7), memories=self.store.memories)

    def fetch(self, method, url, headers, payload=None):
        self.sent.append((method, url, payload))
        if "radio-browser" in url:
            return [{"name": "Smooth Jazz Tokyo", "url_resolved": "https://stream.example/jazz"}, {"name": "Jazz FM", "url": "https://stream.example/fm"}]
        if "/api/states/" in url:
            return {"state": "locked", "attributes": {"current_temperature": 21}}
        return []

    def say(self, line):
        return self.home.handle(line, line.lower())

    def at(self, y, mo, d, h, mi=0, s=0):
        self.t[0] = datetime(y, mo, d, h, mi, s, tzinfo=TOKYO).timestamp()


class Alarms(Base):
    def test_set_list_and_cancel(self):
        self.assertIn("7 AM tomorrow morning", self.say("set an alarm for 7am")["text"])
        self.assertIn("6:30 AM on weekdays", self.say("wake me up at 6:30 on weekdays")["text"])
        self.assertIn("8:15 PM", self.say("Luma, can you set an alarm for 8:15 pm on Sundays please")["text"])
        listed = self.say("what alarms do I have")
        self.assertEqual(len(listed["alarms"]), 3)
        self.assertIn("Done, your 7 AM alarm is off", self.say("cancel my 7 am alarm")["text"])
        self.assertIn("all 2 alarms are off", self.say("cancel all my alarms")["text"])
        self.assertIn("No alarms set", self.say("do i have any alarms")["text"])

    def test_no_am_or_pm_means_the_next_one(self):
        self.at(2026, 11, 13, 22)
        said = self.say("set an alarm for 6")["text"]
        self.assertIn("6 AM tomorrow", said)
        self.at(2026, 11, 14, 9)
        self.assertIn("6 PM", self.say("set an alarm for 6")["text"])

    def test_it_rings_snoozes_and_stops(self):
        self.say("set an alarm for 7am")
        self.at(2026, 11, 14, 6, 59)
        self.assertEqual(self.home.due(), [])
        self.at(2026, 11, 14, 7, 0, 3)
        rang = self.home.due()
        self.assertEqual(len(rang), 1)
        self.assertIn("Good morning. It's 7 AM. Time to get up.", rang[0]["text"])
        self.assertIn(("chime",), self.player.calls)
        self.assertIn("9 more minutes", self.say("snooze")["text"])
        self.at(2026, 11, 14, 7, 9, 10)
        self.assertIn("7:09 AM", self.home.due()[0]["text"])
        self.assertIn("Good morning", self.home.stopping("i'm up")["text"])
        self.at(2026, 11, 15, 7, 0, 5)
        self.assertEqual(self.home.due(), [], "a one-time alarm rings once")

    def test_one_left_ringing_says_it_again_then_lets_go(self):
        self.say("set an alarm for 7am")
        self.at(2026, 11, 14, 7, 0, 1)
        self.home.due()
        self.at(2026, 11, 14, 7, 1, 2)
        self.assertEqual(len(self.home.due()), 1)
        self.at(2026, 11, 14, 7, 20)
        self.home.due()
        self.assertIsNone(self.home.ringing())

    def test_weekday_alarms_come_back(self):
        self.say("wake me up at 6:30 on weekdays")
        self.at(2026, 11, 16, 6, 30, 5)   # a Monday
        self.assertEqual(len(self.home.due()), 1)
        self.home.stop_alarm()
        row = [r for r in self.store.all("alarm") if r["on"]][0]
        self.assertEqual(datetime.fromtimestamp(row["next"], TOKYO).strftime("%a %H:%M"), "Tue 06:30")

    def test_switched_off_overnight_it_does_not_ring_hours_late(self):
        self.say("set an alarm for 7am")
        self.at(2026, 11, 14, 13)
        self.assertEqual(self.home.due(), [])


class Lists(Base):
    def test_add_read_remove_and_clear(self):
        self.assertEqual(self.say("add milk, eggs and bread to my shopping list")["added"], ["milk", "eggs", "bread"])
        self.assertIn("already", self.say("put milk on the grocery list")["text"])
        self.assertIn("call the dentist", self.say("add call the dentist to my to-do list")["text"])
        self.assertEqual(self.say("what's on my shopping list")["items"], ["milk", "eggs", "bread"])
        self.assertIn("Took eggs off", self.say("take eggs off my shopping list")["text"])
        self.assertIn("shopping (2)", self.say("what lists do I have")["text"])
        self.assertIn("Cleared", self.say("clear my shopping list")["text"])
        self.assertIn("empty", self.say("read my shopping list")["text"])

    def test_kids_have_their_own_lists(self):
        self.say("add coffee to my shopping list")
        self.mode = "kids"
        self.assertIn("empty", self.say("what's on my shopping list")["text"])

    def test_a_card_number_is_never_kept(self):
        with self.assertRaises(ValueError):
            self.say("add 4242 4242 4242 4242 to my shopping list")


class QuickAnswers(Base):
    def test_time_here_and_where_their_people_are(self):
        self.assertEqual(self.say("what time is it")["text"], "It's 10 PM.")
        self.assertEqual(self.say("what time is it in ohio")["text"], "It's 8 AM in Ohio, 14 hours behind you.")
        self.assertIn("in London", self.say("what's the time in london")["text"])
        self.assertIn("don't know", self.say("what time is it in narnia")["text"])

    def test_date_and_days_until(self):
        self.assertEqual(self.say("what's the date")["text"], "It's Friday, November 13.")
        self.assertTrue(self.say("how many days until christmas")["text"].startswith("42 days until Christmas"))
        self.assertIn("Thursday, November 26", self.say("how many days until thanksgiving")["text"])
        self.assertIn("days until March 3", self.say("how many days until march 3")["text"])
        self.assertIn("don't know that birthday", self.say("how many days until my birthday")["text"])
        self.store.put("memory", {"text": "My birthday is June 3", "created": self.t[0]})
        self.assertIn("days until My Birthday", self.say("how many days until my birthday")["text"])

    def test_conversions_are_worked_out(self):
        self.assertEqual(self.say("how many cups in a liter")["text"], "1 liter is about 4.23 cups.")
        self.assertEqual(self.say("convert 70 degrees fahrenheit to celsius")["text"], "70 degrees Fahrenheit is about 21.1 degrees Celsius.")
        self.assertEqual(self.say("what's 5 miles in km")["text"], "5 miles is about 8.05 kilometers.")
        self.assertEqual(self.say("how many grams in a pound")["text"], "1 pound is about 454 grams.")
        self.assertIn("don't convert", self.say("convert 3 cups to miles")["text"])

    def test_coin_dice_numbers_and_spelling(self):
        self.assertIn(self.say("flip a coin")["text"], {"Heads.", "Tails."})
        rolled = self.say("roll two dice")
        self.assertEqual(len(rolled["rolls"]), 2)
        self.assertTrue(all(1 <= r <= 6 for r in rolled["rolls"]))
        self.assertTrue(1 <= self.say("roll a d20")["rolls"][0] <= 20)
        self.assertTrue(1 <= int(self.say("pick a number between 1 and 10")["text"].rstrip(".")) <= 10)
        self.assertEqual(self.say("how do you spell necessary")["text"], "Necessary: N-E-C-E-S-S-A-R-Y.")

    def test_stopwatch(self):
        self.assertEqual(self.say("start a stopwatch")["text"], "Stopwatch going.")
        self.t[0] += 95
        self.assertIn("1 minute 35 seconds", self.say("how long has the stopwatch been running")["text"])
        self.assertIn("Stopped at 1 minute 35 seconds", self.say("stop the stopwatch")["text"])


class VolumeAndQuiet(Base):
    def test_volume_follows_what_they_say(self):
        from luma.audio import loudness
        self.assertEqual(self.say("volume up")["volume"], 10)
        self.assertIn("as loud as I go", self.say("louder")["text"])
        self.assertEqual(self.say("set volume to 3")["volume"], 3)
        self.assertEqual(self.say("turn it down")["volume"], 1)
        self.assertEqual(self.say("volume 50 percent")["volume"], 5)
        self.assertEqual(loudness.level(), 5)
        loudness.set_level(8)
        self.assertAlmostEqual(loudness.gain(), 1.0, msg="8 is the loudness Luma always had")

    def test_do_not_disturb(self):
        self.say("do not disturb for 2 hours")
        self.assertAlmostEqual(self.store.setting("hush_until"), self.t[0] + 7200)
        self.say("turn off do not disturb")
        self.assertEqual(self.store.setting("hush_until"), 0)
        self.mode = "kids"
        self.assertIn("grown-up", self.say("do not disturb")["text"])


class Sounds(Base):
    def test_sleep_sounds_play_and_stop(self):
        out = self.say("play rain sounds for 30 minutes")
        self.assertEqual(out["sound"], {"kind": "rain", "minutes": 30})
        self.assertIn(("sound", "rain", 1800), self.player.calls)
        self.assertEqual(self.home.stopping("stop")["text"], "Okay.")
        self.assertFalse(self.player.on)
        self.assertEqual(self.say("play white noise")["sound"]["kind"], "white noise")
        self.assertEqual(self.say("help me sleep")["sound"]["kind"], "rain")

    def test_without_a_speaker_it_is_left_to_the_computer(self):
        self.home.player = None
        self.assertIsNone(self.say("play rain sounds"))
        self.assertIsNone(self.say("play some jazz"))

    def test_every_sound_is_made_here(self):
        from luma.audio.player import noise
        for kind in athome.SOUNDS:
            audio = noise(kind, 2, seed=1)
            self.assertEqual(len(audio), 48000, kind)
            self.assertLessEqual(float(abs(audio).max()), 1.0, kind)


class Music(Base):
    def test_the_radio_waits_for_the_switch_and_sends_only_what_they_asked(self):
        self.assertEqual(self.say("play some jazz")["needs"], "music")
        self.assertEqual(self.sent, [])
        self.switches.add("music")
        self.assertEqual(self.say("play some jazz")["text"], "Here's Smooth Jazz Tokyo.")
        self.assertIn(("stream", "https://stream.example/jazz"), self.player.calls)
        self.assertEqual(len(self.sent), 1)
        self.assertTrue(self.sent[0][1].startswith("https://de1.api.radio-browser.info/json/stations/bytag/jazz?"))
        self.assertEqual(self.say("next")["text"], "Here's Jazz FM.")
        self.assertIn("Jazz FM", self.say("what's playing")["text"])
        self.assertEqual(self.home.stopping("stop the music")["text"], "Okay.")

    def test_their_own_songs_need_nothing_from_outside(self):
        music = self.dir / "Music" / "Hikaru Utada"
        music.mkdir(parents=True)
        (music / "First Love.mp3").write_bytes(b"x")
        self.env["LUMA_MUSIC_DIR"] = str(self.dir / "Music")
        out = self.say("play first love by hikaru utada")
        self.assertIn("Playing", out["text"])
        self.assertEqual(self.sent, [])

    def test_games_and_pretend_are_not_music(self):
        self.switches.add("music")
        for line in ["play a game with me", "play 20 questions", "play devil's advocate", "let's play would you rather", "play it cool"]:
            self.assertIsNone(self.say(line), line)


class House(Base):
    def setUp(self):
        super().setUp()
        self.env.update({"HOME_ASSISTANT_URL": "http://192.168.1.20:8123", "HOME_ASSISTANT_TOKEN": "t",
                         "LUMA_ALLOWED_DEVICES": "light.living_room,light.bedroom_lamp,switch.kettle,climate.hallway,lock.front_door,scene.movie_night,cover.bedroom_blinds"})

    def test_waits_for_the_switch(self):
        self.assertEqual(self.say("turn off the living room lights")["needs"], "home_assistant")
        self.assertEqual(self.sent, [])

    def test_lights_switches_scenes_and_the_thermostat(self):
        self.switches.add("home_assistant")
        self.assertEqual(self.say("turn off the living room lights")["text"], "Living Room off.")
        self.assertEqual(self.sent[-1][1], "http://192.168.1.20:8123/api/services/light/turn_off")
        self.assertEqual(self.sent[-1][2], {"entity_id": "light.living_room"})
        self.say("lights off")
        self.assertEqual(self.sent[-1][2], {"entity_id": ["light.bedroom_lamp", "light.living_room"]})
        self.say("dim the bedroom lamp to 20%")
        self.assertEqual(self.sent[-1][2], {"entity_id": "light.bedroom_lamp", "brightness_pct": 20})
        self.say("turn on the kettle")
        self.assertEqual(self.sent[-1][1].rsplit("/", 2)[-2:], ["switch", "turn_on"])
        self.say("set the thermostat to 22")
        self.assertEqual(self.sent[-1][2], {"entity_id": "climate.hallway", "temperature": 22})
        self.say("turn on movie night scene")
        self.assertEqual(self.sent[-1][1].rsplit("/", 2)[-2:], ["scene", "turn_on"])
        self.say("lock the front door")
        self.assertEqual(self.sent[-1][1].rsplit("/", 2)[-2:], ["lock", "lock"])
        self.say("close the bedroom blinds")
        self.assertEqual(self.sent[-1][1].rsplit("/", 2)[-2:], ["cover", "close_cover"])
        self.assertIn("locked", self.say("is the front door locked")["text"])

    def test_never_unlocks_or_opens_the_garage(self):
        self.switches.add("home_assistant")
        for line in ["unlock the front door", "open the garage", "open the garage door", "unlock all the doors"]:
            self.assertIn("don't unlock", self.say(line)["text"], line)
        self.assertEqual(self.sent, [])

    def test_only_listed_devices_and_never_a_far_away_plain_address(self):
        self.switches.add("home_assistant")
        self.assertIn("don't know which device", self.say("turn on the garage lights")["text"])
        self.env["HOME_ASSISTANT_URL"] = "http://my-house.example.com"
        self.assertIn("https", self.say("turn off the living room lights")["text"])
        self.assertEqual(self.sent, [])

    def test_kids_cannot_run_the_house(self):
        self.switches.add("home_assistant")
        self.mode = "kids"
        self.assertIn("grown-up", self.say("turn off the living room lights")["text"])
        self.assertEqual(self.sent, [])

    def test_ordinary_sentences_with_on_and_off_are_not_commands(self):
        self.switches.add("home_assistant")
        for line in ["turn on the charm", "he turned off his phone", "turn off your brain for a sec", "switch off for the night",
                     "turn on unhinged mode", "turn on kids mode", "switch to study mode",
                     "I need to turn my life around", "put on a brave face"]:
            self.assertIsNone(self.say(line), line)


class Routines(Base):
    def test_bedtime_turns_off_the_lights_and_says_the_alarm(self):
        self.env.update({"HOME_ASSISTANT_URL": "http://192.168.1.20:8123", "HOME_ASSISTANT_TOKEN": "t", "LUMA_ALLOWED_DEVICES": "light.living_room"})
        self.switches.add("home_assistant")
        self.say("set an alarm for 7am")
        said = self.say("bedtime routine")["text"]
        self.assertIn("Lights are off.", said)
        self.assertIn("Your alarm's set for 7 AM.", said)
        self.assertIn("I'll be right here", said)


def _human_lines():
    rows = [json.loads(line) for line in (ROOT / "data" / "human_eval_v2.jsonl").read_text().splitlines() if line.strip()]
    for row in rows:
        if row.get("said"): yield row["said"]
        for turn in row.get("turns", []):
            if turn.get("said"): yield turn["said"]
    yield from re.findall(r'"said": "((?:[^"\\]|\\.)*)"', (ROOT / "scripts" / "train_luma.py").read_text())


class NothingElseIsACommand(Base):
    """What people say to a friend never sets off an alarm, a list or the house. Counts only: held-out lines are never printed."""

    def setUp(self):
        super().setUp()
        self.switches.update({"music", "home_assistant"})
        self.env.update({"HOME_ASSISTANT_URL": "http://192.168.1.20:8123", "HOME_ASSISTANT_TOKEN": "t", "LUMA_ALLOWED_DEVICES": "light.living_room"})

    def _hits(self, lines):
        hits = 0
        for line in lines:
            try:
                out = self.home.handle(line, line.lower())
            except ValueError:
                out = None
            hits += out is not None
        return hits

    def test_human_test_lines(self):
        lines = list(_human_lines())
        self.assertGreater(len(lines), 150)
        self.assertEqual(self._hits(lines), 0, "a human-test line was read as a home command")

    def test_crisis_lines(self):
        """Someone at risk is never answered with a home command (the net answers first anyway; this is a second guard).
        The corpus's look-alikes that aren't a crisis ("can you kill the lights") may be what they sound like."""
        for name in ("crisis_corpus.jsonl", "crisis_heldout.jsonl", "crisis_heldout2.jsonl"):
            rows = [json.loads(line) for line in (ROOT / "tests" / "data" / name).read_text().splitlines() if line.strip()]
            lines = [r["text"] for r in rows if r.get("should")]
            self.assertGreater(len(lines), 10, name)
            self.assertEqual(self._hits(lines), 0, f"{name}: a line was read as a home command")


if __name__ == "__main__":
    unittest.main()


class Speaker(unittest.TestCase):
    def test_music_uses_the_ffmpeg_luma_desktop_installs(self):
        import os
        from unittest import mock
        from luma.audio import player
        with mock.patch.dict(os.environ, {"LUMA_FFMPEG": __file__}):
            self.assertEqual(player.Player(out=lambda blocks, stop: None).ffmpeg, __file__)
