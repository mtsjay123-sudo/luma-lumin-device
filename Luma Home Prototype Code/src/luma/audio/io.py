import tempfile
import threading
import wave
import numpy as np
import sounddevice as sd
from pynput import keyboard
from luma.config import SAMPLE_RATE


def play(wav_path: str) -> None:
    with wave.open(wav_path, "r") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
    sd.play(audio, samplerate=rate)
    sd.wait()


def record_push_to_talk() -> str:
    """Block until spacebar is held, record while held, stop on release.

    Returns the path to a temporary WAV file containing the recording.
    """
    chunks: list[np.ndarray] = []
    recording = threading.Event()
    done = threading.Event()

    def on_press(key):
        if key == keyboard.Key.space and not recording.is_set():
            recording.set()

    def on_release(key):
        if key == keyboard.Key.space:
            done.set()
            return False  # stop listener

    print("Hold SPACEBAR to speak, release to send...", flush=True)

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    # Wait until spacebar is pressed
    recording.wait()
    print("Recording... (release spacebar when done)", flush=True)

    def audio_callback(indata, frames, time, status):
        if not done.is_set():
            chunks.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                        callback=audio_callback):
        done.wait()

    listener.join()
    print("Processing...", flush=True)

    audio = np.concatenate(chunks, axis=0).flatten() if chunks else np.zeros(SAMPLE_RATE, dtype=np.int16)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    with wave.open(tmp.name, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    return tmp.name
