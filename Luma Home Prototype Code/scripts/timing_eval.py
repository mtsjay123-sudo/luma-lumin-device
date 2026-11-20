#!/usr/bin/env python3
"""The Luma timing test: does Luma start talking when a person would, without cutting in?

Nuance Labs reports that their model's reply timing overlaps a person's 89% of the time. This is the same idea for
Luma, on our own conversations. It needs real ones: two people talking, written down as when each stretch of speech
starts and stops (a timeline), which is the owner's to record, with consent. Until there are some, this has nothing
to say about Luma: it only checks its own arithmetic (tests/test_timing_eval.py).

A timeline is JSON:

    {"turns": [{"speech": [[0.0, 2.1], [2.6, 4.0]],        the person's turn: stretches of speech, in seconds
                "done": [false, true],                      optional: what Smart Turn said at the pause after each stretch
                "reply_at": 4.35}]}                         when the other person really started answering

What it works out, with Luma's own rules for when a turn ends (luma.audio.turn: a 300 ms pause puts the question to
Smart Turn, "not done" holds the turn open 1.6 s more; with no model, a plain 900 ms of silence ends it):

- cut-ins:    turns where Luma would have decided "they're done" at a pause in the middle
- the wait:   how long after they really stopped Luma decides they're done
- the window: where the people in these same conversations started answering (the 10th to 90th percentile of the gap)
- in the window: turns where Luma, starting `--latency` seconds after it decides (the brain's first clause and the
  voice: measure this on the device), would have started inside that window and hadn't cut in

  python scripts/timing_eval.py score recordings/*.json --latency 0.9
  python scripts/timing_eval.py score recordings/*.json --plain      # with no Smart Turn model
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def rules():
    """Luma's own numbers, read from where the voice uses them."""
    from luma.audio import turn
    return {"pause": turn.PAUSE_MS / 1000, "plain": turn.PLAIN_MS / 1000, "hold": turn.HOLD_S}


def decided(turn, plain=False, r=None):
    """(when Luma decides the turn is over, counted from the start of the timeline; whether that was a cut-in)."""
    r = r or rules()
    speech = turn["speech"]
    done = turn.get("done") or [None] * len(speech)
    for i, (_start, end) in enumerate(speech):
        last = i == len(speech) - 1
        gap = float("inf") if last else speech[i + 1][0] - end
        if plain:
            if gap >= r["plain"]:
                return end + r["plain"], not last
            continue
        if gap < r["pause"]:
            continue  # too short a pause to ask about
        said = done[i] if i < len(done) and done[i] is not None else last  # no answer recorded: as if the model were right
        if said:
            return end + r["pause"], not last
        if gap >= r["pause"] + r["hold"]:
            return end + r["pause"] + r["hold"], not last  # held open, and they still hadn't gone on
    return speech[-1][1] + (r["plain"] if plain else r["pause"]), False


def score(timelines, latency=0.0, plain=False):
    """Every turn in every timeline, against where people really started answering in these same conversations."""
    r = rules()
    turns = [t for timeline in timelines for t in timeline.get("turns", []) if t.get("speech")]
    gaps = sorted(t["reply_at"] - t["speech"][-1][1] for t in turns if t.get("reply_at") is not None)
    if len(gaps) >= 10:
        low, high = gaps[int(len(gaps) * 0.10)], gaps[min(len(gaps) - 1, int(len(gaps) * 0.90))]
    else:
        low = high = None  # too few to say where people start
    waits, cut_ins, inside = [], 0, 0
    for t in turns:
        at, cut = decided(t, plain=plain, r=r)
        end = t["speech"][-1][1]
        cut_ins += cut
        if not cut:
            waits.append(at - end)
            if low is not None and low <= (at - end) + latency <= high:
                inside += 1
    return {"turns": len(turns), "cut_ins": cut_ins, "wait_median": round(statistics.median(waits), 3) if waits else None,
            "window": [round(low, 3), round(high, 3)] if low is not None else None, "in_window": inside if low is not None else None,
            "latency": latency, "plain": plain}


def summary(result):
    if not result["turns"]:
        return "No turns to score. Record some conversations first (see the top of this file)."
    lines = [f"{result['turns']} turns, {'a plain silence timer' if result['plain'] else 'Smart Turn'}:",
             f"- cut in on {result['cut_ins']} of {result['turns']}",
             f"- decides they're done {result['wait_median']} s after they stop (median)"]
    if result["window"]:
        lines.append(f"- people here started answering {result['window'][0]} to {result['window'][1]} s after the other stopped (10th to 90th percentile)")
        lines.append(f"- starting {result['latency']} s after it decides, Luma is inside that window on {result['in_window']} of {result['turns']}")
    else:
        lines.append("- too few turns with a real answer to say where people start (ten at least)")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("files", nargs="+")
    s.add_argument("--latency", type=float, default=0.0, help="seconds from deciding they're done to Luma's first sound (measure it on the device)")
    s.add_argument("--plain", action="store_true", help="as if there were no Smart Turn model")
    args = parser.parse_args()
    timelines = [json.loads(Path(name).read_text()) for name in args.files]
    print(summary(score(timelines, latency=args.latency, plain=args.plain)))


if __name__ == "__main__":
    main()
