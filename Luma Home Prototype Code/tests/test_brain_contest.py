"""The brain contest's own rules, with made-up pages (the real ones are read on GitHub's machines): a license that isn't
MIT, Apache-2.0 or BSD is never run; the maker's page is believed before a copy's; the file fetched is one whole file."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("brain_contest", ROOT / "scripts" / "brain_contest.py")
contest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contest)

FILES = [{"rfilename": n} for n in ("README.md", "model-Q8_0.gguf", "model-Q4_K_M.gguf", "model-Q4_K_M-00001-of-00002.gguf", "mmproj-model-Q4_K_M.gguf", "model-Q4_0.gguf")]


def pages(**by_repo):
    def fetch(repo):
        if repo not in by_repo: raise OSError("404")
        return by_repo[repo]
    return fetch


class TheLicenseComesFirst(unittest.TestCase):
    def test_what_a_page_states(self):
        self.assertEqual(contest.license_of({"cardData": {"license": "Apache-2.0"}}), "apache-2.0")
        self.assertEqual(contest.license_of({"cardData": {"license": ["mit"]}}), "mit")
        self.assertEqual(contest.license_of({"tags": ["gguf", "license:bsd-3-clause"]}), "bsd-3-clause")
        self.assertEqual(contest.license_of({"cardData": {"license": "other", "license_name": "Some Community License"}}), "other: some community license")
        self.assertEqual(contest.license_of({}), "")

    def test_only_mit_apache_and_bsd_are_run(self):
        for ok in ("mit", "apache-2.0", "bsd-3-clause"): self.assertTrue(contest.allowed(ok), ok)
        for no in ("cc-by-4.0", "cc-by-nc-4.0", "agpl-3.0", "llama3.3", "gemma", "other: its own terms", "openrail", ""): self.assertFalse(contest.allowed(no), no)

    def test_a_license_that_isnt_allowed_is_refused_whatever_the_copy_says(self):
        fetch = pages(**{"maker/model": {"cardData": {"license": "cc-by-nc-4.0"}}, "copy/model-GGUF": {"cardData": {"license": "apache-2.0"}, "siblings": FILES}})
        with self.assertRaises(contest.Refused) as why: contest.find("maker/model", ["copy/model-GGUF"], fetch=fetch)
        self.assertIn("cc-by-nc-4.0", str(why.exception))
        self.assertIn("the maker's page", str(why.exception))

    def test_no_license_anywhere_is_refused(self):
        with self.assertRaises(contest.Refused): contest.find("maker/model", ["copy/model-GGUF"], fetch=pages(**{"maker/model": {}, "copy/model-GGUF": {"siblings": FILES}}))

    def test_a_makers_page_that_cant_be_read_says_so(self):
        got = contest.find("maker/gone", ["copy/model-GGUF"], fetch=pages(**{"copy/model-GGUF": {"tags": ["license:mit"], "siblings": FILES}}))
        self.assertEqual(got["license"], "mit")
        self.assertIn("a copy's page", got["from"])


class TheFile(unittest.TestCase):
    def test_one_whole_file_in_the_first_quant_there_is(self):
        names = [f["rfilename"] for f in FILES]
        self.assertEqual(contest.pick(names), "model-Q4_K_M.gguf")
        self.assertEqual(contest.pick([n for n in names if "Q4_K_M" not in n]), "model-Q4_0.gguf")
        self.assertIsNone(contest.pick(["model-Q4_K_M-00001-of-00002.gguf", "mmproj-model-Q4_K_M.gguf", "README.md"]))

    def test_the_first_copy_that_has_one_is_used(self):
        fetch = pages(**{"maker/model": {"cardData": {"license": "apache-2.0"}}, "a/none": {"siblings": [{"rfilename": "README.md"}]}, "b/has": {"siblings": FILES}})
        got = contest.find("maker/model", ["missing/repo", "a/none", "b/has"], fetch=fetch)
        self.assertEqual((got["repo"], got["file"]), ("b/has", "model-Q4_K_M.gguf"))
        self.assertEqual(got["url"], "https://huggingface.co/b/has/resolve/main/model-Q4_K_M.gguf")
        with self.assertRaises(contest.Refused): contest.find("maker/model", ["a/none"], fetch=fetch)

    def test_the_script_fetches_nothing_itself(self):
        text = (ROOT / "scripts" / "brain_contest.py").read_text()
        for word in ("urlretrieve", "snapshot_download", "hf_hub_download", "subprocess", "open(got"): self.assertNotIn(word, text, word)


if __name__ == "__main__":
    unittest.main()
