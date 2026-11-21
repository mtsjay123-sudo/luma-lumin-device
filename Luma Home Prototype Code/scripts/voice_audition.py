#!/usr/bin/env python3
"""The same eight lines in every voice that can be tried, so they can be judged by ear.

    python scripts/voice_audition.py --engine kokoro --out out/voices            # Luma's classic voice
    python scripts/voice_audition.py --engine chatterbox --out out/voices        # Chatterbox (Resemble AI, MIT), on the CPU
    python scripts/voice_audition.py --engine chatterbox-turbo --out out/voices  # Chatterbox-Turbo (MIT): it can laugh and sigh

Why: on Nov 21, 2026 the owner heard the classic voice say these lines and said the words were right and the voice
wasn't human enough. A voice is judged by ears, never by a number, so this renders the same words through Luma's own
speaking pipeline (shorthand said in full, a person's pauses, a thinking sound, the first word said twice) in each
voice, one file per voice. GitHub's machines can fetch the models (.github/workflows/voice-audition.yml); the result is
committed to demo/voices/ on the branch.

Each engine uses its own stock voice: nobody's recording is cloned here. Only MIT, Apache-2.0 and BSD (rule 7).
"""
from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

# (name, the mood of the moment, what Luma says). The fifth and sixth were chosen because they get a stumble.
LINES = [
    ("hello", "neutral", "Hey. It's good to hear you. How was today?"),
    ("memory", "neutral", "Your mom's birthday is June 3. Want me to remind you the week before?"),
    ("friend", "playful", "ngl that album is kinda mid, but the second track? That one's actually really good lol."),
    ("thinking", "neutral", "I'd go with the blue one, it goes with more of what you already wear a lot."),
    ("stumble", "neutral", "It's a lot to carry on a regular Monday, and you still showed up for it."),
    ("breath", "neutral", "It's more than most people manage on a Sunday, because you care how it lands."),
    ("rough_day", "venting", "Oof. In front of everyone? That would sting for anybody. What did they go after?"),
    ("what_are_you", "neutral", "I'm Luma. A presence, not a person. I live in the lamp, and I'm here with you."),
]
RATE = 24000


def plan(text, mood, expressive):
    """Luma's own plan for saying it: [(words, pause after in ms)]."""
    from luma.audio import feel, tts
    feel.set_mood(mood)
    return tts.speech_plan(text, expressive=expressive)


def resample(samples, rate, target=RATE):
    if rate == target or not len(samples):
        return samples.astype(np.float32)
    n = int(round(len(samples) * target / rate))
    return np.interp(np.linspace(0, len(samples) - 1, n), np.arange(len(samples)), samples).astype(np.float32)


def kokoro():
    from luma.audio import tts
    from luma.config import VOICE_SPEED
    engine = tts._get_kokoro()

    def say(words):
        samples, rate = engine.create(words, voice="af_heart", speed=VOICE_SPEED, lang="en-us")
        return resample(np.asarray(samples, dtype=np.float32), rate)
    return say, False


def chatterbox(turbo=False):
    import torch
    torch.set_num_threads(max(1, torch.get_num_threads()))
    if turbo:
        from chatterbox.tts_turbo import ChatterboxTurboTTS as Model
    else:
        from chatterbox.tts import ChatterboxTTS as Model
    model = Model.from_pretrained(device="cpu")

    def say(words):
        with torch.inference_mode():
            wav = model.generate(words) if turbo else model.generate(words, exaggeration=0.6, cfg_weight=0.4)
        return resample(wav.squeeze().detach().cpu().numpy().astype(np.float32), model.sr)
    return say, turbo


ENGINES = {"kokoro": kokoro, "chatterbox": chatterbox, "chatterbox-turbo": lambda: chatterbox(turbo=True)}


def write(path, samples):
    peak = float(np.abs(samples).max()) or 1.0
    pcm = (np.clip(samples / max(peak, 1e-6) * 0.89, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=sorted(ENGINES), required=True)
    ap.add_argument("--out", default="out/voices")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    say, expressive = ENGINES[args.engine]()
    gap = np.zeros(int(0.8 * RATE), dtype=np.float32)
    whole, notes = [], [f"# {args.engine}: the same eight lines", ""]
    for name, mood, text in LINES:
        pieces = []
        for words, pause in plan(text, mood, expressive):
            if words.strip(" .,!?"):
                pieces.append(say(words))
            pieces.append(np.zeros(int(pause / 1000 * RATE), dtype=np.float32))
        line = np.concatenate(pieces) if pieces else np.zeros(1, dtype=np.float32)
        whole += [line, gap]
        notes.append(f"- **{name}** ({len(line) / RATE:.1f} s): {' '.join(words for words, _ in plan(text, mood, expressive))}")
        print(notes[-1], flush=True)
    write(out / f"{args.engine}.wav", np.concatenate(whole))
    (out / f"{args.engine}.md").write_text("\n".join(notes) + "\n")


if __name__ == "__main__":
    main()
