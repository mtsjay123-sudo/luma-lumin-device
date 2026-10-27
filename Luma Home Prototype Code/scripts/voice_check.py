"""Listen to Luma's voice samples and check each one says exactly what it should.

Speech models can skip a word, repeat one, mumble, or babble on past the end. This transcribes every
sample from scripts/voice_samples.py with Whisper and compares it to the words it was asked to say:

    python scripts/voice_check.py out/        (needs faster-whisper; CI installs it in its own venv)

Writes out/check.json and prints a table: word error rate per file (0 is perfect) and what was heard.
Then UTMOSv2 predicts how natural each voice sounds to people (1 to 5) and ranks the voices, among the ones that
say their words right. Only the standard library, faster-whisper, numpy and (if installed) utmosv2 are used.
"""
import json
import re
import sys
import wave
from pathlib import Path

GOOD = 0.15  # at most about one word in seven heard differently (Whisper itself mishears some)

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
ORDINAL = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}
# Ways of writing the same spoken words.
SAME = [(r"\bok\b", "okay"), (r"\bgotcha\b|\bgot ya\b|\bgot you\b|\bgotchya\b", "gotchu"), (r"\bgoing to\b", "gonna"), (r"\bwant to\b", "wanna"),
        (r"\bgot to\b", "gotta"), (r"\bkind of\b", "kinda"), (r"\bmom'?s\b", "moms"), (r"\buh+m*\b|\bum+\b|\bhm+\b|\bmm+\b", ""),
        (r"\bnah+\b", "nah"), (r"\byeah\b", "yeah")]


def number_words(n):
    if n < 20:
        return ONES[n]
    tens, ones = divmod(n, 10)
    return TENS[tens] + ("" if not ones else " " + ONES[ones]) if n < 100 else str(n)


def ordinal_words(n):
    words = number_words(n).split()
    last = words[-1]
    words[-1] = ORDINAL.get(last) or (last[:-1] + "ieth" if last.endswith("y") else last + "th")
    return " ".join(words)


def normalize(text):
    t = (text or "").lower().replace("’", "'").replace("-", " ")
    t = re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", lambda m: ordinal_words(int(m.group(1))), t)
    t = re.sub(r"\b\d{1,2}\b", lambda m: number_words(int(m.group(0))), t)
    t = re.sub(r"[^a-z0-9' ]+", " ", t)
    for pattern, same in SAME:
        t = re.sub(pattern, same, t)
    return [w.strip("'") for w in t.split() if w.strip("'")]


def word_error_rate(expected, heard):
    a, b = normalize(expected), normalize(heard)
    if not a:
        return 0.0 if not b else 1.0
    row = list(range(len(b) + 1))
    for i, word in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, other in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (word != other))
    return round(row[-1] / len(a), 3)


def seconds(path):
    with wave.open(str(path)) as clip:
        return clip.getnframes() / float(clip.getframerate())


def samples(path):
    """The WAV as 16 kHz mono floats, read here so Whisper doesn't need PyAV (whose newer versions it trips over)."""
    import numpy as np
    with wave.open(str(path)) as clip:
        rate, channels = clip.getframerate(), clip.getnchannels()
        pcm = np.frombuffer(clip.readframes(clip.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        pcm = pcm.reshape(-1, channels).mean(axis=1)
    if rate != 16000 and len(pcm):
        n = int(round(len(pcm) * 16000 / rate))
        pcm = np.interp(np.linspace(0, len(pcm) - 1, n), np.arange(len(pcm)), pcm).astype(np.float32)
    return pcm


def naturalness(out, results):
    """How natural each voice sounds to people, predicted by UTMOSv2 (MIT; first place in 7 of 16 metrics at the VoiceMOS
    Challenge 2024): a score from 1 to 5 per file, averaged per voice. A voice that gets its words wrong can't win."""
    try:
        import utmosv2
        model = utmosv2.create_model(pretrained=True)
    except Exception as error:  # not installed here: the word check still stands on its own
        return {"naturalness_error": str(error)[:300]}
    voices = {}
    for name, r in results.items():
        if name == "reference.wav":
            continue
        try:
            mos = float(model.predict(input_path=str(out / name)))
        except Exception as error:
            r["mos_error"] = str(error)[:200]
            continue
        r["mos"] = round(mos, 3)
        voices.setdefault(name.split("-")[0].replace(".wav", ""), []).append((mos, r["wer"]))
    ranking = []
    for voice, rows in voices.items():
        mos = sum(m for m, _ in rows) / len(rows)
        wer = sum(w for _, w in rows) / len(rows)
        ranking.append({"voice": voice, "mos": round(mos, 3), "wer": round(wer, 3), "files": len(rows), "says_it_right": wer <= GOOD})
    ranking.sort(key=lambda r: (not r["says_it_right"], -r["mos"]))
    return {"ranking": ranking, "most_human": ranking[0]["voice"] if ranking and ranking[0]["says_it_right"] else None}


def main(out, size="small.en"):
    out = Path(out)
    summary = json.loads((out / "summary.json").read_text())
    from faster_whisper import WhisperModel
    model = WhisperModel(size, device="cpu", compute_type="int8")
    results = {}
    for name, expected in sorted(summary.get("files", {}).items()):
        path = out / name
        if not path.exists():
            continue
        segments, _ = model.transcribe(samples(path), language="en", beam_size=5, vad_filter=False, condition_on_previous_text=False)
        heard = " ".join(s.text.strip() for s in segments).strip()
        wer = word_error_rate(expected, heard)
        results[name] = {"wer": wer, "ok": wer <= GOOD, "seconds": round(seconds(path), 2), "expected": expected, "heard": heard}
    voices = {}
    for name, r in results.items():
        voices.setdefault(name.split("-")[0].replace(".wav", ""), []).append(r["wer"])
    report = {"model": f"faster-whisper {size}", "by_voice": {v: round(sum(w) / len(w), 3) for v, w in voices.items()}, "files": results}
    report.update(naturalness(out, results))
    (out / "check.json").write_text(json.dumps(report, indent=2))
    print(f"{'file':28} {'WER':>6}  {'sec':>5}  heard")
    for name, r in results.items():
        print(f"{name:28} {r['wer']:6.3f}  {r['seconds']:5.1f}  {'' if r['ok'] else '!! '}{r['heard']}")
    print("average word error rate by voice:", json.dumps(report["by_voice"]))
    if report.get("ranking"):
        print("how human each voice sounds (UTMOSv2, 1 to 5), among the ones that say their words right:")
        for row in report["ranking"]:
            print(f"  {row['voice']:12} {row['mos']:.2f}  (word error {row['wer']:.3f}){'  <- most human' if row is report['ranking'][0] else ''}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "voice-samples", *sys.argv[2:3])
