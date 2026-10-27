"""Quick answer or deep dive? Luma asks when it could go either way, the way a friend would.

"What do you think about Trump?" "Should I quit my job?" "What's the news today?" can each be a
one-line answer or a real sit-down. Instead of guessing (and either rambling or brushing it off),
Luma asks first, in the way they talk:

    "Ngl, how deep you want me to go on this one? 😭 I can really sit with it, or if you just want
     my answer right now, I gotchu."

Their pick sends it down the quick path (a short, honest answer) or the deep one (Luma thinks it
through from a few angles and checks itself). Luma remembers what they usually pick for each kind
of question and stops asking once it's clear, and never asks when they already said
("real quick", "break it down", "think hard").
"""
from __future__ import annotations

import re
from datetime import datetime

# The kinds of questions that can go either way.
NEWS = re.compile(r"\b(?:what'?s (?:the )?news|news today|today'?s news|what'?s (?:going on|happening) (?:in the world|out there|today)|catch me up(?: on (?:the news|the world|everything))?(?! on)|"
                  r"what'?s new (?:in the world|today)|headlines|what happened today|anything (?:big|new) happen(?:ing|ed)?)\b", re.I)
OPINION = re.compile(r"\b(?:what (?:do |does )?(?:you|u|ya|yall|y'all) (?:think|feel)|how (?:do )?(?:you|u|ya) feel|what'?s your (?:take|opinion|view|stance)|your (?:take|thoughts|opinion) on|thoughts on|"
                     r"what(?:'s| is) (?:the )?(?:tea|word) on|how (?:you|u) rock with|you (?:fw|fuck with|mess with)|"
                     r"do (?:you|u) (?:like|rock with|support|trust)|where do (?:you|u) stand|is \w+ (?:good|bad|right|wrong) for|who'?s right)\b", re.I)
BIG = re.compile(r"\b(?:trump|biden|harris|obama|kamala|vance|desantis|newsom|aoc|bernie|president|presidency|congress|senate|supreme court|election|vote|voting|democrats?|republicans?|"
                 r"liberals?|conservatives?|politic\w*|abortion|immigration|deport\w*|border|gun(?:s| control)?|police|israel|palestin\w*|gaza|ukraine|russia|china|war|tariffs?|"
                 r"economy|recession|inflation|capitalism|socialism|communism|religion|god|church|islam|christian\w*|atheis\w*|racism|reparations|dei|woke|feminism|"
                 r"climate|ai taking|crypto|bitcoin|death penalty|marriage|monogamy|kids|having children)\b", re.I)
ADVICE = re.compile(r"\b(?:should i|do (?:you|u) think i should|what should i do|is it (?:worth it|smart|a good idea|too late)|help me (?:decide|figure (?:it )?out|think)|"
                    r"what would (?:you|u) do|am i wrong|was i wrong|is it bad (?:that|if) i)\b", re.I)
LIFE = re.compile(r"\b(?:quit|job|career|boss|raise|school|college|major|degree|drop out|break up|breakup|divorce|marry|married|propose|engaged|move (?:out|in|to|away|back)|"
                  r"relationship|boyfriend|girlfriend|bf|gf|husband|wife|situationship|ex|friend|friendship|family|mom|dad|parents|invest|investing|stocks|house|rent|"
                  r"loan|debt|credit|savings|business|startup|start a|launch|therapy|health|doctor|baby|pregnant|tattoo|car|lease)\b", re.I)
# Life decisions worth a real sit-down. Everyday asks ("what should I get my mom", "should I text him") are just answered.
DECISION = re.compile(r"\b(?:quit|resign|leave (?:my|the|this) (?:job|school|relationship|city)|take (?:the|that|this) (?:job|offer)|change (?:careers?|jobs?|majors?)|switch (?:careers?|jobs?|majors?)|"
                      r"drop out|go back to school|break up|breakup|divorce|marry|propose|get engaged|move (?:out|to|away|back|in with|across)|relocate|invest|buy a (?:house|home|car)|"
                      r"start (?:a|my own) (?:business|company)|have (?:a )?(?:baby|kids)|cut (?:him|her|them) off|forgive (?:him|her|them)|confront|ask for a raise|go to therapy|take out a loan)\b", re.I)
DILEMMA = re.compile(r"\b(?:what should i do about|am i wrong|was i wrong|is it bad (?:that|if) i|is it too late)\b", re.I)
EXPLAIN = re.compile(r"^\W*(?:can (?:you|u) )?(?:explain|break down|walk me through|why (?:does|do|is|are|did|was|were)|how (?:does|do|did) .{3,} (?:work|happen|start)|"
                     r"what(?:'s| is| was) the (?:difference|deal) (?:between|with)|what really happened (?:with|to|in))\b", re.I)
# "Explain" is worth asking about only when the subject could fill an hour.
DEEP_TOPICS = re.compile(r"\b(?:history|empire|civilization|universe|black holes?|consciousness|stock market|markets?|crypto|bitcoin|quantum|evolution|"
                         r"philosophy|meaning of life|slavery|civil rights|world war|cold war|revolution|colonial\w*|the fed|interest rates|ai)\b", re.I)
COMPARE = re.compile(r"\b(?:which is better|which one is better|what'?s better|\bvs\.?\b|versus|better than|compare)\b", re.I)

# They already said how much they want.
WANTS_QUICK = re.compile(r"\b(?:real quick|quick question|quick take|quickly|in one sentence|in a sentence|one word|in a word|tl;?dr|short answer|short version|"
                         r"just (?:tell me|answer|give me)|yes or no|briefly|keep it (?:short|quick|light)|no essay|straight up)\b", re.I)
WANTS_DEEP = re.compile(r"\b(?:deep dive|go deep|think (?:hard|deep(?:ly)?|it through|carefully)|really think|take your time|break it down|in detail|in depth|"
                        r"all the details|full rundown|explain everything|walk me through everything|pros and cons|weigh (?:it|this|the options))\b", re.I)

# Their answer to "quick or deep?".
PICK_QUICK = re.compile(r"^\W*(?:the )?(?:quick(?:ly| one| answer| take| version| headlines)?|fast|short|shorter|now|right now|just (?:the )?(?:answer|tell me|now|headlines)|"
                        r"keep it (?:short|quick|light|simple)|surface|nah,? just|tl;?dr|first one|the first|1|just your answer|answer now|give it to me now)\b", re.I)
PICK_DEEP = re.compile(r"\b(?:deep(?:er| dive)?|dig in|dig into it|dive in|go in|go off|think|take your time|full|whole|everything|all of it|in depth|break it down|"
                       r"rundown|the long one|second one|the second|2|really think|sit with it|go hard|go crazy|all the way)\b", re.I)
STOP_ASKING = re.compile(r"\b(?:stop asking|don'?t ask (?:me )?(?:that|every time)|just answer (?:me )?(?:from now on|always)|always (?:just )?(?:answer|keep it short))\b", re.I)

SLANG = re.compile(r"\b(?:ngl|gng|fr|frfr|ong|bruh|bro|deadass|lowkey|highkey|finna|tryna|ion|icl|istg|bussin|no cap|cap|bet|aight|ight|twin|gang|fam|lol|lmao|ts|pmo|ya|yall|y'all)\b|😭|💀", re.I)


def kind_of(text):
    """news · politics · advice · explain · compare, or None for anything that's simply answered."""
    t = text or ""
    if len(t.split()) < 3:
        return None
    if NEWS.search(t) and not re.search(r"\b(?:my|your|our) news\b|\bgood news\b|\bbad news\b", t, re.I):
        return "news"
    if OPINION.search(t) and BIG.search(t):
        return "politics"
    if ADVICE.search(t) and (DECISION.search(t) or DILEMMA.search(t)):  # "should I quit my job", not "what should I get my mom"
        return "advice"
    if COMPARE.search(t) and len(t.split()) >= 4 and BIG.search(t):
        return "compare"
    if EXPLAIN.search(t) and len(t.split()) >= 5 and (BIG.search(t) or DEEP_TOPICS.search(t)):
        return "explain"
    return None


def said(text):
    """'quick' / 'deep' if they already said how much they want."""
    if WANTS_DEEP.search(text or ""):
        return "deep"
    if WANTS_QUICK.search(text or ""):
        return "quick"
    return None


def read_choice(text):
    """Their answer to the question: 'quick', 'deep', or None (they said something else entirely)."""
    t = (text or "").strip()
    if len(t.split()) > 12:
        return None
    if PICK_DEEP.search(t) and not re.match(r"^\W*(?:quick|short|fast)\b", t, re.I):
        return "deep"
    if PICK_QUICK.search(t):
        return "quick"
    return None


def casual(text, profile=None, style=None):
    """Do they talk casual (so Luma asks casual)?"""
    if SLANG.search(text or ""):
        return True
    if (profile or {}).get("language_style") == "contemporary":
        return True
    slang = (style or {}).get("slang") or {}
    return sum(slang.values()) >= 3


def ask(kind, text, now, zone, profile=None, style=None, seed=0):
    """The question, in their register. News gets today's date up front, so nobody wonders what 'today' means."""
    chill = casual(text, profile, style)
    if kind == "news":
        day = datetime.fromtimestamp(now, zone)
        date = f"{day:%A}, {day:%B} {day.day}"
        lines = ([f"It's {date}. You want the quick headlines, or should I give you the whole rundown?",
                  f"Okay, it's {date}. Quick version, or you want me to really go through it?"] if chill else
                 [f"It's {date}. Want the quick headlines, or the full rundown?",
                  f"Today's {date}. Should I keep it to the top stories, or go through everything?"])
    elif chill:
        lines = ["Ngl, how deep you want me to go on this one? 😭 I can really sit with it, or if you just want my answer right now, I gotchu.",
                 "Okay wait, you want my quick take, or should I really go in on this one?",
                 "Real talk, I can give you my answer right now, or I can actually sit with it for a sec. Which one?"]
    else:
        lines = ["Okay, how deep you want me to go on this? I can give you my answer right now, or really think it through.",
                 "Quick take, or you want me to really dig into this one?",
                 "I can answer that right now, or sit with it for a sec and give you the real deep dive. Your call."]
    line = lines[seed % len(lines)]
    from luma.agent import humor
    if humor.read_tone(text)["mood"] in ("grief", "upset", "serious"):
        line = line.replace(" 😭", "")  # "for real though, should I take the job?" is serious: no laughing-crying face
    return line


# How to answer once they've picked. Deep goes through Luma's deliberation; these shape the quick answers.
QUICK = {
    "politics": ("They picked your quick take on politics or a public figure. Jump straight in, two or three spoken sentences in their register, "
                 "shaped like: \"Okay, real quick: the people who back him love ___ and ___. The people against him point to ___. Where you at on it?\" "
                 "Fill the blanks with things supporters like and critics push back on that you're sure of (no recent events you can't confirm). "
                 "Don't take a side, and don't start with a disclaimer about having opinions."),
    "advice": "They picked your quick answer. Say what you'd do and the one reason that matters most, in two or three spoken sentences. One short follow-up question if it helps.",
    "explain": "They picked the short version. The core idea in two or three spoken sentences, in everyday words. Offer to go deeper.",
    "compare": "They picked your quick take. Pick one, give the one reason that decides it, two or three spoken sentences.",
}


def how_to_answer(kind, pick):
    return QUICK.get(kind) if pick == "quick" else None


def remembered(prefs, kind):
    """If they've picked the same thing the last three times for this kind of question, just do that."""
    if (prefs or {}).get("_always"):
        return prefs["_always"]
    picks = (prefs or {}).get(kind) or []
    return picks[-1] if len(picks) >= 3 and len(set(picks[-3:])) == 1 else None


def remember(prefs, kind, pick):
    prefs = dict(prefs or {})
    prefs[kind] = (list(prefs.get(kind) or []) + [pick])[-5:]
    return prefs
