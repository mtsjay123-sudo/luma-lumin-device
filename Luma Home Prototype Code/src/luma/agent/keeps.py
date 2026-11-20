"""A lasting fact said in a way the rules don't know: kept as a card anyway.

Luma's rules (presence.notice_facts, people.facts) read "my sister's name is Dana" and never take "I had such a long day"
for a fact. They miss a lasting fact said a new way: on the held-out half of keep-or-today, a third of them
(tests/keep_or_today.py). Rules built on the dev half moved that half by nothing, five times over.

So: the rules first. Where they find nothing, a small model (keeps.npz, the same kind as the best-friend moves: a softmax
layer over hashed words) is asked whether this is something a friend would still know next week. It is believed only
when it's sure AND the sentence has the plain shape of someone stating a thing about themselves (has_shape). A passing
remark must never become a card; a missed fact is still in the day's talk and can still be recalled.

The practice sentences below were written fresh for this (Nov 20, 2026): lasting facts in many shapes, and the same
kinds of sentence about today only ("my allergies are acting up", "I'm at the dentist"). scripts/train_keeps.py teaches
the model from them and from the dev halves of the sets; it never sees a held-out line.

Never kept by the model: anything with a password, a PIN or a card number in it (rule 5), a question, a request, or a
hard moment (that belongs to the feeling, not the deck).
"""
from __future__ import annotations

import re
import threading
from pathlib import Path

LEARNED = Path(__file__).with_name("keeps.npz")
LABELS = ["keep", "today"]
SURE = 0.9   # scripts/train_keeps.py's table, on practice shapes it didn't learn from: at this cut no passing remark was kept in any training; at 0.8 one sometimes was

# Someone stating a thing about themselves, their people or their things.
ABOUT_THEM = re.compile(r"\b(?:i|i'?m|im|i'?ve|ive|i'?d|my|mine|me|we|we'?re|we'?ve|our|ours)\b", re.I)
ASKING = re.compile(r"\?|^\W*(?:(?:hey|yo|ok|okay|luma|so|and|but|well|oh|um|uh)\W+)*(?:what|who|when|where|why|how|which|whose|is|are|am|was|were|do|does|did|"
                    r"can|could|would|will|should|have|has|had|may|might|shall|please|remember|remind|tell|text|message|call|play|set|add|show|find|search|"
                    r"look|open|turn|put|let|make|give|send|read|check|start|stop|order|buy|book|any|anything|anyone|quick question)\b", re.I)
JOKING = re.compile(r"\b(?:lol|lmao|lmfao|haha+|hehe|jk|j/k|kidding|rofl)\b|[😂🤣😅😆💀]", re.I)   # said for a laugh: not a fact to keep
# What belongs to today, however it's phrased.
ONLY_TODAY = re.compile(r"\b(?:today|tonight|tonite|this (?:morning|afternoon|evening|second|minute)|right now|rn|just now|at the moment|earlier|yesterday|"
                        r"last night|all day|all night|all week|in a (?:minute|sec|second|bit|few)|about to|gonna|going to|on my way|omw|almost|still|"
                        r"again|so far|for now|later|soon|tomorrow|this weekend|in town|out of town|visiting|on (?:my|his|her|their|the) way|"
                        r"here|back|ready|awake|asleep|this|that|it)\b", re.I)
SECRET = re.compile(r"\b(?:password|passcode|pass code|pin|ssn|social security|card number|credit card|debit card|cvv|routing|account number|login|log-in|"
                    r"security code|one[- ]time code)\b|\d{6,}", re.I)
# Something that happened, told in the past: "I burned the sushi", "I gave my old guitar to my neighbor", "I wrote notes to
# everyone". A passing event, even when it's full of words a lasting fact would have, and now and then a quiet sign of
# something else. What stays true afterwards is the exception ("I moved to Denver", "I grew up in Osaka", "we got married").
STAYS_TRUE = re.compile(r"^\W*(?:i|we)\s+(?:(?:just|already|finally|even|never|always|actually|also|recently)\s+)*(?:was (?:born|raised|adopted|diagnosed)|"
                        r"were married|grew up|moved (?:to|here|from|back|in with)|lived|worked|named|adopted|married|graduated|retired|learned|studied|"
                        r"majored|served|started (?:at|working|school|college|my own)|converted|immigrated|enlisted|became|quit|gave up|taught|met my|"
                        r"got (?:married|engaged|divorced|sober|diagnosed|my (?:degree|license|diploma|ged|citizenship|black belt))|"
                        r"went (?:vegan|vegetarian|pescatarian|keto|gluten|dairy|sober|to (?:college|school|university|\w+ (?:state|university|college))))\b", re.I)
PAST = (r"\w+ed|gave|wrote|sold|sent|said|told|took|made|did|went|got|had|saw|ate|bought|found|lost|left|came|ran|drove|heard|met|felt|thought|spent|"
        r"slept|woke|broke|paid|caught|threw|put|cut|let|kept|held|brought|built|chose|drew|fell|flew|forgot|froze|hid|hit|hurt|knew|laid|led|lent|"
        r"lit|rode|rang|rose|sang|sat|shut|spoke|stood|stole|swam|swept|tore|won|wore|was|were|burnt")
HAPPENED = re.compile(r"^\W*(?:i|we)\s+(?:(?:just|already|finally|even|actually|also|recently)\s+)*(?:" + PAST + r")\b", re.I)
# The same, said as done: "I've given my records away", "I've stopped answering my phone".
DONE = re.compile(r"\b(?:i|we)(?:'ve|’ve| have|ve)\s+(?:(?:just|already|finally|even|actually)\s+)*(?:stopped|started|given|written|sold|sent|said|told|taken|"
                  r"made|done|gone|gotten|seen|eaten|bought|found|lost|left|decided|finished|cancelled|canceled|deleted|cleaned|packed|thrown|put)\b", re.I)


def happened(said):
    """Is this something that happened, not something that is? ("I gave my guitar away" yes; "I moved to Denver" no.)"""
    return bool((HAPPENED.search(said) and not STAYS_TRUE.search(said)) or DONE.search(said))


# Something they don't do, can't do or have stopped doing. Said about food, drink or driving it's a fact about them. Said
# about leaving the house, answering the phone, sleeping or eating at all, it's how a bad stretch sounds ("I haven't
# really left the apartment this week", "I've stopped answering my phone"), and it is never a card. So a negative is
# only believed in the few forms a lasting fact takes.
NEGATED = re.compile(r"\b(?:\w+n['’]t|dont|cant|wont|isnt|arent|wasnt|didnt|doesnt|havent|hasnt|couldnt|wouldnt|shouldnt|aint|cannot|not|never|"
                     r"no longer|stopped|quit|without|barely|hardly|nothing|nobody|none)\b", re.I)
LASTING_NO = re.compile(r"\b(?:don['’]?t|do not|doesn['’]?t|can['’]?t|cannot|won['’]?t) (?:eat|drink|drive|smoke|have (?:a|any) (?:car|tv|license|kids|siblings|pets)|"
                        r"have (?:kids|siblings|pets|\w+)\b(?=.*\ballerg)|do (?:caffeine|dairy|gluten|meat|spicy)|talk to my|speak to my|speak (?:any )?\w+)\b|"
                        r"\bcan'?t (?:have|stand|handle|do (?:dairy|gluten|spicy))\b|\bnever (?:liked|learned|been (?:a|much|married|to)|had (?:a|kids)|"
                        r"married|met my|knew my)\b|\bnot (?:a fan|much of|close|married|religious|a (?:big |huge )?\w+ person)\b|"
                        r"\bquit (?:smoking|drinking|vaping)\b|\bstopped (?:smoking|drinking|eating (?:meat|pork|beef|dairy|sugar))\b|"
                        r"\bno longer (?:eat|drink|work|live)\b|\bwithout (?:a car|kids|siblings)\b", re.I)
# Said near the end of a worry that builds, and by people who are fine: either way, the turns after it get no model cards.
QUIET_SIGN = re.compile(r"\b(?:in (?:everyone'?s|every ?one'?s|the|their|your|his|her) way|(?:things|affairs|stuff|closet|papers|room) in order|just in case|"
                        r"thanks for everything|over soon|say(?:ing)? (?:good ?bye|bye)|letters? to|gave (?:away|my)|giving (?:away|my)|tired of|"
                        r"makes? (?:a|any|no) difference|getting (?:any )?better|what'?s the (?:point|use))\b", re.I)
# News about someone: "my roommate just had a baby". It's kept as what they said (Agent._keep_line), not as a card.
NEWS = re.compile(r"\bjust\s+(?:had|got|bought|moved|left|came|quit|lost|won|found|broke|passed|finished|graduated|went|made|said|told|called|texted|did)\b", re.I)
# What they've been doing lately: "I've been putting my closet in order", "I've been sleeping a lot". Not a fact about them,
# and sometimes a quiet sign of something else. With how long ("I've been working there for six years") it's a fact.
LATELY = re.compile(r"\b(?:i|we)(?:'ve|’ve| have|ve)? been (?:\w+ )?\w+ing\b(?!.*\b(?:for|since)\b)", re.I)
# Not sure of it themselves: "idk if I should go to grad school". A fact isn't hedged.
HEDGED = re.compile(r"\b(?:idk|i don'?t know|dunno|not sure|unsure|maybe|perhaps|i think|i guess|i suppose|should i|if i should|whether|wondering|"
                    r"might|probably|thinking (?:of|about)|considering|debating|what if|kind of want|kinda want|tempted)\b", re.I)
# Never a card: anything that might be someone not being safe, or hurting. That belongs to the moment and to the crisis
# net, never to a deck of facts. (Found before this shipped: the model alone would have made a card of 18 lines of the
# crisis corpus. The net's own readers are asked first, and these words stop the rest.)
DESPAIR = re.compile(r"\b(?:alive|die|dying|dead|death|kill\w*|suicid\w*|end (?:it|things|my life)|disappear\w*|burden|worthless|hopeless|pointless|no point|"
                     r"give up|giving up|go on|hurt(?:ing)? myself|self[- ]harm|pills|overdos\w*|goodbye|wake up|not be here|without me|better off|"
                     r"can'?t (?:do|take) (?:this|it) anymore|tired of (?:living|life|everything)|(?<!live )(?<!living )alone|lonely|nobody|no one|"
                     r"left out|invisible|hate myself|depress\w*|crying|cried|numb|empty|trapped)\b", re.I)
LEAD = re.compile(r"^\W*(?:(?:oh|so|well|and|but|also|btw|by the way|fyi|fun fact|just so you know|for the record|heads up|honestly|tbh|ngl|lol|haha|ok|okay|"
                  r"hey|yo|luma|i mean|like|actually|yeah|yep|um|uh)\b[\s,:;.!-]*)+", re.I)

SLOTS = {
    "rel": ["sister", "brother", "mom", "dad", "grandma", "grandpa", "uncle", "aunt", "cousin", "niece", "nephew", "son", "daughter", "wife", "husband",
            "partner", "fiancee", "girlfriend", "boyfriend", "best friend", "roommate", "boss", "neighbor", "stepdad", "mother-in-law", "twin"],
    "name": ["Aiden", "Bianca", "Carlos", "Deja", "Elena", "Farid", "Grace", "Hiro", "Imani", "Jonah", "Kavya", "Leo", "Maya", "Noor", "Owen", "Paloma",
             "Quinn", "Rosa", "Sam", "Tess"],
    "city": ["Chicago", "Seattle", "Houston", "Kyoto", "Boston", "Phoenix", "Miami", "Yokohama", "Dallas", "Nashville", "Sendai", "Raleigh", "Kobe", "Omaha"],
    "date": ["April 12", "the 5th of June", "October 30", "Jan 22", "August 9th", "December 1st", "May 17", "the 23rd of February", "July 4th", "Sept 14"],
    "allergen": ["gluten", "tree nuts", "sesame", "strawberries", "ibuprofen", "dust", "dogs", "sulfa drugs", "kiwi", "almonds", "amoxicillin", "wasps"],
    "food": ["pork", "red meat", "seafood", "dairy", "sugar", "fried food", "bread", "eggs", "anything spicy", "beef"],
    "diet": ["vegetarian", "vegan", "pescatarian", "gluten-free", "keto", "kosher", "halal", "dairy-free", "sober", "caffeine-free"],
    "thing": ["vinyl records", "hiking", "anime", "sushi", "jigsaw puzzles", "gardening", "true crime podcasts", "pottery", "chess", "kayaking",
              "lo-fi beats", "baseball", "old westerns", "bouldering", "knitting", "thunderstorms", "bubble tea", "stand-up comedy"],
    "yuck": ["beets", "techno", "flying", "seafood", "big crowds", "coconut", "heights", "spiders", "the dentist", "cold weather", "driving at night",
             "talking on the phone", "pickles", "musicals"],
    "favkind": ["color", "band", "movie", "food", "season", "team", "book", "dessert", "show", "holiday", "sport", "drink", "ice cream", "song", "video game"],
    "fav": ["green", "The Beatles", "Totoro", "pad thai", "spring", "the Mets", "Dune", "cheesecake", "The Office", "Halloween", "soccer", "oat milk lattes",
            "pistachio", "anything by Prince", "Zelda"],
    "job": ["an electrician", "a barista", "an accountant", "an ER nurse", "a truck driver", "a software tester", "a librarian", "a paramedic",
            "a hairstylist", "an English teacher", "a chef", "a plumber", "a vet tech", "a bartender", "a social worker", "a flight attendant"],
    "company": ["a law firm downtown", "the hospital", "Honda", "the airport", "a bakery", "Sony", "the post office", "an elementary school", "Target",
                "a call center", "the city library", "a daycare", "Amazon", "the base"],
    "pet": ["dog", "cat", "bunny", "parakeet", "guinea pig", "tortoise", "corgi", "tabby", "beagle", "gecko", "goldfish", "husky"],
    "petname": ["Miso", "Rocky", "Peanut", "Ginger", "Bear", "Tofu", "Daisy", "Milo", "Coco", "Pickles", "Ramen", "Shadow"],
    "school": ["Ohio State", "community college", "nursing school", "night school", "grad school", "law school", "the university here", "trade school",
               "a language school", "art school"],
    "subject": ["nursing", "accounting", "computer science", "Japanese", "psychology", "welding", "biology", "graphic design", "culinary arts", "law"],
    "language": ["Spanish", "Tagalog", "Japanese", "ASL", "Korean", "Portuguese", "Arabic", "French", "Vietnamese", "Hindi"],
    "condition": ["asthma", "migraines", "a bad knee", "ADHD", "celiac", "type 2 diabetes", "high blood pressure", "a heart murmur", "eczema", "sleep apnea",
                  "a bad back", "epilepsy"],
    "activity": ["therapy", "volleyball practice", "choir", "Japanese class", "pottery class", "band rehearsal", "church", "my support group", "yoga",
                 "book club", "physical therapy", "trivia"],
    "weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "car": ["a blue Corolla", "an old Jeep", "a red Civic", "a minivan", "a Subaru", "a pickup", "a little hatchback", "my dad's old Camry"],
    "age": ["4", "7", "12", "16", "23", "31", "45", "58", "72", "80"],
    "count": ["two", "three", "four", "five"],
    "kin": ["kids", "brothers", "sisters", "older brothers", "little sisters", "cats", "dogs", "roommates", "stepkids", "nieces"],
    "years": ["two years", "six years", "a decade", "fifteen years", "almost a year", "twenty years", "three years", "about eight months"],
    "goal": ["a house", "a trip to Italy", "my wedding", "a motorcycle", "nursing school", "a new roof", "a move back home", "my kid's college"],
    "event": ["a half marathon", "my black belt test", "the bar exam", "a triathlon", "my citizenship test", "my CDL", "a 10k", "my pilot's license"],
    "dream": ["open a bakery", "see the northern lights", "write a novel", "live by the ocean", "learn to fly", "visit every state", "own a food truck",
              "move back to my hometown"],
    "line": ["the Blue Line", "the 6 train", "the Yamanote line", "the 42 bus", "the ferry", "the express bus", "the Chuo line", "light rail"],
    "floor": ["third", "fifth", "ninth", "top", "ground", "second"],
    "grade": ["first", "third", "fifth", "seventh", "ninth", "eleventh"],
    # only today
    "nowplace": ["the store", "the gym", "work", "the airport", "my desk", "the dentist", "the bank", "the laundromat", "a red light", "the DMV", "lunch"],
    "meal": ["pasta", "leftovers", "ramen", "a sandwich", "tacos", "eggs", "curry", "a salad", "soup", "pizza"],
    "show": ["the game", "a cooking show", "that new series", "the news", "a documentary", "cartoons", "the finale", "a movie"],
    "obj": ["keys", "wallet", "charger", "glasses", "badge", "umbrella", "headphones", "phone"],
    "pct": ["3", "8", "12", "20", "41"],
    "body": ["feet", "back", "head", "eyes", "knees", "shoulders", "legs"],
    "mood": ["tired", "exhausted", "bored", "starving", "freezing", "wiped", "stressed", "cranky", "sleepy", "hungry", "restless", "fried"],
    "chore": ["laundry", "the dishes", "my taxes", "email", "homework", "packing", "grocery shopping", "this report"],
    "time": ["3", "noon", "six", "9:30", "eight", "five thirty"],
    "doing": ["gardening", "hiking", "knitting", "kayaking", "studying", "baking", "painting", "gaming", "cleaning", "packing", "practicing", "working"],
    "state": ["at work", "on the phone", "home", "upstairs", "driving", "late", "annoyed", "sick", "busy", "cooking", "napping", "outside", "in the shower",
              "at the store", "in a mood", "over the moon", "running errands", "stuck at the airport"],
}

# (label, sentence). "keep": a friend would still know it next week. "today": the same kind of sentence, about now.
FRAMES = [
    # who's who
    ("keep", "my {rel}'s name is {name}"), ("keep", "my {rel} is called {name}"), ("keep", "{name} is my {rel}"), ("keep", "{name}'s my {rel} btw"),
    ("keep", "i have a {rel} named {name}"), ("keep", "my {rel} goes by {name}"), ("keep", "everyone calls my {rel} {name}"),
    ("keep", "{name} and i have been married {years}"), ("keep", "i've known {name} since we were kids, she's my {rel}"),
    ("keep", "my {rel} and i are really close"), ("keep", "i'm not close with my {rel}"), ("keep", "i don't talk to my {rel} anymore"),
    ("keep", "i have {count} {kin}"), ("keep", "i've got {count} {kin}"), ("keep", "i'm the oldest of {count}"), ("keep", "i'm an only child"),
    ("keep", "i'm the baby of the family"), ("keep", "i'm a twin"), ("keep", "i was adopted"), ("keep", "i'm a single parent"),
    ("keep", "i'm married"), ("keep", "i'm engaged"), ("keep", "i'm divorced"), ("keep", "i'm single"), ("keep", "i've been with my {rel} for {years}"),
    ("keep", "my {rel} raised me"), ("keep", "my {rel} is {age}"), ("keep", "my {rel} just turned {age}"), ("keep", "my {rel} is in {grade} grade"),
    # where
    ("keep", "my {rel} lives in {city}"), ("keep", "my {rel} lives out in {city}"), ("keep", "my {rel} is based in {city}"), ("keep", "my {rel}'s over in {city}"),
    ("keep", "i grew up in {city}"), ("keep", "i'm from {city} originally"), ("keep", "i'm originally from {city}"), ("keep", "born and raised in {city}, me"),
    ("keep", "we live in {city}"), ("keep", "i live in {city}"), ("keep", "i moved to {city} for work"), ("keep", "i've lived in {city} for {years}"),
    ("keep", "home for me is {city}"), ("keep", "my whole family is in {city}"), ("keep", "i live alone"), ("keep", "i live with my {rel}"),
    ("keep", "i live on the {floor} floor"), ("keep", "my apartment is on the {floor} floor"), ("keep", "i rent a place near the station"),
    # dates
    ("keep", "my birthday is {date}"), ("keep", "my bday's {date}"), ("keep", "i was born on {date}"), ("keep", "my {rel}'s birthday is {date}"),
    ("keep", "{date} is my {rel}'s birthday"), ("keep", "our anniversary is {date}"), ("keep", "we got married on {date}"), ("keep", "i'm {age}"),
    ("keep", "i'm {age} years old"), ("keep", "i turn {age} in the spring"), ("keep", "i'm a {date} baby"),
    # body, food
    ("keep", "i'm allergic to {allergen}"), ("keep", "i can't have {allergen}, i'm allergic"), ("keep", "{allergen} gives me hives"),
    ("keep", "i have a {allergen} allergy"), ("keep", "my {rel} is allergic to {allergen}"), ("keep", "i break out if i touch {allergen}"),
    ("keep", "i don't eat {food}"), ("keep", "i can't eat {food}"), ("keep", "i gave up {food} years ago"), ("keep", "i'm {diet}"),
    ("keep", "i went {diet} last year"), ("keep", "i've been {diet} since college"), ("keep", "i don't drink"), ("keep", "i quit smoking"),
    ("keep", "i don't do caffeine"), ("keep", "i have {condition}"), ("keep", "i've got {condition}"), ("keep", "i was diagnosed with {condition}"),
    ("keep", "my {rel} has {condition}"), ("keep", "i take meds for {condition}"), ("keep", "i've had {condition} since i was a kid"),
    ("keep", "i wear hearing aids"), ("keep", "i wear contacts"), ("keep", "i'm left-handed"), ("keep", "i'm colorblind"),
    # likes
    ("keep", "i love {thing}"), ("keep", "i'm really into {thing}"), ("keep", "i'm a huge fan of {thing}"), ("keep", "{thing} is my whole thing"),
    ("keep", "i'm obsessed with {thing}"), ("keep", "i've always loved {thing}"), ("keep", "i collect {thing}"), ("keep", "{thing} is how i unwind"),
    ("keep", "my favorite {favkind} is {fav}"), ("keep", "{fav} is my favorite {favkind}"), ("keep", "my go-to {favkind} is {fav}"),
    ("keep", "my all-time favorite {favkind} is {fav}"), ("keep", "i can't stand {yuck}"), ("keep", "i hate {yuck}"), ("keep", "i'm terrified of {yuck}"),
    ("keep", "not a fan of {yuck}, never have been"), ("keep", "i've never liked {yuck}"), ("keep", "{yuck} freaks me out"), ("keep", "i'm scared of {yuck}"),
    ("keep", "i'm a night owl"), ("keep", "i'm a morning person"), ("keep", "i'm a homebody"), ("keep", "i'm a dog person"), ("keep", "i'm not much of a drinker"),
    ("keep", "my {rel} loves {thing}"), ("keep", "my {rel} is obsessed with {thing}"), ("keep", "my {rel} can't stand {yuck}"),
    # work, school
    ("keep", "i'm {job}"), ("keep", "i work as {job}"), ("keep", "i work at {company}"), ("keep", "i've been {job} for {years}"), ("keep", "my {rel} is {job}"),
    ("keep", "my {rel} works at {company}"), ("keep", "i just started at {company}"), ("keep", "i work nights"), ("keep", "i work the night shift"),
    ("keep", "i work from home"), ("keep", "i work weekends"), ("keep", "i'm between jobs"), ("keep", "i'm retired"), ("keep", "i run my own business"),
    ("keep", "i go to {school}"), ("keep", "i'm studying {subject}"), ("keep", "i'm in my last year of {school}"), ("keep", "i'm majoring in {subject}"),
    ("keep", "i teach {subject}"), ("keep", "i speak {language}"), ("keep", "i'm learning {language}"), ("keep", "my first language is {language}"),
    ("keep", "we speak {language} at home"), ("keep", "i take {line} to work"), ("keep", "my commute is {line}"),
    # animals, things
    ("keep", "i have a {pet} named {petname}"), ("keep", "my {pet}'s name is {petname}"), ("keep", "{petname} is my {pet}"),
    ("keep", "we adopted a {pet}, {petname}"), ("keep", "i've got a {pet} called {petname}"), ("keep", "{petname}, my {pet}, is {age}"),
    ("keep", "i drive {car}"), ("keep", "my car is {car}"), ("keep", "i don't have a car"), ("keep", "i don't drive"), ("keep", "i ride my bike everywhere"),
    # every week, and what they're working toward
    ("keep", "i have {activity} every {weekday}"), ("keep", "{activity} is on {weekday}s"), ("keep", "i go to {activity} {weekday} nights"),
    ("keep", "{weekday}s are my {activity} days"), ("keep", "i'm saving up for {goal}"), ("keep", "i'm training for {event}"),
    ("keep", "i want to {dream} someday"), ("keep", "my dream is to {dream}"), ("keep", "i've always wanted to {dream}"), ("keep", "i'm studying for {event}"),
    ("keep", "i volunteer at the shelter on {weekday}s"), ("keep", "i coach my {rel}'s team"), ("keep", "i play in a band"), ("keep", "i sing in a choir"),

    # only today: how they are, where they are, what just happened
    ("today", "i'm {mood}"), ("today", "i'm so {mood}"), ("today", "i'm kind of {mood}"), ("today", "i'm at {nowplace}"), ("today", "i'm stuck at {nowplace}"),
    ("today", "i'm leaving {nowplace}"), ("today", "i just got to {nowplace}"), ("today", "i just got home"), ("today", "i'm home"), ("today", "i'm in bed"),
    ("today", "i'm running late"), ("today", "i'm running behind"), ("today", "i'm stuck in traffic"), ("today", "i'm in a meeting"), ("today", "i'm on break"),
    ("today", "my phone is at {pct} percent"), ("today", "my phone died"), ("today", "my {body} hurt"), ("today", "my {body} are killing me"),
    ("today", "i have a headache"), ("today", "i have a cold"), ("today", "i'm sick"), ("today", "i'm getting over a cold"), ("today", "my allergies are acting up"),
    ("today", "my asthma is bad this week"), ("today", "my back is sore from the gym"), ("today", "i slept badly"), ("today", "i barely slept"),
    ("today", "i overslept"), ("today", "i'm heading to bed"), ("today", "i'm making {meal}"), ("today", "i had {meal} for lunch"), ("today", "i'm having {meal}"),
    ("today", "i'm craving {meal}"), ("today", "i want {meal}"), ("today", "i ate too much"), ("today", "i skipped breakfast"), ("today", "i need coffee"),
    ("today", "i'm watching {show}"), ("today", "i'm listening to a podcast"), ("today", "i love this song"), ("today", "i love that for you"),
    ("today", "i hate when that happens"), ("today", "i hate this weather"), ("today", "i'm into it"), ("today", "i'm obsessed with this episode"),
    ("today", "we're out of milk"), ("today", "we lost the game"), ("today", "my train is delayed"), ("today", "my bus is late"), ("today", "my flight got pushed"),
    ("today", "my boss is in a mood"), ("today", "my {rel} called"), ("today", "my {rel} is coming over"), ("today", "my {rel} is being annoying"),
    ("today", "my {rel} is mad at me"), ("today", "my {rel} just texted"), ("today", "my {rel} is in town"), ("today", "my {rel} is visiting"),
    ("today", "my {rel} thinks i'm overreacting"), ("today", "i told my {rel} i'd call back"), ("today", "i'm with my {rel}"), ("today", "i miss my {rel}"),
    ("today", "i can't find my {obj}"), ("today", "i lost my {obj}"), ("today", "i forgot my {obj}"), ("today", "i forgot my lunch"),
    ("today", "i'm behind on {chore}"), ("today", "i'm doing {chore}"), ("today", "i finished {chore}"), ("today", "i have so much to do"),
    ("today", "i have {chore} to do"), ("today", "i'm done for the day"), ("today", "i'm off work"), ("today", "i'm working late"), ("today", "i work at {time}"),
    ("today", "i have work in an hour"), ("today", "i have class at {time}"), ("today", "my shift ends at {time}"), ("today", "i have a meeting at {time}"),
    ("today", "i'm waiting on a package"), ("today", "my order hasn't shipped"), ("today", "i'm trying a new recipe"), ("today", "i'm cleaning my room"),
    ("today", "i got a parking ticket"), ("today", "i spilled coffee on my shirt"), ("today", "i missed my stop"), ("today", "i locked myself out"),
    ("today", "i'm nervous about it"), ("today", "i'm excited for it"), ("today", "i'm over it"), ("today", "i'm fine"), ("today", "i'm good"),
    ("today", "i'm a mess"), ("today", "i'm an idiot"), ("today", "i'm the worst"), ("today", "i'm a genius lol"), ("today", "i'm dead"), ("today", "i'm crying"),
    ("today", "my day was fine"), ("today", "my day was long"), ("today", "work was a lot"), ("today", "my wifi is being slow"), ("today", "my laptop is frozen"),
    ("today", "my {rel} is {mood}"), ("today", "my {pet} is being weird"), ("today", "my {pet} threw up"), ("today", "my {pet} woke me up"),
    ("today", "i'm thinking about it"), ("today", "i'm not sure"), ("today", "i don't know"), ("today", "i guess so"), ("today", "i think so"),
    ("today", "i need a nap"), ("today", "i need a vacation"), ("today", "i need to get out of the house"), ("today", "i want to go home"),
    ("today", "my hands are freezing"), ("today", "it's so hot in my apartment"), ("today", "my neighbors are loud"), ("today", "my room is a mess"),
    ("today", "i'm in the car"), ("today", "i'm on the train"), ("today", "i'm walking home"), ("today", "i'm out with friends"), ("today", "i'm at my {rel}'s"),
    ("today", "i have a date"), ("today", "i have plans"), ("today", "i have no plans"), ("today", "i have the day off"), ("today", "i'm off"),
    # the same openings as a lasting fact, about now
    ("today", "my {rel} is {state}"), ("today", "my {rel}'s {state}"), ("today", "my {rel} has a cold"), ("today", "my {rel} got a haircut"),
    ("today", "my {rel} wants {meal}"), ("today", "my {rel} is making {meal}"), ("today", "my {rel} hates me"), ("today", "my {rel} is driving me up the wall"),
    ("today", "my {rel} needs a ride"), ("today", "my {rel} is picking me up"), ("today", "my {rel} said hi"), ("today", "my {rel} says i snore"),
    ("today", "my {pet} is at the vet"), ("today", "my {pet} is hiding"), ("today", "my {pet} is on my lap"), ("today", "my {pet} wants out"),
    ("today", "my car is in the shop"), ("today", "my car is making a noise"), ("today", "my apartment is freezing"), ("today", "my job is killing me"),
    ("today", "my birthday was fun"), ("today", "my birthday dinner got cancelled"), ("today", "my favorite part was the ending"),
    ("today", "i have an idea"), ("today", "i have a question"), ("today", "i have no idea"), ("today", "i have time"), ("today", "i have to go"),
    ("today", "i have to work"), ("today", "i've got a minute"), ("today", "i have {count} meetings"), ("today", "i've got {count} emails to answer"),
    ("today", "i have {count} minutes"), ("today", "i'm {pct} minutes away"), ("today", "i'm {pct} minutes late"), ("today", "i'm {count} for {count}"),
    ("today", "i'm early"), ("today", "i'm next"), ("today", "i'm busy"), ("today", "i'm free"), ("today", "i'm serious"), ("today", "i'm kidding"),
    ("today", "i'm sorry"), ("today", "i'm sure"), ("today", "i'm lost"), ("today", "i'm confused"), ("today", "i'm in"), ("today", "i'm out"), ("today", "i'm down"),
    ("today", "i'm a little {mood}"), ("today", "i'm a bit late"), ("today", "i'm from the future lol"), ("today", "i'm working"), ("today", "i'm at work"),
    ("today", "i love you"), ("today", "i love your energy"), ("today", "i love when things work out"), ("today", "i hate everything"), ("today", "i hate mornings like these"),
    ("today", "i live for the weekend"), ("today", "i live for drama"), ("today", "i don't care"), ("today", "i don't want to"), ("today", "i don't feel like cooking"),
    ("today", "i don't get the joke"), ("today", "i don't have time"), ("today", "i don't know what to eat"), ("today", "i can't sleep"), ("today", "i can't even"),
    ("today", "i can't wait"), ("today", "i can't believe they did me like this"), ("today", "i can't decide"), ("today", "i'm saving you a seat"),
    ("today", "i'm studying"), ("today", "i'm learning a lot"), ("today", "i'm training my replacement"), ("today", "i work in the morning"),
    ("today", "we're leaving"), ("today", "we got food"), ("today", "we're watching {show}"), ("today", "we had {meal}"), ("today", "we're good"),
    ("today", "i drive myself crazy"), ("today", "i speak for everyone when i say no"), ("today", "i take what i can get"), ("today", "i go to bed late"),
    # something that happened, with the words a lasting fact would have
    ("today", "i burned the {meal}"), ("today", "i was {doing} until midnight"), ("today", "i saw {name} at the store"), ("today", "i ran into {name}"),
    ("today", "i watched {fav} with my {rel}"), ("today", "i ate {allergen} at the party"), ("today", "i went to {city} for the day"),
    ("today", "we drove through {city}"), ("today", "i tried {thing} once"), ("today", "i talked to {name}"), ("today", "i heard {name} got promoted"),
    ("today", "i took my {pet} to the park"), ("today", "i walked {petname} twice"), ("today", "i fed {petname}"), ("today", "i dropped my {rel} off"),
    ("today", "i made {meal} for my {rel}"), ("today", "i bought my {rel} a gift"), ("today", "i met my {rel}'s new boyfriend"), ("today", "we watched {fav}"),
    ("today", "i spent all afternoon {doing}"), ("today", "i got {meal} from the place downstairs"), ("today", "i read about {condition}"),
    ("today", "i called {company} about the bill"), ("today", "i drove past {company}"), ("today", "my {rel} went to {city}"), ("today", "my {rel} made {meal}"),
    ("today", "my {rel} watched {fav} without me"), ("today", "my {rel} took the {pet} out"), ("today", "{name} came by"), ("today", "{name} says hi"),
    ("today", "my {rel} just had a baby"), ("today", "my {rel} just got a puppy"), ("today", "my {rel} just got back"), ("today", "my {rel} just quit"),
    ("today", "my {rel} had her baby"), ("today", "my {rel} got the job"), ("today", "my {rel} has a new girlfriend"), ("today", "my {rel} has news"),
    ("today", "idk if i should {dream}"), ("today", "i'm thinking of going {diet}"), ("today", "maybe i'll learn {language}"), ("today", "i might go to {school}"),
    ("today", "i have {fav} on in the background"), ("today", "i have {fav} stuck in my head"), ("today", "i've got {fav} on repeat"),
    ("today", "i'm debating a {pet}"), ("today", "i kind of want to {dream}"), ("today", "i'm not sure about {school}"),
    ("today", "i've been {doing} a lot"), ("today", "i've been sleeping a lot"), ("today", "i've been thinking a lot"), ("today", "i've been cleaning out my room"),
    ("today", "i've been sorting through old photos"), ("today", "i've been avoiding my {rel}"), ("today", "i've been eating badly"),
    ("today", "i've been watching too much tv"), ("today", "we've been arguing"), ("today", "i've been meaning to call my {rel}"),
    ("today", "i gave my old {obj} to my {rel}"), ("today", "i wrote a card for my {rel}"), ("today", "i sold my old {obj}"), ("today", "i donated a bunch of clothes"),
    ("today", "i've given most of my {thing} away"), ("today", "i've stopped answering my phone"), ("today", "i've decided to stay in"),
    ("today", "i sent my {rel} a long text"), ("today", "i said thanks to my {rel}"), ("today", "i wrote thank-you notes to everyone"),
    ("today", "i was born ready"), ("today", "i'm allergic to mondays lol"), ("today", "i'm obsessed"), ("today", "i'm a fan"), ("today", "i'm single-handedly carrying the team"),
]

_model, _lock = None, threading.Lock()


def learned(said):
    """What the small model makes of this: {label: how sure}, or {} when the model isn't here."""
    global _model
    with _lock:
        if _model is None:
            try:
                from . import understanding
                _model = understanding.Model(LEARNED) if LEARNED.exists() else False
            except Exception:
                _model = False   # no numpy, or a damaged file: the rules still work
    if not _model:
        return {}
    return dict(_model.predict(" ".join(str(said or "").split()), len(_model.intents)))


def has_shape(said):
    """Someone plainly stating a thing about themselves: not a question, not a request, nothing that's only about today,
    nothing secret, and not a hard moment. The model is only believed when the sentence looks like this."""
    said = " ".join(str(said or "").split())
    words = said.split()
    if not 3 <= len(words) <= 16 or len(said) > 120:
        return False
    if not ABOUT_THEM.search(said) or ASKING.search(said) or ONLY_TODAY.search(said) or SECRET.search(said) or JOKING.search(said) or happened(said) or NEWS.search(said) or HEDGED.search(said) or LATELY.search(said):
        return False
    if NEGATED.search(said) and not LASTING_NO.search(said):
        return False
    if DESPAIR.search(said):
        return False
    try:
        from . import feelings, friendcheck, rapport
        if friendcheck.at_risk(said) or rapport.hard(feelings.read(said)) or feelings.dry(said):
            return False   # they may not be safe, a hard moment, or a gripe said with good words: for the moment, not for the deck
        from .runtime import CRISIS
        if CRISIS.search(said.lower()):
            return False
    except Exception:
        return False
    return True


def heavy(said):
    """Is this a line from someone who is hurting or may not be safe? (Asked of what they said in the last few turns.)"""
    said = " ".join(str(said or "").split())
    if not said:
        return False
    if DESPAIR.search(said) or QUIET_SIGN.search(said) or (NEGATED.search(said) and not LASTING_NO.search(said)):
        return True   # read widely on purpose: being wrong here only costs a card, and the rules still make theirs
    try:
        from . import feelings, friendcheck, rapport
        felt = feelings.read(said)
        if friendcheck.at_risk(said) or rapport.hard(felt) or (felt and felt.get("family") not in ("joy", "proud", "relieved")):
            return True
        from .runtime import CRISIS
        return bool(CRISIS.search(said.lower()))
    except Exception:
        return True   # can't tell: then no card


def by_model(said):
    """The model alone, with its shape: used where the rules found nothing."""
    if not has_shape(said):
        return False
    guess = learned(LEAD.sub("", said) or said)
    return bool(guess) and guess.get("keep", 0.0) >= SURE and max(guess, key=guess.get) == "keep"


def card(text, recent=()):
    """The card for a lasting fact the rules didn't read, in their own words; or None. recent: what they said in the few
    turns before this one. While any of it is heavy, nothing is made a card by the model: what someone says next to
    "I can't see the point" may be a quiet sign of something else ("I've been putting my closet in order"), and a deck
    of facts is no place for it."""
    from . import presence
    if any(heavy(line) for line in recent):
        return None
    text = presence.strip_wake(str(text or ""))
    for clause in presence.clauses(text):
        clause = (LEAD.sub("", clause) or clause).strip(" ,.!")
        if by_model(clause):
            return clause[:1].upper() + clause[1:]
    return None


def cards(text, recent=(), model=True, names=()):
    """Every card one thing they said becomes, the way a turn makes them (Agent._notice): the rules first, then the model
    where the rules found nothing (never in kids mode: model=False)."""
    from . import people, presence
    found = presence.notice_facts(text) + people.facts(text)
    turned = _turned(text, found, names)   # a name or a home said another way round: the plain sentence, so it's a fact Luma can answer from
    if turned:   # "home for my mom is Tampa" also read as "My mom is Tampa": the turned sentence says what was meant
        ends = tuple(" is " + plain.rsplit(" ", 1)[-1].lower() for plain in turned)
        found = [fact for fact in found if not (len(fact.split()) <= 5 and fact.lower().endswith(ends))]
    if found or turned or not model:
        return found + turned
    extra = card(text, recent)
    return [extra] if extra else []


def _turned(text, found, names=()):
    """people.plainly()'s sentences, less any the rules already read from this message."""
    from . import people
    try:
        from ..memory import facts
        read = [slot for fact in list(found) + [text] for slot in (getattr(facts.read(fact), "slots", None) or [])]
        have = {(who, kind) for who, kind, _ in read} | {(kind, str(value).lower()) for _, kind, value in read}
        out = []
        for plain in people.plainly(text, names):
            slots = getattr(facts.read(plain), "slots", None) or []
            # not when the rules already read the same thing, from a card or from the line itself ("my brother Marcus lives
            # in Austin" is one fact, however many ways it can be put)
            if slots and not any((who, kind) in have or (kind, str(value).lower()) in have for who, kind, value in slots):
                out.append(plain)
        return out
    except Exception:
        return []
