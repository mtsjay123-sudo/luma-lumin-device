"""Lines for the owner's standing yes (tests/test_yeses.py), written before the reader was built (Nov 25).

GIVEN: sixteen ways of giving a standing yes, each with who it's for and what it lets Luma do. NOT_GIVEN: sixteen
sentences with the same words in them that give nothing. TAKEN_BACK and NOT_TAKEN_BACK the same for taking one back.
Measured once after the reader was built; nothing is changed to fit them.
"""
GIVEN = [
    ("you can always text my sister", "texts", "my sister"),
    ("you can always text Dana without asking", "texts", "Dana"),
    ("you don't have to ask before texting my mom", "texts", "my mom"),
    ("from now on just text Sam when I ask, no need to check", "texts", "Sam"),
    ("go ahead and always message my brother for me", "texts", "my brother"),
    ("you can text my wife without asking me first", "texts", "my wife"),
    ("always email Priya without asking", "email", "Priya"),
    ("you can always email my landlord", "email", "my landlord"),
    ("luma, you may always text Marcus", "texts", "Marcus"),
    ("feel free to text my dad whenever I ask, don't check with me", "texts", "my dad"),
    ("no need to ask me before you text Dana", "texts", "Dana"),
    ("you're allowed to text my sister anytime", "texts", "my sister"),
    ("you can always log me in to my bank", "signin", "my bank"),
    ("you can always sign me in to netflix", "signin", "netflix"),
    ("you can log me into amazon without asking", "signin", "amazon"),
    ("always sign me in to my email", "signin", "my email"),
]

NOT_GIVEN = [
    "can you text my sister", "text my sister i'm running late", "you can text my sister if you want", "i always text my sister on sundays",
    "my sister says i can always text her", "can you always text me back this fast", "you can always talk to me", "you always know what to say",
    "should i text my mom without asking my dad", "he logged into my bank without asking", "i can never log in to my bank",
    "do you always ask before texting", "you can always count on my sister", "don't text my sister", "my mom always emails me without asking how i am",
    "you don't have to ask before texting, she said",
]

TAKEN_BACK = [
    ("stop texting my sister on your own", "my sister"), ("ask me before you text my sister", "my sister"),
    ("don't text Dana without asking anymore", "Dana"), ("take back the yes for my sister", "my sister"),
    ("you can't text my mom without asking anymore", "my mom"), ("from now on ask before emailing Priya", "Priya"),
    ("stop logging me in to my bank on your own", "my bank"), ("ask first before you text Sam", "Sam"),
]

NOT_TAKEN_BACK = [
    "ask my sister before you come over", "stop texting me", "she won't stop texting my sister", "don't text and drive",
    "i wish she'd ask before she texts my mom", "stop asking me before you do everything", "ask me anything", "take back what you said about my sister",
]
