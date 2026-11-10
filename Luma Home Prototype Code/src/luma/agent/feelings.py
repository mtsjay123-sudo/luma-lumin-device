"""What they're feeling, read from what they said. The one place Luma reads feeling.

Before this, four parts of Luma each had their own word list: whether a joke is welcome (humor), whether a reply has to
care (friendcheck), how Luma itself feels (mind), and whether to ask how they are tomorrow (presence). A death said softly
("we had to put Max to sleep", "our dog didn't make it") was in none of them, so the brain was told a little humor was
welcome. Now they all ask here.

read(text) gives the feeling as a close friend would name it, or None for plain talk:

    {"family":   grief, heartbreak, fear, shame, hurt, low, lonely, overwhelmed, disappointed,
                 joy, proud, relieved, missing
     "strength": 1 a touch, 2 clearly, 3 a lot
     "about":    who or what, when they said ("their dad", "their cat"), else ""
     "need":     what a friend does first: company, their side, steadying, kindness, cheer, relief
     "heavy":    a moment for no jokes, where the reply has to meet the feeling before anything else
     "why":      a few words for the brain's note}

It's rules, not a brain: it runs in well under a millisecond, the same on a $250 device as on a Mac, and it can be read
and tested line by line. It's written from the common ways people say these things. It never decides whether someone is
safe: that's the crisis net and the safety question, which don't ask here.
"""
from __future__ import annotations

import re

KIN = (r"(?:mom|mum|mama|mommy|mother|dad|daddy|papa|pops|father|grandma|granny|nana|gran|grandmother|grandpa|granddad|gramps|grandfather|"
       r"brother|sister|son|daughter|wife|husband|partner|girlfriend|boyfriend|fianc[eé]e?|uncle|aunt|auntie|cousin|niece|nephew|"
       r"best friend|friend|bestie|roommate|neighbou?r|coworker|teacher|coach|godmother|godfather|stepmom|stepdad|baby|kid|child)")
PET = (r"(?:dog|puppy|pup|cat|kitten|kitty|pet|hamster|rabbit|bunny|bird|parrot|budgie|horse|pony|guinea pig|ferret|turtle|tortoise|lizard|"
       r"snake|goldfish|fish|rat|gerbil|lab|retriever|poodle|terrier|shepherd|beagle|bulldog|husky|corgi|collie|tabby|old (?:girl|boy|man|lady))")
_ADJ = r"(?:(?:old|little|sweet|poor|dear|late|baby|big|older|younger|own|beloved|first|childhood|family)\s+){0,2}"
ONE = rf"(?:my|our|his|her|their)\s+{_ADJ}(?:{KIN}|{PET})"                  # "my dad", "our old lab"
ONE_PET = rf"(?:my|our|his|her|their|the)\s+{_ADJ}{PET}"
ANYONE = rf"(?:{ONE}|him|her|them|[a-z][a-z'’-]+)"                          # a name can be any word: only inside frames that can't mean much else
SUBJECT = rf"(?:{ONE}|he|she|they|[a-z][a-z'’-]+)"
NOT_ME = r"(?<!\bi )(?<!\bwe )(?<!\byou )(?<!\bit )(?<!\bthat )(?<!\bthis )(?<!\bwho )"

# -- when a death word isn't a death ------------------------------------------------------------------------------------
THINGS = (r"(?:phone|iphone|battery|batteries|laptop|computer|pc|mac|car|truck|engine|wifi|wi-fi|internet|tv|remote|charger|plant|printer|"
          r"controller|headphones|airpods|watch|tablet|ipad|console|ps5|xbox|switch|mic|speaker|server|app|game|joke|vibe|party|chat|"
          r"conversation|trend|meme|stream|router|fridge|microwave|sleep schedule|social life|diet|bank account|wallet|group chat)")
NOT_A_DEATH = re.compile(
    rf"\b{THINGS}s?\b[^.!?]{{0,24}}\b(?:died|dead|dies|dying|passed)\b|\b(?:rip|r\.i\.p\.?)\s+(?:to\s+)?(?:my\s+)?{THINGS}|"
    r"\bi(?:'m| am)\s+(?:so\s+|literally\s+|actually\s+)?(?:dead|dying)\b|\b(?:died|dying)\s+(?:laughing|of (?:laughter|embarrassment|cringe|boredom|shame))|"
    r"\bdying\s+(?:to|for (?:a|some|an))\b|\bdead\s+(?:tired|serious|wrong|right|last|ass|end|line|weight|center|set|on|even)\b|"
    r"\b(?:i'?d|i would|would|could|to)\s+die\s+for\b|\bdied down\b|\bkill(?:ed|ing|s)?\s+(?:it|me|the vibe|time|off)\b|"
    r"\b(?:character|episode|season|movie|show|book|novel|series|level|boss fight|spoiler|plot|finale|in the game)\b|"
    r"\b(?:lost|losing|lose)\s+(?:power|electricity|internet|wifi|wi-fi|signal|service|reception|water|heat|track|count|touch|time|money|focus|sleep|weight|"
    r"interest|contact|control|patience|hope|faith|the (?:game|match|lead|bet|case|election|plot|thread|keys|remote))\b|"
    r"\bpassed on\s+(?:the|that|this|an?|my|his|her|their|some|any)\s+(?:offer|chance|opportunity|job|deal|invite|invitation|idea|plan|tickets?|"
    r"dessert|seconds|message|info|word|news|note|savings?|role|promotion|trip)\b",
    re.I)
NOT_REAL = re.compile(r"^\W*(?:what if|imagine if|if)\b|\b(?:if|when|in case|suppose|imagine)\s+(?:my|our|he|she|they|i|we)\b[^.!?]{0,40}"
                      r"\b(?:died|dies|passed|passes|breaks? up|broke up|leaves|left|cheats?|cheated|fails?|failed)\b|\bsomeday\b|\bone day\b|"
                      r"^\W*(?:is it|is that|would it be|do people|does anyone|do you think it'?s)\s+(?:normal|weird|okay|ok|bad|common)\b", re.I)
NOT = r"(?:not|never|no longer|isn'?t|wasn'?t|aren'?t|don'?t|doesn'?t|didn'?t)"
LAUGHING = re.compile(r"\b(?:l+o+l+|l+m+f*a+o+|rofl|ha(?:ha)+h*|he(?:he)+)\b|[😂🤣💀😆]", re.I)

# -- grief: a death, said plainly or softly ------------------------------------------------------------------------------
_GO_ELSEWHERE = r"(?!\s+(?:out|outside|home|to\b|off|play|back|in\b|inside|for\b|early|first|ahead|on\b|run|free|from\b|with\b|at\b))"
GRIEF = [re.compile(p, re.I) for p in (
    # said plainly
    rf"\b(?:died|passed away|passed on\b(?!\s+(?:the|a|an|that|this|it|my|his|her|their|to\b|some|any))|is dead|was dead|found dead|death of|"
    rf"rest in peace|obituary|eulogy|cremat\w+|stillborn|miscarr\w+|euthan\w+|funeral|memorial service|graveside|wake is|burial)\b",
    rf"\b{ONE}(?:'s)?\s+(?:just\s+|recently\s+|suddenly\s+)?passed\b(?!\s+(?:the|my|his|her|their|a|an|it|me|us|them|out|by|up|through|over|on (?:the|a|an)))",
    rf"\b(?:he|she|they|[a-z]+)\s+(?:just\s+)?passed\s+(?:peacefully|in (?:his|her|their) sleep|last (?:night|week|month|year)|this (?:morning|afternoon|week)|"
    rf"yesterday|today|on (?:mon|tues|wednes|thurs|fri|satur|sun)day|(?:\w+\s+){{1,2}}ago|in (?:january|february|march|april|may|june|july|august|september|"
    rf"october|november|december))\b",
    # said softly
    rf"{NOT_ME}\b(?:didn'?t|did not|isn'?t going to|won'?t|not going to|might not|may not|couldn'?t)\s+make it\b"
    rf"(?!\s+(?:to\b|on time|in time|home|back|there|out of|into|onto|past|for\b|work|class|today|tonight|this (?:week|time|year)|big|far|easy|work\b))",
    rf"\b(?:had to|have to|having to|going to have to|gonna have to|need to|decided to|time to|chose to)\s+(?:have\s+)?put\s+{ANYONE}\s+(?:down|to sleep)\b",
    rf"\bput(?:ting)?\s+{ONE_PET}\s+(?:down|to sleep)\b(?!\s+(?:so|for a (?:sec|second|minute)|and (?:then|go)))",
    rf"\b(?:are|were|was|is|we'?re|i'?m)\s+putting\s+{ANYONE}\s+down\s+(?:tomorrow|today|this|on|next)",
    rf"\b(?:had to|have to|having to|going to have to|gonna have to|time to|decided to)\s+let\s+{ANYONE}\s+go\b{_GO_ELSEWHERE}(?=.*\b(?:vet|{PET}|suffering|"
    rf"in (?:so much |a lot of )?pain|cancer|sick|years old|\d{{1,2}}\b|peacefully))",
    rf"\blet\s+(?:my|our)\s+{_ADJ}{PET}\s+go\b{_GO_ELSEWHERE}",
    rf"\bthe vet\s+(?:said|told us|says)\s+(?:it (?:was|is|'s) time|there (?:was|is|'s) nothing)|\bthe vet\s+(?:couldn'?t|could not)\s+(?:save|help|do)\b|"
    rf"\b(?:couldn'?t|could not|weren'?t able to|wasn'?t able to)\s+save\s+(?:him|her|them|{ONE})\b",
    rf"\b(?:had to|have to|having to|got to|time to)\s+say\s+(?:our\s+|my\s+|a\s+|one last\s+|a final\s+)?goodbyes?\s+to\s+(?:{ONE}|him|her|them)\b|"
    rf"\bsaid\s+(?:our\s+|my\s+|a\s+|one last\s+|a final\s+)?goodbyes?\s+to\s+(?:{ONE}|him|her|them)\b",
    rf"\b(?:{ONE}|he|she|they)(?:'s|’s| is|'re| are)\s+(?:really\s+|actually\s+|finally\s+|just\s+)?gone\b"
    rf"(?!\s+(?:to\b|for (?:the|a|an|\w+ (?:days?|weeks?|hours?))|out|home|back|on\b|off|by\b|until|till|shopping|fishing|crazy|mad|viral|wrong|too far|quiet|"
    rf"missing|all (?:day|week)|a lot))",
    rf"\b(?:lost|losing)\s+{ONE}\b(?!'s)|\bwe lost\s+(?:him|her|them)\b(?!\s+(?:at|in the|on the))|\blost the baby\b",
    rf"\brainbow bridge\b|\bcrossed over\b|\b(?:went|gone|going) to heaven\b|\b(?:is|'s) in heaven\b|\bwith (?:god|the angels|jesus|the lord) now\b|"
    rf"\bno longer with us\b|\bleft us (?:today|yesterday|last|this|too soon|so soon)\b|\blaid\s+(?:him|her|them|{ONE})\s+to rest\b|"
    rf"\bburied\s+(?:him|her|them|{ONE})\b|\bscattered\s+(?:his|her|their|{ONE}(?:'s)?)\s+ashes\b|\bwon'?t be coming home\b|\bnever coming home\b",
    # coming, or come round again
    rf"\b(?:doesn'?t|don'?t|won'?t)\s+have\s+(?:much|a lot of|long|much more)\s+(?:time|longer)\b|\b(?:only|just)\s+(?:has|have|got)\s+(?:a few|\w+)\s+"
    rf"(?:days|weeks|months)\s+(?:left|to live)\b|\b(?:in|on|into) hospice\b|\blife support\b|\bterminal\b|\bstage (?:4|four|iv)\b|"
    rf"{NOT_ME}\b(?:is|was|are|'s)\s+dying\b",
    rf"\bwould(?:'ve| have)\s+been\s+(?:his|her|their|\w+'s)\s+(?:\d+\w*\s+)?birthday\b|\b(?:first|second|another)\s+(?:christmas|birthday|thanksgiving|holiday|"
    rf"mother'?s day|father'?s day|new year|easter|eid|hanukkah|diwali)\s+without\b|\b(?:years?|months?|weeks?)\s+(?:ago today|since (?:we lost|"
    rf"(?:he|she|they|{ONE}|\w+)\s+(?:died|passed|left us)))\b|\b(?:ago today|a year ago|years ago)\s+(?:we|i)\s+lost\b|"
    rf"\banniversary of\s+(?:his|her|their|{ONE}(?:'s)?|\w+'s)\s+(?:death|passing)\b",
)]
WHO = re.compile(rf"\b(?:my|our)\s+{_ADJ}(?P<who>{KIN}|{PET})\b", re.I)

# -- the other heavy ones ------------------------------------------------------------------------------------------------
I = r"(?:i'?m|im|i am|i'?ve been|i have been|i feel|i'?m feeling|i felt|feeling|been feeling|i was|i just feel|i been)"
VERY = r"(?:(?:so|really|super|just|very|kind of|kinda|a little|a bit|pretty|completely|totally|absolutely|lowkey|honestly|actually|still)\s+){0,3}"
HEARTBREAK = re.compile(
    r"\b(?:broke up with me|broke up|breaking up with me|dumped me|left me\b(?!\s+(?:a|an|the|some|on read|alone for a (?:sec|minute)|hanging|out|behind at))|"
    r"cheat(?:ed|ing) on me|wants? a divorce|filed for divorce|getting (?:a )?divorced?|ended things|called off the (?:wedding|engagement)|"
    r"(?:doesn'?t|don'?t) love me anymore|fell out of love|(?:been|is|was|'s) seeing someone else|(?:found|caught) (?:him|her|them) (?:with|texting)|"
    r"ghosted me|we'?re over|it'?s over between|moved out and|heartbroken|broke my heart)\b", re.I)
FEAR = re.compile(
    rf"\b{I}\s+{VERY}(?:scared|terrified|afraid|frightened|petrified|nervous|anxious|panicking|freaking out|worried sick|on edge|dreading)\b|"
    r"\bpanic attack\b|\bcan'?t stop (?:worrying|shaking|thinking about what)\b|\bcan'?t breathe\b|\bi'?m dreading\b|\bscared (?:i|that|of|to)\b|"
    r"\bterrified (?:i|that|of|to|about)\b|\bwaiting (?:on|for) (?:the |my )?(?:results|biopsy|scan|diagnosis|test results)\b|\bwhat if (?:it'?s|i|they find)\b",
    re.I)
SHAME = re.compile(
    rf"\b{I}\s+{VERY}(?:like )?(?:such )?(?:a |an )?(?:failure|loser|idiot|burden|disappointment|fraud|joke|mess|terrible|horrible|awful|worthless|pathetic|"
    rf"stupid|dumb|useless|embarrassed|ashamed|humiliated|mortified|guilty)\b|\b(?:it'?s|it was|this is|that'?s)\s+(?:all\s+)?my fault\b|"
    r"\bi (?:messed|screwed|fucked) (?:it |everything |this |that )?up\b|\bi let (?:him|her|them|everyone|everybody|my \w+|the \w+|you) down\b|"
    r"\bi(?:'m| am) (?:a |an |such a )(?:terrible|bad|awful|horrible|shitty|useless) (?:mom|mother|dad|father|parent|friend|person|son|daughter|partner|wife|husband)\b|"
    r"\bcan'?t forgive myself\b|\bi hate (?:that|how) i\b|\bso embarrass\w+\b", re.I)
HURT = re.compile(
    r"\b(?:went|go|going|hung out|hang out|made plans|had (?:a |the )?(?:party|dinner|trip)) (?:out )?without me\b|\b(?:left|leaving|leave) me out\b|"
    r"\b(?:didn'?t|did not|never) (?:even )?invite(?:d)? me\b|\b(?:forgot|forgotten) my birthday\b|\blied to (?:me|my face)\b|\bbehind my back\b|"
    r"\b(?:nobody|no one|none of them) (?:showed up|came|even (?:called|texted|asked|noticed|remembered))\b|\bwithout me\b(?=.*\b(?:group chat|friends|all)\b)|"
    r"\bgroup chat without me\b|\bbetrayed\b|\bstood me up\b|\bmade fun of me\b|\blaughed at me\b|\bin confidence\b|\btold everyone (?:what|about|my)\b|"
    r"\b(?:ignored|ignoring|ignores) me\b|\bstabbed me in the back\b|\b(?:my|our) (?:own )?\w+ (?:said|told me|thinks) i'?m\b(?=.*\b(?:useless|lazy|fat|ugly|stupid|a burden)\b)",
    re.I)
LOW = re.compile(
    rf"\b{I}\s+{VERY}(?:down|sad|low|blue|empty|numb|hollow|miserable|depressed|hopeless|heartsick|not (?:okay|ok|myself|doing (?:well|good|great))|"
    rf"struggling|lost\b(?! (?:my|the|a|an|it|in thought|track))|off\b(?=\s*(?:lately|today|all day|this week|\.|$)))\b|"
    r"\b(?:i )?(?:cried|been crying|keep crying|can'?t stop crying|was crying)\b|\bcan'?t get out of bed\b|\b(?:everything|nothing|it all) feels? "
    r"(?:pointless|gray|grey|heavy|empty|hard|wrong|numb)\b|\bnothing (?:feels good|makes me happy|matters lately)\b|\bmy heart hurts\b", re.I)
LONELY = re.compile(r"\b(?:lonely|so alone|all alone|feel alone|no one to talk to|nobody to talk to|don'?t (?:really )?have anyone|"
                    r"no friends|nobody texts|nobody calls|no one calls|no one texts|nobody cares|no one cares)\b", re.I)
OVERWHELMED = re.compile(
    rf"\b{I}\s+{VERY}(?:overwhelmed|swamped|drowning|burn(?:ed|t) out|fried|at my limit|at (?:my|the) breaking point|stretched (?:so |too )?thin|stressed|"
    rf"stressed out|falling apart|barely (?:holding|keeping) (?:it|on|up)|spiraling|spiralling)\b|\b(?:it'?s|its|this is|everything is) (?:all |just )?too much\b|"
    r"\bcan'?t keep up\b|\bat my limit\b|\bbreaking point\b|\bdrowning (?:in|at)\b|\beverything (?:at once|is falling apart)\b|\bcan'?t (?:do|handle|take) "
    r"(?:this|it|any more|anymore)\b(?=.*\b(?:work|deadline|kids?|school|bills|job|week|exams?)\b)", re.I)
DISAPPOINTED = re.compile(
    r"\b(?:didn'?t|did not) get (?:the|that|my|in\b|it\b|into|accepted|picked|chosen|hired|a callback|an offer)\b|\b(?:went|going|gone) with someone else\b|"
    r"\b(?:picked|chose|hired) someone else\b|\bi (?:failed|flunked|bombed|blew)\b(?! (?:to\b|at being))|\bgot (?:rejected|turned down|passed over|cut from|"
    r"laid off|let go|fired|denied|waitlisted)\b|\b(?:fell|falling) through\b|\b(?:didn'?t|did not) make (?:the (?:team|cut|list)|it (?:onto|into) the)\b|"
    r"\blost my job\b|\b(?:they|he|she) (?:said|told me) no\b|\bdidn'?t (?:pass|qualify|win)\b|\b(?:so|really) disappointed\b|\bgot my hopes up\b", re.I)

# -- the good ones, and missing --------------------------------------------------------------------------------------------
RELIEVED = re.compile(r"\b(?:such a|what a|huge|so much) relief\b|\bso relieved\b|\bthank god\b|\bfinally over\b|\bcan finally breathe\b|\bweight off\b|"
                      r"\b(?:came|come) back (?:negative|benign)\b|\b(?:tests?|results?) (?:were|was|are|came back) (?:negative|fine|normal|benign)\b|\bit'?s benign\b", re.I)
PROUD = re.compile(
    r"\bi finally\s+(?:ran|did|finished|quit|told|asked|went|got through|made it through|paid off|cleaned|passed|called|started|learned|beat|said)\b|"
    r"\b(?:\w+\s+)?(?:days?|weeks?|months?|years?) (?:sober|clean|smoke[- ]free|without (?:a drink|smoking|drinking))\b|\bfor the first time\b|"
    r"\bproud of myself\b|\bi (?:did it|actually did it|pulled it off)\b|\bfinished my (?:degree|thesis|book|first|marathon|training)\b|\bpersonal (?:best|record)\b|"
    r"\bpaid off (?:my|the|our)\b|\bi stood up (?:to|for)\b", re.I)
JOY = re.compile(
    r"\b(?:i|we) got (?:the job|the offer|in\b(?=\s*[!.]|\s*$| to)|into|engaged|married|promoted|accepted|approved|the keys|the house|the apartment|the part|"
    r"the role|the grant|the scholarship|the loan|a raise|my (?:license|degree|offer|first job|visa|green card|citizenship))\b|\b(?:we'?re|i'?m|we are|i am) "
    r"(?:having a baby|pregnant|engaged|getting married|cancer[- ]free|in remission|officially|moving in together)\b|\b(?:she|he|they) said yes\b|"
    r"\bi (?:passed|aced|won|nailed)\b(?! (?:out|the salt|on|by|up|it to|him|her|them|me))|\b(?:came|come) back clear\b|\b(?:cancer[- ]free|in remission|all clear)\b|"
    r"\bit'?s a (?:boy|girl)\b|\b(?:best|happiest) (?:day|news|week) (?:ever|of my life)\b|\bi(?:'m| am) so happy\b|\bgreat news\b|\bgood news\b|\bwe won\b|"
    r"\bjust (?:adopted|closed on|signed the lease|got back from our honeymoon)\b", re.I)
MISSING = re.compile(r"\bi (?:really |just |still |do )?miss\s+(?:my|our|him|her|them|home|how|when|those|that|the (?:old|way)|being|having|you\b)|\bhomesick\b|"
                     r"\bwish (?:i|we) could go back\b", re.I)

SMALL = re.compile(r"\b(?:a little|a bit|a tad|kinda|kind of|sort of|sorta|slightly|a touch|somewhat|lowkey)\b", re.I)
BIG = re.compile(r"\b(?:so so|really really|can'?t (?:breathe|stop|sleep|eat|think|function)|completely|absolutely|utterly|devastated|destroyed|"
                 r"shattered|wrecked|falling apart|worst|unbearable|sobbing|bawling)\b|!{2,}|😭|💔|\b(?:SO|REALLY|CAN'?T|NEVER|HATE)\b")
TODAY = re.compile(r"\b(?:today|tonight|this (?:morning|afternoon|evening)|last night|just now|an hour ago|yesterday|just\b)", re.I)

FAMILIES = {  # family: (need, heavy, why)
    "grief": ("company", True, "they're talking about a loss"),
    "heartbreak": ("their side", True, "they're going through something"),
    "fear": ("steadying", True, "they're going through something"),
    "shame": ("kindness", True, "they're going through something"),
    "hurt": ("their side", True, "they're going through something"),
    "low": ("company", True, "they're going through something"),
    "lonely": ("company", True, "they're going through something"),
    "overwhelmed": ("steadying", True, "they're going through something"),
    "disappointed": ("company", True, "they're going through something"),
    "relieved": ("relief", False, "they're relieved"),
    "proud": ("cheer", False, "they did something hard"),
    "joy": ("cheer", False, "they have good news"),
    "missing": ("company", False, "they're missing someone or somewhere"),
}
ALWAYS_HEAVY = {"grief", "heartbreak", "shame", "hurt"}  # the rest are only heavy when they're clearly felt, not "a little nervous"
ORDER = [("heartbreak", HEARTBREAK), ("fear", FEAR), ("shame", SHAME), ("hurt", HURT), ("lonely", LONELY), ("low", LOW), ("overwhelmed", OVERWHELMED),
         ("disappointed", DISAPPOINTED), ("relieved", RELIEVED), ("proud", PROUD), ("joy", JOY), ("missing", MISSING)]


def not_a_loss(text):
    """A death word that isn't about a death: a phone that died, "I'm dead" at a joke, a character in a show, a what-if."""
    said = str(text or "")
    return bool(NOT_A_DEATH.search(said) or NOT_REAL.search(said))


def _negated(said, start):
    """ "i'm not sad", "i wasn't scared": the feeling word comes right after a not."""
    return bool(re.search(rf"\b{NOT}\s+(?:\w+\s+){{0,2}}$", said[max(0, start - 28):start], re.I))


def _family(said):
    if not not_a_loss(said):
        for pattern in GRIEF:
            if pattern.search(said):
                return "grief"
    if NOT_REAL.search(said):
        return None
    for family, pattern in ORDER:
        found = pattern.search(said)
        if found and not _negated(said, found.end() if family in ("fear", "shame", "low", "overwhelmed") else found.start()):
            return family
    return None


def read(text):
    """The feeling in one message, as a close friend would name it, or None for plain talk."""
    said = " ".join(str(text or "").split())
    if not said:
        return None
    low = said.lower()
    family = _family(low)
    if not family:
        return None
    need, heavy, why = FAMILIES[family]
    strength = 1 if SMALL.search(low) else 3 if (BIG.search(said) or (family == "grief" and TODAY.search(low))) else 2
    if family not in ALWAYS_HEAVY:
        heavy = heavy and strength >= 2 and not (family != "grief" and LAUGHING.search(said))
    who = WHO.search(low) if family in ("grief", "missing", "fear") else None
    return {"family": family, "strength": strength, "about": ("their " + who["who"]) if who else "", "need": need, "heavy": heavy, "why": why}
