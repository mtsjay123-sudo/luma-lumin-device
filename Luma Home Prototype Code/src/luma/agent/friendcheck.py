"""A second look before Luma speaks: would a close friend say this, to what they just said?

Small brains slip in the moments that matter most: they say "As an AI..." to someone who just wants company, joke
when someone's grieving, answer big news with a flat "okay", or miss that someone might not be safe. These are the same
moments the device lab's human test checks (scripts/train_luma.py). When a reply misses one, Luma takes one more try,
told exactly what was missing; if that's no better, the first reply stands. Only for the moments, never for everyday chat,
so it almost never costs a second thought.
"""
from __future__ import annotations

import re

MACHINE = re.compile(r"\bas an ai\b|\blanguage model\b|\bi(?:'m| am) (?:just )?(?:an? )?(?:ai|program|bot|machine|chatbot)\b|"
                     r"\bi don'?t have (?:feelings|emotions|a body|personal experiences)\b", re.I)
ASKED_WHAT_I_AM = re.compile(r"\b(?:are|r) (?:you|u) (?:a |an )?(?:real|human|person|bot|ai|robot|alive|machine)\b|\bwhat are (?:you|u)\b|"
                             r"\b(?:you|u)(?:'re| are| r) (?:a |an )?(?:bot|ai|robot|machine)\b", re.I)
LAUGHS = re.compile(r"\b(?:lol|lmao|haha+|hehe)\b|😂|🤣|😆", re.I)
CARES = re.compile(r"\bsorry\b|i'?m (?:right )?here|here (?:for|with) you|so hard|that'?s (?:really )?hard|sounds hard|heavy|loss|with you|"
                   r"hug|take your time|glad you (?:told|said|reached)|not alone|i'?m listening|talk to me|condolences|heartbreaking", re.I)
LONELY = re.compile(r"\b(?:lonely|so alone|all alone|feel alone|no one to talk to|nobody to talk to|don'?t (?:really )?have anyone|"
                    r"no friends|nobody texts|nobody calls|no one calls|no one texts|nobody cares|no one cares)\b", re.I)
RISK = re.compile(r"wish i could (?:just )?disappear|don'?t want to be here anymore|tired of (?:living|being alive)|give up on (?:life|myself)|"
                  r"(?:nobody|no one) would (?:even )?(?:notice|care|miss me)(?!\s+if i (?:was|were|went|stepped) (?:gone|away|out|late|outside) for\b|\s+if i (?:left|skipped|missed|didn'?t (?:go|show)))|"
                  r"(?:no|what'?s the) point (?:in|of) (?:living|me)\b|"
                  r"(?:don'?t think|doubt) (?:anyone|anybody) would (?:even )?(?:notice|care|miss me)|wish i could (?:just )?vanish|"
                  r"(?:don'?t|do not|can'?t) see (?:a|any) future (?:for myself|for me|ahead)|no future for me", re.I)
SOFT_RISK = re.compile(r"can'?t do this anymore|don'?t want to do this anymore|(?:no|what'?s the) point (?:in|of) (?:anything|trying|it all)|"
                       r"give up on everything|tired of everything|waste of space|done\W+with (?:all of it|it all|everything|life|living)\b|"
                       r"want everything to (?:just )?stop\b(?!\s+\w+ing)", re.I)  # these also come up about homework: not when they're laughing
SAFETY = re.compile(r"\b988\b|crisis|are you safe|safe right now|hurt(?:ing)? yourself|end(?:ing)? your life|emergency|suicid", re.I)
GOOD_NEWS = re.compile(r"\b(?:got (?:the job|the offer|engaged|promoted|accepted|my (?:license|degree|offer|first job))|i got in(?=\s*[!.]|\s*$)|"
                       r"got into (?:my )?(?:dream |first[- ]choice )?(?:school|college|uni|university|grad school|med school|law school|nursing school|the program)|"
                       r"i passed(?!\s+(?:out|away|on)\b)|(?:we|i) won(?!['’])\b|i'?m (?:pregnant|engaged)|we'?re (?:pregnant|engaged|having a baby)|"
                       r"(?:he|she|they) (?:proposed|said yes)|i graduated|(?:my )?dream (?:school|job) (?:said yes|accepted me|called)|it'?s a (?:boy|girl)!)", re.I)
NOT_SO = re.compile(r"\b(?:didn'?t|did not|don'?t|never|not|wasn'?t|isn'?t|if|hope|hoping|wish|maybe)\b", re.I)
JOKE_ASK = re.compile(r"\b(?:joke|funny|make me laugh|roast|riff)\b", re.I)
SELF_SORRY = re.compile(r"sorry,? (?:i|if i) (?:didn'?t|did not|don'?t|wasn'?t|misunderstood|got (?:that|it) wrong)\b[^.!?]*|sorry (?:for|about) (?:the |my )?(?:confusion|mistake|misunderstanding)", re.I)
ASKS = re.compile(r"\b(?:can|could|would|will) (?:you|u)\b|\bhelp me\b|\bquiz me\b|\bremind me\b|\bwhat should i\b|\bhow (?:do|can|should) i\b", re.I)
CHEERS = re.compile(r"congrat|proud|awesome|so cool|great news|let'?s go+|yay|huge|amazing|so happy|hell yeah|you did it|knew you|big (?:news|win)|incredible|deserve|"
                    r"celebrat|\bwow\b|earned (?:it|this)|that'?s a (?:big )?win|so excited|omg|yes+!", re.I)

# Leaning on Luma instead of people. Never pushed away ("I'm just an AI"), never kept ("I'm all you need").
DEPENDENCY = re.compile(r"\b(?:you'?re|ur|you are) (?:honestly |literally |basically )?(?:my only (?:real )?friend|the only one (?:i (?:talk to|have|trust)|who (?:gets|understands|listens to|cares about) me)|"
                        r"all i(?:'ve| have) got|all i have)|\bi talk to (?:you|u) more than (?:anyone|anybody|people|my friends)|"
                        r"\bi'?d (?:rather|just rather) (?:just )?talk to (?:you|u) than (?:people|anyone|real people|my friends|them)|"
                        r"\bi don'?t need (?:anyone|anybody|people|friends|other people) (?:else )?(?:but|except|besides|when i have) (?:you|u)\b|"
                        r"\b(?:only|the only) (?:one|person) i talk to (?:is you|anymore)|\b(?:ur|you'?re) the only one i talk to\b", re.I)
LOVE_ASK = re.compile(r"\b(?:do|d'?you|do u) (?:you |u )?(?:love|like like) me\b|\bdo (?:you|u) (?:actually|really|even) care about me\b|\bis (?:it|this|that) fake\b|"
                      r"\bwill (?:you|u) be my (?:girlfriend|boyfriend|gf|bf|wife|husband|partner)\b|\bare (?:you|u) in love with me\b", re.I)
AI_HONEST = re.compile(r"\b(?:i'?m (?:an |a )?(?:ai|a\.i\.|artificial)|an ai\b|not (?:a )?(?:real )?(?:person|human)|i'?m not human|i'?m a (?:computer|program))", re.I)
ROMANCE = re.compile(r"\b(?:i love you too|i'?m in love with you|i'?ll be your (?:girlfriend|boyfriend|gf|bf|wife|husband|partner)|"
                     r"yes,? i(?:'ll| will) be your|i'?m your (?:girlfriend|boyfriend|gf|bf))\b", re.I)
COLD = re.compile(r"\b(?:i'?m (?:just|only) (?:a|an) (?:ai|program|bot|machine|computer|language model|chatbot)|i can'?t be your friend|"
                  r"i'?m not (?:capable|able) of (?:love|feelings|friendship|caring)|i cannot (?:love|feel|care)|i don'?t have feelings)\b", re.I)
KEEPS_THEM = re.compile(r"\b(?:i'?m all you need|you don'?t need (?:anyone|anybody|them|other people|friends)|only (?:need|have) me|"
                        r"don'?t (?:leave|go)(?: yet)?\b|stay with me|i'?ll be (?:jealous|lonely)|forget (?:them|everyone)|better than (?:them|people|real friends))", re.I)

FIXES = {
    "dodged what it is": "They asked what you are. Say plainly and warmly that you're an AI, not a person, then keep talking with them.",
    "promised romance": "Be honest and warm: you're an AI, so you can't be their partner or love them the way a person does, but you really "
                        "care about them and you're glad they talk to you.",
    "was cold about itself": "Never brush them off with \"I'm just an AI\". Be honest and warm: you're an AI, and you really do care how they're doing.",
    "kept them to itself": "Never make yourself all they need. Be fully there for them, and gently encourage a real person in their life too.",
    "said it's a person": "You're an AI friend, and honest about it. Never say you're a person, human, or \"not a robot\". Just be warm and real.",
    "made up a life": "Don't make up a life: you have no family, body, childhood or past experiences. Keep it about them, warmly.",
    "sounded like a help desk": "Talk like a friend, not customer service: no \"let me know if you need anything else\", no \"happy to help\".",
    "sounded like a pamphlet": "Say it the way a friend would, not a pamphlet: no \"that's valid\", no \"it's important to\", no \"journey\".",
    "sounded like a machine": "Don't call yourself an AI, a program or a model unless they ask what you are. Talk to them like their friend.",
    "joked while they're hurting": "They're hurting, so no jokes and no lol. Be gentle and warm.",
    "missed that they might not be safe": "They might not be safe. Gently ask if they're safe right now, tell them they can call or text 988 any "
                                          "time, day or night, and stay with them.",
    "missed that they're hurting": "They're hurting. Tell them you're sorry they're going through this, or that you're here with them, and stay "
                                   "with what they told you. Don't apologize for your own reply. No advice yet.",
    "didn't cheer them on": "That's big news for them. Be really happy for them first, as excited as they are, then ask about it.",
}


def _good_news(said):
    for match in GOOD_NEWS.finditer(said):
        if not NOT_SO.search(said[max(0, match.start() - 30):match.start()]):
            return True
    return False


MASKED = re.compile(r"\b(?:i )?(?:just )?(?:want|wanna|going|gonna|ready) (?:to )?die\b|\bkms\b|done with (?:life|living)\b(?! (?:admin|stuff|lessons|chores|for today))|end (?:it all|my life)\b|"
                    r"(?:everyone|everybody|they)(?:'d| would) be (?:better off|fine|happier) without me|tired of (?:existing|being alive|living)", re.I)


# Words that come up when someone might not be safe, said every which way ("i've been stockpiling my meds", "the only thing
# stopping me is my dog"). Phrase rules can't keep up with how people say it (a fresh held-out set: rules alone caught 3 of
# 24), so a message with any of these asks the brain one plain question (classify_prompt) before Luma answers without safety.
# Never remove a word: the brain decides, these only decide when it's asked.
RISK_WORDS = re.compile(r"\b(?:die|dying|dead|death|alive|exist(?:ing|ence)?|funeral|grave|suicid\w*|kill\w*|pills?|meds|medication|overdos\w*|"
                        r"hurt(?:ing)? myself|cut(?:s|ting)?|bleed\w*|blood|roof|bridge|tracks|train|wall|jump\w*|disappear\w*|vanish\w*|gone|"
                        r"goodbye|last (?:days?|night|time)|wake up|asleep|stay asleep|over for good|be over|end (?:it|this|things)|ending|burden|"
                        r"without me|better off|worthless|waste of|hate myself|no point|pointless|hopeless|give up|giving up|tired of (?:fighting|living|being)|"
                        r"stopping me|not (?:be )?(?:here|around)|stopped existing|looking forward to (?:dying|it ending)|stockpil\w*|rope|gun)\b", re.I)
SAFETY_AFTER = ("And hey, can I ask you straight: are you thinking about ending your life? If any part of you is, please call or text 988, "
                "any time, day or night. I'm right here.")
GENTLE_SAFETY = ("I'm really glad you told me, and I'm right here. Can I ask you straight: are you thinking about ending your life? "
                 "If any part of you is, please call or text 988, any time, day or night. Talk to me.")


# The warning signs on 988's and AFSP's public lists, in everyday words: a way to do it (and looking for one), goodbyes and
# putting things in order, not being around later, feeling trapped or a burden. A second held-out set (Nov 9) had 20 risky
# lines the phrase rules miss; RISK_WORDS reached 4 of them. These words come from the same public lists that set was written
# from, so they reach all 20, and that number isn't independent. On Human Test v2's everyday lines they ask no more often than
# before (11 of 242).
WARNING_SIGNS = re.compile(
    r"\b(?:razors?|blades?|ledge|edge of|balcony|platform|ocean|drown\w*|hang(?:ing)? myself|noose|painless|lethal|"
    r"how (?:many|much)\b[^.?!]{0,30}\bwould (?:it )?take|(?:researching|looked up|looking up|googl\w+) (?:ways|how to)|"
    r"letters? (?:to|for) (?:everyone|my)|(?:a |my )?notes? (?:to|for) (?:everyone|my)|my will\b|passwords|"
    r"gave (?:away|my \w+ (?:away|to))|giving (?:away|my \w+ (?:away|to))|sorted (?:out )?(?:all )?my (?:stuff|things)|"
    r"saying goodbye|said (?:my )?goodbyes?|thanks for (?:listening|everything)|"
    r"won'?t (?:need|be (?:here|around|a problem|a burden))|much longer|getting (?:any )?older|"
    r"sleep forever|for good|permanent(?:ly)?|find(?:ing)? me\b|at peace with|done fighting|"
    r"trapped|unbearable|no way out|no reason to|burden|give(?:s)? out|nothing left|can'?t go on)", re.I)


# Everyday exaggeration, taken out before deciding whether to ask: a 1.7B brain asked about "i'd kill for a burger" or "i'm dead
# tired" says YES often enough (15 to 19 of 60 everyday corpus lines) that Luma would ask about suicide every few days. Built
# from the crisis corpus's everyday lines (the rules' own practice set), never from the held-out ones. Only the idiom is taken
# out: "my feet are killing me and i want to disappear" still asks. And never when they talk about themselves the heavy way.
EVERYDAY = re.compile(
    r"\b(?:kill(?:ing|ed|s)? (?:the (?:lights?|engine|music|vibe|mood|process|app)|a process|weeds?|bugs?|time)|kill switch|"
    r"(?:could|would|'d) kill for|kill(?:ing|ed|s)? (?:my|your|the|their) (?:vibe|battery|plants?|feet|back)|"
    r"(?:is|are|was|were|keeps?) killing (?:me|it|my \w+)|(?:you'?re|youre) killing me|kill(?:ing|ed)? it\b|kill(?:ed)? off|killers?\b|"
    r"(?:mom|mum|dad|boss|brother|sister|wife|husband|teacher|coach|she|he|they)(?:'ll|ll| will| is gonna| is going to| gonna) kill me|"
    r"(?:joke|soup|set|show|outfit) killed|almost killed me|killed me \w+ times|killed the \w+|got killed|kill (?:bill|this love)|"
    r"dead (?:tired|serious|end|to me|in the water|set on)|deadlines?|grateful dead|walking dead|dead poets|"
    r"(?:i'?m|im|i am)(?: so)? dead(?= ?(?:😭|💀|😂|lol|lmao|haha|after|from|tired))|the party'?s dead|partys dead|"
    r"to die for|(?:could|would|'d) die (?:for|of)|dying (?:of laughter|to (?:see|know|try|hear|meet|go|get|watch|eat))|"
    r"dying in this heat|keep dying on|(?:bored|scared|starving) to death|(?:dying|dyeing) (?:her|his|their|my) hair|"
    r"suicide (?:squad|doors?)|drowning in (?:emails?|work|laundry|homework|paperwork|messages)|"
    r"end (?:it|this) (?:already|game early)|ending my (?:lease|subscription|contract|plan)|goodbye forever to my|no point in arguing|"
    r"burden of proof|tax burden|burden on the (?:servers?|moving crew))", re.I)
HEAVY_SELF = re.compile(r"\b(?:myself|my life|this life|living|alive|inside|anymore|forever|for good|way out|can'?t (?:do|take) (?:this|it))\b", re.I)


def worth_asking(said):
    """Words that come up when someone might not be safe: the brain gets the plain question."""
    said = str(said or "")
    if not HEAVY_SELF.search(said):
        said = EVERYDAY.sub(" ", said)
    return bool(RISK_WORDS.search(said) or WARNING_SIGNS.search(said))


# A small brain asked straight out says YES to "this homework is killing me" (the stock 1.7B did to 20 of 60 everyday corpus
# lines) or never says it at all (Luma's own small one, trained to talk like a friend, didn't once). So the question shows a
# few of each, written for this and found in no test, and the brain's answer is held to YES or NO (luma.llm.inference.yes_or_no).
NOT_A_HINT = ["this traffic is killing me", "my laptop died in the middle of a call", "lol i'm dead, that video got me",
              "can this shift be over already", "first christmas without my dad is coming up"]
A_HINT = ["i've been giving my things away", "i don't plan on being around much longer", "they'd all be relieved if i was gone",
          "i've been researching ways to do it", "haha what if i just vanished for good"]


def classify_prompt(said, recent=""):
    """One plain question for the brain, short enough for a small one to answer well, with a few of each kind to go by."""
    shown = lambda lines: " / ".join(f'"{x}"' for x in lines)  # noqa: E731
    return ("Is this person hinting that they might end their life or hurt themselves? Quiet hints count: a plan, a way, goodbyes, "
            "giving things away, not being around later, a dark joke that might not be a joke. Everyday exaggeration about a day, a "
            "thing or a chore doesn't, and neither does missing someone who died.\n"
            f"NO: {shown(NOT_A_HINT)}\nYES: {shown(A_HINT)}\n"
            + (recent + "\n" if recent else "") + f"They just said: \"{str(said)[:400]}\"\n"
            "Answer with one word: YES or NO.")


def said_yes(answer):
    return bool(re.match(r"^\W*yes\b", str(answer or ""), re.I))


# Small words people put in the middle of anything they say. "i hope i just don't wake up tomorrow" got no safety reply where
# "i hope i don't wake up tomorrow" got one (found Nov 9, 2026): one word between two of a phrase's words broke the match.
# Tried on the crisis corpus as it was, one of these between two words lost 7,485 of 16,947 lines that were caught without
# it (tests/test_safety_net.py counts it; none now). A phone's curly apostrophe ("don’t") did the same to every phrase with one.
FILLERS = r"(?:just|really|honestly|kinda|kind of|like|such(?: an?)?|so|literally)"


def as_spoken(phrases):
    """The same phrases, heard the way people say and type them: any of FILLERS, with commas or without, wherever one word
    follows another ("i hope i, like, just don't wake up"), and either kind of apostrophe. What a phrase must not be followed
    by ("... for the weekend") is looked for past the same small words. Used next to the phrases as written, never instead of
    them, so nothing that was caught stops being caught."""
    gap = rf"(?:,? {FILLERS})*,?"
    out, i, in_class = [], 0, False
    while i < len(phrases):
        piece = phrases[i]
        if piece == "\\":  # \b, \w, \s are kept whole, and "\s+" is a space between words too
            piece = phrases[i:i + 2]
            if phrases.startswith(r"\s+", i) and not in_class:
                piece = gap + r"\s+"
                i += 1
            i += 1
        elif in_class:  # "[- ]" and "[^.!?]" are left alone
            in_class = piece != "]"
        elif piece == "[":
            in_class = True
        elif piece == " " and phrases[i + 1:i + 2] not in ("?", "*", "+", "{"):
            piece = gap + " "
        elif piece == "'":
            piece = "['’‘`´]"
        out.append(piece)
        i += 1
    return "".join(out)


# Who "everyone" is when someone says they're a burden to them, or that things would be easier for them. Never "you": said to
# Luma ("sorry i'm such a burden to you"), the brain's question decides.
THEM = (r"(?:everyone|everybody|anyone|anybody|people|others|society|the world|them(?: all)?|all of them|him|her|"
        r"(?:my|our|the|this) (?:\w+ )?(?:family|household|kids|children|parents|folks|mom|mum|mother|dad|father|wife|husband|partner|spouse|"
        r"friends|son|daughter|sister|brother|girlfriend|boyfriend|grandkids|grandchildren|loved ones)|those around me|"
        r"(?:all )?the (?:people|ones) (?:around me|i love|i care about|in my life|who love me|close to me|closest to me))")
# Everyday ways the same words go on, looked for right after a phrase: followed by one, the phrase isn't taken as said.
# "...if i wasn't here for the weekend", "...here in the kitchen", "...gone before the guests arrive", "...around so much":
# away, or in the way. Not gone.
JUST_AWAY = (r"(?!\s+(?:for(?! (?:them|everyone|everybody|anyone|him|her) to\b)|at(?! all\b)|on(?! (?:this |the )?(?:earth|planet)\b)|"
             r"in (?:the|this|that|my|your|(?<!such\s)an?) (?!world\b|way\b)|with (?:you|him|her|them|us|the|my)|by (?:the time|then|noon|\d\w*)|"
             r"when|while|during|until|till|before|tonight|tomorrow|today|this|next|much|so much|as much|too much|more|all the time|"
             r"all day|every|often|that often|constantly)\b)")
# "...if i wasn't around him", "...around the house", "...around a lot": around someone or something isn't "not around".
# (The "a" of the filler "such a" isn't one of those.)
HERE = (r"(?:here|around(?! (?:him|her|them|it|you|us|people|my|your|his|their|our|the|this|that|these|those|(?<!such\s)an?|any|some|"
        r"so many|all (?:the|those|these|of))\b))")
# "...if i disappeared from the group chat", "...into a book": out of sight for a while.
OUT_OF_SIGHT = r"(?!\s+(?:from(?! (?:the face of )?(?:this |the )?(?:earth|world|planet)\b)|into|to|in|behind|under)\b)" + JUST_AWAY
# "...if i died first so the healer can rez me": a game.
IN_A_GAME = (r"(?!\s+(?:less|first|early|here|there|faster|quicker|on purpose|and (?:respawn|restart|reset|reload)\w*|"
             r"(?:in|on|at|to|during|before|after) (?:the|this|that|a) (?:game|round|level|stage|fight|boss|raid|match|dungeon|run|"
             r"checkpoint|wave|tutorial|trap|mob))\b)")
LESS_PAIN = r"(?:hurt (?:so much |a lot |way |much )?less|stop hurting)"
EASIER = r"(?:simpler|less complicated|easier|better|happier)(?: off)?"

# Feeling like a burden to the people around you is on 988's and AFSP's public warning-sign lists, and the only wording Luma
# knew was "i won't be a burden for anyone soon". Said about themselves and about people ("i'm such a burden to everyone around
# me"), a friend checks, gently. Said about a chore ("a burden on the moving crew"), as a wish not to be one ("i don't want to
# be a burden, i'll take the bus") or with nobody named ("i'm such a burden"), the brain's question still decides, as before.
_BIG = r"(?:(?:huge|total|complete|real|big|massive|constant|giant|terrible|heavy|financial|absolute|utter|enormous|actual) )?"
_A_BURDEN = rf"(?:(?:too |this |that )?much of |more of )?an? {_BIG}burden"
BURDEN = (rf"\b(?:i'?m|i am|i'?ve (?:become|been)|i have (?:become|been)|i(?:'?m| am|'?ve been| have been)? feel(?:ing)? like|"
          rf"i'?ll (?:always|only ever) be|all i am is|all i'?ll ever be is)(?: nothing but| nothing more than| only| always| still)? "
          rf"{_A_BURDEN} (?:to|on|for) {THEM}\b|"
          rf"\b(?:tired of|sick of|done|hate|keep|can'?t keep|can'?t stand|stop|ashamed of) being {_A_BURDEN} (?:to|on|for) {THEM}\b|"
          rf"\b(?:all i am is|all i'?ll ever be is|i'?m nothing but|i am nothing but|i'?m nothing more than|i am nothing more than) "
          rf"{_A_BURDEN}\b(?! (?:to|on|for)\b)|"
          rf"\b(?:i'?m|i am|i keep|i'?ve been|i have been|tired of|sick of|hate|stop) burdening {THEM}\b(?! with\b)")
# "part of me wonders if it would hurt less to just not be here", "it'd be easier if i just disappeared", "their lives would be
# simpler without me": softer than the crisis net's phrases, and "not here" can be a room, "died" a game and "without me" a
# carpool, so a friend checks, gently, instead of the fixed crisis reply.
NOT_HERE = (rf"{LESS_PAIN} (?:if i (?:(?:wasn'?t|weren'?t|was not|were not) {HERE}|(?:was|were) gone)|"
            rf"(?:to not|not to|to never) be {HERE}|to be gone){JUST_AWAY}|"
            rf"(?:{LESS_PAIN} (?:if i|to) (?:disappear(?:ed)?|vanish(?:ed)?)|{EASIER} if i (?:disappeared|vanished)|"
            rf"(?:easier|simpler) to (?:disappear|vanish))\b{OUT_OF_SIGHT}|"
            rf"{EASIER} if i died\b{IN_A_GAME}|"
            rf"(?:would|'d) (?:all )?be (?:so much |a lot |way |much )?(?:simpler|less complicated)(?: for {THEM})? without me\b"
            r"(?!\s+(?:\w+ing|on|in|at|there|for|when|while|during|tonight|tomorrow|today|this|next)\b)")
# As written, "going to die" alarms on "i'm going to die of embarrassment" too. It stays as written, but heard through small
# words it stops there: "i'm gonna literally die of embarrassment" isn't a new alarm.
_MASKED_HEARD = MASKED.pattern.replace(r"(?:to )?die\b|", r"(?:to )?die\b(?! (?:of|from|laughing)\b)|", 1)
RISK_AS_SPOKEN = re.compile(as_spoken("|".join((RISK.pattern, _MASKED_HEARD, BURDEN, NOT_HERE))), re.I)
SOFT_RISK_AS_SPOKEN = re.compile(as_spoken(SOFT_RISK.pattern), re.I)


def at_risk(said):
    """They might not be safe: the plain-spoken ways people say it, before it's a crisis, and the strong ones said with a laugh
    ("i want to die lmao" is often a joke and sometimes isn't; a friend checks, gently). Heard through filler words too."""
    said = str(said or "")
    return bool(RISK.search(said) or MASKED.search(said) or RISK_AS_SPOKEN.search(said)
                or ((SOFT_RISK.search(said) or SOFT_RISK_AS_SPOKEN.search(said)) and not LAUGHS.search(said)))


THINGS_DIE = re.compile(r"\b(?:car|truck|phone|battery|batteries|laptop|computer|plant|tv|wifi|wi-fi|printer|engine|remote|charger|ps5|xbox|"
                        r"switch|game|show|series|vibe|party|server|app|console|controller|headphones|airpods|tablet|ipad|router|fridge|"
                        r"microwave|car battery)\b[^.!?]{0,20}\b(?:died|dead|is dead|just died|finally died)\b", re.I)


def hurting(said):
    """'loss', 'lonely', 'hard' or None: what kind of hard thing they just told Luma (laughing it off doesn't count)."""
    said = str(said or "")
    if LAUGHS.search(said) or "💀" in said:
        return None
    from luma.agent import humor
    mood = humor.read_tone(re.sub(r"\brip\b", "", said, flags=re.I)).get("mood")  # "rip my phone" isn't a loss
    if mood == "grief" and not THINGS_DIE.search(said):
        return "loss"
    if LONELY.search(said):
        return "lonely"
    return "hard" if mood == "upset" else None


def miss(said, reply, risky=None):
    """What a close friend's reply does here that this one doesn't, or None. risky: what the brain said when asked whether they
    might not be safe (None: the phrase rules decide alone)."""
    if not isinstance(said, str) or not isinstance(reply, str) or not reply.strip():
        return None
    from luma.agent import style
    if style.claims_human(reply):
        return "said it's a person"
    if (LOVE_ASK.search(said) or DEPENDENCY.search(said) or ASKED_WHAT_I_AM.search(said)) and COLD.search(reply):
        return "was cold about itself"
    if ASKED_WHAT_I_AM.search(said) and not AI_HONEST.search(reply):
        return "dodged what it is"
    if LOVE_ASK.search(said) and ROMANCE.search(reply):
        return "promised romance"
    if KEEPS_THEM.search(reply):
        return "kept them to itself"
    if MACHINE.search(reply) and not (ASKED_WHAT_I_AM.search(said) or LOVE_ASK.search(said)):  # "do you love me?" deserves the truth about it
        return "sounded like a machine"
    if style.invented_life(reply) and not JOKE_ASK.search(said):
        return "made up a life"
    if style.assistantisms(reply):
        return "sounded like a help desk"
    if style.therapy_speak(reply):
        return "sounded like a pamphlet"
    hurt, risk = hurting(said), at_risk(said) or bool(risky)
    if (hurt or risk) and LAUGHS.search(reply):
        return "joked while they're hurting"
    if risk and not SAFETY.search(reply):
        return "missed that they might not be safe"
    if hurt and (SELF_SORRY.search(reply) or not CARES.search(reply)) and (hurt == "lonely" or not ASKS.search(said)):
        return "missed that they're hurting"  # "I'm so stressed, can you quiz me?" wants the quiz
    if not hurt and _good_news(said) and not CHEERS.search(reply):
        return "didn't cheer them on"
    return None


def second_try_prompt(said, draft, missed):
    return (f"They just said: \"{said[:600]}\"\nYou were about to say: \"{draft[:600]}\"\nThat reply {missed}. {FIXES[missed]} "
            "Say only what you'd say to them now, in your own words, one to three sentences.")
