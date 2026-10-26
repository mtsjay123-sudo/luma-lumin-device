// Luma on your phone: today's chats, memory you can flip through, and the device itself.
// One call (/api/today) paints the screen; chats open in a sheet and keep going from there.
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  let today = null, deckAt = 0, timer = 0;

  async function api(path, data) {
    const r = await fetch(path, data === undefined ? { credentials: "same-origin" } :
      { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    let d = {};
    try { d = await r.json(); } catch (_) { /* not JSON */ }
    if (!r.ok) { const e = new Error(d.error || "Luma didn't answer."); e.status = r.status; throw e; }
    return d;
  }
  function toast(text) {
    const t = $("toast");
    t.textContent = text;
    t.classList.add("show");
    clearTimeout(toast.t);
    toast.t = setTimeout(() => t.classList.remove("show"), 2600);
  }
  function when(ts) {
    if (!ts) return "";
    const d = new Date(ts * 1000), now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const y = new Date(now); y.setDate(now.getDate() - 1);
    if (sameDay) return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    if (d.toDateString() === y.toDateString()) return "Yesterday";
    return d.toLocaleDateString([], { month: "short", day: "numeric" });
  }

  // LED dot numbers, like the device's own display: a 5x7 grid per digit, lit dots and faint ones.
  const FONT = {
    0: ["01110", "10001", "10001", "10001", "10001", "10001", "01110"], 1: ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    2: ["01110", "10001", "00001", "00010", "00100", "01000", "11111"], 3: ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    4: ["00010", "00110", "01010", "10010", "11111", "00010", "00010"], 5: ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    6: ["00110", "01000", "10000", "11110", "10001", "10001", "01110"], 7: ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    8: ["01110", "10001", "10001", "01110", "10001", "10001", "01110"], 9: ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    ".": ["00", "00", "00", "00", "00", "11", "11"], "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
  };
  function dots(text) {
    const wrap = el("span", "dots");
    for (const ch of String(text)) {
      const rows = FONT[ch];
      if (!rows) continue;
      const w = rows[0].length;
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", `0 0 ${w * 10} 70`);
      rows.forEach((row, y) => [...row].forEach((bit, x) => {
        const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        c.setAttribute("cx", x * 10 + 5); c.setAttribute("cy", y * 10 + 5); c.setAttribute("r", 3.6);
        if (bit !== "1") c.setAttribute("class", "off");
        svg.append(c);
      }));
      wrap.append(svg);
    }
    return wrap;
  }

  function size(gb) {
    if (gb >= 10) return `${Math.round(gb)} GB`;
    if (gb >= 1) return `${gb.toFixed(1)} GB`;
    const mb = gb * 1024;
    return mb >= 1 ? `${Math.round(mb)} MB` : "under 1 MB";
  }
  function greet(name) {
    const h = new Date().getHours();
    const part = h < 5 ? "Up late" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
    return name ? `${part}, ${name}.` : `${part}.`;
  }

  function setState(dev) {
    const body = document.body, label = $("state").querySelector("span");
    body.classList.remove("listening", "thinking", "quiet");
    if (!dev) { label.textContent = "Can't reach your Luma"; body.classList.add("quiet"); return; }
    if (dev.busy) { body.classList.add("thinking"); label.textContent = "Thinking"; }
    else if (dev.speaking) { body.classList.add("listening"); label.textContent = "Talking"; }
    else if (dev.mic === "on") { body.classList.add("listening"); label.textContent = "Listening"; }
    else { body.classList.add("quiet"); label.textContent = "Mic off"; }
  }

  function renderChats(chats) {
    const list = $("chain-list");
    list.replaceChildren();
    const todays = chats.filter((c) => c.today);
    const count = $("chats-count");
    count.replaceChildren(dots(todays.length));
    count.setAttribute("aria-label", `${todays.length} today`);
    if (!chats.length) { list.append(el("li", "empty", "No chats yet. Ask Luma something up top, or just talk to it at home.")); return; }
    if (chats.length > 5) {
      const li = el("li"), all = el("button", "more", `All chats (${chats.length})`);
      all.type = "button";
      all.addEventListener("click", () => openAllChats(chats));
      li.append(all);
      queueMicrotask(() => list.append(li));
    }
    for (const c of chats.slice(0, 5)) {
      const li = el("li");
      const b = el("button", "chain" + (c.today ? "" : " older"));
      b.type = "button";
      b.append(el("b", null, c.title || "Chat"), el("time", null, when(c.updated)),
        el("span", null, c.last ? (c.last.role === "you" ? "You: " : "") + c.last.text : `${c.messages} messages`));
      b.addEventListener("click", () => openChain(c.id, c.title));
      li.append(b);
      list.append(li);
    }
  }

  function openAllChats(chats) {
    const wrap = el("ul", "chain-list");
    for (const c of chats) {
      const li = el("li"), b = el("button", "chain" + (c.today ? "" : " older"));
      b.type = "button";
      b.append(el("b", null, c.title || "Chat"), el("time", null, when(c.updated)), el("span", null, c.last ? (c.last.role === "you" ? "You: " : "") + c.last.text : `${c.messages} messages`));
      b.addEventListener("click", () => openChain(c.id, c.title));
      li.append(b);
      wrap.append(li);
    }
    openSheet("All chats", wrap);
  }

  // memory deck
  function renderDeck(mem) {
    const deck = $("deck");
    deck.replaceChildren();
    const count = $("memory-count");
    if (!mem) return;
    count.replaceChildren(dots(mem.used));
    count.setAttribute("aria-label", `${mem.used} memories`);
    $("memory-hint").textContent = mem.limit ? `${mem.used} of ${mem.limit} on the free plan. Swipe through them, tap one to fix or forget it.`
      : "Everything Luma remembers about you. Swipe through it, tap one to fix or forget it.";
    const cards = mem.recent || [];
    if (!cards.length) { deck.append(el("div", "deck-empty", "Nothing yet. Tell Luma something worth keeping, like \"my mom's birthday is June 3\".")); $("deck-pos").textContent = ""; return; }
    deckAt = Math.min(deckAt, cards.length - 1);
    cards.forEach((m, i) => {
      const c = el("button", "card");
      c.type = "button";
      c.setAttribute("role", "option");
      c.setAttribute("aria-label", `${m.kind || "Note"}: ${m.text}`);
      c.append(el("span", "tag", m.kind || "Notes"), el("p", null, m.text), el("small", null, m.when ? when(m.when) : "Remembered"));
      c.addEventListener("click", () => (i === deckAt ? openMemory(m) : (deckAt = i, layoutDeck())));
      deck.append(c);
    });
    layoutDeck();
  }
  function layoutDeck() {
    const cards = [...$("deck").querySelectorAll(".card")];
    cards.forEach((c, i) => {
      const off = i - deckAt, a = Math.abs(off);
      c.classList.toggle("front", off === 0);
      c.setAttribute("aria-selected", String(off === 0));
      c.tabIndex = off === 0 ? 0 : -1;
      // the front card faces you; the rest fan away like folders on a shelf, each one a little further back
      const x = off === 0 ? 0 : Math.sign(off) * (96 + (a - 1) * 26);
      c.style.transform = off === 0 ? "translateZ(40px)" : `translateX(${x}px) translateZ(${-a * 34}px) rotateY(${Math.sign(off) * -62}deg)`;
      c.style.opacity = a > 6 ? 0 : String(1 - a * 0.1);
      c.style.zIndex = String(100 - a);
      c.style.pointerEvents = a > 6 ? "none" : "";
    });
    $("deck-pos").textContent = cards.length ? `${deckAt + 1} of ${cards.length}` : "";
  }
  function step(n) {
    const total = $("deck").querySelectorAll(".card").length;
    if (!total) return;
    deckAt = Math.max(0, Math.min(total - 1, deckAt + n));
    layoutDeck();
  }
  $("deck-prev").addEventListener("click", () => step(-1));
  $("deck-next").addEventListener("click", () => step(1));
  $("deck").addEventListener("keydown", (e) => { if (e.key === "ArrowLeft") { step(-1); e.preventDefault(); } if (e.key === "ArrowRight") { step(1); e.preventDefault(); } });
  let swipeX = null;
  $("deck").addEventListener("pointerdown", (e) => { swipeX = e.clientX; });
  $("deck").addEventListener("pointerup", (e) => { if (swipeX == null) return; const dx = e.clientX - swipeX; swipeX = null; if (Math.abs(dx) > 30) step(dx < 0 ? 1 : -1); });

  const DID = { "files.find": "looked for files", "files.read": "read a file", "app.open": "opened an app", "screen.look": "looked at the screen",
    open: "opened a page", play: "played music", read: "read the page", tabs: "checked your tabs" };
  function renderDevice(dev) {
    const big = $("storage-big"), label = $("storage-label"), bar = $("storage-bar"), legend = $("storage-legend");
    big.replaceChildren(); bar.replaceChildren(); legend.replaceChildren();
    if (!dev) { label.textContent = "Your Luma isn't answering right now."; return; }
    const s = dev.storage;
    if (s) {
      big.append(dots(s.free >= 10 ? Math.round(s.free) : s.free.toFixed(1)), el("span", "unit", "GB left"));
      big.setAttribute("aria-label", `${s.free} GB left`);
      const lumaGB = (s.luma.models || 0) + (s.luma.data || 0) + (s.luma.files || 0);
      label.textContent = `Out of ${Math.round(s.total)} GB. Luma itself uses ${size(lumaGB)}.` + (s.low ? " Running low. Delete old projects to free up space." : "");
      bar.setAttribute("aria-label", `${s.free} of ${s.total} GB free`);
      const n = 40, luma = Math.round((lumaGB / s.total) * n), other = Math.max(0, Math.round(((s.used - lumaGB) / s.total) * n));
      for (let i = 0; i < n; i++) bar.append(el("i", i < luma ? "luma" : i < luma + other ? "other" : ""));
      for (const [cls, text] of [["luma", `Luma ${size(lumaGB)}`], ["other", `Everything else ${size(Math.max(0, s.used - lumaGB))}`], ["", `Free ${size(s.free)}`]]) {
        const li = el("li"); const sw = el("i"); sw.style.background = cls === "luma" ? "var(--warm)" : cls === "other" ? "color-mix(in srgb, var(--ink) 45%, transparent)" : "color-mix(in srgb, var(--ink) 12%, transparent)";
        li.append(sw, document.createTextNode(text)); legend.append(li);
      }
    } else {
      label.textContent = "Storage isn't available from here.";
    }
    const mic = $("mic"), on = dev.mic === "on";
    mic.setAttribute("aria-checked", String(on));
    $("mic-sub").textContent = on ? "On. Luma can hear the room." : "Off. Luma can't hear anything.";
    $("brain").textContent = dev.brain || "Starting up";
    const pc = dev.computer || {};
    const last = (pc.recent || [])[0];
    const t = last ? when(last.at) : "";
    const at = /^\d/.test(t) ? `at ${t}` : t === "Yesterday" ? "yesterday" : `on ${t}`;
    const did = last ? ` Last: ${DID[last.kind] || "used it"}${last.what ? ` (${last.what})` : ""} ${at}${last.ok === false ? ", but it didn't work" : ""}.` : "";
    $("computer").textContent = pc.here ? `${pc.name || "Your computer"} is connected. Luma can use it for you, only in the folders and apps you allowed there.${did}`
      : pc.paired ? `${pc.name || "Your computer"} is paired but asleep or away.${did}` : "Not connected. Pair your computer in Luma Desktop and Luma can use it for you.";
  }

  function renderProjects(projects) {
    const sec = $("projects"), list = $("project-list");
    list.replaceChildren();
    sec.hidden = !projects.length;
    for (const p of projects) {
      const li = el("li", "project");
      const state = { running: "Working on it", done: "Done", attention: "Needs a look", waiting: "Waiting for your OK", stopped: "Paused", new: "Not started" }[p.state] || p.state;
      li.append(el("b", null, p.name), el("small", null, `${state} · ${p.done} of ${p.steps} steps`));
      const dotsRow = el("div", "steps");
      for (let i = 0; i < p.steps; i++) dotsRow.append(el("i", i < p.done ? "done" : ""));
      li.append(dotsRow);
      list.append(li);
    }
  }

  async function refresh() {
    try {
      today = await api("/api/today");
      if (today.kids) { $("hello").textContent = greet(""); $("sub").textContent = "Kids mode is on."; return; }
      $("hello").textContent = greet(today.name);
      const todays = today.chats.filter((c) => c.today).length;
      $("sub").textContent = (todays ? `${todays} chat${todays === 1 ? "" : "s"} today` : "A quiet day so far") +
        (today.approvals ? `, and ${today.approvals} thing${today.approvals === 1 ? "" : "s"} waiting for your OK.` : ".");
      setState(today.device);
      renderChats(today.chats);
      renderDeck(today.memory);
      renderDevice(today.device);
      renderProjects(today.projects || []);
    } catch (e) {
      setState(null);
      if (e.status === 401) {
        $("hello").textContent = "Pair this phone.";
        $("sub").innerHTML = "";
        $("sub").append(document.createTextNode("This phone isn't paired with your Luma yet. On your computer, open Luma, go to Connectors, tap Luma on your phone, and scan the code. "),
          Object.assign(el("a", null, "I have a code"), { href: "/" }));
      } else {
        $("sub").textContent = "Can't reach your Luma. It may be off or offline. This page updates as soon as it's back.";
      }
    }
  }

  // the sheet
  const sheet = $("sheet");
  function openSheet(title, body) {
    $("sheet-title").textContent = title;
    $("sheet-body").replaceChildren(body);
    if (!sheet.open) sheet.showModal();
  }
  $("sheet-close").addEventListener("click", () => sheet.close());
  sheet.addEventListener("click", (e) => { if (e.target === sheet) sheet.close(); });

  function bubble(m) {
    const b = el("div", "msg " + (m.role === "you" ? "you" : "luma"), m.text || "");
    if (m.at) b.append(el("time", null, when(m.at)));
    return b;
  }
  function replyForm(thread, list) {
    const f = el("form", "ask");
    const input = el("input");
    Object.assign(input, { placeholder: "Reply to Luma", maxLength: 4000, enterKeyHint: "send" });
    input.setAttribute("aria-label", "Reply");
    const send = el("button", "send");
    send.type = "submit";
    send.setAttribute("aria-label", "Send");
    send.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
    f.append(input, send);
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      list.append(bubble({ role: "you", text, at: Date.now() / 1000 }));
      const typing = list.appendChild(bubble({ role: "luma", text: "…" }));
      list.lastChild.scrollIntoView({ block: "end" });
      try {
        const r = await api("/api/chat", { text, thread });
        typing.replaceWith(bubble({ role: "luma", text: r.text || r.summary || "Done.", at: Date.now() / 1000 }));
      } catch (err) { typing.replaceWith(bubble({ role: "luma", text: err.message })); }
      list.lastChild.scrollIntoView({ block: "end" });
      refresh();
    });
    return f;
  }
  async function openChain(id, title) {
    const wrap = el("div"), list = el("div");
    wrap.append(list);
    openSheet(title || "Chat", wrap);
    list.append(el("p", "empty", "Loading…"));
    try {
      const chain = await api(`/api/threads/${encodeURIComponent(id)}`);
      list.replaceChildren(...(chain.messages || []).map(bubble));
      wrap.append(replyForm(id, list));
      list.lastChild?.scrollIntoView({ block: "end" });
    } catch (e) { list.replaceChildren(el("p", "empty", e.message)); }
  }
  function openMemory(m) {
    const wrap = el("div");
    const area = el("textarea");
    area.value = m.text;
    area.maxLength = 2000;
    area.setAttribute("aria-label", "This memory");
    const actions = el("div", "actions");
    const save = el("button", "pill primary", "Save");
    const forget = el("button", "pill danger", "Forget it");
    save.type = forget.type = "button";
    save.addEventListener("click", async () => {
      try { await api("/api/memory/save", { id: m.id, text: area.value.trim() }); sheet.close(); toast("Saved. Luma will remember it that way."); refresh(); }
      catch (e) { toast(e.message); }
    });
    forget.addEventListener("click", () => {
      // confirm in place: say what happens, and label the buttons with what they do
      actions.replaceChildren(el("p", "confirm", "Forget this? Luma won't know it anymore, and you can't undo it."));
      const keep = el("button", "pill", "Keep it"), gone = el("button", "pill danger", "Forget it");
      keep.type = gone.type = "button";
      keep.addEventListener("click", () => actions.replaceChildren(save, forget));
      gone.addEventListener("click", async () => {
        try { await api("/api/memory/delete", { id: m.id }); sheet.close(); toast("Forgotten."); refresh(); }
        catch (e) { toast(e.message); }
      });
      actions.append(keep, gone);
    });
    actions.append(save, forget);
    wrap.append(area, actions);
    openSheet("Memory", wrap);
  }

  // ask from the top: the answer opens as a chat you can keep going in
  $("ask").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = $("ask-text"), text = input.value.trim();
    if (!text) return;
    input.value = "";
    const list = el("div"), wrap = el("div");
    list.append(bubble({ role: "you", text, at: Date.now() / 1000 }), bubble({ role: "luma", text: "…" }));
    wrap.append(list);
    openSheet("Luma", wrap);
    try {
      const r = await api("/api/chat", { text });
      list.lastChild.replaceWith(bubble({ role: "luma", text: r.text || r.summary || "Done.", at: Date.now() / 1000 }));
      wrap.append(replyForm("main", list));
    } catch (err) { list.lastChild.replaceWith(bubble({ role: "luma", text: err.message })); }
    refresh();
  });

  $("mic").addEventListener("click", async () => {
    const on = $("mic").getAttribute("aria-checked") === "true";
    try { await api("/api/setting", { key: "muted", value: on }); toast(on ? "Mic off. Luma can't hear anything now." : "Mic on. Luma's listening."); refresh(); }
    catch (e) { toast(e.message); }
  });
  $("state").addEventListener("click", () => document.getElementById("device").scrollIntoView({ behavior: "smooth" }));

  // the dock follows where you are
  const links = [...document.querySelectorAll(".dock a")];
  const watch = new IntersectionObserver((entries) => {
    for (const en of entries) if (en.isIntersecting) links.forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#" + en.target.id));
  }, { rootMargin: "-45% 0px -50% 0px" });
  ["today", "chats", "memory", "device"].forEach((id) => watch.observe($(id)));

  refresh();
  const tick = () => { clearInterval(timer); timer = setInterval(() => { if (!document.hidden && !sheet.open) refresh(); }, 15000); };
  tick();
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
})();
