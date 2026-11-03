"""The phrase bank: over a million ways people in different communities actually talk, each one labeled with the truth.

Every phrase is built from a community's own words (all from Luma's lexicon, with the meaning written there) set into
sentence frames people in that community would really say, about everyday things. Every word is used the way it's
meant: praise words go with things you can enjoy (food that's bussin, a party that was grouse), complaints with
hassles (the commute got me cooked), plans with places you go, and each trade talks about its own work (86 the salmon,
bed four is NPO after midnight). The labels come from Luma's own recognizer reading the finished sentence, with the
lexicon's meanings, so phrase(i) says which community it sounds like, what it's doing (praising, agreeing,
complaining, planning...) and what each slang word in it means. Nothing is guessed, nothing is made up.

It's generated on demand, not stored: phrase(i) for any i below count(), the same every time. Luma uses it three ways:
  - to check itself (tests: every slang word in a phrase is recognized; the community is recognized from how someone talks);
  - as training data for the understanding model and for fine-tuning (scripts/phrase_bank.py writes samples);
  - as each community's safe vocabulary when Luma talks back in someone's register, so it only ever uses real words.

Each pack also carries a few jokes the way people in that circle joke with each other: about shared situations (the
rush at work, the group chat, the weather), never about who someone is.
"""
from __future__ import annotations

import random
import re
from functools import lru_cache

# Everyday things, sorted by what you'd say about them. A slot like {fun2} is another pick from the same list, never the first one again.
SHARED = {
    "food": ["this pizza", "the food here", "my mom's cooking", "the burger", "the tacos", "this cake", "the wings", "the fries",
             "the noodles", "the curry", "the dumplings", "the brunch", "this coffee", "the barbecue", "the pasta", "the ramen",
             "the sushi", "the fried chicken", "the mac and cheese", "the smoothie", "the breakfast burrito", "the pho",
             "the empanadas", "the birthday cake", "the jerk chicken", "the biryani", "the tamales", "the bao", "the brisket", "the lasagna",
             "the waffles", "the chicken rice", "the pancakes", "the street corn"],
    "fun": ["the party last night", "my new shoes", "that movie", "the new album", "this playlist", "my haircut", "the game last night",
            "this song", "that show", "the concert", "my outfit", "the wedding", "the new phone", "the trip", "the hotel", "that trailer",
            "the finale", "this hoodie", "the new episode", "the halftime show", "the fit", "the season opener", "the road trip",
            "the after party", "the new spot downtown", "the cookout", "the reunion", "the open mic", "the club", "the festival",
            "the mixtape", "the beat", "the dance video", "the meme", "the livestream", "the new skin", "the tournament", "my sneakers",
            "the jacket", "my braids", "the new tattoo", "the date", "the new couch", "the apartment", "the beach", "my weekend",
            "the family dinner", "the holidays", "the graduation", "the karaoke night", "the museum", "the art show", "the comedy show",
            "the documentary", "the drag show", "the parade", "the fireworks", "the theme park", "the water park", "the camping trip",
            "the bonfire", "the pool party", "the block party", "the street fair", "the car show", "the vacation", "the cruise",
            "the photoshoot", "my nails", "the music video", "the new restaurant", "the rooftop bar", "the house party", "prom",
            "homecoming", "the talent show"],
    "hassle": ["this weather", "my job", "this traffic", "the drive home", "the meeting", "my sleep schedule", "the line at the store",
               "the commute", "the bus", "the train", "the flight", "the airport", "my phone bill", "the wifi", "this heat", "the rain",
               "the snow", "the interview", "the shift", "the exam", "my rent", "this class", "the move", "my first day", "the new job",
               "the group project", "the parking", "the dentist", "laundry day", "the security line", "the delay", "the queue",
               "the paperwork", "taxes", "the electric bill", "my inbox", "the alarm this morning", "the construction outside",
               "the printer", "the self-checkout", "jury duty", "the landlord's email", "the gas prices", "the heat wave", "the dishes"],
    "event": ["the party", "the game", "the concert", "the wedding", "the cookout", "the gym", "the beach", "the movies", "the festival",
              "the open mic", "the club", "the barbecue", "the reunion", "the graduation", "the family dinner", "the brunch", "work",
              "class", "the mall", "practice", "the barber", "the nail appointment", "the car wash", "my cousin's birthday",
              "the after party", "the game tonight", "the show", "the meetup", "the baby shower", "the road trip", "the museum", "the parade",
              "the pool party", "the block party", "the bonfire", "the art show", "the comedy show", "the theme park", "the rooftop bar",
              "the house party", "prom", "homecoming", "the talent show", "the farmers market", "the fair"],
}
PLURAL = {"the tacos", "the wings", "the fries", "the noodles", "the dumplings", "the empanadas", "my new shoes", "my sneakers", "my braids",
          "the holidays", "the refs", "my nails", "the fireworks", "taxes", "the gas prices", "the dishes", "the tamales",
          "the waffles", "the pancakes"}

# community -> {roles, frames, bits, topics}. Every role word is in Luma's lexicon (tests check), so its meaning is known.
# "topics" are a trade's own everyday things (dishes, beds, deploys); they carry no slang and aren't labeled.
PACKS = {
    "aave": {
        "roles": {"good": ["fire", "fye", "hard", "valid", "a vibe"], "yum": ["bussin", "fire", "fye"], "bad": ["mid", "trash", "corny", "goofy ahh"],
                  "friend": ["bro", "fam", "dawg", "homie", "my G", "twin", "bruh"], "truth": ["no cap", "fr", "on God", "deadass", "on my mama"],
                  "ok": ["bet", "say less"], "about": ["finna", "boutta", "tryna"],
                  "tired": ["cooked", "so cooked"], "money": ["bands", "bread", "guap", "a bag"], "laugh": ["I'm weak", "I'm dead", "LMAO"]},
        "frames": [("{fun} was {good} {truth}", "praise"), ("{food} was {yum} {truth}", "praise"), ("{friend} {fun} is {bad} {truth}", "complain"),
                   ("{ok} {friend}, I'm {about} pull up to {event}", "agree"), ("{hassle} got me {tired} {truth}", "complain"),
                   ("{laugh} {friend}, {fun} was {good}", "laugh"), ("I'm {about} get {money} {truth}", "plan"),
                   ("{friend} you seen {fun}? it's {bad}", "ask"), ("facts, {food} {truth} {yum}", "agree"),
                   ("ion even care, {fun} was {good} {friend}", "praise"), ("{hassle}?? {bad} {truth}, I'm {tired}", "complain"),
                   ("{fun} was {good} but {fun2} was {bad} {truth}", "compare"), ("{friend}, skip {event}, {event2} gonna be {good}", "advise"),
                   ("{food} at {event}? {yum} {truth}", "praise")],
        "bits": ["Group chat got 47 messages and not one of them answered my question. Y'all just be talking.",
                 "Said I'd leave the cookout at nine. It's midnight and I'm holding a plate for the road. That's tradition.",
                 "Auntie asked who I'm dating in front of everybody. Ma'am, I came for the mac and cheese."]},
    "internet": {
        "roles": {"good": ["lowkey iconic", "a vibe", "giving main character"], "bad": ["mid", "cringe", "giving nothing", "so cheugy"],
                  "truth": ["fr", "ngl", "istg", "no because", "be so fr", "icl"], "delulu": ["delulu", "so delulu"], "focus": ["locked in", "so locked in"],
                  "agree": ["same", "mood", "facts"], "laugh": ["I'm screaming", "I'm crying", "LMAO", "dead"], "doom": ["it's so over", "we're so back"]},
        "frames": [("{fun} is {good} {truth}", "praise"), ("{truth} {fun} was {bad}", "complain"), ("{fun} living in my head rent free", "feel"),
                   ("{laugh} {fun} is {good}", "laugh"), ("I'm {delulu} about {fun} {truth}", "feel"), ("{hassle}? {doom} {truth}", "feel"),
                   ("{hassle} being like this? {agree}", "agree"), ("pov: {hassle} is {bad} {truth}", "complain"), ("not {fun} being {good}", "praise"),
                   ("{fun} is {good} but {fun2}? {bad} {truth}", "compare"), ("{fun} and {fun2} living in my head rent free", "feel"),
                   ("I'm {focus} for {event} {truth}", "feel"), ("{fun} is a canon event {truth}", "feel")],
        "bits": ["Opened my phone to check the time. Forty minutes later I know everything about a stranger's kitchen renovation. Still don't know the time.",
                 "My screen time report came in and I'm choosing not to see it. Healing era.",
                 "Typed a whole paragraph, deleted it, sent 'lol'. Communication."]},
    "alpha": {
        "roles": {"good": ["sigma", "plus aura", "plus a thousand aura"], "bad": ["so Ohio", "minus aura", "minus a thousand aura", "skibidi"],
                  "act": ["aura farming", "mewing", "mogging"], "tag": ["fr", "fr fr", "no cap"]},
        "frames": [("{fun} is {good} {tag}", "praise"), ("{fun} is {bad} {tag}", "complain"), ("bro is {act} at {event}", "tease"),
                   ("chat, {hassle} is {bad}", "complain"), ("chat is this real? {fun} is {good}", "praise"),
                   ("{fun} is {good} but {fun2} is {bad}", "compare"), ("{fun} is pure brainrot {tag}", "laugh")],
        "bits": ["Asked my little cousin what 6-7 means. He said 'you wouldn't get it'. He's nine. He's right.",
                 "Minus a thousand aura for tripping on the stairs. Plus five hundred for pretending I meant to."]},
    "uk": {
        "roles": {"good": ["peng", "leng", "nang", "calm"], "nah": ["peak", "moist", "butters"], "drag": ["long", "peak"],
                  "friend": ["bruv", "fam", "blud", "my g", "bossman", "bredrin"], "tag": ["innit", "fam"],
                  "ok": ["safe", "say no more", "calm"], "wow": ["oh my days", "rah"], "mood": ["gassed", "buzzin", "gutted"], "state": ["knackered", "skint"]},
        "frames": [("{fun} was {good} {tag}", "praise"), ("{wow}, {fun} is {nah} {friend}", "complain"), ("allow it {friend}, {hassle} is {drag}", "complain"),
                   ("{ok} {friend}, see you at {event}", "agree"), ("I'm {mood} about {fun} {tag}", "feel"), ("{friend}, {hassle}? {drag} {tag}", "complain"),
                   ("wagwan {friend}, you seen {fun}?", "ask"), ("{fun} was {good}, bare true", "praise"), ("{wow} {friend}, I'm {state} after {hassle}", "feel"),
                   ("{fun} was {good} but {fun2} was {nah} {tag}", "compare"), ("{friend}, forget {event}, {event2} is gonna be {good}", "advise")],
        "bits": ["Asked how they're doing. 'Not bad.' Asked how the funeral went. 'Not bad.' Asked about the promotion. 'Can't complain.' Same energy every time.",
                 "Forecast said sunny spells. Got all four seasons before lunch and a bus that didn't stop.",
                 "Put the kettle on as a reflex. Didn't want tea. Made tea. Drank the tea."]},
    "aus": {
        "roles": {"good": ["sweet as", "heaps good", "grouse"], "greet": ["g'day", "how ya going"], "friend": ["mate", "bro"],
                  "ok": ["no worries", "too easy", "yeah nah, all good"], "time": ["this arvo", "tomorrow arvo", "Sunday arvo"],
                  "thing": ["thongs", "the ute", "the esky", "jandals", "the chilly bin"]},
        "frames": [("{greet} {friend}, {fun} was {good}", "praise"), ("{ok} {friend}, see ya {time}", "agree"),
                   ("grab {thing} {friend}, we're off to {event} {time}", "plan"), ("{fun}? {good} {friend}", "praise"), ("{greet}, bring {thing} {time}", "plan"),
                   ("{ok}, {hassle} sorted {time}", "agree"), ("{fun} was {good}, {fun2} not so much {friend}", "compare"),
                   ("chur {friend}, {food} was {good}", "thanks"), ("stoked for {event} {time}, {friend}", "feel")],
        "bits": ["Magpie season. I don't walk to work anymore, I sprint with an ice cream container on my head. Dignity is for winter.",
                 "It's 38 degrees and Dave's still in a hoodie. Dave is either a legend or a lizard."]},
    "south": {
        "roles": {"about": ["fixin' to", "fixing to", "finna"], "you": ["y'all", "all y'all"], "dear": ["sugar", "hon", "y'all"],
                  "wow": ["bless your heart", "dadgum"], "agree": ["I reckon", "yes ma'am", "you bet"], "place": ["over yonder", "down yonder"]},
        "frames": [("{dear}, I'm {about} head {place}", "plan"), ("{wow}, {you} missed {event}", "tease"), ("{agree}, {fun} was something else", "agree"),
                   ("{you} coming to {event}? I'm {about} leave", "ask"), ("holler at me after {event}, {dear}", "plan"),
                   ("I might could make {event}, {dear}", "plan"), ("{you} staying for supper after {event}?", "ask"),
                   ("{dear}, I'm {about} skip {event} for {event2}", "plan")],
        "bits": ["We said goodbye at the door, again at the porch, and once more at the car. Forty-five minutes. Southern goodbyes have three acts.",
                 "Sweet tea so sweet the dentist sends a Christmas card."]},
    "nyc": {
        "roles": {"truth": ["deadass", "word"], "friend": ["B", "son", "fam", "bro"], "good": ["fire", "mad good", "hard"],
                  "bad": ["trash", "mad corny", "wack"], "greet": ["yerr", "yerrr"]},
        "frames": [("{greet} {friend}, {fun} was {good} {truth}", "praise"), ("{truth} {hassle} is {bad} {friend}", "complain"),
                   ("{greet}, you hitting the bodega before {event}?", "ask"), ("{food} {good} {friend}, {truth}", "praise"),
                   ("{fun} {good} but {fun2} {bad} {truth}", "compare")],
        "bits": ["Train's delayed 'due to train traffic ahead'. The train ahead is also stuck behind train traffic. It's trains all the way down.",
                 "Bodega cat looked at me like I owed it money. I bought a sandwich I didn't want. Respect."]},
    "gaming": {
        "topics": {"play": ["the ranked match", "the boss fight", "the raid", "the tournament", "the new patch", "the new map", "the final round",
                            "the new season", "the battle pass", "the co-op mission", "the scrim", "the last game"]},
        "roles": {"good": ["cracked", "goated", "OP", "pog"], "bad": ["mid", "trash", "a skill issue"], "worse": ["throwing", "inting", "trash", "mid"],
                  "agree": ["gg", "facts", "run it back", "W"], "act": ["carry", "grind", "speedrun", "tryhard"], "feel": ["tilted", "salty", "locked in"],
                  "friend": ["bro", "squad"], "who": ["bro", "the squad", "my squad"]},
        "frames": [("{play} was {good}, {agree}", "praise"), ("{who} is {worse} on {play}", "tease"), ("I'm {feel} after {play}", "feel"),
                   ("{agree} {friend}, {play} was {good}", "agree"), ("gonna {act} {play} tonight", "plan"), ("{play}? {bad} ngl", "complain"),
                   ("lowkey {feel}, {play} was {bad}", "complain"), ("{play} was {good} but {play2} was {bad}", "compare")],
        "bits": ["'One more game.' Narrator: it was not one more game. The sun came up.",
                 "Lost to a level 3 named xXDestroyerXx. He was eight. I'm uninstalling. I'm reinstalling."]},
    "stan": {
        "topics": {"drop": ["the comeback", "the new album", "the MV", "the tour", "the concert", "the stage", "the fancam", "the photoshoot",
                            "the teaser", "the encore", "the live", "the dance practice"]},
        "roles": {"good": ["serving", "mother", "so mother"], "feel": ["delulu", "so delulu"], "act": ["stan", "fully stan"], "agree": ["periodt", "facts"]},
        "frames": [("{drop} is {good} {agree}", "praise"), ("{drop}? I {act}", "feel"), ("I'm {feel} about {drop}", "feel"),
                   ("{drop} was {good}, {agree}", "praise"), ("{drop} was {good} and {drop2} too, {agree}", "praise"), ("{drop} ate, {agree}", "praise")],
        "bits": ["My bank account during comeback season: 'are you okay?' No. Stream the MV.",
                 "Set an alarm for ticket sales, a backup alarm, and a backup backup. Still in queue position 48,000."]},
    "ballroom": {
        "topics": {"look": ["the look", "the walk", "the runway", "the outfit", "the face", "the vogue", "the dip", "the final battle", "the entrance", "the makeup"]},
        "roles": {"good": ["serving", "sickening", "giving", "snatched"], "agree": ["yas", "periodt", "purr", "werk"], "act": ["ate", "slayed"]},
        "frames": [("{look} was {good}, {agree}", "praise"), ("you {act} {look}, {agree}", "praise"), ("{agree}, {look} is {good}", "agree"),
                   ("you {act} {look} and {look2}, {agree}", "praise"), ("clock it, {look} is {good}", "praise"), ("no shade, but {look} was mid", "tease"),
                   ("{look} was {good}, to the house down boots", "praise")],
        "bits": ["I didn't walk into the room, I walked the category. The category was 'running late but make it couture'.",
                 "No shade, but that outfit has lore. And the lore is from 2014."]},
    "jam": {
        "roles": {"greet": ["wagwan", "wah gwaan"], "friend": ["bredda", "bredrin", "yute"], "good": ["irie", "nuff vibes"], "ok": ["big up", "bless up"]},
        "frames": [("{greet} {friend}, {fun} was {good}", "praise"), ("{ok} {friend}", "agree"), ("{greet}, you reach {event} yet?", "ask"),
                   ("save me a likkle bit of {food}, {friend}", "ask"), ("{fun} {good}, {ok}", "praise"), ("{fun} {good}, {fun2} too {friend}", "praise"),
                   ("soon come {friend}, after {event}", "plan")],
        "bits": ["'Soon come' means anywhere from five minutes to next Tuesday. Plan accordingly.",
                 "Rice and peas on Sunday is not food, it's a family meeting with gravy."]},
    "mexican": {
        "roles": {"wow": ["no manches", "órale"], "ugh": ["chale", "híjole"], "friend": ["güey", "carnal", "vato", "mija"],
                  "good": ["chido", "padre", "firme", "bien chido"], "bad": ["gacho", "chafa"], "truth": ["neta", "simón"], "time": ["ahorita", "ahorita mismo"]},
        "frames": [("{wow} {friend}, {fun} was {good}", "praise"), ("{truth}, {hassle} is {bad} {friend}", "complain"), ("{time} vamos to {event}, {friend}", "plan"),
                   ("{wow}, {food} {good} {truth}", "praise"), ("{ugh} {friend}, {hassle}? {bad}", "complain"), ("{wow}, {fun} was {good} but {fun2} {bad}", "compare")],
        "bits": ["'Ahorita' could mean now, in an hour, or never. Mom said 'ahorita' in 2019. Still waiting.",
                 "There's a butter cookie tin in the kitchen. There have never been cookies in it. Only sewing stuff and hope."]},
    "latino": {
        "roles": {"friend": ["mija", "wey"], "good": ["pura vida", "bien chido"], "gossip": ["chisme", "the chisme"]},
        "frames": [("ay Dios mío, {hassle}!", "complain"), ("vamos a janguear after {event}, {friend}", "plan"), ("{friend}, spill {gossip} about {event}", "ask"),
                   ("{fun}? {good}, {friend}", "praise"), ("{friend}, after {event} vamos a janguear at {event2}", "plan"),
                   ("ándale {friend}, we're late for {event}", "plan"), ("qué onda {friend}, how was {fun}?", "ask"),
                   ("I'll textear you after {event}, {friend}", "plan"), ("couldn't parquear near {event}, {friend}", "complain")],
        "bits": ["The chisme travels faster than the group chat. Tía knew before it happened.",
                 "'Five minutes' in family time is a unit of measure, not a duration."]},
    "desi": {
        "roles": {"friend": ["yaar", "bhai", "didi"], "good": ["mast", "paisa vasool", "ekdum mast"], "arre": ["arre", "arre yaar"],
                  "bad": ["bakwaas", "total bakwaas"], "fix": ["jugaad", "full jugaad"]},
        "frames": [("kya baat hai, {fun} was {good}", "praise"), ("{friend}, {fun} was {bad}", "complain"), ("did some {fix} on {hassle}, {friend}", "plan"),
                   ("{fun}? {good} {friend}", "praise"), ("arre {friend}, {fun} was just timepass", "feel"), ("{arre}, {hassle} is {bad}", "complain"),
                   ("{fun} was {good} but {fun2} {bad}", "compare")],
        "bits": ["Fixed the remote with a rubber band and a prayer. Jugaad is an engineering degree nobody gives you.",
                 "Told mom I ate. She heard 'please bring me four more rotis'."]},
    "filipino": {
        "topics": {"crush": ["the date", "his text", "her message", "the love song", "the proposal video", "the wedding", "the first dance"],
                   "cute": ["the baby", "the puppy", "my niece", "the kitten", "my nephew", "the toddler next door"]},
        "roles": {"friend": ["bes", "kuya", "tita", "tito"], "wow": ["nako", "susmaryosep"], "go": ["tara", "sige"], "good": ["petmalu", "astig"]},
        "frames": [("{wow} {friend}, {hassle}!", "complain"), ("I'm so kilig about {crush}, {friend}", "feel"), ("{go} {friend}, {event} na", "plan"),
                   ("{fun} is {good}, {friend}", "praise"), ("{fun}? sana all", "feel"), ("{cute} makes me so gigil, {friend}", "feel"),
                   ("{go} {friend}, {event} then {event2}", "plan"), ("{fun} was {good}, charot", "tease")],
        "bits": ["Went home for the holidays and came back with three pasalubong boxes and four new titas I'm apparently related to.",
                 "The rice cooker is the most loved appliance in the house and nobody can tell me otherwise."]},
    "africa": {
        "roles": {"wow": ["omo", "eish"], "friend": ["oga", "charley"], "talk": ["gist", "the gist"]},
        "frames": [("{wow}, {hassle} na wa", "complain"), ("{friend}, give me {talk} on {event}", "ask"), ("I go chop after {event}, {friend}", "plan"),
                   ("{fun} e choke, {friend}", "praise"), ("{wow} {friend}, {event} don start", "feel"), ("no wahala {friend}, see you at {event}", "agree"),
                   ("abeg {friend}, where {food}?", "ask")],
        "bits": ["NEPA took the light right before the penalty kick. The whole street screamed in one voice. Community.",
                 "Owambe dress code: wear the aso ebi or explain yourself to every aunty in the hall."]},
    "safrica": {
        "roles": {"friend": ["bru", "boet"], "good": ["lekker", "kif"], "wow": ["eish", "yoh"], "time": ["now now", "just now"]},
        "frames": [("howzit {friend}, {fun} was {good}", "praise"), ("{wow}, {hassle} hey", "complain"), ("I'll come {time}, {friend}", "plan"),
                   ("{food}? {good}, {friend}", "praise"), ("{wow} {friend}, load shedding during {event}", "complain"),
                   ("{fun} was {good} but {hassle}, {wow}", "compare"), ("sharp sharp {friend}, see you at {event}", "agree"), ("ja nee {friend}, {hassle} hey", "agree")],
        "bits": ["'I'll do it now now' means soon. 'Just now' means later. 'Now' means maybe. Time is a vibe.",
                 "Load shedding schedule says 18:00. Braai starts at 17:59. Planning."]},
    "singlish": {
        "roles": {"good": ["shiok", "damn shiok"], "bad": ["jialat", "sian"], "wow": ["alamak", "alamak sia"], "act": ["chope", "tapau", "makan"]},
        "frames": [("{food} {good} lah", "praise"), ("{wow}, {hassle} so {bad} lor", "complain"), ("{act} first leh, then {event}", "plan"),
                   ("{event} can or not?", "ask"), ("{food} {good}, but {hassle} {bad} lor", "compare")],
        "bits": ["Left a tissue packet on the table to chope my seat. Came back and an auntie had choped it harder with an umbrella. Respect.",
                 "Hawker centre at lunch: twelve queues, one decision, zero regrets."]},
    "canada": {
        "roles": {"tag": ["eh", "ahlie"], "thing": ["a double-double", "my toque", "a two-four", "a toonie"], "go": ["give'r", "send it"]},
        "frames": [("{fun} was good {tag}", "praise"), ("grab {thing} before {event}, fam", "plan"), ("gonna {go} at {event} {tag}", "plan"),
                   ("mans is tired from {hassle} {tag}", "feel"), ("{event} then {event2}, {go}", "plan")],
        "bits": ["Said sorry to a door I bumped into. The door didn't say it back. Rude, eh.",
                 "It's minus thirty and someone's in shorts at Tim's. Canadian winter is a personality test."]},
    "irish": {
        "topics": {"broke": ["the car", "the telly", "the kettle", "the washing machine", "my phone", "the boiler"]},
        "roles": {"good": ["deadly", "grand"], "craic": ["good craic", "mighty craic", "great craic"], "bad": ["banjaxed", "fully banjaxed"], "who": ["that eejit", "your man"]},
        "frames": [("{fun} was {good}", "praise"), ("{event} was {craic}", "praise"), ("{broke} is {bad} after {event}", "complain"), ("{who} missed {event}", "tease"),
                   ("{fun} was {good} but {broke} is {bad}", "compare")],
        "bits": ["'Grand' covers everything from 'fantastic' to 'my house is on fire'. Context is everything.",
                 "Rained four times on the way to the shop. Bought ice cream anyway. Summer."]},
    "scotwales": {
        "roles": {"lil": ["wee", "wee quick"], "bad": ["dreich", "baltic"], "good": ["braw", "lush"], "who": ["numpty", "bairn"]},
        "frames": [("{fun} was {good}", "praise"), ("it's {bad} out, {event} is off", "complain"), ("just a {lil} blether about {event}", "plan"),
                   ("some {who} ruined {fun}", "complain"), ("{fun} was {good} but the weather was {bad}", "compare"), ("{food} was {good}", "praise")],
        "bits": ["Summer arrived on a Tuesday. It left on the Tuesday.", "It's dreich. It's always dreich. Dreich is the weather and the mood."]},
    "socal": {
        "roles": {"friend": ["dude", "brah", "bro"], "good": ["gnarly", "rad", "sick"], "feel": ["stoked", "amped"]},
        "frames": [("{friend}, {fun} was {good}", "praise"), ("so {feel} for {event}, {friend}", "feel"), ("{fun}? {good}, {friend}", "praise"),
                   ("{fun} was {good}, {fun2} even more {friend}", "praise"), ("{hassle} was gnarly, {friend}", "complain")],
        "bits": ["The 405 was a parking lot, so we just had the beach day in the car.", "Paddled out for two hours, caught one wave, told everyone it was epic."]},
    "hawaii": {
        "roles": {"friend": ["brah", "my brah"]},
        "frames": [("{friend}, {food} was ono", "praise"), ("let's talk story after {event}, {friend}", "plan"), ("shoots {friend}, see you at {event}", "agree"),
                   ("pau hana after {hassle}, {friend}?", "plan"), ("{fun} was mo' bettah than {fun2}, {friend}", "compare")],
        "bits": ["'Da kine' can mean anything. Ask for da kine and grandma hands you exactly the right thing. Every time.",
                 "Party started at six. We showed up at seven. We were the first ones there. Island time."]},
    "kitchen": {
        "topics": {"dish": ["salmon", "short rib", "halibut", "risotto", "burger", "scallops", "chicken", "steak", "pasta", "soup", "crab cake", "special"],
                   "station": ["the grill", "the fryer", "sauté", "the flat top", "the line", "the dish pit"],
                   "table": ["table six", "table twelve", "the patio", "the bar", "the booth", "table four"], "count": ["two", "three", "four", "five", "six"]},
        "roles": {"busy": ["in the weeds", "slammed", "weeded"], "agree": ["heard", "heard chef", "yes chef"], "party": ["a deuce", "a four-top"],
                  "move": ["behind", "corner", "hot behind"]},
        "frames": [("we're {busy} on {station}", "complain"), ("86 {dish}, we're out", "call"), ("{station} is {busy}, need a hand", "complain"),
                   ("{agree}, {count} {dish} all day", "agree"), ("just got sat with {party} on {table}", "complain"), ("{table} turned into campers", "complain"),
                   ("{move}! coming through {station}", "warn"), ("{agree}, {dish} for {table} is up", "agree"),
                   ("{count} {dish} and {count2} {dish2} all day, {agree}", "call")],
        "bits": ["Got sat with a twelve-top at 9:58. Two minutes to close. The universe has jokes and none of them tip.",
                 "Family meal was cereal. Chef calls it 'deconstructed granola'. We call it Tuesday."]},
    "nurse": {
        "topics": {"unit": ["the floor", "the ER", "the unit", "night shift", "the ICU", "peds"],
                   "room": ["bed four", "room nine", "bed twelve", "the hallway bed", "room two", "bed seven"],
                   "patient": ["bed four", "room nine", "my patient in twelve", "the new admit", "the post-op in six", "bed seven"]},
        "roles": {"busy": ["slammed", "so slammed"], "who": ["a frequent flyer", "my sundowner", "our frequent flyer"]},
        "frames": [("don't say the Q word, {unit} is {busy}", "warn"), ("got {who} in {room}", "complain"), ("{unit} is {busy}, full moon energy", "complain"),
                   ("{patient} is NPO after midnight", "call"), ("{patient} needs labs stat", "call"), ("{patient} gets Tylenol PRN", "call"),
                   ("{unit} is {busy} and I got {who} in {room}", "complain"), ("still charting on {patient} and {patient2}", "complain")],
        "bits": ["Someone said the Q word at 0300. By 0310 we had two admits, a code brown and a full moon. Never again.",
                 "Twelve-hour shift, fourteen hours long, and I peed once. Hydration is for day shift."]},
    "military": {
        "topics": {"duty": ["the field op", "the inspection", "PT", "the range", "formation", "the convoy", "the brief", "the ruck march",
                            "the promotion board", "chow", "the duty roster", "the weekend pass"]},
        "roles": {"yes": ["hooah", "oorah", "roger", "wilco", "copy"], "time": ["zero dark thirty", "oh dark thirty"], "state": ["squared away", "FUBAR"],
                  "act": ["Charlie Mike", "Oscar Mike"]},
        "frames": [("{yes}, {duty} at {time}", "agree"), ("{duty} is {state}", "feel"), ("we're {act} after {duty}", "plan"), ("{duty}? {yes}", "agree"),
                   ("{duty} then {duty2} at {time}, {yes}", "agree"), ("{duty} was hurry up and wait", "complain")],
        "bits": ["Showed up at 0500 for a 0700 formation. Stood around till 0900. Hurry up and wait is a lifestyle.",
                 "Got voluntold for the weekend detail. My volunteering spirit is overwhelming."]},
    "tech": {
        "topics": {"work": ["the deploy", "the migration", "the sprint", "the demo", "this ticket", "the build", "the code review", "the API",
                            "the release", "the refactor", "the test suite", "the launch", "the config change", "the new framework"]},
        "roles": {"pain": ["tech debt", "spaghetti code", "yak shaving", "bikeshedding"], "joke": ["works on my machine", "it's not a bug it's a feature"],
                  "where": ["in prod", "straight to prod"], "ok": ["LGTM", "ship it"]},
        "frames": [("{work}? {ok}", "agree"), ("{work} is pure {pain}", "complain"), ("{joke}, but {work} went down {where}", "complain"),
                   ("who pushed {work} {where}", "complain"), ("{work} took down {work2} {where}", "complain"), ("LGTM on {work}, but {work2} is {pain}", "agree")],
        "bits": ["'Quick sync' is a 45-minute meeting with no agenda and a follow-up meeting.",
                 "Spent four hours automating a task that takes three minutes. I'll break even in 2031."]},
    "crypto": {
        "topics": {"coin": ["this coin", "the new token", "my portfolio", "the airdrop", "the presale", "the market", "the rally", "the chart", "the memecoin", "the altcoin"]},
        "roles": {"hold": ["HODL", "diamond hands"], "rug": ["a rug pull", "a total rug pull"], "who": ["a bagholder", "a degen"]},
        "frames": [("{coin}? {hold}", "agree"), ("{coin} was {rug}", "complain"), ("{coin} is going to the moon", "feel"), ("{coin} dumped, NGMI", "feel"),
                   ("{coin} pumped, WAGMI", "feel"), ("I'm {who} on {coin}", "complain"), ("that's just FUD about {coin}", "warn"),
                   ("sold {coin} with paper hands", "complain"), ("{coin} dumped but {coin2}? {hold}", "feel"), ("{coin} is down, buy the dip", "advise")],
        "bits": ["Bought the dip. It kept dipping. I'm now the proud owner of the dip.",
                 "My portfolio is a rollercoaster with no seatbelts and no exit."]},
    "trucker": {
        "topics": {"road": ["the I-40 run", "the fuel stop", "the mountain pass", "the rest area", "the on-ramp", "the bridge", "the truck stop", "the Dallas loop"],
                   "spot": ["mile marker 90", "exit 12", "the state line", "the county line", "mile 140", "the Dallas exit"]},
        "roles": {"yes": ["10-4", "10-4 good buddy"], "cop": ["Smokey", "a smokey bear"], "drive": ["hammer down", "deadheading"]},
        "frames": [("{yes}, {road} is clear", "agree"), ("watch for {cop} past {road}", "warn"), ("{cop} sitting at {spot}", "warn"),
                   ("the chicken coop is open at {spot}", "warn"), ("{drive} after {road}", "plan"), ("{road} then {road2}, {yes}", "agree")],
        "bits": ["Eleven hours of driving, two hours looking for parking, and the only open spot is next to the reefer that hums all night.",
                 "GPS said turn left. The low bridge said no. The low bridge always wins."]},
    "theatre": {
        "topics": {"show": ["the show", "the audition", "the callback", "opening night", "dress rehearsal", "the solo", "the matinee", "closing night",
                            "the spring musical", "the cabaret"]},
        "roles": {"luck": ["break a leg", "merde"], "state": ["off book", "on book"], "week": ["tech week", "hell week"]},
        "frames": [("{luck} at {show}!", "wish"), ("I'm {state} for {show}", "feel"), ("{week} for {show} is killing me", "complain"),
                   ("{luck} at {show} and {show2}!", "wish"), ("places for {show} in five", "call")],
        "bits": ["Tech week: I have seen the ghost light more than my family.", "Someone said 'Macbeth' in the green room and the fog machine quit. Coincidence? No."]},
    "gym": {
        "topics": {"lift": ["bench", "squat", "deadlift", "overhead press", "pull-ups", "rows", "hip thrusts", "curls"],
                   "equip": ["the squat rack", "the bench", "the cable machine", "the leg press", "the dumbbells", "the treadmill"]},
        "roles": {"day": ["leg day", "rest day"], "who": ["a gym rat", "a gym bro"]},
        "frames": [("hit a PB on {lift}", "praise"), ("skipping {lift}, it's {day}", "plan"), ("I'm cutting, so {food} is off", "feel"),
                   ("I'm bulking, pass {food}", "feel"), ("{who} took {equip}", "complain"), ("{lift} then {lift2}, gains", "plan"), ("getting swole off {lift}", "feel")],
        "bits": ["Skipped leg day once. The stairs remember.", "Bought a gallon water jug. I now carry it everywhere like a personality."]},
    "sports": {
        "topics": {"game": ["the game", "the fourth quarter", "the second half", "overtime", "the derby", "game seven", "the finals", "the opener",
                            "the rivalry game", "the playoff game"],
                   "deal": ["the trade", "the draft", "the rebuild", "the new coach", "the rookie"]},
        "roles": {"bad": ["ref ball", "garbage time"], "play": ["posterized him", "broke his ankles"]},
        "frames": [("{game} was clutch", "praise"), ("{game} was {bad}", "complain"), ("he {play} in {game}", "praise"), ("{deal}? trust the process", "advise"),
                   ("everyone's on the bandwagon after {game}", "tease"), ("{game} was clutch but {game2} was {bad}", "compare")],
        "bits": ["My team lost in the last second again. I'm done. See you next game.", "The ref missed a call so bad the ball refused to go in. Ball don't lie."]},
}


def _frame_parts(frame):
    return re.findall(r"\{(\w+)\}", frame)


def _base(community, slot):
    """'fun2' -> 'fun' when that's a list of things: the second pick from the same list."""
    if slot.endswith("2") and _is_topic(community, slot[:-1]):
        return slot[:-1]
    return None


def _is_topic(community, slot):
    return slot in SHARED or slot in (PACKS[community].get("topics") or {}) or bool(_base(community, slot))


def _choices(community, slot):
    base = _base(community, slot) or slot
    topics = PACKS[community].get("topics") or {}
    if base in topics:
        return topics[base]
    if base in SHARED:
        return SHARED[base]
    return PACKS[community]["roles"][base]


def _size(community, slot):
    n = len(_choices(community, slot))
    return n - 1 if _base(community, slot) else n  # the second pick is never the first one again


@lru_cache(maxsize=1)
def _table():
    """[(community, frame, intent, slots, sizes, start, count)] and the running total, for picking phrase i quickly."""
    rows, total = [], 0
    for community, pack in PACKS.items():
        for frame, intent in pack["frames"]:
            slots = _frame_parts(frame)
            sizes = [_size(community, s) for s in slots]
            count = 1
            for n in sizes:
                count *= n
            rows.append((community, frame, intent, slots, sizes, total, count))
            total += count
    return rows, total


def count():
    """How many distinct phrases there are."""
    return _table()[1]


def phrase(i):
    """Phrase number i: {"text", "community", "intent", "terms": [(term as said, meaning, communities)]}. The same i, the same phrase."""
    from luma.agent import slang
    rows, total = _table()
    if not 0 <= i < total:
        raise IndexError(i)
    lo, hi = 0, len(rows) - 1
    while lo < hi:  # the frame this index falls in
        mid = (lo + hi + 1) // 2
        if rows[mid][5] <= i:
            lo = mid
        else:
            hi = mid - 1
    community, frame, intent, slots, sizes, start, _ = rows[lo]
    k = i - start
    index = {}
    for slot, n in zip(reversed(slots), reversed(sizes)):
        index[slot] = k % n
        k //= n
    picked = {}
    for slot in slots:
        options = _choices(community, slot)
        base = _base(community, slot)
        picked[slot] = options[(index[base] + 1 + index[slot]) % len(options)] if base else options[index[slot]]
    text = frame
    for slot in slots:
        if picked[slot] in PLURAL:  # "the fries were fire", not "was"
            text = text.replace("{" + slot + "} is ", "{" + slot + "} are ").replace("{" + slot + "} was ", "{" + slot + "} were ")
    for slot in slots:
        text = text.replace("{" + slot + "}", picked[slot], 1)
    # The labels are what Luma's recognizer reads in the finished sentence (so they always agree with how Luma understands it),
    # minus anything that came only from the everyday topic ("the pass" in a kitchen topic isn't slang someone chose to use).
    topic_only = {e.term for slot in slots if _is_topic(community, slot) for _, e in slang.find(picked[slot])}
    chosen = {e.term for slot in slots if not _is_topic(community, slot) for _, e in slang.find(picked[slot])}
    terms = [(said, e.meaning, e.origins) for said, e in slang.find(text) if e.term not in topic_only or e.term in chosen]
    return {"text": text, "community": community, "intent": intent, "terms": terms}


def sample(n, seed=0, community=None):
    """n phrases at random (the same for the same seed), from every community or just one."""
    rows, total = _table()
    rng = random.Random(seed)
    if community is None:
        return [phrase(rng.randrange(total)) for _ in range(n)]
    spans = [(start, cnt) for c, _, _, _, _, start, cnt in rows if c == community]
    out = []
    for _ in range(n):
        start, cnt = rng.choice(spans)
        out.append(phrase(start + rng.randrange(cnt)))
    return out


def by_community():
    """community -> how many phrases."""
    rows, _ = _table()
    out = {}
    for community, _, _, _, _, _, cnt in rows:
        out[community] = out.get(community, 0) + cnt
    return out


def voice(community, limit=10):
    """Words Luma may use back with someone from this circle: real ones, with their meanings, so it never invents slang.
    Taken from the circle's own words and frames, casual ones only (no cussing, nothing that needs a uniform to say)."""
    from luma.agent import slang
    pack = PACKS.get(community)
    if not pack:
        return []
    words = [w for ws in pack["roles"].values() for w in ws]
    words += [re.sub(r"\{\w+\}", " ", frame) for frame, _ in pack["frames"]]
    seen, out = set(), []
    for w in words:
        for said, entry in slang.find(w):
            key = entry.term.lower()
            if key in seen or entry.register != "c" or community not in entry.origins and community != "internet":
                continue
            seen.add(key)
            out.append((entry.term, entry.meaning))
    return out[:limit]


def joke(community, n=0):
    """One of this circle's in-jokes (about shared situations, never about who someone is), or None."""
    bits = (PACKS.get(community) or {}).get("bits") or []
    return bits[n % len(bits)] if bits else None
