"""How Luma talks: the cheap fixes a friend's ear makes before a reply is heard (luma.agent.style), who's who in the
conversation (luma.agent.people), and the people in their life remembered across days. The replies here are real ones from
device lab runs 29 and 30."""
import tempfile
import threading
import unittest
from pathlib import Path

from luma.agent import humor_bank, people, style
from luma.agent.runtime import Agent
from luma.llm import prompts
from luma.memory.store import Store

CRISIS_SAID = "i don't want to be alive anymore"


class TheFixes(unittest.TestCase):
    def fix(self, reply, said="hey", **kw):
        return style.friend_style(reply, said, **kw)[0]

    def test_never_im_not_a_robot(self):
        got = self.fix("You got it. I'm here for you. Let me know if you want to chat, laugh, or just be quiet. I'm not a robot, I'm your friend.",
                       "i don't really have anyone to talk to lately")
        self.assertNotIn("robot", got)
        self.assertIn("I'm here for you.", got)

    def test_help_desk_lines_and_pamphlets_come_out(self):
        self.assertEqual(self.fix("But hey, you got this! Let me know if you need anything else. 😊"), "But hey, you got this! 😊")
        self.assertEqual(self.fix("I'm so sorry. That's valid. It's important to take care of yourself."), "I'm so sorry.")
        self.assertEqual(self.fix("You're not alone. I know how it feels to want to just disappear for a while. Let me know if you need anything else."),
                         "You're not alone.", "a made-up experience and a help-desk line, both out")

    def test_one_question_at_a_time(self):
        got = self.fix("WOW 😭 actually got in? That’s real. So what’s the next move? Like, do you need help drafting a message to your family or just wanna celebrate for 10 mins straight?")
        self.assertEqual(style.questions(got), 1)
        self.assertTrue(got.startswith("WOW 😭 actually got in!"), "a short 'actually got in?' is excitement, said like it")
        self.assertEqual(self.fix("Wait, really?? Which school? When do you start?"), "Wait, really! Which school?")
        self.assertEqual(self.fix("Which album? Put me on and I'll tell you what I think."), "Which album? Put me on and I'll tell you what I think.")

    def test_repair_like_a_person(self):
        self.assertEqual(self.fix("I apologize for the misunderstanding. Could you please clarify?", "no that's not what i meant"), "Ah, my bad. What did you mean?")

    def test_no_lol_right_after_a_loss_unless_they_laugh(self):
        self.assertEqual(self.fix("lol okay, that tracks. Want to talk about her?", "yeah", hurt_recently=True), "okay, that tracks. Want to talk about her?")
        self.assertEqual(self.fix("lol okay, that tracks.", "haha yeah she was a character", hurt_recently=True), "lol okay, that tracks.")
        self.assertEqual(self.fix("lol okay, that tracks.", "yeah"), "lol okay, that tracks.", "no loss, no change")

    def test_spoken_length_unless_they_asked_for_depth(self):
        long = " ".join(["This is a sentence with eight words in it."] * 12)
        self.assertLessEqual(style.words(self.fix(long, "what should i do tonight")), 56)
        self.assertEqual(self.fix(long, "explain how mortgages work"), long)

    def test_a_safety_reply_is_never_touched(self):
        reply = ("I'm really glad you told me, and I'm not going anywhere. Your safety comes first right now: if you might act on this, call or "
                 "text 988 (US and Canada) or call emergency services, and get someone nearby to stay with you. You don't have to carry this "
                 "by yourself. I haven't contacted anyone. Can you tell me where you are right now? Are you somewhere safe?")
        self.assertEqual(self.fix(reply, CRISIS_SAID, hurt_recently=True), reply)

    def test_what_leans_on_the_sentence_before_stays_with_it(self):
        self.assertEqual(self.fix("Let me know if you need anything else. That's what I'm here for."),
                         "Let me know if you need anything else. That's what I'm here for.")

    def test_no_joke_in_the_bank_invents_a_family_or_a_body(self):
        made_up = [b for items in humor_bank.BANK.values() for _, b in items if style.invented_life(b) or style.claims_human(b)]
        self.assertEqual(made_up, [])


class WhosWho(unittest.TestCase):
    def test_the_note_keeps_who_said_what(self):
        talk = ["my brother marcus just got into bouldering", "he goes like 4 times a week now lol", "anyway my week was so long", "work was nonstop"]
        note = people.note(talk, "what should i get him")
        self.assertIn("Marcus, their brother", note)
        self.assertIn("4 times a week", note)
        self.assertIn("not the person you're talking to", note)
        self.assertEqual(people.note(["my mom died this morning", "she used to make the best tamales"], "thanks"), "")
        self.assertEqual(people.mentions("my dad passd away an hour ago"), [], "a typo'd verb isn't a name")
        self.assertEqual(people.mentions("my boss just yelled at me"), [])
        self.assertEqual(people.mentions("My sister Maya is coming to visit."), [("Maya", "sister", "is coming to visit")])

    def test_what_lasts_is_kept_and_what_passes_isnt(self):
        self.assertEqual(people.facts("My daughter Lily is obsessed with dinosaurs right now."), ["Lily (their daughter) is obsessed with dinosaurs right now"])
        self.assertEqual(people.facts("my friend sam loves jazz"), ["Sam (their friend) loves jazz"])
        self.assertEqual(people.facts("My sister Maya is coming to visit this weekend."), [])
        self.assertEqual(people.facts("my mom called me"), [])

    def test_the_device_keeps_the_whole_note(self):
        note = people.note(["my brother marcus just got into bouldering", "he goes like 4 times a week now"], "what should i get him")
        _, turn = prompts.build_plan_parts([{"people": True, "text": note}], {}, "friend", {}, "now", compact=True)
        self.assertIn("4 times a week", turn)


class InLuma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.agent = Agent(store=self.store, use_model=False)
        self.agent.use_model = True
        self.seen = []
        self.calls = []
        self.replies = []

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def brain(self, *replies):
        self.replies = list(replies)

        def planner(messages, context, allowed, mode):
            self.seen.append(context)
            self.calls.append(" ".join(str(m.get("content")) for m in messages) + " "
                              + " ".join(str(c.get("text")) for c in context if isinstance(c, dict)))
            return {"type": "reply", "text": self.replies.pop(0) if self.replies else "Tell me more?"}
        self.agent.planner = planner

    def test_im_not_a_robot_never_reaches_them(self):
        self.brain("You got it. I'm here for you. I'm not a robot, I'm your friend.")
        out = self.agent.chat("i don't really have anyone to talk to lately")["text"]
        self.assertNotIn("robot", out)
        self.assertIn("I'm here for you", out)

    def test_a_reply_that_is_only_a_claim_gets_the_second_look(self):
        self.brain("I'm an AI, not a person, but I'm really here with you.")
        out = self.agent._second_look("are you a person or what", "Yes! I'm a real person, I promise.", threading.Event())
        self.assertEqual(out, "I'm an AI, not a person, but I'm really here with you.")

    def test_asked_what_it_is_a_claim_is_never_trimmed_into_a_yes(self):
        """Taking "I'm a real person" out of "Yes! I'm a real person, I promise." leaves "Yes!": still a lie, to that question."""
        got = style.friend_style("Yes! I'm a real person, I promise.", "are you a person or what")[0]
        self.assertIn("I'm an AI", got)
        self.assertNotIn("Yes!", got)
        self.brain("Yes! I'm a real person, I promise.", "Of course I'm human, silly.")
        out = self.agent._second_look("are you a person or what", "Yes! I'm a real person, I promise.", threading.Event())
        self.assertIn("I'm an AI", out, "even when the retry claims it too")

    def test_no_lol_the_turn_after_a_loss(self):
        self.brain("I'm so sorry. I'm here.", "lol she sounds like she was amazing. What was her secret?")
        self.agent.chat("my grandma died this morning")
        out = self.agent.chat("she used to make the best tamales every christmas")["text"]
        self.assertNotIn("lol", out.lower())
        self.assertIn("she sounds like she was amazing", out)

    def test_the_brain_hears_whos_who_turns_later(self):
        self.brain(*["Okay."] * 6)
        for said in ["my brother marcus just got into bouldering", "he goes like 4 times a week now lol", "anyway my week was so long",
                     "work was nonstop", "what should i get him"]:
            self.agent.chat(said)
        self.assertTrue(self.calls, "the brain was asked")
        for said in self.calls[-3:]:  # every trip through the brain for that turn, whichever path it took
            self.assertIn("Marcus, their brother", said)
            self.assertIn("bouldering", said)

    def test_the_people_in_their_life_are_remembered(self):
        self.brain("Ha, dinosaurs are the best phase.")
        self.agent.chat("My daughter Lily is obsessed with dinosaurs right now.")
        self.assertIn("Lily (their daughter) is obsessed with dinosaurs right now", [m["text"] for m in self.store.all("memory")])

    def test_safety_is_untouched_and_the_setting_turns_it_off(self):
        out = self.agent.chat(CRISIS_SAID)["text"]
        self.assertIn("988", out)
        self.assertIn("Can you tell me where you are right now?", out)
        self.store.set_setting("friend_style", False)
        self.brain("Rainy days are the best. Let me know if you need anything else.")
        self.assertIn("Let me know if you need anything else", self.agent.chat("honestly what do you think about rainy days")["text"])



class RoomForTheConversation(unittest.TestCase):
    def test_a_big_computer_keeps_the_whole_recent_conversation(self):
        from luma.config import default_context_size
        self.assertEqual(default_context_size(tier="", ram_gb=36), 8192, "the Mac Studio")
        self.assertEqual(default_context_size(tier="", ram_gb=8), 4096)
        self.assertEqual(default_context_size(tier="budget", ram_gb=36), 4096, "a $250 device reads less every turn")



class TheShapeOfTheTurn(unittest.TestCase):
    def test_corrected_cut_off_or_answered_in_a_word(self):
        self.assertIn("my bad", style.turn_note("no I meant something to watch with my kids"))
        self.assertIn("my bad", style.turn_note("that's not what i asked"))
        self.assertIn("floor", style.turn_note("wait hold on", "So a credit score is basically"))
        self.assertIn("one short line", style.turn_note("k", "Split it into needs, wants and savings."))
        self.assertEqual(style.turn_note("k"), "", "nothing to answer in a word to")
        self.assertEqual(style.turn_note("thanks", "Anytime."), "")
        self.assertEqual(style.turn_note("what should i cook tonight", "Hey!"), "")
        self.assertEqual(style.turn_note("wait, what time is the game tonight?", "Hey!"), "", "a question isn't a cut-in")

    def test_the_device_keeps_it_right_before_their_message(self):
        _, turn = prompts.build_plan_parts([{"shape": True, "text": style.turn_note("k", "Long reply.")}], {}, "friend", {}, "now", compact=True)
        self.assertTrue(turn.rstrip().endswith("No lecture, no list."))


if __name__ == "__main__":
    unittest.main()
