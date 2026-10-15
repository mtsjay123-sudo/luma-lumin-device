"""Train Luma's understanding model from generated scenarios.

    PYTHONPATH=src python3 scripts/train_understanding.py [--samples 800000] [--epochs 3]

Writes src/luma/agent/understanding.npz. Only numpy is needed. It generates the
training messages from luma.agent.scenarios (every feature, said every which way),
trains a softmax layer over hashed n-grams with AdaGrad, calibrates a temperature on
deliberately messy held-out messages, and reports accuracy on held-out scenarios and
on hand-written real talk (tests/real_talk.py) that the generator never saw.
"""
from __future__ import annotations

import argparse
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from luma.agent import scenarios, understanding  # noqa: E402


def featurize(texts):
    return [np.asarray(understanding.features(t), dtype=np.int32) for t in texts]


def csr(texts, workers=8):
    chunks = [texts[i:i + 5000] for i in range(0, len(texts), 5000)]
    with Pool(workers) as pool:
        rows = [r for part in pool.map(featurize, chunks) for r in part]
    lengths = np.fromiter((len(r) for r in rows), dtype=np.int64, count=len(rows))
    offsets = np.zeros(len(rows) + 1, dtype=np.int64)
    np.cumsum(lengths, out=offsets[1:])
    return np.concatenate(rows), offsets


def batch_logits(W, b, flat, offsets, ids):
    starts, ends = offsets[ids], offsets[ids + 1]
    idx = np.concatenate([flat[s:e] for s, e in zip(starts, ends)])
    seg = np.repeat(np.arange(len(ids)), ends - starts)
    bounds = np.concatenate([[0], np.cumsum(ends - starts)[:-1]])  # every message has at least its length feature
    logits = np.add.reduceat(W[idx], bounds, axis=0)
    return logits + b, idx, seg


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def train(flat, offsets, y, k, epochs, lr=0.25, batch=512, seed=0):
    rng = np.random.default_rng(seed)
    W = np.zeros((understanding.BUCKETS, k), dtype=np.float32)
    H = np.full((understanding.BUCKETS, k), 1e-6, dtype=np.float32)
    b = np.zeros(k, dtype=np.float32)
    hb = np.full(k, 1e-6, dtype=np.float32)
    n = len(y)
    for epoch in range(epochs):
        order = rng.permutation(n)
        loss, t0 = 0.0, time.time()
        for start in range(0, n, batch):
            ids = order[start:start + batch]
            logits, idx, seg = batch_logits(W, b, flat, offsets, ids)
            p = softmax(logits)
            loss -= np.log(p[np.arange(len(ids)), y[ids]] + 1e-9).sum()
            g = p
            g[np.arange(len(ids)), y[ids]] -= 1.0
            g /= len(ids)
            uniq, inv = np.unique(idx, return_inverse=True)
            grad = np.zeros((len(uniq), k), dtype=np.float32)
            np.add.at(grad, inv, g[seg])
            grad += 1e-6 * W[uniq]
            H[uniq] += grad * grad
            W[uniq] -= lr * grad / np.sqrt(H[uniq])
            gb = g.sum(axis=0)
            hb += gb * gb
            b -= lr * gb / np.sqrt(hb)
        print(f"  epoch {epoch + 1}: loss {loss / n:.4f} ({time.time() - t0:.0f}s)", flush=True)
    return W, b


def predict(W, b, flat, offsets, temperature=1.0):
    out = []
    for start in range(0, len(offsets) - 1, 4096):
        ids = np.arange(start, min(start + 4096, len(offsets) - 1))
        logits, _, _ = batch_logits(W, b, flat, offsets, ids)
        out.append(softmax(logits / temperature))
    return np.concatenate(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=800_000)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--out", default=str(understanding.MODEL_PATH))
    args = ap.parse_args()
    intents = list(scenarios.INTENTS)
    k = len(intents)
    base, slang = scenarios.count()
    print(f"{k} intents; the scenarios combine into {base:,} messages ({slang:,} with slang). Sampling {args.samples:,} to learn from.")

    t0 = time.time()
    train_pairs = list(scenarios.generate(args.samples, seed=11))
    held = list(scenarios.generate(20_000, seed=22))
    rng = __import__("random").Random(33)
    hard = [(scenarios.say(i, rng, 0.95), i) for i in rng.choices(intents, k=10_000)]
    print(f"generated in {time.time() - t0:.0f}s; featurizing…", flush=True)
    t0 = time.time()
    flat, offsets = csr([t for t, _ in train_pairs])
    y = np.array([intents.index(i) for _, i in train_pairs])
    print(f"featurized {len(train_pairs):,} in {time.time() - t0:.0f}s ({len(flat) / len(train_pairs):.0f} features each)", flush=True)

    W, b = train(flat, offsets, y, k, args.epochs)

    def accuracy(pairs, temperature=1.0):
        f, o = csr([t for t, _ in pairs])
        p = predict(W, b, f, o, temperature)
        truth = np.array([intents.index(i) for _, i in pairs])
        return (p.argmax(1) == truth).mean(), p, truth

    acc, _, _ = accuracy(held)
    hacc, hp, htruth = accuracy(hard)
    # Calibrate: the temperature that makes confidence honest on messy messages.
    f, o = csr([t for t, _ in hard])
    best_t, best_nll = 1.0, 1e9
    for t in [0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.2, 2.6, 3.0, 3.5]:
        p = predict(W, b, f, o, t)
        nll = -np.log(p[np.arange(len(htruth)), htruth] + 1e-9).mean()
        if nll < best_nll:
            best_t, best_nll = t, nll
    print(f"held-out scenarios: {acc:.1%}   very messy ones: {hacc:.1%}   temperature {best_t}")
    try:
        from real_talk import REAL_TALK
        rt = [(t, i) for t, i in REAL_TALK if i in intents]
        racc, rp, rtruth = accuracy(rt, best_t)
        print(f"hand-written real talk (never generated): {racc:.1%} of {len(rt)}")
        for (t, i), row in zip(rt, rp):
            if intents[row.argmax()] != i:
                print(f"    miss: {t!r:60} wanted {i}, got {intents[row.argmax()]} ({row.max():.0%})")
    except ImportError:
        pass

    used = np.flatnonzero(np.abs(W).max(axis=1) > 1e-4)
    rows = W[used]
    scale = np.maximum(np.abs(rows).max(axis=1), 1e-8) / 127.0
    q = np.round(rows / scale[:, None]).astype(np.int8)
    np.savez_compressed(args.out, intents=np.array(intents), rows=used.astype(np.int32), q=q, scale=scale.astype(np.float32),
                        bias=b.astype(np.float32), temperature=np.float32(best_t))
    print(f"saved {args.out} ({Path(args.out).stat().st_size / 1e6:.1f} MB, {len(used):,} feature rows)")


if __name__ == "__main__":
    main()
