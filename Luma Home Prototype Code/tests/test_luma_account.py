"""Everyone needs a Luma account to get in: an email and a password. The password never leaves the computer and is
never kept; Luma sends (and, while Luma Cloud can't be reached, keeps) a key made from it, and the account joins
Luma Cloud by itself once it answers. Signing in on another computer takes the same email and password."""
import hashlib
import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from luma.agent.runtime import Agent
from luma.control import server as control_server
from luma.control.server import make_server
from luma.integrations.luma_cloud import CloudError, LumaCloud
from luma.integrations.providers import ProviderError
from luma.memory.store import Store

PASSWORD = "sunset over raleigh"


def key_for(email, password):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), ("luma-account:" + email).encode(), 200_000, 32).hex()


class FakeCloud:
    """Luma Cloud's account routes (api/_lib/luma-cloud.js), in memory. mode: "up", "unset" (no database yet) or "offline"."""
    def __init__(self):
        self.mode, self.accounts, self.calls, self.devices = "up", {}, [], 0

    def __call__(self, method, url, headers, payload=None, timeout=None):
        path = url.split("/api/luma/")[1]
        self.calls.append((path, headers, payload))
        if self.mode == "offline":
            raise OSError("no route to host")
        if self.mode == "unset":
            return 503, {"error": "not_configured", "message": "Luma Cloud isn't set up yet."}
        view = lambda email: {"email": email, "plan": "free", "owner_name": self.accounts[email]["name"]}
        if path == "account-create":
            if payload["email"] in self.accounts:
                return 409, {"error": "email_taken", "message": "There's already a Luma account with that email. Sign in instead."}
            self.accounts[payload["email"]] = {"key": payload["key"], "name": payload["name"]}
            self.devices += 1
            return 200, {"device_token": f"{self.devices:08d}-1111-1111-1111-111111111111.secretsecretsecretsecret", "account": view(payload["email"])}
        if path == "account-login":
            found = self.accounts.get(payload["email"])
            if not found or found["key"] != payload["key"]:
                return 401, {"error": "login", "message": "That email and password don't match."}
            self.devices += 1
            return 200, {"device_token": f"{self.devices:08d}-2222-2222-2222-222222222222.secretsecretsecretsecret", "account": view(payload["email"])}
        if path == "account":
            return 200, {"plan": "free"}
        return 404, {"error": "not_found"}


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.fake = FakeCloud()
        self.cloud = LumaCloud(self.store, env={"LUMA_CLOUD_URL": "https://luma.example.com"}, request=self.fake, clock=lambda: 1000.0)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def kept(self):
        return json.dumps({k: self.store.setting(k) for k in ("luma_cloud_device", "luma_cloud_account", "luma_account_pending")})

    def test_signing_up_sends_a_key_made_from_the_password_never_the_password(self):
        out = self.cloud.create_account("Jay Price", " Jay@Example.com ", PASSWORD)
        self.assertEqual(out["account"]["email"], "jay@example.com")
        path, headers, payload = self.fake.calls[-1]
        self.assertEqual(path, "account-create")
        self.assertNotIn("password", payload)
        self.assertEqual(payload["key"], key_for("jay@example.com", PASSWORD))
        self.assertNotIn(PASSWORD, json.dumps(self.fake.calls))
        self.assertNotIn(PASSWORD, self.kept(), "the password is never kept")
        self.assertTrue(self.cloud.has_account())
        self.assertEqual(self.cloud.credentials["email"], "jay@example.com")

    def test_before_luma_cloud_is_set_up_the_account_waits_here_then_joins_by_itself(self):
        for mode in ("unset", "offline"):
            with self.subTest(mode=mode):
                self.store.set_setting("luma_account_pending", None)
                self.fake.mode = mode
                out = self.cloud.create_account("Jay", "jay@example.com", PASSWORD)
                self.assertTrue(out["pending"])
                self.assertTrue(self.cloud.has_account(), "they're in: the account is on this computer")
                self.assertNotIn(PASSWORD, self.kept())
                self.assertIsNone(self.cloud.finish_pending(), "still unreachable: nothing happens, nothing breaks")
                self.assertTrue(self.cloud.pending_account())
        self.fake.mode = "up"
        self.cloud.finish_pending()
        self.assertIsNone(self.cloud.pending_account())
        self.assertEqual(self.fake.accounts["jay@example.com"]["key"], key_for("jay@example.com", PASSWORD))
        self.assertEqual(self.cloud.credentials["email"], "jay@example.com")

    def test_a_held_account_whose_email_is_already_theirs_signs_in_with_the_same_password(self):
        self.fake.accounts["jay@example.com"] = {"key": key_for("jay@example.com", PASSWORD), "name": "Jay"}
        self.fake.mode = "unset"
        self.cloud.create_account("Jay", "jay@example.com", PASSWORD)
        self.fake.mode = "up"
        self.cloud.finish_pending()
        self.assertEqual(self.cloud.credentials["email"], "jay@example.com")
        self.assertIsNone(self.cloud.pending_account())

    def test_someone_elses_email_is_flagged_instead_of_taken(self):
        self.fake.accounts["jay@example.com"] = {"key": key_for("jay@example.com", "not their password"), "name": "Other"}
        with self.assertRaises(CloudError) as taken:
            self.cloud.create_account("Jay", "jay@example.com", PASSWORD)
        self.assertEqual(taken.exception.status, 409)
        self.fake.mode = "unset"
        self.cloud.create_account("Jay", "jay@example.com", PASSWORD)
        self.fake.mode = "up"
        self.cloud.finish_pending()
        self.assertEqual(self.cloud.pending_account()["problem"], "taken")
        self.assertFalse((self.cloud.credentials or {}).get("email"))

    def test_signing_in_on_another_computer_and_signing_out(self):
        self.fake.accounts["jay@example.com"] = {"key": key_for("jay@example.com", PASSWORD), "name": "Jay Price"}
        with self.assertRaises(CloudError) as wrong:
            self.cloud.sign_in("jay@example.com", "not the password")
        self.assertEqual(wrong.exception.status, 401)
        out = self.cloud.sign_in("JAY@example.com", PASSWORD)
        self.assertEqual(out["account"]["email"], "jay@example.com")
        self.assertEqual(self.cloud.credentials["name"], "Jay Price")
        self.fake.mode = "unset"
        with self.assertRaises(ProviderError):
            self.cloud.sign_in("jay@example.com", PASSWORD)
        self.cloud.sign_out_account()
        self.assertFalse(self.cloud.has_account())

    def test_what_they_type_is_checked_here_first(self):
        for email, password, says in [("nope", PASSWORD, "email"), ("a@b.co", "short", "8 characters"), ("a@b.co", "x" * 201, "too long")]:
            with self.assertRaisesRegex(ValueError, says):
                self.cloud.create_account("Jay", email, password)
        self.assertEqual(self.fake.calls, [])


class Providers:
    def __init__(self, cloud):
        self.env = {"LUMA_CLOUD_URL": "https://luma.example.com"}
        self.cloud_request = cloud


class AccountScreenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.fake = FakeCloud()
        self.agent = Agent(store=self.store, providers=Providers(self.fake), use_model=False, now=lambda: 1791900000.0)
        control_server._account_retry.update(at=0.0, running=False)
        self.server = make_server(self.agent, 0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.client.open(self.base + "/desktop/").read()

    def tearDown(self):
        self.server.control_context.stop.set()
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.temp.cleanup()

    def post(self, path, body):
        request = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={"Origin": self.base, "Content-Type": "application/json"})
        with self.client.open(request) as r:
            return json.load(r)

    def home(self):
        with self.client.open(self.base + "/api/home") as r:
            return json.load(r)

    def test_nobody_gets_in_without_an_account_and_one_made_offline_counts(self):
        self.assertFalse(self.home()["account"]["has_account"])
        self.fake.mode = "unset"
        out = self.post("/api/account/create", {"name": "Jay Price", "email": "jay@example.com", "password": PASSWORD})
        self.assertTrue(out["pending"])
        account = self.home()["account"]
        self.assertTrue(account["has_account"])
        self.assertTrue(account["pending"])
        self.assertEqual(account["email"], "jay@example.com")
        self.assertNotIn("key", json.dumps(account))

    def test_a_taken_email_and_a_wrong_password_say_so(self):
        self.fake.accounts["jay@example.com"] = {"key": key_for("jay@example.com", PASSWORD), "name": "Jay"}
        with self.assertRaises(urllib.error.HTTPError) as taken:
            self.post("/api/account/create", {"name": "Jay", "email": "jay@example.com", "password": PASSWORD})
        self.assertEqual(taken.exception.code, 409)
        self.assertIn("Sign in instead", json.load(taken.exception)["error"])
        with self.assertRaises(urllib.error.HTTPError) as wrong:
            self.post("/api/account/signin", {"email": "jay@example.com", "password": "wrong password!"})
        self.assertEqual(wrong.exception.code, 401)
        out = self.post("/api/account/signin", {"email": "jay@example.com", "password": PASSWORD})
        self.assertEqual(out["account"]["email"], "jay@example.com")
        self.assertTrue(out["account"]["has_account"])
        self.post("/api/account/leave", {})
        self.assertFalse(self.home()["account"]["has_account"])


if __name__ == "__main__":
    unittest.main()
