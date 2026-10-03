// The one-time Twilio setup script, against a pretend Twilio. Run: node --test tests/twilio-setup.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { setup } from "../tools/twilio-setup.mjs";

function pretendTwilio(existing = false) {
  const calls = [];
  const state = { verify: existing ? [{ sid: "VA1", friendly_name: "Luma" }] : [], services: existing ? [{ sid: "MG1", friendly_name: "Luma" }] : [], senders: existing ? [{ phone_number: "+19195550000" }] : [] };
  const fetch = async (url, init = {}) => {
    const params = Object.fromEntries(new URLSearchParams(init.body || ""));
    calls.push({ url, method: init.method, params });
    const ok = (data, status = 200) => ({ ok: true, status, json: async () => data });
    if (url.startsWith("https://verify.twilio.com/v2/Services?")) return ok({ services: state.verify });
    if (url === "https://verify.twilio.com/v2/Services") { state.verify.push({ sid: "VA9", friendly_name: params.FriendlyName }); return ok({ sid: "VA9" }, 201); }
    if (url.startsWith("https://messaging.twilio.com/v1/Services?")) return ok({ services: state.services });
    if (url === "https://messaging.twilio.com/v1/Services") return ok({ sid: "MG9" }, 201);
    if (url.includes("/PhoneNumbers?")) return ok({ phone_numbers: state.senders });
    if (url.includes("AvailablePhoneNumbers")) return ok({ available_phone_numbers: [{ phone_number: "+19195557777" }] });
    if (url.includes("IncomingPhoneNumbers.json")) return ok({ sid: "PN9", phone_number: params.PhoneNumber }, 201);
    if (url.includes("/PhoneNumbers")) return ok({}, 201);
    if (url.includes("/Services/")) return ok({});
    return { ok: false, status: 404, json: async () => ({}) };
  };
  return { fetch, calls };
}
const SID = "AC" + "a".repeat(32);

test("a fresh account gets verification, a messaging service with webhooks, and a shared number", async () => {
  const tw = pretendTwilio();
  const lines = [];
  const env = await setup({ sid: SID, token: "t", site: "https://luma.example.com/", area: "919", fetch: tw.fetch, log: (l) => lines.push(l) });
  assert.equal(env.TWILIO_VERIFY_SERVICE_SID, "VA9");
  assert.equal(env.TWILIO_MESSAGING_SERVICE_SID, "MG9");
  assert.equal(env.LUMA_SHARED_NUMBER, "+19195557777");
  const service = tw.calls.find((c) => c.url === "https://messaging.twilio.com/v1/Services");
  assert.equal(service.params.InboundRequestUrl, "https://luma.example.com/api/luma/twilio-inbound");
  assert.equal(service.params.StickySender, "true");
  assert.ok(tw.calls.some((c) => c.url.endsWith("/Services/MG9/PhoneNumbers") && c.params.PhoneNumberSid === "PN9"));
  assert.ok(lines.some((l) => l.startsWith("LUMA_SHARED_NUMBER=+19195557777")));
  assert.ok(!lines.join("\n").includes("auth_token_value"));
});

test("running it again reuses everything and buys nothing", async () => {
  const tw = pretendTwilio(true);
  const env = await setup({ sid: SID, token: "t", site: "https://luma.example.com", fetch: tw.fetch, log: () => {} });
  assert.equal(env.LUMA_SHARED_NUMBER, "+19195550000");
  assert.ok(!tw.calls.some((c) => c.url.includes("IncomingPhoneNumbers")));
});

test("a dry run only looks", async () => {
  const tw = pretendTwilio();
  await setup({ sid: SID, token: "t", site: "https://luma.example.com", dryRun: true, fetch: tw.fetch, log: () => {} });
  assert.ok(tw.calls.every((c) => !c.method || c.method === "GET"));
});

test("bad input is explained", async () => {
  await assert.rejects(setup({ sid: "nope", token: "t", site: "https://x.com" }), /TWILIO_ACCOUNT_SID/);
  await assert.rejects(setup({ sid: SID, token: "t", site: "http://x.com" }), /--site/);
});
