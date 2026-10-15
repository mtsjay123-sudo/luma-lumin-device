"""Luma makes things beyond decks: Word documents, PDFs and small apps that work on their own."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from luma.agent.runtime import Agent
from luma.memory.store import Store
from luma.skills import documents

SPEC = {"title": "Trip to Lisbon", "subtitle": "Four days, three neighborhoods", "format": "docx",
        "sections": [{"heading": "Day 1: Alfama", "paragraphs": ["Land, drop bags, wander down to the river."], "bullets": ["Tram 28 early", "Fado at night"]},
                     {"heading": "Day 2: Belém", "paragraphs": ["Pastéis de Belém before the line."], "bullets": []}]}


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_word_document_has_the_content(self):
        path = documents.build_docx(documents.validate_doc(SPEC), self.dir / "trip.docx")
        with zipfile.ZipFile(path) as z:
            body = z.read("word/document.xml").decode()
        self.assertIn("Trip to Lisbon", body)
        self.assertIn("Tram 28 early", body)

    def test_pdf_is_a_real_pdf_either_way(self):
        spec = documents.validate_doc({**SPEC, "format": "pdf"})
        plain = documents.simple_pdf(spec)
        self.assertTrue(plain.startswith(b"%PDF-1.4"))
        self.assertIn(b"Trip to Lisbon", plain)
        self.assertTrue(plain.rstrip().endswith(b"%%EOF"))
        path = documents.build_pdf(spec, self.dir / "trip.pdf")
        self.assertTrue(path.read_bytes().startswith(b"%PDF"))

    def test_long_documents_turn_the_page(self):
        long = {"title": "Long", "format": "pdf", "sections": [{"heading": f"Part {i}", "paragraphs": ["word " * 300], "bullets": []} for i in range(8)]}
        pdf = documents.simple_pdf(documents.validate_doc(long))
        self.assertGreater(pdf.count(b"/Type /Page "), 1)

    def test_empty_documents_are_refused(self):
        with self.assertRaises(ValueError):
            documents.validate_doc({"title": "Nothing", "sections": [{"heading": "", "paragraphs": [], "bullets": []}]})

    def test_apps_carry_their_data_safely(self):
        spec = documents.validate_app({"title": "Spending </script><script>alert(1)</script>", "kind": "tracker", "columns": "Date, What, Amount"})
        page = documents.app_html(spec)
        self.assertNotIn("</script><script>alert(1)", page)
        self.assertEqual([c["type"] for c in spec["columns"]], ["date", "text", "number"])
        cards = documents.validate_app({"title": "Spanish", "kind": "flashcards", "cards": [{"front": "hola", "back": "hello"}]})
        self.assertEqual(cards["cards"][0]["back"], "hello")
        with self.assertRaises(ValueError):
            documents.validate_app({"title": "Countdown", "kind": "countdown", "date": "someday"})


class LumaMakesThingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_a_tracker_right_away(self):
        reply = self.agent.chat("make me a spending tracker")
        self.assertEqual(reply["file"]["kind"], "app")
        self.assertEqual(reply["file"]["app"], "tracker")
        row = self.store.get("file", reply["file"]["id"])
        self.assertIn("Amount", Path(row["path"]).read_text())

    def test_a_packing_list_with_their_items(self):
        reply = self.agent.chat("make a packing list: passport, charger, sunscreen")
        page = Path(self.store.get("file", reply["file"]["id"])["path"]).read_text()
        self.assertIn("sunscreen", page)

    def test_a_countdown_to_christmas(self):
        reply = self.agent.chat("make me a countdown to christmas")
        self.assertEqual(reply["file"]["app"], "countdown")

    def test_documents_through_the_tool(self):
        result = self.agent._run("doc.create", {**SPEC, "format": "pdf"})
        self.assertEqual(result["file"]["kind"], "pdf")
        self.assertTrue(Path(self.store.get("file", result["file"]["id"])["path"]).read_bytes().startswith(b"%PDF"))
        self.assertIn("PDF", result["summary"])


if __name__ == "__main__":
    unittest.main()


class PhotosAlwaysAnswerTests(unittest.TestCase):
    """Every way of seeing, best first, and a reply that always lands in the chat."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "s.db", Path(self.temp.name) / "k")
        self.agent = Agent(store=self.store, use_model=False)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_not_ready_still_answers_in_the_chat(self):
        from unittest import mock
        from luma.skills import vision
        with mock.patch.object(vision, "available", return_value=False), mock.patch.object(vision, "apple_read", return_value=None), \
             mock.patch.object(vision, "fetch_in_background"):
            out = self.agent.see(b"\xff\xd8\xff" + b"0" * 500, "", thumb="data:image/jpeg;base64,AAAA")
        self.assertTrue(out["vision_pending"])
        log = self.agent.transcripts["main"]
        self.assertEqual(log[-2]["photo"], "data:image/jpeg;base64,AAAA")
        self.assertIn("downloading", log[-1]["text"])

    def test_the_macs_own_reading_when_the_vision_model_isnt_here(self):
        from unittest import mock
        from luma.skills import vision
        apple = {"text": ["WIFI: BlueHouse5G", "Password: sunflower22"], "labels": ["sign", "paper"]}
        with mock.patch.object(vision, "available", return_value=False), mock.patch.object(vision, "apple_read", return_value=apple):
            out = self.agent.see(b"\xff\xd8\xff" + b"0" * 500, "what does it say?")
        self.assertIn("BlueHouse5G", out["text"])
        self.assertIn("sign", out["text"])

    def test_a_broken_vision_model_falls_through_instead_of_failing(self):
        from unittest import mock
        from luma.skills import vision
        with mock.patch.object(vision, "available", return_value=True), mock.patch.object(vision, "look", side_effect=ImportError("Qwen25VLChatHandler")), \
             mock.patch.object(vision, "apple_read", return_value={"text": [], "labels": ["dog", "beach"]}):
            out = self.agent.see(b"\xff\xd8\xff" + b"0" * 500, "")
        self.assertIn("dog", out["text"])
