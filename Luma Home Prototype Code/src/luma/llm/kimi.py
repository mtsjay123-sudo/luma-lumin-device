"""Luma's other cloud brain: Kimi K3.1 Pro (Moonshot AI), with the owner's own Moonshot API key.

Kimi K3.1 Pro is an open-weight model (about 2.8 trillion parameters, 104 billion active), far too big
for any Mac, so it runs on Moonshot's servers. Off unless the owner picks it. Like the Claude brain,
only the conversation and Luma's instructions go out; approvals, rules, tools and everything Luma does
stay on this computer, and the answer comes back in the same JSON shape the local model uses.

Moonshot's API speaks the OpenAI chat format, so this needs only the standard library.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from luma.llm.prompts import build_plan_prompt, normalize_profile

MODELS = {"kimi-k3.1-pro": "Kimi K3.1 Pro (open model, Moonshot)", "kimi-k3.1-pro-highspeed": "Kimi K3.1 Pro Highspeed (faster)"}
DEFAULT_MODEL = "kimi-k3.1-pro"
KEYS_URL = "https://platform.kimi.ai/"


class AuthenticationError(Exception):
    """Moonshot didn't accept the key."""


class RateLimitError(Exception):
    """Busy, or out of credit."""


class ConnectionFailed(Exception):
    """Couldn't reach Moonshot."""


def _base():
    return (os.environ.get("LUMA_KIMI_BASE") or "https://api.moonshot.ai/v1").rstrip("/")


def _request(key, path, body=None, timeout=120):
    req = urllib.request.Request(_base() + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                                 method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:300]
        if error.code in (401, 403):
            raise AuthenticationError("Moonshot didn't accept that key.") from error
        if error.code == 429:
            raise RateLimitError("Moonshot is busy or the account is out of credit.") from error
        raise RuntimeError(f"Moonshot said {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ConnectionFailed("Couldn't reach Moonshot.") from error


def check_key(key, model=DEFAULT_MODEL):
    """Does this key work? A free lookup of the model list, not a paid request."""
    if not key or not str(key).startswith("sk-") or str(key).startswith("sk-ant-"):
        raise ValueError("That doesn't look like a Moonshot API key. It starts with sk- (get one at platform.kimi.ai).")
    try:
        _request(key, "/models", timeout=30)
    except AuthenticationError as error:
        raise ValueError("Moonshot didn't accept that key. Copy it again from platform.kimi.ai.") from error
    except ConnectionFailed as error:
        raise ValueError("Couldn't reach Moonshot. Is this computer online?") from error


def _history(messages, limit=40):
    recent = [{"role": m["role"], "content": m["content"]} for m in messages
              if m.get("role") in {"user", "assistant"} and isinstance(m.get("content"), str) and m["content"].strip()][-limit:]
    while recent and recent[0]["role"] != "user":
        recent.pop(0)
    return recent


def _content(data):
    try:
        text = data["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError, TypeError, AttributeError) as error:
        raise ValueError("The cloud brain sent back an answer I couldn't read.") from error
    if not text.strip():
        raise ValueError("The cloud brain sent back an empty answer.")
    return text


def _json_object(text):
    """The one JSON object in the answer, even if it came wrapped in a code fence."""
    text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip())
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("The cloud brain returned something that wasn't a proposal. No action was taken.")
        try:
            result = json.loads(text[start:end + 1])
        except json.JSONDecodeError as error:
            raise ValueError("The cloud brain returned something that wasn't a proposal. No action was taken.") from error
    if not isinstance(result, dict):
        raise ValueError("The cloud brain's answer must be a JSON object.")
    return result


def plan(key, messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None, model=DEFAULT_MODEL):
    """Same contract as luma.llm.inference.plan: a dict that's either a reply or one tool proposal."""
    from luma.llm.inference import GenerationCancelled
    profile = normalize_profile(profile)
    now = datetime.now(ZoneInfo(os.environ.get("LUMA_TIMEZONE", "America/New_York"))).isoformat()
    recent = _history(messages)
    if not recent:
        raise ValueError("Nothing to answer yet.")
    body = {"model": model if model in MODELS else DEFAULT_MODEL, "max_tokens": 8192,
            "messages": [{"role": "system", "content": build_plan_prompt(memories, tools, mode, profile, now)}] + recent,
            "response_format": {"type": "json_object"}}
    if cancel_event is not None and cancel_event.is_set():
        raise GenerationCancelled("Conversation interrupted.")
    result = _json_object(_content(_request(key, "/chat/completions", body)))
    if cancel_event is not None and cancel_event.is_set():
        raise GenerationCancelled("Conversation interrupted.")
    if on_text is not None and result.get("type") == "reply" and isinstance(result.get("text"), str):
        on_text(result["text"])  # the whole reply at once, so the voice can start
    return result


def rewrite(key, prompt, max_tokens=300, model=DEFAULT_MODEL):
    """The quick 'what do they mean' pass, short and cheap."""
    body = {"model": model if model in MODELS else DEFAULT_MODEL, "max_tokens": max(max_tokens, 512),
            "messages": [{"role": "system", "content": "You rewrite messages into clear instructions. Answer with the rewrite only."},
                         {"role": "user", "content": prompt}]}
    return _content(_request(key, "/chat/completions", body, timeout=60)).strip()
