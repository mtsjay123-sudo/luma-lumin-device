"""A release: what it is, and how a Luma knows it's really ours.

A release is a manifest (a small JSON file) and its pieces (the code as one archive today; a brain or a small reader
as pieces of their own, so a 3 GB brain isn't sent again for a one-line fix). The manifest names each piece with its
size and SHA-256, and is signed with Ed25519. A Luma holds the public half and installs nothing whose manifest that
key didn't sign, and no piece whose bytes don't match the manifest.

No release key exists yet: PUBLIC_KEYS is empty, so nothing verifies and nothing can be installed until the owner
makes one (`python scripts/release.py keygen`) and its public half is put here. The private half never goes on a
device or in the repository.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

PUBLIC_KEYS: tuple[str, ...] = ()     # base64 of each release key's public half. Empty: no release can be installed.
VERSION = re.compile(r"\d{1,4}\.\d{1,4}\.\d{1,6}")
PIECE = re.compile(r"[a-z][a-z0-9_-]{0,31}")
FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,120}")
BIGGEST = {"code": 200 * 2 ** 20}     # a piece bigger than this isn't fetched (others: 8 GB)


class Refused(ValueError):
    """This release isn't installed. The message says why, for the log."""


def canonical(manifest: dict) -> bytes:
    """The exact bytes that are signed: the same manifest always gives the same bytes."""
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def number(version: str) -> tuple:
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise Refused("That version number isn't one of ours.")
    return tuple(int(part) for part in version.split("."))


def sign(manifest: dict, private_key: Ed25519PrivateKey) -> str:
    return base64.b64encode(private_key.sign(canonical(manifest))).decode()


def keygen():
    """A new release key: (private half as base64, public half as base64). The private half is the owner's to keep."""
    from cryptography.hazmat.primitives import serialization
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(private).decode(), base64.b64encode(public).decode()


def verify(manifest_bytes: bytes, signature: str, public_keys=None) -> dict:
    """The manifest, if one of our keys signed exactly these bytes and it's well formed. Otherwise Refused."""
    keys = PUBLIC_KEYS if public_keys is None else tuple(public_keys)
    if not keys:
        raise Refused("No release key is set on this Luma, so nothing can be installed.")
    if not isinstance(manifest_bytes, (bytes, bytearray)) or len(manifest_bytes) > 200_000:
        raise Refused("The release's manifest is too big to be one of ours.")
    try:
        raw = base64.b64decode(str(signature), validate=True)
    except Exception:
        raise Refused("The release's signature isn't readable.") from None
    for key in keys:
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(key)).verify(raw, bytes(manifest_bytes))
            break
        except (InvalidSignature, ValueError):
            continue
    else:
        raise Refused("The release isn't signed by Luma's key.")
    try:
        manifest = json.loads(bytes(manifest_bytes).decode())
    except Exception:
        raise Refused("The release's manifest isn't readable.") from None
    if canonical(manifest) != bytes(manifest_bytes):
        raise Refused("The release's manifest isn't in the form that was signed.")
    return check(manifest)


def check(manifest: dict) -> dict:
    """Well formed: a version, a rollout share, and pieces with a plain file name, a size and a SHA-256 each."""
    if not isinstance(manifest, dict):
        raise Refused("The release's manifest isn't a manifest.")
    number(manifest.get("version"))
    share = manifest.get("share", 1)
    if not isinstance(share, (int, float)) or isinstance(share, bool) or not 0 <= share <= 1:
        raise Refused("The release's rollout share isn't between none and everyone.")
    pieces = manifest.get("pieces")
    if not isinstance(pieces, list) or not 1 <= len(pieces) <= 20:
        raise Refused("The release has no pieces.")
    seen = set()
    for piece in pieces:
        if not isinstance(piece, dict) or not PIECE.fullmatch(str(piece.get("name") or "")) or piece["name"] in seen:
            raise Refused("A piece of the release has no proper name.")
        seen.add(piece["name"])
        if not FILE.fullmatch(str(piece.get("file") or "")) or ".." in piece["file"]:
            raise Refused(f"The {piece['name']} piece's file name isn't a plain one.")
        if not re.fullmatch(r"[0-9a-f]{64}", str(piece.get("sha256") or "")):
            raise Refused(f"The {piece['name']} piece has no SHA-256.")
        size = piece.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= BIGGEST.get(piece["name"], 8 * 2 ** 30):
            raise Refused(f"The {piece['name']} piece's size isn't believable.")
    if "code" not in seen and not manifest.get("needs"):
        raise Refused("A release without the code has to say which version of the code it goes with.")
    return manifest


def matches(piece: dict, data: bytes) -> bool:
    return len(data) == piece["size"] and hashlib.sha256(data).hexdigest() == piece["sha256"]


def in_rollout(manifest: dict, install_id: str) -> bool:
    """Whether this Luma is in the share of homes the release has reached so far. The same home gets the same answer
    for a release every time, a different one for the next release, and its id never leaves the device."""
    share = float(manifest.get("share", 1))
    if share >= 1:
        return True
    digest = hashlib.sha256(f"{install_id}:{manifest['version']}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2 ** 64 < share
