#!/usr/bin/env python3
"""The wake test: does Luma hear "Hey Luma" across the room, and stay asleep through a day of TV?

The bar (docs/GAME_PLAN.md, section 2): heard at least 95 times in 100 at 3 metres, and no more than one false wake in
24 hours of TV, music and talk. It needs real recordings made with the lamp's own microphones, from people who agreed
to be recorded (docs/WAKE_WORD_PLAN.md). Until there are some, this has nothing to say about Luma: it only checks its
own arithmetic (tests/test_wake_eval.py).

A recording is written down as a timeline, in seconds from its start:

    {"hours": 2.0,                                           how long the recording is
     "said": [{"at": 12.4, "distance": 3, "who": "p07", "room": "tv on"}],     each time the phrase was really said
     "near": [{"at": 300.0, "phrase": "hey lumen"}],         look-alikes said on purpose
     "woke": [12.9, 301.1, 4000.2]}                          every time the wake model fired

What it works out:

- heard:       a wake inside `--within` seconds after the phrase began counts as hearing it. One wake answers one
               phrase. By distance, and by what else was going on in the room.
- look-alikes: how often each one woke it. Reported apart: they're said on purpose, so they aren't a day's false wakes.
- false wakes: every other wake, and what that comes to in 24 hours.
- the verdict: said only when there's enough to say it. Under 24 hours of recording, or under 300 phrases at 3 metres,
               it says how much there is and gives no pass.

  python scripts/wake_eval.py score recordings/wake/*.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HEARD_AT_3M = 95        # percent
FALSE_IN_24H = 1
ENOUGH_HOURS = 24
ENOUGH_AT_3M = 300


def score(timelines, within=2.0):
    by_distance, by_room, near, false, hours = {}, {}, {}, 0, 0.0
    for t in timelines:
        hours += float(t.get("hours") or 0)
        woke = sorted(float(w) for w in t.get("woke", []))
        used = [False] * len(woke)

        def answered(at):
            for n, w in enumerate(woke):
                if not used[n] and at <= w <= at + within:
                    used[n] = True
                    return True
            return False

        for said in sorted(t.get("said", []), key=lambda s: s["at"]):
            got = answered(float(said["at"]))
            for table, key in ((by_distance, said.get("distance")), (by_room, said.get("room") or "quiet")):
                row = table.setdefault(key, [0, 0])
                row[0] += got
                row[1] += 1
        for said in sorted(t.get("near", []), key=lambda s: s["at"]):
            row = near.setdefault(str(said.get("phrase", "?")).lower(), [0, 0])
            row[0] += answered(float(said["at"]))
            row[1] += 1
        false += used.count(False)
    at_3m = by_distance.get(3) or by_distance.get(3.0) or [0, 0]
    per_day = false / hours * 24 if hours else None
    enough = hours >= ENOUGH_HOURS and at_3m[1] >= ENOUGH_AT_3M
    return {"hours": round(hours, 2), "heard": {str(k): v for k, v in sorted(by_distance.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))},
            "rooms": by_room, "near": near, "false": false, "false_in_24h": None if per_day is None else round(per_day, 2),
            "enough": enough,
            "passed": (100 * at_3m[0] >= HEARD_AT_3M * at_3m[1] and per_day <= FALSE_IN_24H) if enough else None}


def summary(s):
    lines = ["### The wake test", "", "| Said from | Heard |", "|---|---|"]
    for distance, (got, of) in s["heard"].items():
        lines.append(f"| {distance} m | {got} of {of} ({round(100 * got / of)}%) |" if of else f"| {distance} m | none said |")
    if s["rooms"]:
        lines += ["", "| With | Heard |", "|---|---|"] + [f"| {room} | {got} of {of} |" for room, (got, of) in sorted(s["rooms"].items())]
    if s["near"]:
        lines += ["", "| Look-alike, said on purpose | Woke it |", "|---|---|"] + [f"| {phrase} | {got} of {of} |" for phrase, (got, of) in sorted(s["near"].items())]
    per_day = "no recording to count them over" if s["false_in_24h"] is None else f"{s['false_in_24h']} in 24 hours"
    lines += ["", f"False wakes: {s['false']} in {s['hours']} hours of recording ({per_day})."]
    if s["passed"] is None:
        lines.append(f"Too little to say whether it passes: the bar needs {ENOUGH_HOURS} hours of recording and {ENOUGH_AT_3M} phrases said at 3 m.")
    else:
        lines.append(f"The bar ({HEARD_AT_3M}% heard at 3 m, at most {FALSE_IN_24H} false wake in 24 hours): {'met' if s['passed'] else 'not met'}.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("score")
    sc.add_argument("files", nargs="+")
    sc.add_argument("--within", type=float, default=2.0, help="seconds after the phrase begins in which a wake counts as hearing it")
    args = parser.parse_args()
    print(summary(score([json.loads(Path(name).read_text()) for name in args.files], within=args.within)))


if __name__ == "__main__":
    main()
