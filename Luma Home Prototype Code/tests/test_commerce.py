"""No tests create real provider lists, carts, charges or orders."""
import copy
import math
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlsplit

from luma.integrations.commerce import GroceryService, validate_list
from luma.integrations.providers import OutcomeUnknown, ProviderError


class Fixture:
    def __init__(self):
        self.calls = []
        self.error = None
        self.response = {"products_link_url": "https://www.instacart.com/store/shopping_lists/fixture-list?aff_id=fixture"}
        self.retailers = {"retailers": [{"retailer_key": "food-lion", "name": "Food Lion"}, {"retailer_key": "another", "name": "Another Grocer"}]}

    def __call__(self, method, url, headers, payload=None):
        self.calls.append((method, url, copy.deepcopy(headers), copy.deepcopy(payload)))
        if self.error:
            raise self.error
        return copy.deepcopy(self.retailers if method == "GET" else self.response)


class CommerceTests(unittest.TestCase):
    def setUp(self):
        self.env = {"INSTACART_API_KEY": "fixture-not-a-real-key"}
        self.http = Fixture()
        self.now = 1788782400
        self.service = GroceryService(self.env, self.http, lambda: self.now)
        self.args = {"title": "Breakfast", "items": [{"name": "eggs", "quantity": 12, "unit": "each"}, {"name": "whole milk", "quantity": 1, "unit": "gallon"}]}

    def test_exact_items_and_measurements_sent_to_documented_endpoint(self):
        receipt = self.service.create_list(self.args)
        method, url, headers, payload = self.http.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://connect.instacart.com/idp/v1/products/products_link")
        self.assertEqual(headers["Authorization"], "Bearer fixture-not-a-real-key")
        self.assertEqual(payload["line_items"][0], {"name": "eggs", "line_item_measurements": [{"quantity": 12, "unit": "each"}]})
        self.assertNotIn("quantity", payload["line_items"][0])
        self.assertEqual(receipt["items"][0]["quantity"], 12)
        self.assertEqual(receipt["provider_reference"], self.http.response["products_link_url"])

    def test_receipt_does_not_invent_price_inventory_cart_or_order(self):
        receipt = self.service.create_list(self.args)
        self.assertEqual(receipt["status"], "shopping_list_created")
        for key in ["provider_list_id", "cart_id", "order_id", "total"]:
            self.assertIsNone(receipt[key])
        for key in ["order_placed", "payment_attempted", "retailer_selected"]:
            self.assertFalse(receipt[key])
        self.assertTrue(receipt["checkout_required"])
        self.assertIsNone(receipt["items"][0]["price"])
        self.assertFalse(receipt["items"][0]["inventory_checked"])
        self.assertTrue(receipt["local_receipt_id"].startswith("grocery-"))

    def test_identical_list_reuses_provider_url_even_concurrently(self):
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: self.service.create_list(self.args), range(2)))
        self.assertEqual(len(self.http.calls), 1)
        self.assertEqual(results[0]["url"], results[1]["url"])
        self.assertEqual({r["reused"] for r in results}, {True, False})
        results[0]["items"][0]["name"] = "changed outside cache"
        self.assertEqual(self.service.create_list(self.args)["items"][0]["name"], "eggs")

    def test_changed_or_expired_list_uses_new_request(self):
        self.service.create_list(self.args)
        self.args["items"][0]["quantity"] = 6
        self.service.create_list(self.args)
        self.now += 7 * 86400 + 1
        self.service.create_list(self.args)
        self.assertEqual(len(self.http.calls), 3)

    def test_missing_configuration_never_makes_request(self):
        for env in [{}, {"INSTACART_API_KEY": "fixture", "INSTACART_ENVIRONMENT": "https://attacker.example"}]:
            with self.assertRaises(ProviderError):
                GroceryService(env, self.http).create_list(self.args)
        self.assertEqual(self.http.calls, [])

    def test_invalid_quantities_units_and_payment_material_are_rejected(self):
        for quantity in [0, -1, True, "12", math.inf, math.nan, 1001]:
            args = copy.deepcopy(self.args)
            args["items"][0]["quantity"] = quantity
            with self.assertRaises(ValueError):
                self.service.create_list(args)
        for change in [{"unit": "truckload"}, {"card_number": "4111111111111111"}, {"name": "password: secret"}]:
            args = copy.deepcopy(self.args)
            args["items"][0].update(change)
            with self.assertRaises(ValueError):
                self.service.create_list(args)
        self.assertEqual(self.http.calls, [])

    def test_unknown_result_does_not_automatically_retry(self):
        self.http.error = OutcomeUnknown("Fixture timeout")
        for _ in range(2):
            with self.assertRaises(OutcomeUnknown):
                self.service.create_list(self.args)
        self.assertEqual(len(self.http.calls), 1)

    def test_unusable_success_is_unknown_and_does_not_accept_external_url(self):
        for url in [None, "https://evil.example/list", "http://instacart.com/list", "https://instacart.com.evil.example/list", "https://user:secret@instacart.com/list", "https://instacart.com/"]:
            http = Fixture()
            http.response = {"products_link_url": url}
            service = GroceryService(self.env, http)
            with self.assertRaises(OutcomeUnknown):
                service.create_list(self.args)
            with self.assertRaises(OutcomeUnknown):
                service.create_list(self.args)
            self.assertEqual(len(http.calls), 1)

    def test_nearby_retailers_are_provider_data_not_guaranteed_stores_or_stock(self):
        result = self.service.nearby({"postal_code": "27514", "country_code": "US"})
        self.assertTrue(result["food_lion_listed"])
        self.assertFalse(result["retailers"][0]["inventory_checked"])
        self.assertFalse(result["retailers"][0]["delivery_slot_checked"])
        self.assertEqual(parse_qs(urlsplit(self.http.calls[0][1]).query), {"postal_code": ["27514"], "country_code": ["US"]})
        self.http.retailers = {"retailers": []}
        self.assertFalse(self.service.nearby({"postal_code": "27514", "country_code": "US"})["food_lion_listed"])

    def test_canadian_postal_code_is_encoded_and_invalid_location_is_rejected(self):
        self.service.nearby({"postal_code": "m5v 3l9", "country_code": "CA"})
        self.assertIn("postal_code=M5V+3L9", self.http.calls[0][1])
        for change in [{"country_code": "UK"}, {"postal_code": "bad?query=1"}]:
            with self.assertRaises(ValueError):
                self.service.nearby({"postal_code": "27514", "country_code": "US", **change})
        self.assertEqual(len(self.http.calls), 1)

    def test_development_requests_are_identified_and_use_official_dev_host(self):
        self.env["INSTACART_ENVIRONMENT"] = "development"
        self.http.response = {"products_link_url": "https://www.dev.instacart.tools/store/shopping_lists/fixture"}
        result = self.service.create_list(self.args)
        self.assertEqual(result["environment"], "development")
        self.assertTrue(self.http.calls[0][1].startswith("https://connect.dev.instacart.tools/"))

    def test_validation_can_prepare_ui_without_network_or_credentials(self):
        self.assertEqual(validate_list(self.args), self.args)
        self.assertEqual(self.http.calls, [])


if __name__ == "__main__":
    unittest.main()
