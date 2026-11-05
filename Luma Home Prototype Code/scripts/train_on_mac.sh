#!/bin/bash
# Train Luma's own brain on this Mac, check it against the stock brain, and install it where Settings finds it.
# Apple Silicon (M1 or newer) with 16 GB of memory or more; a big Mac does it fastest. It sets up its own Python
# (in out/mac-brain/venv), so nothing else on the Mac changes.
#
#   bash scripts/train_on_mac.sh                 # every conversation, twice through, then the check
#   bash scripts/train_on_mac.sh --epochs 3      # more passes (the check still decides)
#   bash scripts/train_on_mac.sh --no-install    # train and check only
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != arm64 ]; then
  echo "This needs an Apple Silicon Mac. Anywhere else, use the cloud run: GitHub > Actions > Train Luma's brain."; exit 1
fi
OUT="${OUT:-out/mac-brain}"
PY="$(bash scripts/_mac_python.sh)"
mkdir -p "$OUT"
[ -x "$OUT/venv/bin/python" ] || "$PY" -m venv "$OUT/venv"
"$OUT/venv/bin/python" -m pip install -q --upgrade pip
"$OUT/venv/bin/python" -m pip install -q "mlx-lm>=0.26" "transformers>=4.51,<6" "huggingface_hub>=0.24" safetensors sentencepiece protobuf numpy gguf torch
"$OUT/venv/bin/python" scripts/train_on_mac.py --out "$OUT" "$@"
