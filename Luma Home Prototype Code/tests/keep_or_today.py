"""Keep or today: 500 things a person says, each marked by hand as something a friend would still know next week
("keep": a name, a birthday, where something is, what they love or can't eat, where they live, their work, a pet, a
plan) or something that belongs to today ("today": a long day, the weather, a mood, a question, a small complaint).

A "keep" line should become a card in the memory deck. A "today" line never should: it stays in the day's chat.

Written fresh, the way people talk, including shapes Luma's rules may not read yet: the number is honest, not fitted.
Half is for building on ("dev": half of the sentence shapes and half of every list's values), half is held out
("heldout": the other shapes and the other values). A held-out line is never printed and no rule is tuned on one.
"""
from __future__ import annotations


LISTS = {
    "name": ["Dana", "Marcus", "Priya", "Tomas", "Keiko", "Luis", "Hannah", "Omar", "Nina", "Jamal", "Sofia", "Ethan"],
    "rel": ["sister", "brother", "mom", "dad", "best friend", "girlfriend", "boyfriend", "wife", "husband", "roommate", "cousin", "aunt"],
    "city": ["Austin", "Denver", "Osaka", "Tampa", "Columbus", "Fukuoka", "Portland", "Atlanta", "Sapporo", "Tucson", "Boise", "Nagoya"],
    "month": ["January", "March", "May", "July", "September", "November", "February", "April", "June", "August", "October", "December"],
    "day": ["3", "9", "14", "21", "27", "30", "2", "8", "12", "19", "24", "28"],
    "obj": ["keys", "wallet", "passport", "charger", "glasses", "headphones", "laptop", "umbrella", "jacket", "backpack", "watch", "tickets"],
    "place": ["on the kitchen counter", "in the top drawer", "by the front door", "under the bed", "in the hall closet", "on my desk",
              "in the glove box", "on the bookshelf", "next to the TV", "in my gym bag", "behind the couch", "on the nightstand"],
    "carplace": ["on level 3", "behind the gym", "on Maple Street", "in the back lot", "near the east entrance", "in row G",
                 "by the pharmacy", "on the roof deck", "across from the bank", "in spot 42", "under the bridge", "at the far end"],
    "allergen": ["peanuts", "shellfish", "penicillin", "cats", "pollen", "eggs", "latex", "dairy", "soy", "bee stings", "mold", "walnuts"],
    "thing": ["spicy ramen", "old jazz records", "horror movies", "long bike rides", "thrift stores", "rainy mornings",
              "karaoke nights", "black coffee", "crossword puzzles", "road trips", "baking bread", "camping"],
    "yuck": ["cilantro", "olives", "mushrooms", "country music", "reality TV", "crowded trains", "mayonnaise", "licorice",
             "small talk", "scary movies", "raw onions", "early flights"],
    "fav": ["color is teal", "band is Radiohead", "movie is Spirited Away", "food is tacos al pastor", "season is fall", "team is the Braves",
            "author is Murakami", "dessert is tiramisu", "show is Parks and Rec", "holiday is Thanksgiving", "sport is tennis", "drink is iced matcha"],
    "job": ["nurse", "welder", "paralegal", "line cook", "kindergarten teacher", "roofer", "dental hygienist", "bus driver",
            "graphic designer", "pharmacist", "translator", "mechanic"],
    "company": ["Brightside Dental", "Toyota", "Delta", "Whole Foods", "Rakuten", "Home Depot", "Mercy Hospital", "Nintendo",
                "FedEx", "Lincoln Elementary", "Costco", "Uniqlo"],
    "pet": ["dog", "cat", "rabbit", "parrot", "hamster", "turtle", "puppy", "kitten", "ferret", "lizard", "horse", "bird"],
    "petname": ["Biscuit", "Mochi", "Pepper", "Ziggy", "Olive", "Tank", "Noodle", "Clementine", "Bandit", "Sushi", "Waffles", "Juniper"],
    "diet": ["vegetarian", "vegan", "lactose intolerant", "diabetic", "pescatarian", "gluten free",
             "vegetarian now", "vegan these days", "diabetic, type 1", "lactose intolerant, sadly", "pescatarian", "gluten-free"],
    "goal": ["a trip to Kyoto", "a down payment", "a new laptop", "my sister's wedding", "a used car", "flight school",
             "a camera", "moving out", "a ring", "grad school", "a motorcycle", "a trip home for Christmas"],
    "food": ["pork", "red meat", "anything fried", "gluten", "sugar anymore", "seafood", "beef", "dairy", "eggs", "meat", "raw fish", "bread"],
    "fear": ["heights", "spiders", "flying", "deep water", "needles", "the dark", "dogs", "elevators", "clowns", "thunder", "snakes", "dentists"],
    "years": ["two", "five", "eleven", "twenty", "six", "thirty", "three", "eight", "fifteen", "nine", "twelve", "four"],
    "age": ["two", "five", "eleven", "six", "three", "eight", "nine", "twelve", "four", "seven", "ten", "thirteen"],
    "subject": ["math", "English", "biology", "art", "history", "music", "chemistry", "Spanish", "PE", "physics", "drama", "geography"],
    # ---- today ----
    "where": ["work", "the office", "school", "the hospital", "the shop", "the warehouse", "the restaurant", "the clinic", "the site", "the store", "the depot", "campus"],
    "tired": ["tired", "wiped", "sleepy", "drained", "fried", "beat", "exhausted", "worn out", "out of it", "sluggish", "zonked", "burnt out"],
    "today": ["today", "tonight", "right now", "this morning", "this afternoon", "this evening", "rn", "at the moment", "lately today", "all day", "since lunch", "tbh"],
    "hassle": ["traffic", "the train", "the line at the store", "the bus", "the commute", "parking", "the wifi", "the elevator",
               "the meeting", "the drive home", "checkout", "the subway"],
    "bad": ["awful", "a mess", "so slow", "a nightmare", "ridiculous", "packed", "terrible", "the worst", "brutal", "a joke", "unreal", "painful"],
    "weather": ["raining", "freezing", "so humid", "windy", "pouring", "gloomy", "snowing", "boiling out", "foggy", "drizzling", "muggy", "icy"],
    "activity": ["make some tea", "hop in the shower", "heat up leftovers", "go for a walk", "fold laundry", "watch something",
                 "do the dishes", "lie down for a bit", "take out the trash", "scroll for a while", "make dinner", "call it a night"],
    "reaction": ["hilarious", "wild", "so true", "kind of sad honestly", "a lot", "fair", "ridiculous", "actually sweet", "rough", "interesting", "weird", "nuts"],
    "ask": ["make for dinner", "watch tonight", "do this weekend", "wear tomorrow", "cook with chicken", "listen to",
            "read next", "get for lunch", "do about my hair", "name my playlist", "bring to the potluck", "say back"],
    "request": ["tell me a joke", "play something chill", "set a timer for ten minutes", "give me a fun fact", "pick a number",
                "tell me the weather", "flip a coin", "read me the news", "turn it down a little", "say that again", "spell necessary", "count to five"],
    "dayname": ["Monday", "Thursday", "Friday", "Sunday", "the weekend", "Wednesday", "Tuesday", "Saturday", "almost midnight", "the end of the month", "dinner time", "this late"],
    "mood": ["in a mood", "so quiet", "being weird", "kind of short with me", "extra chatty", "grumpy",
             "all over the place", "weirdly nice", "super distracted", "on edge", "in a rush", "cranky"],
    "earworm": ["song", "jingle", "chorus", "tune", "theme song", "ad", "melody", "beat", "hook", "ringtone", "riff", "verse"],
    "dragged": ["dragged", "flew by", "was a blur", "felt endless", "was nonstop", "was weird",
                "was fine I guess", "went sideways", "was a lot", "was slow", "was chaos", "never ended"],
    "adj": ["rough", "fine", "boring", "nuts", "slow", "kind of great", "exhausting", "meh", "wild", "okay", "long", "chaotic"],
    "game": ["game", "match", "fight", "race", "show", "episode", "finale", "set", "concert", "stream", "movie", "quiz"],
    "feeling": ["off", "restless", "blah", "wired", "low", "antsy", "flat", "jittery", "mopey", "spacey", "tense", "foggy"],
    "doing": ["chilling", "cooking", "cleaning up", "watching TV", "winding down", "scrolling", "doing laundry", "eating", "resting", "tidying", "hanging out", "stretching"],
    "temp": ["hot", "cold", "stuffy", "dry", "humid", "drafty", "warm", "chilly", "bright", "loud", "dark", "quiet"],
    "want": ["nap", "coffee", "vacation", "snack", "drink", "break", "hug", "shower", "day off", "burger", "stretch", "minute"],
    "body": ["back", "head", "neck", "feet", "knee", "shoulder", "stomach", "wrist", "ankle", "jaw", "hip", "eyes"],
    "spill": ["spilled coffee on my shirt", "missed my stop", "dropped my toast", "locked myself out for a minute", "burned the rice", "stubbed my toe",
              "forgot my lunch", "tripped on the stairs", "sat in gum", "broke a nail", "ripped my sleeve", "lost a sock"],
    "noise": ["the neighbors are", "the dog next door is", "the construction outside is", "the kids upstairs are", "the garbage truck is", "somebody's car alarm is",
              "the people downstairs are", "the birds are", "the wind is", "the pipes are", "the street is", "the fridge is"],
}

# ("keep" | "today", the shape). Shapes alternate dev, held-out, dev, ... in this order.
SHAPES = [
    ("keep", "my {rel}'s name is {name}"),
    ("keep", "my {rel} {name} lives in {city}"),
    ("keep", "my {rel}'s birthday is {month} {day}"),
    ("keep", "{name}'s birthday is {month} {day}"),
    ("keep", "our anniversary is {month} {day}"),
    ("keep", "I left my {obj} {place}"),
    ("keep", "my {obj} is {place} if I ask later"),
    ("keep", "I parked the car {carplace}"),
    ("keep", "I'm allergic to {allergen}"),
    ("keep", "I love {thing}"),
    ("keep", "I can't stand {yuck}"),
    ("keep", "my favorite {fav}"),
    ("keep", "I live in {city}"),
    ("keep", "I grew up in {city}"),
    ("keep", "I work as a {job}"),
    ("keep", "I work at {company}"),
    ("keep", "I have a {pet} named {petname}"),
    ("keep", "my {pet}'s name is {petname}"),
    ("keep", "I'm moving to {city} in {month}"),
    ("keep", "I'm {diet}"),
    ("keep", "my {rel} works as a {job}"),
    ("keep", "my birthday is {month} {day}"),
    ("keep", "I'm from {city} originally"),
    ("keep", "I'm saving up for {goal}"),
    ("keep", "my {rel} is called {name}"),
    ("keep", "I really hate {yuck}"),
    ("keep", "I don't eat {food}"),
    ("keep", "I'm scared of {fear}"),
    ("keep", "I put my {obj} {place}"),
    ("keep", "I've been married to {name} for {years} years"),
    ("keep", "I teach {subject} at a high school"),
    ("keep", "my {rel} {name} is a {job}"),
    ("keep", "my {rel} is allergic to {allergen}"),
    ("keep", "{name} is my {rel}, by the way"),
    ("keep", "I keep my {obj} {place}"),
    ("keep", "my {rel} lives in {city} now"),
    ("keep", "my {pet} {petname} is {age} years old"),
    ("keep", "I'm a {job} at {company}"),
    ("keep", "I was born in {city}"),
    ("keep", "my {rel} {name} just moved to {city}"),
    ("today", "I had such a long day at {where}"),
    ("today", "I'm so {tired} {today}"),
    ("today", "ugh, {hassle} was {bad} today"),
    ("today", "it's {weather} again"),
    ("today", "I just got home from {where}"),
    ("today", "I'm about to {activity}"),
    ("today", "that's {reaction}"),
    ("today", "what should I {ask}?"),
    ("today", "can you {request}?"),
    ("today", "I can't believe it's already {dayname}"),
    ("today", "my {rel} was {mood} today"),
    ("today", "this {earworm} is stuck in my head"),
    ("today", "today {dragged}"),
    ("today", "work was {adj} today"),
    ("today", "I think I'm gonna {activity}"),
    ("today", "lol that's {reaction}"),
    ("today", "the {game} was {adj} tonight"),
    ("today", "I feel kind of {feeling} tonight"),
    ("today", "nothing much, just {doing}"),
    ("today", "it's so {temp} in here"),
    ("today", "I need a {want} so bad"),
    ("today", "my {body} is killing me today"),
    ("today", "guess I'll {activity}"),
    ("today", "today was {adj}, honestly"),
    ("today", "I {spill} this morning"),
    ("today", "{noise} being loud again"),
    ("today", "I'm so over {today}"),
    ("today", "{hassle} took forever, I'm {tired}"),
    ("today", "honestly I hate {today}"),
    ("today", "is it just me or is it {temp} {today}?"),
    ("today", "I love it when {hassle} is {bad}, said nobody"),
    ("today", "didn't sleep great, feeling {feeling}"),
    ("today", "I'm {tired} and it's only {dayname}"),
    ("today", "{hassle} was {bad}, and it's {weather} too"),
    ("today", "I'm just {doing} {today}"),
    ("today", "kind of a {adj} day at {where}"),
    ("today", "I could really use a {want} {today}"),
    ("today", "the {game} last night was {adj}"),
    ("today", "my {body} hurts after {where} today"),
    ("today", "I'm {feeling} and {tired}, that's all"),
]


def _values(key, half):
    values = LISTS[key]
    mid = len(values) // 2
    return values[:mid] if half == "dev" else values[mid:]


def lines(half):
    """[(what they said, "keep" or "today")] for one half: "dev" or "heldout". 125 of each, none said twice."""
    if half not in ("dev", "heldout"):
        raise ValueError("dev or heldout")
    out, seen = [], set()
    for label in ("keep", "today"):
        shapes = [s for lab, s in SHAPES if lab == label]
        mine = shapes[0::2] if half == "dev" else shapes[1::2]
        made, turn = 0, 0
        while made < 125 and turn < 5000:
            shape = mine[turn % len(mine)]
            round_ = turn // len(mine)
            keys = [part.split("}")[0] for part in shape.split("{")[1:]]
            pools = [_values(k, half) for k in keys]
            # each list is walked at its own pace, so every value comes up and no line repeats
            pick = [pool[(round_ * (i + 1) + i + (round_ // len(pool)) * i) % len(pool)] for i, pool in enumerate(pools)]
            text = shape.format(**dict(zip(keys, pick)))
            turn += 1
            if text in seen:
                continue
            seen.add(text)
            out.append((text, label))
            made += 1
    return out


def cards(text):
    """The memory cards Luma would make from one thing they said, the way a turn does (Agent._notice): the rules, then the
    small model where the rules found nothing (luma.agent.keeps)."""
    from luma.agent import keeps
    return keeps.cards(text)


def cards_by_rule(text):
    """The rules alone, as it was before the model."""
    from luma.agent import people, presence
    return presence.notice_facts(text) + people.facts(text)


def score(half):
    """{"keep": (became a card, of), "today": (stayed out of the deck, of)} for one half. Numbers only."""
    rows = lines(half)
    keep = [t for t, lab in rows if lab == "keep"]
    today = [t for t, lab in rows if lab == "today"]
    return {"keep": (sum(1 for t in keep if cards(t)), len(keep)), "today": (sum(1 for t in today if not cards(t)), len(today))}


if __name__ == "__main__":
    for half in ("dev", "heldout"):
        s = score(half)
        print(half, "keep", "%d/%d" % s["keep"], "today", "%d/%d" % s["today"])
