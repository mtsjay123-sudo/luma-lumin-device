#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --- Llama 3.2 3B ---
LLAMA_DIR="$REPO_ROOT/models/llama-3.2-3b-q4"
LLAMA_FILE="$LLAMA_DIR/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
LLAMA_URL="https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

mkdir -p "$LLAMA_DIR"
if [ -f "$LLAMA_FILE" ]; then
    echo "Llama model already downloaded: $LLAMA_FILE"
else
    echo "Downloading Llama 3.2 3B Instruct Q4_K_M (~2.0 GB)..."
    curl -L --progress-bar -o "$LLAMA_FILE" "$LLAMA_URL"
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
