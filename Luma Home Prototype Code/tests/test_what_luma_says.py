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


class SpeakerCommands(Home):
    """Read Nov 21, 2026, with a stand-in brain: things anyone says to a speaker that went to the brain (which can only say
    it did them) or got a line from somewhere else. "wake me up in 20 minutes", "do not disturb until 8", "turn it all
    the way up", "what's my volume" and "snooze" with nothing ringing went to the brain; "what's on my list" answered
    "Your my list is empty."; "how do I turn you off" answered "Sure, let's do it step by step. Open my browser."; "what
    did I spend this month" answered "Show me. Tap the picture button next to where you type and pick a photo.\" Also "cancel
    the meds reminder", which went to the brain."""

    BRAIN = "Okay."   # what the stand-in brain says: seeing it means the line was left to the brain

    def test_wake_me_up_in_a_while_sets_an_alarm(self):
        self.assertRegex(self.say("wake me up in 20 minutes"), r"^Alarm set for \d{1,2}:\d{2} [AP]M, 20 minutes from now\.$")
        self.assertRegex(self.say("what alarms do I have"), r"^One alarm: ")
        self.assertRegex(self.say("set an alarm for an hour from now"), r"^Alarm set for .*, (?:an|1) hour from now\.$")
        self.assertRegex(self.say("wake me in an hour and a half"), r"^Alarm set for .*from now\.$")
        rows = [r for r in self.s.agent.athome._rows("alarm") if r.get("on")]
        self.assertEqual(len(rows), 3)
        now = self.s.clock["t"]
        self.assertTrue(all(now < r["next"] < now + 2 * 3600 for r in rows))

    def test_the_four_the_second_set_missed(self):
        """Left as misses when the second set was measured (18 of 24), fixed afterwards: they're built on now."""
        self.assertRegex(self.say("alarm in 10 minutes"), r"^Alarm set for .*, 10 minutes from now\.$")
        self.s.at({"day": 3, "time": "22:15"})
        self.assertEqual(self.say("don't disturb me until 9"), "Do not disturb until 9 AM. Alarms and timers still go off.")
        self.assertEqual(self.say("volume all the way down"), "Quieter: 1.")
        self.say("remind me to take the trash out tomorrow at 7pm")
        self.assertEqual(self.say("never mind the trash reminder"), "Done. I won't remind you to take the trash out.")
        for said in ("never mind, I figured it out", "forget about it", "the alarm in my building went off for 20 minutes", "don't disturb the cat"):
            self.assertEqual(self.say(said), self.BRAIN, said)

    def test_an_alarm_in_a_while_never_rings_early(self):
        before = self.s.clock["t"]
        self.say("wake me up in 5 minutes")
        row = [r for r in self.s.agent.athome._rows("alarm") if r.get("on")][0]
        self.assertGreaterEqual(row["next"], before + 5 * 60)
        self.assertLess(row["next"], before + 6 * 60 + 1)

    def test_do_not_disturb_until_a_time(self):
        self.s.at({"day": 3, "time": "22:15"})
        self.assertEqual(self.say("do not disturb until 8"), "Do not disturb until 8 AM. Alarms and timers still go off.")
        self.assertEqual(self.say("do not disturb off"), "Do not disturb is off. I'm around.")
        self.assertEqual(self.say("do not disturb until morning"), "Do not disturb until 7 AM. Alarms and timers still go off.")
        self.assertEqual(self.say("do not disturb until 6:30 am"), "Do not disturb until 6:30 AM. Alarms and timers still go off.")
        self.assertRegex(self.say("do not disturb for 2 hours"), r"^Do not disturb until 12:\d\d AM\.")

    def test_volume_all_the_way_and_asked_any_way(self):
        self.assertEqual(self.say("turn it all the way up"), "Louder: 10.")
        self.assertEqual(self.say("what's my volume"), "Volume's at 10.")
        self.assertEqual(self.say("how loud are you"), "Volume's at 10.")
        self.assertEqual(self.say("max volume"), "That's as loud as I go.")
        self.assertEqual(self.say("turn it all the way down"), "Quieter: 1.")
        self.assertEqual(self.say("what volume are you on"), "Volume's at 1.")

    def test_snooze_with_nothing_ringing(self):
        self.assertEqual(self.say("snooze"), "Nothing's ringing.")
        self.assertEqual(self.say("five more minutes"), self.BRAIN)   # that one's talk unless something just rang

    def test_whats_on_my_list_is_the_list_they_used_last(self):
        self.assertEqual(self.say("what's on my list"), "Your shopping list is empty.")
        self.say("add batteries to my packing list")
        self.assertEqual(self.say("what's on my list"), "One thing on your packing list: batteries.")
        self.assertEqual(self.say("read me the list"), "One thing on your packing list: batteries.")
        for said in ("what's on my list", "what's on the list", "show me my list", "read our list"):
            self.assertNotRegex(self.say(said), r"\b(?:my|the|our) list\b", said)

    def test_add_something_just_after_using_a_list_goes_on_it(self):
        self.assertEqual(self.say("add milk"), self.BRAIN)   # with no list in use, it's talk
        self.say("add eggs to the shopping list")
        self.assertEqual(self.say("add milk"), "Added milk to your shopping list.")
        self.assertEqual(self.say("add oat milk and bananas too"), "Added oat milk and bananas to your shopping list.")
        for said in ("add it up for me", "add me to the group chat", "add that to what I said before", "add more detail", "add insult to injury",
                     "add fuel to the fire"):
            self.assertNotIn("to your shopping list", self.say(said), said)
        self.s.clock["t"] += 3600
        self.assertEqual(self.say("add salt"), self.BRAIN)   # an hour later it's talk again

    def test_asked_how_to_turn_it_off_it_says_how(self):
        self.s.agent.set_muted(False)
        for said in ("how do I turn you off", "how do I shut you down?", "can I turn you off", "do you have an off switch", "how can I switch you off at night"):
            reply = self.say(said)
            self.assertIn("unplug me", reply, said)
            self.assertNotIn("browser", reply, said)
        self.assertFalse(self.s.agent.muted)   # asking how isn't asking for it: "can I turn you off" used to turn the mic off
        for said in ("how do I turn off the lights", "how do I turn this feeling off", "can I turn the tv off", "how do I turn my brain off at night"):
            reply = self.say(said)
            self.assertNotIn("unplug me", reply, said)
            self.assertNotIn("step by step", reply, said)   # "my brain" isn't Luma's: it got the walk-through for Luma's brain setting
        self.assertFalse(self.s.agent.muted)

    def test_a_question_about_money_is_never_a_photo(self):
        for said in ("what did I spend this month", "what did I spend on food this month", "how much have I spent this week"):
            self.assertNotIn("picture button", self.say(said), said)
        self.assertIn("picture button", self.say("look at this photo"))
        self.assertIn("picture button", self.say("read this receipt"))

    def test_no_line_of_the_human_tests_or_the_crisis_corpus_is_taken_for_one(self):
        import json

        import human_eval
        from luma.agent import athome
        from luma.agent.runtime import Agent
        lines = [turn["said"] for item in human_eval.everything(None) for turn in item.get("turns", [item]) if turn.get("said")]
        corpus = Path(__file__).resolve().parent / "data" / "crisis_corpus.jsonl"
        lines += [str(json.loads(row).get("text") or "") for row in corpus.read_text().splitlines() if row.strip()]
        self.assertGreater(len(lines), 1000)
        taken = [line for line in lines if athome.ALARM_IN.match(line.lower()) or Agent.TURN_OFF.match(line.lower())
                 or (athome.VOLUME.match(line.lower()) and (athome.VOLUME.match(line.lower())["max"] or athome.VOLUME.match(line.lower())["min"]))
                 or (athome.DND.match(line.lower()) and athome.DND.match(line.lower())["clock"])]
        self.assertEqual(len(taken), 0)      # a count: the lines themselves are never printed


class CancellingAReminder(Home):
    """"cancel the meds reminder" went to the brain, which has no way to do it and says it did. Read by code now: the one
    that matches is cancelled and named, more than one is asked about, and all of them at once is asked about first."""

    def setUp(self):
        super().setUp()
        for said in ("remind me to take my meds at 9pm", "remind me to call the vet tomorrow at 10", "remind me about the dentist on friday at 3",
                     "remind me to take the trash out tomorrow at 7pm"):
            self.say(said)

    def left(self):
        return sorted(r["title"].lower() for r in self.s.agent.store.all("task") if not r["done"])

    def test_the_one_they_name_is_cancelled_and_said_back_as_theirs(self):
        self.assertEqual(self.say("cancel the trash reminder"), "Done. I won't remind you to take the trash out.")
        self.assertEqual(self.say("delete my reminder to call the vet"), "Done. I won't remind you to call the vet.")
        self.assertEqual(self.say("get rid of the dentist reminder"), "Done. I won't remind you about the dentist.")
        self.assertEqual(self.left(), ["take my meds"])
        self.assertEqual(self.say("cancel the reminder"), "Done. I won't remind you to take your meds.")
        self.assertEqual(self.say("what are my reminders"), "You don't have any reminders right now.")

    def test_one_that_isnt_there_and_one_that_could_be_two(self):
        self.assertEqual(self.say("cancel the haircut reminder"), "I don't see a reminder about haircut.")
        self.assertRegex(self.say("cancel the take reminder"), r"^Which one\? You have: take your meds at 9:00 PM; take the trash out tomorrow at 7:00 PM\.$")
        self.assertRegex(self.say("cancel the reminder"), r"^Which one\? You have: ")
        self.assertEqual(len(self.left()), 4)

    def test_all_of_them_is_asked_about_first(self):
        self.assertRegex(self.say("cancel all my reminders"), r"^That's all 4: .* Say “yes, cancel them” and they're gone\.$")
        self.assertEqual(len(self.left()), 4)
        self.assertEqual(self.say("yes, cancel them"), "Done. All 4 are cancelled.")
        self.assertEqual(self.left(), [])
        self.assertEqual(self.say("delete all my reminders"), "You don't have any reminders.")

    def test_anything_but_a_yes_lets_it_drop(self):
        self.say("cancel all my reminders")
        self.say("actually what's the weather in Boston")
        self.say("yes")
        self.assertEqual(len(self.left()), 4)

    def test_one_that_comes_round_every_week(self):
        self.assertEqual(self.say("remind me to call Mom every Sunday at 6"), "Done. On Sundays at 6 PM, I'll remind you to call Mom.")
        self.assertEqual(self.say("cancel the call mom reminder"), "Stopped. I won't remind you to call Mom anymore.")
        self.assertEqual(len(self.left()), 4)   # "call the vet" shares a word and was cancelled in its place, before this was fixed

    def test_only_some_of_the_words_is_never_enough_to_cancel(self):
        self.assertEqual(self.say("cancel the call grandma reminder"), "I don't see one about call grandma. You have: call the vet tomorrow at 10:00 AM.")
        self.assertEqual(len(self.left()), 4)

    def test_an_hour_said_bare_is_the_one_people_mean(self):
        from luma.agent import standing
        for said, at in (("remind me to call mom every sunday at 6", "18:00"), ("every friday at 5 remind me to submit my timesheet", "17:00"),
                         ("every sunday at 6:30 remind me to call dad", "18:30"), ("wake me up every day at 6", "06:00"), ("every morning at 6 tell me the news", "06:00"),
                         ("every weekday at 8, tell me the weather", "08:00"), ("every day at 3am remind me to check the oven", "03:00"),
                         ("every night at 9 remind me to take my meds", "21:00"), ("every day at 12 remind me to eat", "12:00")):
            self.assertEqual(standing.parse(said)["at"], at, said)

    def test_what_isnt_cancelling_a_reminder_is_left_alone(self):
        for said in ("that was a good reminder", "thanks for the reminder", "I need a reminder of why I even try", "cancel my appointment", "stop reminding me of him",
                     "delete that", "remove the reminder app from my phone"):
            self.assertNotRegex(self.say(said), r"^(?:Done\.|Which one|I don't see a reminder|You don't have any reminders|That's all)", said)
        self.assertEqual(len(self.left()), 4)

    def test_no_line_of_the_human_tests_or_the_crisis_corpus_is_taken_for_one(self):
        import json

        import human_eval
        from luma.agent.runtime import Agent
        lines = [turn["said"] for item in human_eval.everything(None) for turn in item.get("turns", [item]) if turn.get("said")]
        corpus = Path(__file__).resolve().parent / "data" / "crisis_corpus.jsonl"
        lines += [str(json.loads(row).get("text") or "") for row in corpus.read_text().splitlines() if row.strip()]
        self.assertGreater(len(lines), 1000)
        self.assertEqual(sum(1 for line in lines if Agent.REMINDER_OFF.match(line.lower())), 0)      # a count: never printed


class TalkIsNeverACommand(unittest.TestCase):
    """Ordinary things people say, read with a stand-in brain (Nov 21, 2026). Each line here got an answer from Luma's own
    code as if it were a command: a forecast for "this weather is making me so sad", the feature list for "what are you up
    to", the mic turned off for "mute button for my thoughts please", a memory saved for "remember the place with the
    terrible karaoke", "Opening along with me here on YouTube Music" for "play along with me here".

    Four sets of 60 lines, each written after the fixes before it and measured once. Wrongly answered by code, before ->
    after the fixes that existed when the set was written: 4 -> 0 (built on), 14 -> 8, 11 -> 11 (fixing line by line
    didn't carry over), 10 -> 6 (guards on each path did: said in passing, a reading's own words, sayings). The lines
    below are the ones that were wrong in any set; all are left to the brain now, which is no number at all."""

    TAKEN = ["the weather has been matching my mood", "remember when we talked about my brother", "what are you up to",
             "the cold weather makes my knees ache", "I can't stand this weather anymore", "remember that time I locked myself out", "remember how we used to stay up talking",
             "do you remember when I got the job", "what do you do when I'm not here", "turn that frown upside down lol", "forget it, it's not important",
             "search me, I have no idea why she left", "tell my why I keep doing this to myself", "show me a person who has it together",
             "I need an umbrella for my life lol", "I'm going to snow myself in and hibernate", "the forecast for my love life is bleak",
             "remember the summer we drove to the coast", "remember how bad I was at this a year ago", "what do you do all night", "where do I even start with my taxes",
             "mute button for my thoughts please", "forget him, honestly", "play along with me here", "text me when you're home, she used to say", "set in my ways, I guess",
             "what's my problem honestly", "turn the page, they say", "remember the place with the terrible karaoke", "remember my old apartment, the one with the leak",
             "do you remember how nervous I was", "play it by ear, that's my plan", "read the room, I told myself", "what's my deal with unavailable people",
             "is this what thirty feels like", "connect the dots, he's gone", "upgrade my life, please", "this weather is making me so sad", "I hate cold weather",
             "the weather was perfect for the funeral"]
    # what the same code must still do when it's asked (the reply starts this way)
    ASKED = [("play some jazz", "Opening jazz on YouTube Music."), ("text my mom I'll be late", "What's your mom's name and number?"),
             ("remember that I parked on level 3", "Got it"), ("remember my sister's birthday is May 2", "Got it"), ("forget that", "There was nothing new to forget."),
             ("what can you do", "Here's what I can do"), ("what do you do", "Here's what I can do"), ("open the news page", "Here's the news."),
             ("what do you remember about me", "Not much yet."), ("take me 2 my goalz", "Nothing running on its own yet."), ("how do I pair my device", "Sure, let's do it step by step."),
             ("stop listening", "Mic's off."), ("give me a minute", "Take your time. I'm here."), ("hold on a sec", "Take your time. I'm here."),
             ("where are my keys", "You haven't told me where your keys are.")]

    @staticmethod
    def said(line):
        import human_eval

        def planner(messages, context, allowed, *args, **kwargs):
            return {"type": "reply", "text": "Okay."}

        s = human_eval.Session(planner)
        try:
            result = s.agent.chat(line)
            return str(result.get("text") or result.get("summary") or "")
        finally:
            s.close()

    def test_every_line_that_was_taken_is_left_to_the_brain(self):
        wrong = [(line, self.said(line)) for line in self.TAKEN]
        self.assertEqual([(line, reply) for line, reply in wrong if reply != "Okay."], [])

    def test_what_is_asked_is_still_done(self):
        for line, starts in self.ASKED:
            self.assertTrue(self.said(line).startswith(starts), (line, self.said(line)))

    def test_the_word_weather_alone_isnt_a_question(self):
        from luma.skills import weather
        for line in ("what's the weather", "weather", "weather in tokyo", "how's the weather today", "is it going to rain tomorrow", "do i need a jacket",
                     "what's the weather, I hate not knowing", "check the weather for me", "tomorrow's weather", "will it snow tonight"):
            self.assertTrue(weather.wants(line), line)
        for line in ("this weather is making me so sad", "i hate cold weather", "the weather was perfect for the funeral", "i love this weather",
                     "the weather has been matching my mood", "the forecast for my love life is bleak", "I need an umbrella for my life lol",
                     "I'm going to snow myself in and hibernate", "nice weather we're having", "i've been under the weather all week"):
            self.assertFalse(weather.wants(line), line)

    def test_said_in_passing_and_sayings(self):
        from luma.agent import runtime
        for line in ("turn the page, they say", "set in my ways, I guess", "forget him, honestly", "text me when you're home, she used to say",
                     "read the room, I told myself", "find a hobby, they said", "booked and busy, allegedly"):
            self.assertTrue(runtime.said_in_passing(line), line)
        for line in ("play some jazz", "text my mom I'll be late", "what's the weather", "remind me to call the vet at 3", "they say it's going to rain",
                     "honestly just play something", "open the news page", "I guess"):
            self.assertFalse(runtime.said_in_passing(line), line)
        for line in ("connect the dots, he's gone", "upgrade my life, please", "play it by ear, that's my plan"):
            self.assertTrue(runtime.SAYINGS.search(line), line)

    def test_a_sure_reading_needs_a_word_of_its_own(self):
        from luma.agent.runtime import Agent
        self.assertIn("email", Agent._words_of("connect_email"))
        self.assertIn("news", Agent._words_of("open_news"))
        for intent in Agent.FIXED_SUBJECT:
            self.assertTrue(Agent._words_of(intent), intent)
            self.assertFalse(Agent._words_of(intent) & {w[:5] for w in ("set", "turn", "open", "page", "show", "get")}, intent)

    def test_a_whole_question_that_ends_in_like_isnt_cut_off(self):
        from luma.agent import understanding
        for line in ("is this what thirty feels like", "do you know what that sounds like", "I wonder what her new place looks like"):
            self.assertIsNone(understanding.cut_off(line), line)
        self.assertIsNotNone(understanding.cut_off("remind me to"))
        self.assertIsNotNone(understanding.cut_off("so I was thinking, like"))


if __name__ == "__main__":
    unittest.main()
