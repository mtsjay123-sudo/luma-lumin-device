"""The exact things that went wrong in a real chat: news Luma said it couldn't get, a connector it said it didn't have,
an email it said it couldn't schedule, and a "what can you do" with nothing behind it."""
import functools
import http.server
import json
import os
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from test_dots_features import FakeIMAP, FakeSMTP, agent_with, raw_email

NOW = 1791900000  # Tue 13 Oct 2026, 14:00 UTC (10:00 in New York)


class Site:
    def __enter__(self):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(Path(__file__).parent / "fixtures" / "web"))
        handler.log_message = lambda *a: None
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        return self

    def __exit__(self, *exc):
        self.server.shutdown()


class LiveNewsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = Site().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.site.__exit__()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        feeds = json.dumps([["Test Wire", self.site.base + "/news-rss.xml"], ["Tech Daily", self.site.base + "/news-atom.xml", "tech"]])
        self.env = mock.patch.dict(os.environ, {"LUMA_NEWS_FEEDS": feeds, "LUMA_NEWS_SEARCH": self.site.base + "/gnews"})
        self.env.start()
        self.now = NOW
        self.agent, self.store = agent_with(Path(self.temp.name), now=lambda: self.now)
        self.agent.news_allow_local = True

    def tearDown(self):
        self.env.stop()
        self.store.close()
        self.temp.cleanup()

    def test_typo_and_time_window_still_get_the_news(self):
        reply = self.agent.chat("tell me new knews in the last uhhh 10hrs")
        self.assertEqual(reply["section"], "news")
        self.assertNotIn("real-time", reply["text"])
        titles = [r["title"] for r in reply["results"]]
        self.assertIn("Fed holds interest rates steady, signals one more cut this year", titles)
        self.assertEqual(len(titles), 3)  # Fed, Starship, M6: everything from the last 10 hours, nothing older
        self.assertTrue(all(r["age"].endswith("ago") for r in reply["results"]))
        self.assertIn("the last 10 hours", reply["text"])

    def test_only_the_hours_they_asked_about(self):
        reply = self.agent.chat("any news in the last 3 hours?")
        self.assertEqual([r["title"] for r in reply["results"]], ["Fed holds interest rates steady, signals one more cut this year"])
        quiet = self.agent.chat("news from the last hour")
        self.assertIn("Nothing new from my sources in the last hour", quiet["text"])
        self.assertTrue(quiet["results"])  # and still the latest it has

    def test_tell_me_the_news_is_the_news_but_good_news_is_theirs(self):
        self.assertEqual(self.agent.chat("tell me the news").get("section"), "news")
        self.assertNotEqual(self.agent.chat("I have good news, I got the job").get("section"), "news")

    def test_a_topic_is_searched_live_and_credits_the_outlet(self):
        reply = self.agent.chat("what's the latest on the fed rate cut")
        self.assertEqual([r["source"] for r in reply["results"]], ["Reuters", "CNBC"])
        self.assertEqual(reply["results"][0]["title"], "Fed signals a December rate cut as inflation cools")
        self.assertEqual(reply["results"][0]["snippet"], "")  # Google repeats the headline; don't show it twice
        sports = self.agent.chat("sports news")
        self.assertEqual(sports["results"][0]["title"], "Lakers win in overtime thriller")

    def test_asking_refreshes_old_headlines_first(self):
        self.agent.read_news(force=True)
        self.now += 20 * 60
        with mock.patch("luma.skills.news.refresh", wraps=__import__("luma.skills.news", fromlist=["refresh"]).refresh) as reread:
            self.agent.chat("what's the news")
        self.assertEqual(reread.call_count, 1)  # 20 minutes old: read again before answering

    def test_do_you_have_a_connector_for_news(self):
        reply = self.agent.chat("do you have a connector for news?")
        self.assertIn("news is built in", reply["text"])
        self.assertIn("Right now:", reply["text"])
        self.assertEqual(reply["section"], "news")
        self.assertNotIn("No,", reply["text"])

    def test_the_model_saying_no_to_news_gets_overruled(self):
        self.agent.use_model = True
        self.agent.planner = lambda *a: {"type": "reply", "text": "I don't have real-time news access, so I can't tell you what's happening right now."}
        reply = self.agent.chat("so whats going on out there rn")
        self.assertEqual(reply["section"], "news")
        self.assertTrue(reply["results"])
        self.agent.planner = lambda *a: {"type": "reply", "text": "I don't have feelings the way you do, but I'm glad you asked."}
        self.assertIn("feelings", self.agent.chat("do you get sad?")["text"])  # a true no stands


class WhatLumaCanDoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.agent, self.store = agent_with(Path(self.temp.name), now=lambda: NOW)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_what_can_you_do_is_answered_from_what_is_real(self):
        for said in ["what can you do?", "tell em what luma can do", "what are your features", "help"]:
            reply = self.agent.chat(said)
            self.assertTrue(reply.get("capabilities"), said)
            self.assertIn("News, live", reply["text"])
            self.assertIn("connect your email in Apps first", reply["text"])  # not connected yet, so it says so

    def test_specific_abilities(self):
        mail = self.agent.chat("can you schedule emails? do you have a feature for scheduling emails")
        self.assertIn("schedule emails for later", mail["text"])
        self.assertEqual(mail["connect"], "mail")
        odd = self.agent.chat("do you have a connector for Notion?")
        self.assertIn("Not built in for Notion", odd["text"])
        self.assertIn("Teach", odd["text"])

    def test_requests_are_not_mistaken_for_questions(self):
        self.assertFalse(self.agent.chat("what can you do about my flight being cancelled").get("capabilities"))


class ScheduledEmailTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = NOW
        self.agent, self.store = agent_with(Path(self.temp.name), now=lambda: self.now)
        self.agent.mail.imap_factory = FakeIMAP
        self.agent.mail.smtp_factory = FakeSMTP
        FakeIMAP.mailbox = [raw_email("1", "Sam Rivera <sam@example.com>", "Dinner Friday?", "Are we still on?")]
        FakeIMAP.appended, FakeSMTP.sent = [], []

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def connect(self):
        self.agent.mail.connect("me@gmail.com", "abcdabcdabcdabcd")
        self.agent.enable("mail", True)

    def local(self, ts):
        return datetime.fromtimestamp(ts, self.agent.zone)

    def test_the_rambling_one_asks_whats_missing_instead_of_searching_the_web(self):
        said = "okay so your app needs to find this and improve it to show real time news ill work on that inthe emtime shceydke me an email"
        reply = self.agent.chat(said)
        self.assertNotIn("results", reply)
        self.assertIn("what it should say and when it should go out", reply["text"])
        self.assertEqual(reply["pending_mail"], ["what", "when"])

    def test_connect_here_then_it_carries_on_and_waits_for_allow(self):
        self.assertIn("Just tell me", self.agent.chat("schedule me an email")["text"])
        need = self.agent.chat("tomorrow at 9am: work on the real-time news feature")
        self.assertEqual(need["connect"], "mail")  # connect right here, and it picks back up
        self.assertIn("remind me instead", need["text"])
        self.connect()
        card = self.agent.chat("done")
        self.assertEqual(card["state"], "pending")
        self.assertEqual(card["tool"], "mail.schedule")
        self.assertEqual(card["arguments"]["to"], "me@gmail.com")
        self.assertEqual(card["arguments"]["subject"], "Reminder: work on the real-time news feature")
        at = self.local(datetime.fromisoformat(card["arguments"]["send_at"]).timestamp())
        self.assertEqual((at.day, at.hour, at.minute), (14, 9, 0))
        self.assertIn("tomorrow at 9:00 AM", card["text"])
        self.assertEqual(FakeSMTP.sent, [])
        done = self.agent.confirm(card["action"], card["confirm_token"])
        self.assertEqual(done["state"], "succeeded")
        self.assertIn("Scheduled", done["summary"])
        self.assertEqual(self.agent.send_due_mail(), [])  # not yet
        self.assertEqual(FakeSMTP.sent, [])
        self.now = at.timestamp() + 5
        sent = self.agent.send_due_mail()
        self.assertEqual([r["state"] for r in sent], ["sent"])
        self.assertEqual(FakeSMTP.sent[0]["To"], "me@gmail.com")
        self.assertIn("work on the real-time news feature", FakeSMTP.sent[0].get_content())
        self.assertEqual(self.agent.feed.list()[0]["title"], "Sent your email to me@gmail.com")
        self.assertEqual(self.agent.send_due_mail(), [])  # never twice

    def test_one_breath_to_someone_else_finds_their_address(self):
        self.connect()
        card = self.agent.chat("email Sam friday at 2pm saying dinner's on me this time")
        self.assertEqual(card["tool"], "mail.schedule")
        self.assertEqual(card["arguments"]["to"], "sam@example.com")
        self.assertEqual(card["recipient_name"], "Sam Rivera")
        self.assertEqual(self.local(datetime.fromisoformat(card["arguments"]["send_at"]).timestamp()).strftime("%a %H:%M"), "Fri 14:00")

    def test_unknown_person_gets_asked_for_their_address(self):
        self.connect()
        ask = self.agent.chat("email Jordan tomorrow at 10am saying welcome aboard")
        self.assertIn("What's Jordan's email address?", ask["text"])
        card = self.agent.chat("jordan@example.org")
        self.assertEqual(card["arguments"]["to"], "jordan@example.org")
        self.assertEqual(card["recipient_name"], "Jordan")

    def test_no_time_means_send_now_after_allow(self):
        self.connect()
        card = self.agent.chat("send an email to sam@example.com saying running 10 minutes late")
        self.assertEqual(card["tool"], "mail.send")
        self.assertEqual(card["state"], "pending")

    def test_cancel_and_list(self):
        self.connect()
        card = self.agent.chat("schedule an email to sam@example.com for tomorrow at 8am about the invoice")
        self.agent.confirm(card["action"], card["confirm_token"])
        self.assertIn("1 scheduled", self.agent.chat("what emails are scheduled?")["text"])
        self.assertIn("Cancelled your email to sam@example.com", self.agent.chat("cancel my scheduled email")["text"])
        self.now += 2 * 86400
        self.assertEqual(self.agent.send_due_mail(), [])
        self.assertEqual(FakeSMTP.sent, [])

    def test_blocked_by_rules_at_send_time_means_it_does_not_go(self):
        self.connect()
        card = self.agent.chat("email sam@example.com in 2 hours saying the deck is ready")
        self.agent.confirm(card["action"], card["confirm_token"])
        self.agent.rules.set("email", "block")
        self.now += 3 * 3600
        self.assertEqual([r["state"] for r in self.agent.send_due_mail()], ["failed"])
        self.assertEqual(FakeSMTP.sent, [])
        self.assertEqual(self.agent.feed.list()[0]["title"], "A scheduled email didn't go out")

    def test_remind_me_instead_when_email_is_not_connected(self):
        self.agent.chat("schedule me an email tomorrow at 9am reminding me to call the bank")
        reply = self.agent.chat("just remind me instead")
        self.assertIn("I'll remind you tomorrow at 9:00 AM: call the bank", reply["text"])
        self.assertEqual(reply["task"]["title"], "call the bank")

    def test_nevermind_drops_it(self):
        self.agent.chat("schedule me an email")
        self.assertIn("dropped it", self.agent.chat("never mind")["text"])
        self.assertIsNone(self.agent.pending_mail)

    def test_the_model_saying_it_cant_schedule_emails_gets_overruled(self):
        self.agent.use_model = True
        self.agent.planner = lambda *a: {"type": "reply", "text": "I can't schedule emails — that's not something I do."}
        reply = self.agent.chat("is emailing people later a thing for you")
        self.assertIn("schedule emails for later", reply["text"])
        self.assertNotIn("can't", reply["text"])


if __name__ == "__main__":
    unittest.main()
