"""Cancellable local voice turns. Capture requires an explicit owner opt-in."""
import json
import os
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
    from luma.audio import tts, vad
    event = cancel_event or agent.turn_cancel
    should_stop = lambda: event.is_set() or (not allow_muted and agent.muted)
    while not _speech_lock.acquire(timeout=.05):
        if should_stop(): return False
    try:
        if should_stop(): return False
        agent.speaking = True
        vad.set_speaking(True)
        return tts.speak(text, should_stop=should_stop)
    finally:
        vad.set_speaking(False)
        agent.speaking = False
        _speech_lock.release()


def ask_typed(text, agent=None, voice=False, cancel_event=None):
    agent = agent or get_agent()
    event = cancel_event or agent.new_turn()
    result = agent.chat(text, cancel_event=event)
    # Do not write private conversations to service logs.
    if getattr(agent, 'on_result', None): agent.on_result(result)
    else: display(result)
    if voice and not event.is_set():
        message = 'Please review the exact action details in your local controls.' if result.get('state') == 'pending' else result.get('text') or result.get('summary') or 'Your result is ready in Luma.'
        speak(message, agent, cancel_event=event)
    return result


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
