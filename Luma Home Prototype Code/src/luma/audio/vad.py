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


def _get_vad_iterator(silence_ms=900):
    global _model
    with _model_lock:
        if _model is None: _model = load_silero_vad()
    return VADIterator(_model, threshold=0.5, sampling_rate=SAMPLE_RATE, min_silence_duration_ms=silence_ms, speech_pad_ms=60)


def _save_wav(audio, path):
    with wave.open(path, "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.astype(np.int16).tobytes())


def start_listening(callback: Callable[[str], None], stop_event=None, should_stop=None, allow_barge_in=False, on_pause=None, on_barge_in=None,
                    on_maybe_done=None, on_carried_on=None):
    """Capture local utterances; barge-in requires playback the mic can't hear, or echo cancellation.

    With the echo canceller (luma.audio.echo, WebRTC AEC3), every chunk of mic audio has Luma's own voice taken out
    before listening, so allow_barge_in is safe on ordinary speakers: while Luma talks, only sound well above what's
    left of its echo can start a turn. Without it, keep allow_barge_in False unless there are headphones. A caller
    that opts in should dispatch callback work to a worker so this loop can capture an interruption during speech.
    on_pause, if given, is called at a short pause inside a long turn (where a listener says "mm-hm"); it must return quickly.
    on_barge_in, if given, is called the moment someone starts talking while Luma is talking (a friend goes quiet then).
    on_maybe_done(audio), if given, is called when they pause and the turn is held open for the rest: they may be done
    (a caller can start on the words so far). on_carried_on() is called if they then keep talking. Both must return quickly.
    """
    if not isinstance(allow_barge_in, bool):
        raise ValueError("Barge-in must be an explicit true or false value.")
    stop_event = stop_event or threading.Event()
    should_stop = should_stop or (lambda: False)
    if should_stop() or stop_event.is_set(): return
    from luma.audio import turn
    smart = turn.model() is not None  # Smart Turn: a short pause asks "is that the end?" instead of waiting out a long silence
    if not smart: turn.fetch_in_background()
    ending = turn.Ending()
    vad = _get_vad_iterator(turn.PAUSE_MS if smart else turn.PLAIN_MS)
    from luma.audio import echo
    aec = echo.canceller()
    q = queue.Queue(maxsize=32)
    utterance, pre = [], deque(maxlen=6)
    in_speech = False
    suppress_until = 0.0
    watch = None
    if on_pause is not None:
        from luma.audio.backchannel import PauseWatch
        watch = PauseWatch(rate=SAMPLE_RATE, chunk=_CHUNK)

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
            if aec is not None:
                chunk = aec.clean(chunk)  # Luma's own voice out, the room and the owner left
                if _speaking.is_set() and not in_speech and echo.level_db(chunk) < echo.TALK_OVER_FLOOR_DB:
                    pre.append(chunk)  # only what's left of Luma's echo: not someone talking over it
                    continue
            result = vad(torch.from_numpy(chunk.astype(np.float32) / 32768.0))
            if result and "start" in result:
                if _speaking.is_set() and on_barge_in is not None:
                    try: on_barge_in()
                    except Exception: pass
                if ending.holding is not None:
                    ending.resumed()  # they kept going after the pause: the same turn
                    if on_carried_on is not None:
                        try: on_carried_on()
                        except Exception: pass
                else:
                    in_speech = True
                    utterance = list(pre)
                    if watch is not None: watch.start()
            if in_speech: utterance.append(chunk)
            if in_speech and watch is not None and watch.feed(chunk) and not _speaking.is_set():
                try: on_pause()
                except Exception: pass  # a missed "mm-hm" never stops listening
            pre.append(chunk)
            ended = bool(result and "end" in result)
            too_long = len(utterance) >= int(30*SAMPLE_RATE/_CHUNK)
            if in_speech and ended and smart and not too_long:
                ended = ending.paused(np.concatenate(utterance))  # mid-thought ("call... um... my sister"): hold on for the rest
                if not ended and on_maybe_done is not None:
                    try: on_maybe_done(np.concatenate(utterance))
                    except Exception: pass  # a missed early start never stops listening
                # That's exactly when a friend says "mm-hm": they paused, they're not done, and they've been talking a while.
                if (not ended and watch is not None and on_pause is not None and not _speaking.is_set()
                        and len(utterance) * _CHUNK / SAMPLE_RATE >= turn.MMHM_AFTER_S and watch.clock() - watch.last >= watch.gap):
                    watch.last = watch.clock()
                    try: on_pause()
                    except Exception: pass
            if in_speech and ending.timed_out():
                ended = True
            if in_speech and (ended or too_long):
                ending.reset()
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
