"""Luma's video hands: the everyday edits, done on this computer with FFmpeg.

Make it vertical for TikTok, Reels and Shorts (9:16, the picture kept whole over a blurred fill, or cropped),
trim it, take out the dead air, even out the sound (to the -14 LUFS streaming services use), put captions on
it (Luma's own speech recognition writes them), and lay out a contact sheet so the owner (and Luma) can see
what's in it at a glance. Every edit writes a new file next to the original and never touches the original.

FFmpeg comes from the computer (Homebrew, or the one Luma Desktop installs with imageio-ffmpeg). Only FFmpeg
is needed, not ffprobe: what a file holds is read from FFmpeg's own description of it.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
AAC = ["-c:a", "aac", "-b:a", "160k"]
WEB = ["-movflags", "+faststart"]
VIDEO_KINDS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}


class VideoError(ValueError):
    """What went wrong, in plain words."""


def ffmpeg():
    """The FFmpeg to use, or a plain-words error saying how to get one."""
    found = os.environ.get("LUMA_FFMPEG") or shutil.which("ffmpeg")
    for candidate in ([found] if found else []) + ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if candidate and Path(candidate).exists():
            return candidate
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise VideoError("Video needs FFmpeg on this computer. Luma Desktop installs it on its next start; "
                         "on a Mac you can also run: brew install ffmpeg") from None


def _run(args, timeout=1800):
    try:
        out = subprocess.run([ffmpeg(), "-hide_banner", "-nostdin", "-y"] + [str(a) for a in args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise VideoError("That took too long, so Luma stopped it. Try a shorter clip.") from None
    if out.returncode != 0:
        last = [line for line in (out.stderr or "").strip().splitlines() if line.strip()][-1:] or ["unknown error"]
        raise VideoError(f"FFmpeg couldn't do that: {last[0][:240]}")
    return out


def probe(path):
    """{"duration": seconds, "width", "height", "fps", "audio": bool, "video": bool} from FFmpeg's description of the file."""
    path = Path(path)
    if not path.exists():
        raise VideoError(f"I can't find {path.name}.")
    out = subprocess.run([ffmpeg(), "-hide_banner", "-nostdin", "-i", str(path)], capture_output=True, text=True, timeout=60)
    text = out.stderr or ""
    info = {"duration": 0.0, "width": 0, "height": 0, "fps": 0.0, "audio": False, "video": False}
    m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if m:
        info["duration"] = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
    for line in text.splitlines():
        if "Stream #" not in line:
            continue
        if ": Video:" in line and not info["video"] and "attached pic" not in line:
            info["video"] = True
            size = re.search(r"\b(\d{2,5})x(\d{2,5})\b", line)
            if size:
                info["width"], info["height"] = int(size[1]), int(size[2])
            fps = re.search(r"([\d.]+) fps", line)
            if fps:
                info["fps"] = float(fps[1])
        elif ": Audio:" in line:
            info["audio"] = True
    if not info["video"] and not info["audio"]:
        raise VideoError(f"{path.name} doesn't look like a video or a recording I can open.")
    return info


def new_path(src, label, ext=".mp4"):
    """Next to the original, never over it: clip.mp4 -> clip-vertical.mp4, clip-vertical-2.mp4, ..."""
    src = Path(src)
    out = src.with_name(f"{src.stem}-{label}{ext}")
    n = 2
    while out.exists():
        out = src.with_name(f"{src.stem}-{label}-{n}{ext}")
        n += 1
    return out


def seconds(value):
    """'1:05' -> 65.0, '90' -> 90.0, '1:02:03.5' -> 3723.5."""
    if isinstance(value, (int, float)):
        return float(value)
    parts = str(value).strip().split(":")
    try:
        total = 0.0
        for part in parts:
            total = total * 60 + float(part)
        return total
    except ValueError:
        raise VideoError(f"I didn't understand the time {value!r}. Use seconds, or minutes:seconds like 1:05.") from None


def _audio_map(info):
    return (["-map", "0:a:0?"] + AAC) if info["audio"] else []


# -- the edits ------------------------------------------------------------------------
def vertical(src, out=None, fit="blur", size=(1080, 1920)):
    """9:16 for TikTok, Reels and Shorts. fit="blur": the whole picture over a blurred, darkened fill of itself;
    fit="crop": the middle of the picture, filling the frame."""
    info = probe(src)
    if not info["video"]:
        raise VideoError("There's no picture in that file to make vertical.")
    w, h = size
    out = Path(out or new_path(src, "vertical"))
    if fit == "crop":
        graph = f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1[v]"
    else:
        graph = (f"[0:v]split=2[a][b];[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=24:2,eq=brightness=-0.12[bg];"
                 f"[b]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]")
    _run(["-i", src, "-filter_complex", graph, "-map", "[v]"] + _audio_map(info) + X264 + WEB + [out])
    return out


def trim(src, start=0, end=None, out=None):
    """Keep from start to end (seconds or m:ss), frame-accurate."""
    info = probe(src)
    a, b = seconds(start or 0), (seconds(end) if end not in (None, "") else info["duration"])
    if b <= a:
        raise VideoError("The end has to come after the start.")
    out = Path(out or new_path(src, "trimmed"))
    _run(["-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src, "-map", "0:v:0?"] + _audio_map(info) + X264 + WEB + [out])
    return out


def loudness(src, out=None, target=-14.0, peak=-1.0):
    """Even out the sound to target LUFS (two passes: measure, then correct), the picture copied untouched."""
    info = probe(src)
    if not info["audio"]:
        raise VideoError("That file has no sound to even out.")
    measure = _run(["-i", src, "-vn", "-af", f"loudnorm=I={target}:TP={peak}:LRA=11:print_format=json", "-f", "null", "-"])
    found = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", measure.stderr, re.S)
    if found:
        m = json.loads(found.group(0))
        chain = (f"loudnorm=I={target}:TP={peak}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                 f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    else:
        chain = f"loudnorm=I={target}:TP={peak}:LRA=11"
    out = Path(out or new_path(src, "even-sound", Path(src).suffix if not info["video"] else ".mp4"))
    picture = ["-map", "0:v:0?", "-c:v", "copy"] if info["video"] else []
    _run(["-i", src] + picture + ["-map", "0:a:0", "-af", chain, "-ar", "48000"] + AAC + (WEB if info["video"] else []) + [out])
    return out


def quiet_spans(src, threshold_db=-35.0, min_seconds=0.6):
    """Where it's silent: [(start, end), ...]."""
    out = _run(["-i", src, "-vn", "-af", f"silencedetect=noise={threshold_db}dB:d={min_seconds}", "-f", "null", "-"])
    spans, start = [], None
    for line in out.stderr.splitlines():
        s = re.search(r"silence_start: (-?[\d.]+)", line)
        e = re.search(r"silence_end: ([\d.]+)", line)
        if s:
            start = max(0.0, float(s[1]))
        elif e and start is not None:
            spans.append((start, float(e[1])))
            start = None
    if start is not None:
        spans.append((start, probe(src)["duration"]))
    return spans


def keep_spans(duration, quiet, margin=0.15):
    """The parts to keep, with a little air left around the speech."""
    keep, at = [], 0.0
    for a, b in quiet:
        cut_from, cut_to = a + margin, b - margin
        if cut_to - cut_from < 0.3:
            continue
        if cut_from > at:
            keep.append((at, cut_from))
        at = max(at, cut_to)
    if duration - at > 0.05:
        keep.append((at, duration))
    return keep


def remove_dead_air(src, out=None, threshold_db=-35.0, min_seconds=0.6, margin=0.15):
    """Jump cuts: the silent stretches taken out, a little air left around the talking. Returns (path, seconds cut)."""
    info = probe(src)
    if not info["audio"]:
        raise VideoError("That file has no sound, so there's no dead air to find.")
    keep = keep_spans(info["duration"], quiet_spans(src, threshold_db, min_seconds), margin)
    cut = info["duration"] - sum(b - a for a, b in keep)
    if cut < 0.3 or not keep:
        raise VideoError("There's no dead air worth cutting in that one.")
    if len(keep) > 300:
        raise VideoError("That has too many pauses to cut in one go. Try a shorter clip.")
    parts, labels = [], ""
    for i, (a, b) in enumerate(keep):
        if info["video"]:
            parts.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}]")
        labels += (f"[v{i}]" if info["video"] else "") + f"[a{i}]"
    graph = ";".join(parts) + f";{labels}concat=n={len(keep)}:v={1 if info['video'] else 0}:a=1" + ("[v][a]" if info["video"] else "[a]")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(graph)
        script = f.name
    try:
        out = Path(out or new_path(src, "tight", ".mp4" if info["video"] else ".m4a"))
        maps = (["-map", "[v]"] + X264 if info["video"] else []) + ["-map", "[a]"] + AAC
        _run(["-i", src, "-filter_complex_script", script] + maps + (WEB if info["video"] else []) + [out])
    finally:
        os.unlink(script)
    return out, round(cut, 1)


def srt_time(t):
    ms = int(round(max(0.0, t) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def srt(lines):
    """[(start, end, text), ...] -> SRT text."""
    return "".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n\n" for i, (a, b, text) in enumerate(lines, 1))


def caption_lines(words, max_chars=38, max_seconds=3.0):
    """Words with times [(start, end, word), ...] -> caption lines short enough to read at a glance."""
    lines, cur = [], []
    for a, b, word in words:
        text = " ".join(w for _, _, w in cur + [(a, b, word)])
        if cur and (len(text) > max_chars or b - cur[0][0] > max_seconds):
            lines.append((cur[0][0], cur[-1][1], " ".join(w for _, _, w in cur)))
            cur = []
        cur.append((a, b, word))
        if re.search(r"[.!?]$", word):
            lines.append((cur[0][0], cur[-1][1], " ".join(w for _, _, w in cur)))
            cur = []
    if cur:
        lines.append((cur[0][0], cur[-1][1], " ".join(w for _, _, w in cur)))
    return lines


def transcribe_words(src):
    """What's said in the file, word by word with times, by Luma's own speech recognition (on this computer)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise VideoError("Captions need Luma's speech recognition, which isn't installed here yet.") from None
    with tempfile.TemporaryDirectory(prefix="luma-video-") as folder:
        wav = Path(folder) / "speech.wav"
        _run(["-i", src, "-vn", "-ac", "1", "-ar", "16000", wav])
        from luma.config import WHISPER_MODEL_SIZE
        model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(wav), language="en", word_timestamps=True, vad_filter=True)
        return [(w.start, w.end, w.word.strip()) for seg in segments for w in (seg.words or []) if w.word.strip()]


def captions(src, out=None, lines=None, burn=True):
    """Captions on the video. lines: [(start, end, text)] (otherwise Luma listens and writes them). burn=True puts them
    in the picture (what TikTok and Reels need); if this FFmpeg can't draw text, they're added as a captions track
    instead. Returns (video path, .srt path)."""
    info = probe(src)
    if lines is None:
        lines = caption_lines(transcribe_words(src))
    if not lines:
        raise VideoError("I didn't hear anything to caption.")
    out = Path(out or new_path(src, "captions"))
    srt_path = out.with_suffix(".srt")
    srt_path.write_text(srt(lines), encoding="utf-8")
    if burn and info["video"]:
        tall = info["height"] > info["width"]
        style = (f"FontName=Helvetica,FontSize={14 if tall else 18},Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
                 f"BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV={60 if tall else 36}")
        escaped = str(srt_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        try:
            _run(["-i", src, "-map", "0:v:0", "-vf", f"subtitles='{escaped}':force_style='{style}'"] + _audio_map(info) + X264 + WEB + [out])
            return out, srt_path
        except VideoError:
            pass  # no text drawing in this FFmpeg: a captions track still shows on phones and in players
    _run(["-i", src, "-i", srt_path, "-map", "0:v:0?", "-map", "0:a:0?", "-map", "1:0", "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
          "-metadata:s:s:0", "language=eng"] + WEB + [out])
    return out, srt_path


def contact_sheet(src, out=None, cols=4, rows=3, width=1600):
    """One picture with frames from across the whole video, so it can be seen at a glance."""
    info = probe(src)
    if not info["video"]:
        raise VideoError("There's no picture in that file.")
    n = cols * rows
    every = max(info["duration"], 0.1) / n
    out = Path(out or new_path(src, "sheet", ".jpg"))
    cell = max(64, width // cols)
    _run(["-i", src, "-vf", f"fps=1/{every:.4f},scale={cell}:-2,tile={cols}x{rows}:padding=4:margin=4:color=0x14121F", "-frames:v", "1", "-q:v", "3", out])
    return out


EDITS = {
    "vertical": "Make it vertical (9:16) for TikTok, Reels and Shorts",
    "trim": "Trim it to a start and end",
    "dead_air": "Take out the dead air",
    "loudness": "Even out the sound",
    "captions": "Put captions on it",
    "sheet": "Lay out a contact sheet",
}
