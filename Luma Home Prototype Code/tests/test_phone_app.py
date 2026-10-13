"""The Luma app on your phone: pairing, end-to-end encryption, approvals by tap, notices."""
import base64
import hashlib
import secrets
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from luma.agent.runtime import Agent
from luma.integrations.phone_app import PhoneApp, b64u, card_for, seal, unb64u, unseal
from luma.memory.store import Store

from test_texting import FakeCloud


class AppCloud(FakeCloud):
    """Luma Cloud's app routes, plus a pretend phone on the other end."""

    def __init__(self):
        super().__init__()
        self.pairings, self.links, self.up, self.to_phone, self.unpaired = {}, {}, [], [], []
        self.registered = 0

    def __call__(self, method, url, headers, payload=None, **kwargs):
        path = url.split("/api/luma/")[1]
        if path == "device-register":
            self.registered += 1
            self.calls.append((method, path, headers, payload))
            return 200, {"device_token": "22222222-2222-2222-2222-222222222222.registeredregisteredregistered"}
        if path == "verify-check" and headers.get("Authorization"):
            self.calls.append((method, path, headers, payload))
            return 200, {"device_token": None, "linked": True, "account": {"plan": "free", "texts_left": 3, "texts_limit": 3, "verified": True}}
        if path == "app-pair-start":
            pair_id = "33333333-3333-3333-3333-%012d" % len(self.pairings)
            self.pairings[pair_id] = payload["secret_hash"]
            return 200, {"pair_id": pair_id, "expires_at": "2026-10-13T12:10:00Z"}
        if path.startswith("app-inbox"):
            self.wait = kwargs.get("timeout")
            rows, self.up = self.up, []
            links = [{"id": k, "pairing_id": v["pair"], "name": v["name"], "last_seen_at": None, "push": False} for k, v in self.links.items()]
            return 200, {"messages": rows, "links": links, "cursor": "2026-10-13T12:00:%02dZ" % len(self.to_phone)}
        if path == "app-reply":
            self.to_phone.extend(payload["messages"])
            return 200, {"results": [{"link_id": m["link_id"], "id": "d%d" % i} for i, m in enumerate(payload["messages"])]}
        if path == "app-unpair":
            self.unpaired.append(payload["link_id"])
            self.links.pop(payload["link_id"], None)
            return 200, {"removed": payload["link_id"]}
        return super().__call__(method, url, headers, payload)

    # -- the phone's side ---------------------------------------------------
    def phone_pairs(self, url, name="Marvin's iPhone"):
        fragment = urlsplit(url).fragment
        assert fragment.startswith("pair=")
        pair_id, secret, key = fragment[5:].split(".")
        assert hashlib.sha256(secret.encode()).hexdigest() == self.pairings[pair_id], "only the hash went to the cloud"
        link_id = "44444444-4444-4444-4444-%012d" % len(self.links)
        self.links[link_id] = {"pair": pair_id, "name": name, "key": unb64u(key)}
        return link_id

    def phone_says(self, link_id, message, key=None, ts=None):
        link = self.links[link_id]
        body = {"v": 1, "n": message.pop("n", secrets.token_urlsafe(9)), "ts": ts if ts is not None else int(time.time() * 1000), **message}
        self.up.append({"id": "u%d" % len(self.up), "link_id": link_id, "payload": seal(key or link["key"], link["pair"], "up", body), "created_at": "2026-10-13T12:00:00Z"})
        return body["n"]

    def phone_reads(self, link_id):
        link = self.links[link_id]
        return [unseal(link["key"], link["pair"], "down", m["payload"]) for m in self.to_phone if m["link_id"] == link_id]


class Providers:
    def __init__(self, cloud):
        self.env = {"LUMA_CLOUD_URL": "https://luma.example.com"}
        self.cloud_request = cloud


class PhoneAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "state.db", root / "state.key")
        self.cloud = AppCloud()
        self.agent = Agent(store=self.store, providers=Providers(self.cloud), use_model=False, now=time.time)
        self.app = PhoneApp(self.agent, wait=0)

    def tearDown(self):
        self.app.stop()
        self.store.close()

    def pair(self):
        out = self.app.start_pairing("Luma")
        self.app.stop()  # tests drive polling by hand
        link_id = self.cloud.phone_pairs(out["url"])
        self.app.poll_once()
        return link_id

    def run_jobs(self):
        if self.app._worker:
            self.app._worker.join(10)

    def test_pairing_registers_without_a_phone_and_keeps_the_key_out_of_the_cloud(self):
        out = self.app.start_pairing("Luma")
        self.app.stop()
        self.assertTrue(out["url"].startswith("https://luma.example.com/app/#pair="))
        self.assertTrue(out["qr"].startswith("data:image/svg+xml;base64,"))
        self.assertEqual(self.cloud.registered, 1)
        self.assertTrue(self.agent.cloud.connected())
        self.assertFalse(self.agent.cloud.signed_in(), "texting still needs a verified phone")
        key = urlsplit(out["url"]).fragment.split(".")[-1]
        for method, path, headers, payload in self.cloud.calls:
            self.assertNotIn(key, str(payload))
        link_id = self.cloud.phone_pairs(out["url"])
        self.app.poll_once()
        self.assertEqual([p["name"] for p in self.app.phones()], ["Marvin's iPhone"])
        self.assertNotIn(key.encode(), self.store.db_path.read_bytes(), "the key is encrypted at rest")
        self.assertEqual(self.app.status()["phones"][0]["id"], link_id)

    def test_hello_gets_a_greeting_and_a_reminder_works_from_the_phone(self):
        link = self.pair()
        hello = self.cloud.phone_says(link, {"t": "hello", "name": "iPhone"})
        n = self.cloud.phone_says(link, {"t": "text", "text": "remind me in 20 minutes to check the oven"})
        self.app.poll_once()
        self.run_jobs()
        replies = self.cloud.phone_reads(link)
        self.assertEqual(replies[0]["re"], hello)
        self.assertIn("on your phone now", replies[0]["text"])
        self.assertEqual(replies[1]["re"], n)
        self.assertIn("remind you", replies[1]["text"])
        self.assertTrue(any("check the oven" in t["title"] for t in self.agent._run("tasks.list", {})["tasks"]))

    def test_a_text_waits_for_send_it_on_the_phone_and_uses_the_one_time_token(self):
        self.agent.cloud.start_signup("Marvin", "+19195550100")
        link = self.pair()
        self.agent.cloud.finish_signup("123456", "Kitchen Luma")
        self.assertTrue(self.agent.cloud.signed_in())
        self.assertEqual(self.cloud.registered, 1, "verifying reuses the registered Luma")
        self.agent.set_message_route("luma_number")
        self.agent.contacts.save({"name": "Maya", "phone": "+19195550123"})

        self.cloud.phone_says(link, {"t": "text", "text": "text Maya that I'm on my way"})
        self.app.poll_once()
        self.run_jobs()
        reply = self.cloud.phone_reads(link)[-1]
        card = reply["card"]
        self.assertEqual((card["kind"], card["to_name"], card["body"]), ("approve", "Maya", "I'm on my way"))
        self.assertFalse(self.sends(), "nothing goes out before the tap")

        self.cloud.phone_says(link, {"t": "confirm", "action": card["action"], "token": "wrong-token"})
        self.app.poll_once()
        self.run_jobs()
        self.assertEqual(self.cloud.phone_reads(link)[-1]["state"], "failed")
        self.assertFalse(self.sends())

        self.cloud.phone_says(link, {"t": "confirm", "action": card["action"], "token": card["token"]})
        self.app.poll_once()
        self.run_jobs()
        done = self.cloud.phone_reads(link)[-1]
        self.assertEqual((done["t"], done["state"]), ("done", "succeeded"))
        self.assertEqual(len(self.sends()), 1)

        # The same tap replayed by a misbehaving relay sends nothing more.
        self.cloud.phone_says(link, {"t": "confirm", "action": card["action"], "token": card["token"]})
        self.app.poll_once()
        self.run_jobs()
        self.assertEqual(len(self.sends()), 1)

    def sends(self):
        return [c for c in self.cloud.calls if c[1] == "sms-send"]

    def test_dont_send_cancels(self):
        self.agent.cloud.start_signup("Marvin", "+19195550100")
        link = self.pair()
        self.agent.cloud.finish_signup("123456")
        self.agent.set_message_route("luma_number")
        self.agent.contacts.save({"name": "Maya", "phone": "+19195550123"})
        self.cloud.phone_says(link, {"t": "text", "text": "text Maya that I'm here"})
        self.app.poll_once()
        self.run_jobs()
        card = self.cloud.phone_reads(link)[-1]["card"]
        self.cloud.phone_says(link, {"t": "cancel", "action": card["action"]})
        self.app.poll_once()
        self.run_jobs()
        self.assertEqual(self.cloud.phone_reads(link)[-1]["state"], "cancelled")
        self.assertFalse(self.sends())
        self.assertEqual(self.store.get("action", card["action"])["state"], "cancelled")

    def test_replays_forgeries_and_stale_messages_are_ignored(self):
        link = self.pair()
        n = self.cloud.phone_says(link, {"t": "text", "text": "what's 2 plus 2"})
        self.cloud.up.append(dict(self.cloud.up[-1], id="again"))  # the relay repeats it
        self.cloud.phone_says(link, {"t": "text", "text": "hi"}, key=b"\0" * 32)  # not this phone's key
        self.cloud.phone_says(link, {"t": "text", "text": "hi"}, ts=int((time.time() - 3 * 86400) * 1000))
        self.app.poll_once()
        self.run_jobs()
        replies = self.cloud.phone_reads(link)
        self.assertEqual([r["re"] for r in replies], [n])

    def test_tampering_with_a_payload_or_its_direction_fails(self):
        key, pair = b"k" * 32, "33333333-3333-3333-3333-000000000000"
        sealed = seal(key, pair, "down", {"v": 1, "t": "reply", "text": "hi"})
        self.assertEqual(unseal(key, pair, "down", sealed)["text"], "hi")
        with self.assertRaises(Exception):
            unseal(key, pair, "up", sealed)  # can't be reflected back as the phone's message
        with self.assertRaises(Exception):
            unseal(key, "33333333-3333-3333-3333-000000000001", "down", sealed)  # or moved to another phone
        raw = bytearray(unb64u(sealed))
        raw[-1] ^= 1
        with self.assertRaises(Exception):
            unseal(key, pair, "down", b64u(bytes(raw)))

    def test_reminders_and_texts_back_reach_the_phone_as_notices(self):
        link = self.pair()
        self.app.notify({"type": "reply", "text": "Maya texted back: “yes! 7?”"})
        self.app.notify({"type": "nudge", "text": "How did the interview go?"})
        notice, nudge = self.cloud.phone_reads(link)
        self.assertEqual((notice["t"], notice["label"]), ("notice", "Text back"))
        self.assertEqual((nudge["t"], nudge["text"]), ("reply", "How did the interview go?"))
        self.assertTrue(all(m.get("notify") for m in self.cloud.to_phone), "these can wake a closed app")

    def test_kids_mode_keeps_the_phone_out(self):
        link = self.pair()
        self.agent.set_mode("kids")
        self.cloud.phone_says(link, {"t": "text", "text": "text Maya hi"})
        self.app.poll_once()
        self.run_jobs()
        self.assertIn("kids mode", self.cloud.phone_reads(link)[-1]["text"])
        with self.assertRaises(ValueError):
            self.app.start_pairing()
        self.assertIsNone(self.app.notify({"type": "reminder", "text": "x"}))

    def test_removing_a_phone_ends_its_access(self):
        link = self.pair()
        self.app.remove(link)
        self.assertEqual(self.cloud.unpaired, [link])
        self.assertEqual(self.app.phones(), [])

    def test_signing_out_of_texting_keeps_the_phone_connected(self):
        self.agent.cloud.start_signup("Marvin", "+19195550100")
        self.pair()
        self.agent.cloud.finish_signup("123456")
        self.agent.cloud.sign_out()
        self.assertFalse(self.agent.cloud.signed_in())
        self.assertTrue(self.agent.cloud.connected())

    def test_cards_for_drafts_and_other_approvals(self):
        draft = card_for({"state": "draft", "message_draft": {"name": "Mom", "to": "+19195550111", "body": "on my way"}})
        self.assertEqual(draft, {"kind": "draft", "to_name": "Mom", "to": "+19195550111", "body": "on my way"})
        other = card_for({"state": "pending", "action": "a1", "confirm_token": "t", "tool": "food.checkout", "review": {"title": "Order groceries", "total": "$42.10"}})
        self.assertEqual((other["title"], other["lines"]), ("Order groceries", ["total: $42.10"]))
        self.assertIsNone(card_for({"text": "hi"}))


if __name__ == "__main__":
    unittest.main()
