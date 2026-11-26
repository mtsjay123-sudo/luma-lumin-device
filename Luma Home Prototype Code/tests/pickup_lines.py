"""Lines for picking up a word the first time and for tuning itself (tests/test_pickup.py, tests/test_tuning.py),
written before either was built (Nov 26).

MADE_UP: forty sentences, each with one word nobody has heard: theirs. ORDINARY: forty sentences with nothing new in
them: uncommon real words, slips of the fingers, names, laughs and drawn-out words. TOO_LONG: twelve ways someone tells
Luma its replies run long; NOT_ABOUT_LUMA: twelve with the same words that aren't about Luma's replies.
Measured once after the code was built; nothing is changed to fit them.
"""
MADE_UP = [
    ("that meeting was so glorp i nearly walked out", "glorp"), ("my brother is being a total snarfle about the car", "snarfle"),
    ("i'm feeling kind of blonky today", "blonky"), ("we call that a frindle in our house", "frindle"),
    ("honestly the whole trip was pure zazz", "zazz"), ("she gave me the wibbles when she said that", "wibbles"),
    ("can't talk long, i'm completely flumped", "flumped"), ("my boss went full krangle on me this morning", "krangle"),
    ("the new place is very snoozle, in a good way", "snoozle"), ("that movie was mid, like deeply plorf", "plorf"),
    ("i need a proper grumbo day on the couch", "grumbo"), ("don't be such a dweezle about it", "dweezle"),
    ("the kids were absolute zorbs at the store", "zorbs"), ("i got that yimby feeling in my stomach again", "yimby"),
    ("we're having a quiet smoodge tonight, just us", "smoodge"), ("work has been nothing but blargle all week", "blargle"),
    ("my grandma used to say i was a real toffelump", "toffelump"), ("that guy at the gym is a certified vonk", "vonk"),
    ("i'm in my flonking era, apparently", "flonking"), ("she texted back with one word, very skrimp of her", "skrimp"),
    ("the dog did a full wazoodle when i got home", "wazoodle"), ("today was a brimble, start to finish", "brimble"),
    ("i hate when my brain goes all quozzy at night", "quozzy"), ("me and my sister call it getting the nargs", "nargs"),
    ("that sandwich was straight up glumptious", "glumptious"), ("he's been pretty drabbit since the layoff", "drabbit"),
    ("i did a little happy shmorgle in the kitchen", "shmorgle"), ("the vibe at dinner was super plinkish", "plinkish"),
    ("i'm too frobbled to cook, ordering in", "frobbled"), ("my coworker is such a klonker in meetings", "klonker"),
    ("it's one of those mornings where everything is jibbly", "jibbly"), ("we used to go trunking down by the river", "trunking"),
    ("i feel a bit woozled after that nap", "woozled"), ("that's the most snerpy thing you've said all day", "snerpy"),
    ("my mom's cooking is peak hobblenosh", "hobblenosh"), ("everybody at the party was being so zibzab", "zibzab"),
    ("i think i'm coming down with the grobbles", "grobbles"), ("the bus ride was a total fwump", "fwump"),
    ("he pulled a classic dorvo and left early", "dorvo"), ("tonight is a snibbet night, phone off", "snibbet"),
]

ORDINARY = [
    "i have a colonoscopy on thursday and i'm dreading it", "my thermostat is acting up again", "we watched a documentary about octopuses",
    "i definately need more sleep", "teh bus was late agian", "i recieved the package yesterday", "my daughter Maribel started kindergarten",
    "hahahaha that's too good", "sooooo tired today", "nooooo way he said that", "ugh mondays", "my chiropractor says it's my posture",
    "we're going to albuquerque for thanksgiving", "i made shakshuka for breakfast", "the pharmacist was really helpful",
    "lol ok", "i can't beleive she remembered", "my nephew plays the euphonium", "tomorow is my day off", "the wifi keeps disconnecting",
    "i used to live in schenectady", "my physiotherapist gave me exercises", "it's absolutely freezing out", "i'm sooo done with this week",
    "we adopted a greyhound named Biscuit", "the casserole burned", "i got a parking ticket downtown", "my landlord finally fixed the radiator",
    "honestly i'm just exhausted", "the kids have a recital on friday", "i'm thinking about going vegetarian", "yesssss i got it",
    "my ex texted me out of nowhere", "probly gonna stay in tonight", "the mechanic said it's the alternator", "i love sudoku",
    "my sister Priya is visiting", "omg stoppp", "i walked to the bodega for milk", "wierd day, don't ask",
]

TOO_LONG = [
    "that's too long", "you talk too much", "can you keep it shorter", "shorter answers please", "tl;dr", "too many words",
    "you don't have to say so much", "just the short version from now on", "that was a lot, keep it brief", "get to the point",
    "less talking", "why are your answers so long",
]

NOT_ABOUT_LUMA = [
    "the line at the dmv was too long", "my mom talks too much", "it's been too long since i saw her", "this week is too long",
    "the short version is i quit", "long story short, we broke up", "he never gets to the point", "the movie was way too long",
    "i've waited too long to call him", "my hair is getting too long", "a lot of words for a sorry", "she said i talk too much",
]

# A second set, written after the reader was changed (a slip of the fingers counts only toward a common word), and
# measured once. This is the honest number; the first set above is what the change was built on.
MADE_UP_2 = [
    ("my roommate left the kitchen in a total skadoosh again", "skadoosh"), ("i'm feeling a little murbly about the move", "murbly"),
    ("we had a proper chinwaggle after church", "chinwaggle"), ("that kid is such a little grembo", "grembo"),
    ("the whole afternoon went fizzlewump on me", "fizzlewump"), ("you know when your head feels all staticky and blorped", "blorped"),
    ("my uncle calls every casserole a hotdish gloop", "gloop"), ("i need to go full hermitto this weekend", "hermitto"),
    ("she did that thing again, the classic swervo", "swervo"), ("it was a deeply unvibey kind of dinner", "unvibey"),
    ("i got the zoomies and the dreadles at the same time", "dreadles"), ("me and dana call it a snacksident", "snacksident"),
    ("the car is making that grunkly noise again", "grunkly"), ("i'm so behind, it's a real paperwork sludgefest", "sludgefest"),
    ("my son says i'm being cringletastic", "cringletastic"), ("that walk was pure medicine, very oomphy", "oomphy"),
    ("i think the neighbors are having another hullabaloozer", "hullabaloozer"), ("today's mood is just bleh with a side of flarp", "flarp"),
    ("we used to call grandpa's truck the rumblebucket", "rumblebucket"), ("i'm a little twizzled from all the coffee", "twizzled"),
    ("the meeting was a snoozapalooza from start to finish", "snoozapalooza"), ("my cat does this little prrrmp when i get home", "prrrmp"),
    ("it's giving me the squirmles thinking about the dentist", "squirmles"), ("he's a sweet guy but kind of a noodlebrain", "noodlebrain"),
    ("i had a full on couchening this afternoon", "couchening"), ("dinner was leftovers, a real fridge scrounge-o", "scrounge"),
    ("i keep doing the worryloop about money", "worryloop"), ("that song has such a good thwump to it", "thwump"),
    ("the baby was extra grizzlish all night", "grizzlish"), ("i told him to stop being so mopish and come out", "mopish"),
    ("my knees are all creakified this morning", "creakified"), ("we're having a low key potterabout day", "potterabout"),
    ("she's in one of her snippety moods", "snippety"), ("this weather makes me feel blanketish", "blanketish"),
    ("my boss sent another one of his megamemos", "megamemos"), ("i did my little morning shufflestretch", "shufflestretch"),
    ("the interview left me kind of jangled and floopy", "floopy"), ("it was a nothingburger of a day honestly", "nothingburger"),
    ("my brother is on his usual grumpalump routine", "grumpalump"), ("i'm in a real sockless sunday frame of mind, total loafage", "loafage"),
]

ORDINARY_2 = [
    "my dermatologist wants to see me again in march", "the dishwasher is leaking onto the floor", "we drove up to saskatoon to see her family",
    "i fogot to call the pharmacy", "its been raining for three days strait", "my daughter Annelise lost her first tooth",
    "bahahaha i can't breathe", "whyyyyy is it only tuesday", "the electrician is coming at nine", "i burned the quesadillas",
    "my grandson is obsessed with stegosauruses", "probaly just going to bed early", "the mortgage payment went up again",
    "i volunteered at the library today", "omggggg she said yes", "my hip replacement is in february", "we had tamales at my aunt's",
    "the neighbor's rottweiler got out again", "i finaly finished the puzzle", "my husband snores like a tractor",
    "the upholstery on that couch is ruined", "thier flight got cancelled", "i'm rewatching seinfeld from the start",
    "my son's pediatrician is retiring", "ughhh my back", "the grocery store was out of cilantro", "i took the ferry to bainbridge",
    "she's allergic to penicillin", "my coworker Dmitri brought donuts", "i slept terribly", "the plumber never showed",
    "we're painting the nursery yellow", "i got a splinter gardening", "my wife's ultrasound is tomorrow", "hehehe you're ridiculous",
    "i should realy drink more water", "the vet says he needs a dental cleaning", "i'm making lasagna for the potluck",
    "my brother moved to chattanooga", "nvm i found it",
]
