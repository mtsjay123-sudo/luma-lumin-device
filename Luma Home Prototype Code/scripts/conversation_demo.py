"""A full conversation with Luma, out loud: someone's lines in, Luma's real replies out, both sides spoken.

The person's lines are typed the way the owner types (fast, caps, "!!", slang), to hear whether Luma picks up their words
and their energy. Luma answers through everything she really runs (the brain, her notes, the second look), and says it
in her own voice. The person's lines are read in a second voice so the recording plays like a real call.

    LUMA_MODEL_PATH=... python scripts/conversation_demo.py --out out/demo

Writes conversation.wav (and conversation.mp3 when ffmpeg is here) and conversation.md, the words of both sides.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Written for this recording, in the owner's own way of typing. None of it is from a held-out test.
LINES = [
    "yooo luma whats good",
    "bro today was CRAZY i finally got the investor meeting locked in for friday!!",
    "ngl im kinda nervous tho what if they think the whole idea is dumb",
    "fr fr. ok should i lead with the lamp or the app",
    "bet. also my mom called me today she said shes proud of me lol",
    "do you ever get nervous??",
    "lmaooo ok ok. remind me friday at 9am to run the pitch one more time",
    "thank you luma fr you the realest",
]
THEM_VOICE = "am_michael"   # Kokoro, Apache-2.0: the person's side
LUMA_VOICE = "af_heart"     # Luma's own classic voice
GAP_MS = 450


def talk(lines, out):
    from luma.agent.runtime import Agent
    from luma.memory.store import Store
    from luma.audio import tts

    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp())
    store = Store(work / "s.db", work / "k")
    agent = Agent(store=store, use_model=True)
    turns = []
    for said in lines:
        started = time.monotonic()
        reply = agent.chat(said)
        text = str(reply.get("text") or reply.get("summary") or "").strip()
        turns.append((said, text, round(time.monotonic() - started, 1)))
        print(f"them: {said}\nluma: {text}  ({turns[-1][2]}s)\n", flush=True)
    store.close()

    pieces, rate = [], None
    for i, (said, text, _) in enumerate(turns):
        for who, words, voice in (("them", said, THEM_VOICE), ("luma", text, LUMA_VOICE)):
            if not words:
                continue
            path = work / f"{i:02d}-{who}.wav"
            tts.synthesize(words, str(path), voice=voice)
            with wave.open(str(path), "rb") as w:
                rate = rate or w.getframerate()
                pieces.append(w.readframes(w.getnframes()))
            pieces.append(b"\x00\x00" * int((rate or 24000) * GAP_MS / 1000))
    with wave.open(str(out / "conversation.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate or 24000)
        w.writeframes(b"".join(pieces))

    md = ["# A conversation with Luma", "", "Real replies from Luma's brain, said in her voice. The other side was typed the way the owner types.", ""]
    for said, text, secs in turns:
        md += [f"**Them:** {said}", "", f"**Luma:** {text}  _(answered in {secs}s)_", ""]
    (out / "conversation.md").write_text("\n".join(md))
    return turns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="out/demo")
    args = ap.parse_args(argv)
    talk(LINES, Path(args.out))


if __name__ == "__main__":
    main()
