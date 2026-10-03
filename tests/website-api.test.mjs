// The waitlist API: admin-only reads, validated sign-ups. Run: node --test tests/website-api.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import reservations from "../api/reservations.js";
import reserve from "../api/reserve.js";

function res() {
  return { code: 0, body: null, headers: {}, setHeader(k, v) { this.headers[k] = v; }, status(c) { this.code = c; return this; }, json(b) { this.body = b; return this; } };
}
const env = { LUMA_ADMIN_TOKEN: "a-very-long-admin-token-123", SUPABASE_URL: "https://x.supabase.co", SUPABASE_SERVICE_ROLE_KEY: "service" };
const rows = [{ email: "a@b.co", phone: "919", timestamp: "2026-10-03" }];
const fakeFetch = async () => ({ ok: true, json: async () => rows });

test("the waitlist is not readable without the admin token", async () => {
  for (const authorization of [undefined, "Bearer wrong-token-wrong-token", "a-very-long-admin-token-123"]) {
    const r = res();
    await reservations({ method: "GET", headers: { authorization } }, r, env, fakeFetch);
    assert.equal(r.code, 401);
  }
  const r = res();
  await reservations({ method: "GET", headers: {} }, r, { ...env, LUMA_ADMIN_TOKEN: "" }, fakeFetch);
  assert.equal(r.code, 401, "no token configured means nobody gets in");
});

test("the admin can read it with the token", async () => {
  const r = res();
  await reservations({ method: "GET", headers: { authorization: "Bearer a-very-long-admin-token-123" } }, r, env, fakeFetch);
  assert.equal(r.code, 200);
  assert.deepEqual(r.body, rows);
});

test("sign-ups are validated", async () => {
  for (const body of [{}, { email: "not-an-email" }, { email: "<script>@x.co" }, { email: "a@b.co", phone: "12" }]) {
    const r = res();
    await reserve({ method: "POST", body }, r);
    assert.equal(r.code, 400, JSON.stringify(body));
  }
});

test("no admin password ships in the website and emails are never rendered as HTML", () => {
  const admin = readFileSync(new URL("../admin.js", import.meta.url), "utf8");
  assert.doesNotMatch(admin, /password\s*===/);
  assert.doesNotMatch(admin, /\$\{entry\./);
});
