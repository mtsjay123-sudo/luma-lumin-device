"""Explain anything as a video: a narrated explainer with chapters and captions that light up word by word.

Luma writes the script (chapters of short spoken lines, each with a few words to show on screen), reads it
in its own voice, draws every frame in its own look (the warm night, Instrument Serif and Geist), and FFmpeg
puts it together. Out come a 16:9 video for YouTube and the web, a 9:16 one for TikTok, Reels and Shorts,
captions (.srt), the script, and a poster frame. Chapters are written into the video, so players show them.

Everything happens on this computer. Luma's own idea and code: nothing here comes from other explainer tools.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

RATE = 24000                      # narration sample rate (Luma's voice speaks at 24 kHz)
WORDS_PER_SECOND = 2.6            # for timing when there's no voice to measure
GAP = 0.28                        # breath between lines
CARD = 1.7                        # a chapter's title card, in seconds
OPENING = 2.4                     # the title at the very start
INK, DIM, FAINT = (246, 241, 234), (128, 121, 112), (246, 241, 234, 38)  # text is drawn opaque: DIM is the muted ink, already mixed
AMBER, AMBER_SOFT = (255, 184, 107), (242, 201, 160)
FONTS = Path(__file__).resolve().parents[1] / "control" / "web" / "desktop" / "fonts"
LAYOUTS = {
    "wide": {"size": (1920, 1080), "margin": 120, "top": 70, "chapter": 64, "show": 118, "show_y": 330, "show_w": 1560, "caption": 46,
             "caption_y": 800, "caption_w": 1500, "bar_y": 1000, "label": 22, "number": 230, "title": 118},
    "tall": {"size": (1080, 1920), "margin": 80, "top": 120, "chapter": 54, "show": 100, "show_y": 600, "show_w": 920, "caption": 52,
             "caption_y": 1330, "caption_w": 920, "bar_y": 1760, "label": 20, "number": 200, "title": 104},
}


class ExplainerError(ValueError):
    """What went wrong, in plain words."""


# -- the script ---------------------------------------------------------------------------
def parse_script(script, title=""):
    """Luma's script -> chapters. A line starting with # is a chapter; every other line is one spoken line, optionally
    "words to show :: what's said". [{"title": ..., "lines": [{"say": ..., "show": ...}]}]"""
    chapters = []
    for raw in str(script or "").splitlines():
        line = raw.strip().lstrip("-*• ").strip()
        if not line:
            continue
        if raw.strip().startswith("#"):
            name = line.lstrip("#").strip(" :")
            name = re.sub(r"^(?:chapter\s*)?\d+[.):\s-]+", "", name, flags=re.I).strip() or f"Part {len(chapters) + 1}"
            chapters.append({"title": name[:60], "lines": []})
            continue
        show, say = (line.split("::", 1) + [""])[:2] if "::" in line else ("", line)
        say = " ".join(say.split()).strip(' "')
        if not say:
            continue
        if not chapters:
            chapters.append({"title": (title or "Introduction")[:60], "lines": []})
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", say):  # one sentence per spoken line
            if sentence.strip():
                chapters[-1]["lines"].append({"say": sentence.strip()[:240], "show": " ".join(show.split()).strip(' "')[:70]})
    chapters = [c for c in chapters if c["lines"]]
    for c in chapters:
        for line in c["lines"]:
            line["show"] = line["show"] or c["title"]
    if not chapters:
        raise ExplainerError("There's no script to read yet.")
    return chapters[:8]


def word_count(chapters):
    return sum(len(line["say"].split()) for c in chapters for line in c["lines"])


# -- the voice ----------------------------------------------------------------------------
def wav_seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / float(w.getframerate())


def silence(path, secs):
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"\x00\x00" * int(RATE * secs))


def _ffmpeg():
    from luma.skills.video import ffmpeg
    return ffmpeg()


def _to_rate(src, dst):
    subprocess.run([_ffmpeg(), "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", str(RATE), "-sample_fmt", "s16", str(dst)],
                   check=True, capture_output=True, timeout=120)


def default_voice(text, path):
    """Luma's own voice when it's installed; the Mac's built-in voice otherwise; None (no sound) if neither is here."""
    try:
        from luma.audio import tts
        if tts.ready():
            raw = Path(path).with_suffix(".raw.wav")
            tts.synthesize(tts.spoken_text(text), str(raw))
            _to_rate(raw, path)
            raw.unlink(missing_ok=True)
            return "luma"
    except Exception:
        pass
    if sys.platform == "darwin":
        try:
            aiff = Path(path).with_suffix(".aiff")
            subprocess.run(["say", "-o", str(aiff), text], check=True, capture_output=True, timeout=120)
            _to_rate(aiff, path)
            aiff.unlink(missing_ok=True)
            return "mac"
        except Exception:
            pass
    return None


def word_times(words, start, length):
    """Each word's (start, end) across a spoken line, by how long the word is (a comma or full stop adds a beat)."""
    weights = [len(w) + 2 + (3 if re.search(r"[,;:]$", w) else 5 if re.search(r"[.!?]$", w) else 0) for w in words]
    total = float(sum(weights)) or 1.0
    out, at = [], start
    for w, weight in zip(words, weights):
        span = length * weight / total
        out.append((at, at + span, w))
        at += span
    return out


# -- the look -----------------------------------------------------------------------------
def _font(name, size):
    from PIL import ImageFont
    files = {"serif": "instrument-serif.woff2", "sans": "geist.woff2"}
    try:
        return ImageFont.truetype(str(FONTS / files[name]), size)
    except Exception:
        for fallback in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            if Path(fallback).exists():
                return ImageFont.truetype(fallback, size)
        return ImageFont.load_default(size)


def _wrap(draw, text, font, width, max_lines=3):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if cur and draw.textlength(trial, font=font) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;:") + "…"
    return lines


def background(size, accent=AMBER):
    """The warm night: a deep gradient with a soft glow, drawn once per video."""
    from PIL import Image, ImageDraw, ImageFilter
    w, h = size
    top, bottom = (24, 19, 15), (9, 8, 8)
    grad = Image.new("RGB", (1, 256))
    for y in range(256):
        t = y / 255
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    img = grad.resize((w, h))
    glow = Image.new("RGB", (w // 4, h // 4), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    gx, gy = (w // 4) * 0.78, (h // 4) * 0.18
    r = min(w, h) // 4 * 0.55
    d.ellipse([gx - r, gy - r, gx + r, gy + r], fill=tuple(int(c * 0.32) for c in accent))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=min(w, h) // 20)).resize((w, h))
    from PIL import ImageChops
    return ImageChops.add(img, glow)


class Painter:
    """Draws every frame of one layout. Static parts are drawn once per line; only the captions and the chapter bar
    change from word to word."""

    def __init__(self, layout, title, chapters, timeline, accent=AMBER):
        from PIL import ImageDraw  # noqa: F401
        self.L = LAYOUTS[layout]
        self.size = self.L["size"]
        self.title, self.chapters, self.timeline, self.accent = title, chapters, timeline, accent
        self.bg = background(self.size, accent)
        self.f_top = _font("sans", 30 if layout == "wide" else 34)
        self.f_chapter = _font("serif", self.L["chapter"])
        self.f_show = _font("serif", self.L["show"])
        self.f_caption = _font("sans", self.L["caption"])
        self.f_label = _font("sans", self.L["label"])
        self.f_number = _font("serif", self.L["number"])
        self.f_title = _font("serif", self.L["title"])

    def _canvas(self):
        return self.bg.copy()  # RGB, so see-through colors blend into it

    def _top(self, draw, chapter_index):
        m, y = self.L["margin"], self.L["top"]
        draw.text((m, y), self.title.upper()[:48], font=self.f_top, fill=DIM)
        if chapter_index is not None:
            count = f"{chapter_index + 1:02d} / {len(self.chapters):02d}"
            draw.text((self.size[0] - m - draw.textlength(count, font=self.f_top), y), count, font=self.f_top, fill=DIM)

    def _bar(self, draw, t):
        """The chapter bar: one segment per chapter, as long as the chapter, filled up to now."""
        m, y = self.L["margin"], self.L["bar_y"]
        width, gap = self.size[0] - 2 * m, 10
        spans = self.timeline["chapters"]
        total = sum(b - a for a, b in spans) or 1.0
        usable = width - gap * (len(spans) - 1)
        x = m
        for i, (a, b) in enumerate(spans):
            seg = max(8, usable * (b - a) / total)
            draw.rounded_rectangle([x, y, x + seg, y + 6], radius=3, fill=FAINT)
            done = 0 if t <= a else seg if t >= b else seg * (t - a) / (b - a)
            if done > 0:
                draw.rounded_rectangle([x, y, x + max(6, done), y + 6], radius=3, fill=self.accent)
            label = self.chapters[i]["title"]
            if i == len(spans) - 1:
                seg = m + width - x  # the last one ends exactly at the margin
                draw.rounded_rectangle([x, y, x + seg, y + 6], radius=3, fill=FAINT)
                if done > 0:
                    draw.rounded_rectangle([x, y, x + max(6, min(seg, done)), y + 6], radius=3, fill=self.accent)
            if draw.textlength(label, font=self.f_label) <= seg:
                draw.text((x, y - self.L["label"] - 14), label, font=self.f_label, fill=INK if a <= t < b else DIM)
            x += seg + gap

    def opening(self):
        img = self._canvas()
        from PIL import ImageDraw
        d = ImageDraw.Draw(img, "RGBA")
        m = self.L["margin"]
        lines = _wrap(d, self.title, self.f_title, self.size[0] - 2 * m, 3)
        h = self.L["title"] * 1.08
        y0 = self.size[1] * 0.42 - h * len(lines) / 2
        for i, line in enumerate(lines):
            d.text((m, y0 + i * h), line, font=self.f_title, fill=INK)
        d.text((m, y0 + len(lines) * h + 30), "Explained by Luma", font=self.f_chapter, fill=self.accent)
        self._bar(d, 0)
        return img

    def card(self, ci, t):
        img = self._canvas()
        from PIL import ImageDraw
        d = ImageDraw.Draw(img, "RGBA")
        m = self.L["margin"]
        self._top(d, ci)
        y = self.size[1] * 0.30
        d.text((m - 8, y), f"{ci + 1:02d}", font=self.f_number, fill=tuple(int(c * 0.55) for c in self.accent))
        lines = _wrap(d, self.chapters[ci]["title"], self.f_title, self.size[0] - 2 * m, 2)
        for i, line in enumerate(lines):
            d.text((m, y + self.L["number"] * 1.05 + i * self.L["title"] * 1.08), line, font=self.f_title, fill=INK)
        self._bar(d, t)
        return img

    def line_base(self, ci, show):
        img = self._canvas()
        from PIL import ImageDraw
        d = ImageDraw.Draw(img, "RGBA")
        m = self.L["margin"]
        self._top(d, ci)
        d.text((m, self.L["show_y"] - self.L["chapter"] * 1.6), self.chapters[ci]["title"], font=self.f_chapter, fill=AMBER_SOFT)
        for i, line in enumerate(_wrap(d, show, self.f_show, self.L["show_w"], 3)):
            d.text((m, self.L["show_y"] + i * self.L["show"] * 1.05), line, font=self.f_show, fill=INK)
        return img

    def spoken(self, base, words, current, t):
        """The line being said, the words so far in full white, this word in amber, the rest waiting in grey."""
        img = base.copy()
        from PIL import ImageDraw
        d = ImageDraw.Draw(img, "RGBA")
        f, width = self.f_caption, self.L["caption_w"]
        rows, row = [], []
        for i, w in enumerate(words):
            if row and d.textlength(" ".join(x for _, x in row + [(i, w)]), font=f) > width:
                rows.append(row)
                row = []
            row.append((i, w))
        if row:
            rows.append(row)
        rows = rows[-3:] if current >= sum(len(r) for r in rows[:-3]) else rows[:3]
        line_h = self.L["caption"] * 1.32
        y = self.L["caption_y"] - (len(rows) - 1) * line_h / 2
        space = d.textlength(" ", font=f)
        for r in rows:
            x = (self.size[0] - d.textlength(" ".join(w for _, w in r), font=f)) / 2
            for i, w in r:
                fill = self.accent if i == current else INK if i < current else DIM
                d.text((x, y), w, font=f, fill=fill)
                x += d.textlength(w, font=f) + space
            y += line_h
        self._bar(d, t)
        return img


# -- putting it together -------------------------------------------------------------------
def render(chapters, title, folder, voice="auto", layouts=("wide", "tall"), progress=None, accent=AMBER):
    """Make the explainer in folder/. voice: "auto" (Luma's voice, else the Mac's), a function(text, wav_path), or None
    for captions only. Returns {"videos": {layout: path}, "srt", "script", "poster", "duration", "voice", "chapters"}."""
    from luma.skills import video as v
    if voice == "auto":
        voice = default_voice
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    say = progress or (lambda message: None)
    title = " ".join(str(title or chapters[0]["title"]).split())[:80]
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "explainer"
    with tempfile.TemporaryDirectory(prefix="luma-explainer-") as work:
        work = Path(work)
        # 1. the voice, line by line, and the timeline from how long each line really takes
        say("Recording the narration")
        voice_used, clips, timeline = None, [], {"lines": [], "cards": [], "chapters": []}
        silence(work / "opening.wav", OPENING)
        clips.append(work / "opening.wav")
        at = OPENING
        n = 0
        for ci, chapter in enumerate(chapters):
            chapter_start = at
            card_wav = work / f"card{ci}.wav"
            silence(card_wav, CARD)
            clips.append(card_wav)
            timeline["cards"].append((ci, at, at + CARD))
            at += CARD
            for line in chapter["lines"]:
                n += 1
                wav = work / f"line{n:03d}.wav"
                used = voice(line["say"], wav) if voice else None
                if used and wav.exists():
                    voice_used = voice_used or used
                    length = wav_seconds(wav)
                else:
                    length = max(1.2, len(line["say"].split()) / WORDS_PER_SECOND + 0.3)
                    silence(wav, length)
                speaking = max(0.4, length - 0.15)
                words = word_times(line["say"].split(), at, speaking)
                timeline["lines"].append({"chapter": ci, "start": at, "end": at + length, "words": words, "show": line["show"], "say": line["say"]})
                clips.append(wav)
                gap = work / f"gap{n:03d}.wav"
                silence(gap, GAP)
                clips.append(gap)
                at += length + GAP
            timeline["chapters"].append((chapter_start, at))
        timeline["end"] = at
        narration = work / "narration.wav"
        with wave.open(str(narration), "w") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(RATE)
            for clip in clips:
                with wave.open(str(clip)) as w:
                    if w.getframerate() != RATE or w.getnchannels() != 1 or w.getsampwidth() != 2:
                        raise ExplainerError("The narration came out in a format I didn't expect.")
                    out.writeframes(w.readframes(w.getnframes()))
        # 2. chapters and captions
        meta = work / "chapters.txt"
        rows = [";FFMETADATA1", f"title={_meta(title)}", "artist=Luma"]
        for (a, b), chapter in zip(timeline["chapters"], chapters):
            rows += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(a * 1000)}", f"END={int(b * 1000)}", f"title={_meta(chapter['title'])}"]
        meta.write_text("\n".join(rows) + "\n", encoding="utf-8")
        srt_path = folder / f"{slug}.srt"
        srt_path.write_text(v.srt(v.caption_lines([w for line in timeline["lines"] for w in line["words"]])), encoding="utf-8")
        script_path = folder / f"{slug}-script.md"
        script_path.write_text(f"# {title}\n\n" + "\n\n".join(f"## {c['title']}\n\n" + "\n".join(f"- **{l['show']}**: {l['say']}" for l in c["lines"]) for c in chapters) + "\n",
                               encoding="utf-8")
        # 3. the frames, one per change on screen, and the video
        videos, poster = {}, None
        for layout in layouts:
            say(f"Drawing the {'vertical' if layout == 'tall' else 'widescreen'} frames")
            painter = Painter(layout, title, chapters, timeline, accent)
            frames = work / layout
            frames.mkdir()
            listing, k = ["ffconcat version 1.0"], 0

            def keep(img, seconds, name=None):
                nonlocal k
                k += 1
                path = frames / f"f{k:05d}.png"
                img.save(path, compress_level=1)
                listing.extend([f"file '{path.name}'", f"duration {max(seconds, 0.04):.3f}"])
                return path

            first = keep(painter.opening(), OPENING)
            if layout == "wide":
                poster = folder / f"{slug}-poster.png"
                poster.write_bytes(first.read_bytes())
            cards = {ci: (a, b) for ci, a, b in timeline["cards"]}
            last_ci = -1
            for line in timeline["lines"]:
                ci = line["chapter"]
                if ci != last_ci:
                    a, b = cards[ci]
                    keep(painter.card(ci, a), b - a)
                    last_ci = ci
                base = painter.line_base(ci, line["show"])
                words = [w for _, _, w in line["words"]]
                for i, (a, b, _) in enumerate(line["words"]):
                    keep(painter.spoken(base, words, i, a), b - a)
                tail = line["end"] - line["words"][-1][1] + GAP
                keep(painter.spoken(base, words, len(words), line["end"]), tail)
            listing.append(f"file 'f{k:05d}.png'")  # the last frame is held to the end
            (frames / "frames.txt").write_text("\n".join(listing) + "\n")
            say(f"Putting the {'vertical' if layout == 'tall' else 'widescreen'} video together")
            out = folder / (f"{slug}.mp4" if layout == "wide" else f"{slug}-vertical.mp4")
            cmd = [_ffmpeg(), "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(frames / "frames.txt"),
                   "-i", str(narration), "-f", "ffmetadata", "-i", str(meta), "-map", "0:v", "-map", "1:a", "-map_metadata", "2", "-map_chapters", "2",
                   "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-tune", "stillimage",
                   "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out)]
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            if done.returncode != 0:
                raise ExplainerError("FFmpeg couldn't put the video together: " + ((done.stderr or "").strip().splitlines() or ["unknown"])[-1][:200])
            videos[layout] = out
    return {"videos": videos, "srt": srt_path, "script": script_path, "poster": poster, "duration": round(timeline["end"], 1),
            "voice": voice_used, "chapters": [c["title"] for c in chapters], "words": word_count(chapters)}


def _meta(text):
    return re.sub(r"([=;#\\\n])", r"\\\1", str(text))
