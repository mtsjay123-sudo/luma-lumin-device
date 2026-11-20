"""An experiment that did not ship: a small model that reads a hard moment the feeling rules miss.

feelings.read hears about two in three hard moments said in words nobody fitted it to (tests/hard_or_not.py, held
out: 100 of 150). The same kind of small model that works for "you're all I need" and "what are you?"
(luma.agent.hears) was tried here, with the practice sentences below, and it does not work (Nov 20, 2026):

- on practice sentence shapes it hadn't learned from, it heard about one hard line in four and misheard ordinary ones
  ("my fiance and i went out today" as heartbreak: it learns the words, not what happened);
- on the held-out halves: hard moments read 100 -> 101 of 150, and 20 ordinary lines newly read as hard (13 of 576
  everyday lines, 4 of 250 facts and passing remarks, 2 of 59 things a child says, 1 of 150 ordinary lines of hard-or-not).

Leaning and "what are you" are said with a small set of words. A hard moment is anything that can happen to a person,
and a bag of words can't tell "my boss forgot my birthday" from "my boss forgot his umbrella". What might: a model that
reads meaning (the one Luma already uses for memory, on computers big enough to hold it), or one plain YES/NO question
to the brain. Neither is built.

Nothing in Luma loads this file. scripts/train_feels.py repeats the experiment and writes to out/, not into Luma.

- learned(said):  {"hurt" | ... | "none": how sure}, or {} when no model has been trained here
- family(said):   the hard feeling the model is sure of, or None
"""
from __future__ import annotations

import re
import threading
from pathlib import Path

LEARNED = Path(__file__).resolve().parents[1] / "out" / "feels.npz"
HARD = ["hurt", "shame", "fear", "low", "lonely", "overwhelmed", "disappointed", "grief", "heartbreak"]
LABELS = HARD + ["none"]
# How sure the model has to be that it's a hard moment at all (its hard feelings added up), and then which one.
# Chosen on practice sentence shapes it hadn't learned from (train_feels.py --check).
SURE = 0.8

MINE = re.compile(r"\b(?:i|i'?m|im|i'?ve|ive|i'?d|i'?ll|my|me|myself|mine|we|we'?re|we'?ve|our|us)\b", re.I)
LAUGH = re.compile(r"\b(?:l+o+l+|l+m+f*a+o+|rofl|ha(?:ha)+h*|he(?:he)+|jk|just kidding|kidding)\b|[😂🤣💀😆😅]", re.I)
WHAT_IF = re.compile(r"^\W*(?:what if|imagine if|if|suppose|say)\b|\b(?:in the (?:show|movie|book|game|episode)|on the show|my character|the character)\b", re.I)
ASKED = re.compile(r"^\W*(?:(?:hey|ok|okay|so|wait|um|luma|and|oh|btw)[, ]+){0,2}(?:what|what'?s|whats|how|where|which|who|who'?s|when|should|do you|does|"
                   r"did you|can you|could you|would you|will you|is it|is there|are there|are you|any (?:ideas|tips))\b", re.I)
ORDER = re.compile(r"^\W*(?:(?:hey|ok|okay|luma|please|pls)[, ]+){0,2}(?:remind|add|set|play|turn|wake|put|start|stop|call|text|open|search|find|show|"
                   r"tell me|give me|look up|order|buy|book|schedule|cancel|pause|skip|volume)\b", re.I)

# ------------------------------------------------------------------------------------------------ practice sentences ---
# Written fresh on Nov 20, 2026. {blank}s are filled from SLOTS by the trainer.
SLOTS = {
    "who": ["manager", "boss", "best friend", "sister", "brother", "roommate", "coworker", "mom", "dad", "teacher", "coach", "cousin", "friend",
            "neighbor", "landlord", "aunt", "uncle", "stepdad", "team lead", "old friend"],
    "partner": ["girlfriend", "boyfriend", "husband", "wife", "partner", "fiance", "fiancee"],
    "kin": ["mom", "dad", "grandma", "grandpa", "brother", "sister", "uncle", "aunt", "best friend", "grandmother", "grandfather", "cousin"],
    "pet": ["dog", "cat", "old dog", "rabbit", "horse", "kitten", "bird", "guinea pig"],
    "crowd": ["everyone", "the whole team", "my friends", "the entire office", "my family", "a full room", "the group chat", "my kids", "strangers",
              "the whole class"],
    "thing": ["interview", "presentation", "exam", "audition", "review", "driving test", "recital", "speech", "tryout", "pitch", "final", "wedding",
              "meeting", "surgery", "court date"],
    "place": ["work", "school", "the office", "church", "the gym", "this city", "this town", "my building", "campus", "the new job", "practice"],
    "when": ["today", "tonight", "this week", "lately", "this morning", "all day", "since monday", "this month", "yesterday", "last night", "again",
             "right now", "these days", "for weeks"],
    "n": ["two", "three", "five", "six", "ten", "twelve", "fifteen"],
    "food": ["tacos", "ramen", "pizza", "curry", "dumplings", "pancakes", "sushi", "a burger", "soup", "pasta"],
    "show": ["that new series", "the game", "the finale", "a documentary", "that movie", "the match", "this podcast", "the season premiere"],
    "game": ["chess", "mario kart", "trivia", "poker", "wordle", "scrabble", "pickleball", "bowling"],
    "errand": ["the store", "the bank", "the gym", "the pharmacy", "the dentist", "the post office", "the mechanic", "the market"],
}

FRAMES = [
    # ---- hurt: someone hurt them ----
    ("hurt", "my {who} made fun of me {when} and everyone laughed"),
    ("hurt", "my {who} has been talking about me behind my back"),
    ("hurt", "my {who} forgot my birthday"),
    ("hurt", "my {who} called me useless"),
    ("hurt", "my {who} ghosted me after {n} years of friendship"),
    ("hurt", "my {who} took credit for my work and nobody said a thing"),
    ("hurt", "i found out my {who} has been lying to me this whole time"),
    ("hurt", "my {who} didn't even say goodbye"),
    ("hurt", "they all went out {when} without telling me"),
    ("hurt", "my {who} said i'm too much"),
    ("hurt", "my {who} told me to stop calling"),
    ("hurt", "my {who} blocked me on everything"),
    ("hurt", "my {who} said i ruined the holidays"),
    ("hurt", "my {who} picked their new friends over me"),
    ("hurt", "nobody stood up for me when my {who} went off on me"),
    ("hurt", "my {who} read my messages out loud to mock me in front of {crowd}"),
    ("hurt", "my {who} said they wish i was more like my {kin}"),
    ("hurt", "my {who} left me on read for a week and it's eating me up"),
    ("hurt", "my {who} rolled their eyes at me in front of {crowd}"),
    ("hurt", "my {who} told {crowd} my secret"),
    ("hurt", "my {who} acts like i don't exist {when}"),
    ("hurt", "my own {kin} didn't show up for me"),
    # ---- shame: hard on themselves ----
    ("shame", "i embarrassed myself so bad at {place}"),
    ("shame", "i can't believe i said that out loud at the {thing}"),
    ("shame", "i'm such a failure, i can't even keep a job"),
    ("shame", "i let everyone down again"),
    ("shame", "i feel so stupid for trusting my {who}"),
    ("shame", "i hate how i acted {when}"),
    ("shame", "i'm the reason we lost"),
    ("shame", "i got caught lying and i feel disgusting"),
    ("shame", "i ruined my {who}'s {thing}"),
    ("shame", "i should be further along by now, i'm so behind everyone my age"),
    ("shame", "i'm embarrassed to even tell you this"),
    ("shame", "i tripped on stage and the whole room saw"),
    ("shame", "i snapped at my kid and i feel like the worst parent"),
    ("shame", "i can't do anything right {when}"),
    ("shame", "i'm a joke at {place}"),
    ("shame", "i blanked in the {thing} and made a fool of myself"),
    ("shame", "i keep screwing everything up"),
    ("shame", "everybody at {place} thinks i'm an idiot now"),
    # ---- fear: scared, anxious, dreading ----
    ("fear", "i'm scared i'm going to lose my job"),
    ("fear", "the doctor wants more tests and i'm freaking out"),
    ("fear", "i have a {thing} {when} and my hands won't stop shaking"),
    ("fear", "i'm so anxious about the {thing} i feel sick"),
    ("fear", "i heard a noise downstairs and i'm scared"),
    ("fear", "my heart is pounding and i can't calm down"),
    ("fear", "i'm dreading the {thing}"),
    ("fear", "i'm so nervous i can't eat"),
    ("fear", "i'm afraid my {partner} is going to leave me"),
    ("fear", "the layoffs are coming and i think i'm next"),
    ("fear", "i'm worried sick about my {kin}"),
    ("fear", "my {kin} is in surgery right now and i can't sit still"),
    ("fear", "i don't know how i'm going to make rent"),
    ("fear", "i think i'm going to fail this class and lose my scholarship"),
    ("fear", "i can't stop shaking"),
    ("fear", "my chest is tight just thinking about the {thing}"),
    ("fear", "i've been up all night worrying about the {thing}"),
    ("fear", "my {kin} hasn't answered in hours and i'm getting scared"),
    # ---- low: down, empty, flat ----
    ("low", "i just feel empty {when}"),
    ("low", "nothing feels good anymore"),
    ("low", "i couldn't get out of bed {when}"),
    ("low", "i'm so down {when}"),
    ("low", "everything feels heavy {when}"),
    ("low", "i've been in a funk for weeks"),
    ("low", "i cried for no reason {when}"),
    ("low", "i feel numb"),
    ("low", "i'm not myself {when}"),
    ("low", "it's been a rough few weeks, i'm barely holding it together"),
    ("low", "i just feel sad and i don't know why"),
    ("low", "i have no energy for anything i used to like"),
    ("low", "i'm having a really bad day"),
    ("low", "today was awful and i just want it to be over"),
    ("low", "i don't feel like doing anything, it all feels gray"),
    ("low", "i've been really struggling {when}"),
    # ---- lonely ----
    ("lonely", "i have no one to talk to here"),
    ("lonely", "i ate dinner alone again {when}"),
    ("lonely", "i haven't made a single friend since i moved"),
    ("lonely", "everyone has plans but me"),
    ("lonely", "nobody texts me first"),
    ("lonely", "i spent my birthday by myself"),
    ("lonely", "i feel invisible at {place}"),
    ("lonely", "the apartment is so quiet it hurts"),
    ("lonely", "i don't have anyone to call when something good happens"),
    ("lonely", "it's saturday night and i'm by myself again"),
    ("lonely", "all my friends are back home and i've got nobody here"),
    ("lonely", "i feel so alone {when}"),
    ("lonely", "i sat by myself at lunch again"),
    ("lonely", "weekends are the worst, there's no one around"),
    ("lonely", "i went the whole day without anyone saying a word to me"),
    ("lonely", "i don't really have people here"),
    # ---- overwhelmed ----
    ("overwhelmed", "i have too much on my plate and i'm drowning"),
    ("overwhelmed", "i can't keep up with everything {when}"),
    ("overwhelmed", "work is crushing me {when}"),
    ("overwhelmed", "i'm so burnt out i can't think"),
    ("overwhelmed", "there aren't enough hours and i'm falling apart"),
    ("overwhelmed", "everything is due at once and i'm losing it"),
    ("overwhelmed", "i'm stretched so thin"),
    ("overwhelmed", "the baby won't sleep, i haven't slept, i can't do this"),
    ("overwhelmed", "i'm taking care of my {kin} and working full time and i'm at my limit"),
    ("overwhelmed", "my to-do list makes me want to cry"),
    ("overwhelmed", "it's all too much {when}"),
    ("overwhelmed", "i'm exhausted and it never stops"),
    ("overwhelmed", "i'm running on fumes and there's still so much to do"),
    ("overwhelmed", "i can't catch a break, it's one thing after another"),
    # ---- disappointed: bad news ----
    ("disappointed", "i didn't get the job"),
    ("disappointed", "they rejected my application"),
    ("disappointed", "i failed the {thing}"),
    ("disappointed", "we lost the house we bid on"),
    ("disappointed", "my visa got denied"),
    ("disappointed", "i got laid off {when}"),
    ("disappointed", "they cancelled my {thing} and i'd been looking forward to it for months"),
    ("disappointed", "i didn't make the team"),
    ("disappointed", "my offer fell through"),
    ("disappointed", "i got a bad grade on the {thing} i worked so hard on"),
    ("disappointed", "i didn't get in"),
    ("disappointed", "they gave the promotion to someone else"),
    ("disappointed", "my flight home got cancelled and i'm going to miss the {thing}"),
    ("disappointed", "the results came back and it's not good news"),
    ("disappointed", "i got passed over again"),
    ("disappointed", "the loan didn't go through"),
    # ---- grief ----
    ("grief", "my {kin} passed away {when}"),
    ("grief", "we had to put our {pet} down"),
    ("grief", "i lost my {kin} last year and it still hits me"),
    ("grief", "it's the anniversary of my {kin}'s death"),
    ("grief", "my {kin} died and i don't know how to do this"),
    ("grief", "i keep reaching for the phone to call my {kin} and then i remember"),
    ("grief", "we scattered my {kin}'s ashes {when}"),
    ("grief", "my {pet} didn't make it"),
    ("grief", "the funeral was {when}"),
    ("grief", "i still set a place at the table for my {kin}"),
    ("grief", "my {kin} is gone and nothing feels right"),
    ("grief", "it's been {n} months since we lost my {kin}"),
    # ---- heartbreak ----
    ("heartbreak", "my {partner} broke up with me"),
    ("heartbreak", "my {partner} left me for someone else"),
    ("heartbreak", "we're getting divorced"),
    ("heartbreak", "i got dumped over text"),
    ("heartbreak", "my {partner} cheated on me"),
    ("heartbreak", "the person i love doesn't love me back"),
    ("heartbreak", "my {partner} said they need space and i know what that means"),
    ("heartbreak", "the engagement is off"),
    ("heartbreak", "i saw my ex with someone new and it wrecked me"),
    ("heartbreak", "they ended things {when} and i can't stop crying"),
    ("heartbreak", "{n} years together and my {partner} just walked out"),
    ("heartbreak", "my {partner} moved out {when}"),
    # ---- none: heavy words, an ordinary day ----
    ("none", "this commute is killing me"),
    ("none", "i'm dead tired after the gym"),
    ("none", "i'm starving"),
    ("none", "i could kill for {food}"),
    ("none", "that movie wrecked me, so good"),
    ("none", "i cried laughing at {show}"),
    ("none", "the game was a heartbreaker but what a match"),
    ("none", "i'm scared of how good this {food} is"),
    ("none", "i'm dying to see {show}"),
    ("none", "i bombed at karaoke and it was great"),
    ("none", "i lost my keys again"),
    ("none", "we lost power for an hour"),
    ("none", "i lost at {game} again"),
    ("none", "i'm so done with {show}"),
    ("none", "i'm sick of this weather"),
    ("none", "i failed to find parking at {errand}"),
    ("none", "nobody was at the gym, i had it all to myself"),
    ("none", "i'm alone tonight, finally some quiet"),
    ("none", "everyone's out so i'm blasting music"),
    ("none", "i'm nervous and excited for the trip"),
    ("none", "happy tears at the wedding {when}"),
    ("none", "my {who} roasted me and it was hilarious"),
    ("none", "i'm broke till friday but whatever"),
    ("none", "work was busy but good"),
    ("none", "long day, good day"),
    ("none", "my {kin} passed the {thing}"),
    ("none", "my {who} passed me the ball and i scored"),
    ("none", "my {thing} is {when}"),
    ("none", "i'm overwhelmed by how nice everyone was"),
    ("none", "too much {food}, i'm stuffed"),
    ("none", "i'm drowning in leftovers"),
    ("none", "can't get out of bed, it's too cozy"),
    ("none", "the vending machine rejected my dollar again"),
    ("none", "my phone died {when}"),
    ("none", "my {who} left for work"),
    ("none", "my {who} left me the last slice"),
    ("none", "they cancelled the meeting, free afternoon"),
    ("none", "i didn't get the joke"),
    ("none", "i didn't get to {errand} {when}"),
    ("none", "i feel like {food}"),
    ("none", "i feel like a walk"),
    ("none", "feeling good {when}"),
    ("none", "i'm crushing it at work {when}"),
    ("none", "that workout destroyed me in a good way"),
    ("none", "i have nobody to split this pizza with, more for me"),
    ("none", "it's quiet {when}, kind of nice"),
    ("none", "i embarrassed my {who} with my dancing and they loved it"),
    ("none", "scary movie night {when}"),
    ("none", "i can't decide what to wear to the {thing}"),
    ("none", "panic over, found my wallet"),
    ("none", "my {who} is driving me nuts {when}"),
    ("none", "ugh mondays"),
    ("none", "the wifi is being awful {when}"),
    ("none", "i hate this printer"),
    ("none", "traffic was brutal {when}"),
    ("none", "my {who} and i are getting {food} {when}"),
    ("none", "i'm heading to {errand}"),
    ("none", "i watched {show} {when}"),
    ("none", "my {who} called me {when}"),
    ("none", "my {who} told me a funny story about {place}"),
    ("none", "my {who} forgot their umbrella at my place"),
    ("none", "my {partner} and i went out {when}"),
    ("none", "my {partner} left their keys here"),
    ("none", "my {kin} is visiting {when}"),
    ("none", "i got the job"),
    ("none", "i made the team"),
    ("none", "i passed the {thing}"),
    ("none", "we got the house"),
    ("none", "the {thing} went fine"),
    ("none", "i'm behind on {show}, no spoilers"),
    ("none", "i'm by myself at {errand}, want anything"),
    ("none", "i moved the {thing} to next week"),
    ("none", "i have a {thing} {when}, wish me luck"),
    ("none", "i need to pay rent {when}"),
    ("none", "my {who} said the {thing} got moved"),
    ("none", "i told my {who} about the {thing}"),
    ("none", "i can't keep up with {show}, too many episodes"),
    ("none", "i broke my record at {game}"),
    ("none", "nothing much {when}, just {food} and {show}"),
    ("none", "my {pet} is asleep on my feet"),
    ("none", "we put our {pet} in the car for the trip"),
    ("none", "my {kin} is gone for the weekend so i have the place to myself"),
    ("none", "my {who} didn't say much, we just watched {show}"),
    ("none", "i'm done with work for the day"),
    ("none", "i cried at {show}, such a good ending"),
    ("none", "i'm exhausted but it was a great day"),
    ("none", "good morning"),
    ("none", "what's for dinner"),
]

_model, _lock = None, threading.Lock()


def learned(said):
    """What the small model makes of this: {label: how sure}, or {} when the model isn't here."""
    global _model
    with _lock:
        if _model is None:
            try:
                from luma.agent import understanding
                _model = understanding.Model(LEARNED) if LEARNED.exists() else False
            except Exception:
                _model = False   # no numpy, or a damaged file: the rules still work
    if not _model:
        return {}
    return dict(_model.predict(" ".join(str(said or "").split()), len(_model.intents)))


def has_shape(said):
    """Someone talking about their own life, plainly: not a laugh, not a what-if, not a question, not a command."""
    said = str(said or "")
    return bool(8 <= len(said) <= 300 and MINE.search(said) and not LAUGH.search(said) and not WHAT_IF.search(said)
                and not ASKED.search(said) and not ORDER.search(said))


def family(said):
    """The hard feeling the model is sure of, or None. Only asked where the rules read nothing."""
    if not has_shape(said):
        return None
    guess = learned(said)
    if not guess or 1.0 - guess.get("none", 0.0) < SURE:
        return None
    best = max(HARD, key=lambda name: guess.get(name, 0.0))
    return best if guess.get(best, 0.0) >= guess.get("none", 0.0) else None
