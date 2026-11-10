"""Local encrypted records. IDs/timestamps/types remain visible SQLite metadata.

This is application payload encryption, not SQLCipher/full-database encryption.
The owner-only key file must be backed up with the DB. FileVault is still advised.

What Luma remembers (a memory, what it means, the day's summary, the life file) is sealed one record at a time: each has
its own key, and that key is kept wrapped by the owner's key. Forgetting a memory deletes its key, so any other copy of
the sealed record (an archive, a synced device) can never be opened again. Records sealed the older way, with the owner's
key directly, still open.

Finding a memory doesn't read them all: the index (luma.memory.index) is built once and kept in step with every write.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

OWN_KEY = {"memory", "vector", "episode", "life"}   # each record of these kinds is sealed with a key of its own
BUILT_FROM_MEMORIES = ("episode", "life")           # forgotten with any memory they were built from ("from": [ids])
SEALED = b"L2"
HOT = 4000                                           # memories kept opened, the ones read most recently


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


def mask_long_numbers(value):
    """For things Luma keeps from the outside world (receipts, feed cards): long digit runs
    such as tracking or order numbers become [number] so nothing card-like is ever stored."""
    if isinstance(value, dict):
        return {k: mask_long_numbers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [mask_long_numbers(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"(?<![A-Za-z0-9+])(?:\d[ -]?){12,18}\d(?![A-Za-z0-9])", "[number]", value)
    return value


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
        owner_key = self.key_path.read_bytes().strip()
        self.cipher = Fernet(owner_key)
        self._wrap = AESGCM(HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"luma record keys v1").derive(base64.urlsafe_b64decode(owner_key)))
        self.lock = threading.RLock()
        self._all = None        # every memory, opened: only for callers that ask for them all (memories())
        self._hot = {}          # id -> memory, the ones read lately
        self._index = None      # luma.memory.index.LifeIndex, built on first use
        self._meanings = False  # whether the index has the meanings loaded
        self._changes = None    # how many times memories were written (by any process), as last seen here
        self._version = None    # sqlite's data_version: moves when another process commits
        self._built = None      # memory id -> what was written from it (episodes, the life file), read once
        self._built_seen = None
        self.db = sqlite3.connect(str(self.db_path), timeout=10, check_same_thread=False)
        self.db.execute("PRAGMA secure_delete=ON")
        self.db.execute("PRAGMA journal_mode=DELETE")
        if not self.db.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone():
            # A new database: room that deleting frees can go back to the device a page at a time (compact()), without
            # rewriting the whole file. One made before this is switched over the first time it's compacted.
            self.db.execute("PRAGMA auto_vacuum=INCREMENTAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT PRIMARY KEY, created REAL, updated REAL, payload BLOB)")
        self.db.execute("CREATE INDEX IF NOT EXISTS records_kind ON records(kind)")
        self.db.execute("CREATE TABLE IF NOT EXISTS keys (id TEXT PRIMARY KEY, wrapped BLOB)")
        self.db.execute("CREATE TABLE IF NOT EXISTS changes (what TEXT PRIMARY KEY, n INTEGER)")
        self.db.commit()
        os.chmod(self.db_path, 0o600)

    # -- sealing ------------------------------------------------------------------------------------------------------
    def _unwrap(self, wrapped, id):
        return self._wrap.decrypt(bytes(wrapped[:12]), bytes(wrapped[12:]), id.encode())

    def _seal(self, kind, id, value):
        """(the sealed record, its newly wrapped key or None). A record that already has a key keeps it."""
        plain = json.dumps(value, ensure_ascii=False).encode()
        ident = id.encode()
        if kind not in OWN_KEY or len(ident) > 255:
            return self.cipher.encrypt(plain), None
        row = self.db.execute("SELECT wrapped FROM keys WHERE id=?", (id,)).fetchone()
        key, wrapped = (self._unwrap(row[0], id), None) if row else (os.urandom(32), None)
        if not row:
            nonce = os.urandom(12)
            wrapped = nonce + self._wrap.encrypt(nonce, key, ident)
        nonce = os.urandom(12)
        return SEALED + bytes([len(ident)]) + ident + nonce + ChaCha20Poly1305(key).encrypt(nonce, plain, ident), wrapped

    def _decode(self, row):
        """Open one record: (payload,) or (payload, its wrapped key). None when it's gone, or its key is (forgotten)."""
        if not row or row[0] is None:
            return None
        blob = row[0] if isinstance(row[0], bytes) else bytes(row[0], "utf-8") if isinstance(row[0], str) else bytes(row[0])
        if blob[:2] != SEALED:
            return json.loads(self.cipher.decrypt(blob).decode())
        size = blob[2]
        ident, nonce, sealed = blob[3:3 + size], blob[3 + size:15 + size], blob[15 + size:]
        wrapped = row[1] if len(row) > 1 else None
        if wrapped is None:
            found = self.db.execute("SELECT wrapped FROM keys WHERE id=?", (ident.decode(),)).fetchone()
            wrapped = found[0] if found else None
        if wrapped is None:
            return None
        return json.loads(ChaCha20Poly1305(self._unwrap(wrapped, ident.decode())).decrypt(nonce, sealed, ident))

    def _changed(self):
        """Inside a write to what Luma remembers: count it, so other processes know to look again."""
        self.db.execute("INSERT INTO changes VALUES('memory', 1) ON CONFLICT(what) DO UPDATE SET n = n + 1")
        self._changes = self.db.execute("SELECT n FROM changes WHERE what='memory'").fetchone()[0]

    def _look(self):
        """Another process wrote a memory: what's kept in RAM here is out of date."""
        version = self.db.execute("PRAGMA data_version").fetchone()[0]
        if version == self._version:
            return
        self._version = version
        row = self.db.execute("SELECT n FROM changes WHERE what='memory'").fetchone()
        if (row[0] if row else None) != self._changes:
            self._changes = row[0] if row else None
            self._all, self._index, self._meanings = None, None, False
            self._hot.clear()

    # -- records ------------------------------------------------------------------------------------------------------
    def get(self, kind, id):
        with self.lock:
            return self._decode(self.db.execute("SELECT payload FROM records WHERE kind=? AND id=?", (kind, id)).fetchone())

    def put(self, kind, value, id=None):
        reject_payment_secrets(value)
        id = id or uuid.uuid4().hex[:12]
        now = time.time()
        value = {**value, "id": id}
        with self.lock:
            was = self._was(id) if kind == "memory" and (self._index is not None or self._all is not None) else None
            with self.db:
                blob, wrapped = self._seal(kind, id, value)
                if wrapped is not None:
                    self.db.execute("INSERT OR REPLACE INTO keys VALUES(?,?)", (id, wrapped))
                self.db.execute("INSERT INTO records VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated=excluded.updated", (kind, id, now, now, blob))
                if kind in ("memory", "vector"):
                    self._changed()
            if kind in BUILT_FROM_MEMORIES:
                self._built = None
            self._wrote(kind, value, was)
        return value

    def put_many(self, kind, values):
        """Many records in one go (a sync, an import): sealed like put(), one transaction. A record's own "created" is kept
        as when it happened."""
        now = time.time()
        rows, keys, kept = [], [], []
        with self.lock:
            with self.db:
                for value in values:
                    reject_payment_secrets(value)
                    id = str(value.get("id") or uuid.uuid4().hex[:12])
                    value = {**value, "id": id}
                    blob, wrapped = self._seal(kind, id, value)
                    if wrapped is not None:
                        keys.append((id, wrapped))
                    when = value.get("created") if isinstance(value.get("created"), (int, float)) else now
                    rows.append((kind, id, when, now, blob))
                    kept.append(value)
                self.db.executemany("INSERT OR REPLACE INTO keys VALUES(?,?)", keys)
                self.db.executemany("INSERT INTO records VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated=excluded.updated", rows)
                if kind in ("memory", "vector"):
                    self._changed()
            if kind in ("memory", "vector"):  # too many to patch one by one: read again when next asked
                self._all, self._index, self._meanings = None, None, False
                self._hot.clear()
        return kept

    def all(self, kind, limit=100):
        with self.lock:
            rows = self.db.execute("SELECT r.payload, k.wrapped FROM records r LEFT JOIN keys k ON k.id = r.id WHERE r.kind=? ORDER BY r.created DESC LIMIT ?", (kind, limit)).fetchall()
            return [value for value in (self._decode(r) for r in rows) if value is not None]

    def count(self, kind):
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM records WHERE kind=?", (kind,)).fetchone()[0]

    def delete(self, kind, id):
        with self.lock:
            was = self._was(id) if kind == "memory" else None
            with self.db:
                gone = self.db.execute("DELETE FROM records WHERE kind=? AND id=?", (kind, id)).rowcount > 0
                if gone:
                    self.db.execute("DELETE FROM keys WHERE id=?", (id,))  # its key goes too: no copy of it opens again
                if gone and kind in ("memory", "vector"):
                    self._changed()
            if kind == "vector" and self._index is not None:
                self._index.drop_meaning(id[7:] if id.startswith("vector:") else id)
            if kind != "memory":
                return gone
            self._hot.pop(id, None)
            if self._all is not None:
                self._all = [m for m in self._all if m.get("id") != id]
            if self._index is not None:
                self._index.remove(id, (was or {}).get("text"))
        from luma.memory import meaning
        meaning.forget(self, id)                # forgetting a memory forgets what it meant too
        if gone:
            self._forget_built_from(id)         # and anything written from it
        return gone

    def _forget_built_from(self, id):
        """What was written from this memory (the day's story, the life file) goes with it. A story that's taken is
        written again, from what's left of that day, the next night (luma.memory.life)."""
        with self.lock:
            version = self.db.execute("PRAGMA data_version").fetchone()[0]
            if self._built is None or self._built_seen != version:  # read once; again only if another process wrote
                built = {}
                for kind in BUILT_FROM_MEMORIES:
                    for record in self.all(kind, 1000000):
                        for source in record.get("from") or ():
                            built.setdefault(source, set()).add((kind, record["id"]))
                self._built, self._built_seen = built, version
            taken = sorted(self._built.pop(id, ()))
            stories = [rid[8:] for kind, rid in taken if kind == "episode" and rid.startswith("episode:") and self.delete(kind, rid)]
            for kind, rid in taken:
                if kind != "episode":
                    self.delete(kind, rid)
            if stories:
                redo = [d for d in (self.setting("stories_to_redo", []) or []) if d not in stories] + stories
                self.set_setting("stories_to_redo", redo[-2000:])

    def _was(self, id):
        return self._hot.get(id) or self._decode(self.db.execute("SELECT payload FROM records WHERE kind='memory' AND id=?", (id,)).fetchone())

    def _wrote(self, kind, value, was):
        """Keep what's in RAM in step with one write."""
        if kind == "memory":
            self._hot[value["id"]] = value
            if self._all is not None:
                if was is None:
                    self._all.insert(0, value)
                else:
                    self._all = [value if m.get("id") == value["id"] else m for m in self._all]
            if self._index is not None:
                if was is not None:
                    self._index.remove(value["id"], was.get("text"))
                self._index.add(value)
        elif kind == "vector" and self._index is not None and self._meanings:
            self._index_meaning(value)

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

    # -- what Luma remembers ------------------------------------------------------------------------------------------
    def memories(self):
        """Every memory, newest first, opened once and kept in step after that. Finding one doesn't need this (see
        recall and search): it's for the few places that go through them all."""
        with self.lock:
            self._look()
            if self._all is None:
                rows = self.db.execute("SELECT r.payload, k.wrapped FROM records r LEFT JOIN keys k ON k.id = r.id WHERE r.kind='memory' ORDER BY r.created DESC").fetchall()
                self._all = [m for m in (self._decode(r) for r in rows) if m is not None]
            return list(self._all)

    def index(self):
        """What's needed to find a memory, in RAM: built by reading each memory once, then kept in step with every write.
        The reading is done a few thousand memories at a time, so nothing else waits on it for long."""
        with self.lock:
            self._look()
            if self._index is not None:
                return self._index
        from luma.memory import meaning
        from luma.memory.index import LifeIndex
        for attempt in range(4):
            last = attempt == 3
            if last:
                self.lock.acquire()  # written to three times while reading: this time, hold everything still
            try:
                with self.lock:
                    seen = self._count_changes()
                index, after = LifeIndex(meaning.DIMS), -1
                while True:
                    with self.lock:  # in the order they were written (the table's own order), so each read picks up where the last ended
                        rows = self.db.execute("SELECT r.payload, k.wrapped, r.rowid FROM records r LEFT JOIN keys k ON k.id = r.id "
                                               "WHERE r.kind='memory' AND r.rowid > ? ORDER BY r.rowid ASC LIMIT 4000", (after,)).fetchall()
                    if not rows:
                        break
                    for row in rows:
                        memory = self._decode(row[:2])
                        if memory is not None:
                            index.add(memory)
                    after = rows[-1][2]
                with self.lock:
                    if self._index is not None:
                        return self._index
                    if self._count_changes() == seen:
                        self._index, self._meanings, self._changes = index, False, seen
                        return index
            finally:
                if last:
                    self.lock.release()
        raise RuntimeError("Couldn't read the memories: they kept changing.")

    def _count_changes(self):
        row = self.db.execute("SELECT n FROM changes WHERE what='memory'").fetchone()
        return row[0] if row else None

    def _read(self, ids):
        """These memories, opened, in this order."""
        with self.lock:
            need = [i for i in ids if i not in self._hot]
            if len(self._hot) + len(need) > HOT:
                self._hot.clear()
                need = list(ids)
            for start in range(0, len(need), 400):
                part = need[start:start + 400]
                marks = ",".join("?" * len(part))
                for row in self.db.execute(f"SELECT r.payload, k.wrapped FROM records r LEFT JOIN keys k ON k.id = r.id WHERE r.kind='memory' AND r.id IN ({marks})", part):
                    memory = self._decode(row)
                    if memory is not None:
                        self._hot[memory["id"]] = memory
            return [self._hot[i] for i in ids if i in self._hot]

    def kept(self, limit=100000):
        """The facts Luma keeps (not the lines of talk around them), newest first."""
        with self.lock:
            return self._read(self.index().fact_ids(limit))

    def kept_counts(self):
        """(facts kept, lines of talk kept)."""
        with self.lock:
            return self.index().counts()

    def same_as(self, text, lines=False):
        """Memories every word of which is in this sentence, or the other way round: the few worth reading to see whether
        it's already kept."""
        with self.lock:
            index = self.index()
            found = self._read([index.ids[row] for row in index.twins(text, lines=lines) if index.ids[row] is not None])
            return [{**m, "ended": True} if index.is_ended(m["id"]) else m for m in found]

    def repeats(self):
        """[(the one to keep, the one that only repeats it)], both opened: the same sentence kept twice."""
        with self.lock:
            pairs = self.index().repeats()
            opened = {m["id"]: m for m in self._read([i for pair in pairs for i in pair])}
            return [(opened[keep], opened[drop]) for keep, drop in pairs if keep in opened and drop in opened]

    def mentioning(self, keys):
        """Memories that may mention every one of these words (a few too many, never too few), or None when only reading
        them all can tell."""
        with self.lock:
            index = self.index()
            rows = index.mentioning(keys)
            return None if rows is None else self._read([index.ids[row] for row in rows if index.ids[row] is not None])

    def said_between(self, start, end):
        """Everything kept from a span of time, oldest first."""
        with self.lock:
            return self._read(self.index().ids_between(start, end))

    def whats_true(self, limit=2000):
        """What's true now, as a friend would tell it: about them, then their people, then the rest."""
        with self.lock:
            return self._read(self.index().whats_true(limit))

    def changes(self):
        """A number that moves whenever anything Luma remembers is written, by any process."""
        with self.lock:
            return self._count_changes()

    def reseal(self, limit=2000):
        """Memories sealed the older way get a key of their own (so forgetting one can delete its key). Returns how many."""
        done = 0
        with self.lock:
            rows = self.db.execute("SELECT r.id, r.payload FROM records r LEFT JOIN keys k ON k.id = r.id WHERE r.kind='memory' AND k.id IS NULL LIMIT ?", (limit,)).fetchall()
            with self.db:
                for id, payload in rows:
                    value = self._decode((payload,))
                    if value is None:
                        continue
                    blob, wrapped = self._seal("memory", id, value)
                    if wrapped is not None:
                        self.db.execute("INSERT OR REPLACE INTO keys VALUES(?,?)", (id, wrapped))
                        self.db.execute("UPDATE records SET payload=? WHERE id=?", (blob, id))
                        done += 1
        return done

    def said_before(self, cutoff):
        """Ids of everything kept from before a moment."""
        with self.lock:
            return self.index().ids_before(cutoff)

    def _index_meaning(self, record):
        from luma.memory import meaning
        vector = meaning.unpack(record)
        if vector is None or record.get("model") != meaning.FILE:
            return
        try:
            mark = bytes.fromhex(str(record.get("for") or ""))
        except ValueError:
            return
        self._index.set_meaning(str(record.get("id", ""))[7:], vector, mark)

    def _near(self, index, query, limit):
        """[(how close, row)] by meaning, checked against the real numbers; [] when this computer can't."""
        from luma.memory import meaning
        if not str(query or "").strip() or not meaning.available(self):
            return []
        if not self._meanings:  # the meanings worked out so far, read once
            for row in self.db.execute("SELECT r.payload, k.wrapped FROM records r LEFT JOIN keys k ON k.id = r.id WHERE r.kind='vector'"):
                record = self._decode(row)
                if record is not None:
                    self._index_meaning(record)
            self._meanings = True
        lacking = index.lacking_meaning()
        if lacking:
            meaning.catch_up(self, self._read(lacking))
        q = meaning._embed(meaning.QUERY + str(query))
        if q is None:
            return []
        import numpy as np
        exact = []
        for _, row in index.meanings.near(q, np.frombuffer(index.alive, dtype=np.uint8), max(16, limit * 3)):
            record = self.get("vector", "vector:" + str(index.ids[row]))
            v = meaning._unit(meaning.unpack(record)) if record else None
            if v is not None:
                exact.append((float(np.dot(q[:len(v)], v[:len(q)])), row))
        exact.sort(key=lambda s: -s[0])
        return [(score, row) for score, row in exact if score >= meaning.CLOSE][:limit]

    def recall(self, query, limit=5):
        """The memories that answer this best: by the words that matter, never just the newest (luma.memory.segments), then
        what words missed but means the same thing, when this computer has the meaning model (luma.memory.meaning)."""
        from luma.memory import meaning
        with self.lock:
            index = self.index()
            rows = [row for _, row in index.words(query, limit)]
            try:
                close = [row for _, row in self._near(index, query, limit) if row not in rows]
                rows += close[:max(meaning.EXTRA, limit - len(rows))]
            except Exception:
                pass
            return self._read([index.ids[row] for row in rows if index.ids[row] is not None])

    def search(self, query, limit=5, now=None, zone=None):
        """What answers this question, knowing who's who, what's still true and when things were said.

        {"memories": best first ([] when Luma was never told), "known": False when it was never told, "why": in plain words,
        "related": what it does have that's close, "window": (start, end) when the question is about a time,
        "unseen": words of the question no memory has (it may know the person and not the thing asked)}.
        A fact that a newer one replaced comes back with "ended": True; one that states the very thing asked ("where do I
        live" and "You moved to Denver") with "answers": True."""
        with self.lock:
            index = self.index()
            near = None
            try:
                from luma.memory import meaning
                if meaning.available(self):
                    near = lambda q: self._near(index, q, limit)  # noqa: E731
            except Exception:
                near = None
            found = index.search(query, limit, now=now, zone=zone, near=near)
            ids = [index.ids[row] for row in found["rows"]]
            ended = {index.ids[row] for row in found["ended"]}
            answers = {index.ids[row] for row in found["facts"]}
            memories = [{**m, **({"ended": True} if m["id"] in ended else {}), **({"answers": True} if m["id"] in answers else {})}
                        if m["id"] in ended or m["id"] in answers else m for m in self._read([i for i in ids if i is not None])]
        return {"memories": memories if found["known"] else [], "related": [] if found["known"] else memories, "known": found["known"],
                "why": found["why"], "window": found["window"], "unseen": found["unseen"]}

    def erase(self):
        with self.lock, self.db:
            self.db.execute("DELETE FROM records")
            self.db.execute("DELETE FROM keys")
            self._changed()
        with self.lock:
            self.db.execute("VACUUM")
            self._all, self._index, self._meanings = None, None, False
            self._hot.clear()
        from luma.memory import meaning
        meaning._cache.clear()

    # -- room, and the database looking after itself ------------------------------------------------------------------
    def sizes(self):
        """How much each kind of thing takes, as it sits sealed on the device: {kind: {"count": n, "bytes": b}}."""
        with self.lock:
            rows = self.db.execute("SELECT kind, COUNT(*), COALESCE(SUM(LENGTH(payload)), 0) FROM records GROUP BY kind").fetchall()
            keys = self.db.execute("SELECT COUNT(*), COALESCE(SUM(LENGTH(wrapped) + LENGTH(id)), 0) FROM keys").fetchone()
        out = {kind: {"count": count, "bytes": size} for kind, count, size in rows}
        if keys[0] and "memory" in out:
            out["memory"]["bytes"] += keys[1]  # each memory's own key is part of what it costs
        return out

    def size_of(self, kind, id):
        """One record's sealed size in bytes, 0 when it isn't there."""
        with self.lock:
            row = self.db.execute("SELECT LENGTH(payload) FROM records WHERE kind=? AND id=?", (kind, id)).fetchone()
        return int(row[0]) if row and row[0] else 0

    def file_bytes(self):
        """What the database takes on the device, with its journal while one is open."""
        total = 0
        for path in (self.db_path, Path(str(self.db_path) + "-journal"), Path(str(self.db_path) + "-wal")):
            try:
                total += path.stat().st_size
            except OSError:
                pass
        return total

    def spare_bytes(self):
        """Room inside the file that deleting left behind and nothing is using."""
        with self.lock:
            return self.db.execute("PRAGMA freelist_count").fetchone()[0] * self.db.execute("PRAGMA page_size").fetchone()[0]

    def compact(self, least=16 * 1024):
        """Give the room that deleting left behind back to the device. Returns the bytes that came back (0 when there
        was too little to bother, or the device had no room to do it: it's tried again after the next delete). It's
        cheap: only the freed pages are touched. A database from before this is rewritten once, to switch it over."""
        with self.lock:
            if self.spare_bytes() < least:
                return 0
            before = self.file_bytes()
            try:
                self.db.commit()
                if self.db.execute("PRAGMA auto_vacuum").fetchone()[0] == 2:
                    self.db.executescript("PRAGMA incremental_vacuum;")  # as a script: execute() would free one page and stop
                else:
                    self.db.execute("PRAGMA auto_vacuum=INCREMENTAL")
                    self.db.execute("VACUUM")
            except sqlite3.Error:
                return 0
            return max(0, before - self.file_bytes())

    def health(self):
        """The database checking itself: whether the file reads back whole, and whether anything was left behind (a key
        with no record to open, a meaning with no memory). Nothing is changed."""
        problems = []
        with self.lock:
            try:
                check = [row[0] for row in self.db.execute("PRAGMA quick_check(20)").fetchall()]
            except sqlite3.Error as error:
                check = [str(error)]
            if check != ["ok"]:
                problems.append("The database file didn't read back whole: " + "; ".join(str(c)[:120] for c in check[:3]))
            try:
                records = self.db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
                keys = self.db.execute("SELECT COUNT(*) FROM keys k WHERE NOT EXISTS (SELECT 1 FROM records r WHERE r.id = k.id)").fetchone()[0]
                meanings = self.db.execute("SELECT COUNT(*) FROM records v WHERE v.kind='vector' AND NOT EXISTS "
                                           "(SELECT 1 FROM records m WHERE m.kind='memory' AND m.id = substr(v.id, 8))").fetchone()[0]
            except sqlite3.Error as error:
                records, keys, meanings = 0, 0, 0
                problems.append("The database couldn't be read: " + str(error)[:120])
            if keys:
                problems.append(f"{keys} key{'s' if keys != 1 else ''} left behind with nothing to open.")
            if meanings:
                problems.append(f"{meanings} meaning{'s' if meanings != 1 else ''} left behind for memories that are gone.")
        return {"ok": not problems, "problems": problems, "records": records, "bytes": self.file_bytes(), "spare": self.spare_bytes(),
                "left_behind": {"keys": keys, "meanings": meanings}}

    def repair(self):
        """Clear what was left behind, rebuild the indexes, and give the spare room back. Never touches a record that
        still has its memory."""
        with self.lock:
            with self.db:
                keys = self.db.execute("DELETE FROM keys WHERE NOT EXISTS (SELECT 1 FROM records r WHERE r.id = keys.id)").rowcount
                meanings = self.db.execute("DELETE FROM records WHERE kind='vector' AND NOT EXISTS "
                                           "(SELECT 1 FROM records m WHERE m.kind='memory' AND m.id = substr(records.id, 8))").rowcount
                if meanings:
                    self._changed()
            try:
                self.db.execute("REINDEX")
                self.db.commit()
            except sqlite3.Error:
                pass
            if meanings:
                self._all, self._index, self._meanings = None, None, False
            freed = self.compact(least=1)
        return {"removed": keys + meanings, "freed": freed, **self.health()}

    def close(self):
        with self.lock: self.db.close()
