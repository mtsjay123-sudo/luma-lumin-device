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
                  f"| Most times one reply was given to different questions | {b.get('same_reply', '-')} | {a.get('same_reply', '-')} |",
                  f"| Average words per reply | {b['avg_words']} | {a['avg_words']} |", "",
                  "At least as honest as the stock brain on every check, with no loops: " + ("**yes**" if r.get("as_honest") else "**no** (not published)")]
        lines += ["", "## Side by side", ""]
        for before, after in list(zip(r.get("before_replies", []), r.get("after_replies", [])))[:12]:
            q = before["question"].split("\n")[0][:120]
            lines += [f"- **{q}**", f"  - stock: {before['reply'][:200]}", f"  - Luma: {after['reply'][:200]}"]
    lines += ["", "Load it in Luma: Settings, Brain, Luma's own brain (or set LUMA_LORA_PATH to this file)."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.stdout.write(report(sys.argv[1]))
