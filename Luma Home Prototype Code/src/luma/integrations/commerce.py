"""Instacart shoppable lists and nearby retailers; never order placement.

Only documented Developer Platform endpoints are used. Product matching,
store-specific prices, fulfillment and payment remain in merchant checkout.
The provider returns a URL, not an order/cart ID or item availability receipt.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import threading
import time
from urllib.parse import urlencode, urlsplit

from luma.integrations.providers import OutcomeUnknown, ProviderError, transport
from luma.memory.store import reject_payment_secrets


UNITS = ("each", "package", "ounce", "pound", "gram", "kilogram", "liter",
         "milliliter", "gallon", "cup", "tablespoon", "teaspoon", "can",
         "bunch", "head", "pint", "quart")
BASES = {"production": "https://connect.instacart.com", "development": "https://connect.dev.instacart.tools"}
LINK_DAYS = 7


def _text(value, label, limit=120):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError(f"{label} must contain 1–{limit} characters without control characters.")
    return value.strip()


def validate_list(args):
    """Return a normalized, exact shopping list without making a request."""
    if not isinstance(args, dict) or set(args) != {"title", "items"}:
        raise ValueError("Provide exactly title and items for the shopping list.")
    reject_payment_secrets(args)
    title = _text(args["title"], "Title")
    if not isinstance(args["items"], list) or not 1 <= len(args["items"]) <= 50:
        raise ValueError("A shopping list must contain 1–50 items.")
    items = []
    for item in args["items"]:
        if not isinstance(item, dict) or set(item) != {"name", "quantity", "unit"}:
            raise ValueError("Each item must contain exactly name, quantity and unit.")
        name = _text(item["name"], "Item name")
        quantity = item["quantity"]
        if type(quantity) not in {int, float} or not 0 < quantity <= 1000 or not math.isfinite(quantity):
            raise ValueError("Item quantities must be finite numbers greater than zero, up to 1000.")
        if item["unit"] not in UNITS:
            raise ValueError("Choose a supported grocery unit: " + ", ".join(UNITS) + ".")
        items.append({"name": name, "quantity": quantity, "unit": item["unit"]})
    return {"title": title, "items": items}


class GroceryService:
    def __init__(self, env=None, request=None, clock=None):
        self.env = os.environ if env is None else env
        self.request = request or transport
        self.clock = clock or time.time
        self._cache = {}
        self._unknown = set()
        self._lock = threading.RLock()

    def _configuration(self):
        environment = self.env.get("INSTACART_ENVIRONMENT", "production")
        if environment not in BASES:
            raise ProviderError("INSTACART_ENVIRONMENT must be production or development.")
        key = self.env.get("INSTACART_API_KEY", "")
        if not isinstance(key, str) or not key or "\n" in key or "\r" in key:
            raise ProviderError("Configure an Instacart Developer Platform INSTACART_API_KEY first.")
        return environment, BASES[environment], {"Authorization": "Bearer " + key, "Accept": "application/json"}

    def nearby(self, args):
        if not isinstance(args, dict) or set(args) != {"postal_code", "country_code"}:
            raise ValueError("Provide postal_code and country_code to find nearby retailers.")
        country = args["country_code"]
        if not isinstance(country, str) or country not in {"US", "CA"} or not isinstance(args["postal_code"], str):
            raise ValueError("Choose US or CA and enter a valid postal code.")
        postal = args["postal_code"].strip().upper()
        pattern = r"\d{5}(?:-\d{4})?" if country == "US" else r"[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTVWXYZ] ?\d[ABCEGHJ-NPRSTVWXYZ]\d"
        if not re.fullmatch(pattern, postal):
            raise ValueError("Enter a valid postal code for the selected country.")
        environment, base, headers = self._configuration()
        result = self.request("GET", base + "/idp/v1/retailers?" + urlencode({"postal_code": postal, "country_code": country}), headers)
        if not isinstance(result, dict) or not isinstance(result.get("retailers"), list):
            raise ProviderError("Instacart did not return a usable retailer list. Local availability is unverified.")
        retailers = []
        for item in result["retailers"][:200]:
            if not isinstance(item, dict):
                continue
            key, name = item.get("retailer_key"), item.get("name")
            if not isinstance(key, str) or not isinstance(name, str) or not key.strip() or not name.strip():
                continue
            retailers.append({"retailer_key": key[:150], "name": name[:150],
                              "is_food_lion": re.sub(r"[^a-z]", "", name.lower()) == "foodlion",
                              "inventory_checked": False, "delivery_slot_checked": False})
        if result["retailers"] and not retailers:
            raise ProviderError("Instacart returned retailer records that could not be verified.")
        return {"provider": "Instacart", "environment": environment, "postal_code": postal,
                "country_code": country, "retailers": retailers,
                "food_lion_listed": any(r["is_food_lion"] for r in retailers),
                "checked_at": self.clock(), "truncated": len(result["retailers"]) > 200,
                "summary": "Instacart returned these nearby retailer organizations. Choose the actual store and confirm address, item availability and fulfillment slots at checkout."}

    def create_list(self, args):
        normalized = validate_list(args)
        environment, base, headers = self._configuration()
        payload = {"title": normalized["title"], "link_type": "shopping_list", "expires_in": LINK_DAYS,
                   "line_items": [{"name": item["name"],
                                   "line_item_measurements": [{"quantity": item["quantity"], "unit": item["unit"]}]}
                                  for item in normalized["items"]]}
        fingerprint = hashlib.sha256(json.dumps([environment, payload], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        with self._lock:
            existing = self._cache.get(fingerprint)
            if existing and existing["expires_at"] > self.clock():
                return {**copy.deepcopy(existing), "reused": True}
            if fingerprint in self._unknown:
                raise OutcomeUnknown("The earlier list-creation result is uncertain. No duplicate request was sent; inspect the previous action before retrying.")
            if len(self._unknown) >= 100:
                raise ProviderError("Too many unresolved list requests. Review provider configuration before creating more lists.")
            requested_at = self.clock()
            try:
                result = self.request("POST", base + "/idp/v1/products/products_link", headers, payload)
            except OutcomeUnknown:
                self._unknown.add(fingerprint)
                raise
            url = result.get("products_link_url") if isinstance(result, dict) else None
            if not self._valid_link(url, environment):
                self._unknown.add(fingerprint)
                raise OutcomeUnknown("Instacart did not return a valid shopping-list link. List creation is unconfirmed; no order or payment was attempted.")
            now = self.clock()
            receipt = {"provider": "Instacart", "environment": environment,
                       "status": "shopping_list_created", "title": normalized["title"],
                       "url": url, "provider_reference": url,
                       # This is an application fingerprint, never a claimed merchant ID.
                       "local_receipt_id": "grocery-" + fingerprint[:20],
                       "provider_list_id": None, "cart_id": None, "order_id": None,
                       "items": [{**item, "match_status": "review_on_instacart", "product_id": None,
                                  "price": None, "inventory_checked": False} for item in normalized["items"]],
                       "item_count": len(normalized["items"]), "created_at": now,
                       "expires_at": requested_at + LINK_DAYS * 86400, "requested_validity_days": LINK_DAYS,
                       "expires_at_source": "calculated_from_requested_ttl", "reused": False,
                       "checkout_required": True, "order_placed": False, "payment_attempted": False,
                       "retailer_selected": False, "total": None,
                       "summary": "Your shoppable list was created on Instacart. Open it, choose an available retailer such as Food Lion, review matched products and quantities, then check out with the merchant. No cart contents, inventory, final price, delivery slot or order are confirmed."}
            self._cache = {k: v for k, v in self._cache.items() if v["expires_at"] > now}
            if len(self._cache) >= 100:
                self._cache.pop(next(iter(self._cache)))
            self._cache[fingerprint] = copy.deepcopy(receipt)
            return receipt

    @staticmethod
    def _valid_link(url, environment):
        if not isinstance(url, str) or not 1 <= len(url) <= 4096 or any(ord(c) < 33 for c in url):
            return False
        try:
            parsed = urlsplit(url)
            host = (parsed.hostname or "").lower()
            allowed = host == "instacart.com" or host.endswith(".instacart.com")
            if environment == "development":
                allowed = allowed or host == "instacart.tools" or host.endswith(".instacart.tools")
            return parsed.scheme == "https" and allowed and not parsed.username and not parsed.password and parsed.port in {None, 443} and bool(parsed.path.strip("/"))
        except ValueError:
            return False
