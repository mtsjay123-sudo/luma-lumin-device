from __future__ import annotations

import os
import contextlib
from typing import Optional
from luma.config import LLAMA_MODEL_PATH
from luma.llm.prompts import SYSTEM_PROMPT

_llm = None


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
            f"Model not found at {LLAMA_MODEL_PATH}. Run scripts/download_models.sh first."
        )

    with _silence_stderr():
        _llm = Llama(
            model_path=str(LLAMA_MODEL_PATH),
            n_ctx=16384,
            n_threads=8,
            n_batch=512,
            verbose=False,
        )
    return _llm


def _strip_repetition(text: str) -> str:
    """Truncate output at the first detected repetition loop.

    Catches:
      - any single word repeated 3+ times in a row (e.g. "what's what's what's")
      - any 2-word phrase repeated 3+ times in a row (e.g. "you know you know you know")
      - any phrase of 3+ words repeated 2+ times in a row
    Earliest detected loop wins so we cut as soon as possible.
    """
    words = text.split()
    n = len(words)
    if n < 2:
        return text

    norm = [w.lower().strip(" .,!?;:\"'") for w in words]

    earliest_cut = None  # index (exclusive) to truncate at

    def consider(cut_index: int) -> None:
        nonlocal earliest_cut
        if earliest_cut is None or cut_index < earliest_cut:
            earliest_cut = cut_index

    # Single-word repeats: need 3+ in a row -> keep only the first occurrence
    for i in range(n - 2):
        if norm[i] and norm[i] == norm[i + 1] == norm[i + 2]:
            consider(i + 1)
            break

    # 2-word phrase repeats: need 3+ in a row -> keep only the first occurrence
    for i in range(n - 5):
        phrase = norm[i : i + 2]
        if phrase[0] == "" and phrase[1] == "":
            continue
        if norm[i + 2 : i + 4] == phrase and norm[i + 4 : i + 6] == phrase:
            consider(i + 2)
            break

    # 3+ word phrase repeats: need 2+ in a row -> keep the first occurrence
    for span in range(3, n // 2 + 1):
        for i in range(n - span * 2 + 1):
            phrase = norm[i : i + span]
            if phrase == norm[i + span : i + span * 2]:
                consider(i + span)
                break
        if earliest_cut is not None and earliest_cut <= span:
            # already have a cut that's at or before this span's earliest possible boundary
            pass

    if earliest_cut is None:
        return text
    return " ".join(words[:earliest_cut]).strip(" .,")


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
        repeat_penalty=1.5,
        stop=["<|eot_id|>", "<|end_of_text|>"],
    )
    raw = result["choices"][0]["message"]["content"].strip()
    return _strip_repetition(_sanitize(raw))
