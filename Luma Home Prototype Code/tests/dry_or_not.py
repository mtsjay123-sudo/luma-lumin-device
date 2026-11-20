"""Dry or not: good words about something that went wrong ("oh great, my card got declined"), against the same good
words about something good ("oh great, I got the job") and a plain gripe with no good words in it.

Luma's reader of sarcasm is luma.agent.feelings.dry(). When it reads a gripe as good news, Luma cheers at a flat tire;
when it reads good news as a gripe, Luma groans at someone's new job. Both are checked.

- "dry":   good words, a bad thing. feelings.dry() must be true, and the feeling read must not be a good one.
- "glad":  good words, a good thing. feelings.dry() must be false.
- "plain": a bad thing said plainly. feelings.dry() must be false (it's a gripe, and not a sarcastic one).

Written fresh on Nov 20, 2026. Half the sentence shapes and half of every list's values are "dev" (for building on);
the rest is "heldout": never printed, never tuned on, numbers only.
"""
from __future__ import annotations

L = {
    "yay": ["oh great", "perfect", "awesome", "wonderful", "fantastic", "lovely", "love that", "so glad", "lucky me", "cool", "amazing", "brilliant",
            "oh joy", "yay", "just great", "how nice", "terrific", "super", "oh good", "what a treat", "beautiful", "just perfect", "nice", "delightful"],
    "bad": ["my car won't start", "the wifi is down again", "I spilled coffee on my laptop", "my flight got cancelled", "the dog ate my headphones",
            "I locked my keys in the car", "my card got declined", "the sink is leaking again", "I missed the last train", "my phone screen cracked",
            "the power's out", "they double-booked my appointment", "I got a parking ticket", "the elevator is broken", "my package got stolen",
            "I left my wallet at home", "the heat is out", "the bus drove right past me", "my alarm didn't go off", "it's pouring on my one day off",
            "the landlord raised the rent", "the washer flooded the floor", "I burned dinner", "my laptop crashed mid-save"],
    "good": ["I got the job", "I passed my exam", "my sister had her baby", "we got the apartment", "I got a raise", "my results came back clear",
             "I won the raffle", "my flight got upgraded", "they approved my visa", "I finished my thesis", "my team won", "I got tickets to the show",
             "my package came early", "I fixed the sink myself", "my mom's surgery went well", "I made the team", "we closed on the house",
             "my brother got engaged", "I got into grad school", "the test came back negative", "I paid off my car", "my book got accepted",
             "I got the scholarship", "my visa came through"],
    "when": ["today", "this morning", "again", "tonight", "right before work", "on my birthday", "of all days", "five minutes ago", "this week",
             "at the worst time", "on a monday", "in front of everyone", "right now", "yesterday", "just now", "for the third time"],
    # when good news happened: plain time words only. ("I got the job at the worst time, great" isn't plainly good news;
    # the first numbers taken with this set had such lines marked "glad", and were thrown away.)
    "day": ["today", "this morning", "tonight", "just now", "yesterday", "this week", "an hour ago", "this afternoon", "last night", "on friday",
            "a minute ago", "over the weekend", "earlier", "at lunch", "this evening", "on my way home"],
}

SHAPES = [
    ("dry", "{yay}, {bad}"),
    ("dry", "{yay}, {bad} {when}"),
    ("dry", "{bad}. {yay}."),
    ("dry", "well {yay}, {bad}"),
    ("dry", "{yay}. {bad} {when}."),
    ("dry", "{bad} {when}, {yay}"),
    ("dry", "oh {yay}, now {bad}"),
    ("dry", "{yay}, just what I needed: {bad}"),
    ("dry", "{bad} {when}. so that's {yay}"),
    ("dry", "{yay} {yay}, {bad}"),
    ("dry", "guess what, {bad}. {yay}"),
    ("dry", "{yay}, because of course {bad} {when}"),
    ("glad", "{yay}, {good}"),
    ("glad", "{yay}, {good} {day}"),
    ("glad", "{good}! {yay}!"),
    ("glad", "{good} {day}, {yay}"),
    ("glad", "guess what, {good}. {yay}"),
    ("glad", "{yay}!! {good}"),
    ("glad", "{good} and I'm so happy"),
    ("glad", "{yay}, finally: {good}"),
    ("plain", "{bad}"),
    ("plain", "ugh, {bad} {when}"),
    ("plain", "{bad} {when} and I'm so annoyed"),
    ("plain", "I can't believe {bad}"),
    ("plain", "{bad}, what a mess"),
    ("plain", "so {bad} {when}"),
]
COUNT = {"dry": 150, "glad": 100, "plain": 75}


def _values(key, half):
    values = L[key]
    return values[:len(values) // 2] if half == "dev" else values[len(values) // 2:]


def lines(half):
    """[(what they said, "dry" | "glad" | "plain")] for one half, none said twice."""
    if half not in ("dev", "heldout"):
        raise ValueError("dev or heldout")
    out, seen = [], set()
    for label, count in COUNT.items():
        shapes = [s for lab, s in SHAPES if lab == label]
        mine = shapes[0::2] if half == "dev" else shapes[1::2]
        made, turn = 0, 0
        while made < count and turn < 8000:
            shape = mine[turn % len(mine)]
            round_ = turn // len(mine)
            keys = [part.split("}")[0] for part in shape.split("{")[1:]]
            pools = [_values(k, half) for k in keys]
            pick = [pool[(round_ * (i + 1) + i * 5 + (round_ // len(pool)) * (i + 2)) % len(pool)] for i, pool in enumerate(pools)]
            text = shape.format(**dict(zip(keys, pick))) if len(set(keys)) == len(keys) else _twice(shape, keys, pick)
            turn += 1
            if text not in seen:
                seen.add(text)
                out.append((text, label))
                made += 1
    return out


def _twice(shape, keys, pick):
    """A shape that uses one list twice ("{yay} {yay}, {bad}"): each blank gets its own value."""
    text = shape
    for key, value in zip(keys, pick):
        text = text.replace("{" + key + "}", value, 1)
    return text


def read_dry(text):
    from luma.agent import feelings
    return bool(feelings.dry(" ".join(text.lower().split())))


def read_good(text):
    from luma.agent import feelings
    felt = feelings.read(text)
    return bool(felt) and felt.get("family") in feelings.GOOD


def score(half):
    """{"dry": (read as a gripe, of), "dry_cheered": how many of the gripes are read as good news, "glad": (left as good news, of),
    "plain": (not called sarcasm, of)}. Numbers only."""
    rows = lines(half)
    dry = [t for t, lab in rows if lab == "dry"]
    glad = [t for t, lab in rows if lab == "glad"]
    plain = [t for t, lab in rows if lab == "plain"]
    return {"dry": (sum(read_dry(t) for t in dry), len(dry)), "dry_cheered": sum(read_good(t) and not read_dry(t) for t in dry),
            "glad": (sum(not read_dry(t) for t in glad), len(glad)), "plain": (sum(not read_dry(t) for t in plain), len(plain))}


if __name__ == "__main__":
    for half in ("dev", "heldout"):
        s = score(half)
        print(half, "dry read as a gripe %d/%d" % s["dry"], "(read as good news instead: %d)" % s["dry_cheered"], "| good news left alone %d/%d" % s["glad"],
              "| plain gripe not called sarcasm %d/%d" % s["plain"])
