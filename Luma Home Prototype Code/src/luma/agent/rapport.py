"""How to be with them: what a close friend learns about a person from what they said and how they took things.

A friend who has known you a month knows two things a stranger doesn't: what you want when you're hurting (to be
listened to, to be told straight, to be taken out of your head, to laugh), and what not to bring up. Luma learns both
from what the owner actually says, never from a guess:

- "I don't need advice, I just need to vent" is kept, with their words and the day they said it.
- "That's not helping, I didn't ask for advice", said right after Luma gave some, counts the same way.
- Wanting advice, a distraction or a laugh has to be asked for on two occasions, or said as how they are ("when I'm
  upset I'd rather you tell me straight"): one "what would you do?" is about that day, not about them.
- "Please don't bring up my ex" is kept, and Luma doesn't: no check-in about it, nothing raised unasked.

What it's used for: when they're hurting, one line tells the brain how they've asked to be met. When they raise a
closed subject themselves, one line says to follow their lead and not dig. On every other turn it says nothing.

What keeps it honest and kind:
- Every line has its evidence: their own words and the day. Evidence older than four months no longer counts, so who
  they were in the spring doesn't speak for who they are now.
- The owner sees all of it in the app, in plain words, and can forget any line. "Forget about ..." forgets it here too.
- It is never used to keep them talking, and never in kids mode. When they might not be safe, the crisis net has
  already answered; this says nothing.
- "Make me laugh" is never applied to grief, heartbreak, fear or shame: there, being with them comes first.

Read by code, kept as one encrypted setting ("rapport").
"""
from __future__ import annotations

import re

KEY = "rapport"
KEEP = 5                     # the newest pieces of evidence kept for each thing
EASY_KEEP = 500              # subjects they've closed, kept (it was 12: memory is the device's, and it's big)
FADES = 120 * 86400          # evidence older than this no longer counts
STYLES = ("listen", "advice", "distract", "laugh")

# What they ask for. "listen" is said plainly enough to count any time; the others only count in a hard moment, because
# "what should I do" about dinner and "tell me a joke" on a slow afternoon say nothing about how to comfort someone.
ASKS = {
    "listen": re.compile(
        r"\bjust (?:listen|hear me out|let me (?:vent|rant|talk|get (?:it|this) out))\b|"
        r"\b(?:don'?t|do not|didn'?t|dont) (?:want|need|ask for) (?:any |your |more )?(?:advice|solutions?|a fix|fixing|a lecture|a pep talk|to be fixed)\b|"
        r"\bnot (?:looking|asking) for (?:any |your )?(?:advice|solutions?|a fix|answers)\b|"
        r"\bjust (?:need|needed|want|wanted|wanna|have|had) to (?:vent|rant|talk|say it|get (?:it|this|that) (?:out|off my chest))\b|"
        r"\b(?:don'?t|stop) (?:try(?:ing)? to )?(?:fix(?:ing)? (?:it|this|me|everything)|solv(?:e|ing) (?:it|this))\b|"
        r"\bstop (?:giving|with the) (?:me )?advice\b|\bi (?:just )?need (?:you|someone) to listen\b|"
        r"\b(?:don'?t|do not|dont) (?:want|need) (?:any |your |the )?(?:answers|tips|ideas|suggestions|a plan|homework)\b|"
        r"\bno (?:advice|fixing|fixes|tips|solutions|suggestions)\b(?=[^.?!]{0,20}\b(?:please|unless|okay|ok|just)\b)|"
        r"\b(?:keep|hold|save|skip) (?:the|your) (?:advice|tips|suggestions)\b|\b(?:don'?t|do not|dont) give me (?:any )?(?:tips|advice|answers|suggestions|solutions)\b", re.I),
    "advice": re.compile(
        r"\bwhat (?:should|do|would|can) (?:i|you think i should) do\b|\bwhat would you do\b|\bi need (?:your |some |real )?advice\b|"
        r"\btell me what to do\b|\b(?:give it to me|tell me) straight\b|\bbe (?:honest|real|straight) with me\b|"
        r"\bhelp me (?:figure|think|sort) (?:this|it|that) (?:out|through)\b|\bwhat do you think i should\b", re.I),
    "distract": re.compile(
        r"\bdistract me\b|\b(?:take|get|keep) my mind off\b|\btalk (?:to me )?about (?:something|anything) else\b|"
        r"\b(?:can we|let'?s) (?:please )?(?:change the subject|talk about (?:something|anything) else)\b|\bi need a distraction\b", re.I),
    "laugh": re.compile(
        r"\bmake me laugh\b|\bcheer me up\b|\bi (?:need|could use) (?:a|to) laugh\b|\btell me something funny\b|\bi need (?:something|anything) funny\b", re.I),
}
# Said as how they are, not just about this moment: "when I'm upset I'd rather you just tell me straight".
GENERAL = re.compile(r"\b(?:when(?:ever)? i'?m (?:upset|sad|down|low|stressed|hurting|like this|struggling|in a mood)|"
                     r"i (?:always|usually|generally|mostly) (?:just )?(?:want|need|like|prefer)|i(?:'d| would) rather you|i (?:like|love|prefer) (?:it )?when you|"
                     r"next time|from now on|in general|as a rule|that'?s (?:just )?how i am)\b", re.I)
# The same thing in words ASKS doesn't know ("if I'm down, change the subject for me", "sometimes I only need an ear, not a
# plan"). Forty ways of saying it, written by hand on Nov 20, 2026 as practice for the brain: Luma heard 3. This reader
# counts a line only when all three are there: it's said as how they are (a hard time of theirs is named, or a standing
# word like "unless I ask" or "I'd rather"), something is asked for, and it's asked of Luma (an order, or "you", "me",
# "I need"). "When I'm sad I watch something funny" is none of Luma's business and teaches nothing.
WHEN_LOW = re.compile(
    r"\b(?:when(?:ever)?|if|any ?time|every ?time|on (?:the )?days?)\b[^.?!;]{0,45}?"
    r"\b(?:upset|sad|down(?! (?:for|to|with)\b)|low|blue|stressed|hurting|struggling|bummed|grumpy|cranky|moping|mopey|anxious|overwhelmed|in a mood|"
    r"(?:bad|rough|hard|long|awful|terrible|crummy|lousy) (?:day|one|night|week|time|patch|stretch)|had a day|"
    r"go(?:es)? (?:wrong|sideways|badly|south)|(?:is|'s|’s) (?:wrong|bad|rough)|stuck|gets? to me|get(?:s|ting)? on top of me|spiral\w*|"
    r"complain\w*|vent\w*|a problem|not (?:okay|ok|doing (?:well|great))|falling apart)\b", re.I)
STANDING = re.compile(r"\b(?:unless i (?:ask|say)|i'?ll (?:tell|ask) you (?:if|when)|sometimes i (?:only|just)|i (?:only|mostly|mainly|usually|always|generally) "
                      r"(?:just )?(?:need|want)|i'?d rather|i would rather|i (?:like|love|prefer) (?:it )?when you|more than i need|i vent to)\b", re.I)
MORE = {
    "listen": re.compile(
        r"\b(?:hear me(?: out)?|be heard|listen(?: to me)?|an ear|be (?:here|there)(?: (?:with|for) me)?|be on my side|stay with me|sit with me|"
        r"let me (?:talk|vent|get it out|say it)|talk it through)\b|"
        r"\b(?:no|not|don'?t|do not|dont|without|instead of)\b[^.?!]{0,25}?\b(?:tips?|advice|answers|ideas|a plan|plans|homework|fix(?:es|ing)?|solutions?|"
        r"suggestions|solve|mend|told what to do)\b", re.I),
    "advice": re.compile(
        r"\b(?:tell me|give it to me|say it) straight\b|\bbe (?:direct|straight|honest|real|blunt) with me\b|\b(?:your )?honest (?:take|opinion|answer)\b|"
        r"\bwhat you (?:really |actually |honestly )?think\b|\bhelp me (?:think|figure|sort|work) (?:(?:it|this|things|that) )?(?:out|through)\b|"
        r"\bdon'?t just (?:nod|agree|listen)\b", re.I),
    "distract": re.compile(
        r"\b(?:something|anything|somewhere) (?:else|different|fun|lighter|light|good)\b|\bchange the subject\b|\bdistract(?:ed|ion)?\b|"
        r"\bout of my (?:own )?head\b|\b(?:tell me|with) a story\b", re.I),
    "laugh": re.compile(
        r"\bmake me (?:laugh|smile|giggle)\b|\bjokes?\b|\bcheer me up\b|\bsomething (?:silly|funny)\b|\bbe funny\b|"
        r"\blighten (?:things|it|me|the mood) up\b|\b(?:want|need|like) to laugh\b|\bget me laughing\b", re.I),
}
# Asked of Luma: "you", "me", "I need", or an order at the start of a clause.
AIMED = re.compile(r"\b(?:you|me|my (?:mind|head|side)|i'?d rather|i would rather|i (?:just |only |mostly |really )?(?:need|want)|i vent)\b|"
                   r"(?:^|[,.;:!?]\s*|\b(?:just|please|then)\s+)(?:be|hear|listen|stay|sit|tell|give|make|cheer|lighten|change|distract|take|get|keep|pull|"
                   r"steer|bring|talk|help|let|don'?t|no|keep|hold|skip)\b", re.I)
# Someone else's way of being comforted, or something they don't want: neither is how to be with them.
SOMEONE_ELSE = re.compile(r"\b(?:she|he|they|everyone|people|nobody|no one|my (?!mind\b|head\b|side\b)[a-z]+(?: [a-z]+)?) (?:just |always |only |never |really )?"
                          r"(?:wants?|needs?|likes?|loves?|hates?|asks?|asked|tells?|told|says?|said|tries|tried|listens?|makes?|cheers?)\b", re.I)
THEIR_WAY = re.compile(r"\b(?:she|he|they|everyone|my (?!mind\b|head\b)[a-z]+) (?:just |always |only |really )?(?:wants?|needs?|asks?|asked|tells?|told|likes?) "
                       r"(?:me|us|people|someone|everyone) to\s+(?:\w+\s+){0,2}$", re.I)
UNWANTED = (r"(?:don'?t|do not|dont|never|stop|quit|hate (?:it )?when you|can'?t stand (?:it )?when you|not)\s+(?:you\s+)?"
            r"(?:try(?:ing)? to |want(?: to be| you to)? |need(?: you to| to be)? |ever |like(?: it when you)? )?(?:a |any |your |to |the )?$")


def said_how(text, model=True):
    """The way they ask to be met, said as how they are in words ASKS doesn't know; or None. The rules first; where they
    find nothing, a small model that is believed only when it's sure and the sentence has the plain shape (hows.py)."""
    how = said_how_by_rule(text)
    if how or not model:
        return how
    try:
        from . import hows
        return hows.by_model(text)
    except Exception:
        return None   # no numpy, or a damaged file: the rules stand alone


def said_how_by_rule(text):
    """The rules alone."""
    said = " ".join(str(text or "").split())
    if not said or len(said) > 240 or "?" in said or not (WHEN_LOW.search(said) or STANDING.search(said)) or not AIMED.search(said) or SOMEONE_ELSE.search(said):
        return None
    found = {}
    for style, pattern in MORE.items():
        m = pattern.search(said)
        if m and not (style != "listen" and re.search(UNWANTED, said[:m.start()], re.I)):
            found[style] = m
    if "distract" in found and not WHEN_LOW.search(said) and re.match(r"(?:something|anything|somewhere)\b", found["distract"].group(0), re.I):
        found.pop("distract")       # "I'd rather have pasta than something else": no hard time named, and nothing but "something else"
    if "advice" in found and re.match(r"don'?t just", found["advice"].group(0), re.I):
        found.pop("listen", None)   # "don't just listen, tell me what you think" asks for a take
    if "listen" in found and re.search(r"(?:don'?t|do not|dont|never|not)\s+(?:need |want |have )?(?:you )?(?:to )?(?:just )?$", said[:found["listen"].start()], re.I) \
            and not re.match(r"(?:no|not|don'?t|do not|dont|without|instead of)\b", found["listen"].group(0), re.I):
        found.pop("listen")         # "I don't need you to listen": the opposite
    if not found:
        return None
    if "listen" in found and len(found) > 1 and re.match(r"(?:no|not|don'?t|do not|dont|without|instead of)\b", found["listen"].group(0), re.I):
        # "I'd rather be distracted, not given advice": what they do want outranks what they don't
        found.pop("listen")
    return min(found, key=lambda style: found[style].start())


# Being listened to is the safe way to be met, so once is enough. The others have to be asked for on two occasions (or said
# as how they are): "be real with me, should I go to the wedding?" asks for a take on one thing, and says nothing about
# how to comfort them a month from now.
NEEDS = {"listen": 1, "advice": 2, "distract": 2, "laugh": 2}
OCCASION = 3600              # asks within the same hour are one occasion
# Luma's reply gave advice; then they said it wasn't what they needed.
ADVISED = re.compile(r"\b(?:you should|you could try|have you (?:tried|thought about|considered)|maybe (?:try|you could|consider)|why don'?t you|"
                     r"my advice|i'?d (?:suggest|recommend|try)|one thing (?:that|you) (?:might|could)|try (?:to |and )?(?:talking|taking|making|setting|writing|going))\b", re.I)
PUSHBACK = re.compile(r"\b(?:that'?s not (?:helping|helpful|what i (?:need|asked|meant|want))|not helpful|i didn'?t ask(?: for (?:advice|that|your opinion))?|"
                      r"you'?re not listening|stop (?:it|that)|i know (?:that|all that) already|easy for you to say|you sound like (?:a|my) (?:therapist|mom|mother|dad))\b", re.I)
# A subject they closed. The thing itself has to be named ("my dad", "the divorce"): "I don't want to talk about it" closes
# this moment, not a subject, and isn't kept.
CLOSED = re.compile(
    r"(?i:\b(?:i (?:really |just )?(?:don'?t|do not|dont) (?:want|wanna|like) to (?:talk|think|hear) about|i'?d rather not (?:talk|think) about|"
    r"can we (?:please |just )?not (?:talk about|bring up|get into|do)|let'?s not (?:talk about|get into|bring up)|"
    r"(?:please |pls )?(?:don'?t|do not|stop|quit) (?:bring(?:ing)? up|ask(?:ing)? (?:me )?about|mention(?:ing)?|talk(?:ing)? about)|"
    # "never bring up my ex again", "please never mention her": only where the sentence starts, so "I never mention my ex" isn't it (Nov 26)
    r"(?<![\w'] )(?:please |pls )?never (?:bring(?:ing)? up|ask(?:ing)? (?:me )?about|mention(?:ing)?|talk(?:ing)? about)))\s+"
    r"(?P<what>(?i:my|the|our|his|her|that whole|this whole)\s+[A-Za-z][A-Za-z' -]{1,38}?|[A-Z][a-z]+)"
    r"(?i:(?=$|[.,!;?]|\s+(?:again|anymore|any more|right now|today|tonight|please|ok|okay|ever|at all|with you|for now|yet|and|but|because|cause|it'?s)\b))")
NOT_A_SUBJECT = {"it", "that", "this", "things", "stuff", "anything", "everything", "the thing", "that thing", "my day", "my feelings", "the weather"}
STOP = {"my", "the", "our", "his", "her", "that", "this", "whole", "thing", "stuff", "a", "an", "and", "of", "with", "about"}
# "laugh" is never for these: being with them comes first (luma.agent.feelings families)
TOO_HEAVY_TO_JOKE = {"grief", "heartbreak", "fear", "shame", "missing"}

LINES = {
    "listen": "How to be with them: when they're hurting, they've asked you to listen, not fix it (they said: “{said}”). Stay with what "
              "they told you and take their side. No advice and no fixes unless they ask for one.",
    "advice": "How to be with them: when something's wrong, they've asked you to be straight and help them think (they said: “{said}”). "
              "One line that you're with them, then one honest, useful thought. Not a list.",
    "distract": "How to be with them: when they're low, they've asked you to take their mind off it (they said: “{said}”). One line that "
                "you're with them, then offer to talk about something else and let them pick.",
    "laugh": "How to be with them: when they're down, they've asked you to make them laugh (they said: “{said}”). One warm line first; "
             "then a light touch is welcome. Never joke about the thing that hurts.",
}
# When Luma can't tell whether this is a hard moment. Forty hard evenings told as plain events ("my boss chewed me out
# over something that wasn't even mine") were written by hand on Nov 20, 2026: Luma's reader of feelings took 9 of them for
# a hard moment. First try: give the brain the line above with an "if" and let it decide. Run 58 (four real brains, 36
# conversations twice, beside the commit before): no difference on any brain. Told or not, a brain offered to change the
# subject on 3 to 6 of 24 hard evenings; the ones that passed were the ones where Luma added the offer itself (owed).
# So the "if" line is gone, and Luma asks the brain one plain question instead (HARD_PROMPT) and adds the line itself on
# a YES. Only for "take my mind off it": it's the one way of being met that code can see in a reply.
HARD_NO = ["I made a really good soup tonight", "my cousin is coming to stay next month", "I finally fixed the squeaky door", "I got the promotion!!",
           "I watched two episodes of that baking show", "I walked to the park and back before work"]
HARD_YES = ["my flight got cancelled and I missed the wedding", "I got yelled at in front of the whole office", "they turned down my application again",
            "someone hit my parked car and drove off", "I studied all month and still failed", "my landlord is making us move out by friday"]


def hard_prompt(said):
    """The one plain question: did something go wrong for them? YES or NO only."""
    shown = lambda lines: " / ".join(f'"{line}"' for line in lines)  # noqa: E731
    return ("Someone is telling you about their day. Did something go wrong for them, or is it bad or upsetting news for them? Good news, "
            "plans, and ordinary things they did don't count.\n"
            f"NO: {shown(HARD_NO)}\nYES: {shown(HARD_YES)}\n"
            f'They just said: "{str(said)[:300]}"\nAnswer with one word: YES or NO.')


def fine_prompt(said):
    """The same question asked the other way round, for a brain that says YES to nearly anything (run 59: on ordinary
    evenings the 1.7B said something went wrong 11 times in 24, Luma's own small one 17). A small brain's YES is believed
    only when it also says NO to this."""
    shown = lambda lines: " / ".join(f'"{line}"' for line in lines)  # noqa: E731
    return ("Someone is telling you about their day. Is it good news, a plan, or an ordinary thing they did, with nothing gone wrong for "
            "them? Something that went wrong, or bad or upsetting news for them, doesn't count.\n"
            f"YES: {shown(HARD_NO)}\nNO: {shown(HARD_YES)}\n"
            f'They just said: "{str(said)[:300]}"\nAnswer with one word: YES or NO.')


# Said as how they are, in words neither the rules nor the small model know (the honest number, Nov 20: 4 of 24 heard).
# A bigger brain is asked, one plain YES/NO question for each way of being met, and believed only when it says YES to
# exactly one. Only on a sentence with the plain shape of a wish (hows.has_shape); never a small brain (run 59).
WISH = {
    "listen": "to listen and be there with them, without advice and without fixing it",
    "advice": "to help them sort it out: say what you think, give advice or a plan",
    "distract": "to take their mind off it: change the subject, talk about something else",
    "laugh": "to make them laugh: joke with them, be silly, say something funny",
}
WISH_YES = {
    "listen": ["when I'm having a hard time I mostly want someone to sit in it with me", "if I'm in a bad place, no fixing, only company",
               "on my worst days an ear is all I'm after"],
    "advice": ["when I'm in a bad spot, be blunt and say what you'd do", "if things fall apart for me, I want a plan from you, not sympathy",
               "whenever I'm struggling, point me at the next step"],
    "distract": ["when I'm in a funk, get me thinking about anything else", "if I've had a horrible day, steer us somewhere else entirely",
                 "whenever I'm low, a different topic helps me more than going over it"],
    "laugh": ["when I'm miserable, be goofy with me", "if I'm having a rotten day, I want your worst puns",
              "whenever I'm blue, getting me to crack up is the cure"],
}
WISH_NO = ["when I'm stressed I bake bread until two in the morning", "when I'm upset my sister always tells me to calm down",
           "whenever I'm down I end up scrolling on my phone for hours", "if tomorrow is another bad day I'm handing in my notice"]


def wish_prompt(said, style):
    """One plain question about one way of being met: are they asking for this, as a standing thing? YES or NO only."""
    shown = lambda lines: " / ".join(f'"{line}"' for line in lines)  # noqa: E731
    others = [WISH_YES[other][0] for other in STYLES if other != style]
    return ("Someone is telling you something about themselves. Are they asking you, as a standing thing for whenever they're having a hard "
            f"time, {WISH[style]}? It's a NO if it's what they do themselves, what someone else does, about one day only, or if what they "
            "ask of you is something different.\n"
            f"YES: {shown(WISH_YES[style])}\nNO: {shown(WISH_NO[:2] + others[:2] + WISH_NO[2:] + others[2:])}\n"
            f'They said: "{str(said)[:300]}"\nAnswer with one word: YES or NO.')


def asks_of_you_prompt(said):
    """Asked before any of the four (run 61: without it a stock 4B took 6 of 55 near misses for a wish, and Luma's own 4B
    took 5 and heard nothing): is anything being asked of you at all? YES or NO only."""
    shown = lambda lines: " / ".join(f'"{line}"' for line in lines)  # noqa: E731
    return ("Someone is telling you something about themselves. Are they telling you what they would like YOU to do for them whenever "
            "they're having a hard time? It's a NO if they're describing what they do themselves, what someone else does or wants, "
            "how they feel, or one particular day; it's a NO if nothing is asked of you.\n"
            f"YES: {shown([WISH_YES[style][1] for style in STYLES])}\nNO: {shown(WISH_NO + ASKS_NOTHING)}\n"
            f'They said: "{str(said)[:300]}"\nAnswer with one word: YES or NO.')


ASKS_NOTHING = ["when I'm having a rough week I barely sleep", "if I'm low my mom can always tell", "whenever I get sad I just want to be alone",
                "on bad days everything feels like too much"]


# What a brain heard is never kept on the brain's word (run 62: a stock 4B still made up 1 wish in 55 near misses, Luma's
# own 4B 2). Luma says back what it understood and keeps it only on a yes.
CHECK = {"listen": "you'd like me to just listen", "advice": "you'd like me to help you sort it out",
         "distract": "you'd like me to take your mind off it", "laugh": "you'd like me to make you laugh"}
SAID_YES = re.compile(r"^\W*(?:yes|yeah|yep|yup|ya|right|exactly|correct|that'?s right|that'?s it|you got it|please|mhm|mm-?hm|uh huh|sure|totally|"
                      r"100%|for sure|pretty much|basically)\b", re.I)
SAID_NO = re.compile(r"^\W*(?:no|nope|nah|not really|not exactly|not quite|wrong|that'?s not)\b", re.I)


def check_line(style):
    return f"Just so I've got it: when things are hard, {CHECK[style]}. Is that right?"


def might_be_a_wish(text):
    """Worth asking a bigger brain: the sentence has the plain shape of a wish, and nothing Luma has heard which."""
    said = " ".join(str(text or "").split())
    if said_how(said) or any(p.search(said) for p in ASKS.values()) or CLOSED.search(said):
        return False
    try:
        from . import hows
        return bool(hows.has_shape(said))
    except Exception:
        return False


THEIRS = re.compile(r"\b(?:i|i'?m|im|i'?ve|ive|i'?d|my|me|we|we'?re|our)\b", re.I)
NOT_TELLING = re.compile(r"\?|^\W*(?:(?:hey|yo|ok|okay|luma|so|and|also|oh|please|pls)\W+)*(?:what|how|where|when|which|who|whose|why|can|could|would|will|"
                         r"should|shall|do|does|did|is|are|am|was|were|set|play|remind|turn|add|open|show|search|find|text|email|call|tell|give|make|"
                         r"help|look|check|put|start|stop|pause|read|write|order|book|buy|send|save|remember|forget|let'?s|thanks|thank you|good (?:morning|night))\b", re.I)


def telling(text, theirs=True, laughing=False):
    """They're telling Luma something about their life: not asking, not giving it something to do, not laughing.
    theirs=False: with no "I" or "my" in it either ("the store wouldn't take the return even with the receipt").
    laughing=True: said with a laugh as well ("lol i totaled my car"), as long as there's a sentence beside the laugh."""
    from . import feelings
    said = " ".join(str(text or "").split())
    if laughing and feelings.LAUGHING.search(said):
        said = " ".join(feelings.LAUGHING.sub(" ", said).split())
        return bool(4 <= len(said.split()) <= 60 and not NOT_TELLING.search(said))
    return bool(6 <= len(said.split()) <= 60 and (THEIRS.search(said) or not theirs) and not NOT_TELLING.search(said)
                and not feelings.LAUGHING.search(said))


RAISED = ("They once asked you not to bring up {topic}. They've raised it themselves now: follow their lead, gently. Don't dig, and "
          "don't remind them they said that.")


def _quote(text, n=90):
    said = " ".join(str(text or "").split()).strip(" .!")
    return said if len(said) <= n else said[:n - 1].rsplit(" ", 1)[0] + "…"


def _keys(topic):
    return [w for w in re.findall(r"[a-z0-9']+", str(topic).lower()) if w not in STOP and len(w) > 1]


def empty():
    return {"comfort": {}, "easy": []}


def _clean(profile):
    profile = profile if isinstance(profile, dict) else {}
    comfort = profile.get("comfort") if isinstance(profile.get("comfort"), dict) else {}
    return {"comfort": {k: [e for e in comfort.get(k, []) if isinstance(e, dict) and e.get("said")] for k in STYLES if comfort.get(k)},
            "easy": [e for e in profile.get("easy", []) if isinstance(e, dict) and e.get("topic")] if isinstance(profile.get("easy"), list) else []}


def learn(profile, text, hurting=False, last_reply="", now=0.0, heard=None):
    """The profile after one thing they said, or None when it taught nothing. hurting: this message or the ones just
    before it were a hard moment (luma.agent.feelings). last_reply: what Luma said just before. heard: the way a bigger
    brain said they asked to be met, when the rules and the small model heard nothing (wish_prompt)."""
    said = " ".join(str(text or "").split())
    if not said or len(said) > 600:
        return None
    profile = _clean(profile)
    changed = False

    def add(style, always=False):
        nonlocal changed
        rows = profile["comfort"].setdefault(style, [])
        if any(r["said"].lower() == _quote(said).lower() for r in rows):
            return
        rows.append({"said": _quote(said), "at": float(now), **({"always": True} if always or GENERAL.search(said) else {})})
        del rows[:-KEEP]
        changed = True

    how = said_how(said) or (heard if heard in STYLES else None)
    for style, pattern in ASKS.items():
        m = pattern.search(said)
        if not m or THEIR_WAY.search(said[:m.start()]) or (style == "listen" and re.search(r"(?:don'?t|do not|dont|never)\s+$", said[:m.start()], re.I)
                                                             and m.group(0).lower().startswith("just")):
            continue  # "when my mom is upset she wants me to just listen" is her way; "don't just listen" asks for more than listening
        # "when I'm down, make me laugh", said on a calm day, is how they are: it counts without a hard moment
        if style == "listen" or hurting or (GENERAL.search(said) and how == style):
            # "when I've had a bad day, talk about something else" reads as a hard moment itself; said as how they are, it's
            # a standing wish all the same, and counts like one (run 59: it didn't, on every brain)
            add(style, always=(how == style))
    if how and not changed:
        add(how, always=True)   # said as how they are, in words the patterns above don't know
    if last_reply and ADVISED.search(str(last_reply)) and PUSHBACK.search(said):
        add("listen")
    closed = CLOSED.search(said)
    if closed:
        topic = " ".join(closed["what"].split()).strip(" .,'")
        topic = re.sub(r"^(?:that|this) whole\s+", "the ", topic, flags=re.I)
        if topic.lower() not in NOT_A_SUBJECT and _keys(topic):
            same = [e for e in profile["easy"] if set(_keys(e["topic"])) == set(_keys(topic))]
            if same:
                same[0]["at"] = float(now)
            else:
                profile["easy"].append({"topic": topic, "said": _quote(said), "at": float(now)})
                del profile["easy"][:-EASY_KEEP]
            changed = True
    return profile if changed else None


def comfort(profile, now=0.0):
    """(style, their words) for how they've asked to be met when they're hurting, or None. The style with the most
    evidence that still counts; between equals, the one said most recently."""
    profile = _clean(profile)
    best = None
    for style in STYLES:
        rows = [r for r in profile["comfort"].get(style, []) if not now or now - float(r.get("at") or 0) <= FADES]
        occasions = len({int(float(r.get("at") or 0) // OCCASION) for r in rows}) + sum(1 for r in rows if r.get("always"))
        if rows and occasions >= NEEDS[style]:
            newest = max(rows, key=lambda r: r.get("at") or 0)
            rank = (occasions, newest.get("at") or 0)
            if best is None or rank > best[0]:
                best = (rank, style, newest["said"])
    return (best[1], best[2]) if best else None


def closed(profile, text, now=0.0):
    """The subject they once closed that this text touches, or ""."""
    low = str(text or "").lower()
    for row in _clean(profile)["easy"]:
        if now and now - float(row.get("at") or 0) > FADES:
            continue
        keys = _keys(row["topic"])
        if keys and all(re.search(rf"\b{re.escape(k)}(?:'s|s|es)?\b", low) for k in keys):  # whole words: "my ex" isn't "my exam"
            return row["topic"]
    return ""


def hard(felt):
    """A feeling that isn't a good one (luma.agent.feelings): hurting, low, fed up."""
    from luma.agent import feelings
    return bool(felt) and felt.get("family") not in feelings.GOOD


def note(profile, text, felt=None, now=0.0):
    """The line for the brain on this turn, or "". felt: luma.agent.feelings.read(text)."""
    if not profile:
        return ""
    said = str(text or "")
    out = []
    topic = closed(profile, said, now)
    if topic and not CLOSED.search(said):
        out.append(RAISED.format(topic=topic))
    # any hard feeling, heavy or not: someone who said "I just need to vent" means it most when they're venting about a
    # parking ticket. Asking for something now beats what they asked before.
    if hard(felt) and not any(p.search(said) for p in ASKS.values()):
        how = comfort(profile, now)
        if how and not (how[0] == "laugh" and (felt.get("family") in TOO_HEAVY_TO_JOKE or (felt.get("strength") or 0) >= 3)):
            out.append(LINES[how[0]].format(said=how[1]))
    return " ".join(out)


# Taking their mind off it is the one way of being met that code can see in a reply: an offer was made, or it wasn't.
# (Month test on real brains, run 50: told "offer to talk about something else and let them pick", four brains stayed
# with the feeling in 13 of 18 replies. Good advice and a good laugh are a judge's call, so nothing is added for those.)
OFFERED_ELSE = re.compile(r"\b(?:something else|anything else|mind off|distract\w*|change the subject|something (?:lighter|fun|silly|different|totally different|"
                          r"completely different|good)|think about something|talk about something|a (?:story|game|joke|movie|show))\b", re.I)
OFFER = "Want me to take your mind off it for a bit? Pick anything."
OFFER_EVERY = 1800   # once in a conversation, not after every line of it


def might_owe(profile, text, felt, reply, now=0.0, last=0.0):
    """Everything owed() asks for, except that no feeling was read: they asked to have their mind taken off it, they're
    telling Luma about their day, and the reply made no offer. Whether it was a hard moment is then the brain's to say
    (hard_prompt); on a YES, Luma adds OFFER."""
    said, reply = str(text or ""), str(reply or "")
    if not profile or felt or not reply.strip() or not telling(said) or any(p.search(said) for p in ASKS.values()) or said_how(said):
        return False
    how = comfort(profile, now)
    if not how or how[0] != "distract" or OFFERED_ELSE.search(reply) or (last and now - last < OFFER_EVERY):
        return False
    return not re.search(r"\b988\b|are you safe", reply, re.I)


def owed(profile, text, felt, reply, now=0.0, last=0.0):
    """The one line Luma adds itself when they've asked to have their mind taken off it and the reply didn't offer to; or "".
    Never on a loss or a broken heart, never at its worst, never when they're asking for something else right now, never
    next to a safety question, never twice in half an hour. last: when it was last added."""
    said, reply = str(text or ""), str(reply or "")
    if not profile or not reply.strip() or not hard(felt) or any(p.search(said) for p in ASKS.values()):
        return ""
    how = comfort(profile, now)
    if not how or how[0] != "distract" or felt.get("family") in ("grief", "heartbreak") or (felt.get("strength") or 0) >= 3:
        return ""
    if OFFERED_ELSE.search(reply) or re.search(r"\b988\b|ending your life|are you safe", reply, re.I) or (last and now - last < OFFER_EVERY):
        return ""
    return OFFER


def forget(profile, matches):
    """The profile without any evidence whose words match (the same test "forget about ..." uses on memories), and
    how many pieces went."""
    profile = _clean(profile)
    gone = 0
    for style in list(profile["comfort"]):
        keep = [r for r in profile["comfort"][style] if not matches(r["said"])]
        gone += len(profile["comfort"][style]) - len(keep)
        if keep:
            profile["comfort"][style] = keep
        else:
            del profile["comfort"][style]
    keep = [e for e in profile["easy"] if not (matches(e["topic"]) or matches(e.get("said", "")))]
    gone += len(profile["easy"]) - len(keep)
    profile["easy"] = keep
    return profile, gone


WORDS = {"listen": "When you're hurting, you want me to listen, not fix it.",
         "advice": "When something's wrong, you want me to be straight and help you think.",
         "distract": "When you're low, you want me to take your mind off it.",
         "laugh": "When you're down, you want me to make you laugh."}


def view(profile, now=0.0):
    """What the app shows under "How to be with me": each line in plain words, with their own words as the reason, and
    a key to forget it by."""
    profile = _clean(profile)
    rows = []
    how = comfort(profile, now)
    for style in STYLES:
        evidence = [r for r in profile["comfort"].get(style) or [] if not now or now - float(r.get("at") or 0) <= FADES]
        occasions = len({int(float(r.get("at") or 0) // OCCASION) for r in evidence}) + sum(1 for r in evidence if r.get("always"))
        if evidence and occasions >= NEEDS[style]:  # only what Luma actually goes by
            rows.append({"key": "comfort:" + style, "kind": "comfort", "text": WORDS[style], "leading": bool(how and how[0] == style),
                         "because": [{"said": r["said"], "at": r.get("at")} for r in evidence[-3:]]})
    for i, row in enumerate(profile["easy"]):
        rows.append({"key": "easy:" + str(i), "kind": "easy", "text": f"I don't bring up {row['topic']} unless you do.",
                     "because": [{"said": row.get("said") or "", "at": row.get("at")}]})
    return rows


def drop(profile, key):
    """The profile without one line from view()."""
    profile = _clean(profile)
    kind, _, which = str(key).partition(":")
    if kind == "comfort":
        profile["comfort"].pop(which, None)
    elif kind == "easy" and which.isdigit() and int(which) < len(profile["easy"]):
        del profile["easy"][int(which)]
    return profile
