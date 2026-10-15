"""Luma's optional cloud brain: Claude, with the owner's own Anthropic API key.

Off unless the owner turns it on. Only the conversation and Luma's instructions go
to Anthropic; approvals, rules, tools and everything Luma does still run on this
computer, and the answer is held to the same JSON shape the local model uses, so
nothing downstream changes.
"""
from __future__ import annotations

import copy
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from luma.llm.prompts import build_plan_prompt, normalize_profile, proposal_schema

MODELS = {"claude-opus-5-5": "Claude Opus 5.5 (smartest)", "claude-sonnet-5-5": "Claude Sonnet 5.5 (faster, cheaper)"}
DEFAULT_MODEL = "claude-opus-5-5"
# Keys the structured-output schema can't take; the runtime validates the result anyway.
_UNSUPPORTED = {"minItems", "maxItems", "minLength", "maxLength", "minimum", "maximum", "multipleOf", "pattern", "exclusiveMinimum", "exclusiveMaximum"}


class CloudRefused(Exception):
    """Claude declined the request (stop_reason "refusal")."""


def _client(key):
    import anthropic
    return anthropic.Anthropic(api_key=key, timeout=120.0, max_retries=2)


def check_key(key, model=DEFAULT_MODEL):
    """Does this key work? A free lookup of the model, not a paid request."""
    import anthropic
    if not key or not str(key).startswith("sk-ant-"):
        raise ValueError("That doesn't look like an Anthropic API key. It starts with sk-ant-.")
    try:
        _client(key).models.retrieve(model)
    except anthropic.AuthenticationError as error:
        raise ValueError("Anthropic didn't accept that key. Copy it again from console.anthropic.com.") from error
    except anthropic.PermissionDeniedError as error:
        raise ValueError("That key can't use this model. Check its workspace in the Anthropic console.") from error
    except anthropic.APIConnectionError as error:
        raise ValueError("Couldn't reach Anthropic. Is this computer online?") from error


def _schema(schema):
    """Luma's grammar, in the form structured outputs accept: anyOf instead of oneOf, no length limits."""
    schema = copy.deepcopy(schema)

    def clean(node):
        if isinstance(node, dict):
            if "oneOf" in node:
                node["anyOf"] = node.pop("oneOf")
            for key in list(node):
                if key in _UNSUPPORTED:
                    node.pop(key)
                else:
                    clean(node[key])
        elif isinstance(node, list):
            for item in node:
                clean(item)
        return node

    return clean(schema)


def _history(messages, limit=40):
    recent = [{"role": m["role"], "content": m["content"]} for m in messages
              if m.get("role") in {"user", "assistant"} and isinstance(m.get("content"), str) and m["content"].strip()][-limit:]
    while recent and recent[0]["role"] != "user":
        recent.pop(0)
    return recent


def _final_text(message):
    if message.stop_reason == "refusal":
        raise CloudRefused("Claude declined that one.")
    blocks = list(message.content)
    # After a server-side fallback, the answer is whatever came after the last switch.
    last_switch = max((i for i, b in enumerate(blocks) if b.type == "fallback"), default=-1)
    text = "".join(b.text for b in blocks[last_switch + 1:] if b.type == "text")
    if not text.strip():
        raise ValueError("The cloud brain sent back an empty answer.")
    return text


def plan(key, messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None, model=DEFAULT_MODEL):
    """Same contract as luma.llm.inference.plan: a dict that's either a reply or one tool proposal."""
    from luma.llm.inference import GenerationCancelled
    from luma.llm.streaming import ReplyTextStream
    profile = normalize_profile(profile)
    now = datetime.now(ZoneInfo(os.environ.get("LUMA_TIMEZONE", "America/New_York"))).isoformat()
    system = build_plan_prompt(memories, tools, mode, profile, now)
    recent = _history(messages)
    if not recent:
        raise ValueError("Nothing to answer yet.")
    stream_text = ReplyTextStream(on_text) if on_text is not None else None
    request = dict(
        model=model if model in MODELS else DEFAULT_MODEL,
        max_tokens=16000,
        system=system,
        messages=recent,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": _schema(proposal_schema(tools))}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # if a safety check declines, Anthropic retries on a model that can answer
    )
    with _client(key).beta.messages.stream(**request) as stream:
        for chunk in stream.text_stream:
            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelled("Conversation interrupted.")
            if stream_text is not None:
                stream_text.feed(chunk)
        message = stream.get_final_message()
    try:
        result = json.loads(_final_text(message))
    except json.JSONDecodeError as error:
        raise ValueError("The cloud brain returned something that wasn't a proposal. No action was taken.") from error
    if not isinstance(result, dict):
        raise ValueError("The cloud brain's answer must be a JSON object.")
    return result


def rewrite(key, prompt, max_tokens=300, model=DEFAULT_MODEL):
    """The quick 'what do they mean' pass, short and cheap."""
    message = _client(key).beta.messages.create(
        model=model if model in MODELS else DEFAULT_MODEL,
        max_tokens=max(max_tokens, 1024),
        system="You rewrite messages into clear instructions. Answer with the rewrite only.",
        messages=[{"role": "user", "content": prompt}],
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    return _final_text(message).strip()


def look(key, image_bytes, question=None, model=DEFAULT_MODEL):
    """Claude looks at the photo (only when the cloud brain is on): what's in it, and any text, read exactly."""
    import base64
    data = bytes(image_bytes)
    kind = "image/jpeg" if data[:3] == b"\xff\xd8\xff" else "image/png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "image/webp" if data[8:12] == b"WEBP" else "image/gif" if data[:4] == b"GIF8" else None
    if not kind:
        raise ValueError("That doesn't look like a photo I can read.")
    ask = " ".join(str(question or "").split())[:500] or "What's in this picture? Tell me like a friend looking at it with me, and read out any text that matters."
    message = _client(key).beta.messages.create(
        model=model if model in MODELS else DEFAULT_MODEL,
        max_tokens=4096,
        system="You are Luma, looking at a photo your owner shared. Describe only what you can actually see, read text exactly, say when you're unsure, "
               "and never identify a real person from their face. Warm and brief, plain sentences.",
        messages=[{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": kind, "data": base64.b64encode(data).decode()}},
                                               {"type": "text", "text": ask}]}],
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    return " ".join(_final_text(message).split())[:2000]
