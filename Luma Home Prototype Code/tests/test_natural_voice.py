"""The new expressive voice runs in its own process with its own Python, learns Luma's classic voice,
laughs when it can, and if it ever stops, the classic voice says the same words."""
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from luma.audio import natural, tts

FAKE_MLX = textwrap.dedent('''
    import os, sys
    import numpy as np

    class Result:
        def __init__(self, audio, rate):
            self.audio, self.sample_rate = audio, rate

    class Model:
        sample_rate = 24000
        def __init__(self, repo):
            self.repo, self.conds = repo, None
        def prepare_conditionals(self, ref):
            self.conds = ref
        def generate(self, text, ref_audio=None, ref_text=None, **kw):
            print("library chatter on stdout")  # must never garble Luma's replies
            if "CRASH" in text:
                os._exit(3)
            seconds = 30.0 if "BABBLE" in text else 0.25 + 0.06 * len(text)
            t = np.arange(int(self.sample_rate * seconds)) / self.sample_rate
            tone = 0.2 * np.sin(2 * np.pi * (440 if "[laugh]" in text else 220) * t)
            yield Result(tone.astype("float32"), self.sample_rate)

    def load_model(repo):
        if "fp16" in repo or any(part and part in repo.lower() for part in os.environ.get("FAKE_MISSING", "").split(",")):
            raise FileNotFoundError("Repository not found")
        return Model(repo)
''')


def make_voice_python(root):
    """A Python with a stand-in mlx-audio, the way the app's voice Python has the real one."""
    env = root / "voice-env"
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(env)], check=True, capture_output=True)
    python = env / "bin" / "python"
    site = subprocess.run([str(python), "-c", "import site; print(site.getsitepackages()[0])"], check=True, capture_output=True, text=True).stdout.strip()
    pkg = Path(site) / "mlx_audio" / "tts"
    pkg.mkdir(parents=True)
    (pkg.parent / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")
    (pkg / "utils.py").write_text(FAKE_MLX)
    return python


@unittest.skipUnless(sys.platform != "win32", "posix venv layout")
class NaturalVoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        try:
            cls.python = make_voice_python(cls.root)
        except Exception as error:  # no venv module here
            raise unittest.SkipTest(f"can't make a venv: {error}")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"LUMA_VOICE_PYTHON": str(self.python), "LUMA_NATURAL_DIR": str(self.root / "natural")})
        self.env.start()
        natural._voice = None
        self.ref = self.root / "ref.wav"
        tts.silence(str(self.ref), ms=1200)

    def tearDown(self):
        if natural._voice:
            natural._voice.stop()
        natural._voice = None
        self.env.stop()

    def test_loads_the_first_model_that_exists_and_talks(self):
        v = natural.voice()
        with mock.patch.object(v, "reference", return_value=self.ref):
            status = v.prepare("expressive")
        self.assertEqual(status["state"], "ready", status)
        self.assertEqual(status["model"], "mlx-community/chatterbox-turbo-bf16")  # the fp16 one "wasn't on the hub"
        self.assertTrue(status["laughs"])
        self.assertTrue(natural.active())
        pcm, rate = v.say("Not gonna lie, that's crazy [laugh]")
        self.assertEqual(rate, 24000)
        self.assertGreater(len(pcm), 2400)

    def test_luma_speech_uses_it_and_keeps_laughs(self):
        v = natural.voice()
        with mock.patch.object(v, "reference", return_value=self.ref):
            v.prepare("expressive")
        plan = tts.speech_plan("lmaooo you're wild 😭 okay so, what happened next?", expressive=tts.expressive_now())
        self.assertIn("[laugh]", [p for p, _ in plan])
        out = self.root / "said.wav"
        tts.synthesize("lmaooo you're wild 😭 okay so, what happened next?", str(out))
        self.assertGreater(out.stat().st_size, 20000)

    def test_a_crash_falls_back_to_the_classic_voice(self):
        v = natural.voice()
        with mock.patch.object(v, "reference", return_value=self.ref):
            v.prepare("expressive")
        classic = (np.ones(4800, dtype=np.int16), 24000)
        with mock.patch.object(tts, "_get_kokoro") as kokoro:
            kokoro.return_value.create.return_value = (np.ones(4800, dtype=np.float32) * 0.1, 24000)
            pcm, rate = tts._samples("CRASH right now", "luma", None)
        self.assertEqual(rate, 24000)
        self.assertEqual(v.status()["state"], "failed")
        self.assertIn("stopped", v.status()["note"])
        self.assertFalse(natural.speaking())  # the classic voice talks for a while before it tries again
        kokoro.return_value.create.assert_called_once()
        self.assertNotIn("[", kokoro.return_value.create.call_args[0][0])

    def test_a_garbled_phrase_is_said_by_the_classic_voice(self):
        v = natural.voice()
        with mock.patch.object(v, "reference", return_value=self.ref):
            v.prepare("expressive")
        with mock.patch.object(tts, "_get_kokoro") as kokoro:
            kokoro.return_value.create.return_value = (np.ones(4800, dtype=np.float32) * 0.1, 24000)
            tts._samples("BABBLE okay", "luma", None)  # thirty seconds for two words: that's babble
            self.assertEqual(kokoro.return_value.create.call_count, 1)
            self.assertEqual(v.status()["state"], "ready")  # one bad phrase doesn't turn it off
            tts._samples("BABBLE again", "luma", None)
            tts._samples("BABBLE more", "luma", None)
        self.assertEqual(v.status()["state"], "failed")  # three in a row does
        self.assertIn("garbl", v.status()["note"])

    def test_a_mac_that_cant_keep_up_keeps_the_classic_voice(self):
        v = natural.voice()
        with mock.patch.object(natural, "MAX_RTF", -1), mock.patch.object(v, "reference", return_value=self.ref):
            status = v.prepare("expressive")
            self.assertEqual(status["state"], "slow")
            self.assertFalse(natural.speaking())
            again = natural.NaturalVoice()
            with mock.patch.object(again, "_call") as call:  # measured this week: not loaded again
                self.assertEqual(again.prepare("expressive")["state"], "slow")
            call.assert_not_called()

    def test_tries_the_other_voice_when_the_first_wont_load(self):
        v = natural.voice()
        with mock.patch.dict(os.environ, {"FAKE_MISSING": "chatterbox"}), mock.patch.object(v, "reference", return_value=self.ref):
            status = v.prepare("expressive")
        self.assertEqual(status["state"], "ready", status)
        self.assertEqual(status["engine"], "studio")
        self.assertFalse(status["laughs"])

    def test_comes_back_after_a_rest(self):
        v = natural.voice()
        with mock.patch.object(v, "reference", return_value=self.ref):
            v.prepare("expressive")
            v._fail(RuntimeError("stopped"))
            self.assertFalse(v.ready())
            v.failed_at -= natural.REST_AFTER_FAILURE + 1
            self.assertFalse(v.ready())  # starts coming back in the background
            v.loader.join(60)
        self.assertTrue(v.ready())

    def test_not_installed_yet_waits_quietly(self):
        with mock.patch.dict(os.environ, {"LUMA_VOICE_PYTHON": str(self.root / "nope" / "python")}):
            status = natural.NaturalVoice().prepare()
        self.assertEqual(status["state"], "waiting")


class SoundsRightTests(unittest.TestCase):
    def test_real_speech_lengths(self):
        self.assertTrue(natural.sounds_right("Okay, I'm here.", 1.1))
        self.assertTrue(natural.sounds_right("Not gonna lie, that's crazy [laugh]", 3.4))
        self.assertFalse(natural.sounds_right("Bet.", 25.0))  # babble
        self.assertFalse(natural.sounds_right("So basically the short version is yes, and the long version is a whole story.", 0.3))  # cut off


class NaturalVoiceHomeTests(unittest.TestCase):
    def test_other_computers_keep_the_classic_voice(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LUMA_VOICE_PYTHON", None)
            with mock.patch.object(natural.sys, "platform", "linux"):
                self.assertFalse(natural.supported())
                self.assertEqual(natural.NaturalVoice().prepare()["state"], "off")


if __name__ == "__main__":
    unittest.main()
