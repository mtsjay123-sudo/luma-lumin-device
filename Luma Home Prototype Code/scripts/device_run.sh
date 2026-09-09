#!/usr/bin/env bash
set -euo pipefail
LUMA_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$LUMA_SOURCE"
if [ ! -x .venv/bin/python ]; then echo "Luma venv missing; run setup first." >&2; exit 1; fi
# Local model loaders never fetch assets here. Start remains muted for privacy.
export PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
exec .venv/bin/python -m luma.cli serve
