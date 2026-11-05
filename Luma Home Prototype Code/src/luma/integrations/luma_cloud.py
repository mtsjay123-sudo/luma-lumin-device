"""Luma's own texting number, through Luma Cloud.

The owner verifies their phone once; this device then holds a credential (in the
encrypted store) for Lumin's relay. Free accounts get a monthly allowance of texts
from Luma's shared number; Luma Plus raises it and adds a dedicated number.
Sends are idempotent: the relay keys each one by the local action id, so a retry
after a dropped connection can never text someone twice.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from luma.integrations.providers import OutcomeUnknown, ProviderError

DEFAULT_URL = "https://lumin-holdings-site.vercel.app"
PHONE = re.compile(r"\+1[2-9]\d{2}[2-9]\d{6}")


class QuotaReached(ProviderError):
    def __init__(self, message, *, plan="free", limit=0, upgrade_url=None, plus=None):
        super().__init__(message)
        self.plan, self.limit, self.upgrade_url, self.plus = plan, limit, upgrade_url, plus or {}


class CloudError(ProviderError):
    def __init__(self, message, code="", status=0):
        super().__init__(message)
        self.code, self.status = code, status


def http(method, url, headers, payload=None, timeout=15):
    """Return (status, json). Network trouble raises OSError for the caller to classify."""
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, method=method,
                                     headers={**headers, "Accept": "application/json",
                                              **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read(200_001) or b"{}")
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read(200_001) or b"{}")
        except (ValueError, OSError):
            body = {}
        return error.code, body


class LumaCloud:
    def __init__(self, store, env=None, request=None, clock=time.time):
        self.store = store
        self.env = os.environ if env is None else env
        self.request = request or http
        self.clock = clock

    # -- configuration ---------------------------------------------------------
    @property
    def base_url(self):
        url = (self.env.get("LUMA_CLOUD_URL") or DEFAULT_URL).rstrip("/")
        parts = urllib.parse.urlsplit(url)
        local = parts.hostname in {"127.0.0.1", "localhost"}
        if parts.scheme != "https" and not (local and parts.scheme == "http"):
            raise ProviderError("Luma Cloud must use HTTPS.")
        return url

    @property
    def credentials(self):
        return self.store.setting("luma_cloud_device")

    def connected(self):
        """This Luma has a Luma Cloud credential (needed for the phone app)."""
        return bool(self.credentials)

    def signed_in(self):
        """Texting from Luma's number is set up: the owner verified their phone."""
        creds = self.credentials
        return bool(creds and creds.get("phone"))

    def _auth(self):
        creds = self.credentials
        if not creds:
            raise CloudError("Set up Luma's number first: verify your phone in People & Texts.", "auth", 401)
        return {"Authorization": "Bearer " + base64.b64decode(creds["token_b64"]).decode()}

    def _call(self, method, path, payload=None, auth=True, side_effect=False, timeout=None):
        headers = self._auth() if auth else {}
        try:
            if timeout is None:
                status, body = self.request(method, self.base_url + path, headers, payload)
            else:
                status, body = self.request(method, self.base_url + path, headers, payload, timeout=timeout)
        except (OSError, ValueError, TimeoutError):
            if side_effect:
                raise OutcomeUnknown("I lost the connection while sending, so I'm not sure it went out. Check before sending again.") from None
            raise ProviderError("I can't reach Luma Cloud right now. Check the internet connection.") from None
        if status == 401 and auth:
            self.store.set_setting("luma_cloud_device", None)
        if status == 402:
            self._cache({**(self.store.setting("luma_cloud_account") or {}), "plan": body.get("plan", "free"), "texts_limit": body.get("texts_limit", 0),
                         "texts_left": 0, **({"plus": body["plus"]} if body.get("plus") else {})})
            raise QuotaReached(body.get("message", "You're out of texts this month."), plan=body.get("plan", "free"),
                               limit=body.get("texts_limit", 0), upgrade_url=body.get("upgrade_url"), plus=body.get("plus"))
        if status >= 400:
            raise CloudError(body.get("message") or "Luma Cloud couldn't do that right now.", body.get("error", ""), status)
        return status, body

    # -- the Luma account: everyone has one, an email and a password -------------------------
    # The password never leaves this computer and is never kept: what's sent (and, while Luma Cloud can't be
    # reached, kept in the encrypted store) is a key made from it and the email, which Luma Cloud hashes again.
    @staticmethod
    def account_key(email, password):
        return hashlib.pbkdf2_hmac("sha256", password.encode(), ("luma-account:" + email).encode(), 200_000, 32).hex()

    @staticmethod
    def _account_input(email, password):
        email = str(email or "").strip().lower()
        if len(email) > 120 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", email):
            raise ValueError("That email doesn't look right.")
        if not isinstance(password, str) or len(password) < 8:
            raise ValueError("Use at least 8 characters for your password.")
        if len(password) > 200:
            raise ValueError("That password is too long.")
        return email, password

    def has_account(self):
        """A Luma account on this computer: signed in, or made here and waiting for Luma Cloud."""
        return bool((self.credentials or {}).get("email") or self.store.setting("luma_account_pending"))

    def pending_account(self):
        return self.store.setting("luma_account_pending")

    def create_account(self, name, email, password, device_name="Luma"):
        email, password = self._account_input(email, password)
        name = " ".join(str(name or "").split())[:60] or "Luma owner"
        return self._create(name, email, self.account_key(email, password), device_name)

    def _create(self, name, email, key, device_name="Luma", hold=True):
        payload = {"name": name, "email": email, "key": key, "device_name": str(device_name)[:60]}
        registered = self.connected()
        try:
            try:
                _, body = self._call("POST", "/api/luma/account-create", payload, auth=registered)
            except CloudError as error:
                if not (registered and error.status == 401):
                    raise
                registered = False  # a credential Luma Cloud no longer knows: start this computer fresh
                _, body = self._call("POST", "/api/luma/account-create", payload, auth=False)
        except CloudError as error:
            if not hold or error.status < 500:
                raise  # 409: that email has an account (sign in instead); 400: what they typed
            return self._hold(name, email, key)
        except ProviderError:
            if not hold:
                raise
            return self._hold(name, email, key)  # no internet, or Luma Cloud is down
        self._keep(body, email, name, linked_ok=registered)
        return {"account": self.store.setting("luma_cloud_account"), "summary": f"Your Luma account is {email}."}

    def _hold(self, name, email, key):
        self.store.set_setting("luma_account_pending", {"name": name, "email": email, "key": key, "since": self.clock()})
        return {"pending": True, "email": email,
                "summary": "Your account is saved on this computer. It joins Luma Cloud by itself as soon as Luma Cloud answers."}

    def _keep(self, body, email, name, linked_ok=False):
        token = body.get("device_token")
        account = body.get("account") or {}
        name = account.get("owner_name") or name
        if linked_ok and token is None and body.get("linked") and self.credentials:
            self.store.set_setting("luma_cloud_device", {**self.credentials, "email": email, "name": self.credentials.get("name") or name})
        elif not isinstance(token, str) or "." not in token:
            raise ProviderError("Luma Cloud didn't return a device credential.")
        else:
            # Encoded so the store's card-number guard doesn't mistake the credential's digits for a card.
            self.store.set_setting("luma_cloud_device", {"token_b64": base64.b64encode(token.encode()).decode(), "phone": None, "name": name, "email": email})
        self.store.set_setting("luma_account_pending", None)
        self._cache(account)

    def sign_in(self, email, password, device_name="Luma"):
        email, password = self._account_input(email, password)
        return self._sign_in(email, self.account_key(email, password), device_name)

    def _sign_in(self, email, key, device_name="Luma"):
        try:
            _, body = self._call("POST", "/api/luma/account-login", {"email": email, "key": key, "device_name": str(device_name)[:60]}, auth=False)
        except CloudError as error:
            if error.status >= 500:
                raise ProviderError("Luma Cloud isn't answering right now, so I can't check your password. Try again in a minute.") from None
            raise
        self.store.set_setting("luma_cloud_device", None)  # this computer's credential is the new one
        self._keep(body, email, (body.get("account") or {}).get("owner_name") or "")
        return {"account": self.store.setting("luma_cloud_account"), "summary": f"Signed in as {email}."}

    def finish_pending(self):
        """An account made while Luma Cloud couldn't be reached joins it now, if it answers. Quiet when it still can't.
        If someone already has that email (this owner, signed up on another computer), the same password signs in."""
        pending = self.pending_account()
        if not pending or (self.credentials or {}).get("email"):
            return None
        try:
            return self._create(pending["name"], pending["email"], pending["key"], hold=False)
        except CloudError as error:
            if error.status != 409:
                return None
            try:
                return self._sign_in(pending["email"], pending["key"])
            except (CloudError, ProviderError):
                self.store.set_setting("luma_account_pending", {**pending, "problem": "taken"})
                return None
        except ProviderError:
            return None

    # -- texting from Luma's number: the owner verifies their phone ---------------------------
    def start_signup(self, name, phone):
        name = " ".join(str(name or "").split())[:60]
        if not name:
            raise ValueError("Add your name so people know who's texting.")
        if not isinstance(phone, str) or not PHONE.fullmatch(phone):
            raise ValueError("Use your US or Canadian mobile number, like +19195550123.")
        self._call("POST", "/api/luma/verify-start", {"name": name, "phone": phone}, auth=False)
        self.store.set_setting("luma_cloud_pending", {"name": name, "phone": phone})
        return {"sent": True, "summary": "I texted a code to " + phone + ". Enter it to finish."}

    def finish_signup(self, code, device_name="Luma"):
        pending = self.store.setting("luma_cloud_pending")
        if not pending:
            raise ValueError("Start by entering your phone number.")
        if not isinstance(code, str) or not re.fullmatch(r"\d{4,10}", code.strip()):
            raise ValueError("Enter the code from the text.")
        # A Luma already registered for the phone app keeps its credential; the phone attaches to it.
        registered = self.connected()
        _, body = self._call("POST", "/api/luma/verify-check",
                             {"phone": pending["phone"], "name": pending["name"], "code": code.strip(), "device_name": str(device_name)[:60]}, auth=registered)
        token = body.get("device_token")
        if registered and token is None and body.get("linked") and self.credentials:
            self.store.set_setting("luma_cloud_device", {**self.credentials, "phone": pending["phone"], "name": pending["name"]})
        elif not isinstance(token, str) or "." not in token:
            raise ProviderError("Luma Cloud didn't return a device credential.")
        else:
            # Encoded so the store's card-number guard doesn't mistake the credential's digits for a card.
            self.store.set_setting("luma_cloud_device", {"token_b64": base64.b64encode(token.encode()).decode(), "phone": pending["phone"], "name": pending["name"]})
        self.store.set_setting("luma_cloud_pending", None)
        self._cache(body.get("account") or {})
        return {"account": self.store.setting("luma_cloud_account"), "summary": "You're set. Luma can text from its number now."}

    def sign_out(self):
        # Texting stops; a phone paired with this Luma keeps working. The account stays signed in: signing out of
        # that is sign_out_account.
        creds = self.credentials
        keep = creds and (self.store.setting("phone_app_b64") or creds.get("email"))
        self.store.set_setting("luma_cloud_device", {"token_b64": creds["token_b64"], "phone": None, "name": None, "email": creds.get("email")} if keep else None)
        if not (creds or {}).get("email"):
            self.store.set_setting("luma_cloud_account", None)
        return {"summary": "Luma's number is disconnected on this device."}

    def sign_out_account(self):
        """Sign out of the Luma account on this computer. Memories stay here; Luma asks to sign in again."""
        self.store.set_setting("luma_cloud_device", None)
        self.store.set_setting("luma_cloud_account", None)
        self.store.set_setting("luma_account_pending", None)
        return {"summary": "Signed out. Your memories stay on this computer."}

    def register(self, device_name="Luma"):
        """Get a Luma Cloud credential without a phone number, for the phone app."""
        if self.connected():
            return
        _, body = self._call("POST", "/api/luma/device-register", {"device_name": str(device_name)[:60]}, auth=False)
        token = body.get("device_token")
        if not isinstance(token, str) or "." not in token:
            raise ProviderError("Luma Cloud didn't return a device credential.")
        self.store.set_setting("luma_cloud_device", {"token_b64": base64.b64encode(token.encode()).decode(), "phone": None, "name": None})

    # -- the Luma app on the owner's phone (payloads are end-to-end encrypted) ----
    def app_pair_start(self, secret_hash):
        _, body = self._call("POST", "/api/luma/app-pair-start", {"secret_hash": secret_hash})
        return body

    def app_inbox(self, cursor=None, wait=25):
        query = {"wait": str(int(wait))}
        if cursor:
            query["after"] = cursor
        _, body = self._call("GET", "/api/luma/app-inbox?" + urllib.parse.urlencode(query), timeout=wait + 15)
        return body

    def app_reply(self, messages):
        _, body = self._call("POST", "/api/luma/app-reply", {"messages": messages})
        return body

    def app_unpair(self, link_id):
        _, body = self._call("POST", "/api/luma/app-unpair", {"link_id": link_id})
        return body

    # -- account -------------------------------------------------------------
    def _cache(self, account):
        if account:
            self.store.set_setting("luma_cloud_account", {**account, "checked": self.clock()})

    def account(self, refresh=False):
        cached = self.store.setting("luma_cloud_account")
        if cached and not refresh and self.clock() - cached.get("checked", 0) < 300:
            return cached
        _, body = self._call("GET", "/api/luma/account")
        self._cache(body)
        return self.store.setting("luma_cloud_account")

    def cached_account(self):
        return self.store.setting("luma_cloud_account") if self.signed_in() else None

    def number_options(self, area_code=None):
        """A few real local numbers to pick from (area code defaults to the owner's own)."""
        area = re.sub(r"\D", "", str(area_code or ""))
        if area and not re.fullmatch(r"[2-9]\d{2}", area):
            raise ValueError("Use a 3-digit US area code, like 919.")
        _, body = self._call("GET", "/api/luma/number-options" + (f"?area_code={area}" if area else ""))
        return body

    def upgrade_link(self, number=None):
        if number is not None and not PHONE.fullmatch(str(number)):
            raise ValueError("Pick one of the numbers shown.")
        _, body = self._call("POST", "/api/luma/billing-checkout", {"number": number} if number else {})
        return body["url"]

    def claim_number(self, number=None):
        if number is not None and not PHONE.fullmatch(str(number)):
            raise ValueError("Pick one of the numbers shown.")
        _, body = self._call("POST", "/api/luma/number-claim", {"number": number} if number else {})
        self._cache(body)
        return self.store.setting("luma_cloud_account")

    def manage_link(self):
        _, body = self._call("POST", "/api/luma/billing-portal", {})
        return body["url"]

    # -- texting -------------------------------------------------------------
    @property
    def owner_phone(self):
        creds = self.credentials
        return creds.get("phone") if creds else None

    def send(self, to, body, client_ref, to_owner=False):
        payload = {"to": to, "body": body, "client_ref": client_ref, **({"to_owner": True} if to_owner else {})}
        status, result = self._call("POST", "/api/luma/sms-send", payload, side_effect=True)
        account = {k: result[k] for k in ("plan", "texts_used", "texts_limit", "texts_left", "number", "dedicated_number", "period_ends", "plus") if k in result}
        self._cache({**(self.store.setting("luma_cloud_account") or {}), **account})
        if status == 202 or result.get("status") == "unknown":
            raise OutcomeUnknown("I'm not sure that text went out. Check with them before I send it again.")
        left = result.get("texts_left")
        return {"provider": "luma_number", "message_id": result.get("message_id"), "status": result.get("status", "queued"),
                "from": result.get("from"), "texts_left": left, "plan": result.get("plan"),
                "summary": "Sent from Luma's number." + (f" {left} texts left this month." if isinstance(left, int) and left <= 5 else "")}

    def whatsapp_send(self, body, client_ref):
        """Luma answering its owner on WhatsApp: free, only to them, and only within a day of their last message there."""
        status, result = self._call("POST", "/api/luma/whatsapp-send", {"body": body, "client_ref": client_ref}, side_effect=True)
        if status == 202 or result.get("status") == "unknown":
            raise OutcomeUnknown("I'm not sure that WhatsApp message went out.")
        return {"provider": "whatsapp", "message_id": result.get("message_id"), "status": result.get("status", "sent"), "summary": "Answered on WhatsApp."}

    def inbox(self):
        cursor = self.store.setting("luma_cloud_inbox_cursor")
        query = "?after=" + urllib.parse.quote(cursor) if cursor else ""
        _, body = self._call("GET", "/api/luma/sms-inbox" + query)
        replies = [r for r in body.get("replies", []) if isinstance(r, dict)]
        if body.get("cursor"):
            self.store.set_setting("luma_cloud_inbox_cursor", body["cursor"])
        return replies
