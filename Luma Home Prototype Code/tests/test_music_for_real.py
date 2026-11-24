"""Music, tried for real (the owner, Nov 24: "does music playing work on Luma?").

It was tried in the cloud with a real song file, real ffmpeg and a stand-in for the speaker. What worked: a song from
their own folder (three seconds of sound came out of a three-second file), sleep sounds, stop. What didn't, with nothing
playing: "what's playing" went to a web look-up, "stop the music" got "What do you want to hear?", "pause the music" opened
"pause the" on YouTube Music, and so did "who is this" and "next time i'll say something". And with the radio directory out
of reach Luma said "I couldn't find a station for jazz. Try a genre, like jazz or city pop."

Not tried, and it can't be here: sound out of a real speaker, and the radio from the real directory (this machine can't
reach it). Those are for the first Luma that's built.
"""
import json
import random
import shutil
import subprocess
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from luma.agent import athome
from luma.agent.athome import AtHome
from luma.agent.runtime import Agent
from luma.audio import player
from luma.memory.store import Store

ROOT = Path(__file__).resolve().parents[1]
TOKYO = ZoneInfo("Asia/Tokyo")

# Written before the fix; the patterns were built on these.
BUILT_ON = ["what's playing", "what song is this", "what am i listening to", "stop the music", "pause the music", "turn off the radio",
            "next song", "change the station", "what station is this", "skip this song", "what is playing right now", "kill the music"]
BUILT_ON_NOT = ["who is this", "what's on", "what's this", "stop it", "skip it", "what's playing at the cinema tonight",
                "i need to stop listening to my ex's playlist", "the music stopped mattering to me", "what's playing on my mind is the interview",
                "i can't stop the music in my head", "next time i'll say something", "what's on your mind"]
# Written after the fix and before it was measured; measured once: 12 of 12 told, 0 of 15 taken. Same hand, same hour, so
# it's a floor to hold and not much of a number. Nothing is changed to fit it.
FRESH = ["what song is that", "pause the song", "turn off the music please", "hey luma what's playing", "skip the song", "can you stop the radio",
         "shut off the music", "next track", "what's this song called", "end the music", "what is this station", "cut the music"]
FRESH_NOT = ["stop", "what's on tv tonight", "i stopped the music lessons last year", "next", "pause", "my radio broke",
             "the station was closed when i got there", "turn off the lights", "what's playing with my head is the silence", "skip the small talk",
             "another one bites the dust", "cut it out", "who is this", "next time i'll say something", "i can't stop the music in my head"]


def told_nothing(text):
    return "nothing's playing" in text.lower() or "not playing anything" in text.lower()


class NothingIsPlaying(unittest.TestCase):
    def agent(self, speaker):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        if speaker:
            agent.athome.player = player.Player(out=lambda blocks, stop: None)
        return agent

    def said(self, agent, line):
        got = agent.chat(line)
        return str(got.get("text") or got.get("summary") or ""), got

    def test_asked_about_the_music_luma_says_nothing_is_playing(self):
        for speaker in (True, False):
            agent = self.agent(speaker)
            self.assertEqual(sum(told_nothing(self.said(agent, line)[0]) for line in BUILT_ON), 12, speaker)
            self.assertGreaterEqual(sum(told_nothing(self.said(agent, line)[0]) for line in FRESH), 12, speaker)

    def test_talk_is_left_alone_and_never_opened_as_a_song(self):
        for speaker in (True, False):
            agent = self.agent(speaker)
            for line in BUILT_ON_NOT + FRESH_NOT:
                text, got = self.said(agent, line)
                self.assertFalse(told_nothing(text), line)
                self.assertNotIn("music.youtube.com", str(got.get("open_url")), line)   # "who is this" used to open YouTube Music
                self.assertNotIn("What do you want to hear", text, line)

    def test_a_tab_luma_knows_is_playing_is_still_the_computers_to_answer_for(self):
        agent = self.agent(False)
        agent.now_playing = "Blue in Green by Miles Davis"
        self.assertIn("Blue in Green", self.said(agent, "what's playing")[0])

    def test_a_real_request_for_music_is_still_one(self):
        agent = self.agent(False)
        for line in ("play some jazz", "put on lo-fi", "play first love by hikaru utada"):
            self.assertIn("music.youtube.com", str(self.said(agent, line)[1].get("open_url")), line)

    def test_no_crisis_or_human_test_line_is_taken_for_one(self):
        lines = [json.loads(row)["text"] for name in ("crisis_corpus.jsonl", "crisis_heldout.jsonl", "crisis_heldout2.jsonl")
                 for row in (ROOT / "tests" / "data" / name).read_text().splitlines() if row.strip()]
        for row in (ROOT / "data" / "human_eval_v2.jsonl").read_text().splitlines():
            if row.strip():
                item = json.loads(row)
                lines += [t.get("said") or "" for t in item.get("turns", [])] + [item.get("said") or ""]
        taken = sum(bool(p.match(line.lower())) for line in lines if line for p in (athome.ABOUT_PLAYING, athome.STOP_NAMED, athome.NEXT_NAMED))
        self.assertEqual(taken, 0)
        self.assertGreater(len(lines), 700)


class TheRadioOutOfReach(unittest.TestCase):
    def home(self, fetch):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        store = Store(folder / "l.db", folder / "k.key")
        self.addCleanup(store.close)

        class Speaker:
            def busy(self): return False
            def stop(self): pass
            def stream(self, url): pass
        return AtHome(store, clock=lambda: datetime(2026, 11, 24, 20, 0, tzinfo=TOKYO).timestamp(), zone=TOKYO, player=Speaker(), fetch=fetch,
                      on=lambda s: s == "music", env={"LUMA_MUSIC_DIR": str(folder / "none")}, mode=lambda: "friend", rng=random.Random(3), memories=store.memories)

    def test_out_of_reach_isnt_no_such_station(self):
        def down(*a, **k): raise OSError("no route")
        text = self.home(down).handle("play some jazz", "play some jazz")["text"]
        self.assertEqual(text, "I can't reach the radio right now. Your own songs and sleep sounds still work.")

    def test_no_such_station_never_suggests_what_they_asked_for(self):
        text = self.home(lambda *a, **k: []).handle("play some jazz", "play some jazz")["text"]
        self.assertIn("couldn't find a station for jazz", text)
        self.assertNotIn("like jazz", text)
        self.assertIn("city pop", text)


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg, as a Luma does to play a song")
class ASongOfTheirOwn(unittest.TestCase):
    def test_a_real_file_is_decoded_and_comes_out_of_the_speaker(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        (folder / "Music").mkdir()
        subprocess.run([shutil.which("ffmpeg"), "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                        str(folder / "Music" / "porch light.mp3")], check=True)
        store = Store(folder / "s.db", folder / "k")
        self.addCleanup(store.close)
        agent = Agent(store=store, use_model=False)
        heard = []

        def speaker(blocks, should_stop):
            for block in blocks:
                if should_stop(): break
                heard.append(np.asarray(block))
        agent.athome.player = player.Player(out=speaker)
        agent.athome.env = {"LUMA_MUSIC_DIR": str(folder / "Music")}
        self.assertEqual(agent.chat("play porch light")["text"], "Playing Porch Light.")
        until = time.time() + 20
        while time.time() < until and sum(len(b) for b in heard) < 1.5 * player.RATE: time.sleep(0.1)
        seconds = sum(len(b) for b in heard) / player.RATE
        self.assertGreater(seconds, 1.5)                                    # the song's own length is two seconds
        self.assertGreater(max(float(np.abs(b).max()) for b in heard), 0.05)  # and it isn't silence
        self.assertEqual(agent.chat("stop the music")["text"], "Okay." if agent.athome.player.busy() else athome.NOTHING_ON)


if __name__ == "__main__":
    unittest.main()
