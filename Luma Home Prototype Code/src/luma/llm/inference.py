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
    """Truncate output at the point where a phrase (4+ words) repeats."""
    words = text.split()
    for span in range(4, len(words) // 2 + 1):
        for i in range(len(words) - span * 2 + 1):
            phrase = words[i : i + span]
            rest = words[i + span :]
            if phrase == rest[: span]:
                return " ".join(words[:i + span]).strip(" .,")
    return text


def generate(messages: list[dict], max_tokens: int = 400, system_prompt: Optional[str] = None) -> str:
    """Send a chat-formatted message list to the LLM and return the reply text."""
    model = _load_model()

    full_messages = [{"role": "system", "content": system_prompt or SYSTEM_PROMPT}] + messages

    result = model.create_chat_completion(
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=0.75,
        mirostat_mode=2,   # adaptive sampling — prevents runaway repetition
        mirostat_tau=4.0,
        mirostat_eta=0.1,
        repeat_penalty=1.4,
        stop=["<|eot_id|>", "<|end_of_text|>"],
    )
    raw = result["choices"][0]["message"]["content"].strip()
    return _strip_repetition(raw)
