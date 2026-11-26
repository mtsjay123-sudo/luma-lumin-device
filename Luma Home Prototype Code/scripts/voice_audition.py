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

    def say(words, pace=1.0):
        samples, rate = engine.create(words, voice="af_heart", speed=VOICE_SPEED * pace, lang="en-us")
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


# ---------------------------------------------------------------------------------------- the fifty pairs (B6) ---
# Does a voice that meets the moment sound more like someone who's with you? (docs/GAME_PLAN.md, B6: "judge listens to
# 50 pairs blind; the toned one wins at least 60%".) Each line is said twice by the classic voice: once flat, and once
# the way luma.audio.feel says it for that moment (slower with longer pauses for someone hurting, quicker and tighter
# for a laugh). Which comes first is shuffled, and the answer sheet is a separate file to open afterwards.
PAIRS = [
    ("grief", "I'm so sorry. Tell me about her, if you want to."),
    ("grief", "That's a lot to lose. I'm here, take your time."),
    ("grief", "He sounds like he was a good dog. Fourteen years is a whole chapter."),
    ("grief", "You don't have to be okay tonight."),
    ("grief", "I remember you talking about her. She mattered."),
    ("grief", "There's no right way to do this. You're doing it."),
    ("grief", "I'm not going anywhere. Say as much or as little as you want."),
    ("grief", "The first birthday without him was always going to be hard."),
    ("grief", "It makes sense that the house feels quiet."),
    ("grief", "You loved her well. That's what this hurt is."),
    ("upset", "That would shake anybody. Are you somewhere you can sit for a minute?"),
    ("upset", "Okay. One thing at a time. What happened first?"),
    ("upset", "You're not overreacting. That was a scary call to get."),
    ("upset", "I hear you. That's a lot for one afternoon."),
    ("upset", "Breathe with me for a second. Then tell me the rest."),
    ("upset", "That wasn't fair to you, and you didn't deserve it."),
    ("upset", "Of course you're rattled. Anyone would be."),
    ("upset", "We can figure out the next step in a bit. Right now, just tell me."),
    ("upset", "I'm sorry it went that way. You prepared so hard for it."),
    ("upset", "That's a hard thing to hear from someone you trust."),
    ("venting", "Three trips for one prescription? That's ridiculous."),
    ("venting", "They moved the deadline again? Of course they did."),
    ("venting", "No, you're right to be annoyed. That was your one day off."),
    ("venting", "He said that in front of everyone? Wow."),
    ("venting", "Two hours on hold and then they hang up. Unreal."),
    ("venting", "That's the third time this month. I'd be done too."),
    ("venting", "So you did all the work and she took the credit. Great."),
    ("venting", "You asked one simple thing. One."),
    ("venting", "Yeah, that would wreck anybody's evening."),
    ("venting", "The landlord again. What is it this time?"),
    ("playful", "Okay, but pineapple on pizza is a bold hill to pick."),
    ("playful", "You named the plant Gerald? I love Gerald already."),
    ("playful", "Bold move, wearing white to a spaghetti dinner."),
    ("playful", "So the plan is no plan. Classic."),
    ("playful", "A third coffee? Living dangerously, I see."),
    ("playful", "You beat your sister at Scrabble. Frame the board."),
    ("playful", "That's either a great idea or a great story. Possibly both."),
    ("playful", "Tell the cat I said hi. And that the vase had it coming."),
    ("playful", "Look at you, cooking on a Tuesday."),
    ("playful", "Fine, the blue one. But I'm noting my objection."),
    ("laughing", "No way. He actually wore the costume to the meeting?"),
    ("laughing", "Stop, that's so good. Then what happened?"),
    ("laughing", "She said that with a straight face? I can't."),
    ("laughing", "Ha! The dog ate the evidence. Perfect."),
    ("laughing", "That's the funniest thing I've heard all day."),
    ("laughing", "You locked yourself out twice? In one morning?"),
    ("laughing", "Okay, that's incredible. Please tell me there's a photo."),
    ("laughing", "And the cake just slid off? Oh no."),
    ("laughing", "He thought it was a costume party. Amazing."),
    ("laughing", "I can't believe that worked. You're a menace."),
]
BAR = 60      # percent of pairs the toned one has to win


def said(say, text, mood, expressive, paced):
    """One line as sound, in this mood."""
    from luma.audio import feel
    pieces = []
    for words, pause in plan(text, mood, expressive):
        if words.strip(" .,!?"):
            pieces.append(say(words, feel.pace(1.0)) if paced else say(words))
        pieces.append(np.zeros(int(pause / 1000 * RATE), dtype=np.float32))
    return np.concatenate(pieces) if pieces else np.zeros(1, dtype=np.float32)


def pairs(say, out, expressive=False, paced=True, seed=20261126):
    """Fifty files, each the same line twice, and the key that says which one was toned."""
    import json
    import random
    out.mkdir(parents=True, exist_ok=True)
    rng, key = random.Random(seed), {}
    sheet = ["# Fifty pairs: which one sounds more like someone who's with you?", "",
             "Each file says the same line twice, A and then B. One is said flat; the other is said the way Luma says it for",
             "that moment. Write a or b for each (or - for no difference) before opening KEY.json, then:", "",
             "    python scripts/voice_audition.py tally --key demo/voices/pairs/KEY.json --picks \"a b a - ...\"", ""]
    for n, (mood, text) in enumerate(PAIRS, 1):
        toned_first = rng.random() < 0.5
        flat, toned = said(say, text, "neutral", expressive, paced), said(say, text, mood, expressive, paced)
        first, second = (toned, flat) if toned_first else (flat, toned)
        write(out / f"pair-{n:02d}.wav", np.concatenate([first, np.zeros(int(1.4 * RATE), dtype=np.float32), second]))
        key[f"{n:02d}"] = "a" if toned_first else "b"
        sheet.append(f"- pair-{n:02d}: {text}  ____")
    from luma.audio import feel
    feel.reset()
    (out / "KEY.json").write_text(json.dumps({"toned": key, "what": "for each pair, which of A and B was the toned one"}, indent=1) + "\n")
    (out / "SHEET.md").write_text("\n".join(sheet) + "\n")
    return key


def tally(key, picks):
    """How often the listener picked the toned one. A dash is no difference, and counts against the bar."""
    toned = key["toned"]
    picks = [p.lower() for p in picks]
    if len(picks) != len(toned):
        raise SystemExit(f"{len(picks)} picks for {len(toned)} pairs")
    won = sum(pick == toned[name] for name, pick in zip(sorted(toned), picks))
    none = sum(pick not in ("a", "b") for pick in picks)
    share = round(100 * won / len(toned))
    return {"won": won, "of": len(toned), "no_difference": none, "share": share, "passed": share >= BAR}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "tally":
        import json
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--key", required=True)
        ap.add_argument("--picks", required=True, help='one for each pair, in order: "a b a - ..."')
        args = ap.parse_args()
        t = tally(json.loads(Path(args.key).read_text()), args.picks.split())
        print(f"The toned one was picked in {t['won']} of {t['of']} ({t['share']}%), no difference in {t['no_difference']}. "
              f"The bar is {BAR}%: {'met' if t['passed'] else 'not met'}.")
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=sorted(ENGINES), required=True)
    ap.add_argument("--out", default="out/voices")
    ap.add_argument("--pairs", action="store_true", help="the fifty pairs, flat against toned, for a blind listen (the classic voice)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    say, expressive = ENGINES[args.engine]()
    if args.pairs:
        if args.engine != "kokoro":
            raise SystemExit("The pairs are made with the classic voice: it's the one whose pace Luma sets.")
        pairs(say, out / "pairs")
        print(f"{len(PAIRS)} pairs in {out / 'pairs'}", flush=True)
        return
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
