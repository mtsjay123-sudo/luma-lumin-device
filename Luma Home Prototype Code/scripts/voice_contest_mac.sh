#!/bin/bash
# The voice contest on this Mac, start to finish: every voice Luma can use says the same lines, Whisper checks each one
# says its words right, and UTMOSv2 ranks how human each sounds. GitHub's test Mac runs out of time on the big voices;
# a fast Mac finishes all of them. Then listen yourself: the samples open in Finder.
#
#   bash scripts/voice_contest_mac.sh
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$(uname -s)" != Darwin ] || [ "$(uname -m)" != arm64 ]; then echo "This needs an Apple Silicon Mac."; exit 1; fi
OUT="${OUT:-out/voice-contest}"
PY="$(bash scripts/_mac_python.sh)"
mkdir -p "$OUT" models/kokoro-82m

echo "1/3  The voice tools (mlx-audio and Luma's classic voice)"
[ -x "$OUT/voice/bin/python" ] || "$PY" -m venv "$OUT/voice"
"$OUT/voice/bin/python" -m pip install -q --upgrade pip
"$OUT/voice/bin/python" -m pip install -q "mlx-audio==0.6.1" "kokoro-onnx>=0.4,<1" numpy
K=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s models/kokoro-82m/kokoro-v1.0.int8.onnx ] || curl -fsSL -o models/kokoro-82m/kokoro-v1.0.int8.onnx "$K/kokoro-v1.0.int8.onnx"
[ -s models/kokoro-82m/voices-v1.0.bin ] || curl -fsSL -o models/kokoro-82m/voices-v1.0.bin "$K/voices-v1.0.bin"

echo "2/3  Every voice says the same lines (the big ones take a while the first time: they download, then learn Luma's voice)"
LUMA_NATURAL_DIR="$PWD/$OUT/natural" LUMA_VOICE_PYTHON="$PWD/$OUT/voice/bin/python" LUMA_VOICE_BUDGET_MIN="${LUMA_VOICE_BUDGET_MIN:-60}" \
  "$OUT/voice/bin/python" scripts/voice_samples.py "$OUT/samples"

echo "3/3  Whisper checks the words, UTMOSv2 ranks how human each voice sounds"
[ -x "$OUT/check/bin/python" ] || "$PY" -m venv "$OUT/check"
"$OUT/check/bin/python" -m pip install -q --upgrade pip
"$OUT/check/bin/python" -m pip install -q "faster-whisper==1.2.1"
"$OUT/check/bin/python" -m pip install -q "git+https://github.com/sarulab-speech/UTMOSv2.git" || echo "UTMOSv2 didn't install; checking the words only"
"$OUT/check/bin/python" -I scripts/voice_check.py "$OUT/samples" | tee "$OUT/ranking.txt"

echo
echo "The ranking is in $OUT/ranking.txt. Now trust your own ears too: the samples are opening in Finder."
echo "Pick the winner in Luma: Settings > Voice (classic, or a natural voice: expressive, studio or lifelike)."
open "$OUT/samples" 2>/dev/null || true
