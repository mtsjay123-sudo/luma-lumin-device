// In-memory stand-in for the Supabase tables, for tests and the local dev relay.
import crypto from "node:crypto";

export function memoryDb(clock = null) {
  const t = { accounts: [], devices: [], messages: [], usage: new Map(), optouts: [], events: new Set(), pairings: [], links: [], appMessages: [] };
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
    touchDevice: async (x, when) => { const d = t.devices.find((r) => r.id === x); if (d) d.last_seen_at = when; },
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
      const m = { id: id(), created_at: at(), kind: "reply", ...row }; t.messages.push(m); return m;
    },
    updateMessage: async (x, patch) => Object.assign(t.messages.find((m) => m.id === x), patch),
    updateMessageBySid: async (sid, patch) => { const m = t.messages.find((r) => r.provider_sid === sid); return m ? Object.assign(m, patch) : null; },
    recentOutbound: async (a) => t.messages.filter((m) => m.account_id === a && m.direction === "out").length,
    hasTexted: async (a, n) => t.messages.some((m) => m.account_id === a && m.direction === "out" && m.kind === "reply" && m.to_number === n && m.status !== "failed"),
    isOptedOut: async (n, a) => t.optouts.some((o) => o.number === n && (o.account_id === null || o.account_id === a)),
    addOptOut: async (n, a) => { if (!t.optouts.some((o) => o.number === n && o.account_id === a)) t.optouts.push({ number: n, account_id: a }); },
    removeOptOut: async (n, a) => { t.optouts = t.optouts.filter((o) => !(o.number === n && o.account_id === a)); },
    inbox: async (a, after) => t.messages.filter((m) => m.account_id === a && m.direction === "in" && m.created_at > after),
    lastSenderTo: async (n, via) => { const m = [...t.messages].reverse().find((r) => r.direction === "out" && r.kind === "reply" && r.to_number === n && (r.from_number === via || r.from_number === null)); return m ? { id: m.account_id } : null; },
    recordEvent: async (e) => (t.events.has(e) ? false : (t.events.add(e), true)),
    updateDevice: async (x, patch) => Object.assign(t.devices.find((d) => d.id === x), patch),
    insertPairing: async (row) => { const p = { id: id(), used_at: null, created_at: at(), ...row }; t.pairings.push(p); return p; },
    getPairing: async (x) => t.pairings.find((p) => p.id === x) || null,
    usePairing: async (x, when) => { const p = t.pairings.find((r) => r.id === x && !r.used_at); if (!p) return null; p.used_at = when; return p; },
    openPairings: async (d, nowIso) => t.pairings.filter((p) => p.device_id === d && !p.used_at && p.expires_at > nowIso).length,
    insertAppLink: async (row) => { const l = { id: id(), created_at: at(), last_seen_at: null, revoked_at: null, push_subscription: null, ...row }; t.links.push(l); return l; },
    getAppLink: async (x) => t.links.find((l) => l.id === x) || null,
    updateAppLink: async (x, patch) => Object.assign(t.links.find((l) => l.id === x), patch),
    touchAppLink: async (x, when) => { const l = t.links.find((r) => r.id === x); if (l) l.last_seen_at = when; },
    listAppLinks: async (d) => t.links.filter((l) => l.device_id === d && !l.revoked_at),
    insertAppMessage: async (row) => {
      const dup = t.appMessages.find((m) => m.link_id === row.link_id && m.client_ref === row.client_ref);
      if (dup) return dup;
      const m = { id: id(), created_at: at(), ...row }; t.appMessages.push(m); return m;
    },
    findAppMessage: async (l, ref) => t.appMessages.find((m) => m.link_id === l && m.client_ref === ref) || null,
    recentAppMessages: async (l, dir, since) => t.appMessages.filter((m) => m.link_id === l && m.direction === dir && m.created_at >= since).length,
    appMessagesForLink: async (l, after, before) => t.appMessages.filter((m) => m.link_id === l && m.direction === "down" && m.created_at > after && m.created_at <= before).slice(0, 50),
    appMessagesForDevice: async (d, after, before) => t.appMessages.filter((m) => m.device_id === d && m.direction === "up" && m.created_at > after && m.created_at <= before).slice(0, 50),
    pruneAppMessages: async (d, before) => { t.appMessages = t.appMessages.filter((m) => !(m.device_id === d && m.created_at < before)); },
  };
}

