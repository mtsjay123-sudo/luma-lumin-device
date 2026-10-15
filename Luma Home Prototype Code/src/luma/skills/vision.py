"""Luma can look at a photo. Free and local: Qwen2.5-VL 3B, run with llama.cpp.

Drop, paste or pick a picture in chat and ask about it. The image never leaves
this computer. Until the vision files have downloaded, Luma says so instead of
guessing what's in a picture.
"""
from __future__ import annotations

import base64
import glob
import re
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


# Luma fetches its own eyes the first time you share a photo (free, from Hugging Face), and says how far along it is.
REPO = "ggml-org/Qwen2.5-VL-3B-Instruct-GGUF"
fetching = {"running": False, "done": 0, "total": 0, "error": None}


def progress():
    """0-100 while the vision files download, or None when nothing is downloading."""
    if not fetching["running"]: return None
    return int(100 * fetching["done"] / fetching["total"]) if fetching["total"] else 0


def fetch_in_background():
    if available() or fetching["running"]:
        return
    fetching.update(running=True, done=0, total=0, error=None)
    threading.Thread(target=_fetch, name="luma-vision-fetch", daemon=True).start()


def _fetch():
    import json, urllib.request
    try:
        os.makedirs(str(VISION_DIR), exist_ok=True)
        with urllib.request.urlopen(f"https://huggingface.co/api/models/{REPO}", timeout=30) as r:
            names = [s["rfilename"] for s in json.load(r).get("siblings", []) if s.get("rfilename", "").endswith(".gguf")]
        main = next((n for n in names if "q4_k_m" in n.lower() and "mmproj" not in n.lower()), None) or next(n for n in names if "mmproj" not in n.lower())
        proj = next((n for n in names if "mmproj" in n.lower() and "f16" in n.lower()), None) or next(n for n in names if "mmproj" in n.lower())
        wanted = [n for n in (proj, main) if not os.path.exists(os.path.join(str(VISION_DIR), os.path.basename(n)))]
        sizes = {}
        for n in wanted:
            req = urllib.request.Request(f"https://huggingface.co/{REPO}/resolve/main/{n}", method="HEAD")
            with urllib.request.urlopen(req, timeout=30) as r:
                sizes[n] = int(r.headers.get("Content-Length") or 0)
        fetching["total"] = sum(sizes.values()) or 1
        for n in wanted:
            final = os.path.join(str(VISION_DIR), os.path.basename(n))
            part = final + ".part"
            with urllib.request.urlopen(f"https://huggingface.co/{REPO}/resolve/main/{n}", timeout=60) as r, open(part, "wb") as out:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk: break
                    out.write(chunk)
                    fetching["done"] += len(chunk)
            os.replace(part, final)  # only a complete file ever counts
    except Exception as error:
        fetching["error"] = str(error)[:200]
    finally:
        fetching["running"] = False


def as_jpeg(data, kind):
    """HEIC/HEIF (iPhone and Mac photos) -> JPEG with macOS's own converter."""
    import subprocess, sys, tempfile
    if sys.platform != "darwin":
        raise ValueError("That's an iPhone-style HEIC photo. Save it as JPEG and share it again.")
    with tempfile.TemporaryDirectory(prefix="luma-photo-") as folder:
        src, dst = os.path.join(folder, "in.heic"), os.path.join(folder, "out.jpg")
        with open(src, "wb") as f: f.write(data)
        subprocess.run(["sips", "-s", "format", "jpeg", "-Z", "1600", src, "--out", dst], check=True, capture_output=True, timeout=60)
        with open(dst, "rb") as f: return f.read()


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
    """What's in the picture, in Luma's own words. Raises ValueError if vision isn't ready or the image is bad.
    When Luma is serving, the looking happens in the brain's own process, so a crash there can't take Luma down."""
    from luma.llm import worker
    if worker.enabled():
        if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
            raise ValueError("Give me a photo to look at.")
        if not available():
            raise ValueError("not_ready")
        return worker.brain().call("look", {"image_bytes": bytes(image_bytes), "question": question})
    return _look_here(image_bytes, question, name)


def _look_here(image_bytes, question=None, name="", cancel_event=None, on_text=None):
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


# -- Apple's own on-device recognition: text in the photo and what's in it, no download --------------
APPLE_READ_JS = r"""
ObjC.import('Foundation');
ObjC.import('Vision');
function run(argv) {
  const url = $.NSURL.fileURLWithPath(argv[0]);
  const handler = $.VNImageRequestHandler.alloc.initWithURLOptions(url, $.NSDictionary.dictionary);
  const text = $.VNRecognizeTextRequest.alloc.init;
  text.setRecognitionLevel(0);
  text.setUsesLanguageCorrection(true);
  const kinds = $.VNClassifyImageRequest.alloc.init;
  handler.performRequestsError($([text, kinds]), null);
  const lines = [], labels = [];
  const tr = text.results;
  if (tr && tr.count) for (let i = 0; i < tr.count; i++) {
    const c = tr.objectAtIndex(i).topCandidates(1);
    if (c.count) lines.push(c.objectAtIndex(0).string.js);
  }
  const kr = kinds.results;
  if (kr && kr.count) for (let i = 0; i < Math.min(kr.count, 80); i++) {
    const o = kr.objectAtIndex(i);
    if (o.confidence > 0.25) labels.push(o.identifier.js);
  }
  return JSON.stringify({ text: lines, labels: labels.slice(0, 12) });
}
"""


def apple_read(image_bytes):
    """On a Mac: the words in a photo and what's in it, from macOS's own Vision framework. None elsewhere."""
    import json, subprocess, sys, tempfile
    if sys.platform != "darwin":
        return None
    with tempfile.TemporaryDirectory(prefix="luma-look-") as folder:
        path = os.path.join(folder, "photo.jpg" if bytes(image_bytes[:3]) == _JPEG else "photo.png")
        with open(path, "wb") as f:
            f.write(bytes(image_bytes))
        try:
            out = subprocess.run(["osascript", "-l", "JavaScript", "-e", APPLE_READ_JS, path], capture_output=True, text=True, timeout=25)
            data = json.loads(out.stdout.strip() or "{}")
        except Exception:
            return None
    words = [str(w).strip() for w in data.get("text") or [] if str(w).strip()]
    labels = [str(l).replace("_", " ") for l in data.get("labels") or [] if str(l).strip()]
    return {"text": words[:120], "labels": labels} if words or labels else None


READING = re.compile(r"\b(?:read|says?|text|written|words?|transcribe|what does (?:it|this) say|copy)\b", re.I)
