"""Jokes Luma tells when asked. A small brain garbles punchlines ("outstanding in his field" came out as "great at
his job"), so the jokes themselves come from here, told as written, and the brain only does the talking around them.
Clean on purpose: they work for anyone in the room. Luma doesn't repeat one until it has told the rest."""
from __future__ import annotations

import random
import re

JOKES = [
    "Why did the scarecrow win an award? He was outstanding in his field.",
    "I'm reading a book about anti-gravity. It's impossible to put down.",
    "Why don't skeletons fight each other? They don't have the guts.",
    "Parallel lines have so much in common. Shame they'll never meet.",
    "I only know 25 letters of the alphabet. I don't know y.",
    "What do you call a fake noodle? An impasta.",
    "Why can't you trust an atom? They make up everything.",
    "I asked the librarian if they had books on paranoia. She whispered, \"They're right behind you.\"",
    "Did you hear about the claustrophobic astronaut? He just needed a little space.",
    "I'd tell you a chemistry joke, but I know I wouldn't get a reaction.",
    "What do you call cheese that isn't yours? Nacho cheese.",
    "Why did the bicycle fall over? It was two tired.",
    "I tried to start a hot air balloon business. It never took off.",
    "I'm afraid of elevators, so I'm taking steps to avoid them.",
    "Why did the coffee file a police report? It got mugged.",
    "I don't trust stairs. They're always up to something.",
    "Why did the math book look sad? Too many problems.",
    "What do you call a bear with no teeth? A gummy bear.",
    "I got a job at a bakery because I knead the dough.",
    "What did the ocean say to the beach? Nothing. It just waved.",
    "I told a joke about a roof once. It went over everyone's head.",
    "What do you call a sleeping dinosaur? A dino-snore.",
    "Why don't eggs tell jokes? They'd crack each other up.",
    "What do you call an alligator in a vest? An investigator.",
    "I used to play piano by ear. Now I use my hands.",
    "What's orange and sounds like a parrot? A carrot.",
    "Why did the golfer bring two pairs of pants? In case he got a hole in one.",
    "I would avoid the sushi if I were you. It's a little fishy.",
    "Why was the computer cold? It left its Windows open.",
    "What do you call a pile of cats? A meowntain.",
    "Why did the tomato blush? It saw the salad dressing.",
    "How does the moon cut its hair? Eclipse it.",
    "What do you call a factory that makes okay products? A satisfactory.",
    "Why are ghosts bad liars? You can see right through them.",
    "What do you call a can opener that doesn't work? A can't opener.",
    "What did one wall say to the other? I'll meet you at the corner.",
    "Why did the cookie go to the doctor? It was feeling crummy.",
    "What do you call a dog that does magic? A labracadabrador.",
    "My wifi went down for five minutes, so I had to talk to my family. They seem like nice people.",
    "Why did the phone wear glasses? It lost all its contacts.",
]

ASK = re.compile(r"^\W*(?:(?:yo|hey|ok|okay|luma|aye|ayo|bro|pls|please)\W+)*(?:(?:can|could) (?:you|u)\s+|pls\s+|please\s+)?"
                 r"(?:tell|give|hit|say)\s+(?:me|us)\s+(?:a|another|one more|some)\s+(?:good\s+|funny\s+|quick\s+|dad\s+|bad\s+|corny\s+)?(?:jokes?|one)"
                 r"|^\W*(?:make me laugh|say something funny|got any jokes|know any jokes|joke time)\b", re.I)
MORE = re.compile(r"^\W*(?:another(?: one)?|one more|again|tell me another|hit me again|more)\W*$", re.I)


def asked(text, last_joke_at=0.0, now=0.0):
    """True when they want a joke: asked outright, or "another one" right after one."""
    if MORE.match(text or ""):
        return bool(last_joke_at) and now - last_joke_at < 600
    return bool(ASK.search(text or ""))


def pick(told, rng=random):
    """A joke they haven't heard yet; once they've heard them all, start over."""
    fresh = [j for j in JOKES if j not in set(told or [])]
    return rng.choice(fresh or JOKES)
