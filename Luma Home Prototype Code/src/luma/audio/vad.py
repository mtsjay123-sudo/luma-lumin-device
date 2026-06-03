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
_MIN_SPEECH_CHUNKS = 4  # ignore very short noise bursts (<4 chunks ≈ 128 ms)

_model = None
_model_lock = threading.Lock()


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
        q.put(indata[:, 0].copy())

    print("Listening... (just talk, LUMA will respond)", flush=True)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                        blocksize=_CHUNK, callback=audio_callback):
        while not stop_event.is_set():
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
