"""The taste rules Luma's websites are held to: no generated-sounding words, buttons that say what
they do, a short headline, and no numbers or quotes nobody can stand behind."""
import json
import tempfile
import unittest
from pathlib import Path

import work_fakes
from luma.memory.store import Store
from luma.work.engine import Engine
from luma.work.projects import Projects
from luma.work.studios import taste


class TasteRuleTests(unittest.TestCase):
    def test_words_and_buttons(self):
        self.assertEqual(taste.fix_dashes("Fast — and fresh"), "Fast, and fresh")
        self.assertEqual(taste.buzzwords("Unlock seamless tacos with our cutting-edge truck"), ["cutting-edge", "seamless", "unlock"])
        self.assertEqual(taste.buzzwords("Tortillas pressed every morning"), [])
        self.assertTrue(taste.generic_cta("Get started →"))
        self.assertFalse(taste.generic_cta("Order lunch"))

    def test_numbers_need_a_source(self):
        self.assertTrue(taste.sourced("12%", "The market grew 12% last year"))
        self.assertFalse(taste.sourced("10K+", "The market grew 12% last year"))


class WebsiteGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.store = Store(root / "s.db", root / "k")
        self.root = root

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def build(self, args):
        eng = Engine(Projects(self.store, self.root / "p"), think=work_fakes.Brain({"work.website": args}), search=work_fakes.search, read=lambda u: "", render=False)
        p = eng.projects.create("Taco Rocket", "site")
        run = eng.start(p["id"], "build a website for my taco truck Taco Rocket")
        return eng, p, run["steps"][0]

    def test_invented_quotes_and_numbers_are_left_out(self):
        args = json.loads(json.dumps(work_fakes.ARGS["work.website"]))
        home = args["pages"][0]["sections"]
        home.append({"kind": "testimonials", "heading": "Fans", "body": "", "items": [{"title": "Jane Doe", "text": "Best tacos ever!", "extra": "CEO"}]})
        home[2]["items"].append({"title": "10K+", "text": "happy customers", "extra": ""})
        eng, p, step = self.build(args)
        html = eng.projects.read(p["id"], "site/taco-rocket/index.html")
        self.assertNotIn("Jane Doe", html)
        self.assertNotIn("10K+", html)
        note = next(c for c in step["checks"] if c["check"] == "no invented numbers or quotes")
        self.assertFalse(note["blocking"])
        css = eng.projects.read(p["id"], "site/taco-rocket/styles.css")
        self.assertTrue(css.startswith("/* Design read:"))
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertNotIn("gradient(", css)  # no linear-gradient or radial-gradient anywhere
        self.assertNotIn("eyebrow", html)

    def test_buzzwords_and_generic_buttons_send_it_back(self):
        args = json.loads(json.dumps(work_fakes.ARGS["work.website"]))
        hero = args["pages"][0]["sections"][0]
        hero["heading"] = "Unlock seamless tacos"
        hero["items"][0]["title"] = "Get started"
        _, _, step = self.build(args)
        failed = {c["check"] for c in step["checks"] if not c["ok"] and c.get("blocking", True)}
        self.assertIn("sounds like a person, not a template", failed)
        self.assertIn("buttons say what they do", failed)
        self.assertEqual(step["state"], "attention")


if __name__ == "__main__":
    unittest.main()
