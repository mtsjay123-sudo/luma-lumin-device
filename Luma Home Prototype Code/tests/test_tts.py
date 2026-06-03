import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from luma.audio.tts import synthesize
from luma.config import DATA_DIR

OUT_PATH = DATA_DIR / "test_audio" / "luma_says.wav"
TEST_TEXT = "Hey, I'm LUMA. Nice to finally meet you."


def test_synthesize():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    synthesize(TEST_TEXT, str(OUT_PATH))
    assert OUT_PATH.exists(), "Output WAV was not created"
    assert OUT_PATH.stat().st_size > 10_000, "WAV too small — synthesis likely failed"
    print(f"\nSaved to: {OUT_PATH} ({OUT_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    test_synthesize()
    print("TTS test passed.")
