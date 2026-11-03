"""Video: explain anything as a narrated video, and edit the owner's own videos.

Explainer: the brain writes a short script in chapters (each line: a few words to show, one sentence to say),
then luma.work.explainer reads it in Luma's voice, draws every frame and puts the video together: 16:9 and
9:16, captions that light up word by word, a chapter bar, chapters in the file, an .srt and the script.

Video edit: the everyday edits on a video the owner added to the project (luma.skills.video), in order, each
step building on the last, the original never touched.
"""
from __future__ import annotations

import re
from pathlib import Path

from luma.work.studios.base import Result, Studio, check, text

EDIT_WORDS = [
    ("trim", r"\b(?:trim|cut (?:it )?(?:down|from|to|between)|keep (?:only )?(?:from|the first|the last)|shorten)\b"),
    ("dead_air", r"\b(?:dead air|silences?|pauses?|jump ?cuts?|tighten|ums?\b)"),
    ("loudness", r"\b(?:loud(?:ness|er)?|volume|even (?:out )?the (?:sound|audio)|normali[sz]e|levels?)\b"),
    ("vertical", r"\b(?:vertical|9 ?: ?16|portrait|tiktok|reels?|shorts|stories)\b"),
    ("captions", r"\b(?:captions?|subtitles?|subs)\b"),
    ("sheet", r"\b(?:contact sheet|storyboard|thumbnails?|overview of (?:the|my) (?:video|clip))\b"),
]
ORDER = ["trim", "dead_air", "loudness", "vertical", "captions", "sheet"]
TIME = r"(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)?"


class Explainer(Studio):
    name, agent, title, tier = "video", "video", "Explainer video", "heavy"
    description = ("Write a narrated explainer video. title: the video's title, under 8 words. script: 2 to 5 chapters. Each chapter starts with "
                   "a line '# Chapter title' (2 to 5 words), then 2 to 5 lines, each written 'words on screen :: one spoken sentence'. Spoken "
                   "sentences are short (under 22 words), plain and friendly, said the way a person talks, and true: use the research and real "
                   "numbers, never filler or made-up facts. Words on screen are the idea in 2 to 6 words, not a repeat of the sentence. "
                   "formats: wide, vertical or both (both unless the request names one).")
    fields = {"title": "string", "script": "text", "formats": "text"}

    def make(self, ctx, args):
        from luma.work import explainer
        title = text(args.get("title"), 80) or ctx.project.get("name") or "Explainer"
        chapters = explainer.parse_script(args.get("script"), title)
        if explainer.word_count(chapters) > 900:
            raise ValueError("That script is too long for one explainer. Keep it under about six minutes.")
        wanted = str(args.get("formats") or "both").lower()
        layouts = tuple(l for l, words in (("wide", ("wide", "both", "16:9", "youtube")), ("tall", ("vertical", "both", "9:16", "tiktok", "reels", "shorts")))
                        if any(w in wanted for w in words)) or ("wide", "tall")
        folder = Path(ctx.folder) / "video"
        out = explainer.render(chapters, title, folder, layouts=layouts, progress=ctx.progress)
        rel = lambda p: str(Path(p).relative_to(ctx.folder))
        files = [rel(p) for p in out["videos"].values()] + [rel(out["srt"]), rel(out["script"])] + ([rel(out["poster"])] if out["poster"] else [])
        minutes, secs = divmod(int(round(out["duration"])), 60)
        voice = {"luma": "in Luma's voice", "mac": "in the Mac's voice (Luma's own voice isn't installed yet)", None: "with no voice (no voice is installed here yet)"}[out["voice"]]
        summary = (f"{title}: a {minutes}:{secs:02d} explainer in {len(chapters)} chapters ({', '.join(out['chapters'])}), narrated {voice}, "
                   f"{' and '.join({'wide': 'widescreen', 'tall': 'vertical'}[l] for l in out['videos'])}, with captions.")
        return Result(files=files, summary=summary, data={"title": title, "duration": out["duration"], "chapters": out["chapters"], "voice": out["voice"],
                                                          "videos": {k: rel(v) for k, v in out["videos"].items()}})

    def check(self, ctx, result):
        from luma.skills import video
        out = []
        for layout, rel_path in result.data.get("videos", {}).items():
            try:
                info = video.probe(Path(ctx.folder) / rel_path)
                size = (1920, 1080) if layout == "wide" else (1080, 1920)
                ok = info["video"] and info["audio"] and (info["width"], info["height"]) == size and info["duration"] >= 5
                out.append(check(f"{Path(rel_path).name} plays ({info['duration']:.0f}s, {info['width']}x{info['height']})", ok, "The video didn't come out right."))
            except ValueError as error:
                out.append(check(f"{Path(rel_path).name} plays", False, str(error)))
        out.append(check("it's narrated", bool(result.data.get("voice")), "No voice is installed here yet, so the video is silent with captions.", blocking=False))
        return out


def wanted_edits(request):
    """The edits a request asks for, in the order they should happen."""
    lowered = str(request or "").lower()
    found = {name for name, pattern in EDIT_WORDS if re.search(pattern, lowered)}
    return [e for e in ORDER if e in found]


def trim_times(request):
    """'trim it from 0:10 to 0:45' -> ("0:10", "0:45"); 'keep the first 30 seconds' -> (0, "30")."""
    lowered = str(request or "").lower()
    m = re.search(r"from\s+" + TIME + r"\s+(?:to|until|till|-)\s+" + TIME, lowered) or re.search(TIME + r"\s*(?:to|-)\s*" + TIME, lowered)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"first\s+" + TIME, lowered)
    if m:
        return "0", m.group(1)
    return None, None


class VideoEdit(Studio):
    name, agent, title, tier = "video_edit", "video", "Video edit", "light"
    description = ("Edit the owner's video. file: the video's name from the project's files. edits: comma-separated, from trim, dead_air, loudness, "
                   "vertical, captions, sheet. start and end: for trim, in seconds or m:ss.")
    fields = {"file": "string", "edits": "text", "start": "text", "end": "text"}

    def fallback(self, ctx, task):
        start, end = trim_times(task)
        return {"file": "", "edits": ",".join(wanted_edits(task)), "start": start or "", "end": end or ""}

    def make(self, ctx, args):
        from luma.skills import video
        videos = [f for f in ctx.files() if Path(str(f.get("path") if isinstance(f, dict) else f)).suffix.lower() in video.VIDEO_KINDS]
        names = [str(f.get("path") if isinstance(f, dict) else f) for f in videos]
        named = text(args.get("file"), 200)
        chosen = next((n for n in names if named and Path(n).name.lower() == Path(named).name.lower()), None) or next(
            (n for n in names if not re.search(r"-(?:vertical|trimmed|tight|even-sound|captions)(?:-\d+)?\.", n)), None)
        if not chosen:
            raise ValueError("Add the video to this project (drag it in) and ask again. I'll edit a copy and leave the original alone.")
        edits = [e for e in ORDER if e in re.split(r"[,\s]+", str(args.get("edits") or "").lower())] or wanted_edits(ctx.task) or ["vertical"]
        current = Path(ctx.folder) / chosen
        made, notes = [], []
        for edit in edits:
            ctx.progress(f"{video.EDITS[edit]}")
            if edit == "vertical":
                current = video.vertical(current)
            elif edit == "trim":
                start, end = args.get("start") or trim_times(ctx.task)[0], args.get("end") or trim_times(ctx.task)[1]
                if not start and not end:
                    raise ValueError("Tell me where to trim it, like \"from 0:10 to 0:45\".")
                current = video.trim(current, start or 0, end)
            elif edit == "dead_air":
                current, cut = video.remove_dead_air(current)
                notes.append(f"took out {cut:g} seconds of dead air")
            elif edit == "loudness":
                current = video.loudness(current)
            elif edit == "captions":
                current, srt_path = video.captions(current)
                made.append(srt_path)
            elif edit == "sheet":
                made.append(video.contact_sheet(current))
                continue
            made.append(current)
        info = video.probe(current) if current.suffix.lower() in video.VIDEO_KINDS else None
        rel = [str(Path(p).relative_to(ctx.folder)) for p in made]
        summary = (f"{Path(chosen).name}: " + ", ".join(video.EDITS[e].lower() for e in edits) + "." + (" I " + " and ".join(notes) + "." if notes else "")
                   + (f" The result is {info['duration']:.0f} seconds, {info['width']}x{info['height']}." if info else "") + " The original is untouched.")
        return Result(files=rel, summary=summary, data={"source": chosen, "result": str(Path(current).relative_to(ctx.folder)), "edits": edits})

    def check(self, ctx, result):
        from luma.skills import video
        path = Path(ctx.folder) / result.data["result"]
        if path.suffix.lower() not in video.VIDEO_KINDS:
            return [check("the result is there", path.exists(), "The edit didn't produce a file.")]
        try:
            info = video.probe(path)
            return [check(f"{path.name} plays ({info['duration']:.0f}s)", info["video"] and info["duration"] > 0.5, "The edited video didn't come out right.")]
        except ValueError as error:
            return [check(f"{path.name} plays", False, str(error))]
