// Run Luma Cloud on your own computer with no accounts: `node tools/luma-cloud-dev.mjs`
//
// It serves the real relay code (api/_lib/luma-cloud.js) with an in-memory
// database, a pretend carrier that prints texts here instead of sending them,
// verification code 123456, and a pretend Luma Plus checkout. Point Luma at it:
//   LUMA_CLOUD_URL=http://127.0.0.1:8787 .venv/bin/python -m luma.cli serve
//
// Dev-only extras:
//   GET  /fake-checkout?account=<id>  completes a Luma Plus purchase
//   POST /dev/reply {"from": "+1919...", "to": "+1919...", "body": "..."}  pretends someone texted back
import http from "node:http";
import crypto from "node:crypto";
import { createHandler, createService, twilioSignature } from "../api/_lib/luma-cloud.js";
import { memoryDb } from "../api/_lib/luma-memory-db.js";

const port = Number(process.env.PORT || 8787);
const base = `http://127.0.0.1:${port}`;
const env = {
  LUMA_CLOUD_PUBLIC_URL: base,
  LUMA_FREE_TEXTS_PER_MONTH: process.env.LUMA_FREE_TEXTS_PER_MONTH || "5",
  LUMA_PLUS_TEXTS_PER_MONTH: "300",
  LUMA_SHARED_NUMBER: "+19195550000",
  TWILIO_ACCOUNT_SID: "AC" + "0".repeat(32),
  TWILIO_AUTH_TOKEN: "dev-token",
  TWILIO_VERIFY_SERVICE_SID: "VAdev",
  STRIPE_SECRET_KEY: "sk_dev",
  LUMA_PLUS_PRICE_ID: "price_dev",
  STRIPE_WEBHOOK_SECRET: "whsec_dev",
  LUMA_PROVISION_NUMBERS: "1",
};
const db = memoryDb();
let sid = 0;
let numbers = 0;
const json = (status, data) => ({ ok: status < 400, status, json: async () => data, text: async () => JSON.stringify(data) });

async function pretendProviders(url, init = {}) {
  const params = Object.fromEntries(new URLSearchParams(init.body || ""));
  if (url.endsWith("/Messages.json")) {
    console.log(`\n📱 text to ${params.To} from ${params.From || "Luma"}:\n   ${params.Body.replace(/\n/g, "\n   ")}`);
    return json(201, { sid: "SM" + String(++sid).padStart(32, "0"), status: "queued" });
  }
  if (url.includes("/Verifications")) {
    console.log(`\n🔐 verification code for ${params.To}: 123456`);
    return json(201, { status: "pending" });
  }
  if (url.includes("/VerificationCheck")) return json(200, { status: params.Code === "123456" ? "approved" : "pending" });
  if (url.includes("checkout/sessions")) return json(200, { url: `${base}/fake-checkout?account=${params.client_reference_id}` });
  if (url.includes("billing_portal")) return json(200, { url: `${base}/fake-portal` });
  if (url.includes("AvailablePhoneNumbers")) return json(200, { available_phone_numbers: [{ phone_number: `+1919555${String(1000 + ++numbers)}` }] });
  if (url.includes("IncomingPhoneNumbers.json")) return json(201, { sid: "PN" + numbers, phone_number: params.PhoneNumber });
  return json(404, {});
}

const handler = createHandler(() => ({ env, db, fetch: pretendProviders }));
const { routes } = createService({ env, db, fetch: pretendProviders });

function page(title, text) {
  return `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title>
<body style="font-family:-apple-system,system-ui,sans-serif;background:#f6f5f1;color:#2d3530;display:grid;place-items:center;min-height:100vh;margin:0">
<div style="max-width:420px;padding:32px;background:#fff;border-radius:24px;border:1px solid #e6e8df"><p style="font-size:11px;letter-spacing:.14em;color:#999d8c">LUMA PLUS · DEV CHECKOUT</p><h1 style="font-size:28px">${title}</h1><p>${text}</p></div>`;
}

http.createServer(async (req, res) => {
  const url = new URL(req.url, base);
  if (url.pathname.startsWith("/api/luma/")) {
    req.query = { ...Object.fromEntries(url.searchParams), route: url.pathname.slice("/api/luma/".length) };
    return handler(req, res);
  }
  if (url.pathname === "/fake-checkout") {
    const account = url.searchParams.get("account");
    const event = JSON.stringify({ id: "evt_" + crypto.randomUUID(), type: "checkout.session.completed",
      data: { object: { mode: "subscription", customer: "cus_" + account.slice(0, 8), subscription: "sub_" + account.slice(0, 8), client_reference_id: account, metadata: { app: "luma", account_id: account } } } });
    const t = Math.floor(Date.now() / 1000);
    const v1 = crypto.createHmac("sha256", env.STRIPE_WEBHOOK_SECRET).update(`${t}.${event}`).digest("hex");
    await routes["stripe-webhook"]({ headers: { "stripe-signature": `t=${t},v1=${v1}` }, raw: event });
    console.log(`\n💳 Luma Plus activated for account ${account}`);
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    return res.end(page("You’re on Luma Plus.", "300 texts a month and your own Luma number. You can close this tab; Luma already knows."));
  }
  if (url.pathname === "/fake-portal") {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    return res.end(page("Manage Luma Plus", "In production this is Stripe’s billing portal."));
  }
  if (url.pathname === "/dev/reply" && req.method === "POST") {
    let raw = "";
    for await (const chunk of req) raw += chunk;
    const { from, to = env.LUMA_SHARED_NUMBER, body } = JSON.parse(raw || "{}");
    const form = { From: from, To: to, Body: body, MessageSid: "SMin" + Date.now() };
    await routes["twilio-inbound"]({ form, headers: { "x-twilio-signature": twilioSignature(env.TWILIO_AUTH_TOKEN, base + "/api/luma/twilio-inbound", form) } });
    console.log(`\n💬 reply from ${from} to ${to}: ${body}`);
    res.setHeader("Content-Type", "application/json");
    return res.end('{"ok":true}');
  }
  res.statusCode = 404;
  res.end("not found");
}).listen(port, "127.0.0.1", () => console.log(`Luma Cloud (dev) on ${base} · verification code 123456 · ${env.LUMA_FREE_TEXTS_PER_MONTH} free texts/month`));
