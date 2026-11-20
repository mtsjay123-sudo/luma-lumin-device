#!/usr/bin/env python3
"""What leaves the home? Every connection Luma tries to make, counted, with nothing let through.

A throwaway Luma with its settings as they come lives a day: an ordinary conversation (talk, memories, alarms, lists,
a hard moment, forgetting something), then a day of its own background work (a tick every five minutes for 24 hours).
Every attempt to look up a host or open a connection is recorded and refused, so nothing is ever sent.

- talk:        things they say that ask for nothing from outside. Must be zero attempts.
- background:  what Luma does by itself over a day. Listed by host, so a person can see exactly what it reaches for.
- asked:       things that do need the outside ("what's the weather"). Listed by host: these are the owner asking.

  python scripts/egress_check.py            # the three lists
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
        return self

    def __exit__(self, *exc):
        socket.getaddrinfo, socket.socket.connect, socket.create_connection = self._getaddrinfo, self._connect, self._create
        os.environ.update(self._proxies)

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
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, indent=1))
    return 1 if out["talk"] else 0


if __name__ == "__main__":
    sys.exit(main())
