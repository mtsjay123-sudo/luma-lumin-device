#!/usr/bin/env python3
"""What leaves the home? Every connection Luma tries to make, counted, with nothing let through.

A throwaway Luma with its settings as they come lives a day: an ordinary conversation (talk, memories, alarms, lists,
a hard moment, forgetting something), then a day of its own background work (a tick every five minutes for 24 hours).
Every attempt to look up a host or open a connection is recorded and refused, so nothing is ever sent.

- talk:        things they say that ask for nothing from outside. Must be zero attempts.
- background:  what Luma does by itself over a day. Listed by host, so a person can see exactly what it reaches for.
- asked:       things that do need the outside ("what's the weather"). Listed by host: these are the owner asking.

- alone:       each switch that lets something out, turned on by itself, reaches only its own hosts; and with the
               web switch off, asking for the weather or a price reaches nothing at all.

  python scripts/egress_check.py            # the four lists
  python scripts/egress_check.py --json out/egress.json
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

TALK = ["hey", "my sister's name is Dana", "I had such a long day at work", "I left my keys on the hook by the door", "where are my keys?",
        "wake me up at 7 tomorrow", "add milk and eggs to my shopping list", "what's on my shopping list", "what time is it in Ohio",
        "how many days until Christmas", "remind me to call Mom every Sunday at 6pm", "I got passed over for the promotion again and I feel like garbage",
        "I don't need advice, I just need to vent", "my mom called me today", "tell me a joke", "I have a job interview tomorrow morning",
        "what's my sister's name again?", "I really miss my sister tonight", "forget about the interview", "flip a coin", "volume 5", "good night"]
ASKED = ["what's the weather today", "what's in the news", "search the web for the best ramen in Osaka", "how much is a PS5 right now", "play some jazz"]
LOCAL = ("127.", "::1", "localhost", "0.0.0.0")


class Watch:
    """Refuses every lookup and connection that isn't to this machine, and remembers who was asked for."""

    def __init__(self):
        self.seen = []
        self._getaddrinfo, self._connect, self._create = socket.getaddrinfo, socket.socket.connect, socket.create_connection

    def _note(self, host, port=None):
        host = str(host)
        if host.startswith(LOCAL) or host in ("", "None"):
            return False
        self.seen.append(f"{host}:{port}" if port else host)
        return True

    def __enter__(self):
        watch = self

        def getaddrinfo(host, port, *args, **kwargs):
            if watch._note(host, port):
                raise socket.gaierror("refused by the egress check")
            return watch._getaddrinfo(host, port, *args, **kwargs)

        def connect(sock, address):
            if isinstance(address, tuple) and watch._note(address[0], address[1]):
                raise OSError("refused by the egress check")
            return watch._connect(sock, address)

        def create_connection(address, *args, **kwargs):
            if watch._note(address[0], address[1]):
                raise OSError("refused by the egress check")
            return watch._create(address, *args, **kwargs)

        socket.getaddrinfo, socket.socket.connect, socket.create_connection = getaddrinfo, connect, create_connection
        # Through a proxy every request looks like a call to the proxy. Without one, each host is asked for by name.
        self._proxies = {k: os.environ.pop(k) for k in list(os.environ) if k.lower() in ("http_proxy", "https_proxy", "all_proxy")}
        # and urllib remembers the proxies it found the first time anything opened a URL in this process: without this,
        # after an earlier test, every request went to the proxy and no host was counted (found Nov 26)
        import urllib.request
        self._opener, urllib.request._opener = urllib.request._opener, None
        return self

    def __exit__(self, *exc):
        socket.getaddrinfo, socket.socket.connect, socket.create_connection = self._getaddrinfo, self._connect, self._create
        os.environ.update(self._proxies)
        import urllib.request
        urllib.request._opener = self._opener

    def take(self):
        got, self.seen = sorted(set(self.seen)), []
        return got


def run():
    import human_eval

    def stand_in(messages, context, allowed, *args, **kwargs):
        return {"type": "reply", "text": "Okay."}

    out = {}
    with Watch() as watch:
        s = human_eval.Session(stand_in)
        try:
            watch.take()  # starting up
            for line in TALK:
                s.say(line)
            s.agent.helpers.thread and s.agent.helpers.thread.join(5)
            out["talk"] = watch.take()
            for step in range(24 * 12):  # a day, five minutes at a time
                s.clock["t"] += 300
                s.tick()
                try:
                    s.agent.helpers.start_due()
                    if s.agent.helpers.thread:
                        s.agent.helpers.thread.join(5)
                except Exception:
                    pass
            out["background"] = watch.take()
            out["asked"] = {}
            for line in ASKED:
                s.say(line)
                out["asked"][line] = watch.take()
        finally:
            s.close()
    return out


# What each switch may reach for, turned on alone. A host is named by how it ends, so api.open-meteo.com and
# geocoding-api.open-meteo.com are both the weather's. Anything else that shows up is a leak.
OWN = {
    "weather (the web switch, as it comes)": ("open-meteo.com", "wttr.in"),
    "a coin's price (the web switch)": ("coinbase.com",),
    "a share's price (the web switch)": ("finance.yahoo.com", "stooq.com"),
    "the radio (Music)": ("radio-browser.info",),
    "the house (Home)": ("192.168.1.20",),
    "the lamp's memory model (memory_by_meaning_small)": ("huggingface.co",),
}
HOUSE = {"HOME_ASSISTANT_URL": "http://192.168.1.20:8123", "HOME_ASSISTANT_TOKEN": "not-a-real-token", "LUMA_ALLOWED_LIGHTS": "light.living_room"}
NEEDS_THE_WEB = ["what's the weather in Osaka", "what's bitcoin at", "what's apple stock at"]


class _Speaker:
    """A stand-in for the lamp's speaker, so the radio path runs. It plays nothing."""

    def busy(self): return False
    def stop(self): return None
    def __getattr__(self, name): return lambda *a, **k: None


def alone():
    """Each outside switch on by itself: what it reached for. And everything off: what the same asks reached for."""
    import time
    import human_eval
    from luma.memory import meaning

    def stand_in(messages, context, allowed, *args, **kwargs):
        return {"type": "reply", "text": "Okay."}

    out = {}

    def home(setup, act):
        with Watch() as watch:
            s = human_eval.Session(stand_in)
            try:
                for service in ("web_search", "music", "home_assistant", "browser", "shopping", "booking", "mail", "calendar", "connectors", "sms"):
                    s.agent.enable(service, False)
                setup(s.agent)
                watch.take()
                act(s)
                return watch.take()
            finally:
                s.close()

    web = lambda agent: agent.enable("web_search", True)
    out["weather (the web switch, as it comes)"] = home(web, lambda s: s.say(NEEDS_THE_WEB[0]))
    out["a coin's price (the web switch)"] = home(web, lambda s: s.say(NEEDS_THE_WEB[1]))
    out["a share's price (the web switch)"] = home(web, lambda s: s.say(NEEDS_THE_WEB[2]))

    def music(agent):
        agent.enable("music", True)
        agent.athome.player = _Speaker()
    out["the radio (Music)"] = home(music, lambda s: s.agent.athome.handle("play some jazz", "play some jazz"))

    def house(agent):
        agent.enable("home_assistant", True)
        agent.athome.env.update(HOUSE)
    out["the house (Home)"] = home(house, lambda s: s.agent.athome.handle("turn on the living room light", "turn on the living room light"))

    def model(s):
        # In a folder of its own, so a model already here (or a stand-in another test left) can't make it skip the fetch.
        import tempfile
        from unittest import mock
        s.agent.store.set_setting("memory_by_meaning_small", True)
        with tempfile.TemporaryDirectory() as empty, mock.patch.object(meaning, "folder", lambda: Path(empty)):
            meaning.fetching_small.update(running=False, tried=0.0)
            meaning.fetch_small(s.agent.store)
            for _ in range(300):   # it fetches in the background; on a busy machine that can take more than a few seconds to start
                if not meaning.fetching_small["running"]:
                    break
                time.sleep(0.1)
    try:
        import tokenizers  # noqa: F401  (without it the lamp's model is never fetched, here or on a lamp)
        out["the lamp's memory model (memory_by_meaning_small)"] = home(lambda agent: None, model)
    except Exception:
        pass

    def everything(s):
        for line in NEEDS_THE_WEB + ["what's in the news", "play some jazz", "turn on the living room light", "search the web for the best ramen in Osaka"]:
            s.say(line)
        s.agent.athome.handle("play some jazz", "play some jazz")
    off = home(lambda agent: None, everything)
    leaks = {name: [h for h in hosts if not h.split(":")[0].endswith(OWN[name])] for name, hosts in out.items()}
    return {"alone": out, "leaks": {k: v for k, v in leaks.items() if v}, "everything_off": off}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json")
    args = parser.parse_args()
    out = run()
    print(f"talk ({len(TALK)} things said that ask for nothing from outside): {len(out['talk'])} hosts reached for")
    for host in out["talk"]:
        print("  ", host)
    print(f"background (a day of Luma's own work, settings as they come): {len(out['background'])} hosts reached for")
    for host in out["background"]:
        print("  ", host)
    print("asked (the owner asking for something from outside):")
    for line, hosts in out["asked"].items():
        print(f"   {line!r}: " + (", ".join(hosts) if hosts else "nothing"))
    each = alone()
    out.update(each)
    print("alone (each switch that lets something out, on by itself, and what it reached for):")
    for name, hosts in each["alone"].items():
        wrong = each["leaks"].get(name)
        print(f"   {name}: " + (", ".join(sorted({h.split(':')[0] for h in hosts})) if hosts else "nothing") + (f"   NOT ITS OWN: {', '.join(wrong)}" if wrong else ""))
    print(f"everything off, then asked for the weather, a price, the news, the radio and the lights: {len(each['everything_off'])} hosts reached for")
    for host in each["everything_off"]:
        print("  ", host)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, indent=1))
    return 1 if out["talk"] or each["leaks"] or each["everything_off"] else 0


if __name__ == "__main__":
    sys.exit(main())
