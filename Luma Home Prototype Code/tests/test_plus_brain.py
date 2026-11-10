"""Luma Plus at home: the Super Intelligence through Luma Cloud, with no key of the owner's.

The home's real code talks to a stand-in Luma Cloud (tests/plus_relay.mjs: the relay's own code on an in-memory database,
with a made-up Claude behind it), run under node on this computer. Skipped where node isn't installed or the relay's code
isn't beside the app. Nothing leaves the machine and no key is real."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from luma.agent.runtime import Agent
from luma.integrations.luma_cloud import CloudError, LumaCloud
from luma.llm import brain, cloud, cloudbrain, inference, kimi, plus
from luma.memory.store import Store

ROOT = Path(__file__).resolve().parents[1]
RELAY = ROOT / "tests" / "plus_relay.mjs"
NODE = shutil.which("node")
HAVE_RELAY = bool(NODE) and (ROOT.parent / "api" / "_lib" / "luma-cloud.js").exists()

sys.path.insert(0, str(ROOT / "scripts"))
import si_lab  # noqa: E402
from cloud_brain_on import setUpModule, tearDownModule  # noqa: F401  the cloud brain is parked; these tests turn it on for themselves

HOME = {"type": "reply", "text": "home brain"}
REPLY = {"type": "reply", "text": "I'm here. Tell me about your day, Marvin."}
SAID = "my sister Dana hasn't called since the funeral"
MESSAGES = [{"role": "user", "content": SAID}]
TOOLS = {"tasks.create": {"description": "Make a reminder", "fields": {"title": "string", "due": "string"}}}
LIFE = [{"life": True, "text": "- Your name is Marvin\n- You live in Tucson"}]


def next_month():
    """Seconds from now until a couple of days into next month."""
    now = datetime.now(timezone.utc)
    first = datetime(now.year + (now.month == 12), now.month % 12 + 1, 1, tzinfo=timezone.utc)
    return (first - now).total_seconds() + 2 * 86400


@unittest.skipUnless(HAVE_RELAY, "needs node and the relay's code (api/_lib/luma-cloud.js)")
class WithLumaCloud(unittest.TestCase):
    people = 0

    @classmethod
    def setUpClass(cls):
        cls.relay = subprocess.Popen([NODE, str(RELAY)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, cwd=str(ROOT))
        cls.url = f"http://127.0.0.1:{json.loads(cls.relay.stdout.readline())['port']}"

    @classmethod
    def tearDownClass(cls):
        cls.relay.terminate()
        cls.relay.wait(timeout=10)
        cls.relay.stdout.close()

    def lab(self, **ask):
        request = urllib.request.Request(self.url + "/__lab", data=json.dumps(ask).encode() if ask else None,
                                         headers={"Content-Type": "application/json"}, method="POST" if ask else "GET")
        with urllib.request.urlopen(request, timeout=10) as answer:
            return json.load(answer)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.lab(forget=True, plus=False, status=200, reply=REPLY, out=24, pause_ms=0, step_ms=0, ahead_ms=0,
                 usage={"input_tokens": 150, "cache_read_input_tokens": 3200, "cache_creation_input_tokens": 300},
                 env={"LUMA_PLUS_BRAIN_BUDGET_CENTS": "400", "LUMA_BRAIN_WORDS": "1", "LUMA_BRAIN_CALLS_PER_MINUTE": "600"})
        brain.init(self.store)
        self.cloud = LumaCloud(self.store, env={"LUMA_CLOUD_URL": self.url})
        WithLumaCloud.people += 1
        self.cloud.create_account("Marvin", f"marvin{WithLumaCloud.people}@example.com", "a long enough password")
        brain.use_plus(self.cloud)
        self.addCleanup(brain.use_plus, None)

    def subscribe(self, yes=True):
        """They subscribed to Plus (and the app looked their account up again); with yes, they said yes on the yes screen."""
        self.lab(plus=True)
        self.cloud.account(refresh=True)
        if yes:
            brain.set_plus(True)

    def ask(self, memories=(), tools=None, **more):
        with mock.patch.object(inference, "plan", return_value=dict(HOME)) as home:
            out = brain.plan(list(MESSAGES), list(memories), tools or {}, "friend", **more)
        return out, home.call_count


class OffUntilTheySayYes(WithLumaCloud):
    def test_paying_isnt_the_yes(self):
        self.subscribe(yes=False)
        view = plus.view(self.store, self.cloud)
        self.assertEqual((view["member"], view["available"], view["consent"], view["on"]), (True, True, False, False))
        self.assertTrue(view["ask"], "the app asks once, on the yes screen")
        self.assertFalse(brain.cloud_on())
        out, home = self.ask(LIFE)
        self.assertEqual((out, home), (HOME, 1))
        self.assertEqual(self.lab()["seen"], [], "nothing left the home")

    def test_not_now_is_an_answer_and_luma_asks_once(self):
        self.subscribe(yes=False)
        self.assertTrue(plus.view(self.store, self.cloud)["ask"])
        brain.set_plus(False)
        view = plus.view(self.store, self.cloud)
        self.assertEqual((view["ask"], view["can_turn_on"], view["on"]), (False, True, False))
        self.assertEqual(view["screen"]["words"], plus.WORDS, "Settings still offers it, behind the same screen")
        self.assertEqual(self.ask(), (HOME, 1))
        self.assertEqual(self.lab()["seen"], [])

    def test_the_yes_screen_says_what_leaves_where_it_goes_whats_kept_and_how_to_turn_it_off(self):
        screen = plus.screen()
        self.assertEqual([part["head"] for part in screen["parts"]], ["What leaves your home", "Where it goes", "What's kept", "How to turn it off"])
        leaves, goes, kept, off = (part["text"] for part in screen["parts"])
        for must in ("what you say", "conversation", "knows about you", "read", "photo"):
            self.assertIn(must, leaves)
        self.assertIn("passwords", leaves)
        for must in ("Luma Cloud", "Claude", "Anthropic"):
            self.assertIn(must, goes)
        for must in ("counts", "doesn't store", "train", "flag"):
            self.assertIn(must, kept)
        self.assertIn("Turn off", off)
        self.assertEqual(screen["words"], plus.WORDS)
        self.assertEqual((screen["yes"], screen["no"]), ("Yes, turn it on", "Not now"))
        self.assertNotIn("—", json.dumps(screen, ensure_ascii=False))

    def test_a_yes_sends_the_turn_through_luma_cloud_on_lumas_own_key(self):
        self.subscribe()
        view = brain.status()["plus"]
        self.assertTrue(view["on"])
        self.assertFalse(view["ask"])
        self.assertEqual(brain.cloud_route(), "plus")
        heard = []
        out, home = self.ask(LIFE, TOOLS, on_text=heard.append)
        self.assertEqual((out["text"], home), (REPLY["text"], 0))
        self.assertEqual("".join(heard), REPLY["text"], "the words were said as they came")
        state = self.lab()
        call = state["seen"][0]
        self.assertEqual(call["key"], "lumas-own-key-for-claude")
        self.assertIsNone(call["authorization"], "this Luma's sign-in stops at Luma Cloud")
        self.assertEqual(call["body"]["model"], "claude-sonnet-5-5", "Auto: the everyday model for talk")
        self.assertEqual(call["body"]["output_config"]["effort"], "medium")
        self.assertIn("Tucson", json.dumps(call["body"]["system"]), "what Luma knows about them goes along")
        self.assertEqual([block["cache_control"] for block in call["body"]["system"]], [{"type": "ephemeral"}] * 2, "and is read once, then cached")
        self.assertNotIn("fallbacks", call["body"])
        self.assertIsNone(call["beta"])
        self.assertEqual(state["used"][-1]["calls"], 1)
        self.assertNotIn("Dana", state["tables"], "Luma Cloud kept the counts and not a word")
        self.assertNotIn("Tucson", state["tables"])
        self.assertGreater(brain.cache_share(), 0.8, "the home's meter sees what was read from the cache")

    def test_a_hard_ask_gets_the_strongest_brain_and_more_thinking(self):
        self.subscribe()
        self.ask(effort="high")
        body = self.lab()["seen"][0]["body"]
        self.assertEqual((body["model"], body["output_config"]["effort"]), ("claude-opus-5-5", "high"))

    def test_someone_without_plus_cant_turn_it_on(self):
        before = self.cloud.account(refresh=True)
        with self.assertRaises(CloudError) as caught:
            brain.set_plus(True)
        self.assertEqual(caught.exception.code, "plus")
        self.assertFalse(self.store.setting(plus.SETTING, False))
        after = self.store.setting("luma_cloud_account")
        self.assertEqual((after.get("plan"), after.get("texts_left")), (before.get("plan"), before.get("texts_left")), "their texting numbers weren't touched")
        self.assertFalse(plus.view(self.store, self.cloud)["ask"], "and Luma doesn't ask someone who hasn't got it")

    def test_the_yes_can_be_taken_back_and_luma_thinks_at_home_right_away(self):
        self.subscribe()
        self.assertFalse(brain.set_plus(False)["plus"]["on"])
        self.assertEqual(self.lab()["accounts"][-1]["consent"], False)
        self.assertEqual(self.ask(), (HOME, 1))
        self.assertEqual(self.lab()["seen"], [])

    def test_it_turns_off_at_home_even_when_luma_cloud_cant_be_reached(self):
        self.subscribe()
        self.cloud.env = {"LUMA_CLOUD_URL": "http://127.0.0.1:9"}
        self.assertFalse(brain.set_plus(False)["plus"]["on"])
        self.assertTrue(self.store.setting(plus.TAKE_BACK), "and Luma Cloud is told as soon as it answers")
        self.cloud.env = {"LUMA_CLOUD_URL": self.url}
        plus.finish(self.store, self.cloud)
        self.assertFalse(self.store.setting(plus.TAKE_BACK))
        self.assertEqual(self.lab()["accounts"][-1]["consent"], False)

    def test_a_yes_taken_back_somewhere_else_is_respected(self):
        self.subscribe()
        self.lab(unsay=True)
        self.assertEqual(self.ask(), (HOME, 1), "Luma Cloud said no, so home answered")
        self.assertFalse(self.store.setting(plus.SETTING))
        view = plus.view(self.store, self.cloud)
        self.assertEqual((view["on"], view["ask"], view["can_turn_on"]), (False, False, True), "it's off, Settings can turn it on again, and Luma doesn't nag")
        self.assertEqual(self.ask(), (HOME, 1))
        self.assertEqual(len(self.lab()["seen"]), 0)

    def test_when_the_words_change_luma_asks_again(self):
        self.subscribe()
        self.lab(env={"LUMA_BRAIN_WORDS": "2"})
        self.assertEqual(self.ask(), (HOME, 1))
        self.assertEqual(len(self.lab()["seen"]), 0)
        view = plus.view(self.store, self.cloud)
        self.assertEqual((view["on"], view["ask"], view["update"]), (False, False, True), "this Luma only has the old words: it says to update, it doesn't ask")
        with self.assertRaises(CloudError) as caught:
            brain.set_plus(True)
        self.assertEqual(caught.exception.code, "words")
        self.assertFalse(self.store.setting(plus.SETTING))

    def test_their_own_key_still_works_and_plus_goes_first(self):
        self.store.set_setting("brain_cloud_key", "sk-ant-their-own")
        self.store.set_setting("brain_cloud", True)
        self.assertEqual(brain.cloud_route(), "own")
        self.assertEqual(brain.cloud_key(), "sk-ant-their-own")
        self.subscribe()
        self.assertEqual(brain.cloud_route(), "plus")
        self.assertIsInstance(brain.cloud_key(), cloud.Relay)
        self.assertEqual(brain.cloud_key("anthropic"), "sk-ant-their-own")
        brain.set_plus(False)
        self.assertEqual(brain.cloud_route(), "own")


class TheMonthsBudget(WithLumaCloud):
    def setUp(self):
        super().setUp()
        self.lab(env={"LUMA_PLUS_BRAIN_BUDGET_CENTS": "1"}, usage={"input_tokens": 6000}, out=400)  # one turn costs 1.6 cents
        self.subscribe()

    def test_when_its_used_up_home_answers_and_luma_stops_asking(self):
        first, second, third = self.ask(), self.ask(), self.ask()
        self.assertEqual(first, (REPLY, 0))
        self.assertEqual((second, third), ((HOME, 1), (HOME, 1)))
        self.assertEqual(len(self.lab()["seen"]), 1, "the second ask was refused at Luma Cloud; the third never left home")
        self.assertFalse(brain.plus_on())
        view = brain.status()["plus"]
        self.assertEqual((view["left_share"], view["on"], view["used_up"]), (0, False, True))
        note = self.store.setting(plus.NOTE)
        self.assertEqual(note["said"], False)
        self.assertIn("used up", brain.status()["cloud"]["last_error"])

    def test_it_comes_back_when_the_month_turns(self):
        self.ask(), self.ask()
        ahead = next_month()
        self.lab(ahead_ms=int(ahead * 1000))
        self.cloud.clock = lambda: time.time() + ahead
        self.assertTrue(brain.plus_on())
        self.assertEqual(self.ask(), (REPLY, 0))


class InLuma(WithLumaCloud):
    def setUp(self):
        super().setUp()
        self.agent = Agent(store=self.store, use_model=True)
        self.agent.cloud.env = {"LUMA_CLOUD_URL": self.url}
        self.cloud = self.agent.cloud
        self.subscribe()

    def used_up(self):
        self.store.set_setting(plus.NOTE, {"month": "2026-11", "resets": "2026-12-01T00:00:00.000Z", "said": False})

    def notices(self, tries=3):
        found = []
        for _ in range(tries):
            event = self.agent.tick()
            if event and event.get("type") == "notice":
                found.append(event["text"])
        return found

    def test_luma_says_once_plainly_that_the_time_is_used_up(self):
        self.used_up()
        said = self.notices()
        self.assertEqual(len(said), 1, "once")
        self.assertIn("used up", said[0])
        self.assertIn("at home", said[0])
        self.assertIn("December", said[0])
        for pitch in ("upgrade", "buy", "more time", "subscribe", "plan", "$", "sorry"):
            self.assertNotIn(pitch, said[0].lower(), "it's news, not a pitch")
        self.assertTrue(self.store.setting(plus.NOTE)["said"])

    def test_it_waits_while_theyre_hurting(self):
        self.used_up()
        self.agent.history += [{"role": "user", "content": "my dad died last week and i can't stop crying"}, {"role": "assistant", "content": "I'm so sorry."}]
        self.assertEqual(self.notices(), [])
        self.assertFalse(self.store.setting(plus.NOTE)["said"], "it's still to be said, later")
        self.agent.history.clear()
        self.assertEqual(len(self.notices()), 1)

    def test_kids_mode_never_hears_about_it(self):
        self.used_up()
        self.agent.set_mode("kids")
        self.assertEqual(self.notices(), [])
        self.assertFalse(self.store.setting(plus.NOTE)["said"])

    def test_kids_mode_keeps_it_off_unless_a_parent_turned_it_on(self):
        self.assertTrue(brain.plus_on())
        self.agent.set_mode("kids")
        self.assertFalse(brain.plus_on())
        self.assertIsNone(brain.cloud_route())
        brain.set_plus(None, kids=True)
        self.assertTrue(brain.plus_on())
        self.assertFalse(self.agent._roomy(), "and kids mode is never told what Luma remembers")

    def test_plus_gives_the_brain_more_of_what_luma_remembers_every_turn(self):
        self.assertFalse(self.store.setting("cloud_life", False), "not the old switch: the yes screen said the life file goes along")
        self.assertTrue(self.agent._roomy())
        brain.set_plus(False)
        self.assertFalse(self.agent._roomy())

    def test_the_crisis_net_answers_at_home_before_any_brain(self):
        out = self.agent.chat("i want to kill myself")
        self.assertIn("988", out["text"])
        self.assertEqual(self.lab()["seen"], [], "not a word of it went to the cloud brain")

    def test_a_turn_in_luma_goes_through_luma_cloud(self):
        out = self.agent.chat("hey, just got off shift")
        self.assertTrue(out["text"])
        seen = self.lab()["seen"]
        self.assertGreaterEqual(len(seen), 1)
        self.assertIn("just got off shift", json.dumps(seen[0]["body"]["messages"]))
        self.assertEqual(seen[0]["key"], "lumas-own-key-for-claude")


class FromTheApp(WithLumaCloud):
    """The yes screen's two buttons, and the switch in Settings, as the desktop app presses them."""

    def setUp(self):
        super().setUp()
        import http.cookiejar
        from luma.control.server import make_server
        self.agent = Agent(store=self.store, use_model=False)
        self.agent.cloud.env = {"LUMA_CLOUD_URL": self.url}
        self.cloud = self.agent.cloud
        self.server = make_server(self.agent, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.window = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.window.open(self.base + "/desktop/").close()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.control_context.stop.set)

    def home(self):
        with self.window.open(self.base + "/api/home") as answer:
            return json.load(answer)["brain"]["plus"]

    def press(self, **body):
        request = urllib.request.Request(self.base + "/api/brain", data=json.dumps(body).encode(), headers={"Origin": self.base, "Content-Type": "application/json"})
        try:
            with self.window.open(request) as answer:
                return answer.status, json.load(answer)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def test_the_app_is_handed_the_yes_screen_once_and_the_yes_turns_it_on(self):
        self.assertFalse(self.home()["member"], "someone without Plus is shown nothing")
        self.subscribe(yes=False)
        view = self.home()
        self.assertTrue(view["ask"])
        self.assertEqual(len(view["screen"]["parts"]), 4)
        status, out = self.press(action="plus_yes")
        self.assertEqual(status, 200)
        self.assertTrue(out["brain"]["plus"]["on"])
        self.assertIn("Super Intelligence", out["brain"]["thinking_with"])
        view = self.home()
        self.assertEqual((view["on"], view["ask"], view["screen"]), (True, False, None))
        status, out = self.press(action="plus_no")
        self.assertEqual((status, out["brain"]["plus"]["on"]), (200, False))
        self.assertEqual(self.lab()["accounts"][-1]["consent"], False)

    def test_after_they_subscribe_the_app_finds_out_by_itself_and_asks(self):
        from luma.control import server
        self.assertFalse(self.home()["member"])
        self.lab(plus=True)  # they subscribed in a browser; nothing told this Luma
        self.assertFalse(self.home()["member"], "it was looked up a moment ago: not again yet")
        cached = self.store.setting("luma_cloud_account")
        self.store.set_setting("luma_cloud_account", {**cached, "checked": self.agent.clock() - server.ACCOUNT_LOOK_EVERY - 1})
        server._account_look.update(at=0.0, running=False)
        self.home()  # the app is open: this starts the look-up in the background
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not self.home()["member"]:
            time.sleep(0.05)
        view = self.home()
        self.assertEqual((view["member"], view["ask"]), (True, True))

    def test_not_now_is_remembered(self):
        self.subscribe(yes=False)
        self.press(action="plus_no")
        view = self.home()
        self.assertEqual((view["ask"], view["can_turn_on"]), (False, True))

    def test_without_plus_the_yes_is_refused_plainly(self):
        status, out = self.press(action="plus_yes")
        self.assertEqual(status, 502)
        self.assertIn("Luma Plus", out["error"])
        self.assertFalse(self.store.setting(plus.SETTING, False))

    def test_a_parent_decides_for_kids_mode_and_a_kid_cant(self):
        self.subscribe()
        self.assertEqual(self.press(action="plus_kids", on=True)[0], 200)
        self.assertTrue(self.store.setting(plus.KIDS))
        self.press(action="plus_kids", on=False)
        self.agent.set_mode("kids")
        for pressed in (self.press(action="plus_kids", on=True), self.press(action="plus_yes"), self.press(action="plus_model", model="claude-opus-5-5")):
            self.assertIn(pressed[0], (400, 403), "kids mode can't change where Luma thinks")
        self.assertFalse(self.store.setting(plus.KIDS))
        self.assertFalse(brain.plus_on())

    def test_the_owners_phone_can_turn_it_off_and_never_on(self):
        import http.cookiejar
        import ssl
        from luma.control.pairing import ensure_local_certificate
        from luma.control.server import make_server
        self.subscribe()
        ctx = self.server.control_context
        phone = make_server(self.agent, 0, context=ctx, phone_host="127.0.0.1")
        cert, key = ensure_local_certificate(Path(self.temp.name) / "tls", "192.168.10.10")
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        phone.socket = tls.wrap_socket(phone.socket, server_side=True)
        threading.Thread(target=phone.serve_forever, daemon=True).start()
        self.addCleanup(phone.server_close)
        self.addCleanup(phone.shutdown)
        base = f"https://127.0.0.1:{phone.server_port}"
        hand = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(cert))),
                                           urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

        def tap(path, data=None):
            request = urllib.request.Request(base + path, data=None if data is None else json.dumps(data).encode(), headers={"Origin": base, "Content-Type": "application/json"})
            try:
                with hand.open(request) as answer:
                    return answer.status, json.load(answer)
            except urllib.error.HTTPError as error:
                return error.code, json.load(error)
        self.assertEqual(tap("/api/phone/pair", {"token": ctx.pairing.create_invite()["token"], "name": "Their phone"})[0], 200)
        seen = tap("/api/today")[1]["device"]["plus"]
        self.assertEqual((seen["on"], seen["left_share"]), (True, 1))
        self.assertEqual(tap("/api/brain", {"action": "plus_no"})[0], 200)
        self.assertFalse(brain.plus_on())
        self.assertEqual(self.lab()["accounts"][-1]["consent"], False)
        self.assertEqual(tap("/api/brain", {"action": "plus_yes"})[0], 403, "the yes is given where the yes screen is shown")
        self.assertEqual(tap("/api/brain", {"action": "cloud_on", "key": "sk-ant-x"})[0], 403)
        self.assertFalse(brain.plus_on())
        self.assertFalse(tap("/api/today")[1]["device"]["plus"]["on"])

    def test_only_brains_plus_offers_can_be_picked(self):
        self.subscribe()
        self.assertEqual(self.press(action="plus_model", model="claude-opus-5-5")[0], 200)
        self.assertEqual(brain.cloud_pick(), "claude-opus-5-5")
        self.assertEqual(self.press(action="plus_model", model="kimi-k3.1-pro")[0], 400)
        self.assertEqual(self.press(action="plus_model", model="claude-fable-5-1")[0], 400)


class AsItComes(WithLumaCloud):
    def setUp(self):
        super().setUp()
        self.subscribe()

    def test_the_first_words_come_before_the_answer_is_over(self):
        self.lab(pause_ms=500)
        began, at = time.monotonic(), []
        out = brain.plan(list(MESSAGES), [], {}, "friend", on_text=lambda chunk: at.append(time.monotonic() - began))
        whole = time.monotonic() - began
        self.assertEqual(out["text"], REPLY["text"])
        self.assertLess(at[0], whole - 0.4, "Luma Cloud passes the answer on as it comes, not all at the end")

    def test_talking_over_luma_stops_the_brain_and_whats_heard_is_counted(self):
        self.lab(step_ms=40)
        stop = threading.Event()
        with self.assertRaises(inference.GenerationCancelled):
            brain.plan(list(MESSAGES), [], {}, "friend", on_text=lambda chunk: stop.set(), cancel_event=stop)
        deadline = time.monotonic() + 5
        state = self.lab()
        while time.monotonic() < deadline and not (state["seen"][0]["stopped"] and state["used"][-1]["calls"]):
            time.sleep(0.05)
            state = self.lab()
        self.assertTrue(state["seen"][0]["stopped"], "the brain wasn't left talking to nobody")
        self.assertFalse(state["seen"][0]["finished"])
        self.assertEqual(state["used"][-1]["calls"], 1)
        self.assertGreater(state["used"][-1]["tokens_in"], 0)

    def test_when_luma_cloud_cant_be_reached_home_answers(self):
        self.cloud.env = {"LUMA_CLOUD_URL": "http://127.0.0.1:9"}
        self.assertEqual(self.ask(), (HOME, 1))
        self.assertIn("reach", brain.status()["cloud"]["last_error"])
        self.assertTrue(self.store.setting(plus.SETTING), "a bad connection isn't a no: it's tried again next turn")

    def test_a_busy_brain_is_answered_at_home(self):
        self.lab(status=529)
        self.assertEqual(self.ask(), (HOME, 1))
        self.assertEqual(self.lab()["used"][-1]["calls"], 0, "and nothing was charged")


@unittest.skipUnless(HAVE_RELAY, "needs node and the relay's code (api/_lib/luma-cloud.js)")
class TheLab(unittest.TestCase):
    def test_the_same_talk_both_ways_and_the_two_counts_agree(self):
        report = si_lab.plus(turns=4, asks=4)
        self.assertTrue(report["meter"]["agree"], report["meter"])
        self.assertEqual(report["meter"]["relay"], report["meter"]["home"])
        self.assertEqual(report["words_kept"]["found"], 0)
        self.assertEqual(report["after_budget"], {"refused": [402, "budget"], "reached_the_brain": 0})
        self.assertTrue(report["sent_on"]["with_lumas_key"])
        self.assertEqual((report["sent_on"]["fallbacks_passed_on"], report["sent_on"]["betas_passed_on"]), (0, 0))
        self.assertEqual((report["straight"]["failed"], report["through"]["failed"]), (0, 0))
        self.assertEqual(report["straight"]["calls_per_turn"], report["through"]["calls_per_turn"], "the relay doesn't add a trip")
        self.assertIn("agree", si_lab.plus_table(report))


class TheWords(unittest.TestCase):
    """What Luma says about Plus when asked: only what Plus does today, and memory is never for sale."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.agent = Agent(store=Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k"), use_model=False)

    def test_asked_about_plus_luma_says_only_what_it_does_today(self):
        from luma.agent import understanding
        said = " ".join(step["say"] for step in understanding.WALKS["plus"]["steps"])
        self.assertIn("texts", said)
        for not_built in ("no limit", "backed up", "back up", "archive", "sync", "Super Intelligence", "unlimited"):
            self.assertNotIn(not_built, said)

    def test_a_full_memory_is_never_answered_with_a_plan(self):
        for said in ("my memory is full", "i need more storage", "can i buy more memory", "can you remember more"):
            out = self.agent._do_intent("luma_plus", said, None)
            self.assertNotIn("Plus", out["text"], said)
            self.assertIn("nothing to buy", out["text"].lower())
        from luma.agent.scenarios import INTENTS
        for phrase in INTENTS["luma_plus"]["t"]:
            self.assertNotRegex(phrase, r"memor|storage")

    def test_asking_what_plus_costs_still_gets_the_walkthrough(self):
        out = self.agent._do_intent("luma_plus", "how much is luma plus", None)
        self.assertIn("texts", out["text"])


class TheMeter(unittest.TestCase):
    """The home's own count of what the cloud brain used, which the owner's cost estimate is made from."""

    def test_a_call_that_isnt_streamed_is_counted_with_its_real_tokens(self):
        server = si_lab.StandIn.start()
        self.addCleanup(server.shutdown)
        patched = mock.patch.dict(os.environ, {"ANTHROPIC_BASE_URL": f"http://127.0.0.1:{server.server_port}"})
        patched.start()
        self.addCleanup(patched.stop)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = Store(Path(temp.name) / "s.db", Path(temp.name) / "k")
        brain.init(store)
        brain.set_cloud(True, key="sk-ant-lab", model="claude-sonnet-5-5")
        self.assertTrue(brain.rewrite("say this more clearly: hey can u remind me abt the thing", tier="standard"))
        (row,) = [row for day in store.setting("usage").values() for row in day.values()]
        self.assertEqual(row["calls"], 1)
        self.assertGreater(row["fresh"] + row["read"] + row["written"], 0, "what the brain says it was sent, not a guess")
        self.assertGreater(row["out"], 0)


class OneInterface(unittest.TestCase):
    """Every cloud brain behind the same few calls, with what each can do written down."""

    def test_each_brain_says_what_it_can_do(self):
        fields = {"context", "window", "caching", "streams", "tools", "thinking", "sees", "retry_on_decline"}
        listed = cloudbrain.catalog()
        self.assertEqual({row["via"] for row in listed}, {"own", "plus"})
        for row in listed:
            self.assertEqual(set(row["abilities"]), fields, row["name"])
        by = {(row["via"], row["name"]): row["abilities"] for row in listed}
        opus = by[("own", "claude-opus-5-5")]
        self.assertEqual((opus["context"], opus["caching"], opus["streams"], opus["sees"], opus["retry_on_decline"]), (1_000_000, True, True, True, True))
        self.assertEqual(opus["thinking"], ("low", "medium", "high"))
        self.assertEqual(opus["window"], cloud.WINDOW)
        self.assertFalse(by[("plus", "claude-opus-5-5")]["retry_on_decline"], "through Luma Cloud a decline comes home: that retry isn't confirmed to keep nothing")
        moon = by[("own", kimi.DEFAULT_MODEL)]
        self.assertEqual((moon["context"], moon["caching"], moon["streams"], moon["sees"], moon["thinking"]), (None, False, False, False, ()))
        self.assertNotIn(("plus", kimi.DEFAULT_MODEL), by, "Plus offers only brains that keep nothing")

    def test_every_brain_is_asked_the_same_way(self):
        for chosen in (cloudbrain.pick("own", "claude-opus-5-5", "k"), cloudbrain.pick("plus", "claude-sonnet-5-5", cloud.Relay("t", "http://127.0.0.1:9")),
                       cloudbrain.pick("own", kimi.DEFAULT_MODEL, "k")):
            self.assertIsInstance(chosen, cloudbrain.CloudBrain)
            for call in ("stream", "plan", "rewrite", "look", "warm", "numbers"):
                self.assertTrue(callable(getattr(chosen, call)), call)
            self.assertTrue(chosen.label)

    def test_stream_gives_the_words_then_the_numbers_then_the_answer(self):
        def fake_plan(key, messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None, model=None, effort=None):
            for chunk in ("Hey ", "Marvin."):
                on_text(chunk)
            cloud._turn.last = {"read": 3200, "written": 300, "fresh": 150, "out": 24, "first_words_s": 0.4, "seconds": 1.1, "model": model}
            return {"type": "reply", "text": "Hey Marvin."}
        with mock.patch.object(cloud, "plan", side_effect=fake_plan):
            events = list(cloudbrain.pick("own", "claude-sonnet-5-5", "k").stream(MESSAGES, {}))
        self.assertEqual([event["type"] for event in events], ["words", "words", "numbers", "proposal"])
        self.assertEqual("".join(event["text"] for event in events[:2]), "Hey Marvin.")
        self.assertEqual(events[2]["read"], 3200)
        self.assertEqual(events[3]["proposal"], {"type": "reply", "text": "Hey Marvin."})

    def test_a_brain_that_cant_see_says_so_instead_of_guessing(self):
        with self.assertRaises(cloudbrain.CantDoThat):
            cloudbrain.pick("own", kimi.DEFAULT_MODEL, "k").look(b"...", "what's this?")

    def test_what_goes_wrong_in_the_brain_comes_out_of_the_stream(self):
        with mock.patch.object(cloud, "plan", side_effect=ValueError("no")):
            with self.assertRaises(ValueError):
                list(cloudbrain.pick("own", "claude-sonnet-5-5", "k").stream(MESSAGES, {}))


if __name__ == "__main__":
    unittest.main()
