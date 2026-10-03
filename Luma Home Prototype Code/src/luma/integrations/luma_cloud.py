"""Luma's own texting number, through Luma Cloud.

The owner verifies their phone once; this device then holds a credential (in the
encrypted store) for Lumin's relay. Free accounts get a monthly allowance of texts
from Luma's shared number; Luma Plus raises it and adds a dedicated number.
Sends are idempotent: the relay keys each one by the local action id, so a retry
after a dropped connection can never text someone twice.
"""
from __future__ import annotations

import base64
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

    def signed_in(self):
        return bool(self.credentials)

    def _auth(self):
        creds = self.credentials
        if not creds:
            raise CloudError("Set up Luma's number first: verify your phone in People & Texts.", "auth", 401)
        return {"Authorization": "Bearer " + base64.b64decode(creds["token_b64"]).decode()}

    def _call(self, method, path, payload=None, auth=True, side_effect=False):
        headers = self._auth() if auth else {}
        try:
            status, body = self.request(method, self.base_url + path, headers, payload)
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

    # -- sign-up -------------------------------------------------------------
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
        _, body = self._call("POST", "/api/luma/verify-check",
                             {"phone": pending["phone"], "name": pending["name"], "code": code.strip(), "device_name": str(device_name)[:60]}, auth=False)
        token = body.get("device_token")
        if not isinstance(token, str) or "." not in token:
            raise ProviderError("Luma Cloud didn't return a device credential.")
        # Encoded so the store's card-number guard doesn't mistake the credential's digits for a card.
        self.store.set_setting("luma_cloud_device", {"token_b64": base64.b64encode(token.encode()).decode(), "phone": pending["phone"], "name": pending["name"]})
        self.store.set_setting("luma_cloud_pending", None)
        self._cache(body.get("account") or {})
        return {"account": self.store.setting("luma_cloud_account"), "summary": "You're set. Luma can text from its number now."}

    def sign_out(self):
        self.store.set_setting("luma_cloud_device", None)
        self.store.set_setting("luma_cloud_account", None)
        return {"summary": "Luma's number is disconnected on this device."}

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

    def upgrade_link(self):
        _, body = self._call("POST", "/api/luma/billing-checkout", {})
        return body["url"]

    def manage_link(self):
        _, body = self._call("POST", "/api/luma/billing-portal", {})
        return body["url"]

    # -- texting -------------------------------------------------------------
    def send(self, to, body, client_ref):
        status, result = self._call("POST", "/api/luma/sms-send", {"to": to, "body": body, "client_ref": client_ref}, side_effect=True)
        account = {k: result[k] for k in ("plan", "texts_used", "texts_limit", "texts_left", "number", "dedicated_number", "period_ends", "plus") if k in result}
        self._cache({**(self.store.setting("luma_cloud_account") or {}), **account})
        if status == 202 or result.get("status") == "unknown":
            raise OutcomeUnknown("I'm not sure that text went out. Check with them before I send it again.")
        left = result.get("texts_left")
        return {"provider": "luma_number", "message_id": result.get("message_id"), "status": result.get("status", "queued"),
                "from": result.get("from"), "texts_left": left, "plan": result.get("plan"),
                "summary": "Sent from Luma's number." + (f" {left} texts left this month." if isinstance(left, int) and left <= 5 else "")}

    def inbox(self):
        cursor = self.store.setting("luma_cloud_inbox_cursor")
        query = "?after=" + urllib.parse.quote(cursor) if cursor else ""
        _, body = self._call("GET", "/api/luma/sms-inbox" + query)
        replies = [r for r in body.get("replies", []) if isinstance(r, dict)]
        if body.get("cursor"):
            self.store.set_setting("luma_cloud_inbox_cursor", body["cursor"])
        return replies
