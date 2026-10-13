// Luma Desktop: talk to Luma, watch it work, approve what goes out.
//
// Served by the local Luma runtime, so every approval still goes through the
// runtime's one-time tokens. This page never approves anything on its own:
// Allow only ever happens when you press it.
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);

  // ------------------------------------------------------------- icons ---
  const ICONS = {
    chat: '<path d="M4 11.5C4 7.4 7.6 4 12 4s8 3.4 8 7.5S16.4 19 12 19c-1 0-1.9-.2-2.8-.4L5 20l1.2-3.4C4.8 15.3 4 13.5 4 11.5Z"/>',
    feed: '<rect x="4" y="4" width="16" height="6.5" rx="2.2"/><rect x="4" y="13.5" width="16" height="6.5" rx="2.2"/>',
    ideas: '<path d="M9.5 18h5M10.5 21h3M12 3a6 6 0 0 0-3.6 10.8c.4.3.6.8.6 1.3V16h6v-.9c0-.5.2-1 .6-1.3A6 6 0 0 0 12 3Z"/>',
    goals: '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r=".9"/>',
    library: '<rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    compose: '<path d="M11 4.5H6.5a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V13"/><path d="M17.6 3.9a1.9 1.9 0 0 1 2.7 2.7L12 14.9l-3.5.8.8-3.5 8.3-8.3Z"/>',
    apps: '<path d="M9 7V4M15 7V4M7 7h10v4a5 5 0 0 1-10 0V7ZM12 16v4"/>',
    rules: '<path d="M12 3 5 6v5c0 4.5 3 8.3 7 10 4-1.7 7-5.5 7-10V6l-7-3Z"/><path d="m9 12 2 2 4-4"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
    mic: '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v2.5"/>',
    up: '<path d="M12 19V6M6.5 11.5 12 6l5.5 5.5"/>',
    down: '<path d="M12 5v13M6.5 12.5 12 18l5.5-5.5"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    cart: '<circle cx="9.5" cy="19.5" r="1.4"/><circle cx="17.5" cy="19.5" r="1.4"/><path d="M3 4h2.5l2.2 10.6a1.6 1.6 0 0 0 1.6 1.3h8.1a1.6 1.6 0 0 0 1.6-1.2L20.5 8H6.3"/>',
    mail: '<rect x="3.5" y="5.5" width="17" height="13" rx="2.5"/><path d="m4.5 7.2 7.5 5.8 7.5-5.8"/>',
    calendar: '<rect x="4" y="5" width="16" height="15" rx="3"/><path d="M8 3v4M16 3v4M4 10h16"/>',
    tag: '<path d="M3.5 12.3V5A1.5 1.5 0 0 1 5 3.5h7.3L21 12.2l-8.8 8.8-8.7-8.7Z"/><circle cx="8" cy="8" r="1.4"/>',
    globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.4 2.4 3.5 5.3 3.5 8.5s-1.1 6.1-3.5 8.5c-2.4-2.4-3.5-5.3-3.5-8.5s1.1-6.1 3.5-8.5Z"/>',
    lock: '<rect x="5" y="10.5" width="14" height="10" rx="2.5"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
    pause: '<rect x="7" y="5" width="3.4" height="14" rx="1"/><rect x="13.6" y="5" width="3.4" height="14" rx="1"/>',
    play: '<path d="M8 5.5v13l10.5-6.5L8 5.5Z"/>',
    stop: '<rect x="6.5" y="6.5" width="11" height="11" rx="2.2"/>',
    hand: '<path d="M8 13V6.5a1.5 1.5 0 0 1 3 0V12M11 11.5V5a1.5 1.5 0 0 1 3 0v6.5M14 11.5V6.5a1.5 1.5 0 0 1 3 0V14c0 3.6-2.4 6.5-6 6.5-2.6 0-4-1.3-5.4-3.4L4 14.4a1.5 1.5 0 0 1 2.4-1.8L8 14.5"/>',
    up_t: '<path d="M7 10.5v9H4.5v-9H7Zm0 0 4-7c1.4 0 2.3 1.2 2 2.5L12.3 9H18a2 2 0 0 1 2 2.3l-1.2 6.5a2 2 0 0 1-2 1.7H7"/>',
    down_t: '<path d="M17 13.5v-9h2.5v9H17Zm0 0-4 7c-1.4 0-2.3-1.2-2-2.5l.7-3H6a2 2 0 0 1-2-2.3l1.2-6.5a2 2 0 0 1 2-1.7H17"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2.5"/><path d="M16 8V6.5A2.5 2.5 0 0 0 13.5 4h-7A2.5 2.5 0 0 0 4 6.5v7A2.5 2.5 0 0 0 6.5 16H8"/>',
    external: '<path d="M7 17 17 7M9 7h8v8"/>',
    trash: '<path d="M5 7h14M10 7V4.5h4V7M7 7l1 13h8l1-13"/>',
    refresh: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6"/>',
    phone: '<rect x="7" y="3" width="10" height="18" rx="2.5"/><path d="M11 18h2"/>',
    cpu: '<rect x="6" y="6" width="12" height="12" rx="2.5"/><path d="M9.5 9.5h5v5h-5zM9 2.5V6M15 2.5V6M9 18v3.5M15 18v3.5M2.5 9H6M2.5 15H6M18 9h3.5M18 15h3.5"/>',
    insta: '<rect x="4" y="4" width="16" height="16" rx="5"/><circle cx="12" cy="12" r="3.6"/><circle cx="16.8" cy="7.2" r=".9"/>',
    spark: '<path d="M12 3.5 13.8 9l5.7 1.5-5.7 1.5L12 17.5 10.2 12l-5.7-1.5L10.2 9 12 3.5ZM18.5 16l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7.7-2Z"/>',
    deck: '<rect x="3.5" y="4.5" width="17" height="11.5" rx="2"/><path d="M12 16v4M8.5 20h7"/>',
    check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    people: '<circle cx="9" cy="8.5" r="3.2"/><path d="M3.5 19c.8-3 3-4.6 5.5-4.6s4.7 1.6 5.5 4.6M16 5.6a3 3 0 0 1 0 5.8M18 14.6c1.3.6 2.2 2 2.6 4.4"/>',
    message: '<path d="M5 5.5h14a1.5 1.5 0 0 1 1.5 1.5v9a1.5 1.5 0 0 1-1.5 1.5H10l-4.5 3v-3H5A1.5 1.5 0 0 1 3.5 16V7A1.5 1.5 0 0 1 5 5.5Z"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
    moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.2M12 19.3v2.2M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6"/>',
    eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
    card: '<rect x="3" y="6" width="18" height="13" rx="2.5"/><path d="M3 10h18M7 15h4"/>',
    list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
    reply: '<path d="M9.5 6.5 4 12l5.5 5.5M4.5 12H14a6 6 0 0 1 6 6v.5"/>',
  };
  function icon(name) {
    const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", "0 0 24 24");
    s.setAttribute("class", "i");
    s.setAttribute("aria-hidden", "true");
    s.innerHTML = ICONS[name] || "";
    return s;
  }
  for (const node of document.querySelectorAll("[data-icon]")) node.prepend(icon(node.dataset.icon));

  // ----------------------------------------------------------- helpers ---
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
  function btn(label, cls, onClick, iconName) {
    const b = el("button", cls);
    b.type = "button";
    if (iconName) b.append(icon(iconName));
    if (label) b.append(document.createTextNode(label));
    b.addEventListener("click", onClick);
    return b;
  }
  function linkOut(label, href, cls, iconName) {
    const a = el("a", cls);
    if (iconName) a.append(icon(iconName));
    if (label) a.append(document.createTextNode(label));
    a.href = href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    return a;
  }
  function chip(kind, iconName, cls = "mini-ic") {
    const c = el("span", `${cls} k-${kind}`);
    c.append(icon(iconName));
    return c;
  }
  function toast(text) {
    const t = $("toast");
    t.textContent = text;
    t.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => t.classList.remove("show"), 4200);
  }
  const money = (v) => typeof v === "number" ? "$" + v.toLocaleString(undefined, { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 }) : String(v || "");
  const clock = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });
  function ago(seconds) {
    if (!seconds) return "";
    const d = Date.now() / 1000 - seconds;
    if (d < 60) return "now";
    if (d < 3600) return Math.round(d / 60) + "m ago";
    if (d < 86400) return Math.round(d / 3600) + "h ago";
    return new Date(seconds * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }
  function until(seconds) {
    const d = seconds - Date.now() / 1000;
    if (d <= 60) return "any moment";
    if (d < 3600) return "in " + Math.round(d / 60) + " min";
    if (d < 86400) return "at " + clock.format(new Date(seconds * 1000));
    return new Date(seconds * 1000).toLocaleDateString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" });
  }
  function host(url) { try { return new URL(url).hostname.replace(/^www\./, ""); } catch (_) { return ""; } }
  const safeUrl = (u) => /^https?:\/\//i.test(String(u || "")) ? u : null;
  const safeImg = (u) => /^(?:https:\/\/|data:image\/(?:png|jpeg|webp|gif|svg\+xml)[;,])/i.test(String(u || "")) ? u : null;
  function picture(src, alt = "") {
    if (!safeImg(src)) return null;
    const img = el("img");
    img.src = src; img.alt = alt; img.loading = "lazy"; img.referrerPolicy = "no-referrer";
    return img;
  }

  // ------------------------------------------------------------- theme ---
  const darkNow = (choice) => choice === "dark" || (choice !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);
  function applyTheme(choice) {
    if (choice === "light" || choice === "dark") document.documentElement.dataset.theme = choice;
    else delete document.documentElement.dataset.theme;
    $("top-theme").replaceChildren(icon(darkNow(choice) ? "sun" : "moon"));
  }
  let theme = "system";
  try { theme = localStorage.getItem("luma-theme") || "system"; } catch (_) { /* private window */ }
  applyTheme(theme);
  function setTheme(v) { theme = v; try { localStorage.setItem("luma-theme", v); } catch (_) { /* private */ } applyTheme(v); }

  // ------------------------------------------------------------- state ---
  const state = {
    view: "chat", thread: "main", transcripts: {}, local: {}, home: null, status: null, data: null,
    busy: false, activity: null, tokens: {}, outcomes: {}, seen: new Set(), firstPoll: true, feedSel: null, offers: new Map(),
    shown: new Set(), // messages already on screen, so only new ones animate in
  };
  const KIND = {
    deal: { icon: "tag", label: "Price check" }, inbox: { icon: "mail", label: "Inbox" }, feed: { icon: "insta", label: "Feed" },
    today: { icon: "calendar", label: "Your day" }, update: { icon: "spark", label: "Update" }, idea: { icon: "ideas", label: "Idea" },
    approval: { icon: "rules", label: "Needs you" }, setup: { icon: "apps", label: "Set up" }, people: { icon: "people", label: "People" },
  };
  const HELPER = {
    price_watch: { icon: "tag", k: "deal", label: "Price watch" }, inbox_digest: { icon: "mail", k: "inbox", label: "Inbox check" },
    feed_digest: { icon: "insta", k: "feed", label: "Feed catch-up" }, agenda: { icon: "calendar", k: "today", label: "Morning agenda" },
    goal: { icon: "goals", k: "update", label: "Goal" }, ideas: { icon: "ideas", k: "idea", label: "Ideas" },
  };
  const EVERY = { hourly: "Every hour", every_6h: "Every 6 hours", daily: "Every day", weekly: "Every week" };
  const TITLES = { feed: "Feed", ideas: "Ideas", goals: "Goals", library: "Library", apps: "Apps", rules: "Rules", settings: "Settings" };

  // ------------------------------------------------------------ mascot ---
  let moodTimer = null;
  function mood(name, doing, holdMs) {
    $("mascot").className = "avatar " + name;
    $("doing").textContent = name === "sleepy" ? "Can't reach Luma" : doing || "";
    clearTimeout(moodTimer);
    if (holdMs) moodTimer = setTimeout(() => mood("idle", "Here with you"), holdMs);
  }
  function guessDoing(text) {
    const t = text.toLowerCase();
    let m;
    if (/cheap|price|deal|compare|buy|shop|how much/.test(t)) return "Checking stores";
    if ((m = /(?:text|tell|message)\s+(?:my\s+)?([a-z]+)/i.exec(text))) return `Writing to ${m[1][0].toUpperCase() + m[1].slice(1)}`;
    if (/e-?mail|inbox|gmail|reply/.test(t)) return "Going through your email";
    if (/calendar|schedule|today|tomorrow/.test(t)) return "Checking your calendar";
    if (/deck|slides|pitch/.test(t)) return "Building your deck";
    if (/remind/.test(t)) return "Setting a reminder";
    if (/instagram|tiktok|feed|scroll/.test(t)) return "Scrolling your feed";
    if (/search|look up|find|research/.test(t)) return "Looking it up";
    if (/homework|study|quiz|explain|math|essay/.test(t)) return "Working through it";
    return "Thinking";
  }
  let bigCount = 0;
  function bigAvatar() {
    // A copy of Luma's face; its gradient ids are renamed so they don't collide with the original.
    const a = $("mascot").cloneNode(true);
    a.removeAttribute("id");
    a.className = "avatar big idle";
    const tag = "b" + (++bigCount) + "-";
    a.querySelectorAll("[id]").forEach((n) => { n.id = tag + n.id; });
    a.querySelectorAll("[fill^='url(#'], [clip-path^='url(#']").forEach((n) => {
      for (const attr of ["fill", "clip-path"]) { const v = n.getAttribute(attr); if (v && v.startsWith("url(#")) n.setAttribute(attr, "url(#" + tag + v.slice(5)); }
    });
    return a;
  }

  // -------------------------------------------------------------- chat ---
  function items(thread) {
    const server = (state.transcripts[thread] || []).map((m) => ({ ...m, at: (m.at || 0) * 1000 }));
    const local = state.local[thread] || [];
    return server.concat(local).sort((a, b) => a.at - b.at);
  }
  function pushLocal(thread, item) {
    (state.local[thread] = state.local[thread] || []).push({ at: Date.now(), ...item });
    state.stick = true;
    if (thread === state.thread && state.view === "chat") renderChat();
  }
  async function loadThread(thread) {
    try {
      const d = await api("/api/threads/" + encodeURIComponent(thread));
      state.transcripts[thread] = d.messages || [];
    } catch (e) {
      if (e.status === 404 && thread !== "main") { state.thread = "main"; return loadThread("main"); }
    }
  }
  function threadTitle(id) { return (state.home?.threads || []).find((t) => t.id === id)?.title; }

  function renderChat() {
    const box = $("thread");
    const list = items(state.thread);
    $("chat-title").textContent = state.thread === "main" ? "Luma" : (threadTitle(state.thread) || "Side chat");
    const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 80;
    box.replaceChildren();
    if (!list.length && !state.busy) { box.append(emptyChat()); return; }
    for (const m of list) {
      if (m.role === "notice") {
        const n = el("div", "notice");
        n.append(el("b", null, m.label || "Luma"), document.createTextNode(m.text));
        box.append(n);
        continue;
      }
      const key = `${state.thread}|${m.role}|${Math.round(m.at / 1000)}|${String(m.text || "").slice(0, 40)}`;
      const row = el("div", "msg " + (m.role === "you" ? "you" : "luma") + (state.shown.has(key) ? " seen" : ""));
      state.shown.add(key);
      if (m.text) row.append(el("div", "bubble", m.text));
      if (m.role !== "you") {
        const extra = m.result ? rich(m.result) : null;
        if (extra) row.append(extra);
        row.append(replyTools(m));
      }
      box.append(row);
    }
    if (state.busy) {
      const a = state.activity;
      if (a && ["running", "paused", "stopping"].includes(a.state) && !a.background) box.append(computer(a, true));
      else { const t = el("div", "typing"); t.append(el("i"), el("i"), el("i")); box.append(t); }
    }
    if (atBottom || state.busy || state.stick) { box.scrollTop = box.scrollHeight; requestAnimationFrame(() => { box.scrollTop = box.scrollHeight; }); }
    state.stick = false;
  }

  function replyTools(m) {
    const tools = el("div", "tools");
    const add = (name, title, fn) => { const b = btn("", "", fn, name); b.title = title; b.setAttribute("aria-label", title); tools.append(b); };
    add("copy", "Copy", async () => { await navigator.clipboard.writeText(m.text || "").catch(() => {}); toast("Copied"); });
    add("up_t", "Good reply", () => api("/api/feedback", { id: "reply", value: "up" }).then(() => toast("Thanks! I'll keep doing that.")).catch(() => {}));
    add("down_t", "Not quite", () => teach());
    return tools;
  }
  function teach() {
    const body = el("div");
    body.style.display = "flex"; body.style.flexDirection = "column"; body.style.gap = "12px";
    body.append(el("p", "lede", "What should I do differently? I'll remember it."));
    const input = el("textarea");
    Object.assign(input, { rows: 3, maxLength: 300, placeholder: "e.g. Keep replies shorter, and never use emojis in my emails." });
    const actions = el("div", "actions");
    actions.append(btn("Teach Luma", "pill primary", async () => {
      try { const r = await api("/api/feedback", { id: "reply", value: "down", note: input.value }); closeSheet(); toast(r.summary); } catch (e) { toast(e.message); }
    }));
    body.append(input, actions);
    openSheet("Teach Luma", body);
    input.focus();
  }

  const STARTERS = [
    ["deal", "cart", "Find the cheapest AirPods Pro 2", "I'll check five stores and line them up", "find me the cheapest AirPods Pro 2"],
    ["inbox", "mail", "Go through my inbox", "What matters, and drafts for the rest", "check my email"],
    ["feed", "insta", "Catch me up on Instagram", "I scroll it so you don't have to", "catch me up on instagram"],
    ["update", "deck", "Make a pitch deck", "Ten slides with speaker notes", "make a pitch deck for a dog-walking startup"],
    ["today", "calendar", "What's on today?", "Your calendar and to-dos", "what's on my calendar today?"],
    ["people", "message", "Text my mom I'm on my way", "You approve every text", "text my mom I'm on my way"],
  ];
  function emptyChat() {
    const e = el("div", "empty");
    const h = new Date().getHours();
    const name = state.home?.profile?.name;
    e.append(bigAvatar());
    e.append(el("h2", null, `${h < 5 ? "Up late" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening"}${name ? ", " + name : ""}`));
    e.append(el("p", null, state.thread === "main" ? "What should I take off your plate?" : "A fresh side chat. What's this one about?"));
    const grid = el("div", "starters");
    for (const [k, ic, title, sub, say] of STARTERS) {
      const b = el("button", "starter");
      b.type = "button";
      const t = el("span");
      t.append(el("b", null, title), el("span", null, sub));
      b.append(chip(k, ic, "ic"), t);
      b.addEventListener("click", () => send(say));
      grid.append(b);
    }
    e.append(grid);
    return e;
  }

  // A runtime result becomes a card: products, a checkout, a deck, email, agenda.
  function rich(r) {
    if (r.state === "pending" && r.action) return approval(r);
    if (r.kind === "shopping" && r.offers) return products(r);
    if (r.file && r.file.url) return deckCard(r.file);
    if (r.messages && r.messages.length) return mailCard(r.messages);
    if (r.events) return agendaCard(r.events);
    if (r.message_draft && ["draft", "quota"].includes(r.state)) return draftCard(r.message_draft, r.state === "quota");
    if (r.helper) return helperChip(r.helper);
    if (r.cart && r.url) { const a = el("div", "actions"); a.append(linkOut("Open your cart", r.url, "pill soft small", "cart")); return a; }
    if (r.section === "apps" || r.open === "apps") { const a = el("div", "actions"); a.append(btn("Open Apps", "pill soft small", () => go("apps"), "apps")); return a; }
    if (r.url && safeUrl(r.url)) { const a = el("div", "actions"); a.append(linkOut(host(r.url) || "Open page", r.url, "pill soft small", "globe")); return a; }
    return null;
  }

  function products(r) {
    const c = el("div", "card box");
    const head = el("div", "card-head");
    const t = el("div");
    t.append(el("div", "t", r.query ? `Cheapest ${r.query}` : "Price check"), el("div", "s", (r.checked || []).length ? `Checked ${(r.checked || []).join(", ")}` : ""));
    head.append(chip("deal", "tag", "chip-ic"), t, el("span", "spacer"));
    if (r.query) head.append(btn("Watch price", "pill soft small", () => send(`watch the price of ${r.query}`), "eye"));
    c.append(head);
    const grid = el("div", "products");
    (r.offers || []).slice(0, 9).forEach((o, i) => { if (o.url) state.offers.set(o.url, o); grid.append(productTile(o, i === 0)); });
    if (!(r.offers || []).length) grid.append(el("p", "checked", "No real matches this time."));
    c.append(grid);
    if ((r.skipped || []).length) c.append(el("div", "checked", "Couldn't load: " + r.skipped.map((s) => s.store).join(", ")));
    return c;
  }
  function productTile(o, best) {
    const p = el("div", "product");
    if (best) p.append(el("span", "tag", "Cheapest"));
    const pic = el("div", "pic");
    const img = picture(o.image);
    if (img) { img.addEventListener("error", () => img.replaceWith(el("div", "ph", (o.store || "?")[0]))); pic.append(img); }
    else pic.append(el("div", "ph", (o.store || "?")[0]));
    const info = el("div", "info");
    info.append(el("div", "store", o.store), el("div", "name", o.title), el("div", "price", money(o.price)));
    const row = el("div", "row");
    row.append(btn("Add", "pill primary", () => addToCart(o), "cart"));
    if (safeUrl(o.url)) row.append(linkOut("View", o.url, "pill soft"));
    info.append(row);
    p.append(pic, info);
    return p;
  }
  async function addToCart(o) {
    try {
      const r = await api("/api/shop/add", { offer: { store: o.store, title: o.title, price: o.price, url: o.url } });
      remember(r);
      if (state.view !== "chat") go("chat");
      if (r.state === "pending") {
        pushLocal(state.thread, { role: "luma", text: `Want me to add this to your ${o.store} cart?`, result: r });
        mood("waiting", "Waiting for your OK");
      } else {
        pushLocal(state.thread, { role: "luma", text: r.summary || "Done.", result: r });
        mood("happy", "Added to cart", 3500);
      }
    } catch (e) { toast(e.message); }
  }

  function remember(r) { if (r && r.action && r.confirm_token) state.tokens[r.action] = r.confirm_token; }
  function pendingIds() { return new Set((state.home?.approvals || []).map((a) => a.id)); }

  const WANTS = {
    "shop.add_to_cart": ["Checkout", "add this to your cart"], "mail.send": ["Email", "send this email"], "luma.send": ["Text", "send this text"],
    "sms.send": ["Text", "send this text"], "mac_messages.send": ["Text", "send this text"], "browser.act": ["Website", "do this on a website"],
    "booking.create": ["Booking", "book this"], "home.light": ["Home", "change your lights"], "food.checkout": ["Groceries", "set up this checkout"],
  };
  const ROUTES = { luma_number: "From Luma's number", mac_imessage: "From your iMessage", mac_sms: "From your number (SMS)", twilio: "From your Twilio number" };
  const TEXTY = ["luma.send", "sms.send", "mac_messages.send"];

  // Muse-style: "Checkout · Luma wants to…", the item as it looks on the store, then Deny / Allow.
  function approval(r) {
    const a = r.arguments || {};
    const [kind, verb] = WANTS[r.tool] || ["Action", "do this"];
    const c = el("div", "card checkout");
    const head = el("div", "co-head");
    const hic = el("span", "chip-ic");
    hic.append(icon(r.tool === "shop.add_to_cart" ? "cart" : r.tool === "mail.send" ? "mail" : TEXTY.includes(r.tool) ? "message" : "rules"));
    const where = r.tool === "shop.add_to_cart" ? ` at ${host(a.url) || a.store}`
      : (r.tool === "mail.send" || TEXTY.includes(r.tool)) ? ` to ${r.recipient_name || a.to}`
      : r.tool === "browser.act" ? ` on ${host(String(a.page || "").split(" — ").pop()) || "a website"}` : "";
    const line = el("div");
    line.append(el("b", null, kind), el("span", "muted", ` · Luma wants to ${verb}${where}`));
    head.append(hic, line);
    c.append(head);
    const sub = {
      "shop.add_to_cart": "Check the item and price before you allow it. Checkout and payment always stay with you.",
      "mail.send": "These are the exact words that will go out. It's in your Drafts too.",
      "browser.act": a.reason ? `Why I'm asking: ${a.reason}.` : "Nothing happens on the site until you allow it.",
    }[r.tool] || (TEXTY.includes(r.tool) ? (ROUTES[state.status?.message_route] || "Every text waits for you") + ". These are the exact words." : "Nothing happens until you allow it.");
    c.append(el("div", "co-sub", sub));

    if (r.tool === "shop.add_to_cart") {
      const o = state.offers.get(a.url) || {};
      const page = el("div", "co-page");
      const bar = el("div", "co-bar");
      bar.append(el("span", "fav", (a.store || "?")[0]), el("b", null, a.store || host(a.url)), document.createTextNode(host(a.url) ? "  ·  " + host(a.url) : ""));
      const body = el("div", "co-body");
      const pic = el("div", "co-pic");
      pic.append(picture(o.image, a.title) || el("div", "ph", (a.store || "?")[0]));
      const info = el("div", "co-info");
      const press = el("span", "press");
      press.append(icon("cart"), document.createTextNode("Luma will press Add to cart"));
      info.append(el("div", "store", a.store), el("div", "title", a.title), el("div", "price", a.price), press);
      body.append(pic, info);
      page.append(bar, body);
      c.append(page);
      const rows = el("div", "co-rows");
      const row = (ic, label, value) => { const r2 = el("div", "co-row"); r2.append(icon(ic), el("span", "grow", label), el("span", "v", value)); rows.append(r2); };
      row("card", "Payment", "You check out yourself");
      row("tag", "Item price", a.price);
      c.append(rows);
    } else if (r.tool === "mail.send") {
      const mail = el("div", "co-mail");
      for (const [k, v] of [["To", r.recipient_name ? `${r.recipient_name} <${a.to}>` : a.to], ["Subject", a.subject || "(no subject)"]]) {
        const row = el("div", "row");
        row.append(el("b", null, k), el("span", null, v));
        mail.append(row);
      }
      mail.append(el("div", "body", a.body));
      c.append(mail);
    } else if (TEXTY.includes(r.tool)) {
      c.append(phone(r.recipient_name || a.to, a.body));
    } else if (r.tool === "browser.act") {
      const rows = el("div", "co-rows");
      const r1 = el("div", "co-row");
      r1.append(icon("hand"), el("span", "grow", a.kind === "type" ? `Type “${a.text}” into “${a.label}”` : `Press “${a.label || "this button"}”`));
      const r2 = el("div", "co-row");
      r2.append(icon("globe"), el("span", "grow", a.page || ""));
      rows.append(r1, r2);
      c.append(rows);
    } else {
      const rows = el("div", "co-rows");
      for (const [k, v] of Object.entries(r.review || a)) if (typeof v === "string" || typeof v === "number") { const rr = el("div", "co-row"); rr.append(el("span", "grow", k.replace(/_/g, " ")), el("span", "v", String(v))); rows.append(rr); }
      c.append(rows);
    }

    const lineEl = el("span", "state-line");
    const foot = el("div", "co-foot");
    foot.append(lineEl);
    const actions = el("div", "co-actions");
    const finish = (text, ok) => {
      state.outcomes[r.action] = { text, ok };
      c.classList.add("done");
      lineEl.textContent = text;
      lineEl.classList.toggle("ok", Boolean(ok));
    };
    const token = r.confirm_token || state.tokens[r.action] || (state.home?.approvals || []).find((x) => x.id === r.action)?.confirm_token;
    const deny = btn("Deny", "pill deny", async () => {
      try { await api("/api/cancel", { id: r.action }); } catch (_) { /* already gone */ }
      finish("Denied. Nothing went out.", false);
      mood("idle", "Here with you");
      refreshHome();
    });
    const allow = btn("Allow", "pill blue", async () => {
      if (!token) { finish("Ask me again to get a fresh approval.", false); return; }
      allow.disabled = deny.disabled = true;
      lineEl.textContent = "Working on it…";
      mood("working", r.tool === "shop.add_to_cart" ? "Adding to your cart" : "Sending");
      try {
        const done = await api("/api/confirm", { id: r.action, token });
        const ok = done.state === "succeeded";
        finish(ok ? (done.verified === false ? "Pressed, but couldn't confirm it landed" : "Done ✓") : done.state === "handoff" ? "Over to you" : done.state === "unknown" ? "Not sure it went through" : "Didn't go through", ok);
        pushLocal(state.thread, { role: "luma", text: done.text || done.summary || (ok ? "Done." : "That didn't go through."), result: { cart: done.cart, url: done.url } });
        mood(ok ? "happy" : "idle", ok ? "Done" : "Here with you", ok ? 3500 : 0);
        refreshHome();
      } catch (e) { allow.disabled = deny.disabled = false; lineEl.textContent = e.message; mood("idle", "Here with you"); }
    });
    actions.append(deny, allow);
    if (TEXTY.includes(r.tool) || r.tool === "mail.send") {
      const spacer = el("span");
      spacer.style.flex = "1";
      foot.append(spacer, btn("Edit", "pill quiet small", () => edit(c, r), "compose"));
    }
    c.append(actions, foot);

    const outcome = state.outcomes[r.action];
    if (outcome) finish(outcome.text, outcome.ok);
    else if (!token && state.home && !pendingIds().has(r.action)) finish("No longer waiting", false);
    else if (r.expires && r.expires * 1000 < Date.now()) finish("This one expired. Ask me again.", false);
    return c;
  }

  function edit(card, r) {
    const a = r.arguments || {};
    const box = el("div", "co-edit");
    const area = el("textarea");
    area.value = a.body || "";
    const actions = el("div", "actions");
    actions.append(btn("Use this", "pill primary", async () => {
      try {
        await api("/api/cancel", { id: r.action }).catch(() => {});
        const next = r.tool === "mail.send"
          ? await api("/api/mail/compose", { to: a.to, subject: a.subject, body: area.value.trim(), reply_to_id: a.reply_to_id || "" })
          : await api("/api/messages/prepare", { recipient: a.to, body: area.value.trim() });
        remember(next);
        state.outcomes[r.action] = { text: "Edited", ok: false };
        pushLocal(state.thread, { role: "luma", text: next.text || "Here's the new version.", result: { ...next, recipient_name: r.recipient_name } });
      } catch (e) { toast(e.message); }
    }), btn("Cancel", "pill quiet", () => renderChat()));
    box.append(el("span", "label", "Edit before it goes out"), area, actions);
    card.querySelector(".co-mail, .phone")?.replaceWith(box);
    card.querySelector(".co-actions")?.remove();
    card.querySelector(".co-foot")?.remove();
    area.focus();
  }

  function phone(name, body) {
    const p = el("div", "phone");
    p.append(el("div", "to", "To: " + (name || "them")), el("div", "sms", body));
    return p;
  }
  function draftCard(d, quota) {
    const c = el("div", "card box");
    c.append(el("span", "label", quota ? "Out of free texts this month: send it yourself" : "Ready for you to send"));
    const p = phone(d.name || d.to, d.body);
    p.style.margin = "0";
    c.append(p);
    const actions = el("div", "actions");
    if (d.to) { const a = el("a", "pill primary small", "Open in Messages"); a.href = `sms:${d.to}&body=${encodeURIComponent(d.body)}`; actions.append(a); }
    actions.append(btn("Copy", "pill soft small", async () => { await navigator.clipboard.writeText(d.body).catch(() => {}); toast("Copied"); }, "copy"));
    c.append(actions);
    return c;
  }
  function deckCard(f) {
    const c = el("div", "card box");
    const head = el("div", "card-head");
    const t = el("div");
    t.append(el("div", "t", f.title || f.name), el("div", "s", `${f.slides || (f.outline || []).length} slides · speaker notes included`));
    head.append(chip("update", "deck", "chip-ic"), t, el("span", "spacer"));
    const dl = el("a", "pill primary small");
    dl.append(icon("down"), document.createTextNode("Download"));
    dl.href = f.url;
    head.append(dl);
    c.append(head, slides(f));
    return c;
  }
  function slides(f) {
    const box = el("div", "slides");
    (f.outline || []).slice(0, 12).forEach((s, i) => {
      const tile = el("div", `slide theme-${f.theme || "midnight"}`);
      tile.append(el("span", "k", `${i + 1} · ${String(s.layout || "slide").replace("_", " ")}`));
      if (s.title) tile.append(el("span", "t", s.title));
      if (s.big) tile.append(el("span", s.layout === "quote" ? "q" : "n", s.layout === "quote" ? `“${s.big}”` : s.big));
      if (s.points?.length) { const ul = el("ul"); s.points.slice(0, 3).forEach((p) => ul.append(el("li", null, p))); tile.append(ul); }
      box.append(tile);
    });
    return box;
  }
  function initials(name) { return String(name || "?").replace(/<.*>/, "").trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase() || "?"; }
  const FACE = ["k-inbox", "k-deal", "k-feed", "k-today", "k-people"];
  function face(name) {
    let h = 0;
    for (const ch of String(name)) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return el("span", "face " + FACE[h % FACE.length], initials(name));
  }
  function replyTo(from) { go("chat"); $("input").value = `reply to ${String(from).split(" ")[0]} saying `; resize(); $("input").focus(); }
  function mailCard(messages) {
    const c = el("div", "card box");
    const rows = el("div", "rows");
    for (const m of messages.slice(0, 8)) {
      const r = el("div", "r");
      const g = el("div", "grow");
      g.append(el("div", "t", `${m.from} · ${m.subject}`), el("div", "s", m.snippet || ""));
      r.append(face(m.from), g, btn("Reply", "pill quiet small", () => replyTo(m.from), "reply"));
      rows.append(r);
    }
    c.append(rows);
    return c;
  }
  function agendaCard(events) {
    const c = el("div", "card box");
    if (!events.length) { c.append(el("div", "checked", "Nothing on the calendar.")); return c; }
    const rows = el("div", "rows");
    for (const e of events.slice(0, 10)) {
      const r = el("div", "r");
      r.append(el("div", "when", e.all_day ? "All day" : e.time || clock.format(new Date(e.start * 1000))));
      const g = el("div", "grow");
      g.append(el("div", "t", e.title), el("div", "s", [new Date(e.start * 1000).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" }), e.location].filter(Boolean).join(" · ")));
      r.append(g);
      rows.append(r);
    }
    c.append(rows);
    return c;
  }
  function helperChip(h) {
    const c = el("div", "card box");
    const head = el("div", "card-head");
    const meta = HELPER[h.kind] || HELPER.goal;
    const t = el("div");
    t.append(el("div", "t", h.title), el("div", "s", `${meta.label} · ${EVERY[h.every] || ""}${h.at ? " at " + h.at : ""}`));
    head.append(chip(meta.k, meta.icon, "chip-ic"), t, el("span", "spacer"), btn("See Goals", "pill soft small", () => go("goals")));
    c.append(head);
    return c;
  }

  // ------------------------------------------------- Luma's computer ---
  function computer(a, big) {
    const finished = ["done", "failed", "stopped"].includes(a.state);
    const c = el("section", "card computer" + (big ? " big" : "") + (a.state === "paused" ? " paused" : finished ? " done" : ""));
    const chrome = el("div", "chrome");
    const lights = el("span", "lights");
    lights.append(el("i"), el("i"), el("i"));
    const url = el("div", "url");
    url.append(icon("lock"));
    if (a.url) {
      let path = "";
      try { const u = new URL(a.url); path = u.pathname + u.search; } catch (_) { /* odd url */ }
      url.append(el("b", null, host(a.url)), document.createTextNode(path.slice(0, 48)));
    } else url.append(document.createTextNode("Opening Luma's browser…"));
    const live = el("span", "live" + (a.state === "paused" ? " paused" : finished ? " done" : ""));
    live.append(el("i"), document.createTextNode({ running: "Live", paused: "Paused", stopping: "Stopping", done: "Done", stopped: "Stopped", failed: "Stopped" }[a.state] || "Live"));
    chrome.append(lights, url, live);
    c.append(chrome);
    const screen = el("div", "screen");
    if (a.shot) {
      const img = el("img");
      img.alt = a.page_title ? `What Luma sees: ${a.page_title}` : "What Luma sees";
      img.src = "/api/activity/shot?n=" + a.shot + "&id=" + a.id;
      screen.append(img);
    }
    screen.append(el("span", "cursor"));
    c.append(screen);
    const below = el("div", "below");
    below.append(el("div", "title", a.title));
    const steps = el("div", "steps");
    const all = a.steps || [];
    all.forEach((s, i) => {
      const now = ["running", "paused"].includes(a.state) && i === all.length - 1 && !s.done;
      const row = el("div", "step" + (s.done ? " done" : now ? " now" : ""));
      row.append(el("span", "s"), el("span", null, s.text));
      steps.append(row);
    });
    below.append(steps);
    if (["running", "paused", "stopping"].includes(a.state)) {
      const controls = el("div", "controls");
      if (a.state === "paused") controls.append(btn("Resume", "pill soft", () => control("resume"), "play"));
      else controls.append(btn("Pause", "pill soft", () => control("pause"), "pause"));
      controls.append(btn("Stop", "pill soft", () => control("stop"), "stop"));
      controls.append(btn("Take over", "pill soft", () => control("show"), "hand"));
      below.append(controls);
    } else if (a.summary) below.append(el("div", "checked", a.summary));
    c.append(below);
    requestAnimationFrame(() => { steps.scrollTop = steps.scrollHeight; });
    return c;
  }
  async function control(action) {
    try {
      const r = await api("/api/activity/control", { action });
      state.activity = r.activity;
      if (r.summary) toast(r.summary);
      paintActivity(true);
    } catch (e) { toast(e.message); }
  }
  let lastPaint = "";
  function paintActivity(force) {
    const a = state.activity;
    const key = a ? [a.id, a.state, a.shot, (a.steps || []).length, (a.steps || []).filter((s) => s.done).length].join(":") : "";
    if (key === lastPaint && !force) return;
    lastPaint = key;
    const running = a && ["running", "paused", "stopping"].includes(a.state);
    const recent = a && (running || (a.finished && Date.now() / 1000 - a.finished < 45));
    const inline = state.busy && a && !a.background && running;
    const w = $("w-computer");
    if (recent && !inline) {
      const c = computer(a, false);
      w.className = c.className.replace("card", "widget");
      w.replaceChildren(...c.childNodes);
      w.hidden = false;
    } else w.hidden = true;
    if (state.busy && state.view === "chat") renderChat();
    if (running) $("doing").textContent = (a.background ? "In the background: " : "") + a.title;
  }
  let activityTimer = null;
  function watchActivity(on) {
    clearInterval(activityTimer);
    activityTimer = null;
    if (!on) return;
    activityTimer = setInterval(async () => {
      try {
        const d = await api("/api/activity");
        state.activity = d.activity;
        paintActivity();
        if (!state.busy && (!d.activity || !["running", "paused", "stopping"].includes(d.activity.state))) watchActivity(false);
      } catch (_) { /* the next home poll will notice */ }
    }, 900);
  }

  // ------------------------------------------------------------- talk ---
  async function send(text) {
    text = String(text || "").trim();
    if (!text || state.busy) return;
    if (state.view !== "chat") go("chat");
    const thread = state.thread;
    pushLocal(thread, { role: "you", text, optimistic: true });
    state.busy = true;
    mood("thinking", guessDoing(text));
    renderChat();
    resize();
    watchActivity(true);
    try {
      const r = await api("/api/chat", { text, thread });
      remember(r);
      if (r.event_id) state.seen.add(r.event_id);
      await loadThread(thread);
      state.local[thread] = (state.local[thread] || []).filter((m) => !m.optimistic);
      if (r.state === "pending") mood("waiting", "Waiting for your OK");
      else if (r.state === "stopped") mood("idle", "Stopped");
      else if (r.kind === "shopping" && r.best) mood("happy", "Found it for " + money(r.best.price), 5000);
      else if (r.file || r.helper || r.state === "succeeded" || r.task) mood("happy", "Done", 3500);
      else mood("idle", "Here with you");
      if (r.open === "apps") setTimeout(() => go("apps"), 900);
    } catch (e) {
      state.local[thread] = (state.local[thread] || []).filter((m) => !m.optimistic);
      pushLocal(thread, { role: "you", text });
      pushLocal(thread, { role: "luma", text: e.status ? e.message : "I can't reach my brain right now. Is Luma running?" });
      mood(e.status ? "idle" : "sleepy", e.status ? "Here with you" : "Can't reach Luma");
    } finally {
      state.busy = false;
      state.stick = true;
      renderChat();
      resize();
      refreshHome();
    }
  }

  // -------------------------------------------------------------- nav ---
  function go(view) {
    state.view = view;
    if (location.hash.slice(1) !== view) history.replaceState(null, "", view === "chat" ? location.pathname : "#" + view);
    for (const b of document.querySelectorAll(".nav-item")) b.classList.toggle("active", b.dataset.view === view && (view !== "chat" || state.thread === "main"));
    for (const b of document.querySelectorAll(".thread-item")) b.classList.toggle("active", view === "chat" && b.dataset.id === state.thread);
    for (const v of document.querySelectorAll(".view")) v.hidden = v.id !== "view-" + view;
    $("center").classList.toggle("page-mode", view !== "chat");
    $("top-title").hidden = view === "chat";
    $("top-title").textContent = TITLES[view] || "";
    if (view === "chat") { renderChat(); $("input").focus(); }
    else renderView(view);
  }
  for (const b of document.querySelectorAll(".nav-item")) b.addEventListener("click", () => {
    if (b.dataset.view === "chat" && state.thread !== "main") { state.thread = "main"; loadThread("main").then(() => go("chat")); return; }
    go(b.dataset.view);
  });
  $("open-settings").addEventListener("click", () => go("settings"));
  $("top-apps").addEventListener("click", () => go("apps"));
  $("top-rules").addEventListener("click", () => go("rules"));
  $("top-theme").addEventListener("click", () => setTheme(darkNow(theme) ? "light" : "dark"));
  $("top-new").addEventListener("click", newChat);
  $("new-chat").addEventListener("click", newChat);
  $("who").addEventListener("click", () => { if (state.view !== "chat") go("chat"); });
  $("add").addEventListener("click", () => openPalette(""));
  async function newChat() {
    try {
      const t = await api("/api/threads/new", {});
      state.transcripts[t.id] = [];
      state.thread = t.id;
      await refreshHome();
      go("chat");
    } catch (e) { toast(e.message); }
  }
  function renderThreads() {
    const box = $("threads");
    box.replaceChildren();
    const threads = (state.home?.threads || []).filter((x) => x.id !== "main");
    if (!threads.length) {
      const hint = el("button", "thread-item hint", "Start a side chat for anything you want to keep separate.");
      hint.type = "button";
      hint.addEventListener("click", newChat);
      box.append(hint);
    }
    for (const t of threads) {
      const b = el("button", "thread-item" + (state.view === "chat" && state.thread === t.id ? " active" : ""));
      b.type = "button";
      b.dataset.id = t.id;
      b.append(el("span", null, t.title));
      const x = el("span", "x");
      x.append(icon("x"));
      x.title = "Delete chat";
      x.addEventListener("click", async (e) => {
        e.stopPropagation();
        try { await api("/api/threads/delete", { id: t.id }); if (state.thread === t.id) { state.thread = "main"; await loadThread("main"); } await refreshHome(); if (state.view === "chat") renderChat(); } catch (err) { toast(err.message); }
      });
      b.append(x);
      b.addEventListener("click", async () => { state.thread = t.id; await loadThread(t.id); go("chat"); });
      box.append(b);
    }
  }

  // ----------------------------------------------------------- widgets ---
  function wHead(iconName, title, opts = {}) {
    const h = el("div", "w-head");
    h.append(icon(iconName), el("b", null, title));
    if (opts.meta) h.append(el("span", "meta", opts.meta));
    if (opts.go) { const g = btn("", "go", opts.go, "external"); g.title = opts.goTitle || "Open"; g.setAttribute("aria-label", g.title); h.append(g); }
    return h;
  }
  function renderWidgets() {
    const h = state.home;
    if (!h) return;
    const today = h.today || {};
    const now = Date.now() / 1000;

    // Waiting on you: Muse's approvals, small
    const ap = $("w-approvals");
    const approvals = h.approvals || [];
    ap.hidden = !approvals.length;
    ap.replaceChildren(wHead("rules", "Waiting on you", { meta: String(approvals.length) }));
    for (const a of approvals.slice(0, 3)) {
      if (a.confirm_token) state.tokens[a.id] = a.confirm_token;
      const args = a.arguments || {};
      const card = el("button", "wait-card");
      card.type = "button";
      const o = state.offers.get(args.url) || {};
      const ph = el("span", "ph");
      ph.append(icon(a.tool === "mail.send" ? "mail" : TEXTY.includes(a.tool) ? "message" : "cart"));
      card.append(picture(o.image) || ph);
      const g = el("div", "grow");
      const what = WANTS[a.tool] || ["Action", "do this"];
      g.append(el("div", "t", what[0] === "Checkout" ? `Add to cart${args.price ? " · " + args.price : ""}` : what[0] === "Email" ? `Email to ${a.recipient_name || args.to}` : what[0] === "Text" ? `Text to ${a.recipient_name || args.to}` : what[0]),
               el("div", "s", args.title || args.subject || args.body || args.label || ""));
      card.append(g, el("span", "status blue", "Review"));
      card.addEventListener("click", () => {
        go("chat");
        pushLocal(state.thread, { role: "luma", text: "Here's what's waiting on you.", result: { ...a, state: "pending", action: a.id, confirm_token: a.confirm_token } });
      });
      ap.append(card);
    }

    // Up next: two big time tiles (Muse's "Webinars")
    const next = $("w-next");
    next.replaceChildren(wHead("calendar", today.date || "Today", { go: () => send("what's on my calendar today?"), goTitle: "Ask Luma about today" }));
    const upcoming = (today.events || []).filter((e) => e.all_day || e.end > now);
    const tiles = el("div", "tiles2");
    const two = upcoming.slice(0, 2).map((e) => ({ big: e.all_day ? "All day" : e.time || clock.format(new Date(e.start * 1000)), t: e.title, s: e.location || "Calendar" }));
    for (const t of (today.tasks || [])) { if (two.length >= 2) break; two.push({ big: clock.format(new Date(t.due * 1000)), t: t.title, s: "Reminder" }); }
    for (const it of two) { const tile = el("div", "ttile"); tile.append(el("div", "big", it.big), el("div", "t", it.t), el("div", "s", it.s)); tiles.append(tile); }
    if (two.length < 2) {
      const tile = el("div", "ttile empty-tile");
      if (h.connections?.calendar?.connected) tile.append(document.createTextNode("Nothing else today"));
      else { tile.append(document.createTextNode("Connect your calendar")); tile.append(btn("Apps", "link", () => go("apps"))); }
      tiles.append(tile);
    }
    next.append(tiles);
    for (const e of upcoming.slice(2, 5)) {
      const r = el("div", "wrow");
      const g = el("div", "grow");
      g.append(el("div", "t", e.title), el("div", "s", e.location || ""));
      r.append(g, el("span", "status grey", e.all_day ? "All day" : e.time || ""));
      next.append(r);
    }

    // Tasks with toggles and status pills (Muse's dashboard)
    const tw = $("w-tasks");
    const tasks = today.tasks || [];
    tw.replaceChildren(wHead("list", "Tasks", { go: () => { go("chat"); $("input").value = "remind me "; resize(); $("input").focus(); }, goTitle: "Add a reminder" }));
    if (!tasks.length) tw.append(el("div", "none", "Nothing due. Try “remind me at 6 to grab flowers.”"));
    for (const t of tasks.slice(0, 5)) {
      const r = el("div", "wrow");
      const sw = el("button", "switch small");
      sw.setAttribute("role", "switch");
      sw.setAttribute("aria-checked", "false");
      sw.setAttribute("aria-label", "Done: " + t.title);
      sw.addEventListener("click", async () => { sw.setAttribute("aria-checked", "true"); try { await api("/api/task/complete", { id: t.id }); setTimeout(() => r.remove(), 300); } catch (e) { sw.setAttribute("aria-checked", "false"); toast(e.message); } });
      const g = el("div", "grow");
      g.append(el("div", "t", t.title), el("div", "s", t.when || ""));
      const overdue = t.due < now;
      const soon = t.due - now < 3 * 3600;
      r.append(sw, g, el("span", "status " + (overdue ? "red" : soon ? "amber" : "grey"), overdue ? "Overdue" : soon ? "Soon" : "To-do"));
      tw.append(r);
    }

    // Goals
    const gw = $("w-goals");
    gw.replaceChildren(wHead("goals", "Goals", { go: () => go("goals"), goTitle: "See all goals" }));
    for (const g of (h.helpers || []).slice(0, 4)) {
      const meta = HELPER[g.kind] || HELPER.goal;
      const r = el("div", "wrow");
      const t = el("div", "grow");
      t.append(el("div", "t", g.title), el("div", "s", g.last_error ? "Hit a snag" : g.last_result || (g.enabled ? "Next " + until(g.next_run) : "Paused")));
      r.append(chip(meta.k, meta.icon), t, el("span", "status " + (!g.enabled ? "grey" : g.last_error ? "red" : "green"), !g.enabled ? "Paused" : g.last_error ? "Check" : "On"));
      gw.append(r);
    }
    if (!(h.helpers || []).length) {
      const n = el("div", "none");
      n.append(document.createTextNode("Nothing running on its own yet. "), btn("Add a goal", "link", () => go("goals")));
      gw.append(n);
    }

    const unread = (h.cards || []).filter((c) => !c.read).length;
    $("feed-badge").hidden = !unread;
    $("feed-badge").textContent = unread;
    const active = (h.helpers || []).filter((g) => g.enabled).length;
    $("goals-badge").hidden = !active;
    $("goals-badge").textContent = active;
  }

  // -------------------------------------------------------------- feed ---
  function cardImage(c) { return (c.items || []).map((i) => i.image).find(safeImg); }
  function renderFeed() {
    const list = $("feed-list");
    const cards = state.home?.cards || [];
    list.replaceChildren();
    if (!state.feedSel || !cards.some((c) => c.id === state.feedSel)) state.feedSel = cards[0]?.id || null;
    for (const c of cards) {
      const meta = KIND[c.kind] || KIND.update;
      const b = el("button", "fcard" + (c.id === state.feedSel ? " active" : ""));
      b.type = "button";
      const who = el("div", "who-row");
      const g = el("div", "grow");
      const src = el("div", "src");
      if (!c.read) src.append(el("span", "unread-dot"));
      src.append(document.createTextNode(meta.label));
      g.append(src, el("div", "time", ago(c.created)));
      const arrow = el("span", "arrow");
      arrow.append(icon("external"));
      who.append(chip(c.kind in KIND ? c.kind : "update", meta.icon, "face"), g, arrow);
      b.append(who, el("div", "ttl", c.title));
      const img = cardImage(c);
      if (img) {
        const pv = el("div", "preview");
        pv.append(picture(img));
        if (c.items?.[0]?.price) pv.append(el("span", "price-chip", money(c.items[0].price) + " · " + c.items[0].store));
        b.append(pv);
      } else if (c.body) b.append(el("div", "snip", c.body));
      b.addEventListener("click", () => { state.feedSel = c.id; renderFeed(); });
      list.append(b);
    }
    if (!cards.length) list.append(el("p", "lede", "Nothing yet. Set up a goal and I'll leave what I find here."));
    renderReader(cards.find((c) => c.id === state.feedSel));
  }
  function renderReader(c) {
    const r = $("reader");
    r.replaceChildren();
    if (!c) {
      const e = el("div", "empty-reader");
      e.append(bigAvatar(), el("h2", null, "Your feed"), el("p", null, "Deals I find, inbox summaries and catch-ups land here."));
      e.append(btn("Set up a goal", "pill primary", () => go("goals")));
      r.append(e);
      return;
    }
    if (!c.read) api("/api/cards/read", { id: c.id }).then(() => { c.read = true; renderWidgets(); }).catch(() => {});
    const meta = KIND[c.kind] || KIND.update;
    const top = el("div", "r-top");
    top.append(btn("Remove", "", async () => { try { await api("/api/cards/delete", { id: c.id }); state.feedSel = null; await refreshHome(); renderFeed(); } catch (e) { toast(e.message); } }, "trash"));
    top.append(el("span", null, new Date(c.created * 1000).toLocaleString(undefined, { weekday: "long", month: "long", day: "numeric", hour: "numeric", minute: "2-digit" })));
    const hero = el("div", "r-hero");
    hero.append(chip(c.kind in KIND ? c.kind : "update", meta.icon, "face"), el("h1", null, c.title), el("div", "s", `${meta.label} · ${ago(c.created)}`));
    const acts = el("div", "r-acts");
    acts.append(btn("Ask Luma", "r-act", () => { go("chat"); $("input").value = `About “${c.title}”: `; resize(); $("input").focus(); }, "chat"));
    if (safeUrl(c.url)) acts.append(linkOut("Open", c.url, "r-act", "external"));
    const upB = btn("", "r-act icon-only" + (c.feedback === "up" ? " on" : ""), () => rate("up"), "up_t");
    const downB = btn("", "r-act icon-only" + (c.feedback === "down" ? " on" : ""), () => rate("down"), "down_t");
    upB.title = "Useful"; downB.title = "Not for me";
    upB.setAttribute("aria-label", "Useful"); downB.setAttribute("aria-label", "Not for me");
    acts.append(upB, downB);
    const body = el("div", "r-body");
    if (c.body) body.append(el("div", "r-text", c.body));
    if (c.kind === "deal" && (c.items || []).length) {
      const grid = el("div", "products");
      c.items.forEach((o, i) => { if (o.url) state.offers.set(o.url, o); grid.append(productTile(o, i === 0)); });
      body.append(grid);
    }
    if (c.kind === "inbox" && (c.items || []).length) {
      const rows = el("div", "rows");
      for (const m of c.items) {
        const row = el("div", "r");
        const g = el("div", "grow");
        g.append(el("div", "t", `${m.from} · ${m.title}`), el("div", "s", m.snippet || ""));
        row.append(face(m.from), g, btn("Reply", "pill quiet small", () => replyTo(m.from), "reply"));
        rows.append(row);
      }
      body.append(rows);
    }
    if (safeUrl(c.url)) {
      const at = el("div", "attach");
      const a = linkOut("", c.url, "", "globe");
      const t = el("span");
      t.append(document.createTextNode(host(c.url)), el("small", null, "Open the page"));
      a.append(t);
      at.append(a);
      body.append(at);
    }
    const reply = el("form", "r-reply");
    const note = el("input");
    note.placeholder = "Tell Luma what you'd rather see…";
    note.maxLength = 300;
    const sendB = el("button", "send");
    sendB.type = "submit";
    sendB.setAttribute("aria-label", "Teach Luma");
    sendB.append(icon("up"));
    reply.append(note, sendB);
    reply.addEventListener("submit", (e) => { e.preventDefault(); if (note.value.trim()) rate(c.feedback || "down", note.value); });
    r.append(top, hero, acts, body, reply);
    async function rate(value, text) {
      try {
        const res = await api("/api/feedback", { id: c.id, value, note: text || "" });
        c.feedback = value;
        toast(res.summary);
        renderReader(c);
      } catch (e) { toast(e.message); }
    }
  }

  // ------------------------------------------------------------- ideas ---
  function renderIdeas() {
    const box = $("ideas");
    box.replaceChildren();
    for (const i of state.home?.ideas || []) {
      const k = i.kind in KIND ? i.kind : "idea";
      const c = el("div", "idea card");
      c.append(chip(k, (KIND[k] || KIND.idea).icon, "ic"), el("h3", null, i.title), el("p", null, i.why));
      const setup = /^connect my (email|calendar)$/.test(i.say);
      c.append(btn(setup ? "Set it up" : "Do it", "pill small " + (setup ? "soft" : "primary"), () => setup ? go("apps") : send(i.say)));
      box.append(c);
    }
  }

  // ------------------------------------------------------------- goals ---
  let goalKind = "price_watch";
  function renderGoals() {
    const form = $("goal-form");
    form.replaceChildren();
    const head = el("div", "card-head");
    head.append(chip("update", "plus", "chip-ic"), el("div", "t", "New goal"));
    form.append(head);
    const seg = el("div", "segmented");
    for (const [k, label] of [["price_watch", "Price watch"], ["inbox_digest", "Inbox"], ["feed_digest", "Feed"], ["agenda", "Morning agenda"], ["goal", "Anything"]]) {
      seg.append(btn(label, goalKind === k ? "on" : "", () => { goalKind = k; renderGoals(); }));
    }
    form.append(seg);
    const fields = el("div", "fields");
    const field = (label, input, wide) => { const f = el("label", "field" + (wide ? " wide" : "")); f.append(document.createTextNode(label), input); fields.append(f); return input; };
    const text = (name, placeholder) => { const i = el("input"); i.name = name; i.placeholder = placeholder; i.maxLength = 300; return i; };
    let q, target, site, goal;
    if (goalKind === "price_watch") { q = field("Product", text("query", "AirPods Pro 2"), true); target = field("Tell me under ($)", text("target", "180")); target.inputMode = "numeric"; }
    if (goalKind === "feed_digest") {
      site = el("select");
      for (const s of ["instagram", "tiktok", "x", "reddit", "linkedin", "youtube", "facebook"]) { const o = el("option", null, s[0].toUpperCase() + s.slice(1)); o.value = s; site.append(o); }
      field("Site", site);
    }
    if (goalKind === "goal") goal = field("What should I keep working on?", text("goal", "Find a cheaper phone plan than my $85 one"), true);
    const every = el("select");
    for (const [v, label] of Object.entries(EVERY)) { const o = el("option", null, label); o.value = v; every.append(o); }
    every.value = "daily";
    field("How often", every);
    const at = el("input");
    at.type = "time"; at.value = goalKind === "feed_digest" ? "18:00" : "08:00";
    field("At", at);
    every.addEventListener("change", () => { at.disabled = !["daily", "weekly"].includes(every.value); });
    fields.append(btn("Start", "pill primary", async () => {
      try {
        const body = { kind: goalKind, every: every.value, at: at.disabled ? null : at.value };
        if (q) body.query = q.value.trim();
        if (target && target.value.trim()) body.target = Number(target.value.replace(/[^\d.]/g, ""));
        if (site) body.site = site.value;
        if (goal) body.goal = goal.value.trim();
        await api("/api/helpers/create", body);
        toast("Started. I'll run it now and then on schedule.");
        await refreshHome();
        renderGoals();
      } catch (e) { toast(e.message); }
    }, "play"));
    form.append(fields);

    const box = $("goals");
    box.replaceChildren();
    for (const g of state.home?.helpers || []) {
      const meta = HELPER[g.kind] || HELPER.goal;
      const c = el("div", "goal card" + (g.enabled ? "" : " off"));
      const top = el("div", "top");
      const t = el("div");
      t.style.flex = "1"; t.style.minWidth = "0";
      t.append(el("div", "t", g.title), el("div", "s", `${meta.label} · ${EVERY[g.every] || ""}${g.at ? " at " + g.at : ""}`));
      const sw = el("button", "switch");
      sw.setAttribute("role", "switch");
      sw.setAttribute("aria-checked", String(Boolean(g.enabled)));
      sw.setAttribute("aria-label", "On");
      sw.addEventListener("click", async () => { try { await api("/api/helpers/update", { id: g.id, enabled: !g.enabled }); await refreshHome(); renderGoals(); } catch (e) { toast(e.message); } });
      top.append(chip(meta.k, meta.icon, "ic"), t, sw);
      c.append(top);
      if (g.last_error) c.append(el("div", "result err", g.last_error));
      else if (g.last_result) c.append(el("div", "result", g.last_result));
      const prices = (g.history || []).map((x) => x.price).filter((p) => typeof p === "number");
      if (prices.length > 1) c.append(spark(prices));
      const foot = el("div", "actions");
      const firstRun = g.next_run - Date.now() / 1000 > 60 ? "First run " + until(g.next_run) : "Starting…";
      const when = el("span", "s", g.enabled ? (g.runs ? `Ran ${g.runs}× · next ${until(g.next_run)}` : firstRun) : "Paused");
      when.style.flex = "1"; when.style.color = "var(--muted)"; when.style.fontSize = "12.5px";
      foot.append(when);
      foot.append(btn("Run now", "pill quiet small", async () => { try { await api("/api/helpers/update", { id: g.id, run_now: true }); toast("Running it now."); refreshHome(); } catch (e) { toast(e.message); } }, "refresh"));
      const del = btn("", "pill quiet small", async () => { try { await api("/api/helpers/delete", { id: g.id }); await refreshHome(); renderGoals(); } catch (e) { toast(e.message); } }, "trash");
      del.setAttribute("aria-label", "Delete goal");
      foot.append(del);
      c.append(foot);
      box.append(c);
    }
    if (!(state.home?.helpers || []).length) box.append(el("p", "lede", "No goals yet. Try a price watch: I'll check every day and tell you when it drops."));
  }
  function spark(values) {
    const w = 260, h = 34, min = Math.min(...values), max = Math.max(...values), span = max - min || 1;
    const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - 3 - ((v - min) / span) * (h - 6)}`);
    const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", `0 0 ${w} ${h}`);
    s.setAttribute("preserveAspectRatio", "none");
    s.setAttribute("class", "spark");
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", "M" + pts.join(" L"));
    s.append(p);
    return s;
  }

  // ----------------------------------------------------------- library ---
  async function renderLibrary() {
    const box = $("library");
    box.replaceChildren(el("p", "lede", "Loading…"));
    let d = state.data;
    try { d = state.data = await api("/api/state"); state.status = d.status; } catch (_) { /* show what we have */ }
    box.replaceChildren();
    const section = (title) => { const s = el("section"); s.append(el("h2", null, title)); const t = el("div", "tiles"); s.append(t); box.append(s); return t; };
    const decks = (d?.files || []).filter((f) => f.kind === "deck");
    if (decks.length) {
      const t = section("Decks");
      for (const f of decks) {
        const tile = el("button", "tile card");
        tile.type = "button";
        const thumb = el("div", `slide theme-${f.theme || "midnight"}`);
        thumb.append(el("span", "k", "Deck"), el("span", "t", f.title || f.name));
        const cap = el("div", "cap");
        cap.append(el("div", "t", f.title || f.name), el("div", "s", `${f.slides || "?"} slides · ${ago(f.created)}`));
        tile.append(thumb, cap);
        tile.addEventListener("click", () => { const b = el("div"); b.append(deckCard(f)); openSheet(f.title || f.name, b); });
        t.append(tile);
      }
    }
    const deals = (state.home?.cards || []).filter((c) => c.kind === "deal" && (c.items || []).length);
    if (deals.length) {
      const t = section("Deals");
      for (const c of deals.slice(0, 12)) {
        const tile = el("button", "tile card");
        tile.type = "button";
        const best = c.items[0];
        const thumb = el("div", "thumb");
        thumb.append(picture(best.image) || el("span", "checked", best.store));
        const cap = el("div", "cap");
        cap.append(el("div", "t", c.title), el("div", "s", `${best.store}: ${best.title}`));
        tile.append(thumb, cap);
        tile.addEventListener("click", () => { state.feedSel = c.id; go("feed"); });
        t.append(tile);
      }
    }
    const drafts = d?.message_drafts || [];
    if (drafts.length) {
      const t = section("Drafts");
      for (const m of drafts) {
        const tile = el("button", "tile card");
        tile.type = "button";
        const cap = el("div", "cap");
        cap.append(el("div", "t", "Text to " + (m.name || m.to)), el("div", "s", m.body));
        tile.append(cap);
        tile.addEventListener("click", () => { const b = el("div"); b.append(draftCard(m)); openSheet("Draft", b); });
        t.append(tile);
      }
    }
    if (!box.children.length) box.append(el("p", "lede", "Nothing yet. Ask me for a deck, a price check or a text and it'll show up here."));
  }

  // -------------------------------------------------------------- apps ---
  function appCard(title, sub, color, letterOrIcon, on, statusText) {
    const c = el("div", "app-card card");
    const top = el("div", "top");
    const logo = el("span", "logo");
    logo.style.background = color;
    if (ICONS[letterOrIcon]) logo.append(icon(letterOrIcon)); else logo.textContent = letterOrIcon;
    const t = el("div");
    t.append(el("div", "t", title), el("div", "s", sub));
    top.append(logo, t, el("span", "status " + (on ? "green" : "grey"), statusText || (on ? "Connected" : "Not connected")));
    c.append(top);
    return c;
  }
  function renderApps() {
    const h = state.home || {};
    const con = h.connections || {};
    const box = $("apps");
    box.replaceChildren();

    const mail = con.mail || {};
    const mc = appCard("Email", mail.connected ? mail.address : "Gmail, iCloud, Outlook, Yahoo", "linear-gradient(135deg,#ea4335,#fbbc05)", "mail", mail.connected);
    if (mail.connected) {
      mc.append(el("div", "help", "I read your inbox, write drafts into your Drafts folder, and only send when you press Allow."));
      const a = el("div", "actions");
      a.append(btn("Check my email", "pill soft small", () => send("check my email")), btn("Disconnect", "pill quiet small danger", async () => { await api("/api/connect/disconnect", { service: "mail" }).catch((e) => toast(e.message)); refreshHome().then(renderApps); }));
      mc.append(a);
    } else {
      const f = el("form");
      const addr = el("input"); addr.type = "email"; addr.placeholder = "you@gmail.com"; addr.required = true; addr.autocomplete = "email";
      const pw = el("input"); pw.type = "password"; pw.placeholder = "App password (16 letters)"; pw.required = true; pw.autocomplete = "off";
      const help = el("div", "help");
      help.append(document.createTextNode("Free and private. Make an app password at "), linkOut("Google", "https://myaccount.google.com/apppasswords", ""), document.createTextNode(", "), linkOut("Apple", "https://account.apple.com/account/manage", ""), document.createTextNode(" or "), linkOut("Yahoo", "https://login.yahoo.com/account/security/app-passwords", ""), document.createTextNode(". It's never your real password."));
      const adv = el("details");
      adv.append(el("summary", null, "Other provider"));
      const imap = el("input"); imap.placeholder = "IMAP server, e.g. imap.fastmail.com";
      const smtp = el("input"); smtp.placeholder = "SMTP server, e.g. smtp.fastmail.com";
      adv.append(imap, smtp);
      const go1 = el("button", "pill primary", "Connect email");
      go1.type = "submit";
      f.append(addr, pw, adv, go1, help);
      f.addEventListener("submit", async (e) => {
        e.preventDefault();
        go1.disabled = true; go1.textContent = "Checking…";
        try {
          await api("/api/connect/mail", { address: addr.value.trim(), app_password: pw.value, ...(imap.value ? { imap_host: imap.value.trim(), smtp_host: smtp.value.trim() } : {}) });
          pw.value = "";
          toast("Email connected. Try “check my email”.");
          await refreshHome(); renderApps();
        } catch (err) { toast(err.message); go1.disabled = false; go1.textContent = "Connect email"; }
      });
      mc.append(f);
    }
    box.append(mc);

    const cal = con.calendar || {};
    const cc = appCard("Calendar", cal.connected ? cal.host : "Google, iCloud, Outlook", "linear-gradient(135deg,#4285f4,#34a853)", "calendar", cal.connected);
    if (cal.connected) {
      const a = el("div", "actions");
      a.append(btn("What's on today?", "pill soft small", () => send("what's on my calendar today?")), btn("Disconnect", "pill quiet small danger", async () => { await api("/api/connect/disconnect", { service: "calendar" }).catch((e) => toast(e.message)); refreshHome().then(renderApps); }));
      cc.append(a);
    } else {
      const f = el("form");
      const url = el("input"); url.placeholder = "Private iCal link (https:// or webcal://)"; url.required = true;
      const help = el("div", "help", "Google Calendar: Settings → your calendar → “Secret address in iCal format”. I can read it, never change it.");
      const b = el("button", "pill primary", "Connect calendar"); b.type = "submit";
      f.append(url, b, help);
      f.addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await api("/api/connect/calendar", { url: url.value.trim() }); toast("Calendar connected."); await refreshHome(); renderApps(); } catch (err) { toast(err.message); }
      });
      cc.append(f);
    }
    box.append(cc);

    const br = con.browser || {};
    const bc = appCard("Instagram, stores and the web", br.available ? "Luma's own browser, signed in by you" : "Needs Luma's browser tools", "linear-gradient(135deg,#f58529,#dd2a7b 50%,#8134af)", "insta", br.on, br.on ? "On" : "Off");
    bc.append(el("div", "help", "I scroll feeds and compare prices in my own browser. Sign in once yourself; I never see or type passwords. Liking, posting and buying always wait for you."));
    const ba = el("div", "actions");
    ba.append(btn(br.on ? "Turn off" : "Turn on", br.on ? "pill quiet small" : "pill primary small", async () => { try { await api("/api/setting", { key: "browser", value: !br.on }); await refreshHome(); renderApps(); } catch (e) { toast(e.message); } }));
    if (br.on) {
      for (const [label, url] of [["Sign in to Instagram", "https://www.instagram.com/"], ["Sign in to Amazon", "https://www.amazon.com/"]]) {
        ba.append(btn(label, "pill soft small", async () => { try { const r = await api("/api/browser/show", { url }); toast(r.summary); } catch (e) { toast(e.message); } }));
      }
      ba.append(btn("Done signing in", "pill quiet small", async () => { try { await api("/api/browser/hide", {}); toast("Got it. I'll take it from here."); } catch (e) { toast(e.message); } }));
    }
    bc.append(ba);
    box.append(bc);

    const tx = con.texting || {};
    const tc = appCard("Texts", "iMessage, your number or Luma's number", "linear-gradient(135deg,#34c759,#30b0c7)", "message", tx.enabled, tx.enabled ? "On" : "Drafts only");
    const sel = el("select");
    for (const [v, label] of [["phone_draft", "Drafts I send myself"], ["mac_imessage", "My iMessage (Mac)"], ["mac_sms", "My number by SMS (Mac)"], ["luma_number", "Luma's number"]]) { const o = el("option", null, label); o.value = v; sel.append(o); }
    sel.value = tx.route || "phone_draft";
    sel.addEventListener("change", async () => { try { await api("/api/messages/route", { route: sel.value }); toast("Saved. Every text still waits for your OK."); refreshHome(); } catch (e) { toast(e.message); } });
    tc.append(sel, el("div", "help", "Every text shows you the exact words first. Nothing sends until you press Allow."));
    box.append(tc);

    const pa = con.phone_app || {};
    const phones = pa.phones || [];
    const pc = appCard("Luma on your phone", phones.length ? phones.map((p) => p.name).join(", ") : "Talk to Luma from anywhere", "linear-gradient(135deg,#6a67f4,#d48cc4)", "phone", phones.length > 0, phones.length ? "Paired" : "Not paired");
    pc.append(el("div", "help", "Encrypted end to end. Approvals and price drops come to your lock screen."));
    const pact = el("div", "actions");
    pact.append(btn("Connect a phone", "pill soft small", async () => {
      try {
        const r = await api("/api/phone-app/pair", {});
        const b = el("div");
        const img = el("img", "qr");
        img.src = r.qr; img.alt = "Scan with your phone's camera"; img.width = 240;
        b.append(img, el("p", "lede", "Scan with your phone's camera. Works once, for 10 minutes."));
        b.style.display = "flex"; b.style.flexDirection = "column"; b.style.alignItems = "center";
        openSheet("Connect your phone", b);
      } catch (e) { toast(e.message); }
    }));
    pc.append(pact);
    box.append(pc);

    const model = state.status?.model_name || "";
    const pretty = /qwen3-4b/i.test(model) ? "Qwen3 4B" : /llama-3\.2-3b/i.test(model) ? "Llama 3.2 3B" : model.replace(/[-_]Q\d.*$|\.gguf$/gi, "").replace(/[-_]/g, " ") || "Local model";
    const mc2 = appCard("Luma's brain", pretty + ", on this computer", "linear-gradient(135deg,#111118,#3a3a46)", "cpu", h.model?.on, h.model?.on ? "Running" : "Off");
    mc2.append(el("div", "help", "No cloud AI and no subscription. What you say stays here unless you send it."));
    box.append(mc2);
  }

  // ------------------------------------------------------------- rules ---
  function renderRules() {
    const box = $("rules");
    box.replaceChildren();
    for (const r of state.home?.rules || []) {
      const it = el("div", "item");
      const g = el("div", "grow");
      g.append(el("div", "title", r.label), el("div", "sub", r.locked ? (r.id === "spend" ? "I never check out or pay. That's always you." : "Can ask or be blocked, never run on its own.") : r.choices.includes("ask") ? "Allow skips the question for this one." : "Only reads or prepares, so nothing leaves without you."));
      it.append(g);
      if (r.locked) { const l = icon("lock"); l.classList.add("lock"); it.append(l); }
      const seg = el("div", "segmented");
      for (const v of ["allow", "ask", "block"]) {
        if (!r.choices.includes(v)) continue;
        seg.append(btn({ allow: "Allow", ask: "Ask me", block: "Block" }[v], (r.value === v ? "on " : "") + v, async () => {
          try { const res = await api("/api/rules", { id: r.id, value: v }); state.home.rules = res.rules; renderRules(); } catch (e) { toast(e.message); }
        }));
      }
      it.append(seg);
      box.append(it);
    }
    const learned = $("learned");
    learned.replaceChildren();
    for (const m of state.home?.learned || []) {
      const it = el("div", "item");
      const g = el("div", "grow");
      g.append(el("div", "title", m.text), el("div", "sub", m.source === "feedback" ? "From your feedback" : m.source === "explicit_user_request" ? "You asked me to remember" : "Picked up in conversation"));
      it.append(g, btn("Forget", "pill quiet small", async () => { try { await api("/api/memory/delete", { id: m.id }); await refreshHome(); renderRules(); } catch (e) { toast(e.message); } }));
      learned.append(it);
    }
    if (!learned.children.length) learned.append(el("div", "item", "Nothing yet. Use thumbs up or down on anything I do and I'll learn."));
  }

  // ---------------------------------------------------------- settings ---
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
  async function renderSettings() {
    try { const d = await api("/api/state"); state.data = d; state.status = d.status; } catch (_) { /* keep going */ }
    const s = state.status || {};
    const box = $("settings");
    box.replaceChildren();
    const look = el("div", "item");
    const lg = el("div", "grow");
    lg.append(el("div", "title", "Appearance"), el("div", "sub", "Light, dark, or follow your computer."));
    const seg = el("div", "segmented");
    for (const [v, label] of [["system", "Auto"], ["light", "Light"], ["dark", "Dark"]]) seg.append(btn(label, theme === v ? "on" : "", () => { setTheme(v); renderSettings(); }));
    look.append(lg, seg);
    box.append(look);
    box.append(toggleRow("Listen for “Hey Luma”", "Talk out loud from across the room. The microphone stays off until you turn this on.", !s.microphone_muted, (on) => api("/api/setting", { key: "muted", value: !on })));
    box.append(toggleRow("Remember things I mention", "Small facts (your sister's birthday, your coffee order), encrypted on this computer.", s.presence?.learn_from_chat !== false, (on) => api("/api/setting", { key: "learn_from_chat", value: on })));
    box.append(toggleRow("Check back on things", "“How did the interview go?” the day after.", s.presence?.check_ins !== false, (on) => api("/api/setting", { key: "check_ins", value: on })));
    box.append(toggleRow("Morning briefing", "Your day, every morning.", s.daily_briefing_enabled, (on) => api("/api/setting", { key: "daily_briefing_enabled", value: on })));
    for (const [title, sub, view] of [["Apps", "Email, calendar, Instagram, texts and your phone.", "apps"], ["Rules", "What Luma does on its own, asks about, or never does.", "rules"]]) {
      const it = el("div", "item");
      const g = el("div", "grow");
      g.append(el("div", "title", title), el("div", "sub", sub));
      it.append(g, btn("Open", "pill soft small", () => go(view)));
      box.append(it);
    }
    const about = el("div", "item");
    const ag = el("div", "grow");
    ag.append(el("div", "title", "Everything else"), el("div", "sub", "Voice, personality, kids mode, quiet hours and the full controls."));
    const full = el("a", "pill soft small", "All controls");
    full.href = "/";
    about.append(ag, full);
    box.append(about);
  }

  function renderView(view) {
    if (view === "feed") renderFeed();
    if (view === "ideas") renderIdeas();
    if (view === "goals") renderGoals();
    if (view === "library") renderLibrary();
    if (view === "apps") renderApps();
    if (view === "rules") renderRules();
    if (view === "settings") renderSettings();
  }

  // -------------------------------------------------------------- sheet ---
  function openSheet(title, body) {
    $("sheet-title").textContent = title;
    $("sheet-body").replaceChildren(body);
    $("sheet").hidden = false;
  }
  function closeSheet() { $("sheet").hidden = true; }
  $("sheet-close").addEventListener("click", closeSheet);
  $("sheet").addEventListener("click", (e) => { if (e.target === $("sheet")) closeSheet(); });

  // ------------------------------------------------------------ palette ---
  // ⌘K: jump anywhere, find a chat or feed card, or just ask Luma.
  let paletteItems = [];
  let paletteSel = 0;
  function openPalette(text) {
    $("palette").hidden = false;
    $("palette-input").value = text || "";
    renderPalette();
    $("palette-input").focus();
  }
  function closePalette() { $("palette").hidden = true; }
  function renderPalette() {
    const raw = $("palette-input").value.trim();
    const q = raw.toLowerCase();
    const has = (s) => !q || String(s || "").toLowerCase().includes(q);
    const out = $("palette-results");
    out.replaceChildren();
    paletteItems = [];
    const section = (name, rows) => {
      if (!rows.length) return;
      out.append(el("div", "sec", name));
      for (const r of rows) {
        const b = el("button");
        b.type = "button";
        b.append(r.chip, el("span", null, r.title));
        if (r.sub) b.append(el("span", "s", r.sub));
        b.addEventListener("click", () => { closePalette(); r.run(); });
        out.append(b);
        paletteItems.push({ b, run: r.run });
      }
    };
    if (q) section("Ask Luma", [{ chip: chip("update", "chat"), title: raw, sub: "↵", run: () => send(raw) }]);
    const views = [["chat", "Main chat", "chat"], ["feed", "Feed", "feed"], ["ideas", "Ideas", "ideas"], ["goals", "Goals", "goals"], ["library", "Library", "library"], ["apps", "Apps", "apps"], ["rules", "Rules", "rules"], ["settings", "Settings", "settings"]];
    section("Go to", views.filter(([, t]) => has(t)).slice(0, q ? 4 : 8).map(([v, t, ic]) => ({ chip: chip("setup", ic), title: t, run: () => { if (v === "chat") state.thread = "main"; go(v); } })));
    section("Chats", (state.home?.threads || []).filter((t) => t.id !== "main" && has(t.title)).slice(0, 5).map((t) => ({ chip: chip("people", "chat"), title: t.title, run: async () => { state.thread = t.id; await loadThread(t.id); go("chat"); } })));
    section("Feed", (state.home?.cards || []).filter((c) => has(c.title) || has(c.body)).slice(0, 5).map((c) => ({ chip: chip(c.kind in KIND ? c.kind : "update", (KIND[c.kind] || KIND.update).icon), title: c.title, sub: ago(c.created), run: () => { state.feedSel = c.id; go("feed"); } })));
    section("Ideas", (state.home?.ideas || []).filter((i) => has(i.title)).slice(0, q ? 4 : 5).map((i) => ({ chip: chip(i.kind in KIND ? i.kind : "idea", (KIND[i.kind] || KIND.idea).icon), title: i.title, run: () => (/^connect my/.test(i.say) ? go("apps") : send(i.say)) })));
    paletteSel = 0;
    paintPaletteSel();
  }
  function paintPaletteSel() { paletteItems.forEach((p, i) => p.b.classList.toggle("sel", i === paletteSel)); paletteItems[paletteSel]?.b.scrollIntoView({ block: "nearest" }); }
  $("palette-input").addEventListener("input", renderPalette);
  $("palette-input").addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); paletteSel = Math.min(paletteItems.length - 1, paletteSel + 1); paintPaletteSel(); }
    if (e.key === "ArrowUp") { e.preventDefault(); paletteSel = Math.max(0, paletteSel - 1); paintPaletteSel(); }
    if (e.key === "Enter") { e.preventDefault(); const it = paletteItems[paletteSel]; if (it) { closePalette(); it.run(); } }
    if (e.key === "Escape") closePalette();
  });
  $("palette").addEventListener("click", (e) => { if (e.target === $("palette")) closePalette(); });
  $("open-search").addEventListener("click", () => openPalette(""));

  // --------------------------------------------------------- live data ---
  async function refreshHome() {
    try {
      const h = await api("/api/home");
      const before = JSON.stringify([state.home?.cards?.length, state.home?.helpers, state.home?.ideas, state.home?.connections, state.home?.rules, state.home?.approvals?.length]);
      state.home = h;
      if (h.status) state.status = h.status;
      state.activity = h.activity;
      handleEvents(h.events || []);
      renderThreads();
      renderWidgets();
      paintActivity();
      if (h.activity && ["running", "paused"].includes(h.activity.state) && !activityTimer) watchActivity(true);
      const after = JSON.stringify([h.cards?.length, h.helpers, h.ideas, h.connections, h.rules, h.approvals?.length]);
      if (before !== after && state.view !== "chat" && !document.activeElement?.closest?.(".page, .feed-view")) renderView(state.view);
      const approvalsNow = (h.approvals || []).map((a) => a.id).join(",");
      if (approvalsNow !== state.approvalsKey) { state.approvalsKey = approvalsNow; if (state.view === "chat" && !state.busy && !document.activeElement?.closest?.(".checkout")) renderChat(); }
      if ($("mascot").classList.contains("sleepy") && !state.busy) mood("idle", "Here with you");
      $("mic").classList.toggle("on", Boolean(h.status && !h.status.microphone_muted));
      return h;
    } catch (_) {
      if (!state.busy) mood("sleepy", "Can't reach Luma. Is it running?");
      return null;
    }
  }
  function handleEvents(events) {
    let reload = false;
    for (const ev of events) {
      const r = ev.result || ev;
      const id = r.event_id || `${ev.created}:${r.text}`;
      if (state.seen.has(id)) continue;
      state.seen.add(id);
      if (state.firstPoll) continue; // don't replay history on open
      if (r.you && r.channel) { reload = true; continue; } // from the phone: it's in the transcript
      if (r.type && r.text) {
        const label = { reply: "Text back", reminder: "Reminder", timer: "Timer", briefing: "Today", helper: "Goal" }[r.type];
        pushLocal("main", { role: "notice", label: label || "Luma", text: r.text });
        if (document.hidden && "Notification" in window && Notification.permission === "granted") new Notification("Luma", { body: r.text, icon: "/desktop/logo" });
        mood("happy", label || "Thought of something", 3000);
      }
    }
    state.firstPoll = false;
    if (reload) loadThread("main").then(() => { if (state.thread === "main" && !state.busy && state.view === "chat") renderChat(); });
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
    send(text);
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
    if (e.key === "Escape") { if (!$("palette").hidden) closePalette(); else if (!$("sheet").hidden) closeSheet(); }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "n") { e.preventDefault(); newChat(); }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); if ($("palette").hidden) openPalette(""); else closePalette(); }
  });
  // The window's menu (in the Mac app) can ask for a view.
  window.addEventListener("hashchange", () => { const v = location.hash.slice(1); if (document.getElementById("view-" + v)) go(v); });
  const scheme = matchMedia("(prefers-color-scheme: dark)");
  if (scheme.addEventListener) scheme.addEventListener("change", () => applyTheme(theme));

  // ------------------------------------------------------------- start ---
  mood("idle", "Here with you");
  Promise.all([loadThread("main"), refreshHome()]).then(() => {
    const v = location.hash.slice(1);
    if (v && document.getElementById("view-" + v)) go(v); else go("chat");
    if ("Notification" in window && Notification.permission === "default") Notification.requestPermission().catch(() => {});
  });
  setInterval(refreshHome, 4000);
  resize();
  input.focus();
})();
