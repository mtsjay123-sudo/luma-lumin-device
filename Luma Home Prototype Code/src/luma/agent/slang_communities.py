"""More communities: the way people talk at work, in scenes, and in more of the world.

Restaurant kitchens, nurses, the military, tech, crypto traders, truckers, theatre kids, gym regulars, sports fans,
South Africa, Singapore and Malaysia, Canada and Toronto, and New Zealand. Same format as slang_data.LEXICON:

    term | other spellings | communities | register | what it means | how to say it

Only words whose meaning is well established go here: Luma explains slang from this list, and the phrase bank and
tests are built on it, so a wrong meaning here would become a wrong answer everywhere. When in doubt, leave it out.
Registers: c casual · v vulgar (cussing; only when the owner allows it).
"""
from __future__ import annotations

ORIGINS = {
    "kitchen": "restaurant and kitchen crews",
    "nurse": "nurses and hospital staff",
    "military": "the US military",
    "tech": "tech and software people",
    "crypto": "crypto and trading",
    "trucker": "truckers and CB radio",
    "theatre": "theatre kids",
    "gym": "the gym",
    "sports": "sports fans",
    "safrica": "South Africa",
    "singlish": "Singapore and Malaysia (Singlish)",
    "canada": "Canada and Toronto",
}

LEXICON = r"""
# --- restaurant and kitchen crews ---
86 | eighty-six, 86'd, eighty-sixed, 86 it | kitchen | c | out of it, or taken off the menu (and "86 him": cut him off) | eighty-six
in the weeds | weeded, in the weeds bad | kitchen | c | swamped, way behind on orders | in the weeds
heard | heard chef, heard that | kitchen | c | understood, got it (answering a call in the kitchen) | heard
behind | behind you | kitchen | c | "I'm walking behind you", so nobody turns into you | behind
hot behind | hot behind you | kitchen | c | "I'm behind you with something hot" | hot behind
corner | corner! | kitchen | c | "I'm coming around the corner", a heads-up so nobody collides | corner
all day | | kitchen | c | the total still to make of one item ("four steaks all day") | all day
on the fly | | kitchen | c | needed right now, rushed | on the fly
expo | expediter, expeditor | kitchen | c | the person at the pass checking plates before they go out | expo
the pass | | kitchen | c | the counter where finished plates wait to be run | the pass
walk-in | the walk-in | kitchen | c | the big walk-in fridge | walk-in
dying in the window | dying on the pass | kitchen | c | food getting cold under the lights because nobody's running it | dying in the window
deuce | two-top, 2-top | kitchen | c | a table for two | deuce
four-top | four top, 4-top | kitchen | c | a table for four | four-top
comp | comped, comp it | kitchen | c | give it for free, on the house | comp
family meal | staff meal | kitchen | c | the meal the crew eats together before service | family meal
mise | mise en place, mise'd | kitchen | c | everything prepped and in its place before service | meez
slammed | | kitchen | c | extremely busy | slammed
the rail | ticket rail | kitchen | c | where tickets hang in the order they came in | the rail
back of house | boh | kitchen | c | the kitchen side of a restaurant | back of house
front of house | foh | kitchen | c | the dining room side: servers, hosts, the bar | front of house
campers | | kitchen | c | guests who sit at a table long after they've finished | campers
stiffed | got stiffed | kitchen | c | left no tip | stiffed
fire it | fire table, fire that | kitchen | c | start cooking it now ("fire table six") | fire it
behind the line | on the line | kitchen | c | the cooking stations in a restaurant kitchen | behind the line

# --- nurses and hospital staff ---
the q word | the q-word | nurse | c | "quiet": say it out loud on shift and it's supposedly about to get terrible, so nobody does | the Q word
frequent flyer | frequent flier, frequent flyers | nurse | c | a patient who comes back to the ER again and again | frequent flyer
npo | | nurse | c | nothing by mouth: no food or drink, usually before a procedure | N P O
prn | | nurse | c | as needed (a medication; or a nurse who picks up shifts as needed) | P R N
stat | | nurse | c | right now, urgently | stat
code brown | | nurse | c | a bowel-movement mess to clean up | code brown
code blue | | nurse | c | a patient whose heart or breathing has stopped: everyone runs | code blue
nocs | noc, noc shift | nurse | c | the night shift | knocks
floated | float pool, got floated | nurse | c | sent to cover another unit for the shift | floated
sundowning | sundowner, sundowns | nurse | c | confusion or agitation that gets worse in the evening, often with dementia | sundowning
charting | | nurse | c | writing up patient notes | charting
bed bath | | nurse | c | washing a patient who can't get up | bed bath
pee and poop report | | nurse | c | the handoff details nobody else wants to hear, but nurses need | pee and poop report
full moon | | nurse | c | the night everyone swears the ER gets wild | full moon

# --- the US military ---
hooah | hoo-ah, huah | military | c | Army for "yes", "got it" or "let's go" | hoo-ah
oorah | ooh-rah, urah, oo-rah | military | c | Marine Corps for "yes" or "let's go" | ooh-rah
hooyah | hoo-yah | military | c | Navy (especially SEALs) for "yes" or "let's go" | hoo-yah
fubar | | military | v | messed up beyond all recognition (the f-word version) | FUBAR
snafu | | military | c | situation normal: all messed up | SNAFU
rack out | racked out, hit the rack | military | c | go to sleep | rack out
pt | p.t. | military | c | physical training | P T
mre | mres | military | c | a packaged field meal (Meal, Ready-to-Eat) | M R E
oscar mike | | military | c | on the move | Oscar Mike
charlie mike | | military | c | continue mission: keep going | Charlie Mike
fobbit | fobbits | military | c | a service member who never leaves the base on deployment (teasing) | fobbit
zero dark thirty | oh dark thirty, o dark thirty, oh-dark-thirty | military | c | very early, before dawn | zero dark thirty
battle buddy | battle buddies | military | c | the partner you look out for, and who looks out for you | battle buddy
geardo | geardos | military | c | someone who buys every piece of gear there is | geardo
high speed | high speed low drag, high-speed | military | c | squared away, really good at the job | high speed
squared away | | military | c | organized, has it together | squared away
voluntold | | military | c | "volunteered" by someone else: told, not asked | voluntold
hurry up and wait | | military | c | rush to be somewhere, then wait around for hours | hurry up and wait
roger | roger that | military | c | understood | roger
wilco | | military | c | will comply: understood, and I'll do it | wilco
copy | copy that | military | c | I heard you, understood | copy

# --- tech and software ---
lgtm | | tech | c | looks good to me (approving a change) | L G T M
ship it | shipping it, shipped it | tech | c | release it, it's good enough | ship it
yak shaving | yak-shaving | tech | c | a chain of side jobs you have to finish before the real one | yak shaving
bikeshedding | bikeshed | tech | c | arguing about small details instead of the hard problem | bikeshedding
dogfooding | dogfood, eating our own dog food | tech | c | using your own product yourself | dogfooding
rubber ducking | rubber duck, rubber duck debugging | tech | c | explaining a bug out loud (even to a toy duck) until you see it | rubber ducking
10x engineer | 10x dev | tech | c | a supposedly ten-times-as-productive programmer (often said sarcastically) | ten-x engineer
works on my machine | wfm, works for me | tech | c | the classic shrug: it worked for me, so it's your setup | works on my machine
tech debt | technical debt | tech | c | shortcuts that will cost time to fix later | tech debt
prod | in prod | tech | c | the live system real users use ("don't test in prod") | prod
standup | stand-up | tech | c | the short daily team check-in | stand-up
hotfix | hot fix | tech | c | an urgent fix pushed straight to the live system | hotfix
spaghetti code | | tech | c | tangled, hard-to-follow code | spaghetti code
greenfield | | tech | c | a brand-new project with no old code to work around | greenfield
legacy code | | tech | c | old code everyone's scared to touch | legacy code
rtfm | | tech | v | read the (f-ing) manual | R T F M
pebkac | | tech | c | problem exists between keyboard and chair: user error | peb-kak
nerd sniped | nerd snipe, nerd-sniped, nerdsniped | tech | c | hooked by a problem so interesting it eats your whole afternoon | nerd sniped
bus factor | | tech | c | how many people would have to vanish before a project is stuck | bus factor
vibe coding | vibe-coding, vibecoding, vibe code | tech | c | building software by prompting an AI and going with the flow | vibe coding
it's not a bug it's a feature | not a bug it's a feature | tech | c | the joking excuse for something that works wrong | it's not a bug, it's a feature

# --- crypto and trading ---
hodl | hodling, hodler | crypto | c | hold on, don't sell | hodl
to the moon | 🚀 | crypto | c | the price is about to shoot way up | to the moon
diamond hands | 💎🙌 | crypto | c | holding through big drops without selling | diamond hands
paper hands | paper-handed | crypto | c | selling at the first sign of a drop | paper hands
rug pull | got rugged, rugpull | crypto | c | the people behind it took the money and vanished | rug pull
ape in | aped in, aping in | crypto | c | buy in big without much research | ape in
bagholder | bag holder, holding the bag, holding bags | crypto | c | stuck holding something that crashed | bagholder
wagmi | | crypto | c | we're all gonna make it | wag-me
ngmi | | crypto | c | not gonna make it | N G M I
fud | | crypto | c | fear, uncertainty and doubt: scary talk meant to make people sell | fud
dyor | | crypto | c | do your own research | D Y O R
whale | whales | crypto | c | someone holding so much they can move the price | whale
stonks | | crypto+internet | c | stocks, said jokingly (from the meme) | stonks
buy the dip | btd, btfd | crypto | c | buy after the price drops | buy the dip
tendies | | crypto | c | chicken tenders; in trading talk, gains (from WallStreetBets) | tendies
pump and dump | pump-and-dump | crypto | c | hype it up, then sell to everyone who bought in | pump and dump
gm | | crypto | c | good morning (the crypto-Twitter hello) | G M

# --- truckers and CB radio ---
10-4 | ten-four, 10 4 | trucker | c | okay, message received | ten-four
what's your 20 | what's your twenty, your 20 | trucker | c | where are you? | what's your twenty
smokey | smokey bear, smokeys | trucker | c | a state trooper, a highway cop | Smokey
chicken coop | chicken coops | trucker | c | a weigh station | chicken coop
hammer down | put the hammer down | trucker | c | drive fast, floor it | hammer down
breaker one-nine | breaker 1-9, breaker breaker | trucker | c | asking for a turn to talk on CB channel 19 | breaker one-nine
deadhead | deadheading | trucker | c | driving with an empty trailer | deadhead
four-wheeler | 4-wheeler, four wheeler | trucker | c | an ordinary car | four-wheeler
reefer | reefers | trucker | c | a refrigerated trailer | reefer

# --- theatre kids ---
break a leg | | theatre | c | good luck (never say "good luck" in a theatre) | break a leg
the scottish play | | theatre | c | Macbeth (saying the name in a theatre is bad luck) | the Scottish play
tech week | hell week | theatre | c | the exhausting week of technical rehearsals before opening | tech week
off book | | theatre | c | has their lines memorized | off book
upstaging | upstage, upstaged | theatre | c | stealing attention from another actor | upstaging
ghost light | | theatre | c | the single lamp left on in an empty theatre overnight | ghost light
jazz hands | | theatre | c | hands spread wide and shaking, for showbiz flair | jazz hands
triple threat | | theatre | c | someone who can act, sing and dance | triple threat
places | places please | theatre | c | everyone to your starting spots, the show is starting | places

# --- the gym ---
gains | gainz | gym | c | muscle you've built | gains
leg day | skipped leg day | gym | c | the day you train legs (the one people famously skip) | leg day
swole | swol | gym | c | very muscular | swole
bulking | on a bulk | gym | c | eating extra on purpose to build muscle | bulking
cutting | on a cut | gym | c | dieting to lose fat while keeping muscle | cutting
spot me | spot me bro | gym | c | stand by and help if I can't finish the lift | spot me
gym rat | gym bro, gym rats | gym | c | someone who basically lives at the gym | gym rat
doms | | gym | c | the muscle soreness a day or two after a workout | DOMS
mirin | mirin' | gym | c | admiring (checking out someone's muscles) | mirin
natty | | gym | c | built without steroids ("is he natty?") | natty
pb | personal best, pr'd | gym | c | your best lift ever | P B
rest day | | gym | c | a planned day off from training | rest day

# --- sports fans ---
ball don't lie | | sports | c | justice was served (a missed free throw right after a bad call) | ball don't lie
and one | and-1, and 1 | sports | c | scored while fouled, with a free throw to come | and one
posterized | poster dunk, put him on a poster | sports | c | dunked on so hard it belongs on a poster | posterized
broke his ankles | ankle breaker, broke her ankles | sports | c | a crossover so quick the defender fell | broke his ankles
garbage time | | sports | c | the end of a blowout, when the result's already decided | garbage time
clutch | | sports | c | coming through in the big moment | clutch
hat trick | hat-trick | sports | c | three goals by one player in a game | hat trick
walk-off | walkoff, walk off | sports | c | a play that wins the game in the last inning | walk-off
bandwagon | bandwagoner, bandwagon fan, on the bandwagon | sports | c | a fan who only shows up when the team's winning | bandwagon
trust the process | | sports | c | stay patient through the rebuild | trust the process
ref ball | | sports | c | a game decided by the referees' calls | ref ball

# --- South Africa ---
lekker | | safrica | c | great, nice, delicious | lekker
howzit | howzit bru | safrica | c | hi, how's it going | howzit
braai | braaing, braaied | safrica | c | a barbecue; to barbecue | brye
eish | | safrica | c | surprise, frustration or sympathy, all in one word | aysh
now now | | safrica | c | soon, in a little while | now now
just now | | safrica | c | at some point later (maybe much later) | just now
robot | robots | safrica | c | a traffic light | robot
bakkie | bakkies | safrica | c | a pickup truck | bucky
shame | ag shame | safrica | c | aww: sympathy or "how sweet", not blame | shame
sharp sharp | | safrica | c | okay, cool; see you | sharp sharp
jol | jolling, a jol | safrica | c | a party; to have a good time | jol
ja nee | ja-nee | safrica | c | yes, no: "well, that's how it is" | yah near
bru | boet | safrica | c | bro, mate | brew
dop | dops | safrica | c | a drink (alcohol) | dop
izit | | safrica | c | really? (said to keep a story going) | izzit
voetsek | voetsak | safrica | v | get lost, go away (rude) | foot-sek
yoh | yho | safrica | c | wow | yoh
kif | kief | safrica | c | cool, awesome | kif

# --- Singapore and Malaysia (Singlish) ---
lah | | singlish | c | a particle that softens or stresses what you say ("okay lah") | lah
leh | | singlish | c | a particle for a gentle ask or a soft complaint | leh
lor | | singlish | c | a particle of shrugging acceptance ("like that lor") | lor
shiok | | singlish | c | amazing, really satisfying (often food) | shee-ok
kiasu | | singlish | c | so afraid of missing out you rush to be first | kee-ah-soo
chope | choped, choping | singlish | c | reserve a seat (often with a tissue packet) | chope
paiseh | pai seh | singlish | c | embarrassed; sorry | pie-seh
can or not | can anot | singlish | c | is that possible? (answer: "can" or "cannot") | can or not
alamak | | singlish | c | oh no! | ah-lah-mak
sian | | singlish | c | bored, fed up, drained | see-an
jialat | | singlish | c | terrible, in a bad way | jee-ah-lat
makan | | singlish | c | eat; food | mah-kan
atas | | singlish | c | fancy, posh | ah-tas
tapau | dabao, da bao, ta pau | singlish | c | takeaway: pack the food to go | tah-pow
bo jio | | singlish | c | you didn't invite me! | bo jee-oh
confirm plus chop | | singlish | c | absolutely, definitely certain | confirm plus chop
kopi | | singlish | c | local coffee | koh-pee

# --- Canada and Toronto ---
ahlie | ahli | canada | c | right? isn't it? (Toronto) | ah-lee
mans | | canada | c | I or me ("mans is tired"), or the guys (Toronto) | mans
the 6ix | 6ix | canada | c | Toronto | the six
double-double | double double | canada | c | a coffee with two creams and two sugars | double-double
toque | tuque | canada | c | a knit winter hat | toohk
loonie | loonies | canada | c | the one-dollar coin | loonie
toonie | twoonie, toonies | canada | c | the two-dollar coin | toonie
eh | | canada | c | right? isn't it? (on the end of a sentence) | eh
give'r | giver, give 'er | canada | c | go all out, give it everything | give 'er
keener | keeners | canada | c | an overly eager person, a try-hard | keener
two-four | 2-4, two four | canada | c | a case of 24 beers | two-four
mickey | | canada | c | a small (375 ml) bottle of liquor | mickey

# --- New Zealand ---
chur | chur bro | aus | c | thanks, cheers, awesome (New Zealand) | chur
sweet as | | aus | c | great, no problem (New Zealand) | sweet as
jandals | jandal | aus | c | flip-flops (New Zealand) | jandals
chilly bin | | aus | c | a cooler (New Zealand) | chilly bin
tu meke | | aus+pasifika | c | too much, awesome (Māori, New Zealand) | too meh-keh
dairy | the dairy | aus | c | a corner shop (New Zealand) | dairy
# --- everyday slang the phrase bank needs (well established) ---
trash | | general | c | bad, worthless ("that movie was trash") | trash
hard | goes hard, go hard | aave | c | really good, intense ("this song hard") | hard
sick | | general | c | awesome, really good | sick
word | word up | nyc+aave | c | true; I agree | word
rah | | uk | c | wow (surprise) | rah
grouse | | aus | c | great, excellent (Australia) | grouse
how ya going | how you going, how are ya going | aus | c | how are you? (Australia) | how ya goin'
too easy | | aus | c | no problem, done (Australia) | too easy
esky | the esky | aus | c | a cooler (Australia) | esky
your man | your one | irish | c | that guy (your one: that woman) | your man
baltic | | scotwales | c | freezing cold | baltic
amped | | socal | c | excited, hyped | amped
yes chef | yes chef! | kitchen | c | understood, on it (answering the chef) | yes chef
degen | degens | crypto+gaming | c | a reckless, high-risk gambler or trader (often said proudly) | degen
merde | | theatre | c | good luck (what dancers say instead of "break a leg") | mared
on book | | theatre | c | still reading lines from the script | on book
holler at me | holler at you, holla at me | south+aave | c | get in touch with me, hit me up | holler at me
na wa | na wa o | africa | c | wow, this is too much (surprise or exasperation, Nigerian Pidgin) | na wa
omo | | africa | c | wow! (surprise, Nigerian) | oh-mo
e choke | | africa | c | it's amazing, overwhelming (Nigerian Pidgin) | eh choke
no wahala | | africa | c | no problem (Nigerian Pidgin) | no wahala
load shedding | | safrica | c | scheduled rolling power cuts (South Africa) | load shedding
astig | | filipino | c | cool, tough, impressive | ah-stig
"""

# Slang in one sense, everyday English in another: understood when asked, but never taken as a sign of someone's circle.
EVERYDAY = frozenset({
    "heard", "behind", "corner", "all day", "on the fly", "the pass", "comp", "slammed", "fire it", "stiffed", "campers", "the rail", "expo",
    "stat", "charting", "full moon", "bed bath", "copy", "roger", "squared away", "high speed", "pt", "prod", "standup", "hotfix", "greenfield",
    "legacy code", "ship it", "whale", "gm", "smokey", "reefer", "deadhead", "places", "upstaging", "gains", "cutting", "bulking", "spot me",
    "rest day", "pb", "clutch", "bandwagon", "and one", "hat trick", "shame", "just now", "now now", "robot", "eh", "mickey", "dairy",
    "toque", "two-four", "dop", "trash", "hard", "sick", "word", "amped",
})
