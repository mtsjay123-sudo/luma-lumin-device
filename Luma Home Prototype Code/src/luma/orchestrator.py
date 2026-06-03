import tempfile
from luma.llm.inference import generate
from luma.audio.tts import synthesize
from luma.audio.io import play

_history: list[dict] = []


def ask_typed(prompt: str) -> str:
    _history.append({"role": "user", "content": prompt})
    reply = generate(_history)
    _history.append({"role": "assistant", "content": reply})

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    synthesize(reply, wav_path)
    play(wav_path)

    return reply


def reset():
    _history.clear()
