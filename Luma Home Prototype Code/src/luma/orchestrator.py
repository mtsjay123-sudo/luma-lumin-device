"""Agent voice orchestration. Microphone access requires explicit local opt-in."""
import json
import os
import re
import tempfile
import threading
import time

_default_agent = None


def get_agent():
    global _default_agent
    if _default_agent is None:
        from luma.agent.runtime import Agent
        _default_agent = Agent()
    return _default_agent


def display(result):
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)


def speak(text, agent):
    if agent.muted: return
    from luma.audio import io, tts, vad
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f: path = f.name
    agent.speaking = True
    vad.set_speaking(True)
    try:
        tts.synthesize(text, path)
        if not agent.muted: io.play(path, should_stop=lambda: agent.muted)
    finally:
        vad.set_speaking(False)
        agent.speaking = False
        try: os.unlink(path)
        except FileNotFoundError: pass


def ask_typed(text, agent=None, voice=False):
    agent = agent or get_agent()
    result = agent.chat(text)
    display(result)
    if getattr(agent, "on_result", None): agent.on_result(result)
    if voice:
        message = "Please review the exact action details and confirm using your local controls." if result.get("state") == "pending" else result.get("text", result.get("summary", "Your local result is ready."))
        speak(message, agent)
    return result


def reset():
    get_agent().history.clear()


def ask_voice(agent=None):
    agent = agent or get_agent()
    if agent.muted: raise ValueError("Enable the microphone locally before voice capture.")
    from luma.audio.io import record_push_to_talk
    from luma.audio.stt import transcribe
    path = record_push_to_talk(should_stop=lambda: agent.muted)
    if not path: return
    try:
        text = transcribe(path)
        if text and not agent.muted: return ask_typed(text, agent, voice=True)
    finally:
        try: os.unlink(path)
        except FileNotFoundError: pass


def start_hands_free(agent=None, stop_event=None, ambient=False):
    agent = agent or get_agent()
    stop_event = stop_event or threading.Event()
    from luma.audio import vad
    from luma.audio.stt import transcribe
    followup_until = 0.0

    def received(path):
        nonlocal followup_until
        try:
            if agent.muted: return
            text = transcribe(path).strip()
            if not text or agent.muted: return
            named = re.search(r"\b(?:luma|luna)\b", text, re.I)
            addressed = bool(named) or time.monotonic() < followup_until
            # Experimental heuristic, not diarization or a trained addressee model.
            if ambient and re.match(r"(?:remember |recall |remind me |search |text \+|every day at )", text, re.I): addressed = True
            if not addressed: return
            if named: text = text[named.end():].lstrip(" ,.:!?") or "Hello"
            with agent.lock:
                if agent.muted: return
                ask_typed(text, agent, voice=True)
                followup_until = time.monotonic() + 45
        except Exception as e:
            print("Voice turn failed: " + str(e), flush=True)
        finally:
            try: os.unlink(path)
            except FileNotFoundError: pass

    while not stop_event.is_set():
        if agent.muted:
            stop_event.wait(0.2)
            continue
        try:
            vad.start_listening(received, stop_event, should_stop=lambda: agent.muted)
        except Exception as e:
            agent.set_muted(True)
            print("Microphone stopped: " + str(e), flush=True)
