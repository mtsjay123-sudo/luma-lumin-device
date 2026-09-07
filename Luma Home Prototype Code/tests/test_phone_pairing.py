import hashlib
import ipaddress
import json
from pathlib import Path
import stat
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from luma.control.pairing import (
    DEVICE_SECONDS, INVITE_SECONDS, PairingError, PairingManager,
    ensure_local_certificate, private_ipv4,
)
from luma.memory.store import Store


class PhonePairingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = 1788782400
        self.store = Store(self.root / "state.db", self.root / "state.key")
        self.manager = PairingManager(self.store, clock=lambda: self.now)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def pair(self, name="My phone"):
        return self.manager.pair(self.manager.create_invite()["token"], name)

    def test_pairing_returns_a_revocable_persistent_credential_not_stored_in_plaintext(self):
        invite = self.manager.create_invite()
        paired = self.manager.pair(invite["token"], "Amiri’s iPhone")
        self.assertEqual(self.manager.authenticate(paired["token"])["name"], "Amiri’s iPhone")
        serialized = json.dumps(self.store.all("phone_invite") + self.store.all("phone_device"))
        self.assertNotIn(invite["token"], serialized)
        self.assertNotIn(paired["token"], serialized)
        self.assertNotIn(hashlib.sha256(paired["token"].encode()).hexdigest().encode(), self.store.db_path.read_bytes())
        self.store.close()
        self.store = Store(self.root / "state.db", self.root / "state.key")
        self.manager = PairingManager(self.store, clock=lambda: self.now)
        self.assertIsNotNone(self.manager.authenticate(paired["token"]))
        self.assertTrue(self.manager.revoke(paired["device"]["id"]))
        self.assertIsNone(self.manager.authenticate(paired["token"]))

    def test_invite_is_single_use_across_independent_database_connections(self):
        invite = self.manager.create_invite()
        second_store = Store(self.root / "state.db", self.root / "state.key")
        second_manager = PairingManager(second_store, clock=lambda: self.now)
        def consume(manager):
            try:
                return manager.pair(invite["token"], "Phone")
            except PairingError:
                return None
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(consume, [self.manager, second_manager]))
            self.assertEqual(sum(r is not None for r in results), 1)
            self.assertEqual(len(self.manager.list_devices()), 1)
        finally:
            second_store.close()

    def test_new_invite_invalidates_old_and_exact_expiry_rejects(self):
        old = self.manager.create_invite()
        latest = self.manager.create_invite()
        with self.assertRaises(PairingError):
            self.manager.pair(old["token"], "Old link")
        self.now += INVITE_SECONDS
        with self.assertRaises(PairingError):
            self.manager.pair(latest["token"], "Expired link")
        self.assertEqual(self.manager.list_devices(), [])

    def test_authentication_does_not_extend_thirty_day_expiry(self):
        paired = self.pair()
        self.now += DEVICE_SECONDS - 1
        self.assertIsNotNone(self.manager.authenticate(paired["token"]))
        self.now += 1
        self.assertIsNone(self.manager.authenticate(paired["token"]))
        self.assertFalse(self.manager.list_devices()[0]["active"])

    def test_five_device_cap_and_revocation_frees_a_slot(self):
        phones = [self.pair("Phone " + chr(65 + i)) for i in range(5)]
        with self.assertRaises(PairingError):
            self.manager.create_invite()
        self.manager.revoke(phones[0]["device"]["id"])
        self.pair("Replacement phone")
        self.assertEqual(sum(d["active"] for d in self.manager.list_devices()), 5)

    def test_expired_devices_do_not_block_new_pairing(self):
        for i in range(5):
            self.pair("Phone " + chr(65 + i))
        self.now += DEVICE_SECONDS
        self.assertIsNotNone(self.manager.authenticate(self.pair()["token"]))

    def test_bad_inputs_do_not_consume_invite(self):
        invite = self.manager.create_invite()
        for name in [None, {}, "", "   ", "x" * 61, "hidden\nname", "wrong\u202ename"]:
            with self.assertRaises(PairingError):
                self.manager.pair(invite["token"], name)
        result = self.manager.pair(invite["token"], "Valid name")
        self.assertEqual(len(result["device"]["id"]), 32)

    def test_token_tampering_and_type_confusion_fail(self):
        invite = self.manager.create_invite()
        paired = self.manager.pair(invite["token"], "Phone")
        for token in [None, {}, 123, "x" * 10000, invite["token"], paired["token"] + "\n",
                      paired["token"][:-1] + ("A" if paired["token"][-1] != "A" else "B"),
                      "ld_" + "0" * 32 + "." + "A" * 43]:
            self.assertIsNone(self.manager.authenticate(token))
        with self.assertRaises(PairingError):
            self.manager.pair(paired["token"], "Phone")
        self.assertFalse(self.manager.revoke("phone:invite"))
        self.assertFalse(self.manager.revoke("f" * 32))

    def test_list_contains_only_metadata(self):
        self.pair()
        self.assertEqual(set(self.manager.list_devices()[0]), {
            "id", "name", "created_at", "expires_at", "revoked_at", "active"
        })


class LocalCertificateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = 1788782400

    def tearDown(self):
        self.temp.cleanup()

    def ensure(self, address="192.168.1.30"):
        return ensure_local_certificate(self.root / "tls", address, clock=lambda: self.now)

    def test_matching_certificate_reuses_owner_only_key_and_expected_sans(self):
        certificate_path, key_path = self.ensure()
        original_key = key_path.read_bytes()
        certificate = x509.load_pem_x509_certificate(certificate_path.read_bytes())
        ips = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)
        self.assertIn(ipaddress.ip_address("192.168.1.30"), ips)
        self.assertIn(ipaddress.ip_address("127.0.0.1"), ips)
        key = serialization.load_pem_private_key(original_key, password=None)
        self.assertEqual(key.public_key().public_numbers(), certificate.public_key().public_numbers())
        self.assertEqual(stat.S_IMODE(key_path.stat().st_mode), 0o600)
        self.assertEqual(self.ensure(), (certificate_path, key_path))
        self.assertEqual(original_key, key_path.read_bytes())

    def test_address_change_and_expiry_generate_matching_new_certificates(self):
        certificate_path, key_path = self.ensure()
        old = certificate_path.read_bytes()
        self.ensure("10.0.0.7")
        self.assertNotEqual(old, certificate_path.read_bytes())
        changed = certificate_path.read_bytes()
        self.now += 90 * 24 * 3600
        self.ensure("10.0.0.7")
        self.assertNotEqual(changed, certificate_path.read_bytes())

    def test_public_or_ambiguous_addresses_are_rejected(self):
        for address in ["8.8.8.8", "127.0.0.1", "169.254.10.1", "0.0.0.0", "::1", "localhost", "100.64.0.1", None]:
            with self.assertRaises(ValueError):
                private_ipv4(address)
        self.assertEqual(str(private_ipv4("172.16.1.1")), "172.16.1.1")

    def test_symlink_key_is_never_followed_or_overwritten(self):
        directory = self.root / "tls"
        directory.mkdir()
        secret = self.root / "other-file"
        secret.write_text("existing owner data")
        (directory / "phone-key.pem").symlink_to(secret)
        with self.assertRaises(ValueError):
            self.ensure()
        self.assertEqual(secret.read_text(), "existing owner data")


if __name__ == "__main__":
    unittest.main()
