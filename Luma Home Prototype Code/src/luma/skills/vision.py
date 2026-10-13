"""Luma can look at a photo. Free and local: Qwen2.5-VL 3B, run with llama.cpp.

Drop, paste or pick a picture in chat and ask about it. The image never leaves
this computer. Until the vision files have downloaded, Luma says so instead of
guessing what's in a picture.
"""
from __future__ import annotations

import base64
import glob
import os
import threading

from luma.config import VISION_DIR, LLAMA_GPU_LAYERS, LLAMA_THREADS

_model = None
_lock = threading.RLock()
_MAX_IMAGE_BYTES = 12_000_000
_JPEG = b"\xff\xd8\xff"
_PNG = b"\x89PNG\r\n\x1a\n"
_WEBP = b"RIFF"
_GIF = b"GIF8"


def _find(pattern):
    hits = sorted(glob.glob(os.path.join(str(VISION_DIR), pattern)))
    return hits[0] if hits else None


def model_path():
    # The main vision model: a Qwen2.5-VL *.gguf that is not the mmproj file.
    for name in sorted(glob.glob(os.path.join(str(VISION_DIR), "*.gguf"))):
        if "mmproj" not in os.path.basename(name).lower():
            return name
    return None


def projector_path():
    return _find("mmproj*.gguf")


def available():
    return bool(model_path() and projector_path())


def _load():
    global _model
    with _lock:
        if _model is not None:
            return _model
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import Qwen25VLChatHandler
        handler = Qwen25VLChatHandler(clip_model_path=projector_path(), verbose=False)
        _model = Llama(model_path=model_path(), chat_handler=handler, n_ctx=4096,
                       n_gpu_layers=LLAMA_GPU_LAYERS, n_threads=LLAMA_THREADS, logits_all=False, verbose=False)
        return _model


def _data_uri(data):
    if data[:3] == _JPEG:
        kind = "jpeg"
    elif data[:8] == _PNG:
        kind = "png"
    elif data[:4] == _WEBP and data[8:12] == b"WEBP":
        kind = "webp"
    elif data[:4] == _GIF:
        kind = "gif"
    else:
        raise ValueError("That doesn't look like a photo I can read (use a JPEG, PNG, WebP or GIF).")
    return f"data:image/{kind};base64," + base64.b64encode(data).decode()


def look(image_bytes, question=None, name=""):
    """What's in the picture, in Luma's own words. Raises ValueError if vision isn't ready or the image is bad."""
    if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
        raise ValueError("Give me a photo to look at.")
    if len(image_bytes) > _MAX_IMAGE_BYTES:
        raise ValueError("That image is big. Try one under about 12 MB.")
    if not available():
        raise ValueError("not_ready")
    uri = _data_uri(bytes(image_bytes))
    ask = " ".join(str(question or "").split())[:500] or "What's in this picture? Describe it naturally, like a friend looking at it with me."
    messages = [
        {"role": "system", "content": "You are Luma, looking at a photo with your friend. Describe only what you can actually see. "
                                       "If you're unsure, say so. Never claim to recognize a specific private individual. Be warm and brief."},
        {"role": "user", "content": [{"type": "image_url", "image_url": {"url": uri}}, {"type": "text", "text": ask}]},
    ]
    model = _load()
    with _lock:
        out = model.create_chat_completion(messages=messages, max_tokens=320, temperature=0.4)
    text = (out.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
    return " ".join(str(text).split())[:1400] or "I looked, but I couldn't make much out. Want to try a clearer photo?"


def warm_up():
    try:
        if available():
            _load()
    except Exception as error:
        print(f"[vision] not ready: {error}", flush=True)
