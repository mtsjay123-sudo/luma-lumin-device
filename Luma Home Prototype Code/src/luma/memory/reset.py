"""A factory reset: everything is forgotten for real (docs/PRESENCE_MASTER_PROMPT.md, section 9).

Everything Luma keeps is sealed with one key (and, for memories, a key each that this one unwraps). So the reset is
the key: it's overwritten and removed first, and from that moment a copy of the database somebody took earlier, or
the one still on the disk, can't be read by anyone. Then the database goes, with the sign-ins the browser inside
Luma held, their files, the pairings with their phone and computer, and what the command line remembered.

What stays: Luma's own code and the models it thinks and speaks with. None of that is about anyone.

It can't be undone, and nothing here asks "are you sure": whoever calls it has already asked.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

THEIRS = ("browser-profile", "files", "phone-tls", "link-tls", "cli.json")   # beside the store: their sign-ins, their files, their pairings


def _destroy(path: Path):
    """Overwrite a small file with noise, make sure that reached the disk, then remove it."""
    try:
        size = path.stat().st_size
        with open(path, "r+b") as f:
            f.write(os.urandom(max(size, 64)))
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass
    path.unlink(missing_ok=True)


def factory_reset(store):
    """Destroy the key, then remove everything of theirs. Returns what was removed, by name, for the one line that's
    shown afterwards. The store is closed and can't be used again; start a new one for a fresh Luma."""
    db, key = Path(store.db_path), Path(store.key_path)
    home = db.parent
    try:
        store.close()
    except Exception:
        pass
    gone = []
    _destroy(key)                       # first: from here on nothing kept can be read, whatever happens next
    gone.append("the key")
    for path in (db, Path(str(db) + "-wal"), Path(str(db) + "-shm"), Path(str(db) + "-journal")):
        if path.exists():
            path.unlink()
            gone.append(path.name)
    for name in THEIRS:
        path = home / name
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
            gone.append(name)
        elif path.exists() or path.is_symlink():
            path.unlink(missing_ok=True)
            gone.append(name)
    return gone
