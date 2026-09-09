#!/usr/bin/env bash
# Provision only a real Jetson. Inspection is the default; never runs on the Mac.
set -euo pipefail

LUMA_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LUMA_PYTHON="${LUMA_PYTHON:-python3.11}"
LUMA_ACCELERATOR="cpu"
LUMA_INSTALL=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --install) LUMA_INSTALL=1 ;;
    --check) LUMA_INSTALL=0 ;;
    --cuda) LUMA_ACCELERATOR="cuda" ;;
    --python) shift; LUMA_PYTHON="${1:?--python requires a Python executable}" ;;
    --help)
      echo "Usage: scripts/setup_jetson.sh [--check | --install] [--cuda] [--python python3.11]"
      echo "Inspection only by default. Install on the actual Jetson after reading docs/DEVICE_SETUP.md."
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

echo "Luma device bootstrap: $(uname -s) / $(uname -m); accelerator=$LUMA_ACCELERATOR"
if [ "$LUMA_INSTALL" -eq 0 ]; then
  if [ -r /proc/device-tree/model ]; then tr -d '\0' </proc/device-tree/model; echo; fi
  if [ -r /etc/nv_tegra_release ]; then head -n 1 /etc/nv_tegra_release; fi
  if command -v "$LUMA_PYTHON" >/dev/null 2>&1; then "$LUMA_PYTHON" --version; else echo "Required: Python >=3.11 with venv support ($LUMA_PYTHON not found)."; fi
  if [ -x "$LUMA_SOURCE/.venv/bin/python" ]; then
    "$LUMA_SOURCE/.venv/bin/python" -m luma.hardware.diagnostics --no-audio || true
  fi
  echo "Inspection complete. No packages, system settings or services were changed."
  exit 0
fi

if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != aarch64 ] ||
   [ ! -r /proc/device-tree/model ] || ! tr -d '\0' </proc/device-tree/model | grep -q NVIDIA; then
  echo "Installation requires the actual NVIDIA Jetson running Linux/aarch64. No changes made." >&2
  exit 1
fi
if [ "$(id -u)" -eq 0 ]; then
  echo "Run as the intended unprivileged Luma user; sudo is used only for system packages." >&2
  exit 1
fi
if ! command -v "$LUMA_PYTHON" >/dev/null 2>&1; then
  echo "Install a trusted Python 3.11+ interpreter with venv support, then pass --python /path/to/python." >&2
  echo "This script does not replace JetPack's system Python or add third-party apt repositories." >&2
  exit 1
fi
"$LUMA_PYTHON" -c 'import sys, venv; assert sys.version_info >= (3,11), "Luma needs Python >=3.11"'
if [ "$LUMA_ACCELERATOR" = cuda ]; then
  if [ ! -x /usr/local/cuda/bin/nvcc ] && ! command -v nvcc >/dev/null 2>&1; then
    echo "--cuda requires the CUDA toolkit for the installed JetPack. CPU mode is available without it." >&2
    exit 1
  fi
  export CUDACXX="$(command -v nvcc || echo /usr/local/cuda/bin/nvcc)"
  export CMAKE_ARGS="-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87"
else
  export CMAKE_ARGS="-DGGML_CUDA=OFF"
fi

sudo apt-get update
sudo apt-get install -y build-essential cmake pkg-config libportaudio2 portaudio19-dev \
  libsndfile1 espeak-ng libespeak-ng1 alsa-utils ffmpeg libopenblas-dev
if [ -e "$LUMA_SOURCE/.venv" ] && [ ! -x "$LUMA_SOURCE/.venv/bin/python" ]; then
  echo "Existing .venv is unusable; preserve it and create a Linux venv before retrying." >&2
  exit 1
fi
if [ ! -d "$LUMA_SOURCE/.venv" ]; then "$LUMA_PYTHON" -m venv "$LUMA_SOURCE/.venv"; fi
LUMA_VENV_PYTHON="$LUMA_SOURCE/.venv/bin/python"
"$LUMA_VENV_PYTHON" -m pip install --upgrade pip setuptools wheel
# Always build this package for the selected CPU/CUDA mode; never reuse a Mac wheel.
"$LUMA_VENV_PYTHON" -m pip install --no-cache-dir --force-reinstall --no-deps \
  --no-binary llama-cpp-python 'llama-cpp-python==0.3.23'
"$LUMA_VENV_PYTHON" -m pip install -c "$LUMA_SOURCE/deploy/jetson-constraints.txt" -e "$LUMA_SOURCE"
"$LUMA_VENV_PYTHON" -m pip check

# Preserve every existing setting/secret. Only append platform defaults not yet set.
LUMA_SOURCE="$LUMA_SOURCE" LUMA_ACCELERATOR="$LUMA_ACCELERATOR" "$LUMA_VENV_PYTHON" - <<'PY'
import ctypes.util, os
from pathlib import Path
from dotenv import dotenv_values
root = Path(os.environ['LUMA_SOURCE'])
path = root / '.env'
if path.is_symlink(): raise SystemExit('Refusing to replace a symlinked .env')
existing = dotenv_values(path) if path.exists() else {}
library = next((p for p in Path('/usr/lib').glob('*/libespeak-ng.so.1') if p.is_file()), None)
data = next((p for p in (Path('/usr/lib/aarch64-linux-gnu/espeak-ng-data'), Path('/usr/share/espeak-ng-data')) if p.is_dir()), None)
defaults = {'LUMA_ESPEAK_LIB': str(library or '/usr/lib/aarch64-linux-gnu/libespeak-ng.so.1'),
            'LUMA_ESPEAK_DATA': str(data or '/usr/lib/aarch64-linux-gnu/espeak-ng-data'),
            'LUMA_GPU_LAYERS': '-1' if os.environ['LUMA_ACCELERATOR'] == 'cuda' else '0',
            'LUMA_THREADS': '4', 'LUMA_BATCH_SIZE': '128', 'LUMA_CONTEXT_SIZE': '4096',
            'LUMA_WHISPER_DEVICE': 'cpu', 'LUMA_WHISPER_COMPUTE_TYPE': 'int8',
            'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}
with path.open('a') as handle:
    for key, value in defaults.items():
        if key not in existing: handle.write(f'\n{key}={value}\n')
path.chmod(0o600)
PY

mkdir -p "$LUMA_SOURCE/.local-state/device"
chmod 700 "$LUMA_SOURCE/.local-state" "$LUMA_SOURCE/.local-state/device"
LUMA_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
"$LUMA_VENV_PYTHON" -m pip freeze >"$LUMA_SOURCE/.local-state/device/requirements-$LUMA_STAMP.txt"
chmod 600 "$LUMA_SOURCE/.local-state/device/requirements-$LUMA_STAMP.txt"
echo "Dependencies installed. Select the local GGUF and audio devices in .env, then copy/verify model assets."
echo "Run .venv/bin/python -m luma.hardware.diagnostics before installing the boot service."
echo "No service was enabled and no microphone was opened by this installer."
