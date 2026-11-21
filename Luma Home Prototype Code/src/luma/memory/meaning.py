"""Memory by meaning: Luma finds what you told it even when you ask in other words.

Word recall (luma.memory.segments) finds "my keys are in the blue bowl" from "where are my keys", but not "that thing my
mom likes" from "mom loves lavender candles". This adds meaning: a small open embedding model, Qwen3-Embedding-0.6B
(Alibaba Qwen, Apache-2.0, multilingual), turns each memory and each question into numbers that sit close together when
they mean the same thing. It runs on this computer through the same engine as Luma's brain (llama.cpp); nothing is sent
anywhere.

The numbers say what a memory is about, so they're kept like the memory itself: encrypted with the same key, and
forgotten with it. Word recall still comes first; meaning adds what words missed. With no model here (a small device, or
before it's downloaded) Luma recalls by words alone, exactly as before.

A lamp can't hold that model. It can hold a small one of another kind (potion-base-8M, MIT, 30 MB): a table with a row
of numbers for each word-piece, averaged over the sentence. No network to run, numpy and a tokenizer to read it. Tried
on a thousand memories (scripts/meaning_small_eval.py), questions asked in other words were found 27 times in 40
instead of 19, and "never told" said wrongly 6 times instead of 11. It's a download, so it's off until the owner
switches it on (the setting "memory_by_meaning_small"); the bigger model is used wherever it's there.
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

# the lamp's model: a static one (a row of numbers a word-piece, averaged), read with numpy and the tokenizers package
SMALL_REPO = "minishlab/potion-base-8M"
SMALL_FILES = ("model.safetensors", "tokenizer.json", "config.json")
SMALL_TAG = "potion-base-8M"   # kept beside each meaning it worked out, so one model's numbers are never read as another's
SMALL_CLOSE = 0.4              # measured at 0.35 to 0.65 (docs/HUMAN_PLAN.md): below 0.35 everything is a bit close
SMALL_TOKENS = 512
SMALL_LIMITS = {"model.safetensors": 200 << 20, "tokenizer.json": 20 << 20, "config.json": 1 << 20}

_lock = threading.Lock()
_model = {"llm": None, "failed": False}
_small = {"model": None, "failed": False}
fetching_small = {"running": False, "error": None, "tried": 0.0}
_cache = {}          # memory id -> (text fingerprint, unit vector), decrypted once
_catching_up = {"running": False}
fetching = {"running": False, "error": None}


def folder():
    from luma.llm import brain
    return brain.models_dir() / "meaning"


def model_path():
    path = folder() / FILE
    return path if path.is_file() and (path.parent / (FILE + ".ok")).exists() else None


def small_folder():
    return folder() / "small"


def small_path():
    path = small_folder()
    return path if (path / "ok").exists() and all((path / name).is_file() for name in SMALL_FILES[:2]) else None


def _tensors(path):
    """The tables in a .safetensors file, read in place: {name: array}. It's a download, so every number in its header is
    checked against the file before anything is read."""
    import numpy as np
    kinds = {"F32": np.float32, "F16": np.float16, "F64": np.float64}
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        n = int.from_bytes(f.read(8), "little")
        if not 2 <= n <= min(size - 8, 16 << 20):
            raise ValueError("not a table of meanings")
        header = json.loads(f.read(n))
    out = {}
    for name, info in header.items():
        if name == "__metadata__" or not isinstance(info, dict):
            continue
        kind, shape, (start, end) = kinds.get(info.get("dtype")), tuple(int(x) for x in info.get("shape") or ()), info.get("data_offsets") or (0, 0)
        if kind is None or len(shape) != 2 or min(shape) < 1:
            continue
        if not (0 <= start < end <= size - 8 - n) or end - start != shape[0] * shape[1] * np.dtype(kind).itemsize:
            raise ValueError("not a table of meanings")
        out[name] = np.memmap(path, dtype=kind, mode="r", offset=8 + n + start, shape=shape)
    return out


class _Static:
    """The lamp's model: each word-piece has a row of numbers; a sentence is their average."""

    def __init__(self, path):
        from tokenizers import Tokenizer
        self.words = Tokenizer.from_file(str(path / "tokenizer.json"))
        tables = _tensors(path / "model.safetensors")
        self.rows = tables.get("embeddings")
        if self.rows is None or self.rows.shape[1] < DIMS or self.rows.shape[0] < self.words.get_vocab_size():
            raise ValueError("not a table of meanings")
        self.unknown = self.words.token_to_id("[UNK]")

    def __call__(self, text):
        import numpy as np
        ids = [i for i in self.words.encode(str(text or ""), add_special_tokens=False).ids if i != self.unknown and 0 <= i < self.rows.shape[0]]
        if not ids:
            return None
        return np.asarray(self.rows[ids[:SMALL_TOKENS]], dtype=np.float32).mean(axis=0)


def _static(text):
    with _lock:
        if _small["model"] is None:
            if _small["failed"]:
                return None
            try:
                _small["model"] = _Static(small_path())
            except Exception:
                _small["failed"] = True   # no tokenizers here, or a file that isn't what it should be: words alone, as before
                return None
        model = _small["model"]
    return model(text)


def engine():
    """Which model works out a meaning here: "test" (a stand-in), "big" (the 16 GB one), "small" (the lamp's), or None."""
    if embedder is not None:
        return "test"
    if model_path() is not None and not _model["failed"]:
        return "big"
    if small_path() is not None and not _small["failed"]:
        return "small"
    return None


def tag():
    """The name kept beside each meaning: which model's numbers they are."""
    return SMALL_TAG if engine() == "small" else FILE


def close_enough():
    return SMALL_CLOSE if engine() == "small" else CLOSE


def asking(question):
    """A question as the model wants it: the bigger one is told what it's for; the small one just reads the words."""
    return str(question) if engine() == "small" else QUERY + str(question)


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
    which = engine()
    fn = embedder if which == "test" else _Llama() if which == "big" else _static if which == "small" else None
    if fn is None:
        return None
    try:
        values = fn(text)
    except Exception:
        return None
    return _unit(values) if values is not None and len(values) else None


def small_wanted(store):
    """The lamp's model is a download, so it's used (and fetched) only when the owner has switched it on."""
    return store is not None and store.setting("memory_by_meaning", True) is not False and store.setting("memory_by_meaning_small", False) is True


def available(store=None):
    if store is not None and store.setting("memory_by_meaning", True) is False:
        return False
    which = engine()
    if which == "small":
        return store is None or small_wanted(store)
    return which is not None


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
    if kept and kept.get("for") == mark and kept.get("model") == tag():
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
                store.put("vector", {"model": tag(), "for": mark, "h": pack(v)}, "vector:" + memory["id"])
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
    q = _embed(asking(question))
    if q is None:
        return []
    import numpy as np
    scored, missing, near = [], [], close_enough()
    for memory in memories:
        v = _vector(store, memory)
        if v is None:
            missing.append(memory)
            continue
        score = float(np.dot(q, v))
        if score >= near:
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


def _checked(name, entry, data):
    """Does a downloaded file match what the host lists for it? Big files are listed by SHA-256, small ones the way git names them."""
    listed = (entry.get("lfs") or {}).get("oid")
    if listed:
        return hashlib.sha256(data).hexdigest() == listed
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() == entry.get("oid")


def fetch_small(store):
    """Download the lamp's model in the background: only when the owner has switched it on, and only with the tokenizers
    package here to read it. Each file is checked against what the host lists before it's kept; one that doesn't match is
    thrown away. Tried again no more than once an hour."""
    import time
    if fetching_small["running"] or small_path() or not small_wanted(store) or time.time() - fetching_small["tried"] < 3600:
        return
    try:
        import tokenizers  # noqa: F401
    except Exception:
        fetching_small["error"] = "The small memory model needs the tokenizers package, which isn't installed here."
        return
    fetching_small.update(running=True, error=None, tried=time.time())

    def run():
        from luma.llm import brain
        try:
            with urllib.request.urlopen(urllib.request.Request(f"https://huggingface.co/api/models/{SMALL_REPO}/tree/main", headers=brain.UA), timeout=30) as r:
                listed = {f.get("path"): f for f in json.load(r)}
            out = small_folder()
            out.mkdir(parents=True, exist_ok=True)
            (out / "ok").unlink(missing_ok=True)
            kept = {}
            for name in SMALL_FILES:
                entry = listed.get(name)
                if not entry:
                    raise RuntimeError("Couldn't find the small memory model's files right now.")
                with urllib.request.urlopen(urllib.request.Request(f"https://huggingface.co/{SMALL_REPO}/resolve/main/{name}", headers=brain.UA), timeout=60) as r:
                    data = r.read(SMALL_LIMITS[name] + 1)
                if len(data) > SMALL_LIMITS[name] or not _checked(name, entry, data):
                    raise RuntimeError("The small memory model's download didn't check out, so I threw it away.")
                kept[name] = data
            for name, data in kept.items():   # only once every file has checked out
                part = out / (name + ".part")
                part.write_bytes(data)
                os.replace(part, out / name)
            (out / "ok").write_text(SMALL_TAG)
            _small.update(model=None, failed=False)
        except Exception as error:
            fetching_small["error"] = str(error)[:200]
        finally:
            fetching_small["running"] = False

    threading.Thread(target=run, daemon=True, name="luma-meaning-small-fetch").start()
