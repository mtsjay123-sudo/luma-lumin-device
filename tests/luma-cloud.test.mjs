// Luma Cloud texting relay: run with `node --test tests/`.
// Twilio, Stripe and Supabase are replaced by in-memory fakes; nothing leaves the machine.
import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { createService, createHandler, twilioSignature, period } from "../api/_lib/luma-cloud.js";
import { makeSupabaseDb } from "../api/_lib/luma-db.js";
import { memoryDb } from "../api/_lib/luma-memory-db.js";

const PUBLIC = "https://luma.example.com";
const ENV = {
  LUMA_CLOUD_PUBLIC_URL: PUBLIC, LUMA_FREE_TEXTS_PER_MONTH: "3", LUMA_PLUS_TEXTS_PER_MONTH: "300",
  LUMA_SHARED_NUMBER: "+19195550000", TWILIO_ACCOUNT_SID: "AC" + "1".repeat(32), TWILIO_AUTH_TOKEN: "twilio-token",
  TWILIO_VERIFY_SERVICE_SID: "VA123", STRIPE_SECRET_KEY: "sk_test_x", LUMA_PLUS_PRICE_ID: "price_plus",
  STRIPE_WEBHOOK_SECRET: "whsec_test", LUMA_PROVISION_NUMBERS: "1",
};

function fakeNetwork() {
  const calls = [];
  const behavior = { sendStatus: 201, sendBody: null, throwOnSend: false, verifyStatus: "approved" };
  let sid = 0;
  const fetch = async (url, init = {}) => {
    const params = Object.fromEntries(new URLSearchParams(init.body || ""));
    calls.push({ url, method: init.method || "GET", params });
    const json = (status, data) => ({ ok: status < 400, status, json: async () => data, text: async () => JSON.stringify(data) });
    if (url.endsWith("/Messages.json")) {
      if (behavior.throwOnSend) throw new Error("network down");
      if (behavior.sendStatus >= 400) return json(behavior.sendStatus, behavior.sendBody || { code: 30007 });
      return json(201, { sid: "SM" + String(++sid).padStart(32, "0"), status: "queued" });
    }
    if (url.includes("/Verifications")) return json(201, { status: "pending" });
    if (url.includes("/VerificationCheck")) return json(200, { status: params.Code === "123456" ? behavior.verifyStatus : "pending" });
    if (url.includes("checkout/sessions")) return json(200, { url: "https://checkout.stripe.com/c/pay/test" });
    if (url.includes("billing_portal")) return json(200, { url: "https://billing.stripe.com/p/test" });
    if (url.includes("AvailablePhoneNumbers")) return json(200, { available_phone_numbers: [{ phone_number: "+19195551234" }] });
    if (url.includes("IncomingPhoneNumbers.json")) return json(201, { sid: "PN1", phone_number: params.PhoneNumber });
    return json(404, {});
  };
  return { fetch, calls, behavior };
}

function setup(envOverrides = {}) {
  const db = memoryDb();
  const net = fakeNetwork();
  let clock = Date.UTC(2026, 9, 3, 12, 0, 0);
  const service = createService({ env: { ...ENV, ...envOverrides }, db, fetch: net.fetch, now: () => clock });
  const call = (route, args = {}) => service.routes[route]({ headers: {}, body: {}, form: {}, raw: "", query: {}, ...args });
  return { db, net, call, service, tick: (ms) => (clock += ms), now: () => clock };
}

async function signUp(ctx, phone = "+19195550123", name = "Marvin") {
  await ctx.call("verify-start", { body: { phone, name } });
  const out = await ctx.call("verify-check", { body: { phone, code: "123456", name, device_name: "Kitchen Luma" } });
  return { authorization: "Bearer " + out.json.device_token };
}

const sends = (net) => net.calls.filter((c) => c.url.endsWith("/Messages.json"));
const rejects = (promise, status, code) => assert.rejects(promise, (e) => e.status === status && (!code || e.code === code));

test("sign-up only works for verified US/Canada phones and issues a device token", async () => {
  const ctx = setup();
  await rejects(ctx.call("verify-start", { body: { phone: "+447700900123", name: "M" } }), 403, "destination");
  await rejects(ctx.call("verify-start", { body: { phone: "9195550123", name: "M" } }), 400, "bad_number");
  await rejects(ctx.call("verify-check", { body: { phone: "+19195550123", code: "000000" } }), 403, "code");
  const headers = await signUp(ctx);
  const account = await ctx.call("account", { headers });
  assert.equal(account.json.plan, "free");
  assert.equal(account.json.texts_limit, 3);
  assert.equal(account.json.number, "+19195550000");
  assert.equal(ctx.db.t.devices[0].secret_hash.length, 64, "only a hash of the device secret is stored");
  await rejects(ctx.call("account", { headers: { authorization: headers.authorization.slice(0, -2) + "xx" } }), 401);
});

test("free texts go out from Luma's number with the owner's name and opt-out on first contact", async () => {
  const ctx = setup();
  const headers = await signUp(ctx);
  const first = await ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "running 10 late, save me a seat", client_ref: "action1" } });
  assert.equal(first.status, 200);
  assert.equal(first.json.texts_used, 1);
  assert.equal(first.json.texts_left, 2);
  const [sent] = sends(ctx.net);
  assert.equal(sent.params.From, "+19195550000");
  assert.match(sent.params.Body, /^Marvin: running 10 late, save me a seat\n\n\(Sent via Luma for Marvin\. Reply STOP to opt out\.\)$/);
  await ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "here now", client_ref: "action2" } });
  assert.equal(sends(ctx.net)[1].params.Body, "Marvin: here now", "no footer after the first text to someone");
});

test("a retried send with the same reference never texts twice", async () => {
  const ctx = setup();
  const headers = await signUp(ctx);
  const body = { to: "+19195550199", body: "hey", client_ref: "action-retry" };
  await ctx.call("sms-send", { headers, body });
  const again = await ctx.call("sms-send", { headers, body });
  assert.equal(again.json.duplicate, true);
  assert.equal(sends(ctx.net).length, 1);
  assert.equal(again.json.texts_used, 1);
});

test("running out of free texts returns 402 with a Luma Plus checkout link and sends nothing", async () => {
  const ctx = setup();
  const headers = await signUp(ctx);
  for (let i = 0; i < 3; i++) await ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "msg " + i, client_ref: "ref-" + i + "-abc" } });
  await assert.rejects(ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "one more", client_ref: "ref-4-abcd" } }), (e) => {
    assert.equal(e.status, 402);
    assert.equal(e.extra.upgrade_url, "https://checkout.stripe.com/c/pay/test");
    assert.equal(e.extra.plus.texts_limit, 300);
    assert.match(e.message, /3 free texts/);
    return true;
  });
  assert.equal(sends(ctx.net).length, 3);
  const checkout = ctx.net.calls.find((c) => c.url.includes("checkout/sessions"));
  assert.equal(checkout.params["line_items[0][price]"], "price_plus");
  assert.equal(checkout.params["metadata[app]"], "luma");
});

test("the allowance resets next month", async () => {
  const ctx = setup({ LUMA_FREE_TEXTS_PER_MONTH: "1" });
  const headers = await signUp(ctx);
  await ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "a", client_ref: "month-one-1" } });
  await rejects(ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "b", client_ref: "month-one-2" } }), 402);
  ctx.tick(31 * 86400_000);
  const next = await ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "c", client_ref: "month-two-1" } });
  assert.equal(next.json.texts_used, 1);
});

test("carrier rejection gives the text back; an unknown outcome keeps it and says so", async () => {
  const ctx = setup();
  const headers = await signUp(ctx);
  ctx.net.behavior.sendStatus = 400;
  ctx.net.behavior.sendBody = { code: 21211 };
  await rejects(ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "x", client_ref: "reject-1" } }), 422, "rejected");
  assert.equal(await ctx.db.usage(ctx.db.t.accounts[0].id, period(ctx.now())), 0);
  ctx.net.behavior.sendStatus = 201;
  ctx.net.behavior.throwOnSend = true;
  const unknown = await ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "y", client_ref: "unknown-1" } });
  assert.equal(unknown.status, 202);
  assert.equal(unknown.json.status, "unknown");
  assert.equal(unknown.json.texts_used, 1);
});

test("STOP from a recipient blocks future texts; bad Twilio signatures are refused", async () => {
  const ctx = setup();
  const headers = await signUp(ctx);
  await ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "hi", client_ref: "stop-flow-1" } });
  const form = { From: "+19195550199", To: "+19195550000", Body: "Stop", MessageSid: "SMin1" };
  await rejects(ctx.call("twilio-inbound", { form, headers: { "x-twilio-signature": "forged" } }), 403);
  const signature = twilioSignature("twilio-token", PUBLIC + "/api/luma/twilio-inbound", form);
  await ctx.call("twilio-inbound", { form, headers: { "x-twilio-signature": signature } });
  await rejects(ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "again", client_ref: "stop-flow-2" } }), 403, "opted_out");
  assert.equal(sends(ctx.net).length, 1);
});

test("replies to Luma's number come back to the right owner's inbox", async () => {
  const ctx = setup();
  const marvin = await signUp(ctx, "+19195550123", "Marvin");
  const other = await signUp(ctx, "+19195550124", "Dana");
  await ctx.call("sms-send", { headers: marvin, body: { to: "+19195550199", body: "dinner?", client_ref: "reply-flow-1" } });
  const form = { From: "+19195550199", To: "+19195550000", Body: "yes! 7?", MessageSid: "SMin2" };
  await ctx.call("twilio-inbound", { form, headers: { "x-twilio-signature": twilioSignature("twilio-token", PUBLIC + "/api/luma/twilio-inbound", form) } });
  const inbox = await ctx.call("sms-inbox", { headers: marvin, query: {} });
  assert.deepEqual(inbox.json.replies.map((r) => [r.from, r.body]), [["+19195550199", "yes! 7?"]]);
  assert.equal((await ctx.call("sms-inbox", { headers: other, query: {} })).json.replies.length, 0);
  assert.equal((await ctx.call("sms-inbox", { headers: marvin, query: { after: inbox.json.cursor } })).json.replies.length, 0);
});

function stripeEvent(ctx, event) {
  const raw = JSON.stringify(event);
  const t = Math.floor(ctx.now() / 1000);
  const v1 = crypto.createHmac("sha256", "whsec_test").update(`${t}.${raw}`).digest("hex");
  return ctx.call("stripe-webhook", { raw, headers: { "stripe-signature": `t=${t},v1=${v1}` } });
}

test("paying for Luma Plus raises the limit, assigns a dedicated number and routes its replies", async () => {
  const ctx = setup();
  const headers = await signUp(ctx);
  const accountId = ctx.db.t.accounts[0].id;
  await rejects(ctx.call("stripe-webhook", { raw: "{}", headers: { "stripe-signature": "t=1,v1=bad" } }), 400, "signature");
  await stripeEvent(ctx, { id: "evt_1", type: "checkout.session.completed", data: { object: { mode: "subscription", customer: "cus_1", subscription: "sub_1", client_reference_id: accountId, metadata: { app: "luma", account_id: accountId } } } });
  const view = (await ctx.call("account", { headers })).json;
  assert.equal(view.plan, "plus");
  assert.equal(view.texts_limit, 300);
  assert.equal(view.number, "+19195551234");
  assert.equal(view.dedicated_number, true);
  const bought = ctx.net.calls.find((c) => c.url.includes("IncomingPhoneNumbers.json"));
  assert.equal(bought.params.SmsUrl, PUBLIC + "/api/luma/twilio-inbound");
  assert.ok(ctx.net.calls.some((c) => c.url.includes("AreaCode=919")), "number is local to the owner");

  await ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "it's me on my new number", client_ref: "plus-send-1" } });
  const sent = sends(ctx.net).at(-1);
  assert.equal(sent.params.From, "+19195551234");
  assert.ok(sent.params.Body.startsWith("it's me on my new number"), "no name prefix on a dedicated number");

  const form = { From: "+19195550199", To: "+19195551234", Body: "nice", MessageSid: "SMin3" };
  await ctx.call("twilio-inbound", { form, headers: { "x-twilio-signature": twilioSignature("twilio-token", PUBLIC + "/api/luma/twilio-inbound", form) } });
  assert.equal((await ctx.call("sms-inbox", { headers, query: {} })).json.replies[0].body, "nice");

  const dup = await stripeEvent(ctx, { id: "evt_1", type: "checkout.session.completed", data: { object: {} } });
  assert.equal(dup.json.duplicate, true);
  await stripeEvent(ctx, { id: "evt_2", type: "customer.subscription.deleted", data: { object: { id: "sub_1", customer: "cus_1", status: "canceled", metadata: { app: "luma", account_id: accountId } } } });
  assert.equal((await ctx.call("account", { headers })).json.plan, "free");
});

test("events from other Lumin apps on the same Stripe account are ignored", async () => {
  const ctx = setup();
  await signUp(ctx);
  const out = await stripeEvent(ctx, { id: "evt_x", type: "checkout.session.completed", data: { object: { mode: "subscription", customer: "cus_9", metadata: { app: "omnishort" } } } });
  assert.equal(out.json.ignored, true);
  assert.equal(ctx.db.t.accounts[0].plan, "free");
});

test("bursts are rate limited", async () => {
  const ctx = setup({ LUMA_TEXTS_PER_MINUTE: "2", LUMA_FREE_TEXTS_PER_MONTH: "50" });
  const headers = await signUp(ctx);
  await ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "1", client_ref: "burst-1" } });
  await ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "2", client_ref: "burst-2" } });
  await rejects(ctx.call("sms-send", { headers, body: { to: "+19195550199", body: "3", client_ref: "burst-3" } }), 429);
});

function fakeRes() {
  const res = { headers: {}, statusCode: 0, body: "", setHeader(k, v) { this.headers[k.toLowerCase()] = v; }, end(b) { this.body = b; } };
  return res;
}

test("HTTP wrapper enforces methods, parses bodies and answers Twilio with TwiML", async () => {
  const db = memoryDb();
  const net = fakeNetwork();
  const handler = createHandler(() => ({ env: ENV, db, fetch: net.fetch }));
  let res = fakeRes();
  await handler({ method: "GET", query: { route: "sms-send" }, headers: {} }, res);
  assert.equal(res.statusCode, 405);
  res = fakeRes();
  await handler({ method: "GET", query: { route: "nope" }, headers: {} }, res);
  assert.equal(res.statusCode, 404);
  res = fakeRes();
  await handler({ method: "POST", query: { route: "verify-start" }, headers: { "content-type": "application/json" }, rawBody: "{bad" }, res);
  assert.equal(res.statusCode, 400);
  const form = { From: "+19195550199", To: "+19195550000", Body: "HELP" };
  res = fakeRes();
  await handler({ method: "POST", query: { route: "twilio-inbound" }, headers: { "content-type": "application/x-www-form-urlencoded", "x-twilio-signature": twilioSignature("twilio-token", PUBLIC + "/api/luma/twilio-inbound", form) }, rawBody: new URLSearchParams(form).toString() }, res);
  assert.equal(res.statusCode, 200);
  assert.match(res.body, /<Response><Message>Luma sends texts/);
});

test("without Supabase configured the API says so instead of crashing", async () => {
  const handler = createHandler(() => ({ env: ENV, db: makeSupabaseDb({}, fetch), fetch }));
  const res = fakeRes();
  await handler({ method: "GET", query: { route: "account" }, headers: { authorization: "Bearer 00000000-0000-0000-0000-000000000000.abcdefghijklmnopqrstuvwxyz" } }, res);
  assert.equal(res.statusCode, 503);
});

test("Supabase adapter talks PostgREST with the service key and maps conflicts", async () => {
  const seen = [];
  const fetchImpl = async (url, init) => {
    seen.push({ url, init });
    if (url.includes("luma_stripe_events")) return { ok: false, status: 409, text: async () => JSON.stringify({ code: "23505" }) };
    if (url.includes("rpc/luma_reserve_text")) return { ok: true, status: 200, text: async () => "null" };
    return { ok: true, status: 200, text: async () => "[]" };
  };
  const db = makeSupabaseDb({ SUPABASE_URL: "https://x.supabase.co/", SUPABASE_SERVICE_ROLE_KEY: "service" }, fetchImpl);
  assert.equal(await db.recordEvent("evt_1"), false);
  assert.equal(await db.reserveText("a", "2026-10", 3), null);
  assert.equal(await db.getAccount("a b"), null);
  assert.equal(seen[0].init.headers.Authorization, "Bearer service");
  assert.ok(seen.at(-1).url.startsWith("https://x.supabase.co/rest/v1/luma_accounts?id=eq.a%20b"));
});
