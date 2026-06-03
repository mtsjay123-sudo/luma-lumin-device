import tempfile
from luma.llm.inference import generate
from luma.audio.tts import synthesize
from luma.audio.io import play, record_push_to_talk
from luma.audio.stt import transcribe

_history: list[dict] = []


def _speak(text: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    synthesize(text, wav_path)
    play(wav_path)


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


def reset():
    _history.clear()
