"""A stand-in brain for the brain-process tests: it streams, it can be stopped, and it can crash on cue."""
import os
import time

from luma.llm.inference import GenerationCancelled


def _plan_here(messages, memories, tools, mode, profile=None, cancel_event=None, on_text=None):
    how = os.environ.get("FAKE_BRAIN", "ok")
    if how == "crash" or (how == "crash_on_gpu" and os.environ.get("LUMA_GPU_LAYERS") != "0"):
        os._exit(139)  # what a native segfault looks like from outside
    if how == "slow":
        for _ in range(400):
            if cancel_event is not None and cancel_event.is_set():
                raise GenerationCancelled("Conversation interrupted.")
            time.sleep(0.01)
    if how == "error":
        raise ValueError("The local model returned an invalid proposal. No action was taken.")
    if on_text is not None:
        on_text("Hi ")
        on_text("there")
    return {"type": "reply", "text": "Hi there", "gpu": os.environ.get("LUMA_GPU_LAYERS", "-1")}


def _rewrite_here(prompt, max_tokens=90, cancel_event=None, on_text=None):
    return prompt.upper()
