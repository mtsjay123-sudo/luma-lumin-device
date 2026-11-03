"""Speech to text, measured: Whisper (what Luma uses now) against Moonshine (moonshine-ai/moonshine, MIT English models),
on the same clips, for speed and for getting the words right.

    python -I scripts/stt_bench.py out/        (out/ is the folder scripts/voice_samples.py wrote, with summary.json)

Each clip's words are known (summary.json), so the word error rate is exact. Writes out/stt_bench.json and prints a
markdown table for the run summary. A recognizer that isn't installed is skipped and said so.
"""
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from voice_check import samples, word_error_rate  # noqa: E402

MAX_CLIPS = 24


def whisper():
    from faster_whisper import WhisperModel
    model = WhisperModel("base.en", device="cpu", compute_type="int8")

    def hear(pcm):
        segments, _ = model.transcribe(pcm, beam_size=3, language="en", vad_filter=True, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segments)
    return hear


def moonshine(arch_name):
    def make():
        from moonshine_voice import ModelArch, get_model_for_language
        from moonshine_voice.transcriber import Transcriber
        path, arch = get_model_for_language("en", getattr(ModelArch, arch_name))
        model = Transcriber(path, arch)

        def hear(pcm):
            result = model.transcribe_without_streaming([float(x) for x in pcm], 16000)
            return " ".join(line.text.strip() for line in (result.lines or []))
        return hear
    return make


ENGINES = [("whisper base.en", whisper), ("moonshine small", moonshine("SMALL_STREAMING")), ("moonshine medium", moonshine("MEDIUM_STREAMING"))]


def main(out):
    out = Path(out)
    files = sorted((json.loads((out / "summary.json").read_text()).get("files") or {}).items())[:MAX_CLIPS]
    clips = [(name, expected, samples(out / name)) for name, expected in files if (out / name).exists()]
    report = {"clips": len(clips), "engines": {}}
    for label, make in ENGINES:
        try:
            hear = make()
            hear(clips[0][2]) if clips else None  # warm up: the first call loads everything
        except Exception as error:
            report["engines"][label] = {"error": f"{type(error).__name__}: {error}"[:200]}
            continue
        times, errors, heard = [], [], {}
        for name, expected, pcm in clips:
            start = time.perf_counter()
            text = hear(pcm)
            times.append(time.perf_counter() - start)
            errors.append(word_error_rate(expected, text))
            heard[name] = text
        report["engines"][label] = {"median_seconds": round(statistics.median(times), 3) if times else None,
                                    "mean_wer": round(sum(errors) / len(errors), 3) if errors else None, "heard": heard}
    (out / "stt_bench.json").write_text(json.dumps(report, indent=2))
    print(f"### Speech to text on {report['clips']} clips\n\n| Recognizer | Median seconds per clip | Word error rate |\n|---|---|---|")
    for label, row in report["engines"].items():
        if "error" in row:
            print(f"| {label} | didn't run: {row['error']} | |")
        else:
            print(f"| {label} | {row['median_seconds']} | {row['mean_wer']} |")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "out")
