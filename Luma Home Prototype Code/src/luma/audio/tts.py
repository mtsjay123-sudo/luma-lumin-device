"""Local Luma profile blended from licensed Kokoro stock styles; no voice cloning."""
import os
import re
import tempfile
import threading
import wave
from pathlib import Path
import numpy as np
from luma.config import KOKORO_MODEL_PATH, KOKORO_VOICES_PATH, VOICE_ID, VOICE_SPEED, ESPEAK_LIB, ESPEAK_DATA

_kokoro = None
_lock = threading.RLock()
DEFAULT_VOICE = VOICE_ID


class SpeechCancelled(Exception):
    """Speech was interrupted before a complete output file was published."""


def _check_stop(should_stop):
    if should_stop is not None and should_stop():
        raise SpeechCancelled("Speech interrupted.")


def speech_chunks(text, max_chars=240):
    """Bound synthesis latency while preferring sentence/phrase boundaries."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Speech text cannot be empty.")
    if not isinstance(max_chars, int) or max_chars < 40:
        raise ValueError("Speech chunks must allow at least 40 characters.")
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        while len(sentence) > max_chars:
            boundary = max(sentence.rfind(mark, 0, max_chars + 1) for mark in (", ", "; ", ": "))
            if boundary < max_chars // 3:
                boundary = sentence.rfind(" ", 0, max_chars + 1)
            if boundary <= 0:
                boundary = max_chars
            elif sentence[boundary] in ",;:":
                boundary += 1
            chunks.append(sentence[:boundary].strip())
            sentence = sentence[boundary:].strip()
        if sentence:
            chunks.append(sentence)
    return chunks


def _samples(text, voice, should_stop):
    _check_stop(should_stop)
    if not 0.5 <= VOICE_SPEED <= 1.5:
        raise ValueError("LUMA_VOICE_SPEED must be 0.5–1.5.")
    while not _lock.acquire(timeout=0.05):
        _check_stop(should_stop)
    try:
        _check_stop(should_stop)
        engine = _get_kokoro()
        style = 0.7 * engine.get_voice_style("af_bella") + 0.3 * engine.get_voice_style("af_heart") if voice == "luma" else voice
        samples, rate = engine.create(text, voice=style, speed=VOICE_SPEED, lang="en-us")
    finally:
        _lock.release()
    _check_stop(should_stop)
    samples = np.asarray(samples)
    if not samples.size or not np.isfinite(samples).all() or np.max(np.abs(samples)) < 0.00001:
        raise RuntimeError("Speech synthesis produced empty or silent audio.")
    if not isinstance(rate, (int, np.integer)) or not 8000 <= rate <= 192000:
        raise RuntimeError("Speech synthesis produced an invalid sample rate.")
    return (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16), int(rate)


def _get_kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        from kokoro_onnx.config import EspeakConfig
        if not KOKORO_MODEL_PATH.is_file() or not KOKORO_VOICES_PATH.is_file():
            raise FileNotFoundError("Install the documented Kokoro model and voices before enabling speech.")
        _kokoro = Kokoro(str(KOKORO_MODEL_PATH), str(KOKORO_VOICES_PATH), espeak_config=EspeakConfig(lib_path=ESPEAK_LIB, data_path=ESPEAK_DATA))
    return _kokoro


def synthesize(text: str, out_path: str, voice: str = DEFAULT_VOICE, should_stop=None) -> None:
    """Create a complete local WAV atomically; interrupted audio stays private."""
    chunks = speech_chunks(text)
    _check_stop(should_stop)
    destination = Path(out_path)
    with tempfile.NamedTemporaryFile(prefix=".luma-speech-", suffix=".wav", dir=destination.parent, delete=False) as temporary:
        path = temporary.name
    try:
        first_pcm, sample_rate = _samples(chunks[0], voice, should_stop)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(first_pcm.tobytes())
            for chunk in chunks[1:]:
                pcm, rate = _samples(chunk, voice, should_stop)
                if rate != sample_rate:
                    raise RuntimeError("Speech synthesis changed sample rate mid-response.")
                wf.writeframes(pcm.tobytes())
        _check_stop(should_stop)
        os.replace(path, destination)
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def speak(text: str, should_stop=None, voice: str = DEFAULT_VOICE) -> bool:
    """Speak one bounded phrase at a time. Return False after interruption."""
    from luma.audio.io import play
    chunks = speech_chunks(text)
    try:
        for chunk in chunks:
            _check_stop(should_stop)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temporary:
                path = temporary.name
            try:
                synthesize(chunk, path, voice, should_stop=should_stop)
                _check_stop(should_stop)
                play(path, should_stop=should_stop)
                _check_stop(should_stop)
            finally:
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass
        return True
    except SpeechCancelled:
        return False
