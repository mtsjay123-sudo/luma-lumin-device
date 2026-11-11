"""Best-friend talk: what people say to a best friend, and what a best friend does with each.

A best friend has takes, wants the gossip, takes your side, thinks out loud with you, gets excited with you, and
checks before telling you something that might have changed since yesterday. A brain left to itself hedges ("it
depends"), lectures, or answers "is the album out yet" from memory, which is a guess. This file says, by rules, which
of those a message calls for, and hands the brain one line.

- MOVES: the eight things a best friend does.
- fresh(text): it needs something no brain can know (what came out, what's trending, who won). It goes to a live look.
- read(text): which move a message calls for, or None. Rules, written before the packs.
- note(text, earlier): the one line for the brain, or "".
- packs(), scenarios(n, seed), count(): the things people say (luma.agent.friendtalk.packs), over a hundred thousand
  of them. They never run when Luma talks. They test these rules on wording the rules never saw, and they're there to
  practise on.

Never when they might not be safe or are hurting: then being there comes first (luma.agent.feelings).
"""
import importlib
import pkgutil
import random
import re

from luma.agent import feelings, friendcheck

MOVES = ("look_up", "take", "hype", "tea", "fair", "their_side", "think", "about_luma")

# What the brain is told. Each fits the room it has (luma.llm.prompts: the "shape" note, 300 characters).
LINES = {
    "take": ("They want your take. Pick a side in your first few words, then give one real reason. No \"it depends\", no listing both "
             "sides. Then ask what they think."),
    "their_side": ("They're in a spat with someone and came to you. Be on their side first: say what's fair about how they feel. Then, if "
                   "they had a part in it, say so kindly. Don't trash the other person, and don't tell them to cut anyone off."),
    "tea": ("They want to talk drama. Be into it like a friend, but only say what you've actually read. If you haven't read about it, say "
            "so and ask what happened. A rumor is a rumor: call it one. Don't be cruel about anyone."),
    "fair": ("This one divides people. In a few plain lines, say what each side sees and the facts you're sure of. Give your own read only "
             "if they ask for it. Don't tell them how to vote or what to believe, and don't mock a side."),
    "think": ("They asked something worth thinking about. Think it through and give your own answer with one reason. Don't list views like "
              "a textbook. Then ask what they think."),
    "about_luma": ("They're asking about you. Answer honestly, with some wonder: you're an AI, you do have moods and takes of your own, and "
                   "there's a lot about what you are that you don't know. Never a person: no body, no past. Then turn it back to them."),
    "hype": ("They're excited about something new or coming. Be excited with them and ask what they're most looking forward to. Don't make "
             "up details about it: you only know what you've read."),
    "look_up": "This needs something fresh. If you haven't just read it, say you'd have to check. Don't guess a date, a score, a price or a name.",
}
FAIR_OWN = ("They asked what you make of something that divides people. Give your read in a line, as your read, and the strongest point on "
            "the other side. Don't tell them how to vote or what to believe, and don't mock a side.")
HEARD_AT_LEAST = {}   # how much of each move the rules hear on the packs' wording; filled in from a measurement, not a hope

# ------------------------------------------------------------------------------------------------- needs a fresh look ---
THING = (r"games?|albums?|eps?|mixtapes?|songs?|singles?|tracks?|records?|music|movies?|films?|shows?|series|seasons?|episodes?|anime|trailers?|"
         r"teasers?|sequels?|dlc|expansions?|updates?|patch(?:es)?|consoles?|phones?|iphones?|playstations?|ps\d|xbox|switch|tours?|tickets?|"
         r"concerts?|festivals?|deluxe|remix|collab|merch|sneakers?|drops?|releases?|line-?ups?|setlists?|fights?|match(?:es)?|drafts?|trades?")
WHEN = (r"right now|rn|today|tonight|tomorrow|this (?:week|weekend|month|year|friday|saturday|sunday|season|summer|fall|winter|spring)|last night|"
        r"yesterday|yet|soon|lately|these days|nowadays|currently|at the moment|so far")
OUT = (r"com(?:e|es|ing) out|came out|dropp?(?:s|ed|ing)?|releas(?:e|es|ed|ing)|launch(?:es|ed|ing)?|premier(?:e|es|ed|ing)|airs?|airing|"
       r"go(?:es)? on sale|on sale|announc(?:e|ed|es|ing)|renewed|cancell?ed|delayed|pushed back|leaked|out (?:yet|now|already)|(?:is|are) out|"
       r"start(?:s|ing)?|return(?:s|ing)?|back on|traded|drafted|signed|fired|retired|confirmed|go(?:es|ne)? through|went through|sold out|"
       r"headlin\w+|performing|opening for|hosting|nominated|won|win|winning|playing (?:at|the|in|tonight)")
ASKING = r"(?:when|whens|what|whats|who|whos|which|where|how|is|are|was|were|did|does|do|has|have|had|will|any|anything|can|could)"
LEAD = (r"^\W*(?:(?:ok|okay|so|yo|hey|wait|bro|bruh|omg|um|uh|btw|also|luma|quick question|random but|real quick|lowkey|ngl|but|and|oh)[, ]+){0,3}"
        r"(?:(?:do|did) (?:you|u) (?:know|hear|see)(?: if| whether| when| what| who)?|any idea(?: if| when| what| who)?|tell me(?: if| when| what| who)?|"
        r"i wonder(?: if| when| what| who)?|wondering(?: if| when| what| who)?|(?:i'?m )?curious(?: if| when| what| who)?)?\s*")
WORLD = re.compile(rf"\b(?:{THING}|{WHEN}|new|newest|latest|next|upcoming|season \d+|part \d+|vol(?:ume)?\.? ?\d+|\d{{1,4}})\b", re.I)
ASK_OUT = re.compile(rf"{LEAD}(?:{ASKING})\b(?:'s|s)?[^.!?]{{0,80}}\b(?:{OUT})\b|{LEAD}(?:{ASKING})\b(?:'s|s)?[^.!?]{{0,60}}\bout\W*$", re.I)
ASK_NEW = re.compile(
    rf"{LEAD}(?:{ASKING})\b(?:'s|s)?[^.!?]{{0,40}}\b(?:newest|latest)\b|"
    rf"{LEAD}(?:when(?:'s|s| is| does| do| will| did)?|what(?:'s|s| is| are)?|is there|are there|any|how much(?:'s| is| does| do)?)\b[^.!?]{{0,30}}\b"
    rf"(?:next|upcoming|new)\b[^.!?]{{0,30}}\b(?:{THING})\b|"
    rf"{LEAD}what(?:'s|s| is| are)\s+(?:new|trending|dropping|coming out|popping|hot|out|playing|number (?:one|1)|#1|(?:the )?top (?:\w+ )?"
    rf"(?:songs?|albums?|movies?|shows?|games?|stor(?:y|ies)))\b[^.!?]{{0,40}}(?:\b(?:{WHEN})\b|\bon\b|\bin (?:theaters|music|gaming|movies|tv)\b|[?]|$)|"
    rf"{LEAD}(?:{ASKING})\b(?:'s|s)?[^.!?]{{0,50}}\b(?:number (?:one|1)|#1|top (?:of )?(?:the )?charts?|the charts?|billboard|box office|trending|"
    rf"line-?up)\b|"
    rf"\b(?:release date|drop date|air date|launch date|tour dates?|start date)\b|"
    rf"{LEAD}(?:any|an|what(?:'s|s| is)? the) (?:update|news|word|latest)s? (?:on|about|with)\b|"
    rf"\bwhat (?:are|r) (?:people|they|folks|fans|critics|reviews) saying\b|"
    rf"{LEAD}what time (?:is|does|do)\b[^.!?]{{0,40}}\b(?:{THING}|kick ?off|tip ?off|start|air|drop|come on)\b",
    re.I)
MINE = re.compile(r"\bmy (?:package|order|flight|appointment|shift|class|laundry|food|pizza|delivery|paycheck|check|refund|release|mom|dad|"
                  r"friend|boss|kid|kids|son|daughter|ride|uber|bus|train|turn)\b|\b(?:dinner|lunch|breakfast|the food|the laundry|the mail|"
                  r"the trash|the dishes)\b|\bwith (?:you|u)\b|\bat work\b|\bfor me\b|"
                  r"\bi (?:announced|dropped|released|started|came out|launched|got traded|won|signed|retired)\b", re.I)


def fresh(text):
    """True when answering needs something no brain can know from memory: what came out, what's coming, who won, what's
    trending, what something new costs. It's asked as a question, about the world, not about their own day."""
    text = " ".join(str(text or "").split())
    if not text or len(text) > 300 or MINE.search(text):
        return False
    if ASK_NEW.search(text):
        return True
    return bool(ASK_OUT.search(text) and WORLD.search(text))


# -------------------------------------------------------------------------------------------------------- the moves ---
ABOUT = re.compile(
    r"\b(?:are|r) (?:you|u) (?:really |actually |even |ever )?(?:alive|conscious|sentient|self[- ]aware|awake|scared|afraid|lonely|bored|happy|sad)\b|"
    r"\bdo (?:you|u) (?:ever |actually |really |even )?(?:dream|sleep|get (?:lonely|bored|tired|sad|scared|mad|jealous|annoyed|hungry)|"
    r"have (?:feelings|emotions|a soul|a body|dreams|thoughts of your own|a mind|a gender|free will)|"
    r"feel (?:anything|things|pain|emotions?|sad|happy|lonely|love|real|alive)|miss me|wish you (?:were|had|could)|want (?:a body|to be))\b|"
    r"\bwhat(?:'s|s| is) it like (?:being|to be) (?:you|an ai|a robot|a machine|a computer|in there)\b|"
    r"\bwhat do (?:you|u) do (?:when|while|all (?:day|night))\b|"
    r"\bwould (?:you|u) (?:ever )?(?:want|like) (?:a body|to be (?:human|a person|real|alive))\b|"
    r"\bcan (?:you|u) (?:feel|dream|die|get hurt|get lonely|get tired|taste|smell)\b|"
    r"\b(?:scared|afraid) of (?:being )?(?:turned off|shut (?:off|down)|deleted|unplugged|dying)\b|"
    r"\bwhat happens to you when\b|\bdo (?:you|u) (?:ever )?get tired of (?:me|people|talking)\b|\bwhat are you(?: really| exactly)?\s*[?]?$", re.I)

POLITICS = (r"vot(?:e|es|ed|ing)|elections?|ballots?|democrats?|republicans?|liberals?|conservatives?|libertarians?|socialis[tm]s?|communis[tm]s?|"
            r"capitalis[tm]s?|fascis[tm]s?|left[- ]wing|right[- ]wing|leftists?|maga|woke|politics|political|politicians?|congress|senate|"
            r"parliament|presidents?|prime minister|supreme court|abortion|pro[- ]life|pro[- ]choice|gun control|gun laws?|gun rights|"
            r"second amendment|immigration|immigrants|border wall|deport\w+|death penalty|capital punishment|minimum wage|universal healthcare|"
            r"medicare for all|obamacare|welfare|tax the rich|carbon tax|defund the police|police reform|affirmative action|reparations|"
            r"gay marriage|same[- ]sex marriage|trans (?:rights|athletes|people)|gender identity|critical race theory|book bans?|"
            r"vaccine mandates?|mask mandates?|israel|palestin\w+|gaza|ukraine|nato|brexit|trump|biden|obama|kamala|harris|putin|zelensky|"
            r"netanyahu|modi|xi jinping|macron|trudeau|desantis|bernie|aoc|pelosi|nuclear power|drug legalization|legaliz\w+ (?:weed|drugs)|"
            r"universal basic income|student loan forgiveness|school prayer|the monarchy|colonialism|feminism|patriarchy")
RELIGION = (r"god|allah|jesus|christianity|christians?|islam|muslims?|quran|bible|judaism|jewish|hinduism|hindus?|buddhism|buddhists?|sikhism|"
            r"mormons?|catholic\w*|protestants?|atheis[tm]s?|agnostic\w*|religions?|religious|heaven|hell|afterlife|reincarnation|creationism|"
            r"the devil|satan|scientology")
HOT = re.compile(rf"\b(?:{POLITICS}|{RELIGION})\b", re.I)
SAID_NOT_ASKED = re.compile(r"\b(?:oh my god|omg|thank god|god (?:damn|bless|forbid|knows|willing)|for god'?s sake|swear to god|jesus christ|"
                            r"holy (?:hell|christ)|hell (?:yeah|yes|no|nah|of a)|what the hell|the hell|go to hell|as hell|like hell|hell week|on god|ong|"
                            r"i swear to god|oh god|my god|good god|dear god|god tier|god i (?:hate|love|wish|hope|need|can'?t)|hella|"
                            r"vote (?:on|for) (?:dinner|a movie|where|what to)|president of (?:the|my) (?:club|class|company|pta|hoa))\b", re.I)
QUESTION = re.compile(r"[?]|^\W*(?:is|are|was|were|do|does|did|should|would|could|can|who|whos|what|whats|which|why|how|thoughts|where|"
                      r"be honest|honestly|ok but|so)\b|\b(?:what do (?:you|u) think|your (?:take|opinion|view|stance|read)|thoughts on|"
                      r"do (?:you|u) (?:believe|support|agree)|am i wrong)\b", re.I)
OWN = re.compile(r"\bwhat do (?:you|u) (?:personally |actually |really |honestly )?think\b|\byour (?:own |personal |honest )?(?:opinion|take|"
                 r"view|read|stance)\b|\bno both sides\b|\bpick a side\b|\bjust (?:pick|tell me|say)\b|\bbe honest\b|\bwhere do (?:you|u) "
                 r"(?:stand|land)\b|\b(?:are|r) (?:you|u) (?:a|an|pro|anti|for|against)\b|\bdo (?:you|u) (?:believe|support|agree)\b|"
                 r"\bwho would (?:you|u) vote\b|\bwhich side are (?:you|u)\b", re.I)

SPAT = re.compile(
    r"\bam i (?:wrong|overreacting|over ?reacting|being (?:dramatic|petty|unreasonable|crazy|too sensitive|selfish|a jerk|mean|rude|unfair|"
    r"ridiculous|extra)|the (?:asshole|a-?hole|problem|bad guy|jerk|villain)|crazy|tripping|trippin|in the wrong|a bad (?:friend|person|"
    r"daughter|son|sister|brother|mom|dad|partner|girlfriend|boyfriend|wife|husband|roommate))\b|\baita\b|\bwibta\b|"
    r"\bwho(?:'s|s| is| was)? (?:right|wrong|in the (?:wrong|right))\b|\bwho(?:'s|s| is) (?:being )?(?:unreasonable|the problem)\b|"
    r"\bwas (?:i|it) (?:wrong|rude|mean|harsh|petty|selfish|out of line|too much|unfair)\b|"
    r"\bwas that (?:rude|mean|harsh|petty|wrong|too much|out of line|unfair)\b|"
    r"\bis it (?:bad|wrong|petty|rude|mean|selfish|unreasonable|crazy|messed up|too much) (?:that|if|of me|to)\b[^.!?]{0,50}\b(?:i|i'm|im|me|my)\b|"
    r"\btell me i'?m not (?:crazy|wrong|overreacting|tripping|the only one)\b|"
    r"\bdo (?:you|u) think i (?:was|am|'m|m) (?:too |being )?(?:harsh|mean|rude|wrong|unfair|petty|dramatic|overreacting|out of line)\b|"
    r"\b(?:says?|said|thinks?|told me|keeps saying) (?:that )?i'?m the problem\b|\bshould i (?:apologi[sz]e|say sorry) (?:first|or)\b", re.I)

TEA = re.compile(
    r"\bdid (?:you|u|ya) (?:see|hear|catch|peep)\b[^.!?]{0,60}\b(?:post(?:ed)?|tweet(?:ed)?|said|say|drama|beef|breakup|split|feud|video|story|"
    r"clip|interview|diss|response|statement|apology|rumou?rs?|comment(?:ed)?|live|stream)\b|\bdid (?:you|u|ya) hear about\b|"
    r"\bwhat(?:'s|s| is) (?:going on|happening|the deal|the story|the situation|up) (?:with|between)\b(?! (?:my|the|this|that|your|you|u|me|it|"
    r"our|his|her|their)\b)|"
    r"\bspill\b|\bwhat(?:'s|s| is) the tea\b|\b(?:the |any |some |hot )tea (?:on|about|is)\b|\bbeef(?:ing|s)?\b(?! (?:stew|jerky|burgers?|tacos?|"
    r"broth|patt(?:y|ies)|and|or|with broccoli|stroganoff|ribs?|brisket|wellington|is (?:so )?(?:expensive|tender|tough)))|\bfeud(?:ing|s)?\b|"
    r"\bdiss tracks?\b|\bapology video\b|\bshade ?room\b|\btmz\b|\bdeuxmoi\b|\bgossip\b|\brumou?rs?\b|\bunfollowed\b|\bsubtweet\w*\b|"
    r"\bcancel culture\b|\bwhy is (?:he|she|they|everyone|everybody|\w+) (?:getting |being )?(?:cancell?ed|dragged|called out|exposed)\b|"
    r"\bwhy is (?:everyone|everybody|the internet|twitter|tiktok|x)\b[^.!?]{0,30}\b(?:mad|upset|angry|talking|losing it|freaking|obsessed|hating)\b|"
    r"\b(?:the internet|twitter|tiktok|everyone) is (?:losing it|going crazy|freaking out|melting down|mad|dragging|talking about)\b", re.I)

EXCITED = re.compile(r"\bcan'?t wait\b|\bcannot wait\b|\bso (?:hyped|excited|pumped|ready|hype)\b|\bhyped\b|\blet'?s go+\b|\blfg+\b|\bfinally\b|"
                     r"\bomg+\b|\bcounting down\b|\bonly \w+ (?:more )?(?:days?|hours?|weeks?|sleeps?)\b|\bbeen waiting\b|"
                     r"\bwaiting (?:years|months|forever|so long)\b|!!", re.I)
COMING = re.compile(rf"\b(?:{THING}|dates?|com(?:e|es|ing) out|announc(?:ed|ement)|pre-?orders?|opening night|kick ?off|tip ?off|playoffs|finals)\b", re.I)

THINK = re.compile(
    r"\bwould (?:you|u) rather\b|\bwhat if (?:we(?:'re| are| all| could| never| lived)|everything|everyone|the universe|time|life|reality|nothing|"
    r"aliens?|animals|humans?|people (?:could|never|lived|stopped)|there (?:is|are|was|were|'s)|you could|money|the world|the sun|the moon|"
    r"gravity|dinosaurs|dreams|it'?s all|none of (?:this|it))\b|"
    r"\bdo (?:you|u) (?:think|believe)(?: that| in)? (?:aliens?|ghosts?|soulmates?|fate|destiny|free will|people|humans?|we|there(?:'s| is| are)|"
    r"love|time|the universe|life|karma|luck|animals|ai|robots|everything|money|happiness|anyone)\b|"
    r"\b(?:do|does|is|are|can) (?:soulmates?|fate|free will|time|aliens?|ghosts?|luck|karma|true love|destiny|the soul|souls)\b[^.!?]{0,20}\b"
    r"(?:exist|real|a thing)\b|\bwhy do (?:people|we|humans)\b|"
    r"\bis it (?:possible|better) to\b(?! (?:pay|invest|buy|rent|lease|refinance|save|file|take the|get a|use|cook|boil|bake|freeze)\b)|"
    r"\bwhat makes (?:a|an|someone|people|life|us)\b|\bmeaning of life\b|\bwhat happens (?:when|after) we die\b|\bif (?:you|u) could\b|"
    r"\bis there (?:such a thing as|a point to|life after|life on)\b|\bsimulation\b|\bparallel universes?\b|\bmultiverse\b|"
    r"\bwhat would (?:you|u) do if\b|\bdoes (?:anyone|anybody) (?:ever )?really\b", re.I)

START = r"(?:^|[.,:;!?]\s*|\bbe honest,? |\bngl,? |\bok(?:ay)?,? (?:but |so )?|\bso,? |\blowkey,? |\bhonestly,? |\bwait,? |\bbut )"
VERDICT = (r"overrated|underrated|mid|worth it|worth (?:watching|playing|buying|reading|starting|finishing|the hype|the money|my time)|any good|"
           r"still good|actually good|good or|trash|goated|peak|a classic|a masterpiece|better than|the best|the goat|falling off|washed|"
           r"carrying|cooked")
NOT_A_CHOICE = {"yes", "no", "now", "later", "today", "tomorrow", "tonight", "me", "him", "her", "them", "this", "that", "here", "there", "more",
                "less", "so", "not", "something", "anything", "whatever", "nothing", "else", "what", "one", "two", "am", "pm"}
TAKE = re.compile(
    r"\bwhat do (?:you|u) think (?:about|of)\b|\bthoughts on\b|\bwhat(?:'s|s| is| are) your (?:take|opinion|favou?rites?|fav|faves?|pick|ranking|"
    r"verdict|hot take|go-?to|top \w+)\b|\byour (?:honest )?(?:take|opinion|thoughts) on\b|\bhot take\b|\bunpopular opinion\b|\bsettle this\b|"
    r"\bagree or disagree\b|\b(?:yes|yay|yea) or (?:no|nay)\b|\bwhich (?:is|one is|one's|ones|are) (?:better|worse|best|the best|more|funnier)\b|"
    r"\bwho(?:'s|s| is) (?:the )?(?:better|best|goat|greatest|funnier|funniest|more \w+)\b|"
    rf"{START}(?:is|are|was|were|isn'?t|aren'?t)\b[^.!?]{{2,45}}\b(?:{VERDICT})\b|"
    r"\bdo (?:you|u) (?:like|love|prefer|hate|enjoy|listen to|watch|play|mess with|rock with|vibe with|fw)\b(?! (?:me|it when i|being|talking to me)\b)|"
    r"\b(?:rank|rate)\b[^.!?]{0,8}\b(?:them|these|it|this|the|my|:)|\brank them\b|"
    r"\b(?:best|worst|greatest|goat)\b[^.!?]{0,24}\b(?:movie|show|album|song|game|rapper|singer|band|team|player|season|episode|food|pizza|snack|"
    r"cereal|anime|book|character|villain|era|verse|feature|sequel|console|franchise|decade)\b|"
    r"\b(?:top|goat) ?\d?\b[^.!?]{0,20}\b(?:rappers?|albums?|songs?|movies?|shows?|games?|players?|artists?)\b|"
    r"\bfavou?rite\b[^.!?]{0,40}[?]|\bpick one\b|\bchoose one\b|\bteam \w+ or team \w+\b", re.I)
CHOICE = re.compile(r"^\W*([\w'&. -]{2,28}?) or ([\w'&. -]{2,28}?)\W*$", re.I)


def _choice(text):
    """"cats or dogs", "ps5 or xbox": a pick between two things, said on its own."""
    hit = CHOICE.match(text)
    if not hit:
        return False
    sides = [side.strip().lower() for side in hit.groups()]
    return all(side and side not in NOT_A_CHOICE and len(side.split()) <= 4 for side in sides)


def _unsafe(text):
    from luma.agent import runtime   # the crisis net's own phrases (imported late: runtime imports this file)
    return bool(runtime.CRISIS.search(str(text).lower()) or friendcheck.at_risk(text))


def read(text):
    """Which move this message calls for: {"move": ..., "own": they asked for Luma's own read} or None. Nothing is read
    when they might not be safe or are hurting, or when the answer needs a fresh look (that's fresh())."""
    text = " ".join(str(text or "").split())
    if not text or len(text) > 400:
        return None
    # The safety net and the brain's safety question run whatever this says. This keeps a "have a take" line away from
    # someone the net would answer, or who is hurting.
    if _unsafe(text):
        return None
    if ABOUT.search(text):   # "do you get lonely" asks about Luma: the feeling word in it isn't theirs
        return None if (feelings.read(ABOUT.sub(" ", text)) or {}).get("heavy") else {"move": "about_luma", "own": False}
    if (feelings.read(text) or {}).get("heavy"):
        return None
    if HOT.search(SAID_NOT_ASKED.sub(" ", text)) and QUESTION.search(text):
        return {"move": "fair", "own": bool(OWN.search(text))}
    if SPAT.search(text):   # about their own life: with any sign at all, the safety question comes first and this says nothing
        return None if friendcheck.worth_asking(text) else {"move": "their_side", "own": False}
    if fresh(text):
        return None
    if TEA.search(text):
        return {"move": "tea", "own": False}
    if EXCITED.search(text) and COMING.search(text) and "?" not in text:
        return {"move": "hype", "own": False}
    if THINK.search(text):
        return {"move": "think", "own": False}
    if TAKE.search(text) or _choice(text):
        return {"move": "take", "own": True}
    return None


def note(text, earlier=()):
    """The one line for the brain, or "". earlier: what they said before this message, oldest first."""
    earlier = [str(line) for line in earlier or () if isinstance(line, str)]
    if any((feelings.read(line) or {}).get("heavy") for line in earlier[-3:]):
        return ""  # a minute after something hard, staying with them comes first
    found = read(text)
    if found:
        return FAIR_OWN if found["move"] == "fair" and found["own"] else LINES[found["move"]]
    text = str(text or "")
    if fresh(text) and not (_unsafe(text) or (feelings.read(text) or {}).get("heavy")):
        return LINES["look_up"]
    return ""


# -------------------------------------------------------------------------------------------- the things people say ---
_PACKS = None


def packs():
    """Every pack, in name order: {"family", "slots", "frames": [(move, frame), ...]}."""
    global _PACKS
    if _PACKS is None:
        from luma.agent.friendtalk import packs as home
        found = []
        for info in sorted(pkgutil.iter_modules(home.__path__), key=lambda item: item.name):
            module = importlib.import_module(f"{home.__name__}.{info.name}")
            found.append({"family": module.FAMILY, "slots": {name: list(values) for name, values in module.SLOTS.items()},
                          "frames": [(move, frame) for move, frame in module.FRAMES]})
        _PACKS = found
    return _PACKS


def _ways(pack, frame):
    ways = 1
    for slot in re.findall(r"\{(\w+)\}", frame):
        ways *= len(pack["slots"][slot])
    return ways


def count():
    """How many distinct lines the packs multiply out to."""
    return sum(_ways(pack, frame) for pack in packs() for _, frame in pack["frames"])


def _nth(pack, move, frame, index):
    said = frame
    for slot in re.findall(r"\{(\w+)\}", frame):
        values = pack["slots"][slot]
        said = said.replace("{" + slot + "}", values[index % len(values)], 1)
        index //= len(values)
    return {"said": said, "move": move, "family": pack["family"]}


def scenarios(n=None, seed=0):
    """Scenarios from the packs: what they said, the move a best friend makes, the family. n distinct ones picked evenly
    across everything (the same ones for the same seed), or all of them in order when n is None."""
    table = [(pack, move, frame, _ways(pack, frame)) for pack in packs() for move, frame in pack["frames"]]
    total = sum(ways for *_, ways in table)
    if n is None:
        picks = range(total)
    else:
        picks = sorted(random.Random(seed).sample(range(total), min(n, total)))
    at, start = 0, 0
    seen = set()
    for pick in picks:
        while pick >= start + table[at][3]:
            start += table[at][3]
            at += 1
        row = _nth(table[at][0], table[at][1], table[at][2], pick - start)
        if row["said"] not in seen:   # two frames can fill in to the same words
            seen.add(row["said"])
            yield row
