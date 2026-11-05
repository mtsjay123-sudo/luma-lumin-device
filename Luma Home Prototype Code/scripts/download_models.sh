#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- The brain ---
# A $250-$400 Luma (a board with 12 GB of memory or less, or --device) gets Qwen3 1.7B, the device's own brain: the
# smallest that answers every message in the device lab, 3.3 GB at its peak with hearing and the voice. Everything else
# gets Llama 3.2 3B (a computer's Luma downloads its bigger brain from the app).
mem_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
if [ "${1:-}" = "--device" ] || { [ "${mem_kb:-0}" -gt 0 ] && [ "$mem_kb" -le $((12 * 1024 * 1024)) ]; }; then
    QUANT="${LUMA_DEVICE_QUANT:-Q4_K_M}"
    LLAMA_DIR="$REPO_ROOT/models/qwen3-1.7b"
    LLAMA_FILE="$LLAMA_DIR/Qwen_Qwen3-1.7B-$QUANT.gguf"
    LLAMA_URL="https://huggingface.co/bartowski/Qwen_Qwen3-1.7B-GGUF/resolve/main/Qwen_Qwen3-1.7B-$QUANT.gguf"
    LLAMA_NAME="Qwen3 1.7B $QUANT, the device's own brain (~1.1 GB)"
else
    LLAMA_DIR="$REPO_ROOT/models/llama-3.2-3b-q4"
    LLAMA_FILE="$LLAMA_DIR/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    LLAMA_URL="https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    LLAMA_NAME="Llama 3.2 3B Instruct Q4_K_M (~2.0 GB)"
fi

mkdir -p "$LLAMA_DIR"
if [ -f "$LLAMA_FILE" ]; then
    echo "Brain already downloaded: $LLAMA_FILE"
else
    echo "Downloading $LLAMA_NAME..."
    curl -fL --progress-bar -o "$LLAMA_FILE.part" "$LLAMA_URL"
    mv "$LLAMA_FILE.part" "$LLAMA_FILE"
    echo "Done: $LLAMA_FILE"
fi

# --- Kokoro-82M TTS ---
KOKORO_DIR="$REPO_ROOT/models/kokoro-82m"
KOKORO_MODEL="$KOKORO_DIR/kokoro-v1.0.int8.onnx"
KOKORO_VOICES="$KOKORO_DIR/voices-v1.0.bin"
KOKORO_MODEL_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx"
KOKORO_VOICES_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

mkdir -p "$KOKORO_DIR"
if [ -f "$KOKORO_MODEL" ]; then
    echo "Kokoro model already downloaded: $KOKORO_MODEL"
else
    echo "Downloading Kokoro-82M ONNX int8 (~88 MB)..."
    curl -L --progress-bar -o "$KOKORO_MODEL" "$KOKORO_MODEL_URL"
    echo "Done: $KOKORO_MODEL"
fi

if [ -f "$KOKORO_VOICES" ]; then
    echo "Kokoro voices already downloaded: $KOKORO_VOICES"
else
    echo "Downloading Kokoro voices (~27 MB)..."
    curl -L --progress-bar -o "$KOKORO_VOICES" "$KOKORO_VOICES_URL"
    echo "Done: $KOKORO_VOICES"
fi
