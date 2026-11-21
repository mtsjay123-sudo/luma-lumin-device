"""A hard moment said in words no rule knows: "another saturday by myself", "they all went to the party without me".

The hand-written rules (luma.agent.feelings) read every hard line they were built on and two in three of the lines
nobody fitted them to (tests/hard_or_not.py, the held-out half: 100 of 150), and they never take an ordinary line for
a hard one. So a small model on the device listens as well. It adds a little, not a lot: 100 -> 108 of 150 on that
held-out half (all eight are a worry), and nothing on forty lines written to be said sideways (2 of 40 before and after:
tests/test_feels.py). A
bag of words hears the words, not what happened; what's said sideways is still the brain's to read
(Agent._went_wrong_for_them). It only adds: the rules are asked first, and the model
is believed only where they read nothing, only when it's sure (SURE), and only when the message has the plain shape
of someone telling Luma about themselves (it's a statement, they're in it, it isn't a request).

- by_model(said):  the feeling the model is sure of and is believed about ("lonely" or "fear"), or ""
- learned(said):   what the model alone makes of it: {label: how sure}

The model (feels.npz) is taught by scripts/train_feels.py from the practice sentences in this file and the dev halves
of the hand-written sets. It never sees a held-out line. With no numpy or no model file, the rules still work alone.

It is never asked about a line the safety readers read (friendcheck.at_risk, worth_asking) or one that leans on Luma
(friendcheck.leaning), and no practice sentence is a safety line: what such a line is owed is the safety question or
the leaning care, and the model has no say in either.

What it changes: which note the brain is given ("be fully here with them first" instead of "a little humor is
welcome"). It never touches the crisis net, which has read the message before any of this.
"""
from __future__ import annotations

import re
import threading
from pathlib import Path

LEARNED = Path(__file__).with_name("feels.npz")
LABELS = ["lonely", "hurt", "disappointed", "low", "overwhelmed", "fear", "none"]
# Which feelings the model is believed about, and how sure it must be. On practice shapes it didn't learn from
# (scripts/train_feels.py --check) it's only worth believing about two: at 0.7 it heard 6 of 64 lonely lines and 15 of 102
# worried ones and gave no ordinary line either name, while "hurt" took 10 ordinary lines and "disappointed" 13 ("i've been
# waiting two weeks for this package and it finally came"). So those two, at 0.7. The other four are learned so the model
# has somewhere else to put a hard line, and are never believed.
SURE = {"lonely": 0.7, "fear": 0.7}

ME = re.compile(r"\b(?:i|i'?m|im|i'?ve|ive|i'?d|i'?ll|me|my|mine|myself|we|we'?re|we'?ve|our|us)\b", re.I)
ASKING = re.compile(r"\?\s*$|^\W*(?:(?:hey|ok|okay|so|luma|um|and|oh)\W+)*(?:what|what'?s|when|where|who|how|why|which|can|could|would|will|do|does|did|is|"
                    r"are|should|any|tell me|show me|remind|add|set|play|call|text|turn|stop|start|put|open|find|search|look up|read|send|"
                    r"wake|cancel|pause|skip|what time)\b", re.I)

# Lonely has a plain shape of its own, the way leaning does (hears.SHUTS_OUT): somebody is missing from the sentence.
# "like i wasn't even the one who messed up the order" has the model's words and nobody missing, so it isn't believed.
ABSENT = re.compile(r"\b(?:alone|by myself|on my own|myself|just me|only me|nobody|nobody'?s|no one|no one'?s|no-one|noone|without me|invited|anyone|"
                    r"anybody|a soul|a single person|empty|quiet|silent|silence|their own (?:lives|plans|friends|things?|group)|left out|left over)\b", re.I)

SLOTS = {
    "who": ["my sister", "my brother", "my mom", "my dad", "my best friend", "my roommate", "my boyfriend", "my girlfriend", "my husband", "my wife",
            "my cousin", "my boss", "my daughter", "my son", "my neighbor", "my ex", "my aunt", "my uncle", "my grandma", "my oldest friend"],
    "they": ["everyone", "everybody", "they", "my friends", "the whole crew", "my coworkers", "the group", "my family", "my classmates", "the girls",
             "the guys", "all of them", "the whole office", "my teammates", "the people next door", "my cousins"],
    "event": ["the party", "the trip", "dinner", "the barbecue", "game night", "the concert", "brunch", "the cookout", "the reunion", "movie night",
              "the birthday thing", "the lake weekend", "the baby shower", "happy hour", "the camping trip", "the beach day"],
    "day": ["friday", "saturday", "my birthday", "christmas", "thanksgiving", "the weekend", "new year's", "valentine's day", "sunday", "easter",
            "the holidays", "my day off", "the fourth of july", "halloween"],
    "span": ["weeks", "months", "three days", "a week", "two weeks", "a month", "days", "ages", "four days", "a long time", "a year", "forever",
             "six months", "ten days"],
    "place": ["this apartment complex", "the warehouse", "my new school", "the firm", "this suburb", "the plant", "my department", "the academy", "the restaurant", "night school", "the call center", "the site"],
    "thing": ["my application", "the proposal", "the grant", "my thesis defense", "the big meeting", "the showcase", "my review", "the screening", "the callback", "the assessment", "the hearing", "my licensing board"],
    "work": ["portfolio", "essay", "demo", "design", "script", "sample", "resume", "audition tape", "manuscript", "short film", "proposal", "painting"],
    "contest": ["election", "final", "match", "bid", "championship", "spelling bee", "case", "vote", "tournament", "playoff game", "debate", "race"],
    "show": ["recital", "game", "play", "art show", "concert", "award thing", "retirement party", "first match", "book reading", "open mic",
             "science fair", "housewarming"],
    "sib": ["sister", "brother", "cousin", "older sister", "little brother", "twin"],
    "task": ["laundry", "the dishes", "my email", "the bills", "homework", "my room", "the mail", "groceries", "the trash", "my taxes", "the vacuuming",
             "my inbox"],
    "hobby": ["painting", "running", "cooking", "guitar", "gardening", "reading", "baking", "fishing", "knitting", "drawing", "piano", "hiking"],
    "bill": ["the mortgage", "my student loans", "the water bill", "the gas bill", "childcare", "the hospital bill", "my car note", "the credit cards", "property tax", "the internet bill", "the dentist bill", "back rent"],
    "n": ["two", "three", "four", "five", "six", "ten", "eight", "twelve"],
    "when": ["monday", "next week", "tuesday", "tomorrow", "friday", "on the 14th", "in two days", "thursday morning", "next month", "this week"],
    "pet": ["the dog", "the cat", "my cat", "my dog", "the puppy", "the kitten"],
    "city": ["denver", "chicago", "austin", "seattle", "boston", "miami", "portland", "atlanta", "phoenix", "nashville", "tokyo", "osaka"],
    "food": ["lasagna", "pho", "burritos", "meatloaf", "bibimbap", "grilled cheese", "pad thai", "gumbo", "omelets", "nachos"],
    "lead": ["honestly", "ngl", "tbh", "idk", "man", "so", "anyway", "well", "i mean", "not gonna lie", "look", "welp"],
}

FRAMES = [
    # ---- lonely: nobody there, said as what happened ----
    ("lonely", "haven't left the apartment in {span}"),
    ("lonely", "it's {day} night and my phone hasn't made a sound"),
    ("lonely", "{they} went to {event} without me"),
    ("lonely", "nobody asked if i wanted to come to {event}"),
    ("lonely", "i wasn't invited to {event}"),
    ("lonely", "another {day} by myself"),
    ("lonely", "{lead} spending {day} on my own again"),
    ("lonely", "i haven't had a real conversation in {span}"),
    ("lonely", "the only person i talked to today was the delivery guy"),
    ("lonely", "the only messages i get are from my phone company"),
    ("lonely", "{span} at {place} and i still take my breaks in my car"),
    ("lonely", "no one noticed i wasn't at {event}"),
    ("lonely", "i go {span} without anyone saying my name"),
    ("lonely", "i don't have anybody to put down as an emergency contact"),
    ("lonely", "there's no one i could call if my car broke down"),
    ("lonely", "i got good news today and had no one to tell"),
    ("lonely", "it's just me in this house now"),
    ("lonely", "it's so still in here since {who} moved out"),
    ("lonely", "{who} moved away and now there's nobody around"),
    ("lonely", "i went to the movies by myself again"),
    ("lonely", "i went to {event} and didn't talk to a single person"),
    ("lonely", "i stood by the wall at {event} the whole time and nobody came over"),
    ("lonely", "{they} have their own lives now and i'm not in them"),
    ("lonely", "{they} are always busy when i ask to hang out"),
    ("lonely", "i'm always the one who texts first. if i stopped it would just go silent"),
    ("lonely", "i haven't hugged anyone in {span}"),
    ("lonely", "i talk to {pet} more than i talk to people"),
    ("lonely", "my voice cracked ordering coffee because i hadn't used it in {span}"),
    ("lonely", "i scroll through my contacts and there's nobody i can actually call"),
    ("lonely", "the weekends are the worst, nothing but me and the walls"),
    ("lonely", "{who} is the only person i talk to and they're moving"),
    ("lonely", "i sit by myself at {place} every day"),
    ("lonely", "nobody saved me a seat"),
    ("lonely", "nobody picked me for their group again"),
    ("lonely", "i watched everybody pair up and i was the one left over"),
    ("lonely", "everyone has somebody to go home to"),
    ("lonely", "i came home to an empty house again"),
    ("lonely", "my evenings are just me waiting until it's late enough to go to bed"),
    ("lonely", "no plans for {day}. no plans ever, really"),
    ("lonely", "{lead} i wish somebody would just ask how my day was"),
    ("lonely", "nobody's asked me how i'm doing in {span}"),
    ("lonely", "i could go a whole weekend without speaking out loud"),
    ("lonely", "{they} stopped asking me to come along"),
    ("lonely", "i heard them all laughing next door and stayed in my room"),
    ("lonely", "i walked around the mall just to be near people"),
    ("lonely", "i reread old messages because nobody sends new ones"),
    ("lonely", "{day} came and went and nobody remembered me"),
    ("lonely", "i set out two cups this morning before i remembered"),
    # ---- hurt: someone did something to them ----
    ("hurt", "{who} forgot my birthday"),
    ("hurt", "{who} didn't even say happy birthday"),
    ("hurt", "{who} cancelled on me again, last minute"),
    ("hurt", "{who} stood me up"),
    ("hurt", "{who} has been talking about me behind my back"),
    ("hurt", "{who} said i was too much"),
    ("hurt", "{who} called me dead weight"),
    ("hurt", "{who} said i'm the problem"),
    ("hurt", "{who} told me i'd never amount to anything"),
    ("hurt", "{who} laughed at me in front of {they}"),
    ("hurt", "{who} made a joke about my weight in front of {they}"),
    ("hurt", "{who} ignored me the whole night"),
    ("hurt", "{who} walked right past me like i wasn't there"),
    ("hurt", "{who} hasn't spoken to me in {span}"),
    ("hurt", "{who} stopped picking up when i call"),
    ("hurt", "{who} blocked me"),
    ("hurt", "{who} unfollowed me out of nowhere"),
    ("hurt", "{who} chose {event} over me"),
    ("hurt", "{who} picked them over me"),
    ("hurt", "{who} took their side"),
    ("hurt", "{who} didn't stand up for me"),
    ("hurt", "{who} lied to my face"),
    ("hurt", "{who} went through my phone"),
    ("hurt", "{who} uninvited me from {event}"),
    ("hurt", "{who} never asks about my life"),
    ("hurt", "{who} only calls when they need something"),
    ("hurt", "{who} forgot to pick me up"),
    ("hurt", "{who} said they wished i was more like my {sib}"),
    ("hurt", "{who} compared me to my {sib} again"),
    ("hurt", "{who} yelled at me in front of {they}"),
    ("hurt", "{who} read my diary"),
    ("hurt", "{they} were making fun of me and i heard all of it"),
    ("hurt", "{they} made a group chat without me"),
    ("hurt", "{they} all knew and nobody told me"),
    ("hurt", "i overheard {who} say they only invited me out of pity"),
    ("hurt", "{who} said they don't have time for me anymore"),
    ("hurt", "{who} told me to stop being so sensitive"),
    ("hurt", "{who} didn't thank me, didn't even look up"),
    ("hurt", "i drove {n} hours to see {who} and they left after ten minutes"),
    ("hurt", "{who} gave my spot to someone else"),
    ("hurt", "{who} said my cooking was embarrassing in front of {they}"),
    ("hurt", "{who} told me i wasn't welcome at {event}"),
    ("hurt", "{who} called me selfish for asking for one thing"),
    ("hurt", "{who} threw out the present i made"),
    ("hurt", "{lead} {who} said she's ashamed of me"),
    ("hurt", "{who} said he never wanted kids, right to my face"),
    ("hurt", "{who} hung up on me mid sentence"),
    # ---- disappointed: it didn't happen, said as what happened ----
    ("disappointed", "i didn't make it past the first round of {thing}"),
    ("disappointed", "i worked on my {work} for {span} and they passed"),
    ("disappointed", "they went with another candidate"),
    ("disappointed", "they gave it to someone with more experience"),
    ("disappointed", "{thing} went badly. really badly"),
    ("disappointed", "i froze in {thing} and couldn't get a word out"),
    ("disappointed", "i prepared for {span} and still came up short"),
    ("disappointed", "they said my {work} wasn't what they were looking for"),
    ("disappointed", "my {work} got sent back with a form letter"),
    ("disappointed", "waitlisted again"),
    ("disappointed", "i came in last"),
    ("disappointed", "i lost the {contest}"),
    ("disappointed", "we lost the {contest} by one point"),
    ("disappointed", "the offer got pulled at the last minute"),
    ("disappointed", "the deal collapsed the day before signing"),
    ("disappointed", "the house we wanted went to another buyer"),
    ("disappointed", "my flight got cancelled and i'm going to miss {event}"),
    ("disappointed", "the trip's off. {who} bailed"),
    ("disappointed", "the test was negative again. we've been trying for {span}"),
    ("disappointed", "another month, another no"),
    ("disappointed", "i was so sure this time and it still didn't happen"),
    ("disappointed", "i was one class short of graduating"),
    ("disappointed", "they cut my hours right after promising me full time"),
    ("disappointed", "the raise i was promised isn't happening"),
    ("disappointed", "they never called back after the third interview"),
    ("disappointed", "the scholarship went to somebody else"),
    ("disappointed", "my visa got pushed back another {span}"),
    ("disappointed", "i saved for {span} and the car died anyway"),
    ("disappointed", "the surprise i planned for {who} fell flat"),
    ("disappointed", "nobody came to my {show}"),
    ("disappointed", "i set up for {n} hours and {n} people showed"),
    ("disappointed", "i thought i'd finally done it and then the email came"),
    ("disappointed", "they picked the other team's {work}"),
    ("disappointed", "my name wasn't on the list"),
    ("disappointed", "didn't place. didn't even make the top ten"),
    ("disappointed", "{lead} all that work on {thing} for nothing"),
    ("disappointed", "i got the email. it's a no"),
    ("disappointed", "they told me to try again next year"),
    # ---- low: worn down, flat, crying, can't get going ----
    ("low", "i haven't showered in {span}"),
    ("low", "i haven't opened my mail in {span}"),
    ("low", "i can't make myself do {task}"),
    ("low", "i slept until 3 again and still feel like nothing"),
    ("low", "i stayed in bed all {day}. couldn't do it"),
    ("low", "nothing sounds good. not food, not shows, nothing"),
    ("low", "i used to love {hobby} and now i can't be bothered"),
    ("low", "i haven't done any {hobby} in {span}. don't even miss it"),
    ("low", "everything's been gray lately"),
    ("low", "i'm just going through the motions"),
    ("low", "i've been crying in the shower so nobody hears"),
    ("low", "i cried on the bus home and i don't even know why"),
    ("low", "i burst into tears at the grocery store over nothing"),
    ("low", "i keep tearing up at my desk"),
    ("low", "i can't stop crying today"),
    ("low", "woke up with that heavy thing sitting on me again"),
    ("low", "it took everything i had just to brush my teeth"),
    ("low", "getting dressed today was like climbing a mountain"),
    ("low", "i've been eating cereal for dinner for {span} because i can't be bothered"),
    ("low", "i cancelled on {who} again because i couldn't face it"),
    ("low", "i haven't answered anybody's texts in {span}. i just can't"),
    ("low", "i keep saying i'm fine so nobody asks"),
    ("low", "i smiled all day at work and came home and fell apart"),
    ("low", "some days i just sit in the dark"),
    ("low", "i don't recognize myself lately"),
    ("low", "i'm tired in a way sleep doesn't fix"),
    ("low", "{lead} it's been a rough {span} and it's not letting up"),
    ("low", "today knocked the wind out of me"),
    ("low", "this week broke me a little"),
    ("low", "i have nothing left by the time i get home"),
    ("low", "i can't seem to get it together"),
    ("low", "i put on a show and realized an hour later i hadn't watched any of it"),
    ("low", "i don't look forward to anything anymore, not even {day}"),
    ("low", "even {hobby} doesn't do anything for me now"),
    # ---- overwhelmed: too much at once, money, no rest ----
    ("overwhelmed", "i'm working doubles all week and {task} is piling up"),
    ("overwhelmed", "between work and school and the baby i don't get {n} minutes to myself"),
    ("overwhelmed", "i'm taking care of {who} full time and working nights"),
    ("overwhelmed", "i picked up a second job and i still can't cover {bill}"),
    ("overwhelmed", "{bill} is {n} months behind"),
    ("overwhelmed", "i got a shutoff notice in the mail today"),
    ("overwhelmed", "the collectors keep calling about {bill}"),
    ("overwhelmed", "my card got declined buying groceries"),
    ("overwhelmed", "i've got {n} dollars until payday"),
    ("overwhelmed", "i don't know how i'm going to pay for {bill} this month"),
    ("overwhelmed", "my boss dumped {n} more projects on me"),
    ("overwhelmed", "i haven't had a day off in {span}"),
    ("overwhelmed", "i've slept maybe {n} hours a night all week"),
    ("overwhelmed", "the baby's been up every hour and i have to be at work at six"),
    ("overwhelmed", "my to-do list has {n} things on it and i can't start one"),
    ("overwhelmed", "every time i fix one thing something else breaks"),
    ("overwhelmed", "the car died, the sink's leaking and now {bill} is due"),
    ("overwhelmed", "i'm so behind i don't even know where to begin"),
    ("overwhelmed", "i can't catch a break this month"),
    ("overwhelmed", "i'm running on coffee and panic"),
    ("overwhelmed", "i've got finals, a move and a sick parent all in the same week"),
    ("overwhelmed", "it's one thing after another and i'm out of gas"),
    ("overwhelmed", "there aren't enough of me to go around"),
    ("overwhelmed", "everyone needs something from me and i've got nothing left"),
    ("overwhelmed", "{lead} i haven't sat down since six this morning"),
    ("overwhelmed", "i ate lunch standing up for the {n}th day in a row"),
    ("overwhelmed", "i'm the only one doing anything for {who} and nobody helps"),
    # ---- fear: something might be wrong, said as what's happening ----
    ("fear", "they found a lump and i have to wait until {when} to hear"),
    ("fear", "the biopsy results come back {when}"),
    ("fear", "my scan is {when} and i can't think about anything else"),
    ("fear", "{who} is in surgery right now"),
    ("fear", "{who} is in the er and nobody will tell me anything"),
    ("fear", "i have court {when} and i can't sleep"),
    ("fear", "my custody hearing is {when}"),
    ("fear", "the landlord says we have until the end of the month"),
    ("fear", "there was an eviction notice on the door when i got home"),
    ("fear", "immigration sent a letter and i don't understand it"),
    ("fear", "{who} has been forgetting things and the doctor said the word dementia"),
    ("fear", "{who} fell again and won't use the walker"),
    ("fear", "my kid's fever won't come down"),
    ("fear", "the vet said to prepare ourselves"),
    ("fear", "i start the new job {when} and i can't stop shaking"),
    ("fear", "i have to give a speech {when} and my stomach is in knots"),
    ("fear", "my hands won't stop shaking before {thing}"),
    ("fear", "someone tried my door handle last night and i keep checking the locks"),
    ("fear", "the storm's supposed to hit tonight and i'm here by myself"),
    ("fear", "my ex found out where i live"),
    ("fear", "the test said positive and i haven't told anyone"),
    ("fear", "i'm waiting on a call from the hospital"),
    ("fear", "my chest has been tight all day and i keep googling it"),
    ("fear", "i can't stop thinking something bad is going to happen to {who}"),
    ("fear", "{who} drove off angry in the snow and that was {n} hours ago"),
    ("fear", "{thing} is {when} and i keep throwing up"),

    # ---- none: the same words on an ordinary or a good day ----
    ("none", "finally got the place to myself {when}"),
    ("none", "home by myself and loving it"),
    ("none", "just me and {pet} tonight, perfect"),
    ("none", "i went to the movies by myself and it was great"),
    ("none", "solo trip to {city} next month, can't wait"),
    ("none", "i like taking my breaks in my car, it's the only quiet i get"),
    ("none", "quiet night in, exactly what i wanted"),
    ("none", "nobody's home so i'm blasting music"),
    ("none", "i turned my phone off for the weekend on purpose"),
    ("none", "haven't left the apartment all weekend, best weekend ever"),
    ("none", "{they} went to {event}, i stayed in to finish my book"),
    ("none", "skipping {event}, i'd rather sleep"),
    ("none", "no plans for {day} and i couldn't be happier"),
    ("none", "another {day} at the lake with {they}"),
    ("none", "{they} are coming over for {event}"),
    ("none", "{who} invited me to {event}"),
    ("none", "i'm going to {event} with {who}"),
    ("none", "{who} saved me a seat"),
    ("none", "{who} called just to say hi"),
    ("none", "had a great talk with {who} today"),
    ("none", "{who} remembered my birthday and brought cake"),
    ("none", "{who} surprised me at work"),
    ("none", "{who} texted me back right away"),
    ("none", "{who} stood up for me in the meeting"),
    ("none", "{who} said the nicest thing today"),
    ("none", "{who} is moving in next month"),
    ("none", "{who} moved out so i finally have an office"),
    ("none", "{who} forgot their keys again, classic"),
    ("none", "{who} cancelled so now i have a free evening"),
    ("none", "{who} told {they} about my promotion"),
    ("none", "{who} laughed at my joke for five minutes straight"),
    ("none", "{who} beat me at chess again"),
    ("none", "{who} took my side and we won the argument"),
    ("none", "{who} only calls when the game is on"),
    ("none", "{who} chose the restaurant this time"),
    ("none", "{who} hasn't seen the new place yet"),
    ("none", "{who} has been busy with the new baby"),
    ("none", "{who} left me the last slice"),
    ("none", "{who} went through my playlist and stole half of it"),
    ("none", "{who} came to my {show} with flowers"),
    ("none", "{who} picked me up from the airport"),
    ("none", "{who} made a group chat for {event}"),
    ("none", "{they} made fun of my hat and honestly fair"),
    ("none", "{they} all knew about the surprise and nobody told me, i love them"),
    ("none", "{who} blocked the driveway again"),
    ("none", "{who} hung up because the oven was beeping"),
    ("none", "{who} threw out the leftovers before i got any"),
    ("none", "{who} read my essay and liked it"),
    ("none", "i drove {n} hours to see {who} and it was worth it"),
    ("none", "{event} is on {day} this year"),
    ("none", "{event} got moved to {day}"),
    ("none", "it's {day} night, i'm picking a movie"),
    ("none", "my phone hasn't made a sound all day, i think the ringer's off"),
    ("none", "i haven't had coffee in {span} and i'm doing great"),
    ("none", "haven't showered yet, heading to the gym first"),
    ("none", "i slept until 3 because i worked the night shift"),
    ("none", "i stayed in bed all morning reading"),
    ("none", "i can't make myself like cilantro"),
    ("none", "{task} is done, finally"),
    ("none", "i need to do {task} tonight"),
    ("none", "i've been eating cereal for dinner because it's delicious"),
    ("none", "i used to love {hobby} and i'm getting back into it"),
    ("none", "picked {hobby} back up after {span}"),
    ("none", "i haven't done any {hobby} in {span}, starting again {when}"),
    ("none", "i cried laughing at {who}'s text"),
    ("none", "i cried at the end of that movie, so good"),
    ("none", "happy tears at the ceremony all day"),
    ("none", "got {n} deadlines this week but i'm on top of it"),
    ("none", "working doubles this week, the overtime is going to be nice"),
    ("none", "busy week but a good one"),
    ("none", "paid off {bill} today"),
    ("none", "{bill} went down this month"),
    ("none", "got a second job at the bookstore, i love it"),
    ("none", "my boss gave me {n} more projects and a raise"),
    ("none", "first day off in {span}, going hiking"),
    ("none", "the baby slept through the night"),
    ("none", "crossed {n} things off my list today"),
    ("none", "fixed the sink myself"),
    ("none", "the car's running fine again"),
    ("none", "i haven't sat down since six because the party prep is so fun"),
    ("none", "i made it past the first round of {thing}"),
    ("none", "they went with my {work}"),
    ("none", "{thing} went great"),
    ("none", "i nailed {thing}"),
    ("none", "i passed {thing}"),
    ("none", "got the callback"),
    ("none", "they called back after the interview, i start monday"),
    ("none", "my {work} got accepted"),
    ("none", "we won the {contest} by one point"),
    ("none", "the offer came through"),
    ("none", "the house is ours"),
    ("none", "my flight got moved up so i'll make {event}"),
    ("none", "my name was on the list"),
    ("none", "came in third, i'll take it"),
    ("none", "my visa came through"),
    ("none", "the results came back clear"),
    ("none", "the scan was fine"),
    ("none", "{who} is out of surgery and doing great"),
    ("none", "{who} is home from the hospital"),
    ("none", "court went my way"),
    ("none", "the landlord renewed our lease"),
    ("none", "i start the new job {when} and i'm excited"),
    ("none", "i have to give a speech {when}, i think it's ready"),
    ("none", "the storm missed us"),
    ("none", "the vet said she's healthy"),
    ("none", "my kid's fever broke"),
    ("none", "waiting on a call from the pizza place"),
    ("none", "the biopsy came back benign"),
    ("none", "they want to run the ad again because it did so well"),
    ("none", "in the show the main character gets stood up at the altar"),
    ("none", "that movie where the dog gets left behind always gets me"),
    ("none", "this song is about a guy nobody calls"),
    ("none", "the book is about a woman who moves to {city} and knows no one"),
    ("none", "my character in the game has no friends, it's hilarious"),
    ("none", "{who} says nobody came to her yard sale"),
    ("none", "{who} didn't get the job, she's applying again {when}"),
    ("none", "{who} failed the driving test, third time"),
    ("none", "{who} is working doubles all week"),
    ("none", "traffic was awful today"),
    ("none", "the wifi keeps dropping"),
    ("none", "my coffee went cold"),
    ("none", "the line at the dmv took {n} hours"),
    ("none", "they were out of {food}"),
    ("none", "i stubbed my toe on the same chair again"),
    ("none", "the meeting ran long"),
    ("none", "my package is late"),
    ("none", "it rained on my day off"),
    ("none", "my team lost last night"),
    ("none", "missed the bus by ten seconds"),
    ("none", "i burnt the toast"),
    ("none", "we lost at trivia by one point, rematch {when}"),
    ("none", "i came in last at bowling, as usual"),
    ("none", "{lead} i'm making {food} tonight"),
    ("none", "thinking about {food} for dinner"),
    ("none", "i moved to {city} {span} ago and i love it here"),
    ("none", "i sit by the window at {place} every day, best seat"),
    ("none", "{they} are always busy on {day}, so we do {event} the day after"),
    ("none", "i walked around the mall for an hour and bought nothing"),
    ("none", "i reread old messages from {who} and laughed"),
    ("none", "my evenings are mostly {hobby} and tea"),
    ("none", "i talk to {pet} all day, she's a great listener"),
    ("none", "i've got {n} dollars left on the gift card"),
    ("none", "my to-do list has {n} things on it, knocking them out"),
    ("none", "i can't stop laughing today"),
    ("none", "i'm tired, long shift, good day though"),
    ("none", "today was a lot but we got it done"),
]

_model, _lock = None, threading.Lock()
_seen = {}


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


def has_shape(said, label=""):
    """Someone telling Luma about themselves: a statement, with them in it, that isn't a request. The model is only believed
    then; and about lonely only when somebody is missing from the sentence."""
    said = str(said or "")
    if not (12 <= len(said) <= 300 and ME.search(said)) or ASKING.search(said):
        return False
    return label != "lonely" or bool(ABSENT.search(said))


def by_model(said):
    """The feeling the model is sure of, where the message has the shape; "" otherwise."""
    said = " ".join(str(said or "").split())
    if said in _seen:
        return _seen[said]
    out = ""
    if has_shape(said):
        guess = learned(said)
        if guess:
            label = max(guess, key=guess.get)
            if label in SURE and guess[label] >= SURE[label] and has_shape(said, label):
                out = label
    if len(_seen) > 4000:
        _seen.clear()
    _seen[said] = out
    return out
