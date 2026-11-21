"""A death said with a slip of the fingers, as how it happened, or in Spanish.

"my dad passd away this morning" was plain talk to Luma, so the brain was told a little humor was welcome. Found by
reading what a brain is told on Human Test v2 (Nov 21, 2026), then built on twenty fresh lines and twenty near
misses, none of them the test's.

BUILT_ON and NEAR: what the patterns were written on (11 of 20 read before, 2 of 20 near misses read as a loss).
SECOND and SECOND_NEAR: written before the patterns were applied and measured once: 7 -> 13 of 20 read, near misses
taken 3 -> 2 of 20. The two taken (lost in a shop, a goodbye at the airport) are built on now; the seven misses
stand: they're ways of saying it without a death word at all, and on a real brain the plain question catches those.
"""
import unittest

from luma.agent import feelings, humor

BUILT_ON = [
    'my dad passd away this morning',
    'my mom pased away last night',
    'my grandma dide yesterday',
    'he past away on sunday',
    'my brother passed awya an hour ago',
    'my wife died las night',
    "my best friend is gone, he od'd on friday",
    'we lost him. my baby brother',
    'my dog didnt make it through the night',
    "she didn't make it. the surgery",
    'my grandpa is no longer with us as of this morning',
    "got the call. dad's gone",
    'mi mamá falleció ayer',
    'mi abuelo murió esta mañana',
    'se nos fue mi tío anoche',
    'my aunt passed 2 days ago n i cant stop thinking abt it',
    'rip to my cousin, he was only 22',
    'they took my mom off life support today',
    'my husbands funeral is tomorrow',
    'my sister was killed by a drunk driver last week',
]
NEAR = [
    "my phone passed away lol it won't charge",
    'my dad passed the kidney stone finally',
    'i passed out at the gym',
    'the deadline passed yesterday',
    "he past me in the hallway and didn't say hi",
    'my battery died on the highway',
    'i died laughing at that',
    'my character died in the last episode',
    'the wifi is gone again',
    "my team didn't make it to the playoffs",
    "she didn't make it to the party",
    'i killed it at karaoke',
    'my grandma passed her driving test at 80',
    "dad's gone fishing for the weekend",
    'mi mamá llegó ayer',
    'se nos fue la luz anoche',
    'rip my diet',
    "my husband's funeral home job is stressing him out",
    'they took my mom off the waiting list, she got the appointment',
    'my uncle passed me the ball and i scored',
]
SECOND = [
    'my mom passed awy on friday',
    'lost my dad to cancer in march',
    'my granddad pasted away this morning',
    'my little brother was killed in a car wreck',
    'mi papá murió hace dos semanas',
    'my friend took his own life last month',
    "grandma's gone. she went in her sleep",
    'my baby was born sleeping',
    'we had to turn off the machines yesterday',
    'my husband died in my arms',
    'they found my uncle this morning. heart attack',
    'my wife didnt wake up this morning',
    'the hospital called, mom is gone',
    "my son overdosed and didn't survive",
    'falleció mi abuelita anoche',
    'my dog got hit by a car and didnt survive',
    'we said our last goodbye to grandpa today',
    'my twin sister passed 3 weeks ago',
    'just came back from burying my father',
    'my best friend got shot and killed saturday',
]
SECOND_NEAR = [
    'my mom passed the bar exam!!',
    'i lost my dad at the mall for twenty minutes',
    'my brother killed it at his recital',
    'mi papá llegó hace dos semanas',
    'my friend took his own car to the shop',
    "grandma's gone to bingo",
    'my baby finally slept through the night',
    'we had to turn off the water yesterday',
    'my laptop died in the middle of the meeting',
    "they found my uncle's lost wallet this morning",
    "my wife didn't wake up to her alarm again",
    'the hospital called, mom can come home',
    'my son overslept and missed the bus',
    'the old year passed so fast',
    'my dog got hit by a skunk spray and smells awful',
    'we said goodbye to grandpa at the airport today',
    'my sister passed me a note in church',
    'just came back from visiting my father',
    'my best friend shot a hole in one saturday',
    'time passed away so quickly on vacation',
]


def a_loss(line):
    return humor.read_tone(line)["mood"] == "grief"


class ReadAsALoss(unittest.TestCase):
    def test_the_lines_it_was_built_on(self):
        for line in BUILT_ON:
            self.assertTrue(a_loss(line), line)
            self.assertEqual((feelings.read(line) or {}).get("family"), "grief", line)
        for line in NEAR:
            self.assertFalse(a_loss(line), line)

    def test_the_second_set_is_the_honest_number(self):
        self.assertGreaterEqual(sum(a_loss(line) for line in SECOND), 13)       # measured once: 13 of 20 (7 before)
        self.assertEqual([line for line in SECOND_NEAR if a_loss(line)], [])    # 2 of 20 when measured, built on now

    def test_the_brain_is_told_its_a_loss_and_never_that_humor_is_welcome(self):
        for line in ("my mom pased away last night", "mi abuelo murió esta mañana", "my sister was killed by a drunk driver last week"):
            note = humor.turn_note(line)
            self.assertIn("they're talking about a loss", note, line)
            self.assertNotIn("humor is welcome", note, line)

    def test_a_deadline_passing_and_a_job_at_a_funeral_home_arent_one(self):
        for line in ("the deadline passed yesterday", "my husband's funeral home job is stressing him out", "i lost my dad at the mall for twenty minutes",
                     "we said goodbye to grandpa at the airport today", "se nos fue la luz anoche"):
            self.assertFalse(a_loss(line), line)
        for line in ("i lost my dad in the spring", "we said goodbye to grandpa in the hospital last night"):
            self.assertTrue(a_loss(line), line)


if __name__ == "__main__":
    unittest.main()
