import wave
import numpy as np
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig
from luma.config import MODELS_DIR

_KOKORO_DIR = MODELS_DIR / "kokoro-82m"
_MODEL_PATH = _KOKORO_DIR / "kokoro-v1.0.int8.onnx"
_VOICES_PATH = _KOKORO_DIR / "voices-v1.0.bin"
# System espeak-ng installed via brew (espeakng-loader has a broken build path on this machine)
_ESPEAK_LIB = "/opt/homebrew/lib/libespeak-ng.dylib"
_ESPEAK_DATA = "/opt/homebrew/share/espeak-ng-data"
DEFAULT_VOICE = "af_bella"

_kokoro: Kokoro | None = None


def _get_kokoro() -> Kokoro:
    global _kokoro
    if _kokoro is None:
        espeak_cfg = EspeakConfig(lib_path=_ESPEAK_LIB, data_path=_ESPEAK_DATA)
        _kokoro = Kokoro(str(_MODEL_PATH), str(_VOICES_PATH), espeak_config=espeak_cfg)
    return _kokoro


def synthesize(text: str, out_path: str, voice: str = DEFAULT_VOICE) -> None:
    kokoro = _get_kokoro()
    samples, sample_rate = kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
    samples_int16 = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(out_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples_int16.tobytes())
