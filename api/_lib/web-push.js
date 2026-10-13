// Web Push for the Luma app (RFC 8291 message encryption, RFC 8292 VAPID).
//
// Luma Cloud only ever forwards the device's end-to-end encrypted payload, so
// the push service sees ciphertext inside ciphertext. Node's crypto is enough;
// no dependency.
import crypto from "node:crypto";

const b64url = (buf) => Buffer.from(buf).toString("base64url");
const unb64url = (text) => Buffer.from(String(text || ""), "base64url");

// VAPID keys are a P-256 pair: the public key as an uncompressed point
// (65 bytes) and the private scalar (32 bytes), both base64url.
export function generateVapidKeys() {
  const ecdh = crypto.createECDH("prime256v1");
  ecdh.generateKeys();
  return { publicKey: b64url(ecdh.getPublicKey()), privateKey: b64url(ecdh.getPrivateKey()) };
}

export function vapidReady(vapid) {
  return unb64url(vapid?.publicKey).length === 65 && unb64url(vapid?.privateKey).length === 32 && /^(mailto:|https:)/.test(vapid?.subject || "");
}

function privateKeyObject(vapid) {
  const pub = unb64url(vapid.publicKey);
  return crypto.createPrivateKey({
    key: { kty: "EC", crv: "P-256", d: vapid.privateKey, x: b64url(pub.subarray(1, 33)), y: b64url(pub.subarray(33, 65)) },
    format: "jwk",
  });
}

export function vapidAuthorization(endpoint, vapid, nowSeconds) {
  const audience = new URL(endpoint).origin;
  const header = b64url(JSON.stringify({ typ: "JWT", alg: "ES256" }));
  const claims = b64url(JSON.stringify({ aud: audience, exp: nowSeconds + 12 * 3600, sub: vapid.subject }));
  const signature = crypto.sign("sha256", Buffer.from(`${header}.${claims}`), { key: privateKeyObject(vapid), dsaEncoding: "ieee-p1363" });
  return `vapid t=${header}.${claims}.${b64url(signature)}, k=${vapid.publicKey}`;
}

// One aes128gcm record, as RFC 8291 describes.
export function encryptPayload(subscription, plaintext, { salt = crypto.randomBytes(16), ecdh = null } = {}) {
  const receiver = unb64url(subscription?.keys?.p256dh);
  const authSecret = unb64url(subscription?.keys?.auth);
  if (receiver.length !== 65 || authSecret.length !== 16) throw new Error("bad subscription keys");
  const sender = ecdh || crypto.createECDH("prime256v1");
  if (!ecdh) sender.generateKeys();
  const senderPublic = sender.getPublicKey();
  const shared = sender.computeSecret(receiver);
  const keyInfo = Buffer.concat([Buffer.from("WebPush: info\0"), receiver, senderPublic]);
  const ikm = Buffer.from(crypto.hkdfSync("sha256", shared, authSecret, keyInfo, 32));
  const cek = Buffer.from(crypto.hkdfSync("sha256", ikm, salt, Buffer.from("Content-Encoding: aes128gcm\0"), 16));
  const nonce = Buffer.from(crypto.hkdfSync("sha256", ikm, salt, Buffer.from("Content-Encoding: nonce\0"), 12));
  const cipher = crypto.createCipheriv("aes-128-gcm", cek, nonce);
  const body = Buffer.concat([cipher.update(Buffer.concat([Buffer.from(plaintext), Buffer.from([2])])), cipher.final(), cipher.getAuthTag()]);
  const recordSize = Buffer.alloc(4);
  recordSize.writeUInt32BE(4096);
  return Buffer.concat([salt, recordSize, Buffer.from([senderPublic.length]), senderPublic, body]);
}

// Returns "sent", "gone" (the phone unsubscribed; forget it) or "failed".
export async function sendPush(subscription, payload, vapid, { fetch: fetchImpl = fetch, now = Date.now(), ttl = 86400 } = {}) {
  if (!vapidReady(vapid) || !/^https:\/\//.test(subscription?.endpoint || "")) return "failed";
  let body;
  try { body = encryptPayload(subscription, Buffer.from(JSON.stringify(payload))); } catch { return "failed"; }
  try {
    const response = await fetchImpl(subscription.endpoint, {
      method: "POST",
      headers: {
        Authorization: vapidAuthorization(subscription.endpoint, vapid, Math.floor(now / 1000)),
        "Content-Encoding": "aes128gcm",
        "Content-Type": "application/octet-stream",
        TTL: String(ttl),
        Urgency: "high",
      },
      body,
      signal: AbortSignal.timeout(4000),
    });
    if (response.status === 404 || response.status === 410) return "gone";
    return response.ok ? "sent" : "failed";
  } catch {
    return "failed";
  }
}
