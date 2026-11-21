"""Memory by meaning on a lamp: the small static model (luma.memory.meaning, the "small" engine).

The real model is a download (potion-base-8M, MIT, 30 MB), so these use a stand-in built here in the same two files: a
tokenizer.json and a model.safetensors with a row of numbers for each word. In it "glasses" sits beside "eye", "leak"
beside "plumber" and "garbage" beside "trash", the way they do in the real one; every other word is next to nothing.

What the real one does on a thousand memories is in docs/HUMAN_PLAN.md ("The lamp's meaning experiment"), measured on
GitHub's machines by scripts/meaning_small_eval.py.
"""
import hashlib
import io
import json
import struct
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

try:
    import numpy as np
    import tokenizers  # noqa: F401
    HAVE = True
except Exception:
    HAVE = False

from luma.memory import meaning  # noqa: E402

GROUPS = [["glasses", "eye", "vision"], ["leak", "plumber", "pipe"], ["garbage", "trash"]]
WORDS = ["[UNK]", "my", "is", "the", "who", "do", "i", "about", "on", "number", "fridge", "marchetti", "goes", "out", "monday", "thursday", "what", "days",
         "pickup", "call", "a", "had", "pasta", "for", "dinner", "bus", "was", "late", "again", "it", "rained", "all", "weekend", "s", "'", ".", "doctor", "dr", "see"]
WORDS += [w for group in GROUPS for w in group]


def stand_in(folder, dims=meaning.DIMS):
    """A tiny static model in the real one's two files."""
    from tokenizers import Tokenizer, models, pre_tokenizers
    vocab = {word: i for i, word in enumerate(WORDS)}
    tok = Tokenizer(models.WordLevel(vocab, unk_token="[UNK]"))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    from tokenizers import normalizers
    tok.normalizer = normalizers.Lowercase()
    folder.mkdir(parents=True, exist_ok=True)
    tok.save(str(folder / "tokenizer.json"))
    rng = np.random.default_rng(7)
    rows = rng.standard_normal((len(WORDS), dims)).astype(np.float32) * 0.002    # little words: next to nothing, as in the real one
    for g, group in enumerate(GROUPS):
        direction = np.zeros(dims, dtype=np.float32)
        direction[g] = 1.0
        for word in group:
            rows[vocab[word]] = direction + rng.standard_normal(dims).astype(np.float32) * 0.005
    (folder / "model.safetensors").write_bytes(safetensors({"embeddings": rows}))
    (folder / "config.json").write_text(json.dumps({"normalize": True}))
    (folder / "ok").write_text(meaning.SMALL_TAG)
    return folder


def safetensors(tables):
    header, blob = {}, b""
    for name, array in tables.items():
        data = np.ascontiguousarray(array, dtype=np.float32).tobytes()
        header[name] = {"dtype": "F32", "shape": list(array.shape), "data_offsets": [len(blob), len(blob) + len(data)]}
        blob += data
    head = json.dumps(header).encode()
    return struct.pack("<Q", len(head)) + head + blob


def settle():
    """Wait for meanings being worked out in the background."""
    for _ in range(500):
        if not meaning._catching_up["running"]:
            return
        time.sleep(0.01)


@unittest.skipUnless(HAVE, "needs numpy and the tokenizers package")
class OnALamp(unittest.TestCase):
    def setUp(self):
        from luma.memory.store import Store
        self.dir = tempfile.TemporaryDirectory()
        self.home = Path(self.dir.name)
        self.patches = [mock.patch.object(meaning, "folder", lambda: self.home / "meaning"), mock.patch.object(meaning, "embedder", None)]
        for p in self.patches:
            p.start()
        meaning._small.update(model=None, failed=False)
        meaning._cache.clear()
        meaning.fetching_small.update(running=False, error=None, tried=0.0)
        self.store = Store(self.home / "s.db", self.home / "k")
        now = time.time()
        self.store.put_many("memory", [{"text": text, "source": "said", "created": now - 86400 * (30 + i), "category": "notes"} for i, text in enumerate(
            ["my eye doctor is Dr. Marchetti", "the plumber's number is on the fridge", "the trash goes out Monday and Thursday",
             "I had pasta for dinner", "the bus was late again", "it rained all weekend"])])

    def tearDown(self):
        settle()
        self.store.close()
        for p in self.patches:
            p.stop()
        meaning._small.update(model=None, failed=False)
        meaning._cache.clear()
        self.dir.cleanup()

    def found(self, question):
        got = self.store.search(question)
        if meaning.available(self.store):   # meanings are worked out in the background the first time; then it's asked again
            settle()
            meaning.catch_up(self.store, self.store.memories(), wait=True)
            got = self.store.search(question)
        return got["known"], [m["text"] for m in got["memories"]]

    def test_off_until_the_owner_switches_it_on_and_nothing_is_fetched(self):
        stand_in(meaning.small_folder())
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("nothing leaves the home for this")):
            self.assertFalse(meaning.available(self.store))
            known, texts = self.found("who do i see about my glasses")
            self.assertNotIn("my eye doctor is Dr. Marchetti", texts)
        self.assertFalse(meaning.fetching_small["running"])
        self.assertEqual(self.store.all("vector", 100), [])

    def test_switched_on_it_finds_what_was_said_in_other_words(self):
        stand_in(meaning.small_folder())
        self.store.set_setting("memory_by_meaning_small", True)
        self.assertEqual(meaning.engine(), "small")
        self.assertTrue(meaning.available(self.store))
        for question, said in (("who do i see about my glasses", "my eye doctor is Dr. Marchetti"), ("who do i call about a leak", "the plumber's number is on the fridge"),
                               ("what days is garbage pickup", "the trash goes out Monday and Thursday")):
            known, texts = self.found(question)
            self.assertTrue(known, question)
            self.assertIn(said, texts, question)

    def test_its_meanings_are_kept_under_its_own_name_and_encrypted(self):
        stand_in(meaning.small_folder())
        self.store.set_setting("memory_by_meaning_small", True)
        self.found("who do i see about my glasses")
        kept = self.store.all("vector", 100)
        self.assertEqual(len(kept), 6)
        self.assertEqual({v["model"] for v in kept}, {meaning.SMALL_TAG})
        raw = (self.home / "s.db").read_bytes()
        self.assertNotIn(b"Marchetti", raw)
        self.assertEqual(meaning.tag(), meaning.SMALL_TAG)
        self.assertEqual(meaning.close_enough(), meaning.SMALL_CLOSE)
        self.assertEqual(meaning.asking("where is it"), "where is it")           # no instruction in front: it just reads the words

    def test_the_bigger_models_numbers_are_never_read_as_its_own(self):
        stand_in(meaning.small_folder())
        self.store.set_setting("memory_by_meaning_small", True)
        memory = self.store.memories()[0]
        wrong = np.zeros(meaning.DIMS, dtype=np.float32)
        wrong[0] = 1.0
        self.store.put("vector", {"model": meaning.FILE, "for": meaning._fingerprint(memory["text"]), "h": meaning.pack(wrong)}, "vector:" + memory["id"])
        self.assertIsNone(meaning._vector(self.store, memory))
        self.found("who do i see about my glasses")
        self.assertEqual(self.store.get("vector", "vector:" + memory["id"])["model"], meaning.SMALL_TAG)

    def test_switched_off_again_it_stops(self):
        stand_in(meaning.small_folder())
        self.store.set_setting("memory_by_meaning_small", True)
        self.assertTrue(meaning.available(self.store))
        self.store.set_setting("memory_by_meaning_small", False)
        self.assertFalse(meaning.available(self.store))
        self.store.set_setting("memory_by_meaning_small", True)
        self.store.set_setting("memory_by_meaning", False)                       # the switch for all memory by meaning wins
        self.assertFalse(meaning.available(self.store))

    def test_a_file_that_isnt_what_it_should_be_is_never_used(self):
        folder = stand_in(meaning.small_folder())
        good = (folder / "model.safetensors").read_bytes()
        n = struct.unpack("<Q", good[:8])[0]
        header = json.loads(good[8:8 + n])
        for broken in (b"\x00" * 4, struct.pack("<Q", 1 << 40) + b"{}", good[:8 + n] + good[8 + n:-4],
                       self._with(header, good, n, shape=[10 ** 9, 256]), self._with(header, good, n, data_offsets=[0, 8])):
            (folder / "model.safetensors").write_bytes(broken)
            meaning._small.update(model=None, failed=False)
            self.assertIsNone(meaning._static("my eye doctor"))
            self.assertTrue(meaning._small["failed"])
            self.assertIsNone(meaning.engine())
        self.store.set_setting("memory_by_meaning_small", True)
        known, texts = self.found("who is my eye doctor")                       # words alone still work
        self.assertIn("my eye doctor is Dr. Marchetti", texts)

    @staticmethod
    def _with(header, good, n, **change):
        changed = {"embeddings": {**header["embeddings"], **change}}
        head = json.dumps(changed).encode()
        return struct.pack("<Q", len(head)) + head + good[8 + n:]

    def test_a_sentence_is_the_average_of_its_words_and_unknown_words_are_left_out(self):
        model = meaning._Static(stand_in(meaning.small_folder()))
        both = model("glasses plumber")
        self.assertAlmostEqual(float(both[0]), 0.5, delta=0.02)
        self.assertAlmostEqual(float(both[1]), 0.5, delta=0.02)
        self.assertIsNone(model("zzzz qqqq"))
        np.testing.assert_allclose(model("glasses zzzz"), model("glasses"), atol=1e-6)


@unittest.skipUnless(HAVE, "needs numpy and the tokenizers package")
class FetchingIt(unittest.TestCase):
    """The download, with the host replaced by a stand-in: only on the owner's yes, every file checked, nothing kept that doesn't match."""

    def setUp(self):
        from luma.memory.store import Store
        self.dir = tempfile.TemporaryDirectory()
        self.home = Path(self.dir.name)
        self.patches = [mock.patch.object(meaning, "folder", lambda: self.home / "meaning"), mock.patch.object(meaning, "embedder", None)]
        for p in self.patches:
            p.start()
        meaning._small.update(model=None, failed=False)
        meaning.fetching_small.update(running=False, error=None, tried=0.0)
        self.store = Store(self.home / "s.db", self.home / "k")
        made = stand_in(self.home / "made")
        self.files = {name: (made / name).read_bytes() for name in meaning.SMALL_FILES}
        self.asked = []

    def tearDown(self):
        self.wait()
        settle()
        self.store.close()
        for p in self.patches:
            p.stop()
        meaning._small.update(model=None, failed=False)
        meaning.fetching_small.update(running=False, error=None, tried=0.0)
        self.dir.cleanup()

    def host(self, files=None, listed=None):
        files = files or self.files
        listed = listed or self.files

        def urlopen(request, timeout=0):
            url = request.full_url
            self.asked.append(url)
            if url.endswith("/tree/main"):
                tree = [{"path": name, "oid": hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(),
                         **({"lfs": {"oid": hashlib.sha256(data).hexdigest()}} if name.endswith(".safetensors") else {})} for name, data in listed.items()]
                return io.BytesIO(json.dumps(tree).encode())
            return io.BytesIO(files[url.rsplit("/", 1)[1]])
        return mock.patch("urllib.request.urlopen", side_effect=urlopen)

    def wait(self):
        for _ in range(200):
            if not meaning.fetching_small["running"]:
                return
            time.sleep(0.01)

    def test_nothing_is_asked_for_until_the_owner_says_yes(self):
        with self.host():
            meaning.fetch_small(self.store)
            self.store.search("who do i see about my glasses")
            self.wait()
        self.assertEqual(self.asked, [])
        self.assertIsNone(meaning.small_path())

    def test_on_a_yes_its_fetched_checked_and_used(self):
        self.store.set_setting("memory_by_meaning_small", True)
        with self.host():
            self.store.search("who do i see about my glasses")       # asking is what starts it; this answer is by words
            self.wait()
        self.assertTrue(all(url.startswith("https://huggingface.co/") and meaning.SMALL_REPO in url for url in self.asked), self.asked)
        self.assertEqual(len(self.asked), 4)
        self.assertIsNotNone(meaning.small_path())
        self.assertEqual(meaning.engine(), "small")
        self.assertIsNone(meaning.fetching_small["error"])

    def test_a_file_that_doesnt_match_is_thrown_away(self):
        self.store.set_setting("memory_by_meaning_small", True)
        tampered = {**self.files, "tokenizer.json": self.files["tokenizer.json"] + b" "}
        with self.host(files=tampered):
            meaning.fetch_small(self.store)
            self.wait()
        self.assertIsNone(meaning.small_path())
        self.assertIn("didn't check out", meaning.fetching_small["error"])
        self.assertFalse((meaning.small_folder() / "model.safetensors").exists())      # nothing is kept unless every file checked out
        with self.host():                                                               # and it isn't tried again straight away
            meaning.fetch_small(self.store)
            self.wait()
        self.assertIsNone(meaning.small_path())


if __name__ == "__main__":
    unittest.main()
