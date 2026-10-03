// Server-side admin check for the waitlist tools. The token lives only in Vercel
// env (LUMA_ADMIN_TOKEN); the browser sends it as a Bearer header.
import crypto from "node:crypto";

export function isAdmin(req, env = process.env) {
  const expected = env.LUMA_ADMIN_TOKEN || "";
  const header = String(req.headers?.authorization || "");
  const given = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (expected.length < 16 || !given) return false;
  const a = crypto.createHash("sha256").update(given).digest();
  const b = crypto.createHash("sha256").update(expected).digest();
  return crypto.timingSafeEqual(a, b);
}
