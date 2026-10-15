import os

from faster_whisper import WhisperModel
from luma.config import WHISPER_MODEL_SIZE

_model: WhisperModel | None = None


def _quiet_av():
    """PyAV 14 dropped open()'s metadata_errors option, which faster-whisper still passes ("unexpected keyword
    argument 'metadata_errors'"). Accept it and drop it, so any PyAV version decodes the recording."""
    try:
        import av
    except ImportError:
        return
    if getattr(av.open, "_luma_quiet", False):
        return
    original = av.open
    def open_(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        except TypeError as error:
            if "metadata_errors" not in str(error): raise
            kwargs.pop("metadata_errors", None)
            return original(*args, **kwargs)
    open_._luma_quiet = True
    av.open = open_


_quiet_av()

# Audio files smaller than this are treated as silent/too-short and skipped
# entirely — this avoids whisper hallucinating text from noise.
_MIN_AUDIO_BYTES = 1000


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        # The desktop app may fetch the speech model once (about 150 MB); the device ships with it.
        download = os.environ.get("LUMA_WHISPER_DOWNLOAD") == "1"
        _model = WhisperModel(WHISPER_MODEL_SIZE, device=os.environ.get("LUMA_WHISPER_DEVICE", "cpu"), compute_type=os.environ.get("LUMA_WHISPER_COMPUTE_TYPE", "int8"), local_files_only=not download)
    return _model


# What Whisper tends to "hear" in silence. Alone, these are noise, not you.
_PHANTOMS = {"", "you", "thank you", "thanks for watching", "thank you for watching", "bye", "okay", "so"}


def _wav_samples(data):
    """16-bit PCM WAV -> mono float32 at 16 kHz, the way Whisper wants it. None if it isn't that."""
    import io, wave
    import numpy as np
    try:
        with wave.open(io.BytesIO(data)) as clip:
            if clip.getsampwidth() != 2: return None
            channels, rate = clip.getnchannels(), clip.getframerate()
            pcm = np.frombuffer(clip.readframes(clip.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    except (wave.Error, EOFError):
        return None
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1)
    if rate != 16000 and len(pcm):
        pcm = np.interp(np.linspace(0, len(pcm), int(len(pcm) * 16000 / rate), endpoint=False), np.arange(len(pcm)), pcm).astype(np.float32)
    return pcm


def transcribe_clip(data: bytes, suffix: str = ".webm", *, quick: bool = False, keep: tuple = ()) -> str:
    """Text from a short recording made in Luma's window. Nothing leaves this computer.

    quick: one fast pass, for the words shown while you're still talking and for "Hey Luma".
    keep: phantom words that mean something here (in a conversation, "bye" ends it).
    """
    import tempfile
    if len(data) < _MIN_AUDIO_BYTES:
        return ""
    options = dict(beam_size=1 if quick else 3, language="en", vad_filter=True, condition_on_previous_text=False)
    samples = _wav_samples(data) if suffix == ".wav" else None
    if samples is not None:
        # Plain WAV from Luma's window: straight to Whisper, no audio decoder involved at all.
        segments, _info = _get_model().transcribe(samples, **options)
        text = " ".join(seg.text.strip() for seg in segments).strip()
    else:
        with tempfile.TemporaryDirectory(prefix="luma-voice-") as folder:
            path = os.path.join(folder, "clip" + suffix)
            with open(path, "wb") as handle:
                handle.write(data)
            segments, _info = _get_model().transcribe(path, **options)
            text = " ".join(seg.text.strip() for seg in segments).strip()
    said = text.lower().strip(" .!?,")
    return "" if said in _PHANTOMS and said not in keep else text


def warm_up():
    """Load (and on the desktop, fetch once) the speech model in the background."""
    try:
        _get_model()
    except Exception as error:
        print(f"[stt] not ready yet: {error}", flush=True)


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
