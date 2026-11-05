#!/bin/bash
# Prints a Python 3.10 or newer that runs natively on this Mac's Apple Silicon (MLX needs one), or says how to get it.
for p in python3.13 python3.12 python3.11 python3.10 /opt/homebrew/bin/python3 python3; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import platform, sys; sys.exit(0 if sys.version_info >= (3, 10) and platform.machine() == "arm64" else 1)' 2>/dev/null; then
    command -v "$p"; exit 0
  fi
done
echo "This needs Python 3.10 or newer for Apple Silicon. Install it with: brew install python@3.12  (or from python.org), then run this again." >&2
exit 1
