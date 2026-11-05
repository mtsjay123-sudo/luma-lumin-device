"""Train Luma's own brain on this Mac with Apple's MLX: every conversation, a few times over, judged by the same checks as
the cloud run, and put where Luma finds it (Settings > Brain > "Luma's own brain" > Use it).

    bash scripts/train_on_mac.sh                  # sets up its own Python, then runs this
    python scripts/train_on_mac.py --epochs 2     # inside that Python

GitHub's free machines train about ten tokens a second on plain CPUs, so the cloud run stops at a time budget before it has
seen every conversation. An Apple Silicon Mac's graphics chip trains the same add-on on all of them, more than once, and
checks the result before anything changes:

  1. the conversations (scripts/finetune_data.py, through train_luma.conversations(): the short system line plus the
     dictionary note Luma's brain gets live), minus the held-out ones the check uses;
  2. a LoRA add-on on Qwen3 4B Instruct 2507 (the brain Luma ships and the one the device runs): rank 16, every layer,
     only Luma's words learned (mask_prompt), a cosine schedule over the whole run;
  3. the stock brain and the trained one answer the held-out conversations, judged by train_luma.judge: numbers that
     weren't in what was found, made-up or wrong slang meanings, a sentence said over and over, one reply to everything;
  4. the add-on is rewritten as a PEFT adapter and converted with llama.cpp into the one small GGUF file Luma loads on top
     of the brain it already has, and installed only if it's at least as honest as the stock brain on every check.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

BASE = "Qwen/Qwen3-4B-Instruct-2507"
KEYS = ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj", "mlp.gate_proj", "mlp.up_proj", "mlp.down_proj"]
OWN_FILE = "luma-brain-lora.gguf"


def trainer():
    """scripts/train_luma.py: the same conversations, held-out set, judge and gate as the cloud run (it needs no PyTorch for these)."""
    spec = importlib.util.spec_from_file_location("train_luma", ROOT / "scripts" / "train_luma.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps({"messages": r["messages"]}, ensure_ascii=False) + "\n" for r in rows))


def config(args, data, adapters, iters):
    warm = min(40, max(5, iters // 20))
    return {
        "model": args.base, "train": True, "data": str(data), "fine_tune_type": "lora", "mask_prompt": True,
        "num_layers": -1, "batch_size": args.batch, "iters": iters, "val_batches": -1, "learning_rate": args.lr,
        "steps_per_report": 10, "steps_per_eval": max(50, iters // 6), "save_every": 100, "adapter_path": str(adapters),
        "max_seq_length": args.max_len, "grad_checkpoint": True, "seed": 7,
        "lr_schedule": {"name": "cosine_decay", "warmup": warm, "warmup_init": 1e-7, "arguments": [args.lr, max(1, iters - warm), args.lr * 0.05]},
        "lora_parameters": {"keys": KEYS, "rank": args.rank, "scale": args.alpha / args.rank, "dropout": 0.05},
    }


def run_mlx_lora(cfg_path):
    """mlx-lm's trainer, by its newer name first ("python -m mlx_lm lora") and its older one if that isn't there."""
    for command in ([sys.executable, "-m", "mlx_lm", "lora", "--config", str(cfg_path)],
                    [sys.executable, "-m", "mlx_lm.lora", "--config", str(cfg_path)]):
        result = subprocess.run(command)
        if result.returncode == 0:
            return
    raise SystemExit("mlx-lm's trainer didn't finish. The lines above say why.")


def replies(base, rows, adapter=None, max_tokens=60):
    from mlx_lm import generate, load
    model, tokenizer = load(base, adapter_path=str(adapter)) if adapter else load(base)
    out = []
    for row in rows:
        try:
            prompt = tokenizer.apply_chat_template(row["messages"][:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        except TypeError:
            prompt = tokenizer.apply_chat_template(row["messages"][:-1], tokenize=False, add_generation_prompt=True)
        out.append(generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens, verbose=False).strip())
    return out


def to_peft(adapters, out, base, rank, alpha):
    """mlx-lm's add-on as the PEFT adapter llama.cpp converts: lora_a (in, r) and lora_b (r, out) become lora_A (r, in) and
    lora_B (out, r) under Hugging Face's names, and the scale becomes lora_alpha = scale x rank."""
    import mlx.core as mx
    weights = mx.load(str(adapters / "adapters.safetensors"))
    peft = {}
    for name, value in weights.items():
        if name.endswith(".lora_a"):
            peft[f"base_model.model.{name[:-len('.lora_a')]}.lora_A.weight"] = value.T.astype(mx.float32)
        elif name.endswith(".lora_b"):
            peft[f"base_model.model.{name[:-len('.lora_b')]}.lora_B.weight"] = value.T.astype(mx.float32)
    if not peft:
        raise SystemExit("The trained add-on had no LoRA weights in it.")
    out.mkdir(parents=True, exist_ok=True)
    mx.save_safetensors(str(out / "adapter_model.safetensors"), peft)
    modules = sorted({k.split(".lora_")[0].rsplit(".", 1)[-1] for k in peft})
    (out / "adapter_config.json").write_text(json.dumps({
        "peft_type": "LORA", "task_type": "CAUSAL_LM", "base_model_name_or_path": base, "r": rank, "lora_alpha": alpha,
        "lora_dropout": 0.0, "target_modules": modules, "bias": "none", "fan_in_fan_out": False, "inference_mode": True}, indent=2))
    return len(peft) // 2


def to_gguf(peft_dir, out_file, base, work):
    """llama.cpp's own converter, the same one the cloud run uses."""
    llama = work / "llama.cpp"
    if not (llama / "convert_lora_to_gguf.py").exists():
        subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/ggml-org/llama.cpp", str(llama)], check=True)
    from huggingface_hub import snapshot_download
    base_dir = snapshot_download(base, allow_patterns=["*.json", "*.model", "*.txt", "*.safetensors", "*.tiktoken"])
    env = {**os.environ, "PYTHONPATH": str(llama / "gguf-py")}
    subprocess.run([sys.executable, str(llama / "convert_lora_to_gguf.py"), str(peft_dir), "--base", base_dir,
                    "--outtype", "f16", "--outfile", str(out_file)], check=True, env=env)
    data = out_file.read_bytes()[:4]
    if data != b"GGUF":
        raise SystemExit("The converted file isn't a GGUF file.")


def luma_models_dir():
    """Where Luma keeps its brains: LUMA_MODEL_PATH's folder if it's set, else Luma Desktop's, else this checkout's models/."""
    if os.environ.get("LUMA_MODEL_PATH"):
        return Path(os.environ["LUMA_MODEL_PATH"]).expanduser().parent
    desktop = Path.home() / "Library" / "Application Support" / "Luma" / "runtime" / "models"
    return desktop if desktop.is_dir() else ROOT / "models"


def install(gguf, folder):
    target = folder / "luma-brain"
    target.mkdir(parents=True, exist_ok=True)
    final = target / OWN_FILE
    if final.exists():
        shutil.copy2(final, target / (OWN_FILE + ".before-mac-training"))  # the last one stays, in case
    part = target / (OWN_FILE + ".part")
    shutil.copy2(gguf, part)
    part.replace(final)
    return final


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--out", default="out/mac-brain")
    ap.add_argument("--epochs", type=float, default=2.0, help="times through every conversation")
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=float, default=32.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--eval", type=int, default=48, help="held-out conversations judged before and after")
    ap.add_argument("--no-install", action="store_true", help="train and check, but leave Luma's brain as it is")
    args = ap.parse_args(argv)

    t = trainer()
    out = (ROOT / args.out).resolve()
    data, adapters = out / "data", out / "adapters"
    data.mkdir(parents=True, exist_ok=True)
    rows = t.conversations()
    held = t.held_out(rows, args.eval)
    train = [r for r in rows if r not in held]
    write_jsonl(data / "train.jsonl", train)
    write_jsonl(data / "valid.jsonl", held)  # the loss on conversations it never trains on
    iters = max(10, math.ceil(len(train) * args.epochs / args.batch))
    cfg_path = out / "lora.yaml"
    cfg_path.write_text(json.dumps(config(args, data, adapters, iters), indent=2))  # JSON is YAML too
    print(f"{len(train)} conversations to learn from ({args.epochs:g} times through), {len(held)} held out to check; {iters} steps", flush=True)

    report = {"base": args.base, "device": "mac (mlx)", "epochs": args.epochs, "rank": args.rank, "lr": args.lr,
              "conversations_seen": len(train), "of": len(rows), "steps": iters}
    print("The stock brain answers the held-out conversations first...", flush=True)
    report["before"], report["before_replies"] = t.summarize(held, replies(args.base, held), "stock brain")

    started = time.time()
    run_mlx_lora(cfg_path)
    report["minutes"] = round((time.time() - started) / 60, 1)

    report["after"], report["after_replies"] = t.summarize(held, replies(args.base, held, adapter=adapters), "Luma brain")
    report["as_honest"] = t.honest_enough(report["before"], report["after"])
    n = to_peft(adapters, out / "adapter", args.base, args.rank, args.alpha * 1.0)
    print(f"{n} LoRA layers rewritten for llama.cpp", flush=True)
    gguf = out / OWN_FILE
    to_gguf(out / "adapter", gguf, args.base, out)
    (out / "eval.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    subprocess.run([sys.executable, str(ROOT / "scripts" / "train_report.py"), str(out / "eval.json")])

    if not report["as_honest"]:
        print(f"\nNot installed: on the held-out check it wasn't at least as honest as the stock brain (see {out / 'eval.json'}).")
        return 1
    if args.no_install:
        print(f"\nPassed. The add-on is at {gguf} (not installed, as asked).")
        return 0
    where = install(gguf, luma_models_dir())
    print(f"\nPassed and installed: {where}\nIn Luma: Settings > Brain > \"Luma's own brain\" > Use it. (Don't press \"Get it\": that downloads the cloud-trained one over it.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
