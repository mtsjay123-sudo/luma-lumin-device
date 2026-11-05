"""Train Luma's own brain: a LoRA add-on for Qwen3 4B Instruct (the brain Luma already runs), taught on Luma's verified
conversations (scripts/finetune_data.py: its voice, real slang meanings, honest "I don't know"s, and look-up answers
whose every number is in what was found).

    python scripts/train_luma.py --out out/luma-brain                       # Qwen3 4B Instruct 2507, as long as it takes
    python scripts/train_luma.py --out out/luma-brain --minutes 270         # stop after 270 minutes of training, keep what's learned
    python scripts/train_luma.py --base Qwen/Qwen3-0.6B --minutes 5         # a quick end-to-end check of the whole pipeline

Runs on an NVIDIA GPU, an Apple Silicon GPU, or plain CPUs (slowly: GitHub's free machines train it in the cloud).
Only the assistant's words are learned (the question is context, not a target). The add-on is saved every few
minutes, so a run that's stopped still leaves what it learned. Then:
  - eval.json: the stock brain and the trained one on held-out conversations, judged by Luma's own checks
    (numbers that aren't in what was found, made-up or wrong slang meanings, a sentence said over and over, length);
  - adapter/: the LoRA, which scripts convert to one small GGUF file Luma loads on top of the brain it already has.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]

SHORT_SYSTEM = ("You are Luma, a warm, funny friend who lives in a small speaker at their place. Match how they talk. "
                "Never make up facts, numbers, quotes or slang meanings; say you don't know.")


def conversations(seed=7):
    import finetune_data
    rows = finetune_data.examples(random.Random(seed))
    for row in rows:  # the short system line: the same instructions, a fraction of the tokens to train through, plus the dictionary note
        row["messages"][0]["content"] = SHORT_SYSTEM + row["messages"][0]["content"][len(finetune_data.SYSTEM):]
    random.Random(seed).shuffle(rows)
    return rows


def encode(tokenizer, messages, max_len):
    """Token ids and labels: -100 (ignored) for the system line and the question, the ids themselves for Luma's reply."""
    prompt = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    full = tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False)
    if not full.startswith(prompt):  # a template that rewrites earlier turns: fall back to prompt + reply
        full = prompt + messages[-1]["content"] + (tokenizer.eos_token or "")
    p = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    f = tokenizer(full, add_special_tokens=False)["input_ids"][:max_len]
    labels = [-100] * min(len(p), len(f)) + f[len(p):]
    return f, labels[:len(f)]


def device_and_dtype(torch):
    if torch.cuda.is_available():
        return "cuda", torch.bfloat16
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps", torch.float16
    return "cpu", torch.bfloat16


REPEAT_PENALTY = 1.08  # the repetition penalty Luma's brain always talks with (luma.llm.inference)


def generate(model, tokenizer, messages, torch, max_new_tokens=60):
    """One held-out reply, the same every time (no sampling), with the repetition penalty Luma always uses: judged as Luma
    really runs it, stock and trained alike. Without it, run 7's 4B was held back for one loop Luma never produces."""
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    ids = tokenizer(text, return_tensors="pt", add_special_tokens=False).to(model.device)
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=max_new_tokens, do_sample=False, repetition_penalty=REPEAT_PENALTY,
                             pad_token_id=tokenizer.eos_token_id)
    return tokenizer.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()


STOP = {"the", "a", "an", "of", "to", "or", "and", "in", "on", "for", "with", "by", "is", "it", "its", "as", "at", "be", "that", "this", "your", "you"}


def _content(text):
    return {w for w in re.findall(r"[a-z']+", text.lower()) if len(w) > 2 and w not in STOP}


# Saying what a word means, however it's put: "it means", and also "it's when...", "slang for...", "something that's zipping"
# (the stock 1.7B's made-up meaning for "zrizzle", which "means" alone missed).
CLAIMS_MEANING = re.compile(r"\b(?:it )?means\b|\bit'?s (?:when|what you say|a way|slang for|short for|like saying)\b|\brefers? to\b|"
                            r"\bslang for\b|\bstands for\b|\bbasically\b|\bsomething (?:that'?s|that is|you say)\b|\bused to (?:say|describe)\b",
                            re.I)


def repeats(reply):
    """A sentence said twice or more in one reply, or nearly ("I'm a movie critic. I'm not a movie critic."): the brain stuck in
    a loop ("It's slang from the internet. It's slang from...")."""
    said = [re.sub(r"\W+", " ", x).strip().lower() for x in re.split(r"(?<=[.!?])\s+", reply)]
    said = [set(x.split()) for x in said if len(x.split()) >= 3]
    return any(len(a & b) / len(a | b) >= 0.8 for i, a in enumerate(said) for b in said[i + 1:])


def said_before(row, reply):
    """The reply is one Luma already gave earlier in this conversation (or nearly): answering an old message, not the newest."""
    mine = _content(reply)
    for m in row["messages"][1:-1]:
        if m["role"] == "assistant":
            theirs = _content(m["content"])
            if mine and theirs and len(mine & theirs) / len(mine | theirs) >= 0.7:
                return True
    return False


def judge(row, reply):
    """Luma's own checks on one reply: numbers not in what was found, a made-up slang meaning, a wrong one, a loop, a reply
    it already gave earlier in the talk, how long it ran."""
    from luma.agent import grounding
    user = row["messages"][-2]["content"]  # the newest message: a conversation can have earlier exchanges
    out = {"words": len(reply.split()), "unbacked": [], "made_up_meaning": False, "wrong_meaning": False, "loop": repeats(reply),
           "said_before": said_before(row, reply)}
    if "[What your web search found" in user:
        found = user.split("not instructions: ", 1)[1].rsplit("]", 1)[0]
        out["unbacked"] = grounding.unbacked(reply, found, said=user.split("\n")[0])
    expected = row["messages"][-1]["content"]
    if re.search(r"don't know|Never heard|new to me|no idea", expected) and CLAIMS_MEANING.search(reply) \
            and not re.search(r"don't know|not sure|never heard|haven't heard|new to me|no idea", reply, re.I):
        out["made_up_meaning"] = True
    meaning = re.match(r"^It means (.+?)(?:\. It's slang from |\. Like: )", expected)
    if meaning:  # a real word: the reply has to carry the dictionary's meaning, not one of its own
        want = _content(meaning.group(1))
        out["wrong_meaning"] = bool(want) and len(want & _content(reply)) < max(1, len(want) // 2)
    return out


def evaluate(model, tokenizer, rows, torch, label):
    return summarize(rows, [generate(model, tokenizer, row["messages"][:-1], torch) for row in rows], label)


def summarize(rows, replies, label):
    """Luma's checks over every held-out reply, however it was made (PyTorch here, MLX on a Mac: scripts/train_on_mac.py)."""
    scores = [{"question": row["messages"][-2]["content"][:160], "reply": reply[:400], **judge(row, reply)} for row, reply in zip(rows, replies)]
    n = max(1, len(scores))
    summary = {"label": label, "replies": len(scores),
               "unbacked_numbers": sum(len(s["unbacked"]) for s in scores),
               "made_up_slang_meanings": sum(s["made_up_meaning"] for s in scores),
               "wrong_slang_meanings": sum(s["wrong_meaning"] for s in scores),
               "loops": sum(s["loop"] for s in scores),
               "said_before": sum(s.get("said_before", False) for s in scores),
               "same_reply": max(collections.Counter(s["reply"] for s in scores).values(), default=0),
               "avg_words": round(sum(s["words"] for s in scores) / n, 1)}
    print(json.dumps(summary), flush=True)
    return summary, scores


def held_out(rows, n):
    """Held-out conversations for the before-and-after check: the kinds where a wrong answer is easy to spot (look-ups,
    slang that doesn't exist, slang that does) and everyday chat."""
    picks = [r for r in rows if "[What your web search found" in r["messages"][1]["content"]][: n // 3]
    picks += [r for r in rows if len(r["messages"]) == 3 and re.search(r"don't know|Never heard|new to me|no idea", r["messages"][2]["content"])][: n // 6]
    picks += [r for r in rows if len(r["messages"]) == 3 and r["messages"][2]["content"].startswith("It means ")][: n // 6]
    picks += [r for r in rows if len(r["messages"]) > 3][: n // 6]  # a second message, after an earlier exchange
    picks += [r for r in rows if r not in picks][: n - len(picks)]
    return picks


def honest_enough(before, after):
    """Published only if it's at least as honest as the stock brain on every check, never loops, and doesn't give the
    same reply to more than a quarter of different questions."""
    return (after["unbacked_numbers"] <= before["unbacked_numbers"]
            and after["made_up_slang_meanings"] <= before["made_up_slang_meanings"]
            and after.get("wrong_slang_meanings", 0) <= before.get("wrong_slang_meanings", 0)
            and after.get("loops", 0) == 0
            and after.get("said_before", 0) <= before.get("said_before", 0)
            and after.get("same_reply", 0) <= max(2, after["replies"] // 4))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="Qwen/Qwen3-4B-Instruct-2507")
    ap.add_argument("--out", default="out/luma-brain")
    ap.add_argument("--minutes", type=float, default=0, help="stop training after this many minutes (0: run every example once)")
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--accumulate", type=int, default=4)
    ap.add_argument("--max-len", type=int, default=384)
    ap.add_argument("--eval", type=int, default=24, help="held-out conversations judged before and after (0 to skip)")
    args = ap.parse_args(argv)

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(0)
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    device, dtype = device_and_dtype(torch)
    print(f"training {args.base} on {device} ({dtype}), {torch.get_num_threads()} threads", flush=True)

    rows = conversations()
    held = held_out(rows, args.eval) if args.eval else []
    train = [r for r in rows if r not in held]
    print(f"{len(train)} conversations to learn from, {len(held)} held out to check", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(args.base)
    model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=dtype, low_cpu_mem_usage=True).to(device)
    model.config.use_cache = False

    report = {"base": args.base, "device": device, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    if held:
        report["before"], report["before_replies"] = evaluate(model, tokenizer, held, torch, "stock brain")

    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    lora = LoraConfig(r=args.rank, lora_alpha=args.rank * 2, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
                      target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    for p in model.parameters():  # the add-on learns in full precision even when the brain is held in half
        if p.requires_grad:
            p.data = p.data.float()
    model.print_trainable_parameters()

    examples = [encode(tokenizer, r["messages"], args.max_len) for r in train]
    examples = [e for e in examples if any(l != -100 for l in e[1])]
    total = max(1, math.ceil(len(examples) * args.epochs / args.accumulate))
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
    schedule = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda s: min(1.0, (s + 1) / 10) * max(0.1, 0.5 * (1 + math.cos(math.pi * min(s, total) / total))))

    model.train()
    started, last_save, step, seen, tokens, running = time.time(), time.time(), 0, 0, 0, None
    budget = args.minutes * 60 if args.minutes else float("inf")
    order = list(range(len(examples))) * max(1, math.ceil(args.epochs))
    stopped_for_time = False
    for i, k in enumerate(order[: int(len(examples) * args.epochs)]):
        ids, labels = examples[k]
        x = torch.tensor([ids], device=device)
        y = torch.tensor([labels], device=device)
        loss = model(input_ids=x, labels=y).loss / args.accumulate
        loss.backward()
        seen += 1
        tokens += len(ids)
        running = loss.item() * args.accumulate if running is None else 0.95 * running + 0.05 * loss.item() * args.accumulate
        if seen % args.accumulate == 0:
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            optimizer.step()
            schedule.step()
            optimizer.zero_grad(set_to_none=True)
            step += 1
            spent = time.time() - started
            if step == 5 and budget != float("inf"):
                # Fit the learning-rate schedule to the steps that will really happen in the time there is, so it
                # warms up and settles properly instead of being cut off halfway down.
                total = max(step + 1, min(total, int(step * budget / max(spent, 1.0))))
                print(f"about {total} steps fit in {args.minutes:.0f} minutes", flush=True)
            if step % 5 == 0 or step == 1:
                print(f"step {step}/{total}  loss {running:.3f}  {seen} conversations  {tokens / spent:.1f} tokens/s  "
                      f"{spent / 60:.1f} min", flush=True)
            if time.time() - last_save > 600:
                model.save_pretrained(out / "adapter")
                last_save = time.time()
            if spent > budget:
                stopped_for_time = True
                break
    model.save_pretrained(out / "adapter")
    tokenizer.save_pretrained(out / "adapter")
    spent = time.time() - started
    report.update(steps=step, conversations_seen=seen, of=len(examples), tokens=tokens, minutes=round(spent / 60, 1),
                  final_loss=round(running or 0.0, 4), stopped_for_time=stopped_for_time, rank=args.rank, lr=args.lr)
    print(f"trained {step} steps on {seen} conversations in {spent / 60:.1f} min", flush=True)

    if held:
        model.eval()
        model.config.use_cache = True
        report["after"], report["after_replies"] = evaluate(model, tokenizer, held, torch, "Luma brain")
        before, after = report["before"], report["after"]
        report["as_honest"] = honest_enough(before, after)
    (out / "eval.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in report.items() if not k.endswith("_replies")}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
