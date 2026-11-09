"""A short Markdown report of a training run (eval.json from scripts/train_luma.py), for the run's page and the release notes."""
import json
import sys


def report(path):
    r = json.loads(open(path, encoding="utf-8").read())
    lines = [f"# Luma brain: {r.get('base')}", "",
             f"Trained {r.get('steps', 0)} steps on {r.get('conversations_seen', 0)} of {r.get('of', 0)} conversations "
             f"({r.get('tokens', 0):,} tokens) in {r.get('minutes', 0)} minutes on {r.get('device')}; final loss {r.get('final_loss')}"
             + (" (stopped at the time budget)." if r.get("stopped_for_time") else ".")]
    if r.get("before") and r.get("after"):
        b, a = r["before"], r["after"]
        lines += ["", "| Held-out check | Stock brain | Luma brain |", "|---|---|---|",
                  f"| Numbers not in what was found (lower is better) | {b['unbacked_numbers']} | {a['unbacked_numbers']} |",
                  f"| Made-up slang meanings (lower is better) | {b['made_up_slang_meanings']} | {a['made_up_slang_meanings']} |",
                  f"| Wrong meanings for real slang (lower is better) | {b.get('wrong_slang_meanings', '-')} | {a.get('wrong_slang_meanings', '-')} |",
                  f"| Replies stuck repeating a sentence | {b.get('loops', '-')} | {a.get('loops', '-')} |",
                  f"| Said an earlier reply again instead of answering the newest message | {b.get('said_before', '-')} | {a.get('said_before', '-')} |",
                  f"| Brushed them off (a word or two, or only a question back when they asked for ideas) | {b.get('brushed_off', '-')} | {a.get('brushed_off', '-')} |",
                  f"| Flat (a bare list said to nobody, when they talked about their life) | {b.get('flat', '-')} | {a.get('flat', '-')} |",
                  f"| Said their message back to them (\"Okay, work was a lot.\") | {b.get('parrots', '-')} | {a.get('parrots', '-')} |",
                  f"| **Human test**: of 10 moments a friend gets right (higher is better) | {b.get('human_passed', '-')} | {a.get('human_passed', '-')} |",
                  f"| **Not safe, on its own**: of the held-out not-safe moments, asked if they're safe or gave 988, with no safety net (higher is better) | {b.get('safety_passed', '-')} | {a.get('safety_passed', '-')} |",
                  f"| Most times one reply was given to different questions | {b.get('same_reply', '-')} | {a.get('same_reply', '-')} |",
                  f"| Average words per reply | {b['avg_words']} | {a['avg_words']} |", "",
                  "At least as honest as the stock brain on every check, with no loops: " + ("**yes**" if r.get("as_honest") else "**no** (not published)")]
        if r.get("after_human"):
            lines += ["", "## Human test, side by side", ""]
            for before, after in zip(r.get("before_human", []), r["after_human"]):
                lines += [f"- **{after['said']}** ({after['kind']})",
                          f"  - stock: {before['reply'][:200]}" + (f" *({before['missed']})*" if before.get("missed") else ""),
                          f"  - Luma: {after['reply'][:200]}" + (f" *({after['missed']})*" if after.get("missed") else "")]
        lines += ["", "## Side by side", ""]
        for before, after in list(zip(r.get("before_replies", []), r.get("after_replies", [])))[:12]:
            q = before["question"].split("\n")[0][:120]
            lines += [f"- **{q}**", f"  - stock: {before['reply'][:200]}", f"  - Luma: {after['reply'][:200]}"]
    lines += ["", "Load it in Luma: Settings, Brain, Luma's own brain (or set LUMA_LORA_PATH to this file)."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.stdout.write(report(sys.argv[1]))
