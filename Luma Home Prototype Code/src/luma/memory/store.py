"""Local encrypted records. IDs/timestamps/types remain visible SQLite metadata.

This is application payload encryption, not SQLCipher/full-database encryption.
The owner-only key file must be backed up with the DB. FileVault is still advised.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from cryptography.fernet import Fernet


def reject_payment_secrets(value):
    """Do not persist raw card/CVC/password material, even inside a memory."""
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k).lower() in {"card_number", "pan", "cvc", "cvv", "password", "pin"}:
                raise ValueError("Store provider tokens only; card numbers, CVCs and passwords are not accepted.")
            reject_payment_secrets(v)
    elif isinstance(value, list):
        for v in value: reject_payment_secrets(v)
    elif isinstance(value, str):
        if re.search(r"\b(?:cvv|cvc|card number|password)\b\s*(?:is|:|=)\s*\S+", value, re.I):
            raise ValueError("Do not save payment credentials or passwords in LUMA memory.")
        # Broadly reject plausible PANs (including formatted numbers), not phone numbers.
        if re.search(r"(?<![A-Za-z0-9+])(?:\d[ -]?){12,18}\d(?![A-Za-z0-9])", value):
            raise ValueError("Long payment-like numbers are not accepted. Use merchant-saved payment details.")


class Store:
    def __init__(self, db_path: Path, key_path: Path):
        self.db_path, self.key_path = Path(db_path), Path(key_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.db_path.parent, 0o700)
        if self.db_path.is_symlink() or self.key_path.is_symlink():
            raise ValueError("LUMA state files must not be symbolic links.")
        if not self.key_path.exists():
            if self.db_path.exists() and self.db_path.stat().st_size:
                raise RuntimeError("State key is missing. Restore the original key; a new key cannot decrypt existing memory.")
            try:
                fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as f: f.write(Fernet.generate_key())
            except FileExistsError:
                pass
        os.chmod(self.key_path, 0o600)
        self.cipher = Fernet(self.key_path.read_bytes().strip())
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(self.db_path), timeout=10, check_same_thread=False)
        self.db.execute("PRAGMA secure_delete=ON")
        self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT PRIMARY KEY, created REAL, updated REAL, payload BLOB)")
        self.db.execute("CREATE INDEX IF NOT EXISTS records_kind ON records(kind)")
        self.db.commit()
        os.chmod(self.db_path, 0o600)

    def _decode(self, row):
        return json.loads(self.cipher.decrypt(row[0]).decode()) if row else None

    def get(self, kind, id):
        with self.lock:
            return self._decode(self.db.execute("SELECT payload FROM records WHERE kind=? AND id=?", (kind, id)).fetchone())

    def put(self, kind, value, id=None):
        reject_payment_secrets(value)
        id = id or uuid.uuid4().hex[:12]
        now = time.time()
        value = {**value, "id": id}
        blob = self.cipher.encrypt(json.dumps(value, ensure_ascii=False).encode())
        with self.lock, self.db:
            self.db.execute("INSERT INTO records VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated=excluded.updated", (kind, id, now, now, blob))
        return value

    def all(self, kind, limit=100):
        with self.lock:
            rows = self.db.execute("SELECT payload FROM records WHERE kind=? ORDER BY created DESC LIMIT ?", (kind, limit)).fetchall()
            return [self._decode(r) for r in rows]

    def delete(self, kind, id):
        with self.lock, self.db:
            return self.db.execute("DELETE FROM records WHERE kind=? AND id=?", (kind, id)).rowcount > 0

    def transition(self, id, expected, state, **extra):
        """Atomic cross-process action claim; only one caller may execute a draft."""
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                current = self._decode(self.db.execute("SELECT payload FROM records WHERE kind='action' AND id=?", (id,)).fetchone())
                if not current or current["state"] not in expected:
                    raise ValueError("Action already handled, missing, or not in an executable state.")
                current.update(state=state, **extra)
                reject_payment_secrets(current)
                blob = self.cipher.encrypt(json.dumps(current).encode())
                self.db.execute("UPDATE records SET payload=?, updated=? WHERE id=?", (blob, time.time(), id))
                self.db.commit()
                return current
            except BaseException:
                self.db.rollback()
                raise

    def setting(self, key, default=None):
        row = self.get("setting", "setting:" + key)
        return row["value"] if row else default

    def set_setting(self, key, value):
        return self.put("setting", {"value": value}, "setting:" + key)

    def recall(self, query, limit=5):
        # Deterministic lexical retrieval. No claim of embeddings/semantic search.
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        memories = self.all("memory", 1000)
        ranked = sorted(memories, key=lambda r: len(terms & set(re.findall(r"[a-z0-9]+", r["text"].lower()))), reverse=True)
        return [r for r in ranked if terms & set(re.findall(r"[a-z0-9]+", r["text"].lower()))][:limit]

    def erase(self):
        with self.lock, self.db:
            self.db.execute("DELETE FROM records")
        with self.lock: self.db.execute("VACUUM")

    def close(self):
        with self.lock: self.db.close()
