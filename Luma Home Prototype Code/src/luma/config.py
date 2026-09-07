from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
MODELS_DIR = REPO_ROOT / "models"
LLAMA_MODEL_PATH = MODELS_DIR / "llama-3.2-3b-q4" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
WHISPER_MODEL_SIZE = "base.en"
MEMORY_DB_PATH = Path("~/.luma/memory.db").expanduser()
SAMPLE_RATE = 16000

# New state does not silently migrate or overwrite any earlier memory database.
STATE_DIR = Path(os.environ.get("LUMA_STATE_DIR", "~/.luma/agent")).expanduser()
STATE_DB_PATH = STATE_DIR / "state.db"
STATE_KEY_PATH = STATE_DIR / "state.key"
KOKORO_MODEL_PATH = MODELS_DIR / "kokoro-82m" / "kokoro-v1.0.int8.onnx"
KOKORO_VOICES_PATH = MODELS_DIR / "kokoro-82m" / "voices-v1.0.bin"
VOICE_ID = os.environ.get("LUMA_VOICE", "luma")
VOICE_SPEED = float(os.environ.get("LUMA_VOICE_SPEED", "0.96"))
ESPEAK_LIB = os.environ.get("LUMA_ESPEAK_LIB", "/opt/homebrew/lib/libespeak-ng.dylib")
ESPEAK_DATA = os.environ.get("LUMA_ESPEAK_DATA", "/opt/homebrew/share/espeak-ng-data")

CLOUD_INTEGRATIONS = {
    "weather": False,
    "news": False,
    "calendar": False,
    "music": False,
    "web_search": False,
    "vision": False,
}
