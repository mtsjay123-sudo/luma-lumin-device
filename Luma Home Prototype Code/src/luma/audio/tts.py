"""Local Luma profile blended from licensed Kokoro stock styles; no voice cloning."""
import threading
import wave
import numpy as np
from luma.config import KOKORO_MODEL_PATH, KOKORO_VOICES_PATH, VOICE_ID, VOICE_SPEED, ESPEAK_LIB, ESPEAK_DATA

_kokoro = None
_lock = threading.RLock()
DEFAULT_VOICE = VOICE_ID


def _get_kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        from kokoro_onnx.config import EspeakConfig
        if not KOKORO_MODEL_PATH.is_file() or not KOKORO_VOICES_PATH.is_file():
            raise FileNotFoundError("Install the documented Kokoro model and voices before enabling speech.")
        _kokoro = Kokoro(str(KOKORO_MODEL_PATH), str(KOKORO_VOICES_PATH), espeak_config=EspeakConfig(lib_path=ESPEAK_LIB, data_path=ESPEAK_DATA))
    return _kokoro


def synthesize(text: str, out_path: str, voice: str = DEFAULT_VOICE) -> None:
    if not text.strip(): raise ValueError("Speech text cannot be empty.")
    if not 0.5 <= VOICE_SPEED <= 1.5: raise ValueError("LUMA_VOICE_SPEED must be 0.5–1.5.")
    with _lock:
        engine = _get_kokoro()
        style = 0.7 * engine.get_voice_style("af_bella") + 0.3 * engine.get_voice_style("af_heart") if voice == "luma" else voice
        samples, rate = engine.create(text, voice=style, speed=VOICE_SPEED, lang="en-us")
    samples = np.asarray(samples)
    if not samples.size or not np.isfinite(samples).all() or np.max(np.abs(samples)) < 0.00001:
        raise RuntimeError("Speech synthesis produced empty or silent audio.")
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(out_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm.tobytes())
