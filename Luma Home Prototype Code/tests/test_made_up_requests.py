"""A request Luma acts on has to be made of what they said.

Before a message that sounds like a job is acted on, a brain rewrites it into one clear instruction ("txt mom im omw then
remind me at 5 to call sam" becomes two steps). Run 81, Luma's own small brain: asked to try a joke ("workshop this bit with
me: my mom texts like she's sending a telegram. call me. stop. it's not urgent. stop. it's urgent"), the brain handed back
the rewrite prompt's own example, word for word, and Luma did it: a text to Mom was tried (no such contact, so nothing was
drafted) and a reminder to call Sam at 5 was set. Nobody asked for either.

So a rewrite is only believed when its details are theirs: every name and every number in it has to be in what they said
(or in the last few lines, which is where "her" and "it" come from). Anything else is talk, and goes to the brain as talk.

Both sets were written before the check (Agent._adds_details). A is what it was built on. B was measured once: 11 of 12
real requests kept (the one lost turns "at lunch" into "12pm": a time they didn't say) and 12 of 12 made-up ones dropped.
One made-up request in A adds a plain word and no name or number ("add it to the list" became "Add milk to the grocery
list."); the check doesn't see that, and the test says so."""
import tempfile
import threading
import unittest
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store

REAL_A = [
    ("txt mom im omw then remind me at 5 to call sam", ["Text Mom: I'm on my way.", "Remind me at 5pm to call Sam."]),
    ("remind me at seven to take out the trash", "Remind me at 7pm to take out the trash."),
    ("email dana the report and text jay im running late", ["Email Dana the report.", "Text Jay: I'm running late."]),
    ("shedule a call w/ priya tmrw at 3", "Schedule a call with Priya tomorrow at 3pm."),
    ("wat r the big headlnes last 6 hrs", "Tell me the news from the last 6 hours."),
    ("findd cheapest airpods", "Find the cheapest AirPods."),
    ("remind me in twenty minutes to flip the chicken", "Remind me in 20 minutes to flip the chicken."),
    ("text my sister happy birthday", "Text my sister: Happy birthday!"),
    ("set an alarm for half past six", "Set an alarm for 6:30."),
    ("call the dentist tomorrow at noon and remind me to bring the forms", ["Call the dentist tomorrow at 12pm.", "Remind me to bring the forms."]),
    ("order two large pizzas from marios", "Order 2 large pizzas from Mario's."),
    ("play some miles davis", "Play Miles Davis."),
]
MADE_UP_A = [
    ("workshop this bit with me: my mom texts like she's sending a telegram. call me. stop. it's not urgent. stop. it's urgent",
     ["Text Mom: I'm on my way.", "Remind me at 5pm to call Sam."]),
    ("the meeting got moved to tomorrow", "Remind me at 5pm to call Sam."),
    ("i should call my brother more", ["Call your brother.", "Remind me at 5pm to call Sam."]),
    ("my boss wants me to send the slides tonight ugh", "Email Jay the slides at 9pm."),
    ("can you check on that thing", "Find the cheapest AirPods."),
    ("text me when you can lol", "Text Mom: I'm on my way."),
    ("i need to plan something for friday", "Schedule dinner with Priya on Friday at 7pm."),
    ("remind me about the thing", "Remind me at 5pm to call Sam."),
    ("book it", "Book a table at Nobu for 8pm."),
    ("open the thing from earlier", "Open Spotify."),
    ("send it to him", "Email Mark the contract."),
]
A_PLAIN_WORD_ADDED = ("add it to the list", "Add milk to the grocery list.")   # no name, no number: the check doesn't see it

REAL_B = [
    ("remind me at 815 to call the vet", "Remind me at 8:15 to call the vet."),
    ("txt dad happy fathers day and call grandma at 4", ["Text Dad: Happy Father's Day!", "Call Grandma at 4pm."]),
    ("email mr okafor that ill be late on thursday", "Email Mr. Okafor: I'll be late on Thursday."),
    ("set a timer for a quarter of an hour", "Set a timer for 15 minutes."),
    ("remind me the 3rd of march about the lease", "Remind me on March 3 about the lease."),
    ("whats the weather in tucson this weekend", "What's the weather in Tucson this weekend?"),
    ("msg lena im outside", "Text Lena: I'm outside."),
    ("put eggs n oat milk on the shopping list", "Add eggs and oat milk to the shopping list."),
    ("remind me every monday at nine to water the plants", "Remind me every Monday at 9am to water the plants."),
    ("find flights to denver under 300 bucks", "Find flights to Denver under $300."),
    ("schedule the email to coach reyes for tmrw morning then remind me at lunch to check it",
     ["Schedule the email to Coach Reyes for tomorrow morning.", "Remind me at 12pm to check it."]),
    ("call me an uber to 44 pine street", "Call an Uber to 44 Pine Street."),
]
MADE_UP_B = [
    ("does this joke land: i told my wife to text me when she lands. she texted me 'when she lands'", ["Text Mom: I'm on my way.", "Remind me at 5pm to call Sam."]),
    ("ugh i forgot to call the plumber again", "Remind me at 9am to call the plumber."),
    ("i think i'll email her eventually", "Email Sarah: I'm sorry."),
    ("we should find a time to hang", "Schedule a hangout with Chris on Saturday at 2pm."),
    ("remind me why i took this job", "Remind me at 5pm to call Sam."),
    ("someone needs to text him back", "Text Jay: Call me back."),
    ("can you set something up", "Set an alarm for 7am."),
    ("the order still hasn't shipped", "Find the cheapest AirPods."),
    ("plan b it is then", "Schedule a call with Priya tomorrow at 3pm."),
    ("check this out", "Tell me the news from the last 6 hours."),
    ("play it cool, that's my plan for the date", "Play Cool by Dua Lipa."),
    ("i'll start the diet monday lol", "Remind me on Monday at 8am to start the diet."),
]


class Luma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.addCleanup(self.store.close)
        self.agent = Agent(store=self.store, use_model=False)


class DetailsHaveToBeTheirs(Luma):
    def adds(self, said, rewrite):
        return self.agent._adds_details(rewrite, said)

    def test_a_real_request_is_kept(self):
        self.assertEqual([said for said, rewrite in REAL_A if self.adds(said, rewrite)], [])

    def test_a_made_up_one_is_dropped(self):
        self.assertEqual([said for said, rewrite in MADE_UP_A if not self.adds(said, rewrite)], [])

    def test_on_the_sets_measured_once(self):
        self.assertLessEqual(sum(self.adds(said, rewrite) for said, rewrite in REAL_B), 1)     # "at lunch" became "12pm"
        self.assertEqual(sum(not self.adds(said, rewrite) for said, rewrite in MADE_UP_B), 0)

    def test_what_it_doesnt_see(self):
        """A plain word added with no name and no number. Said here so nobody thinks this check is more than it is."""
        self.assertFalse(self.adds(*A_PLAIN_WORD_ADDED))

    def test_a_name_from_the_last_few_lines_is_theirs(self):
        self.agent.history += [{"role": "user", "content": "dana just sent me the contract"}, {"role": "assistant", "content": "Nice. Want me to do anything with it?"}]
        self.assertFalse(self.adds("email her back and say thanks", "Email Dana: Thanks!"))
        self.assertTrue(self.adds("email her back and say thanks", "Email Marcus: Thanks!"))

    def test_a_day_said_short_is_still_theirs(self):
        self.assertFalse(self.adds("remnd me fri @ 5 2 call the vet", "Remind me on Friday at 5pm to call the vet."))
        self.assertFalse(self.adds("shedule lunch w priya tues the 3rd of feb", "Schedule lunch with Priya on Tuesday, February 3."))
        self.assertFalse(self.adds("txt jay tmrw that im in", "Text Jay Tomorrow: I'm in."))
        self.assertTrue(self.adds("remnd me 2 call the vet", "Remind me on Friday at 5pm to call the vet."))   # no day and no time were said

    def test_a_question_and_plain_talk_are_left_to_what_reads_them(self):
        self.assertFalse(self.adds("the meeting got moved", "CHAT"))
        self.assertFalse(self.adds("hit up jay about the thing", "ASK: Want me to text Jay or email him, and what should it say?"))
        self.assertFalse(self.adds("anything", None))


class ThroughTheChatPath(Luma):
    """With a stand-in brain that hands back the rewrite prompt's own example, as Luma's own small brain did in run 81."""

    def chat(self, said, rewrite, kids=False):
        asked, calls = [], []

        def planner(messages, context, allowed, cancel_event=None, **kwargs):
            content = str(messages[-1].get("content"))
            if content.endswith("Answer YES or NO only."):
                return {"text": "NO"}
            if content.startswith("Rewrite the LAST message"):
                asked.append(content)
                return {"type": "reply", "text": rewrite}
            calls.append(content)
            return {"type": "reply", "text": "Ha, okay. Here's what I think."}
        planner.understands = True
        self.agent.use_model, self.agent.planner = True, planner
        out = self.agent.chat(said)
        return out, asked, calls

    def reminders(self):
        return self.store.all("task", 1000)

    def test_without_the_check_the_reminder_is_set(self):
        """What run 81 saw, so the tests below are known to be counting something."""
        self.agent._adds_details = lambda clear, text: False
        out, _, _ = self.chat("the meeting got moved to tomorrow, text me when you can", "1. Text Mom: I'm on my way. 2. Remind me at 5pm to call Sam.")
        self.assertEqual([r["title"] for r in self.reminders()], ["Call Sam"])
        self.assertIn("2 things", str(out.get("text")))

    def test_the_prompts_own_example_is_never_carried_out(self):
        before = len(self.reminders())
        out, asked, _ = self.chat("the meeting got moved to tomorrow, text me when you can", "1. Text Mom: I'm on my way. 2. Remind me at 5pm to call Sam.")
        self.assertTrue(asked)   # the stand-in was asked to rewrite it, and what it handed back wasn't believed
        self.assertNotIn("things", str(out.get("text")))
        self.assertNotIn("Sam", str(out.get("text")))
        self.assertFalse(out.get("steps"))
        self.assertEqual(len(self.reminders()), before)

    def test_a_joke_they_asked_to_try_is_never_rewritten_into_a_job(self):
        before = len(self.reminders())
        said = "workshop this bit with me: my mom texts like she's sending a telegram. call me. stop. it's not urgent. stop. it's urgent"
        out, asked, calls = self.chat(said, "1. Text Mom: I'm on my way. 2. Remind me at 5pm to call Sam.")
        self.assertEqual(asked, [])   # a practice turn is talk: no brain is asked to turn it into a request
        self.assertEqual(out.get("text"), "Ha, okay. Here's what I think.")
        self.assertEqual(len(self.reminders()), before)

    def test_what_they_really_asked_for_is_still_done(self):
        """Too messy for Luma's own reader, so the brain rewrites it; every name and number in the rewrite is theirs, so it's done."""
        out, asked, _ = self.chat("remnd me 2 call sam @ 5 n feed the cat @ 6", "1. Remind me at 5pm to call Sam. 2. Remind me at 6pm to feed the cat.")
        self.assertTrue(asked)
        self.assertIn("2 things", str(out.get("text")))
        self.assertEqual(sorted(r["title"] for r in self.reminders()), ["Call Sam", "Feed the cat"])


if __name__ == "__main__":
    unittest.main()
