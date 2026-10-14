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


def transcribe_clip(data: bytes, suffix: str = ".webm", *, quick: bool = False, keep: tuple = ()) -> str:
    """Text from a short recording made in Luma's window. Nothing leaves this computer.

    quick: one fast pass, for the words shown while you're still talking and for "Hey Luma".
    keep: phantom words that mean something here (in a conversation, "bye" ends it).
    """
    import tempfile
    if len(data) < _MIN_AUDIO_BYTES:
        return ""
    with tempfile.TemporaryDirectory(prefix="luma-voice-") as folder:
        path = os.path.join(folder, "clip" + suffix)
        with open(path, "wb") as handle:
            handle.write(data)
        segments, _info = _get_model().transcribe(path, beam_size=1 if quick else 3, language="en", vad_filter=True,
                                                  condition_on_previous_text=False)
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
