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
_inference_lock = threading.RLock()


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


def plan(messages, memories, tools, mode, profile=None):
    """Generate a constrained proposal; execution remains in the runtime."""
    profile = normalize_profile(profile)
    now = datetime.now(ZoneInfo(os.environ.get("LUMA_TIMEZONE", "America/New_York"))).isoformat()
    prompt = build_plan_prompt(memories, tools, mode, profile, now)
    max_tokens = {"brief": 224, "balanced": 384, "detailed": 640}[profile["verbosity"]]
    with _inference_lock:
        model = _load_model()
        count = lambda text: len(model.tokenize(text.encode("utf-8"), add_bos=False))
        recent = fit_history(messages, count, LLAMA_CONTEXT_SIZE - count(prompt) - max_tokens - 160)
        result = model.create_chat_completion(
            messages=[{"role": "system", "content": prompt}] + recent,
            response_format={"type": "json_object", "schema": proposal_schema(tools)},
            max_tokens=max_tokens, temperature=0.45, top_p=0.9, repeat_penalty=1.08,
        )
    try:
        result = json.loads(result["choices"][0]["message"]["content"])
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


def _load_model():
    global _llm
    if _llm is not None:
        return _llm
    try:
        from llama_cpp import Llama
    except ImportError as e:
        raise RuntimeError("llama-cpp-python not installed — run scripts/setup_mac.sh") from e

    if not LLAMA_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {LLAMA_MODEL_PATH}. Check LUMA_MODEL_PATH or run scripts/download_models.sh for the original model."
        )

    with _silence_stderr():
        _llm = Llama(
            model_path=str(LLAMA_MODEL_PATH),
            n_ctx=LLAMA_CONTEXT_SIZE,
            n_gpu_layers=LLAMA_GPU_LAYERS,
            n_threads=LLAMA_THREADS,
            n_batch=min(LLAMA_BATCH_SIZE, LLAMA_CONTEXT_SIZE),
            chat_format=LLAMA_CHAT_FORMAT,
            verbose=False,
        )
    return _llm


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


def generate(messages: list[dict], max_tokens: int = 180, system_prompt: Optional[str] = None) -> str:
    """Send a chat-formatted message list to the LLM and return the reply text."""
    model = _load_model()

    full_messages = [{"role": "system", "content": system_prompt or SYSTEM_PROMPT}] + messages

    result = model.create_chat_completion(
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=0.65,
        mirostat_mode=2,
        mirostat_tau=3.5,
        mirostat_eta=0.1,
        repeat_penalty=1.8,
        stop=["<|eot_id|>", "<|end_of_text|>"],
    )
    raw = result["choices"][0]["message"]["content"].strip()
    cleaned = _strip_repetition(_sanitize(raw))
    # Ensure the response ends with terminal punctuation so TTS doesn't trail off
    if cleaned and not cleaned.endswith(('.', '!', '?')):
        cleaned += '.'
    return cleaned
