// The Super Intelligence's relay (Luma Plus): run with `node --test tests/`.
// Anthropic and Supabase are replaced by in-memory fakes; nothing leaves the machine and no key here is real.
import test from "node:test";
import assert from "node:assert/strict";
import { createService, createHandler, brainCost, usageCounter, settings } from "../api/_lib/luma-cloud.js";
import { memoryDb } from "../api/_lib/luma-memory-db.js";
import brainFunction from "../api/luma/brain/v1/messages.js";

const LUMAS_KEY = "lumas-own-key-for-claude";
const ENV = { LUMA_CLOUD_PUBLIC_URL: "https://luma.example.com", ANTHROPIC_API_KEY: LUMAS_KEY, LUMA_BRAIN_ZERO_RETENTION: "1" };
const SAID = "my sister Dana hasn't called since the funeral";
const ANSWER = "That silence must sting, Marvin. Do you want to talk about her?";
const ASK = {
  model: "claude-sonnet-5-5", max_tokens: 16000, stream: true, output_config: { effort: "medium" },
  system: [{ type: "text", text: "You are Luma.", cache_control: { type: "ephemeral" } }],
  messages: [{ role: "user", content: SAID }],
};
const USED = { input_tokens: 120, cache_read_input_tokens: 3000, cache_creation_input_tokens: 400, output_tokens: 1 };

const event = (name, data) => `event: ${name}\ndata: ${JSON.stringify({ type: name, ...data })}\n\n`;

// What Claude sends back for one streamed turn, event by event.
function answer({ model = "claude-sonnet-5-5", usage = USED, text = ANSWER, out = 14, iterations = null } = {}) {
  const words = text.split(" ");
  return [
    event("message_start", { message: { id: "msg_1", type: "message", role: "assistant", model, content: [], usage } }),
    event("content_block_start", { index: 0, content_block: { type: "text", text: "" } }),
    ...words.map((word, i) => event("content_block_delta", { index: 0, delta: { type: "text_delta", text: (i ? " " : "") + word } })),
    event("content_block_stop", { index: 0 }),
    event("message_delta", { delta: { stop_reason: "end_turn" }, usage: { output_tokens: out, ...(iterations ? { iterations } : {}) } }),
    event("message_stop", {}),
  ];
}

function fakeAnthropic() {
  const calls = [];
  const behavior = { status: 200, events: answer(), json: null, bytes: 0, throws: false };
  const fetch = async (url, init = {}) => {
    const body = JSON.parse(init.body);
    const call = { url, headers: init.headers, body, read: 0, stopped: false };
    calls.push(call);
    if (behavior.throws) throw new Error("connect ECONNREFUSED while sending " + init.body);
    if (behavior.status >= 400) {
      const text = JSON.stringify({ type: "error", error: { type: "overloaded_error", message: "Overloaded" } });
      return { ok: false, status: behavior.status, text: async () => text };
    }
    if (!body.stream) {
      const whole = behavior.json || { id: "msg_1", type: "message", role: "assistant", model: body.model, content: [], stop_reason: "end_turn", usage: USED };
      return { ok: true, status: 200, text: async () => JSON.stringify(whole) };
    }
    const all = behavior.events.join("");
    const pieces = behavior.bytes ? all.match(new RegExp(`[\\s\\S]{1,${behavior.bytes}}`, "g")) : behavior.events;
    async function* stream() {
      for (const piece of pieces) {
        if (init.signal?.aborted) {
          call.stopped = true;
          throw Object.assign(new Error("This operation was aborted"), { name: "AbortError" });
        }
        call.read += 1;
        yield new TextEncoder().encode(piece);
      }
    }
    return { ok: true, status: 200, body: stream() };
  };
  return { fetch, calls, behavior };
}

function setup(env = {}) {
  const db = memoryDb();
  const net = fakeAnthropic();
  let clock = Date.UTC(2026, 10, 10, 12, 0, 0);
  const deps = { env: { ...ENV, ...env }, db, fetch: net.fetch, now: () => clock };
  const service = createService(deps);
  const call = (route, args = {}) => service.routes[route]({ headers: {}, body: {}, form: {}, raw: "", query: {}, ip: "10.1.1.1", ...args });
  return { db, net, call, deps, tick: (ms) => (clock += ms), now: () => clock };
}

let people = 0;
async function member(ctx, { plus = true, yes = true } = {}) {
  people += 1;
  const made = await ctx.call("account-create", { body: { email: `member${people}@example.com`, key: "ab".repeat(32), name: "Marvin", device_name: "Kitchen Luma" }, ip: "10.0.0." + people });
  const token = made.json.device_token;
  const headers = { authorization: "Bearer " + token };
  const account = ctx.db.t.accounts.at(-1);
  if (plus) await ctx.db.updateAccount(account.id, { plan: "plus", subscription_status: "active" });
  if (yes) await ctx.call("brain-consent", { headers, body: { yes: true, words: 1 } });
  return { headers, account, token };
}

async function heard(result) {
  let text = "";
  for await (const chunk of result.stream) text += Buffer.from(chunk).toString("utf8");
  return text;
}

const rejects = (promise, status, code) => assert.rejects(promise, (e) => e.status === status && (!code || e.code === code));
const brainOf = async (ctx, who) => (await ctx.call("account", { headers: who.headers })).json.brain;
const kept = (ctx, who, month = "2026-11") => ctx.db.brainUsage(who.account.id, month);
const everything = (tables) => JSON.stringify(tables, (key, value) => (value instanceof Map ? [...value.entries()] : value));

function fakeRes({ hangUpAfter = 0 } = {}) {
  const listeners = {};
  return {
    headers: {}, statusCode: 0, body: "", writes: 0, writableEnded: false,
    setHeader(k, v) { this.headers[k.toLowerCase()] = v; },
    on(name, fn) { (listeners[name] = listeners[name] || []).push(fn); },
    write(chunk) {
      this.body += Buffer.from(chunk).toString("utf8");
      this.writes += 1;
      if (hangUpAfter && this.writes === hangUpAfter) for (const fn of listeners.close || []) fn();
    },
    end(chunk) { if (chunk) this.body += chunk; this.writableEnded = true; },
  };
}

const post = (who, body, extra = {}) => ({ method: "POST", query: { route: "brain" }, headers: { ...who.headers, "content-type": "application/json", ...extra }, rawBody: JSON.stringify(body) });

test("off until they say yes: a sign-in, Plus and the owner's yes are all needed, and paying isn't the yes", async () => {
  const ctx = setup();
  await rejects(ctx.call("brain", { body: ASK }), 401);
  const free = await member(ctx, { plus: false, yes: false });
  await rejects(ctx.call("brain", { headers: free.headers, body: ASK }), 402, "plus");
  await rejects(ctx.call("brain-consent", { headers: free.headers, body: { yes: true, words: 1 } }), 402, "plus");

  const paid = await member(ctx, { yes: false });
  let view = await brainOf(ctx, paid);
  assert.equal(view.available, true);
  assert.equal(view.consent, false, "paying isn't the yes");
  await rejects(ctx.call("brain", { headers: paid.headers, body: ASK }), 403, "consent");
  await rejects(ctx.call("brain-consent", { headers: paid.headers, body: { yes: true } }), 400, "words");
  assert.equal(ctx.net.calls.length, 0, "nothing left the relay before the yes");

  view = (await ctx.call("brain-consent", { headers: paid.headers, body: { yes: true, words: 1 } })).json.brain;
  assert.equal(view.consent, true);
  assert.equal((await ctx.call("brain", { headers: paid.headers, body: ASK })).status, 200);

  view = (await ctx.call("brain-consent", { headers: paid.headers, body: { yes: false } })).json.brain;
  assert.equal(view.consent, false, "the yes can be taken back");
  await rejects(ctx.call("brain", { headers: paid.headers, body: ASK }), 403, "consent");

  await ctx.call("brain-consent", { headers: paid.headers, body: { yes: true, words: 1 } });
  await ctx.db.updateAccount(paid.account.id, { subscription_status: "canceled" });
  await rejects(ctx.call("brain", { headers: paid.headers, body: ASK }), 402, "plus");
});

test("a yes is to the words that were shown: when what leaves the home changes, Luma asks again", async () => {
  const ctx = setup({ LUMA_BRAIN_WORDS: "2" });
  const who = await member(ctx, { yes: false });
  await ctx.call("brain-consent", { headers: who.headers, body: { yes: true, words: 1 } });
  assert.equal((await brainOf(ctx, who)).consent, false);
  assert.equal((await brainOf(ctx, who)).words, 2);
  await rejects(ctx.call("brain", { headers: who.headers, body: ASK }), 403, "consent");
  await ctx.call("brain-consent", { headers: who.headers, body: { yes: true, words: 2 } });
  assert.equal((await ctx.call("brain", { headers: who.headers, body: ASK })).status, 200);
});

test("it stays off until Luma's own key is set and zero data retention is confirmed for it", async () => {
  for (const missing of [{ ANTHROPIC_API_KEY: "" }, { LUMA_BRAIN_ZERO_RETENTION: "" }]) {
    const ctx = setup(missing);
    const who = await member(ctx);
    assert.equal((await brainOf(ctx, who)).available, false);
    await rejects(ctx.call("brain", { headers: who.headers, body: ASK }), 503, "not_configured");
    assert.equal(ctx.net.calls.length, 0);
  }
});

test("the request goes on with Luma's key, never the device's, and carries only what the brain needs", async () => {
  const ctx = setup();
  const who = await member(ctx);
  const extras = {
    max_tokens: 64000, fallbacks: "default", tools: [{ type: "web_search_20250305", name: "web_search" }], mcp_servers: [{ url: "https://elsewhere.example" }],
    metadata: { user_id: "marvin" }, container: "c1", service_tier: "priority",
  };
  const out = await ctx.call("brain", {
    headers: { ...who.headers, "anthropic-version": "2023-06-01", "anthropic-beta": "server-side-fallback-2026-07-01,files-api-2025-04-14" },
    body: { ...ASK, ...extras },
  });
  await heard(out);
  const sent = ctx.net.calls[0];
  assert.equal(sent.url, "https://api.anthropic.com/v1/messages?beta=true");
  assert.equal(sent.headers["x-api-key"], LUMAS_KEY);
  assert.equal(sent.headers["anthropic-version"], "2023-06-01");
  assert.ok(!JSON.stringify(sent.headers).includes(who.token.split(".")[1]), "the device's sign-in isn't passed on");
  assert.deepEqual(Object.keys(sent.body).sort(), ["max_tokens", "messages", "model", "output_config", "stream", "system"]);
  assert.equal(sent.body.max_tokens, 16000);
  assert.equal(sent.headers["anthropic-beta"], undefined, "nothing is switched on that could keep what was said");
  assert.deepEqual(sent.body.messages, ASK.messages);

  await rejects(ctx.call("brain", { headers: who.headers, body: { ...ASK, model: "claude-fable-5-1" } }), 400, "model");
  await rejects(ctx.call("brain", { headers: who.headers, body: { ...ASK, messages: [] } }), 400, "messages");
  assert.equal(ctx.net.calls.length, 1);

  const byKey = await ctx.call("brain", { headers: { "x-api-key": who.token }, body: ASK }); // how older versions of the library sign in
  assert.equal(byKey.status, 200);
});

test("retrying on another model after a decline is passed on only once the operator has confirmed it keeps nothing", async () => {
  const ctx = setup({ LUMA_BRAIN_FALLBACKS: "1" });
  const who = await member(ctx);
  await heard(await ctx.call("brain", { headers: { ...who.headers, "anthropic-beta": "server-side-fallback-2026-07-01,files-api-2025-04-14" }, body: { ...ASK, fallbacks: "default" } }));
  assert.equal(ctx.net.calls[0].body.fallbacks, "default");
  assert.equal(ctx.net.calls[0].headers["anthropic-beta"], "server-side-fallback-2026-07-01");
  await rejects(ctx.call("brain", { headers: who.headers, body: { ...ASK, fallbacks: [{ model: "claude-fable-5-1" }] } }), 400, "fallbacks");
});

test("the answer streams through exactly as it came, and only the counts are kept", async () => {
  const ctx = setup();
  const who = await member(ctx);
  const out = await ctx.call("brain", { headers: who.headers, body: ASK });
  assert.equal(out.contentType, "text/event-stream");
  assert.equal(await heard(out), answer().join(""));
  // 120 fresh at $2 a million, 400 written at 1.25 times that, 3,000 read from the cache at $0.20, 14 out at $10.
  assert.deepEqual(await kept(ctx, who), { micros: 240 + 1000 + 600 + 140, calls: 1, tokens_in: 3520, tokens_out: 14, cache_read: 3000, ms: 0 });
  const view = await brainOf(ctx, who);
  assert.equal(view.calls, 1);
  assert.equal(view.budget_cents, 400);
  assert.equal(view.used_cents, 0.2);
  assert.equal(view.left_share, 0.9995);
});

test("the price is the price of the brain that answered", async () => {
  const ctx = setup();
  const who = await member(ctx);
  ctx.net.behavior.events = answer({ model: "claude-opus-5-5" });
  await heard(await ctx.call("brain", { headers: who.headers, body: ASK }));
  assert.equal((await kept(ctx, who)).micros, 480 + 2000 + 600 + 280);
  ctx.net.behavior.events = answer({ model: "a-brain-with-no-price-yet" });
  await heard(await ctx.call("brain", { headers: who.headers, body: ASK }));
  assert.equal((await kept(ctx, who)).micros, 2 * (480 + 2000 + 600 + 280), "a brain with no price is charged as the dearest");
});

test("when a decline was retried, every attempt is counted, each at its own brain's price", async () => {
  const ctx = setup({ LUMA_BRAIN_FALLBACKS: "1" });
  const who = await member(ctx);
  ctx.net.behavior.events = answer({
    model: "claude-opus-5-5",
    iterations: [
      { type: "message", input_tokens: 120, cache_read_input_tokens: 3000, cache_creation_input_tokens: 400, output_tokens: 2 },
      { type: "fallback_message", input_tokens: 3520, cache_read_input_tokens: 0, cache_creation_input_tokens: 0, output_tokens: 14 },
    ],
  });
  await heard(await ctx.call("brain", { headers: who.headers, body: { ...ASK, fallbacks: "default" } }));
  const used = await kept(ctx, who);
  assert.equal(used.micros, (240 + 1000 + 600 + 20) + (3520 * 4 + 14 * 20));
  assert.equal(used.tokens_in, 3520 + 3520);
  assert.equal(used.tokens_out, 16);
});

test("when the month's budget is used up it says so plainly, sends nothing, and comes back next month", async () => {
  const ctx = setup({ LUMA_PLUS_BRAIN_BUDGET_CENTS: "1" });
  const who = await member(ctx);
  ctx.net.behavior.events = answer({ usage: { input_tokens: 4000, output_tokens: 1 }, out: 500 }); // 1.3 cents
  await heard(await ctx.call("brain", { headers: who.headers, body: ASK }));
  const error = await ctx.call("brain", { headers: who.headers, body: ASK }).catch((e) => e);
  assert.equal(error.status, 402);
  assert.equal(error.code, "budget");
  assert.match(error.message, /used up/);
  assert.equal(error.extra.resets, "2026-12-01T00:00:00.000Z");
  assert.equal(ctx.net.calls.length, 1, "nothing was sent once the budget was gone");
  const view = await brainOf(ctx, who);
  assert.equal(view.left_share, 0);
  assert.equal(view.resets, "2026-12-01T00:00:00.000Z");
  ctx.tick(21 * 24 * 3600_000);
  assert.equal((await ctx.call("brain", { headers: who.headers, body: ASK })).status, 200);
});

test("nothing anyone said is stored or written to a log", async () => {
  const ctx = setup();
  const who = await member(ctx);
  const handler = createHandler(() => ctx.deps);
  const logged = [];
  const real = { error: console.error, log: console.log, warn: console.warn, info: console.info };
  for (const name of Object.keys(real)) console[name] = (...args) => logged.push(args.map(String).join(" "));
  try {
    let res = fakeRes();
    await handler(post(who, ASK), res);
    assert.equal(res.statusCode, 200);
    assert.ok(res.body.includes("sting"), "the answer did reach the device");
    ctx.net.behavior.status = 400;
    res = fakeRes();
    await handler(post(who, ASK), res);
    assert.equal(res.statusCode, 400);
    ctx.net.behavior.status = 200;
    ctx.net.behavior.throws = true; // an error whose own message carries the conversation
    res = fakeRes();
    await handler(post(who, ASK), res);
    assert.equal(res.statusCode, 500);
  } finally {
    Object.assign(console, real);
  }
  assert.equal(logged.length, 1, "the failure was noted");
  for (const word of ["Dana", "funeral", "sting", who.token.split(".")[1], LUMAS_KEY]) {
    assert.ok(!logged.join("\n").includes(word), `a log holds "${word}"`);
    assert.ok(!everything(ctx.db.t).includes(word), `the database holds "${word}"`);
  }
  assert.deepEqual(Object.keys(await kept(ctx, who)).sort(), ["cache_read", "calls", "micros", "ms", "tokens_in", "tokens_out"]);
});

test("when the device hangs up the brain is stopped, and what was heard is still counted", async () => {
  const ctx = setup();
  const who = await member(ctx);
  const handler = createHandler(() => ctx.deps);
  const res = fakeRes({ hangUpAfter: 6 }); // the start, the block, then "That", " silence", " must", " sting,"
  await handler(post(who, ASK), res);
  const call = ctx.net.calls[0];
  assert.equal(call.stopped, true, "the brain wasn't left talking to nobody");
  assert.ok(call.read < answer().length);
  assert.equal(res.writableEnded, true);
  const used = await kept(ctx, who);
  assert.equal(used.calls, 1);
  assert.equal(used.tokens_in, 3520);
  assert.equal(used.tokens_out, Math.ceil("That silence must sting,".length / 4), "with no final count, the words that passed are counted at four letters a token");
});

test("a brain that's busy comes back as it is, and nothing is charged", async () => {
  const ctx = setup();
  const who = await member(ctx);
  ctx.net.behavior.status = 529;
  const out = await ctx.call("brain", { headers: who.headers, body: ASK });
  assert.equal(out.status, 529);
  assert.match(out.text, /overloaded_error/);
  assert.deepEqual(await kept(ctx, who), { micros: 0, calls: 0, tokens_in: 0, tokens_out: 0, cache_read: 0, ms: 0 });
});

test("a warm-up that isn't streamed is passed through and counted too", async () => {
  const ctx = setup();
  const who = await member(ctx);
  ctx.net.behavior.json = { id: "msg_w", type: "message", role: "assistant", model: "claude-sonnet-5-5", content: [], stop_reason: "max_tokens",
    usage: { input_tokens: 5, cache_creation_input_tokens: 3400, cache_read_input_tokens: 0, output_tokens: 0 } };
  const { stream: _, ...warm } = ASK;
  const out = await ctx.call("brain", { headers: who.headers, body: { ...warm, max_tokens: 0 } });
  assert.equal(out.status, 200);
  assert.equal(JSON.parse(out.text).id, "msg_w");
  assert.equal(ctx.net.calls[0].body.max_tokens, 0);
  assert.equal((await kept(ctx, who)).micros, 10 + 8500);
});

test("a Luma that asks far too fast is told to slow down", async () => {
  const ctx = setup({ LUMA_BRAIN_CALLS_PER_MINUTE: "3" });
  const who = await member(ctx);
  for (let i = 0; i < 3; i += 1) await heard(await ctx.call("brain", { headers: who.headers, body: ASK }));
  await rejects(ctx.call("brain", { headers: who.headers, body: ASK }), 429, "slow_down");
  assert.equal(ctx.net.calls.length, 3);
  ctx.tick(61_000);
  assert.equal((await ctx.call("brain", { headers: who.headers, body: ASK })).status, 200);
});

test("a conversation bigger than a text is taken, and a flood isn't", async () => {
  const ctx = setup();
  const who = await member(ctx);
  const handler = createHandler(() => ctx.deps);
  const sized = (bytes) => {
    const raw = Buffer.from(JSON.stringify({ ...ASK, messages: [{ role: "user", content: "a".repeat(bytes) }] }));
    return { method: "POST", query: { route: "brain" }, headers: { ...who.headers, "content-type": "application/json" }, readable: true,
      async *[Symbol.asyncIterator]() { for (let at = 0; at < raw.length; at += 65536) yield raw.subarray(at, at + 65536); } };
  };
  let res = fakeRes();
  await handler(sized(300_000), res);
  assert.equal(res.statusCode, 200);
  res = fakeRes();
  await handler(sized(2_100_000), res);
  assert.equal(res.statusCode, 413);
  assert.equal(ctx.net.calls.length, 1);
});

test("Anthropic's own library finds the brain at /api/luma/brain/v1/messages", async () => {
  let res = fakeRes();
  await brainFunction({ method: "GET", query: {}, headers: {} }, res);
  assert.equal(res.statusCode, 405);
  res = fakeRes();
  const token = "00000000-0000-0000-0000-000000000000." + "a".repeat(32);
  await brainFunction({ method: "POST", query: {}, headers: { authorization: "Bearer " + token, "content-type": "application/json" }, rawBody: JSON.stringify(ASK) }, res);
  assert.equal(res.statusCode, 503, "the route is there; this machine just has no database set up");
});

test("the counts are read from the stream however it's cut up, and nothing else is", () => {
  const whole = answer().join("") + "data: not json\n\n";
  for (const size of [1, 7, 64, 5000]) {
    const counter = usageCounter();
    for (const piece of whole.match(new RegExp(`[\\s\\S]{1,${size}}`, "g"))) counter.feed(piece);
    assert.deepEqual(counter.total(), { fresh: 120, read: 3000, written: 400, out: 14 });
    assert.equal(counter.model(), "claude-sonnet-5-5");
    assert.deepEqual(Object.keys(counter).sort(), ["attempts", "feed", "model", "total", "whole"]);
  }
});

test("what a call costs", () => {
  const prices = settings({}).brainPrices;
  const used = { fresh: 1000, written: 2000, read: 10000, out: 500 };
  assert.equal(brainCost(prices, "claude-sonnet-5-5", used), 2000 + 5000 + 2000 + 5000);
  assert.equal(brainCost(prices, "claude-opus-5-5", used), 4000 + 10000 + 2000 + 10000);
  assert.equal(brainCost(prices, "claude-haiku-5-5", used), 100 + 250 + 100 + 250);
  assert.equal(brainCost(prices, "something-new", used), brainCost(prices, "claude-opus-5-5", used));
  assert.equal(brainCost(settings({ LUMA_BRAIN_PRICES: '{"claude-sonnet-5-5":[3,15,0.3]}' }).brainPrices, "claude-sonnet-5-5", used), 3000 + 7500 + 3000 + 7500);
  assert.equal(settings({ LUMA_BRAIN_PRICES: "{not json" }).brainPrices["claude-sonnet-5-5"][0], 2);
});
