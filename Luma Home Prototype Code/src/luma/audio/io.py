import os
import tempfile
import threading
import wave
import numpy as np
import sounddevice as sd
from luma.config import SAMPLE_RATE
from luma.hardware.device import resolve_audio_device


def play_chunks(chunks, should_stop=None) -> bool:
    """Play (mono int16 samples, rate) chunks without reopening the audio device."""
    should_stop = should_stop or (lambda: False)
    iterator = iter(chunks)
    if should_stop(): return False
    try: first, rate = next(iterator)
    except StopIteration: return not should_stop()
    if should_stop(): return False
    device = resolve_audio_device(os.getenv("LUMA_OUTPUT_DEVICE"), sd.query_devices(), direction="output")
    block = max(1, rate // 50)
    with sd.OutputStream(samplerate=rate, channels=1, dtype='float32', device=device, latency='low', blocksize=block) as stream:
        import itertools
        try:
            for pcm, next_rate in itertools.chain([(first, rate)], iterator):
                if next_rate != rate: raise ValueError("Speech sample rate changed during playback.")
                audio = np.asarray(pcm).astype(np.float32) / 32767.0
                if audio.ndim != 1 or not np.isfinite(audio).all(): raise ValueError("Invalid speech audio.")
                for start in range(0, len(audio), block):
                    if should_stop(): stream.abort(); return False
                    stream.write(audio[start:start+block].reshape(-1,1))
            if should_stop(): stream.abort(); return False
        except BaseException:
            stream.abort()
            raise
    return True


def play(wav_path: str, should_stop=None) -> bool:
    if should_stop is not None and should_stop(): return False
    with wave.open(wav_path, "r") as wf:
        if wf.getsampwidth() != 2 or wf.getnchannels() != 1:
            raise ValueError("Luma playback requires a mono 16-bit PCM WAV.")
        rate = wf.getframerate()
        pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    return play_chunks([(pcm,rate)], should_stop=should_stop)


def record_push_to_talk(should_stop=None) -> str | None:
    """Block until spacebar is held, record while held, stop on release.

    Returns the path to a temporary WAV file containing the recording.
    """
    should_stop = should_stop or (lambda: False)
    if should_stop(): return None
    try:
        from pynput import keyboard
    except (ImportError, RuntimeError) as error:
        raise RuntimeError("Keyboard voice capture needs a desktop session. Use the web microphone control or hands-free mode on this device.") from error
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

    try:
        device = resolve_audio_device(os.getenv("LUMA_INPUT_DEVICE"), sd.query_devices(), direction="input")
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", device=device,
                            callback=audio_callback):
            import time
            deadline = time.monotonic() + 30
            while not done.wait(0.1):
                if should_stop() or time.monotonic() >= deadline:
                    done.set()
                    break
    finally:
        listener.stop()
        listener.join(timeout=1)
    if should_stop():
        return None
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
