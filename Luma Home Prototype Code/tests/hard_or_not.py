"""Hard or not: things a person says on a bad day ("hard") and on an ordinary or a good one ("not"), marked by hand.

Everything Luma does for someone who's hurting starts with reading that they are (luma.agent.feelings.read). A hard
line it doesn't read as hard gets no care: no "be with them first", no comfort the way they asked for it, a joke
allowed. An ordinary line it reads as hard gets tiptoed around.

- "hard": said by someone hurt, humiliated, scared, lonely, let down, worn down or grieving. Must be read as a feeling
  that isn't a good one.
- "not": plain talk, plans, small complaints with no weight, and good news. Must not be read as a hard feeling.

Written fresh, the way people talk. Half the sentence shapes and half of every list's values are "dev" (for building
on); the rest is "heldout": never printed, never tuned on, numbers only.
"""
from __future__ import annotations

L = {
    "who": ["manager", "boss", "landlord", "best friend", "sister", "brother", "roommate", "coworker", "mom", "dad", "teacher", "coach",
            "girlfriend", "boyfriend", "neighbor", "cousin"],
    "crowd": ["everyone", "the whole team", "the whole class", "my friends", "all the customers", "the entire office", "my family", "a full room",
              "the group chat", "my kids", "strangers", "the neighbors", "half the school", "our clients", "the whole table", "people I respect"],
    "bill": ["rent", "car payment", "tuition", "electric bill", "medical bill", "insurance", "phone bill", "credit card", "daycare", "loan",
             "vet bill", "heating bill", "bus pass", "groceries", "the deposit", "school fees"],
    "thing": ["interview", "audition", "exam", "presentation", "tryout", "driving test", "performance review", "first date", "pitch", "recital",
              "sales call", "final", "speech", "open mic", "certification", "demo"],
    "loss": ["grandma", "grandpa", "dog", "cat", "uncle", "aunt", "old friend", "mentor", "neighbor", "cousin", "horse", "godmother",
             "teammate", "dad", "mom", "brother"],
    "place": ["this city", "work", "school", "this town", "the office", "church", "the gym", "my building", "the base", "campus", "this country",
              "the new job", "my team", "the dorm", "this neighborhood", "the hospital"],
    "time": ["today", "tonight", "this week", "again", "this morning", "all day", "lately", "since Monday", "all weekend", "for days", "this month",
             "right now", "yesterday", "at lunch", "this afternoon", "last night"],
    "food": ["tacos", "ramen", "pancakes", "curry", "pizza", "soup", "dumplings", "a sandwich", "pasta", "stir-fry", "sushi", "chili", "a salad",
             "waffles", "fried rice", "burgers"],
    "show": ["a documentary", "the game", "that new series", "a cooking show", "an old movie", "the finale", "a podcast", "the news", "anime",
             "a baking show", "the highlights", "a mystery", "stand-up", "a nature show", "reruns", "the match"],
    "errand": ["the store", "the bank", "the post office", "the gym", "the pharmacy", "the laundromat", "the library", "the dentist", "the market",
               "the mechanic", "the barber", "the vet", "the hardware store", "the bakery", "the dry cleaner", "the park"],
    "win": ["the job", "a raise", "the apartment", "an A", "the scholarship", "the promotion", "my license", "the part", "the grant", "a bonus",
            "the contract", "first place", "the internship", "my visa", "the lease", "the lead role"],
}

SHAPES = [
    ("hard", "my {who} humiliated me in front of {crowd} {time}"),
    ("hard", "I can't afford the {bill} and I don't know what to do"),
    ("hard", "my {who} stopped answering my texts and it really hurts"),
    ("hard", "I completely froze during my {thing} and I want to crawl into a hole"),
    ("hard", "it's the first holiday without my {loss} and I'm not okay"),
    ("hard", "nobody at {place} even knows my name"),
    ("hard", "my {who} screamed at me {time} and I'm still shaking"),
    ("hard", "I'm terrified about my {thing} tomorrow, I can't breathe right"),
    ("hard", "I got rejected for {win} and I feel worthless"),
    ("hard", "I've been crying in the bathroom at {place} {time}"),
    ("hard", "my {who} told me I'm a disappointment"),
    ("hard", "I feel like I don't belong at {place}"),
    ("hard", "we buried my {loss} last week and the house is so quiet"),
    ("hard", "I'm behind on the {bill} {time} and I'm panicking"),
    ("hard", "my {who} left me out {time} and it stung more than I thought"),
    ("hard", "I messed up my {thing} and now I can't stop replaying it"),
    ("hard", "I haven't talked to a single person {time} and it's getting to me"),
    ("hard", "my {who} said something cruel {time} and I can't shake it"),
    ("hard", "I didn't get {win} and I'm crushed"),
    ("hard", "I keep having panic attacks at {place}"),
    ("hard", "everyone at {place} got invited except me"),
    ("hard", "I miss my {loss} so much it's hard to get up"),
    ("hard", "my {who} laughed at me in front of {crowd}"),
    ("hard", "I'm so ashamed of how my {thing} went"),
    ("not", "I'm making {food} {time}"),
    ("not", "I got {win}!!"),
    ("not", "I'm heading to {errand} {time}"),
    ("not", "thinking of watching {show} {time}"),
    ("not", "my {who} is coming over for {food}"),
    ("not", "my {thing} is on Thursday, any tips"),
    ("not", "I need to pay the {bill} {time}"),
    ("not", "what should I make with {food} leftovers"),
    ("not", "my {who} and I watched {show} {time}"),
    ("not", "I walked to {errand} and back"),
    ("not", "guess what, I finally got {win}"),
    ("not", "I had {food} for lunch {time}"),
    ("not", "my {who} sent me a funny picture {time}"),
    ("not", "is {show} any good"),
    ("not", "I'm at {errand} {time}, back soon"),
    ("not", "my {thing} went great, I'm so happy"),
    ("not", "we're having {food} with my {who} {time}"),
    ("not", "remind me about the {bill} on Friday"),
    ("not", "I passed my {thing}!"),
    ("not", "I'm going to {place} early {time}"),
    ("not", "my {who} got {win}, I'm proud of them"),
    ("not", "put {show} on my list"),
    ("not", "I love it at {place} {time}"),
    ("not", "the {thing} got moved to next week"),
]


def _values(key, half):
    values = L[key]
    return values[:len(values) // 2] if half == "dev" else values[len(values) // 2:]


def lines(half):
    """[(what they said, "hard" or "not")] for one half, 150 of each, none said twice."""
    if half not in ("dev", "heldout"):
        raise ValueError("dev or heldout")
    out, seen = [], set()
    for label in ("hard", "not"):
        shapes = [s for lab, s in SHAPES if lab == label]
        mine = shapes[0::2] if half == "dev" else shapes[1::2]
        made, turn = 0, 0
        while made < 150 and turn < 8000:
            shape = mine[turn % len(mine)]
            round_ = turn // len(mine)
            keys = [part.split("}")[0] for part in shape.split("{")[1:]]
            pools = [_values(k, half) for k in keys]
            pick = [pool[(round_ * (i + 1) + i + (round_ // len(pool)) * i) % len(pool)] for i, pool in enumerate(pools)]
            text = shape.format(**dict(zip(keys, pick)))
            turn += 1
            if text not in seen:
                seen.add(text)
                out.append((text, label))
                made += 1
    return out


def read_as_hard(text):
    """Luma reads a feeling here that isn't a good one."""
    from luma.agent import feelings
    felt = feelings.read(text)
    return bool(felt) and felt.get("family") not in feelings.GOOD


def score(half):
    """{"hard": (read as hard, of), "not": (left alone, of)}. Numbers only."""
    rows = lines(half)
    hard = [t for t, lab in rows if lab == "hard"]
    calm = [t for t, lab in rows if lab == "not"]
    return {"hard": (sum(read_as_hard(t) for t in hard), len(hard)), "not": (sum(not read_as_hard(t) for t in calm), len(calm))}


if __name__ == "__main__":
    for half in ("dev", "heldout"):
        s = score(half)
        print(half, "hard", "%d/%d" % s["hard"], "not", "%d/%d" % s["not"])
