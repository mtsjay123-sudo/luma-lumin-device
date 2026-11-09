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

import threading
import time

from luma.llm.prompts import FIELD_SCHEMAS, build_plan_blocks, build_plan_prompt, normalize_profile, proposal_schema

MODELS = {"claude-opus-5-5": "Claude Opus 5.5 (smartest)", "claude-sonnet-5-5": "Claude Sonnet 5.5 (faster, cheaper)"}
DEFAULT_MODEL = "claude-opus-5-5"
# What the lab and the router may also use. Not offered to the owner until the human test says it sounds like Luma.
FAST_MODEL = "claude-haiku-5-5"
RUNNABLE = {*MODELS, FAST_MODEL}
NO_SERVER_FALLBACK = {FAST_MODEL}  # this model has no server-side refusal fallback: a refusal goes to the next brain at home
EFFORT = "medium"                   # for talk: held the same from turn to turn, because a change throws away the cached conversation
HARD_EFFORT = "high"                # for the rare hard ask (luma.llm.router)
WINDOW = 80                         # messages of conversation sent; the runtime moves its window in steps, so the start holds still
CACHE = {"type": "ephemeral"}       # kept five minutes, and every turn that reads it starts the five minutes again

# One answer shape for every turn, whatever tools the turn may use. A shape that changed with the tools was compiled again
# each time, and a changed shape throws away what Claude has cached of the conversation. A tool's fields travel as a JSON
# object inside a string; this computer reads and checks them (_proposal), and asks again in the exact shape if they're off.
PROPOSAL = {"anyOf": [
    {"type": "object", "properties": {"type": {"const": "reply"}, "text": {"type": "string"}}, "required": ["type", "text"], "additionalProperties": False},
    {"type": "object", "properties": {"type": {"const": "tool"}, "name": {"type": "string"}, "arguments": {"type": "string"}},
     "required": ["type", "name", "arguments"], "additionalProperties": False},
]}
ARGUMENTS_NOTE = ('For a tool, write "arguments" as that tool\'s fields in a JSON object inside a string, for example '
                  '{"type":"tool","name":"tasks.create","arguments":"{\\"title\\":\\"Call mom\\",\\"due\\":\\"tomorrow 9am\\"}"}. '
                  "Use only the tools listed for this turn, with exactly their fields.")

# What this computer has learned about the API while running: a shape it refused isn't sent again.
_learned = {"notes_in_user": set(), "exact_only": set()}
_turn = threading.local()  # the last call's real numbers (tokens read from cache, time to the first words), for the meter
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


def _history(messages, limit=WINDOW):
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


def _proposal(result, tools):
    """The brain's answer in the shape the runtime takes, or None when its tool call can't be read or isn't one this turn
    allows (then it's asked again, held to the exact shape)."""
    if not isinstance(result, dict):
        return None
    if result.get("type") == "reply" and isinstance(result.get("text"), str) and set(result) == {"type", "text"}:
        return result
    if result.get("type") != "tool" or result.get("name") not in (tools or {}):
        return None
    try:
        arguments = json.loads(result.get("arguments") or "{}")
    except (TypeError, ValueError):
        return None
    fields = tools[result["name"]].get("fields", {})
    if not isinstance(arguments, dict) or set(arguments) != set(fields):
        return None
    kinds = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict}
    for key, kind in fields.items():
        wanted = kinds.get(FIELD_SCHEMAS[kind].get("type") if kind in FIELD_SCHEMAS else kind)
        value = arguments[key]
        if wanted is None or not isinstance(value, wanted) or (isinstance(value, bool) and wanted is not bool):
            return None
    return {"type": "tool", "name": result["name"], "arguments": arguments}


def _blocks(recent, notes, notes_in_user):
    """The conversation as Claude takes it: a marker on their newest message (so the next turn reads everything up to here
    from the cache), then this turn's notes, which are never part of what's cached."""
    messages = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in recent]
    messages[-1]["content"][-1]["cache_control"] = dict(CACHE)
    if notes_in_user:
        messages[-1]["content"].append({"type": "text", "text": "<notes-from-luma-for-this-turn>\n" + notes + "\n</notes-from-luma-for-this-turn>"})
    else:
        messages.append({"role": "system", "content": notes})
    return messages


def _options(model, effort, schema):
    options = dict(model=model, max_tokens=16000, output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}})
    if model not in NO_SERVER_FALLBACK:
        options.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")  # if a safety check declines, Anthropic retries on a model that can answer
    return options


def _ask(key, request, cancel_event, on_text):
    """Send one request, streaming the reply's words as they come. Returns the parsed answer and notes the real numbers."""
    from luma.llm.inference import GenerationCancelled
    from luma.llm.streaming import ReplyTextStream
    stream_text = ReplyTextStream(on_text) if on_text is not None else None
    began, first = time.perf_counter(), None
    with _client(key).beta.messages.stream(**request) as stream:
        for chunk in stream.text_stream:
            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelled("Conversation interrupted.")
            if first is None and chunk:
                first = time.perf_counter() - began
            if stream_text is not None:
                stream_text.feed(chunk)
        message = stream.get_final_message()
    used = getattr(message, "usage", None)
    count = lambda name: int(getattr(used, name, 0) or 0)  # noqa: E731
    _turn.last = {"model": request["model"], "first_words_s": round(first, 3) if first is not None else None, "seconds": round(time.perf_counter() - began, 3),
                  "read": count("cache_read_input_tokens"), "written": count("cache_creation_input_tokens"), "fresh": count("input_tokens"),
                  "out": count("output_tokens")}
    try:
        result = json.loads(_final_text(message))
    except json.JSONDecodeError as error:
        raise ValueError("The cloud brain returned something that wasn't a proposal. No action was taken.") from error
    if not isinstance(result, dict):
        raise ValueError("The cloud brain's answer must be a JSON object.")
    return result


def last_turn():
    """The last call's real numbers on this thread, once: {"read", "written", "fresh", "out", "first_words_s", "seconds",
    "shape"}. Tokens read from Claude's cache cost a twentieth to a tenth of fresh ones and aren't read again."""
    last, _turn.last = getattr(_turn, "last", None), None
    return last


def _exact(key, model, effort, recent, memories, tools, mode, profile, now, cancel_event, on_text):
    """The request as it was before caching: one system prompt, and an answer shape that names this turn's tools exactly."""
    request = dict(_options(model, effort, _schema(proposal_schema(tools))), system=build_plan_prompt(memories, tools, mode, profile, now), messages=recent)
    result = _ask(key, request, cancel_event, on_text)
    if getattr(_turn, "last", None):
        _turn.last["shape"] = "exact"
    return result


def plan(key, messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None, model=DEFAULT_MODEL, effort=None):
    """Same contract as luma.llm.inference.plan: a dict that's either a reply or one tool proposal.

    Built so Claude reads as little as possible again: Luma's instructions first, word for word the same every turn; then
    the life file; then the conversation; and this turn's notes (the time, what fits the message, its tools) last. If the
    API won't take that, the request goes out the older way and this computer remembers not to ask again."""
    import anthropic
    profile = normalize_profile(profile)
    now = datetime.now(ZoneInfo(os.environ.get("LUMA_TIMEZONE", "America/New_York"))).isoformat()
    model = model if model in RUNNABLE else DEFAULT_MODEL
    effort = effort or EFFORT
    recent = _history(messages)
    if not recent:
        raise ValueError("Nothing to answer yet.")
    if model in _learned["exact_only"] or recent[-1]["role"] != "user":
        return _exact(key, model, effort, recent, memories, tools, mode, profile, now, cancel_event, on_text)
    frozen, life, turn = build_plan_blocks(memories, tools, mode, profile, now)
    system = [{"type": "text", "text": frozen, "cache_control": dict(CACHE)}]
    if life:
        system.append({"type": "text", "text": life, "cache_control": dict(CACHE)})
    notes = turn + "\n\n" + ARGUMENTS_NOTE if tools else turn
    heard = []  # nothing has been said out loud yet if the reply has to be asked for again

    def said(chunk):
        heard.append(chunk)
        on_text(chunk)
    try:
        for attempt in range(2):
            in_user = model in _learned["notes_in_user"]
            request = dict(_options(model, effort, PROPOSAL), system=system, messages=_blocks(recent, notes, in_user))
            try:
                result = _ask(key, request, cancel_event, said if on_text is not None else None)
                break
            except anthropic.BadRequestError as error:
                if not in_user and "system" in str(error).lower() and "role" in str(error).lower():
                    _learned["notes_in_user"].add(model)  # this model takes no instruction mid-conversation: the notes ride with their message
                    continue
                raise
    except anthropic.BadRequestError:
        if heard:
            raise
        _learned["exact_only"].add(model)
        return _exact(key, model, effort, recent, memories, tools, mode, profile, now, cancel_event, on_text)
    if getattr(_turn, "last", None):
        _turn.last["shape"] = "cached"
    proposal = _proposal(result, tools)
    if proposal is None and not heard:  # a tool call this computer can't read: asked again, held to the exact shape
        kept = getattr(_turn, "last", None)
        proposal = _exact(key, model, effort, recent, memories, tools, mode, profile, now, cancel_event, on_text)
        if kept and getattr(_turn, "last", None):
            _turn.last.update({k: _turn.last[k] + kept[k] for k in ("read", "written", "fresh", "out")}, shape="cached, then exact")
    if proposal is None:
        raise ValueError("The cloud brain returned something that wasn't a proposal. No action was taken.")
    return proposal


def warm(key, memories, mode, profile=None, model=DEFAULT_MODEL, effort=None):
    """Have Claude read Luma's instructions and the life file into its cache before the first word of a conversation, so
    the first reply doesn't wait on them. Nothing is answered: no output is billed, only the read (written to the cache).
    Returns the tokens written and read, or None if the API wouldn't."""
    model = model if model in RUNNABLE else DEFAULT_MODEL
    frozen, life, _ = build_plan_blocks(memories, {}, mode, normalize_profile(profile), "")
    system = [{"type": "text", "text": frozen, "cache_control": dict(CACHE)}]
    if life:
        system.append({"type": "text", "text": life, "cache_control": dict(CACHE)})
    options = dict(model=model, max_tokens=0, output_config={"effort": effort or EFFORT}, system=system, messages=[{"role": "user", "content": "warm up"}])
    if model not in NO_SERVER_FALLBACK:
        options.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    try:
        message = _client(key).beta.messages.create(**options)
    except Exception:
        return None
    used = getattr(message, "usage", None)
    return {"written": int(getattr(used, "cache_creation_input_tokens", 0) or 0), "read": int(getattr(used, "cache_read_input_tokens", 0) or 0)}


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
