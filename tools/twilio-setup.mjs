// One-time Twilio setup for Lumin (customers never touch Twilio).
//
//   TWILIO_ACCOUNT_SID=AC... TWILIO_AUTH_TOKEN=... \
//     node tools/twilio-setup.mjs --site https://your-site.vercel.app --area 919
//
// Creates (or reuses, if they already exist) everything Luma Cloud needs:
//   1. a Verify service for owners' one-time sign-up codes
//   2. a Messaging Service named "Luma" with inbound + delivery webhooks and
//      sticky sender (each friend always hears from the same Luma number)
//   3. one shared local number for free-plan texts, added to that service
// …then prints the variables to paste into Vercel. Add --dry-run to only look.
// Carrier registration (A2P 10DLC) is a separate form: see docs/TWILIO_SETUP.md.
import { pathToFileURL } from "node:url";

const SERVICE_NAME = "Luma";

export async function setup({ sid, token, site, area = "", dryRun = false, fetch: fetchImpl = fetch, log = console.log }) {
  if (!/^AC[0-9a-fA-F]{32}$/.test(sid || "") || !token) throw new Error("Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN (Twilio Console → Account → API keys & tokens).");
  if (!/^https:\/\/[^/]+$/.test((site || "").replace(/\/+$/, ""))) throw new Error("Pass --site with your live website, like https://lumin-holdings-site.vercel.app");
  site = site.replace(/\/+$/, "");
  const auth = "Basic " + Buffer.from(`${sid}:${token}`).toString("base64");
  async function call(method, url, params) {
    const response = await fetchImpl(url, {
      method,
      headers: { Authorization: auth, ...(params ? { "Content-Type": "application/x-www-form-urlencoded" } : {}) },
      body: params ? new URLSearchParams(params).toString() : undefined,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(`Twilio said no (${response.status}${data.code ? ", code " + data.code : ""}): ${data.message || url}`);
    return data;
  }
  const inbound = `${site}/api/luma/twilio-inbound`;
  const status = `${site}/api/luma/twilio-status`;

  // 1. Verify service
  const verifyList = await call("GET", "https://verify.twilio.com/v2/Services?PageSize=50");
  let verify = (verifyList.services || []).find((s) => s.friendly_name === SERVICE_NAME);
  if (verify) log(`✓ Verify service already exists (${verify.sid})`);
  else if (dryRun) log("• would create a Verify service named Luma");
  else {
    verify = await call("POST", "https://verify.twilio.com/v2/Services", { FriendlyName: SERVICE_NAME, CodeLength: "6" });
    log(`✓ Created Verify service ${verify.sid}`);
  }

  // 2. Messaging Service
  const msgList = await call("GET", "https://messaging.twilio.com/v1/Services?PageSize=50");
  let service = (msgList.services || []).find((s) => s.friendly_name === SERVICE_NAME);
  const serviceSettings = { InboundRequestUrl: inbound, InboundMethod: "POST", StatusCallback: status, UseInboundWebhookOnNumber: "false", StickySender: "true", AreaCodeGeomatch: "true" };
  if (service) {
    log(`✓ Messaging Service already exists (${service.sid}); webhooks ${dryRun ? "would be" : ""} pointed at ${site}`);
    if (!dryRun) await call("POST", `https://messaging.twilio.com/v1/Services/${service.sid}`, serviceSettings);
  } else if (dryRun) log("• would create a Messaging Service named Luma with webhooks to " + site);
  else {
    service = await call("POST", "https://messaging.twilio.com/v1/Services", { FriendlyName: SERVICE_NAME, ...serviceSettings });
    log(`✓ Created Messaging Service ${service.sid}`);
  }

  // 3. Shared number for the free plan
  let shared = null;
  if (service && !dryRun) {
    const senders = await call("GET", `https://messaging.twilio.com/v1/Services/${service.sid}/PhoneNumbers?PageSize=50`);
    shared = (senders.phone_numbers || [])[0]?.phone_number || null;
  }
  if (shared) log(`✓ Shared number already in the service: ${shared}`);
  else if (dryRun) log(`• would buy a local number${area ? " in " + area : ""} and add it to the service`);
  else {
    const found = await call("GET", `https://api.twilio.com/2010-04-01/Accounts/${sid}/AvailablePhoneNumbers/US/Local.json?SmsEnabled=true&PageSize=1${area ? "&AreaCode=" + area : ""}`);
    const pick = found.available_phone_numbers?.[0]?.phone_number;
    if (!pick) throw new Error(`No numbers available${area ? " in " + area : ""}. Try another --area.`);
    const bought = await call("POST", `https://api.twilio.com/2010-04-01/Accounts/${sid}/IncomingPhoneNumbers.json`, { PhoneNumber: pick, SmsUrl: inbound, SmsMethod: "POST", FriendlyName: "Luma shared" });
    await call("POST", `https://messaging.twilio.com/v1/Services/${service.sid}/PhoneNumbers`, { PhoneNumberSid: bought.sid });
    shared = bought.phone_number;
    log(`✓ Bought ${shared} and added it to the Luma Messaging Service`);
  }

  const env = {
    LUMA_CLOUD_PUBLIC_URL: site,
    TWILIO_ACCOUNT_SID: sid,
    TWILIO_AUTH_TOKEN: "(the auth token you used)",
    TWILIO_VERIFY_SERVICE_SID: verify?.sid || "(created on a real run)",
    TWILIO_MESSAGING_SERVICE_SID: service?.sid || "(created on a real run)",
    LUMA_SHARED_NUMBER: shared || "(bought on a real run)",
    LUMA_PROVISION_NUMBERS: "1",
  };
  log("\nPaste these into Vercel → your project → Settings → Environment Variables (Production):\n");
  for (const [k, v] of Object.entries(env)) log(`${k}=${v}`);
  log("\nNext: register the brand and campaign so carriers deliver your texts (docs/TWILIO_SETUP.md).");
  return env;
}

if (import.meta.url === pathToFileURL(process.argv[1] || "").href) {
  const arg = (name) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : undefined; };
  setup({ sid: process.env.TWILIO_ACCOUNT_SID, token: process.env.TWILIO_AUTH_TOKEN, site: arg("--site"), area: arg("--area") || "", dryRun: process.argv.includes("--dry-run") })
    .catch((error) => { console.error("✗ " + error.message); process.exit(1); });
}
