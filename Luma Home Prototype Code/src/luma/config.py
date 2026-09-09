from pathlib import Path
import os
import sys
import ctypes.util

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
MODELS_DIR = REPO_ROOT / "models"
DEFAULT_LLAMA_MODEL_PATH = MODELS_DIR / "llama-3.2-3b-q4" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
# Keep the verified Llama model by default. Select another tested GGUF explicitly.
LLAMA_MODEL_PATH = Path(os.environ.get("LUMA_MODEL_PATH") or DEFAULT_LLAMA_MODEL_PATH).expanduser()


def _model_int(name, default, minimum, maximum):
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value


LLAMA_CONTEXT_SIZE = _model_int("LUMA_CONTEXT_SIZE", 4096, 2048, 32768)
LLAMA_GPU_LAYERS = _model_int("LUMA_GPU_LAYERS", -1, -1, 999)
LLAMA_THREADS = _model_int("LUMA_THREADS", min(8, os.cpu_count() or 4), 1, 128)
LLAMA_BATCH_SIZE = _model_int("LUMA_BATCH_SIZE", 512, 1, 2048)
LLAMA_CHAT_FORMAT = os.environ.get("LUMA_CHAT_FORMAT") or None
WHISPER_MODEL_SIZE = os.environ.get("LUMA_WHISPER_MODEL", "base.en")
MEMORY_DB_PATH = Path("~/.luma/memory.db").expanduser()
SAMPLE_RATE = 16000

# New state does not silently migrate or overwrite any earlier memory database.
STATE_DIR = Path(os.environ.get("LUMA_STATE_DIR", "~/.luma/agent")).expanduser()
STATE_DB_PATH = STATE_DIR / "state.db"
STATE_KEY_PATH = STATE_DIR / "state.key"
KOKORO_MODEL_PATH = Path(os.environ.get("LUMA_TTS_MODEL_PATH") or MODELS_DIR / "kokoro-82m" / "kokoro-v1.0.int8.onnx").expanduser()
KOKORO_VOICES_PATH = MODELS_DIR / "kokoro-82m" / "voices-v1.0.bin"
VOICE_ID = os.environ.get("LUMA_VOICE", "luma")
VOICE_SPEED = float(os.environ.get("LUMA_VOICE_SPEED", "1.03"))
ESPEAK_LIB = os.environ.get("LUMA_ESPEAK_LIB") or ("/opt/homebrew/lib/libespeak-ng.dylib" if sys.platform == "darwin" else ctypes.util.find_library("espeak-ng") or "libespeak-ng.so.1")
ESPEAK_DATA = os.environ.get("LUMA_ESPEAK_DATA", "/opt/homebrew/share/espeak-ng-data" if sys.platform == "darwin" else "/usr/lib/aarch64-linux-gnu/espeak-ng-data")

CLOUD_INTEGRATIONS = {
    "weather": False,
    "news": False,
    "calendar": False,
    "music": False,
    "web_search": False,
    "vision": False,
}
