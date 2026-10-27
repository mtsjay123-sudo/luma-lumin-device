from __future__ import annotations

import os
import contextlib
import json
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from luma.config import (LLAMA_MODEL_PATH, LLAMA_CONTEXT_SIZE, LLAMA_GPU_LAYERS,
                         LLAMA_THREADS, LLAMA_BATCH_SIZE, LLAMA_CHAT_FORMAT)
from luma.llm.prompts import SYSTEM_PROMPT, build_plan_prompt, normalize_profile, proposal_schema

_llm = None
_llm_path = None
_override = None  # a bigger model, once it's downloaded and verified (see luma.llm.brain)
_inference_lock = threading.RLock()


def use_model_path(path):
    """Think with this model file from the next message on (None: the default one)."""
    global _override, _llm
    from luma.llm import worker
    if worker.enabled():
        worker.brain().use_model_path(path)
    with _inference_lock:
        _override = path
        if _llm is not None and _llm_path != (path or LLAMA_MODEL_PATH):
            _llm = None  # loaded fresh on the next call


class GenerationCancelled(Exception):
    """The owner interrupted this turn; a partial proposal must never execute."""


def _check_cancel(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise GenerationCancelled("Conversation interrupted.")


@contextlib.contextmanager
def _model_access(cancel_event=None):
    """A superseded request can leave the queue without waiting for another turn."""
    while not _inference_lock.acquire(timeout=0.05):
        _check_cancel(cancel_event)
    try:
        _check_cancel(cancel_event)
        yield
    finally:
        _inference_lock.release()


def _complete(model, cancel_event=None, on_delta=None, **kwargs):
    _check_cancel(cancel_event)
    if cancel_event is None and on_delta is None:
        return model.create_chat_completion(**kwargs)["choices"][0]["message"]["content"]
    # Closing the generator stops token generation. Native model loading/prompt
    # prefill must finish first; they cannot be safely killed from another thread.
    chunks = model.create_chat_completion(stream=True, **kwargs)
    text = []
    try:
        for chunk in chunks:
            _check_cancel(cancel_event)
            choices = chunk.get("choices", [])
            if choices:
                content = choices[0].get("delta", {}).get("content")
                if isinstance(content, str):
                    text.append(content)
                    if on_delta is not None:
                        on_delta(content)
        _check_cancel(cancel_event)
        return "".join(text)
    finally:
        close = getattr(chunks, "close", None)
        if close is not None:
            close()


def fit_history(messages, token_count, budget):
    """Keep whole recent turns; never silently truncate a current action request."""
    recent, used = [], 0
    for message in reversed(messages):
        if message.get("role") not in {"user", "assistant"} or not isinstance(message.get("content"), str):
            continue
        cost = token_count(message["content"]) + 24
        if used + cost > budget:
            if not recent:
                raise ValueError("This request is too long for the local model. Please shorten it; no action was taken.")
            break
        recent.insert(0, {"role": message["role"], "content": message["content"]})
        used += cost
    while recent and recent[0]["role"] != "user":
        recent.pop(0)
    return recent


def plan(messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None):
    """Generate a constrained proposal; execution remains in the runtime. Runs in the brain's own process when Luma is serving."""
    from luma.llm import worker
    if worker.enabled():
        return worker.brain().call("plan", {"messages": messages, "memories": memories, "tools": tools, "mode": mode, "profile": profile},
                                   cancel_event=cancel_event, on_text=on_text)
    return _plan_here(messages, memories, tools, mode, profile, cancel_event, on_text)


def _plan_here(messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None):
    profile = normalize_profile(profile)
    now = datetime.now(ZoneInfo(os.environ.get("LUMA_TIMEZONE", "America/New_York"))).isoformat()
    prompt = build_plan_prompt(memories, tools, mode, profile, now)
    max_tokens = {"brief": 224, "balanced": 384, "detailed": 640}[profile["verbosity"]]
    if any({"slides", "sections", "cards"} & set(spec.get("fields", {}).values()) for spec in tools.values()):
        max_tokens = 1800  # a whole deck, document or set of cards in one constrained answer
    with _model_access(cancel_event):
        model = _load_model()
        _check_cancel(cancel_event)
        count = lambda text: len(model.tokenize(text.encode("utf-8"), add_bos=False))
        recent = fit_history(messages, count, LLAMA_CONTEXT_SIZE - count(prompt) - max_tokens - 160)
        from luma.llm.streaming import ReplyTextStream
        stream = ReplyTextStream(on_text) if on_text is not None else None
        raw = _complete(model, cancel_event, on_delta=stream.feed if stream else None,
            messages=[{"role": "system", "content": prompt}] + recent,
            response_format={"type": "json_object", "schema": proposal_schema(tools)},
            max_tokens=max_tokens, temperature=0.45, top_p=0.9, repeat_penalty=1.08,
        )
    try:
        _check_cancel(cancel_event)
        result = json.loads(raw)
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        raise ValueError("The local model returned an invalid proposal. No action was taken.") from e
    if not isinstance(result, dict):
        raise ValueError("The model proposal must be a JSON object.")
    return result


@contextlib.contextmanager
def _silence_stderr():
    """Suppress C-level stderr (llama.cpp prints warnings there)."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old = os.dup(2)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old, 2)
        os.close(old)


def _gpu_layers():
    """Read when the model loads: the brain process may have been told to stay off the graphics chip."""
    try:
        return int(os.environ.get("LUMA_GPU_LAYERS", LLAMA_GPU_LAYERS))
    except ValueError:
        return LLAMA_GPU_LAYERS


def _load_model():
    global _llm, _llm_path
    if _llm is not None:
        return _llm
    model_path = _override or LLAMA_MODEL_PATH
    try:
        from llama_cpp import Llama
    except ImportError as e:
        raise RuntimeError("llama-cpp-python not installed — run scripts/setup_mac.sh") from e

    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. Check LUMA_MODEL_PATH or run scripts/download_models.sh for the original model."
        )

    def make(layers):
        with _silence_stderr():
            return Llama(
                model_path=str(model_path),
                n_ctx=LLAMA_CONTEXT_SIZE,
                n_gpu_layers=layers,
                n_threads=LLAMA_THREADS,
                n_batch=min(LLAMA_BATCH_SIZE, LLAMA_CONTEXT_SIZE),
                chat_format=LLAMA_CHAT_FORMAT,
                verbose=False,
            )

    global note
    layers = _gpu_layers()
    _llm = make(layers)
    if layers != 0 and not _sane(_llm):
        # Some graphics chips (a virtual Mac's, an old driver) run the model but return nonsense. The processor is
        # slower but right: think there from now on in this process.
        close = getattr(_llm, "close", None)
        if close:
            try:
                close()
            except Exception:
                pass
        _llm = None
        os.environ["LUMA_GPU_LAYERS"] = "0"
        _llm = make(0)
        note = "My brain came out garbled on the graphics chip, so I'm thinking on the processor instead. A bit slower, but right."
    _llm_path = model_path
    return _llm


note = ""  # what the brain had to change about itself, in plain words


def garbled_seen():
    """A reply came out as symbols after the start-up check passed (a graphics chip that goes bad partway): think on the processor from the next turn on."""
    global _llm, note
    from luma.llm import worker
    if worker.enabled():
        worker.brain().to_processor()
        return
    if os.environ.get("LUMA_GPU_LAYERS") == "0":
        return
    os.environ["LUMA_GPU_LAYERS"] = "0"
    with _inference_lock:
        _llm = None  # reloaded on the processor next time
    note = "My brain came out garbled on the graphics chip, so I'm thinking on the processor instead. A bit slower, but right."


def garbled(text):
    """Symbols where words should be ('+A57', '#8++&B+,#$C8'): a model running wrong, not one that's just terse."""
    compact = "".join((text or "").split())
    if len(compact) < 3:
        return False
    return sum(ch.isalpha() or ord(ch) > 0x2000 for ch in compact) / len(compact) < 0.5  # emoji are fine: "😭😭" is an answer


def _sane(model):
    """One tiny, fixed question right after loading: real words back, or this model is running wrong here."""
    try:
        reply = model.create_chat_completion(messages=[{"role": "user", "content": "Say hello in a few words."}],
                                             max_tokens=12, temperature=0)["choices"][0]["message"]["content"]
    except Exception:
        return True  # it couldn't answer at all: that's handled where it happens, not mistaken for nonsense
    if not isinstance(reply, str):
        return True
    import re
    return not garbled(re.sub(r"</?think>", "", reply))


def _strip_repetition(text: str) -> str:
    """Truncate at the first detected repetition. Then trim to the last clean sentence end."""
    import re
    words = text.split()
    n = len(words)
    if n < 2:
        return text

    norm = [w.lower().strip(" .,!?;:\"'") for w in words]
    earliest_cut = None

    def consider(cut_index: int) -> None:
        nonlocal earliest_cut
        if earliest_cut is None or cut_index < earliest_cut:
            earliest_cut = cut_index

    # Single word repeated 2+ times in a row: "that that", "inna inna"
    for i in range(n - 1):
        if norm[i] and norm[i] == norm[i + 1]:
            consider(i + 1)
            break

    # 2-word phrase repeated 2+ times: "tend to tend to"
    for i in range(n - 3):
        phrase = norm[i : i + 2]
        if phrase[0] == "" and phrase[1] == "":
            continue
        if norm[i + 2 : i + 4] == phrase:
            consider(i + 2)
            break

    # 3+ word phrase repeated 2+ times
    for span in range(3, n // 2 + 1):
        for i in range(n - span * 2 + 1):
            if norm[i : i + span] == norm[i + span : i + span * 2]:
                consider(i + span)
                break

    if earliest_cut is not None:
        truncated = " ".join(words[:earliest_cut]).strip(" .,")
        # trim to the last complete sentence so the audio doesn't end mid-thought
        # Find the last sentence-ending punctuation and truncate there
        last_end = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
        if last_end > 10:
            return truncated[:last_end + 1].strip()
        return truncated

    return text


def _sanitize(text: str) -> str:
    """Remove non-ASCII characters and collapse whitespace."""
    cleaned = "".join(c if ord(c) < 128 else " " for c in text)
    return " ".join(cleaned.split())


def rewrite(prompt: str, max_tokens: int = 90, cancel_event=None) -> str:
    """A quick, short, low-temperature pass (no persona, no tools, no history): turning a messy message into a clear one."""
    from luma.llm import worker
    if worker.enabled():
        return worker.brain().call("rewrite", {"prompt": prompt, "max_tokens": max_tokens}, cancel_event=cancel_event)
    return _rewrite_here(prompt, max_tokens, cancel_event)


def _rewrite_here(prompt: str, max_tokens: int = 90, cancel_event=None, on_text=None) -> str:
    with _model_access(cancel_event):
        model = _load_model()
        return _complete(model, cancel_event, messages=[{"role": "system", "content": "You rewrite messages into clear instructions. Answer with the rewrite only."},
                                                        {"role": "user", "content": prompt}],
                         max_tokens=max_tokens, temperature=0.1, top_p=0.9).strip()


def generate(messages: list[dict], max_tokens: int = 180, system_prompt: Optional[str] = None, cancel_event=None) -> str:
    """Send a chat-formatted message list to the LLM and return the reply text."""
    from luma.llm import worker
    if worker.enabled():
        return worker.brain().call("generate", {"messages": messages, "max_tokens": max_tokens, "system_prompt": system_prompt}, cancel_event=cancel_event)
    return _generate_here(messages, max_tokens, system_prompt, cancel_event)


def _generate_here(messages: list[dict], max_tokens: int = 180, system_prompt: Optional[str] = None, cancel_event=None, on_text=None) -> str:
    full_messages = [{"role": "system", "content": system_prompt or SYSTEM_PROMPT}] + messages
    with _model_access(cancel_event):
        model = _load_model()
        raw = _complete(model, cancel_event,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=0.65,
            mirostat_mode=2,
            mirostat_tau=3.5,
            mirostat_eta=0.1,
            repeat_penalty=1.8,
            stop=["<|eot_id|>", "<|end_of_text|>"],
        ).strip()
    cleaned = _strip_repetition(_sanitize(raw))
    # Ensure the response ends with terminal punctuation so TTS doesn't trail off
    if cleaned and not cleaned.endswith(('.', '!', '?')):
        cleaned += '.'
    return cleaned
