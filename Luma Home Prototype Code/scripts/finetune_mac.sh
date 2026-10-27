#!/bin/bash
# Fine-tune Luma's brain to talk like a friend, on an Apple Silicon Mac (16 GB of memory or more; about an hour on an M1/M2).
# It needs the Mac's graphics chip: GitHub's virtual Macs and cloud containers don't have a usable one.
#
#   bash scripts/finetune_mac.sh
#
# 1. writes the training conversations (scripts/finetune_data.py: Luma's own jokes, hard-moment replies, honest "I don't know"s)
# 2. trains a small add-on (LoRA) on Qwen3 4B Instruct with mlx-lm
# 3. merges it and converts it to one GGUF file Luma can load
# 4. runs the lab's honesty and humor checks on it, so it only replaces the stock brain if it's at least as honest
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${OUT:-out/finetune}"
BASE="${BASE:-mlx-community/Qwen3-4B-Instruct-2507-4bit}"
HF_BASE="${HF_BASE:-Qwen/Qwen3-4B-Instruct-2507}"

python3 -m venv "$OUT/venv"
"$OUT/venv/bin/pip" install -q --upgrade pip
"$OUT/venv/bin/pip" install -q "mlx-lm>=0.26" "transformers>=4.51" sentencepiece gguf numpy

"$OUT/venv/bin/python" scripts/finetune_data.py "$OUT/data"

# A light touch: a few hundred steps on the top layers, so it picks up the voice without forgetting what it knows.
"$OUT/venv/bin/python" -m mlx_lm.lora --model "$BASE" --train --data "$OUT/data" --iters 600 --batch-size 4 --num-layers 16 \
  --learning-rate 1e-5 --steps-per-eval 100 --adapter-path "$OUT/adapters"

"$OUT/venv/bin/python" -m mlx_lm.fuse --model "$BASE" --adapter-path "$OUT/adapters" --save-path "$OUT/fused" --dequantize

[ -d "$OUT/llama.cpp" ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp "$OUT/llama.cpp"
"$OUT/venv/bin/python" "$OUT/llama.cpp/convert_hf_to_gguf.py" "$OUT/fused" --outfile "$OUT/luma-friend-q8_0.gguf" --outtype q8_0

echo "Checking the new brain against the stock one (honesty and humor)..."
LUMA_MODEL_PATH="$PWD/$OUT/luma-friend-q8_0.gguf" python3 scripts/luma_lab.py honesty --save "$OUT/honesty.json" || true
LUMA_MODEL_PATH="$PWD/$OUT/luma-friend-q8_0.gguf" python3 scripts/luma_lab.py humor --save "$OUT/humor.json" || true
python3 scripts/luma_lab.py summary "$OUT"/honesty.json "$OUT"/humor.json
echo
echo "If those look right, point Luma at it: LUMA_MODEL_PATH=$PWD/$OUT/luma-friend-q8_0.gguf (base model: $HF_BASE)."
