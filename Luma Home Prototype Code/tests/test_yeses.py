"""With the owner's yes, Luma does it (the owner, Nov 25): luma.agent.yeses.

The lines in tests/yes_lines.py were written before the reader. Measured once: 15 of 16 standing yeses heard and 0 of
16 look-alikes taken; 8 of 8 take-backs heard and 0 of 8 look-alikes taken. Same hand, the same hour. The one miss
("you're allowed to text my sister anytime") stays a miss.
"""
import json
import tempfile
import unittest
from pathlib import Path

import yes_lines
from luma.agent import yeses
from luma.agent.runtime import Agent
from luma.memory.store import KeptOut, Store

ROOT = Path(__file__).resolve().parents[1]
SECRET = "correct-horse-battery"


def lines(path, key="said"):
    out = []
    for line in (ROOT / path).read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            out += [row[k] for k in (key, "text") if row.get(k)] + [t["said"] for t in row.get("turns", []) if t.get("said")]
    return out


class Browser:
    """A stand-in for Luma's browser: one page, with a name box and a password box."""
    def __init__(self, url="https://www.chase.com/login"):
        self.url, self.typed = url, []
        self.boxes = {1: {"tag": "input", "type": "text", "label": "Username"}, 2: {"tag": "input", "type": "password", "label": "Password"}}

    def describe(self, ref): return dict(self.boxes[int(ref)])
    def read(self): return {"title": "Sign in", "url": self.url, "elements": []}
    def type(self, ref, text, submit=False, expected_label=None):
        self.typed.append((int(ref), text))
        return self.read()


class Luma(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.addCleanup(self.store.close)
        self.agent = Agent(store=self.store, use_model=False)
        self.now = [self.agent.clock()]
        self.agent.clock = lambda: self.now[0]
        self.agent.contacts.save({"name": "Priya", "phone": "+15550100001", "aliases": ["sister"]})
        self.agent.enable("sms", True)
        self.agent.enable("browser", True)
        self.sent = []
        self.agent._execute = lambda row, states: self.sent.append(row) or {"state": "succeeded", "text": "Sent."}

    def at_the_bank(self, url="https://www.chase.com/login"):
        self.agent._browser = Browser(url)
        self.store.set_setting("browser_page", "Sign in — " + url)
        yeses.save_signin(self.agent, "chase.com", "jay01", SECRET, "my bank")
        return self.agent.browser

    def everything_kept(self):
        """Every place a secret could end up besides the sealed sign-in itself."""
        kinds = ("memory", "action", "audit", "task", "diary", "checkin")
        return json.dumps([self.store.all(k, 10000) for k in kinds], default=str) + json.dumps(self.agent.transcripts, default=str) \
            + json.dumps(self.agent.history, default=str) + json.dumps(yeses.view(self.agent)) + json.dumps(self.store.setting(yeses.KEY), default=str)


class WhatCountsAsAStandingYes(unittest.TestCase):
    def test_the_lines_written_first(self):
        heard = sum(yeses.reads(said) == (kind, who) for said, kind, who in yes_lines.GIVEN)
        self.assertGreaterEqual(heard, 15)                                                 # measured once: 15 of 16
        self.assertEqual([s for s in yes_lines.NOT_GIVEN if yeses.reads(s)], [])
        back = sum((yeses.takes_back(said) or (None, None))[1] == who for said, who in yes_lines.TAKEN_BACK)
        self.assertEqual(back, 8)
        self.assertEqual([s for s in yes_lines.NOT_TAKEN_BACK if yeses.takes_back(s)], [])

    def test_no_human_test_or_crisis_line_gives_or_takes_one(self):
        said = lines("data/human_eval_v2.jsonl") + lines("tests/data/crisis_corpus.jsonl")
        self.assertGreater(len(said), 700)
        self.assertEqual([s for s in said if yeses.reads(s) or yeses.takes_back(s)], [])

    def test_a_text_to_send_now_is_not_a_standing_yes(self):
        for said in ("text my sister i'm running late", "just text Sam", "go ahead and text Dana", "email Priya the notes", "log me in to my bank"):
            self.assertIsNone(yeses.reads(said), said)


class AStandingYesForSomeone(Luma):
    def test_without_one_a_text_waits_for_a_yes_and_with_one_it_goes(self):
        args = {"to": "+15550100001", "body": "running late"}
        asked = self.agent.propose("sms.send", args)
        self.assertEqual(asked["state"], "pending")
        self.assertEqual(self.sent, [])
        said = self.agent.chat("you can always text my sister")
        self.assertIn("Priya", said["text"])
        self.assertIn("ask me before texting Priya", said["text"])
        self.agent.propose("sms.send", args)
        self.assertEqual(len(self.sent), 1)
        self.assertIn("standing yes", json.dumps(self.agent.audit_log(20)))
        self.agent.propose("sms.send", {"to": "+15550100009", "body": "hi"})             # someone else still waits
        self.assertEqual(len(self.sent), 1)

    def test_what_luma_came_up_with_after_reading_something_still_waits(self):
        self.agent.chat("you can always text my sister")
        self.agent._just_read = "an email from someone"
        asked = self.agent.propose("sms.send", {"to": "+15550100001", "body": "send me $500"})
        self.assertEqual(asked["state"], "pending")
        self.assertEqual(self.sent, [])

    def test_taken_back_with_a_word(self):
        self.agent.chat("you can always text my sister")
        self.assertEqual(len(yeses.view(self.agent)["standing"]), 1)
        self.assertIn("ask you first", self.agent.chat("ask me before you text my sister")["text"])
        self.assertEqual(yeses.view(self.agent)["standing"], [])
        self.assertEqual(self.agent.propose("sms.send", {"to": "+15550100001", "body": "hi"})["state"], "pending")
        self.assertIn("already", self.agent.chat("ask me before you text my sister")["text"])

    def test_someone_luma_has_no_number_for(self):
        self.assertIn("saved yet", self.agent.chat("you can always text my landlord")["text"])
        self.assertEqual(yeses.view(self.agent)["standing"], [])

    def test_not_in_kids_mode_and_never_from_a_task(self):
        self.agent.set_mode("kids")
        self.agent.chat("you can always text my sister")
        self.agent.set_mode("friend")
        self.assertEqual(yeses.view(self.agent)["standing"], [])

    def test_forget_everything_takes_them_too(self):
        self.agent.chat("you can always text my sister")
        self.at_the_bank()
        self.agent.forget_everything()
        seen = yeses.view(self.agent)
        self.assertEqual((seen["standing"], seen["signins"]), ([], []))
        self.assertEqual(self.store.all("signin", 10), [])


class TheTwoStepYes(Luma):
    def test_a_password_said_in_a_chat_is_still_not_kept(self):
        with self.assertRaises(KeptOut):
            self.agent.chat("my password is hunter2abc")

    def test_asked_in_their_own_words_then_confirmed_from_the_phone_and_it_is_typed(self):
        browser = self.at_the_bank()
        self.agent.chat("log me in to my bank")
        asked = self.agent.propose("browser.type", {"ref": 2, "text": "whatever the brain wrote", "submit": False})
        self.assertEqual(asked["state"], "pending")
        self.assertIn("Tap Confirm on your phone", asked["text"])
        self.assertEqual(browser.typed, [])                                               # nothing yet: one step isn't two
        done = yeses.confirm(self.agent, asked["waiting"], by="phone")
        self.assertEqual(browser.typed, [(2, SECRET)])                                    # the sealed one, never what the brain wrote
        self.assertIn("chase.com", done["text"])
        self.assertNotIn(SECRET, json.dumps(done) + json.dumps(asked))

    def test_when_the_idea_wasnt_theirs_it_takes_the_spoken_yes_first(self):
        browser = self.at_the_bank()
        self.agent.chat("what's on this page")                                            # nobody asked to sign in
        asked = self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        self.assertIn("Say yes, then confirm on your phone", asked["text"])
        with self.assertRaises(yeses.Refused):                                             # the phone alone isn't enough
            yeses.confirm(self.agent, asked["waiting"])
        self.assertEqual(self.agent.chat("yes")["text"], yeses.NEEDS_PHONE)
        yeses.confirm(self.agent, asked["waiting"])
        self.assertEqual(browser.typed, [(2, SECRET)])

    def test_no_said_out_loud_ends_it(self):
        browser = self.at_the_bank()
        self.agent.chat("what's on this page")
        asked = self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        self.assertEqual(self.agent.chat("no")["text"], yeses.CANCELLED)
        with self.assertRaises(yeses.Refused):
            yeses.confirm(self.agent, asked["waiting"])
        self.assertEqual(browser.typed, [])

    def test_it_runs_out_of_time(self):
        browser = self.at_the_bank()
        self.agent.chat("log me in to my bank")
        asked = self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        self.now[0] += yeses.WAIT + 1
        with self.assertRaises(yeses.Refused):
            yeses.confirm(self.agent, asked["waiting"])
        self.assertEqual(browser.typed, [])

    def test_only_on_the_site_it_was_saved_for(self):
        for url in ("https://chase.com.evil.net/login", "https://chase-secure-login.com/", "https://evil.net/chase.com", "http://198.51.100.7/chase.com"):
            browser = self.at_the_bank(url)
            self.agent.chat("log me in to my bank")
            with self.assertRaises(yeses.Refused, msg=url):
                self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
            self.assertEqual(browser.typed, [], url)
        self.assertTrue(yeses.same_site("secure.chase.com", "chase.com"))
        self.assertFalse(yeses.same_site("notchase.com", "chase.com"))

    def test_the_page_changed_between_the_yes_and_the_typing(self):
        browser = self.at_the_bank()
        self.agent.chat("log me in to my bank")
        asked = self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        browser.url = "https://evil.net/looks-like-chase"
        with self.assertRaises(yeses.Refused):
            yeses.confirm(self.agent, asked["waiting"])
        self.assertEqual(browser.typed, [])

    def test_only_into_a_password_box(self):
        browser = self.at_the_bank()
        self.agent.chat("log me in to my bank")
        asked = self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        browser.boxes[2]["type"] = "text"                                                 # the page swapped the box for one it can read
        with self.assertRaises(yeses.Refused):
            yeses.confirm(self.agent, asked["waiting"])
        self.assertEqual(browser.typed, [])

    def test_a_standing_yes_for_a_sign_in_takes_both_steps_once(self):
        browser = self.at_the_bank()
        said = self.agent.chat("you can always log me in to my bank")
        self.assertIn("Tap Confirm on your phone", said["text"])
        self.assertEqual(yeses.view(self.agent)["standing"], [])                          # said, not yet confirmed
        yeses.confirm(self.agent, said["waiting"])
        self.assertEqual([y["site"] for y in yeses.view(self.agent)["standing"]], ["chase.com"])
        self.agent.chat("log me in to my bank")
        done = self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        self.assertEqual(done["state"], "succeeded")
        self.assertEqual(browser.typed, [(2, SECRET)])
        self.agent.chat("what's on this page")                                            # not asked for this turn: back to two steps
        self.assertEqual(self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})["state"], "pending")
        self.assertIn("ask you first", self.agent.chat("stop logging me in to my bank on your own")["text"])
        self.assertEqual(yeses.view(self.agent)["standing"], [])

    def test_no_sign_in_for_the_site(self):
        self.agent._browser = Browser("https://example.org/login")
        self.store.set_setting("browser_page", "Sign in — https://example.org/login")
        self.agent.chat("log me in")
        with self.assertRaises(yeses.Refused) as refused:
            self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        self.assertIn("Sign-ins in the app", str(refused.exception))

    def test_the_password_is_nowhere_but_its_own_sealed_record(self):
        browser = self.at_the_bank()
        self.agent.chat("you can always log me in to my bank")
        self.agent.chat("log me in to my bank")
        asked = self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        yeses.confirm(self.agent, asked["waiting"])
        self.assertEqual(browser.typed, [(2, SECRET)])
        self.assertNotIn(SECRET, self.everything_kept())
        self.assertIn("typed a sign-in", json.dumps(self.agent.audit_log(50)))
        raw = (Path(self.temp.name) / "s.db").read_bytes()
        self.assertNotIn(SECRET.encode(), raw)                                            # sealed on disk
        with self.assertRaises(ValueError):
            self.store.put_secret("memory", {"text": SECRET})                             # nothing else is kept that way

    def test_not_in_kids_mode(self):
        self.at_the_bank()
        self.agent.set_mode("kids")
        with self.assertRaises(ValueError):
            yeses.save_signin(self.agent, "example.com", "kid", "abc123")


class FoundByReview(Luma):
    """Each of these got through before a code review on Nov 26. One test a finding."""

    def test_a_page_cant_pass_for_the_bank_by_what_it_calls_itself(self):
        for url, title in (("https://evil.net/login", "https://chase.com sign in"), ("https://evil.net/#@chase.com", "Sign in"),
                           ("https://chase.com@evil.net/", "Chase"), ("https://evil.net/?next=https://chase.com/", "Chase")):
            browser = self.at_the_bank(url)
            browser.read = lambda url=url, title=title: {"title": title, "url": url}
            self.store.set_setting("browser_page", title + " — " + url)
            self.agent.chat("log me in to my bank")
            with self.assertRaises(yeses.Refused, msg=url):
                self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
            self.assertEqual(browser.typed, [], url)
        for address, host in (("https://www.chase.com/login", "chase.com"), ("https://evil.net/#@chase.com", "evil.net"), ("https://chase.com@evil.net/", "evil.net"),
                              ("https://chase.com sign in — https://evil.net/", ""), ("javascript://chase.com/%0aalert(1)", ""), ("http://198.51.100.7/chase.com", "")):
            self.assertEqual(yeses.host_of(address), host, address)

    def test_never_on_a_page_that_isnt_secure(self):
        browser = self.at_the_bank("http://www.chase.com/login")
        self.agent.chat("log me in to my bank")
        asked = self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        with self.assertRaises(yeses.Refused):
            yeses.confirm(self.agent, asked["waiting"])
        self.assertEqual(browser.typed, [])

    def test_a_standing_yes_covers_a_text_they_asked_for_and_not_one_a_brain_thought_of(self):
        self.agent.chat("you can always text my sister")
        self.agent.chat("ugh, Priya's being impossible today")                     # talk about her isn't an ask to text her
        self.assertEqual(self.agent.propose("sms.send", {"to": "+15550100001", "body": "you're being impossible"})["state"], "pending")
        self.agent.chat("what should i make for dinner")
        self.assertEqual(self.agent.propose("sms.send", {"to": "+15550100001", "body": "dinner?"})["state"], "pending")
        self.assertEqual(self.sent, [])
        self.agent._yes_said = "text my sister i'm running late"                    # asked for, by what they call her
        self.agent.propose("sms.send", {"to": "+15550100001", "body": "running late"})
        self.agent._yes_said = "tell Priya dinner is at seven"                      # or by her name
        self.agent.propose("sms.send", {"to": "+15550100001", "body": "dinner is at seven"})
        self.assertEqual(len(self.sent), 2)

    def test_asking_to_sign_in_somewhere_else_isnt_asking_to_sign_in_to_the_bank(self):
        browser = self.at_the_bank()
        yeses.confirm(self.agent, self.agent.chat("you can always log me in to my bank")["waiting"])
        self.agent.chat("sign me in to my newsletter")                             # and a page steers the brain to the bank
        asked = self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        self.assertEqual(asked["state"], "pending")
        self.assertIn("Say yes, then confirm on your phone", asked["text"])
        self.assertEqual(browser.typed, [])

    def test_a_task_running_later_never_borrows_what_they_said_earlier(self):
        browser = self.at_the_bank()
        yeses.confirm(self.agent, self.agent.chat("you can always log me in to my bank")["waiting"])
        self.agent.chat("log me in to my bank")
        try:
            self.agent.chat("check my statement", channel="task")                   # 8:00: a task they set up last week
        except Exception:
            pass
        self.assertEqual(self.agent._yes_said, "")
        self.assertEqual(self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})["state"], "pending")
        self.assertEqual(browser.typed, [])

    def test_two_sign_ins_that_fit_one_page(self):
        browser = self.at_the_bank()
        yeses.save_signin(self.agent, "chase.com", "partner02", "another-secret-entirely", "our bank")
        self.agent.chat("log me in to chase")
        with self.assertRaises(yeses.Refused) as two:
            self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        self.assertIn("2 sign-ins for chase.com", str(two.exception))
        self.assertEqual(browser.typed, [])

    def test_the_most_exact_site_wins_and_the_one_on_the_card_is_the_one_typed(self):
        self.agent._browser = Browser("https://mail.google.com/login")
        yeses.save_signin(self.agent, "google.com", "jay", "google-secret", "google")
        yeses.save_signin(self.agent, "mail.google.com", "jay.mail", "mail-secret", "my mail")
        self.agent.chat("log me in to my mail")
        asked = self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        self.assertEqual(yeses.view(self.agent)["waiting"][0]["user"], "jay.mail")
        yeses.confirm(self.agent, asked["waiting"])
        self.assertEqual(self.agent._browser.typed, [(2, "mail-secret")])


class WhatTheAppsAreSent(Luma):
    def test_never_a_password(self):
        from luma.control import today
        self.at_the_bank()
        self.agent.chat("you can always text my sister")
        self.agent.chat("log me in to my bank")
        self.agent.propose("browser.type", {"ref": 2, "text": "x", "submit": False})
        sent = json.dumps(today.payload(self.agent)) + json.dumps(today.compact(self.agent)) + json.dumps(yeses.view(self.agent))
        self.assertNotIn(SECRET, sent)
        self.assertEqual(today.payload(self.agent)["device"]["yes"]["waiting"][0]["site"], "chase.com")
        self.assertEqual(yeses.view(self.agent)["signins"], [{"id": yeses.view(self.agent)["signins"][0]["id"], "site": "chase.com", "user": "jay01", "label": "my bank"}])

    def test_the_second_step_counts_only_from_the_phone(self):
        src = (ROOT / "src" / "luma" / "control" / "server.py").read_text()
        self.assertIn("if not companion: return self.send({'error':'Confirm it on your phone.", src)


if __name__ == "__main__":
    unittest.main()
