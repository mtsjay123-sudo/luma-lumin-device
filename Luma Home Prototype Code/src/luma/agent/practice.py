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
    r"^\W*(?:ok(?:ay)?\W+|so\W+)?(?:is|was) (?:this|that)(?: one)? (?:actually )?funny(?: or\b|\W*$|\s*:)|"
    rf"\bdoes (?:this|that|it|the|my) (?:{MATERIAL} )?(?:land|work|hit)\b|\bwhich of (?:these|the) [^.?!]{{0,12}}punchlines?\b|"
    rf"\b(?:{ASK})\b[^.?!]{{0,25}}\b(?:be|get|being) (?:funn(?:y|ier)|better at (?:being funny|jokes|telling (?:jokes|stories)))\b|"
    r"\bhow (?:do|can|could) i (?:be|get|become) funn(?:y|ier)\b|\bhow to be funn(?:y|ier)\b|"
    rf"\b(?:{ASK})\b[^.?!]{{0,30}}\b(?:tell a (?:story|joke)|my {MATERIAL}|make people laugh)\b|"
    rf"\bhow (?:do|can) i make my {MATERIAL}\b|\bmy jokes never (?:hit|land|work)\b|\bwrote a (?:bit|joke|set)\b[^.?!]{{0,40}}\b(?:by|on|past) (?:you|u)\b",
    re.I)
SAY = re.compile(
    rf"\b(?:{ASK})\b[^.?!]{{0,20}}\b{PRACTISE}\b[^.?!]{{0,6}}\b(?:my|what i|what to|how to|how i|telling|saying|asking|quitting|breaking|coming out|ordering|"
    r"the (?:speech|toast|talk|pitch|presentation|apology|conversation|interview))\b|"
    rf"\b{PRACTISE}\b[^.?!]{{0,60}}\b(?:on|with) (?:you|u)\b(?!r)|"
    r"\bmock interview\b|"
    r"\brun (?:my|this|the) [^.?!]{0,25}\b(?:by|past) (?:you|u)\b|\brun through (?:my|the|this) [^.?!]{0,30}\bwith (?:you|u)\b|"
    r"\bsay it to (?:you|u) first\b|\bask me (?:some |the )?(?:interview )?questions\b", re.I)
TALK = re.compile(
    rf"\b(?:{ASK})\b[^.?!]{{0,45}}\b(?:small talk|talking (?:to|with) (?:people|strangers|girls|guys|women|men|anyone)|chatting|flirting|"
    r"introducing myself|(?:keep|start|hold|have) a conversation|conversations?|less awkward|comfortable (?:talking|around people))\b|"
    rf"\b(?:freeze|clam|lock) up\b[^.?!]{{0,40}}\b(?:{PRACTISE})\b|\bget better at talking\b", re.I)

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
    return NOTES.get(asks(text), "")
