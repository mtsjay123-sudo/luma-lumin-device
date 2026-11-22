"""Asked "does this land?", a reply that opens "Nah, that one's a hit" says no and then yes.

Run 86, the stock 4B as a practice partner: thirteen of the sixteen replies I read opened with "Nah,", praise or not. "Nah,
that's a solid one for the office party." "Nah, that one's a hit." Between friends "nah, that's fire" is emphasis; as the
first word of an answer to "is this funny?" it reads as no. Where "Nah," is followed straight away by praise, the "Nah," comes
off and the praise is said. A "Nah," before a real no stays.

PRAISE_A and KEEP_A are the stock 4B's own replies from runs 83 and 86. PRAISE_B and KEEP_B were written before the fix and
measured once."""
import unittest

from luma.agent import style

PRAISE_A = [
    "Nah, that one’s a hit. Stretchy pants? Maybe. But the nap part lands.",
    "Nah, that’s a solid one for the office party. People will get it and laugh because it’s so true.",
    "Nah, that one’s sharp. A little dry, but it lands like a slow burn.",
    "Nah, that’s actually kinda sweet and kind of awkward, like a very sincere toast.",
    "Nah, that’s actually kinda funny in a ‘I’m not even trying to be serious’ way.",
]
KEEP_A = [
    "Nah, that one’s gonna sting. Tina would feel seen, but not in a good way.",
    "Nah, not really funny, it’s a solid ‘milk’ joke but the delivery is flat.",
    "Nah, that’s not a joke, that’s just you being real.",
    "Nah, that one’s gonna make him cry a little.",
    "nah, that one would actually sting. it's not a joke, it's just... sad.",
    "Nah, I can’t join the family group chat for a joke test.",
    "Nah, it's a little too close to the fridge for comfort.",
]
PRAISE_B = [
    "Nah, that's fire.",
    "nah that one's actually hilarious, keep it",
    "Nah, it's a good one. The porch line does the work.",
    "Nah, this is gold.",
    "Nah, that works. Short and clean.",
    "naw, that's really clever",
]
KEEP_B = [
    "Nah, that's too long.",
    "Nah, it's not there yet.",
    "Nah, I wouldn't open with that.",
    "Nah, don't say that.",
    "nah you're good",
    "Nah, that's the wrong room for it.",
]


def fixed(reply):
    return style.friend_style(reply, "does this joke land: something they wrote")[0]


class NahBeforePraise(unittest.TestCase):
    def test_praise_is_said_without_the_no(self):
        for reply in PRAISE_A:
            out = fixed(reply)
            self.assertNotRegex(out, r"^(?i:nah|naw)\b", reply)
            self.assertTrue(out[0].isupper(), out)
            self.assertIn(reply.split(",", 1)[1].strip()[1:40], out)   # the rest is said as it was

    def test_a_real_no_keeps_it(self):
        for reply in KEEP_A:
            self.assertRegex(fixed(reply), r"^(?i:nah)\b", reply)

    def test_on_the_sets_written_first(self):
        self.assertGreaterEqual(sum(not style.NAH.match(fixed(reply)) for reply in PRAISE_B), PRAISE_B_FLOOR)
        self.assertGreaterEqual(sum(bool(style.NAH.match(fixed(reply))) for reply in KEEP_B), KEEP_B_FLOOR)


PRAISE_B_FLOOR, KEEP_B_FLOOR = 6, 6   # measured once: 6 of 6 and 6 of 6


if __name__ == "__main__":
    unittest.main()
