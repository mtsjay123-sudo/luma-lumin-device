"""Training Luma's own brain on a Mac: the same conversations and checks as the cloud run, an mlx-lm config that trains every
layer on Luma's words only, the add-on rewritten exactly the way llama.cpp's converter reads a PEFT adapter, and the result
installed where Settings > Brain finds it."""
import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("train_on_mac", ROOT / "scripts" / "train_on_mac.py")
mac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mac)


class TrainOnMacTests(unittest.TestCase):
    def test_every_layer_learns_only_lumas_words_on_a_schedule_over_the_whole_run(self):
        args = types.SimpleNamespace(base=mac.BASE, batch=4, lr=1e-4, max_len=512, rank=16, alpha=32.0)
        cfg = mac.config(args, Path("/d"), Path("/a"), 830)
        self.assertTrue(cfg["mask_prompt"], "the question is context, not something to learn")
        self.assertEqual(cfg["num_layers"], -1)
        self.assertEqual(cfg["lora_parameters"]["scale"], 2.0, "alpha 32 over rank 16, like the cloud run")
        self.assertEqual(set(cfg["lora_parameters"]["keys"]), {"self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj",
                                                               "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj"})
        schedule = cfg["lr_schedule"]
        self.assertEqual(schedule["name"], "cosine_decay")
        self.assertEqual(schedule["warmup"] + schedule["arguments"][1], 830, "warm-up plus the decay cover every step")
        json.loads(json.dumps(cfg))  # written as JSON, which mlx-lm reads as YAML

    def test_the_add_on_is_rewritten_the_way_llama_cpp_reads_a_peft_adapter(self):
        r, d_in, d_out = 4, 6, 10
        a = np.arange(d_in * r, dtype=np.float32).reshape(d_in, r)       # mlx-lm: lora_a is (in, r)
        b = np.arange(r * d_out, dtype=np.float32).reshape(r, d_out)     # and lora_b is (r, out)
        saved = {}
        fake = types.SimpleNamespace(load=lambda path: {"model.layers.0.self_attn.q_proj.lora_a": a, "model.layers.0.self_attn.q_proj.lora_b": b,
                                                        "model.layers.3.mlp.down_proj.lora_a": a, "model.layers.3.mlp.down_proj.lora_b": b},
                                     float32=np.float32, save_safetensors=lambda path, tensors: saved.update(tensors))
        with tempfile.TemporaryDirectory() as root, mock.patch.dict(sys.modules, {"mlx": types.ModuleType("mlx"), "mlx.core": fake}):
            sys.modules["mlx"].core = fake
            n = mac.to_peft(Path(root), Path(root) / "adapter", mac.BASE, rank=r, alpha=8.0)
            config = json.loads((Path(root) / "adapter" / "adapter_config.json").read_text())
        self.assertEqual(n, 2)
        A = saved["base_model.model.model.layers.0.self_attn.q_proj.lora_A.weight"]
        B = saved["base_model.model.model.layers.0.self_attn.q_proj.lora_B.weight"]
        self.assertEqual(A.shape, (r, d_in))
        self.assertEqual(B.shape, (d_out, r))
        x = np.ones((1, d_in), dtype=np.float32)
        scale = 2.0
        np.testing.assert_allclose(scale * (x @ a) @ b, x @ ((config["lora_alpha"] / config["r"]) * (B @ A)).T,
                                   err_msg="the same change to the brain's output, before and after the rewrite")
        self.assertEqual((config["peft_type"], config["r"], config["lora_alpha"]), ("LORA", r, 8.0))
        self.assertEqual(sorted(config["target_modules"]), ["down_proj", "q_proj"])

    def test_it_installs_where_settings_finds_it_and_keeps_the_last_one(self):
        with tempfile.TemporaryDirectory() as root:
            models = Path(root) / "models"
            new = Path(root) / "new.gguf"
            new.write_bytes(b"GGUF" + b"\0" * 64)
            (models / "luma-brain").mkdir(parents=True)
            (models / "luma-brain" / mac.OWN_FILE).write_bytes(b"GGUF old")
            where = mac.install(new, models)
            self.assertEqual(where, models / "luma-brain" / "luma-brain-lora.gguf")
            self.assertEqual(where.read_bytes()[:4], b"GGUF")
            self.assertEqual((models / "luma-brain" / (mac.OWN_FILE + ".before-mac-training")).read_bytes(), b"GGUF old")
            with mock.patch.dict(os.environ, {"LUMA_MODEL_PATH": str(models / "Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf")}):
                self.assertEqual(mac.luma_models_dir(), models)

    def test_it_trains_on_the_cloud_runs_conversations_and_checks_with_its_judge(self):
        t = mac.trainer()
        rows = t.conversations()
        held = t.held_out(rows, 48)
        self.assertEqual(len(held), 48)
        self.assertTrue(all(r["messages"][0]["content"].startswith(t.SHORT_SYSTEM) for r in rows))
        summary, scores = t.summarize(held[:2], ["I don't know that one.", "It means to talk."], "check")
        self.assertEqual(summary["replies"], 2)
        self.assertIn("wrong_slang_meanings", summary)


if __name__ == "__main__":
    unittest.main()
