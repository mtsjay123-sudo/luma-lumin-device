"""Configured integrations. Nothing connects until a registry action executes.

Inject transport in tests. No retries for side effects: timeout means unknown.
"""
from __future__ import annotations

import base64
import ipaddress
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request


class ProviderError(RuntimeError): pass
class OutcomeUnknown(ProviderError): pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # never forward authorization headers to another host


def transport(method, url, headers, payload=None, form=False):
    data = None
    if payload is not None:
        data = (urllib.parse.urlencode(payload) if form else json.dumps(payload)).encode()
        headers = {**headers, "Content-Type": "application/x-www-form-urlencoded" if form else "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=15) as response:
            content = response.read(1_000_001)
            if len(content) > 1_000_000: raise ProviderError("Provider response exceeds size limit.")
            return json.loads(content)
    except urllib.error.HTTPError as e:
        if method != "GET" and e.code >= 500:
            raise OutcomeUnknown("Provider server error; check the provider before trying again.") from None
        raise ProviderError(f"Provider rejected request (HTTP {e.code}). Check configuration/account; no automatic retry.") from None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        if method != "GET":
            raise OutcomeUnknown("Provider outcome is unknown; check its dashboard before creating a new action.") from None
        raise ProviderError("Provider unavailable or returned an invalid response.") from None


class Providers:
    def __init__(self, env=None, request=None):
        self.env = os.environ if env is None else env
        self.request = request or transport

    def require(self, *names):
        missing = [n for n in names if not self.env.get(n)]
        if missing: raise ProviderError("Configure " + ", ".join(missing) + " first.")

    def _twilio(self):
        self.require("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN")
        sid = self.env["TWILIO_ACCOUNT_SID"]
        if not re.fullmatch(r"AC[0-9a-fA-F]{32}", sid): raise ProviderError("Invalid Twilio account SID.")
        auth = base64.b64encode(f"{sid}:{self.env['TWILIO_AUTH_TOKEN']}".encode()).decode()
        return f"https://api.twilio.com/2010-04-01/Accounts/{sid}", {"Authorization": "Basic " + auth}

    def sms(self, args):
        self.require("TWILIO_FROM_NUMBER")
        base, headers = self._twilio()
        result = self.request("POST", base + "/Messages.json", headers, {"To": args["to"], "From": self.env["TWILIO_FROM_NUMBER"], "Body": args["body"]}, form=True)
        if not result.get("sid"):
            raise OutcomeUnknown("Twilio response has no message ID; check its dashboard before retrying.")
        return {"message_id": result["sid"], "status": result.get("status", "accepted"), "summary": "Twilio accepted the SMS request. Delivery is not confirmed."}

    def sms_status(self, args):
        """Read one provider receipt. A sent message has not necessarily arrived."""
        message_id = args.get("message_id") if isinstance(args, dict) else None
        if not isinstance(message_id, str) or not re.fullmatch(r"SM[0-9a-fA-F]{32}", message_id):
            raise ValueError("Use the Twilio message ID returned by a confirmed SMS action.")
        base, headers = self._twilio()
        result = self.request("GET", base + "/Messages/" + message_id + ".json", headers)
        if not isinstance(result, dict) or result.get("sid") != message_id:
            raise ProviderError("Twilio returned an invalid message receipt. Delivery remains unconfirmed.")
        summaries = {
            "accepted": "Twilio accepted the request. Delivery is not confirmed.",
            "scheduled": "Twilio reports the message is scheduled. It has not been sent.",
            "queued": "The message is queued at Twilio. Delivery is not confirmed.",
            "sending": "Twilio is sending the message. Delivery is not confirmed.",
            "sent": "Twilio reports the message was sent to the carrier. Delivery is not confirmed.",
            "delivered": "Twilio reports delivery. This does not confirm the recipient read the SMS.",
            "undelivered": "Twilio reports the message was not delivered. No retry was attempted.",
            "failed": "Twilio reports the message failed. No retry was attempted.",
            "canceled": "Twilio reports the scheduled message was canceled.",
            "receiving": "Twilio is receiving this inbound message.",
            "received": "Twilio received this inbound message; this is not an outbound delivery receipt.",
            "read": "Twilio reports the message was read on a supported messaging channel.",
            "partially_delivered": "Twilio reports partial delivery. Complete delivery is not confirmed.",
        }
        status = result.get("status")
        if not isinstance(status, str) or status not in summaries:
            status = "unknown"
        receipt = {"message_id": message_id, "status": status, "summary": summaries.get(status, "Twilio did not return a recognized status. Delivery remains unconfirmed.")}
        if result.get("error_code") is not None:
            receipt["error_code"] = str(result["error_code"])[:32]
        if isinstance(result.get("error_message"), str):
            receipt["error_message"] = " ".join(result["error_message"].split())[:400]
        return receipt

    def search(self, args):
        self.require("BRAVE_SEARCH_API_KEY")
        query = urllib.parse.urlencode({"q": args["query"], "count": 5})
        result = self.request("GET", "https://api.search.brave.com/res/v1/web/search?" + query, {"Accept": "application/json", "X-Subscription-Token": self.env["BRAVE_SEARCH_API_KEY"]})
        hits = [{"title": str(r.get("title", ""))[:200], "url": r["url"], "snippet": str(r.get("description", ""))[:500]} for r in result.get("web", {}).get("results", []) if urllib.parse.urlsplit(r.get("url", "")).scheme == "https"][:5]
        return {"results": hits, "summary": "Search results found. Prices, availability, tax and delivery fees must be checked at the merchant."}

    def light(self, args):
        self.require("HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN")
        base = self.env["HOME_ASSISTANT_URL"].rstrip("/")
        u = urllib.parse.urlsplit(base)
        if u.scheme not in {"http", "https"} or u.username or u.password or u.query or u.fragment:
            raise ProviderError("Configure a valid Home Assistant base URL without credentials or query strings.")
        if u.scheme == "http":
            try: local = ipaddress.ip_address(u.hostname).is_private or ipaddress.ip_address(u.hostname).is_loopback
            except ValueError: local = u.hostname == "localhost" or (u.hostname or "").endswith(".local")
            if not local: raise ProviderError("Remote Home Assistant connections require HTTPS.")
        allowed = {x.strip() for x in self.env.get("LUMA_ALLOWED_LIGHTS", "").split(",") if x.strip()}
        if args["entity_id"] not in allowed: raise ProviderError("This light is not in LUMA_ALLOWED_LIGHTS.")
        data = {"entity_id": args["entity_id"]}
        if args["state"] == "on": data["brightness_pct"] = args.get("brightness", 100)
        self.request("POST", base + "/api/services/light/turn_" + args["state"], {"Authorization": "Bearer " + self.env["HOME_ASSISTANT_TOKEN"]}, data)
        return {"summary": "Home Assistant accepted the light command. Physical device state is not independently verified."}

    def checkout(self, args):
        merchants = json.loads(self.env.get("LUMA_MERCHANTS_JSON", "{}"))
        url = merchants.get(args["merchant"])
        if not isinstance(url, str): raise ProviderError("Configure this merchant in LUMA_MERCHANTS_JSON first.")
        u = urllib.parse.urlsplit(url)
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment:
            raise ProviderError("Merchant URLs must be clean HTTPS pages without embedded credentials or query strings.")
        return {"handoff": True, "url": url, "items": args["items"], "budget_cents": args["budget_cents"], "summary": "Shopping list prepared. Open the merchant, build/review the cart and pay there with its saved wallet. No order has been placed and no price has been quoted."}
