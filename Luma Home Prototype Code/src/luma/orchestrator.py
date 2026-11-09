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
        agent.speaking_since = time.monotonic()  # when Luma started talking: talking over it this early means it jumped in too soon
        vad.set_speaking(True)
        preferences = agent.voice_preferences
        if isinstance(text, str):
            return tts.speak(text, should_stop=should_stop, voice=preferences["voice"], speed=preferences["speed"])
        return tts.speak_stream(text, should_stop=should_stop, voice=preferences["voice"], speed=preferences["speed"])
    finally:
        vad.set_speaking(False)
        agent.speaking = False
        _speech_lock.release()


FILLER_AFTER = float(os.environ.get("LUMA_FILLER_AFTER_S", "1.2"))  # seconds of silence before Luma thinks out loud
FILLER_AGAIN = 3.0   # right after the last one, it waits longer: a friend doesn't say "hmm" before every answer
FILLER_GAP = 25.0    # seconds that count as "right after"


class SpeechStream:
    """Feed it the reply as the model writes it; Luma starts talking at the first sentence."""

    def __init__(self, agent, cancel_event, allow_muted=False, speaker=None):
        from luma.llm.streaming import SentenceBuffer
        self.agent, self.event, self.allow_muted = agent, cancel_event, allow_muted
        self.buffer = SentenceBuffer()
        self.phrases = queue.Queue()
        self.thread = None
        self.speaker = speaker or speak
        self._heard = self._closed = False
        self._timer = None

    def think_out_loud(self, said):
        """If the first words don't come soon (a slow brain, a look-up), say a short line so the quiet doesn't feel like
        Luma didn't hear: "Hmm, let me think.", "Let me check." Once a turn, and later when it just said one."""
        store = getattr(self.agent, "store", None)
        if not said or (store is not None and store.setting("thinking_out_loud", True) is False):
            return self
        recent = time.monotonic() - getattr(self.agent, "_filler_at", -FILLER_GAP * 2) < FILLER_GAP
        self._timer = threading.Timer(FILLER_AGAIN if recent else FILLER_AFTER, self._fill, args=(said,))
        self._timer.daemon = True
        self._timer.start()
        return self

    def _fill(self, said):
        if self.event.is_set() or self._heard or self._closed or getattr(self.agent, "speaking", False):
            return
        from luma.agent import language
        line = language.filler(said, seed=f"{said}|{time.monotonic():.0f}", avoid=(getattr(self.agent, "_filler_last", ""),))
        if not line:
            return
        self.agent._filler_at, self.agent._filler_last = time.monotonic(), line
        try:
            self.speaker(line, self.agent, cancel_event=self.event, allow_muted=self.allow_muted)
        except Exception:
            pass

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
        if delta:
            self._heard = True  # the answer is coming: no "hmm" now
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
        self._closed = True
        if self._timer is not None:
            self._timer.cancel()
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
    stream = SpeechStream(agent, event).think_out_loud(text) if voice else None
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
    from luma.audio import backchannel, echo, vad
    from luma.audio.stt import transcribe
    from luma.agent.conversation import interruption_intent
    from luma.agent import turntaking
    followup_until = 0.0
    transcribing = threading.Lock()
    heard = {"text": None}           # what they said that Luma's answering now
    barge = {"spoke_for": None}      # how long Luma had been talking when they started talking over it

    ahead = {"turn": 0, "text": None, "for": None, "done": None}  # the words so far, heard while a turn was held open

    def named_text(raw):
        """What they said, after Luma's name if they said it: (text, whether they named it)."""
        text = backchannel.clean(raw.strip())
        named = re.search(r'\b(?:luma|luna)\b', text, re.I) if text else None
        return ((text[named.end():].lstrip(' ,.:!?') or 'Hello') if named else text), bool(named)

    def maybe_done(audio):
        """They paused and the turn is held open in case there's more. Hear the words so far and start on a reply
        (Agent.think_ahead): if that's all they say, it's ready sooner. Off unless the owner turned it on."""
        if not agent.store.setting('early_start', False) or capture_blocked(agent) or agent.busy or agent.speaking:
            return
        ahead["turn"] += 1
        turn, done = ahead["turn"], threading.Event()
        ahead.update(text=None, done=done)
        ahead["for"] = turn

        def work():
            path = None
            try:
                if not transcribing.acquire(blocking=False): return
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp: path = tmp.name
                    vad._save_wav(audio, path)
                    text, named = named_text(transcribe(path))
                finally: transcribing.release()
                if turn != ahead["turn"] or not text: return  # they carried on while this was being heard
                ahead["text"] = (text, named)
                if (named or time.monotonic() < followup_until) and not interruption_intent(text):
                    agent.think_ahead(text)
            except Exception:
                pass
            finally:
                done.set()
                if path:
                    try: os.unlink(path)
                    except FileNotFoundError: pass
        threading.Thread(target=work, daemon=True).start()

    def carried_on():
        ahead["turn"] += 1  # what was heard so far isn't the whole turn
        ahead["text"] = None
        try: agent.forget_ahead()
        except Exception: pass

    def talked_over():
        # They started talking while Luma talks: go quiet now, like a friend, and remember how early it was.
        if agent.speaking:
            barge["spoke_for"] = time.monotonic() - (getattr(agent, "speaking_since", None) or time.monotonic())
            agent.interrupt()

    def received(path):
        def process():
            nonlocal followup_until
            try:
                if capture_blocked(agent) or stop_event.is_set(): return
                # A bounded single transcription worker avoids accumulating recordings.
                early = None
                if ahead["for"] == ahead["turn"] and ahead["done"] is not None:  # the turn ended on the words already heard
                    ahead["done"].wait(4)
                    early, ahead["for"] = ahead["text"], None
                if early:
                    text, named = early
                else:
                    if not transcribing.acquire(blocking=False): return
                    try: text, named = named_text(transcribe(path))  # Luma's own "mm-hm" isn't part of what they said
                    finally: transcribing.release()
                if not text or capture_blocked(agent) or stop_event.is_set(): return
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
                spoke_for, barge["spoke_for"] = barge["spoke_for"], None
                if turntaking.cut_them_off(spoke_for, heard["text"], text):
                    # Luma jumped in before they were done: say sorry while it thinks, then answer the whole thought.
                    text = turntaking.together(heard["text"], text)
                    threading.Thread(target=speak, args=(turntaking.sorry(text), agent), kwargs={"cancel_event": event}, daemon=True).start()
                heard["text"] = text
                try:  # say the reply the way they said it: gentle when they're hurting, lighter when they're laughing
                    from luma.audio import feel
                    feel.set_from(text) if agent.store.setting('match_mood', True) is not False else feel.reset()
                except Exception:
                    pass
                ask_typed(text, agent, voice=True, cancel_event=event)
                followup_until = time.monotonic() + 45
            except Exception as error:
                if getattr(agent, 'on_result', None): agent.on_result({'text':'Voice turn paused: ' + str(error)[:250]})
            finally:
                try: os.unlink(path)
                except FileNotFoundError: pass
        threading.Thread(target=process, daemon=True).start()

    def listening():
        # In a conversation with Luma, a long turn gets a soft "mm-hm" at its pauses. Never to people just talking in the room.
        if (time.monotonic() < followup_until and agent.store.setting('backchannels', True) and not agent.speaking and not agent.busy
                and not capture_blocked(agent)):
            backchannel.say_softly((agent.voice_preferences or {}).get('voice', 'luma'))

    while not stop_event.is_set():
        agent.device.set_indicator(muted=capture_blocked(agent))
        if capture_blocked(agent):
            stop_event.wait(.1)
            continue
        try:
            # Talking over Luma works when its mic can't hear its own voice: headphones, a mic that cancels echo, or Luma's own
            # echo canceller (WebRTC AEC3). The owner's choice wins.
            chosen = agent.store.setting('barge_in', None)
            barge_in = chosen if isinstance(chosen, bool) else (backchannel.safe_to_talk_over(*backchannel.device_names()) or echo.ready())
            vad.start_listening(received, stop_event,
                                should_stop=lambda: capture_blocked(agent) or agent.store.setting('barge_in', None) != chosen,
                                allow_barge_in=barge_in, on_pause=listening, on_barge_in=talked_over if barge_in else None,
                                on_maybe_done=maybe_done, on_carried_on=carried_on)
        except Exception as error:
            agent.set_muted(True)
            if getattr(agent, 'on_result', None): agent.on_result({'text':'Microphone stopped: ' + str(error)[:250]})
