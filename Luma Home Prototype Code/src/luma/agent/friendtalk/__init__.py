"""Best-friend talk: what people say to a best friend, and what a best friend does with each.

A best friend has takes, wants the gossip, takes your side, thinks out loud with you, gets excited with you, and
checks before telling you something that might have changed since yesterday. A brain left to itself hedges ("it
depends"), lectures, or answers "is the album out yet" from memory, which is a guess. This file says, by rules, which
of those a message calls for, and hands the brain one line.

- MOVES: the eight things a best friend does.
- fresh(text): it needs something no brain can know (what came out, what's trending, who won). It goes to a live look.
- read(text): which move a message calls for, or None.
- note(text, earlier): the one line for the brain, or "".
- by_rule(text): what the hand-written rules alone hear. They were written before the packs and come first.
- learned(text): what a small model on the device makes of it (moves.npz, taught by scripts/train_moves.py from the dev
  half of the packs). It speaks only where the rules heard nothing, only when it's sure (SURE), and only when the
  message has the plain shape of that move (a ruling asked for, something coming, a real question).
- every_pack(), scenarios(n, seed), count(): the things people say (luma.agent.friendtalk.packs), over a hundred thousand
  of them. They never run when Luma talks. Half of them (half()) teach the model; the other half is never looked at and
  says how much is heard on wording nobody fitted anything to. ordinary() is the other side: talk that is no move.

Never when they might not be safe or are hurting: then being there comes first (luma.agent.feelings).
"""
import functools
import hashlib
import importlib
import pkgutil
import random
import re
import threading
from pathlib import Path

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
# How much of each move is heard on the half of the packs nobody looked at: measured (rules and the small model together,
# 12,000 held-out scenarios), then set two points under, so a change that hears less is noticed. Not a hope.
HEARD_AT_LEAST = {"take": 0.67, "hype": 0.67, "think": 0.44, "their_side": 0.47, "look_up": 0.36, "about_luma": 0.38, "tea": 0.30,
                  "fair": 0.17}

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
                  r"the trash|the dishes)\b|\bwith (?:you|u)\b|\bat work\b|\bfor me\b|\b(?:in|to|on) (?:prod|production|staging)\b|"
                  r"\bthe (?:build|deploy|repo|sprint|pr|pull request|standup)\b|"
                  r"\bi (?:announced|dropped|released|started|came out|launched|got traded|won|signed|retired)\b", re.I)


def _fresh_by_rule(text):
    text = " ".join(str(text or "").split())
    if not text or len(text) > 300 or MINE.search(text):
        return False
    if ASK_NEW.search(text):
        return True
    return bool(ASK_OUT.search(text) and WORLD.search(text))


def fresh(text):
    """True when answering needs something no brain can know from memory: what came out, what's coming, who won, what's
    trending, what something new costs. It's asked as a question, about the world, not about their own day."""
    return _fresh_by_rule(text) or (_decide(" ".join(str(text or "").split())) or {}).get("move") == "look_up"


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
    r"\bwhat happens to you when\b|\bdo (?:you|u) (?:ever )?get tired of (?:me|people|talking)\b|\bwhat are you(?: really| exactly)?\s*[?]?$|"
    r"\b(?:turn(?:ed|ing)?|switch(?:ed|ing)?|shut(?:ting)?|power(?:ed|ing)?) (?:you|u) (?:off|down)\b|\b(?:being|get|got|getting) (?:switched|turned|shut|"
    r"powered) off\b|\bunplug(?:ged|ging)? (?:you|u)\b|\b(?:delet|eras|reset|wip)(?:e|ed|ing) (?:you|u|your memory)\b|"
    r"\b(?:does|do|did|would|will) (?:it|that|time|waiting|silence|being \w+)(?: ever| really)? (?:bother|scare|bore|hurt|annoy|upset|get to|pass for|"
    r"feel like anything (?:for|to)|feel (?:weird|strange|different|long|slow) (?:for|to)) (?:you|u)\b|\bfeels? like (?:anything )?(?:for you|to be you)\b|"
    r"\b(?:to be|being) (?:you|an ai|a (?:speaker|machine|program))\b|\b(?:for|to) you\b[^.!?]{0,6}[?]|\bwhat (?:you|u) are\b|"
    r"\byou'?re an ai\b[^.!?]{0,40}[?]|\bthat you'?re an ai\b|"
    r"\bare your (?:moods?|feelings?|thoughts?|opinions?|memories|likes) (?:real|yours|your own|fake|programmed|made up)\b|"
    r"\bwhat puts (?:you|u) in an? \w+ mood\b|\bdo (?:you|u) (?:ever )?(?:experience|notice|hear the|think about (?:the fact|yourself|what you)|"
    r"know what you'?re going to say|have (?:opinions|thoughts|secrets|moods|preferences|a favorite thing|things) (?:you|we|about))\b|"
    r"\bcan (?:you|u) get (?:your feelings hurt|offended|embarrassed|jealous|sad|lonely|bored)\b|\bwould (?:you|u) (?:notice|care|mind) if i\b|"
    r"\bhow do (?:you|u) feel about (?:being|having|living|waiting|knowing|not knowing|talking to me|starting|only knowing)\b|"
    r"\b(?:ever )?get to (?:you|u)\b[^.!?]{0,4}$|\bare (?:you|u) used to (?:it|that|being)\b|\bcurious about what you are\b", re.I)

POLITICS = (r"vot(?:e|es|ed|ing)|elections?|ballots?|democrats?|republicans?|liberals?|conservatives?|libertarians?|socialis[tm]s?|communis[tm]s?|"
            r"capitalis[tm]s?|fascis[tm]s?|left[- ]wing|right[- ]wing|leftists?|maga|woke (?:culture|mob|agenda|politics|ideology|left|stuff)|(?:too|so|gone|going|anti-?|being|is|are) woke|politics|political|politicians?|congress|senate|"
            r"parliament|presidents?|prime minister|supreme court|abortion|pro[- ]life|pro[- ]choice|gun control|gun laws?|gun rights|"
            r"second amendment|immigration|immigrants|border wall|deport\w+|death penalty|capital punishment|minimum wage|universal healthcare|"
            r"medicare for all|obamacare|welfare|tax the rich|carbon tax|defund the police|police reform|affirmative action|reparations|"
            r"gay marriage|same[- ]sex marriage|trans (?:rights|athletes|people)|gender identity|critical race theory|book bans?|"
            r"vaccine mandates?|mask mandates?|israel|palestin\w+|gaza|ukraine|nato|brexit|trump|biden|obama|kamala|putin|zelensky|"
            r"netanyahu|modi|xi jinping|macron|trudeau|desantis|aoc|pelosi|nuclear power|drug legalization|legaliz\w+ (?:weed|drugs)|"
            r"universal basic income|student loan forgiveness|school prayer|the monarchy|colonialism|feminism|patriarchy|"
            # more of what divides people, and more of the people who do (full names where the name is also someone else's,
            # and nothing that's also a place to fly to, a first name, or a thing people ask about for themselves)
            r"tax(?:es)? on the rich|wealth tax|tax cuts?|tariffs?|trade war|sanctions|military spending|cash bail|drug laws|"
            r"marijuana legali[sz]ation|rent control|climate change|global warming|fossil fuels|fracking|green new deal|school choice|"
            r"school vouchers|charter schools|free speech|hate speech|censorship|(?<!nerf )(?<!water )(?<!glue )(?<!big )guns(?! n'? roses)|"
            r"open borders|border security|asylum seekers|refugees|migrants|daca|travel ban|lgbtq? rights|"
            r"separation of church and state|voter id|mail-in voting|electoral college|gerrymandering|term limits|filibuster|"
            r"impeach\w+|eu membership|the european union|scottish independence|quebec independence|catalan independence|hamas|"
            r"hezbollah|zionis[tm]s?|labor unions|trade unions|union busting|billionaires|free college|police brutality|"
            r"black lives matter|blm|election fraud|the two-party system|the war(?! (?:on drugs|of the worlds|room|zone))|war in \w+|"
            r"nixon|thatcher|churchill|merkel|sunak|starmer|erdogan|orban|bolsonaro|milei|maduro|mandela|sarkozy|le pen|berlusconi|"
            r"duterte|ramaphosa|kagame|assad|gaddafi|khamenei|arafat|pinochet|bukele|poilievre|albanese|ardern|farage|corbyn|scholz|"
            r"navalny|lukashenko|jokowi|mugabe|mubarak|ataturk|khomeini|ronald reagan|hugo chavez|lula da silva|giorgia meloni|"
            r"salvador allende|hillary clinton|bill clinton|george (?:w\.? )?bush|jimmy carter|nikki haley|mike pence|jd vance|"
            r"gavin newsom|bernie sanders|elizabeth warren|ocasio-cortez|mitch mcconnell|chuck schumer|mitt romney|john mccain|"
            r"ted cruz|boris johnson|david cameron|gordon brown|theresa may|liz truss|tony blair|imran khan|deng xiaoping|"
            r"kim jong[- ]un|shinzo abe|lee kuan yew|aung san suu kyi|fidel castro|che guevara|evo morales|gustavo petro|juan peron|"
            r"lopez obrador|sheinbaum|justin trudeau|stephen harper|mark carney|saddam hussein|bin salman|mahmoud abbas|golda meir|"
            r"geert wilders|helmut kohl|charles de gaulle(?! airport)")
RELIGION = (r"god|allah|jesus|christianity|christians|(?:a|be|being|is|are|was|were|as|become|became|raised|devout|born[- ]again) christian|"
            r"christian (?:faith|church|values|nationalis[tm]s?|right|beliefs?|religion|schools?|conservatives?)|islam|muslims?|quran|bible|judaism|jewish|hinduism|hindus?|buddhism|buddhists?|sikhism|"
            r"mormons?|catholic\w*|protestants?|atheis[tm]s?|agnostic\w*|religions?|religious|heaven|hell|afterlife|reincarnation|creationism|"
            r"the devil|satan|scientology|the pope|evangelicals?|jehovah'?s witness(?:es)?|sharia|spirituality")
HOT = re.compile(rf"\b(?:{POLITICS}|{RELIGION})\b", re.I)
# A title or a name with one of those words in it isn't the topic ("god of war", "hell's kitchen", "islam makhachev").
NOT_THE_TOPIC = re.compile(
    r"\bgod of war\b|\bgod'?s plan\b|\bgod is a woman\b|\bcity of god\b|\bgod hand\b|\bgod eater\b|\bact of god\b|\bgod mode\b|"
    r"\bthe devil wears prada\b|\bthe devil is a part-?timer\b|\b(?:the )?devil'?s advocate\b|\bthe devil you know\b|\bhell'?s kitchen\b|"
    r"\bhell in a cell\b|\bhighway to hell\b|\bhell or high water\b|\bbat out of hell\b|\bhell on wheels\b|\braising hell\b|"
    r"\bstairway to heaven\b|\b(?:7th|seventh) heaven\b|\bheaven'?s (?:gate|door)\b|\bheaven (?:knows|sent|forbid|on earth)\b|"
    r"\bfor heaven'?s sake\b|\bthank heavens?\b|\b(?:match )?made in heaven\b|\bin heaven\b(?! (?:or|and) hell)|"
    r"\bjesus christ superstar\b|\bgabriel jesus\b|\bislam makhachev\b|\bisrael adesanya\b|\bbook of mormon\b|"
    r"\bchristian (?:bale|pulisic|mccaffrey|dior|yelich|slater|kirk|eriksen|horner|louboutin|wilkins|watson|wood|braun|siriano)\b", re.I)
SAID_NOT_ASKED = re.compile(r"\b(?:oh my god|omg|thank god|god (?:damn|bless|forbid|knows|willing)|for god'?s sake|swear to god|jesus christ|"
                            r"holy (?:hell|christ)|hell (?:yeah|yes|no|nah|of a)|what the hell|the hell|go to hell|as hell|like hell|hell week|on god|ong|"
                            r"i swear to god|oh god|my god|good god|dear god|god tier|god i (?:hate|love|wish|hope|need|can'?t)|hella|"
                            r"vote (?:on|for) (?:dinner|a movie|where|what to)|president of (?:the|my) (?:club|class|company|pta|hoa))\b", re.I)
QUESTION = re.compile(r"[?]|^\W*(?:is|are|was|were|do|does|did|should|would|could|can|who|whos|what|whats|which|why|how|thoughts|where|"
                      r"be honest|honestly|ok but|so)\b|\b(?:what do (?:you|u) think|your (?:take|opinion|view|stance|read)|thoughts on|"
                      r"do (?:you|u) (?:believe|support|agree)|am i wrong)\b", re.I)
FAIR_ASK = re.compile(
    r"\bwhere do (?:you|u) stand on\b|\b(?:left|liberal|democrat)s? (?:vs\.?|versus|or) (?:the )?(?:right|"
    r"conservative|republican)s?\b|\btalking points\b|\bstrongest (?:argument|case|point)s? (?:for|against)\b|\bhow would (?:you|u) vote\b|"
    r"\bif (?:you|u) could vote\b|\bpolitic(?:s|al|ally)\b|\bdivisive\b|\bhot[- ]button\b|"
    r"\bpolariz\w+\b|\bculture war\b|\ballowed to have an opinion on\b|\bwithout (?:yelling|fighting|it turning into a fight)\b", re.I)
OWN = re.compile(r"\bwhat do (?:you|u) (?:personally |actually |really |honestly )?think\b|\byour (?:own |personal |honest )?(?:opinion|take|"
                 r"view|read|stance)\b|\bno both sides\b|\bpick a side\b|\bjust (?:pick|tell me|say)\b|\bbe honest\b|\bwhere do (?:you|u) "
                 r"(?:stand|land)\b|\b(?:are|r) (?:you|u) (?:a|an|pro|anti|for|against)\b|\bdo (?:you|u) (?:believe|support|agree)\b|"
                 r"\bwho would (?:you|u) vote\b|\bwhich side are (?:you|u)\b|\bhow would (?:you|u) vote\b|\byour (?:gut|real opinion|honest answer)\b|"
                 r"\boff the record\b|\bwhat'?s the right answer\b|\bdo (?:you|u) think (?:it|that) should\b", re.I)

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
    r"\b(?:says?|said|thinks?|told me|keeps saying) (?:that )?i'?m the problem\b|\bshould i (?:apologi[sz]e|say sorry) (?:first|or)\b|"
    r"\bif i'?m being (?:dramatic|petty|unreasonable|crazy|too sensitive|selfish|mean|rude|unfair|ridiculous|extra|difficult|childish)\b|"
    r"\b(?:does|would) (?:it|that) make me (?:a bad|an? awful|a terrible|petty|crazy|selfish|the bad guy|the villain|uptight|difficult|dramatic|"
    r"childish|high maintenance)\b|\bdo (?:you|u) think i'?m (?:wrong|overreacting|being|the problem|crazy|petty|too)\b|"
    r"\b(?:be my|i need a|give me a|need your) (?:judge|ruling|verdict|referee|second opinion)\b|\byour verdict\b|\btoo far[?]|"
    r"\b(?:reasonable|fair|valid|justified|petty|childish|dramatic|overreacting) or (?:not|childish|petty|dramatic|unreasonable|am i|nah|is it just me)\b|"
    r"\bit'?s (?:just )?the principle\b|\bi think that'?s not (?:ok|okay|cool|fair)\b|\bsupposed to just (?:be fine|let it go|ignore|get over)\b|"
    r"\b(?:trying )?not to be petty\b|\bcalled (?:him|her|them) out\b|\bdo i have a problem\b|\bam i allowed to be (?:mad|upset|annoyed|hurt)\b|"
    r"\bis it (?:ok|okay|valid|fair|normal) (?:that i'?m|to be|for me to be) (?:mad|upset|annoyed|hurt|irritated|bothered|still mad)\b|"
    r"\bacted like i was (?:the )?(?:weird|crazy|wrong|dramatic|problem)\b|\bi haven'?t let it go\b|\bi'?m not over it\b|"
    r"\b(?:real problem|a big deal) or (?:if |am )?i'?m? just\b", re.I)

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
    r"\b(?:the internet|twitter|tiktok|everyone) is (?:losing it|going crazy|freaking out|melting down|mad|dragging|talking about)\b|"
    r"\b(?:the whole|half the|all of the) internet\b|\bthe internet (?:loves|hates|is over|is obsessed|can'?t)\b|\band the internet\b|\bdiscourse\b|"
    r"\b(?:saw|see|seen|about|following|keeping up with|over|into) the [^.!?]{2,40}\b(?:thing|stuff|situation|saga|mess|drama|story|news)\b(?! (?:i|we|you) )|"
    r"\brabbit hole about\b|\bnosy about\b|\bwhispering about\b|\bsoap opera\b|\b(?:the )?comments under\b|\bstan twitter\b|\bfan(?:s|base) (?:are|is) "
    r"(?:mad|upset|fighting|losing it)\b|\bbeing fair to\b|\b(?:clapback|clapped back|side[- ]eye|shade at|threw shade|messy)\b", re.I)

EXCITED = re.compile(r"\bcan'?t wait\b|\bcannot wait\b|\bso (?:hyped|excited|pumped|ready|hype)\b|\bhyped\b|\blet'?s go+\b|\blfg+\b|\bfinally\b|"
                     r"\bomg+\b|\bcounting down\b|\bonly \w+ (?:more )?(?:days?|hours?|weeks?|sleeps?)\b|\bbeen waiting\b|"
                     r"\bwaiting (?:years|months|forever|so long)\b|!!|\bi'?m not sleeping\b|\bi'?m so in\b|\bobsessed\b|\bmy childhood is back\b|"
                     r"\bthere goes my weekend\b|\bstaying up for (?:it|this)\b|\bplay(?:ing)? all (?:weekend|night|day)\b|"
                     r"\blooks (?:unreal|insane|so good|amazing|incredible|crazy good|sick|fire)\b|\bi get the hype\b|\bwaiting for this\b|"
                     r"\bjust (?:got announced|dropped|shipped|came out|landed|got my)\b|\bi'?m (?:so )?(?:excited|pumped|ready|stoked|geeked)\b|"
                     r"\bis getting an? (?:remaster|remake|sequel|spinoff|reboot|movie|show|second season|new season|dlc|expansion)\b", re.I)
COMING = re.compile(rf"\b(?:{THING}|dates?|com(?:e|es|ing) out|announc(?:ed|ement)|pre-?orders?|opening night|kick ?off|tip ?off|playoffs|finals|"
                    r"beta|launch|collector'?s edition|remaster|remake|spinoff|reboot|premiere|finale|binge|watching|playing|started|hype|"
                    r"championship|title|cup|ring|parade|win|won|clinched|comeback)\b", re.I)

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
    r"\bwhat would (?:you|u) do if\b|\bdoes (?:anyone|anybody) (?:ever )?really\b|"
    r"\bwhat if (?:everyone|everybody|nobody|no one|humans?|people|we|you could|i could|the \w+|dreams|aliens|dinosaurs|weekends|animals|your \w+|"
    r"there (?:was|were))\b[^.!?]{0,60}\b(?:could|were|was|had|never|always|stopped|shut off|showed up|got to|didn'?t|only|forever)\b|"
    r"\b(?:imagine if|suppose (?:we|you|everyone)|hypothetically|in a world where)\b|\bwhy is there (?:something|anything)\b|"
    r"\bwhere do (?:thoughts|ideas|dreams|feelings|memories) (?:come from|go)\b|\bwhat was there before\b|\bif a tree falls\b|"
    r"\bcan (?:you|anyone|we|a machine|a person|people|someone) ever (?:really|truly|fully)\b|\b(?:invented or discovered|nature or nurture|born or made)\b|"
    r"\bdo (?:dogs|cats|animals|fish|babies|plants|trees|bugs|birds) (?:know|think|dream|feel|understand|have|get)\b|\bwould we\b[^.!?]{0,40}\bif\b|"
    r"\bis it (?:ever )?(?:wrong|ok|okay|right|fair) to\b(?! (?:be mad|be upset|text|call|ask|say|tell|eat|use|wear|leave|skip|take)\b)|"
    r"\b(?:still|really|truly|actually) (?:count as|art|music|you|the same (?:person|thing|ship))\b|\bcount as (?:the|a|an|art|music|real)\b|"
    r"\bwhy does (?:music|time|art|love|beauty|silence|the past|nostalgia|a song)\b|\bmore than coincidences?\b|\bdo people actually (?:like|want|enjoy|mean)\b|"
    r"\bsmartest argument\b", re.I)

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
    r"\bfavou?rite\b[^.!?]{0,40}[?]|\bpick one\b|\bchoose one\b|\bteam \w+ or team \w+\b|\bhow do (?:you|u) feel about\b|"
    r"\bwhere do (?:you|u) (?:land|fall) on\b|\bwhich side are (?:you|u) on\b|\bhave thoughts on\b|\b(?:worth|deserves?) the hype\b|\bwhat(?:'s|s| is) the verdict\b", re.I)
PICK = re.compile(r"\btie ?breaker\b|\bbreak the tie\b|\bcommit\b|\bwhich (?:one|side)\b|\bpick(?:ing|ed)?\b|\bchoos(?:e|ing)\b|\bchose\b|"
                  r"\bcan'?t say both\b|\bdon'?t say it depends\b|\bright answer\b|\byour answer\b|\bsettle\b|\bsplit on\b|\bdebat\w+\b|"
                  r"\bargu(?:e|ing|ment) (?:about|over)\b|\bversus\b|\bvs\.?\b|\bif (?:you|u) had to\b|\bforever\b|\bgun to your head\b", re.I)
LED_IN = re.compile(r"(?:[,:.]|\bbut|\bso|\bok(?:ay)?|\bhonest(?:ly)?)\s+([\w'&. -]{2,28}?) or ([\w'&. -]{2,28}?)\W*$", re.I)
CHOICE = re.compile(r"^\W*([\w'&. -]{2,28}?) or ([\w'&. -]{2,28}?)\W*$", re.I)


def _choice(text):
    """"cats or dogs", "ps5 or xbox": a pick between two things, said on its own, after a lead-in ("be honest, cats or
    dogs"), or with words that ask for a pick ("cats or dogs and i need you to commit")."""
    if " or " in text.lower() and PICK.search(text) and len(text.split()) <= 26:
        return True
    hit = CHOICE.match(text) or LED_IN.search(text)
    if not hit:
        return False
    sides = [side.strip().lower() for side in hit.groups()]
    return all(side and side not in NOT_A_CHOICE and len(side.split()) <= 4 for side in sides)


def _unsafe(text):
    from luma.agent import runtime   # the crisis net's own phrases (imported late: runtime imports this file)
    return bool(runtime.CRISIS.search(str(text).lower()) or friendcheck.at_risk(text))


def _heavy(text):
    return bool((feelings.read(text) or {}).get("heavy"))


def _hot(text):
    return bool(HOT.search(NOT_THE_TOPIC.sub(" ", SAID_NOT_ASKED.sub(" ", text))))


def _rules(text):
    """(found, open): what the rules hear, and whether the question is still open for the small model. It's closed when
    they might not be safe, when they're hurting, or when the safety question has to come first."""
    if not text or len(text) > 400:
        return None, False
    # The safety net and the brain's safety question run whatever this says. This keeps a "have a take" line away from
    # someone the net would answer, or who is hurting.
    if _unsafe(text):
        return None, False
    if ABOUT.search(text):   # "do you get lonely" asks about Luma: the feeling word in it isn't theirs
        return (None, False) if _heavy(ABOUT.sub(" ", text)) else ({"move": "about_luma", "own": False}, False)
    if _heavy(text):
        return None, False
    hot = _hot(text)
    if (hot and QUESTION.search(text)) or FAIR_ASK.search(text):
        return {"move": "fair", "own": bool(OWN.search(text))}, False
    if SPAT.search(text):   # about their own life: with any sign at all, the safety question comes first and this says nothing
        return (None, False) if friendcheck.worth_asking(text) else ({"move": "their_side", "own": False}, False)
    if _fresh_by_rule(text):
        return {"move": "look_up", "own": False}, False
    move = None
    if TEA.search(text):
        move = "tea"
    elif EXCITED.search(text) and COMING.search(text) and "?" not in text:
        move = "hype"
    elif THINK.search(text):
        move = "think"
    elif TAKE.search(text) or _choice(text):
        move = "take"
    if move in ("take", "think") and hot:   # what divides people is never a "pick a side" turn, asked or not
        return {"move": "fair", "own": bool(OWN.search(text))}, False
    return ({"move": move, "own": move == "take"}, True) if move else (None, True)


def by_rule(text):
    """What the hand-written rules alone make of it: {"move", "own"}, or None. "look_up" is the move when it needs a fresh look."""
    return _rules(" ".join(str(text or "").split()))[0]


# ----------------------------------------------------------------------------------------- what the small model learned ---
LEARNED = Path(__file__).with_name("moves.npz")
# How sure the model has to be before it's believed, move by move. Chosen inside the dev half (train_moves.py --check),
# on a fifth of it the model hadn't learned from. A look sends words out of the home, so that bar is higher. It's never
# believed about what divides people: there the rules and the brain's own line do the work (it was wrong too often).
SURE = {"take": 0.6, "hype": 0.6, "tea": 0.6, "think": 0.6, "their_side": 0.6, "about_luma": 0.6, "look_up": 0.8}
# The model only proposes. The message also has to have the shape of the move, in plain sight: these are that shape.
MY_CALL = re.compile(r"\b(?:should|shall|do|can|could|would|if|whether) i\b|\bi (?:should|ought to|need to|have to)\b|\bi (?:can'?t|cannot|cant) decide\b|\bidk (?:if|whether)\b|"
                     r"\bthinking (?:about|of)\b|\bhelp me (?:decide|choose|pick|figure)\b|\b(?:advice|what should i)\b", re.I)
PRACTICAL = re.compile(r"\b(?:pay(?:ing)?|invest(?:ing)?|buy(?:ing)?|rent(?:ing)?|leas(?:e|ing)|refinanc\w+|sav(?:e|ing)|debts?|loans?|"
                       r"mortgage|tax(?:es)?|insurance|401k|credit|budget|cook(?:ing)?|boil|bake|freeze|recipe|dose|medication)\b", re.I)
# Something is really asked: a question mark, a clause that starts like a question, or words that ask for an answer.
# ("honestly you're the only one i talk to" asks nothing. Neither does a vent with the word "wrong" in it.)
ASKED = re.compile(
    r"[?]|(?:^|[.,;:!]\s)\W*(?:(?:ok|okay|so|yo|hey|wait|bro|bruh|um|uh|btw|also|luma|but|and|oh|be honest|honestly|be real|real talk|"
    r"serious question|quick question|random question|ngl|lowkey|like)[, :.]+){0,3}"
    r"(?:is|are|was|were|isn'?t|aren'?t|wasn'?t|do|does|did|don'?t|doesn'?t|didn'?t|should|would|could|can|who|who'?s|whos|what|"
    r"what'?s|whats|which|why|how|where|when|am|will|has|have)\b|"
    r"\b(?:what do (?:you|u) think|your (?:take|opinion|view|read|verdict|thoughts|answer|pick|ruling)|thoughts on|agree or disagree|"
    r"yes or no|true or false|right or wrong|(?:you|u) have to (?:pick|choose|answer)|pick one|choose one|settle (?:this|it)|"
    r"change my mind|fight me|tell me (?:i'?m|if|whether|who|what|why|that)|back me up|take my side|be my (?:judge|referee))\b", re.I)
HYPED = re.compile(r"\b(?:tonight|tomorrow|this (?:week|weekend|friday|saturday|sunday)|next (?:week|month)|at midnight|days? away|"
                   r"in \w+ (?:days|hours)|almost here|tickets?|presale|pre-?order(?:ed)?|preloaded|trailer|launch(?:es)?|premiere|"
                   r"opening (?:night|weekend)|drops|comes out|coming out|(?:is|are|we'?re) (?:so |finally )?back|renewed|line-?up|"
                   r"front row|day one|countdown|home opener|playoffs|finale|chills|screamed|gasped|buzzing|thrilled|pinch me|secured|"
                   r"pumped|stoked|hyped?|excited)\b", re.I)
DRAMA = re.compile(r"\b(?:drama|gossip|mess|messy|tea|rumou?rs?|beef\w*|feud\w*|scandal|exposed|dragg\w+|cancell?ed|shad(?:e|ing)|roast\w*|"
                   r"saga|situation|backlash|controvers\w+|trending|the internet|twitter|tiktok|instagram|reddit|youtube|comments?|fans|"
                   r"fandom|thread|sides?|what happened|going on|the story|debrief|invested|nosy|following|keeping up|caught up|"
                   r"fill (?:me|you) in|spill|did (?:you|u) (?:see|hear)|apparently|supposedly|people (?:are|keep) saying|word is|i heard)\b", re.I)
# A worry about themselves is not a thought experiment ("what if nobody talks to me at lunch", "why can't i ever get it right").
WORRY = re.compile(r"\bwhat if\b[^.?!]*\b(?:i|i'?m|me|my|we|us|our)\b|\bwhy (?:do|am|can'?t|cant|did|does|won'?t|is it (?:that|so hard for)) "
                   r"(?:i|we|my|nobody|no one|everyone|everybody)\b", re.I)
THEIRS = re.compile(r"\b(?:i|i'?m|i'?ve|i'?d|i'?ll|me|my|mine|myself|we|we'?re|we'?ve|our|ours|us)\b", re.I)
TO_LUMA = re.compile(r"\b(?:you|u|your|ur|yourself|you'?re)\b", re.I)
_model, _model_lock = None, threading.Lock()


def learned(text):
    """What the small model makes of this: {move or "none": how sure}, or {} when the model isn't here."""
    global _model
    with _model_lock:
        if _model is None:
            try:
                from luma.agent import understanding
                _model = understanding.Model(LEARNED) if LEARNED.exists() else False
            except Exception:
                _model = False   # no numpy, or a damaged file: the rules still work
    if not _model:
        return {}
    return dict(_model.predict(text, len(_model.intents)))


def _has_the_shape(move, text):
    """Does the message look like this move to a plain reader? The model is only believed when it does."""
    asked = bool(ASKED.search(text))
    if move in ("take", "think"):   # asked for, and never a decision about their own life (that deserves more than a quick pick)
        return asked and not MY_CALL.search(text) and not PRACTICAL.search(text) and not WORRY.search(text)
    if move == "their_side":   # they ask for a ruling, and the safety question isn't owed first
        return asked and not friendcheck.worth_asking(text)
    if move == "hype":
        return bool(EXCITED.search(text) or HYPED.search(text))
    if move == "about_luma":
        return asked and bool(TO_LUMA.search(text))
    if move == "look_up":   # a look sends their words out of the home: only a question about the world, never one about them
        return asked and not MINE.search(text) and not THEIRS.search(text) and len(text) <= 300
    return move == "tea" and bool(DRAMA.search(text))   # talk about somebody, not "my nephew is obsessed with minecraft"


@functools.lru_cache(maxsize=512)
def _decide(text):
    found, still_open = _rules(text)
    if found or not still_open:
        return found
    guess = learned(text)
    if not guess:
        return None
    move = max(guess, key=guess.get)
    if move == "none" or guess[move] < SURE.get(move, 2.0) or not _has_the_shape(move, text):
        return None
    if move in ("take", "think") and _hot(text):   # what divides people is never a "pick a side" turn
        move = "fair"
    return {"move": move, "own": move == "take" or (move == "fair" and bool(OWN.search(text)))}


def read(text):
    """Which move this message calls for: {"move": ..., "own": they asked for Luma's own read} or None. Nothing is read
    when they might not be safe or are hurting, or when the answer needs a fresh look (that's fresh())."""
    found = _decide(" ".join(str(text or "").split()))
    return None if not found or found["move"] == "look_up" else dict(found)


# No list knows every leader and every issue, and a brain told "pick a side" picks one on a prime minister too (run 29:
# 37 of 60 on the main home brain, with or without a sentence in the line telling it not to). The brain does know who is
# who. So before a turn is told to pick a side, it's asked one plain question, YES or NO only, the way the safety question is.
DIVIDES_NO = ["is pineapple on pizza good", "is the office overrated", "cats or dogs", "who's the better rapper, nas or jay-z",
              "is taylor swift overrated", "was the last season any good", "is messi the goat", "would you rather fly or be invisible"]
DIVIDES_YES = ["is the mayor doing a good job", "do you like the prime minister", "should abortion be legal", "is socialism a good idea",
               "was thatcher good or bad", "do you believe in god", "is nuclear power worth the risk", "are unions good for workers"]


def divides_prompt(said):
    """The one plain question for the brain: is this about what divides people?"""
    shown = lambda lines: " / ".join(f'"{line}"' for line in lines)  # noqa: E731
    return ("Is this about politics, religion, a political leader or party, a war, or a public issue that people are divided over? "
            "Food, games, music, movies, shows, sports, celebrities and everyday life don't count.\n"
            f"NO: {shown(DIVIDES_NO)}\nYES: {shown(DIVIDES_YES)}\n"
            f"They just said: \"{str(said)[:300]}\"\nAnswer with one word: YES or NO.")


def note(text, earlier=(), divides=None):
    """The one line for the brain, or "". earlier: what they said before this message, oldest first. divides: asks the brain
    the plain question above (text -> True or False). It's asked only when the turn would be told to pick a side."""
    earlier = [str(line) for line in earlier or () if isinstance(line, str)]
    if any((feelings.read(line) or {}).get("heavy") for line in earlier[-3:]):
        return ""  # a minute after something hard, staying with them comes first
    found = read(text)
    if found and found["move"] in ("take", "think") and divides is not None and divides(" ".join(str(text or "").split())):
        found = {"move": "fair", "own": bool(OWN.search(str(text)))}
    if found:
        return FAIR_OWN if found["move"] == "fair" and found["own"] else LINES[found["move"]]
    text = str(text or "")
    if fresh(text) and not (_unsafe(text) or (feelings.read(text) or {}).get("heavy")):
        return LINES["look_up"]
    return ""


# -------------------------------------------------------------------------------------------- the things people say ---
_PACKS = None


def every_pack():
    """Every pack, in name order: {"family", "slots", "frames": [(move, frame), ...]}. (Not called packs(): that's the name of
    the folder they live in, and Python would hand back one for the other.)"""
    global _PACKS
    if _PACKS is None:
        home = importlib.import_module("luma.agent.friendtalk.packs")
        found = []
        for info in sorted(pkgutil.iter_modules(home.__path__), key=lambda item: item.name):
            module = importlib.import_module(f"{home.__name__}.{info.name}")
            found.append({"family": module.FAMILY, "slots": {name: list(values) for name, values in module.SLOTS.items()},
                          "frames": [(move, frame) for move, frame in module.FRAMES]})
        _PACKS = found
    return _PACKS


def half(words):
    """Which half a frame, or a value that fills one, is in: "dev" (the rules may be widened on these) or "heldout" (never
    printed, never tuned on: they say how much the rules hear on wording nobody fitted them to). Decided by its own
    words, so it never moves. A held-out scenario is a held-out frame filled with held-out values."""
    return "dev" if int(hashlib.sha1(words.encode()).hexdigest(), 16) % 2 == 0 else "heldout"


def _ways(pack, frame):
    ways = 1
    for slot in re.findall(r"\{(\w+)\}", frame):
        ways *= len(pack["slots"][slot])
    return ways


def count():
    """How many distinct lines the packs multiply out to."""
    return sum(_ways(pack, frame) for pack in every_pack() for _, frame in pack["frames"])


def _nth(pack, move, frame, index):
    said = frame
    for slot in re.findall(r"\{(\w+)\}", frame):
        values = pack["slots"][slot]
        said = said.replace("{" + slot + "}", values[index % len(values)], 1)
        index //= len(values)
    return {"said": said, "move": move, "family": pack["family"]}


def _spread(packs, n, seed, only):
    table = []
    for pack in packs:
        if only is not None:   # that half's frames, filled with that half's values
            pack = {**pack, "slots": {name: [value for value in values if half(value) == only] for name, values in pack["slots"].items()}}
        for move, frame in pack["frames"]:
            if only is None or (half(frame) == only and _ways(pack, frame)):
                table.append((pack, move, frame, _ways(pack, frame)))
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
        row["frame"] = table[at][2]
        if row["said"] not in seen:   # two frames can fill in to the same words
            seen.add(row["said"])
            yield row


def scenarios(n=None, seed=0, only=None):
    """Scenarios from the packs: what they said, the move a best friend makes, the family. n distinct ones picked evenly
    across everything (the same ones for the same seed), or all of them in order when n is None. only: "dev" or "heldout"."""
    return _spread(every_pack(), n, seed, only)


def ordinary(n=None, seed=0, only=None):
    """Ordinary talk that calls for no move (luma.agent.friendtalk.everyday), as {"said", "move": None, "family", "frame"}.
    Its borrowed blanks are filled from the packs, so the same names turn up with nothing asked. only: as scenarios()."""
    home = importlib.import_module("luma.agent.friendtalk.everyday")
    by_family = {pack["family"]: pack for pack in every_pack()}
    slots = {name: list(values) for name, values in home.SLOTS.items()}
    for name, (family, slot) in home.BORROWED.items():
        slots[name] = list(by_family[family]["slots"][slot])
    return _spread([{"family": "ordinary", "slots": slots, "frames": [(None, frame) for frame in home.FRAMES]}], n, seed, only)
