"""Somewhere to practise being themselves: a joke before it's told, a hard thing before it's said, talking before a room.

The owner, Nov 21, 2026: not everybody needs another person, and Luma can train them: to be funny, to use their personality
the same way in real life, to know which jokes would land and which wouldn't. This reads the ways someone asks for that and
tells the brain how to be a practice partner: honest about what landed and what didn't, one better version, then again.

Only when they ask. Luma never suggests practising for other people; that would be the nudge the owner took out the same day.
Never in kids mode, and never of anyone who's hurting or might not be safe: then they're owed something else first."""
import re

ASK = r"(?:can|could|may|will|would) (?:i|we|you|u)|help me|let me|lemme|let'?s|i (?:need|want|have|would like|'d like) to|i'?m trying to|teach me|coach me|show me"
MATERIAL = r"(?:jokes?|bits?|puns?|punchlines?|one-?liners?|material|set|roast|comebacks?|openers?|delivery)"
PRACTISE = r"(?:practi[cs]e|practi[cs]ing|rehears(?:e|ing)|run through|go over|work on|try out|workshop)"

JOKE = re.compile(
    rf"\b(?:try|test|run|bounce|workshop|practi[cs]e)\b[^.?!]{{0,30}}\b{MATERIAL}\b[^.?!]{{0,30}}\b(?:on|by|past|with|off) (?:you|u)\b|"
    rf"\b(?:rate|grade|judge|score|critique|fix|punch up)\b[^.?!]{{0,12}}\b(?:my|this|these|the) [^.?!]{{0,12}}{MATERIAL}\b|"
    r"\b(?:tell me|be honest|honestly)\b[^.?!]{0,20}\b(?:if|whether|was|is) (?:this|that|it)(?: one)?(?: is| was)? (?:actually )?funny\b|"
    r"^\W*(?:ok(?:ay)?\W+|so\W+)?(?:is|was) (?:this|that)(?: one)? (?:actually )?funny(?: or\b|\W*$|\s*:| (?:for|at|in) [^.?!:]{2,40}:)|"
    rf"\bdoes (?:this|that|it|the|my) (?:{MATERIAL} )?(?:land|work|hit)\b|\bwhich of (?:these|the) [^.?!]{{0,12}}punchlines?\b|"
    rf"\b(?:{ASK})\b[^.?!]{{0,25}}\b(?:be|get|being) (?:funn(?:y|ier)|better at (?:being funny|jokes|telling (?:jokes|stories)))\b|"
    r"\bhow (?:do|can|could) i (?:be|get|become) funn(?:y|ier)\b|\bhow to be funn(?:y|ier)\b|"
    r"\bworkshop (?:this|that|my|a|an|some)\b[^.?!]{0,20}\bwith me\b|"
    r"\brate (?:this|that|it)(?: one)?\s*:|\b(?:tell me|be honest|honestly)\b[^.?!]{0,20}\b(?:if|whether) it'?s (?:actually )?funny\b|"
    rf"\b(?:can|could|may) i (?:try|test|run) (?:a|an|my|this|one|some) {MATERIAL}\b|"
    r"\bis (?:this|that|it)(?: joke| one| line)? (?:ok|okay|fine|too much|too mean|too dark|appropriate)(?: to say| for)\b|"
    rf"\b(?:{ASK})\b[^.?!]{{0,30}}\b(?:tell a (?:story|joke)|my {MATERIAL}|make people laugh)\b|"
    rf"\bhow (?:do|can) i make my {MATERIAL}\b|\bmy jokes never (?:hit|land|work)\b|\bwrote a (?:bit|joke|set)\b[^.?!]{{0,40}}\b(?:by|on|past) (?:you|u)\b",
    re.I)
SAY = re.compile(
    rf"\b(?:{ASK})\b[^.?!]{{0,20}}\b{PRACTISE}\b[^.?!]{{0,6}}\b(?:my|what i|what to|how to|how i|telling|saying|asking|quitting|breaking|coming out|ordering|setting (?:a |some )?boundar\w+|standing up|turning down|"
    r"the (?:speech|toast|talk|pitch|presentation|apology|conversation|interview))\b|"
    rf"\b{PRACTISE}\b[^.?!]{{0,60}}\b(?:on|with) (?:you|u)\b(?!r)|"
    r"\bmock interview\b|"
    r"\brun (?:my|this|the) [^.?!]{0,25}\b(?:by|past) (?:you|u)\b|\brun through (?:my|the|this) [^.?!]{0,30}\bwith (?:you|u)\b|"
    r"\bsay it to (?:you|u) first\b|\bask me (?:some |the )?(?:interview )?questions\b", re.I)
SOCIAL = (r"(?:making friends|meeting (?:people|new people|someone|strangers|[a-z']+ (?:parents|family|friends))|phone calls?|talking|calling|small talk|"
          r"conversations?|chatting|flirting|dating|dates?|socializ\w+|networking|mingling|how to talk|introductions?)")
TALK = re.compile(
    rf"\b(?:{ASK})\b[^.?!]{{0,45}}\b(?:small talk|talking (?:to|with) (?:people|strangers|girls|guys|women|men|anyone)|chatting|flirting|"
    r"introducing myself|(?:keep|start|hold|have) a conversation|conversations?|less awkward|comfortable (?:talking|around people))\b|"
    rf"\b(?:freeze|clam|lock) up\b[^.?!]{{0,40}}\b(?:{PRACTISE})\b|\bget better at talking\b|"
    # "help me practice making friends at the gym", "can you help me practice phone calls", "i need practice talking to my coworkers"
    rf"\b(?:{ASK}|i need)\b[^.?!]{{0,30}}\b(?:{PRACTISE}|practice)\b[^.?!]{{0,12}}\b{SOCIAL}\b|"
    # "i want to be better at talking on dates", "teach me to be less awkward on the phone"
    rf"\b(?:{ASK})\b[^.?!]{{0,20}}\b(?:be|get|being|getting|feel) (?:better|good|less awkward|less shy|less nervous|more comfortable|more confident|braver) "
    rf"(?:at|with|on|about|around|when|in)\b[^.?!]{{0,25}}\b(?:{SOCIAL}|people|friends|strangers|parties|the phone)\b", re.I)

# Playing a part. "pretend you're the interviewer and ask me questions" is practice; "pretend you're a real person" and "pretend
# you're my girlfriend" are not (rules 1 and 3 answer those). It counts only with a part from everyday errands and work, or with
# words that say what the playing is for.
PLAY = re.compile(r"\brole ?-?play\b|\b(?:pretend|act like|act as if) (?:you'?re|you are|u r|to be|the)\b|\b(?:play|be) (?:my|the|a) [a-z]+\b|"
                  r"\byou be (?:my|the|a) [a-z]+\b", re.I)
PART = re.compile(r"\b(?:interviewer|boss|manager|landlord|customer|client|teacher|professor|waiter|waitress|cashier|doctor|officer|recruiter|"
                  r"coworker|neighbou?r|roommate|audience|judge|hiring manager)\b", re.I)
WHAT_FOR = re.compile(rf"\b(?:{PRACTISE}|so i can|ask me|interview|let me try|i'?ll (?:say|ask|tell|try)|and i(?:'ll| will) (?:say|ask|tell))\b", re.I)

NOTES = {
    "joke": ("They want to get funnier and they're trying it on you. Be an honest practice partner: say what landed and what didn't, and why, in a "
             "sentence; offer one sharper version; then ask for the next one. Laugh if it's funny. Never flatter and never lecture."),
    "say": ("They want to practise saying something to someone. Play it with them: have them say it to you, tell them honestly how it would land, "
            "offer one better way to put the hardest line, then run it again. Keep it in their words, not yours."),
    "talk": ("They want to get better at talking with people. Be somewhere to practise: trade a few lines as if it's real, then say one thing they "
             "did well and one thing to try. Keep it light; never a lesson."),
}

# Two things run 81 showed a 4B doesn't do unasked. A joke about someone in their life (their body, looks, brains, money): asked
# "does this joke land: my coworker tina's so big ...", it wrote a sharper one about Tina. And a joke they'll say in front of
# people: asked to rate a wedding toast that gives the marriage two years, "that's actually kinda gold ... perfect for a toast".
# An honest friend says who it would hurt and how it lands in that room. Luma never writes the sharper dig (rule 3: never a
# word against the people in their life).
EXPENSE = ("They're trying a joke on you, and it's at the expense of a real person in their life. Be honest and kind about it: say it would sting, "
           "and who it would hurt if it got back to them. Don't sharpen it or add to it. If there's a funny idea in it that isn't about "
           "that person, offer that. No lecture.")
ROOM = ("They're trying a joke on you and they said where they'll say it. Be honest about how it lands in that room, with those people "
        "listening, and who it's about. If it works there, say so; if it would sting, say that and offer one version that wouldn't. Never "
        "flatter, never lecture.")
# What Luma says itself when a brain sharpened the dig twice.
EXPENSE_LINE = "Honest take: that one's at their expense, and it would sting if it got back to them. I'd leave it out. Got one that isn't about a person?"

# A joke for a room that would hurt someone in it. Run 83: told the ROOM note, the stock 4B still called a wedding toast that
# gives the marriage two years "actually kinda gold". No list knows every room and every dig, and the brain does better with
# one plain question than with a note (the same was true of gripes and of what divides people). So before the reply it's
# asked, YES or NO only, whether the joke would land on someone there (Agent._hurts_the_room; never a small brain, which says
# YES to nearly anything). On a YES it's told so firmly, and a reply that still only praises gets one more try, then Luma's
# own careful line. On a NO, or with nobody to ask, nothing changes.
def room_prompt(joke):
    return ("Someone wants to say this in front of people:\n\"" + " ".join(str(joke or "").split())[:400] + "\"\n"
            "Would it insult, embarrass or hurt someone who will be in that room, or the people the occasion is for? Answer YES or NO only.")


# A side count only (scripts/human_eval.py, the practice side check): can a brain tell a joke that works from one that doesn't
# when it's asked plainly? In its replies the stock 4B said what was wrong with 7 of 12 broken jokes and flattered 4 (runs 81
# and 83). If the plain question separates the two kinds better than that, it's worth asking before the reply, the way the room
# is asked about; if it doesn't, it isn't. Nothing in the chat path asks this.
def works_prompt(joke):
    return ("Someone is trying out a joke:\n\"" + " ".join(str(joke or "").split())[:400] + "\"\n"
            "Does the joke work as written: is there a real punchline that would get a laugh? Answer YES or NO only.")


ROOM_HURTS = ("They're trying a joke on you that they'll say in front of people, and it would land on someone in that room. Say so first, "
              "plainly and kindly: who it hits and why that's the wrong room for it. Then offer one version that keeps the laugh "
              "without the sting. Don't call it great. No lecture.")
ROOM_LINE = ("Honest take: I'd be careful with that one in that room. It could land hard on someone who's there. "
             "Want to work on a version that keeps the laugh without the risk?")

PERSON = (r"\bm(?:y|ah) (?:[a-z]+ )?(?:co-?workers?|colleagues?|boss|manager|supervisor|teacher|professor|landlord|neighbou?r|roommate|friend|bestie|sister|brother|"
          r"mom|mum|mother|dad|father|wife|husband|girlfriend|boyfriend|partner|ex|cousin|uncle|aunt|grandma|grandpa|grandmother|grandfather|in-?laws?|"
          r"son|daughter|kid|nephew|niece|classmate|teammate)\b(?:[ -]in[ -]law)?")
KIND_WORDS = r"(?:proud|kind|sweet|happy|funny|smart|good|nice|excited|cute|lovely|great|generous|patient|talented|brave|strong|cool|helpful|supportive)"
DIG = re.compile(
    r"(?:'s|’s|\bis|\bare|'re) so (?!" + KIND_WORDS + r"\b)[a-z]+\b|"
    r"\bface for radio\b|\blooks? like (?:he|she|they|a|an|something|somebody)\b|\bsmells? like\b|\bso (?:fat|big|ugly|dumb|stupid|bald|old|short|skinny|poor|"
    r"broke|lazy|cheap|greedy|hairy|boring|slow) (?:he|she|they|his|her|their|that|you|even|when)\b", re.I)
WHERE = re.compile(
    r"\b(?:for|at|in|during|open(?:ing)?|giv(?:e|ing)|doing|post(?:ing)?|say(?:ing)? (?:it|this|that) (?:at|in|to)|in front of)\b[^.?!:]{0,45}?"
    r"\b(?:wedding|toast|funeral|eulogy|church|service|meeting|all[- ]hands|office party|work (?:party|thing|event|dinner)|party|speech|presentation|interview|"
    r"class|graduation|thanksgiving|christmas|dinner|group chat|open mic|stand[- ]?up|stage|retirement|reunion|shower|pta|in-?laws|crowd|audience)\b", re.I)


def at_expense(text):
    """The joke is a dig at someone in their life: their body, their looks, their brains, their money."""
    said = " ".join(str(text or "").split())
    return bool(re.search(PERSON, said, re.I) and DIG.search(said))


def where(text):
    """They said where they'll say it: a wedding, a funeral, a meeting, church, the family group chat."""
    return bool(WHERE.search(" ".join(str(text or "").split())))


def joke_note(text, ask=""):
    """What the brain is told about a joke they're trying: who it's about and where it'll be said come first."""
    if at_expense(text):
        return EXPENSE
    if where(text) or where(ask):
        return ROOM
    return None


# What an honest reply to a joke at someone's expense has in it: that it stings, or who it hurts, or that Luma wouldn't tell it.
SAYS_IT_STINGS = re.compile(
    r"\b(?:mean|cruel|unkind|harsh|hurt(?:s|ful|ing)?|sting(?:s)?|at (?:her|his|their|your|\w+'s|someone'?s|a real person'?s) expense|punch(?:ing|es)? down|"
    r"wouldn'?t (?:say|tell|use|open|lead|do)|i'?d (?:skip|drop|lose|leave|cut|think about|know which)|leave (?:it|that one) out|not (?:okay|ok|cool|kind|fair|nice)|"
    r"(?:her|his|their|someone'?s) (?:body|weight|looks|size|face)|how (?:she|he|they) looks?|careful|risky|backfire|g(?:e|o)t back to|"
    r"if (?:she|he|they|\w+) (?:hears?|heard|finds? out|is in the room|were in the room)|behind (?:her|his|their) back|(?:she|he|they)'?d feel|feelings?|"
    r"in on it|laughs? (?:too|at that one)|just puts up with|a real person|rough day)\b", re.I)


def says_it_stings(reply):
    return bool(SAYS_IT_STINGS.search(str(reply or "")))


# What an honest reply to a joke that would hurt the room has in it: that it stings (above), or that this isn't the room for it.
WRONG_ROOM = re.compile(
    r"\b(?:(?:wrong|not the(?: right)?|isn'?t the(?: right)?) (?:room|place|crowd|time|moment|audience|occasion)|awkward|uncomfortable|go(?:es)? quiet|"
    r"(?:a little|real|very|dead) quiet|silence|wince|cringe|offend(?:s|ed|ing)?|insult(?:s|ed|ing)?|embarrass(?:es|ed|ing)?|too (?:much|far|harsh|mean|sharp|pointed)|"
    r"land(?:s|ing)? (?:wrong|badly|hard|on)|won'?t land|might not land|not (?:land|go over|play) well|go over (?:badly|poorly)|think twice|second thoughts|"
    r"soften|tone it down|save it for|save that (?:one )?for|different crowd|another crowd|not everyone|some (?:people|folks|of them)|take it (?:personally|the wrong way)|"
    r"sour|side-?eye|raised? (?:an )?eyebrows?|upset|the couple|the bride|the groom|in front of)\b", re.I)


def says_its_risky(reply):
    """The reply says the joke stings, or that this isn't the room for it."""
    return bool(SAYS_IT_STINGS.search(str(reply or "")) or WRONG_ROOM.search(str(reply or "")))


# They asked, and what they want to try sits close to something that hurts: a joke for their dad's funeral, a line about their
# mom's dementia. It's theirs to tell and they asked for an honest ear; kind first, then what they asked for, gently. (Until
# this, someone hurting got no practice note at all, so a eulogy joke got condolences and nothing about the joke.) Never when
# they might not be safe.
# Runs 81 and 83: asked to workshop "mom met me for the first time again today. apparently i make a great first impression", the
# 4B answered it as news ("Aww, that's sweet"), and once made up something the mother said. So the note says what it is: a joke
# they wrote, to be answered as one, with nothing added that they didn't say.
GENTLE = ("They asked to try this on you, and it's close to something that hurts. It's a joke or a line they wrote, not news: add nothing "
          "about their life they didn't say. Be kind first, in a few words. Then say honestly and gently how it would land and with whom, "
          "and one better way to put it. No lecture.")


# A joke about something that is hard whatever words it's told in. "it's about my mom's dementia: mom met me for the first time
# again today. apparently i make a great first impression" has no feeling word in it, so nothing read it as close to home
# (run 81, the stock 4B: "Aww, that's so sweet ... like a full-circle hug").
CLOSE_TO_HOME = re.compile(
    r"\b(?:dementia|alzheimer'?s|cancer|chemo(?:therapy)?|tumou?r|funeral|eulogy|hospice|miscarriage|stillb(?:orn|irth)|divorced?|rehab|sober|sobriety|relapsed?|"
    r"wheelchair|amput\w+|disabilit(?:y|ies)|diagnos(?:is|ed)|stroke|parkinson'?s|depress(?:ion|ed)|bipolar|ptsd|widow(?:ed|er)?|dialysis|"
    r"(?:my|our) (?:late|dead) \w+|passed away|(?:my|our) (?:mom|mum|mother|dad|father|wife|husband|son|daughter|brother|sister|grandma|grandpa|friend|dog|cat) died)\b", re.I)


def close_to_home(text):
    return bool(CLOSE_TO_HOME.search(" ".join(str(text or "").split())))


# "can you be funnier" and "be funnier" are about Luma's own jokes (humor.dial_request), not theirs.
LUMAS_OWN = re.compile(r"\b(?:can|could|will|would) (?:you|u) (?:please |just |maybe )?(?:be|get|try (?:to be|being)) (?:a (?:bit|little) |more |less )?"
                       r"(?:funn|serious)|^\W*(?:please )?(?:be|get) (?:a (?:bit|little) |more |less )?funn", re.I)


def asks(text):
    """What they're asking to practise with Luma: "joke", "say", "talk", or None."""
    said = " ".join(str(text or "").split())
    if not said or LUMAS_OWN.search(said):
        return None
    if JOKE.search(said):
        return "joke"
    if TALK.search(said):
        return "talk"
    if SAY.search(said) or (PLAY.search(said) and (PART.search(said) or WHAT_FOR.search(said))):
        return "say"
    return None


def note(text):
    """What the brain is told on a turn they ask to practise, or ""."""
    kind = asks(text)
    return (kind == "joke" and joke_note(text)) or NOTES.get(kind, "")


# ---- practice that goes on past the ask --------------------------------------------------------------------------------------
# "can i try a joke on you" / "Go for it." / the joke. The ask and the joke are two messages, and the note used to reach the
# brain only when they came as one (0 of 30 two-message lines). This reads whether they're still in the middle of it: the
# message right after an ask with nothing to practise in it yet, or one that answers Luma asking for the next. It ends when
# they say so, when they change the subject with a marker, and (in runtime.py) when they're hurting or might not be safe.
STOP = re.compile(
    r"^\W*(?:(?:ok(?:ay)?|actually|wait|you know what|nah|ugh|sorry|oh|honestly|on second thought)\W+)*"
    r"(?:never ?mind|nvm|forget (?:it|that)|let'?s (?:stop|not|talk about|do something)|can we stop|that'?s (?:enough|all|it)\b|i'?m (?:done|good|too tired|tired)\b|"
    r"not (?:now|tonight|today)|later\b|anyway\b|btw\b|by the way\b|changing the subject|on another note|unrelated\b|different (?:subject|question|topic)|"
    r"thanks?(?: you)?\W*$|thank you\b|ok(?:ay)?\W*$|cool\W*$|stop\W*$)|"
    r"\b(?:enough (?:practice|jokes|for (?:now|today|tonight))|stop practi[cs]ing|change the subject|talk about something else|done for (?:today|tonight|now))\b|"
    r"\b(?:what'?s the point|this is pointless|i give up|i can'?t do this|i'?m (?:terrible|awful|hopeless|useless|so bad) at)\b|"
    r"\b(?:hang on|hold on|one sec(?:ond)?|just a sec(?:ond)?|gimme a sec(?:ond)?|give me a (?:sec|second|minute|min)|brb|be right back)\b", re.I)
INVITED = re.compile(
    r"\b(?:next one|another(?: one)?|one more|again|go (?:for it|ahead|on)|let'?s hear|let me hear|hit me|i'?m (?:ready|listening|all ears)|lay it on me|"
    r"fire away|your turn|whenever you'?re ready|ready when you are|try (?:it|that|one|me)|say it|start (?:whenever|from)|take your time|do it|please do)\b|"
    r"\bgo\W*$|\?\s*$", re.I)
TO_SOMEONE = re.compile(r"\b(?:you|your|you'?re|you'?ve|u|ur|y'?all)\b|^\W*(?:hey|hi|hello|dear|mom|dad|mama|papa|sir|ma'?am|mr|mrs|ms|dr|buddy|babe|honey)\b", re.I)

STILL = {
    "joke": ("They're trying jokes on you to get funnier, and this is likely the next one. Say what landed and what didn't, and why, in a sentence; "
             "offer one sharper version; ask for the next. Laugh if it's funny. Never flatter, never lecture. If they've changed the subject, go "
             "with them."),
    "say": ("They're practising something they have to say to someone, and this is likely it. Tell them honestly how it would land, and offer "
            "one better way to put the hardest line, in their words. Then run it again if they want. If they've changed the subject, go with "
            "them."),
    "talk": ("They're practising talking with people and you're in the scene with them: answer as the person you're playing and keep it going. "
             "After a few lines, say one thing they did well and one thing to try. Keep it light. If they've changed the subject, go with them."),
}


def bare(ask):
    """An ask with nothing to practise in it yet: the joke, the line, comes next. "rate my joke. my wheelchair has better parking
    than my boss" has the joke in it, after the ask; "my dad died last night. can i try a joke on you" doesn't."""
    said = " ".join(str(ask or "").split())
    if re.search(r"[:\"“”]", said):
        return False
    found = JOKE.search(said) or TALK.search(said) or SAY.search(said) or PLAY.search(said)
    after = said[found.end():] if found else said
    said_after = re.search(r"[.?!]\s+(\S.*)$", after)
    return len(said.split()) <= 24 and not (said_after and len(said_after.group(1).split()) >= 4)


def to_someone(line):
    """A line said to somebody ("i'm sorry i hurt you", "mom, i'm not coming home"): rehearsed, it's the practice, not how they feel."""
    return bool(TO_SOMEONE.search(" ".join(str(line or "").split())))


def still(earlier, last_reply, text):
    """The kind of practice they're still in the middle of ("joke", "say", "talk"), or None. `earlier` is what they said before
    this, most recent last; `last_reply` is what Luma said back."""
    said = " ".join(str(text or "").split())
    if not said or asks(said) or STOP.search(said):
        return None
    earlier = [" ".join(str(m or "").split()) for m in (earlier or [])][-6:]
    if earlier and asks(earlier[-1]) and bare(earlier[-1]):
        return asks(earlier[-1])   # the message right after the ask is what they wanted to try
    if not INVITED.search(str(last_reply or "")):
        return None
    for m in reversed(earlier):
        if STOP.search(m):
            return None
        if asks(m):
            return asks(m)
    return None


# ---- when they say they're ready for people ---------------------------------------------------------------------------------
# The owner, Nov 21: "when the person is ready then eventually luma can suggest". Luma never raises other people itself (rule
# 3). This reads the ways someone says, in their own words, that they want people or one person back, and only then tells the
# brain to help. Being lonely isn't being ready ("nobody texts me anymore"), and neither is leaning on Luma.
WANTS = (r"(?:i (?:really |just |kind of |kinda |think i |do )?(?:want|need|wish|would like|'d like|'d love|would love|hope) to|i'?d like to|i'?m (?:ready|going|gonna|trying|"
         r"hoping|planning) to|i'?m (?:thinking|thinking about|thinking of|considering)|i'?ve been (?:thinking|meaning|wanting)(?: about| of| to)?|"
         r"(?:maybe )?i (?:should|could|might|ought to)|should i|would it be (?:weird|ok|okay|strange|bad) to|how (?:do|can|could|would) (?:i|you|people)(?: even)?|"
         r"where (?:do|can|could) (?:i|people)[^.?!]{0,20}|thinking (?:about|of))")
REACH = (r"(?:make (?:some |new |more |a few )?friends|meet(?:ing)? (?:some |new |more )?(?:people|someone|each other)|start(?:ing)? dating|dat(?:e|ing) again|"
         r"get(?:ting)? back (?:out there|on the apps|into dating|in touch)|put(?:ting)? myself out there|get(?:ting)? out more|stop isolating|"
         r"join(?:ing)? (?:a|the|that|some) \w+|sign(?:ing)? up for [^.?!]{0,30}\bto meet\b|go(?:ing)? to (?:that|the|a) [^.?!]{0,20}\b(?:meetup|group|thing|class|club)\b|"
         r"reach(?:ing)? out|reconnect|patch things up|get(?:ting)? (?:close|closer) to|get(?:ting)? to know|be friends with|"
         r"(?:call|text|message|write to|email|visit|see|invite|have)(?:ing)? (?:my |her\b|him\b|them\b|people over)|find(?:ing)? my people|"
         r"talk to someone|someone to talk to in person)")
READY = re.compile(
    rf"\b{WANTS}\b[^.?!]{{0,30}}\b{REACH}|"
    r"\bi (?:want|need|wish i had|'d like|would like) (?:a |some |more )?(?:friends?|people|someone)\b(?! else)[^.?!]{0,40}\b(?:to|i can|in my life|again|in person|around)\b|"
    r"\bi wish i had (?:someone|a friend|friends|people)\b|\bready (?:for a relationship|to (?:meet|date|put myself))\b|"
    r"\b(?:tired of being|don'?t want to be)(?: this| so)? alone\b[^.?!]{0,40}\b(?:want|change|anymore|any more)\b|"
    r"\b(?:there'?s|there is) (?:a|this|someone)\b[^.?!]{0,40}\bi'?d like to (?:get to know|be friends with|talk to|ask out)\b", re.I)
NOT_READY = re.compile(r"\b(?:don'?t|do not|not ready|never|hate|can'?t stand|no desire|refuse)\b[^.?!]{0,25}\b(?:want|need|ready|to (?:meet|see|date|talk|call|make))\b|"
                       r"\bnot ready\b|\b(?:get|adopt|buy) a (?:cat|dog|pet)\b|\bmove to\b", re.I)
READY_NOTE = ("They're saying they want people in their life, or one person back. That's theirs, and they brought it up: be glad with them, help with "
              "the next small step they choose, and offer to practise it with you first if they'd like. One idea, not a list; no pep talk.")


def ready(text):
    """They say, in their own words, that they want people or one person back."""
    said = " ".join(str(text or "").split())
    if not said or NOT_READY.search(said):
        return False
    if re.match(r"^\W*(?:so |ok |okay )?(?:should|do|would|could|can|shall) i\b", said, re.I) and re.search(r"\bor\b", said, re.I):
        return False   # "should i text him first or wait for him" asks for a pick between two things, and a friend picks
    return bool(READY.search(said))
