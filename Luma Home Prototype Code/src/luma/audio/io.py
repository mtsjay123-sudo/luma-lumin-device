import wave
import numpy as np
import sounddevice as sd


def play(wav_path: str) -> None:
    with wave.open(wav_path, "r") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
    sd.play(audio, samplerate=rate)
    sd.wait()
