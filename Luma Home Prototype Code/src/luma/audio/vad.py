import threading
import tempfile
import wave
from typing import Callable
import numpy as np
import sounddevice as sd
import torch
from silero_vad import VADIterator, load_silero_vad
from luma.config import SAMPLE_RATE

# VADIterator requires 512-sample chunks at 16 kHz
_CHUNK = 512
_SILENCE_MS = 800  # ms of silence before utterance is considered done
_MIN_SPEECH_CHUNKS = 8  # ignore very short noise bursts (<8 chunks ≈ 256 ms)

_model = None
_model_lock = threading.Lock()
_speaking = threading.Event()  # set while LUMA is playing audio — mic is ignored


def set_speaking(val: bool) -> None:
    if val:
        _speaking.set()
    else:
        _speaking.clear()


def _get_vad_iterator() -> VADIterator:
    global _model
    with _model_lock:
        if _model is None:
            _model = load_silero_vad()
    return VADIterator(
        _model,
        threshold=0.5,
        sampling_rate=SAMPLE_RATE,
        min_silence_duration_ms=_SILENCE_MS,
        speech_pad_ms=60,
    )


def _save_wav(audio: np.ndarray, path: str) -> None:
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.astype(np.int16).tobytes())


def start_listening(callback: Callable[[str], None], stop_event: threading.Event | None = None) -> None:
    """Listen continuously. When a complete utterance is detected, call callback(wav_path).

    Blocks until stop_event is set (or KeyboardInterrupt if stop_event is None).
    """
    vad = _get_vad_iterator()
    utterance: list[np.ndarray] = []
    in_speech = False
    speech_chunk_count = 0

    if stop_event is None:
        stop_event = threading.Event()

    q: "queue.Queue[np.ndarray]" = __import__("queue").Queue()

    def audio_callback(indata, frames, time, status):
        if not _speaking.is_set():
            q.put(indata[:, 0].copy())

    print("Listening... (just talk, LUMA will respond)", flush=True)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                        blocksize=_CHUNK, callback=audio_callback):
        was_speaking = False
        while not stop_event.is_set():
            # When LUMA finishes speaking, wait for room reverb to die down,
            # then reset VAD + drain queue to avoid echo triggers
            if was_speaking and not _speaking.is_set():
                _time = __import__("time")
                _queue = __import__("queue")
                # Sleep 400ms so reverb dies down before we start listening again
                _time.sleep(0.4)
                # Keep draining for another 400ms to flush any reverb-tail audio
                drain_deadline = _time.monotonic() + 0.4
                while _time.monotonic() < drain_deadline:
                    try:
                        q.get_nowait()
                    except _queue.Empty:
                        _time.sleep(0.01)
                vad.reset_states()
                in_speech = False
                utterance = []
                speech_chunk_count = 0
                print("Listening...", flush=True)
            was_speaking = _speaking.is_set()

            if _speaking.is_set():
                __import__("time").sleep(0.05)
                continue

            try:
                chunk = q.get(timeout=0.5)
            except __import__("queue").Empty:
                continue

            tensor = torch.from_numpy(chunk.astype(np.float32) / 32768.0)
            result = vad(tensor)

            if result is not None:
                if "start" in result:
                    in_speech = True
                    utterance = []
                    speech_chunk_count = 0

                if "end" in result:
                    if in_speech and speech_chunk_count >= _MIN_SPEECH_CHUNKS:
                        audio = np.concatenate(utterance)
                        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                        tmp.close()
                        _save_wav(audio, tmp.name)
                        callback(tmp.name)
                    in_speech = False
                    utterance = []
                    speech_chunk_count = 0

            if in_speech:
                utterance.append(chunk)
                speech_chunk_count += 1
