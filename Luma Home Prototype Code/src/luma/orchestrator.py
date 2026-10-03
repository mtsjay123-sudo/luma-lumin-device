"""Cancellable local voice turns. Capture requires an explicit owner opt-in."""
import json
import os
import queue
import re
import threading
import time

_default_agent = None
_speech_lock = threading.Lock()


def get_agent():
    global _default_agent
    if _default_agent is None:
        from luma.agent.runtime import Agent
        _default_agent = Agent()
    return _default_agent


def display(result):
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)


def capture_blocked(agent):
    return agent.muted or not agent.device.capture_allowed()


def speak(text, agent, cancel_event=None, allow_muted=False):
    """Speak a whole reply, or an iterable of phrases as they arrive."""
    from luma.audio import tts, vad
    event = cancel_event or agent.turn_cancel
    should_stop = lambda: event.is_set() or (not allow_muted and agent.muted)
    while not _speech_lock.acquire(timeout=.05):
        if should_stop(): return False
    try:
        if should_stop(): return False
        agent.speaking = True
        vad.set_speaking(True)
        preferences = agent.voice_preferences
        if isinstance(text, str):
            return tts.speak(text, should_stop=should_stop, voice=preferences["voice"], speed=preferences["speed"])
        return tts.speak_stream(text, should_stop=should_stop, voice=preferences["voice"], speed=preferences["speed"])
    finally:
        vad.set_speaking(False)
        agent.speaking = False
        _speech_lock.release()


class SpeechStream:
    """Feed it the reply as the model writes it; Luma starts talking at the first sentence."""

    def __init__(self, agent, cancel_event, allow_muted=False, speaker=None):
        from luma.llm.streaming import SentenceBuffer
        self.agent, self.event, self.allow_muted = agent, cancel_event, allow_muted
        self.buffer = SentenceBuffer()
        self.phrases = queue.Queue()
        self.thread = None
        self.speaker = speaker or speak

    @property
    def started(self):
        return self.thread is not None

    def _iter(self):
        while not self.event.is_set():
            try: phrase = self.phrases.get(timeout=.05)
            except queue.Empty: continue
            if phrase is None: return
            yield phrase

    def feed(self, delta):
        for phrase in self.buffer.feed(delta):
            self._push(phrase)

    def _push(self, phrase):
        if self.thread is None:
            phrases = self._iter()
            self.thread = threading.Thread(target=self._run, args=(phrases,), daemon=True)
            self.thread.start()
        self.phrases.put(phrase)

    def _run(self, phrases):
        try: self.speaker(phrases, self.agent, cancel_event=self.event, allow_muted=self.allow_muted)
        except Exception as error:
            if getattr(self.agent, 'on_result', None): self.agent.on_result({'text': 'Voice could not play: ' + str(error)[:250]})

    def finish(self, wait=True):
        """Speak whatever is left. Returns True if anything was spoken by streaming."""
        if self.thread is None:
            return False
        for phrase in self.buffer.flush():
            self.phrases.put(phrase)
        self.phrases.put(None)
        if wait: self.thread.join()
        return True


def ask_typed(text, agent=None, voice=False, cancel_event=None):
    agent = agent or get_agent()
    event = cancel_event or agent.new_turn()
    stream = SpeechStream(agent, event) if voice else None
    result = agent.chat(text, cancel_event=event, on_text=stream.feed if stream else None)
    # Do not write private conversations to service logs.
    if getattr(agent, 'on_result', None): agent.on_result(result)
    else: display(result)
    if voice and not event.is_set() and not stream.finish():
        speak(spoken_reply(result), agent, cancel_event=event)
    return result


def spoken_reply(result):
    """What Luma says out loud for a finished turn that wasn't already streamed."""
    return result.get('text') or result.get('summary') or 'Your result is ready in Luma.'


def reset():
    agent = get_agent()
    agent.interrupt()
    with agent.lock:
        agent.history.clear()
        agent.last_task = agent.last_draft = None
        agent.last_reply = ''


def ask_voice(agent=None):
    agent = agent or get_agent()
    if capture_blocked(agent): raise ValueError('Enable the microphone and release any physical privacy cutoff before voice capture.')
    from luma.audio.io import record_push_to_talk
    from luma.audio.stt import transcribe
    path = record_push_to_talk(should_stop=lambda: capture_blocked(agent))
    if not path: return
    try:
        text = transcribe(path)
        if text and not capture_blocked(agent): return ask_typed(text, agent, voice=True)
    finally:
        try: os.unlink(path)
        except FileNotFoundError: pass


def start_hands_free(agent=None, stop_event=None, ambient=False):
    agent = agent or get_agent()
    stop_event = stop_event or threading.Event()
    from luma.audio import vad
    from luma.audio.stt import transcribe
    from luma.agent.conversation import interruption_intent
    followup_until = 0.0
    transcribing = threading.Lock()

    def received(path):
        def process():
            nonlocal followup_until
            try:
                if capture_blocked(agent) or stop_event.is_set(): return
                # A bounded single transcription worker avoids accumulating recordings.
                if not transcribing.acquire(blocking=False): return
                try: text = transcribe(path).strip()
                finally: transcribing.release()
                if not text or capture_blocked(agent) or stop_event.is_set(): return
                named = re.search(r'\b(?:luma|luna)\b', text, re.I)
                if named: text = text[named.end():].lstrip(' ,.:!?') or 'Hello'
                intent = interruption_intent(text)
                addressed = bool(named) or time.monotonic() < followup_until
                if intent and (agent.busy or agent.speaking): addressed = True
                if ambient and re.match(r'(?:remember |recall |remind me |search |text \+|every day at )', text, re.I): addressed = True
                if not addressed: return
                if intent == 'stop':
                    result = agent.interrupt()
                    if getattr(agent, 'on_result', None): agent.on_result(result)
                    followup_until = time.monotonic() + 45
                    return
                event = agent.new_turn()
                followup_until = time.monotonic() + 45
                ask_typed(text, agent, voice=True, cancel_event=event)
                followup_until = time.monotonic() + 45
            except Exception as error:
                if getattr(agent, 'on_result', None): agent.on_result({'text':'Voice turn paused: ' + str(error)[:250]})
            finally:
                try: os.unlink(path)
                except FileNotFoundError: pass
        threading.Thread(target=process, daemon=True).start()

    while not stop_event.is_set():
        agent.device.set_indicator(muted=capture_blocked(agent))
        if capture_blocked(agent):
            stop_event.wait(.1)
            continue
        try:
            barge_in = agent.store.setting('barge_in', False)
            vad.start_listening(received, stop_event,
                                should_stop=lambda: capture_blocked(agent) or agent.store.setting('barge_in',False) != barge_in,
                                allow_barge_in=barge_in)
        except Exception as error:
            agent.set_muted(True)
            if getattr(agent, 'on_result', None): agent.on_result({'text':'Microphone stopped: ' + str(error)[:250]})
