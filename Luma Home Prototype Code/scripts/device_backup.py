#!/usr/bin/env python3
"""Save a coherent local state database, key and settings before a device update.

Run while Luma is stopped; backups contain private data and stay mode 0700/0600.
No backup is uploaded, and no secret is printed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys


def backup(root: Path, state: Path, destination: Path):
    if root.is_symlink() or state.is_symlink() or destination.is_symlink():
        raise ValueError("Use real directories rather than symlinks for private backups.")
    database, key = state / "state.db", state / "state.key"
    if database.exists() and not key.is_file():
        raise ValueError("State database exists without its matching key. Repair this before making a recovery backup.")
    if destination.exists():
        raise FileExistsError("Backup destination already exists; choose a new directory.")
    if any(path.is_symlink() for path in (database, key, root / ".env")):
        raise ValueError("Refusing symlinked state, key or environment files.")
    destination.mkdir(mode=0o700, parents=True)
    try:
        if database.exists():
            with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as source:
                with sqlite3.connect(destination / "state.db") as target:
                    source.backup(target)
                    if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("Database integrity check failed; original state remains unchanged.")
            (destination / "state.db").chmod(0o600)
        for source, name in ((key, "state.key"), (root / ".env", "environment.env")):
            if source.is_file():
                shutil.copyfile(source, destination / name)
                (destination / name).chmod(0o600)
        revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        manifest = {"created": datetime.now(timezone.utc).isoformat(), "source_revision": revision,
                    "database_included": database.exists(), "key_included": key.is_file(),
                    "note": "Private recovery material. Restore state.db together with state.key while Luma is stopped."}
        (destination / "backup.json").write_text(json.dumps(manifest, indent=2))
        (destination / "backup.json").chmod(0o600)
    except Exception:
        # Keep partial data private and visibly incomplete; never delete an original.
        (destination / "INCOMPLETE").touch(mode=0o600)
        raise
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    from dotenv import load_dotenv
    load_dotenv(root / ".env", override=False)
    state = Path(os.getenv("LUMA_STATE_DIR", "~/.luma/agent")).expanduser()
    result = backup(root, state, args.destination.expanduser())
    print(f"Private backup saved: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
