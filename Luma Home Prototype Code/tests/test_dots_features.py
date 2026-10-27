import base64
"""Luma's Dots-style features: cheapest-price shopping you can watch and stop, the owner's
rules, free email and calendar, always-on helpers, the feed, feedback and side chats."""
import email
import functools
import http.cookiejar
import http.server
import importlib.util
import json
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

from luma.agent.activity import Activity, Stopped
from luma.agent.runtime import Agent
from luma.integrations.providers import Providers
from luma.memory.store import Store
from luma.skills import shopping

FIXTURES = Path(__file__).parent / "fixtures" / "web"
HAS_BROWSER = importlib.util.find_spec("playwright") is not None


class FakeBrowser:
    """Store pages as lists of listings; one store can be down."""

    def __init__(self, pages, broken=(), on_open=None):
        self.pages, self.broken, self.on_open = pages, set(broken), on_open
        self.url = None
        self.opened = []
        self.clicked = []

    def open(self, url):
        self.url = url
        self.opened.append(url)
        if self.on_open: self.on_open(url)
        if any(b in url for b in self.broken): raise RuntimeError("blocked by the store")
        return {"url": url, "title": "page", "text": "Added to cart" if self.clicked else "", "elements": [{"ref": 1, "label": "Add to cart", "tag": "button"}]}

    def scroll(self, direction="down", times=2): return self.open(self.url)
    def screenshot(self): return {"url": self.url, "title": "page", "jpeg_base64": "/9j/"}
    def click(self, ref, expected_label=None):
        self.clicked.append((ref, expected_label))
        return {"url": self.url, "text": "Added to cart. Cart (1)", "elements": []}

    def products(self):
        return next((v for k, v in self.pages.items() if k in self.url), [])


STORES = [{"id": "a", "name": "Store A", "search": "https://a.example/s?q={q}"},
          {"id": "b", "name": "Store B", "search": "https://b.example/s?q={q}"},
          {"id": "c", "name": "Store C", "search": "https://c.example/s?q={q}"}]
LISTINGS = {
    "a.example": [{"title": "Apple AirPods Pro 2 Wireless Earbuds", "price": 199.99, "url": "https://a.example/p/1"},
                  {"title": "Case for AirPods Pro 2", "price": 9.99, "url": "https://a.example/p/2"}],
    "b.example": [{"title": "AirPods Pro 2 with USB-C case", "price": "$189.00", "url": "https://b.example/p/1"},
                  {"title": "AirPods Pro (1st generation)", "price": 99, "url": "https://b.example/p/2"}],
    "c.example": [{"title": "Apple AirPods Pro 2nd Gen", "price": 174.95, "url": "https://c.example/p/1"}],
}


def agent_with(root, env=None, **kw):
    store = Store(root / "state.db", root / "state.key")
    return Agent(store=store, providers=Providers(env=env or {"LUMA_SHOP_STORES_JSON": json.dumps(STORES)}), use_model=False, **kw), store


class ShoppingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.agent, self.store = agent_with(Path(self.temp.name))
        self.agent.enable("browser", True)
        self.agent._browser = FakeBrowser(LISTINGS)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_relevance_skips_accessories_and_wrong_generations(self):
        self.assertGreater(shopping.relevance("airpods pro 2", "Apple AirPods Pro 2 Wireless"), 0.9)
        self.assertLess(shopping.relevance("airpods pro 2", "Silicone Case for AirPods Pro 2"), 0.6)
        self.assertLess(shopping.relevance("airpods pro 2", "AirPods Pro (1st generation)"), 0.6)
        self.assertEqual(shopping.parse_price("$1,299.50"), 1299.5)

    def test_cheapest_real_match_wins_and_steps_are_shown(self):
        result = self.agent.chat("find me the cheapest AirPods Pro 2")
        self.assertEqual(result["kind"], "shopping")
        self.assertEqual([o["store"] for o in result["offers"]], ["Store C", "Store B", "Store A"])
        self.assertEqual(result["best"]["price"], 174.95)
        self.assertIn("Cheapest I found", result["text"])
        self.assertIn("$174.95 at Store C", result["text"])
        view = self.agent.activity.view()
        self.assertEqual(view["state"], "done")
        self.assertTrue(any("Store B" in s["text"] for s in view["steps"]))
        self.assertEqual(self.agent.activity.image(), b"\xff\xd8\xff")
        self.assertEqual(self.agent.feed.list()[0]["kind"], "deal")

    def test_price_limit_and_a_store_that_is_down(self):
        self.agent._browser = FakeBrowser(LISTINGS, broken={"c.example"})
        result = self.agent.chat("compare prices for airpods pro 2 under $195")
        self.assertEqual([o["store"] for o in result["offers"]], ["Store B"])
        self.assertEqual(result["skipped"][0]["store"], "Store C")

    def test_stop_ends_the_search_and_nothing_is_bought(self):
        def stop_on_second(url):
            if "b.example" in url: self.agent.activity.stop()
        self.agent._browser = FakeBrowser(LISTINGS, on_open=stop_on_second)
        result = self.agent.chat("find me the cheapest airpods pro 2")
        self.assertEqual(result["state"], "stopped")
        self.assertEqual(self.agent.activity.view()["state"], "stopped")
        self.assertFalse(any("c.example" in u for u in self.agent._browser.opened))

    def test_everyday_price_questions_go_to_the_stores(self):
        for text in ["How much are AirPods Pro 2 going for these days?", "what's the price of airpods pro 2 right now?"]:
            self.assertEqual(self.agent.chat(text)["kind"], "shopping", text)
        self.assertIsNone(next((p.fullmatch("how much is 15% of 80") for p in Agent.SHOP_PATTERNS if p.fullmatch("how much is 15% of 80")), None))

    def test_pause_holds_the_job_until_resume(self):
        activity = Activity()
        activity.start("shopping", "x")
        activity.pause()
        done = []
        worker = threading.Thread(target=lambda: (activity.step("next"), done.append(1)))
        worker.start()
        time.sleep(0.3)
        self.assertEqual(done, [])
        activity.resume()
        worker.join(2)
        self.assertEqual(done, [1])

    def test_adding_to_cart_waits_for_the_owner_then_checks_it_landed(self):
        self.agent.chat("find me the cheapest airpods pro 2")
        pending = self.agent.chat("add the cheapest one to my cart")
        self.assertEqual(pending["state"], "pending")
        self.assertEqual(pending["tool"], "shop.add_to_cart")
        self.assertEqual(pending["arguments"]["store"], "Store C")
        self.assertEqual(self.agent._browser.clicked, [])
        done = self.agent.confirm(pending["action"], pending["confirm_token"])
        self.assertTrue(done["verified"])
        self.assertIn("Checkout is yours", done["summary"])

    def test_cart_rule_set_to_allow_skips_the_question_but_texts_never_can(self):
        self.agent.rules.set("cart", "allow")
        self.agent.chat("find me the cheapest airpods pro 2")
        done = self.agent.chat("add it to my cart")
        self.assertEqual(done["state"], "succeeded")
        with self.assertRaises(ValueError): self.agent.rules.set("texts", "allow")
        with self.assertRaises(ValueError): self.agent.rules.set("spend", "allow")

    def test_blocked_browsing_is_refused(self):
        self.agent.rules.set("browse", "block")
        with self.assertRaises(ValueError) as caught:
            self.agent.propose("shop.compare", {"query": "airpods", "max_price": 0})
        self.assertIn("Rules", str(caught.exception))

    def test_watch_the_price_makes_a_helper_that_reports_a_drop(self):
        self.agent.chat("find me the cheapest airpods pro 2")
        made = self.agent.chat("watch the price and tell me when it drops below $180")
        helper = made["helper"]
        self.assertEqual(helper["params"], {"query": "airpods pro 2", "target": 180.0})
        outcome = self.agent.helpers.run(helper["id"])
        self.assertIn("under your $180 target", outcome["notify"])
        event = self.agent.helpers.pop_event()
        self.assertIn("Price drop", event["text"])
        again = self.agent.helpers.run(helper["id"])
        self.assertIsNone(again.get("notify"))  # same price, no second buzz
        row = self.store.get("helper", helper["id"])
        self.assertEqual(row["runs"], 2)
        self.assertGreater(row["next_run"], time.time() + 3600)


class FakeIMAP:
    mailbox = []
    appended = []

    def __init__(self, host, port): self.host = host
    def login(self, user, secret):
        if secret != "abcdabcdabcdabcd": import imaplib; raise imaplib.IMAP4.error("bad")
    def select(self, box, readonly=False): return ("OK", [b"2"])
    def list(self): return ("OK", [b'(\\HasNoChildren \\Drafts) "/" "[Gmail]/Drafts"', b'(\\HasNoChildren) "/" "INBOX"'])
    def append(self, folder, flags, when, data): FakeIMAP.appended.append((folder, flags, data)); return ("OK", [b""])
    def logout(self): pass
    def uid(self, command, *args):
        if command == "SEARCH":
            ids = [m["uid"] for m in self.mailbox if not ("UNSEEN" in args and m["seen"])]
            return ("OK", [" ".join(ids).encode()])
        wanted = args[0].decode() if isinstance(args[0], bytes) else args[0]
        message = next(m for m in self.mailbox if m["uid"] == wanted)
        raw = message["raw"]
        if "BODY.PEEK[]" in args[1]:
            return ("OK", [(f"1 (UID {message['uid']} BODY[] {{{len(raw)}}}".encode(), raw), b")"])
        head, _, body = raw.partition(b"\r\n\r\n")
        flags = "\\Seen" if message["seen"] else ""
        return ("OK", [(f"1 (UID {message['uid']} FLAGS ({flags}) BODY[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)] {{{len(head)}}}".encode(), head + b"\r\n"),
                       (f" BODY[TEXT]<0> {{{len(body)}}}".encode(), body), b")"])


class FakeSMTP:
    sent = []

    def __init__(self, host, port): pass
    def login(self, user, secret): pass
    def send_message(self, message): FakeSMTP.sent.append(message); return {}
    def quit(self): pass


def raw_email(uid, sender, subject, body, seen=False):
    text = (f"From: {sender}\r\nSubject: {subject}\r\nDate: Tue, 13 Oct 2026 09:00:00 -0400\r\nMessage-ID: <m{uid}@example.com>\r\n"
            f"Content-Type: text/plain; charset=utf-8\r\n\r\n{body}\r\n")
    return {"uid": uid, "seen": seen, "raw": text.encode()}


class MailAndCalendarTests(unittest.TestCase):
    ICS = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "BEGIN:VEVENT", "UID:1", "DTSTART;TZID=America/New_York:20261013T150000", "DTEND;TZID=America/New_York:20261013T160000", "SUMMARY:Dentist", "END:VEVENT",
        "BEGIN:VEVENT", "UID:2", "DTSTART;VALUE=DATE:20261013", "SUMMARY:Mom's birthday", "END:VEVENT",
        "BEGIN:VEVENT", "UID:3", "DTSTART:20260929T223000Z", "DURATION:PT1H", "RRULE:FREQ=WEEKLY;BYDAY=TU", "SUMMARY:Soccer practice", "END:VEVENT",
        "BEGIN:VEVENT", "UID:4", "DTSTART:20261014T130000Z", "SUMMARY:Tomorrow thing", "END:VEVENT",
        "END:VCALENDAR", ""])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = 1791896400  # Tue 13 Oct 2026, 09:00 in New York
        self.agent, self.store = agent_with(Path(self.temp.name), now=lambda: self.now)
        self.agent.mail.imap_factory = FakeIMAP
        self.agent.mail.smtp_factory = FakeSMTP
        FakeIMAP.mailbox = [raw_email("1", "Sam Rivera <sam@example.com>", "Dinner Friday?", "Are we still on for dinner Friday at 7?"),
                            raw_email("2", "Deals <promo@shop.example>", "50% off", "Big sale", seen=True)]
        FakeIMAP.appended, FakeSMTP.sent = [], []
        self.agent.calendar.fetcher = lambda url: self.ICS

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_email_needs_connecting_first(self):
        reply = self.agent.chat("check my email")
        self.assertEqual(reply["section"], "apps")

    def test_connect_check_and_reply_with_approval(self):
        with self.assertRaises(RuntimeError):
            self.agent.mail.connect("me@gmail.com", "wrong password here")
        status = self.agent.mail.connect("me@gmail.com", "abcd abcd abcd abcd")
        self.assertEqual(status["provider"], "gmail")
        self.assertNotIn("abcd", json.dumps(self.store.setting("mail_account")).replace("secret_b64", ""))
        self.agent.enable("mail", True)
        inbox = self.agent.chat("check my email")
        self.assertEqual([m["subject"] for m in inbox["messages"]], ["Dinner Friday?"])
        self.assertIn("1 unread", inbox["text"])
        pending = self.agent.chat("reply to Sam saying yes, see you at 7")
        self.assertEqual(pending["state"], "pending")
        self.assertEqual(pending["tool"], "mail.send")
        self.assertEqual(pending["arguments"]["to"], "sam@example.com")
        self.assertEqual(pending["arguments"]["subject"], "Re: Dinner Friday?")
        self.assertIn("Yes, see you at 7", pending["arguments"]["body"])
        self.assertEqual(FakeIMAP.appended[0][0], '"[Gmail]/Drafts"')
        self.assertEqual(FakeSMTP.sent, [])
        done = self.agent.confirm(pending["action"], pending["confirm_token"])
        self.assertEqual(done["state"], "succeeded")
        sent = FakeSMTP.sent[0]
        self.assertEqual(sent["To"], "sam@example.com")
        self.assertEqual(sent["In-Reply-To"], "<m1@example.com>")

    def test_emails_never_get_signed_with_a_made_up_name(self):
        self.agent.use_model = True
        self.agent.planner = lambda *a: {"type": "reply", "text": "Hey Sam,\nYes, see you at 7!\nBest, Alex"}
        self.assertTrue(self.agent.write_email("Sam", "yes see you at 7").endswith("Best,"))
        self.agent.set_profile({**self.agent.profile, "name": "Xiena"})
        self.agent.planner = lambda *a: {"type": "reply", "text": "Hey Sam,\nYes!\nBest, Xiena"}
        self.assertTrue(self.agent.write_email("Sam", "yes").endswith("Best, Xiena"))

    def test_inbox_helper_only_buzzes_for_new_mail(self):
        self.agent.mail.connect("me@gmail.com", "abcdabcdabcdabcd")
        self.agent.enable("mail", True)
        made = self.agent.chat("every morning go through my inbox")
        self.assertEqual(made["helper"]["kind"], "inbox_digest")
        self.assertEqual(made["helper"]["at"], "08:00")
        first = self.agent.helpers.run(made["helper"]["id"])
        self.assertIn("1 new email", first["notify"])
        second = self.agent.helpers.run(made["helper"]["id"])
        self.assertIsNone(second.get("notify"))
        self.assertEqual(self.agent.feed.list()[0]["kind"], "inbox")

    def test_plan_my_week_reads_the_real_calendar_or_asks_for_it(self):
        ask = self.agent.chat("plan my week")
        self.assertEqual(ask["section"], "apps")
        self.assertIn("Connect your calendar", ask["text"])
        self.assertNotIn("events", ask)
        self.agent.calendar.connect("webcal://calendar.example.com/private/basic.ics")
        self.agent.enable("calendar", True)
        week = self.agent.chat("can you plan my week")
        titles = [e["title"] for e in week["events"]]
        self.assertIn("Dentist", titles)
        self.assertIn("Tomorrow thing", titles)
        self.assertEqual(titles.count("Soccer practice"), 1)  # weekly, so once this week
        self.assertEqual(week["kind"], "agenda")
        tomorrow = self.agent.chat("plan tomorrow")
        self.assertEqual([e["title"] for e in tomorrow["events"]], ["Tomorrow thing"])

    def test_calendar_today_including_repeats(self):
        self.agent.calendar.connect("webcal://calendar.example.com/private/basic.ics")
        self.agent.enable("calendar", True)
        today = self.agent.chat("what's on my calendar today?")
        titles = [e["title"] for e in today["events"]]
        self.assertEqual(titles, ["Mom's birthday", "Dentist", "Soccer practice"])
        self.assertIn("Dentist at 3:00 PM", today["text"])
        self.assertIn("Soccer practice at 6:30 PM", today["text"])
        tomorrow = self.agent.chat("what do I have tomorrow")
        self.assertEqual([e["title"] for e in tomorrow["events"]], ["Tomorrow thing"])
        with self.assertRaises(ValueError):
            self.agent.calendar.connect("http://insecure.example.com/cal.ics")


class FeedbackThreadsAndServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.agent, self.store = agent_with(Path(self.temp.name))

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_feedback_note_becomes_a_preference(self):
        card = self.agent.feed.add({"kind": "feed", "title": "Your Instagram", "body": "..."})
        result = self.agent.feedback(card["id"], "down", "only show me posts from close friends")
        self.assertIn("close friends", result["learned"]["text"])
        self.assertIn("close friends", self.store.recall("instagram friends posts")[0]["text"])
        self.assertEqual(self.store.get("card", card["id"])["feedback"], "down")

    def test_side_chats_keep_their_own_history(self):
        side = self.agent.new_thread()
        self.agent.chat("remember the wifi password hint is the dog's name", thread=side["id"])
        self.agent.chat("tasks")
        self.assertEqual(len(self.agent.threads[side["id"]]), 2)
        self.assertTrue(all("wifi" not in m["content"] for m in self.agent.threads["main"]))
        self.assertTrue(self.agent.thread_titles[side["id"]].startswith("remember the wifi"))
        self.assertEqual(self.agent.transcripts[side["id"]][0]["role"], "you")
        with self.assertRaises(ValueError): self.agent.chat("hi", thread="nope")

    def test_ideas_offer_next_steps(self):
        ideas = self.agent.ideas()
        self.assertTrue(any(i["say"] == "connect my gmail" for i in ideas))  # two clicks through the apps hub
        self.assertTrue(all(i["title"] and i["say"] for i in ideas))

    def test_home_activity_rules_and_feedback_over_http(self):
        from luma.control.server import make_server
        server = make_server(self.agent, 0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}"
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def post(path, body):
            request = urllib.request.Request(base + path, data=json.dumps(body).encode(), headers={"Origin": base, "Content-Type": "application/json"})
            with client.open(request) as r: return json.load(r)
        try:
            client.open(base + "/desktop/").read()
            with client.open(base + "/api/home") as r: home = json.load(r)
            for key in ["today", "cards", "approvals", "helpers", "ideas", "activity", "threads", "rules", "connections"]:
                self.assertIn(key, home)
            self.assertEqual(next(r for r in home["rules"] if r["id"] == "texts")["choices"], ["ask", "block"])
            rules = post("/api/rules", {"id": "posts", "value": "block"})["rules"]
            self.assertEqual(next(r for r in rules if r["id"] == "posts")["value"], "block")
            helper = post("/api/helpers/create", {"kind": "price_watch", "query": "standing desk", "target": 300, "every": "daily"})["helper"]
            self.assertEqual(helper["title"], "Price of standing desk under $300")
            self.assertTrue(post("/api/helpers/update", {"id": helper["id"], "enabled": False})["helper"]["enabled"] is False)
            thread = post("/api/threads/new", {})
            reply = post("/api/chat", {"text": "tasks", "thread": thread["id"]})
            self.assertEqual(reply["thread"], thread["id"])
            with client.open(base + "/api/threads/" + thread["id"]) as r:
                self.assertEqual(len(json.load(r)["messages"]), 2)
            self.agent.activity.start("shopping", "test")
            self.agent.activity.shot("/9j/", "https://a.example", "A")
            self.assertEqual(post("/api/activity/control", {"action": "pause"})["activity"]["state"], "paused")
            with client.open(base + "/api/activity/shot") as r:
                self.assertEqual(r.headers["Content-Type"], "image/jpeg")
            self.assertEqual(post("/api/activity/control", {"action": "stop"})["activity"]["state"], "stopping")
        finally:
            server.control_context.stop.set()
            server.shutdown()
            server.server_close()


@unittest.skipUnless(HAS_BROWSER, "playwright not installed")
class RealBrowserShoppingTests(unittest.TestCase):
    """The real thing: headless Chromium reads three differently built store pages."""

    @classmethod
    def setUpClass(cls):
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(FIXTURES))
        handler.log_message = lambda *a: None
        cls.site = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.site.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.site.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.site.shutdown()
        cls.site.server_close()

    def setUp(self):
        from luma.integrations.browser import BrowserSession
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        stores = [{"name": "Gadget Mart", "search": self.base + "/store-jsonld.html?q={q}"},
                  {"name": "Shop Two", "search": self.base + "/store-microdata.html?q={q}"},
                  {"name": "Third Store", "search": self.base + "/store-tiles.html?q={q}"}]
        self.agent, self.store = agent_with(root, env={"LUMA_SHOP_STORES_JSON": json.dumps(stores)})
        self.agent._browser = BrowserSession(root / "profile", allow_local=True)
        self.agent.enable("browser", True)

    def tearDown(self):
        self.agent._browser.close()
        self.store.close()
        self.temp.cleanup()

    def test_compare_three_real_pages_then_add_to_cart(self):
        result = self.agent.chat("find me the cheapest airpods pro 2 under $250")
        self.assertEqual([(o["store"], o["price"]) for o in result["offers"]],
                         [("Third Store", 174.95), ("Shop Two", 189.0), ("Gadget Mart", 199.99)])
        self.assertTrue(result["offers"][0]["url"].startswith(self.base + "/product.html"))
        self.assertTrue(self.agent.activity.image().startswith(b"\xff\xd8"))
        pending = self.agent.chat("add the cheapest one to my cart")
        done = self.agent.confirm(pending["action"], pending["confirm_token"])
        self.assertTrue(done["verified"], done)
        page = self.agent.browser.read()["text"]
        self.assertIn("Added to cart", page)
        self.assertNotIn("ORDER PLACED", page)

    def test_owner_drives_lumas_browser_from_the_window(self):
        browser = self.agent.browser
        browser.open(self.base + "/shop.html")
        frame = browser.frame()
        self.assertTrue(base64.b64decode(frame["jpeg_base64"]).startswith(b"\xff\xd8"))
        self.assertEqual(frame["title"], "Headphones")
        browser.drive("key", {"key": "Tab"})
        browser.drive("type", {"text": "earbuds"})
        landed = browser.drive("key", {"key": "Enter"})
        self.assertIn("q=earbuds", landed["url"])
        self.assertNotIn("q=", browser.drive("back")["url"])
        with self.assertRaises(ValueError):
            browser.drive("key", {"key": "Meta+Q"})

    def test_a_taught_task_replays_by_what_things_say_and_still_asks_before_buying(self):
        from luma.agent.taught import Recorder
        browser = self.agent.browser
        browser.open(self.base + "/shop.html")
        teach = Recorder(self.base + "/shop.html")
        browser.drive("key", {"key": "Tab"})
        typed = browser.drive("type", {"text": "earbuds"})
        self.assertEqual(typed["target"]["label"], "Search the store")
        teach.add("type", {"text": "earbuds"}, typed)
        teach.add("key", {"key": "Enter"}, browser.drive("key", {"key": "Enter"}))
        teach.add("click", {}, {"target": {"tag": "button", "type": "", "label": "Add to cart", "name": "", "placeholder": "", "href": ""}})
        teach.add("click", {}, {"target": {"tag": "button", "type": "", "label": "Buy now", "name": "", "placeholder": "", "href": ""}})
        self.assertEqual([s["do"] for s in teach.steps], ["type", "click", "click"])
        self.assertTrue(teach.steps[0]["submit"])
        saved = self.agent.taught.save("buy my earbuds", teach)
        with self.assertRaises(ValueError):
            self.agent.taught.save("Buy my earbuds", teach)
        result = self.agent.chat("run buy my earbuds")
        self.assertEqual(result["state"], "pending")  # "Buy now" waits for the owner, taught or not
        self.assertIn("needs your OK", result["text"])
        page = browser.read()
        self.assertIn("q=earbuds", page["url"])
        self.assertIn("In cart (1)", page["text"])
        self.assertNotIn("ORDER PLACED", page["text"])
        self.assertEqual(self.agent.taught.list()[0]["id"], saved["id"])

    def test_a_taught_enter_that_would_send_a_form_waits_for_the_owner(self):
        from luma.agent.taught import Recorder
        teach = Recorder(self.base + "/checkout-form.html")
        note = {"tag": "input", "type": "", "label": "Gift note", "name": "note", "placeholder": "", "href": ""}
        teach.add("click", {}, {"target": note})
        teach.add("key", {"key": "Enter"}, {"target": note})
        self.assertEqual([s["do"] for s in teach.steps], ["click", "key"])
        self.agent.taught.save("checkout", teach)
        result = self.agent.chat("run checkout")
        self.assertTrue(result.get("handoff"))
        self.assertIn("presses Enter", result["text"])
        self.assertNotIn("ORDER PLACED", self.agent.browser.read()["text"])

    def test_a_field_inside_a_frame_that_looks_secret_is_never_kept(self):
        self.agent.browser.open(self.base + "/secret-frame.html")
        import time; time.sleep(0.5)
        focused = self.agent.browser.focused()
        self.assertEqual(focused["name"], "login_secret")
        self.assertTrue(focused["secret"])
        from luma.agent.taught import Recorder
        teach = Recorder(self.base + "/secret-frame.html")
        teach.add("type", {"text": "123456"}, {"target": focused})
        teach.add("type", {"text": "hunter2"}, {"target": None})
        self.assertNotIn("123456", str(teach.steps))
        self.assertNotIn("hunter2", str(teach.steps))

    def test_a_taught_task_never_keeps_a_password(self):
        from luma.agent.taught import Recorder
        teach = Recorder(self.base + "/login.html")
        secret = {"tag": "input", "type": "password", "label": "", "name": "pw", "placeholder": "", "href": ""}
        teach.add("type", {"text": "hunter2"}, {"target": secret})
        teach.add("type", {"text": "more"}, {"target": secret})
        self.assertEqual(teach.steps, [{"do": "type", "target": secret, "text": "", "secret": True}])
        self.assertNotIn("hunter2", str(self.agent.taught.save("sign in", teach)))

    def test_add_to_cart_finds_the_button_far_down_a_busy_page_and_remembers_it(self):
        args = {"store": "Amazon", "title": "Apple AirPods Pro (2nd Generation)", "price": "$129.35",
                "url": self.base + "/product-amazonish.html"}
        done = self.agent._add_to_cart(args)
        self.assertTrue(done["verified"], done)
        self.assertEqual(self.agent.store.setting("cart_buttons")["127.0.0.1"], "#add-to-cart-button")
        again = self.agent._add_to_cart(args)  # tries what worked first
        self.assertTrue(again["verified"])

    def test_add_to_cart_hands_over_instead_of_giving_up(self):
        done = self.agent._add_to_cart({"store": "Shoe Shop", "title": "Running Shoes", "price": "$80",
                                        "url": self.base + "/product-nobutton.html"})
        self.assertTrue(done["handoff"])
        self.assertIn("couldn't press Add to cart on Shoe Shop", done["text"])  # (no screen here to show the page on)
        self.assertEqual(self.agent.pending_handoff["store"], "Shoe Shop")

    def test_search_the_web_for_free_in_lumas_browser(self):
        self.agent.providers.env["LUMA_SEARCH_URL"] = self.base + "/search.html?q={q}"
        result = self.agent.search_web("raleigh weather")
        self.assertEqual([r["url"] for r in result["results"]], ["https://weather.example/raleigh", "https://news.example/story"])
        self.assertEqual(result["results"][0]["snippet"], "Sunny with a high of 72.")

    def test_pictures_come_from_the_store_page(self):
        from luma.skills import shopping

        class Steps:
            def step(self, *args, **kwargs): pass
            def shot(self, *args, **kwargs): pass
            def results(self, *args, **kwargs): pass

        stores = [{"id": "lazy", "name": "Lazy Store", "search": self.base + "/store-lazy.html?q={q}"}]
        result = shopping.compare("airpods pro 2", self.agent.browser, Steps(), stores)
        offers = {o["title"]: o for o in result["offers"]}
        lazy = offers["Apple AirPods Pro 2 Lazy Loaded"]
        self.assertEqual(lazy["image"], self.base + "/pic.png")  # the real picture behind the lazy-load placeholder
        self.assertNotIn("image_shot", lazy)
        bare = offers["Apple AirPods Pro 2 No Picture Address"]
        self.assertTrue(bare["image_shot"].startswith("data:image/jpeg;base64,/9j/"))  # taken straight off the page
        self.assertNotIn("pic", bare)
        self.assertNotIn("image_weak", bare)


if __name__ == "__main__":
    unittest.main()
