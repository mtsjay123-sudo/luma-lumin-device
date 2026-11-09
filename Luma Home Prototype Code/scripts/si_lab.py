"""The Super Intelligence labs: the cloud brain, apps, news and thinking, each measured the same way every time.

    python scripts/luma_lab.py cloud [--turns 12] [--model claude-sonnet-5-5] [--save cloud.json]

`cloud` holds one made-up conversation through Luma's real request path and reports, per turn: how much of what was
sent Claude had already read (its prompt cache), the time to the first words, the cost, and how many turns had to be
asked again another way. With an Anthropic key in LUMA_LAB_ANTHROPIC_KEY it talks to the real API and the numbers are
real (and billed to that key: about 30 cents on Sonnet or 60 on Opus for the default run). Without one it runs against a stand-in
that follows the cache's published rules and says so: those numbers show whether the request holds still, not how fast
Claude is.

The made-up person here is nobody: the life file and the conversation are invented for the lab.
"""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import statistics
import threading
import time

# Dollars per million tokens, as published in October 2026: (fresh input, output, read from cache). Writing to the
# five-minute cache costs 1.25 times fresh input. Check the pricing page before trusting a cost from here.
PRICES = {"claude-opus-5-5": (4.0, 20.0, 0.20), "claude-sonnet-5-5": (2.0, 10.0, 0.20), "claude-haiku-5-5": (0.10, 0.50, 0.01)}
WRITE = 1.25
SMALLEST = 512  # tokens: a beginning shorter than this isn't cached at all on these models
KEPT = 300      # seconds an entry lives after it was last written or read


def tokens(text):
    return max(1, len(text) // 4)


class PromptCache:
    """Claude's prompt cache, by its published rules, for requests that never leave this computer.

    A request is its blocks in order: the system blocks, then each message's blocks. A marker (cache_control) on a block
    saves everything up to and including it. A later request reads the longest beginning that was saved, is still fresh and
    is word for word the same: it looks at each of its own markers and up to 20 blocks back from each. A different model,
    effort or answer shape is a different cache. Reading an entry keeps it for another five minutes."""
    LOOK_BACK = 20

    def __init__(self):
        self.saved = {}  # hash of a beginning -> when it was last written or read

    @staticmethod
    def _blocks(body):
        system = body.get("system") or []
        out = [("system", {"type": "text", "text": system})] if isinstance(system, str) else [("system", b) for b in system]
        for message in body.get("messages") or []:
            content = message.get("content")
            blocks = [{"type": "text", "text": content}] if isinstance(content, str) else list(content or [])
            out += [(message.get("role"), block) for block in blocks]
        return out

    def use(self, body, now=None):
        """{"read", "written", "fresh"} in tokens for this request, and remember what it saved."""
        now = time.time() if now is None else now
        config = body.get("output_config") or {}
        running = hashlib.sha256(json.dumps([body.get("model"), config.get("effort"), config.get("format")], sort_keys=True).encode())
        places, marks, total = [], [], 0  # every block: (the hash of everything up to it, tokens up to it)
        for role, block in self._blocks(body):
            plain = {k: v for k, v in block.items() if k != "cache_control"}
            running.update(json.dumps([role, plain], sort_keys=True, ensure_ascii=False).encode())
            total += tokens(str(plain.get("text") or json.dumps(plain)))
            places.append((running.copy().hexdigest(), total))
            if block.get("cache_control"):
                marks.append(len(places) - 1)
        read = 0
        for mark in marks:
            for at in range(mark, max(-1, mark - self.LOOK_BACK - 1), -1):
                key, upto = places[at]
                if upto >= SMALLEST and now - self.saved.get(key, -1e18) <= KEPT:
                    read = max(read, upto)
                    self.saved[key] = now  # read: kept another five minutes
                    break
        last = places[marks[-1]][1] if marks and places[marks[-1]][1] >= SMALLEST else 0
        for mark in marks:
            key, upto = places[mark]
            if upto >= SMALLEST:
                self.saved[key] = now
        return {"read": read, "written": max(0, last - read), "fresh": total - max(read, last)}


def cost(model, used):
    """Dollars for one call, from the tokens it really used."""
    fresh, out, read = PRICES.get(model, PRICES["claude-sonnet-5-5"])
    return (used.get("fresh", 0) * fresh + used.get("written", 0) * fresh * WRITE + used.get("read", 0) * read + used.get("out", 0) * out) / 1e6


class StandIn(http.server.BaseHTTPRequestHandler):
    """Anthropic's API, on this computer: it answers every turn the same short way and counts tokens with PromptCache."""
    cache = PromptCache()
    seen = []
    reply = None         # a fixed answer (or body -> answer) for a test; otherwise a different plain line each turn
    LINES = ["Long shift. Glad you're off.", "Short two people is rough. Did you get a break at all?", "Of course you are. Idris is brand new.",
             "A text first is easy. She'll see it when she's up.", "That works. Something small is enough tonight.", "Go on, Pepper's earned it.",
             "Cold walks count double. How was she?", "Four days isn't the end of it. Tomorrow's a fresh start.", "March is still a ways off. One easy run gets you back.",
             "Something warm and quick. Pad thai, no shrimp?", "Never shrimp. I've got you.", "Good. Eat, then feet up.", "Anytime. I liked it too.",
             "Sleep well, Sam.", "Night."]
    refuse = None        # body -> an error message, to answer 400 with it
    clock = staticmethod(time.time)

    def log_message(self, *a):
        pass

    def _json(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self._json({"type": "model", "id": self.path.rsplit("/", 1)[1], "display_name": "Claude", "created_at": "2026-01-01T00:00:00Z"})

    def do_POST(self):
        cls = type(self)
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        cls.seen.append({"body": body, "beta": self.headers.get("anthropic-beta")})
        problem = cls.refuse(body) if cls.refuse else None
        if problem:
            return self._json({"type": "error", "error": {"type": "invalid_request_error", "message": problem}}, 400)
        used = cls.cache.use(body, cls.clock())
        usage = {"input_tokens": used["fresh"], "cache_read_input_tokens": used["read"], "cache_creation_input_tokens": used["written"], "output_tokens": 0}
        if cls.reply is None:  # a different line each turn of a conversation, the same line when the same turn is asked again
            turns = sum(1 for m in body.get("messages") or [] if m.get("role") == "user")
            reply = {"type": "reply", "text": cls.LINES[(turns - 1) % len(cls.LINES)]}
        else:
            reply = cls.reply(body) if callable(cls.reply) else cls.reply
        text = json.dumps(reply)
        message = {"id": "msg_lab", "type": "message", "role": "assistant", "model": body["model"], "content": [], "stop_reason": None,
                   "stop_sequence": None, "usage": usage}
        if not body.get("stream"):
            done = body.get("max_tokens") == 0
            return self._json({**message, "content": [] if done else [{"type": "text", "text": text}], "stop_reason": "max_tokens" if done else "end_turn"})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        events = [("message_start", {"type": "message_start", "message": message}),
                  ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}})]
        events += [("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[i:i + 12]}})
                   for i in range(0, len(text), 12)]
        events += [("content_block_stop", {"type": "content_block_stop", "index": 0}),
                   ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": tokens(text)}}),
                   ("message_stop", {"type": "message_stop"})]
        for name, data in events:
            self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode())
            self.wfile.flush()

    @classmethod
    def start(cls):
        cls.cache, cls.seen, cls.refuse, cls.reply = PromptCache(), [], None, None
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), cls)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return server


# A made-up person and a made-up evening. Nobody real.
LIFE = """- Your name is Sam
- You live in Tucson
- You work nights at the hospital pharmacy
- Your sister's name is Noor
- Noor (their sister) lives in Phoenix
- Noor (their sister) just had a baby, Idris
- Your dog's name is Pepper
- You're allergic to shellfish
- Your goal: run the half marathon in March
- You love thai food
- (2026-11-07) drove up to Phoenix to meet Idris. Noor looked exhausted but happy."""
TALK = ["hey, just got off shift", "it was a long one, we were short two people", "i keep thinking about noor and the baby",
        "yeah i should call her, it's just late there too", "maybe i'll text first", "pepper's staring at me, she wants a walk",
        "ok we're back, it's cold out", "i haven't run in four days", "the half is in march, i'm behind", "what should i eat, i'm starving",
        "nothing with shrimp obviously", "ok that sounds good", "thanks for hanging out with me tonight", "i think i'm going to sleep now", "night"]
FACTS = ["You work nights at the hospital pharmacy", "Noor (their sister) just had a baby, Idris", "Your goal: run the half marathon in March",
         "You're allergic to shellfish", "Your dog's name is Pepper"]
TOOLS = {"tasks.create": {"description": "Make a reminder", "fields": {"title": "string", "due": "string"}},
         "memory.remember": {"description": "Keep a fact", "fields": {"text": "string"}}}


def middle(values, share):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * share))] if ordered else None


def _totals(store):
    """What the cloud brain has used so far in this profile: calls and tokens, over every model."""
    out = {"calls": 0, "read": 0, "written": 0, "fresh": 0, "out": 0, "errors": 0, "again": 0}
    for day in (store.setting("usage") or {}).values():
        for name, row in day.items():
            if "local" in name:
                continue
            for key in ("calls", "read", "written", "fresh", "out", "errors"):
                out[key] += row.get(key, 0)
            out["again"] += sum((row.get("shapes") or {}).get(shape, 0) for shape in ("cached, then exact",))
    return out


def cloud(turns=12, model="claude-sonnet-5-5", legacy=False, pause=0.0):
    """One conversation through the real Luma (a throwaway one) with the cloud brain on, turn by turn: every trip to the
    brain a turn makes is counted, not just the reply. Returns the report."""
    import luma_lab
    from luma.llm import brain, cloud as claude
    key = os.environ.get("LUMA_LAB_ANTHROPIC_KEY", "").strip()
    real = bool(key)
    server, old = None, os.environ.get("ANTHROPIC_BASE_URL")
    if not real:
        server = StandIn.start()
        os.environ["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
        key = "sk-ant-lab"
    elif "ANTHROPIC_BASE_URL" in os.environ and not os.environ.get("LUMA_LAB_KEEP_BASE_URL"):
        os.environ.pop("ANTHROPIC_BASE_URL")  # the real API, not whatever this shell points at
    for learned in claude._learned.values():
        learned.discard(model)
    if legacy:
        claude._learned["exact_only"].add(model)
    profile = luma_lab.Profile(use_model=True)
    rows = []
    try:
        now = time.time()
        profile.store.put_many("memory", [{"text": line[2:], "created": now - 86400 * (40 - i)} for i, line in enumerate(LIFE.splitlines()) if not line.startswith("- (")])
        profile.store.set_setting("cloud_life", not legacy)  # the life file goes to the brain only in the new request
        brain.set_cloud(True, key=key, model=model)
        before = _totals(profile.store)
        for i, said in enumerate(TALK[:turns]):
            result = profile.say(said)
            after = _totals(profile.store)
            used = {k: after[k] - before[k] for k in after}
            before = after
            sent = used["read"] + used["written"] + used["fresh"]
            rows.append({"turn": i + 1, **used, "share_read": round(used["read"] / sent, 3) if sent else None,
                         "first_words_s": result["_first_words"], "seconds": result["_seconds"], "cost": round(cost(model, used), 6),
                         "error": result.get("text", "")[:60] if str(result.get("text", "")).startswith("ERROR") else None})
            if pause:
                time.sleep(pause)
    finally:
        profile.close()
        if server is not None:
            server.shutdown()
        if old is None:
            os.environ.pop("ANTHROPIC_BASE_URL", None)
        else:
            os.environ["ANTHROPIC_BASE_URL"] = old
        for learned in claude._learned.values():
            learned.discard(model)
    later = rows[1:]
    sent = sum(r["read"] + r["written"] + r["fresh"] for r in later)
    first = [r["first_words_s"] for r in rows]
    return {"kind": "cloud", "real": real, "model": model, "legacy": legacy, "turns": rows,
            "read_from_second_turn": round(sum(r["read"] for r in later) / sent, 3) if sent else None,
            "first_words_s": {"p50": middle(first, .5), "p95": middle(first, .95)} if real and first else None,
            "calls_per_turn": round(statistics.mean(r["calls"] for r in rows), 2) if rows else None,
            "tokens_per_turn": round(statistics.mean(r["read"] + r["written"] + r["fresh"] for r in rows)) if rows else None,
            "cost_per_turn": round(statistics.mean(r["cost"] for r in rows), 6) if rows else None,
            "asked_again": sum(r["again"] for r in rows), "failed": sum(1 for r in rows if r["error"]) + sum(r["errors"] for r in rows)}


def cloud_table(reports):
    lines = ["| Request | Model | Numbers | Trips to the brain per turn | Tokens sent per turn | Read from cache, turn 2 on | First words p50 | p95 | Cost per turn | Asked again | Failed |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in reports:
        first = r.get("first_words_s") or {}
        show = lambda v: f"{v:.2f} s" if isinstance(v, (int, float)) else "not measured"  # noqa: E731
        lines.append(f"| {'as before' if r['legacy'] else 'cache first'} | {r['model']} | {'real API' if r['real'] else 'stand-in'} | "
                     f"{r.get('calls_per_turn')} | {r.get('tokens_per_turn'):,} | "
                     f"{100 * (r['read_from_second_turn'] or 0):.0f}% | {show(first.get('p50'))} | {show(first.get('p95'))} | "
                     f"${r['cost_per_turn']:.5f} | {r['asked_again']} | {r['failed']} |")
    return "\n".join(lines)
