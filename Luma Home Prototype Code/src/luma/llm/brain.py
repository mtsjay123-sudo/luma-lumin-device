"""Which brain Luma thinks with, and getting it a bigger one.

Three choices, all behind the same plan/rewrite calls the runtime already uses:
  • the small local model (Qwen3 4B), always there;
  • a bigger local model (Qwen3 30B-A3B, a mixture-of-experts that thinks like a big
    model but runs at the speed of a 3B one) for computers with the memory for it,
    downloaded once, checked against its published SHA-256;
  • the cloud brain (Claude) with the owner's own key, if they turn it on.
If the cloud brain can't answer (offline, out of credit), Luma falls back to the
local one for that turn instead of failing.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import urllib.request

from luma.config import LLAMA_MODEL_PATH

# Tried in order; whichever has the files answers. The quant is picked to fit this computer's memory.
BIG_REPOS = ["bartowski/Qwen_Qwen3-30B-A3B-Instruct-2507-GGUF", "unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF",
             "lmstudio-community/Qwen3-30B-A3B-Instruct-2507-GGUF"]
QUANTS = ["Q4_K_M", "IQ4_XS", "Q3_K_L", "Q3_K_M", "IQ3_M", "IQ3_XS"]  # best first
MIN_RAM_GB = 24
UA = {"User-Agent": "LumaDesktop/1.0 (+https://github.com/mtsjay123-sudo/luma-lumin-device)"}

fetching = {"running": False, "done": 0, "total": 0, "error": None, "file": None}
_store = None


def ram_gb():
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30
    except (ValueError, OSError, AttributeError):
        return 0.0


def models_dir():
    return LLAMA_MODEL_PATH.parent


def big_model_path():
    """The bigger model, only once it's complete and verified."""
    folder = models_dir()
    if not folder.is_dir():
        return None
    for path in sorted(folder.glob("*30B-A3B*.gguf")):
        if (path.parent / (path.name + ".ok")).exists():
            return path
    return None


def init(store):
    """At startup: remember the settings, and think with the bigger model if it's here and wanted."""
    global _store
    _store = store
    _apply_local()
    from luma.llm import worker
    if worker.enabled():
        # If the bigger brain crashes for lack of memory, the brain process falls back on its own; remember that choice.
        worker.brain().on_change = lambda which: store.set_setting("brain_local", which)


class BrainUnavailable(ValueError):
    """The local brain can't think right now. The message says why, in plain words, and what fixes it."""


def health():
    """Can the local brain think, and if not, why not (checked without loading anything)."""
    import importlib.util
    from luma.llm import inference, worker
    if importlib.util.find_spec("llama_cpp") is None:
        return {"ok": False, "reason": "engine", "say": "My brain's engine didn't finish installing. Use Repair in Settings and I'll reinstall it."}
    path = inference._override or LLAMA_MODEL_PATH
    if not path.exists():
        return {"ok": False, "reason": "model", "say": "My brain's model file is missing. Use Repair in Settings and I'll download it again."}
    if path.stat().st_size < 200 * 2 ** 20:
        return {"ok": False, "reason": "model", "say": "My brain's model file is incomplete. Use Repair in Settings and I'll download it again."}
    out = {"ok": True, "reason": None, "say": ""}
    if worker.enabled():
        state = worker.brain().state()
        out["process"] = state
        if state["resting"]:
            out.update(ok=False, reason="crashing", say=state["note"])
        elif state["note"]:
            out["say"] = state["note"]
    return out


def _local(call, *args, **kwargs):
    """The local brain, with its failures turned into something a person can act on."""
    from luma.llm import inference, worker
    try:
        return call(*args, **kwargs)
    except inference.GenerationCancelled:
        raise
    except (worker.BrainCrashed, worker.BrainResting) as error:
        raise BrainUnavailable(str(error) if isinstance(error, worker.BrainResting) else
                               "My brain hit a snag and restarted. Say that again and I'll answer.") from error
    except (FileNotFoundError, ImportError, RuntimeError, MemoryError, OSError) as error:
        h = health()
        raise BrainUnavailable(h["say"] if not h["ok"] else
                               "My brain couldn't start on this computer just now. Close a few big apps and try again, or turn on the cloud brain in Settings.") from error


def _apply_local():
    from luma.llm import inference
    wanted = _store is None or _store.setting("brain_local", "auto") != "small"
    inference.use_model_path(big_model_path() if wanted else None)


def use_small(small=True):
    _store.set_setting("brain_local", "small" if small else "auto")
    _apply_local()


# -- cloud ---------------------------------------------------------------------
def cloud_key():
    return (_store.setting("brain_cloud_key") or "") if _store is not None else ""


def cloud_on():
    return bool(_store is not None and _store.setting("brain_cloud", False) and cloud_key())


def set_cloud(on, key=None, model=None):
    from luma.llm import cloud
    if on:
        key = (key or cloud_key()).strip()
        model = model or _store.setting("brain_cloud_model", cloud.DEFAULT_MODEL)
        if model not in cloud.MODELS:
            raise ValueError("Choose Claude Opus 5.5 or Claude Sonnet 5.5.")
        cloud.check_key(key, model)
        _store.set_setting("brain_cloud_key", key)
        _store.set_setting("brain_cloud_model", model)
    _store.set_setting("brain_cloud", bool(on))
    return status()


def forget_key():
    _store.set_setting("brain_cloud", False)
    _store.set_setting("brain_cloud_key", None)
    return status()


def status():
    from luma.llm import cloud
    big = big_model_path()
    gb = ram_gb()
    local_name = "Qwen3 30B (bigger)" if big and (_store is None or _store.setting("brain_local", "auto") != "small") else "Qwen3 4B"
    return {
        "cloud": {"on": cloud_on(), "has_key": bool(cloud_key()), "model": (_store.setting("brain_cloud_model", cloud.DEFAULT_MODEL) if _store else cloud.DEFAULT_MODEL),
                  "models": cloud.MODELS, "last_error": (_store.setting("brain_cloud_error") if _store else None)},
        "local": {"name": local_name, "big_ready": bool(big), "big_fits": gb >= MIN_RAM_GB, "ram_gb": round(gb),
                  "fetching": progress(), "fetch_error": fetching["error"]},
        "health": health(),
        "thinking_with": cloud.MODELS.get(_store.setting("brain_cloud_model", cloud.DEFAULT_MODEL), "Claude") if cloud_on() else local_name,
    }


# -- the calls the runtime makes ------------------------------------------------
def plan(messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None):
    from luma.llm import inference
    if cloud_on():
        from luma.llm import cloud
        try:
            result = cloud.plan(cloud_key(), messages, memories, tools, mode, profile=profile, cancel_event=cancel_event,
                                on_text=on_text, model=_store.setting("brain_cloud_model", cloud.DEFAULT_MODEL))
            if _store.setting("brain_cloud_error"): _store.set_setting("brain_cloud_error", None)
            return result
        except inference.GenerationCancelled:
            raise
        except Exception as error:  # offline, out of credit, a refusal: the local brain answers this turn
            _store.set_setting("brain_cloud_error", _plain_error(error))
    return _local(inference.plan, messages, memories, tools, mode, profile=profile, cancel_event=cancel_event, on_text=on_text)


def rewrite(prompt, max_tokens=90, cancel_event=None):
    from luma.llm import inference
    if cloud_on():
        from luma.llm import cloud
        try:
            return cloud.rewrite(cloud_key(), prompt, max_tokens=max_tokens, model=_store.setting("brain_cloud_model", cloud.DEFAULT_MODEL))
        except Exception as error:
            _store.set_setting("brain_cloud_error", _plain_error(error))
    return _local(inference.rewrite, prompt, max_tokens=max_tokens, cancel_event=cancel_event)


def _plain_error(error):
    name = type(error).__name__
    if "Authentication" in name: return "Anthropic stopped accepting the key. Paste a new one in Settings."
    if "RateLimit" in name: return "The cloud brain is busy or out of credit, so I used the local one."
    if "Connection" in name or "Timeout" in name: return "Couldn't reach the cloud brain, so I used the local one."
    if "Refused" in name: return "The cloud brain declined one message, so the local one answered."
    return f"The cloud brain had a problem ({name}), so I used the local one."


# -- getting the bigger local model ---------------------------------------------------
def progress():
    if not fetching["running"]: return None
    return int(100 * fetching["done"] / fetching["total"]) if fetching["total"] else 0


def pick(files, gb):
    """The best quant of the bigger model that leaves this computer room to breathe (about half its memory)."""
    room = gb * 0.5 * 2 ** 30
    sized = {f["path"]: f for f in files if f.get("path", "").endswith(".gguf") and "mmproj" not in f["path"].lower()}
    for quant in QUANTS:
        for path, f in sized.items():
            if f"-{quant}.gguf".lower() in path.lower() and "/" not in path and 0 < f.get("size", 0) <= room:
                return f
    return None


def fetch_bigger():
    if big_model_path() or fetching["running"]:
        return status()
    if ram_gb() < MIN_RAM_GB:
        raise ValueError(f"The bigger brain needs a computer with at least {MIN_RAM_GB} GB of memory; this one has {round(ram_gb())} GB. "
                         "The cloud brain (Settings) is the way to go here.")
    fetching.update(running=True, done=0, total=0, error=None, file=None)
    threading.Thread(target=_fetch, name="luma-brain-fetch", daemon=True).start()
    return status()


def _fetch():
    try:
        choice, repo = None, None
        for repo in BIG_REPOS:
            try:
                with urllib.request.urlopen(urllib.request.Request(f"https://huggingface.co/api/models/{repo}/tree/main", headers=UA), timeout=30) as r:
                    choice = pick(json.load(r), ram_gb())
            except Exception:
                continue
            if choice: break
        if not choice:
            raise RuntimeError("Couldn't find the bigger model's files right now. Try again later.")
        sha = (choice.get("lfs") or {}).get("oid") or (choice.get("lfs") or {}).get("sha256")
        folder = models_dir()
        folder.mkdir(parents=True, exist_ok=True)
        final = folder / os.path.basename(choice["path"])
        part = final.with_name(final.name + ".part")
        fetching.update(total=int(choice["size"]), file=final.name)
        have = part.stat().st_size if part.exists() else 0
        digest = hashlib.sha256()
        if have:  # resume: hash what's already there first
            with open(part, "rb") as f:
                for block in iter(lambda: f.read(1 << 22), b""): digest.update(block)
        fetching["done"] = have
        req = urllib.request.Request(f"https://huggingface.co/{repo}/resolve/main/{choice['path']}", headers={**UA, **({"Range": f"bytes={have}-"} if have else {})})
        with urllib.request.urlopen(req, timeout=60) as r, open(part, "ab" if have else "wb") as out:
            if have and r.status != 206:  # the server started over: so do we
                out.seek(0); out.truncate(); digest = hashlib.sha256(); fetching["done"] = 0
            for chunk in iter(lambda: r.read(1 << 20), b""):
                out.write(chunk); digest.update(chunk); fetching["done"] += len(chunk)
        if part.stat().st_size != int(choice["size"]) or (sha and digest.hexdigest() != sha):
            part.unlink(missing_ok=True)
            raise RuntimeError("The download didn't check out, so I threw it away. Try again.")
        os.replace(part, final)
        (folder / (final.name + ".ok")).write_text(digest.hexdigest())
        _apply_local()  # think with it from the next message on
    except Exception as error:
        fetching["error"] = str(error)[:200]
    finally:
        fetching["running"] = False
