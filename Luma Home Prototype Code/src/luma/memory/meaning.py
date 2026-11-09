"""Memory by meaning: Luma finds what you told it even when you ask in other words.

Word recall (luma.memory.segments) finds "my keys are in the blue bowl" from "where are my keys", but not "that thing my
mom likes" from "mom loves lavender candles". This adds meaning: a small open embedding model, Qwen3-Embedding-0.6B
(Alibaba Qwen, Apache-2.0, multilingual), turns each memory and each question into numbers that sit close together when
they mean the same thing. It runs on this computer through the same engine as Luma's brain (llama.cpp); nothing is sent
anywhere.

The numbers say what a memory is about, so they're kept like the memory itself: encrypted with the same key, and
forgotten with it. Word recall still comes first; meaning adds what words missed. With no model here (a small device, or
before it's downloaded) Luma recalls by words alone, exactly as before.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import urllib.request

REPO = "Qwen/Qwen3-Embedding-0.6B-GGUF"
FILE = "Qwen3-Embedding-0.6B-Q8_0.gguf"
DIMS = 256          # the model is trained so its first numbers carry the most meaning (Matryoshka): 256 of 1024 keep it small
CLOSE = 0.5         # how close a memory's meaning has to be to count (cosine; unrelated things land well below)
EXTRA = 2           # memories found by meaning on top of the ones words found
MIN_RAM_GB = 16     # computers big enough to keep it loaded next to the brain
CACHE = 20000       # meanings kept opened here; the index (luma.memory.index) holds them all, smaller
QUERY = "Instruct: Given something a person said to their AI friend, find the memories about them it refers to\nQuery:"

_lock = threading.Lock()
_model = {"llm": None, "failed": False}
_cache = {}          # memory id -> (text fingerprint, unit vector), decrypted once
_catching_up = {"running": False}
fetching = {"running": False, "error": None}


def folder():
    from luma.llm import brain
    return brain.models_dir() / "meaning"


def model_path():
    path = folder() / FILE
    return path if path.is_file() and (path.parent / (FILE + ".ok")).exists() else None


def _fingerprint(text):
    return hashlib.sha256(str(text or "").encode()).hexdigest()[:16]


def pack(vector):
    """A meaning, small enough to keep a million of: half-size numbers, as text."""
    import base64
    import numpy as np
    return base64.b64encode(np.asarray(vector, dtype=np.float16).tobytes()).decode()


def unpack(record):
    """The numbers of a kept meaning, in either form it's been stored in; None when there aren't any."""
    if not isinstance(record, dict):
        return None
    if record.get("h"):
        import base64
        import numpy as np
        try:
            return np.frombuffer(base64.b64decode(record["h"]), dtype=np.float16).astype(np.float32)
        except Exception:
            return None
    return record.get("v") or None


def _unit(values):
    import numpy as np
    v = np.asarray(values, dtype=np.float32).reshape(-1)[:DIMS]
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else None


class _Llama:
    """The embedding model, loaded once and shared."""

    def __call__(self, text):
        with _lock:
            if _model["llm"] is None:
                if _model["failed"]:
                    return None
                try:
                    from llama_cpp import Llama
                    _model["llm"] = Llama(model_path=str(model_path()), embedding=True, n_ctx=512, verbose=False,
                                          n_threads=max(1, min(4, os.cpu_count() or 1)))
                except Exception:
                    _model["failed"] = True
                    return None
            out = _model["llm"].embed(text)
        if out and isinstance(out[0], list):  # one vector per token (a model without pooling): the last one stands for it
            out = out[-1]
        return out


embedder = None  # tests (and a future engine) can set this to a callable: text -> list of numbers


def _embed(text):
    fn = embedder or (_Llama() if model_path() else None)
    if fn is None:
        return None
    try:
        values = fn(text)
    except Exception:
        return None
    return _unit(values) if values is not None and len(values) else None


def available(store=None):
    if store is not None and store.setting("memory_by_meaning", True) is False:
        return False
    return embedder is not None or (model_path() is not None and not _model["failed"])


def _vector(store, memory):
    """A memory's meaning: from the cache, from the encrypted copy, or None when it hasn't been worked out yet."""
    mid, text = memory.get("id"), memory.get("text", "")
    if not mid:
        return None
    mark = _fingerprint(text)
    hit = _cache.get(mid)
    if hit and hit[0] == mark:
        return hit[1]
    kept = store.get("vector", "vector:" + mid)
    if kept and kept.get("for") == mark and kept.get("model") == FILE:
        v = _unit(unpack(kept) if unpack(kept) is not None else [])
        if v is not None:
            if len(_cache) > CACHE:
                _cache.clear()
            _cache[mid] = (mark, v)
            return v
    return None


def _work_out(store, memories):
    """Every memory without its meaning yet, in the background: recall doesn't wait for it."""
    try:
        for memory in memories:
            if not available(store):
                return
            if memory.get("id") and _vector(store, memory) is None:
                v = _embed(memory.get("text", ""))
                if v is None:
                    continue
                mark = _fingerprint(memory.get("text", ""))
                store.put("vector", {"model": FILE, "for": mark, "h": pack(v)}, "vector:" + memory["id"])
                if len(_cache) > CACHE:
                    _cache.clear()
                _cache[memory["id"]] = (mark, v)
    finally:
        _catching_up["running"] = False


def catch_up(store, memories, wait=False):
    if _catching_up["running"]:
        return
    _catching_up["running"] = True
    if wait:
        _work_out(store, memories)
    else:
        threading.Thread(target=_work_out, args=(store, memories), daemon=True, name="luma-memory-meaning").start()


def close(store, question, memories, limit=5, wait=False):
    """The memories closest in meaning to the question: [(closeness, memory)], best first, only ones close enough."""
    if not memories or not str(question or "").strip() or not available(store):
        return []
    q = _embed(QUERY + str(question))
    if q is None:
        return []
    import numpy as np
    scored, missing = [], []
    for memory in memories:
        v = _vector(store, memory)
        if v is None:
            missing.append(memory)
            continue
        score = float(np.dot(q, v))
        if score >= CLOSE:
            scored.append((score, memory))
    if missing:
        catch_up(store, missing, wait=wait)
    scored.sort(key=lambda s: s[0], reverse=True)
    return scored[:limit]


def recall(store, question, memories, found, limit=5, wait=False):
    """Word recall's finds, then up to EXTRA more that mean the same thing, not already there."""
    have = {m.get("id") for m in found}
    extra = [m for _, m in close(store, question, memories, limit, wait=wait) if m.get("id") not in have]
    room = max(EXTRA, limit - len(found))
    return found + extra[:room]


def forget(store, memory_id):
    _cache.pop(memory_id, None)
    store.delete("vector", "vector:" + memory_id)


def fetch(store=None):
    """Download the model in the background on a computer big enough for it (checked against its published SHA-256)."""
    from luma.llm import brain
    if fetching["running"] or model_path() or brain.ram_gb() < MIN_RAM_GB:
        return
    if store is not None and store.setting("memory_by_meaning", True) is False:
        return
    fetching.update(running=True, error=None)

    def run():
        try:
            req = urllib.request.Request(f"https://huggingface.co/api/models/{REPO}/tree/main", headers=brain.UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                files = json.load(r)
            choice = next((f for f in files if f.get("path") == FILE), None)
            if not choice or not (choice.get("lfs") or {}).get("oid"):
                raise RuntimeError("Couldn't find the memory model's file right now.")
            sha = choice["lfs"]["oid"]
            out = folder()
            out.mkdir(parents=True, exist_ok=True)
            part = out / (FILE + ".part")
            digest = hashlib.sha256()
            with urllib.request.urlopen(urllib.request.Request(f"https://huggingface.co/{REPO}/resolve/main/{FILE}", headers=brain.UA),
                                        timeout=60) as r, open(part, "wb") as f:
                for chunk in iter(lambda: r.read(1 << 20), b""):
                    f.write(chunk)
                    digest.update(chunk)
            if digest.hexdigest() != sha:
                part.unlink(missing_ok=True)
                raise RuntimeError("The memory model's download didn't check out, so I threw it away.")
            os.replace(part, out / FILE)
            (out / (FILE + ".ok")).write_text(sha)
        except Exception as error:
            fetching["error"] = str(error)[:200]
        finally:
            fetching["running"] = False

    threading.Thread(target=run, daemon=True, name="luma-meaning-fetch").start()
