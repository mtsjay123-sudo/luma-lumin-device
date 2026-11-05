"""Luma's own brain: an add-on trained on Luma's conversations (the "Train Luma's brain" workflow), downloaded from the
newest published release, loaded on top of the brain it was trained for and nothing else, and never at the cost of
the brain itself: an add-on that won't load means the stock brain answers."""
import io
import json
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

from luma.llm import brain, inference
from luma.memory.store import Store

BASE = "Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf"


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


class OwnBrainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "s.db", self.root / "k")
        self.patches = [mock.patch.object(brain, "models_dir", return_value=self.root), mock.patch.object(brain, "_store", self.store),
                        mock.patch("luma.llm.worker.enabled", return_value=False)]
        for p in self.patches: p.start()
        inference.use_adapter(None)

    def tearDown(self):
        inference.use_adapter(None)
        for p in self.patches: p.stop()
        self.store.close()
        self.temp.cleanup()

    def wait(self):
        for _ in range(200):
            if not brain.own_fetching["running"]:
                return
            time.sleep(0.01)

    def releases(self, assets=True, payload=b"GGUF" + b"\x00" * 2_000_000):
        listing = [{"tag_name": "v1.0", "assets": []},
                   {"tag_name": "luma-brain-12", "draft": False,
                    "assets": [{"name": brain.OWN_FILE, "browser_download_url": "https://github.com/x/luma-brain-lora.gguf"}] if assets else []}]
        return lambda url, timeout: Response(json.dumps(listing).encode() if "api.github.com" in url else payload)

    def test_gets_the_newest_published_brain_and_thinks_with_it(self):
        brain.fetch_own(opener=self.releases())
        self.wait()
        self.assertIsNone(brain.own_fetching["error"])
        self.assertEqual(brain.own_path(), self.root / "luma-brain" / brain.OWN_FILE)
        self.assertEqual(brain.own_status()["release"], "luma-brain-12")
        self.assertTrue(brain.own_on())
        self.assertEqual(inference._adapter, brain.own_path())
        brain.set_own(False)
        self.assertIsNone(inference._adapter, "off means the stock brain")

    def test_nothing_published_yet_says_so(self):
        brain.fetch_own(opener=self.releases(assets=False))
        self.wait()
        self.assertIn("no trained Luma brain published yet", brain.own_fetching["error"])
        self.assertIsNone(brain.own_path())

    def test_a_download_that_isnt_a_brain_is_never_used(self):
        brain.fetch_own(opener=self.releases(payload=b"<html>rate limited</html>"))
        self.wait()
        self.assertIn("didn't look like a Luma brain", brain.own_fetching["error"])
        self.assertIsNone(brain.own_path())

    def test_only_on_the_brain_it_was_trained_for(self):
        lora = self.root / "luma.gguf"
        lora.write_bytes(b"GGUF")
        inference.use_adapter(lora)
        self.assertEqual(inference.adapter_for(self.root / BASE), lora)
        self.assertIsNone(inference.adapter_for(self.root / "Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf"), "a LoRA on another model is noise")
        self.assertIsNone(inference.adapter_for(self.root / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"))

    def test_the_device_brain_has_its_own_add_on(self):
        small = self.root / "luma-brain-1.7b-lora.gguf"
        small.write_bytes(b"GGUF")
        inference.use_adapter(small)
        self.assertEqual(inference.adapter_for(self.root / "Qwen_Qwen3-1.7B-Q4_K_M.gguf"), small)
        self.assertIsNone(inference.adapter_for(self.root / BASE), "the 1.7B's add-on never goes on the 4B")
        big = self.root / "luma-brain-lora.gguf"
        big.write_bytes(b"GGUF")
        inference.use_adapter(big)
        self.assertIsNone(inference.adapter_for(self.root / "Qwen_Qwen3-1.7B-Q4_K_M.gguf"), "nor the 4B's on the 1.7B")
        with mock.patch.object(brain, "LLAMA_MODEL_PATH", self.root / "Qwen_Qwen3-1.7B-Q4_K_M.gguf"):
            self.assertEqual(brain.own_file(), "luma-brain-1.7b-lora.gguf")
        with mock.patch.object(brain, "LLAMA_MODEL_PATH", self.root / BASE):
            self.assertEqual(brain.own_file(), "luma-brain-lora.gguf")

    def test_an_add_on_that_wont_load_never_costs_luma_its_brain(self):
        model = self.root / BASE
        model.write_bytes(b"GGUF")
        lora = self.root / "luma.gguf"
        lora.write_bytes(b"GGUF")
        made = []

        class Llama:
            def __init__(self, **kw):
                if "lora_path" in kw:
                    raise RuntimeError("adapter doesn't match")
                made.append(kw)

        with mock.patch.dict(sys.modules, {"llama_cpp": types.SimpleNamespace(Llama=Llama)}), \
                mock.patch.object(inference, "_gpu_layers", return_value=0), mock.patch.object(inference, "_offloads", return_value=False):
            inference.use_model_path(model)
            inference.use_adapter(lora)
            try:
                loaded = inference._load_model()
            finally:
                inference.use_model_path(None)
                inference._llm = None
        self.assertIsInstance(loaded, Llama)
        self.assertNotIn("lora_path", made[0])



class ReleaseTests(unittest.TestCase):
    def test_a_brain_release_never_takes_latest_from_the_desktop_app(self):
        """The website's Download for Mac is releases/latest/download/Luma-mac-apple-silicon.dmg: a brain release marked
        latest (GitHub's default, by date) sends every visitor to a release with no app in it."""
        workflow = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "train-luma.yml").read_text().splitlines()
        creates = [i for i, line in enumerate(workflow) if "gh release create" in line]
        self.assertTrue(creates)
        for i in creates:
            self.assertIn("--latest=false", " ".join(workflow[i:i + 2]), "every brain release")
        desktop = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "luma-desktop.yml").read_text()
        self.assertIn("--latest", desktop.split('gh release create "desktop-v', 1)[1].split("\n", 2)[1])

if __name__ == "__main__":
    unittest.main()
