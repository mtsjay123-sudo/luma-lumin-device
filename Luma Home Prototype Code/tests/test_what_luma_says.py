"""What Luma says itself, read against fresh things people say (Nov 21, 2026). Each of these was wrong in a way a person
never is: "cancel the timer" answered "Saved record not found in this household mode."; "take eggs off the list"
answered "I don't see eggs on your the list."; an unnamed timer was "Your Kitchen timer", and a second one was refused
because the name was taken; "play some rain sounds" on a computer said it was playing and had opinions about it."""
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "scripts")]


class Home(unittest.TestCase):
    def setUp(self):
        import human_eval

        def planner(messages, context, allowed, *args, **kwargs):
            return {"type": "reply", "text": "Okay."}

        self.s = human_eval.Session(planner)

    def tearDown(self):
        self.s.close()

    def say(self, text):
        return self.s.say(text)[0]


class Timers(Home):
    def test_with_no_timer_it_says_so(self):
        for said in ("cancel the timer", "stop the timer", "pause my timer"):
            self.assertEqual(self.say(said), "There's no timer running.", said)

    def test_a_timer_nobody_named_has_no_name_said_back(self):
        self.assertEqual(self.say("set a timer for 12 minutes"), "Timer set for 12 minutes.")
        self.assertRegex(self.say("how long is left on the timer"), r"^1[12] minutes(?: and \d+ seconds)? left on your timer\.$")
        self.assertEqual(self.say("cancel the timer"), "Your 12-minute timer is cancelled.")
        self.assertEqual(self.say("stop the timer"), "There's no timer running.")

    def test_a_second_unnamed_timer_doesnt_trip_over_the_first(self):
        self.assertEqual(self.say("set a timer for 5 minutes"), "Timer set for 5 minutes.")
        self.assertEqual(self.say("set a 5 minute timer"), "Timer set for 5 minutes.")
        self.assertEqual(self.say("set a pasta timer for 8 minutes"), "Your pasta timer is running for 8 minutes.")
        self.assertEqual(self.say("cancel the timer"), "Which one? You have the 5-minute timer, the 5-minute 2 timer and the pasta timer.")
        self.assertEqual(self.say("cancel the pasta timer"), "Your pasta timer is cancelled.")

    def test_one_that_isnt_there_and_one_already_paused(self):
        self.say("set a timer for 20 minutes")
        self.assertEqual(self.say("stop the rice timer"), "I don't see a rice timer running.")
        self.assertEqual(self.say("pause the timer"), "Your 20-minute timer is paused.")
        self.assertEqual(self.say("pause the 20 minute timer"), "It's already paused.")
        self.assertEqual(self.say("resume the timer"), "Your 20-minute timer is running again.")

    def test_no_reply_is_ever_the_inside_of_the_machine(self):
        for said in ("cancel the timer", "set a timer for 3 minutes", "stop the soup timer", "resume the timer", "cancel the timer", "cancel the timer"):
            self.assertNotRegex(self.say(said), r"(?i)record|household mode|acknowledged|\bID\b|Kitchen", said)

    def test_a_timer_that_finished_while_luma_was_off_is_said_in_the_first_person(self):
        import inspect

        from luma.agent import household
        source = inspect.getsource(household)
        self.assertIn("It finished while I was off.", source)
        self.assertNotIn("Luma was not running", source)


class Lists(Home):
    def test_the_list_is_the_one_that_has_it(self):
        self.say("add oat milk and eggs to my shopping list")
        self.say("add call mom to my to-do list")
        self.assertEqual(self.say("take eggs off the list"), "Took eggs off your shopping list.")
        self.assertEqual(self.say("cross call mom off my list"), "Took call mom off your to-do list.")

    def test_otherwise_its_the_one_they_used_last_and_never_a_list_called_the(self):
        self.assertEqual(self.say("add bread to the list"), "Added bread to your shopping list.")       # no lists yet: the shopping list
        self.say("add sunscreen to my packing list")
        self.assertEqual(self.say("add a hat to the list"), "Added hat to your packing list.")
        self.assertEqual(self.say("take pizza off the list"), "I don't see pizza on your packing list.")
        for said in ("take eggs off the list", "add jam to the list", "take jam off my list"):
            self.assertNotIn("your the list", self.say(said))
            self.assertNotIn("your my list", self.say(said))


class Sounds(Home):
    def test_on_a_computer_it_says_what_it_did(self):
        rain = self.say("play some rain sounds")
        self.assertEqual(rain, "Opening rain sounds on YouTube Music.")
        music = self.say("play some lo-fi")
        self.assertTrue(music.startswith("Opening lo-fi on YouTube Music."), music)
        self.assertIn("opinions", music)


class Reminders(Home):
    """"remind me to at 5" was kept as a reminder about "to"; "remind me tomorrow" as a reminder called "What you told me";
    "remind me every Monday at 9 to take out the trash" as a one-off about "every to take out the trash"; and reminders
    were read back as "Take my meds"."""

    def titles(self):
        return sorted(t["title"] for t in self.s.store.all("task", 20))

    def test_nothing_to_do_is_asked_about_not_saved(self):
        self.assertEqual(self.say("remind me to at 5"), "Sure. What should I remind you about?")
        self.assertEqual(self.titles(), [])
        self.assertEqual(self.say("call the vet"), "Got it. I'll remind you to call the vet tomorrow at 5 PM.")
        self.assertEqual(self.titles(), ["Call the vet"])

    def test_remind_me_tomorrow_with_nothing_said_asks_what(self):
        self.assertEqual(self.say("remind me tomorrow"), "Sure. What should I remind you about?")
        self.assertEqual(self.titles(), [])
        self.assertEqual(self.say("pay the water bill"), "Got it. I'll remind you to pay the water bill tomorrow at 9 AM.")

    def test_something_said_first_is_still_what_its_about(self):
        self.assertTrue(self.say("I parked on level 3, remind me later").startswith("Got it."))
        self.assertEqual(self.titles(), ["I parked on level 3"])

    def test_every_in_the_middle_is_a_weekly_task(self):
        self.assertEqual(self.say("remind me every Monday at 9 to take out the trash"), "Done. On Mondays at 9 AM, I'll remind you to take out the trash.")
        self.assertEqual(self.titles(), [])                       # a task that comes round, not a one-off reminder
        self.assertEqual(self.say("what tasks do I have"), "One task: on Mondays at 9 AM, remind you to take out the trash.")
        self.assertEqual(self.say("remind me every day at 8 to take my vitamins"), "Done. Every day at 8 AM, I'll remind you to take your vitamins.")

    def test_read_back_they_are_yours(self):
        self.say("remind me to take my meds at 9pm")
        self.say("remind me about the dentist on Friday")
        self.assertEqual(self.say("what reminders do I have?"), "You've got 2 things: take your meds at 9:00 PM; the dentist on Friday at 9:00 AM.")

    def test_what_isnt_a_schedule_isnt_made_one(self):
        from luma.agent import standing
        for said in ("remind me every now and then to drink water", "remind me to tell everyone about the party", "tell me every detail about your day",
                     "remind me to call each of them at 5"):
            self.assertIsNone(standing.parse(said.lower()), said)


if __name__ == "__main__":
    unittest.main()
