"""What each brain is used for, and what it costs: calls, tokens, time and errors per model, per day.

Tokens are counted roughly (about four characters each) so the same measure works for the local
models and both cloud brains. Local models cost nothing per call. For the cloud brains the owner can
enter their price per million tokens in Settings; Luma never guesses a price.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime

_lock = threading.Lock()
KEEP_DAYS = 31


def tokens(value):
    try:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(value)
    return max(1, len(text) // 4)


def record(store, model, tokens_in, tokens_out, seconds, ok=True, tier=None):
    """Count one call. Best effort: counting can never break the call it's counting."""
    if store is None:
        return
    try:
        _record(store, model, tokens_in, tokens_out, seconds, ok, tier)
    except Exception:
        pass


def _record(store, model, tokens_in, tokens_out, seconds, ok, tier):
    day = datetime.now().strftime("%Y-%m-%d")
    with _lock:
        usage = dict(store.setting("usage") or {})
        today = dict(usage.get(day) or {})
        row = dict(today.get(model) or {"calls": 0, "tokens_in": 0, "tokens_out": 0, "seconds": 0.0, "errors": 0})
        row["calls"] += 1
        row["tokens_in"] += int(tokens_in)
        row["tokens_out"] += int(tokens_out)
        row["seconds"] = round(row["seconds"] + float(seconds), 2)
        row["errors"] += 0 if ok else 1
        if tier:
            row.setdefault("tiers", {})[tier] = row.get("tiers", {}).get(tier, 0) + 1
        today[model] = row
        usage[day] = today
        for old in sorted(usage)[:-KEEP_DAYS]:
            usage.pop(old, None)
        store.set_setting("usage", usage)


def summary(store, days=30):
    """Totals per model over the last `days`, with a cost estimate wherever the owner set a price."""
    usage = (store.setting("usage") or {}) if store is not None else {}
    prices = (store.setting("model_prices") or {}) if store is not None else {}
    totals = {}
    for day in sorted(usage)[-days:]:
        for model, row in usage[day].items():
            t = totals.setdefault(model, {"calls": 0, "tokens_in": 0, "tokens_out": 0, "seconds": 0.0, "errors": 0})
            for key in ("calls", "tokens_in", "tokens_out", "errors"):
                t[key] += row.get(key, 0)
            t["seconds"] = round(t["seconds"] + row.get("seconds", 0), 2)
    for model, t in totals.items():
        price = prices.get(model)
        t["cost"] = round(t["tokens_in"] / 1e6 * price[0] + t["tokens_out"] / 1e6 * price[1], 4) if isinstance(price, (list, tuple)) and len(price) == 2 else None
    return {"models": totals, "since": sorted(usage)[-days:][0] if usage else None}


class Timer:
    def __init__(self):
        self.started = time.time()

    @property
    def seconds(self):
        return time.time() - self.started
