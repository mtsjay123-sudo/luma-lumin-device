"""Luma's expressive voice, in a process of its own.

Runs with the voice's own Python (it has mlx-audio, the open-source speech library for Apple
Silicon) and talks to Luma over stdin/stdout, one JSON request per line:

  {"id": 1, "op": "load", "engine": "expressive", "ref": "/path/luma-ref.wav", "ref_text": "..."}
  {"id": 2, "op": "say", "text": "Not gonna lie, that's crazy [laugh]"}

and answers {"id": 1, "ok": true, ...} with the audio as base64 16-bit PCM. Only the standard
library, numpy and mlx-audio are used here, so nothing else from Luma has to load in this process.
If the native code underneath crashes, only this process goes; Luma notices and keeps talking in
its classic voice.
"""
import base64
import json
import os
import sys
import time

# Each engine: the open models to try, in order (the first one that loads wins), and what it can do.
ENGINES = {
    # Chatterbox-Turbo (Resemble AI, MIT): small and fast, clones a voice from a few seconds, and can really laugh.
    "expressive": {"repos": ["mlx-community/chatterbox-turbo-fp16", "mlx-community/chatterbox-turbo-bf16", "mlx-community/chatterbox-turbo-8bit",
                             "mlx-community/chatterbox-turbo-4bit", "mlx-community/Chatterbox-Turbo-fp16", "mlx-community/Chatterbox-Turbo-TTS-fp16"],
                   "tags": True},
    # Qwen3-TTS 0.6B (Alibaba Qwen, Apache-2.0): a bigger model with very natural rhythm, clones a voice from 3 seconds.
    "studio": {"repos": ["mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16", "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit"], "tags": False},
}

state = {"model": None, "engine": None, "repo": None, "ref": None, "ref_text": None, "rate": 24000, "conds": False}


# Replies go to the real stdout; anything a library prints goes to stderr instead, so it can't garble a reply.
_replies = os.fdopen(os.dup(1), "w")
os.dup2(2, 1)
sys.stdout = sys.stderr


def reply(message):
    _replies.write(json.dumps(message) + "\n")
    _replies.flush()


def load(engine, ref=None, ref_text=None, repos=None):
    from mlx_audio.tts.utils import load_model
    spec = ENGINES.get(engine)
    if not spec:
        raise ValueError("Unknown voice engine.")
    errors = []
    for repo in repos or spec["repos"]:
        try:
            model = load_model(repo)
        except Exception as error:  # this one isn't on the hub (or won't load here): try the next
            errors.append(f"{repo}: {str(error).splitlines()[0][:160] if str(error) else type(error).__name__}")
            continue
        state.update(model=model, engine=engine, repo=repo, ref=ref, ref_text=ref_text, conds=False,
                     rate=int(getattr(model, "sample_rate", 24000) or 24000))
        # Chatterbox learns the voice once up front, instead of on every sentence.
        if ref and os.path.exists(ref) and hasattr(model, "prepare_conditionals"):
            try:
                model.prepare_conditionals(ref)
                state["conds"] = True
            except Exception:
                state["conds"] = False
        return {"engine": engine, "repo": repo, "tags": spec["tags"], "rate": state["rate"]}
    raise RuntimeError("None of the voice models would load: " + " | ".join(errors)[:900])


def say(text):
    import numpy as np
    model = state["model"]
    if model is None:
        raise RuntimeError("No voice loaded yet.")
    kwargs = {"text": text}
    if state["ref"] and os.path.exists(state["ref"]) and not state.get("conds"):
        kwargs["ref_audio"] = state["ref"]
        if state["engine"] == "studio" and state["ref_text"]:
            kwargs["ref_text"] = state["ref_text"]
    started = time.time()
    pieces = []
    for result in model.generate(**kwargs):
        audio = np.asarray(result.audio, dtype=np.float32).reshape(-1)
        if audio.size:
            pieces.append(audio)
        rate = getattr(result, "sample_rate", None)
        if rate:
            state["rate"] = int(rate)
    if not pieces:
        raise RuntimeError("The voice made no sound.")
    audio = np.concatenate(pieces)
    if not np.isfinite(audio).all() or float(np.max(np.abs(audio))) < 1e-5:
        raise RuntimeError("The voice made empty or broken audio.")
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    seconds = len(pcm) / state["rate"]
    return {"pcm": base64.b64encode(pcm.tobytes()).decode(), "rate": state["rate"], "seconds": round(seconds, 2),
            "rtf": round((time.time() - started) / max(seconds, 0.01), 3)}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except ValueError:
            continue
        ident, op = request.get("id"), request.get("op")
        try:
            if op == "ping":
                result = {"pid": os.getpid(), "engine": state["engine"], "repo": state["repo"]}
            elif op == "load":
                result = load(request.get("engine") or "expressive", request.get("ref"), request.get("ref_text"), request.get("repos"))
            elif op == "say":
                result = say(str(request.get("text") or "")[:600])
            elif op == "quit":
                reply({"id": ident, "ok": True})
                return
            else:
                raise ValueError("Unknown request.")
            reply({"id": ident, "ok": True, **result})
        except Exception as error:
            reply({"id": ident, "ok": False, "error": (str(error) or type(error).__name__)[:1000]})


if __name__ == "__main__":
    main()
