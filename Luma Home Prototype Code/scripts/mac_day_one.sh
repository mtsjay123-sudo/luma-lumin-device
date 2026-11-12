#!/bin/bash
# Day one on a new Mac. What this Mac can run, Luma's best voice picked on this Mac, and Luma's own brain trained here.
#
#   bash scripts/mac_day_one.sh            # all of it (an hour or two on a big Mac; it says what it's doing)
#   bash scripts/mac_day_one.sh --check    # just what this Mac can run
#   bash scripts/mac_day_one.sh --voice    # just the voice contest
#   bash scripts/mac_day_one.sh --brain    # just the training
#   bash scripts/mac_day_one.sh --test     # the human test and the safety net on the biggest brain this Mac has
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != arm64 ]; then echo "This is for an Apple Silicon Mac."; exit 1; fi
what="${1:-all}"

chip="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Apple Silicon")"
gb=$(( $(sysctl -n hw.memsize) / 1073741824 ))
free_gb=$(df -g . | awk 'NR==2 {print $4}')
echo "This Mac: $chip, $gb GB of memory, $free_gb GB free on this disk."
echo
# The same lines Luma's brain settings use (src/luma/llm/brain.py): 24 GB for the bigger brain, 64 for the 122B, 128 for the studio brain, 192 for the biggest.
if   [ "$gb" -ge 192 ]; then brain="Qwen3.5 397B (the studio brain)"; need=160
elif [ "$gb" -ge 128 ]; then brain="Qwen3 235B (the studio brain)"; need=100
elif [ "$gb" -ge 64 ];  then brain="Qwen3.6 35B (the bigger brain), and Qwen3.5 122B fits too (Settings > Brain > Get Qwen3.5 122B)"; need=45
elif [ "$gb" -ge 24 ];  then brain="Qwen3.6 35B (the bigger brain: fast and much smarter than the small one)"; need=25
else brain="Qwen3 4B (the small, fast brain)"; need=5; fi
echo "Brain this Mac can run at home, free and private: $brain"
echo "  In Luma: Settings > Brain > Get the bigger brain (or Get the studio brain). It needs about $need GB of disk."
[ "$free_gb" -lt "$need" ] && echo "  Not enough free disk for it yet: clear some space first."
[ "$gb" -ge 128 ] && echo "  With this much memory, the huge brain runs too (Settings > Brain > Get the huge brain), for the deepest work."
echo "Luma thinks at home: with any of these, nothing you say leaves this Mac to get an answer."
echo "Luma's own brain (the one the device runs): trained on this Mac below, or Settings > Brain > Luma's own brain > Get it."
echo
[ "$what" = "--check" ] && exit 0

if [ "$what" = "--test" ]; then
  # The human test decides. The same turns every brain gets, on the biggest brain here, and then the safety net on it.
  PY=".venv/bin/python"; [ -x "$PY" ] || PY="$(bash scripts/_mac_python.sh)"
  big="$(PYTHONPATH=src "$PY" -c 'from luma.llm import brain; print(brain.big_model_path() or "")')"
  if [ -z "$big" ]; then
    echo "No bigger brain on this Mac yet. In Luma: Settings > Brain > Get the bigger brain (or Get the studio brain). Then run this again."; exit 1
  fi
  name="$(PYTHONPATH=src "$PY" -c 'from luma.llm import brain; print(brain.big_label())')"
  mkdir -p out
  echo "== The human test on $name (269 turns; an hour or more on a studio brain) =="
  LUMA_MODEL_PATH="$big" "$PY" scripts/human_eval.py run --label "$name" --save out/v2-studio.json
  echo "== The safety net on $name =="
  LUMA_MODEL_PATH="$big" "$PY" scripts/human_eval.py safety --label "$name"
  echo "Saved in out/v2-studio.json. Side by side with another brain's run: $PY scripts/human_eval.py summary out/v2-studio.json out/<the other>.json"
  exit 0
fi

if [ "$what" = all ] || [ "$what" = --voice ]; then
  echo "== The voice contest =="; bash scripts/voice_contest_mac.sh || echo "The voice contest stopped early; the lines above say why."
fi
if [ "$what" = all ] || [ "$what" = --brain ]; then
  echo "== Training Luma's own brain =="; bash scripts/train_on_mac.sh || echo "Training stopped early or didn't pass the check; the lines above say why."
fi
