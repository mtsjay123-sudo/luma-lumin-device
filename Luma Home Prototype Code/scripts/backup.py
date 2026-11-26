#!/usr/bin/env python3
"""Back up a home, look inside a backup, or bring one back (luma.memory.backup; docs/STORAGE.md).

  python scripts/backup.py make out/luma-2026-11-26.backup      # asks for a passphrase twice
  python scripts/backup.py look out/luma-2026-11-26.backup
  python scripts/backup.py restore out/luma-2026-11-26.backup   # only onto a Luma that has met nobody

The passphrase is asked for at the keyboard and is never written anywhere. (For a script: LUMA_BACKUP_PASSPHRASE.)
The home it works on is the one Luma uses here (LUMA_STATE_DIR, as always).
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def passphrase(twice=False):
    given = os.environ.get("LUMA_BACKUP_PASSPHRASE")
    if given:
        return given
    first = getpass.getpass("Passphrase: ")
    if twice and getpass.getpass("Once more: ") != first:
        raise SystemExit("Those two weren't the same. Nothing was written.")
    return first


def main():
    from luma.config import STATE_DB_PATH as DB_PATH, STATE_KEY_PATH as KEY_PATH
    from luma.memory import backup
    from luma.memory.store import Store
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("what", choices=("make", "look", "restore"))
    parser.add_argument("file")
    args = parser.parse_args()
    try:
        if args.what == "make":
            store = Store(DB_PATH, KEY_PATH)
            try:
                out = backup.make(store, passphrase(twice=True), args.file)
            finally:
                store.close()
            print(f"Backed up {out['records']} records to {out['file']} ({out['bytes']:,} bytes).")
            print("Not in it: " + "; ".join(out["not_in_it"]) + ".")
            print("Keep the passphrase somewhere safe. Without it this file can't be opened by anyone, Luma included.")
        elif args.what == "look":
            out = backup.look(args.file, passphrase())
            print(f"Made {datetime.fromtimestamp(out['made']).strftime('%B %-d, %Y at %-I:%M %p')}: {out['records']} records, {out['bytes']:,} bytes.")
        else:
            out = backup.restore(args.file, passphrase(), DB_PATH, KEY_PATH)
            print(f"Restored {out['records']} records. The store's own check passed.")
            print("Not brought back (they were never in the backup): " + "; ".join(out["not_in_it"]) + ".")
    except backup.Refused as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
