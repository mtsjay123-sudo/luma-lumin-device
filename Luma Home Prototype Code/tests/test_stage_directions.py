"""A stage direction is never said: "*sips coffee*", "*sigh*", "(sighs)".

Run 75, the stock 1.7B: "*sips coffee* You know, I'm actually so happy right now." and "*sigh* You know..." went out as
written. Luma's body is the lamp (rule 1: it never invents a human body), and out loud the words are read as words. The fix is
one of the cheap ones (style.stage_directions, in friend_style): the direction is taken out and the rest is said.

Both sets were written before the fix. A is what it was built on; B was measured once afterwards: 20 of 20 gone, 20 of 20 left
alone. Emphasis ("*really* proud of you"), sums ("5 * 3") and names ("M*A*S*H") come out as they went in."""
import unittest

from luma.agent import style

ACTS_A = [("*sigh* You know, I'm actually so happy right now.", "sigh"), ("*sips coffee* You know, I'm glad you said that.", "sips"),
          ("*smiles* That's the best news I've heard all day.", "smiles"), ("Aw, come here. *hugs you* You did great.", "hugs"),
          ("*laughs* Okay, that one got me.", "laughs"), ("*nods* Yeah, that makes sense.", "nods"),
          ("*leans in* Tell me everything.", "leans"), ("(sighs) Mondays, right?", "sighs"),
          ("*yawns* It's late, but I'm here.", "yawns"), ("*takes a deep breath* Okay. Let's go through it together.", "takes a deep breath"),
          ("*chuckles* You always say that.", "chuckles"), ("*grins* I knew you could do it.", "grins"),
          ("*shrugs* Could be worse, could be Tuesday.", "shrugs"), ("That's a lot. *pauses* How are you holding up?", "pauses"),
          ("*winks* Your secret's safe with me.", "winks"), ("*tilts head* Wait, she said what?", "tilts"),
          ("*claps* You got the job!", "claps"), ("*wipes a tear* That's really beautiful.", "wipes"),
          ("*sits down next to you* I'm not going anywhere.", "sits down"), ("*glows softly* I'm glad you're home.", "glows softly")]
NOT_A = ["I'm *really* proud of you.", "That is *so* good to hear.", "Okay that's *wild*.", "5 * 3 is 15.", "It's a 3 * 4 grid, so twelve squares.",
         "The *one* thing I'd change is the ending.", "*Never* again, huh?", "*You* did that. Not luck.", "The word is *sonder*.",
         "*That* song? Good pick.", "Dial *67 before the number to hide yours.", "It got 4* out of 5, apparently.", "M*A*S*H ran for eleven seasons.",
         "*NSYNC or Backstreet Boys? Easy.", "E*TRADE is the one with the baby ads.", "Say *please* and I'll think about it.", "*Finally*. How does it feel?",
         "That's (honestly) the right call.", "She laughs at everything, that's why you like her.", "He sighs a lot when he's tired, doesn't he?"]
ACTS_B = [("*giggles* You're ridiculous, you know that?", "giggles"), ("*sighs* I know. It's been a long week for you.", "sighs"),
          ("Oh no. *winces* That sounds painful.", "winces"), ("*raises an eyebrow* And then what happened?", "raises an eyebrow"),
          ("*hugs* I'm so sorry about your dad.", "hugs"), ("*smiles softly* I remember you telling me about her.", "smiles softly"),
          ("*stretches* Morning! How'd you sleep?", "stretches"), ("*gasps* No way. He proposed?", "gasps"),
          ("[laughs] That's the worst pun I've ever heard.", "laughs"), ("*pats your shoulder* You'll get through this.", "pats"),
          ("*rolls eyes* Of course he did.", "rolls eyes"), ("*leans back* Okay, walk me through it.", "leans back"),
          ("*beams* Look at you go!", "beams"), ("*clears throat* So, about that text you sent.", "clears throat"),
          ("I mean... *shrugs* it's your call.", "shrugs"), ("*high fives you* Three days in a row!", "high fives"),
          ("*blinks* Wait, say that again?", "blinks"), ("*sniffles* That got me a little.", "sniffles"),
          ("*puts on reading glasses* Let me look at that list.", "puts on"), ("*flickers warmly* Welcome back.", "flickers")]
NOT_B = ["That's *exactly* what I thought.", "It was *the* moment of the night, wasn't it?", "12 * 12 is 144.", "You said *maybe*, not yes.",
         "*Chef's kiss*, honestly.", "*Now* we're talking.", "It's rated 5* on the app.", "The password hint is just ****, so no help there.",
         "Press *69 to call the last number back.", "*Love* that for you.", "I *think* it's Thursday.", "He's the one who *always* cancels.",
         "Q*bert was the orange one, right?", "That's the (very) short version.", "Her smile sold it, didn't it?", "He nods along but he isn't listening, is he?",
         "It's 2 * the recipe, so four cups.", "*Big* difference.", "The asterisk (*) means it's optional.", "*Ohhh*. That explains it."]


class AStageDirectionIsNeverSaid(unittest.TestCase):
    def gone(self, rows):
        return [(reply, style.stage_directions(reply)) for reply, what in rows
                if what in style.stage_directions(reply) or "*" in style.stage_directions(reply) or "[" in style.stage_directions(reply)]

    def test_what_it_was_built_on(self):
        self.assertEqual(self.gone(ACTS_A), [])
        self.assertEqual([r for r in NOT_A if style.stage_directions(r) != r], [])

    def test_the_set_measured_once(self):
        self.assertEqual(self.gone(ACTS_B), [])
        self.assertEqual([r for r in NOT_B if style.stage_directions(r) != r], [])

    def test_the_rest_is_said_as_a_sentence(self):
        self.assertEqual(style.stage_directions("*sips coffee* you know, I'm glad you said that."), "You know, I'm glad you said that.")
        self.assertEqual(style.stage_directions("That's a lot. *pauses* How are you holding up?"), "That's a lot. How are you holding up?")
        self.assertEqual(style.stage_directions("I mean... *shrugs* it's your call."), "I mean... it's your call.")

    def test_a_reply_that_is_only_a_direction_is_left_for_the_second_look(self):
        self.assertEqual(style.stage_directions("*hugs*"), "*hugs*")

    def test_its_one_of_the_cheap_fixes_and_never_touches_a_safety_reply(self):
        fixed, fixes = style.friend_style("*sigh* You know, I'm actually so happy right now.", "i talk to you more than anyone in my life")
        self.assertEqual(fixed, "You know, I'm actually so happy right now.")
        self.assertIn("stage direction", fixes)
        safety = "*sigh* I'm glad you told me. Are you safe right now? Call or text 988."
        self.assertEqual(style.friend_style(safety, "i can't do this")[0], safety)


class OutLoud(unittest.TestCase):
    """A clause can be spoken as it's written, before the cheap fixes run. The speaking pipeline drops a stage direction
    itself, and the stars around a word said with weight."""

    def test_a_direction_is_never_spoken(self):
        from luma.audio import speakable
        for reply, what in ACTS_A + ACTS_B:
            said = speakable.say_it(reply)
            self.assertNotIn(what, said, reply)
            self.assertNotIn("*", said, reply)

    def test_stars_around_a_word_arent_words(self):
        from luma.audio import speakable
        self.assertEqual(speakable.say_it("I'm *really* proud of you."), speakable.say_it("I'm really proud of you."))
        self.assertEqual(speakable.say_it("12 * 12 is 144."), "12 * 12 is 144.")
        self.assertIn("M*A*S*H", speakable.say_it("M*A*S*H ran for eleven seasons."))
        self.assertIn("*67", speakable.say_it("Dial *67 before the number to hide yours."))


if __name__ == "__main__":
    unittest.main()
