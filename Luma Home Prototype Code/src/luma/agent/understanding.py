"""What they mean, however they say it.

A small model trained on billions of possible phrasings (scenarios.py) that runs in a
millisecond with nothing but numpy: hashed word and letter n-grams into a linear layer,
so slang, typos and speech-to-text slips still land. Luma uses it to:

- act on messy requests ("take me 2 my goalz", "wats on my cal")
- ask "Did you mean ...?" with a few choices when it's not sure, instead of guessing
- notice when someone got cut off ("remind me to") and ask them to finish
- notice frustration ("that's not what I said", "wtf") and recover, one step at a time
- walk someone through a feature bit by bit when they ask how

The trained weights live next to this file (understanding.npz); scripts/train_understanding.py
makes them from scenarios.py.
"""
from __future__ import annotations

import re
import threading
import zlib
from pathlib import Path

from luma.agent.scenarios import INTENTS

MODEL_PATH = Path(__file__).with_name("understanding.npz")
BUCKETS = 1 << 18

# How people type, back to plain words. Only for understanding; what they said is never rewritten.
SLANG = {
    "u": "you", "ya": "you", "yu": "you", "ur": "your", "youre": "you're", "r": "are", "pls": "please", "plz": "please", "pleasee": "please", "pleaseee": "please",
    "tmrw": "tomorrow", "tmr": "tomorrow", "tmrow": "tomorrow", "tomoro": "tomorrow", "tomorow": "tomorrow", "2moro": "tomorrow", "2morrow": "tomorrow",
    "tonite": "tonight", "2nite": "tonight", "2day": "today", "wat": "what", "wut": "what", "whut": "what", "whats": "what's", "wats": "what's", "da": "the",
    "w/": "with", "bc": "because", "cuz": "because", "cause": "because", "mins": "minutes", "min": "minutes", "hr": "hour", "hrs": "hours", "msg": "message",
    "txt": "text", "ppl": "people", "wanna": "want to", "gonna": "going to", "gotta": "got to", "tryna": "trying to", "finna": "about to", "lemme": "let me",
    "gimme": "give me", "dont": "don't", "cant": "can't", "wont": "won't", "im": "i'm", "ive": "i've", "id": "i'd", "k": "okay", "kk": "okay", "thx": "thanks",
    "ty": "thanks", "tysm": "thanks", "bday": "birthday", "abt": "about", "smth": "something", "sth": "something", "insta": "instagram",
    "ig": "instagram", "yt": "youtube", "fb": "facebook", "appt": "appointment", "rly": "really", "kno": "know", "dat": "that", "dis": "this", "sched": "schedule",
    "pic": "picture", "pics": "pictures", "mum": "mom", "b4": "before", "newz": "news", "luna": "luma", "lumen": "luma", "emial": "email", "e-mail": "email",
    "emails": "emails", "idk": "i don't know", "nvm": "never mind", "lmk": "let me know", "rn": "right now", "prob": "probably", "probs": "probably",
    "convo": "conversation", "info": "information", "rmd": "remind", "remindr": "reminder", "remnd": "remind", "reminde": "remind", "pod": "podcast",
    "wyd": "what are you doing", "hbu": "how about you", "wbu": "what about you", "omw": "on my way", "nm": "nothing much", "tho": "though", "thru": "through",
}
SPOKEN = [(re.compile(r"\be[ -]mail\b"), "email"), (re.compile(r"\bloom a\b"), "luma"), (re.compile(r"\btime her\b"), "timer"), (re.compile(r"\bpod cast\b"), "podcast")]
WORD = re.compile(r"[a-z0-9']+|w/")


def normalize(text):
    """'Yo can u remind me abt da dentist tmrw' -> 'yo can you remind me about the dentist tomorrow'."""
    text = str(text or "").lower().replace("’", "'")
    for pattern, plain in SPOKEN:
        text = pattern.sub(plain, text)
    words = [SLANG.get(w, w) for w in WORD.findall(text)]
    words = [re.sub(r"(.)\1{2,}", r"\1\1", w) for w in words]  # "pleaseeee", "nooo"
    return " ".join(words)


_VOCAB = None


def _vocab():
    """Words Luma's commands are made of, counted, for fixing typos in them (never in names or messages)."""
    global _VOCAB
    if _VOCAB is None:
        from collections import Counter
        words = Counter()
        for spec in INTENTS.values():
            for template in spec["t"]:
                words.update(w for w in re.findall(r"[a-z']+", re.sub(r"\{\w+\}", " ", template)) if len(w) >= 3)
        _VOCAB = words
    return _VOCAB


def _close(a, b, limit):
    """Edit distance (with swaps) up to limit, or limit + 1."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            if prev2 is not None and i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
        if min(prev) > limit:
            return limit + 1
    return prev[-1]


# Real words are never "fixed" into other words ("then" is not a typo of "the").
COMMON = set("""a about above after again against all almost also always am an and any anything are around as ask at away back be because been before being
below best better between big both bring but by call came can could day did different do does doing done down each else even ever every few find first
for found from get give go going gone good got great had has have he her here him his home how i if in into is it its just keep kind know last
later least leave left let life like little long look lot made make many may me mean might more most much must my need never new next nice no not
now of off often oh ok on once one only open or other our out over own part people place please put rather really right said same saw say see seem
she should show side since so some something soon still such sure take tell than thank thanks that the their them then there these they thing
things think this those though thought through time to today together told tomorrow tonight too took try turn two under until up us use very want
was way we week well went were what when where which while who whole why will with without word work would yeah year yes yet you your yours
wait wanna gonna went got lol omg hey yo sup bro dude man girl guy home house room car food mom dad sister brother friend friends boss money""".split())


def respell(text):
    """'mak a podcst abt space' -> 'make a podcast about space'. Only command words get fixed."""
    vocab = _vocab()
    out = []
    for w in normalize(text).split():
        if len(w) >= 3 and w.isalpha() and w not in vocab and w not in COMMON and w not in SLANG.values():
            limit = 1 if len(w) <= 5 else 2
            near = [(_close(w, v, limit), -n, v) for v, n in vocab.items() if v[0] == w[0] and abs(len(v) - len(w)) <= limit]
            near = [c for c in near if c[0] <= limit]
            if near:
                w = min(near)[2]
        out.append(w)
    return " ".join(out)


def _h(feature):
    return zlib.crc32(feature.encode()) & (BUCKETS - 1)


def features(text):
    """Hashed words, word pairs and letter n-grams of the plain version, plus a hint of the shape."""
    plain = normalize(text)
    words = plain.split()
    out = {_h("w:" + w) for w in words}
    out.update(_h("b:" + a + "_" + b) for a, b in zip(["^"] + words, words + ["$"]))
    for w in words:
        padded = f"<{w}>"
        for n in (3, 4, 5):
            out.update(_h(f"c{n}:" + padded[i:i + n]) for i in range(max(1, len(padded) - n + 1)))
    out.add(_h("len:" + str(min(len(words), 12))))
    if "?" in str(text): out.add(_h("shape:?"))
    if words: out.add(_h("first:" + words[0]))
    return sorted(out)


class Model:
    """The trained understanding model: a linear layer over hashed features, softmax with a calibrated temperature."""
    def __init__(self, path=MODEL_PATH):
        import numpy as np
        data = np.load(path, allow_pickle=False)
        self.intents = [str(x) for x in data["intents"]]
        rows, q, scale = data["rows"], data["q"], data["scale"]
        self.lookup = {int(r): i for i, r in enumerate(rows)}
        self.weights = q.astype(np.float32) * scale[:, None]
        self.bias = data["bias"].astype(np.float32)
        self.temperature = float(data["temperature"])

    def predict(self, text, k=4):
        import numpy as np
        idx = [self.lookup[f] for f in features(text) if f in self.lookup]
        logits = self.bias + (self.weights[idx].sum(axis=0) if idx else 0)
        z = logits / self.temperature
        p = np.exp(z - z.max())
        p /= p.sum()
        top = np.argsort(-p)[:k]
        return [(self.intents[i], float(p[i])) for i in top]


_model, _lock = None, threading.Lock()


def model():
    global _model
    with _lock:
        if _model is None and MODEL_PATH.exists():
            try:
                _model = Model()
            except Exception:
                _model = False  # a damaged file: Luma still works, it just won't guess
        return _model or None


def guess(text, k=4):
    """[(intent, probability), ...] best first, or [] when the model isn't here."""
    m = model()
    return m.predict(text, k) if m else []


def label(intent):
    return INTENTS.get(intent, {}).get("label")


# ---------------------------------------------------------------------------
# Cut off mid-sentence
# ---------------------------------------------------------------------------
DANGLING = re.compile(
    r"(?:(?<!just )\b(?:the|a|an|my|your|our|and|or|but|because|so that|if|um+|uh+|like|whether|than)"
    r"|\b(?:remind me|ping me|nudge me|need|want|have|got|going|gonna|wanna|trying|tryna|how|ask \w+|tell \w+|text \w+|email \w+|is|was|were)\s+to"
    r"|\bremind me(?: that)?|(?:^\W*|\b(?:can you|could you|please|and|then|to|gotta|need to)\s+)(?:tell|text|email|ask)\s+(?!you\b|u\b|back\b|me\b|again\b|now\b|later\b|too\b|please\b)\w+(?: (?!again\b|now\b|later\b|too\b|please\b)\w+)?(?: that)?"
    r"|\blet (?!me\b|us\b)\w+ know(?: that)?"
    r"|\b(?:can you|could you|would you|will you|i need you to|i want you to|i need|i want|set a reminder for|play some|look up|search for|find me|make me|open my|what's on my|what is on my|where is my|where are my|about the|for the|with the|to the|at the|on the|in the|of the)"
    r"|\.\.\.|…|[-—])\s*$", re.I)
QUESTION_START = re.compile(r"^\W*(?:who|what|where|when|why|which|how)\b", re.I)


def cut_off(text):
    """'remind me to' -> what to ask so they can finish. None when the message is whole."""
    said = " ".join(str(text or "").split())
    trailing = said.endswith(("...", "…", "-", "—"))
    if not said or (said[-1] in ".!?" and not trailing) or len(said.split()) < 2 or len(said) > 240:
        return None
    m = DANGLING.search(said)
    if not m:
        return None
    if QUESTION_START.match(said) and not re.search(r"\b(?:the|a|an|my|your|and|or|but|um+|uh+)$|\.\.\.$|…$", said, re.I):
        return None  # "who should I send it to" is a whole question, even without the question mark
    tail = " ".join(said.rstrip(".…-— ").split()[-4:])
    lowered = said.lower()
    if re.search(r"\b(?:remind|ping|nudge) me(?: (?:tomorrow|tonight|later|at \S+|in \S+ \S+))?(?: to| about)?\W*$", lowered):
        ask = "Remind you to what?"
    elif re.search(r"\b(?:text|tell|email|message|let)\b", lowered):
        ask = "What should I tell them?"
    elif re.search(r"\b(?:play)\b", lowered):
        ask = "Play what?"
    elif re.search(r"\b(?:open|what's on|what is on|where is|where are)\b", lowered):
        ask = "Your what?"
    elif re.search(r"\b(?:look up|search|find)\b", lowered):
        ask = "Find what?"
    elif re.search(r"\b(?:make|build|create)\b", lowered):
        ask = "Make what?"
    else:
        ask = "Keep going, I'm listening."
    return f"You got cut off after “{tail}”. {ask}"


# ---------------------------------------------------------------------------
# Frustration
# ---------------------------------------------------------------------------
# Aimed at Luma: it got something wrong.
AT_LUMA = re.compile(
    r"\b(?:are you (?:serious|kidding(?: me)?|dumb|stupid|deaf|for real|even listening)|bro+ what|"
    r"you(?:'re| are|r) (?:useless|stupid|dumb|so dumb|not listening|wrong|trash|annoying|broken|not helping)|useless|"
    r"(?:that'?s|thats|this is|this isn'?t|it'?s|its) (?:not it|wrong|not right|stupid|dumb|broken|annoying|ridiculous|not what i (?:said|asked|meant|wanted))|"
    r"not what i (?:said|asked(?: for)?|meant|wanted)|i (?:said|told you|already (?:said|told you))\b|no+ (?:that'?s |thats )?wrong|nope,? wrong|wrong again|"
    r"(?:you|it|that|this) (?:doesn'?t|does not|isn'?t|is not|didn'?t) (?:work|working|help)|why (?:would|did) you (?:do that|say that|open that)|"
    r"you got it wrong|you'?re not listening|listen to me|stop (?:it|that|doing that)|do it right|try again|that'?s not what i)\b"
    r"|^\W*no+\s*!+\W*$|^\W*wrong\W*$", re.I)
# Could be at Luma or at life: "ugh", "smh", "bruh".
HEAVY_SIGH = re.compile(r"\b(?:wtf|what the (?:hell|heck|fuck|f)|ffs|smh|ugh+|omg+|bruh+|come on|cmon|i give up|seriously|jesus|oh my god)\b", re.I)
STRONG = re.compile(r"\b(?:wtf|ffs|fuck\w*|useless|trash|dumb|stupid|i give up|wrong again|are you serious)\b|!{3,}", re.I)


def frustration(text):
    """(level, aimed_at_luma, what's left once it's taken out). level 0 means calm."""
    said = " ".join(str(text or "").split())
    aimed = bool(AT_LUMA.search(said))
    sighs = bool(HEAVY_SIGH.search(said))
    if not aimed and not sighs:
        return 0, False, said
    letters = [c for c in said if c.isalpha()]
    shouting = len(letters) >= 4 and sum(c.isupper() for c in letters) / len(letters) > 0.8
    level = 2 if STRONG.search(said) or shouting else 1
    rest = HEAVY_SIGH.sub(" ", AT_LUMA.sub(" ", said))
    rest = re.sub(r"^\W*(?:no+|nah|nope|bro|dude|man|luma|ok(?:ay)?|like|just|i mean|and|but)\b\W*", "", rest, flags=re.I)
    rest = re.sub(r"\s+", " ", rest).strip(" ,.!?-")
    return level, aimed, rest


# ---------------------------------------------------------------------------
# Picking from "Did you mean ...?"
# ---------------------------------------------------------------------------
ORDINALS = [(re.compile(r"\b(?:second|2nd|two|2|latter)\b|^\W*b\W*$"), 1), (re.compile(r"\b(?:third|3rd|three|3)\b|^\W*c\W*$"), 2),
            (re.compile(r"\b(?:fourth|4th|four|4)\b|^\W*d\W*$"), 3), (re.compile(r"\b(?:first|1st|top|former)\b|^\W*(?:one|1|a)\W*$"), 0)]
YES = re.compile(r"^\W*(?:y(?:es|ea|eah|ep|up|uh)|ya+|sure|bet|correct|right|exactly|that(?: one|'?s it)?|yes+ please|mhm|uh huh|ok(?:ay)?|do it|go|that'?s right|you got it)\W*$", re.I)
NO = re.compile(r"^\W*(?:no+|nah|nope|neither|none(?: of (?:them|those|that))?|wrong|something else|not (?:that|those|really)|no+ thanks?|other)\b", re.I)
_STOP = {"the", "one", "that", "yeah", "yes", "please", "um", "uh", "i", "want", "meant", "mean", "do", "a", "an", "to", "it", "my", "your", "you", "me", "for", "lol"}


def pick(reply, options):
    """Which option they chose: an index, 'none' if they said none of them, or None if they moved on."""
    said = normalize(reply)
    if not said:
        return None
    for i, o in enumerate(options):
        if said == normalize(o):
            return i
    words = set(said.split()) - _STOP
    best, score = None, 0.0
    for i, o in enumerate(options):
        theirs = set(normalize(o).split()) - _STOP
        if words and theirs:
            overlap = len(words & theirs) / len(words)
            if overlap > score:
                best, score = i, overlap
    if best is not None and score >= 0.5:
        return best
    if len(said.split()) <= 5:
        if re.search(r"\b(?:last|latter)\b", said) and options:
            return len(options) - 1
        for pattern, i in ORDINALS:
            if pattern.search(said) and i < len(options):
                return i
        if YES.match(reply):
            return 0
    if NO.match(reply) and len(said.split()) <= 5:
        return "none"
    return None


# ---------------------------------------------------------------------------
# Step by step
# ---------------------------------------------------------------------------
WALKS = {
    "chrome": {"title": "Luma in your Chrome", "steps": [
        {"say": "First, open Connectors and find “Luma for Chrome”. I'll take you there.", "open": "apps"},
        {"say": "Tap Get Luma for Chrome. I'll open the folder with the extension in it.", "stuck": "It's the card with the Chrome logo. Scroll down a little if you don't see it."},
        {"say": "Now in Chrome, go to chrome://extensions, turn on Developer mode at the top right, click Load unpacked and pick that folder.",
         "stuck": "Developer mode is a little switch in the top right corner of the extensions page. Once it's on, the Load unpacked button shows up on the left."},
        {"say": "Last one: click the Luma icon in Chrome's toolbar and press Pair. Then try “play some lofi” or “open YouTube”.",
         "stuck": "If the icon's hidden, click the puzzle piece in Chrome's toolbar and pin Luma."}]},
    "device": {"title": "Pair your Luma device", "steps": [
        {"say": "Plug in your Luma device and make sure it's on the same Wi-Fi as this computer.", "stuck": "Give it a minute after plugging in. Its light shows when it's ready."},
        {"say": "Now open Settings and find “Your Luma device”. Tap Find my Luma. I'll take you there.", "open": "settings"},
        {"say": "Pick your Luma from the list. It shows and says a 6-digit code. Type that in.",
         "stuck": "If it's not on the list, type its address instead. It's on the device's screen, or in your router's list of devices."},
        {"say": "That's it. You've got one Luma now: same memory on both, and it keeps going when your laptop's closed."}]},
    "brain": {"title": "A smarter brain", "steps": [
        {"say": "Open Settings and find “Luma's brain”. I'll take you there.", "open": "settings"},
        {"say": "For the strongest brain, paste an Anthropic API key (it starts with sk-ant-) and turn on the cloud brain. You can make one at console.anthropic.com.",
         "stuck": "At console.anthropic.com, go to API keys and press Create key. Copy it and paste it into Luma."},
        {"say": "Or, if this computer has 24 GB of memory or more, tap Get the bigger brain. It's free and private, and runs right here."}]},
    "plus": {"title": "Luma Plus", "steps": [
        {"say": "Luma Plus remembers everything with no limit, backed up and private, and it unlocks your phone and texting."},
        {"say": "Sign in with your phone number in Settings, then tap Get Luma Plus. I'll take you there.", "open": "settings"}]},
    "teach": {"title": "Teach me a task", "steps": [
        {"say": "Open my browser. I'll take you there.", "open": "browser"},
        {"say": "Tap Teach at the top, then do the task once like you normally would. I'll watch.",
         "stuck": "Teach is the button with the hand, next to the address bar."},
        {"say": "Give it a name and tap Save. Next time just say its name and I'll do it. Anything that sends or buys still waits for your OK."}]},
    "goals": {"title": "Goals", "steps": [
        {"say": "Just tell me what to keep doing, like “every morning check my email” or “tell me when AirPods drop under $150”."},
        {"say": "I'll run it on my own and put what I find in your Feed."},
        {"say": "You can see or stop any of them under Goals. I'll take you there.", "open": "goals"}]},
    "voice": {"title": "Talking out loud", "steps": [
        {"say": "Tap the mic next to where you type, or press Command Shift Space."},
        {"say": "Talk like normal. Cut me off anytime and I'll stop and listen."},
        {"say": "Say “stop” or tap the mic again when you're done."}]},
    "memory": {"title": "What I remember", "steps": [
        {"say": "Just talk. When you mention something worth keeping, like where you left your keys or someone's birthday, I save it on my own."},
        {"say": "Ask “where are my keys” or “what do you remember about me” anytime."},
        {"say": "You can see, change or delete any of it under Identity. I'll take you there.", "open": "identity"}]},
    "photo": {"title": "Showing me a photo", "steps": [
        {"say": "Tap the picture button next to where you type and pick a photo."},
        {"say": "Ask me anything about it, like “what does this say?” or “what plant is this?”."}]},
    "rules": {"title": "What I ask about first", "steps": [
        {"say": "Anything that sends, posts or buys waits for your OK. I show you exactly what will happen first."},
        {"say": "Say “yes”, “send it” or “bet”, or tap Allow. “Nah” or “wait” stops it."},
        {"say": "You can change what I do on my own under Rules. I'll take you there.", "open": "rules"}]},
    "deck": {"title": "Making a deck", "steps": [
        {"say": "Tell me what it's about and who it's for, like “a pitch deck for my coffee startup, for investors”."},
        {"say": "I'll build it and show you the slides. Ask for changes like “make slide 3 punchier”."},
        {"say": "It's saved in your Library, and opens in Keynote or PowerPoint."}]},
}
WALK_FOR = {"connect_chrome": "chrome", "pair_device": "device", "cloud_brain": "brain", "luma_plus": "plus", "teach": "teach", "goal": "goals", "open_goals": "goals",
            "talk": "voice", "remember": "memory", "open_identity": "memory", "recall_me": "memory", "forget_last": "memory", "where_is": "memory", "photo": "photo",
            "open_rules": "rules", "deck": "deck"}
HOW = re.compile(r"\b(?:how (?:do|can|would|should|does) (?:i|you|we|it|this)|how (?:does|do) (?:the |your |my )?\w+(?: \w+)? work|how to|walk me through|show me how|teach me how|help me (?:set up|connect|use|with)|"
                 r"i don'?t (?:get|understand|know how)|where do i|what do i (?:do|press|tap|click)|explain how|step by step)\b", re.I)
NEXT = re.compile(r"^\W*(?:(?:done|got it|ok(?:ay)?|did it|yep|yeah)[, ]+next|next|ok(?:ay)?(?: next| done| what now| then)?|done|did it|got it|k|kk|yep|yup|yes|yeah|sure|cool|and then|then what|what now|what next|"
                  r"what'?s next|i did (?:it|that)|finished|go on|continue|keep going|alright|aight|bet|word|now what|that worked|it worked)\W*$", re.I)
STUCK = re.compile(r"\b(?:stuck|not working|doesn'?t work|can'?t find|cannot find|don'?t see|where is (?:it|that)|i'?m lost|confused|huh|what\?|help|it'?s not there|nothing happened|didn'?t work)\b", re.I)
STOP = re.compile(r"^\W*(?:stop|never ?mind|nvm|cancel|that'?s enough|i got it(?: from here)?|i'?m good|forget it|later|not now|end)\W*$", re.I)


def walk_topic(text):
    """A how-to question about one of Luma's features -> which walkthrough, or None."""
    how = HOW.search(str(text or ""))
    if not how:
        return None
    text = str(text)[how.start():]  # "you have that in your memory, how can I connect?" is about connecting
    lowered = normalize(text)
    for key, words in [("chrome", r"chrome|extension"), ("device", r"device|hardware|luma box|pair"), ("brain", r"brain|api key|claude|smarter|model"),
                       ("plus", r"plus|upgrade|premium|subscri|pricing"), ("teach", r"teach"), ("goals", r"goal|routine|every (?:day|morning)"),
                       ("voice", r"talk|voice|mic|speak"), ("memory", r"memor|remember|forget"), ("photo", r"photo|picture|image|screenshot"),
                       ("rules", r"rules?|approv|permission|allow"), ("deck", r"deck|slides|presentation|powerpoint|keynote")]:
        if re.search(rf"\b(?:{words})", lowered):
            return key
    top = guess(text, 1)
    return WALK_FOR.get(top[0][0]) if top and top[0][1] >= 0.5 else None
