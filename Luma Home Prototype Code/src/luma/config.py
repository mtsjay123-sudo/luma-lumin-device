from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
MODELS_DIR = REPO_ROOT / "models"
LLAMA_MODEL_PATH = MODELS_DIR / "llama-3.2-3b-q4" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
WHISPER_MODEL_SIZE = "base.en"
MEMORY_DB_PATH = Path("~/.luma/memory.db").expanduser()
SAMPLE_RATE = 16000

CLOUD_INTEGRATIONS = {
    "weather": False,
    "news": False,
    "calendar": False,
    "music": False,
    "web_search": False,
    "vision": False,
}
