// Luma Cloud: Luma's own texting number, monthly quotas and Luma Plus billing.
//
// One Vercel function (api/luma/[route].js) serves every route below. All state
// lives in Supabase tables that only the service role can touch (see
// supabase/migrations). Twilio sends and receives the texts; Stripe bills Luma
// Plus. Dependencies are injected so the whole flow runs in tests without a
// network.
//
// Device routes authenticate with "Authorization: Bearer <device_id>.<secret>".
// Webhook routes authenticate with the provider's signature.
import crypto from "node:crypto";

const STOP_WORDS = new Set(["STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT", "REVOKE", "OPTOUT"]);
const START_WORDS = new Set(["START", "UNSTOP", "OPTIN"]);
const HELP_WORDS = new Set(["HELP", "INFO"]);
const E164 = /^\+[1-9]\d{7,14}$/;
const NANP = /^\+1[2-9]\d{2}[2-9]\d{6}$/;
const MAX_BODY = 640; // four SMS segments at most

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
    async buyNumberNear(phone, smsUrl) {
      const area = /^\+1(\d{3})/.exec(phone)?.[1];
      const search = await call("GET", `${base}/AvailablePhoneNumbers/US/Local.json?SmsEnabled=true&PageSize=1${area ? "&AreaCode=" + area : ""}`);
      let candidate = search.ok ? search.data.available_phone_numbers?.[0] : null;
      if (!candidate && area) {
        const any = await call("GET", `${base}/AvailablePhoneNumbers/US/Local.json?SmsEnabled=true&PageSize=1`);
        candidate = any.ok ? any.data.available_phone_numbers?.[0] : null;
      }
      if (!candidate) return null;
      const bought = await call("POST", `${base}/IncomingPhoneNumbers.json`, { PhoneNumber: candidate.phone_number, SmsUrl: smsUrl, SmsMethod: "POST" });
      if (!bought.ok) return null;
      if (cfg.messagingService) {
        await call("POST", `https://messaging.twilio.com/v1/Services/${cfg.messagingService}/PhoneNumbers`, { PhoneNumberSid: bought.data.sid });
      }
      return { number: bought.data.phone_number, sid: bought.data.sid };
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
    async checkout(account) {
      const back = cfg.publicUrl + "/luma-plus.html";
      const session = await call("checkout/sessions", {
        mode: "subscription",
        line_items: [{ price: cfg.stripePrice, quantity: 1 }],
        success_url: back + "?status=success",
        cancel_url: back + "?status=cancelled",
        client_reference_id: account.id,
        allow_promotion_codes: "true",
        customer: account.stripe_customer_id || undefined,
        metadata: { app: "luma", account_id: account.id },
        subscription_data: { metadata: { app: "luma", account_id: account.id } },
      });
      return session.url;
    },
    async portal(account) {
      const session = await call("billing_portal/sessions", { customer: account.stripe_customer_id, return_url: cfg.publicUrl + "/luma-plus.html" });
      return session.url;
    },
  };
}

// ----------------------------------------------------------------- service ---

export function createService({ env, db, fetch: fetchImpl, now = () => Date.now(), random = (n) => crypto.randomBytes(n) }) {
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
      replies: true,
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
    async "verify-check"({ body }) {
      if (!cfg.verifyService || !twilio.configured()) throw new HttpError(503, "not_configured", "Luma Cloud texting isn't set up yet.");
      const phone = checkNumber(body.phone, cfg.countries);
      const code = String(body.code || "").trim();
      if (!/^\d{4,10}$/.test(code)) throw new HttpError(400, "code", "Enter the code from the text.");
      const check = await twilio.checkVerify(phone, code);
      if (!check.ok || check.data.status !== "approved") throw new HttpError(403, "code", "That code didn't work. Try again or request a new one.");
      const name = String(body.name || "").trim().slice(0, 60) || "Luma owner";
      let account = await db.getAccountByPhone(phone);
      const stamp = new Date(now()).toISOString();
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

    async "billing-checkout"({ headers }) {
      const { account } = await authDevice(headers);
      if (!stripe.configured() || !cfg.publicUrl) throw new HttpError(503, "not_configured", "Luma Plus checkout isn't set up yet.");
      if (isPlus(account)) throw new HttpError(409, "already_plus", "You already have Luma Plus.");
      return { status: 200, json: { url: await stripe.checkout(account) } };
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
          const bought = await twilio.buyNumberNear(account.owner_phone, cfg.publicUrl + "/api/luma/twilio-inbound").catch(() => null);
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
      const getRoutes = new Set(["account", "sms-inbox"]);
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
      const result = await run({ headers, body, form, raw, query: req.query || {} });
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
