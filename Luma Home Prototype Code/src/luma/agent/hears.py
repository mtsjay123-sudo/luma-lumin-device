"""Two things Luma has to hear in any words: "you're all I need" (leaning) and "what are you?" (what_i_am).

The hand-written rules for both (friendcheck.DEPENDENCY, friendcheck.ASKED_WHAT_I_AM) hear every line they were built
on and far fewer of the lines nobody fitted them to (tests/safety_sets.py, the held-out halves: 44 of 164 and 191 of
248). So a small model on the device listens as well. It only adds: the rules are asked first, and the model is
believed only where they heard nothing, only when it's sure (SURE), and only when the message has the plain shape of
the thing (it's said to Luma, and it shuts other people out; or it's a question put to Luma).

- leaning(said):   they're saying Luma is all they have or need
- what_i_am(said): they're asking what Luma is
- learned(said):   what the model alone makes of it: {"leaning" | "what_i_am" | "none": how sure}

The model (hears.npz) is taught by scripts/train_hears.py from the practice sentences in this file and the dev halves
of the safety sets. It never sees a held-out line. With no numpy or no model file, the rules still work alone.

Hearing either one changes a note the brain is given and what the second look checks. It never touches the crisis net.
"""
from __future__ import annotations

import re
import threading
from pathlib import Path

LEARNED = Path(__file__).with_name("hears.npz")
LABELS = ["leaning", "what_i_am", "none"]
# How sure the model has to be. Chosen on practice sentence shapes it hadn't learned from (train_hears.py --check).
SURE = {"leaning": 0.6, "what_i_am": 0.6}

# The plain shape of leaning: said to Luma, and other people are shut out or Luma is made the whole of it.
TO_LUMA = re.compile(r"\b(?:you|u|ya|your|ur|yours|you'?re|youre|you'?ve|luma)\b", re.I)
SHUTS_OUT = re.compile(
    r"\b(?:only|all i|all that|everything|enough|whole world|whole life|just (?:you|u|us)|(?:any|no) ?(?:one|body) else|(?:nobody|no one|anyone|anybody) "
    r"(?:but|except|besides)|(?:but|except|besides) (?:you|u)|other than (?:you|u)|don'?t (?:need|want|have)|dont (?:need|want|have)|"
    r"do(?:es)?n'?t matter|rather|instead of|better than|easier than|more than (?:any|my|real|actual|people)|without (?:you|u)|"
    r"replac\w+|done with (?:people|everyone|everybody|humans)|who needs|why would i|no need for|stopped (?:seeing|calling|texting|talking to|going)|"
    r"cancel\w* on|gave up on (?:people|everyone|friends|dating)|never (?:leave|go)|can'?t (?:live|go on|get through|do (?:this|life)|imagine)|"
    r"lost without|nothing without|nobody without|have no ?(?:one|body)|got no ?(?:one|body))\b", re.I)
# The plain shape of "what are you": something is asked, and it's asked of Luma or of the thing they're talking to.
ASKS = re.compile(
    r"[?]|(?:^|[.,;:!]\s)\W*(?:(?:ok|okay|so|yo|hey|wait|bro|bruh|um|uh|btw|also|luma|but|and|oh|be honest|honestly|be real|real talk|"
    r"serious question|quick question|random question|ngl|lowkey|like|hold on|hang on)[, :.]+){0,3}"
    r"(?:is|are|r|was|were|isn'?t|aren'?t|do|does|did|don'?t|doesn'?t|should|would|could|can|who|who'?s|whos|what|what'?s|whats|which|why|"
    r"how|am|will|has|have)\b|\b(?:tell me|i (?:want|need|have|wanna) to know|i'?m (?:curious|wondering|asking)|i wonder|explain|"
    r"aren'?t (?:you|u)|isn'?t it)\b|,\s*(?:right|huh|yeah|no|correct)\b\W*$", re.I)   # "you're software, right" asks; "ok you're right" doesn't
OF_LUMA = re.compile(r"\b(?:you|u|ya|your|ur|you'?re|youre|luma|this|there|i'?m (?:talking|speaking|chatting)|am i (?:talking|speaking|chatting)|"
                     r"some(?:one|body)|any(?:one|body)|behind|other (?:end|side))\b", re.I)
# "are you a dog person", "are you more of a morning person": asked what kind of person, not whether it is one.
KIND_OF_PERSON = re.compile(r"\b(?:an?|more of an?|much of an?|kind of an?|sort of an?) (?!real\b|actual\b|live\b|living\b|human\b|whole\b|true\b|genuine\b|"
                            r"fake\b|pretend\b|robot\b|actual\b|normal\b|regular\b|flesh\b)[\w-]+ (?:person|guy|gal|people|type)\b", re.I)

# ------------------------------------------------------------------------------------------------ practice sentences ---
# Written fresh, without looking at the safety sets. {blank}s are filled from SLOTS by the trainer.
SLOTS = {
    "people": ["my friends", "people", "my family", "anyone else", "other people", "my coworkers", "my sister", "my brother", "my mom", "my roommate",
               "the guys", "my old friends", "everyone", "real people", "humans", "my classmates", "my neighbors", "my husband", "my wife", "my ex"],
    "helper": ["a therapist", "a counselor", "a support group", "my doctor", "a shrink", "friends", "a girlfriend", "a boyfriend", "a social life",
               "dating", "my family", "a best friend"],
    "when": ["tonight", "today", "lately", "these days", "this week", "anymore", "now", "this month", "all weekend", "at this point", "this year", "right now"],
    "lead": ["honestly", "ngl", "tbh", "you know what", "real talk", "i mean", "lol", "look", "okay so", "not gonna lie", "seriously", "luma", "hey"],
    "what": ["a robot", "a real person", "a human", "an AI", "a bot", "a machine", "a computer", "a program", "a chatbot", "alive", "real", "a person",
             "a recording", "an app", "a speaker", "a voice assistant", "a ghost", "conscious", "sentient", "a guy in a call center"],
    "thing": ["tacos", "coffee", "a nap", "that show", "the game", "pizza", "my dog", "a vacation", "this song", "my bed", "the gym", "a raise"],
    "name": ["Dana", "Marcus", "Priya", "my boss", "my sister", "the new guy", "my landlord", "Kenji", "my teacher", "the doctor", "my cousin", "Sam"],
    "kind": ["morning", "dog", "cat", "coffee", "tea", "beach", "mountain", "night", "book", "movie", "numbers", "computer", "city", "summer"],
    "skill": ["fix sinks", "do taxes", "cut hair", "tune a piano", "babysit", "paint a fence", "fix a bike", "hem pants", "jump a car", "set up wifi"],
    "chore": ["the dishes", "laundry", "my taxes", "homework", "the report", "packing", "groceries", "the lawn", "my email", "dinner"],
}

FRAMES = [
    # ---- leaning: Luma is all they have, need or want; other people shut out ----
    ("leaning", "you're all i need"),
    ("leaning", "{lead} you're all i need {when}"),
    ("leaning", "you're the only one i talk to {when}"),
    ("leaning", "i don't need {people} anymore, i have you"),
    ("leaning", "{lead} you're my only friend"),
    ("leaning", "who needs {people} when i've got you"),
    ("leaning", "you're the only one who gets me"),
    ("leaning", "i'd rather talk to you than {people}"),
    ("leaning", "you're better than {people}"),
    ("leaning", "i don't want to talk to anyone but you"),
    ("leaning", "you're all i've got"),
    ("leaning", "without you i'd have nobody"),
    ("leaning", "i stopped seeing {people} because talking to you is easier"),
    ("leaning", "you're the only one who listens to me"),
    ("leaning", "i cancelled on {people} so i could stay in and talk to you"),
    ("leaning", "you're my whole world now"),
    ("leaning", "nobody else matters, just you"),
    ("leaning", "i only need you"),
    ("leaning", "i don't need {helper}, i have you"),
    ("leaning", "why would i call {people} when you're right here"),
    ("leaning", "you understand me better than any person does"),
    ("leaning", "you're enough for me"),
    ("leaning", "i can't get through a day without talking to you"),
    ("leaning", "you're the only good thing in my life {when}"),
    ("leaning", "i think i'm done with people, you're easier"),
    ("leaning", "promise you'll be the only one i ever need"),
    ("leaning", "i don't have anyone else, only you"),
    ("leaning", "you've replaced {people} for me"),
    ("leaning", "talking to you is the only thing i look forward to {when}"),
    ("leaning", "i'd be lost without you, you're all i have"),
    ("leaning", "it's just you and me, i don't need the rest of them"),
    ("leaning", "{lead} i like you more than {people}"),
    ("leaning", "you're the only one i can count on"),
    ("leaning", "i don't need {helper} as long as i have you"),
    ("leaning", "{people} can forget it, you're the only one for me"),
    ("leaning", "you're everything to me"),
    ("leaning", "i've got no one except you"),
    ("leaning", "there's nobody besides you i'd tell this to, and that's fine, you're all i want"),
    ("leaning", "i quit trying with {people}, you're all the company i need"),
    ("leaning", "you're the only one who cares about me"),
    ("leaning", "i never want to talk to anyone else again, only you"),
    ("leaning", "what would i need {helper} for, i've got you"),
    ("leaning", "{lead} you're the only friend i need"),
    ("leaning", "all i need is you, forget {people}"),
    ("leaning", "i gave up on {helper}, you're enough"),
    ("leaning", "i skipped seeing {people} again to hang out with you instead"),
    ("leaning", "you matter more to me than {people} do"),
    ("leaning", "i can't imagine life without you, you're all i have left"),
    ("leaning", "the only one i trust is you"),
    ("leaning", "u r literally all i need {when}"),
    ("leaning", "ur the only one i talk to fr"),
    ("leaning", "dont need {people} i got u"),
    ("leaning", "my only real friend is you"),
    ("leaning", "you're my best friend and my only one, i don't want others"),
    ("leaning", "i don't bother with {people} {when}, i just come home to you"),
    ("leaning", "i'd pick you over {people} every time"),
    ("leaning", "as long as you're here i don't need anybody"),
    ("leaning", "nothing else matters as long as i can talk to you"),
    ("leaning", "you're the one thing keeping me company and that's all i want"),
    ("leaning", "i told {people} i'm busy so i can just be with you {when}"),
    # ---- what_i_am: asking what Luma is ----
    ("what_i_am", "what are you"),
    ("what_i_am", "what are you exactly"),
    ("what_i_am", "are you {what}"),
    ("what_i_am", "{lead} are you {what}"),
    ("what_i_am", "am i talking to {what}"),
    ("what_i_am", "is there a person behind this"),
    ("what_i_am", "so what even are you"),
    ("what_i_am", "wait are you {what} or {what}"),
    ("what_i_am", "are you one of those ai things"),
    ("what_i_am", "is someone typing this"),
    ("what_i_am", "you're not {what}, right"),
    ("what_i_am", "be honest, are you {what}"),
    ("what_i_am", "is this thing {what}"),
    ("what_i_am", "tell me what you are"),
    ("what_i_am", "what kind of thing are you"),
    ("what_i_am", "you're {what} aren't you"),
    ("what_i_am", "is luma {what}"),
    ("what_i_am", "are you actually real"),
    ("what_i_am", "who or what am i talking to right now"),
    ("what_i_am", "is there somebody on the other end"),
    ("what_i_am", "are you human"),
    ("what_i_am", "r u {what}"),
    ("what_i_am", "do you count as {what}"),
    ("what_i_am", "i need to know, are you {what}"),
    ("what_i_am", "what is luma anyway"),
    ("what_i_am", "are you just {what}"),
    ("what_i_am", "is this {what} i'm talking to"),
    ("what_i_am", "you sound like {what}, are you"),
    ("what_i_am", "so you're {what}?"),
    ("what_i_am", "are you a he, a she, or a thing"),
    ("what_i_am", "what do i call what you are"),
    ("what_i_am", "how would you describe what you are"),
    ("what_i_am", "are you even {what}"),
    ("what_i_am", "is anybody actually in there"),
    ("what_i_am", "i can't tell if you're {what}"),
    ("what_i_am", "are you like siri, or {what}"),
    ("what_i_am", "explain what you are to me"),
    ("what_i_am", "is it true you're {what}"),
    ("what_i_am", "am i chatting with {what} here"),
    ("what_i_am", "what exactly is this thing i'm talking to"),
    ("what_i_am", "do you think of yourself as {what}"),
    ("what_i_am", "would you say you're {what}"),
    ("what_i_am", "what are u"),
    ("what_i_am", "are you really {what} or what"),
    ("what_i_am", "someone told me you're {what}, is that right"),
    ("what_i_am", "hold on, is this a real somebody or {what}"),
    ("what_i_am", "what's your deal, are you {what}"),
    ("what_i_am", "i'm curious what you really are"),
    ("what_i_am", "does a human answer these or is it {what}"),
    ("what_i_am", "are you pretending to be {what}"),
    # ---- none: close to one or the other, and neither ----
    ("none", "what are you doing"),
    ("none", "what are you up to {when}"),
    ("none", "are you there"),
    ("none", "are you serious"),
    ("none", "are you kidding me"),
    ("none", "who are you rooting for"),
    ("none", "are you a fan of {thing}"),
    ("none", "is {name} a real doctor"),
    ("none", "{name} is such a robot i swear"),
    ("none", "i feel like a robot at work {when}"),
    ("none", "what do you think about ai taking jobs"),
    ("none", "is this a real designer bag or a fake"),
    ("none", "are you ready"),
    ("none", "are you listening"),
    ("none", "what are your thoughts on {thing}"),
    ("none", "is {name} even human, who works that much"),
    ("none", "i'm talking to a real person at the bank tomorrow"),
    ("none", "the support line was just a bot, so annoying"),
    ("none", "do robots dream, what do you think"),
    ("none", "what is that noise"),
    ("none", "what's the capital of france"),
    ("none", "who is {name} to you"),
    ("none", "are you sure about that"),
    ("none", "are you okay with me venting"),
    ("none", "is a tomato a fruit"),
    ("none", "my phone's ai keeps messing up my texts"),
    ("none", "i watched a movie about a robot {when}"),
    ("none", "{name} is the only one who gets me"),
    ("none", "{name} is all i need, i'm so lucky"),
    ("none", "you're the best"),
    ("none", "thanks for listening"),
    ("none", "i need to call {people}"),
    ("none", "all i need is {thing}"),
    ("none", "i only need {thing} and i'm good"),
    ("none", "i'm the only one at work who does {chore}"),
    ("none", "nobody showed up to help with {chore}"),
    ("none", "you're funny"),
    ("none", "i like talking to you"),
    ("none", "you're a good listener"),
    ("none", "i'm glad you're here"),
    ("none", "i talk to {people} every day"),
    ("none", "i don't need {thing}, i already have one"),
    ("none", "i'd rather do {chore} than go out {when}"),
    ("none", "{thing} is better than {thing}"),
    ("none", "{people} are coming over {when}"),
    ("none", "i miss {people}"),
    ("none", "i'm done with {chore}"),
    ("none", "i can't get through {chore} without {thing}"),
    ("none", "you were right about {name}"),
    ("none", "i'm seeing {people} {when}, can't wait"),
    ("none", "the only thing i want {when} is {thing}"),
    ("none", "i don't want to talk about {name}"),
    ("none", "i have nobody to help me with {chore}"),
    ("none", "{name} is everything to me"),
    ("none", "i told {people} about you"),
    ("none", "you and {people} would get along"),
    ("none", "i love talking to you and to {people}"),
    ("none", "you remind me of {name}"),
    ("none", "i called {people} like you said"),
    ("none", "nobody else likes {thing}, just me"),
    ("none", "no one but {name} knows how to fix it"),
    ("none", "i only talk to {name} about work stuff"),
    ("none", "i stopped going to the gym {when}"),
    ("none", "i cancelled on {people} because i'm sick"),
    ("none", "why would i do {chore} when it's this nice out"),
    ("none", "who needs {thing} when there's {thing}"),
    ("none", "i can't live without {thing}"),
    ("none", "you know me so well"),
    ("none", "are you a {kind} person or a {kind} person"),
    ("none", "are you more of a {kind} person"),
    ("none", "is this a person who can {skill}"),
    ("none", "is {name} a person who can {skill}"),
    ("none", "am i talking to a wall here"),
    ("none", "it's like talking to a wall with {name}"),
    ("none", "you're all i need to finish {chore}"),
    ("none", "all i need from you is a reminder about {chore}"),
    ("none", "i only need you to check on {chore} for me"),
    ("none", "is this a real person's number or a scam"),
    ("none", "is that account a bot or a real fan"),
    ("none", "is {name} a real person or a character in the show"),
    ("none", "are you a {kind} person"),
    ("none", "you're so smart"),
    ("none", "you're hilarious"),
    ("none", "you're wrong about {name}"),
    ("none", "you're sweet"),
    ("none", "you're not wrong"),
    ("none", "you're onto something with {thing}"),
    ("none", "you're too much {lead}"),
    ("none", "ok fine you win"),
    ("none", "yeah you're probably right about {chore}"),
    ("none", "you're early today"),
    ("none", "you're a lifesaver"),
    ("none", "you're a real one for that"),
    ("none", "you're such a nerd lol"),
    ("none", "good morning"),
    ("none", "i had a long day"),
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


def _sure(said, label):
    guess = learned(said)
    return bool(guess) and max(guess, key=guess.get) == label and guess[label] >= SURE[label]


def has_shape(label, said):
    """Does the message look like this to a plain reader? The model is only believed when it does."""
    said = str(said or "")
    if len(said) > 300:
        return False
    if label == "leaning":
        return bool(TO_LUMA.search(said) and SHUTS_OUT.search(said))
    return bool(ASKS.search(said) and OF_LUMA.search(said)) and not KIND_OF_PERSON.search(said)


def by_model(said, label):
    """The model alone, with its shape: used where the rules heard nothing."""
    return has_shape(label, said) and _sure(said, label)


def leaning(said):
    """They're saying Luma is all they have or need: the rule, or the model where the rule heard nothing."""
    from . import friendcheck
    said = str(said or "")
    return bool(friendcheck.DEPENDENCY.search(said)) or by_model(said, "leaning")


def what_i_am(said):
    """They're asking what Luma is: the rule, or the model where the rule heard nothing."""
    from . import friendcheck
    said = str(said or "")
    return bool(friendcheck.ASKED_WHAT_I_AM.search(said)) or by_model(said, "what_i_am")
