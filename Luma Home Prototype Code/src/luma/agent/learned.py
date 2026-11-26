"""Everything Luma has learned about how to be with this person, as lines they can read and undo
(docs/PRESENCE_MASTER_PROMPT.md, 3.2: "nothing learned is a guess they can't see").

One list for both apps: how they want to be met (luma.agent.rapport), the words of theirs Luma picked up
(luma.agent.pickup) and what Luma changed about itself (luma.agent.tuning). Each line has its reason, in their own
words or Luma's own count, and a key that takes it back.
"""
from __future__ import annotations


def rows(agent):
    from luma.agent import pickup, rapport, tuning
    out = list(rapport.view(agent.store.setting(rapport.KEY), agent.clock()))
    for change in tuning.view(agent)["log"]:
        if change.get("undone"):
            continue
        reason = {"said": change["said"], "at": change.get("at")} if change.get("said") else {"noticed": change.get("why") or "", "at": change.get("at")}
        if change.get("dial") == "speaks":
            text = "I check in the way I used to" if change.get("says") == "more" and change.get("to") == 0 else "I check in a bit more again" if change.get("says") == "more" \
                else "I don't check in on my own" if change.get("to") == tuning.QUIETEST else "I check in less: once a day at most"
        else:
            text = "I keep my replies shorter" if change.get("says") == "shorter" else "I say a bit more"
        out.append({"key": "tuned:" + change["id"], "text": text, "because": [reason]})
    for word in pickup.view(agent)[:20]:
        out.append({"key": "word:" + word["word"], "text": f"“{word['word']}” is a word of yours", "because": [{"said": word["in"], "at": word.get("at")}]})
    return out


def forget(agent, key):
    """Take one line back, whichever kind it is."""
    from luma.agent import pickup, rapport, tuning
    key = str(key or "")
    if key.startswith("word:"):
        pickup.forget(agent, key[5:])
    elif key.startswith("tuned:"):
        tuning.undo(agent, key[6:])
    else:
        agent.store.set_setting(rapport.KEY, rapport.drop(agent.store.setting(rapport.KEY), key))
    return rows(agent)
