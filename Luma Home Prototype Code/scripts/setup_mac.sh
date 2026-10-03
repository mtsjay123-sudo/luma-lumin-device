#!/usr/bin/env bash
set -euo pipefail
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -e ".[agent,dev]"
# Luma's own browser (Instagram, store pages). Downloads a private Chromium once.
python -m playwright install chromium
