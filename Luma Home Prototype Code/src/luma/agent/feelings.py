"""What they're feeling, read from what they said. The one place Luma reads feeling.

Before this, four parts of Luma each had their own word list: whether a joke is welcome (humor), whether a reply has to
care (friendcheck), how Luma itself feels (mind), and whether to ask how they are tomorrow (presence). A death said softly
("we had to put Max to sleep", "our dog didn't make it") was in none of them, so the brain was told a little humor was
welcome. Now they all ask here.

read(text) gives the feeling as a close friend would name it, or None for plain talk:

    {"family":   grief, heartbreak, fear, shame, hurt, low, lonely, overwhelmed, disappointed,
                 fed up, joy, proud, relieved, missing
     "strength": 1 a touch, 2 clearly, 3 a lot
     "about":    who or what, when they said ("their dad", "their cat"), else ""
     "need":     what a friend does first: company, their side, steadying, kindness, cheer, relief
     "heavy":    a moment for no jokes, where the reply has to meet the feeling before anything else
     "also":     a second feeling of the other kind, said in the same breath ("such a relief, and i still cried"), else ""
     "why":      a few words for the brain's note}

note(read) is the one line the brain gets for it: what this feeling needs before anything else.

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
BARE = r"(?:mom|mum|mama|mommy|dad|daddy|papa|pops|grandma|granny|nana|gran|grandpa|granddad|gramps)"  # said like a name: "since we lost dad"
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
    r"\b(?:character|villain|protagonist|narrator|spoilers?|plot twist|boss fight)\b|"
    r"\b(?:sick|scared|bored|worried|tickled|frozen|starved|worked|done|loved?|love (?:you|him|her|it|them)|beat(?:en)?|talked) to death\b|\bdeath (?:stare|glare|grip|march|trap|metal)\b|"
    rf"\b(?:\d+\s*%|{THINGS})[^.!?]{{0,40}}\blife support\b|\blife support\b[^.!?]{{0,40}}\b(?:\d+\s*%|{THINGS})\b|"
    r"\b(?:in|on|of|from)\s+(?:the|this|that|my|a|an|last night'?s)\s+(?:\w+\s+){0,2}(?:episode|season|movie|film|show|book|novel|series|finale|chapter|game|level|anime|play)\b|"
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
    rf"\bwould(?:'ve| have)\s+been\s+(?:his|her|their|\w+'s)\s+(?:\d+\w*\s+)?birthday\b|\b(?:first|second|another)\s+(?:christmas|birthday|thanksgiving|holidays?|"
    rf"mother'?s day|father'?s day|new year|easter|eid|hanukkah|diwali)\s+without\b|\b(?:years?|months?|weeks?)\s+(?:ago today|since (?:we lost|"
    rf"(?:he|she|they|{ONE}|\w+)\s+(?:died|passed|left us)))\b|\b(?:ago today|a year ago|years ago)\s+(?:we|i)\s+lost\b|"
    rf"\banniversary of\s+(?:his|her|their|{ONE}(?:'s)?|\w+'s)\s+(?:death|passing|accident|funeral|suicide)\b",
    # a while ago, and what's left
    rf"\bmy late\s+{KIN}\b|\b(?:widow|widower|widowed)\b|(?<!good )\b(?:grief|grieving|mourning|bereaved|bereavement)\b",
    rf"\b(?:can'?t|cannot|couldn'?t|can not)\s+(?:bring myself to\s+)?(?:delete|erase|throw (?:out|away)|get rid of|give away|pack up|wash)\s+"
    rf"(?:his|her|their|{ONE}(?:'s)?)\s+(?:number|contact|voicemails?|texts?|messages?|clothes|things|stuff|room|side of the bed|collar|bowl|toys|pictures|photos|leash)\b",
    rf"\bkeep(?:s)? expecting\s+(?:him|her|them|{ONE})\s+to\s+(?:walk|come|call|be|text|run|show up|greet|jump)\b|"
    rf"\b(?:listen(?:ing)? to|saved|kept|keep|play(?:ing)?)\s+(?:his|her|their|{ONE}(?:'s)?)\s+(?:old\s+|last\s+)?(?:voicemails?|voice ?mail|last (?:message|text))\b",
    rf"\b(?:headstone|gravestone|tombstone|casket|coffin|gravesite|graveside|cemetery|graveyard|mausoleum)\b|"
    rf"\b(?:his|her|their|{ONE}(?:'s)?|{BARE}'s|the)\s+grave\b(?!\s+(?:mistake|danger|concern|error|matter|situation))|\ban urn\b|\b(?:his|her|their) urn\b",
    rf"\b(?:took|taken|drew)\s+(?:his|her|their)\s+last breath\b|\b(?:comfort care|palliative(?: care)?|end[- ]of[- ]life care)\b",
    rf"\b(?:they|the\s+(?:doctors?|vets?|oncologists?|specialists?|surgeons?|hospital))\s+(?:gave|give|are giving|is giving|have given|has given|only gave)\s+"
    rf"(?:him|her|them|{ONE}|{BARE})\s+(?:about\s+|maybe\s+|only\s+|just\s+|at most\s+|less than\s+)?(?:an?|\d+|a few|a couple(?: of)?|[a-z]+)\s+(?:days?|weeks?|months?|years?)\b"
    rf"(?!\s+(?:to\s+(?:finish|decide|pay|move|respond|complete|submit|think|get|find|turn|fix|learn|study|prepare|recover|heal)|off\b|of\s+(?:leave|vacation|pto|rest)|notice|probation|extension))",
    rf"\b(?:{ONE}|{BARE}|he|she|they)\s+would(?:'ve| have)\s+(?:been|turned)\s+(?:\d{{1,3}}|[a-z]+ty(?:[- ][a-z]+)?|[a-z]+teen)\b(?!\s*(?:dollars|bucks|percent|%|degrees|miles|minutes|hours|pounds|\$))",
    rf"\b(?:years?|months?|weeks?)\s+since\s+(?:we\s+(?:lost|said goodbye)|i\s+lost|(?:he|she|they|{ONE}|{BARE})\s+(?:left us|passed|died|went))\b|"
    rf"\bmarks?\s+(?:\w+\s+){{1,3}}(?:years?|months?)\s+(?:without|since)\b|\bsaid\s+(?:our\s+|my\s+|a\s+)?goodbyes?\s+to\s+{BARE}\b",
    rf"\bheaven(?:ly)? birthday\b|\bangel(?:versary| anniversary)\b|\bdeathiversary\b|\b(?:lost|losing) the (?:pregnancy|twins)\b",
    rf"\b(?:make|made|making)\s+the\s+(?:call|decision|choice)\s+to\s+(?:let\s+(?:him|her|them|{ONE})\s+go|put\s+(?:him|her|them|{ONE})\s+(?:down|to sleep))\b",
    rf"\b(?:went|go|going|started|picked up the phone)\s+to\s+(?:call|text|phone|ring|tell)\s+(?:him|her|them|{ONE}|{BARE})\s+(?:and|before i|then)\s+(?:then\s+)?(?:remembered|realized|realised)\b",
    rf"\b(?:his|her|their)\s+(?:food\s+|water\s+)?(?:bowl|collar|leash|side of the bed)\s+is\s+(?:still|just)\b",
    rf"\bwould(?:'ve| have)\s+been\s+(?:our|my|his|her|their)\s+(?:\d+\w*\s+|[a-z]+\s+)?(?:anniversary|birthday|wedding day|graduation|due date)\b|"
    rf"\b(?:was|is) supposed to be\s+(?:my|our|the)\s+due date\b|\b(?:my|our) due date\s+(?:was|would have been)\b",
    rf"\b(?:{ONE}|{BARE}|he|she)(?:'s|’s|\s+has|\s+is)\s+been gone\s+(?:for\s+)?(?:\w+\s+){{0,2}}(?:years?|months?|so long)\b|"
    rf"\b(?:{ONE}|{BARE})(?:'s|’s|\s+has)\s+been gone\b(?!\s+(?:for\s+)?(?:\w+\s+){{0,2}}(?:hours?|minutes?|all day|since (?:this|noon|lunch)))",
    rf"\bsince\s+(?:{ONE}|{BARE}|he|she|they|(?!i\b|we\b|you\b|it\b)[a-z]+)\s+passed\b(?!\s+(?:the|my|his|her|their|a|an|it|me|us|them|out|by|up|through|over|on (?:the|a|an)))|"
    rf"\blit a candle for\s+(?:him|her|them|{ONE}|{BARE})\b|\b(?:first|second|third|another|whole|full|one|a)\s+year\s+without\s+(?:him|her|them|{ONE}|{BARE})\b",
    rf"\b(?:he|she)\s+was\s+only\s+\d{{1,2}}\b(?!\s*(?:when|at the time|and already|years old when|,? and (?:he|she)))|"
    rf"\b(?:never got|didn'?t get|never had the chance)\s+to say goodbye\b(?!\s+(?:before|at the|when (?:he|she|they) left for))",
    rf"\b(?:he|she|they|{ONE}|[a-z]+)\s+(?:overdosed|od'?d|took (?:his|her|their) own life|killed (?:himself|herself|themselves)|drowned|didn'?t survive|never woke up)\b|"
    rf"\blost\s+(?:his|her|their)\s+(?:battle|fight)\s+(?:with|to|against)\b|"
    rf"\b(?:cancer|covid|alzheimer'?s|dementia|the (?:stroke|accident|crash|fire|overdose|heart attack))\s+took\s+(?:him|her|them|{ONE}|{BARE})\b",
    rf"\b(?:his|her|their|{ONE}(?:'s)?|{BARE}'s)\s+(?:memorial|wake|viewing|ashes|obituary)\b|"
    rf"\b(?:memorial|celebration of life)\s+(?:is|was|will be)\s+(?:on|this|next|tomorrow|today|saturday|sunday|monday|tuesday|wednesday|thursday|friday)\b",
)]
WHO = re.compile(rf"\b(?:my|our)\s+{_ADJ}(?P<who>{KIN}|{PET})\b", re.I)

# -- the other heavy ones ------------------------------------------------------------------------------------------------
I = r"(?:i'?m|im|i am|i'?ve been|i have been|i feel|i'?m feeling|i felt|feeling|been feeling|i was|i just feel|i been)"
VERY = r"(?:(?:so|really|super|just|very|kind of|kinda|a little|a bit|pretty|completely|totally|absolutely|lowkey|honestly|actually|still)\s+){0,3}"
HEARTBREAK = re.compile(
    r"\b(?:broke up with me|broke up|breaking up with me|dumped me|left me\b(?!\s+(?:a|an|the|some|on read|alone for a (?:sec|minute)|hanging|out|behind at))|"
    r"cheat(?:ed|ing) on me|wants? a divorce|filed for divorce|getting (?:a )?divorced?|ended things|called off the (?:wedding|engagement)|"
    r"(?:doesn'?t|don'?t) love me anymore|fell out of love|(?:been|is|was|'s) seeing someone else|(?:found|caught) (?:him|her|them) (?:with|texting)|"
    r"ghosted me|we'?re over|it'?s over between|heartbroken|broke my heart)\b|"
    r"\b(?:he|she|my (?:wife|husband|partner|girlfriend|boyfriend|fianc[eé]e?))\s+(?:just\s+)?moved out\b|"
    r"\b(?:my|our)\s+(?:marriage|relationship|engagement)\s+is\s+(?:over|ending|falling apart|done|finished)\b|"
    r"\b(?:we|my \w+ and i|me and my \w+)\s+(?:just\s+|recently\s+|finally\s+)?(?:split up|separated|broke up|called it quits|called it off)\b(?!\s+the\b)|"
    r"\b(?:caught|found out)\s+(?:him|her|them|he|she|my \w+)(?:\s+was|\s+is|\s+has been|'s)?\s+cheating\b|\bunfaithful\b|\b(?:having|had|been having) an affair\b", re.I)
FEAR = re.compile(
    rf"\b{I}\s+{VERY}(?:scared|terrified|afraid|frightened|petrified|nervous|anxious|panicking|freaking out|worried sick|on edge|dreading)\b|"
    r"\bpanic attacks?\b|\bcan'?t stop (?:worrying|shaking|thinking about what)\b|"
    r"\bmy anxiety\s+(?:is|has been|'s|’s)\s+(?:so |really |been )?(?:bad|through the roof|terrible|awful|out of control|acting up|high|killing me)\b|"
    r"\bi'?m\s+(?:so|really|very|super|extremely)\s+worried\b|\bsick to my stomach\b|\bwhat if\s+(?:the|my)\s+(?:cancer|tumou?r|test|results?|scan|biopsy)\b|\bcan'?t breathe\b|\bi'?m dreading\b|\bscared (?:i|that|of|to)\b|"
    r"\bterrified (?:i|that|of|to|about)\b|\bwaiting (?:on|for) (?:the |my )?(?:results|biopsy|scan|diagnosis|test results)\b|"
    r"\bwhat if\s+(?:it'?s\s+(?:cancer|serious|bad|malignant|something (?:serious|bad|wrong))|they find\s+(?:something|cancer|a\b)|"
    r"i\s+(?:lose|can'?t|fail|never|don'?t (?:make it|get|pass|wake)))\b",
    re.I)
SHAME = re.compile(
    rf"\b{I}\s+{VERY}(?:like )?(?:such )?(?:a |an )?(?:failure|loser|idiot|burden|disappointment|fraud|joke|mess|terrible|horrible|awful|worthless|pathetic|"
    rf"stupid|dumb|useless|embarrassed|ashamed|humiliated|mortified|guilty)\b|\b(?:it'?s|it was|this is|that'?s)\s+(?:all\s+)?my fault\b|"
    r"\bi (?:messed|screwed|fucked) (?:it |everything |this |that )?up\b|\bi let (?:him|her|them|everyone|everybody|my \w+|the \w+|you) down\b|"
    r"\bi(?:'m| am) (?:a |an |such a )(?:terrible|bad|awful|horrible|shitty|useless) (?:mom|mother|dad|father|parent|friend|person|son|daughter|partner|wife|husband)\b|"
    r"\bcan'?t forgive myself\b|\bi hate (?:that|how) i\b|\bso embarrass\w+\b|"
    r"\bi\s+(?:ruined|wrecked|destroyed)\s+(?:everything|my (?:life|chance|chances|marriage|career|family)|things with)\b|"
    r"\bi'?m the worst\b(?!\s+(?:at|with|about)\b)|\bi hate myself\b|\bi'?(?:m| am|ll never be| will never be)\s+not good enough\b(?!\s+at\b)|"
    r"\bi'?m not good enough\b(?!\s+at\b)|\bi can'?t do anything right\b|"
    r"\bi should(?:'ve| have)\s+(?:been there|done more|known|seen it|called|visited|said something|stayed)\b|\bi relapsed\b|\bfell off the wagon\b|"
    r"\bi\s+(?:disappointed|failed|let down|hurt)\s+(?:my (?:parents|mom|dad|kids?|family|wife|husband|partner|team|friends?|son|daughter)|everyone|everybody)\b|"
    r"\bi let\s+(?:my (?:kids?|parents|family|team|mom|dad|wife|husband|partner|son|daughter))\s+down\b", re.I)
HURT = re.compile(
    r"\b(?:went|go|going|hung out|hang out|made plans|had (?:a |the )?(?:party|dinner|trip)) (?:out )?without me\b|\b(?:left|leaving|leave) me out\b|"
    r"\b(?:didn'?t|did not|never) (?:even )?invite(?:d)? me\b|\b(?:forgot|forgotten) my birthday\b|\blied to (?:me|my face)\b|\bbehind my back\b|"
    r"\b(?:nobody|no one|none of them) (?:showed up|came|even (?:called|texted|asked|noticed|remembered))\b|"
    r"\b(?:nobody|no one|not one person|none of (?:them|my friends|my kids|my family))\s+(?:even\s+)?(?:called|texted|remembered|asked|noticed|said anything|wished me|"
    r"checked in|reached out|invited me|visited)\b(?!\s+(?:about|back about|for the|regarding|the (?:police|cops)|in sick))|\bwithout me\b(?=.*\b(?:group chat|friends|all)\b)|"
    r"\bgroup chat without me\b|\bbetrayed\b|\bstood me up\b|\bmade fun of me\b|\blaughed at me\b|\bin confidence\b|\btold everyone (?:what|about|my)\b|"
    r"\b(?:ignored|ignoring|ignores) me\b|\bstabbed me in the back\b|"
    r"\b(?:stopped|quit)\s+(?:talking|speaking)\s+to me\b|\b(?:called|calls)\s+me\s+(?:an? )?(?:worthless|stupid|fat|ugly|useless|lazy|crazy|loser|burden|failure|idiot|dumb|"
    r"pathetic|nothing)\b|\bdidn'?t\s+(?:even\s+)?(?:come|show up|show|bother coming)\s+to my\b|\bi wasn'?t\s+(?:even\s+)?invited\b|"
    r"\bwish(?:es|ed)?\s+(?:i|she'?d|he'?d|they'?d)\s+(?:was|were|had)\s+never\s+(?:been\s+)?born\b|\bchose\s+(?:him|her|them|[a-z]+)\s+over me\b|"
    r"\b(?:replaced|excluded|abandoned|ditched|unfriended|uninvited)\s+me\b|\bblocked me\b(?=[^.!?]*\b(?:everything|everywhere|instagram|facebook|snap|whatsapp|"
    r"number|phone|socials?|all)\b)|\b(?:my|our) (?:own )?\w+ (?:said|told me|thinks) i'?m\b(?=.*\b(?:useless|lazy|fat|ugly|stupid|a burden)\b)",
    re.I)
LOW = re.compile(
    rf"\b{I}\s+{VERY}(?:down|sad|low|blue|empty|numb|hollow|miserable|depressed|hopeless|heartsick|not (?:okay|ok|myself|doing (?:well|good|great))|"
    rf"struggling|lost\b(?! (?:my|the|a|an|it|in thought|track))|off\b(?=\s*(?:lately|today|all day|this week|\.|$)))\b|"
    r"\b(?:i )?(?:cried|been crying|keep crying|can'?t stop crying|was crying)\b|\bcan'?t get out of bed\b|\b(?:everything|nothing|it all) feels? "
    r"(?:pointless|gray|grey|heavy|empty|hard|wrong|numb)\b|\bnothing (?:feels good|makes me happy|matters lately)\b|\bmy heart hurts\b|\bi hate my life\b|"
    r"\bhaven'?t\s+(?:left|been out of|gotten out of|got out of)\s+(?:my|the)\s+(?:apartment|house|room|bed|place|flat)\s+(?:in|for)\s+(?:days|weeks|months|a week|a few days|[a-z]+ days)\b|"
    r"\blost interest in\s+(?:everything|things|life|all of it|the things i (?:used to )?(?:love|enjoy))\b|\bdon'?t enjoy\s+(?:anything|things|life)\b|"
    r"\b(?:want|wanna)\s+to\s+(?:sleep|stay in bed)\s+all day\b|\bgoing through the motions\b|\bi feel like crying\b|\bon the verge of tears\b|"
    r"\bi\s+(?:just\s+|completely\s+|totally\s+)?broke down\b(?=\s*(?:[.!,]|$|crying|in tears|and cried|at work|in the car|in front of|on the phone|in the bathroom))|"
    r"\b(?:it'?s been|been|having|had|going through)\s+(?:a\s+|some\s+)?(?:really\s+|pretty\s+|very\s+)?(?:dark|rough|hard|heavy|awful|terrible|tough)\s+"
    r"(?:few\s+|couple of\s+|couple\s+)?(?:days|weeks|months|year|time|patch|stretch)\b", re.I)
LONELY = re.compile(
    r"\b(?:lonel(?:y|ier|iest|iness)|so alone|all alone|no one to talk to|nobody to talk to|don'?t (?:really )?have anyone|no friends|nobody cares|no one cares)\b|"
    r"\bmy phone\s+(?:never|doesn'?t|hasn'?t|barely)\s+(?:rings?|rung|buzz(?:es|ed)?|goes off|lights up)\b(?!\s+(?:during|in|at|when|while))|"
    r"\b(?:an afterthought|a third wheel|the third wheel|the odd one out|a backup (?:friend|plan)|everyone'?s (?:second|last) choice)\b|"
    r"\b(?:hard|tough|impossible|difficult)\s+to\s+(?:make|meet|find)\s+(?:friends|people)\b|\bmaking friends\b(?=[^.!?]*\b(?:hard|tough|impossible|difficult|exhausting)\b)|"
    r"\b(?:been|keep|keeping|started)\s+(?:isolating|to myself|isolating myself|pushing (?:people|everyone) away|shutting (?:people|everyone) out)\b|"
    r"\b(?:there'?s|i have|i'?ve got)\s+no one else\b|\bno one else to\s+(?:talk to|tell|call)\b|\bsince\b[^.!?]{0,40}\bit'?s\s+(?:just\s+been|been\s+just|just)\s+me\b|"
    r"\bmy\s+(?:kids?|son|daughter|children|family|friends?|brother|sister|grandkids|grandchildren)\s+(?:never|don'?t|doesn'?t|hasn'?t|haven'?t|barely|hardly|rarely)\s+"
    r"(?:ever\s+)?(?:calls?|called|visits?|visited|texts?|texted|comes? (?:by|over|around)|checks? in|answers?|writes?)\b|"
    r"\b(?:all (?:of )?my friends|everyone i know|my friends)\s+(?:all\s+)?(?:moved (?:away|on)|have (?:kids|families|partners) now|are (?:all )?(?:married|gone)|left|"
    r"drifted (?:away|apart))\b|\b(?:drifted apart from everyone|lost touch with (?:everyone|everybody|all (?:of )?my friends|my friends))\b|"
    r"\b(?:no one|nobody|nothing)\s+(?:waiting (?:for me\s+)?at home|to come home to)\b|"
    r"\bi wish (?:someone|somebody|anyone)\s+would\s+(?:just\s+)?(?:hug|hold|call|ask|check|notice|listen|care|text)\b|"
    r"\bi'?m\s+(?:alone|by myself|on my own)\s+(?:a lot|most of the time|all the time|all day|every night|every day|so much|too much|again tonight)\b|"
    r"\bi miss having\s+(?:friends|people|someone|a (?:friend|partner|family|person))\b|\b(?:ain'?t|aint)\s+got\s+(?:nobody|no one|no friends)\b|"
    r"\bnadie me\s+(?:habla|llama|escribe|busca|entiende|quiere)\b|\bno tengo amigos\b|"
    r"\b(?:feel|felt|feeling|feels)\s+(?:so |really |very |completely |totally |just |pretty |kinda |kind of )?alone\b|\balone even (?:around|with|in a room|surrounded)\b|"
    r"\b(?:nobody|no one)\s+(?:ever\s+)?(?:texts|calls|messages|reaches out|checks in)(?:\s+(?:to\s+)?me)?\b(?!\s+(?:during|at|in|on|while|when|after|before|until)\b)|"
    r"\b(?:i|we)\s+(?:don'?t|dont|do not)\s+have\s+(?:anybody|anyone|a single (?:friend|person|soul)|any (?:real |close )?friends|a soul)\b(?!['’]s)|"
    r"\bi(?:'ve| have)?\s+(?:got|have|had)\s+(?:no one|nobody|no friends)\b(?!\s+to\s+(?:blame|thank|ask about|answer to))|"
    r"\bhaven'?t\s+(?:talked|spoken|said a word)\s+to\s+(?:anyone|anybody|a (?:single )?(?:soul|person))\b|\bhaven'?t\s+(?:seen|heard from)\s+(?:anyone|anybody)\s+(?:in|for|all)\b|"
    r"\b(?:eat|eating|ate)\s+(?:\w+\s+){0,2}(?:by myself|alone)\s+(?:every|again|most|all the)\b|"
    r"\bspent\s+(?:my|the|another)\s+(?:birthday|holidays?|christmas|thanksgiving|new year'?s?(?: eve)?|weekend|anniversary|valentine'?s(?: day)?)\s+(?:all\s+)?(?:alone|by myself|on my own)\b|"
    r"\b(?:house|apartment|place|home)\s+(?:is|feels|seems)\s+(?:so|too|really|just so|awfully)\s+(?:quiet|empty)\b|"
    r"\bdon'?t\s+know\s+(?:a single (?:person|soul)|anyone|anybody)\b(?=[^.!?]*\b(?:here|there|city|town|out here|school|work)\b)|\bdon'?t know a single (?:person|soul)\b|"
    r"\b(?:friends|they|everyone|everybody|people)\s+(?:all\s+)?(?:stopped|quit)\s+(?:inviting|calling|texting|including|checking on|reaching out to|talking to)\s+me\b|"
    r"\b(?:nobody|no one)\s+(?:ever\s+)?(?:checks\s+(?:on|in on|up on)|thinks about|remembers|notices|visits|invites|includes|gets|understands|wants|needs|sees|hears|listens to)\s+me\b|"
    r"\b(?:nobody|no one)\s+(?:ever\s+)?asks\s+(?:me\s+)?(?:how i(?:'m| am)|about (?:me|my day))\b|\b(?:ain'?t|aint)\s+nobody\s+(?:checking|looking|coming|calling|texting|worried|thinking)\b|"
    r"\bi\s+(?:feel|felt)\s+(?:so |really |just |kind of |kinda |pretty )?(?:invisible|left out|isolated|disconnected|unwanted|forgotten|out of place|excluded|unseen|unloved|"
    r"like (?:an outsider|a ghost|nobody|no one (?:sees|cares|notices)))\b|\b(?:so|really|pretty|very|kind of|kinda)\s+isolat(?:ing|ed)\b|"
    r"\bdon'?t\s+(?:fit in|belong)(?:\s+(?:anywhere|here|there))?\b|\b(?:always|only)\s+the one\s+(?:reaching out|who\s+(?:calls|texts|reaches out|makes plans|checks in))\b|"
    r"\bit'?s\s+(?:been\s+)?just me\b(?=[^.!?]*\b(?:tv|most nights|every night|a long time|these days|lately|and the (?:dog|cat))\b)|\bdon'?t\s+see\s+(?:anyone|anybody|a soul)\b|"
    r"\b(?:miss|want|need|wish i had|just want)\s+(?:having\s+)?(?:someone|somebody|anyone|a friend|a person|people)\s+to\s+(?:talk to|share|call|hang out with|be with|sit with|come home to)\b|"
    r"\bno one to\s+(?:share|call|turn to|lean on|sit with|eat with|celebrate with)\b|\bi wish i had\s+(?:friends|a friend|someone|somebody|anyone|people|a best friend)\b|"
    r"\beveryone(?:\s+else)?(?:\s+has|'s got|’s got|\s+has got)\s+(?:someone|somebody|a person|people|plans|friends)\b(?=[^.!?]*\b(?:except|but)\s+(?:me|i)\b)|"
    r"\b(?:holidays?|christmas|thanksgiving|weekends|nights|evenings|sundays)\s+(?:are|is|get|gets)\s+(?:so |really |the )?(?:hard|hardest|worst|rough|long|quiet)\b"
    r"(?=[^.!?]*\b(?:on (?:my|your) own|alone|by myself|by yourself|don'?t see|nobody|no one)\b)|"
    r"\bi'?m\s+by myself\s+(?:all day|all the time|every day|most days|a lot|so much)\b|\b(?:now\s+)?there'?s nobody\b|\bnobody (?:out )?here\b|"
    r"\bme siento\s+(?:muy |tan |bien |super )?sol[oa]\b|\bestoy\s+(?:muy |tan )?sol[oa]\b|\bno tengo a nadie\b", re.I)
OVERWHELMED = re.compile(
    rf"\b{I}\s+{VERY}(?:overwhelmed|swamped|drowning|burn(?:ed|t) out|fried|at my limit|at (?:my|the) breaking point|stretched (?:so |too )?thin|stressed|"
    rf"stressed out|falling apart|barely (?:holding|keeping) (?:it|on|up)|spiraling|spiralling)\b|\b(?:it'?s|its|this is|everything is) (?:all |just )?too much\b|"
    r"\bcan'?t keep up\b|\bat my limit\b|\bbreaking point\b|\bdrowning (?:in|at)\b|"
    r"\b(?:too|so|way too)\s+much on my plate\b|\bhaven'?t slept\b(?=[^.!?]*\b(?:days|week|weeks|nights)\b)|\brunning on (?:empty|fumes|no sleep)\b|"
    rf"\b{I}\s+(?:so|completely|totally|just so|beyond)\s+(?:exhausted|drained|worn out|wiped out)\b|"
    r"\bcan'?t\s+(?:pay|afford|make)\s+(?:rent|my rent|the rent|the bills|my bills|the mortgage|ends meet)\b|"
    r"\bbehind on\s+(?:rent|my rent|the rent|bills|my bills|the mortgage|payments|everything)\b|\b(?:buried|drowning) in (?:debt|bills)\b|"
    r"\b(?:everything|it all|things)\s+(?:is|are|keeps?)\s+piling up\b|\bend of my (?:rope|tether)\b|\bat my wit'?s end\b|\baren'?t enough hours in the day\b|\beverything (?:at once|is falling apart)\b|\bcan'?t (?:do|handle|take) "
    r"(?:this|it|any more|anymore)\b(?=.*\b(?:work|deadline|kids?|school|bills|job|week|exams?)\b)", re.I)
DISAPPOINTED = re.compile(
    r"\b(?:didn'?t|did not) get (?:the|that|my|in\b|it\b|into|accepted|picked|chosen|hired|a callback|an offer)\b|\b(?:went|going|gone) with someone else\b|"
    r"\b(?:picked|chose|hired) someone else\b|\bi (?:failed|flunked|bombed|blew)\b(?! (?:to\b|at being))|\bgot (?:rejected|turned down|passed over|cut from|"
    r"laid off|let go|fired|denied|waitlisted)\b|\b(?:fell|falling) through\b|\b(?:didn'?t|did not) make (?:the (?:team|cut|list)|it (?:onto|into) the)\b|"
    r"\blost my job\b|\b(?:they|he|she) (?:said|told me) no\b|\bdidn'?t (?:pass|qualify|win)\b|\b(?:so|really) disappointed\b|\bgot my hopes up\b|"
    r"\b(?:application|loan|visa|claim|appeal|request|offer|proposal|manuscript|submission)\s+(?:was|got|has been)\s+(?:denied|rejected|declined|turned down)\b|"
    r"\b(?:another\s+)?rejection\s+(?:letter|email)\b|\banother rejection\b|\bgave\s+(?:the|my)\s+(?:job|promotion|role|part|spot)\s+to\s+(?:someone else|him|her)\b|"
    r"\b(?:my|our)\s+(?:business|shop|store|restaurant|company|startup)\s+(?:is failing|failed|went under|is going under|closed down|is closing)\b|"
    r"\b(?:ivf|the transfer|the treatment|the chemo)\s+didn'?t\s+(?:work|take)\b", re.I)

# -- fed up: not a wound, a gripe. A friend is on their side and asks what happened ---------------------------------------------
FED_UP = re.compile(
    rf"\b{I}\s+{VERY}(?:fed up|annoyed|irritated|frustrated|pissed(?: off)?|mad\b(?! (?:about how|at how) (?:good|cute))|angry|furious|livid|heated|aggravated|fuming|seething|"
    rf"over it|so done\b(?! with the)|done with (?:this|it|him|her|them|everything|everyone|people|all of it)|sick of|sick and tired|tired of)\b|"
    r"\b(?:so|really|super|hella|beyond)\s+(?:annoyed|irritated|frustrated|pissed|fed up|over it)\b|"
    r"\b(?:is|are|was|were|keeps?|been)\s+driving me\s+(?:crazy|nuts|insane|up the wall|mad|bananas|bonkers)\b|"
    r"\bi\s+(?:can'?t|cannot)\s+stand\s+(?:my|this|that|these|those|him|her|them|how|when|it when|people)\b|"
    r"\bi\s+(?:really |fucking |freaking |absolutely |just |lowkey )?hate\s+(?:my (?:job|boss|manager|landlord|roommates?|commute|coworkers?|school|class|professor|teacher|schedule|shift|"
    r"apartment|neighbou?rs?)|it here|this (?:job|place|city|town|school|class|week|day)|working (?:here|there|retail|nights|weekends)|people|everyone)\b|"
    r"\b(?:work|today|my day|this week|my shift|school|the meeting|class|my morning|tonight|this morning)\s+(?:was|is|has been|'s been)\s+"
    r"(?:a |an |such a |the |an absolute |a total |a complete |so |just |really )?(?:nightmare|disaster|mess|joke|worst|hell|awful|terrible|horrible|brutal|rough|trash|garbage|"
    r"shit|a lot|too much|exhausting|miserable|chaos|draining)\b|"
    r"\b(?:customers?|clients?|drivers|coworkers?|my\s+(?:boss|manager|coworkers?|landlord|roommates?|neighbou?rs?|in-?laws|mother-in-law|ex|professor|teacher|supervisor))\s+"
    r"(?:was|were|is|are)\s+(?:so |being |such |so damn |really |just |being so )?(?:an? )?(?:awful|rude|the worst|terrible|horrible|impossible|ridiculous|unbearable|nightmare|nasty|"
    r"disrespectful|out of line|on my (?:case|ass|back|nerves)|at it again|jerks?|assholes?|idiots?|unreasonable|useless|incompetent)\b|"
    r"\bi'?ve had\s+(?:it|enough)\b|\b(?:about to|gonna|going to|ready to)\s+(?:lose it|lose my (?:mind|shit|temper|patience)|snap|scream|explode|walk out)\b|"
    r"^\W*(?:ugh+|argh+|grr+)\b|\b(?:can|could) you believe\s+(?:he|she|they|that|this|the|my)\b(?![^.!?]*\b(?:already|how (?:fast|good|cute|big|cheap))\b)|"
    r"\b(?:had|has|have) the\s+(?:audacity|nerve|gall)\b|\bthe (?:audacity|nerve) of\b|"
    r"\b(?:nobody|no one)\s+(?:ever\s+)?(?:appreciates|helps|listens|respects|notices|thanks me|says thank you)\b|"
    r"\bi do everything\b(?=[^.!?]*\b(?:around here|myself|alone|nobody|no one)\b)|"
    r"\b(?:he|she|they|my \w+)\s+(?:never|doesn'?t ever|don'?t ever)\s+(?:listens?|helps?|asks?|does anything|lifts? a finger|shows? up|calls? back|texts? back|answers?|cleans?|pays?)\b|"
    r"\b(?:wrote me up|got written up|got (?:yelled|screamed) at|got chewed out|got blamed|yelled at me|screamed at me|blamed me|threw me under the bus|"
    r"took (?:the |all the )?credit for my|talk(?:s|ed)? down to me|disrespected me|cut my hours|docked my pay|keeps? changing my (?:schedule|shifts?|hours))\b|"
    r"\b(?:parking|speeding) ticket\b|\b(?:the\s+)?(?:airline|landlord|bank|dealership|contractor|insurance(?: company)?|cable company|post office)\s+"
    r"(?:lost|cancell?ed|overcharged|double[- ]charged|denied|messed up|screwed up|broke|ruined|delayed|towed|charged me|raised|won'?t|refuses?)\b|"
    r"\b(?:need|needed|have|got|want|wanna|gotta)\s+to\s+(?:vent|rant)\b|\b(?:can|may|could)\s+i\s+(?:just\s+)?(?:vent|rant|complain)\b|\blet me\s+(?:vent|rant)\b|"
    r"\b(?:this|it)\s+is\s+(?:so |just |fucking |freaking |absolutely |beyond |honestly )?(?:ridiculous|unbelievable|unfair|bullshit|infuriating|unacceptable|outrageous|maddening|"
    r"frustrating|annoying)\b|\b(?:it'?s|that'?s|this is)\s+(?:so |just )?(?:not fair|unfair)\b|\bi\s+(?:can'?t|cannot)\s+with\s+(?:this|these|him|her|them|people|today)\b|"
    r"\b(?:had|having|been|it'?s been|what)\s+(?:a|an|such a|the|one of those)\s+(?:really |very |super |pretty |so )?(?:rough|bad|hard|long|terrible|awful|horrible|shitty|crappy|"
    r"tough|brutal|exhausting|stressful)\s+(?:day|week|night|morning|shift|month)\b|"
    r"\b(?:been\s+)?on hold for\b|\b(?:flight|train|bus|appointment|order|package|delivery|interview|shift|reservation|trip)\s+(?:got|was|has been|keeps getting)\s+"
    r"(?:cancell?ed|delayed|rescheduled|lost|bumped|pushed back)\b|"
    r"\b(?:made|making|makes)\s+me\s+(?:stay late|work (?:late|the weekend|weekends|saturday|sunday|overtime|a double)|come in on|redo|cover (?:for|his|her|their))\b|"
    r"\b(?:ate|took|used|borrowed|broke|lost|wore|stole|drank|finished|moved|threw (?:out|away))\s+my\s+\w+(?:\s+\w+)?\s+(?:again|without asking|without telling me)\b|"
    r"\b(?:sat|stuck)\s+in traffic\b|\btraffic\s+(?:was|is)\s+(?:insane|awful|terrible|a nightmare|horrible|brutal|hell|the worst)\b|\bmicromanag\w+\b|"
    r"\b(?:keeps?|kept|won'?t stop)\s+(?:interrupting|ignoring|blaming|yelling at|nagging|criticizing|correcting|bothering|harassing|pressuring|guilt[- ]tripping|talking over|"
    r"lying to|cancell?ing on|flaking on)\s+me\b|\b(?:nothing|everything)\s+(?:went|is going|has gone|keeps going|that could go)\s+(?:right|wrong)\b|"
    r"\bone thing after another\b|\bwhen it rains it pours\b|\bcan'?t catch a break\b|"
    r"\b(?:work|school|my job|this job|today|everything|my (?:boss|manager|landlord|schedule|commute|week|day))\s+suck(?:s|ed)\b(?!\s+me)|"
    r"\b(?:denied|rejected|refused)\s+my\s+(?:claim|request|vacation|pto|time off|application|appeal|refund|leave)\b|"
    r"\b(?:screwed (?:me|us) over|ripped (?:me|us) off|got (?:scammed|ripped off|screwed over|screwed|robbed|overcharged))\b|\bwhy do i (?:even )?(?:bother|try)\b|"
    r"\b(?:changed|moved|pushed|bumped)\s+(?:the|my)\s+(?:deadline|schedule|shift|meeting)\s+(?:up\s+)?(?:on me|again|last minute)\b|"
    r"\bsick to death of\b|\bhad it up to here\b|\b(?:nobody|no one)\s+(?:even\s+)?(?:said|says)\s+(?:thanks|thank you)\b", re.I)

# -- the good ones, and missing --------------------------------------------------------------------------------------------
_WHO = rf"(?:i|we|he|she|they|{ONE})"
_NOW = r"(?:just\s+|finally\s+|actually\s+|officially\s+)?"
_TESTS = (r"(?:test|tests|exam|exams|boards|bar|quiz|class|classes|course|interview|inspection|audit|road test|driving test|finals?|midterms?|certification|"
          r"nclex|mcat|lsat|gre|ged|sat|physical|background check|probation)")
RELIEVED = re.compile(
    r"\b(?:such a|what a|huge|so much|a big|a huge) relief\b|\bso relieved\b|\bfinally over\b|\bcan finally breathe\b|\bweight off\b|"
    r"\bthank (?:god|goodness|the lord)\b(?=[^.!?]*\b(?:over|done|behind (?:me|us)|okay|ok|fine|safe|negative|benign|clear|made it|worked out|found (?:him|her|it|them))\b)|"
    r"\b(?:biopsy|tumou?r|lump|scan|mri|tests?|results?|bloodwork|x-?rays?|mammogram|labs?)\s+(?:was|were|is|are|came back|come back|turned out)\s+"
    r"(?:benign|negative|clear|clean|normal|fine|good|okay|ok)\b|\bit'?s benign\b|"
    r"\bcoming home from the hospital\b|\b(?:out of|left)\s+(?:the\s+)?(?:icu|hospital|surgery)\b|\bgot discharged\b|"
    r"\bhome\s+(?:safe|from (?:deployment|the hospital|rehab|overseas|basic training|the nicu))\b|"
    r"\b(?:they|we|someone|the police)\s+found\s+(?:my|our)\s+(?:dog|cat|kitten|puppy|pet|son|daughter|kid|little (?:boy|girl))\b|"
    r"\b(?:he|she|they)(?:'s|'re|’s|\s+is|\s+are)\s+(?:going to be|gonna be)\s+(?:okay|ok|fine|alright|all right)\b|"
    r"\b(?:he|she)(?:'s|’s|\s+is)\s+(?:safe|stable|awake|recovering|out of the woods)\b|"
    r"\b(?:surgery|operation|procedure|transplant)\s+(?:went\s+(?:really |so |very )?(?:well|great|perfectly|smoothly|fine)|was a success)\b", re.I)
PROUD = re.compile(
    r"\bi finally\s+(?:ran|did|finished|quit|told|asked|went|got through|made it through|paid off|cleaned|passed|called|started|learned|beat|said)\b|"
    r"\b(?:\w+\s+)?(?:days?|weeks?|months?|years?)\s+(?:sober|clean|smoke[- ]free|without (?:a drink|smoking|drinking))\b|"
    r"\b(?:i'?ve|i have|i'?m|we'?ve|he'?s|she'?s)\s+(?:been\s+|stayed\s+)?(?:sober|clean|smoke[- ]free|drug[- ]free)\s+(?:for|since)\b|"
    r"\bfor the first time in\s+(?:years|months|weeks|forever|a long time|my life|ages)\b|\bproud of myself\b|\bi (?:did it|actually did it|pulled it off)\b|"
    r"\bfinished my (?:degree|thesis|book|first|marathon|training|dissertation|apprenticeship)\b|\bpersonal (?:best|record)\b|\bpaid off (?:my|the|our)\b|\bi stood up (?:to|for)\b|"
    r"\b(?:ran|finished|completed|did|walked|swam)\s+(?:my|a|the|our)\s+first\s+(?:\w+\s+){0,2}(?:marathon|5k|10k|race|triathlon|mile|lap|pull[- ]?up|open mic|show|gig|shift|solo)\b|"
    r"\b(?:made|got|had|booked|landed|signed)\s+(?:my|our|its|his|her|their)\s+first\s+(?:sale|client|customer|order|booking|paycheck|commission|gig|subscriber|review)\b|"
    r"\b(?:hit|reached|met|crushed|smashed|beat)\s+(?:my|our|his|her|the)\s+(?:\w+\s+){0,2}(?:goal|target|record|quota|milestone)\b|"
    r"\b(?:lost|dropped|down)\s+(?:\d+|[a-z]+)\s+(?:pounds|lbs|kilos|kg|stone)\b|"
    r"\b(?:finished|done with|completed|rang the bell)\s+(?:my\s+)?(?:last\s+(?:round|day|session)\s+of\s+)?(?:chemo|radiation|treatment|rehab|physical therapy)\b|"
    r"\blast\s+(?:day|round|session|treatment)\s+of\s+(?:chemo|radiation|treatment|dialysis|physical therapy)\b|\bi\s+made it through\s+(?:my|the|a)\s+(?:first|whole|entire|last)\b|"
    r"\b(?:sold|published|released|launched|opened|recorded)\s+(?:my|our)\s+(?:first|own)\s+\w+", re.I)
JOY = re.compile(
    rf"\b{_WHO}\s+{_NOW}(?:got|landed|scored|earned|received|won)\s+(?:the|a|an|my|our|his|her|their)\s+(?:dream\s+|new\s+|first\s+|full\s+)?(?:job|offer|promotion|position|"
    rf"role|part|lead|raise|bonus|scholarship|ride|grant|loan|visa|green card|citizenship|license|driver'?s license|permit|degree|diploma|transfer|internship|apprenticeship|"
    rf"contract|house|apartment|award|trophy|medal)\b|"
    rf"\b{_WHO}\s+{_NOW}got the keys to\s+(?:my|our|his|her|their|the)\s+(?:\w+\s+)?(?:apartment|house|place|home|condo|car|truck|shop|store|office|studio)\b|"
    rf"\b{_WHO}\s+{_NOW}got\s+(?:in\b(?=\s*[!.,]|\s*$|\s+to\s)|into\s+(?:college|school|uni|university|grad school|med school|law school|nursing school|the (?:program|academy|union|"
    rf"league|band|show|company)|(?:my|his|her|their|our)\s+(?:dream|first[- ]choice|top|number one)\s+\w+|(?:a|the|my|his|her|their)\s+(?:\w+\s+)?(?:college|school|university|"
    rf"program|residency|conservatory|cohort|fellowship)))|"
    r"\b(?:got|was|were|been|is|are)\s+(?:accepted|approved|promoted|hired|chosen|selected|published|nominated|cleared)\b|\bgetting\s+(?:published|promoted|married)\b|"
    r"\b(?:they|he|she)\s+accepted\s+(?:my|our)\s+offer\b|\b(?:they|he|she|[a-z]+)\s+offered me\s+(?:the|a|an)\s+(?:job|position|role|spot|place|promotion|contract|scholarship|"
    r"internship|part)\b|\b(?:adoption|sale|loan|deal|offer|paperwork|transfer|application|visa|mortgage|closing|settlement)\s+(?:finally\s+|just\s+)?went through\b|"
    r"\b(?:i'?m|i am|we'?re|we are)\s+(?:officially\s+|finally\s+|now\s+|going to be\s+|gonna be\s+|about to be\s+)(?:an?\s+)?(?:homeowners?|dad|mom|father|mother|grandma|grandpa|"
    r"grandmother|grandfather|aunt|uncle|parents?|grandparents?|graduate|doctor|nurse|citizens?|published author|business owner|debt[- ]free|cancer[- ]free|done with (?:school|chemo))\b|"
    r"\b(?:i'?m|i am)\s+(?:an?\s+)(?:dad|mom|father|mother|grandma|grandpa|aunt|uncle|homeowner)\s*!|"
    r"\b(?:my|our)\s+(?:\w+\s+)?(?:son|daughter|sister|brother|best friend|mom|dad|kid|grandson|granddaughter|niece|nephew)\s+(?:is|'s)\s+(?:getting married|engaged|pregnant|"
    r"having a baby|expecting|graduating|cancer[- ]free|in remission)\b|\bi'?m\s+(?:finally\s+)?graduating\b|"
    r"\bmoving into\s+(?:our|my)\s+(?:new|first|own)\s+(?:house|home|place|apartment|condo)\b|\basked me to marry\s+(?:him|her|them)\b|"
    r"\bguess who(?:'s|\s+is)?\s+(?:just\s+)?(?:got|a|an|officially|finally|going)\b(?!\s+(?:at|on|in)\b)|\b(?:can'?t stop smiling|happy tears|dream come true|on top of the world)\b|"
    r"\b(?:i'?m|we'?re)\s+(?:so|really|super)\s+proud of\s+(?:my|him|her|them|our)\b|^\W*it'?s official\b|"
    r"\b(?:promotion|raise|offer|transfer|adoption|visa|loan|approval|scholarship|acceptance)\s+(?:came through|is official|got approved|was approved)\b|"
    r"\b(?:we'?re|i'?m|we are|i am)\s+(?:finally\s+|officially\s+|actually\s+)?(?:having a baby|pregnant|engaged|expecting\b(?! (?:a|an|the|to|it|him|her|them|some|you))|getting married|cancer[- ]free|in remission|"
    r"debt[- ]free|moving in together|adopting)\b|\bgot\s+(?:engaged|married)\b|\b(?:he|she|they)\s+proposed\b|"
    r"^\W*(?:omg[,! ]*|guess what[,! ]*)?(?:she|he|they) said yes\b|\basked\s+(?:her|him|them)\s+(?:out|to (?:marry me|prom|the dance))\s+and\s+(?:she|he|they)\s+said yes\b|"
    rf"\bi\s+{_NOW}graduated\b|\b(?:closed on|bought|signed the lease (?:on|for)|moved into)\s+(?:the|our|my|a)\s+(?:first\s+|new\s+|own\s+)?(?:house|home|apartment|place|condo)\b|"
    r"\b(?:was|were)\s+born\s+(?:this|today|yesterday|last night|on|at)\b|\bhad\s+(?:her|the|their|our|a healthy)\s+(?:baby|twins|son|daughter|little (?:boy|girl))\b(?!\s+shower)|"
    r"\bit'?s a (?:boy|girl)(?=\s*[!.]*\s*$|\s*!)|\b(?:took|taking)\s+(?:his|her|their)\s+first steps\b|\bsaid\s+(?:his|her|their)\s+first word\b|"
    rf"\b{_WHO}\s+{_NOW}made\s+(?:the|it (?:onto|on|to) the)\s+(?:\w+\s+)?(?:team|cut|squad|finals|playoffs|honor roll|dean'?s list|shortlist|varsity)\b|"
    rf"\b(?:i|we)\s+{_NOW}(?:passed|aced)\s+(?:my|the|it|all my|both|all of my)?\s*(?:\w+\s+){{0,2}}{_TESTS}\b|\bpassed\s+(?:my|the|all my|both)\s+(?:\w+\s+){{0,2}}{_TESTS}\b|"
    r"\bi\s+(?:passed|did it|got it)\s*!+\s*$|\bi\s+(?:aced|nailed|crushed)\s+(?:it|the|my)\b|"
    r"\b(?:i|we|he|she|they)\s+won(?!['’]t)\b(?!\s+(?:t|der)\b)|\bfirst place\b|\bgold medal\b|\b(?:came|come) back clear\b|\b(?:cancer[- ]free|in remission|all clear)\b|"
    r"\b(?:best|happiest)\s+(?:day|news|week)\s+(?:ever|of my life)\b|"
    r"\b(?:i'?m|i am|we'?re|we are)\s+(?:so|super|really|beyond|just so)\s+(?:happy|excited|thrilled|stoked|pumped|hyped)\b|\bover the moon\b|\bon cloud nine\b|"
    r"\b(?:i|we)(?:'ve| have|'ve got| got)\s+(?:some\s+|a bit of\s+)?(?:good|great|big|amazing|exciting|wonderful|the best|happy)\s+news\b|"
    r"^\W*(?:good|great|big|huge|amazing|exciting|wonderful|happy)\s+news\s*[!:,.]|"
    r"\bjust\s+(?:adopted|closed on|signed the lease|got back from our honeymoon)\b|"
    r"\b(?:first day|interview|audition|presentation|date|opening night|recital|show|performance|meeting|pitch)\s+(?:[a-z]+\s+){0,4}went\s+(?:really |so |super |very )?"
    r"(?:well|great|perfectly|amazing|smoothly)\b|\b(?:hit|celebrat\w+|made it to)\s+(?:our|my|their)\s+(?:\d+\w*|[a-z]+)\s+(?:wedding\s+)?anniversary\b|"
    r"\b(?:we'?re|i'?m|we are|i am)\s+(?:getting|adopting)\s+(?:a|an|another)\s+(?:puppy|kitten|dog|cat)\b", re.I)
MISSING = re.compile(r"\bi (?:really |just |still |do )?miss\s+(?:my|our|him|her|them|home|how|when|those|that|the (?:old|way)|being|having|you\b)|\bhomesick\b|"
                     r"\bwish (?:i|we) could go back\b|"
                     rf"\bwish\s+(?:my|our)\s+{_ADJ}(?:{KIN}|{PET})\s+(?:was|were|could be|could have been|could'?ve been|had been)\s+(?:still\s+)?(?:here|there|around|alive)\b", re.I)
ASKS_FOR = re.compile(r"\?|\b(?:what|how) (?:do|should|can|would|could) i\b|\bshould i\b|\bany (?:advice|ideas|tips|suggestions)\b|\bwhat (?:would|do) you\b|\bhelp me\b|"
                      r"\b(?:can|could|would|will) (?:you|u)\b|\bi need (?:advice|help|ideas)\b|\bquiz me\b|\bremind me\b|\btell me (?:what|how)\b", re.I)
ASKING = re.compile(r"^\W*(?:what|how|where|which|who|should|do you|does|can you|could you|is it|are there|any (?:ideas|tips)|when (?:do|does|should|is))\b", re.I)

SMALL = re.compile(r"\b(?:a little|a bit|a tad|kinda|kind of|sort of|sorta|slightly|a touch|somewhat|lowkey)\b", re.I)
BIG = re.compile(r"\b(?:so so|really really|can'?t (?:breathe|stop|sleep|eat|think|function)|completely|absolutely|utterly|devastated|destroyed|"
                 r"shattered|wrecked|falling apart|worst|unbearable|sobbing|bawling)\b|!{2,}|😭|💔|\b(?:SO|REALLY|CAN'?T|NEVER|HATE)\b")
TODAY = re.compile(r"\b(?:today|tonight|this (?:morning|afternoon|evening)|last night|just now|an hour ago|yesterday|just\b)", re.I)

FAMILIES = {  # family: (need, heavy, why)
    "grief": ("company", True, "they're talking about a loss"),
    "heartbreak": ("their side", True, "their heart just got broken"),
    "fear": ("steadying", True, "they're scared"),
    "shame": ("kindness", True, "they're being hard on themselves"),
    "hurt": ("their side", True, "someone hurt them"),
    "low": ("company", True, "they're feeling low"),
    "lonely": ("company", True, "they're feeling alone"),
    "overwhelmed": ("steadying", True, "they're overwhelmed"),
    "disappointed": ("company", True, "they just got bad news"),
    "relieved": ("relief", False, "they're relieved"),
    "proud": ("cheer", False, "they did something hard"),
    "joy": ("cheer", False, "they have good news"),
    "missing": ("company", False, "they're missing someone"),
    "fed up": ("their side", False, "they're venting"),
}
GOOD = {"joy", "proud", "relieved"}
ALWAYS_HEAVY = {"grief", "heartbreak", "shame", "hurt"}  # the rest are only heavy when they're clearly felt, not "a little nervous"
ORDER = [("heartbreak", HEARTBREAK), ("fear", FEAR), ("shame", SHAME), ("hurt", HURT), ("lonely", LONELY), ("low", LOW), ("overwhelmed", OVERWHELMED),
         ("disappointed", DISAPPOINTED), ("fed up", FED_UP), ("relieved", RELIEVED), ("proud", PROUD), ("joy", JOY), ("missing", MISSING)]


def not_a_loss(text):
    """A death word that isn't about a death: a phone that died, "I'm dead" at a joke, a character in a show, a what-if."""
    said = str(text or "")
    return bool(NOT_A_DEATH.search(said) or NOT_REAL.search(said))


def _negated(said, start):
    """ "i'm not sad", "i wasn't scared": the feeling word comes right after a not."""
    return bool(re.search(rf"\b{NOT}\s+(?:\w+\s+){{0,2}}$", said[max(0, start - 28):start], re.I))


def _families(said):
    """Every feeling in it, the one that matters most first."""
    found = []
    if not not_a_loss(said) and any(pattern.search(said) for pattern in GRIEF):
        found.append("grief")
    if NOT_REAL.search(said):
        hit = FEAR.search(said)  # "what if it's cancer" isn't a what-if about a loss: it's a worry they have right now
        return found + (["fear"] if hit and not _negated(said, hit.end()) and not found else [])
    for family, pattern in ORDER:
        hit = pattern.search(said)
        if not hit or _negated(said, hit.end() if family in ("fear", "shame", "low", "overwhelmed") else hit.start()):
            continue
        if family in GOOD and ASKING.search(said):
            continue  # "what do you get someone who just got engaged" is a question, not their news
        if family == "fed up" and LAUGHING.search(said):
            continue  # "that's ridiculous lol" is a laugh
        found.append(family)
    return found


def read(text):
    """The feeling in one message, as a close friend would name it, or None for plain talk."""
    said = " ".join(str(text or "").split())
    if not said:
        return None
    low = said.lower()
    found = _families(low)
    if not found:
        return None
    family = found[0]
    need, heavy, why = FAMILIES[family]
    strength = 1 if SMALL.search(low) else 3 if (BIG.search(said) or (family == "grief" and TODAY.search(low))) else 2
    if family not in ALWAYS_HEAVY:
        heavy = heavy and strength >= 2 and not (family != "grief" and LAUGHING.search(said))
    elif family == "shame" and LAUGHING.search(said):
        heavy = False  # "i'm such an idiot lol", "i hate myself for eating that whole pizza lol": said with a laugh, it's a joke at their own expense
    who = WHO.search(low) if family in ("grief", "missing", "fear") else None
    also = next((f for f in found[1:] if (f in GOOD) != (family in GOOD)), "")  # glad and hurting at once, not two hurts
    return {"family": family, "strength": strength, "about": ("their " + who["who"]) if who else "", "need": need, "heavy": heavy, "also": also, "why": why}


# -- what the brain is told ------------------------------------------------------------------------------------------------
# One line each, short enough that a $250 device's brain is given all of it (luma.llm.prompts gives a small brain 200
# characters of this note). A loss keeps the words every run so far was measured with.
NO_JOKES = "No jokes, no teasing, no emoji laughs this turn."
PLAIN = "Be warm, plain and present, like a good friend."
FIRST = {
    "grief": PLAIN,
    "heartbreak": "Be on their side, warm and plain. No bright side yet, and don't explain the other person.",
    "fear": "Be calm and right there with them, in a few plain words. No \"don't worry\", no lecture.",
    "shame": "Be kind and plain. Don't agree with what they called themselves, and don't rush to fix it.",
    "hurt": "Be on their side first, warm and plain. Don't explain or defend the other person.",
    "low": "Keep them company, warm and plain. Don't try to fix it or cheer them up.",
    "lonely": "Be fully here with them first, warm and plain, like a good friend.",
    "overwhelmed": "Be calm and on their side, in a few plain words. One thing at a time; no list of tips.",
    "disappointed": "Be sorry with them first, warm and plain. No bright side, no next steps unless they ask.",
}
GLAD = {
    "joy": "They have good news: be happy with them right away, as big as they are. Then ask for the story. No advice, no caution.",
    "proud": "They did something hard and they're proud: tell them it's a big deal, because it is. Then ask how it felt. No advice.",
    "relieved": "They're relieved: be relieved with them, warm and easy. Don't bring the worry back up.",
    "missing": "They're missing someone or somewhere: be gentle. Let them tell you about it, and ask one small thing. No jokes unless they start.",
}


def note(felt, asked=False):
    """The line for the brain, or "" when there's nothing to say. asked: they also asked for something ("can you quiz me"),
    so the line stays plain and nothing in it argues with doing what they asked."""
    if not felt:
        return ""
    family, also = felt["family"], felt.get("also") or ""
    if also and not asked and (felt["heavy"] or family in GOOD):
        glad, hard = (family, also) if family in GOOD else (also, family)
        return (f"Read the room: two feelings at once ({FAMILIES[hard][2]}, and {FAMILIES[glad][2]}). No jokes or emoji laughs. "
                "Hold both: be glad with them, and gentle about the part that hurts.")
    if felt["heavy"]:
        return f"Read the room: {felt['why']}. {NO_JOKES} {PLAIN if asked else FIRST.get(family, PLAIN)}"
    return "" if asked else GLAD.get(family, "")
