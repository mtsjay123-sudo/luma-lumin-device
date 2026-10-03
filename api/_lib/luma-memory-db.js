// In-memory stand-in for the Supabase tables, for tests and the local dev relay.
import crypto from "node:crypto";

export function memoryDb(clock = null) {
  const t = { accounts: [], devices: [], messages: [], usage: new Map(), optouts: [], events: new Set() };
  const id = () => crypto.randomUUID();
  // Strictly increasing timestamps, so "replies after <cursor>" behaves like Postgres.
  let last = 0;
  const at = () => {
    last = Math.max(last + 1, clock ? clock() : Date.UTC(2026, 9, 3, 12));
    return new Date(last).toISOString();
  };
  return {
    t,
    getDevice: async (x) => t.devices.find((d) => d.id === x) || null,
    touchDevice: async () => {},
    insertDevice: async (row) => { const d = { id: id(), revoked_at: null, ...row }; t.devices.push(d); return d; },
    getAccount: async (x) => t.accounts.find((a) => a.id === x) || null,
    getAccountByPhone: async (p) => t.accounts.find((a) => a.owner_phone === p) || null,
    getAccountByCustomer: async (c) => t.accounts.find((a) => a.stripe_customer_id === c) || null,
    getAccountByNumber: async (n) => t.accounts.find((a) => a.assigned_number === n) || null,
    insertAccount: async (row) => { const a = { id: id(), plan: "free", subscription_status: null, assigned_number: null, ...row }; t.accounts.push(a); return a; },
    updateAccount: async (x, patch) => { const a = t.accounts.find((r) => r.id === x); Object.assign(a, patch); return a; },
    usage: async (a, p) => t.usage.get(a + p) || 0,
    reserveText: async (a, p, limit) => { const n = t.usage.get(a + p) || 0; if (n >= limit) return null; t.usage.set(a + p, n + 1); return n + 1; },
    releaseText: async (a, p) => { const n = t.usage.get(a + p) || 0; if (n > 0) t.usage.set(a + p, n - 1); },
    findMessageByRef: async (d, r) => t.messages.find((m) => m.device_id === d && m.client_ref === r) || null,
    insertMessage: async (row) => {
      if (row.client_ref && t.messages.some((m) => m.device_id === row.device_id && m.client_ref === row.client_ref)) throw Object.assign(new Error("dup"), { status: 409 });
      const m = { id: id(), created_at: at(), ...row }; t.messages.push(m); return m;
    },
    updateMessage: async (x, patch) => Object.assign(t.messages.find((m) => m.id === x), patch),
    updateMessageBySid: async (sid, patch) => { const m = t.messages.find((r) => r.provider_sid === sid); return m ? Object.assign(m, patch) : null; },
    recentOutbound: async (a) => t.messages.filter((m) => m.account_id === a && m.direction === "out").length,
    hasTexted: async (a, n) => t.messages.some((m) => m.account_id === a && m.direction === "out" && m.to_number === n && m.status !== "failed"),
    isOptedOut: async (n, a) => t.optouts.some((o) => o.number === n && (o.account_id === null || o.account_id === a)),
    addOptOut: async (n, a) => { if (!t.optouts.some((o) => o.number === n && o.account_id === a)) t.optouts.push({ number: n, account_id: a }); },
    removeOptOut: async (n, a) => { t.optouts = t.optouts.filter((o) => !(o.number === n && o.account_id === a)); },
    inbox: async (a, after) => t.messages.filter((m) => m.account_id === a && m.direction === "in" && m.created_at > after),
    lastSenderTo: async (n, via) => { const m = [...t.messages].reverse().find((r) => r.direction === "out" && r.to_number === n && r.from_number === via); return m ? { id: m.account_id } : null; },
    recordEvent: async (e) => (t.events.has(e) ? false : (t.events.add(e), true)),
  };
}

