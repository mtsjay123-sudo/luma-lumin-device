// Luma Desktop: talk to Luma, watch it work, approve what goes out.
//
// The same local runtime as the main controls (this page is served by it), so
// approvals still go through the runtime's one-time tokens. This page never
// approves anything on its own.
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const TEXT_TOOLS = ["luma.send", "sms.send", "mac_messages.send"];
  const TASKY = /^(?:hey |ok |okay |please |can you |could you |luma,? )*(text|tell|message|remind|make|build|create|draft|write|find|look|search|check|scroll|order|book|plan|send|add|schedule|set|start|open|summari[sz]e|research)\b/i;
  const state = { thread: [], seen: new Set(), files: [], status: null, data: null, busy: false, cards: new Map() };

  // ------------------------------------------------------------ helpers ---
  async function api(path, data) {
    const r = await fetch(path, data === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw Object.assign(new Error(d.error || "Luma couldn't do that."), { status: r.status });
    return d;
  }
  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }
  function btn(label, cls, onClick) {
    const b = el("button", cls, label);
    b.type = "button";
    b.addEventListener("click", onClick);
    return b;
  }
  function toast(text) {
    const t = $("toast");
    t.textContent = text;
    t.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => t.classList.remove("show"), 4200);
  }
  const time = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });

  // --------------------------------------------------------- the mascot ---
  let moodTimer = null;
  function mood(name, doing, holdMs) {
    const m = $("mascot");
    m.className = "mascot " + name;
    $("doing").textContent = doing || "";
    clearTimeout(moodTimer);
    if (holdMs) moodTimer = setTimeout(() => mood("idle", "Here with you"), holdMs);
  }

  // What Luma is probably doing, in plain words, while the model works.
  function guessDoing(text) {
    const t = text.toLowerCase();
    let m;
    if ((m = /(?:text|tell|message)\s+(?:my\s+)?([a-z]+)/i.exec(text))) return `Drafting the text to ${m[1][0].toUpperCase() + m[1].slice(1)}`;
    if (/deck|slides|pitch/.test(t)) return "Building your deck";
    if (/remind/.test(t)) return "Setting a reminder";
    if (/instagram|tiktok|feed|scroll/.test(t)) return "Scrolling your feed";
    if (/search|look up|find|research/.test(t)) return "Looking it up";
    if (/homework|study|quiz|explain|math/.test(t)) return "Working through it";
    return "Working on it";
  }

  // ------------------------------------------------------------ thread ---
  function save() {
    try { sessionStorage.setItem("luma-desktop-thread", JSON.stringify(state.thread.slice(-120))); } catch (_) { /* private mode */ }
  }
  function load() {
    try { state.thread = JSON.parse(sessionStorage.getItem("luma-desktop-thread") || "[]"); } catch (_) { state.thread = []; }
  }

  function add(item) {
    state.thread.push({ at: Date.now(), ...item });
    save();
    render();
  }

  function render() {
    const box = $("thread");
    box.replaceChildren();
    if (!state.thread.length) {
      const empty = el("div", "empty");
      empty.append(el("h2", null, greeting()));
      const chips = el("div", "chips");
      for (const s of ["Text my mom I'm on my way", "Make a pitch deck for a dog-walking startup", "Remind me at 6 to grab flowers", "Help me study for my bio quiz", "What's on today?"])
        chips.append(btn(s, "", () => { $("input").value = s; resize(); $("input").focus(); }));
      empty.append(chips);
      box.append(empty);
      return;
    }
    let prev = null;
    for (const item of state.thread) {
      if (item.who === "notice") {
        const n = el("div", "notice");
        if (item.label) n.append(el("b", null, item.label));
        n.append(document.createTextNode(item.text));
        box.append(n);
        prev = item;
        continue;
      }
      const row = el("div", `row ${item.who}${prev && prev.who === item.who ? "" : " first"}`);
      row.append(el("div", "bubble", item.text));
      if (item.links && item.links.length) {
        const links = el("div", "links");
        item.links.forEach((l, i) => {
          if (i) links.append(el("span", "dot", "·"));
          links.append(btn(l.label, "", () => openWork(l.work)));
        });
        row.append(links);
      }
      if (item.meta) row.append(el("div", "meta", item.meta));
      box.append(row);
      prev = item;
    }
    if (state.busy) {
      const t = el("div", "typing");
      t.append(el("i"), el("i"), el("i"));
      box.append(t);
    }
    box.scrollTop = box.scrollHeight;
  }

  function greeting() {
    const h = new Date().getHours();
    const name = state.status?.profile?.name;
    const part = h < 5 ? "Up late" : h < 12 ? "Morning" : h < 17 ? "Afternoon" : "Evening";
    return `${part}${name ? ", " + name : ""}. What are we doing?`;
  }

  // ------------------------------------------------------------ talking ---
  async function say(text) {
    add({ who: "you", text });
    const task = TASKY.test(text);
    state.busy = true;
    mood("thinking", "Thinking it through…");
    if (task) setTimeout(() => { if (state.busy) { add({ who: "luma", text: "On it." }); mood("working", guessDoing(text)); } }, 450);
    render();
    try {
      const result = await api("/api/chat", { text });
      if (result.event_id) state.seen.add(result.event_id);
      state.busy = false;
      show(result);
    } catch (error) {
      state.busy = false;
      add({ who: "luma", text: error.status ? error.message : "I can't reach my brain right now. Is Luma running?" });
      mood(error.status ? "idle" : "sleepy", error.status ? "Here with you" : "Can't reach Luma");
    }
  }

  // Turn a runtime result into a reply, links to the work, and a mood.
  function show(result) {
    const work = workFor(result);
    const text = result.text || result.summary || (work ? "Take a look." : "Done.");
    const links = [];
    if (work) links.push({ label: work.link, work });
    if (work && work.kind === "deck" && work.file?.url) links.push({ label: "Download", work: { ...work, download: true } });
    let meta = null;
    if (result.noticed?.length) meta = "I'll remember: " + result.noticed.map((n) => n.text).join("; ");
    add({ who: "luma", text, links, meta, noticed: result.noticed });
    if (work) openWork(work);
    if (work && work.kind === "approve") mood("waiting", "Waiting for your OK");
    else if (result.state === "succeeded" || result.task || result.file) mood("happy", result.file ? "Your deck's ready" : "Done", 4000);
    else mood("idle", "Here with you");
  }

  function workFor(r) {
    if (r.state === "pending" && r.confirm_token && r.action) {
      const args = r.arguments || {};
      const isText = TEXT_TOOLS.includes(r.tool);
      return { kind: "approve", link: isText ? "Review text" : "Review", action: r.action, token: r.confirm_token, tool: r.tool, expires: r.expires,
        to: args.to, to_name: r.recipient_name || args.to, body: args.body, review: r.review || {}, isText, route: state.status?.message_route };
    }
    if (r.message_draft && ["draft", "quota"].includes(r.state)) {
      const d = r.message_draft;
      return { kind: "draft", link: "Draft text", to: d.to, to_name: d.name, body: d.body, quota: r.state === "quota" };
    }
    if (r.file && r.file.url) return { kind: "deck", link: "Open deck", file: r.file };
    if (r.page && r.url) return { kind: "page", link: "View page", title: r.title || r.url, url: r.url, page: r.page };
    if (r.task) return { kind: "today", link: "Today" };
    return null;
  }

  // -------------------------------------------------------- work panel ---
  function openWork(work) {
    if (!work) return;
    if (work.download && work.file?.url) { window.location.href = work.file.url; toast("Saving the deck to your Downloads."); return; }
    if (work.kind === "today") return go("today");
    const body = $("panel-body");
    body.replaceChildren(card(work));
    $("panel-title").textContent = { approve: work.isText ? "Text" : "Approval", draft: "Draft", deck: "Deck", page: "Page" }[work.kind] || "Work";
    $("panel").hidden = false;
  }
  $("panel-close").addEventListener("click", () => { $("panel").hidden = true; });

  function card(work) {
    const c = el("div", "card");
    if (work.kind === "approve") return approveCard(c, work);
    if (work.kind === "draft") {
      c.append(el("span", "label", work.quota ? "Out of free texts this month: send it yourself" : "Draft for you to send"));
      c.append(phone(work.to_name, work.body));
      const actions = el("div", "actions");
      if (work.to) {
        const open = el("a", "pill primary", "Open in Messages");
        open.href = `sms:${work.to}&body=${encodeURIComponent(work.body)}`;
        actions.append(open);
      }
      actions.append(btn("Copy", "pill soft", async (e) => { await navigator.clipboard.writeText(work.body).catch(() => {}); e.target.textContent = "Copied"; }));
      c.append(actions);
      return c;
    }
    if (work.kind === "deck") {
      const f = work.file;
      c.append(el("h3", null, f.title || f.name));
      c.append(el("span", "label", `${f.slides || (f.outline || []).length} slides · speaker notes included`));
      const slides = el("div", "slides");
      (f.outline || []).forEach((s, i) => {
        const tile = el("div", `slide theme-${f.theme || "midnight"}`);
        tile.append(el("span", "k", `${i + 1} · ${String(s.layout || "slide").replace("_", " ")}`));
        if (s.title) tile.append(el("span", "t", s.title));
        if (s.big) tile.append(el("span", s.layout === "quote" ? "q" : "n", s.layout === "quote" ? `“${s.big}”` : s.big));
        if (s.points?.length) { const ul = el("ul"); s.points.slice(0, 3).forEach((p) => ul.append(el("li", null, p))); tile.append(ul); }
        slides.append(tile);
      });
      if ((f.outline || []).length) c.append(slides);
      const actions = el("div", "actions");
      const dl = el("a", "pill primary", "Download .pptx");
      dl.href = f.url;
      actions.append(dl);
      c.append(actions);
      return c;
    }
    if (work.kind === "page") {
      c.append(el("h3", null, work.title));
      c.append(el("span", "label", work.url));
      c.append(el("div", "page-snap", String(work.page || "").slice(0, 4000)));
      const actions = el("div", "actions");
      const a = el("a", "pill soft", "Open in your browser");
      a.href = work.url;
      a.target = "_blank";
      a.rel = "noopener";
      actions.append(a);
      c.append(actions);
      return c;
    }
    c.append(el("p", null, "Nothing to show."));
    return c;
  }

  function phone(name, body) {
    const p = el("div", "phone");
    p.append(el("div", "to", "To: " + (name || "them")));
    p.append(el("div", "sms", body));
    return p;
  }

  const ROUTES = { luma_number: "From Luma's number", mac_imessage: "From your iMessage", mac_sms: "From your number (SMS)", twilio: "From your Twilio number" };

  function approveCard(c, work) {
    const expired = () => work.expires && work.expires * 1000 < Date.now();
    if (work.isText) {
      c.append(el("span", "label", ROUTES[work.route] || "Ready to send"));
      const preview = phone(work.to_name, work.body);
      c.append(preview);
    } else {
      c.append(el("h3", null, String(work.review.title || work.tool || "Approve this").replace(/\./g, " ")));
      const ul = el("ul");
      for (const [k, v] of Object.entries(work.review || {})) if (k !== "title" && (typeof v === "string" || typeof v === "number")) ul.append(el("li", null, `${k.replace(/_/g, " ")}: ${v}`));
      c.append(ul);
    }
    const stateLine = el("span", "state");
    const actions = el("div", "actions");
    const finish = (text, ok) => {
      c.classList.add("done");
      stateLine.textContent = text;
      mood(ok ? "happy" : "idle", ok ? "Sent" : "Here with you", ok ? 4000 : 0);
    };
    actions.append(btn(work.isText ? "Send it" : "Approve", "pill primary", async () => {
      if (expired()) { finish("That one expired. Ask me again.", false); return; }
      stateLine.textContent = "Sending…";
      mood("working", work.isText ? `Sending to ${work.to_name}` : "Doing it");
      try {
        const r = await api("/api/confirm", { id: work.action, token: work.token });
        const ok = r.state === "succeeded";
        finish(ok ? (work.isText ? "Sent ✓" : "Done ✓") : r.state === "unknown" ? "Not sure it went out" : "Didn't go through", ok);
        add({ who: "luma", text: r.text || r.summary || (ok ? "Done." : "That didn't go through.") });
      } catch (e) { stateLine.textContent = e.message; mood("idle", "Here with you"); }
    }));
    if (work.isText) actions.append(btn("Edit", "pill soft", () => {
      const area = el("textarea");
      area.value = work.body;
      const save = btn("Use this", "pill primary", async () => {
        try {
          await api("/api/cancel", { id: work.action }).catch(() => {});
          const r = await api("/api/messages/prepare", { recipient: work.to, body: area.value.trim() });
          show(r);
        } catch (e) { toast(e.message); }
      });
      c.replaceChildren(el("span", "label", "Edit the text to " + work.to_name), area, save);
      area.focus();
    }));
    actions.append(btn(work.isText ? "Don't send" : "Cancel", "pill quiet", async () => {
      try { await api("/api/cancel", { id: work.action }); } catch (_) { /* already gone */ }
      finish("Not sent", false);
      add({ who: "luma", text: "Okay, I won't send it." });
    }));
    c.append(actions, stateLine);
    if (expired()) finish("That one expired. Ask me again.", false);
    return c;
  }

  // ------------------------------------------------------------- views ---
  function go(view) {
    for (const b of document.querySelectorAll(".rail-btn")) b.classList.toggle("active", b.dataset.view === view);
    for (const v of document.querySelectorAll(".view")) v.hidden = v.id !== "view-" + view;
    if (view !== "chat") refresh().then(() => renderView(view));
    else $("input").focus();
  }
  for (const b of document.querySelectorAll(".rail-btn")) b.addEventListener("click", () => go(b.dataset.view));

  function renderView(view) {
    const d = state.data;
    if (!d) return;
    if (view === "library") {
      const box = $("library");
      box.replaceChildren();
      const pending = (d.actions || []).filter((a) => a.state === "pending");
      for (const a of pending) {
        const t = el("button", "tile");
        const cap = el("div", "cap");
        cap.append(el("div", "title", TEXT_TOOLS.includes(a.tool) ? "Text waiting on you" : "Waiting on you"), el("div", "sub", a.arguments?.body || a.tool));
        t.append(cap);
        t.addEventListener("click", () => { go("chat"); toast("Ask Luma to set it up again to get fresh Send buttons."); });
        box.append(t);
      }
      for (const f of d.files || []) {
        const t = el("button", "tile");
        const thumb = el("div", `slide theme-${f.theme || "midnight"}`);
        thumb.append(el("span", "k", "Deck"), el("span", "t", f.title || f.name));
        const cap = el("div", "cap");
        cap.append(el("div", "title", f.title || f.name), el("div", "sub", `${f.slides || "?"} slides`));
        t.append(thumb, cap);
        t.addEventListener("click", () => { go("chat"); openWork({ kind: "deck", file: f }); });
        box.append(t);
      }
      for (const m of d.message_drafts || []) {
        const t = el("button", "tile");
        const cap = el("div", "cap");
        cap.append(el("div", "title", "Draft to " + (m.name || m.to)), el("div", "sub", m.body));
        t.append(cap);
        t.addEventListener("click", () => { go("chat"); openWork({ kind: "draft", to: m.to, to_name: m.name, body: m.body }); });
        box.append(t);
      }
      if (!box.children.length) box.append(el("p", "lede", "Nothing yet. Ask Luma for a deck or a text and it shows up here."));
    }
    if (view === "today") {
      $("today-brief").textContent = d.household?.briefing?.text || "Your reminders and routines.";
      const box = $("today");
      box.replaceChildren();
      for (const t of d.tasks || []) {
        const it = el("div", "item");
        const g = el("div", "grow");
        g.append(el("div", "title", t.title), el("div", "sub", t.due ? new Date(t.due * 1000).toLocaleString([], { weekday: "short", hour: "numeric", minute: "2-digit" }) : ""));
        it.append(g, btn("Done", "pill soft", async () => { try { await api("/api/task/complete", { id: t.id }); it.remove(); } catch (e) { toast(e.message); } }));
        box.append(it);
      }
      for (const r of d.routines || []) {
        const it = el("div", "item");
        const g = el("div", "grow");
        g.append(el("div", "title", r.title), el("div", "sub", "Every day at " + r.at));
        it.append(g);
        box.append(it);
      }
      if (!box.children.length) box.append(el("p", "lede", "Nothing scheduled. Try “remind me at 6 to grab flowers.”"));
    }
    if (view === "people") {
      const box = $("people");
      box.replaceChildren();
      for (const p of d.contacts || []) {
        const it = el("div", "item");
        const g = el("div", "grow");
        g.append(el("div", "title", p.name), el("div", "sub", [p.phone, ...(p.aliases || [])].join(" · ")));
        it.append(g, btn("Remove", "pill quiet", async () => { try { await api("/api/contacts/delete", { id: p.id }); it.remove(); } catch (e) { toast(e.message); } }));
        box.append(it);
      }
      if (!box.children.length) box.append(el("p", "lede", "No one yet."));
    }
    if (view === "settings") renderSettings();
  }

  $("person-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    try {
      await api("/api/contacts/save", { name: f.get("name"), phone: String(f.get("phone")).replace(/[^\d+]/g, ""), ...(f.get("nicknames") ? { aliases: String(f.get("nicknames")) } : {}) });
      e.target.reset();
      await refresh();
      renderView("people");
    } catch (err) { toast(err.message); }
  });

  function toggleRow(title, sub, on, onChange) {
    const it = el("div", "item");
    const g = el("div", "grow");
    g.append(el("div", "title", title), el("div", "sub", sub));
    const sw = el("button", "switch");
    sw.setAttribute("role", "switch");
    sw.setAttribute("aria-checked", String(Boolean(on)));
    sw.setAttribute("aria-label", title);
    sw.addEventListener("click", async () => {
      const next = sw.getAttribute("aria-checked") !== "true";
      try { await onChange(next); sw.setAttribute("aria-checked", String(next)); } catch (e) { toast(e.message); }
    });
    it.append(g, sw);
    return it;
  }

  function renderSettings() {
    const s = state.status || {};
    const box = $("settings");
    box.replaceChildren();
    box.append(toggleRow("Listen for “Hey Luma”", "Talk out loud from across the room. The microphone stays off until you turn this on.", !s.microphone_muted,
      (on) => api("/api/setting", { key: "muted", value: !on })));
    box.append(toggleRow("Remember things I mention", "Luma keeps small facts (your sister's birthday, your coffee order), encrypted on this computer.", s.presence?.learn_from_chat !== false,
      (on) => api("/api/setting", { key: "learn_from_chat", value: on })));
    box.append(toggleRow("Check back on things", "“How did the interview go?” the day after.", s.presence?.check_ins !== false,
      (on) => api("/api/setting", { key: "check_ins", value: on })));
    const route = el("div", "item");
    const rg = el("div", "grow");
    rg.append(el("div", "title", "Send texts"), el("div", "sub", "Where Luma's texts come from. Every text still waits for your OK."));
    const sel = el("select", "pill soft");
    for (const [v, label] of [["phone_draft", "Drafts I send myself"], ["mac_imessage", "My iMessage"], ["mac_sms", "My number (SMS)"], ["luma_number", "Luma's number"]]) {
      const o = el("option", null, label);
      o.value = v;
      sel.append(o);
    }
    sel.value = s.message_route || "phone_draft";
    sel.addEventListener("change", async () => { try { await api("/api/messages/route", { route: sel.value }); await refresh(); } catch (e) { toast(e.message); } });
    route.append(rg, sel);
    box.append(route);
    const phoneRow = el("div", "item");
    const pg = el("div", "grow");
    const phones = state.data?.phone_app?.phones || [];
    pg.append(el("div", "title", "Luma on your phone"), el("div", "sub", phones.length ? phones.map((p) => p.name).join(", ") + " connected" : "Talk to Luma from anywhere. Encrypted end to end."));
    phoneRow.append(pg, btn("Connect a phone", "pill soft", async () => {
      try {
        const r = await api("/api/phone-app/pair", {});
        const c = el("div", "card");
        const img = el("img");
        img.src = r.qr;
        img.alt = "Scan with your phone's camera";
        img.width = 220;
        c.append(el("h3", null, "Scan with your phone's camera"), img, el("span", "label", "Works once, for 10 minutes."));
        $("panel-body").replaceChildren(c);
        $("panel-title").textContent = "Your phone";
        $("panel").hidden = false;
      } catch (e) { toast(e.message); }
    }));
    box.append(phoneRow);
    const about = el("div", "item");
    const ag = el("div", "grow");
    ag.append(el("div", "title", "Brain"), el("div", "sub", (s.model_name || "").includes("Qwen") ? "Qwen3 4B, running on this computer. Nothing you say leaves it unless you send it." : "Running on this computer."));
    const full = el("a", "pill quiet", "All controls");
    full.href = "/";
    about.append(ag, full);
    box.append(about);
  }

  // ------------------------------------------------------ live updates ---
  let first = true;
  async function refresh() {
    try {
      const d = await api("/api/state");
      state.data = d;
      state.status = d.status;
      $("mic").classList.toggle("on", d.status && !d.status.microphone_muted);
      $("mic").title = d.status && !d.status.microphone_muted ? "Listening for “Hey Luma”. Click to stop." : "Talk out loud";
      const events = d.events || [];
      for (const ev of events) {
        const r = ev.result || ev;
        const id = r.event_id || `${ev.created}:${r.text}`;
        if (state.seen.has(id)) continue;
        state.seen.add(id);
        if (first) continue; // don't replay history on open
        if (r.you && r.channel) {
          add({ who: "you", text: r.you, meta: r.channel === "app" ? "From your phone" : r.channel === "sms" ? "By text" : null });
          show(r);
        } else if (r.type && r.text) {
          const label = { reply: "Text back", reminder: "Reminder", timer: "Timer", briefing: "Today" }[r.type];
          if (label) add({ who: "notice", label, text: r.text });
          else add({ who: "luma", text: r.text });
          if (document.hidden && "Notification" in window && Notification.permission === "granted") new Notification("Luma", { body: r.text });
          mood("happy", label || "Thought of something", 3000);
        }
      }
      first = false;
      if (!state.busy && $("mascot").classList.contains("sleepy")) mood("idle", "Here with you");
      if (!state.busy && d.status?.busy && $("mascot").classList.contains("idle")) mood("thinking", "Listening…", 3000);
      return d;
    } catch (_) {
      if (!state.busy) mood("sleepy", "Can't reach Luma. Is it running?");
      return null;
    }
  }

  // ----------------------------------------------------------- composer ---
  const input = $("input");
  function resize() {
    $("send").disabled = !input.value.trim() || state.busy;
    input.style.height = "auto";
    input.style.height = Math.min(180, input.scrollHeight) + "px";
  }
  input.addEventListener("input", resize);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); $("composer").requestSubmit(); }
  });
  $("composer").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text || state.busy) return;
    input.value = "";
    resize();
    say(text).then(resize);
    resize();
  });
  $("mic").addEventListener("click", async () => {
    const on = !$("mic").classList.contains("on");
    try {
      await api("/api/setting", { key: "muted", value: !on });
      $("mic").classList.toggle("on", on);
      toast(on ? "Listening. Say “Hey Luma”." : "Microphone off.");
    } catch (e) { toast(e.message); }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !$("panel").hidden) $("panel").hidden = true;
    if ((e.metaKey || e.ctrlKey) && e.key === "n") { e.preventDefault(); state.thread = []; save(); render(); mood("idle", "Here with you"); }
  });

  load();
  render();
  refresh().then(() => { render(); if ("Notification" in window && Notification.permission === "default") Notification.requestPermission().catch(() => {}); });
  setInterval(refresh, 3000);
  input.focus();
})();
