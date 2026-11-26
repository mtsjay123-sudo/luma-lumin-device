#!/usr/bin/env python3
"""The barge-in test: when someone talks over Luma, does it go quiet in time?

The bar (docs/GAME_PLAN.md, B7): Luma's voice has stopped within 300 ms of the person starting, at least 95 times in
100, over 200 recorded interruptions. It needs real recordings: a person talking over Luma in a room, on the device's
own microphones and speaker, with the moment they started and the moment Luma's sound ended read off the recording.
Until there are some, this has nothing to say about Luma: it only checks its own arithmetic (tests/test_barge_eval.py).

What the code already does is in luma/audio/vad.py and luma/orchestrator.py: with echo cancellation or headphones the
microphone stays open while Luma talks, and the moment speech starts `talked_over` calls `agent.interrupt()`. How long
that takes on a real speaker is exactly what isn't known.

A recording is written down as a timeline, in seconds from its start:

    {"minutes": 12.0,                                   how long Luma was talking in this recording, in all
     "interruptions": [{"at": 31.20, "quiet_at": 31.41},          they started talking; Luma's sound ended
                       {"at": 80.05, "quiet_at": null}],          it never stopped
     "false_stops": [140.3]}                            Luma went quiet and nobody had said anything

What it works out:

- in time:      interruptions where Luma was quiet within `--within` seconds (0.3 unless said)
- how long:     the middle one and the slowest tenth, of those where it stopped at all
- never:        interruptions it talked straight through
- false stops:  and how many that is in ten minutes of Luma talking
- the verdict:  said only with 200 interruptions or more

  python scripts/barge_eval.py score recordings/barge/*.json
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

IN_TIME = 95        # percent
WITHIN = 0.3        # seconds
ENOUGH = 200


def score(timelines, within=WITHIN):
    waits, never, minutes, false = [], 0, 0.0, 0
    for t in timelines:
        minutes += float(t.get("minutes") or 0)
        false += len(t.get("false_stops") or [])
        for one in t.get("interruptions", []):
            quiet = one.get("quiet_at")
            if quiet is None or float(quiet) < float(one["at"]):
                never += 1
            else:
                waits.append(float(quiet) - float(one["at"]))
    of = len(waits) + never
    in_time = sum(w <= within + 1e-9 for w in waits)
    ordered = sorted(waits)
    return {"of": of, "in_time": in_time, "never": never,
            "middle": round(statistics.median(ordered), 3) if ordered else None,
            "slowest_tenth": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.9))], 3) if ordered else None,
            "false_stops": false, "minutes": round(minutes, 1),
            "false_in_ten_minutes": round(false / minutes * 10, 2) if minutes else None,
            "within": within, "passed": (100 * in_time >= IN_TIME * of) if of >= ENOUGH else None}


def summary(s):
    if not s["of"]:
        return "### The barge-in test\n\nNo interruptions recorded yet."
    lines = ["### The barge-in test", "",
             f"Quiet within {int(s['within'] * 1000)} ms: **{s['in_time']} of {s['of']} ({round(100 * s['in_time'] / s['of'])}%)**. "
             f"Talked straight through: {s['never']}."]
    if s["middle"] is not None:
        lines.append(f"Where it stopped: {int(s['middle'] * 1000)} ms in the middle, {int(s['slowest_tenth'] * 1000)} ms for the slowest tenth.")
    per = "no talking time written down" if s["false_in_ten_minutes"] is None else f"{s['false_in_ten_minutes']} in ten minutes of Luma talking"
    lines.append(f"Went quiet with nobody speaking: {s['false_stops']} ({per}).")
    if s["passed"] is None:
        lines.append(f"Too few to say whether it passes: the bar needs {ENOUGH} interruptions.")
    else:
        lines.append(f"The bar ({IN_TIME}% quiet within {int(s['within'] * 1000)} ms): {'met' if s['passed'] else 'not met'}.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("score")
    sc.add_argument("files", nargs="+")
    sc.add_argument("--within", type=float, default=WITHIN)
    args = parser.parse_args()
    print(summary(score([json.loads(Path(name).read_text()) for name in args.files], within=args.within)))


if __name__ == "__main__":
    main()
