#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="$REPO_ROOT/models/llama-3.2-3b-q4"
MODEL_FILE="$MODEL_DIR/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
MODEL_URL="https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"

mkdir -p "$MODEL_DIR"

if [ -f "$MODEL_FILE" ]; then
    echo "Model already downloaded: $MODEL_FILE"
    exit 0
fi

echo "Downloading Llama 3.2 3B Instruct Q4_K_M (~2.0 GB)..."
curl -L --progress-bar -o "$MODEL_FILE" "$MODEL_URL"
echo "Done: $MODEL_FILE"
