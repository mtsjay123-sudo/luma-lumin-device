"""Bounded, mute-aware local VAD. Audio exists only in temporary utterance files."""
import os
import queue
import threading
import tempfile
import time
import wave
from collections import deque
from typing import Callable
import numpy as np
import sounddevice as sd
import torch
from silero_vad import VADIterator, load_silero_vad
from luma.config import SAMPLE_RATE
from luma.hardware.device import resolve_audio_device

_CHUNK = 512
_speaking = threading.Event()
_model = None
_model_lock = threading.Lock()


def set_speaking(value):
    _speaking.set() if value else _speaking.clear()


def _get_vad_iterator():
    global _model
    with _model_lock:
        if _model is None: _model = load_silero_vad()
    return VADIterator(_model, threshold=0.5, sampling_rate=SAMPLE_RATE, min_silence_duration_ms=900, speech_pad_ms=60)


def _save_wav(audio, path):
    with wave.open(path, "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.astype(np.int16).tobytes())


def start_listening(callback: Callable[[str], None], stop_event=None, should_stop=None, allow_barge_in=False):
    """Capture local utterances; barge-in requires explicitly isolated playback.

    There is no acoustic echo cancellation. Keep allow_barge_in False on ordinary
    speakers. A caller using headphones may opt in and dispatch callback work to
    a worker so this loop can capture an interruption during speech generation.
    """
    if not isinstance(allow_barge_in, bool):
        raise ValueError("Barge-in must be an explicit true or false value.")
    stop_event = stop_event or threading.Event()
    should_stop = should_stop or (lambda: False)
    if should_stop() or stop_event.is_set(): return
    vad = _get_vad_iterator()
    q = queue.Queue(maxsize=32)
    utterance, pre = [], deque(maxlen=6)
    in_speech = False
    suppress_until = 0.0

    def audio_callback(indata, frames, timing, status):
        if (_speaking.is_set() and not allow_barge_in) or should_stop() or time.monotonic() < suppress_until: return
        try: q.put_nowait(indata[:, 0].copy())
        except queue.Full: pass

    device = resolve_audio_device(os.getenv("LUMA_INPUT_DEVICE"), sd.query_devices(), direction="input")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", device=device, blocksize=_CHUNK, callback=audio_callback):
        while not stop_event.is_set() and not should_stop():
            try: chunk = q.get(timeout=0.1)
            except queue.Empty: continue
            if _speaking.is_set() and not allow_barge_in:
                utterance, in_speech = [], False
                vad.reset_states(); pre.clear()
                continue
            result = vad(torch.from_numpy(chunk.astype(np.float32) / 32768.0))
            if result and "start" in result:
                in_speech = True
                utterance = list(pre)
            if in_speech: utterance.append(chunk)
            pre.append(chunk)
            ended = result and "end" in result
            if in_speech and (ended or len(utterance) >= int(30*SAMPLE_RATE/_CHUNK)):
                captured = utterance
                utterance, in_speech = [], False
                vad.reset_states(); pre.clear()
                if len(captured) >= 12 and not should_stop():
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp: path = tmp.name
                    _save_wav(np.concatenate(captured), path)
                    # Caller owns deletion, including transcription/model failures.
                    callback(path)
                suppress_until = time.monotonic() + 0.4
                # Bounded drain: callbacks are suppressed throughout recovery.
                for _ in range(q.maxsize):
                    try: q.get_nowait()
                    except queue.Empty: break
