// Luma Cloud: Luma's own texting number, monthly quotas and Luma Plus billing.
//
// One Vercel function (api/luma/[route].js) serves every route below. All state
// lives in Supabase tables that only the service role can touch (see
// supabase/migrations). Twilio sends and receives the texts; Stripe bills Luma
// Plus. Dependencies are injected so the whole flow runs in tests without a
// network.
//
// Device routes authenticate with "Authorization: Bearer <device_id>.<secret>".
// The Luma app on a phone authenticates with "Authorization: LumaApp <link_id>.<secret>".
// Webhook routes authenticate with the provider's signature.
//
// The app and the device talk end to end encrypted (AES-GCM with a key that
// only travels in the pairing link's #fragment), so Luma Cloud stores and
// forwards ciphertext it cannot read.
import crypto from "node:crypto";
import { sendPush, vapidReady } from "./web-push.js";

const STOP_WORDS = new Set(["STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT", "REVOKE", "OPTOUT"]);
const START_WORDS = new Set(["START", "UNSTOP", "OPTIN"]);
const HELP_WORDS = new Set(["HELP", "INFO"]);
const E164 = /^\+[1-9]\d{7,14}$/;
const NANP = /^\+1[2-9]\d{2}[2-9]\d{6}$/;
const MAX_BODY = 640; // four SMS segments at most
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const PAYLOAD = /^[A-Za-z0-9_-]{24,24000}$/; // base64url of iv + AES-GCM ciphertext
const REF = /^[A-Za-z0-9_-]{6,64}$/;
const APP_RETENTION_DAYS = 30;
const MAX_LINKS = 8;

export class HttpError extends Error {
  constructor(status, code, message, extra = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.extra = extra;
  }
}

function int(value, fallback) {
  const n = Number.parseInt(value ?? "", 10);
  return Number.isFinite(n) && n >= 0 ? n : fallback;
}

export function settings(env) {
  return {
    publicUrl: (env.LUMA_CLOUD_PUBLIC_URL || "").replace(/\/+$/, ""),
    freeTexts: int(env.LUMA_FREE_TEXTS_PER_MONTH, 30),
    plusTexts: int(env.LUMA_PLUS_TEXTS_PER_MONTH, 300),
    plusPriceLabel: env.LUMA_PLUS_PRICE_LABEL || "$9.99/month",
    countries: (env.LUMA_TEXT_COUNTRY_CODES || "1").split(",").map((c) => c.trim()).filter(Boolean),
    perMinute: int(env.LUMA_TEXTS_PER_MINUTE, 6),
    sharedNumber: env.LUMA_SHARED_NUMBER || "",
    messagingService: env.TWILIO_MESSAGING_SERVICE_SID || "",
    twilioSid: env.TWILIO_ACCOUNT_SID || "",
    twilioToken: env.TWILIO_AUTH_TOKEN || "",
    verifyService: env.TWILIO_VERIFY_SERVICE_SID || "",
    stripeKey: env.STRIPE_SECRET_KEY || "",
    stripePrice: env.LUMA_PLUS_PRICE_ID || "",
    stripeWebhookSecret: env.STRIPE_WEBHOOK_SECRET || "",
    provisionNumbers: env.LUMA_PROVISION_NUMBERS === "1",
    releaseNumbers: env.LUMA_RELEASE_NUMBERS_ON_CANCEL === "1",
    portalConfig: env.LUMA_STRIPE_PORTAL_CONFIG || "",
    vapid: { publicKey: env.LUMA_VAPID_PUBLIC_KEY || "", privateKey: env.LUMA_VAPID_PRIVATE_KEY || "", subject: env.LUMA_VAPID_SUBJECT || "" },
  };
}

// ---------------------------------------------------------------- helpers ---

export function period(now) {
  const d = new Date(now);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

export function periodEnd(now) {
  const d = new Date(now);
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1)).toISOString();
}

export function sha256(text) {
  return crypto.createHash("sha256").update(text).digest("hex");
}

function safeEqual(a, b) {
  const x = Buffer.from(String(a));
  const y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
}

export function checkNumber(number, countries) {
  if (typeof number !== "string" || !E164.test(number)) {
    throw new HttpError(400, "bad_number", "Use a full phone number with country code, like +19195550123.");
  }
  const allowed = countries.some((code) => number.startsWith("+" + code));
  if (!allowed || (number.startsWith("+1") && !NANP.test(number))) {
    throw new HttpError(403, "destination", "Luma's number can only text US and Canadian numbers right now.");
  }
  return number;
}

export function cleanBody(body) {
  if (typeof body !== "string") throw new HttpError(400, "bad_body", "The text is empty.");
  const text = body.replace(/[\u0000-\u0008\u000B-\u001F\u007F]/g, "").trim();
  if (!text) throw new HttpError(400, "bad_body", "The text is empty.");
  if (text.length > MAX_BODY) throw new HttpError(400, "too_long", `Keep texts under ${MAX_BODY} characters.`);
  return text;
}

export function twilioSignature(token, url, params) {
  const data = url + Object.keys(params).sort().map((key) => key + params[key]).join("");
  return crypto.createHmac("sha1", token).update(Buffer.from(data, "utf8")).digest("base64");
}

export function stripeSignatureValid(secret, header, raw, nowSeconds, tolerance = 300) {
  if (!secret || typeof header !== "string") return false;
  let timestamp = null;
  const signatures = [];
  for (const part of header.split(",")) {
    const [key, value] = part.split("=", 2).map((x) => x?.trim());
    if (key === "t") timestamp = value;
    if (key === "v1" && value) signatures.push(value);
  }
  if (!timestamp || !signatures.length || Math.abs(nowSeconds - Number(timestamp)) > tolerance) return false;
  const expected = crypto.createHmac("sha256", secret).update(`${timestamp}.${raw}`, "utf8").digest("hex");
  return signatures.some((sig) => safeEqual(sig, expected));
}

export function formEncode(value, prefix = "", out = new URLSearchParams()) {
  if (value === undefined || value === null) return out;
  if (typeof value === "object" && !Array.isArray(value)) {
    for (const [k, v] of Object.entries(value)) formEncode(v, prefix ? `${prefix}[${k}]` : k, out);
  } else if (Array.isArray(value)) {
    value.forEach((v, i) => formEncode(v, `${prefix}[${i}]`, out));
  } else {
    out.append(prefix, String(value));
  }
  return out;
}

function firstWord(body) {
  return String(body || "").trim().split(/\s+/)[0]?.toUpperCase().replace(/[^A-Z]/g, "") || "";
}

// ------------------------------------------------------------- providers ---

export function makeTwilio(cfg, fetchImpl) {
  const auth = "Basic " + Buffer.from(`${cfg.twilioSid}:${cfg.twilioToken}`).toString("base64");
  const base = `https://api.twilio.com/2010-04-01/Accounts/${cfg.twilioSid}`;
  async function call(method, url, params) {
    const response = await fetchImpl(url, {
      method,
      headers: { Authorization: auth, ...(params ? { "Content-Type": "application/x-www-form-urlencoded" } : {}) },
      body: params ? formEncode(params).toString() : undefined,
    });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, status: response.status, data };
  }
  return {
    configured: () => Boolean(cfg.twilioSid && cfg.twilioToken),
    async send({ to, body, from, statusCallback }) {
      const params = { To: to, Body: body, StatusCallback: statusCallback || undefined };
      if (cfg.messagingService) params.MessagingServiceSid = cfg.messagingService;
      if (from) params.From = from;
      return call("POST", `${base}/Messages.json`, params);
    },
    async startVerify(phone) {
      return call("POST", `https://verify.twilio.com/v2/Services/${cfg.verifyService}/Verifications`, { To: phone, Channel: "sms" });
    },
    async checkVerify(phone, code) {
      return call("POST", `https://verify.twilio.com/v2/Services/${cfg.verifyService}/VerificationCheck`, { To: phone, Code: code });
    },
    async searchNumbers(areaCode, limit = 5) {
      const query = `SmsEnabled=true&PageSize=${limit}${areaCode ? "&AreaCode=" + areaCode : ""}`;
      const found = await call("GET", `${base}/AvailablePhoneNumbers/US/Local.json?${query}`);
      if (!found.ok) return [];
      return (found.data.available_phone_numbers || []).filter((n) => NANP.test(n.phone_number || "")).slice(0, limit)
        .map((n) => ({ number: n.phone_number, locality: n.locality || null, region: n.region || null }));
    },
    // Buy the number the customer picked; if someone else got it first, the nearest one.
    async buyNumber(desired, ownerPhone, smsUrl) {
      if (desired && NANP.test(desired)) {
        const exact = await this.purchase(desired, smsUrl);
        if (exact) return exact;
        return this.buyNumberNear("+1" + desired.slice(2, 5), smsUrl);
      }
      return this.buyNumberNear(ownerPhone, smsUrl);
    },
    async purchase(number, smsUrl) {
      const bought = await call("POST", `${base}/IncomingPhoneNumbers.json`, { PhoneNumber: number, SmsUrl: smsUrl, SmsMethod: "POST" });
      if (!bought.ok) return null;
      if (cfg.messagingService) {
        await call("POST", `https://messaging.twilio.com/v1/Services/${cfg.messagingService}/PhoneNumbers`, { PhoneNumberSid: bought.data.sid });
      }
      return { number: bought.data.phone_number, sid: bought.data.sid };
    },
    async buyNumberNear(phone, smsUrl) {
      const area = /^\+1(\d{3})/.exec(phone)?.[1];
      const search = await call("GET", `${base}/AvailablePhoneNumbers/US/Local.json?SmsEnabled=true&PageSize=1${area ? "&AreaCode=" + area : ""}`);
      let candidate = search.ok ? search.data.available_phone_numbers?.[0] : null;
      if (!candidate && area) {
        const any = await call("GET", `${base}/AvailablePhoneNumbers/US/Local.json?SmsEnabled=true&PageSize=1`);
        candidate = any.ok ? any.data.available_phone_numbers?.[0] : null;
      }
      if (!candidate) return null;
      return this.purchase(candidate.phone_number, smsUrl);
    },
    async releaseNumber(sid) {
      return call("DELETE", `${base}/IncomingPhoneNumbers/${sid}.json`);
    },
  };
}

export function makeStripe(cfg, fetchImpl) {
  async function call(path, params) {
    const response = await fetchImpl(`https://api.stripe.com/v1/${path}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${cfg.stripeKey}`, "Content-Type": "application/x-www-form-urlencoded" },
      body: formEncode(params).toString(),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new HttpError(502, "billing", "Billing is unavailable right now. Try again in a minute.");
    return data;
  }
  return {
    configured: () => Boolean(cfg.stripeKey && cfg.stripePrice),
    async checkout(account, desiredNumber = null) {
      const back = cfg.publicUrl + "/luma-plus.html";
      const session = await call("checkout/sessions", {
        mode: "subscription",
        line_items: [{ price: cfg.stripePrice, quantity: 1 }],
        success_url: back + "?status=success",
        cancel_url: back + "?status=cancelled",
        client_reference_id: account.id,
        allow_promotion_codes: "true",
        customer: account.stripe_customer_id || undefined,
        metadata: { app: "luma", account_id: account.id, ...(desiredNumber ? { desired_number: desiredNumber } : {}) },
        subscription_data: { metadata: { app: "luma", account_id: account.id } },
      });
      return session.url;
    },
    async portal(account) {
      const session = await call("billing_portal/sessions", { customer: account.stripe_customer_id, return_url: cfg.publicUrl + "/luma-plus.html",
        configuration: cfg.portalConfig || undefined });
      return session.url;
    },
  };
}

// ----------------------------------------------------------------- service ---

// Best effort, per server instance: enough to blunt scripted sign-ups.
const recentByIp = new Map();
export function ipAllowed(key, limit, windowMs, now) {
  const hits = (recentByIp.get(key) || []).filter((t) => now - t < windowMs);
  if (recentByIp.size > 5000) recentByIp.clear();
  if (hits.length >= limit) { recentByIp.set(key, hits); return false; }
  hits.push(now);
  recentByIp.set(key, hits);
  return true;
}

export function createService({ env, db, fetch: fetchImpl, now = () => Date.now(), random = (n) => crypto.randomBytes(n),
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)), push = sendPush }) {
  const cfg = settings(env);
  const twilio = makeTwilio(cfg, fetchImpl);
  const stripe = makeStripe(cfg, fetchImpl);

  const limitFor = (account) => (isPlus(account) ? cfg.plusTexts : cfg.freeTexts);
  const isPlus = (account) => account.plan === "plus" && ["active", "trialing"].includes(account.subscription_status);

  async function authDevice(headers) {
    const match = /^Bearer\s+([0-9a-f-]{36})\.([A-Za-z0-9_-]{20,})$/.exec(headers.authorization || "");
    if (!match) throw new HttpError(401, "auth", "This Luma isn't signed in to Luma Cloud.");
    const device = await db.getDevice(match[1]);
    if (!device || device.revoked_at || !safeEqual(device.secret_hash, sha256(match[2]))) {
      throw new HttpError(401, "auth", "This Luma isn't signed in to Luma Cloud.");
    }
    const account = await db.getAccount(device.account_id);
    if (!account) throw new HttpError(401, "auth", "This Luma isn't signed in to Luma Cloud.");
    if (db.touchDevice) await db.touchDevice(device.id, new Date(now()).toISOString()).catch(() => {});
    return { device, account };
  }

  // The Luma app on the owner's phone, paired to one Luma device.
  async function authApp(headers) {
    const match = /^LumaApp\s+([0-9a-f-]{36})\.([A-Za-z0-9_-]{20,})$/.exec(headers.authorization || "");
    const unpaired = () => new HttpError(401, "unpaired", "This phone isn't connected to a Luma anymore. Pair it again from your Luma.");
    if (!match) throw unpaired();
    const link = await db.getAppLink(match[1]);
    if (!link || link.revoked_at || !safeEqual(link.secret_hash, sha256(match[2]))) throw unpaired();
    const device = await db.getDevice(link.device_id);
    if (!device || device.revoked_at) throw unpaired();
    return { link, device };
  }

  function lumaStatus(device) {
    const seen = device.last_seen_at ? Date.parse(device.last_seen_at) : 0;
    return { name: device.name || "Luma", online: now() - seen < 90_000, last_seen_at: device.last_seen_at || null };
  }

  function checkPayload(payload) {
    if (typeof payload !== "string" || !PAYLOAD.test(payload)) throw new HttpError(400, "payload", "That message couldn't be read.");
    return payload;
  }

  function waitSeconds(query) {
    const n = Number.parseInt(query.wait ?? "0", 10);
    return Number.isFinite(n) ? Math.max(0, Math.min(25, n)) : 0;
  }

  function cursorFrom(query, fallbackMs) {
    return typeof query.after === "string" && !Number.isNaN(Date.parse(query.after)) ? new Date(query.after).toISOString() : new Date(now() - fallbackMs).toISOString();
  }

  // Only hand out messages older than this, so one whose transaction commits a
  // moment late can't slip behind a reader's cursor and be skipped.
  const horizon = () => new Date(now() - 750).toISOString();

  // Hold the request open until something arrives (or the wait runs out), so
  // phones and devices hear about new messages in about a second without polling hard.
  async function longPoll(fetchRows, seconds) {
    const until = now() + seconds * 1000;
    for (;;) {
      const rows = await fetchRows();
      if (rows.length || now() >= until) return rows;
      await sleep(Math.min(1500, Math.max(0, until - now())));
    }
  }

  async function accountView(account) {
    const used = await db.usage(account.id, period(now()));
    return {
      plan: isPlus(account) ? "plus" : "free",
      subscription_status: account.subscription_status || null,
      texts_used: used,
      texts_limit: limitFor(account),
      texts_left: Math.max(0, limitFor(account) - used),
      period_ends: periodEnd(now()),
      number: isPlus(account) && account.assigned_number ? account.assigned_number : cfg.sharedNumber || null,
      dedicated_number: Boolean(isPlus(account) && account.assigned_number),
      number_pending: Boolean(isPlus(account) && !account.assigned_number && cfg.provisionNumbers),
      can_pick_number: Boolean(cfg.provisionNumbers && twilio.configured() && !account.assigned_number),
      replies: true,
      verified: Boolean(account.owner_phone),
      owner_name: account.owner_name,
      plus: { price: cfg.plusPriceLabel, texts_limit: cfg.plusTexts, available: stripe.configured() },
    };
  }

  const routes = {
    // Step 1 of sign-up: text a one-time code to the owner's own phone.
    async "verify-start"({ body }) {
      if (!cfg.verifyService || !twilio.configured()) throw new HttpError(503, "not_configured", "Luma Cloud texting isn't set up yet.");
      const phone = checkNumber(body.phone, cfg.countries);
      const name = String(body.name || "").trim().slice(0, 60);
      if (!name) throw new HttpError(400, "name", "Tell Luma your name so friends know who's texting.");
      const result = await twilio.startVerify(phone);
      if (!result.ok) throw new HttpError(502, "verify", "Couldn't send the code. Check the number and try again.");
      return { status: 200, json: { sent: true } };
    },

    // Step 2: check the code, create or reuse the account, and issue a device credential.
    // A Luma that already registered (for the phone app) keeps its credential:
    // verifying just attaches the owner's phone to it.
    async "verify-check"({ headers, body }) {
      if (!cfg.verifyService || !twilio.configured()) throw new HttpError(503, "not_configured", "Luma Cloud texting isn't set up yet.");
      const phone = checkNumber(body.phone, cfg.countries);
      const code = String(body.code || "").trim();
      if (!/^\d{4,10}$/.test(code)) throw new HttpError(400, "code", "Enter the code from the text.");
      const registered = headers.authorization ? await authDevice(headers) : null;
      const check = await twilio.checkVerify(phone, code);
      if (!check.ok || check.data.status !== "approved") throw new HttpError(403, "code", "That code didn't work. Try again or request a new one.");
      const name = String(body.name || "").trim().slice(0, 60) || "Luma owner";
      let account = await db.getAccountByPhone(phone);
      const stamp = new Date(now()).toISOString();
      if (registered) {
        if (account && account.id !== registered.account.id) {
          await db.updateDevice(registered.device.id, { account_id: account.id });
          account = await db.updateAccount(account.id, { owner_name: name, phone_verified_at: stamp });
        } else {
          account = await db.updateAccount(registered.account.id, { owner_phone: phone, owner_name: name, phone_verified_at: stamp });
        }
        return { status: 200, json: { device_token: null, linked: true, account: await accountView(account) } };
      }
      if (!account) account = await db.insertAccount({ owner_phone: phone, owner_name: name, plan: "free", phone_verified_at: stamp });
      else account = await db.updateAccount(account.id, { owner_name: name, phone_verified_at: stamp });
      const secret = random(32).toString("base64url");
      const device = await db.insertDevice({ account_id: account.id, secret_hash: sha256(secret), name: String(body.device_name || "Luma").slice(0, 60) });
      return { status: 200, json: { device_token: `${device.id}.${secret}`, account: await accountView(account) } };
    },

    async account({ headers }) {
      const { account } = await authDevice(headers);
      return { status: 200, json: await accountView(account) };
    },

    // Send one reviewed text from Luma's number. client_ref makes retries safe.
    async "sms-send"({ headers, body }) {
      const { device, account } = await authDevice(headers);
      if (!account.owner_phone) throw new HttpError(403, "verify_phone", "Verify your phone in People & Texts first, so people know who's texting.");
      if (!twilio.configured() || !(cfg.sharedNumber || cfg.messagingService)) {
        throw new HttpError(503, "not_configured", "Luma's number isn't connected yet.");
      }
      const toOwner = body.to_owner === true;
      const to = checkNumber(body.to, cfg.countries);
      if (toOwner && to !== account.owner_phone) throw new HttpError(403, "not_owner", "Luma can only answer you at your own verified number.");
      if (toOwner && !isPlus(account)) throw new HttpError(402, "plus_required", "Texting with Luma from your phone is part of Luma Plus.", { plan: "free", plus: { price: cfg.plusPriceLabel, texts_limit: cfg.plusTexts } });
      const text = cleanBody(body.body);
      const ref = String(body.client_ref || "");
      if (!/^[A-Za-z0-9_-]{6,64}$/.test(ref)) throw new HttpError(400, "client_ref", "Missing request reference.");

      const existing = await db.findMessageByRef(device.id, ref);
      if (existing) return { status: 200, json: { ...messageView(existing), duplicate: true, ...(await accountView(account)) } };
      if (!toOwner && await db.isOptedOut(to, account.id)) {
        throw new HttpError(403, "opted_out", "That person replied STOP to Luma's number, so Luma can't text them. Text them from your own phone instead.");
      }
      const since = new Date(now() - 60_000).toISOString();
      if ((await db.recentOutbound(account.id, since)) >= cfg.perMinute) {
        throw new HttpError(429, "slow_down", "That's a lot of texts at once. Give it a minute.");
      }
      const limit = limitFor(account);
      const used = await db.reserveText(account.id, period(now()), limit);
      if (used === null) {
        const plus = isPlus(account);
        let upgrade_url = null;
        if (!plus && stripe.configured() && cfg.publicUrl) upgrade_url = await stripe.checkout(account).catch(() => null);
        throw new HttpError(402, "quota", plus
          ? `You've sent all ${limit} texts included in Luma Plus this month.`
          : `You've used your ${limit} free texts from Luma's number this month.`,
          { plan: plus ? "plus" : "free", texts_limit: limit, upgrade_url, plus: { price: cfg.plusPriceLabel, texts_limit: cfg.plusTexts } });
      }

      const dedicated = isPlus(account) && account.assigned_number;
      const from = dedicated ? account.assigned_number : cfg.sharedNumber || "";
      const firstContact = !toOwner && !(await db.hasTexted(account.id, to));
      const owner = account.owner_name || "A Luma owner";
      // Recipients need to know who is texting and how to opt out. Luma answering its owner needs neither.
      let outgoing = toOwner || dedicated ? text : `${owner}: ${text}`;
      if (firstContact) outgoing += `\n\n(Sent via Luma for ${owner}. Reply STOP to opt out.)`;

      let row;
      try {
        row = await db.insertMessage({ account_id: account.id, device_id: device.id, client_ref: ref, direction: "out", to_number: to, from_number: from || null, body: text, status: "sending", kind: toOwner ? "luma" : "reply" });
      } catch (error) {
        await db.releaseText(account.id, period(now()));
        const dup = await db.findMessageByRef(device.id, ref);
        if (dup) return { status: 200, json: { ...messageView(dup), duplicate: true, ...(await accountView(account)) } };
        throw error;
      }

      let result;
      try {
        result = await twilio.send({ to, body: outgoing, from: from || undefined, statusCallback: cfg.publicUrl ? cfg.publicUrl + "/api/luma/twilio-status" : undefined });
      } catch {
        await db.updateMessage(row.id, { status: "unknown" });
        return { status: 202, json: { message_id: row.id, status: "unknown", summary: "The text may or may not have gone out. Check before sending again.", ...(await accountView(account)) } };
      }
      if (result.status >= 500) {
        await db.updateMessage(row.id, { status: "unknown" });
        return { status: 202, json: { message_id: row.id, status: "unknown", summary: "The text may or may not have gone out. Check before sending again.", ...(await accountView(account)) } };
      }
      if (!result.ok) {
        await db.releaseText(account.id, period(now()));
        const code = result.data?.code;
        if (code === 21610) await db.addOptOut(to, dedicated ? account.id : null);
        await db.updateMessage(row.id, { status: "failed", error_code: code ? String(code) : String(result.status) });
        const reason = code === 21610 ? "That person has opted out of texts from Luma's number."
          : code === 21211 || code === 21614 ? "That number can't receive texts."
          : "The carrier didn't accept that text. Nothing was sent, and it didn't count against your texts.";
        throw new HttpError(422, "rejected", reason);
      }
      const usedNumber = result.data.from || from || null; // a Messaging Service picks the pool number
      await db.updateMessage(row.id, { status: result.data.status || "queued", provider_sid: result.data.sid, from_number: usedNumber });
      return { status: 200, json: { message_id: row.id, status: result.data.status || "queued", from: usedNumber, first_contact: firstContact, ...(await accountView(account)) } };
    },

    async "sms-inbox"({ headers, query }) {
      const { account } = await authDevice(headers);
      const after = typeof query.after === "string" && !Number.isNaN(Date.parse(query.after)) ? new Date(query.after).toISOString() : new Date(now() - 7 * 86400_000).toISOString();
      const replies = await db.inbox(account.id, after);
      return { status: 200, json: { replies: replies.map((r) => ({ id: r.id, from: r.from_number, body: r.body, received_at: r.created_at, kind: r.kind || "reply" })), cursor: replies.at(-1)?.created_at || after } };
    },

    // ---- The Luma app: your Luma on your phone, from anywhere -------------

    // A Luma registers itself so a phone can pair with it. No phone number
    // needed; texting from Luma's number still requires verify-start/check.
    async "device-register"({ body, ip }) {
      if (!ipAllowed("register:" + ip, 5, 3600_000, now())) throw new HttpError(429, "slow_down", "Too many new Lumas from here. Try again in an hour.");
      const account = await db.insertAccount({ owner_phone: null, owner_name: "Luma owner", plan: "free" });
      const secret = random(32).toString("base64url");
      const device = await db.insertDevice({ account_id: account.id, secret_hash: sha256(secret), name: String(body.device_name || "Luma").trim().slice(0, 60) || "Luma" });
      return { status: 200, json: { device_token: `${device.id}.${secret}` } };
    },

    // The device opens a 10-minute pairing window. It sends only a hash of the
    // pairing secret; the secret and the encryption key stay in the QR link.
    async "app-pair-start"({ headers, body }) {
      const { device } = await authDevice(headers);
      if (typeof body.secret_hash !== "string" || !/^[0-9a-f]{64}$/.test(body.secret_hash)) throw new HttpError(400, "secret_hash", "Missing pairing secret.");
      const stamp = new Date(now()).toISOString();
      if ((await db.openPairings(device.id, stamp)) >= 5) throw new HttpError(429, "slow_down", "Use one of the pairing codes already showing, or wait a few minutes.");
      if ((await db.listAppLinks(device.id)).length >= MAX_LINKS) throw new HttpError(409, "too_many", `A Luma can connect to ${MAX_LINKS} phones. Remove one first.`);
      const pairing = await db.insertPairing({ device_id: device.id, secret_hash: body.secret_hash, expires_at: new Date(now() + 600_000).toISOString() });
      return { status: 200, json: { pair_id: pairing.id, expires_at: pairing.expires_at } };
    },

    // The phone redeems the pairing link and gets its own credential.
    async "app-pair"({ body, ip }) {
      if (!ipAllowed("pair:" + ip, 20, 600_000, now())) throw new HttpError(429, "slow_down", "Too many tries. Wait a few minutes.");
      const pairId = String(body.pair_id || "");
      const secret = String(body.secret || "");
      const expired = () => new HttpError(410, "pairing", "That pairing code expired or was already used. Make a new one on your Luma.");
      if (!UUID.test(pairId) || !/^[A-Za-z0-9_-]{20,100}$/.test(secret)) throw expired();
      const pairing = await db.getPairing(pairId);
      if (!pairing || pairing.used_at || Date.parse(pairing.expires_at) < now() || !safeEqual(pairing.secret_hash, sha256(secret))) throw expired();
      if (!(await db.usePairing(pairId, new Date(now()).toISOString()))) throw expired(); // single use, even under a race
      const device = await db.getDevice(pairing.device_id);
      if (!device || device.revoked_at) throw expired();
      const linkSecret = random(32).toString("base64url");
      const name = String(body.name || "").replace(/[\u0000-\u001F\u007F]/g, "").trim().slice(0, 40) || "Phone";
      const link = await db.insertAppLink({ device_id: device.id, pairing_id: pairId, secret_hash: sha256(linkSecret), name });
      return { status: 200, json: { app_token: `${link.id}.${linkSecret}`, link_id: link.id, luma: lumaStatus(device), push_key: vapidReady(cfg.vapid) ? cfg.vapid.publicKey : null } };
    },

    // Phone → Luma. Idempotent per client_ref, so a flaky connection can't double-send.
    async "app-send"({ headers, body }) {
      const { link, device } = await authApp(headers);
      const ref = String(body.client_ref || "");
      if (!REF.test(ref)) throw new HttpError(400, "client_ref", "Missing request reference.");
      const existing = await db.findAppMessage(link.id, ref);
      if (existing) return { status: 200, json: { id: existing.id, created_at: existing.created_at, duplicate: true, luma: lumaStatus(device) } };
      if ((await db.recentAppMessages(link.id, "up", new Date(now() - 60_000).toISOString())) >= 30) throw new HttpError(429, "slow_down", "That's a lot at once. Give Luma a second.");
      const row = await db.insertAppMessage({ device_id: device.id, link_id: link.id, direction: "up", payload: checkPayload(body.payload), client_ref: ref });
      return { status: 200, json: { id: row.id, created_at: row.created_at, luma: lumaStatus(device) } };
    },

    // Luma → phone, read by the phone. ?wait=25 holds until something arrives.
    async "app-thread"({ headers, query }) {
      const { link, device } = await authApp(headers);
      await db.touchAppLink(link.id, new Date(now()).toISOString()).catch(() => {});
      const after = cursorFrom(query, 7 * 86400_000);
      const rows = await longPoll(() => db.appMessagesForLink(link.id, after, horizon()), waitSeconds(query));
      const fresh = rows.length ? device : (await db.getDevice(device.id)) || device;
      return { status: 200, json: { messages: rows.map((r) => ({ id: r.id, payload: r.payload, created_at: r.created_at })), cursor: rows.at(-1)?.created_at || after, luma: lumaStatus(fresh) } };
    },

    // The phone's Web Push subscription, so Luma can reach it when the app is closed.
    async "app-push"({ headers, body }) {
      const { link } = await authApp(headers);
      const sub = body.subscription;
      if (sub === null) { await db.updateAppLink(link.id, { push_subscription: null }); return { status: 200, json: { push: false } }; }
      const endpoint = String(sub?.endpoint || "");
      if (!/^https:\/\/[^\s]{10,900}$/.test(endpoint) || typeof sub?.keys?.p256dh !== "string" || typeof sub?.keys?.auth !== "string" || sub.keys.p256dh.length > 200 || sub.keys.auth.length > 64) {
        throw new HttpError(400, "subscription", "That notification setup didn't look right.");
      }
      await db.updateAppLink(link.id, { push_subscription: { endpoint, keys: { p256dh: sub.keys.p256dh, auth: sub.keys.auth } } });
      return { status: 200, json: { push: true } };
    },

    // A phone leaves (from the phone), or the owner removes it (from the Luma).
    async "app-unpair"({ headers, body }) {
      if (/^LumaApp\s/.test(headers.authorization || "")) {
        const { link } = await authApp(headers);
        await db.updateAppLink(link.id, { revoked_at: new Date(now()).toISOString(), push_subscription: null });
        return { status: 200, json: { removed: link.id } };
      }
      const { device } = await authDevice(headers);
      const link = UUID.test(String(body.link_id || "")) ? await db.getAppLink(body.link_id) : null;
      if (!link || link.device_id !== device.id) throw new HttpError(404, "not_found", "That phone isn't connected.");
      await db.updateAppLink(link.id, { revoked_at: new Date(now()).toISOString(), push_subscription: null });
      return { status: 200, json: { removed: link.id } };
    },

    // What phones said to this Luma, plus which phones are connected. ?wait=25 holds.
    async "app-inbox"({ headers, query }) {
      const { device } = await authDevice(headers);
      const after = cursorFrom(query, 86400_000);
      const rows = await longPoll(() => db.appMessagesForDevice(device.id, after, horizon()), waitSeconds(query));
      const links = await db.listAppLinks(device.id);
      if (random(1)[0] < 8) await db.pruneAppMessages(device.id, new Date(now() - APP_RETENTION_DAYS * 86400_000).toISOString()).catch(() => {});
      return { status: 200, json: {
        messages: rows.map((r) => ({ id: r.id, link_id: r.link_id, payload: r.payload, created_at: r.created_at })),
        cursor: rows.at(-1)?.created_at || after,
        links: links.map((l) => ({ id: l.id, pairing_id: l.pairing_id, name: l.name, created_at: l.created_at, last_seen_at: l.last_seen_at || null, push: Boolean(l.push_subscription) })),
      } };
    },

    // Luma → phone(s). Each message is encrypted for one phone's key.
    // notify: true also wakes the phone with a notification if the app isn't open.
    async "app-reply"({ headers, body }) {
      const { device } = await authDevice(headers);
      const items = Array.isArray(body.messages) ? body.messages : [];
      if (!items.length || items.length > 10) throw new HttpError(400, "messages", "Send between 1 and 10 messages.");
      const links = new Map((await db.listAppLinks(device.id)).map((l) => [l.id, l]));
      const results = [];
      for (const item of items) {
        const link = links.get(String(item?.link_id || ""));
        if (!link) { results.push({ link_id: item?.link_id || null, error: "not_connected" }); continue; }
        const ref = String(item.client_ref || "");
        if (!REF.test(ref)) throw new HttpError(400, "client_ref", "Missing request reference.");
        const payload = checkPayload(item.payload);
        let row = await db.findAppMessage(link.id, ref);
        const duplicate = Boolean(row);
        if (!row) row = await db.insertAppMessage({ device_id: device.id, link_id: link.id, direction: "down", payload, client_ref: ref });
        let pushed = null;
        const appOpen = link.last_seen_at && now() - Date.parse(link.last_seen_at) < 30_000;
        if (!duplicate && item.notify === true && link.push_subscription && !appOpen && vapidReady(cfg.vapid)) {
          pushed = await push(link.push_subscription, { id: row.id, payload: payload.length <= 3000 ? payload : null }, cfg.vapid, { fetch: fetchImpl, now: now() });
          if (pushed === "gone") await db.updateAppLink(link.id, { push_subscription: null }).catch(() => {});
        }
        results.push({ link_id: link.id, id: row.id, duplicate, pushed });
      }
      return { status: 200, json: { results } };
    },

    async "app-config"() {
      return { status: 200, json: { push_key: vapidReady(cfg.vapid) ? cfg.vapid.publicKey : null } };
    },

    // A few real, available local numbers to choose from before upgrading.
    async "number-options"({ headers, query }) {
      const { account } = await authDevice(headers);
      if (!cfg.provisionNumbers || !twilio.configured()) throw new HttpError(503, "not_configured", "Picking a number isn't available yet.");
      const area = String(query.area_code || /^\+1(\d{3})/.exec(account.owner_phone || "")?.[1] || "").replace(/\D/g, "");
      if (area && !/^[2-9]\d{2}$/.test(area)) throw new HttpError(400, "area_code", "Use a 3-digit US area code, like 919.");
      let numbers = await twilio.searchNumbers(area, 5);
      const nearby = !numbers.length && area;
      if (nearby) numbers = await twilio.searchNumbers("", 5);
      return { status: 200, json: { area_code: area || null, numbers, note: nearby ? `Nothing free in ${area} right now, so here are some others.` : null } };
    },

    async "billing-checkout"({ headers, body }) {
      const { account } = await authDevice(headers);
      if (!account.owner_phone) throw new HttpError(403, "verify_phone", "Verify your phone in People & Texts first.");
      if (!stripe.configured() || !cfg.publicUrl) throw new HttpError(503, "not_configured", "Luma Plus checkout isn't set up yet.");
      if (isPlus(account)) throw new HttpError(409, "already_plus", "You already have Luma Plus.");
      const desired = body?.number ? checkNumber(body.number, ["1"]) : null;
      return { status: 200, json: { url: await stripe.checkout(account, desired) } };
    },

    // A Plus member without a number yet (or whose pick was taken) chooses one now.
    async "number-claim"({ headers, body }) {
      const { account } = await authDevice(headers);
      if (!isPlus(account)) throw new HttpError(402, "plus_required", "Your own Luma number comes with Luma Plus.");
      if (account.assigned_number) throw new HttpError(409, "has_number", "You already have a Luma number.");
      if (!cfg.provisionNumbers || !twilio.configured() || !cfg.publicUrl) throw new HttpError(503, "not_configured", "Picking a number isn't available yet.");
      const desired = body?.number ? checkNumber(body.number, ["1"]) : null;
      const bought = await twilio.buyNumber(desired, account.owner_phone, cfg.publicUrl + "/api/luma/twilio-inbound");
      if (!bought) throw new HttpError(502, "number", "Couldn't get that number. Pick another one.");
      const updated = await db.updateAccount(account.id, { assigned_number: bought.number, assigned_number_sid: bought.sid });
      return { status: 200, json: await accountView(updated) };
    },

    // What's configured (never the values), so setup can be checked from a browser.
    async health() {
      let database = false;
      try { await db.getAccount("00000000-0000-0000-0000-000000000000"); database = true; } catch { database = false; }
      const checks = {
        public_url: Boolean(cfg.publicUrl), database,
        twilio: twilio.configured(), phone_verification: Boolean(cfg.verifyService),
        sending_number: Boolean(cfg.sharedNumber || cfg.messagingService), messaging_service: Boolean(cfg.messagingService),
        stripe: stripe.configured(), stripe_webhook: Boolean(cfg.stripeWebhookSecret), numbers_for_plus: cfg.provisionNumbers,
      };
      // The phone app needs only the database; notifications need the VAPID keys.
      const app = { pairing: database, notifications: vapidReady(cfg.vapid) };
      return { status: 200, json: { ready: Object.values(checks).every(Boolean), checks, app } };
    },

    async "billing-portal"({ headers }) {
      const { account } = await authDevice(headers);
      if (!account.stripe_customer_id || !stripe.configured()) throw new HttpError(404, "no_billing", "There's no Luma Plus subscription to manage yet.");
      return { status: 200, json: { url: await stripe.portal(account) } };
    },

    // Stripe tells us when someone subscribes, renews, fails to pay or cancels.
    async "stripe-webhook"({ headers, raw }) {
      if (!stripeSignatureValid(cfg.stripeWebhookSecret, headers["stripe-signature"], raw, Math.floor(now() / 1000))) {
        throw new HttpError(400, "signature", "Invalid signature.");
      }
      const event = JSON.parse(raw);
      if (!(await db.recordEvent(event.id))) return { status: 200, json: { received: true, duplicate: true } };
      const object = event.data?.object || {};
      const accountId = object.metadata?.account_id || object.client_reference_id || null;
      if (object.metadata?.app && object.metadata.app !== "luma") return { status: 200, json: { received: true, ignored: true } };
      let account = accountId ? await db.getAccount(accountId) : null;
      if (!account && object.customer) account = await db.getAccountByCustomer(object.customer);
      if (!account) return { status: 200, json: { received: true, ignored: true } };

      if (event.type === "checkout.session.completed" && object.mode === "subscription") {
        account = await db.updateAccount(account.id, { plan: "plus", subscription_status: "active", stripe_customer_id: object.customer, stripe_subscription_id: object.subscription });
        if (cfg.provisionNumbers && !account.assigned_number && twilio.configured() && cfg.publicUrl) {
          const bought = await twilio.buyNumber(object.metadata?.desired_number || null, account.owner_phone, cfg.publicUrl + "/api/luma/twilio-inbound").catch(() => null);
          if (bought) await db.updateAccount(account.id, { assigned_number: bought.number, assigned_number_sid: bought.sid });
        }
      } else if (event.type === "customer.subscription.updated" || event.type === "customer.subscription.created") {
        const active = ["active", "trialing"].includes(object.status);
        await db.updateAccount(account.id, { plan: active ? "plus" : "free", subscription_status: object.status, stripe_subscription_id: object.id });
      } else if (event.type === "customer.subscription.deleted") {
        await db.updateAccount(account.id, { plan: "free", subscription_status: "canceled" });
        if (cfg.releaseNumbers && account.assigned_number_sid) {
          await twilio.releaseNumber(account.assigned_number_sid).catch(() => null);
          await db.updateAccount(account.id, { assigned_number: null, assigned_number_sid: null });
        }
      } else if (event.type === "invoice.payment_failed") {
        await db.updateAccount(account.id, { subscription_status: "past_due" });
      }
      return { status: 200, json: { received: true } };
    },

    // Someone texted Luma's number back: a reply, or STOP/HELP.
    async "twilio-inbound"({ headers, form }) {
      verifyTwilio(headers, form, "/api/luma/twilio-inbound");
      const from = String(form.From || "");
      const to = String(form.To || "");
      const body = String(form.Body || "").slice(0, 1600);
      const word = firstWord(body);
      const owner = await db.getAccountByNumber(to);
      if (STOP_WORDS.has(word)) {
        await db.addOptOut(from, owner ? owner.id : null);
        return { status: 200, twiml: "" };
      }
      if (START_WORDS.has(word)) {
        await db.removeOptOut(from, owner ? owner.id : null);
        return { status: 200, twiml: "" };
      }
      if (HELP_WORDS.has(word)) {
        return { status: 200, twiml: "Luma sends texts for people who use the Luma home companion. Reply STOP to stop texts from this number." };
      }
      // The owner texting their own Luma is a conversation, unless they're answering
      // another Luma owner who texted them from the shared number.
      const self = await db.getAccountByPhone(from);
      const repliedTo = owner ? null : await db.lastSenderTo(from, to);
      const ownsThisNumber = self && (owner ? owner.id === self.id : to === cfg.sharedNumber || !cfg.sharedNumber);
      if (self && ownsThisNumber && (!repliedTo || repliedTo.id === self.id)) {
        if (!isPlus(self)) {
          return { status: 200, twiml: `Texting with your Luma is part of Luma Plus (${cfg.plusPriceLabel}). Upgrade from People & Texts in the Luma app.` };
        }
        await db.insertMessage({ account_id: self.id, direction: "in", from_number: from, to_number: to, body, status: "received", provider_sid: form.MessageSid || null, kind: "owner" });
        return { status: 200, twiml: "" };
      }
      const account = owner || repliedTo;
      if (account) await db.insertMessage({ account_id: account.id, direction: "in", from_number: from, to_number: to, body, status: "received", provider_sid: form.MessageSid || null, kind: "reply" });
      return { status: 200, twiml: "" };
    },

    async "twilio-status"({ headers, form }) {
      verifyTwilio(headers, form, "/api/luma/twilio-status");
      if (form.MessageSid && form.MessageStatus) {
        await db.updateMessageBySid(String(form.MessageSid), { status: String(form.MessageStatus).slice(0, 20), error_code: form.ErrorCode ? String(form.ErrorCode) : null });
      }
      return { status: 200, twiml: "" };
    },
  };

  function verifyTwilio(headers, form, path) {
    if (!cfg.twilioToken || !cfg.publicUrl) throw new HttpError(503, "not_configured", "Not configured.");
    const expected = twilioSignature(cfg.twilioToken, cfg.publicUrl + path, form);
    if (!safeEqual(expected, headers["x-twilio-signature"] || "")) throw new HttpError(403, "signature", "Invalid signature.");
  }

  function messageView(row) {
    return { message_id: row.id, status: row.status, from: row.from_number || null };
  }

  return { routes, settings: cfg };
}

// ------------------------------------------------------------ HTTP wrapper ---

async function readRaw(req) {
  if (typeof req.rawBody === "string") return req.rawBody;
  if (Buffer.isBuffer(req.rawBody)) return req.rawBody.toString("utf8");
  if (req.readable !== false && typeof req[Symbol.asyncIterator] === "function") {
    const chunks = [];
    let size = 0;
    for await (const chunk of req) {
      size += chunk.length;
      if (size > 64_000) throw new HttpError(413, "too_large", "Request too large.");
      chunks.push(Buffer.from(chunk));
    }
    return Buffer.concat(chunks).toString("utf8");
  }
  return typeof req.body === "string" ? req.body : JSON.stringify(req.body || {});
}

export function createHandler(makeDeps) {
  return async function handler(req, res) {
    const route = String(req.query?.route || "");
    const reply = (status, payload, xml = false) => {
      res.statusCode = status;
      res.setHeader("Cache-Control", "no-store");
      if (xml) {
        res.setHeader("Content-Type", "text/xml");
        const message = payload ? `<Message>${payload.replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" })[c])}</Message>` : "";
        res.end(`<?xml version="1.0" encoding="UTF-8"?><Response>${message}</Response>`);
      } else {
        res.setHeader("Content-Type", "application/json");
        res.end(JSON.stringify(payload));
      }
    };
    try {
      const { routes } = createService(makeDeps());
      const run = routes[route];
      const getRoutes = new Set(["account", "sms-inbox", "number-options", "health", "app-thread", "app-inbox", "app-config"]);
      if (!run) return reply(404, { error: "not_found" });
      if (getRoutes.has(route) ? req.method !== "GET" : req.method !== "POST") return reply(405, { error: "method" });
      const headers = Object.fromEntries(Object.entries(req.headers || {}).map(([k, v]) => [k.toLowerCase(), Array.isArray(v) ? v[0] : v]));
      const raw = req.method === "POST" ? await readRaw(req) : "";
      const contentType = headers["content-type"] || "";
      let body = {};
      let form = {};
      if (contentType.includes("application/x-www-form-urlencoded")) form = Object.fromEntries(new URLSearchParams(raw));
      else if (raw && route !== "stripe-webhook") {
        try { body = JSON.parse(raw); } catch { return reply(400, { error: "bad_json" }); }
        if (!body || typeof body !== "object" || Array.isArray(body)) return reply(400, { error: "bad_json" });
      }
      const ip = String(headers["x-forwarded-for"] || req.socket?.remoteAddress || "").split(",")[0].trim();
      const result = await run({ headers, body, form, raw, query: req.query || {}, ip });
      if ("twiml" in result) return reply(result.status, result.twiml, true);
      return reply(result.status, result.json);
    } catch (error) {
      if (error instanceof HttpError) return reply(error.status, { error: error.code, message: error.message, ...error.extra });
      if (error?.notConfigured) return reply(503, { error: "not_configured", message: "Luma Cloud isn't set up yet." });
      console.error("luma-cloud", route, error?.message);
      return reply(500, { error: "server", message: "Luma Cloud hit a problem. Nothing was charged." });
    }
  };
}
