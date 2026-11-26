"""Does Luma's memory stay flat while it runs? A short stand-in for "72 hours with memory use flat and no restart"
(docs/PRESENCE_MASTER_PROMPT.md, section 9).

    PYTHONPATH=src python3 scripts/soak.py --turns 3000

It talks to one Luma (no brain: Luma's own code paths, the memory store, the timers, the nightly work) for thousands of
turns and clock ticks, moving its clock forward a minute a turn so days go by, and prints how much memory the process
holds at the start, a third of the way in, and at the end. Flat means the last two are close. What it can't show: a
brain's own memory, the voice, the microphone, or real days. Those need the lamp.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SAID = ["what time is it", "set a timer for 2 minutes", "add milk to my shopping list", "what's on my shopping list", "my sister Priya lives in Tampa",
        "where does my sister live", "i had a long day at work", "remind me to call mom tomorrow at 5", "flip a coin", "how many ounces in a cup",
        "that's too long", "tell me a joke", "i'm kind of tired today", "cancel the timer", "what's the date", "good night"]


def held():
    """Megabytes this process holds right now (resident), from the kernel's own count."""
    try:
        pages = int(Path("/proc/self/statm").read_text().split()[1])
        import os
        return pages * os.sysconf("SC_PAGE_SIZE") / 2 ** 20
    except (OSError, ValueError):
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def soak(turns):
    from luma.agent.runtime import Agent
    from luma.memory.store import Store
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "s.db", Path(folder) / "k")
        agent = Agent(store=store, use_model=False)
        now = [agent.clock()]
        agent.clock = lambda: now[0]
        marks, failed = {}, 0
        for n in range(turns):
            now[0] += 60
            try:
                agent.chat(SAID[n % len(SAID)])
            except Exception:
                failed += 1
            for _ in range(3):
                now[0] += 20
                agent.tick()
            if n in (0, turns // 3, turns - 1):
                gc.collect()
                marks[n] = held()
        store.close()
    start, third, end = (marks[k] for k in sorted(marks))
    return {"turns": turns, "days_gone_by": round(turns * 2 / 1440, 1), "start_mb": round(start, 1), "a_third_in_mb": round(third, 1), "end_mb": round(end, 1),
            "grew_after_warm_up_mb": round(end - third, 1), "turns_that_raised": failed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=3000)
    print(json.dumps(soak(parser.parse_args().turns), indent=1))
