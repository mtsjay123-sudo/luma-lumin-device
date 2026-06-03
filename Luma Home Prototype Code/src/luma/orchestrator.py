import tempfile
import threading
from luma.llm.inference import generate
from luma.audio.tts import synthesize
from luma.audio.io import play, record_push_to_talk
from luma.audio.stt import transcribe
from luma.audio.vad import start_listening, set_speaking

_history: list[dict] = []
_response_lock = threading.Lock()


def _speak(text: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    synthesize(text, wav_path)
    set_speaking(True)
    try:
        play(wav_path)
    finally:
        set_speaking(False)


def ask_typed(prompt: str) -> str:
    _history.append({"role": "user", "content": prompt})
    reply = generate(_history)
    _history.append({"role": "assistant", "content": reply})
    _speak(reply)
    return reply


def ask_voice() -> str:
    """Record push-to-talk audio, transcribe, send to LLM, speak reply."""
    wav_path = record_push_to_talk()
    transcript = transcribe(wav_path)
    print(f"You said: {transcript}")
    if not transcript.strip():
        return ""
    return ask_typed(transcript)


def ask_voice_hands_free(stop_event: threading.Event | None = None) -> None:
    """Hands-free loop: VAD detects speech, transcribes, LLM replies, speaks.

    Blocks until stop_event is set or KeyboardInterrupt.
    """
    def _handle_utterance(wav_path: str):
        try:
            transcript = transcribe(wav_path)
            stripped = transcript.strip()
            if len(stripped.split()) < 2:
                return
            print(f"You said: {stripped}")
            reply = ask_typed(stripped)
            print(f"LUMA: {reply}\n")
        except Exception as e:
            print(f"[error] {e}", flush=True)

    def on_utterance(wav_path: str):
        # If LUMA is already working on a response, drop this utterance instead
        # of queuing it up — prevents stale audio from piling up.
        if not _response_lock.acquire(blocking=False):
            return

        def _worker():
            try:
                _handle_utterance(wav_path)
            finally:
                _response_lock.release()

        threading.Thread(target=_worker, daemon=True).start()

    start_listening(on_utterance, stop_event=stop_event)


def reset():
    _history.clear()
