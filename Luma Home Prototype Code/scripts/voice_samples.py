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

ENGINE_BUDGET = 15 * 60  # seconds of rendering per new voice, at most

DESIGNS = [
    ("warm", "A warm, playful young woman in her early twenties with a relaxed American accent, quick to laugh, confident and friendly, natural conversational pacing."),
    ("smooth", "A smooth, upbeat young African American woman, casual and expressive, with natural warmth, humor and a relaxed Southern lilt."),
    ("late-night", "A calm, warm young woman with a slightly low, smooth voice, relaxed and reassuring, speaking clearly at a normal volume, "
                   "like a close friend on a late-night phone call."),
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


def render_with(v, engine, text, entry, restarts=2):
    """Every phrase made by this engine itself, never quietly by the classic voice (that would rank the classic voice
    under the new one's name). If the engine stops (a GPU hang, a timeout), it's started again and the phrase retried."""
    plan = tts.speech_plan(text, expressive=bool(v.tags))
    pieces, rate = [], None
    for chunk, pause in plan:
        last = None
        for _ in range(3):
            if not v.ready():
                if entry.get("restarts", 0) >= restarts:
                    raise RuntimeError(f"it stopped and didn't come back: {v.note or last}")
                entry["restarts"] = entry.get("restarts", 0) + 1
                v.state = "off"
                if v.prepare(engine, "luma", timeout=1800)["state"] != "ready" or v.engine != engine:
                    raise RuntimeError(f"it stopped and wouldn't start again: {v.note or last}")
            try:
                made = v.say(chunk, 300)
                entry.setdefault("rtf", []).append(v.rtf)
                break
            except Exception as error:
                last = error
        else:
            raise RuntimeError(f"couldn't say {chunk[:40]!r}: {last}")
        pcm, r = tts._with_pause(made, pause)
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
        natural._voice = None  # nothing here may fall back to the classic voice: render_with talks to this engine only
        started = time.time()
        status = v.prepare(engine, "luma", timeout=3600)
        entry = {"status": status, "load_seconds": round(time.time() - started, 1)}
        ref = natural._home() / "luma-ref-2-luma.wav"
        if ref.exists() and not (out / "reference.wav").exists():
            shutil.copy(ref, out / "reference.wav")  # what the new voices learn Luma's voice from
            summary["files"]["reference.wav"] = natural.REF_TEXT
        if status["state"] == "ready" and status["engine"] == engine:
            began = time.time()
            for name, text in LINES:
                if time.time() - began > ENGINE_BUDGET:  # one slow engine can't take the whole contest's time
                    entry.setdefault("errors", []).append(f"{name}: out of time on this Mac (over {ENGINE_BUDGET // 60} minutes for this voice)")
                    continue
                try:
                    pcm, rate, plan = render_with(v, engine, text, entry)
                    write(out / f"{engine}-{name}.wav", pcm, rate)
                    summary["files"][f"{engine}-{name}.wav"] = words(plan)
                except Exception as error:
                    entry.setdefault("errors", []).append(f"{name}: {error}")
            # How fast the smaller builds are, for Macs where the full model can't keep up.
            for repo in (natural.FASTER.get(engine, []) if time.time() - began < ENGINE_BUDGET else []):
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
        (out / "summary.json").write_text(json.dumps(summary, indent=2))  # saved as it goes: a run cut short still gets checked

    # 4. Candidate voices for Luma's own identity (a description, no real person's voice).
    try:
        import mlx.core as mx
        try:
            if not mx.metal.is_available():
                mx.set_default_device(mx.cpu)  # a virtual Mac with no usable graphics chip: the processor, slower but the same voice
        except Exception:
            mx.set_default_device(mx.cpu)
        from mlx_audio.tts.utils import load_model
        model = load_model("mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16")
        designs = {}
        for key, description in DESIGNS:
            started = time.time()
            line = "Okay so, you're telling me he really showed up late again? Nah, that's crazy. What did you say to him?"
            tries = 0
            for tries in range(1, 4):  # it samples, and now and then stops after a word or two: try again, like the live voice does
                audio = [np.asarray(result.audio, dtype=np.float32).reshape(-1)
                         for result in model.generate_voice_design(text=line, language="English", instruct=description)]
                pcm = (np.clip(np.concatenate(audio) if audio else np.zeros(0, np.float32), -1, 1) * 32767).astype(np.int16)
                if pcm.size and natural.sounds_right(line, pcm.size / 24000):
                    break
            write(out / f"design-{key}.wav", pcm, 24000)
            summary["files"][f"design-{key}.wav"] = line
            designs[key] = {"description": description, "seconds": round(time.time() - started, 1), "tries": tries}
        summary["voices"]["design"] = designs
    except Exception as error:
        summary["voices"]["design"] = {"error": str(error)[:400]}

    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "voice-samples")
