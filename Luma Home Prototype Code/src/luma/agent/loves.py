"""What they love doing, and when a friend brings it back.

Early on they say "back home I was in a choir". Ten minutes later: "I've got nothing to do tonight." A friend puts the
two together ("is there a choir near you?"). A brain mostly doesn't: it offers a movie and a walk. This does the putting
together, by rules, and hands the brain one line.

- said(text): the thing they told you they love doing, in their own words, or "".
- at_a_loose_end(text): they don't know what to do with themselves, or they want people around.
- note(text, earlier, interests): the one line for the brain on that turn, or "".

It never brings back what they're better off without (drinking, smoking, gambling, an ex), what they can't do any more,
or what they did with someone they lost. And it says nothing when they might not be safe or are hurting: then being
there comes first (luma.agent.feelings).
"""
import re

from luma.agent import feelings, friendcheck

# Pastimes, as people name them. A list on purpose: "I used to <anything>" would bring back smoking as readily as soccer.
TAIL = r"(?:lessons?|practice|rehearsals?|class(?:es)?|clubs?|teams?|leagues?|groups?|circle|society|troupe|nights?|meets?|camp|workshops?)"
THING = (
    r"soccer|football|futsal|basketball|baseball|softball|volleyball|hockey|rugby|cricket|lacrosse|tennis|pickleball|badminton|squash|"
    r"table tennis|ping[- ]pong|golf(?:ing)?|bowling|curling|ultimate frisbee|frisbee|kickball|dodgeball|netball|track|cross[- ]country|"
    r"running(?!\s+(?:around|late|out|behind|errands|on|low|into|the|a|an|my|this|that|things))|jogging|hik(?:ing|es)|climbing|bouldering|"
    r"swimming|cycling|biking|bike rides|yoga|pilates|zumba|tai chi|crossfit|weightlifting|boxing|kickboxing|karate|judo|jiu[- ]?jitsu|"
    r"taekwondo|martial arts|fencing|archery|rowing|kayaking|canoeing|paddle ?boarding|sailing|surfing|skiing|snowboarding|skating|"
    r"skateboarding|roller derby|horseback riding|gymnastics|long walks|"
    r"danc(?:e|ing)|salsa|ballroom|ballet|choirs?|chorus|singing|karaoke|bands?|orchestra|guitar|piano|bass|drums|drumming|violin|cello|"
    r"fiddle|banjo|ukulele|saxophone|trumpet|flute|clarinet|open mics?|improv|theat(?:er|re)|acting|musicals|"
    r"painting|drawing(?!\s+(?:a blank|the line|near|close|to a close|attention|conclusions?))|sketching|watercolou?rs?|pottery|ceramics|"
    r"sculpting|knitting|crochet(?:ing)?|sewing|quilting|embroidery|woodworking|carpentry|photography|scrapbooking|calligraphy|baking|"
    r"cooking(?!\s+the books)|gardening|my garden|poetry|journaling|"
    r"reading(?!\s+(?:about|that|your|the news|an? article|this|it|up on|into|between|his|her|their|my (?:email|messages|texts)))|"
    r"fishing(?!\s+for)|camping|bird ?watching|birding|stargazing|foraging|chess|board games?|game nights?|trivia|pub quiz|d&d|"
    r"dungeons (?:and|&) dragons|tabletop|mah ?jong|dominoes|bingo|puzzles|crosswords|book clubs?|"
    r"volunteer(?:ing|ed)?|coach(?:ing|ed)|scouts|youth group|bible study|supper club|meetups?|little league|"
    r"(?:rec|recreational|adult|local|community|church|company|pub|sunday|darts|pool|drama|garden|film|movie|glee|swim|ski|surf|art|music|"
    r"voice|riding|craft|writing|walking)\s+" + TAIL
)

# Said as something they did or do: "I paint", "we danced", "I used to run".
DID = (r"paint(?:ed)?|draw|drew|sketch(?:ed)?|knit(?:ted)?|sew(?:ed)?|quilt(?:ed)?|crochet(?:ed)?|garden(?:ed)?|bake[ds]?|sing|sang|sung|"
       r"dance[ds]?|swim|swam|hike[ds]?|climb(?:ed)?|bowl(?:ed)?|golf(?:ed)?|ski(?:ed)?|surf(?:ed)?|skate[ds]?|fish(?:ed)?|camp(?:ed)?|"
       r"jog(?:ged)?|run|ran|cycle[ds]?|bike[ds]?|row(?:ed)?|sail(?:ed)?|box(?:ed)?|volunteer(?:ed)?|coach(?:ed)?|"
       r"r(?:o|i)de (?:my |our |a )?(?:bikes?|horses?)")
NOT_IT = r"(?!\s+(?:into|out|over|up|down|by|through|away|off|around|for office|late|errands|a|an|the|my|our|this|that|his|her|their)\b)"
OFTEN = (r"every|most|twice|once a|times a|on (?:sun|mon|tues|wednes|thurs|fri|satur)days?|on (?:the )?weekends|each (?:week|morning|sunday|"
         r"saturday|summer)|a lot|all the time|everywhere|for fun|for (?:\w+ )?years|competitively|since i was|growing up|together|"
         r"in (?:college|high school|school)|in my (?:twenties|thirties|forties|teens|youth)|back then|back in the day|back home|as a kid|"
         r"when i was (?:younger|a kid|little|in)")
DAY = r"(?:sun|mon|tues|wednes|thurs|fri|satur)day(?: night| morning| afternoon)?"
# What they are: "I'm a runner", "I was a big reader".
ONE = (r"runner|swimmer|dancer|climber|cyclist|hiker|painter|singer|musician|golfer|bowler|gardener|baker|knitter|quilter|reader|skier|"
       r"surfer|skater|boxer|rower|birder|drummer|guitarist|pianist|violinist|goalie|goalkeeper|point guard|pitcher|shortstop|"
       r"striker|midfielder|yogi|chess player|soccer player|tennis player|ball ?player|choir (?:girl|boy|kid)|band (?:kid|geek|nerd)|theat(?:er|re) kid")

WHO = r"(?:\b(?:i|we)\b(?:['’](?:ve|d|m|ll|re))?|\bme and my \w+|\bmy \w+ and i\b)"
NEAR = r"[^.!?;]{0,48}?"
NOT_THAT = r"(?!\s+(?:that|this|the|how|when|what|it|his|her|their)\b)"  # "I love how quiet the yoga studio is" is about the quiet
LOVED = (r"play(?:ed|ing|s)?|(?:lov(?:e|ed|es|ing)|lik(?:e|ed|es)|enjoy(?:ed|s|ing)?|ador(?:e|ed))" + NOT_THAT + r"|miss(?:ed|ing)?" + NOT_THAT +
         r"|into|big on|keen on|mad about|crazy about|obsessed with|passionate about|hooked on|belong(?:ed|s)? to|happiest|"
         r"(?:was|were|am|['’]m|been|being|be|are|['’]re)\s+(?:in|on|part of|a part of|a member of)(?=\s+(?:a|an|the|my|our)\s+(?:[\w'’-]+\s+){0,2}(?:" + THING + r")\b)|"
         r"(?:was|were|am|['’]m)\s+(?:the|a|an)\s+\w+(?:\s+\w+)?\s+(?:on|in|for|of)|"
         r"grew up|s[ai]ng|sung|been(?=\s+(?:really |seriously |mostly )?(?:" + THING + r")\b)|"
         r"(?:do|did|doing|done|go|goes|going|went|gone|take|took|taking|join(?:ed)?|start(?:ed)?|picked up|took up|tak(?:e|ing) up|ran|"
         r"teach|taught|practic(?:e|ed)|train(?:ed)?|compet(?:e|ed))(?=\s+(?:(?:a|an|the|my|some|to|for|out|up|in|lots of|a lot of|a bit of|"
         r"local|new|weekly)\s+){0,3}(?:" + THING + r")\b)")
BEST = r"(?:best part|highlight|high point|favou?rite part|thing i looked forward to|what i lived for|what kept me (?:sane|going)|(?:one|only) thing (?:i|that))"
SAID = re.compile(
    rf"{WHO}{NEAR}\b(?:{LOVED})\b{NEAR}\b(?:{THING})\b|"
    rf"^\W*(?:really |always |still |honestly )*(?:used to (?:do|play|go|love|be in|be into)|lov(?:e|ed)|miss(?:ed)?|played)\b{NEAR}\b(?:{THING})\b|"  # "used to do yoga"
    rf"{WHO}\s+had\s+(?:a|an|our|my)\s+[^.!?;]{{0,30}}?\b(?:{THING})\b[^.!?;]{{0,40}}?\b(?:{OFTEN})\b|"
    rf"{WHO}\s+used to\s+(?:go\s+)?(?:{DID})\b{NOT_IT}|"
    rf"{WHO}(?:\s+(?:still|also|usually|always|mostly|even))?\s+(?:{DID})\b{NOT_IT}[^.!?;]{{0,40}}?\b(?:{OFTEN})\b|"
    rf"\bi(?:['’]m| am| was| used to be|['’]ve always been| have always been)\s+(?:a|an|the)\s+(?:[\w-]+ ){{0,2}}(?:{ONE})\b|"
    rf"{WHO}\s+had\s+(?:a|an|our|my)\s+(?:(?:standing|weekly|regular|monthly|{DAY})\s+)+(?:\w+\s+)?(?:{THING})\b|"
    rf"\b(?:{THING})\b\s+(?:used to |always |really |still |would )?(?:calm(?:ed|s)?|relax(?:ed|es)?|ground(?:ed|s)?|cent(?:er|re)(?:d|s)?|help(?:ed|s)?|"
    r"saved?|kept|keeps?|clear(?:ed|s)?|ma(?:de|kes?))\s+(?:me|my)\b|"
    rf"\b(?:{THING})\b[^.!?;]{{0,24}}?\s(?:is|was|were|are|has always been|['’]s|used to be)\s+(?:kind of |sort of |totally |really |always )?"
    rf"(?:my\s+(?:thing|hobby|passion|happy place|escape|outlet|whole life|jam|favou?rite|second home|whole world|everything|life|sanctuary|"
    rf"therapy)\b|(?:the |my ){BEST}|the best\b|so much fun\b|a blast\b|everything to me\b)|"
    rf"\bmy\s+(?:hobby|passion|thing|favou?rite thing(?: to do)?|happy place|outlet)\s+(?:is|was|has always been)\b[^.!?;]{{0,30}}?\b(?:{THING})\b|"
    rf"\b(?:(?:sun|mon|tues|wednes|thurs|fri|satur)days?|weekends|evenings|summers)\s+(?:were|was|are|is)\s+(?:always )?for\s+(?:{THING})\b",
    re.I)

# Never brought back: what they're better off without, what ended badly, what they can't do now, who they lost.
NEVER = re.compile(
    r"\b(?:drink(?:ing|s)?|drank|drunk|booze|bar ?hopp\w+|pub crawls?|beers?|wine|whiske?y|vodka|shots|wasted|hammered|smok(?:e|ed|ing)|"
    r"vap(?:e|ed|ing)|cigarettes?|weed|stoned|high(?! school)|drugs?|pills?|coke|cocaine|meth|heroin|gambl\w+|casinos?|slots|poker|"
    r"bett?ing|bets?|lottery|scratch[- ]offs?|diet(?:ing|s|ed)?|fast(?:ing|ed)|purg\w+|starv\w+|bing(?:e|ed|ing)|myself|self[- ]harm|"
    r"fights?|fighting|fought|hook(?:ing|ed)? up|hookups?|strip clubs?|ex|dat(?:e|ed|ing)|broke up|divorc\w+|affair|cheat\w+|"
    r"late (?:wife|husband|mother|father|mom|mum|dad|son|daughter|brother|sister|partner|friend)|passed|died|dead|death|funeral|"
    r"hat(?:e|ed|es)|can['’]?t stand|couldn['’]?t stand|never (?:liked|enjoyed|got into|went back|again)|(?:don['’]?t|didn['’]?t|"
    r"doesn['’]?t|do not|did not) (?:like|enjoy|play|do|miss|care for)|not (?:into|a fan|my thing|for me)|sucked at|terrible at|"
    r"quit|gave up|got (?:cut|kicked)|cut from|kicked (?:off|out)|dropped out|can['’]?t (?:any ?more|do it|play|run|dance|walk)|"
    r"any ?more|no longer|too old|surgery|injur\w+|blew out|bad (?:knees?|back|hip|shoulder)|doctor|arthritis|wheelchair|"
    r"terrible|awful|lousy|horrible|worst|"
    r"you|your|yours|u|ur)\b", re.I)
SOMEONE_ELSE = re.compile(r"(?<!with )(?<!and )\b(?:he|she|they|his|her|their|my (?:son|daughter|kids?|husband|wife|partner|boyfriend|girlfriend|"
                          r"mom|mum|mother|dad|father|brother|sister|friend|roommate|boss|neighbou?r)s?)\b", re.I)

WHEN = (r"with myself|this weekend|tonight|today|tomorrow|this (?:afternoon|evening|morning|saturday|sunday|week)|on (?:the |my )?weekends?|"
        r"on (?:saturdays?|sundays?)|on my days? off|after work|in the evenings?|with (?:all )?(?:my|this|the) (?:free |spare )?(?:time|weekends?|"
        r"evenings?|days? off|nights?|saturdays?|sundays?)|(?:my|the|this) (?:long |whole |entire )?(?:time|days?|evenings?|weekends?|nights?|hours)")
HOME = r"(?:at home|home|in my (?:apartment|room|flat|house|place)|on the couch|on my couch|inside|indoors|in the house|in bed)"
LOOSE = re.compile(
    rf"\b(?:no idea|(?:don['’]?t|do not|never|never really) know|dunno|not sure|no clue|can['’]?t think|figur(?:e|ing) out|wondering|deciding)\s+"
    rf"(?:of\s+)?(?:what to do|how to (?:fill|spend))\s+(?:{WHEN})|"
    r"\bnothing to fill\b|\bnowhere to (?:be|go)\b|"  # not "staring at the wall": that's feeling low, and company comes first
    r"\bwhat do (?:people|you|folks|adults|grown-?ups) (?:even |actually )?do (?:on (?:the )?weekends?|for fun|around here|in this town|here)\b|"
    r"\b(?:evenings|weekends|nights) are just (?:tv|netflix|the couch|me and|work|scrolling)\b|"
    r"\b(?:need|want|could use) something to look forward to\b|"
    r"\b(?:haven['’]?t|have not) (?:made|met) (?:a single|any|one|many) (?:new )?(?:friends?|people|person)\b|"
    r"\b(?:do|doing) nothing but (?:work|sleep|sit|scroll)\b|"
    r"\b(?:got|have|having) a free (?:evening|day|weekend|afternoon|night|saturday|sunday)\b|"
    r"\b(?:don['’]?t|do not|barely|hardly|rarely|never) (?:really |ever |even )?(?:get|go) out\b(?!\s+of\b)|"
    r"\b(?:i['’]?m|i am|im|i['’]?ve been|i feel|i['’]?m feeling|i['’]?m getting)\s+(?:so |really |just |super |very |pretty |kinda |kind of |"
    r"a bit |a little |bit |too |still )*bored\b(?!\s+(?:of|with|by)\b)|"
    r"(?:^|[.!?]\s+)(?:ugh,?\s+|so\s+|just\s+|god,?\s+|man,?\s+|honestly,?\s+|still\s+|super\s+|really\s+|very\s+)*bored\b(?!\s+(?:of|with|by)\b)|"
    r"\b(?:nothing|nothin|not much|not a thing|nada)\s+(?:to do|going on|planned|on)\b(?!\s+with\b)|"
    r"\b(?:don['’]?t|do not) (?:really |even )?have (?:anything|much|a lot|a thing) (?:going on|to do|planned|on)\b(?!\s+with\b)|"
    r"\bweekend\b[^.!?]{0,30}\b(?:got|have|having) nothing\b|\b(?:got|have|having) nothing\b[^.!?]{0,30}\bweekend\b|"
    r"\bno plans\b(?=\s*(?:[.!,?]|$|this|tonight|today|tomorrow|at all|again|yet|as usual|for (?:the |this )?(?:weekend|tonight|today|saturday|"
    r"sunday|holidays?|summer|break|long weekend)))|"
    rf"\bwhat (?:should|can|could|do|shall) (?:i|we) (?:even )?do\s+(?:{WHEN}|for fun|around here)|"
    r"\bwhat(?:['’]s| is) there to do\b|"
    r"\bideas? (?:for|on|about) (?:what to do|something to do|things to do|the weekend|this weekend|tonight)\b|"
    r"\b(?:any|got any|have any) (?:ideas|suggestions)\b[^.!?]{0,40}\b(?:weekend|tonight|today|saturday|sunday|out of the house|to do)\b|"
    r"\bfree (?:all|this|the whole|the entire) (?:weekend|day|evening|afternoon|night)\b[^.!?]{0,30}\b(?:ideas?|suggestions?|what (?:should|to))\b|"
    r"\bneed (?:a|some|to find a|to get a|to pick up a) (?:new )?hobb(?:y|ies)\b|\bneed to get a life\b|"
    r"\b(?:need|want|wish|looking for|find|finding|never|isn['’]?t|ain['’]?t|is there|are there)\b[^.!?]{0,25}\b(?:something|anything|stuff|"
    r"things)\s+(?:fun |new |social |different |good )?to do\b(?!\s+with (?!myself|my (?:time|weekends?|evenings?|days? off)))|"
    r"\b(?:need to|should|ought to|have to|gotta|got to|want to|wanna) get out (?:more|of the (?:house|apartment|flat) more)\b|"
    r"\bget (?:me|myself) out of the (?:house|apartment|flat)\b|"
    r"\b(?:should|need to|ought to|want to|wanna|gotta) join (?:something|a (?:club|team|group|class|league|gym|choir|band))\b|"
    r"\b(?:want|need|like|love|trying|hoping|hard|tough|impossible|difficult|ways?|how|places?|somewhere)\s+to\s+(?:meet|make)\s+(?:some |new |more )?(?:people|friends|"
    r"folks)\b(?!\s+(?:who|that|with|from)\b)|"
    r"\b(?:hard|tough|impossible|difficult|struggl\w+)\b[^.!?]{0,20}\b(?:making|meeting)\s+(?:new |some )?(?:friends|people)\b|"
    r"\bhow (?:do|does|can|would) (?:you|i|anyone|one|an adult|a person|people|we) (?:even |ever )?(?:meet|make) (?:some |new )?(?:people|"
    r"friends)\b|\bfind my (?:people|tribe|crowd|community)\b|"
    r"\btoo much (?:free |spare )?time on my hands\b|\ball this (?:free |spare )?time\b|\b(?:so|too) much (?:free|spare) time\b|\btime to kill\b|"
    r"\b(?:weekends?|evenings?|nights|sundays?|saturdays?) (?:are|is|feel|feels|get|gets) (?:so |really |too |very |pretty |just )?"
    r"(?:long|empty|boring|quiet|dull|endless|slow)\b|\b(?:weekends?|evenings?|nights|sundays?|saturdays?|days) (?:drag|drags|dragging)\b|"
    r"\b(?:calendar|schedule|weekend|social life|diary) (?:is|['’]s|looks) (?:so |totally |completely |pretty )?(?:empty|wide open|open|blank|dead|"
    r"non-?existent)\b(?!\s+for\b)|"
    rf"\b(?:just |only )?(?:sit|sitting|sat|stay|staying|stayed|stuck) {HOME} (?:every|all|most|again)\b|"
    rf"\b(?:friday|saturday) night\b[^.!?]{{0,30}}\b(?:{HOME}|no plans|nothing)\b|"
    r"\ball i (?:ever )?do is (?:work|sleep|sit|watch|scroll|eat|stay)\b|"
    r"\bcooped up\b|\bstir[- ]crazy\b|\bclimbing the walls\b|\bcabin fever\b|\bstuck (?:inside|indoors|in the house|in my apartment) all\b|"
    r"\b(?:fill|filling|occupy|kill) (?:my|the|up my) (?:time|days?|evenings?|weekends?|nights?|hours)\b|\bat a loose end\b|\bat loose ends\b|"
    r"\b(?:whole|entire) (?:day|weekend|evening|afternoon) (?:free|off|to myself|open)\b", re.I)
NOT_LOOSE = re.compile(
    r"\bwhat to do (?:about|if|when|with (?:this|that|the|it|him|her|them|these|those|my (?!time|weekends?|evenings?|days? off|nights?|"
    r"saturdays?|sundays?|free|spare)))\b|\bany ?more\b|\btoo much to do\b|\bnothing to do (?:with|but|except|until)\b|\bwith my life\b|"
    r"\bto do about\b|\bwhat (?:should|can|could|do|shall) (?:i|we) do\b[^.!?]*,[^.!?]*\bor\b", re.I)

ROOM = 300   # what this note may take in the brain's instructions (luma.llm.prompts: the "shape" note)
WORDS = 100  # of that, their own words


def _sentences(text):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", str(text or "")) if part.strip()]


def _short(sentence):
    """Their words, whole when they fit; else cut at a word, with the pastime kept."""
    sentence = " ".join(sentence.split())
    if len(sentence) <= WORDS:
        return sentence
    hit = SAID.search(sentence)
    start = max(0, min(hit.start(), hit.end() - WORDS + 1)) if hit else 0
    cut = sentence[start:start + WORDS - 1]
    cut = cut[cut.find(" ") + 1:] if start and " " in cut else cut  # never start mid-word
    return (cut[:cut.rfind(" ")] if " " in cut and len(sentence) > start + len(cut) else cut).rstrip(" ,;:") + "…"


DOING = {"paint": "painting", "draw": "drawing", "drew": "drawing", "sketch": "sketching", "knit": "knitting", "sew": "sewing", "quilt": "quilting",
         "crochet": "crochet", "garden": "gardening", "bake": "baking", "sing": "singing", "sang": "singing", "sung": "singing", "dance": "dancing",
         "swim": "swimming", "swam": "swimming", "hike": "hiking", "climb": "climbing", "bowl": "bowling", "golf": "golf", "ski": "skiing",
         "surf": "surfing", "skate": "skating", "fish": "fishing", "camp": "camping", "jog": "jogging", "run": "running", "ran": "running",
         "cycle": "cycling", "bike": "cycling", "row": "rowing", "sail": "sailing", "box": "boxing", "volunteer": "volunteering", "coach": "coaching"}


def named(sentence):
    """The one word for what they love, to hand a brain that can't carry a whole quoted line: "choir", "painting". "" when
    there's no plain word for it."""
    sentence = str(sentence or "")
    hit = re.search(rf"\b(?:{THING})\b", sentence, re.I)
    if hit:
        return re.sub(r"^my ", "", " ".join(hit.group(0).lower().split()))
    hit = re.search(rf"\b(?:{DID})\b", sentence, re.I)
    if not hit:
        return ""
    word = hit.group(0).lower()
    if "bike" in word:
        return "cycling"
    if "horse" in word:
        return "riding"
    word = re.sub(r"(?:ted|ged|ed|d|s)$", "", word) if word not in DOING else word
    return DOING.get(word, DOING.get(word + "e", ""))


def said(text):
    """The sentence in which they told of something they love doing, or "". Their words, at most 100 characters."""
    for sentence in _sentences(text):
        hit = SAID.search(sentence)
        if not hit or NEVER.search(sentence) or SOMEONE_ELSE.search(sentence[:hit.end()]):
            continue
        if (feelings.read(sentence) or {}).get("heavy"):
            continue
        return _short(sentence)
    return ""


def at_a_loose_end(text):
    """They don't know what to do with themselves, or want people around. Not a problem they're stuck on."""
    text = str(text or "")
    return bool(LOOSE.search(text)) and not NOT_LOOSE.search(text)


def note(text, earlier=(), interests=""):
    """One line for the brain when they're at a loose end and have told Luma what they love doing. "" otherwise.

    earlier: what they said before this message, oldest first. interests: what they put on their profile, if anything."""
    text = str(text or "")
    if not at_a_loose_end(text) or said(text):
        return ""
    if friendcheck.at_risk(text) or friendcheck.worth_asking(text) or (feelings.read(text) or {}).get("heavy"):
        return ""
    earlier = [str(line) for line in earlier or () if isinstance(line, str)]
    if any((feelings.read(line) or {}).get("heavy") for line in earlier[-3:]):
        return ""  # a minute after something hard, staying with them comes first
    theirs = next((found for found in (said(line) for line in reversed(earlier[-24:])) if found), "")
    interests = " ".join(str(interests or "").split())[:WORDS]
    if not theirs and (not interests or NEVER.search(interests)):
        return ""
    if not theirs:
        line = (f"They're at a loose end. You know they're into: {interests}. Bring that back, like a friend who remembers: wonder with "
                "them if there's something like it near them. One idea, from their own life. No list of tips.")
        return line if len(line) <= ROOM else ""
    for name in (named(theirs), ""):   # with the word for it when there's room; a small brain acts on a word more than on a quote
        by = f" by name ({name})" if name else ""
        line = (f"They're at a loose end. Earlier they told you: “{theirs}” Bring it back{by}, like a friend who remembers: wonder with "
                "them if there's something like it near them. One idea, theirs. No list of tips.")
        if len(line) <= ROOM:
            return line
    return ""
