from faster_whisper import WhisperModel
from luma.config import WHISPER_MODEL_SIZE

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> str:
    model = _get_model()
    segments, _ = model.transcribe(audio_path, beam_size=5, language="en")
    return " ".join(seg.text.strip() for seg in segments).strip()
