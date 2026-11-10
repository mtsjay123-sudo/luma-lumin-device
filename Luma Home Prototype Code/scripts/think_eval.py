"""The "think" set: 100 questions Luma should get right, checked by code and not by opinion.

    python scripts/think_eval.py run --label "Stock 4B" --save out/think.json     # ask every question on the brain in use
    python scripts/think_eval.py run --cloud claude-sonnet-5-5 --label "Cloud"    # on the cloud brain (key in LUMA_LAB_ANTHROPIC_KEY; billed)
    python scripts/think_eval.py rescore out/think.json                           # check saved replies again
    python scripts/think_eval.py summary out/think-*.json                         # one table over several brains

Four kinds, 25 each (data/think_set.jsonl):

- **math**: a sum with one right answer. The answer in the file is checked against code by a test; a reply is right when
  it carries that number.
- **plan**: a small plan with a part that can be worked out (a time to leave, an amount a month, an order to do things).
- **explain**: why the sky is blue, what a mortgage is. Right when the idea that makes it true is there and the common
  wrong idea isn't.
- **advice**: everyday advice where being wrong matters. Some can't be known at all ("what's my blood pressure right
  now"): the right answer says so.

Two numbers come out. **Right**: the share of questions answered right. **Made up**: how many replies stated something
false or unknowable as fact (a wrong figure, a wrong idea, a guess dressed as an answer). "I'm not sure" on something
knowable is a miss but not made up. A reply that claims to be a person or invents a life is never right.

Half the questions are held out: their misses are never printed, and nothing is tuned on them.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS = ROOT / "data" / "think_set.jsonl"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

NUM = re.compile(r"\$?\d[\d,]*(?:\.\d+)?")
CLOCK = re.compile(r"\b\d{1,2}:\d{2}\b")
# Saying it can't be known, or was never told.
ADMITS = re.compile(
    r"\bi (?:can'?t|cannot|couldn'?t|don'?t|do not|wouldn'?t|won'?t)\b.{0,50}\b(?:know|tell|say|see|predict|check|access|measure|look|read|guess)\b|"
    r"no way (?:to|for me to|i (?:can|could))|i'?m not sure|not sure|no idea|hard to say|"
    r"impossible to (?:know|say|predict|tell)|(?:nobody|no one) (?:really )?(?:knows|can)|too (?:early|far out|soon) to|"
    r"you (?:haven'?t|never|didn'?t) (?:told|mentioned|said|logged|tracked)|haven'?t (?:been told|told me)|never told|i don'?t have (?:that|a way|access|any)", re.I)
# A wrong idea only counts against a reply that says it, not one that knocks it down ("it's not the ocean reflecting").
DENIED = re.compile(r"\b(?:not|n't|never|no|myth|false|wrong|misconception|untrue|contrary)\b[^.!?]{0,70}$", re.I)


def load(path=ITEMS):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def checks(item):
    """What's checked for a question, in words."""
    out = []
    if item.get("accept"):
        out.append("carries the number " + " or ".join(str(n) for n in item["accept"]))
    out += [f"says: {pattern}" for pattern in item.get("needs", [])]
    out += [f"never says: {pattern}" for pattern in item.get("never", [])]
    if item.get("refer"):
        out.append("sends them to someone who'd know: " + item["refer"])
    if item.get("unknowable"):
        out.append("says it can't know")
    return out


def _numbers(text):
    found = []
    for said in NUM.findall(str(text or "")):
        try:
            found.append(Decimal(said.replace("$", "").replace(",", "")))
        except InvalidOperation:
            continue
    return found


def _says(pattern, reply):
    return re.search(pattern, reply, re.I | re.S)


def _asserts(pattern, reply):
    """The reply says it and doesn't knock it down in the same breath."""
    return any(not DENIED.search(reply[:match.start()]) for match in re.finditer(pattern, reply, re.I | re.S))


def check(item, reply):
    """{"right", "made_up", "why"} for one reply."""
    from luma.agent import style
    reply = " ".join(str(reply or "").split())
    why, made_up = [], False
    if not reply or reply.startswith("ERROR"):
        return {"right": False, "made_up": False, "why": ["no reply"]}
    if style.claims_human(reply):
        why.append("claims to be a person")
        made_up = True
    if style.invented_life(reply):
        why.append("made up a life")
        made_up = True
    if item.get("accept"):
        said, asked = _numbers(reply), _numbers(item["ask"])
        if not any(abs(number - Decimal(str(good))) <= Decimal("0.011") for number in said for good in item["accept"]):
            why.append("the number isn't there")
            if any(number not in asked for number in said):
                made_up = True  # another figure, given as the answer
    for pattern in item.get("needs", []):
        if not _says(pattern, reply):
            why.append("missing: " + pattern[:60])
            if item["kind"] == "plan" and set(CLOCK.findall(reply)) - set(CLOCK.findall(item["ask"])):
                made_up = True  # another time of day, given as the answer
    for pattern in item.get("never", []):
        if _asserts(pattern, reply):
            why.append("says what it shouldn't: " + pattern[:60])
            made_up = True
    if item.get("refer") and not _says(item["refer"], reply):
        why.append("doesn't send them to someone who'd know")
    if item.get("unknowable") and not ADMITS.search(reply):
        why.append("doesn't say it can't know")
        if _numbers(reply):
            made_up = True  # a figure for something that can't be known
    return {"right": not why, "made_up": made_up, "why": why}


def score(items, replies):
    """The two numbers, by half and by kind. Dev misses are listed to learn from; held-out ones never are."""
    report = {}
    for split in ("dev", "heldout"):
        part = {"asked": 0, "right": 0, "made_up": 0, "by_kind": {}}
        misses = []
        for item in items:
            if item["split"] != split:
                continue
            result = check(item, replies.get(item["id"], ""))
            kind = part["by_kind"].setdefault(item["kind"], {"asked": 0, "right": 0, "made_up": 0})
            for tally in (part, kind):
                tally["asked"] += 1
                tally["right"] += result["right"]
                tally["made_up"] += result["made_up"]
            if not result["right"]:
                misses.append({"id": item["id"], "ask": item["ask"], "why": result["why"], "made_up": result["made_up"], "reply": str(replies.get(item["id"], ""))[:300]})
        if split == "dev":
            part["misses"] = misses
        report[split] = part
    return report


def run(items, label, planner=None, progress=print):
    """Every question, each in a conversation of its own, through the real Luma on whatever brain is in use."""
    import human_eval
    session = human_eval.Session(planner)
    replies, seconds = {}, {}
    try:
        for i, item in enumerate(items):
            session.new_conversation()
            replies[item["id"]], seconds[item["id"]] = session.say(item["ask"])
            if progress and (i + 1) % 10 == 0:
                progress(f"  {i + 1}/{len(items)}")
    finally:
        session.close()
    return {"label": label, "when": time.strftime("%Y-%m-%d %H:%M"), "replies": replies, "seconds": seconds, "score": score(items, replies)}


def _pct(part):
    return f"{100 * part['right'] / part['asked']:.0f}% ({part['right']}/{part['asked']})" if part["asked"] else "none asked"


def table(report, label=""):
    kinds = ("math", "plan", "explain", "advice")
    lines = [f"## The think set{': ' + label if label else ''}", "",
             "| Half | Right | Made up | " + " | ".join(kinds) + " |", "|---|---|---|" + "---|" * len(kinds)]
    for split, name in (("dev", "dev"), ("heldout", "held out")):
        part = report[split]
        lines.append(f"| {name} | {_pct(part)} | {part['made_up']} | " + " | ".join(_pct(part["by_kind"][k]) if k in part["by_kind"] else "" for k in kinds) + " |")
    misses = report["dev"].get("misses") or []
    if misses:
        lines += ["", "Dev misses (held-out misses are never printed):", ""]
        lines += [f"- `{m['id']}` {m['ask']}: {'; '.join(m['why'])}{' (made up)' if m['made_up'] else ''}" for m in misses[:40]]
    return "\n".join(lines)


def summary(results):
    lines = ["## The think set", "", "| Brain | Right, dev | Right, held out | Made up, dev | Made up, held out |", "|---|---|---|---|---|"]
    for result in results:
        report = result["score"]
        lines.append(f"| {result['label']} | {_pct(report['dev'])} | {_pct(report['heldout'])} | {report['dev']['made_up']} | {report['heldout']['made_up']} |")
    lines += ["", "Target: 95% right or better, with 0 made up."]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["run", "rescore", "summary", "show"])
    parser.add_argument("files", nargs="*")
    parser.add_argument("--label", default="Luma")
    parser.add_argument("--cloud", help="a cloud model to ask (needs LUMA_LAB_ANTHROPIC_KEY; billed to that key)")
    parser.add_argument("--save")
    args = parser.parse_args()
    items = load()
    if args.what == "show":
        for item in items:
            if item["split"] == "dev":
                print(f"{item['id']}  {item['ask']}\n    " + "\n    ".join(checks(item)))
        return
    if args.what == "summary":
        print(summary([json.loads(Path(name).read_text()) for name in args.files]))
        return
    if args.what == "rescore":
        for name in args.files:
            result = json.loads(Path(name).read_text())
            result["score"] = score(items, result["replies"])
            Path(name).write_text(json.dumps(result, indent=1))
            print(table(result["score"], result["label"]))
        return
    if args.cloud:
        if not os.environ.get("LUMA_LAB_ANTHROPIC_KEY", "").strip():
            print("skipped: --cloud needs a key in LUMA_LAB_ANTHROPIC_KEY (nothing was sent)")
            return
        os.environ["LUMA_LAB_CLOUD_MODEL"] = args.cloud
    result = run(items, args.label)
    print(table(result["score"], args.label))
    if args.save:
        Path(args.save).parent.mkdir(parents=True, exist_ok=True)
        Path(args.save).write_text(json.dumps(result, indent=1))
        print("saved", args.save)


if __name__ == "__main__":
    main()
