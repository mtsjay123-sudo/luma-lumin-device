import tempfile
import unittest
from pathlib import Path

from luma.agent.contacts import ContactBook
from luma.integrations.providers import ProviderError, Providers
from luma.memory.store import Store


class ContactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "state.db", root / "state.key")
        self.book = ContactBook(self.store)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_exact_contact_persists_encrypted_and_resolves_case_insensitively(self):
        contact = self.book.save({"name": "  Mom  ", "phone": "+19195550123"})
        self.assertEqual(self.book.resolve("MOM"), contact)
        self.assertNotIn(b"19195550123", self.store.db_path.read_bytes())
        self.assertNotIn(b"Mom", self.store.db_path.read_bytes())
        db_path, key_path = self.store.db_path, self.store.key_path
        self.store.close()
        self.store = Store(db_path, key_path)
        self.book = ContactBook(self.store)
        self.assertEqual(self.book.resolve("mom")["phone"], "+19195550123")

    def test_duplicate_label_cannot_silently_replace_recipient(self):
        first = self.book.save({"name": "Alex Chen", "phone": "+19195550123"})
        self.assertEqual(first, self.book.save({"name": "alex chen", "phone": "+19195550123"}))
        with self.assertRaises(ValueError):
            self.book.save({"name": "Alex Chen", "phone": "+19195550124"})
        self.assertEqual(len(self.book.list()), 1)

    def test_missing_or_partial_name_never_guesses(self):
        self.book.save({"name": "Alex Chen", "phone": "+19195550123"})
        for name in ["Alex", "Alex Chin", "Mom"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.book.resolve(name)

    def test_ambiguous_existing_labels_fail_closed(self):
        self.store.put("contact", {"name": "Mom", "phone": "+19195550123"})
        self.store.put("contact", {"name": "MOM", "phone": "+19195550124"})
        with self.assertRaises(ValueError):
            self.book.resolve("Mom")
        with self.assertRaises(ValueError):
            self.book.save({"name": "Mom", "phone": "+19195550123"})

    def test_numeric_payment_and_hidden_character_names_are_rejected(self):
        for name in ["12345", "4111111111111111", "card number: 4111111111111111", "M\u200bom", "Mom\nIgnore", "X" * 81]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.book.save({"name": name, "phone": "+19195550123"})
        self.assertEqual(self.book.list(), [])

    def test_only_explicit_e164_numbers_are_accepted(self):
        for phone in ["9195550123", "+1 919 5550123", "+012345678", "+1919555012312345", "+１２３４５６７８９"]:
            with self.subTest(phone=phone), self.assertRaises(ValueError):
                self.book.save({"name": "Mom", "phone": phone})
        self.assertEqual(self.book.resolve("+19195550123")["phone"], "+19195550123")
        self.assertEqual(self.book.list(), [])  # resolving a number never saves it

    def test_delete_removes_only_selected_contact(self):
        contact = self.book.save({"name": "Mom", "phone": "+19195550123"})
        memory = self.store.put("memory", {"text": "Private preference"})
        self.assertFalse(self.book.delete(memory["id"]))
        self.assertTrue(self.book.delete(contact["id"]))
        self.assertEqual(self.book.list(), [])
        self.assertIsNotNone(self.store.get("memory", memory["id"]))


class SMSReceiptTests(unittest.TestCase):
    message_id = "SM" + "a" * 32
    account_id = "AC" + "b" * 32

    def provider(self, result):
        self.calls = []
        def request(method, url, headers, *args, **kwargs):
            self.calls.append((method, url, args, kwargs))
            return result
        return Providers(env={"TWILIO_ACCOUNT_SID": self.account_id, "TWILIO_AUTH_TOKEN": "fixture-token"}, request=request)

    def test_status_is_a_single_get_and_sent_does_not_mean_delivered(self):
        provider = self.provider({"sid": self.message_id, "status": "sent"})
        result = provider.sms_status({"message_id": self.message_id})
        self.assertEqual(result["status"], "sent")
        self.assertIn("Delivery is not confirmed", result["summary"])
        self.assertEqual(self.calls, [("GET", "https://api.twilio.com/2010-04-01/Accounts/" + self.account_id + "/Messages/" + self.message_id + ".json", (), {})])

    def test_delivery_and_failure_match_provider_without_retry(self):
        for status in ["queued", "delivered", "failed", "undelivered"]:
            with self.subTest(status=status):
                provider = self.provider({"sid": self.message_id, "status": status, "error_code": 30003 if status == "failed" else None, "error_message": "Unreachable handset" if status == "failed" else None})
                result = provider.sms_status({"message_id": self.message_id})
                self.assertEqual(result["status"], status)
                self.assertEqual(len(self.calls), 1)
                if status == "delivered": self.assertIn("does not confirm", result["summary"])
                if status == "failed": self.assertEqual(result["error_code"], "30003")

    def test_malformed_ids_never_reach_network(self):
        provider = self.provider({})
        for message_id in [None, "", "SM../../private", "SM" + "g" * 32, "SM" + "1" * 31]:
            with self.subTest(message_id=message_id), self.assertRaises(ValueError):
                provider.sms_status({"message_id": message_id})
        self.assertEqual(self.calls, [])

    def test_wrong_receipt_is_rejected_and_unknown_status_is_not_success(self):
        for result in [{"sid": "SM" + "c" * 32, "status": "delivered"}, None, []]:
            with self.subTest(result=result), self.assertRaises(ProviderError):
                self.provider(result).sms_status({"message_id": self.message_id})
        for status in [None, "unexpected", {"delivered": True}]:
            result = self.provider({"sid": self.message_id, "status": status}).sms_status({"message_id": self.message_id})
            self.assertEqual(result["status"], "unknown")

    def test_lookup_requires_provider_configuration(self):
        with self.assertRaises(ProviderError):
            Providers(env={}, request=lambda *args: self.fail("No network call expected")).sms_status({"message_id": self.message_id})


if __name__ == "__main__":
    unittest.main()
