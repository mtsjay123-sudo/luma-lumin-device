import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from luma.audio.stt import transcribe
from luma.config import DATA_DIR

SAMPLE = DATA_DIR / "test_audio" / "sample.wav"


def test_transcribe():
    assert SAMPLE.exists(), f"Sample WAV not found at {SAMPLE}"
    text = transcribe(str(SAMPLE))
    print(f"\nTranscription: {text!r}")
    assert len(text) > 5, "Transcription too short — check the audio file"
    assert any(word in text.lower() for word in ["weather", "hey", "what"]), (
        f"Expected weather/hey/what in transcription, got: {text!r}"
    )


if __name__ == "__main__":
    test_transcribe()
    print("STT test passed.")
