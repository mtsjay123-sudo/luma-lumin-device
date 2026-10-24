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


def speech_plan(text, expressive=False):
    """A whole reply as [(words to say, pause after it in ms)]: shorthand said in full, laughs and sighs
    (real ones in an expressive voice, a beat in the plain one), and a person's pauses between phrases."""
    from luma.audio import speakable
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Speech text cannot be empty.")
    paragraphs = [p for p in re.split(r"\n[ \t]*\n", text) if p.strip()]
    plan = []
    for index, para in enumerate(paragraphs):
        try:
            spoken = spoken_text(para)
        except ValueError:
            continue
        beats = speakable.beats(speakable.say_it(spoken))
        for b, (words, after) in enumerate(beats):
            last_beat = b == len(beats) - 1
            kind = ("break" if index < len(paragraphs) - 1 else None) if last_beat else after
            if words in (speakable.LAUGH, speakable.SIGH):
                cue = speakable.for_voice(words, expressive)
                if cue:
                    plan.append((cue, speakable.pause_ms(cue, kind or "laugh")))
                elif plan:  # the plain voice can't laugh: it takes a beat instead
                    said, pause = plan[-1]
                    plan[-1] = (said, pause + speakable.pause_ms(words, "laugh"))
                continue
            said = speakable.for_voice(words, expressive)
            if not said or not re.search(r"\w", said):
                continue
            chunks = speech_chunks(said)
            for c, chunk in enumerate(chunks):
                plan.append((chunk, speakable.pause_ms(chunk, kind if c == len(chunks) - 1 else None)))
    if not plan:
        raise ValueError("Speech text cannot be empty.")
    return plan


def _with_pause(pcm_rate, ms):
    """Append a pause (silence) to a phrase, so the next one starts when a person would."""
    pcm, rate = pcm_rate
    if not ms or ms <= 0:
        return pcm, rate
    return np.concatenate([pcm, np.zeros(int(rate * min(ms, 1500) / 1000), dtype=np.int16)]), rate


def _resample(pcm, rate, target):
    """Match one phrase's sample rate to the rest (if the voice changed mid-reply)."""
    if rate == target or not len(pcm):
        return pcm
    n = max(1, int(round(len(pcm) * target / rate)))
    return np.interp(np.linspace(0, len(pcm) - 1, n), np.arange(len(pcm)), pcm.astype(np.float32)).astype(np.int16)


def _samples(text, voice, should_stop, speed=None):
    _check_stop(should_stop)
    # The new expressive voice talks when it's ready; if it can't, the classic voice says the same words.
    try:
        from luma.audio import natural
        if natural.speaking():
            pcm, rate = natural.voice().say(text)
            _check_stop(should_stop)
            return pcm, rate
    except SpeechCancelled:
        raise
    except Exception:
        pass
    text = re.sub(r"\[(?:laugh|chuckle|sigh|cough)\]", "", text).strip() or "."
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
        # A system espeak-ng if there is one; otherwise the one kokoro-onnx brings with it (no Homebrew needed).
        espeak = EspeakConfig(lib_path=ESPEAK_LIB, data_path=ESPEAK_DATA) if ESPEAK_LIB and os.path.exists(str(ESPEAK_LIB)) else None
        _kokoro = Kokoro.from_session(session, str(KOKORO_VOICES_PATH), espeak_config=espeak)
    return _kokoro


def expressive_now():
    """Is the expressive voice (it can laugh and sigh) the one speaking right now?"""
    try:
        from luma.audio import natural
        return natural.active()
    except Exception:
        return False


def ready():
    """Is Luma's natural voice installed here?"""
    try:
        import kokoro_onnx  # noqa: F401
    except ImportError:
        return False
    return KOKORO_MODEL_PATH.is_file() and KOKORO_VOICES_PATH.is_file()


def warm_up(voice: str = DEFAULT_VOICE):
    """Load the voice once at startup, so the first thing Luma says isn't slow."""
    if not ready():
        return False
    try:
        _samples("Hi.", voice, None)
        return True
    except Exception:
        return False


def synthesize(text: str, out_path: str, voice: str = DEFAULT_VOICE, should_stop=None, speed=None) -> None:
    """Create a complete local WAV atomically; interrupted audio stays private.
    Each phrase is followed by a natural pause, including the last (the gap before the next piece plays)."""
    plan = speech_plan(text, expressive=expressive_now())
    _check_stop(should_stop)
    destination = Path(out_path)
    with tempfile.NamedTemporaryFile(prefix=".luma-speech-", suffix=".wav", dir=destination.parent, delete=False) as temporary:
        path = temporary.name
    try:
        first_pcm, sample_rate = _with_pause(_samples(plan[0][0], voice, should_stop, speed), plan[0][1])
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(first_pcm.tobytes())
            for chunk, pause in plan[1:]:
                pcm, rate = _with_pause(_samples(chunk, voice, should_stop, speed), pause)
                wf.writeframes(_resample(pcm, rate, sample_rate).tobytes())
        _check_stop(should_stop)
        os.replace(path, destination)
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def silence(out_path: str, ms: int = 180, rate: int = 24000) -> None:
    """A moment of quiet, for a piece that has nothing to say out loud (only an emoji, say)."""
    with wave.open(out_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(np.zeros(int(rate * ms / 1000), dtype=np.int16).tobytes())


def speak(text: str, should_stop=None, voice: str = DEFAULT_VOICE, speed=None) -> bool:
    """Prefetch at most two phrases while one continuous output stream plays."""
    return _play_phrases(iter(speech_plan(text, expressive=expressive_now())), should_stop, voice, speed)


def speak_stream(phrases, should_stop=None, voice: str = DEFAULT_VOICE, speed=None) -> bool:
    """Speak phrases as they arrive (e.g. while the model is still writing).

    `phrases` is a blocking iterator of text pieces, already grouped into
    sentences by the caller (see luma.llm.streaming.SentenceBuffer).
    """
    def chunks():
        for phrase in phrases:
            if isinstance(phrase, str) and phrase.strip():
                try:
                    yield from speech_plan(phrase, expressive=expressive_now())
                except ValueError:
                    continue  # only an emoji or a mark: nothing to say
    return _play_phrases(chunks(), should_stop, voice, speed)


def _play_phrases(chunks, should_stop, voice, speed):
    from luma.audio.io import play_chunks
    stopped = threading.Event()
    pending = queue.Queue(maxsize=2)
    should_cancel = lambda: stopped.is_set() or (should_stop is not None and should_stop())

    def publish(value):
        while not should_cancel():
            try: pending.put(value, timeout=.05); return
            except queue.Full: continue

    def produce():
        try:
            for item in chunks:
                _check_stop(should_cancel)
                chunk, pause = item if isinstance(item, tuple) else (item, 0)
                publish(_with_pause(_samples(chunk, voice, should_cancel, speed), pause))
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
