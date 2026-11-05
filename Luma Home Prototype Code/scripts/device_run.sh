#!/usr/bin/env bash
set -euo pipefail
LUMA_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$LUMA_SOURCE"
if [ ! -x .venv/bin/python ]; then echo "Luma venv missing; run setup first." >&2; exit 1; fi
# Local model loaders never fetch assets here. Start remains muted for privacy.
export PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
# The device is the home's Luma: paired computers come in over Luma Link (a 6-digit code it says out loud, its own
# certificate pinned), lend it their brain and their hands. Set LUMA_LINK_HOST=0 to keep it to itself.
export LUMA_LINK_HOST="${LUMA_LINK_HOST:-1}"
# A small board (12 GB of memory or less, the $250-$400 Luma) runs the budget profile: the brain on the four big cores, one
# trip through it per everyday turn, and thinking out loud while it works. Set LUMA_DEVICE_TIER or LUMA_THREADS to override.
mem_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
if [ -z "${LUMA_DEVICE_TIER:-}" ] && [ "${mem_kb:-0}" -gt 0 ] && [ "$mem_kb" -le $((12 * 1024 * 1024)) ]; then
  export LUMA_DEVICE_TIER=budget
  cores="$(nproc 2>/dev/null || echo 4)"
  export LUMA_THREADS="${LUMA_THREADS:-$(( cores < 4 ? cores : 4 ))}"
  # The device's own brain, Qwen3 1.7B (scripts/download_models.sh fetches it on a board this size), unless one is chosen.
  # While a paired computer is on, Luma thinks with that computer's brain instead (Settings: Think on my computer).
  if [ -z "${LUMA_MODEL_PATH:-}" ]; then
    for quant in Q4_K_M Q4_0; do
      if [ -f "models/qwen3-1.7b/Qwen_Qwen3-1.7B-$quant.gguf" ]; then
        export LUMA_MODEL_PATH="$LUMA_SOURCE/models/qwen3-1.7b/Qwen_Qwen3-1.7B-$quant.gguf"
        break
      fi
    done
  fi
fi
exec .venv/bin/python -m luma.cli serve
