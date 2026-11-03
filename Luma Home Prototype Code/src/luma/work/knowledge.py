"""Search a project's own files: what's in the PDFs, decks, spreadsheets and notes the owner added.

Files are read into passages (a few paragraphs each) and ranked with BM25, the ranking search engines
were built on: no model to download, fast on any computer, and every hit points back to its file and
place so answers can cite it. The index is rebuilt only for files that changed.

Reading keeps what a person would see, tables included, using the best open tools when they're installed:
  - Word, PowerPoint, Excel, EPUB, Outlook messages and notebooks through Microsoft's MarkItDown (MIT), as Markdown,
    so a table stays a table ("| ACME | A-1042 | $1,250.00 |") instead of disappearing;
  - PDFs through Docling (MIT, IBM), which reads layout, reading order and tables, page by page;
  - web pages through Trafilatura (Apache-2.0): the article, not the menus, cookie banners and footers.
Without them, Luma falls back to its plain readers (pypdf, python-docx, python-pptx, openpyxl), so nothing breaks.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

TEXT = {".txt", ".md", ".csv", ".json", ".html", ".htm", ".py", ".js", ".css", ".gd", ".scad", ".svg"}
WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
STOP = set("a an and are as at be but by for from has have he her his i if in into is it its of on or our she so that the their them "
           "they this to was we were what when which who will with you your".split())
CHUNK = 900


def words(text):
    return [w for w in WORD.findall(text.lower()) if w not in STOP]


MARKITDOWN = {".docx", ".pptx", ".xlsx", ".xls", ".epub", ".msg", ".ipynb"}
SLIDE = re.compile(r"<!--\s*Slide number:\s*(\d+)\s*-->")
SHEET = re.compile(r"^## (.+)$", re.M)
_markitdown = None


def _with_markitdown(path, ext):
    """Markdown from MarkItDown, split back into slides or sheets so answers can still say where. None if it can't."""
    global _markitdown
    try:
        if _markitdown is None:
            from markitdown import MarkItDown
            _markitdown = MarkItDown(enable_plugins=False)
        text = _markitdown.convert(str(path)).text_content or ""
    except Exception:
        return None
    if not text.strip():
        return None
    if ext == ".pptx":
        parts = SLIDE.split(text)
        slides = [(f"slide {parts[i]}", parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]
        return slides or [("", text)]
    if ext in (".xlsx", ".xls"):
        parts = SHEET.split(text)
        sheets = [(f"sheet {parts[i].strip()}", parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]
        return sheets or [("", text)]
    return [("", text)]


def _with_docling(path):
    """A PDF page by page through Docling: layout, reading order and tables kept. None if Docling isn't here or can't."""
    try:
        from docling.document_converter import DocumentConverter
    except Exception:
        return None
    try:
        document = DocumentConverter().convert(str(path)).document
        try:
            pages = [(f"page {n}", document.export_to_markdown(page_no=n)) for n in range(1, document.num_pages() + 1)]
        except TypeError:  # an older Docling without per-page export: the whole document at once
            pages = [("", document.export_to_markdown())]
        return pages if any(t.strip() for _, t in pages) else None
    except Exception:
        return None


def page_text(html):
    """The main text of a web page (the article, the recipe, the lyrics), not its menus and footers. '' if there's none."""
    try:
        import trafilatura
        text = trafilatura.extract(html, include_tables=True, include_comments=False, include_links=False, favor_recall=True)
        if text and text.strip():
            return text.strip()
    except Exception:
        pass
    raw = re.sub(r"<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", " ", str(html or ""), flags=re.S | re.I)
    return re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()


def extract(path):
    """The readable text of a file, as (place, text) pieces. Unknown or unreadable files give nothing."""
    path = Path(path)
    ext = path.suffix.lower()
    try:
        if ext in MARKITDOWN:
            found = _with_markitdown(path, ext)
            if found:
                return found
        if ext == ".pdf":
            found = _with_docling(path)
            if found:
                return found
        if ext in {".html", ".htm"}:
            return [("", page_text(path.read_text("utf-8", "replace")))]
        if ext in TEXT:
            raw = path.read_text("utf-8", "replace")
            if ext in {".html", ".htm", ".svg"}:
                raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
                raw = re.sub(r"<[^>]+>", " ", raw)
            return [("", raw)]
        if ext == ".docx":
            from docx import Document
            return [("", "\n".join(p.text for p in Document(str(path)).paragraphs))]
        if ext == ".pptx":
            from pptx import Presentation
            out = []
            for number, slide in enumerate(Presentation(str(path)).slides, 1):
                bits = [shape.text_frame.text for shape in slide.shapes if shape.has_text_frame]
                if slide.has_notes_slide:
                    bits.append(slide.notes_slide.notes_text_frame.text)
                out.append((f"slide {number}", "\n".join(bits)))
            return out
        if ext == ".pdf":
            from pypdf import PdfReader
            return [(f"page {i}", page.extract_text() or "") for i, page in enumerate(PdfReader(str(path)).pages, 1)]
        if ext == ".xlsx":
            from openpyxl import load_workbook
            book = load_workbook(str(path), read_only=True, data_only=True)
            out = []
            for sheet in book.worksheets:
                rows = [", ".join("" if v is None else str(v) for v in row) for row in sheet.iter_rows(values_only=True, max_row=2000)]
                out.append((f"sheet {sheet.title}", "\n".join(rows)))
            return out
    except Exception:
        return []
    return []


def passages(text, size=CHUNK):
    """Paragraph-aligned pieces of about `size` characters, overlapping by one paragraph."""
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n(?=[#*\-•])", text) if p.strip()]
    out, current = [], []
    for para in paras:
        while len(para) > size * 1.5:
            out.append(para[:size])
            para = para[size - 100:]
        current.append(para)
        if sum(len(p) for p in current) >= size:
            out.append("\n".join(current))
            current = current[-1:]
    if current and (not out or "\n".join(current) != out[-1]):
        out.append("\n".join(current))
    return out


class Index:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.file = self.folder / ".luma" / "index.json"
        try:
            self.data = json.loads(self.file.read_text())
        except (OSError, ValueError):
            self.data = {"files": {}, "chunks": []}

    def refresh(self):
        """Index new and changed files; drop deleted ones."""
        seen = {}
        for path in sorted(self.folder.rglob("*")):
            rel = path.relative_to(self.folder).as_posix()
            if not path.is_file() or rel.startswith(".luma/") or path.stat().st_size > 30 * 2 ** 20:
                continue
            seen[rel] = path.stat().st_mtime
        changed = {rel for rel, mtime in seen.items() if self.data["files"].get(rel) != mtime}
        gone = set(self.data["files"]) - set(seen)
        if not changed and not gone:
            return self
        chunks = [c for c in self.data["chunks"] if c["file"] not in changed | gone]
        for rel in sorted(changed):
            for place, text in extract(self.folder / rel):
                for piece in passages(text):
                    terms = words(piece)
                    if terms:
                        chunks.append({"file": rel, "place": place, "text": piece[:1600], "terms": dict(Counter(terms)), "length": len(terms)})
        self.data = {"files": seen, "chunks": chunks}
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self.data))
        return self

    def search(self, query, limit=6, k1=1.4, b=0.75):
        """Best passages for the query, each with its file and place (page, slide, sheet) to cite."""
        chunks = self.data["chunks"]
        terms = [t for t in dict.fromkeys(words(query))]
        if not chunks or not terms:
            return []
        avg = sum(c["length"] for c in chunks) / len(chunks)
        df = {t: sum(1 for c in chunks if t in c["terms"]) for t in terms}
        scored = []
        for chunk in chunks:
            score = 0.0
            for t in terms:
                tf = chunk["terms"].get(t, 0)
                if tf:
                    idf = math.log(1 + (len(chunks) - df[t] + 0.5) / (df[t] + 0.5))
                    score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * chunk["length"] / avg))
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda pair: -pair[0])
        return [{"file": c["file"], "place": c["place"], "text": c["text"], "score": round(s, 3)} for s, c in scored[:limit]]
