"""Pull it into a spreadsheet, through the real projects engine: every document the owner added becomes a row with the
columns they asked for, amounts become real numbers with a total that stays a formula, a document that can't be read
is said plainly instead of guessed at, and the brain is told to copy, never guess."""
import tempfile
import unittest
from pathlib import Path

import work_fakes
from luma.memory.store import Store
from luma.work.engine import Engine
from luma.work.projects import Projects

INVOICE_A = "ACME PLUMBING\nInvoice #A-1042\nDate: October 3, 2026\nKitchen sink repair\nTotal due: $1,250.00\n"
INVOICE_B = "Bright Electric LLC\nInvoice No. 77\nIssued 2026-10-12\nPanel inspection\nAmount due $310.50\n"


def reader(asked):
    """What a careful model answers for one document: only what that document says."""
    if "ACME" in asked:
        return {"vendor": "ACME Plumbing", "date": "2026-10-03", "invoice_number": "A-1042", "total": "$1,250.00"}
    if "Bright Electric" in asked:
        return {"vendor": "Bright Electric LLC", "date": "2026-10-12", "invoice_number": "77", "total": "$310.50"}
    return {}


class ExtractStudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.projects = Projects(self.store, root / "projects")
        self.asked = []

        def per_document(n):
            prompt = self.brain.calls[-1]["prompt"]
            self.asked.append(prompt)
            return reader(prompt)
        self.brain = work_fakes.Brain({"work.extract": {"title": "October invoices", "fields": "vendor, date, invoice number, total"},
                                       "work.extract.document": per_document})
        self.engine = Engine(self.projects, think=self.brain, search=work_fakes.search, render=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_invoices_into_a_spreadsheet(self):
        from docx import Document
        from openpyxl import load_workbook
        project = self.projects.create("Taxes", "")
        folder = self.projects.folder(project["id"])
        (folder / "uploads").mkdir(parents=True, exist_ok=True)
        (folder / "uploads" / "acme.txt").write_text(INVOICE_A)
        doc = Document()
        for line in INVOICE_B.splitlines():
            doc.add_paragraph(line)
        doc.save(str(folder / "uploads" / "bright.docx"))
        (folder / "uploads" / "receipt.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # a photo, with no eyes in this test

        run = self.engine.start(project["id"], "pull the vendor, date, invoice number and total from these invoices into a spreadsheet")
        step = run["steps"][-1]
        self.assertEqual((step["tool"], step["state"]), ("extract", "done"), step.get("checks"))
        self.assertIn("Totals: Total 1,560.50", step["summary"])
        self.assertIn("Couldn't read 1", step["summary"])
        self.assertTrue({"extracted/october-invoices.xlsx", "extracted/october-invoices.csv"} <= {f["path"] for f in self.projects.files(project["id"])})

        sheet = load_workbook(folder / "extracted/october-invoices.xlsx").active
        rows = [[c.value for c in r] for r in sheet.iter_rows()]
        self.assertEqual(rows[0], ["Document", "Vendor", "Date", "Invoice number", "Total", "Note"])
        by_doc = {r[0]: r for r in rows[1:4]}
        self.assertEqual(by_doc["acme.txt"][1:5], ["ACME Plumbing", "2026-10-03", "A-1042", 1250.0], "amounts are real numbers")
        self.assertEqual(by_doc["bright.docx"][4], 310.5)
        self.assertEqual(by_doc["receipt.jpg"][5], "Couldn't read this one")
        self.assertEqual(rows[4][0], "Total")
        self.assertEqual(rows[4][4], "=SUM(E2:E4)", "the total stays a formula, so it's right after edits")
        self.assertEqual(sheet.freeze_panes, "A2")

        self.assertEqual(len(self.asked), 2, "one careful read per readable document")
        self.assertIn("Never guess", self.asked[0])
        self.assertIn("Kitchen sink repair", "".join(self.asked), "the document's own words go to the brain")
        checks = {c["check"]: c["ok"] for c in step["checks"]}
        self.assertTrue(checks["every document has a row"])
        self.assertFalse(checks["every document could be read"])

    def test_no_documents_says_how_to_add_them(self):
        project = self.projects.create("Empty", "")
        run = self.engine.start(project["id"], "put my receipts into a spreadsheet")
        self.assertIn("Add the documents to this project", str(run["steps"][-1]))

    def test_fields_come_from_the_request_when_no_brain_is_there(self):
        from luma.work.studios.extract import Extract
        guess = Extract().fallback(None, "extract the name, email and top skills from each resume")
        self.assertEqual(guess["fields"], "name, email, top skills")
        self.assertEqual(Extract().fallback(None, "put my receipts into a spreadsheet")["fields"], "store, date, total, payment method")


if __name__ == "__main__":
    unittest.main()
