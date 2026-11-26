"""A backup the owner keeps, and getting a Luma back from it (docs/GAME_PLAN.md, E3; docs/STORAGE.md).

Everything Luma keeps is one sealed database and the one key that opens it. A backup is both of them in a single file,
sealed again under a passphrase only the owner knows. Without the passphrase the file reads as noise: it can sit on a
USB stick or in somebody's cloud folder and say nothing. Luma never sends it anywhere; it's written where they say.

What's in it: every memory, check-in, list, reminder, setting, how to be with them, their passcode's hash, and any
sign-in they sealed. What isn't: Luma's code and models (none of that is about anyone), the files they gave Luma, and
the browser's own profile. Those are named when a backup is made so nobody thinks they came along.

Restoring is for a Luma that has met nobody: a new lamp, or one after "Erase everything". It never writes over a home
that's there. Afterwards the store checks itself, and the answer comes back with what was restored.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"LUMA-BACKUP-1\n"
NOT_IN_IT = ("the files you gave Luma", "the browser inside Luma and where it's signed in", "Luma's own code and models")
WORK = {"n": 2 ** 15, "r": 8, "p": 1}      # scrypt: slow enough that guessing a passphrase costs real time


class Refused(ValueError):
    """Said to the owner as it is."""


def weak(passphrase):
    """Why this passphrase won't do, or None. Twelve characters, or four words: it guards everything they've told Luma."""
    said = str(passphrase or "").strip()
    if len(said) < 12 and len(said.split()) < 4:
        return "Use a longer passphrase: twelve characters or more, or four words. It's the only thing guarding this backup."
    if len(set(said.lower())) < 5:
        return "That passphrase is too easy to guess."
    return None


def _key(passphrase, salt, work=WORK):
    made = Scrypt(salt=salt, length=32, n=work["n"], r=work["r"], p=work["p"]).derive(str(passphrase).strip().encode())
    return base64.urlsafe_b64encode(made)


def _database(store):
    """One consistent copy of the database as bytes, taken while Luma goes on running."""
    with tempfile.TemporaryDirectory() as temp:
        copy = Path(temp) / "copy.db"
        with store.lock:
            store.db.commit()
            out = sqlite3.connect(str(copy))
            try:
                store.db.backup(out)
            finally:
                out.close()
        return copy.read_bytes()


def make(store, passphrase, to):
    """Write a backup to `to`. Returns what's in it and what isn't, for the line the owner reads."""
    why = weak(passphrase)
    if why:
        raise Refused(why)
    to = Path(to)
    if to.exists():
        raise Refused("There's already a file there. Pick a new name, so an older backup is never written over.")
    database, key = _database(store), Path(store.key_path).read_bytes()
    head = {"made": time.time(), "records": store.health()["records"], "database": len(database),
            "sha256": hashlib.sha256(database).hexdigest()}
    body = json.dumps(head).encode() + b"\n" + base64.b64encode(key) + b"\n" + database
    salt = os.urandom(16)
    sealed = Fernet(_key(passphrase, salt)).encrypt(body)
    to.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(to, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(MAGIC + base64.b64encode(salt) + b"\n" + sealed)
        f.flush()
        os.fsync(f.fileno())
    return {"file": str(to), "bytes": to.stat().st_size, "records": head["records"], "not_in_it": list(NOT_IN_IT)}


def _open(path, passphrase):
    raw = Path(path).read_bytes()
    if not raw.startswith(MAGIC):
        raise Refused("That file isn't a Luma backup.")
    salt, _, sealed = raw[len(MAGIC):].partition(b"\n")
    try:
        body = Fernet(_key(passphrase, base64.b64decode(salt))).decrypt(sealed)
    except (InvalidToken, ValueError):
        # a wrong passphrase and a file somebody changed look the same from here, and are answered the same
        raise Refused("That passphrase doesn't open this backup, or the file has been changed.") from None
    head, _, rest = body.partition(b"\n")
    key, _, database = rest.partition(b"\n")
    head = json.loads(head)
    if len(database) != head["database"] or hashlib.sha256(database).hexdigest() != head["sha256"]:
        raise Refused("That backup is damaged: what's inside doesn't match what it says it holds.")
    return head, base64.b64decode(key), database


def look(path, passphrase):
    """What a backup holds, without restoring anything: when it was made and how many records."""
    head, _, _ = _open(path, passphrase)
    return {"made": head["made"], "records": head["records"], "bytes": head["database"]}


def restore(path, passphrase, db_path, key_path):
    """Bring a backup into a Luma that has met nobody. Returns the store's own check afterwards.

    Never onto a home that's there: a store with anything in it, or a key, is refused. Erase everything first
    (luma.memory.reset) if this lamp is to become the backed-up one."""
    from luma.memory.store import Store
    db_path, key_path = Path(db_path), Path(key_path)
    if key_path.exists() or (db_path.exists() and db_path.stat().st_size):
        raise Refused("This Luma already has a home on it. Erase everything first, then restore.")
    head, key, database = _open(path, passphrase)
    db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    for target, data in ((key_path, key), (db_path, database)):
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    store = Store(db_path, key_path)
    try:
        health = store.health()
    finally:
        store.close()
    if not health["ok"] or health["records"] != head["records"]:
        raise Refused("The backup was written back, but the store's own check didn't pass: " + "; ".join(health["problems"] or ["the record count is different"]))
    return {"records": health["records"], "made": head["made"], "ok": True, "not_in_it": list(NOT_IN_IT)}
