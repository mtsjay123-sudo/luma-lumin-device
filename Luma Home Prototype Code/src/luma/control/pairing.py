"""One-use local pairing and revocable companion credentials.

The HTTP layer must require HTTPS, validate its actual Host/Origin, rate-limit
pairing attempts and never accept identity from forwarded headers. This module
does not start a listener or authorize any assistant action by itself.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import time
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


INVITE_SECONDS = 10 * 60
DEVICE_SECONDS = 30 * 24 * 60 * 60
MAX_DEVICES = 5
_TOKEN_RE = re.compile(r"(li|ld)_([a-f0-9]{32})\.([A-Za-z0-9_-]{43})\Z")
_ID_RE = re.compile(r"[a-f0-9]{32}\Z")
_PRIVATE_NETWORKS = tuple(ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"
))


class PairingError(ValueError):
    """A pairing request cannot be completed; messages contain no credentials."""


def _hash(token):
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _parse(token, prefix):
    if not isinstance(token, str) or len(token) > 100:
        return None
    match = _TOKEN_RE.fullmatch(token)
    return match.group(2) if match and match.group(1) == prefix else None


class PairingManager:
    """Encrypted persistent credentials, with a transaction for every mutation.

    Uses Store's SQLite connection, encryption and lock because its public
    transition() method is specific to assistant actions. BEGIN IMMEDIATE also
    serializes pairing across independent Store connections/processes.
    """

    def __init__(self, store, clock=time.time):
        self.store, self.clock = store, clock

    @contextlib.contextmanager
    def _transaction(self):
        with self.store.lock:
            self.store.db.execute("BEGIN IMMEDIATE")
            try:
                yield
                self.store.db.commit()
            except BaseException:
                self.store.db.rollback()
                raise

    def _read(self, kind, record_id):
        return self.store._decode(self.store.db.execute(
            "SELECT payload FROM records WHERE kind=? AND id=?", (kind, record_id)
        ).fetchone())

    def _write(self, kind, record_id, value, now):
        # All values here are constructed locally; tokens are replaced by hashes.
        payload = self.store.cipher.encrypt(json.dumps(value).encode())
        self.store.db.execute(
            "INSERT INTO records VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "payload=excluded.payload, updated=excluded.updated",
            (kind, record_id, now, now, payload),
        )

    def _devices(self):
        return [self.store._decode(r) for r in self.store.db.execute(
            "SELECT payload FROM records WHERE kind='phone_device' ORDER BY created DESC"
        ).fetchall()]

    @staticmethod
    def _active(device, now):
        return device.get("revoked_at") is None and now < device["expires_at"]

    def _metadata(self, device, now):
        return {k: device[k] for k in (
            "id", "name", "created_at", "expires_at", "revoked_at"
        )} | {"active": self._active(device, now)}

    def _check_capacity(self, now):
        if sum(self._active(d, now) for d in self._devices()) >= MAX_DEVICES:
            raise PairingError("Five phones are already paired. Revoke a phone before adding another.")

    def create_invite(self):
        """Issue one invite; a new invite immediately invalidates the previous one."""
        now = self.clock()
        token = "li_" + uuid.uuid4().hex + "." + secrets.token_urlsafe(32)
        expires_at = now + INVITE_SECONDS
        with self._transaction():
            self._check_capacity(now)
            self._write("phone_invite", "phone:invite", {
                "token_hash": _hash(token), "expires_at": expires_at,
                "created_at": now, "consumed_at": None,
            }, now)
        return {"token": token, "expires_at": expires_at}

    def pair(self, invite_token, device_name):
        """Consume an invite and return the new device token exactly once."""
        if not _parse(invite_token, "li"):
            raise PairingError("Pairing link is invalid or expired. Create a new link on Luma.")
        if not isinstance(device_name, str):
            raise PairingError("Enter a phone name using 1–60 visible characters.")
        name = device_name.strip()
        if not 1 <= len(name) <= 60 or any(
            not c.isprintable() or unicodedata.category(c).startswith("C") for c in name
        ):
            raise PairingError("Enter a phone name using 1–60 visible characters.")
        now = self.clock()
        device_id = uuid.uuid4().hex
        token = "ld_" + device_id + "." + secrets.token_urlsafe(32)
        with self._transaction():
            invite = self._read("phone_invite", "phone:invite")
            # Compare a fixed-length digest even for a missing invite.
            correct = hmac.compare_digest(_hash(invite_token), (invite or {}).get("token_hash", "0" * 64))
            if not correct or not invite or invite["consumed_at"] is not None or now >= invite["expires_at"]:
                raise PairingError("Pairing link is invalid or expired. Create a new link on Luma.")
            self._check_capacity(now)
            device = {"id": device_id, "name": name, "token_hash": _hash(token),
                      "created_at": now, "expires_at": now + DEVICE_SECONDS,
                      "revoked_at": None}
            invite["consumed_at"] = now
            self._write("phone_invite", "phone:invite", invite, now)
            self._write("phone_device", "phone-device:" + device_id, device, now)
        return {"token": token, "device": self._metadata(device, now)}

    def authenticate(self, device_token):
        """Return metadata for an active credential, otherwise None; never extend expiry."""
        device_id = _parse(device_token, "ld")
        if not device_id:
            return None
        with self.store.lock:
            device = self._read("phone_device", "phone-device:" + device_id)
        correct = hmac.compare_digest(_hash(device_token), (device or {}).get("token_hash", "0" * 64))
        now = self.clock()
        if not correct or not device or not self._active(device, now):
            return None
        return self._metadata(device, now)

    def list_devices(self):
        """Return labels, IDs and validity dates only; never a token or hash."""
        now = self.clock()
        with self.store.lock:
            return [self._metadata(d, now) for d in self._devices()]

    def revoke(self, device_id):
        if not isinstance(device_id, str) or not _ID_RE.fullmatch(device_id):
            return False
        now = self.clock()
        with self._transaction():
            device = self._read("phone_device", "phone-device:" + device_id)
            if not device:
                return False
            if device["revoked_at"] is None:
                device["revoked_at"] = now
                self._write("phone_device", "phone-device:" + device_id, device, now)
        return True


def private_ipv4(value):
    """Only RFC1918 LAN addresses: exclude public, loopback and link-local binds."""
    try:
        address = ipaddress.IPv4Address(value)
    except (ipaddress.AddressValueError, TypeError) as exc:
        raise ValueError("Use the Luma computer's private Wi-Fi IPv4 address.") from exc
    if not any(address in network for network in _PRIVATE_NETWORKS):
        raise ValueError("Phone access requires a private RFC1918 Wi-Fi IPv4 address.")
    return address


def _atomic_write(path, data, mode=0o600):
    temporary = path.with_name(path.name + "." + secrets.token_hex(8) + ".tmp")
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(fd, "wb") as target:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def ensure_local_certificate(directory, private_ip, clock=time.time):
    """Return (certificate_path, key_path) for a self-signed LAN HTTPS server.

    No certificate authority, public DNS, network request or trust-store change
    is involved. Browsers require the owner to trust this local certificate.
    Reuse only a matching key/certificate with the requested SAN and >1 day left.
    The dedicated directory and key remain owner-only. Changed Wi-Fi addresses
    cause regeneration and require the phone to trust the new certificate.
    """
    address = private_ipv4(private_ip)
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError("The Luma certificate directory cannot be a symbolic link.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    certificate_path, key_path = directory / "phone-cert.pem", directory / "phone-key.pem"
    lock_path = directory / ".certificate.lock"
    for path in (certificate_path, key_path, lock_path):
        if path.is_symlink():
            raise ValueError("Luma certificate files cannot be symbolic links.")
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        now = datetime.fromtimestamp(clock(), timezone.utc)
        try:
            certificate = x509.load_pem_x509_certificate(certificate_path.read_bytes())
            key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
            ips = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.IPAddress)
            key_bytes = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
            certificate_bytes = certificate.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
            if address in ips and ipaddress.IPv4Address("127.0.0.1") in ips and hmac.compare_digest(key_bytes, certificate_bytes) and certificate.not_valid_before_utc <= now and certificate.not_valid_after_utc > now + timedelta(days=1):
                os.chmod(key_path, 0o600)
                return certificate_path, key_path
        except (OSError, ValueError, TypeError, x509.ExtensionNotFound):
            pass
        key = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Luma local phone connection")])
        certificate = (
            x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=90))
            .add_extension(x509.SubjectAlternativeName([
                x509.IPAddress(address), x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.DNSName("localhost"),
            ]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(key, hashes.SHA256())
        )
        _atomic_write(key_path, key.private_bytes(serialization.Encoding.PEM,
                      serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        _atomic_write(certificate_path, certificate.public_bytes(serialization.Encoding.PEM))
        return certificate_path, key_path
