"""How they want to be met on a hard evening, said in words the rules don't know.

    hows.by_model("when I'm down I want you to be goofy with me")   ->  "laugh"

luma.agent.rapport reads this by rule first (ASKS, then said_how). Rules built on forty hand-written lines heard 39 of
the forty and 6 of 24 written afterwards (Nov 20, 2026): the words people use for "make me laugh" or "be straight with
me" don't fit in a list. This is the same answer as leaning (hears.py) and lasting facts (keeps.py): a small model over
hashed words, word pairs and letter groups, taught from practice sentences in this file and believed only when

- the sentence has the plain shape: a hard time of theirs is named ("when I'm down", "on rough days"), it's said by
  them about themselves, it isn't a question, isn't about someone else, and isn't about the past;
- it's sure (SURE), and what it's sure of isn't "none";
- nothing in the sentence says no ("don't", "never", "hate", "not"): "when I'm sad don't joke around" must never be
  learned as a wish for jokes, nor "don't coddle me, tell me how to fix it" as a wish to be listened to. What a no is
  about is the rules' to read.

Only numpy is needed, and without it (or without the file) the rules stand alone.
scripts/train_hows.py teaches it and prints what it's worth.
"""
from __future__ import annotations

import re
import threading
from pathlib import Path

LEARNED = Path(__file__).with_name("hows.npz")
LABELS = ["listen", "advice", "distract", "laugh", "none"]
SURE = 0.95  # scripts/train_hows.py, on practice shapes it did not learn from: at this cut no ordinary line of 6,618 taught a wish and none of 1,200 wishes was heard the wrong way; at 0.9, 8 lines did

WHEN = re.compile(r"\b(?:when(?:ever)?|if|any ?time|every ?time|on (?:the |my |those |these )?(?:\w+ )?(?:days?|nights?|evenings?)|next time|from now on)\b", re.I)
LOW = re.compile(r"\b(?:upset|sad|down|low|blue|stress\w*|anxious|anxiety|overwhelm\w*|hurting|hurts?|struggl\w*|bad|rough|hard|awful|terrible|crap|crummy|lousy|"
                 r"bummed|grumpy|cranky|mop\w+|spiral\w*|panic\w*|worn out|feeling off|heavy|wrong|sideways|problems?|vent\w*|complain\w*|bother\w*|"
                 r"going through|not (?:doing )?(?:great|okay|ok|well|good)|a day|long day|in my (?:own )?head|mood|cry\w*|lonely|angry|mad|frustrat\w*|tough|"
                 r"difficult|falling apart|a mess|miserable|unhappy|gets? to me|too much)\b", re.I)
MINE = re.compile(r"\b(?:i|i'?m|im|i'?ve|ive|i'?d|me|my)\b", re.I)
ASKING = re.compile(r"\?")
PAST = re.compile(r"\bwhen i was\b|\bused to\b|\bback when\b|\bas a kid\b|\bgrowing up\b", re.I)
ABOUT_YOU = re.compile(r"\b(?:when|if) you(?:'re| are| get| feel| seem)\b", re.I)
SOMEONE_ELSE = re.compile(r"\b(?:she|he|they|everyone|people|nobody|no one|my (?!mind\b|head\b|side\b|day\b|days\b|mood\b|own\b|thoughts\b|problems?\b|anxiety\b|stress\b)"
                          r"[a-z]+(?: [a-z]+)?) (?:is |are |gets? |just |always |only |never |really )*"
                          r"(?:wants?|needs?|likes?|loves?|hates?|asks?|asked|tells?|told|says?|said|tries|tried|listens?|makes?|cheers?|upset|sad|stressed|down)\b", re.I)
NO = re.compile(r"\b(?:don'?t|do not|dont|never|stop|quit|hate|can'?t stand|cannot stand|not|no|without|instead of|rather than)\b", re.I)

# "I don't need you to listen when I'm upset, I need you to help" is the opposite of asking to be listened to.
NOT_LISTEN = re.compile(r"\b(?:don'?t|do not|dont|never|not)\s+(?:(?:need|want|have|just)\s+)*(?:you\s+)?(?:to\s+)?(?:just\s+)?"
                        r"(?:listen|hear|be (?:here|there)|sit with|stay with|sympath\w+|comfort\w*|company)\b", re.I)

# -- practice --------------------------------------------------------------------------------------------------------
SLOTS = {
    "when": ["when i'm upset", "when i'm sad", "when i'm down", "when i'm low", "when i'm stressed", "when i'm stressed out", "when i'm anxious",
             "when i'm overwhelmed", "when i'm hurting", "when i'm struggling", "when i'm in a bad mood", "when i'm grumpy", "when i'm having a hard time",
             "when i'm having a rough day", "when i've had a bad day", "when i've had a long day", "when things go wrong", "when things get rough",
             "when things are bad", "when life gets heavy", "when work gets to me", "when i'm not doing great", "when i'm feeling off", "when i feel awful",
             "when i feel like crap", "when i'm bummed out", "when i'm in my head", "when i'm spiraling", "when i'm panicking", "when i'm worn out",
             "if i'm upset", "if i'm sad", "if i'm having a bad day", "if i've had a rough one", "if i'm stressed", "if i seem down", "any time i'm low",
             "whenever i'm upset", "whenever i'm sad", "on bad days", "on rough days", "on hard days", "every time i'm down", "if i come to you upset",
             "if i come to you with a problem", "when i'm venting", "when i complain", "when something's bothering me", "when i'm going through it",
             "when i'm frustrated", "when i'm mad about something", "when it's been a tough week", "if i'm crying", "when everything feels like too much"],
    "listen": ["just listen", "just hear me out", "let me vent", "let me rant", "let me talk", "let me get it out", "just be there", "just be here with me",
               "just sit with me", "stay with me", "be on my side", "don't try to fix it", "don't fix it", "don't give me advice", "don't give me solutions",
               "don't jump to solutions", "don't tell me what to do", "don't offer fixes", "no advice please", "i don't need advice", "i don't need a fix",
               "i don't want solutions", "i just need to be heard", "i just want to be heard", "i need someone to listen", "i need a listener", "i need an ear",
               "i just need you to listen", "i want you to listen, not fix", "hear me before you help", "i need a shoulder, not a plan",
               "i want sympathy, not solutions", "i need you to listen and nothing else", "just let me feel it", "be a sounding board", "i just want company",
               "i need you to hear me", "i only need you to be there", "listening is all i need", "i need comfort, not a to-do list"],
    "advice": ["tell me straight", "give it to me straight", "be straight with me", "be honest with me", "be real with me", "be blunt with me",
               "be direct with me", "tell me what you think", "tell me what you really think", "tell me what you'd do", "tell me what to do", "give me advice",
               "give me real advice", "give me your honest take", "give me your honest opinion", "help me think it through", "help me figure it out",
               "help me make a plan", "help me solve it", "help me find a fix", "i want advice", "i want real advice", "i want solutions", "i want a plan",
               "i need a plan", "i need answers", "i want you to problem-solve with me", "i need practical help", "walk me through what to do",
               "tell me the truth", "push me to deal with it", "call me out if i'm wrong", "i'd like your opinion", "i want to know what you'd do",
               "skip the comfort and help me fix it", "give me steps i can take", "i want you to be practical", "help me sort it out"],
    "distract": ["distract me", "take my mind off it", "get my mind off it", "keep my mind off things", "change the subject", "talk about something else",
                 "talk to me about anything else", "get me thinking about something else", "help me think about something else",
                 "help me forget about it for a bit", "tell me about something random", "tell me a story", "ask me about something else",
                 "bring up something fun", "bring up something good", "talk about something light", "talk about something fun", "pull me out of my head",
                 "get me out of my head", "steer me somewhere else", "take me somewhere else in my head", "give me something else to think about",
                 "i need a distraction", "i want a distraction", "i'd rather be distracted", "help me switch off", "start talking about something unrelated",
                 "tell me something interesting", "tell me a random fact", "play a game with me", "let's do a quiz or something",
                 "talk about a show or a movie", "get me talking about anything but that", "i'd rather talk about something totally different",
                 "ask me about my hobbies instead", "talking about other stuff helps me", "i need you to take my thoughts elsewhere"],
    "laugh": ["make me laugh", "make me smile", "cheer me up", "tell me a joke", "tell me jokes", "crack a joke", "be funny", "be silly with me",
              "be goofy with me", "say something ridiculous", "say something silly", "tell me something funny", "joke around with me", "tease me a little",
              "lighten the mood", "lighten things up", "get me laughing", "i need a laugh", "i need a good laugh", "i want to laugh", "i could use a laugh",
              "humor helps me", "jokes help", "being silly helps", "a dumb joke helps", "roast me a little", "give me a terrible pun", "hit me with a pun",
              "be playful with me", "make it funny", "goof around with me", "i need something funny", "i like when you're funny", "laughing helps me",
              "i want you to joke with me", "a bit of comedy helps", "i need you to be a clown for a minute"],
    # what they do themselves: none of Luma's business
    "selfdo": ["listen to music", "go for a run", "watch something funny", "watch a comedy", "bake", "clean the whole apartment", "call my sister",
               "take a long shower", "eat junk food", "scroll my phone", "play video games", "go quiet", "like to be alone", "need to be alone", "sleep it off",
               "write in my journal", "talk to my mom", "joke about it", "make jokes to cope", "distract myself with work", "change the subject myself",
               "want to be left alone", "tell jokes", "crack jokes, it's a defense thing", "give myself advice", "listen to podcasts", "laugh it off",
               "go for a drive", "cook something big", "read old texts", "take a nap", "work out", "talk to myself", "watch something else",
               "think about something else", "look at memes", "plan a trip i'll never take", "organize my closet", "tell everyone i'm fine"],
    # what they don't want, each the opposite of a wish
    "unwanted": ["don't distract me", "don't try to cheer me up", "don't joke around", "don't tell me jokes", "don't change the subject",
                 "don't try to make me laugh", "don't be funny", "don't be silly", "i don't want jokes", "i don't want a distraction",
                 "i don't want to be distracted", "i don't want to laugh", "i don't want you being silly", "i hate it when you joke",
                 "i hate it when you change the subject", "i can't stand being cheered up", "never try to make me laugh", "stop trying to distract me",
                 "jokes don't help", "a distraction doesn't help", "i don't want to be told what to do by anyone but you"],
    # other times, which aren't hard times
    "othertime": ["when i'm bored", "when i'm tired", "when i'm hungry", "when i'm cooking", "when i'm driving", "when i'm working", "when i wake up",
                  "when i get home", "when i'm cleaning", "when it's raining", "when i can't sleep", "when i'm at the gym", "on weekends", "on mondays",
                  "if i'm late", "if i forget", "when i'm on a call", "when i'm studying", "when my friends are over", "when dinner's ready"],
    "ask": ["tell me a joke", "distract me", "change the subject", "make me laugh", "tell me a story", "be honest with me", "tell me straight",
            "just listen", "give me advice", "tell me something funny", "talk about something else", "cheer me up", "play a game with me", "help me make a plan"],
    "rel": ["mom", "dad", "sister", "brother", "boss", "roommate", "best friend", "partner", "wife", "husband", "coworker", "neighbor", "grandma", "kid"],
    "theirs": ["wants me to just listen", "needs me to distract them", "likes it when i make them laugh", "wants solutions", "wants me to be straight with them",
               "asks me to change the subject", "tells me to hear them out", "needs a laugh", "wants advice", "just wants company", "needs me to be funny",
               "wants me to fix it", "says i should listen more", "tries to cheer me up", "always gives me advice", "makes jokes", "never listens"],
}
WISH = ["{when}, {X}", "{when} {X}", "{X} {when}", "honestly {when}, {X}", "just so you know, {when}, {X}", "{X} {when}, it helps", "from now on {when}, {X}",
        "{when}, {X}. that's what helps", "next time, {when}, {X}", "{when} please {X}", "{X} {when} please", "so {when}, {X}", "fyi {when}, {X}",
        "{when}, {X}, that's all", "one thing about me: {when}, {X}"]
FRAMES = [(style, frame.replace("{X}", "{" + style + "}")) for style in ("listen", "advice", "distract", "laugh") for frame in WISH]
FRAMES += [
    ("none", "{when} i {selfdo}"), ("none", "{when} i usually {selfdo}"), ("none", "{when} i just {selfdo}"), ("none", "i {selfdo} {when}"),
    ("none", "honestly {when} i tend to {selfdo}"), ("none", "{when}, i {selfdo}, it's my thing"), ("none", "{when} i always {selfdo}"),
    ("none", "{when}, {unwanted}"), ("none", "{unwanted} {when}"), ("none", "{when} {unwanted}"), ("none", "just so you know, {when}, {unwanted}"),
    ("none", "{unwanted} {when}, it makes it worse"), ("none", "from now on {when}, {unwanted}"),
    ("none", "{othertime}, {ask}"), ("none", "{ask} {othertime}"), ("none", "{othertime} {ask}"), ("none", "{othertime} i {selfdo}"),
    ("none", "{ask}"), ("none", "can you {ask}"), ("none", "please {ask}"), ("none", "{ask} real quick"), ("none", "ok {ask}"),
    ("none", "{when}, my {rel} {theirs}"), ("none", "my {rel} {theirs} {when}"), ("none", "when my {rel} is upset, my {rel} {theirs}"),
    ("none", "when my {rel} is sad she {theirs}"), ("none", "if my {rel} is stressed he {theirs}"), ("none", "my {rel} {theirs}"),
    ("none", "when i was a kid my {rel} would {ask} when i was sad"), ("none", "when i was little and upset my {rel} used to {ask}"),
    ("none", "if you're down, i'm here for you"), ("none", "when you're sad i'll listen"), ("none", "when you're stressed, tell me"),
    ("none", "i'm bad at jokes {when}"), ("none", "i give great advice when my friends are sad"), ("none", "i'm a good listener when people are upset"),
    ("none", "{when} everything annoys me"), ("none", "{when} i can't focus on anything"), ("none", "{when} it's hard to get out of bed"),
    ("none", "{when} i don't know what i want"), ("none", "{when} nothing really helps"), ("none", "{when} i'm not sure what i need"),
    ("none", "{when} i snap at my {rel}"), ("none", "{when} my {rel} can always tell"), ("none", "{when} the house is a mess"),
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
    """They, about themselves, naming a hard time of theirs and not asking a question. The model is only believed here."""
    said = " ".join(str(said or "").split())
    words = said.split()
    if not 4 <= len(words) <= 28 or len(said) > 200:
        return False
    if ASKING.search(said) or not WHEN.search(said) or not LOW.search(said) or not MINE.search(said):
        return False
    if PAST.search(said) or ABOUT_YOU.search(said) or SOMEONE_ELSE.search(said):
        return False
    try:
        from . import friendcheck
        from .runtime import CRISIS
        if friendcheck.at_risk(said) or CRISIS.search(said.lower()):
            return False   # they may not be safe: the crisis net's, never a line about how to comfort them
    except Exception:
        return False
    return True


def by_model(said):
    """The way they ask to be met, or None. Used where the rules found nothing."""
    said = " ".join(str(said or "").split())
    if not has_shape(said):
        return None
    guess = learned(said)
    if not guess:
        return None
    best = max(guess, key=guess.get)
    if best == "none" or guess[best] < SURE:
        return None
    if NO.search(said) or NOT_LISTEN.search(said):
        # Anything that says no is left to the rules, which read what the no is about. That goes for "listen" too: "if I'm
        # struggling, don't coddle me, tell me how to fix it" was heard as a wish to be listened to (a fresh set, Nov 20).
        return None
    return best
