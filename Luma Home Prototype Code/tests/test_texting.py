"""Texting friends and family: drafts in your voice, "send it", Luma's number and its quota."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from luma.agent.runtime import Agent
from luma.memory.store import Store


class FakeCloud:
    """Stands in for Luma Cloud (api/luma/[route].js)."""
    def __init__(self):
        self.calls, self.left, self.limit, self.replies, self.down = [], 3, 3, [], False

    def __call__(self, method, url, headers, payload=None):
        path = url.split("/api/luma/")[1]
        self.calls.append((method, path, headers, payload))
        if self.down and path.startswith("sms-send"):
            raise OSError("connection dropped")
        account = {"plan": "free", "texts_used": self.limit - self.left, "texts_limit": self.limit, "texts_left": self.left,
                   "number": "+19195550000", "plus": {"price": "$9.99/month", "texts_limit": 300, "available": True}}
        if path == "verify-start": return 200, {"sent": True}
        if path == "verify-check":
            return (200, {"device_token": "11111111-1111-1111-1111-111111111111.secretsecretsecretsecret", "account": account}) if payload["code"] == "123456" else (403, {"error": "code", "message": "That code didn't work."})
        if path == "account": return 200, account
        if path == "sms-send":
            if self.left == 0:
                return 402, {"error": "quota", "message": "You've used your 3 free texts from Luma's number this month.", "plan": "free", "texts_limit": 3,
                             "upgrade_url": "https://checkout.stripe.com/c/pay/test", "plus": account["plus"]}
            self.left -= 1
            return 200, {"message_id": "m1", "status": "queued", "from": "+19195550000", **account, "texts_left": self.left, "texts_used": self.limit - self.left}
        if path.startswith("number-options"):
            area = path.split("area_code=")[1] if "area_code=" in path else "919"
            return 200, {"area_code": area, "numbers": [{"number": f"+1{area}5552000", "locality": "Raleigh", "region": "NC"}]}
        if path == "billing-checkout":
            return 200, {"url": "https://checkout.stripe.com/c/pay/x" + ("?n=" + payload["number"] if payload.get("number") else "")}
        if path.startswith("sms-inbox"):
            replies, self.replies = self.replies, []
            return 200, {"replies": replies, "cursor": "2026-10-03T12:00:00Z"}
        return 404, {"error": "not_found"}


class Providers:
    def __init__(self, cloud):
        self.env = {"LUMA_CLOUD_URL": "https://luma.example.com"}
        self.cloud_request = cloud


class TextingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "state.db", root / "state.key")
        self.cloud = FakeCloud()
        self.now = 1791043200.0  # 2026-10-03 12:00 UTC (8am New York)
        self.agent = Agent(store=self.store, providers=Providers(self.cloud), use_model=False, now=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def sends(self):
        return [c for c in self.cloud.calls if c[1] == "sms-send"]

    def test_unknown_person_gets_asked_for_then_saved_with_their_nickname(self):
        ask = self.agent.chat("text my girl that I'll pick her up at 7")
        self.assertIn("Who's my girl? Give me her name and number", ask["text"])
        draft = self.agent.chat("Maya, 919-555-0123")
        self.assertEqual(draft["message_draft"]["to"], "+19195550123")
        self.assertEqual(draft["message_draft"]["body"], "I'll pick you up at 7")
        self.assertTrue(draft["text"].startswith("Saved Maya as your girl."))
        again = self.agent.chat("let my girl know I'm outside")
        self.assertEqual(again["message_draft"]["body"], "I'm outside")
        self.assertEqual(again["message_draft"]["to"], "+19195550123")

    def test_saving_a_contact_conversationally(self):
        saved = self.agent.chat("save Dana +1 (919) 555-0177 as my sister")
        self.assertIn("Dana is saved", saved["text"])
        result = self.agent.chat("text my sister to call me when she's free")
        self.assertEqual(result["message_draft"]["body"], "Can you call me when you're free?")
        with self.assertRaises(ValueError):
            self.agent.contacts.save({"name": "Rae", "phone": "+19195550188", "aliases": ["sister"]})

    @patch("luma.agent.runtime.MacMessages")
    def test_send_it_sends_once_from_your_own_number(self, mac):
        mac.return_value.send.return_value = {"provider": "mac_messages", "status": "accepted", "summary": "accepted"}
        self.agent.contacts.save({"name": "Maya", "phone": "+19195550123", "aliases": ["babe"]})
        self.agent.set_message_route("mac_imessage")
        pending = self.agent.chat("text babe that I'm running 10 late")
        self.assertEqual(pending["state"], "pending")
        self.assertEqual(pending["text"], "Here's the text for Maya: “I'm running 10 late”. Want me to send it from your number?")
        mac.return_value.send.assert_not_called()
        sent = self.agent.chat("yeah send it")
        mac.return_value.send.assert_called_once_with({"to": "+19195550123", "body": "I'm running 10 late"})
        self.assertEqual(sent["text"], "Sent to Maya from your number.")
        self.assertIsNone(self.agent._spoken_approval("send it"), "nothing left to approve")
        self.assertEqual(mac.return_value.send.call_count, 1)

    @patch("luma.agent.runtime.MacMessages")
    def test_dont_send_it_cancels(self, mac):
        self.agent.contacts.save({"name": "Mom", "phone": "+19195550111"})
        self.agent.set_message_route("mac_sms")
        pending = self.agent.chat("text mom that dinner is at 6")
        cancelled = self.agent.chat("don't send it")
        self.assertEqual(cancelled["text"], "Okay, I won't send it.")
        self.assertEqual(self.store.get("action", pending["action"])["state"], "cancelled")
        mac.return_value.send.assert_not_called()

    @patch("luma.agent.runtime.MacMessages")
    def test_expired_approval_does_not_send(self, mac):
        self.agent.contacts.save({"name": "Mom", "phone": "+19195550111"})
        self.agent.set_message_route("mac_sms")
        self.agent.chat("text mom that dinner is at 6")
        self.now += 601
        late = self.agent.chat("send it")
        self.assertIn("didn't send it", late["text"])
        mac.return_value.send.assert_not_called()

    def sign_up(self):
        self.agent.cloud.start_signup("Marvin", "+19195550100")
        self.agent.cloud.finish_signup("123456", "Kitchen Luma")
        self.agent.set_message_route("luma_number")
        self.agent.contacts.save({"name": "Maya", "phone": "+19195550123"})

    def test_lumas_number_sends_with_the_action_id_and_warns_when_running_low(self):
        with self.assertRaises(Exception):
            self.agent.cloud.finish_signup("123456")  # no code was requested yet
        self.sign_up()
        import base64
        token = base64.b64decode(self.store.setting("luma_cloud_device")["token_b64"]).decode()
        self.assertNotIn(token.encode(), self.store.db_path.read_bytes(), "device credential is encrypted at rest")
        pending = self.agent.chat("text Maya that I'm here")
        self.assertIn("from Luma's number (3 free texts left this month)", pending["text"])
        sent = self.agent.chat("send it")
        method, _, headers, payload = self.sends()[0]
        self.assertEqual(payload, {"to": "+19195550123", "body": "I'm here", "client_ref": pending["action"]})
        self.assertTrue(headers["Authorization"].startswith("Bearer 11111111-"))
        self.assertEqual(sent["text"], "Sent to Maya from Luma’s number. 2 free texts left this month.")

    def test_out_of_free_texts_offers_luma_plus_or_your_own_number(self):
        self.sign_up()
        self.cloud.left = 1
        first = self.agent.chat("text Maya that I'm here")
        self.cloud.left = 0  # used up elsewhere before approval
        result = self.agent.chat("send it")
        self.assertEqual(result["state"], "failed")
        self.assertTrue(result["quota"])
        self.assertEqual(result["upgrade_url"], "https://checkout.stripe.com/c/pay/test")
        self.assertIn("Luma Plus is $9.99/month for 300 texts", result["text"])
        self.assertIn("from your own number through Messages, which is free", result["text"])
        self.assertEqual(self.store.get("action", first["action"])["state"], "failed")
        # Next time Luma knows before proposing anything.
        blocked = self.agent.chat("text Maya that I'm on my way")
        self.assertEqual(blocked["state"], "quota")
        self.assertNotIn("action", blocked)
        self.assertEqual(blocked["message_draft"]["body"], "I'm on my way")

    def test_lost_connection_is_reported_as_unknown_and_never_retried(self):
        self.sign_up()
        pending = self.agent.chat("text Maya that I'm here")
        self.cloud.down = True
        result = self.agent.confirm(pending["action"], pending["confirm_token"])
        self.assertEqual(result["state"], "unknown")
        self.assertIn("not sure", result["text"])
        with self.assertRaises(ValueError):
            self.agent.confirm(pending["action"], pending["confirm_token"])
        self.assertEqual(len(self.sends()), 1)

    def test_replies_are_announced_and_can_be_asked_about(self):
        self.sign_up()
        self.cloud.replies = [{"id": "r1", "from": "+19195550123", "body": "yes! 7?", "received_at": "2026-10-03T12:00:00Z"}]
        event = self.agent.tick()
        self.assertEqual(event["text"], "Maya texted back: “yes! 7?”")
        self.assertIsNone(self.agent.tick(), "announced once")
        self.assertEqual(self.agent.chat("did Maya text back?")["text"], "Maya said: “yes! 7?”")

    @patch("luma.agent.runtime.MacMessages")
    def test_drafts_pick_up_how_you_text_each_person(self, mac):
        mac.return_value.send.return_value = {"provider": "mac_messages", "status": "accepted", "summary": "accepted"}
        self.agent.contacts.save({"name": "Maya", "phone": "+19195550123"})
        self.agent.set_message_route("mac_imessage")
        for line in ["omw", "save me a seat lol"]:
            self.agent.chat(f"text Maya that {line}")
            self.agent.chat("send it")
        draft = self.agent.chat("text Maya that I'm Running Late.")
        self.assertEqual(draft["arguments"]["body"], "i'm running late")

    def test_lumas_number_not_set_up_yet_keeps_a_draft_and_says_why(self):
        self.agent.contacts.save({"name": "Maya", "phone": "+19195550123"})
        self.agent.set_message_route("luma_number")
        result = self.agent.chat("text Maya that I'm here")
        self.assertEqual(result["state"], "draft")
        self.assertIn("isn't set up yet", result["text"])
        self.assertFalse(self.sends())

    def test_picking_a_number_before_upgrading(self):
        self.agent.cloud.start_signup("Marvin", "+19195550100")
        self.agent.cloud.finish_signup("123456")
        self.assertEqual(self.agent.cloud.number_options()["numbers"][0]["number"], "+19195552000")
        self.assertEqual(self.agent.cloud.number_options("704")["numbers"][0]["number"], "+17045552000")
        with self.assertRaises(ValueError):
            self.agent.cloud.number_options("12")
        self.assertTrue(self.agent.cloud.upgrade_link("+17045552000").endswith("?n=+17045552000"))
        with self.assertRaises(ValueError):
            self.agent.cloud.upgrade_link("not a number")

    def test_kids_mode_cannot_text(self):
        self.agent.contacts.save({"name": "Maya", "phone": "+19195550123"})
        self.agent.set_mode("kids")
        self.assertIn("can't text people in kids mode", self.agent.chat("text Maya that hi")["text"])


if __name__ == "__main__":
    unittest.main()


class OwnerTextTests(unittest.TestCase):
    """Texting Luma's number from your own phone reaches your Luma at home."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "state.db", root / "state.key")
        self.cloud = FakeCloud()
        self.cloud.left = 50
        self.agent = Agent(store=self.store, providers=Providers(self.cloud), use_model=False, now=lambda: 1791043200.0)
        self.agent.cloud.start_signup("Marvin", "+19195550100")
        self.agent.cloud.finish_signup("123456")
        self.agent.contacts.save({"name": "Dana", "phone": "+19195550177", "aliases": ["my sister"]})
        self.agent.set_message_route("luma_number")

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def owner(self, body, n):
        return self.agent.answer_owner_text({"id": f"in{n}", "body": body, "kind": "owner"})

    def last_send(self):
        return [c for c in self.cloud.calls if c[1] == "sms-send"][-1][3]

    def test_a_text_to_luma_gets_answered_by_text(self):
        out = self.owner("remind me in 20 minutes to grab flowers", 1)
        self.assertIn("grab flowers", out["reply"])
        sent = self.last_send()
        self.assertEqual(sent["to"], "+19195550100")
        self.assertTrue(sent["to_owner"])
        self.assertEqual(len(self.store.all("task")), 1)

    def test_sending_from_a_text_needs_the_one_time_code(self):
        draft = self.owner("text my sister that I'll be late to mom's", 1)
        code = self.agent.awaiting["code"]
        self.assertIn(f"Reply YES {code} to send", draft["reply"])
        self.assertEqual(self.last_send()["to"], "+19195550100", "the draft goes back to the owner, not Dana")
        plain = self.owner("yes", 2)
        self.assertIn(f"reply YES {code}", plain["reply"])
        wrong = self.owner("YES 0000" if code != "0000" else "YES 1111", 3)
        self.assertIn("reply YES", wrong["reply"])
        self.assertFalse([c for c in self.cloud.calls if c[1] == "sms-send" and c[3]["to"] == "+19195550177"])
        done = self.owner(f"yes {code}", 4)
        to_dana = [c[3] for c in self.cloud.calls if c[1] == "sms-send" and c[3]["to"] == "+19195550177"]
        self.assertEqual(to_dana[0]["body"], "I'll be late to mom's")
        self.assertIn("Sent to Dana", done["reply"])

    def test_no_by_text_cancels_without_a_code(self):
        self.owner("text my sister that dinner's at 6", 1)
        self.assertIn("won't send", self.owner("no", 2)["reply"])
        self.assertIsNone(self.agent.awaiting)

    def test_owner_texts_are_picked_up_from_the_inbox(self):
        self.cloud.replies = [{"id": "o1", "from": "+19195550100", "body": "timers", "kind": "owner", "received_at": "2026-10-03T12:00:00Z"}]
        self.agent._poll_replies()
        self.agent._owner_worker.join(10)
        self.assertEqual(self.last_send()["to"], "+19195550100")
        self.assertFalse(self.store.all("sms_reply"), "the owner's own texts aren't 'replies from people'")
