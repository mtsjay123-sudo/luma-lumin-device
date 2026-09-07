import tempfile
import threading
import wave
import numpy as np
import sounddevice as sd
from pynput import keyboard
from luma.config import SAMPLE_RATE


def play(wav_path: str, should_stop=None) -> None:
    with wave.open(wav_path, "r") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
    # Use an explicit OutputStream rather than sd.play() to avoid the global
    # sounddevice state that can conflict with the always-open InputStream.
    with sd.OutputStream(samplerate=rate, channels=1, dtype='float32') as stream:
        for start in range(0, len(audio), max(1, rate // 10)):
            if should_stop and should_stop(): break
            stream.write(audio[start:start + max(1, rate // 10)].reshape(-1, 1))


def record_push_to_talk(should_stop=None) -> str | None:
    """Block until spacebar is held, record while held, stop on release.

    Returns the path to a temporary WAV file containing the recording.
    """
    should_stop = should_stop or (lambda: False)
    if should_stop(): return None
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
    while not recording.wait(0.1):
        if should_stop():
            listener.stop()
            return None
    if should_stop():
        listener.stop()
        return None
    print("Recording... (release spacebar when done)", flush=True)

    def audio_callback(indata, frames, time, status):
        if not done.is_set():
            chunks.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                        callback=audio_callback):
        import time
        deadline = time.monotonic() + 30
        while not done.wait(0.1):
            if should_stop() or time.monotonic() >= deadline:
                done.set()
                break

    listener.stop()

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
