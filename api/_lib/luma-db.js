// Supabase (PostgREST) storage for Luma Cloud. Server-side only: it uses the
// service-role key, which must never reach a browser or a Luma device.

export function makeSupabaseDb(env, fetchImpl) {
  const base = (env.SUPABASE_URL || "").replace(/\/+$/, "");
  const key = env.SUPABASE_SERVICE_ROLE_KEY || "";
  if (!base || !key) {
    return new Proxy({}, { get: () => async () => { throw Object.assign(new Error("Supabase is not configured"), { notConfigured: true }); } });
  }
  const headers = { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json" };
  const enc = encodeURIComponent;

  async function request(method, path, body, prefer) {
    const response = await fetchImpl(`${base}/rest/v1/${path}`, {
      method,
      headers: { ...headers, ...(prefer ? { Prefer: prefer } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      const error = new Error(`Supabase ${method} ${path.split("?")[0]} failed (${response.status})`);
      error.status = response.status;
      error.code = data?.code;
      throw error;
    }
    return data;
  }
  const one = async (path) => (await request("GET", path + "&limit=1"))?.[0] || null;
  const insert = async (table, row) => (await request("POST", table, row, "return=representation"))[0];
  const update = async (table, filter, patch) => (await request("PATCH", `${table}?${filter}`, patch, "return=representation"))[0] || null;

  return {
    getDevice: (id) => one(`luma_devices?id=eq.${enc(id)}&select=*`),
    touchDevice: (id, at) => request("PATCH", `luma_devices?id=eq.${enc(id)}`, { last_seen_at: at }),
    insertDevice: (row) => insert("luma_devices", row),
    getAccount: (id) => one(`luma_accounts?id=eq.${enc(id)}&select=*`),
    getAccountByPhone: (phone) => one(`luma_accounts?owner_phone=eq.${enc(phone)}&select=*`),
    getAccountByCustomer: (customer) => one(`luma_accounts?stripe_customer_id=eq.${enc(customer)}&select=*`),
    getAccountByNumber: (number) => one(`luma_accounts?assigned_number=eq.${enc(number)}&select=*`),
    insertAccount: (row) => insert("luma_accounts", row),
    updateAccount: (id, patch) => update("luma_accounts", `id=eq.${enc(id)}`, patch),
    async usage(accountId, period) {
      const row = await one(`luma_usage?account_id=eq.${enc(accountId)}&period=eq.${enc(period)}&select=texts_sent`);
      return row ? row.texts_sent : 0;
    },
    reserveText: (accountId, period, limit) => request("POST", "rpc/luma_reserve_text", { p_account: accountId, p_period: period, p_limit: limit }),
    releaseText: (accountId, period) => request("POST", "rpc/luma_release_text", { p_account: accountId, p_period: period }),
    findMessageByRef: (deviceId, ref) => one(`luma_messages?device_id=eq.${enc(deviceId)}&client_ref=eq.${enc(ref)}&select=*`),
    insertMessage: (row) => insert("luma_messages", row),
    updateMessage: (id, patch) => update("luma_messages", `id=eq.${enc(id)}`, patch),
    updateMessageBySid: (sid, patch) => update("luma_messages", `provider_sid=eq.${enc(sid)}`, patch),
    async recentOutbound(accountId, sinceIso) {
      const rows = await request("GET", `luma_messages?account_id=eq.${enc(accountId)}&direction=eq.out&created_at=gte.${enc(sinceIso)}&select=id&limit=50`);
      return rows.length;
    },
    async hasTexted(accountId, number) {
      return Boolean(await one(`luma_messages?account_id=eq.${enc(accountId)}&direction=eq.out&to_number=eq.${enc(number)}&status=not.eq.failed&kind=eq.reply&select=id`));
    },
    async isOptedOut(number, accountId) {
      const rows = await request("GET", `luma_optouts?number=eq.${enc(number)}&or=(account_id.is.null,account_id.eq.${enc(accountId)})&select=number&limit=1`);
      return rows.length > 0;
    },
    async addOptOut(number, accountId) {
      try { await request("POST", "luma_optouts", { number, account_id: accountId }); }
      catch (error) { if (error.status !== 409) throw error; }
    },
    removeOptOut: (number, accountId) => request("DELETE", `luma_optouts?number=eq.${enc(number)}&account_id=${accountId ? "eq." + enc(accountId) : "is.null"}`),
    inbox: (accountId, afterIso) => request("GET", `luma_messages?account_id=eq.${enc(accountId)}&direction=eq.in&created_at=gt.${enc(afterIso)}&order=created_at.asc&limit=50&select=id,from_number,body,created_at,kind`),
    async lastSenderTo(number, viaNumber) {
      // The pool number Twilio used, or a pool send whose number wasn't reported.
      const row = await one(`luma_messages?direction=eq.out&kind=eq.reply&to_number=eq.${enc(number)}&or=(from_number.eq.${enc(viaNumber)},from_number.is.null)&order=created_at.desc&select=account_id`);
      return row ? { id: row.account_id } : null;
    },
    async recordEvent(id) {
      try { await request("POST", "luma_stripe_events", { id }); return true; }
      catch (error) { if (error.status === 409) return false; throw error; }
    },

    // ---- the Luma app (payloads are end-to-end encrypted; never readable here)
    updateDevice: (id, patch) => update("luma_devices", `id=eq.${enc(id)}`, patch),
    insertPairing: (row) => insert("luma_app_pairings", row),
    getPairing: (id) => one(`luma_app_pairings?id=eq.${enc(id)}&select=*`),
    // Conditional update: only one phone can ever redeem a pairing.
    usePairing: (id, at) => update("luma_app_pairings", `id=eq.${enc(id)}&used_at=is.null`, { used_at: at }),
    async openPairings(deviceId, nowIso) {
      const rows = await request("GET", `luma_app_pairings?device_id=eq.${enc(deviceId)}&used_at=is.null&expires_at=gt.${enc(nowIso)}&select=id&limit=20`);
      return rows.length;
    },
    insertAppLink: (row) => insert("luma_app_links", row),
    getAppLink: (id) => one(`luma_app_links?id=eq.${enc(id)}&select=*`),
    updateAppLink: (id, patch) => update("luma_app_links", `id=eq.${enc(id)}`, patch),
    touchAppLink: (id, at) => request("PATCH", `luma_app_links?id=eq.${enc(id)}`, { last_seen_at: at }),
    listAppLinks: (deviceId) => request("GET", `luma_app_links?device_id=eq.${enc(deviceId)}&revoked_at=is.null&order=created_at.asc&limit=20&select=*`),
    async insertAppMessage(row) {
      try { return await insert("luma_app_messages", row); }
      catch (error) {
        if (error.status !== 409) throw error;
        return one(`luma_app_messages?link_id=eq.${enc(row.link_id)}&client_ref=eq.${enc(row.client_ref)}&select=*`);
      }
    },
    findAppMessage: (linkId, ref) => one(`luma_app_messages?link_id=eq.${enc(linkId)}&client_ref=eq.${enc(ref)}&select=*`),
    async recentAppMessages(linkId, direction, sinceIso) {
      const rows = await request("GET", `luma_app_messages?link_id=eq.${enc(linkId)}&direction=eq.${enc(direction)}&created_at=gte.${enc(sinceIso)}&select=id&limit=60`);
      return rows.length;
    },
    appMessagesForLink: (linkId, afterIso, beforeIso) => request("GET", `luma_app_messages?link_id=eq.${enc(linkId)}&direction=eq.down&created_at=gt.${enc(afterIso)}&created_at=lte.${enc(beforeIso)}&order=created_at.asc&limit=50&select=id,payload,created_at`),
    appMessagesForDevice: (deviceId, afterIso, beforeIso) => request("GET", `luma_app_messages?device_id=eq.${enc(deviceId)}&direction=eq.up&created_at=gt.${enc(afterIso)}&created_at=lte.${enc(beforeIso)}&order=created_at.asc&limit=50&select=id,link_id,payload,created_at`),
    pruneAppMessages: (deviceId, beforeIso) => request("DELETE", `luma_app_messages?device_id=eq.${enc(deviceId)}&created_at=lt.${enc(beforeIso)}`),
  };
}
