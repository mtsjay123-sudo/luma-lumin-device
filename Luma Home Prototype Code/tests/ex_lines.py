"""Lines for an ex, a closed subject and a wish to vent (luma.agent.exes). Written Nov 26, 2026, before the reader, by
one hand in one sitting. The first group of each is built on; the "_2" groups were written in the same sitting, after
the first, and are measured once and never tuned on (the honest number, by the same hand the same hour).

Made-up people only."""

# They close the subject of their ex, and that's the whole of what they said.
CLOSE_EX = [
    "please don't bring up my ex again",
    "can we not talk about my ex",
    "don't mention my ex anymore",
    "I don't want to talk about my ex",
    "stop asking about my ex please",
    "let's not bring up my ex-boyfriend",
    "please never mention my ex-girlfriend",
    "i'd rather not talk about my ex husband",
    "can you stop bringing up my ex",
    "do not talk about my ex wife",
    "never bring up my ex again ok",
    "quit mentioning my ex",
]
CLOSE_EX_2 = [
    "pls dont bring up my ex",
    "I really don't want to talk about my ex right now",
    "can we please not talk about my ex-husband",
    "stop bringing up my ex, seriously",
    "don't ask me about my ex",
    "let's not talk about my ex tonight",
]

# Closing a subject that isn't an ex.
CLOSE_OTHER = [
    "please don't bring up the divorce",
    "can we not talk about my dad",
    "don't mention my job",
    "stop asking about the wedding",
    "I don't want to talk about my weight",
    "let's not bring up the accident",
]

# An ex, or bringing something up, that isn't closing anything.
NOT_CLOSE = [
    "my ex texted me out of nowhere",
    "should I bring up my ex with my therapist",
    "he keeps bringing up his ex",
    "my ex brought up the house again",
    "don't let me text my ex tonight",
    "I can't stop thinking about my ex",
    "my friend won't stop talking about her ex",
    "remind me to bring up the rent with my landlord",
    "can we talk about my ex",
    "what do you think of my ex",
]
NOT_CLOSE_2 = [
    "my ex is getting married",
    "I ran into my ex at the grocery store",
    "is it weird to stay friends with an ex",
    "don't let me forget to mention the leak to my landlord",
    "my sister wants me to stop talking about my ex",
    "I want to talk about my ex",
]

# They broke up: (what they said, the name in it or None, the word for who it was or None).
BREAKUP = [
    ("Caden and I broke up", "Caden", None),
    ("I broke up with Caden last night", "Caden", None),
    ("Caden dumped me", "Caden", None),
    ("me and Jordan split up", "Jordan", None),
    ("we broke up", None, None),
    ("I broke up with my boyfriend", None, "boyfriend"),
    ("my girlfriend broke up with me", None, "girlfriend"),
    ("Sam broke up with me today", "Sam", None),
    ("it's over between me and Alex", "Alex", None),
    ("Riley is my ex now", "Riley", None),
    ("Taylor and I aren't together anymore", "Taylor", None),
]
BREAKUP_2 = [
    ("Morgan and I called it quits", "Morgan", None),
    ("I dumped Chris", "Chris", None),
    ("my boyfriend and I split up last week", None, "boyfriend"),
    ("Devon broke up with me over text", "Devon", None),
    ("we're not together anymore", None, None),
    ("my husband left me", None, "husband"),
]

# Not a breakup.
NOT_BREAKUP = [
    "my sister broke up with her boyfriend",
    "the band broke up",
    "Caden broke his phone",
    "I broke up the fight",
    "my parents split up when I was a kid",
    "the meeting broke up early",
    "we broke up the work into parts",
    "Jordan and I made up",
    "my friend Sam dumped her boyfriend",
    "the call broke up",
    "Alex and I are together again",
]
NOT_BREAKUP_2 = [
    "the ice broke up on the lake",
    "my best friend and her girlfriend split up",
    "Morgan and I split the bill",
    "I dumped all the old files",
    "Chris broke the news to me",
    "we're not together on this one",
]

# What they say back when Luma asks the ex's name: (said, the name kept).
NAME_ANSWERS = [
    ("Caden", "Caden"),
    ("his name is Caden", "Caden"),
    ("her name's Mia", "Mia"),
    ("it's Jordan", "Jordan"),
    ("Caden.", "Caden"),
    ("caden", "Caden"),
    ("Marcus Reed", "Marcus Reed"),
    ("it was Tyler", "Tyler"),
    ("they're called Sam", "Sam"),
    ("ugh, Derek", "Derek"),
]
NAME_ANSWERS_2 = [
    ("Ethan", "Ethan"),
    ("his name was Logan", "Logan"),
    ("her name is Priya", "Priya"),
    ("Noah lol", "Noah"),
]
# What they say back that isn't a name, and is never kept as one.
NOT_NAMES = [
    "I'd rather not say",
    "never mind",
    "no",
    "it doesn't matter",
    "why do you need that",
    "ugh traffic was awful",
    "I'm tired",
    "what's the weather tomorrow",
    "lol",
    "idk",
    "forget it",
]
NOT_NAMES_2 = [
    "I don't want to say his name",
    "nope",
    "can we move on",
    "Tuesday",
    "my day was fine",
]

# Only the wish to vent: a friend says they're listening.
VENT_ONLY = [
    "I don't need advice, I just need to vent",
    "i just need to vent",
    "can you just listen",
    "I just want to rant for a minute",
    "no advice please, just listen",
    "I don't want solutions, I just want to vent",
    "just let me vent ok",
    "I need to vent",
]
VENT_ONLY_2 = [
    "i need to rant",
    "just listen to me for a sec",
    "not looking for advice, just need to vent",
    "can I vent to you",
]
# The wish with more in it, or not the wish at all: the brain answers these.
NOT_VENT_ONLY = [
    "I just need to vent about my boss, he yelled at me in front of everyone",
    "my friend always needs to vent to me",
    "do you ever need to vent",
    "I don't need advice on my resume, just a second look",
    "can you listen to this song",
    "I vented to my mom earlier",
]
NOT_VENT_ONLY_2 = [
    "I need to vent the dryer",
    "she just wants to vent",
    "can you listen for the doorbell",
    "I need to vent because my landlord raised the rent again and I can't afford it",
]
