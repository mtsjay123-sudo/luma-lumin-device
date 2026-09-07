import os

from faster_whisper import WhisperModel
from luma.config import WHISPER_MODEL_SIZE

_model: WhisperModel | None = None

# Audio files smaller than this are treated as silent/too-short and skipped
# entirely — this avoids whisper hallucinating text from noise.
_MIN_AUDIO_BYTES = 1000


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8", local_files_only=True)
    return _model


def transcribe(audio_path: str) -> str:
    global _model

    # Fix 1 / Fix 4: guard against missing, empty, or too-short audio files
    # before we ever hand them to whisper. Returning "" lets the orchestrator's
    # "< 2 words" gate drop them cleanly.
    try:
        if not audio_path or not os.path.exists(audio_path):
            return ""
        size = os.path.getsize(audio_path)
        if size == 0 or size < _MIN_AUDIO_BYTES:
            return ""
    except OSError:
        return ""

    try:
        model = _get_model()
        segments, _info = model.transcribe(audio_path, beam_size=5, language="en")
        return " ".join(seg.text.strip() for seg in segments).strip()
    except Exception as e:
        # Fix 5: drop the model so the next call reloads it fresh. Recovers
        # from a corrupted/half-initialized model state without a restart.
        print(f"[stt] transcription failed: {e}", flush=True)
        _model = None
        return ""
