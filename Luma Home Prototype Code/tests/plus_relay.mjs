// A stand-in for Luma Cloud, for the home's tests and the Plus lab: the relay's own code (api/_lib/luma-cloud.js) on an
// in-memory database, with a made-up Claude behind it. Nothing leaves this computer and no key is real.
// Prints {"port": N} on its first line once it's listening. The /__lab endpoints exist only here.
import http from "node:http";
import { createHandler, period } from "../../api/_lib/luma-cloud.js";
import { memoryDb } from "../../api/_lib/luma-memory-db.js";

const db = memoryDb();
const env = { LUMA_CLOUD_PUBLIC_URL: "http://127.0.0.1", ANTHROPIC_API_KEY: "lumas-own-key-for-claude", LUMA_BRAIN_ZERO_RETENTION: "1",
  ...JSON.parse(process.env.LUMA_LAB_RELAY_ENV || "{}") };
const lab = {
  seen: [],          // what the made-up Claude was sent, call by call
  status: 200,       // what it answers with
  reply: { type: "reply", text: "I'm here. Tell me about your day, Marvin." },
  usage: { input_tokens: 150, cache_read_input_tokens: 3200, cache_creation_input_tokens: 300 },
  out: 24,
  pause_ms: 0,       // a wait after the first words, so a test can tell words came before the end
  step_ms: 0,        // a wait between every few words after that
  ahead_ms: 0,       // the clock, moved forward (to cross into next month)
};
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let signups = 0;
const event = (name, data) => `event: ${name}\ndata: ${JSON.stringify({ type: name, ...data })}\n\n`;

// The made-up Claude: answers in Luma's proposal shape, a few letters at a time, the way the real one streams.
async function claude(url, init = {}) {
  const body = JSON.parse(init.body);
  const call = { url, key: init.headers["x-api-key"], beta: init.headers["anthropic-beta"] || null, authorization: init.headers.authorization || null,
    body, stopped: false, finished: false };
  lab.seen.push(call);
  if (lab.status >= 400) {
    const text = JSON.stringify({ type: "error", error: { type: lab.status === 529 ? "overloaded_error" : "invalid_request_error", message: "made-up trouble" } });
    return { ok: false, status: lab.status, text: async () => text };
  }
  const text = JSON.stringify(lab.reply);
  const message = { id: "msg_lab", type: "message", role: "assistant", model: body.model, content: [], stop_reason: null, stop_sequence: null, usage: { ...lab.usage, output_tokens: 1 } };
  if (!body.stream) {
    const whole = { ...message, content: body.max_tokens ? [{ type: "text", text }] : [], stop_reason: body.max_tokens ? "end_turn" : "max_tokens", usage: { ...lab.usage, output_tokens: body.max_tokens ? lab.out : 0 } };
    return { ok: true, status: 200, text: async () => JSON.stringify(whole) };
  }
  const pieces = [event("message_start", { message }), event("content_block_start", { index: 0, content_block: { type: "text", text: "" } })];
  for (let at = 0; at < text.length; at += 9) pieces.push(event("content_block_delta", { index: 0, delta: { type: "text_delta", text: text.slice(at, at + 9) } }));
  pieces.push(event("content_block_stop", { index: 0 }), event("message_delta", { delta: { stop_reason: "end_turn", stop_sequence: null }, usage: { output_tokens: lab.out } }),
    event("message_stop", {}));
  async function* stream() {
    for (let i = 0; i < pieces.length; i += 1) {
      if (init.signal?.aborted) {
        call.stopped = true;
        throw Object.assign(new Error("This operation was aborted"), { name: "AbortError" });
      }
      yield new TextEncoder().encode(pieces[i]);
      if (i === 5 && lab.pause_ms) await sleep(lab.pause_ms);
      else if (i > 5 && lab.step_ms) await sleep(lab.step_ms);
    }
    call.finished = true;
  }
  return { ok: true, status: 200, body: stream() };
}

// LUMA_LAB_REAL_UPSTREAM: the brain behind the relay is another process on this computer (LUMA_BRAIN_UPSTREAM), reached
// over HTTP the way Anthropic is, instead of the made-up Claude above. The Plus lab uses it to compare like with like.
const brainBehind = process.env.LUMA_LAB_REAL_UPSTREAM ? fetch : claude;
const handler = createHandler(() => ({ env, db, fetch: brainBehind, now: () => Date.now() + lab.ahead_ms }));

async function read(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {};
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  const json = (status, data) => { res.statusCode = status; res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(data)); };
  try {
    if (url.pathname === "/__lab") {
      if (req.method === "POST") {
        const ask = await read(req);
        if (ask.plus !== undefined) for (const account of db.t.accounts) Object.assign(account, ask.plus ? { plan: "plus", subscription_status: "active" } : { plan: "free", subscription_status: null });
        if (ask.unsay) for (const account of db.t.accounts) Object.assign(account, { brain_consent_at: null, brain_consent_words: null });
        if (ask.env) Object.assign(env, ask.env);
        if (ask.forget) { lab.seen.length = 0; db.t.brain = new Map(); }
        for (const key of ["status", "reply", "usage", "out", "pause_ms", "step_ms", "ahead_ms"]) if (ask[key] !== undefined) lab[key] = ask[key];
      }
      const month = period(Date.now() + lab.ahead_ms);
      const used = await Promise.all(db.t.accounts.map((account) => db.brainUsage(account.id, month)));
      const tables = JSON.stringify(db.t, (key, value) => (value instanceof Map ? [...value.entries()] : value));
      return json(200, { seen: lab.seen, used, month, accounts: db.t.accounts.map((a) => ({ plan: a.plan, consent: Boolean(a.brain_consent_at), words: a.brain_consent_words || null })), tables });
    }
    if (url.pathname === "/api/luma/brain/v1/messages") req.query = { route: "brain" };
    else if (url.pathname.startsWith("/api/luma/")) req.query = { ...Object.fromEntries(url.searchParams), route: url.pathname.slice("/api/luma/".length) };
    else return json(404, { error: "not_found" });
    // Every test signs up from this one computer; the relay's limit on new accounts from one address is tested elsewhere.
    if (req.query.route === "account-create") req.headers["x-forwarded-for"] = `10.9.${(signups >> 8) & 255}.${signups++ & 255}`;
    await handler(req, res);
  } catch (error) {
    if (!res.headersSent) json(500, { error: "lab", message: String(error?.message || error) });
    else res.end();
  }
});
server.listen(Number(process.env.LUMA_LAB_RELAY_PORT || 0), "127.0.0.1", () => console.log(JSON.stringify({ port: server.address().port })));
