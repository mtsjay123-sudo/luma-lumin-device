"""Render Luma's voice samples on a real Apple Silicon Mac, to listen to and compare.

Run in CI (macOS runner) or on a Mac with mlx-audio installed:
    LUMA_VOICE_PYTHON=$(which python) python scripts/voice_samples.py out/

Writes one WAV per line per voice:
  classic-*.wav     Luma's classic voice (Kokoro) with the new pauses, laughs-as-beats and slang said right
  expressive-*.wav  Chatterbox-Turbo, learning Luma's classic voice from one short line, with real laughs
  studio-*.wav      Qwen3-TTS 0.6B, learning the same voice
  dia-*.wav         Dia 1.6B (Nari Labs), made for conversation, with real laughs, continuing the same voice
  csm-*.wav         Sesame CSM 1B, a conversational model, continuing the same voice
  design-*.wav      Qwen3-TTS VoiceDesign: candidate voices for Luma's own identity, from a description
and summary.json with which model loaded, how fast it ran (real-time factor: under 1 is faster than real time),
and the words each file should say, for scripts/voice_check.py to check by ear.
"""
import json
import shutil
import sys
import time
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from luma.audio import natural, tts  # noqa: E402

LINES = [
    ("late", "Okay so, you're telling me he really showed up late again? 😭 Nah, that's crazy. What did you say to him?"),
    ("deep", "ngl gng, how hard you want me to think about this? Because I can deep dive... but if you just want my answer right now, I gotchu."),
    ("news", "Hmm, okay. It's Saturday, October twenty-fourth, and honestly the big story today is the Fed holding rates steady. Want the quick version, or the full rundown?"),
    ("bday", "Wait, your mom's birthday is Saturday? Bet. I'll remind you Friday morning so you're not scrambling lol."),
    ("care", "I hear you. That sounds really heavy... Take your time, I'm right here."),
    ("think", "Hmm... I'd go with the black one. It hides scuffs, and honestly, it still looks sharp a year from now."),
    ("friend", "Man, that hurts. First thing, you're not broken, you just felt it deep. Want to talk it through, or just sit with it for a bit?"),
]

DESIGNS = [
    ("warm", "A warm, playful young woman in her early twenties with a relaxed American accent, quick to laugh, confident and friendly, natural conversational pacing."),
    ("smooth", "A smooth, upbeat young African American woman, casual and expressive, with natural warmth, humor and a relaxed Southern lilt."),
    ("late-night", "A calm, soft-spoken young woman with a slightly husky voice, intimate and reassuring, like a close friend on a late-night phone call."),
]


def write(path, pcm, rate):
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(np.asarray(pcm, dtype=np.int16).tobytes())


def words(plan):
    """What a listener should hear: the spoken chunks, without the laugh and sigh cues."""
    return " ".join(chunk for chunk, _ in plan if not chunk.startswith("["))


def render(text, expressive):
    plan = tts.speech_plan(text, expressive=expressive)
    pieces, rate = [], None
    for chunk, pause in plan:
        pcm, r = tts._with_pause(tts._samples(chunk, "luma", None), pause)
        rate = rate or r
        pieces.append(tts._resample(pcm, r, rate))
    return np.concatenate(pieces), rate, plan


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    summary = {"lines": dict(LINES), "voices": {}, "files": {}}

    # 1. The classic voice, with the new conversation layer.
    natural._voice = None
    started = time.time()
    for name, text in LINES:
        pcm, rate, plan = render(text, expressive=False)
        write(out / f"classic-{name}.wav", pcm, rate)
        summary["files"][f"classic-{name}.wav"] = words(plan)
    summary["voices"]["classic"] = {"model": "Kokoro-82M", "seconds": round(time.time() - started, 1)}

    # 2 and 3. The new open voices, each learning Luma's classic voice from one paragraph. Each one on its own, and
    # rendered even when this runner is too slow for a live conversation, so they can be heard (the speed is reported).
    natural.MAX_RTF = float("inf")
    for engine in ("expressive", "studio", "dia", "csm"):
        natural.ENGINES = (engine,)
        v = natural.NaturalVoice()
        natural._voice = v
        misses, real_say = [], v.say

        def say(text, timeout=60, real_say=real_say, misses=misses):
            try:
                return real_say(text, timeout)
            except Exception as error:  # the classic voice says this phrase instead: note it, so it's not mistaken for the new voice
                misses.append(f"{text[:50]}: {error}")
                raise
        v.say = say
        started = time.time()
        status = v.prepare(engine, "luma", timeout=3600)
        entry = {"status": status, "load_seconds": round(time.time() - started, 1)}
        ref = natural._home() / "luma-ref-2-luma.wav"
        if ref.exists() and not (out / "reference.wav").exists():
            shutil.copy(ref, out / "reference.wav")  # what the new voices learn Luma's voice from
            summary["files"]["reference.wav"] = natural.REF_TEXT
        if status["state"] == "ready" and status["engine"] == engine:
            rtfs = []
            for name, text in LINES:
                try:
                    pcm, rate, plan = render(text, expressive=natural.active())
                    write(out / f"{engine}-{name}.wav", pcm, rate)
                    summary["files"][f"{engine}-{name}.wav"] = words(plan)
                    rtfs.append(v.rtf)
                except Exception as error:
                    entry.setdefault("errors", []).append(f"{name}: {error}")
            entry["rtf"] = rtfs
            entry["said_by_classic_voice"] = misses
            # How fast the smaller builds are, for Macs where the full model can't keep up.
            for repo in natural.FASTER.get(engine, []):
                try:
                    v._call("load", 3600, engine=engine, ref=str(ref), ref_text=natural.REF_TEXT, repos=[repo])
                    v._call("say", 300, text="Okay, I'm here.")
                    entry.setdefault("faster", {})[repo] = v._call("say", 300, text=natural.SPEED_LINE).get("rtf")
                except Exception as error:
                    entry.setdefault("faster", {})[repo] = str(error)[:200]
        summary["voices"][engine] = entry
        v.stop()
        natural._voice = None
        print(engine, json.dumps(entry, indent=1), flush=True)

    # 4. Candidate voices for Luma's own identity (a description, no real person's voice).
    try:
        from mlx_audio.tts.utils import load_model
        model = load_model("mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16")
        designs = {}
        for key, description in DESIGNS:
            started = time.time()
            audio = []
            line = "Okay so, you're telling me he really showed up late again? Nah, that's crazy. What did you say to him?"
            for result in model.generate_voice_design(text=line, language="English", instruct=description):
                audio.append(np.asarray(result.audio, dtype=np.float32).reshape(-1))
            pcm = (np.clip(np.concatenate(audio), -1, 1) * 32767).astype(np.int16)
            write(out / f"design-{key}.wav", pcm, 24000)
            summary["files"][f"design-{key}.wav"] = line
            designs[key] = {"description": description, "seconds": round(time.time() - started, 1)}
        summary["voices"]["design"] = designs
    except Exception as error:
        summary["voices"]["design"] = {"error": str(error)[:400]}

    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "voice-samples")
