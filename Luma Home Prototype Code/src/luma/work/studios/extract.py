"""Pull it into a spreadsheet: the same facts out of every document the owner added.

Invoices, receipts, bank statements, contracts, resumes, reviews: Luma reads each one (PDF, Word, text, or a photo
with Luma's own eyes), fills one row per document with the columns asked for, copying names, dates and amounts as
written and leaving a blank rather than guessing, and hands back an Excel workbook (with totals for money columns)
and a CSV. Luma's own code; the idea of turning piles of documents into structured data is an old one.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from luma.work.studios.base import Result, Studio, check, slug, text

READABLE = {".pdf", ".docx", ".txt", ".md", ".html", ".htm", ".eml", ".rtf", ".csv", ".json", ".xlsx"}
PICTURES = {".png", ".jpg", ".jpeg", ".webp", ".heic"}
OUT_FOLDER = "extracted"
MAX_DOCS = 200
MONEY = re.compile(r"^\s*[-(]?\s*[$€£¥]?\s*-?\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?\s*\)?\s*(?:USD|EUR|GBP)?\s*$|^\s*[$€£¥]?\s*-?\d+(?:\.\d{1,2})?\s*$")
GUESS_FIELDS = [
    (r"\binvoices?\b|\bbills?\b", "vendor, date, invoice number, total"),
    (r"\breceipts?\b", "store, date, total, payment method"),
    (r"\bstatements?\b", "account, period, opening balance, closing balance"),
    (r"\bresumes?\b|\bcvs?\b", "name, current role, years of experience, top skills, email"),
    (r"\bcontracts?\b|\bagreements?\b", "parties, start date, end date, amount, renewal terms"),
    (r"\breviews?\b", "product, rating, what they liked, what they didn't"),
]


def named_fields(request):
    """'pull the vendor, date and total from these invoices' -> 'vendor, date, total'. None if no list was named."""
    m = re.search(r"\b(?:pull|extract|grab|copy|collect|list|get)\s+(?:out\s+)?(?:the\s+|each\s+|every\s+)?(.{3,140}?)\s+(?:from|out of|in|for)\s+(?:each|every|all|these|those|the|my)\b", str(request or ""), re.I)
    if not m:
        return None
    named = re.split(r"\s*(?:,|\band\b|&|/|;)\s*", m.group(1))
    named = [re.sub(r"^(?:the|their|its|each|every)\s+", "", n.strip(" ."), flags=re.I) for n in named]
    named = [n for n in named if n and len(n) <= 40 and not re.fullmatch(r"(?:info|information|data|details|stuff|everything|totals?)", n, re.I) or n.lower() in {"total", "totals"}]
    return ", ".join(dict.fromkeys(named)) if named else None


def columns(spec):
    """'vendor, date, invoice number' -> [("vendor", "Vendor"), ("date", "Date"), ("invoice_number", "Invoice number")]."""
    out = []
    for raw in re.split(r"\s*[,;\n]\s*", str(spec or "")):
        label = " ".join(raw.split()).strip(" .:-")[:40]
        key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")[:32]
        if label and key and key not in {k for k, _ in out}:
            out.append((key, label[:1].upper() + label[1:]))
    return out[:12]


def as_number(value):
    """'$1,250.00' -> 1250.0, '(45.10)' -> -45.1, anything else -> None."""
    s = str(value or "").strip()
    if not s or not MONEY.match(s):
        return None
    negative = s.startswith("(") or "-" in s
    digits = re.sub(r"[^\d.]", "", s.replace(",", ""))
    try:
        number = float(digits)
    except ValueError:
        return None
    return -number if negative else number


ID_LABEL = re.compile(r"(?i)\b(?:number|no|#|id|zip|postal|phone|account|invoice|order|reference|ref|code|year|years|rating|score|page)\b")
MONEY_LABEL = re.compile(r"(?i)\b(?:total|amount|price|cost|balance|paid|due|subtotal|tax|fee|fees|salary|spent|charge|refund|tip|value)\b")


def is_money(label, values):
    """A column of amounts: named like one (or written with currency signs or cents), and nearly every value is a number.
    Invoice numbers, years and ratings are numbers too, but nobody wants them added up."""
    if not values or (ID_LABEL.search(label) and not MONEY_LABEL.search(label)):
        return False
    numeric = sum(1 for v in values if as_number(v) is not None)
    looks = MONEY_LABEL.search(label) or any(re.search(r"[$€£¥]|\.\d{2}\b", str(v)) for v in values)
    return bool(looks) and numeric * 10 >= len(values) * 8


class Extract(Studio):
    name, agent, title, tier = "extract", "data", "Pull it into a spreadsheet", "standard"
    description = ("Pull the same facts out of every document the owner added to the project (invoices, receipts, statements, contracts, "
                   "resumes, reviews). fields: the columns to fill, comma-separated, in the order a person reads them (for invoices: vendor, "
                   "date, invoice number, total). Use the owner's own words when they named the fields. title: a short name for the spreadsheet.")
    fields = {"title": "string", "fields": "text"}

    def fallback(self, ctx, task):
        named = named_fields(task)
        guess = next((f for pattern, f in GUESS_FIELDS if re.search(pattern, str(task), re.I)), "title, date, summary")
        return {"title": "", "fields": named or guess}

    def documents(self, ctx):
        found = []
        for f in ctx.files():
            path = str(f.get("path") if isinstance(f, dict) else f)
            suffix = Path(path).suffix.lower()
            if path.split("/")[0] in {OUT_FOLDER, "code", "video", "graphics"} or path.endswith(("-script.md", "SECURITY.md")):
                continue
            if suffix in READABLE or suffix in PICTURES:
                found.append(path)
        return found[:MAX_DOCS]

    def read(self, ctx, rel):
        """The document's words: text from PDFs and Office files, Luma's eyes for photos. '' if nothing could be read."""
        path = Path(ctx.folder) / rel
        if path.suffix.lower() in PICTURES:
            try:
                from luma.skills import vision
                data = path.read_bytes()
                if vision.available():
                    return vision.look(data, "Copy out every word and number on this document exactly as written, line by line.") or ""
                apple = vision.apple_read(data)
                return "\n".join(apple.get("text") or []) if apple else ""
            except Exception:
                return ""
        from luma.work.knowledge import extract
        return "\n".join(t for _, t in extract(path)).strip()

    def make(self, ctx, args):
        cols = columns(args.get("fields")) or columns(self.fallback(ctx, ctx.task)["fields"])
        docs = self.documents(ctx)
        if not docs:
            raise ValueError("Add the documents to this project (drag in the PDFs, photos or files) and ask again.")
        title = text(args.get("title"), 60) or "Extracted"
        keys = {key: "text" for key, _ in cols}
        rows, unreadable = [], []
        for n, rel in enumerate(docs, 1):
            ctx.progress(f"Reading {Path(rel).name} ({n} of {len(docs)})")
            words = self.read(ctx, rel)
            if not words:
                unreadable.append(rel)
                rows.append([Path(rel).name] + [""] * len(cols) + ["Couldn't read this one"])
                continue
            asked = (f"Document: {Path(rel).name}\n---\n{words[:9000]}\n---\n"
                     f"Fill in these fields from this document only: {', '.join(label for _, label in cols)}. Copy names, numbers and amounts "
                     "exactly as written (keep the currency sign); write dates as YYYY-MM-DD when the date is clear. If a field isn't in the "
                     "document, leave it empty. Never guess or fill in from other documents.")
            got = ctx.ask(asked, keys, "work.extract.document", "light") or {}
            values = [" ".join(str(got.get(key) or "").split())[:300] for key, _ in cols]
            rows.append([Path(rel).name] + values + [""])
        header = ["Document"] + [label for _, label in cols] + ["Note"]
        base = f"{OUT_FOLDER}/{slug(title, 'extracted')}"
        totals = self._workbook(ctx, f"{base}.xlsx", title, header, rows)
        buf = io.StringIO()
        csv.writer(buf).writerows([header] + rows)
        ctx.write(f"{base}.csv", buf.getvalue())
        blanks = sum(1 for row in rows for v in row[1:-1] if not v)
        money = ", ".join(f"{label} {total:,.2f}" for label, total in totals.items())
        summary = (f"{len(rows)} document{'s' if len(rows) != 1 else ''} into {base}.xlsx: {', '.join(label for _, label in cols)}."
                   + (f" Totals: {money}." if money else "") + (f" {blanks} blank{'s' if blanks != 1 else ''} where a document didn't say." if blanks else "")
                   + (f" Couldn't read {len(unreadable)}." if unreadable else ""))
        return Result(files=[f"{base}.xlsx", f"{base}.csv"], summary=summary,
                      data={"columns": [label for _, label in cols], "rows": len(rows), "documents": docs, "unreadable": unreadable, "blanks": blanks,
                            "totals": totals, "preview": [dict(zip(header, r)) for r in rows[:5]]})

    def _workbook(self, ctx, rel, title, header, rows):
        """An Excel workbook people can use straight away: bold frozen header, filters, sensible widths, real numbers for
        amounts and a total under each money column (as a formula, so it stays right when they edit)."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter
        book = Workbook()
        sheet = book.active
        sheet.title = (re.sub(r"[\[\]:*?/\\]", "", title) or "Extracted")[:31]
        sheet.append(header)
        money_cols = {c for c in range(1, len(header) - 1) if is_money(header[c], [r[c] for r in rows if r[c]])}
        for r in rows:
            sheet.append([as_number(v) if i in money_cols and as_number(v) is not None else v for i, v in enumerate(r)])
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1B1714")
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = f"A1:{get_column_letter(len(header))}{len(rows) + 1}"
        totals = {}
        if money_cols and rows:
            total_row = len(rows) + 2
            sheet.cell(row=total_row, column=1, value="Total").font = Font(bold=True)
            for c in sorted(money_cols):
                col = get_column_letter(c + 1)
                cell = sheet.cell(row=total_row, column=c + 1, value=f"=SUM({col}2:{col}{len(rows) + 1})")
                cell.font = Font(bold=True)
                totals[header[c]] = round(sum(as_number(r[c]) or 0 for r in rows), 2)
                for row in range(2, total_row + 1):
                    sheet.cell(row=row, column=c + 1).number_format = "#,##0.00"
        for i, name in enumerate(header, 1):
            longest = max([len(str(name))] + [len(str(r[i - 1])) for r in rows[:200]])
            sheet.column_dimensions[get_column_letter(i)].width = min(48, max(10, longest + 2))
        out = io.BytesIO()
        book.save(out)
        ctx.write(rel, out.getvalue())
        return totals

    def check(self, ctx, result):
        d = result.data
        out = [check("every document has a row", d["rows"] == len(d["documents"]), "Some documents are missing from the spreadsheet.")]
        filled = [r for r in d["preview"] if any(v for k, v in r.items() if k not in {"Document", "Note"})]
        out.append(check("it found something", bool(filled) or not d["preview"], "Nothing was found in the documents. Check the field names."))
        if d["unreadable"]:
            out.append(check("every document could be read", False, "Couldn't read: " + ", ".join(Path(p).name for p in d["unreadable"][:6]), blocking=False))
        return out
