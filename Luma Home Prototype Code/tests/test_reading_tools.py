"""Reading what a person would see, with the best open tools: tables in Word, PowerPoint and Excel kept as tables
(MarkItDown), PDFs read with their layout and tables (Docling, when it's installed), and web pages down to the article
itself (Trafilatura). Without those tools Luma falls back to its plain readers, so nothing breaks."""
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from luma.work import knowledge

HAVE_MARKITDOWN = importlib.util.find_spec("markitdown") is not None
HAVE_TRAFILATURA = importlib.util.find_spec("trafilatura") is not None

PAGE = """<html><head><title>Basil</title><script>var tracking = 1</script></head><body>
<nav><a href="/">Home</a> <a href="/deals">Deals</a> <a href="/login">Sign in</a></nav>
<div class="cookie">We use cookies. Accept all?</div>
<article><h1>How to keep basil alive</h1>
<p>Basil wants six to eight hours of sun and soil that dries slightly between waterings, more in a heat wave.</p>
<p>Pinch off the flower buds as soon as they show up, or the leaves turn bitter and the plant stops growing.</p></article>
<aside>Trending: 10 celebrity gardens you won't believe</aside><footer>© 2026 Garden Co. Privacy Terms</footer></body></html>"""


class OfficeFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def word_with_a_table(self):
        from docx import Document
        doc = Document()
        doc.add_paragraph("Totals by vendor.")
        table = doc.add_table(rows=3, cols=3)
        for r, row in enumerate([["Vendor", "Invoice", "Total"], ["ACME", "A-1042", "$1,250.00"], ["Bright Electric", "77", "$310.50"]]):
            for c, value in enumerate(row):
                table.cell(r, c).text = value
        path = self.dir / "costs.docx"
        doc.save(str(path))
        return path

    @unittest.skipUnless(HAVE_MARKITDOWN, "MarkItDown isn't installed here")
    def test_a_table_in_a_word_file_stays_a_table(self):
        text = "\n".join(t for _, t in knowledge.extract(self.word_with_a_table()))
        self.assertIn("| ACME | A-1042 | $1,250.00 |", text)
        self.assertIn("Totals by vendor.", text)

    @unittest.skipUnless(HAVE_MARKITDOWN, "MarkItDown isn't installed here")
    def test_slides_and_sheets_keep_their_names_so_answers_can_say_where(self):
        from openpyxl import Workbook
        from pptx import Presentation
        from pptx.util import Inches
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[5])
        slide.shapes.title.text = "Revenue"
        table = slide.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(4), Inches(1)).table
        for (r, c), value in {(0, 0): "Region", (0, 1): "Revenue", (1, 0): "West", (1, 1): "$2.4M"}.items():
            table.cell(r, c).text = value
        deck.save(str(self.dir / "deck.pptx"))
        pieces = dict(knowledge.extract(self.dir / "deck.pptx"))
        self.assertIn("| West | $2.4M |", pieces["slide 1"], "the old reader dropped this table entirely")
        book = Workbook()
        book.active.title = "Budget"
        book.active.append(["Item", "Cost"])
        book.active.append(["Rent", 2100])
        book.save(str(self.dir / "book.xlsx"))
        self.assertIn("| Rent | 2100 |", dict(knowledge.extract(self.dir / "book.xlsx"))["sheet Budget"])

    def test_without_markitdown_the_plain_reader_still_works(self):
        path = self.word_with_a_table()
        with mock.patch.object(knowledge, "_with_markitdown", return_value=None):
            self.assertIn("Totals by vendor.", knowledge.extract(path)[0][1])


class PdfTests(unittest.TestCase):
    def test_docling_reads_a_pdf_page_by_page_when_its_installed(self):
        class Doc:
            def num_pages(self): return 2
            def export_to_markdown(self, page_no=None):
                return {1: "# Lease\n| Rent | $2,100 |", 2: "Signed by both parties."}[page_no]
        converter = mock.Mock()
        converter.return_value.convert.return_value = types.SimpleNamespace(document=Doc())
        fake = types.ModuleType("docling.document_converter")
        fake.DocumentConverter = converter
        with tempfile.NamedTemporaryFile(suffix=".pdf") as pdf, \
                mock.patch.dict(sys.modules, {"docling": types.ModuleType("docling"), "docling.document_converter": fake}):
            self.assertEqual(knowledge.extract(pdf.name), [("page 1", "# Lease\n| Rent | $2,100 |"), ("page 2", "Signed by both parties.")])

    def test_without_docling_pdfs_still_read_with_pypdf(self):
        with mock.patch.dict(sys.modules, {"docling.document_converter": None}):
            self.assertIsNone(knowledge._with_docling("nothing.pdf"))


class WebPageTests(unittest.TestCase):
    @unittest.skipUnless(HAVE_TRAFILATURA, "Trafilatura isn't installed here")
    def test_a_page_comes_down_to_the_article(self):
        text = knowledge.page_text(PAGE)
        self.assertIn("six to eight hours of sun", text)
        self.assertIn("Pinch off the flower buds", text)
        for clutter in ("Sign in", "cookies", "celebrity gardens", "Privacy Terms", "tracking"):
            self.assertNotIn(clutter, text)

    def test_without_trafilatura_the_obvious_clutter_still_goes(self):
        with mock.patch.dict(sys.modules, {"trafilatura": None}):
            text = knowledge.page_text(PAGE)
        self.assertIn("Pinch off the flower buds", text)
        self.assertNotIn("Sign in", text)
        self.assertNotIn("tracking", text)

    @unittest.skipUnless(HAVE_TRAFILATURA, "Trafilatura isn't installed here")
    def test_a_story_with_no_paragraph_tags_is_still_read(self):
        from luma.skills import news
        story = "<html><head><title>Rates</title></head><body><nav>Menu Markets Login</nav><div class='story'>" + "".join(
            f"<div class='para'>The central bank held rates steady for the {n} straight meeting, citing cooling inflation and a steady job market.</div>"
            for n in ("third", "fourth", "fifth")) + "</div><footer>Subscribe now</footer></body></html>"
        got = news.read_article("https://wire.example/rates", fetch=lambda url, allow_local: story.encode())
        self.assertEqual(len(got["paragraphs"]), 3)
        self.assertNotIn("Menu", " ".join(got["paragraphs"]))

    def test_luma_answers_from_the_article_not_the_whole_screen(self):
        from luma.agent.runtime import Agent
        from luma.memory.store import Store
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "s.db", Path(root) / "k")
            try:
                agent = Agent(store=store, use_model=False)
                article = "Basil wants six to eight hours of sun. " * 10
                prompt = agent._observation_prompt("how do i keep basil alive", "browser.read",
                                                   {"text": "Home Deals Sign in We use cookies " * 30, "article": article})
                self.assertIn("six to eight hours", prompt)
                self.assertNotIn("We use cookies", prompt)
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
