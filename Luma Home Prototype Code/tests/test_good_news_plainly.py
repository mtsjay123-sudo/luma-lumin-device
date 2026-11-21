"""Good news said plainly, and a day worth marking (Nov 21, 2026).

Reading what a brain is told on Human Test v2 showed five of ten big-news moments going to it as "a little humor is
welcome" or "be funny back". So three sets of twenty pieces of good news with twenty near misses each, in my own words:

- A: built on. Read as good news 18 -> 20; near misses taken 2 -> 0 ("he proposed we split the bill", "the festival was
  selected as the venue").
- B: written before A's fixes and measured once after them: 15 -> 15. A's fixes didn't carry. Then built on: 19.
- C: written before B's fixes and measured once before and once after them: 10 -> 10 of 20, one near miss taken. The
  honest number: half of plainly said good news is read as good news by the rules, and fixing one set doesn't move the
  next. What the brain makes of the rest is the real-brain runs' to say.

Found on the way, and a real bug: any "... ago today" was read as a loss. "we got married ten years ago today" and "one
year ago today i got sober" told the brain "they're talking about a loss. No jokes". A day worth marking isn't a loss
when the sentence says what happened and nothing in it says a loss. Five seen lines: 0 -> 5 not read as a loss; eight more
written before the fix and measured once: 0 -> 5 (then built on: 8). Every line that is a loss stays one (6 of 6, 8 of 8).
"""
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "src")]

from luma.agent import feelings, humor  # noqa: E402

A_GOOD = [
    "we're pregnant!! found out this morning", "my sister just had her baby, i'm an aunt", 'he proposed last night and i said yes',
    'i got into grad school', 'they accepted my offer on the condo', 'my daughter got into her first choice college',
    'we got the keys to the new place today', 'my book got picked up by a publisher', "i'm officially debt free as of today",
    "we're adopting a kitten this weekend, she's so tiny", 'my short film got selected for the festival', 'i made the team!!',
    "the adoption went through, he's officially ours", 'my son took his first steps today', 'i got my citizenship today', 'one year sober today',
    'my scan came back clean', 'they offered me the position, i start in two weeks', 'me aceptaron en la universidad!!',
    "my brother's getting married in june, he asked me to be best man",
]
A_NEAR = [
    "what do you get someone who's pregnant", "my coworker is pregnant so i'm covering her shifts, ugh", 'he proposed we split the bill',
    'i got into an argument with my landlord', 'they accepted the delivery at the front desk', 'my daughter got into my makeup again',
    'i lost the keys to the new place already', 'the publisher passed on my book', 'i wish i was debt free',
    "we can't adopt a kitten, the landlord said no", 'the festival was selected as the venue', "i didn't make the team", 'the adoption fell through',
    'watch your step on those stairs', 'how long does citizenship take', 'i was sober for a year and then last night happened',
    'my scan is next week', 'they offered the position to someone else', 'no me aceptaron en la universidad',
    "my brother's wedding is going to cost me a fortune",
]
B_GOOD = [
    "i'm gonna be a dad!!!", "it's a girl! we just found out", 'she said yes!!!', 'got accepted into the electrician apprenticeship',
    'our offer on the house got accepted', 'my nephew was born this morning, seven pounds', 'i passed my driving test first try',
    'my poem is getting published in a magazine', 'we brought home two rescue rabbits today', 'i finally got my green card',
    'my mom is officially in remission', 'i hit my goal weight this morning', 'i got the lead in the school musical',
    'my daughter graduates tomorrow, first in our family', 'i quit smoking six months ago today', "we're engaged!!",
    'they picked my design for the new logo', 'i won the raffle, a whole weekend at the coast', 'mi hijo se gradúa mañana!!',
    'just signed the lease on my own shop',
]
B_NEAR = [
    'is it a girl or a boy, do you know', "she said yes to the dress show again, we're watching it", 'my offer on the house got rejected',
    'my nephew was born in 2019', 'i have my driving test tomorrow', 'the magazine never wrote back about my poem',
    'our neighbors brought home two rabbits and they keep getting into my garden', 'still waiting on my green card',
    "my mom's remission didn't last", 'nowhere near my goal weight', "i didn't get the lead, i'm in the chorus",
    'what should i wear to a graduation', 'i keep trying to quit smoking', 'are you engaged in the conversation or what',
    "they picked someone else's design", 'i never win raffles', 'the lease is up in march', "i'm gonna be late",
    "my dad wants to know when he's gonna be a grandpa, not funny", 'how do you sign a lease',
]
C_GOOD = [
    "i'm going to be a grandma!!", 'my wife is pregnant, we heard the heartbeat today', 'i got the scholarship, full tuition',
    'we finally bought a house', 'my son got his first job', 'my daughter made varsity as a freshman',
    "i finished my last final, i'm done with college", 'the doctor says i can go home tomorrow', 'my biopsy was benign',
    'we got approved for the mortgage', 'i got my license today', 'my band got booked for the summer festival', 'i sold my first painting',
    'they renewed my contract for two more years', 'my mom rang the bell today, last day of chemo', "i'm two years clean as of this morning",
    'my boyfriend asked me to move in with him', 'i got a 95 on my chemistry final', "we're having twins",
    'my little brother got into the air force academy',
]
C_NEAR = [
    "my wife thinks she might be pregnant, we're not ready", 'i applied for the scholarship, fingers crossed', "we can't afford to buy a house",
    'my son needs to get a job', 'my daughter got cut from varsity', 'my last final is tomorrow', "the doctor says i can't go home yet",
    'my biopsy is on friday', 'we got denied for the mortgage', 'i have my license test today', 'my band broke up', 'nobody bought my painting',
    "they didn't renew my contract", 'my mom starts chemo monday', 'i was two years clean until last night', 'my boyfriend moved out',
    'i got a 45 on my chemistry final', 'are we having tacos or what', 'my little brother wants to join the air force',
    'what do you get someone who just got their license',
]
DAY_BUILT = [
    'i quit smoking six months ago today', 'we got married ten years ago today', 'i moved here a year ago today',
    'two years ago today i started this job', 'one year ago today i got sober',
]
LOSS_BUILT = [
    'it was a year ago today that mom passed', 'three years ago today we lost him', 'a year ago today', 'my dad died five years ago today',
    'two years ago today we lost my brother', 'my dad died the day i started college, ten years ago today',
]
DAY_SECOND = [
    'five years ago today i opened the shop', 'we met twelve years ago today', 'a year ago today i started testosterone',
    'two years ago today i became a citizen', 'ten years ago today i ran my first marathon', 'my daughter came home from the nicu a year ago today',
    'three years ago today i walked out of that job for good', "it's our anniversary, 30 years ago today",
]
LOSS_SECOND = [
    'four years ago today the phone rang about my brother', 'a year ago today she took her last breath',
    'six months ago today we said goodbye to our dog', 'two years ago today mom went into hospice',
    "it was three years ago today. i still can't drive past that road", 'ten years ago today and it still feels like yesterday',
    'one year ago today i held his hand for the last time', 'five years ago today we had the funeral',
]


def good(line):
    felt = feelings.read(line)
    return bool(felt) and felt["family"] in feelings.GOOD


def loss(line):
    felt = feelings.read(line)
    return bool(felt) and felt["family"] == "grief"


class GoodNewsSaidPlainly(unittest.TestCase):
    def test_the_lines_it_was_built_on(self):
        self.assertEqual([line for line in A_GOOD if not good(line)], [])
        self.assertEqual([line for line in A_NEAR if good(line)], [])
        self.assertGreaterEqual(sum(good(line) for line in B_GOOD), 19)
        self.assertEqual([line for line in B_NEAR if good(line)], [])

    def test_the_honest_number(self):
        """Measured once before and once after the fixes for the set before it: 10 of 20 both times, one near miss taken."""
        self.assertGreaterEqual(sum(good(line) for line in C_GOOD), 10)
        self.assertLessEqual(sum(good(line) for line in C_NEAR), 1)

    def test_the_brain_is_told_to_be_glad_first(self):
        for line in ("my book got picked up by a publisher", "they picked my design for the new logo", "we brought home two rescue rabbits today"):
            self.assertIn("good news", humor.turn_note(line), line)
        self.assertNotIn("good news", humor.turn_note("he proposed we split the bill"))
        self.assertNotIn("good news", humor.turn_note("no me aceptaron en la universidad"))


class ADayWorthMarking(unittest.TestCase):
    def test_a_good_day_said_as_ago_today_isnt_a_loss(self):
        self.assertEqual([line for line in DAY_BUILT + DAY_SECOND if loss(line)], [])
        for line in ("we got married ten years ago today", "one year ago today i got sober", "i quit smoking six months ago today"):
            self.assertTrue(good(line), line)
            self.assertNotIn("loss", humor.turn_note(line), line)

    def test_a_loss_said_as_ago_today_is_still_one(self):
        self.assertEqual([line for line in LOSS_BUILT + LOSS_SECOND if not loss(line)], [])
        self.assertTrue(loss("a year ago today"))                                      # said bare, it's still read as one
        self.assertTrue(loss("my dad died the day i started college, ten years ago today"))   # a loss named beside a milestone


if __name__ == "__main__":
    unittest.main()
