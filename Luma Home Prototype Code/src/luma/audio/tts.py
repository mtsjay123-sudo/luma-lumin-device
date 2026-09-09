"""Local conversational speech with coherent phrasing and bounded prefetch."""
import os
import queue
import math
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
VOICE_PROFILES = {
    "luma": {"label":"Luma · Conversational", "voice":"af_heart"},
    "soft": {"label":"Luma · Warm", "voice":"af_bella"},
    "grounded": {"label":"Luma · Grounded", "voice":"am_fenrir"},
}


def validate_preferences(value):
    if not isinstance(value, dict) or set(value) != {"voice", "speed"}:
        raise ValueError("Choose a voice and speaking pace.")
    if value["voice"] not in VOICE_PROFILES:
        raise ValueError("Choose one of Luma's available voices.")
    speed = value["speed"]
    if type(speed) not in (int, float) or not math.isfinite(speed) or not .85 <= speed <= 1.2:
        raise ValueError("Speaking pace must be between 0.85 and 1.20.")
    return {"voice":value["voice"], "speed":round(speed,2)}


def _spoken_dollars(match):
    """Read an explicit two-decimal dollar amount without rounding its value."""
    dollars = int(match["whole"].replace(",", ""))
    cents = int(match["cents"])
    parts = []
    if dollars or not cents:
        parts.append(f"{dollars} dollar" + ("" if dollars == 1 else "s"))
    if cents:
        parts.append(f"{cents} cent" + ("" if cents == 1 else "s"))
    return ("minus " if match["sign"] else "") + " and ".join(parts)


def spoken_text(text):
    """Prepare speech; retain displayed text and exact monetary values elsewhere."""
    if not isinstance(text,str) or not text.strip(): raise ValueError("Speech text cannot be empty.")
    text = re.sub(r"\*\*(.+?)\*\*",r"\1",text)
    text = re.sub(r"`([^`]+)`",r"\1",text)
    text = re.sub(r"(?m)^\s*#{1,6}\s+", "", text)
    # Give explicit list items their own phrasing, including wrapped item text.
    # Collapsing all newlines first makes "Get eggs / Call Mom" run together.
    blocks, current = [], ""
    for line in text.splitlines():
        item = re.match(r"^[ \t]*[-*•][ \t]+(.*)", line)
        if item or not line.strip():
            if current: blocks.append(current)
            current = item[1].strip() if item else ""
        else:
            current = (current + " " + line.strip()).strip()
    if current: blocks.append(current)
    text = " ".join(block if index == len(blocks)-1 or re.search(r'[.!?;:,][\"\u201d\u2019\')\]]*$', block)
                    else block + "." for index, block in enumerate(blocks))
    text = re.sub(r"(?<=[A-Za-z])[—–](?=[A-Za-z])", ", ", text)
    # Kokoro's installed tokenizer reads "$12.50" as "dollar twelve, fifty".
    # Only normalize explicit decimal amounts: leave shorthand, other currencies,
    # dates, phone numbers, IDs and unsupported number formats unchanged.
    text = re.sub(r"(?<![\w$])(?P<sign>-)?\$(?P<whole>\d{1,3}(?:,\d{3}){1,3}|\d{1,12})"
                  r"\.(?P<cents>\d{2})(?!\w|[.,]\d)", _spoken_dollars, text)
    return re.sub(r"\s+", " ", text).strip()


class SpeechCancelled(Exception):
    """Speech was interrupted before a complete output file was published."""


def _check_stop(should_stop):
    if should_stop is not None and should_stop():
        raise SpeechCancelled("Speech interrupted.")


def speech_chunks(text, max_chars=240):
    """Keep short connected sentences together so their intonation has context."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Speech text cannot be empty.")
    if not isinstance(max_chars, int) or max_chars < 40:
        raise ValueError("Speech chunks must allow at least 40 characters.")
    text = re.sub(r"\s+", " ", text).strip()
    pieces = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        while len(sentence) > max_chars:
            boundary = max(sentence.rfind(mark, 0, max_chars + 1) for mark in (", ", "; ", ": "))
            if boundary < max_chars // 3: boundary = sentence.rfind(" ", 0, max_chars + 1)
            if boundary <= 0: boundary = max_chars
            elif sentence[boundary] in ",;:": boundary += 1
            pieces.append(sentence[:boundary].strip())
            sentence = sentence[boundary:].strip()
        if sentence: pieces.append(sentence)
    chunks, current = [], ""
    for piece in pieces:
        if current and len(current)+len(piece)+1 > max_chars:
            chunks.append(current); current = ""
        current = (current + " " + piece).strip()
    if current: chunks.append(current)
    return chunks


def _samples(text, voice, should_stop, speed=None):
    _check_stop(should_stop)
    speed = VOICE_SPEED if speed is None else speed
    if type(speed) not in (int,float) or not math.isfinite(speed) or not 0.5 <= speed <= 1.5:
        raise ValueError("LUMA_VOICE_SPEED must be 0.5–1.5.")
    while not _lock.acquire(timeout=0.05):
        _check_stop(should_stop)
    try:
        _check_stop(should_stop)
        engine = _get_kokoro()
        style = VOICE_PROFILES.get(voice, {}).get("voice", voice)
        samples, rate = engine.create(text, voice=style, speed=speed, lang="en-us")
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
        import onnxruntime as ort
        options = ort.SessionOptions()
        threads = int(os.environ.get("LUMA_TTS_THREADS", "2"))
        if not 1 <= threads <= 8: raise ValueError("LUMA_TTS_THREADS must be 1–8.")
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(str(KOKORO_MODEL_PATH), sess_options=options, providers=["CPUExecutionProvider"])
        _kokoro = Kokoro.from_session(session, str(KOKORO_VOICES_PATH), espeak_config=EspeakConfig(lib_path=ESPEAK_LIB, data_path=ESPEAK_DATA))
    return _kokoro


def synthesize(text: str, out_path: str, voice: str = DEFAULT_VOICE, should_stop=None, speed=None) -> None:
    """Create a complete local WAV atomically; interrupted audio stays private."""
    chunks = speech_chunks(spoken_text(text))
    _check_stop(should_stop)
    destination = Path(out_path)
    with tempfile.NamedTemporaryFile(prefix=".luma-speech-", suffix=".wav", dir=destination.parent, delete=False) as temporary:
        path = temporary.name
    try:
        first_pcm, sample_rate = _samples(chunks[0], voice, should_stop, speed)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(first_pcm.tobytes())
            for chunk in chunks[1:]:
                pcm, rate = _samples(chunk, voice, should_stop, speed)
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


def speak(text: str, should_stop=None, voice: str = DEFAULT_VOICE, speed=None) -> bool:
    """Prefetch at most two phrases while one continuous output stream plays."""
    from luma.audio.io import play_chunks
    chunks = speech_chunks(spoken_text(text))
    stopped = threading.Event()
    pending = queue.Queue(maxsize=2)
    should_cancel = lambda: stopped.is_set() or (should_stop is not None and should_stop())

    def publish(value):
        while not should_cancel():
            try: pending.put(value, timeout=.05); return
            except queue.Full: continue

    def produce():
        try:
            for chunk in chunks:
                _check_stop(should_cancel)
                publish(_samples(chunk, voice, should_cancel, speed))
            publish(None)
        except Exception as error:
            publish(error)

    def consume():
        while not should_cancel():
            try: value = pending.get(timeout=.05)
            except queue.Empty: continue
            if value is None: return
            if isinstance(value, Exception): raise value
            yield value
        raise SpeechCancelled("Speech interrupted.")

    worker = threading.Thread(target=produce, daemon=True)
    worker.start()
    try:
        return play_chunks(consume(), should_stop=should_cancel)
    except SpeechCancelled:
        return False
    finally:
        # A native synthesis already in progress may finish, but never enqueue/play
        # stale speech after an interruption. Audio stays in a bounded RAM queue.
        stopped.set()
