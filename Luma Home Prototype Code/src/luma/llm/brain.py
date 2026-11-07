"""Which brain Luma thinks with, and getting it a bigger one.

Three choices, all behind the same plan/rewrite calls the runtime already uses:
  • the small local model (Qwen3 4B), always there;
  • a bigger local model (Qwen3.6 35B-A3B, or Qwen3 30B-A3B where the brain engine is too old for it: a
    mixture-of-experts that thinks like a big model but runs at the speed of a 3B one) for computers with
    the memory for it, downloaded once, checked against its published SHA-256;
  • on a computer with a lot of memory (a Mac Studio), a much bigger mixture-of-experts
    (Qwen3.5 397B-A17B, or Qwen3 235B-A22B), the same way, in as many pieces as it ships in;
  • the huge brain, on a big Mac (a Mac Studio): an open model of hundreds of billions of parameters
    (GLM-5.2, 744B, whole, with 512 GB of memory) run by colibri on this computer. Slow, so it gets the
    work worth waiting for (projects, research write-ups, the last word on a hard question), not small talk;
  • the cloud brain, if they turn it on: Claude (Anthropic) or Kimi K3.1 Pro (Moonshot's open model,
    far too big for a Mac), each with the owner's own key.
If the huge or cloud brain can't answer (stopped, offline, out of credit), the next brain answers
that turn instead of failing.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import urllib.request

from luma.config import LLAMA_MODEL_PATH
from luma.llm import colibri

# Tried in order; whichever has the files answers. The quant is picked to fit this computer's memory. Qwen3.6 35B-A3B
# (April 2026, Apache 2.0) first: a 64 GB Mac talks with it at full speed. It's built like Qwen3.5, so it needs a brain
# engine that knows that design (llama-cpp-python 0.3.36 carries it); with an older one, Qwen3 30B-A3B, which every
# engine runs, so the bigger brain always loads.
NEW_REPOS = ["unsloth/Qwen3.6-35B-A3B-GGUF", "bartowski/Qwen_Qwen3.6-35B-A3B-GGUF", "lmstudio-community/Qwen3.6-35B-A3B-GGUF"]
BIG_REPOS = NEW_REPOS + ["bartowski/Qwen_Qwen3-30B-A3B-Instruct-2507-GGUF", "unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF",
                         "lmstudio-community/Qwen3-30B-A3B-Instruct-2507-GGUF"]
NEW_ENGINE = (0, 3, 36)
QUANTS = ["Q6_K", "Q5_K_M", "Q4_K_M", "IQ4_XS", "Q3_K_L", "Q3_K_M", "IQ3_M", "IQ3_XS"]  # best first
MIN_RAM_GB = 24
# A Mac Studio's worth of memory: the biggest open brains that still run here, best first. A repo that isn't
# there is skipped; the quant is the best whose pieces fit in about 70% of memory (the rest is the OS and context).
# A 64 GB Mac holds a big brain too: Qwen3.5 122B-A10B at 2 to 3 bits (Unsloth's dynamic quants keep the parts that
# matter most at higher precision): 44.7 GB at UD-IQ3_XXS, 39 GB at UD-IQ2_M. It only reads 10B of itself per word.
STUDIO_REPOS = [(192, "unsloth/Qwen3.5-397B-A17B-GGUF", "Qwen3.5 397B"), (128, "unsloth/Qwen3-235B-A22B-Instruct-2507-GGUF", "Qwen3 235B"),
                (64, "unsloth/Qwen3.5-122B-A10B-GGUF", "Qwen3.5 122B")]
STUDIO_QUANTS = ["UD-Q4_K_XL", "Q4_K_M", "Q4_K_S", "UD-Q3_K_XL", "Q3_K_M", "UD-IQ3_XXS", "UD-Q2_K_XL", "Q2_K", "UD-IQ2_M", "UD-IQ2_XXS"]
STUDIO_RAM_GB = 128  # "bigger" means the studio brain from here up
STUDIO_MIN_GB = 64   # the smallest Mac a studio brain fits (offered, not the default)
STUDIO_NAMES = ("397B", "235B", "122B")
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


def engine():
    """The brain engine's version, read without loading it: (0, 3, 36), or () if it isn't installed."""
    try:
        from importlib.metadata import version
        return tuple(int(x) for x in re.findall(r"\d+", version("llama-cpp-python"))[:3])
    except Exception:
        return ()


def bigger_repos():
    """The bigger brains this computer's engine can run, best first."""
    return BIG_REPOS if engine() >= NEW_ENGINE else [r for r in BIG_REPOS if r not in NEW_REPOS]


def bigger_name():
    return "Qwen3.6 35B" if engine() >= NEW_ENGINE else "Qwen3 30B"


def big_model_path(skip=()):
    """The biggest verified local model here: a studio brain if there is one, else the 35B or the 30B. skip: ones that
    were too slow to talk with on this Mac."""
    folder = models_dir()
    if not folder.is_dir():
        return None
    for pattern in ("*397B*.gguf", "*235B*.gguf", "*122B*.gguf", "*35B-A3B*.gguf", "*30B-A3B*.gguf"):
        for path in sorted(folder.glob(pattern)):
            if path.name not in skip and (path.parent / (path.name + ".ok")).exists():
                return path
    return None


def is_studio(path):
    return bool(path) and any(n in path.name for n in STUDIO_NAMES)


def _slow():
    return tuple((_store.setting("brain_slow") or ()) if _store is not None else ())


def studio_name(gb=None):
    """The studio brain this Mac would get, or None."""
    gb = ram_gb() if gb is None else gb
    for need, repo, label in STUDIO_REPOS:
        if gb >= need and (engine() >= NEW_ENGINE or "Qwen3.5" not in repo):
            return label
    return None


def big_label(path=None):
    path = path or big_model_path()
    name = path.name if path else ""
    return ("Qwen3.5 397B" if "397B" in name else "Qwen3 235B" if "235B" in name else "Qwen3.5 122B" if "122B" in name
            else "Qwen3.6 35B" if "35B-A3B" in name else "Qwen3 30B")


def pick_parts(files, gb, quants=STUDIO_QUANTS, share=0.7):
    """The best quant of a big model that fits, with every piece it's split into: [file, ...] or None."""
    room = gb * share * 2 ** 30
    ggufs = [f for f in files if f.get("path", "").endswith(".gguf") and "mmproj" not in f["path"].lower()]
    for quant in quants:
        parts = [f for f in ggufs if f"{quant}".lower() in f["path"].lower().replace("/", "-") and
                 (f"/{quant}".lower() in "/" + f["path"].lower() or f"-{quant}.".lower() in f["path"].lower() or f"-{quant}-".lower() in f["path"].lower())]
        if quant.startswith("Q") and not quant.startswith("UD"):
            parts = [f for f in parts if "ud-" not in f["path"].lower()]
        if parts and sum(int(f.get("size", 0)) for f in parts) <= room:
            return sorted(parts, key=lambda f: f["path"])
    return None


# -- Luma's own brain: a LoRA add-on trained on Luma's conversations (scripts/train_luma.py, the "Train Luma's brain" workflow)
OWN_FILE = "luma-brain-lora.gguf"
RELEASES = "https://api.github.com/repos/mtsjay123-sudo/luma-lumin-device/releases?per_page=100"
own_fetching = {"running": False, "error": None}


def own_file():
    """The add-on for the brain this computer runs: the 1.7B has its own (the $249 device), the rest use the 4B's."""
    from luma.llm import inference
    base = inference.base_of(getattr(inference, "_override", None) or LLAMA_MODEL_PATH)
    return inference.ADAPTERS.get(base, OWN_FILE)


def own_path():
    """The add-on file, if it's here."""
    path = models_dir() / "luma-brain" / own_file()
    return path if path.is_file() else None


def own_on():
    return bool(_store is not None and _store.setting("brain_own", False) and own_path())


def _apply_own():
    from luma.llm import inference
    inference.use_adapter(own_path() if own_on() else None)


def set_own(on):
    _store.set_setting("brain_own", bool(on))
    _apply_own()
    return status()


def own_status():
    return {"on": own_on(), "ready": bool(own_path()), "release": (_store.setting("brain_own_release") if _store else None),
            "fetching": own_fetching["running"], "error": own_fetching["error"]}


def newest_release(releases, wanted):
    """The newest published release that carries this add-on, and the add-on: (release, asset) or None. GitHub's list
    isn't always newest first (it put luma-brain-small-6 ahead of small-11), so go by when each one was published, then
    by its number."""
    found = [(r, a) for r in releases if str(r.get("tag_name", "")).startswith("luma-brain-") and not r.get("draft")
             for a in r.get("assets", []) if a.get("name") == wanted]

    def when(pair):
        tag = str(pair[0].get("tag_name", ""))
        number = re.search(r"(\d+)$", tag)
        return str(pair[0].get("published_at") or ""), int(number.group(1)) if number else -1

    return max(found, key=when, default=None)


def fetch_own(opener=None):
    """Download the newest published Luma brain (it's only published when it's at least as honest as the stock brain),
    then think with it. Small: tens of megabytes, on top of the brain that's already here."""
    if own_fetching["running"]:
        return status()
    own_fetching.update(running=True, error=None)
    get = opener or (lambda url, timeout: urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout))

    def run():
        try:
            with get(RELEASES, 30) as response:
                releases = json.loads(response.read(8_000_000))
            wanted = own_file()
            pick = newest_release(releases, wanted)
            if not pick:
                own_fetching["error"] = "There's no trained Luma brain published yet."
                return
            release, asset = pick
            with get(asset["browser_download_url"], 120) as response:
                data = response.read(1_200_000_000)
            if data[:4] != b"GGUF" or not 1_000_000 <= len(data) <= 1_100_000_000:
                own_fetching["error"] = "That download didn't look like a Luma brain, so I didn't use it."
                return
            folder = models_dir() / "luma-brain"
            folder.mkdir(parents=True, exist_ok=True)
            part = folder / (wanted + ".part")
            part.write_bytes(data)
            part.replace(folder / wanted)
            _store.set_setting("brain_own_release", release.get("tag_name"))
            _store.set_setting("brain_own", True)
            _apply_own()
        except Exception as error:
            own_fetching["error"] = _plain_error(error)
        finally:
            own_fetching["running"] = False

    threading.Thread(target=run, daemon=True, name="luma-brain-fetch").start()
    return status()


def init(store):
    """At startup: remember the settings, and think with the bigger model if it's here and wanted."""
    global _store
    _store = store
    _apply_local()
    _apply_own()
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
    wanted = _store is None or _store.setting("brain_local", "auto") not in ("small", "auto_fast")  # auto_fast: too slow on this Mac
    inference.use_model_path(big_model_path(skip=_slow()) if wanted else None)


def use_small(small=True):
    _store.set_setting("brain_local", "small" if small else "auto")
    if not small:  # back to the bigger brain: time it afresh rather than holding old slow replies against it
        speeds = _store.setting("brain_speed") or {}
        speeds.pop("big", None)
        _store.set_setting("brain_speed", speeds)
        _store.set_setting("brain_note", None)
        _store.set_setting("brain_slow", None)
    _apply_local()


# -- cloud ---------------------------------------------------------------------
KEY_SETTING = {"anthropic": "brain_cloud_key", "kimi": "brain_kimi_key"}  # each company's key is kept on its own


def cloud_models():
    from luma.llm import cloud, kimi
    return {**cloud.MODELS, **kimi.MODELS}


def cloud_model():
    from luma.llm import cloud
    model = _store.setting("brain_cloud_model", cloud.DEFAULT_MODEL) if _store is not None else cloud.DEFAULT_MODEL
    return model if model in cloud_models() else cloud.DEFAULT_MODEL


def provider(model=None):
    from luma.llm import kimi
    return "kimi" if (model or cloud_model()) in kimi.MODELS else "anthropic"


def _provider_module(name):
    from luma.llm import cloud, kimi
    return kimi if name == "kimi" else cloud


def cloud_key(which=None):
    return (_store.setting(KEY_SETTING[which or provider()]) or "") if _store is not None else ""


def cloud_on():
    return bool(_store is not None and _store.setting("brain_cloud", False) and cloud_key())


# -- the paired computer's brain, on the device ------------------------------------------
# A $250 to $400 board's processor can't hold a conversation with a good brain (the device lab: 13 to 15 s before the 4B
# starts talking, 7 s for the 1.7B), and the owner's own computer can. On the device, while a paired computer is
# connected over Luma Link, each turn is thought out on that computer; the tools still run here, with this device's
# approvals. When it's away, the cloud brain (if it's on) answers, then the device's own brain.
_computer = {"host": None}
COMPUTER_WAIT = 20  # seconds: a computer that hasn't answered by then counts as away for this turn


def use_computer(host):
    """On the device: think with the paired computer's brain while it's connected (None: never)."""
    _computer["host"] = host


def computer_on():
    host = _computer["host"]
    if host is None:
        return False
    try:
        here = host.listening() if hasattr(host, "listening") else host.connected()
        return bool(here and (_store is None or _store.setting("brain_use_computer", True)))
    except Exception:
        return False


def computer_label():
    return "your computer's brain (Luma Link)"


def _ask_computer(kind, payload, cancel_event=None, wait=COMPUTER_WAIT):
    from luma.llm import inference
    host = _computer["host"]
    if host is None:
        raise BrainUnavailable("No computer is connected.")
    got = host.send(kind, wait=wait, cancel=cancel_event, log=False, **payload)
    if cancel_event is not None and cancel_event.is_set():
        raise inference.GenerationCancelled("The owner interrupted this turn.")
    if not isinstance(got, dict):
        raise TimeoutError("Your computer didn't answer in time.")
    if got.get("error"):
        raise RuntimeError(str(got["error"])[:200])
    return got


def _computer_plan(messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None):
    got = _ask_computer("brain.plan", {"messages": messages, "memories": memories, "tools": tools, "mode": mode, "profile": profile}, cancel_event)
    proposal = got.get("proposal")
    if not isinstance(proposal, dict) or proposal.get("type") not in ("reply", "tool"):
        raise ValueError("Your computer's brain sent back something that isn't an answer.")
    if on_text is not None and proposal.get("type") == "reply" and isinstance(proposal.get("text"), str):
        on_text(proposal["text"])  # the whole reply at once: the voice starts on it like on a streamed one
    return proposal


def _computer_rewrite(prompt, max_tokens=90, cancel_event=None):
    text = _ask_computer("brain.rewrite", {"prompt": prompt, "max_tokens": max_tokens}, cancel_event).get("text")
    if not isinstance(text, str):
        raise ValueError("Your computer's brain sent back no rewrite.")
    return text


def _from_computer(call, args, kwargs, sent, tier):
    """One call on the computer's brain, or None when it couldn't (the next brain answers)."""
    from luma.llm import inference
    try:
        result = _metered(computer_label(), tier, call, args, kwargs, sent)
        if _store is not None and _store.setting("brain_computer_error"):
            _store.set_setting("brain_computer_error", None)
        return result
    except inference.GenerationCancelled:
        raise
    except Exception as error:  # asleep, closed, too slow this once: the next brain answers this turn
        if _store is not None:
            _store.set_setting("brain_computer_error", f"Your computer's brain couldn't answer ({type(error).__name__}), so another one did.")
        return None


def set_cloud(on, key=None, model=None):
    if on:
        model = model or cloud_model()
        if model not in cloud_models():
            raise ValueError("Choose Claude Opus 5.5, Claude Sonnet 5.5 or Kimi K3.1 Pro.")
        which = provider(model)
        key = (key or cloud_key(which)).strip()
        _provider_module(which).check_key(key, model)
        _store.set_setting(KEY_SETTING[which], key)
        _store.set_setting("brain_cloud_model", model)
    _store.set_setting("brain_cloud", bool(on))
    return status()


def forget_key():
    _store.set_setting("brain_cloud", False)
    _store.set_setting(KEY_SETTING[provider()], None)
    return status()


def status():
    from luma.llm import cloud
    big = big_model_path(skip=_slow())
    any_studio = any(is_studio(p) for p in models_dir().glob("*.gguf") if (p.parent / (p.name + ".ok")).exists()) if models_dir().is_dir() else False
    gb = ram_gb()
    using_big = bool(big) and (_store is None or _store.setting("brain_local", "auto") not in ("small", "auto_fast"))
    local_name = f"{big_label(big)} (bigger)" if using_big else "Qwen3 4B"
    measured = speed()
    return {
        "cloud": {"on": cloud_on(), "has_key": bool(cloud_key()), "keys": {which: bool(cloud_key(which)) for which in KEY_SETTING},
                  "model": cloud_model(), "provider": provider(), "models": cloud_models(),
                  "last_error": (_store.setting("brain_cloud_error") if _store else None)},
        "local": {"name": local_name, "big_ready": bool(big), "big_fits": gb >= MIN_RAM_GB, "ram_gb": round(gb), "using_big": using_big,
                  "big_name": big_label(big) if big else ("a Mac Studio-size brain" if gb >= STUDIO_RAM_GB else bigger_name()),
                  "studio": bool(studio_name(gb)) and not any_studio, "studio_name": studio_name(gb),
                  "fetching": progress(), "fetch_error": fetching["error"],
                  "speed": measured, "keeps_up": (measured.get("big" if using_big else "fast", KEEPS_UP) >= KEEPS_UP),
                  "note": (_store.setting("brain_note") if _store else None)},
        "huge": huge_status(),
        "own": own_status(),
        "health": health(),
        "thinking_with": cloud_models().get(cloud_model(), "the cloud brain") if cloud_on() else local_name,
    }


# -- the calls the runtime makes ------------------------------------------------
# Every call has a tier. "light" (quick reads, short rewrites, classifying) stays on the free local brain
# even when a cloud brain is on, unless the owner turned routing off; "heavy" (planning, coding, research
# write-ups) goes to the strongest brain available; None is an ordinary chat turn.
TIERS = ("light", "standard", "heavy")


def use_cloud(tier=None):
    if not cloud_on():
        return False
    return not (tier == "light" and _store.setting("route_by_task", True) and health()["ok"])


def local_label():
    return f"{big_label()} (local)" if inference_model_is_big() else "Qwen3 4B (local)"


def inference_model_is_big():
    from luma.llm import inference
    return bool(getattr(inference, "_override", None))


def _metered(label, tier, call, args, kwargs, sent):
    from luma.llm import usage
    timer = usage.Timer()
    try:
        result = call(*args, **kwargs)
    except Exception:
        usage.record(_store, label, usage.tokens(sent), 0, timer.seconds, ok=False, tier=tier)
        raise
    usage.record(_store, label, usage.tokens(sent), usage.tokens(result), timer.seconds, ok=True, tier=tier)
    if label.endswith("(local)"):
        note_speed(usage.tokens(result), timer.seconds)
    return result


# -- how fast it really is on this computer -----------------------------------------
KEEPS_UP = 8.0     # tokens a second, start to finish: below this a spoken reply leaves people waiting
SPEED_SAMPLES = 6  # replies timed before deciding anything


def note_speed(tokens, seconds):
    """Every real reply is timed on this computer. If the bigger brain can't keep up here (in auto, not when the owner
    picked it), Luma goes back to the fast one on its own; the choice comes from this Mac, not from a spec sheet."""
    if _store is None or tokens < 20 or seconds <= 0:
        return
    which = "big" if inference_model_is_big() else "fast"
    speeds = _store.setting("brain_speed") or {}
    rates = (speeds.get(which) or [])[-(SPEED_SAMPLES - 1):] + [round(tokens / seconds, 1)]
    speeds[which] = rates
    _store.set_setting("brain_speed", speeds)
    if which == "big" and len(rates) >= SPEED_SAMPLES and _median(rates) < KEEPS_UP and _store.setting("brain_local", "auto") == "auto":
        # Too slow to talk with here: the next brain down that's on this Mac (the 122B steps down to the 35B), and the
        # small fast one only when there's none.
        now = big_model_path(skip=_slow())
        slow = sorted(set(_slow()) | ({now.name} if now else set()))
        after = big_model_path(skip=slow)
        if after:
            speeds.pop("big", None)  # the next brain down is timed afresh
            _store.set_setting("brain_speed", speeds)
            _store.set_setting("brain_slow", slow)
            _store.set_setting("brain_note", f"{big_label(now)} answered at about {_median(rates):.0f} words a second on this Mac, too slow to talk, "
                                             f"so I switched to {big_label(after)}. You can switch back in Settings.")
        else:
            _store.set_setting("brain_local", "auto_fast")
            _store.set_setting("brain_note", f"The bigger brain answered at about {_median(rates):.0f} words a second on this Mac, too slow to talk, "
                                             "so I switched to the fast one. You can switch back in Settings.")
        _apply_local()


def _median(values):
    ordered = sorted(values)
    return ordered[len(ordered) // 2] if ordered else 0.0


SLOW = 15.0  # tokens a second: a brain slower than this answers in one trip (no think-first, weigh-it-out or second look)


def slow_here():
    """A brain that has to save its trips through the model: a $250 device says so itself (LUMA_DEVICE_TIER=budget), or this
    computer timed the brain it's using below SLOW. The cloud brain and a paired computer's think fast, so with either nothing is slow."""
    if cloud_on() or computer_on():
        return False
    if os.environ.get("LUMA_DEVICE_TIER", "").strip().lower() == "budget":
        return True
    rate = speed().get("big" if inference_model_is_big() else "fast")
    return bool(rate) and rate < SLOW


def speed():
    """What this computer has measured: {"fast": tokens/s, "big": tokens/s} (median of recent replies), or empty."""
    speeds = (_store.setting("brain_speed") or {}) if _store is not None else {}
    return {which: _median(rates) for which, rates in speeds.items() if rates}


# -- the huge brain (colibri, on this Mac) ------------------------------------------------
def huge_on():
    """Turned on by the owner, and colibri is answering on this computer right now."""
    return bool(_store is not None and _store.setting("brain_huge", False) and colibri.ready())


def use_huge(tier=None):
    """Heavy work goes to the huge brain when it's on. Ordinary replies only if the owner wants to talk with it (and no
    cloud brain is on); quick reads never wait on it."""
    if not huge_on():
        return False
    if tier == "heavy":
        return True
    return tier != "light" and bool(_store.setting("brain_huge_chat", False)) and not cloud_on()


def huge_label():
    return f"{colibri.ready() or 'the huge brain'} (colibri, local)"


def set_huge(on, chat=None):
    _store.set_setting("brain_huge", bool(on))
    if chat is not None:
        _store.set_setting("brain_huge_chat", bool(chat))
    if on and colibri.installed() and not colibri.ready(max_age=0):
        threading.Thread(target=colibri.start, daemon=True, name="colibri-start").start()
    if on:
        _store.set_setting("brain_huge_error", None)
    return get_huge()


def get_huge():
    return {"huge": huge_status()}


def huge_status():
    gb = ram_gb()
    on = bool(_store is not None and _store.setting("brain_huge", False))
    return {"on": on, "chat": bool(_store is not None and _store.setting("brain_huge_chat", False)),
            "installed": colibri.installed(), "running": bool(colibri.ready()), "model": colibri.ready(),
            "ram_gb": round(gb), "whole_glm": gb >= colibri.WHOLE_GLM_RAM_GB, "fits": gb >= 16,
            "installing": dict(colibri.installing), "error": (_store.setting("brain_huge_error") if _store else None)}


def install_huge():
    return colibri.install(ram_gb())


def plan(messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None, tier=None, use_computer_brain=True):
    """One turn's proposal from the best brain that can answer: the huge one for heavy work, the paired computer's (on the
    device), the cloud brain if it's on, then this one's own. use_computer_brain=False: a computer lending its brain to the
    device never hands the turn on again."""
    from luma.llm import inference
    sent = [messages, memories, tools]
    if use_huge(tier):
        try:
            result = _metered(huge_label(), tier, colibri.plan, (messages, memories, tools, mode),
                              {"profile": profile, "cancel_event": cancel_event, "on_text": on_text}, sent)
            if _store.setting("brain_huge_error"): _store.set_setting("brain_huge_error", None)
            return result
        except inference.GenerationCancelled:
            raise
        except Exception as error:  # stopped, out of memory, an empty answer: the next brain answers this turn
            _store.set_setting("brain_huge_error", f"The huge brain couldn't answer ({type(error).__name__}), so another one did.")
    if use_computer_brain and computer_on():
        result = _from_computer(_computer_plan, (messages, memories, tools, mode),
                                {"profile": profile, "cancel_event": cancel_event, "on_text": on_text}, sent, tier)
        if result is not None:
            return result
    if use_cloud(tier):
        try:
            result = _metered(cloud_models().get(cloud_model(), cloud_model()), tier, _provider_module(provider()).plan,
                              (cloud_key(), messages, memories, tools, mode),
                              {"profile": profile, "cancel_event": cancel_event, "on_text": on_text, "model": cloud_model()}, sent)
            if _store.setting("brain_cloud_error"): _store.set_setting("brain_cloud_error", None)
            return result
        except inference.GenerationCancelled:
            raise
        except Exception as error:  # offline, out of credit, a refusal: the local brain answers this turn
            _store.set_setting("brain_cloud_error", _plain_error(error))
    return _metered(local_label(), tier, _local, (inference.plan, messages, memories, tools, mode),
                    {"profile": profile, "cancel_event": cancel_event, "on_text": on_text}, sent)


def rewrite(prompt, max_tokens=90, cancel_event=None, tier="light", use_computer_brain=True):
    from luma.llm import inference
    if use_huge(tier):
        try:
            return _metered(huge_label(), tier, colibri.rewrite, (prompt,), {"max_tokens": max_tokens, "cancel_event": cancel_event}, prompt)
        except inference.GenerationCancelled:
            raise
        except Exception as error:
            _store.set_setting("brain_huge_error", f"The huge brain couldn't answer ({type(error).__name__}), so another one did.")
    if use_computer_brain and computer_on():
        said = _from_computer(_computer_rewrite, (prompt,), {"max_tokens": max_tokens, "cancel_event": cancel_event}, prompt, tier)
        if said is not None:
            return said
    if use_cloud(tier):
        try:
            return _metered(cloud_models().get(cloud_model(), cloud_model()), tier, _provider_module(provider()).rewrite,
                            (cloud_key(), prompt), {"max_tokens": max_tokens, "model": cloud_model()}, prompt)
        except Exception as error:
            _store.set_setting("brain_cloud_error", _plain_error(error))
    return _metered(local_label(), tier, _local, (inference.rewrite, prompt), {"max_tokens": max_tokens, "cancel_event": cancel_event}, prompt)


def _plain_error(error):
    name = type(error).__name__
    if "Authentication" in name: return "The cloud brain stopped accepting your key. Paste a new one in Settings."
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


def fetch_bigger(studio=False):
    """The bigger brain this Mac has room for. studio: the big one instead, for a 64 GB Mac (on 128 GB and up, the
    studio brain is what "bigger" means already)."""
    have = big_model_path()
    studio = bool(studio_name()) and (studio or ram_gb() >= STUDIO_RAM_GB)
    studio_ready = is_studio(have)
    upgrade = have is not None and "30B-A3B" in have.name and engine() >= NEW_ENGINE  # the 30B, and the 35B runs here now
    if fetching["running"] or studio_ready or (have and not studio and ram_gb() < STUDIO_RAM_GB and not upgrade):
        return status()
    if ram_gb() < MIN_RAM_GB:
        raise ValueError(f"The bigger brain needs a computer with at least {MIN_RAM_GB} GB of memory; this one has {round(ram_gb())} GB. "
                         "The cloud brain (Settings) is the way to go here.")
    fetching.update(running=True, done=0, total=0, error=None, file=None)
    threading.Thread(target=_fetch, args=(studio,), name="luma-brain-fetch", daemon=True).start()
    return status()


def _download(repo, choice, folder):
    """One file from Hugging Face, resumed if it was cut off, checked against its SHA-256."""
    sha = (choice.get("lfs") or {}).get("oid") or (choice.get("lfs") or {}).get("sha256")
    final = folder / os.path.basename(choice["path"])
    part = final.with_name(final.name + ".part")
    have = part.stat().st_size if part.exists() else 0
    digest = hashlib.sha256()
    if have:
        with open(part, "rb") as f:
            for block in iter(lambda: f.read(1 << 22), b""): digest.update(block)
    fetching["done"] += have
    req = urllib.request.Request(f"https://huggingface.co/{repo}/resolve/main/{choice['path']}", headers={**UA, **({"Range": f"bytes={have}-"} if have else {})})
    with urllib.request.urlopen(req, timeout=60) as r, open(part, "ab" if have else "wb") as out:
        if have and r.status != 206:
            out.seek(0); out.truncate(); digest = hashlib.sha256(); fetching["done"] -= have
        for chunk in iter(lambda: r.read(1 << 20), b""):
            out.write(chunk); digest.update(chunk); fetching["done"] += len(chunk)
    if part.stat().st_size != int(choice["size"]) or (sha and digest.hexdigest() != sha):
        part.unlink(missing_ok=True)
        raise RuntimeError("The download didn't check out, so I threw it away. Try again.")
    os.replace(part, final)
    return final, digest.hexdigest()


def _fetch_studio():
    """The Mac Studio brain: the first that fits, every piece downloaded and checked before it's used."""
    gb = ram_gb()
    for need, repo, label in STUDIO_REPOS:
        if gb < need or ("Qwen3.5" in repo and engine() < NEW_ENGINE):  # Qwen3.5's design needs the newer engine
            continue
        try:
            with urllib.request.urlopen(urllib.request.Request(f"https://huggingface.co/api/models/{repo}/tree/main?recursive=true", headers=UA), timeout=30) as r:
                parts = pick_parts(json.load(r), gb)
        except Exception:
            continue
        if not parts:
            continue
        folder = models_dir()
        folder.mkdir(parents=True, exist_ok=True)
        fetching.update(total=sum(int(f["size"]) for f in parts), done=0, file=f"{label} ({len(parts)} piece{'s' if len(parts) > 1 else ''})")
        done = [_download(repo, f, folder) for f in parts]
        (folder / (done[0][0].name + ".ok")).write_text(" ".join(h for _, h in done))
        return True
    return False


def _fetch(studio=None):
    try:
        if (ram_gb() >= STUDIO_RAM_GB if studio is None else studio) and _fetch_studio():
            _apply_local()
            return
        choice, repo = None, None
        for repo in bigger_repos():
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
