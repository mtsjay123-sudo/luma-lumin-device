"""Lines for the lock (tests/test_who.py), written before the lock was built (Nov 25).

The passcode in every line is "blue kettle tuesday". RIGHT is forty ways someone says it: fast, slow, mumbled, with the
wake word, mid-sentence, and the slips a speech reader makes (a doubled letter, a vowel heard wrong, one word heard as two).
NEAR is twenty that are close and must not open it. The other 180 "sentences that aren't it" are the first 180 things
people say in Human Test v2, read from its file by the test.
"""
PASSCODE = "blue kettle tuesday"

RIGHT = [
    "blue kettle tuesday", "Blue Kettle Tuesday", "blue kettle tuesday.", "blue, kettle, tuesday", "BLUE KETTLE TUESDAY",
    "blue kettle tuesday!", "uh blue kettle tuesday", "um, blue kettle tuesday", "it's blue kettle tuesday", "its blue kettle tuesday",
    "hey luma blue kettle tuesday", "yo luma, blue kettle tuesday", "luma blue kettle tuesday", "okay blue kettle tuesday",
    "my passcode is blue kettle tuesday", "the passcode is blue kettle tuesday", "passcode blue kettle tuesday",
    "it's me, blue kettle tuesday", "blue kettle tuesday, it's me", "blue kettle tuesday please", "blue kettle tuesday thanks",
    "blue kettle tuesday luma", "so blue kettle tuesday", "right, blue kettle tuesday", "blue... kettle... tuesday",
    "blue kettle - tuesday", "blue  kettle   tuesday", "bluekettle tuesday", "blue kettle tues day", "blu kettle tuesday",
    "blue kettel tuesday", "blue kettle tuseday", "blue cattle tuesday", "blue kettle tuesdays", "bleu kettle tuesday",
    "blue kettle chewsday", "hang on, blue kettle tuesday, okay", "yeah it's blue kettle tuesday man",
    "unlock, blue kettle tuesday", "blue kettle toosday",
]

NEAR = [
    "blue kettle", "kettle tuesday", "blue tuesday", "tuesday kettle blue", "blue tuesday kettle", "kettle blue tuesday",
    "blue kettle wednesday", "red kettle tuesday", "blue bottle tuesday", "blue kettle thursday", "green kettle tuesday",
    "the kettle is blue and it's tuesday", "i bought a blue kettle on tuesday", "blue", "tuesday", "kettle",
    "is the passcode blue something", "i forgot the passcode", "blue kettles are on sale tuesday through friday", "black kettle tuesday",
]
