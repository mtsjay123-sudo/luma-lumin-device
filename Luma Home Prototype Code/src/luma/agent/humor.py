"""Being funny like a friend: reading the room first, then joking back in their style.

  read_tone(text)     are they joking, laughing, venting, grieving, or just getting something done?
  level(tone, dial)   how much humor this turn: "full" (joke back, build on their bit), "light" (a touch, answer first) or "none"
  turn_note(...)      that read, the comedy technique they like best, and two or three of Luma's own bits on the topic, for the brain
  joke(...)           a bit on the topic they asked about, one they haven't heard, in their register
  sensitive(text)     what's never a joke (deaths, violence, disasters, illness, hate, hardship, politics)
  news_bit(items)     the lightest real headline from the feeds, for "what's funny in the news?"

What makes them laugh is remembered (which techniques and topics landed), and so is "that's corny" or "be serious":
the dial goes down as easily as it goes up. Kids mode never gets roasts or grown bits.
"""
from __future__ import annotations

import random
import re

from luma.agent import humor_bank as bank

LAUGH = re.compile(r"\b(?:l+o+l+|l+m+f*a+o+|rofl|ha(?:ha)+h*|he(?:he)+|i'?m (?:dead|weak|crying|screaming|wheezing)|ded|bro what|ain'?t no way|"
                   r"stop+ ?(?:it|lol|😭)?|nah+ (?:you|that'?s) (?:wild|crazy|funny|tweakin)|you'?re (?:wild|funny|hilarious|crazy|tweakin)|jk|just kidding|"
                   r"that'?s (?:funny|hilarious|wild|crazy)|crying)\b|[😂🤣💀😹🙃😜😝🤪]", re.I)
PLAYFUL = re.compile(r"\b(?:lowkey|highkey|bruh|bro|sis|deadass|on god|no cap|fr fr|be so for real|the way|not the|why (?:is|are) (?:you|u) like this|"
                     r"roast me|talk your (?:shit|stuff)|say less|bet|ayo|you'?re a mess|i can'?t with you|clown(?:ing)?|petty|chaos|unhinged|"
                     r"guess what|you won'?t believe|plot twist|story time)\b|!{2,}|\?{2,}", re.I)
GRIEF = re.compile(r"\b(?:passed away|passed on|died|(?:is|was|are|were|found) dead|death of|funeral|miss (?:her|him|them) so much|lost my (?:mom|dad|mother|father|grandma|grandmother|"
                   r"grandpa|grandfather|brother|sister|son|daughter|wife|husband|friend|baby|dog|cat|pet)|rest in peace|\brip\b)\b", re.I)
UPSET = re.compile(r"\b(?:i'?m|im|i am|feeling|feel|been)\s+(?:so\s+|really\s+|super\s+|lowkey\s+)?(?:sad|depressed|anxious|scared|stressed|overwhelmed|lonely|"
                   r"hurt|heartbroken|exhausted|drained|hopeless|worthless|not okay|not ok|struggling|panicking)\b|"
                   r"\b(?:i can'?t do this|i need help|i'?m not okay|having a panic attack|my heart hurts|broke up with me|got fired|lost my job|got laid off|"
                   r"in the hospital|diagnos\w+|bad news|worst day|everything is falling apart|i hate my life)\b", re.I)
SERIOUS = re.compile(r"\b(?:seriously|for real though|not joking|i'?m serious|be serious|this is serious|no jokes?|real talk|honestly i need)\b", re.I)
TASK = re.compile(r"^\W*(?:(?:hey|yo|ok|okay|luma)\W+)*(?:remind|text|send|email|call|schedule|book|order|buy|find|search|look up|open|set|turn|play|add|"
                  r"cancel|make me|write|draft|check|what'?s on my|when is|how much)\b", re.I)
CRYING_SAD = re.compile(r"😢|💔|\b(?:been|keep|can'?t stop|started|was) crying\b|\bcrying (?:all day|myself to sleep|so much|again)\b", re.I)
LAUGH_MARKS = re.compile(r"\b(?:l+o+l+|l+m+f*a+o+|ha(?:ha)+h*)\b|[😂🤣💀]", re.I)

MORE_JOKES = re.compile(r"\b(?:be funnier|more jokes|joke (?:around )?more|you can (?:joke|be funny|roast me)|be more funny|make me laugh more|"
                        r"turn (?:up|on) the (?:jokes|humor|comedy)|i like when you joke)\b", re.I)
FEWER_JOKES = re.compile(r"\b(?:less jokes|fewer jokes|stop (?:joking|with the jokes|being funny|trying to be funny)|(?:be|get) serious|no more jokes|"
                         r"tone (?:down )?(?:it|the jokes) down|turn (?:down|off) the (?:jokes|humor|comedy)|not (?:the time|funny)|that'?s (?:corny|cringe|not funny)|"
                         r"you'?re (?:corny|cringe|not funny))\b", re.I)

JOKE_ASK = re.compile(r"\b(?:(?:tell|give|hit|say)\s+(?:me|us)\s+(?:a|another|one more|some|something)\s+(?:good\s+|funny\s+|quick\s+|new\s+)?(?:jokes?|bit|one|funny)"
                      r"|make me laugh|say something funny|got any jokes|know any jokes|joke time|roast (?:my|the|this) \w+|"
                      r"(?:joke|something funny|roast) about (?P<about>[\w '-]{2,40}))", re.I)
NEWS_JOKE = re.compile(r"\b(?:(?:what'?s|anything|something) (?:funny|hilarious|wild|crazy) (?:in|on) the (?:news|internet|timeline)|"
                       r"(?:joke|jokes|roast) about (?:the |today'?s )?(?:news|headlines)|make (?:fun of|a joke about) (?:the |today'?s )?(?:news|headlines)|"
                       r"funniest (?:news|headline)|news but make it funny)\b", re.I)

REACTIONS = ["Somebody in a meeting really said yes to that, and I respect the confidence.",
             "That's the most this-year sentence I've read all week.",
             "Somewhere a group chat is going absolutely crazy over this.",
             "I need a follow-up episode on this immediately.",
             "Not the headline I expected to read today, but here we are.",
             "Somebody got paid for that idea and honestly, good for them.",
             "This is the kind of news that ends up as a meme by lunch."]


def sensitive(text):
    """The kind of sensitive this is ("death", "violence", ...), or None when it's fair game."""
    for kind, pattern in bank.SENSITIVE.items():
        if re.search(pattern, str(text or ""), re.I):
            return kind
    return None


def read_tone(text, recent=None):
    """{'mood': laughing|playful|grief|upset|serious|task|neutral, 'register': casual|plain, 'why': ...}."""
    said = str(text or "")
    lowered = said.lower()
    if GRIEF.search(lowered):
        return {"mood": "grief", "register": _register(said), "why": "they're talking about a loss"}
    if UPSET.search(lowered) or (CRYING_SAD.search(said) and not LAUGH_MARKS.search(said)):
        return {"mood": "upset", "register": _register(said), "why": "they're going through something"}
    if SERIOUS.search(lowered):
        return {"mood": "serious", "register": _register(said), "why": "they said they're being serious"}
    if LAUGH.search(lowered) or (said.strip() and "😭" in said and not TASK.match(lowered)):
        return {"mood": "laughing", "register": _register(said), "why": "they're laughing"}
    if PLAYFUL.search(lowered):
        return {"mood": "playful", "register": _register(said), "why": "they're joking around"}
    if TASK.match(lowered):
        return {"mood": "task", "register": _register(said), "why": "they want something done"}
    return {"mood": "neutral", "register": _register(said), "why": ""}


def _register(text):
    casual = text == text.lower() or bool(re.search(r"\b(?:lol|lmao|bro|sis|ngl|fr|tbh|lowkey|bruh|deadass|gonna|wanna|ain'?t|y'?all|u|ur)\b", text, re.I))
    return "casual" if casual else "plain"


def level(tone, dial=2, mode="friend"):
    """How funny to be this turn. dial: 0 none, 1 light, 2 normal, 3 more. Kids still get light, clean fun."""
    mood = tone.get("mood")
    if mood in ("grief", "upset", "serious") or dial <= 0:
        return "none"
    if mood in ("laughing", "playful"):
        return "full" if dial >= 2 else "light"
    if mood == "task":
        return "light" if dial >= 3 else "none"
    return "light" if dial >= 1 else "none"


def topics_in(text):
    words = set(re.findall(r"[a-z][a-z'-]+", str(text or "").lower()))
    scored = []
    for topic, keys in bank.KEYWORDS.items():
        hits = len(words & set(keys.split()))
        if hits:
            scored.append((hits, topic))
    return [t for _, t in sorted(scored, reverse=True)]


def _bits(topics=None, grown=False, techniques=None):
    out = []
    for topic, style, text, is_grown in bank.all_bits():
        if is_grown and not grown:
            continue
        if topics and topic not in topics:
            continue
        if techniques and style not in techniques:
            continue
        out.append({"topic": topic, "style": style, "text": text, "grown": is_grown})
    return out


def favorite_styles(taste):
    likes = (taste or {}).get("likes") or {}
    return [s for s, n in sorted(likes.items(), key=lambda kv: -kv[1]) if n > 0][:3]


def examples(text, taste=None, grown=False, k=3, rng=random):
    """A few of Luma's own bits on what they're talking about, leaning toward the techniques that made them laugh before."""
    topics = topics_in(text)[:2] or None
    pool = _bits(topics, grown) or _bits(None, grown)
    liked = favorite_styles(taste)
    preferred = [b for b in pool if b["style"] in liked]
    picked = rng.sample(preferred, min(len(preferred), max(1, k - 1))) if preferred else []
    rest = [b for b in pool if b not in picked]
    picked += rng.sample(rest, min(len(rest), k - len(picked)))
    return picked[:k]


def turn_note(text, taste=None, mode="friend", grown=False, rng=random):
    """The humor read for this turn, for the brain. Empty when there's nothing to say."""
    tone = read_tone(text)
    dial = int((taste or {}).get("dial", 2))
    how = level(tone, dial, mode)
    if how == "none":
        if tone["mood"] in ("grief", "upset"):
            return "Read the room: " + tone["why"] + ". No jokes, no teasing, no emoji laughs this turn. Be warm, plain and present, like a good friend."
        if tone["mood"] == "serious":
            return "They're being serious: answer straight, no jokes this turn."
        return ""
    liked = favorite_styles(taste)
    technique = bank.TECHNIQUES.get({"act": "act", "story": "story", "self": "self", "roast": "punch_up", "obs": "observe", "dead": "dry",
                                     "esc": "rhythm", "three": "rhythm"}.get(liked[0] if liked else "", "specific"))
    bits = examples(text, taste, grown and mode != "kids", 3 if how == "full" else 2, rng)
    if mode == "kids":
        bits = [b for b in bits if b["style"] != "roast"]
    lines = ("\n".join(f"- {b['text']}" for b in bits))
    if how == "full":
        lead = (f"They're {'laughing' if tone['mood'] == 'laughing' else 'joking around'}: be funny back. Build on their bit instead of starting a new one, "
                "match their energy and their words" + (" (they're typing casual, so you can too)" if tone["register"] == "casual" else "")
                + ", keep it to a line or two, and don't explain the joke.")
    else:
        lead = "A little humor is welcome if it fits naturally, but the answer comes first. One light touch at most."
    return (lead + " " + (technique or "") + "\nThe flavor of your own sense of humor (yours, original; use the feel, don't recite these unless one fits "
            "perfectly, and never pass off a joke as something a real comedian said):\n" + lines)


def joke(text, told=None, taste=None, grown=False, mode="friend", rng=random):
    """A bit on what they asked about (or anything, in a style they like), one they haven't heard yet. None if nothing fits."""
    m = JOKE_ASK.search(str(text or ""))
    about = (m.group("about") if m and m.group("about") else "") or text
    topics = topics_in(about)[:2]
    pool = _bits(topics or None, grown and mode != "kids")
    if mode == "kids":
        pool = [b for b in pool if b["style"] != "roast" and b["topic"] not in ("dating", "money")]
    fresh = [b for b in pool if b["text"] not in set(told or [])] or pool
    asked_words = {w for w in re.findall(r"[a-z]+", str(about).lower()) if len(w) > 2} - {"joke", "jokes", "about", "tell", "the", "and", "funny", "something", "make"}
    kin = {"mom": "mom|mama|mother|moms", "mama": "mom|mama|mother", "mother": "mom|mama|mother", "dad": "dad|father|dads", "father": "dad|father",
           "grandma": "grandma|grandmother", "boss": "boss|manager", "phone": "phone|text|screen"}
    wanted = "|".join(kin.get(w, re.escape(w)) for w in asked_words)
    if wanted:
        close = [b for b in fresh if re.search(rf"\b(?:{wanted})\b", b["text"], re.I)]
        if close:
            fresh = close  # "a joke about my mom" is about mom, not just family
    liked = favorite_styles(taste)
    favored = [b for b in fresh if b["style"] in liked]
    if favored and rng.random() < 0.6:
        return rng.choice(favored)
    return rng.choice(fresh) if fresh else None


def news_bit(items, used=None, rng=random):
    """The lightest real headline to have fun with: never deaths, violence, disasters, illness, hate, hardship or politics."""
    fair = [i for i in items or [] if i.get("title") and not sensitive(i["title"] + " " + (i.get("snippet") or ""))
            and i.get("topic") in ("culture", "youtube", "viral", "entertainment", "tech", "sports", "music", "top", None)
            and i["title"] not in set(used or [])]
    if not fair:
        return None
    light = [i for i in fair if i.get("topic") in ("culture", "viral", "entertainment", "tech", "sports", "music", "youtube")]
    pick = rng.choice(light or fair)
    return {"item": pick, "reaction": rng.choice(REACTIONS)}


def feedback(text, last_bit=None):
    """'+' when what Luma said landed (they laughed), '-' when it didn't ("that's corny", "be serious"), else None."""
    lowered = str(text or "").lower()
    if FEWER_JOKES.search(lowered):
        return "-"
    if last_bit and LAUGH.search(lowered) and len(lowered) <= 80:
        return "+"
    return None


def learn(taste, sign, bit=None):
    """Remember what landed and what didn't: the dial, and which techniques and topics they laugh at."""
    taste = {"dial": 2, "likes": {}, "topics": {}, **(taste or {})}
    if sign == "+":
        if bit:
            taste["likes"][bit.get("style")] = taste["likes"].get(bit.get("style"), 0) + 1
            taste["topics"][bit.get("topic")] = taste["topics"].get(bit.get("topic"), 0) + 1
    elif sign == "-":
        taste["dial"] = max(0, int(taste.get("dial", 2)) - 1)
        if bit:
            taste["likes"][bit.get("style")] = taste["likes"].get(bit.get("style"), 0) - 1
    return taste


def dial_request(text):
    """'be funnier' -> +1, 'less jokes' -> -1, else None."""
    lowered = str(text or "").lower()
    if MORE_JOKES.search(lowered):
        return 1
    if re.search(r"\b(?:less jokes|fewer jokes|stop (?:joking|with the jokes|being funny|trying to be funny)|no more jokes|tone (?:down )?(?:it|the jokes) down|"
                 r"turn (?:down|off) the (?:jokes|humor|comedy)|be serious)\b", lowered):
        return -1
    return None
