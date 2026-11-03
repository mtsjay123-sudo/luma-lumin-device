"""Moonshine hears Luma's window when the owner turns it on; Whisper hears it otherwise, and takes any clip Moonshine
can't. Both recognizers are stand-ins here: what's tested is which one gets the clip."""
import importlib
import io
import os
import sys
import types
import unittest
import wave
from unittest import mock

import numpy  # noqa: F401  (loaded once, before the recognizers are swapped for stand-ins)


def wav(seconds=1.0, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as clip:
        clip.setnchannels(1)
        clip.setsampwidth(2)
        clip.setframerate(rate)
        clip.writeframes(b"\x10\x00" * int(seconds * rate))
    return buf.getvalue()


class FakeWhisper:
    def __init__(self, *a, **k):
        pass

    def transcribe(self, audio, **options):
        return [types.SimpleNamespace(text=" what's the weather")], None


class FakeTranscriber:
    calls = []
    fail = False

    def __init__(self, path, arch):
        self.path, self.arch = path, arch

    def transcribe_without_streaming(self, samples, rate):
        FakeTranscriber.calls.append((len(samples), rate))
        if FakeTranscriber.fail:
            raise RuntimeError("model not fetched")
        return types.SimpleNamespace(lines=[types.SimpleNamespace(text="Remind me to call mom"), types.SimpleNamespace(text=" at five.")])


class MoonshineTests(unittest.TestCase):
    def setUp(self):
        whisper = types.ModuleType("faster_whisper")
        whisper.WhisperModel = FakeWhisper
        moon = types.ModuleType("moonshine_voice")
        moon.ModelArch = types.SimpleNamespace(SMALL_STREAMING="small-streaming", MEDIUM_STREAMING="medium-streaming")
        moon.get_model_for_language = lambda lang, arch: (f"/models/{arch}", arch)
        transcriber = types.ModuleType("moonshine_voice.transcriber")
        transcriber.Transcriber = FakeTranscriber
        self.modules = mock.patch.dict(sys.modules, {"faster_whisper": whisper, "moonshine_voice": moon, "moonshine_voice.transcriber": transcriber})
        self.modules.start()
        sys.modules.pop("luma.audio.stt", None)
        self.stt = importlib.import_module("luma.audio.stt")
        FakeTranscriber.calls.clear()
        FakeTranscriber.fail = False

    def tearDown(self):
        sys.modules.pop("luma.audio.stt", None)
        self.modules.stop()

    def test_whisper_by_default(self):
        with mock.patch.dict(os.environ, {"LUMA_STT_ENGINE": ""}):
            self.assertEqual(self.stt.engine(), "whisper")
            self.assertEqual(self.stt.transcribe_clip(wav(), ".wav"), "what's the weather")
        self.assertFalse(FakeTranscriber.calls)

    def test_moonshine_when_turned_on(self):
        with mock.patch.dict(os.environ, {"LUMA_STT_ENGINE": "moonshine"}):
            self.assertEqual(self.stt.transcribe_clip(wav(), ".wav"), "Remind me to call mom at five.")
        self.assertEqual(FakeTranscriber.calls, [(16000, 16000)], "16 kHz mono floats, the way Moonshine wants them")

    def test_whisper_takes_a_clip_moonshine_cant(self):
        FakeTranscriber.fail = True
        with mock.patch.dict(os.environ, {"LUMA_STT_ENGINE": "moonshine"}):
            self.assertEqual(self.stt.transcribe_clip(wav(), ".wav"), "what's the weather")


if __name__ == "__main__":
    unittest.main()
