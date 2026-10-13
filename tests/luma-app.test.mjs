// The Luma app channel (phone ↔ Luma through Luma Cloud) and Web Push.
// Run with `node --test tests/luma-app.test.mjs`. Nothing leaves the machine.
import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import { createService, createHandler } from "../api/_lib/luma-cloud.js";
import { memoryDb } from "../api/_lib/luma-memory-db.js";
import { encryptPayload, generateVapidKeys, sendPush, vapidAuthorization } from "../api/_lib/web-push.js";

const VAPID = generateVapidKeys();
const ENV = {
  LUMA_CLOUD_PUBLIC_URL: "https://luma.example.com", TWILIO_ACCOUNT_SID: "AC" + "1".repeat(32), TWILIO_AUTH_TOKEN: "t",
  TWILIO_VERIFY_SERVICE_SID: "VA1", LUMA_SHARED_NUMBER: "+19195550000",
  LUMA_VAPID_PUBLIC_KEY: VAPID.publicKey, LUMA_VAPID_PRIVATE_KEY: VAPID.privateKey, LUMA_VAPID_SUBJECT: "mailto:hello@example.com",
};
const sha256 = (text) => crypto.createHash("sha256").update(text).digest("hex");
const payload = (n = 1) => Buffer.alloc(40, n).toString("base64url"); // stands in for AES-GCM ciphertext

let lastIp = 0;
function setup(env = ENV) {
  const ip = `203.0.113.${++lastIp}`; // the per-address limiter outlives a single test
  let clock = Date.UTC(2026, 9, 13, 12);
  const db = memoryDb(() => clock);
  const pushes = [];
  const net = [];
  const fetch = async (url, init = {}) => {
    net.push({ url, params: Object.fromEntries(new URLSearchParams(init.body || "")) });
    const json = (status, data) => ({ ok: status < 400, status, json: async () => data });
    if (url.includes("/VerificationCheck")) return json(200, { status: "approved" });
    if (url.includes("/Verifications")) return json(201, { status: "pending" });
    if (url.endsWith("/Messages.json")) return json(201, { sid: "SM1", status: "queued" });
    return json(404, {});
  };
  const push = async (sub, body) => { pushes.push({ sub, body }); return sub.endpoint.includes("gone") ? "gone" : "sent"; };
  const service = createService({ env, db, fetch, now: () => clock, sleep: async (ms) => { clock += ms; }, push });
  const call = (route, args = {}) => service.routes[route]({ headers: {}, body: {}, form: {}, raw: "", query: {}, ip, ...args });
  return { db, call, pushes, net, tick: (ms) => (clock += ms), now: () => clock };
}

const rejects = (promise, status, code) => assert.rejects(promise, (e) => e.status === status && (!code || e.code === code));

async function registered(ctx) {
  const out = await ctx.call("device-register", { body: { device_name: "Kitchen Luma" } });
  return { authorization: "Bearer " + out.json.device_token };
}

async function paired(ctx, device, name = "Marvin's iPhone") {
  const secret = crypto.randomBytes(32).toString("base64url");
  const start = await ctx.call("app-pair-start", { headers: device, body: { secret_hash: sha256(secret) } });
  const out = await ctx.call("app-pair", { body: { pair_id: start.json.pair_id, secret, name } });
  return { app: { authorization: "LumaApp " + out.json.app_token }, pairId: start.json.pair_id, out };
}

test("a Luma registers without a phone, a phone pairs once, and messages flow both ways", async () => {
  const ctx = setup();
  const device = await registered(ctx);
  const { app, pairId, out } = await paired(ctx, device);
  assert.equal(out.json.luma.name, "Kitchen Luma");
  assert.equal(out.json.luma.online, true);
  assert.equal(out.json.push_key, VAPID.publicKey);

  const sent = await ctx.call("app-send", { headers: app, body: { payload: payload(1), client_ref: "phone-0001" } });
  const again = await ctx.call("app-send", { headers: app, body: { payload: payload(1), client_ref: "phone-0001" } });
  assert.equal(again.json.duplicate, true);
  assert.equal(again.json.id, sent.json.id);

  const early = await ctx.call("app-inbox", { headers: device });
  assert.equal(early.json.messages.length, 0, "held back until it's safely committed");
  ctx.tick(1000);
  const inbox = await ctx.call("app-inbox", { headers: device });
  assert.equal(inbox.json.messages.length, 1);
  assert.equal(inbox.json.messages[0].payload, payload(1));
  assert.equal(inbox.json.links.length, 1);
  assert.equal(inbox.json.links[0].pairing_id, pairId);
  assert.equal(inbox.json.links[0].name, "Marvin's iPhone");
  const linkId = inbox.json.links[0].id;

  const reply = await ctx.call("app-reply", { headers: device, body: { messages: [{ link_id: linkId, payload: payload(2), client_ref: "luma-0001" }] } });
  assert.equal(reply.json.results[0].duplicate, false);
  const thread = await ctx.call("app-thread", { headers: app, query: { wait: "5" } }); // the long poll waits out the horizon
  assert.deepEqual(thread.json.messages.map((m) => m.payload), [payload(2)]);
  // The phone's own messages never come back down, and the cursor moves on.
  const later = await ctx.call("app-thread", { headers: app, query: { after: thread.json.cursor } });
  assert.equal(later.json.messages.length, 0);
});

test("pairing links are single use, expire in 10 minutes and need the exact secret", async () => {
  const ctx = setup();
  const device = await registered(ctx);
  const secret = crypto.randomBytes(32).toString("base64url");
  const start = await ctx.call("app-pair-start", { headers: device, body: { secret_hash: sha256(secret) } });
  await rejects(ctx.call("app-pair", { body: { pair_id: start.json.pair_id, secret: secret.slice(0, -2) + "xx" } }), 410, "pairing");
  await ctx.call("app-pair", { body: { pair_id: start.json.pair_id, secret } });
  await rejects(ctx.call("app-pair", { body: { pair_id: start.json.pair_id, secret } }), 410, "pairing");

  const secret2 = crypto.randomBytes(32).toString("base64url");
  const start2 = await ctx.call("app-pair-start", { headers: device, body: { secret_hash: sha256(secret2) } });
  ctx.tick(601_000);
  await rejects(ctx.call("app-pair", { body: { pair_id: start2.json.pair_id, secret: secret2 } }), 410, "pairing");
  await rejects(ctx.call("app-pair-start", { headers: device, body: { secret_hash: "short" } }), 400, "secret_hash");
  await rejects(ctx.call("app-pair-start", { body: { secret_hash: sha256("x") } }), 401, "auth");
});

test("a removed phone is locked out, from either side", async () => {
  const ctx = setup();
  const device = await registered(ctx);
  const one = await paired(ctx, device, "iPhone");
  const two = await paired(ctx, device, "iPad");
  await ctx.call("app-unpair", { headers: one.app });
  await rejects(ctx.call("app-thread", { headers: one.app }), 401, "unpaired");
  const links = (await ctx.call("app-inbox", { headers: device })).json.links;
  assert.deepEqual(links.map((l) => l.name), ["iPad"]);
  await ctx.call("app-unpair", { headers: device, body: { link_id: links[0].id } });
  await rejects(ctx.call("app-send", { headers: two.app, body: { payload: payload(), client_ref: "phone-0002" } }), 401, "unpaired");
  // Another device can't remove someone else's phone.
  const other = await registered(ctx);
  const three = await paired(ctx, device, "Laptop");
  const id = (await ctx.call("app-inbox", { headers: device })).json.links[0].id;
  await rejects(ctx.call("app-unpair", { headers: other, body: { link_id: id } }), 404);
  await ctx.call("app-thread", { headers: three.app });
});

test("ciphertext only: payloads are validated, never interpreted", async () => {
  const ctx = setup();
  const device = await registered(ctx);
  const { app } = await paired(ctx, device);
  await rejects(ctx.call("app-send", { headers: app, body: { payload: "hello mom, plain text", client_ref: "phone-0003" } }), 400, "payload");
  await rejects(ctx.call("app-send", { headers: app, body: { payload: payload(), client_ref: "x" } }), 400, "client_ref");
  await rejects(ctx.call("app-send", { headers: { authorization: "LumaApp nope" }, body: { payload: payload(), client_ref: "phone-0004" } }), 401, "unpaired");
});

test("long polling waits for the next message instead of returning empty right away", async () => {
  const ctx = setup();
  const device = await registered(ctx);
  const { app } = await paired(ctx, device);
  const started = ctx.now();
  const empty = await ctx.call("app-thread", { headers: app, query: { wait: "25" } });
  assert.equal(empty.json.messages.length, 0);
  assert.ok(ctx.now() - started >= 25_000, "held for the full wait");
  assert.ok(ctx.now() - started < 27_000);
  const capped = ctx.now();
  await ctx.call("app-inbox", { headers: device, query: { wait: "500" } });
  assert.ok(ctx.now() - capped <= 25_000, "wait is capped at 25 seconds");
});

test("Luma wakes a closed app with a push, but not an open one, and forgets dead subscriptions", async () => {
  const ctx = setup();
  const device = await registered(ctx);
  const { app } = await paired(ctx, device);
  const sub = { endpoint: "https://push.example.net/send/abc", keys: { p256dh: Buffer.alloc(65, 4).toString("base64url"), auth: Buffer.alloc(16, 1).toString("base64url") } };
  await rejects(ctx.call("app-push", { headers: app, body: { subscription: { endpoint: "http://insecure", keys: sub.keys } } }), 400, "subscription");
  await ctx.call("app-push", { headers: app, body: { subscription: sub } });
  const linkId = (await ctx.call("app-inbox", { headers: device })).json.links[0].id;

  await ctx.call("app-reply", { headers: device, body: { messages: [{ link_id: linkId, payload: payload(3), client_ref: "luma-0002", notify: true }] } });
  assert.equal(ctx.pushes.length, 1);
  assert.equal(ctx.pushes[0].body.payload, payload(3));

  await ctx.call("app-thread", { headers: app }); // the app is open now
  await ctx.call("app-reply", { headers: device, body: { messages: [{ link_id: linkId, payload: payload(4), client_ref: "luma-0003", notify: true }] } });
  assert.equal(ctx.pushes.length, 1, "no push while the app is on screen");

  ctx.tick(60_000);
  await ctx.call("app-reply", { headers: device, body: { messages: [{ link_id: linkId, payload: payload(5), client_ref: "luma-0004" }] } });
  assert.equal(ctx.pushes.length, 1, "only messages marked notify wake the phone");

  await ctx.call("app-push", { headers: app, body: { subscription: { ...sub, endpoint: "https://push.example.net/gone/1" } } });
  ctx.tick(60_000);
  await ctx.call("app-reply", { headers: device, body: { messages: [{ link_id: linkId, payload: payload(6), client_ref: "luma-0005", notify: true }] } });
  assert.equal(ctx.db.t.links[0].push_subscription, null);
});

test("verifying a phone later attaches it to the same Luma; texting waits for that", async () => {
  const ctx = setup();
  const device = await registered(ctx);
  const { app } = await paired(ctx, device);
  await rejects(ctx.call("sms-send", { headers: device, body: { to: "+19195550177", body: "hi", client_ref: "send-0001" } }), 403, "verify_phone");
  await ctx.call("verify-start", { body: { phone: "+19195550123", name: "Marvin" } });
  const linked = await ctx.call("verify-check", { headers: device, body: { phone: "+19195550123", code: "123456", name: "Marvin" } });
  assert.equal(linked.json.device_token, null);
  assert.equal(linked.json.linked, true);
  assert.equal(linked.json.account.verified, true);
  const sent = await ctx.call("sms-send", { headers: device, body: { to: "+19195550177", body: "hi", client_ref: "send-0002" } });
  assert.equal(sent.status, 200);
  await ctx.call("app-thread", { headers: app }); // the phone stays paired through it
});

test("one owner who verifies on a second Luma joins their existing account", async () => {
  const ctx = setup();
  await ctx.call("verify-start", { body: { phone: "+19195550123", name: "Marvin" } });
  const first = await ctx.call("verify-check", { body: { phone: "+19195550123", code: "123456", name: "Marvin" } });
  const device = await registered(ctx);
  await ctx.call("verify-check", { headers: device, body: { phone: "+19195550123", code: "123456", name: "Marvin" } });
  const a = await ctx.call("account", { headers: device });
  const b = await ctx.call("account", { headers: { authorization: "Bearer " + first.json.device_token } });
  assert.equal(a.json.verified, true);
  assert.equal(ctx.db.t.devices[1].account_id, ctx.db.t.devices[0].account_id);
  assert.equal(a.json.owner_name, b.json.owner_name);
});

test("registration is rate limited per address", async () => {
  const ctx = setup();
  for (let i = 0; i < 5; i++) await ctx.call("device-register", { ip: "198.51.100.7" });
  await rejects(ctx.call("device-register", { ip: "198.51.100.7" }), 429, "slow_down");
  await ctx.call("device-register", { ip: "198.51.100.8" });
});

test("health reports what the app needs", async () => {
  const ctx = setup();
  const health = await ctx.call("health");
  assert.deepEqual(health.json.app, { pairing: true, notifications: true });
  const bare = setup({});
  assert.equal((await bare.call("app-config")).json.push_key, null);
});

test("the HTTP wrapper routes app GETs and POSTs", async () => {
  const db = memoryDb();
  const handler = createHandler(() => ({ env: ENV, db, fetch: async () => ({ ok: false, status: 404, json: async () => ({}) }) }));
  const run = async (method, route, body, headers = {}) => {
    const res = { statusCode: 0, headers: {}, setHeader(k, v) { this.headers[k] = v; }, end(b) { this.body = b; } };
    await handler({ method, query: { route }, headers: { "content-type": "application/json", ...headers }, rawBody: body ? JSON.stringify(body) : "" }, res);
    return { status: res.statusCode, json: JSON.parse(res.body || "{}") };
  };
  assert.equal((await run("GET", "app-config")).status, 200);
  assert.equal((await run("POST", "app-config")).status, 405);
  const reg = await run("POST", "device-register", { device_name: "Den" }, { "x-forwarded-for": "192.0.2.44" });
  assert.equal(reg.status, 200);
  assert.match(reg.json.device_token, /^[0-9a-f-]{36}\.[A-Za-z0-9_-]{40,}$/);
  assert.equal((await run("GET", "app-thread", null, { authorization: "LumaApp bad" })).status, 401);
});

// --------------------------------------------------------------- Web Push ---

function decryptAsBrowser(body, receiver, authSecret) {
  const salt = body.subarray(0, 16);
  const idlen = body[20];
  const senderPublic = body.subarray(21, 21 + idlen);
  const ciphertext = body.subarray(21 + idlen);
  const shared = receiver.computeSecret(senderPublic);
  const keyInfo = Buffer.concat([Buffer.from("WebPush: info\0"), receiver.getPublicKey(), senderPublic]);
  const ikm = Buffer.from(crypto.hkdfSync("sha256", shared, authSecret, keyInfo, 32));
  const cek = Buffer.from(crypto.hkdfSync("sha256", ikm, salt, Buffer.from("Content-Encoding: aes128gcm\0"), 16));
  const nonce = Buffer.from(crypto.hkdfSync("sha256", ikm, salt, Buffer.from("Content-Encoding: nonce\0"), 12));
  const decipher = crypto.createDecipheriv("aes-128-gcm", cek, nonce);
  decipher.setAuthTag(ciphertext.subarray(-16));
  const plain = Buffer.concat([decipher.update(ciphertext.subarray(0, -16)), decipher.final()]);
  assert.equal(plain.at(-1), 2, "last-record padding delimiter");
  return plain.subarray(0, -1).toString();
}

test("push payloads decrypt the way a phone's browser decrypts them (RFC 8291)", async () => {
  const receiver = crypto.createECDH("prime256v1");
  receiver.generateKeys();
  const authSecret = crypto.randomBytes(16);
  const sub = { endpoint: "https://fcm.googleapis.com/fcm/send/abc", keys: { p256dh: receiver.getPublicKey().toString("base64url"), auth: authSecret.toString("base64url") } };
  const body = encryptPayload(sub, Buffer.from('{"id":"1","payload":"abc"}'));
  assert.equal(decryptAsBrowser(body, receiver, authSecret), '{"id":"1","payload":"abc"}');

  let seen = null;
  const result = await sendPush(sub, { id: "m1", payload: "xyz" }, { ...VAPID, subject: "mailto:hello@example.com" }, {
    now: Date.UTC(2026, 9, 13), fetch: async (url, init) => { seen = { url, init }; return { ok: true, status: 201 }; },
  });
  assert.equal(result, "sent");
  assert.equal(seen.init.headers["Content-Encoding"], "aes128gcm");
  assert.deepEqual(JSON.parse(decryptAsBrowser(seen.init.body, receiver, authSecret)), { id: "m1", payload: "xyz" });

  // The VAPID token verifies against the public key and names the push service.
  const auth = seen.init.headers.Authorization;
  const [, jwt, key] = /^vapid t=([^,]+), k=(.+)$/.exec(auth);
  assert.equal(key, VAPID.publicKey);
  const [h, c, s] = jwt.split(".");
  const pub = Buffer.from(VAPID.publicKey, "base64url");
  const publicKey = crypto.createPublicKey({ key: { kty: "EC", crv: "P-256", x: pub.subarray(1, 33).toString("base64url"), y: pub.subarray(33).toString("base64url") }, format: "jwk" });
  assert.ok(crypto.verify("sha256", Buffer.from(`${h}.${c}`), { key: publicKey, dsaEncoding: "ieee-p1363" }, Buffer.from(s, "base64url")));
  const claims = JSON.parse(Buffer.from(c, "base64url"));
  assert.equal(claims.aud, "https://fcm.googleapis.com");
  assert.equal(claims.sub, "mailto:hello@example.com");
  assert.ok(vapidAuthorization(sub.endpoint, { ...VAPID, subject: "mailto:a@b.c" }, 1).startsWith("vapid t="));

  const gone = await sendPush(sub, {}, { ...VAPID, subject: "mailto:a@b.c" }, { fetch: async () => ({ ok: false, status: 410 }) });
  assert.equal(gone, "gone");
  assert.equal(await sendPush(sub, {}, { publicKey: "", privateKey: "", subject: "" }), "failed");
});
