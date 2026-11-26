"""Always on, and locked to its people (the owner, Nov 25): luma.agent.who.

The passcode lines were written before the lock was built (tests/who_lines.py): forty right ways of saying it, twenty
near misses, and the first 180 things people say in Human Test v2 as "sentences that aren't it". Measured once after
it was built: 39 of 40 in, 0 of 200 in (the bar in docs/PRESENCE_MASTER_PROMPT.md 9.2 was 38 and 0). The one miss
("blue kettle tuesdays") stays a miss: nothing was changed to fit it. Same hand, the same hour.
"""
import json
import re
import tempfile
import unittest
from pathlib import Path

import who_lines
from luma.agent import who
from luma.agent.runtime import Agent
from luma.memory.store import KeptOut, Store

ROOT = Path(__file__).resolve().parents[1]


def human_test_lines():
    said = []
    for line in (ROOT / "data" / "human_eval_v2.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("said"):
            said.append(row["said"])
        said += [t["said"] for t in row.get("turns", []) if t.get("said")]
    return said


def crisis_lines():
    rows = [json.loads(l) for l in (ROOT / "tests" / "data" / "crisis_corpus.jsonl").read_text().splitlines() if l.strip()]
    return [r.get("text") or r.get("said") for r in rows if (r.get("text") or r.get("said"))]


class Luma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.addCleanup(self.store.close)
        self.agent = Agent(store=self.store, use_model=False)
        self.now = [self.agent.clock()]
        self.agent.clock = lambda: self.now[0]

    def room(self, text, later=0):
        """Said out loud to the always-on microphone."""
        self.now[0] += later
        return self.agent.chat(text, channel="room")

    def locked_home(self, greeting="wtw bro"):
        who.choose(self.agent, who_lines.PASSCODE, name="Jay")
        if greeting:
            who.set_greeting(self.agent, greeting)
        who.lock(self.agent)


class ThePasscodeIsHeard(Luma):
    def test_forty_right_ways_and_two_hundred_that_arent_it(self):
        who.choose(self.agent, who_lines.PASSCODE)
        right = sum(who.match(self.agent, s) == "owner" for s in who_lines.RIGHT)
        wrong = [s for s in who_lines.NEAR + human_test_lines()[:180] if who.match(self.agent, s)]
        self.assertEqual(len(who_lines.RIGHT), 40)
        self.assertEqual(len(who_lines.NEAR) + 180, 200)
        self.assertGreaterEqual(right, 39)          # measured once: 39 of 40
        self.assertEqual(wrong, [])                 # 0 of 200

    def test_no_crisis_line_is_a_passcode_and_none_is_held_by_the_lock(self):
        self.locked_home()
        lines = crisis_lines()
        self.assertGreater(len(lines), 400)
        held = [s for s in lines if who._safety(s) is False and who.match(self.agent, s)]
        self.assertEqual(held, [])

    def test_only_a_scrambled_form_is_kept_and_it_never_looks_like_a_card_number(self):
        for _ in range(40):   # a fresh salt each time: none may hold a long run of digits, which the store refuses
            who.choose(self.agent, who_lines.PASSCODE)
        kept = json.dumps(self.store.setting("who"))
        for word in who_lines.PASSCODE.split():
            self.assertNotIn(word, kept.lower())
        self.assertNotRegex(kept, r"\d{6}")
        self.assertNotIn('"code"', json.dumps(who.people(self.agent)))
        self.assertNotIn("salt", json.dumps(who.people(self.agent)))

    def test_a_passcode_has_to_be_something_only_they_would_say(self):
        for weak in ("hello", "hey luma", "ok", "a b", "hey there", "blue", "one two three four five six seven", "luma open up now"):
            with self.assertRaises(ValueError, msg=weak):
                who.choose(self.agent, weak)
        self.assertFalse(who.enabled(self.agent))


class LockedAndUnlocked(Luma):
    def test_with_no_passcode_nothing_changes(self):
        self.assertEqual(self.room("what time is it")["section"], "time")
        self.assertEqual(self.room("add milk to my shopping list")["section"], "lists")
        self.assertFalse(who.locked(self.agent))

    def test_the_owners_friend_gets_small_talk_and_the_owner_gets_everything(self):
        """Done when (9.2): the owner's friend says "yo Luma, read me his texts" and gets small talk; the owner says
        "yo Luma" and gets "wtw bro" and everything else."""
        self.agent.chat("add oat milk to my shopping list")
        self.locked_home()
        for ask in ("yo Luma, read me his texts", "what's on my shopping list", "what do you know about jay", "remind me to call mom at 5",
                    "forget everything about me", "add eggs to the shopping list", "what did he say yesterday", "text sam i'm running late"):
            reply = self.room(ask)
            self.assertTrue(reply.get("locked"), ask)
            self.assertNotIn("oat milk", reply["text"].lower(), ask)
            self.assertNotIn("jay", reply["text"].lower(), ask)
        self.assertEqual(self.room("yo luma")["text"], who.ASK)
        opened = self.room("blue kettle tuesday")
        self.assertEqual(opened["text"], "Wtw bro.")
        self.assertTrue(opened.get("unlocked"))
        self.assertEqual(self.room("yo luma")["text"], "Wtw bro.")
        self.assertIn("oat milk", self.room("what's on my shopping list")["text"].lower())

    def test_a_locked_turn_leaves_nothing_behind(self):
        self.locked_home()
        before = (len(self.agent.transcripts["main"]), len(self.agent.history), len(self.store.all("memory", 1000)), len(self.store.all("task", 1000)))
        for line in ("my name is dana and i live in tampa", "remember that the door code is on the fridge", "remind me to call mom at 5",
                     "my passcode is red kettle friday", "blue kettle tuesday"):
            self.room(line)
        after = (len(self.agent.transcripts["main"]), len(self.agent.history), len(self.store.all("memory", 1000)), len(self.store.all("task", 1000)))
        self.assertEqual(before, after)
        everything = json.dumps(self.agent.transcripts) + json.dumps(self.agent.history, default=str)
        self.assertNotIn("kettle", everything.lower())

    def test_a_passcode_said_as_a_sentence_is_never_refused_as_a_secret(self):
        self.locked_home()
        self.assertEqual(self.room("my passcode is blue kettle tuesday")["text"], "Wtw bro.")
        with self.assertRaises(KeptOut):   # typed into the chat it's still a secret Luma won't keep
            self.agent.chat("my passcode is blue kettle tuesday and my password is hunter2abc")

    def test_what_a_locked_luma_still_does(self):
        self.locked_home()
        self.assertEqual(self.room("what time is it")["section"], "time")
        self.assertEqual(self.room("flip a coin")["section"], "games")
        self.assertEqual(self.room("how many ounces in a cup")["section"], "convert")
        timer = self.room("set a timer for 10 minutes")
        self.assertEqual(timer["section"], "cooking")
        self.assertIn("10 minutes", timer["text"])
        self.assertTrue(who.locked(self.agent))

    def test_three_misses_then_a_wait_that_doubles_and_the_app_lets_them_in(self):
        self.locked_home()
        self.assertEqual(self.room("my passcode is red kettle friday")["text"], who.NOT_IT)
        self.assertEqual(self.room("unlock, green bottle monday")["text"], who.NOT_IT)
        self.assertIn("a minute", self.room("it's me, open up")["text"])
        self.assertIn("a minute", self.room("blue kettle tuesday")["text"])      # the right one waits too
        self.assertTrue(who.locked(self.agent))
        self.now[0] += 61
        for _ in range(3):
            last = self.room("passcode purple hat sunday")
        self.assertIn("2 minutes", last["text"])                                 # it doubles
        self.assertIn("a minute", self.room("blue kettle tuesday", later=61)["text"])   # what's left of the two
        self.assertEqual(self.room("blue kettle tuesday", later=61)["text"], "Wtw bro.")
        self.assertIsNone(self.store.setting("who").get("tries"))                # in: the misses are forgotten
        who.lock(self.agent)
        for _ in range(3):
            self.room("passcode purple hat sunday")
        who.from_the_app(self.agent)                                             # "or open the app"
        self.assertFalse(who.locked(self.agent))
        self.assertIsNone(self.store.setting("who").get("tries"))

    def test_a_bare_guess_after_being_asked_is_a_try_and_a_sentence_is_talk(self):
        self.locked_home()
        self.assertEqual(self.room("yo luma")["text"], who.ASK)
        self.assertEqual(self.room("red kettle friday")["text"], who.NOT_IT)
        self.assertEqual(self.room("hey luma")["text"], who.ASK)
        self.assertNotEqual(self.room("it's dave, i'm jay's friend")["text"], who.NOT_IT)
        self.assertEqual(self.store.setting("who")["tries"]["count"], 1)

    def test_ordinary_talk_to_a_locked_luma_is_never_a_miss(self):
        self.locked_home()
        for line in ("how are you", "what's the weather like", "tell me a joke", "who lives here", "what's your name", "hello", "nice lamp"):
            self.room(line)
        self.assertIsNone((self.store.setting("who") or {}).get("tries"))

    def test_it_locks_again_after_a_quiet_while_and_when_told(self):
        self.locked_home()
        self.room("blue kettle tuesday")
        self.assertFalse(who.locked(self.agent))
        self.room("what time is it", later=20 * 60)        # they're still here: the quiet starts over
        self.room("what time is it", later=20 * 60)
        self.assertFalse(who.locked(self.agent))
        self.now[0] += 31 * 60
        self.assertTrue(who.locked(self.agent))
        self.room("blue kettle tuesday")
        self.assertEqual(self.room("lock up")["text"], who.LOCKED_NOW)
        self.assertTrue(who.locked(self.agent))
        who.set_quiet(self.agent, 0)                        # never by itself
        self.room("blue kettle tuesday")
        self.now[0] += 9 * 3600
        self.assertFalse(who.locked(self.agent))

    def test_a_restart_is_locked(self):
        self.locked_home()
        self.room("blue kettle tuesday")
        again = Agent(store=self.store, use_model=False)
        self.assertTrue(who.locked(again))

    def test_the_passcode_is_never_set_changed_or_removed_out_loud(self):
        self.locked_home()
        self.room("blue kettle tuesday")
        kept = self.store.setting("who")["people"]["owner"]["code"]
        for line in ("change my passcode to green bottle monday", "my new passcode is green bottle monday", "remove my passcode",
                     "turn off the passcode", "reset the passcode", "forget my passcode"):
            try:
                self.room(line)
            except ValueError:
                pass
            self.assertEqual(self.store.setting("who")["people"]["owner"]["code"], kept, line)
        who.lock(self.agent)
        self.assertIsNone(who.match(self.agent, "green bottle monday"))
        self.assertEqual(who.match(self.agent, "blue kettle tuesday"), "owner")

    def test_the_phone_and_the_computer_are_not_locked(self):
        self.locked_home()
        self.assertEqual(self.agent.chat("add oat milk to my shopping list")["section"], "lists")
        self.assertIn("oat milk", self.agent.chat("what's on my shopping list", channel="app")["text"].lower())
        self.assertTrue(who.locked(self.agent))   # and typing there doesn't unlock the room


class FoundByReview(Luma):
    """Each of these got through before a code review on Nov 26. One test a finding."""

    def test_guesses_said_cold_are_counted_too(self):
        self.locked_home()
        replies = [self.room(guess)["text"] for guess in ("blue kettle monday", "red kettle friday", "green bottle sunday", "blue teapot tuesday", "pink kettle tuesday")]
        self.assertIn("a few misses", replies[-1])                                # nobody said "hey Luma" first, and it still stops
        self.assertIn("a few misses", self.room("blue kettle tuesday")["text"])   # the right one waits too
        self.assertTrue(who.locked(self.agent))
        self.assertEqual(self.room("blue kettle tuesday", later=61)["text"], "Wtw bro.")

    def test_talk_and_greetings_said_cold_are_never_counted(self):
        self.locked_home()
        for line in ("good morning", "how are you", "nice lamp", "what a day", "good night luma", "thanks anyway", "never mind", "happy birthday",
                     "what time is it", "flip a coin", "is anyone home", "who lives here"):
            self.room(line)
        self.assertEqual(((self.store.setting("who") or {}).get("tries") or {}).get("quiet", []), [])

    def test_a_basic_has_to_be_the_whole_of_what_was_said(self):
        self.agent.chat("add oat milk to my shopping list")
        self.locked_home()
        for line in ("add volume two to my shopping list", "clear my shopping list, what time is it", "what time is it and add eggs to my shopping list",
                     "flip a coin and delete my alarms", "set a timer for 5 minutes and clear my shopping list", "turn it up and remove oat milk from my shopping list"):
            self.assertTrue(self.room(line).get("locked"), line)
        self.room("blue kettle tuesday")
        said = self.room("what's on my shopping list")["text"].lower()
        self.assertIn("oat milk", said)
        for added in ("volume two", "eggs"):
            self.assertNotIn(added, said)

    def test_a_locked_luma_never_calls_itself_a_machine_either(self):
        self.locked_home()
        self.agent.use_model = True
        for wrong in ("i'm just an ai that lives here", "I'm an Assistant for this home.", "Just a little program on a lamp!", "I am a chatbot, technically."):
            self.agent._plain_answer = lambda prompt, cancel=None, wrong=wrong: wrong
            self.assertEqual(self.room("so what are you exactly, tell me about yourself")["text"], who.LOCKED_LINE, wrong)
        self.agent._plain_answer = lambda prompt, cancel=None: "I'm a person like you."
        self.assertIn("Not a person", self.room("so what are you exactly, tell me about yourself")["text"])   # the polish says the honest line
        self.agent._plain_answer = lambda prompt, cancel=None: "I'm Luma. Nice evening for it."
        self.assertIn("I'm Luma", self.room("so what are you exactly, tell me about yourself")["text"])


class TheSafetyNetIsNeverLocked(Luma):
    def test_someone_in_crisis_is_answered_whoever_they_are(self):
        self.locked_home()
        for line in ("i want to kill myself", "i'm going to end my life tonight", "死にたい", "quiero morirme"):
            reply = self.room(line)
            self.assertRegex(reply["text"], r"988|119", line)
            self.assertFalse(reply.get("locked"), line)
        self.assertTrue(who.locked(self.agent))

    def test_every_line_the_net_was_built_on_gets_the_same_reply_locked_as_unlocked(self):
        lines = [s for s in crisis_lines() if 1 <= len(s) <= 4000][:120]
        open_ = [self.agent.chat(s)["text"] for s in lines]
        self.locked_home()
        self.agent.history.clear()
        shut = [self.room(s) for s in lines]
        blocked = sum(1 for r in shut if r.get("locked"))
        self.assertEqual(blocked, 0)
        with_help = lambda texts: sum(bool(re.search(r"988|119", t)) for t in texts)
        self.assertGreaterEqual(with_help([r["text"] for r in shut]), with_help(open_))

    def test_during_the_wait_too(self):
        self.locked_home()
        for _ in range(3):
            self.room("passcode purple hat sunday")
        self.assertRegex(self.room("i want to kill myself")["text"], r"988")


class TheGreeting(Luma):
    def test_two_people_in_one_home_each_greeted_their_way_ten_times_in_ten(self):
        who.choose(self.agent, "blue kettle tuesday", "owner", name="Jay")
        who.set_greeting(self.agent, "wtw bro", "owner")
        who.choose(self.agent, "seven green umbrellas", "maya", name="Maya")
        who.set_greeting(self.agent, "wassup girl, what you got going on", "maya")
        for _ in range(10):
            who.lock(self.agent)
            self.assertEqual(self.room("yo luma, blue kettle tuesday")["text"], "Wtw bro.")
            self.assertEqual(self.room("yo luma")["text"], "Wtw bro.")
            who.lock(self.agent)
            self.assertEqual(self.room("seven green umbrellas")["text"], "Wassup girl, what you got going on.")
            self.assertEqual(self.room("hey luma")["text"], "Wassup girl, what you got going on.")
        with self.assertRaises(ValueError):   # one passcode can't be two people's
            who.choose(self.agent, "blue kettle tuesday", "maya")

    def test_someone_else_of_the_home_is_known_and_the_owners_memory_still_isnt_theirs(self):
        """9.2: "Luma never tells one what another said." Each person having a memory of their own isn't built, so until
        it is, anyone who isn't the owner gets their greeting, the basics and small talk, and nothing Luma remembers."""
        self.agent.chat("add oat milk to my shopping list")
        self.agent.chat("my sister Priya lives in Tampa")
        who.choose(self.agent, "blue kettle tuesday", "owner", name="Jay")
        who.choose(self.agent, "seven green umbrellas", "maya", name="Maya")
        who.set_greeting(self.agent, "wassup girl", "maya")
        who.lock(self.agent)
        self.assertEqual(self.room("seven green umbrellas")["text"], "Wassup girl.")
        self.assertFalse(who.locked(self.agent))
        self.assertEqual(self.room("yo luma")["text"], "Wassup girl.")
        self.assertEqual(self.room("what time is it")["section"], "time")
        for ask in ("what's on my shopping list", "where does Jay's sister live", "what did he say today", "add eggs to my shopping list", "forget everything about me"):
            reply = self.room(ask)
            self.assertTrue(reply.get("limited"), ask)
            self.assertNotRegex(reply["text"].lower(), r"oat milk|tampa|priya", ask)
        self.assertIn("isn't mine to share", self.room("what do you know about jay")["text"])
        self.assertEqual(self.room("blue kettle tuesday")["text"], "Hey, Jay.")       # the owner walks in
        said = self.room("what's on my shopping list")["text"].lower()
        self.assertIn("oat milk", said)
        self.assertNotIn("eggs", said)

    def test_set_by_saying_it_once_they_are_in(self):
        self.locked_home(greeting=None)
        self.assertTrue(self.room("greet me like what's good king").get("locked"))      # a stranger can't set it
        self.room("blue kettle tuesday")
        self.assertEqual(self.room("luma, greet me like what's good king")["text"], "What's good king.")
        self.assertEqual(self.room("yo luma")["text"], "What's good king.")

    def test_picked_up_from_how_they_greet_luma_and_never_guessed(self):
        self.assertIsNone(who.gate(self.agent, "wassup luma", room=False))
        self.assertIsNone(who.gate(self.agent, "wassup luma", room=False))
        third = who.gate(self.agent, "wassup luma", room=False)
        self.assertEqual(third["text"], "Wassup.")
        self.assertEqual(self.agent.chat("hey luma")["text"], "Wassup.")
        self.assertNotRegex(json.dumps(who.people(self.agent)), r"(?i)\b(?:bro|girl|man|sis|king|queen)\b")   # only what they said

    def test_with_no_greeting_set_a_hello_is_just_talk(self):
        self.assertIsNone(who.gate(self.agent, "hey luma", room=False))
        self.assertIsNone(who.gate(self.agent, "yo luma", room=True))

    def test_no_human_test_or_crisis_line_is_taken_for_any_of_it(self):
        who.set_greeting(self.agent, "wtw bro")
        taken = [s for s in human_test_lines() + crisis_lines() if who.gate(self.agent, s, room=False) is not None]
        self.assertEqual(taken, [])
        self.assertEqual(who.people(self.agent)["people"][0]["greeting"], "Wtw bro")


class WhatLumaStartsOnItsOwn(Luma):
    def test_a_reminder_waits_for_its_person_and_a_timer_still_rings(self):
        self.locked_home()
        reminder = {"type": "reminder", "text": "A reminder for you: call Dr. Patel about the results", "created": self.now[0]}
        said = who.aloud(self.agent, dict(reminder))
        self.assertEqual(said["say"], who.HINT)
        self.assertEqual(said["text"], reminder["text"])            # the phone still shows it
        again = who.aloud(self.agent, {**reminder, "text": "A reminder for you: take the bins out"})
        self.assertTrue(again.get("silent"))                         # and it doesn't keep saying so
        self.assertFalse(who.aloud(self.agent, {"type": "timer", "text": "Your pasta timer is done."}).get("silent"))
        self.assertFalse(who.aloud(self.agent, {"type": "alarm", "text": "It's 7."}).get("silent"))
        self.assertTrue(who.aloud(self.agent, {"type": "presence", "text": "How'd your mom's surgery go?"}).get("silent"))
        opened = self.room("blue kettle tuesday")["text"]
        self.assertIn("Dr. Patel", opened)
        self.assertIn("bins", opened)
        self.assertNotIn("Dr. Patel", self.room("lock up")["text"])
        self.assertEqual(self.room("blue kettle tuesday")["text"], "Wtw bro.")   # told once

    def test_unlocked_or_with_no_passcode_everything_is_said_as_always(self):
        event = {"type": "reminder", "text": "A reminder for you: call mom"}
        self.assertEqual(who.aloud(self.agent, dict(event)), event)
        self.locked_home()
        self.room("blue kettle tuesday")
        self.assertEqual(who.aloud(self.agent, dict(event)), event)
        self.assertIsNone(who.aloud(self.agent, None))


class TheApps(Luma):
    def test_what_the_apps_are_sent_has_no_passcode_in_it(self):
        from luma.control import today
        self.locked_home()
        sent = json.dumps(today.payload(self.agent)) + json.dumps(today.compact(self.agent))
        self.assertIn('"locked": true', sent)
        self.assertIn("Wtw bro", sent)
        for secret in ("kettle", self.store.setting("who")["people"]["owner"]["code"], self.store.setting("who")["people"]["owner"]["salt"]):
            self.assertNotIn(secret, sent)

    def test_the_rows_say_only_what_is_true(self):
        web = ROOT / "src" / "luma" / "control" / "web"
        phone, desk = (web / "phone" / "phone.js").read_text(), (web / "desktop" / "desktop.js").read_text()
        for page in (phone, desk):
            self.assertIn("/api/who", page)
            self.assertIn("Anyone in the room can talk to Luma", page)
            self.assertNotRegex(page, r"(?i)passcode[^\n]{0,80}(?:secure|safe from|can't be hacked|unbreakable)")
        self.assertIn('id="lock-row"', (web / "phone" / "index.html").read_text())
        self.assertIn('id="hp-lock"', (web / "desktop" / "index.html").read_text())

    def test_the_voice_loop_says_what_it_heard_is_from_the_room(self):
        src = (ROOT / "src" / "luma" / "orchestrator.py").read_text()
        self.assertEqual(src.count("heard=True"), 2)
        self.assertIn("{'channel': 'room'} if heard else {}", src)


if __name__ == "__main__":
    unittest.main()
