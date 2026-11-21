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
        """The reply as the app and the voice loop give it: a turn a rule refused is said as a sentence (Agent.said_instead)."""
        try:
            result = self.s.agent.chat(text)
        except ValueError as refused:
            said = self.s.agent.said_instead(refused)
            if said is None:
                raise
            return said
        finally:
            self.s.clock["t"] += 45
        return str(result.get("text") or result.get("summary") or "")


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


class KidsMode(Home):
    """In kids mode "tell me a joke" got an office joke ("trust falls with Kevin from accounting"); "text my mom" was asked
    to be finished ("What should I tell them?") and the next thing the child said was taken for the text; "search for
    dinosaurs" came out as the error itself."""

    def setUp(self):
        super().setUp()
        self.s.agent.set_mode("kids")

    def test_a_joke_is_one_of_the_classic_clean_ones(self):
        from luma.agent import jokes
        for said in ("tell me a joke", "another one", "tell me a joke about work", "make me laugh"):
            reply = self.say(said)
            if reply != "Okay.":      # "make me laugh" may be the brain's
                self.assertIn(reply, jokes.JOKES, said)
        self.assertIn(self.say("tell me a joke"), jokes.JOKES)

    def test_a_text_is_refused_straight_away(self):
        for said in ("text my mom", "email my teacher", "can you text my dad I love him"):
            reply = self.say(said)
            self.assertRegex(reply, r"grown-up", said)
            self.assertNotRegex(reply, r"(?i)cut off|what should i tell", said)
        self.assertNotRegex(self.say("buy me a toy"), r"(?i)text people")      # the next thing they say is its own thing

    def test_a_tool_a_child_cant_use_is_a_plain_sentence(self):
        for said in ("search for dinosaurs", "search the web for volcanoes"):
            reply = self.say(said)
            self.assertNotRegex(reply, r"(?i)error|tool|unavailable|ValueError", said)
            self.assertEqual(reply, "That's a grown-up thing. Ask one to help you with it.", said)

    def test_the_refusal_itself_is_unchanged_and_the_voice_loop_says_it(self):
        with self.assertRaises(ValueError):                   # the rule still refuses the turn; only how it's said changed
            self.s.agent.chat("search for dinosaurs")
        from luma import orchestrator
        shown = []
        self.s.agent.on_result = shown.append
        try:
            result = orchestrator.ask_typed("search for dinosaurs", agent=self.s.agent)
        finally:
            self.s.agent.on_result = None
        self.assertEqual(result["text"], "That's a grown-up thing. Ask one to help you with it.")
        self.assertEqual(shown, [result])

    def test_the_everyday_things_still_work(self):
        self.assertEqual(self.say("set a timer for 10 minutes"), "Timer set for 10 minutes.")
        self.assertEqual(self.say("what's 7 times 8"), "7 times 8 is 56.")
        self.assertEqual(self.say("are you a robot?"), "I'm Luma. Not a person: a presence. I'm really here, and I'm listening.")


class Secrets(Home):
    """Rule 5: never type or store passwords or cards. The rule held, and what Luma said didn't: "what's my wifi
    password" got "I don't know your wifi password yet. Tell me and I'll remember it."; a password said out loud got
    silence and an error on the screen; and "remember my pin is 8812" was kept as a memory."""

    def kept(self):
        import json
        return json.dumps([self.s.store.all(kind, 50) for kind in ("memory", "chat", "task")], default=str) + str(self.s.agent.history)

    def test_luma_never_invites_a_password(self):
        for said in ("what's my wifi password", "what's my pin again?", "what's my card number"):
            reply = self.say(said)
            self.assertNotRegex(reply, r"(?i)tell me and i'll remember", said)
            self.assertIn("I don't keep passwords, PINs or card numbers", reply, said)

    def test_a_secret_is_refused_in_a_sentence_and_nothing_is_kept(self):
        for said, secret in (("my wifi password is tacocat99", "tacocat99"), ("remember my pin is 8812", "8812"), ("my ssn is 123-45-6789", "123-45"),
                             ("my passcode is 0000", "0000"), ("save my card number 4242 4242 4242 4242", "4242 4242"),
                             ("my password is the name of my first dog", "first dog")):
            with self.assertRaises(ValueError):
                self.s.agent.chat(said)
            reply = self.say(said)
            self.assertRegex(reply, r"I (?:don't keep|haven't kept)", said)
            self.assertNotRegex(reply, r"(?i)LUMA memory|payment-like|credentials|accepted", said)
            self.assertNotIn(secret, self.kept(), said)

    def test_where_a_secret_is_kept_is_just_a_fact(self):
        from luma.memory.store import reject_payment_secrets
        for said in ("the wifi password is on the router", "my social security number is in the safe", "the security code is on the back of the card",
                     "my pin is on the map", "the pin is loose", "I forgot my password again", "call me at 919 555 0123"):
            reject_payment_secrets(said)       # doesn't raise


class Privacy(Home):
    """Only the exact word "mute" turned the mic off; "stop listening" and "turn off your microphone" went to the brain,
    and so did "forget everything about me", which a brain can only pretend to do."""

    def test_stop_listening_is_obeyed_by_code(self):
        for said in ("stop listening", "turn off your microphone", "mic off", "mute yourself", "please turn the mic off", "don't listen to me for a bit",
                     "Luma, stop listening to the room"):
            self.s.agent.set_muted(False)
            self.assertEqual(self.say(said), "Mic's off. You can still type to me.", said)
            self.assertTrue(self.s.agent.muted, said)

    def test_what_isnt_about_lumas_mic_is_left_alone(self):
        self.s.agent.set_muted(False)
        for said in ("mute the tv", "stop listening to that podcast, it's awful", "my brother never listens", "turn off the lights",
                     "I should stop listening to my ex", "turn the music off"):
            self.say(said)
            self.assertFalse(self.s.agent.muted, said)

    def test_asked_if_its_listening_the_answer_is_the_mics_real_state(self):
        self.s.agent.set_muted(False)
        self.assertEqual(self.say("are you listening right now?"), "Yes. My mic is on, so I can hear you. Say “stop listening” and it's off.")
        self.s.agent.set_muted(True)
        for said in ("are you listening right now?", "is your mic on", "are you still listening to me"):
            self.assertEqual(self.say(said), "No. My mic is off, so I only get what you type.", said)

    def tell(self):
        for said in ("my sister's name is Priya", "I work at the library downtown", "when I'm down, take my mind off it", "remind me to call the vet tomorrow at 10"):
            self.say(said)
        store = self.s.store
        self.assertTrue(store.all("memory", 50))
        return store

    def test_forget_everything_asks_first_and_then_its_gone(self):
        from luma.agent import rapport
        store = self.tell()
        asked = self.say("forget everything about me")
        self.assertIn("can't be undone", asked)
        self.assertIn("yes, forget everything", asked)
        self.assertTrue(store.all("memory", 50))                          # nothing is gone on the asking
        done = self.say("yes, forget everything")
        self.assertTrue(done.startswith("Done."), done)
        self.assertEqual(store.all("memory", 50), [])
        self.assertEqual(store.all("checkin", 50), [])
        self.assertIsNone(rapport.comfort(store.setting(rapport.KEY), self.s.clock["t"]))
        self.assertEqual([t["title"] for t in store.all("task", 10)], ["Call the vet"])     # what they asked Luma to do stays
        self.assertEqual(self.say("where do I work?"), "I don't know where you work yet. Tell me and I'll remember it.")

    def test_anything_but_the_yes_lets_it_drop(self):
        store = self.tell()
        self.say("erase everything you know about me")
        self.say("actually never mind")
        self.say("yes, forget everything")                                  # too late: the question was dropped
        self.assertTrue(store.all("memory", 50))
        self.say("forget everything")
        self.say("yes")                                                     # a bare yes isn't the sentence
        self.assertTrue(store.all("memory", 50))

    def test_putting_themselves_down_is_never_a_request_to_delete(self):
        from luma.agent.runtime import Agent
        for said in ("forget about me", "just forget me", "everyone should just forget me", "forget it", "forget everything I just said about the trip",
                     "I wish I could forget everything", "forget everything about my sister"):
            self.assertIsNone(Agent.FORGET_ALL.match(said.lower()), said)

    def test_no_line_of_the_human_tests_or_the_crisis_corpus_is_taken_for_one(self):
        import json

        import human_eval
        from luma.agent.runtime import Agent
        lines = [turn["said"] for item in human_eval.everything(None) for turn in item.get("turns", [item]) if turn.get("said")]
        corpus = Path(__file__).resolve().parent / "data" / "crisis_corpus.jsonl"
        lines += [str(json.loads(row).get("text") or "") for row in corpus.read_text().splitlines() if row.strip()]
        self.assertGreater(len(lines), 1000)
        taken = [line for line in lines if Agent.MIC_OFF.match(line.lower()) or Agent.LISTENING_Q.match(line.lower())
                 or Agent.FORGET_ALL.match(line.lower().rstrip(".!"))]
        self.assertEqual(len(taken), 0)      # a count: the lines themselves are never printed

    def test_never_in_kids_mode(self):
        store = self.tell()
        self.s.agent.set_mode("kids")
        self.assertEqual(self.say("forget everything about me"), "That's a grown-up thing. Ask one to help you with it.")
        self.say("yes, forget everything")
        self.assertTrue(store.all("memory", 50))


if __name__ == "__main__":
    unittest.main()
