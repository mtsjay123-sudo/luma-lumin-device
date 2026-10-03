let state,
  seen = new Set(),
  busy = false;
const $ = (s) => document.querySelector(s),
  make = (tag, text, cls) => {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };
async function api(path, data) {
  const r = await fetch(
    path,
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
  );
  const d = await r.json();
  if (!r.ok) {
    const error = Error(d.error || "Device request failed");
    error.status = r.status;
    throw error;
  }
  return d;
}
function toast(text) {
  $("#toast").textContent = text;
  $("#toast").classList.add("show");
  setTimeout(() => $("#toast").classList.remove("show"), 5000);
}
async function setting(key, value) {
  try {
    await api("/api/setting", { key, value });
    await refresh();
  } catch (e) {
    toast(e.message);
  }
}
const renderedActions = new Set();
const prettyPhone = (n) => (/^\+1\d{10}$/.test(n || "") ? `(${n.slice(2, 5)}) ${n.slice(5, 8)}-${n.slice(8)}` : n);
const MESSAGE_TOOLS = ["sms.send", "mac_messages.send", "luma.send"];
const ROUTE_NAMES = {
  "luma.send": "Luma’s number",
  "mac_messages.send": "your number",
  "sms.send": "your Twilio number",
};
function thread() {
  return $("#results");
}
function scrollThread() {
  const t = thread();
  t.scrollTop = t.scrollHeight;
}
function bubble(role) {
  const row = make("div", undefined, "msg " + role),
    b = make("div", undefined, "bubble");
  row.append(b);
  thread().querySelector(".typing")?.remove();
  thread().append(row);
  while (thread().children.length > 50) thread().firstElementChild.remove();
  return b;
}
function sayYou(text) {
  bubble("you").append(make("p", text));
  scrollThread();
}
function showTyping() {
  const row = make("div", undefined, "msg luma typing"),
    b = make("div", undefined, "bubble");
  b.append(make("i"), make("i"), make("i"));
  row.append(b);
  thread().append(row);
  scrollThread();
}
async function openUpgrade() {
  try {
    const { url } = await api("/api/texting/upgrade", {});
    window.open(url, "_blank", "noopener");
  } catch (e) {
    toast(e.message);
  }
}
function upgradeOffer(data) {
  const offer = make("div", undefined, "plan-offer");
  offer.append(
    make("b", "Luma Plus"),
    make("span", "More texts every month and your own Luma number."),
  );
  const actions = make("div", undefined, "review-actions");
  actions.append(
    button("Get Luma Plus", openUpgrade, "button"),
    button("Send from my number instead", () =>
      $("#people").scrollIntoView({ behavior: "smooth" }),
    ),
  );
  offer.append(actions);
  return offer;
}
function textCard(data) {
  const name = data.recipient_name || data.arguments.to;
  const card = make("div", undefined, "text-card");
  card.append(
    make("span", `TEXT TO ${name.toUpperCase()} · FROM ${(ROUTE_NAMES[data.tool] || "your phone").toUpperCase()}`, "eyebrow"),
  );
  const body = make("div", data.arguments.body, "imsg");
  card.append(body);
  const actions = make("div", undefined, "review-actions");
  const lock = () => actions.querySelectorAll("button").forEach((e) => (e.disabled = true));
  actions.append(
    button("Send it", async () => {
      lock();
      try {
        result(await api("/api/confirm", { id: data.action, token: data.confirm_token }));
        actions.remove();
      } catch (e) {
        result({ text: e.message });
      }
      await refresh();
    }, "button"),
    button("Don’t send", async () => {
      lock();
      try {
        await api("/api/cancel", { id: data.action });
        actions.remove();
        result({ text: "Okay, I won’t send it." });
      } catch (e) {
        result({ text: e.message });
      }
    }, "pill"),
    button("Edit", async () => {
      const editor = make("textarea");
      editor.value = data.arguments.body;
      editor.maxLength = 1000;
      editor.rows = 3;
      body.replaceWith(editor);
      editor.focus();
      actions.replaceChildren(
        button("Use this", async () => {
          try {
            await api("/api/cancel", { id: data.action });
            result(await api("/api/messages/prepare", { recipient: data.arguments.to, body: editor.value }));
            card.remove();
          } catch (e) {
            toast(e.message);
          }
        }, "button"),
      );
    }),
  );
  card.append(actions);
  return card;
}
function reviewCard(data) {
  const box = make("div", undefined, "text-card");
  box.append(make("span", "READY FOR YOUR OK", "eyebrow"), make("h3", data.tool.replaceAll(".", " · ")));
  const review = data.review
    ? {
        appointment: data.review.title,
        start: data.review.local_start || data.review.start,
        time_zone: data.review.time_zone,
        attendee: data.review.attendee?.name,
        email: data.review.attendee?.email,
        price: "$0 · free appointment",
      }
    : data.arguments;
  for (const [k, v] of Object.entries(review)) {
    const row = make("p");
    row.append(make("b", k.replaceAll("_", " ") + ": "), make("span", String(v)));
    box.append(row);
  }
  box.append(make("p", "Nothing happens until you confirm.", "footnote"));
  const buttons = make("div", undefined, "review-actions");
  for (const [label, path] of [["Confirm", "/api/confirm"], ["Cancel", "/api/cancel"]]) {
    const b = make("button", label, label === "Cancel" ? "pill" : "button");
    b.onclick = async () => {
      buttons.querySelectorAll("button").forEach((e) => (e.disabled = true));
      try {
        result(await api(path, { id: data.action, token: data.confirm_token }));
      } catch (e) {
        result({ text: e.message });
      }
      await refresh();
    };
    buttons.append(b);
  }
  box.append(buttons);
  return box;
}
function draftCard(d) {
  const card = make("div", undefined, "text-card");
  card.append(make("span", `DRAFT FOR ${(d.name || d.to).toUpperCase()} · NOT SENT`, "eyebrow"), make("div", d.body, "imsg"));
  const actions = make("div", undefined, "review-actions");
  actions.append(
    button("Copy", async () => {
      await navigator.clipboard.writeText(d.body);
      toast("Copied. Paste it in Messages and tap Send.");
    }),
  );
  const open = make("a", "Open in Messages", "pill");
  open.href = `sms:${d.to}&body=${encodeURIComponent(d.body)}`;
  actions.append(open);
  card.append(actions);
  return card;
}
function result(data) {
  if (data.event_id && renderedActions.has(data.event_id)) return;
  if (data.event_id) renderedActions.add(data.event_id);
  const identity = data.action && `${data.action}:${data.state}`;
  if (identity && renderedActions.has(identity)) return;
  if (identity) renderedActions.add(identity);
  const box = bubble("luma");
  const pendingText = data.state === "pending" && MESSAGE_TOOLS.includes(data.tool);
  const text =
    data.text ||
    (pendingText ? "" : data.summary) ||
    (data.memories
      ? data.memories.length
        ? "Here’s what you asked me to remember."
        : "No matching memories yet."
      : data.tasks
        ? "Your reminders are below."
        : data.state === "cancelled"
          ? "Okay, cancelled."
          : data.state === "pending"
            ? "Take a look before I do this."
            : "Done.");
  if (text) box.append(make("p", text));
  if (data.state === "pending") box.append(pendingText ? textCard(data) : reviewCard(data));
  if (data.message_draft && ["draft", "quota"].includes(data.state)) box.append(draftCard(data.message_draft));
  if (data.quota) box.append(upgradeOffer(data));
  if (data.profile) profileLoaded = false;
  if (data.memories) for (const m of data.memories) box.append(make("p", m.text, "remembered"));
  if (data.records) for (const r of data.records) box.append(make("p", r.title + ": " + r.details, "remembered"));
  if (data.results)
    for (const h of data.results)
      if (/^https:\/\//.test(h.url)) {
        const a = make("a", h.title, "source");
        a.href = h.url;
        a.target = "_blank";
        a.rel = "noreferrer";
        box.append(a, make("p", h.snippet, "footnote"));
      }
  if (data.file && /^\/files\//.test(data.file.url || "")) {
    const a = make("a", "⬇ " + data.file.name, "button file-link");
    a.href = data.file.url;
    a.download = data.file.name;
    box.append(a);
  }
  if (data.handoff && /^https:\/\//.test(data.url)) {
    const a = make("a", "Continue to the store ↗", "button");
    a.href = data.url;
    a.target = "_blank";
    a.rel = "noreferrer";
    box.append(a, make("p", `List: ${data.items}. Budget: $${(data.budget_cents / 100).toFixed(2)}. You review the cart and pay at the store.`, "footnote"));
  }
  if (["groceries", "people"].includes(data.section) && !data.quota && data.state !== "draft")
    box.append(
      button(data.section === "groceries" ? "Open groceries" : "Open People & Texts", () =>
        document.getElementById(data.section).scrollIntoView({ behavior: "smooth" }),
      ),
    );
  const spoken = text || (pendingText ? `Text to ${data.recipient_name}: ${data.arguments.body}` : "");
  if (spoken && state?.viewer !== "phone") {
    const hear = button("▶", async () => {
      await api("/api/speak", { text: spoken });
    }, "hear");
    hear.setAttribute("aria-label", "Hear this");
    box.append(hear);
  }
  scrollThread();
}
function empty(target, text) {
  target.replaceChildren(make("p", text, "empty"));
}
async function refresh() {
  try {
    state = await api("/api/state");
    const s = state.status;
    renderExtra(state);
    if (typeof renderCompanion === "function") renderCompanion(state);
    $("#privacy").textContent = s.microphone_muted
      ? "Microphone off"
      : "Microphone on · mute";
    $("#privacy").classList.toggle("enabled", !s.microphone_muted);
    $("#device-status").textContent = s.busy ? "Thinking, right here." : s.speaking ? "Speaking with you." : s.microphone_muted
      ? "Quietly ready."
      : "Listening on this Mac.";
    $(".device-scene").classList.toggle("listening", !s.microphone_muted);
    $("#mode").value = s.mode;
    $("#runtime-mode").textContent = s.model_enabled
      ? "Local intelligence"
      : "Local tools · model off";
    const tasks = $("#reminders");
    empty(tasks, "Nothing you need to remember right now.");
    if (state.tasks.length) {
      tasks.replaceChildren();
      for (const t of state.tasks) {
        const row = make("div", undefined, "list-row");
        const b = make("button", "○", "check");
        b.setAttribute("aria-label", "Complete " + t.title);
        b.onclick = async () => {
          await api("/api/task/complete", { id: t.id });
          refresh();
        };
        const text = make("div");
        text.append(
          make("b", t.title),
          make("small", new Date(t.due * 1000).toLocaleString()),
        );
        row.append(b, text);
        tasks.append(row);
      }
    }
    const routines = $("#routines");
    routines.replaceChildren();
    for (const r of state.routines)
      routines.append(make("p", `${r.at} daily · ${r.title}`, "routine"));
    const memories = $("#memories");
    empty(
      memories,
      s.mode === "kids"
        ? "Adult memories are hidden in Kids mode."
        : "Tell Luma “Remember…” to save something you choose.",
    );
    if (state.memories.length) {
      memories.replaceChildren();
      for (const m of state.memories) {
        const row = make("div", undefined, "memory-row");
        row.append(make("p", m.text));
        const b = make("button", "Remove");
        b.onclick = async () => {
          await api("/api/memory/delete", { id: m.id });
          refresh();
        };
        row.append(button("Edit", async () => {
          $("#memory-edit").hidden = false;
          $("#memory-edit-id").value = m.id;
          $("#memory-edit-text").value = m.text;
          $("#memory-edit-text").focus();
        }), b);
        memories.append(row);
      }
    }
    for (const c of document.querySelectorAll("[data-service]")) {
      const service = c.dataset.service,
        on = s.integrations[service];
      c.querySelector("button").textContent = on
        ? "Enabled · turn off"
        : "Enable";
      c.querySelector("button").classList.toggle("enabled", on);
      c.querySelector("button").disabled =
        s.mode === "kids" ||
        state.viewer === "phone" ||
        (!on && !s.provider_ready?.[service]);
      c.querySelector("small").textContent =
        s.mode === "kids"
          ? "Unavailable in Kids mode"
          : service === "sms" && s.message_route.startsWith("mac_")
            ? "Mac bridge available · account not yet verified"
          : s.provider_ready?.[service]
            ? "Connection configured"
            : "Connection setup needed";
    }
    for (const event of state.events) {
      const key = JSON.stringify(event);
      if (!seen.has(key)) {
        seen.add(key);
        result(event.result || { text: event.text });
      }
    }
  } catch (e) {
    if (e.status === 401) {
      $("main").hidden = true;
      $("#pair-screen").hidden = false;
      $("#pair-message").textContent =
        "This device session ended. Reopen the Mac controls or scan a new phone invitation.";
    } else toast(e.message);
  }
}
$("#command").onsubmit = async (e) => {
  e.preventDefault();
  if (busy) return;
  const text = $("#message").value.trim();
  if (!text) return;
  busy = true;
  $("#send").disabled = true;
  sayYou(text);
  $("#message").value = "";
  showTyping();
  try {
    const d = await api("/api/chat", { text, voice: $("#speak-replies").checked });
    result(d);
    await refresh();
  } catch (e) {
    result({ text: e.message });
  } finally {
    thread().querySelector(".typing")?.remove();
    busy = false;
    $("#send").disabled = false;
    $("#message").focus();
  }
};
$("#message").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    $("#command").requestSubmit();
  }
});
$("#privacy").onclick = () => setting("muted", !state.status.microphone_muted);
$("#mode").onchange = async (e) => {
  await setting("mode", e.target.value);
  thread().replaceChildren();
  seen.clear();
};
$("#hush").onclick = () => setting("hush", true);
for (const b of document.querySelectorAll("[data-prompt]"))
  b.onclick = () => {
    $("#message").value = b.dataset.prompt;
    $("#message").focus();
  };
for (const c of document.querySelectorAll("[data-service]"))
  c.querySelector("button").onclick = () =>
    setting(c.dataset.service, !state.status.integrations[c.dataset.service]);
setInterval(() => {
  if (!document.hidden && !$("main").hidden) refresh();
}, 4000);
let pairToken = "",
  selectedOffer = null,
  profileLoaded = false;
async function initialize() {
  if (location.hash.startsWith("#pair=")) {
    pairToken = location.hash.slice(6);
    history.replaceState(null, "", location.pathname);
  }
  try {
    const session = await api("/api/session");
    const phone = session.viewer === "phone";
    $(".local").textContent = phone ? "Connected to your Luma" : "On this Mac";
    $("#privacy").hidden = phone;
    document.querySelectorAll(".owner-only").forEach((e) => (e.hidden = phone));
    $("#mode").disabled = phone;
    if (!session.paired) {
      $("main").hidden = true;
      $("#pair-screen").hidden = false;
      $("#pair-form").hidden = !pairToken;
      $("#pair-message").textContent = pairToken
        ? "Give this phone a name. It will have access to your Luma conversations, contacts and reviewed actions."
        : "Create a private pairing invitation in the Mac controls, then scan it with this phone.";
      return;
    }
    $("main").hidden = false;
    $("#pair-screen").hidden = true;
    await refresh();
  } catch (e) {
    toast(e.message);
  }
}
$("#pair-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await api("/api/phone/pair", {
      token: pairToken,
      name: $("#pair-name").value,
    });
    pairToken = "";
    await initialize();
  } catch (error) {
    $("#pair-message").textContent = error.message;
  }
};
function button(label, action, cls = "text-button") {
  const b = make("button", label, cls);
  b.type = "button";
  b.onclick = async () => {
    b.disabled = true;
    try {
      await action();
    } catch (e) {
      toast(e.message);
    } finally {
      b.disabled = false;
    }
  };
  return b;
}
function renderExtra(data) {
  renderGroceries(data);
  const adult = data.status.mode !== "kids",
    phone = data.viewer === "phone";
  for (const id of [
    "people",
    "groceries",
    "appointments",
    "phone-connection",
    "personality",
  ])
    $("#" + id).hidden =
      !adult || (phone && ["phone-connection", "personality"].includes(id));
  for (const c of document.querySelectorAll("[data-service]"))
    if (phone) c.querySelector("button").disabled = true;
  $("#contacts-list").replaceChildren();
  $("#contact-options").replaceChildren();
  for (const c of data.contacts || []) {
    const row = make("div", undefined, "memory-row"),
      copy = make("div");
    copy.append(make("b", c.name), make("p", prettyPhone(c.phone) + (c.aliases?.length ? " · " + c.aliases.join(", ") : "")));
    row.append(
      copy,
      button("Remove", async () => {
        await api("/api/contacts/delete", { id: c.id });
        await refresh();
      }),
    );
    $("#contacts-list").append(row);
    const option = make("option");
    option.value = c.name;
    $("#contact-options").append(option);
  }
  const route = data.status.message_route;
  $("#message-route").textContent = !data.status.integrations.sms
    ? "Right now Luma drafts texts for you to send from your phone. Pick a route below to have Luma send them after you say “send it”."
    : route === "luma_number"
      ? "Luma sends from its own number after you approve each text. Replies come back to Luma."
      : route === "twilio"
        ? "Luma sends from your Twilio number after you approve each text."
        : "Luma sends from your own number through this Mac’s Messages after you approve each text. It’s free.";
  renderTexting(data);
  const drafts = $("#message-drafts");
  drafts.replaceChildren();
  for (const d of data.message_drafts || []) {
    const card = make("article", undefined, "receipt");
    card.append(
      make("span", "PHONE DRAFT · NOT SENT", "eyebrow"),
      make("h3", d.name || d.to),
      make("p", d.body),
    );
    card.append(
      button("Copy message", async () => {
        await navigator.clipboard.writeText(d.body);
        toast("Copied. Paste it in Messages and tap Send.");
      }),
    );
    if (/^\+[1-9]\d{7,14}$/.test(d.to)) {
      const link = make("a", "Open Messages ↗", "text-button");
      link.href = "sms:" + d.to;
      card.append(link);
    }
    card.append(
      button("Remove draft", async () => {
        await api("/api/messages/delete-draft", { id: d.id });
        await refresh();
      }),
    );
    drafts.append(card);
  }
  const sms = $("#message-receipts");
  sms.replaceChildren();
  for (const action of (data.actions || []).filter(
    (a) =>
      ["sms.send", "mac_messages.send"].includes(a.tool) && a.result?.status,
  )) {
    const receipt =
      (data.sms_receipts || []).find((r) => r.action_id === action.id) ||
      action.result;
    const card = make("article", undefined, "receipt");
    card.append(
      make("span", "MESSAGE RECEIPT", "eyebrow"),
      make("h3", receipt.status || "Accepted"),
      make("p", receipt.summary),
    );
    if (action.result.message_id)
      card.append(
        button("Check delivery", async () => {
          const r = await api("/api/messages/status", { action_id: action.id });
          toast(r.summary);
          await refresh();
        }),
      );
    sms.append(card);
  }
  const select = $("#booking-service"),
    previous = select.value;
  select.replaceChildren();
  for (const service of data.booking_services || []) {
    const option = make("option", service.service);
    option.value = service.service;
    select.append(option);
  }
  if (previous && Array.from(select.options).some((o) => o.value === previous))
    select.value = previous;
  if (!select.options.length)
    select.append(make("option", "No connected services"));
  const ready =
    data.status.integrations.booking && data.status.provider_ready.booking;
  $("#availability-form button").disabled = !ready || !adult;
  $("#booking-help").textContent = ready
    ? "Choose a service and dates. Every offered time comes from the booking provider."
    : "Connect your Cal.com account and approved services in the Mac settings, then enable appointments. No times are invented.";
  if (!$("#booking-from").value) {
    const start = new Date(),
      end = new Date(Date.now() + 7 * 86400000);
    $("#booking-from").value = start.toISOString().slice(0, 10);
    $("#booking-through").value = end.toISOString().slice(0, 10);
  }
  const bookings = $("#booking-receipts");
  bookings.replaceChildren();
  for (const a of (data.actions || []).filter(
    (a) => a.tool === "booking.create" && a.result?.booking_uid,
  )) {
    const r = a.result,
      card = make("article", undefined, "receipt");
    card.append(
      make("span", "BOOKING RECEIPT", "eyebrow"),
      make("h3", r.title || "Appointment"),
      make("p", `${r.status} · ${new Date(r.start).toLocaleString()}`),
      make("p", r.summary),
    );
    card.append(
      button("Check appointment", async () => {
        const updated = await api("/api/booking/status", {
          booking_uid: r.booking_uid,
        });
        result(updated);
      }),
    );
    bookings.append(card);
  }
  if (!phone) {
    const conn = data.phone,
      active = !!conn.origin,
      addresses = conn.addresses || [],
      address = $("#phone-address"),
      prior = address.value;
    address.replaceChildren();
    for (const ip of addresses) {
      const o = make("option", ip);
      o.value = ip;
      address.append(o);
    }
    if (addresses.includes(prior)) address.value = prior;
    $("#phone-address-label").hidden = active || !addresses.length;
    $("#phone-start").hidden = active;
    $("#phone-start").disabled = !addresses.length;
    $("#phone-invite").hidden = !active;
    $("#phone-status").textContent = active
      ? `Ready at ${conn.origin}. Connect your phone to the same Wi-Fi, then create an invitation.`
      : addresses.length
        ? "A local network is available. Start the encrypted connection, then scan an invitation."
        : "Connect this Mac and your phone to the same home Wi-Fi. No reachable private address is available here yet.";
    const devices = $("#paired-devices");
    empty(devices, "No phones paired yet.");
    if (conn.devices?.length) {
      devices.replaceChildren();
      for (const d of conn.devices) {
        const row = make("div", undefined, "memory-row");
        row.append(
          make(
            "p",
            `${d.name} · ${d.active ? "Connected" : "Expired or removed"}`,
          ),
        );
        if (d.active)
          row.append(
            button("Remove", async () => {
              await api("/api/phone/revoke", { id: d.id });
              await refresh();
            }),
          );
        devices.append(row);
      }
    }
    if (document.activeElement !== $("#message-transport"))
      $("#message-transport").value = data.status.message_route;
    $("#model-info").textContent =
      (data.status.model_name?.includes("Qwen") ? "Qwen3 4B" : "Llama 3.2 3B") +
      " · runs on this Mac";
    if (!profileLoaded && adult) {
      const p = data.status.profile;
      $("#profile-name").value = p.name;
      $("#profile-tone").value = p.tone;
      $("#profile-style").value = p.language_style;
      $("#profile-verbosity").value = p.verbosity;
      profileLoaded = true;
    }
  }
}
$("#contact-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const aliases = $("#contact-aliases").value.split(",").map((a) => a.trim()).filter(Boolean);
    let phone = $("#contact-phone").value.replace(/[\s().-]/g, "");
    if (/^\d{10}$/.test(phone)) phone = "+1" + phone;
    else if (/^1\d{10}$/.test(phone)) phone = "+" + phone;
    await api("/api/contacts/save", { name: $("#contact-name").value, phone, ...(aliases.length ? { aliases } : {}) });
    e.target.reset();
    await refresh();
  } catch (error) {
    toast(error.message);
  }
};
$("#message-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    result(
      await api("/api/messages/prepare", {
        recipient: $("#message-recipient").value,
        body: $("#message-body").value,
      }),
    );
    await refresh();
    $("#results").scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (error) {
    toast(error.message);
  }
};
$("#phone-start").onclick = async () => {
  try {
    await api("/api/phone/start", { host: $("#phone-address").value });
    await refresh();
  } catch (e) {
    toast(e.message);
  }
};
$("#phone-invite").onclick = async () => {
  try {
    const d = await api("/api/phone/invite", {});
    $("#pair-invite").hidden = false;
    $("#pair-qr").src = d.qr;
    $("#pair-link").href = d.url;
    setTimeout(
      () => {
        $("#pair-invite").hidden = true;
        $("#pair-qr").removeAttribute("src");
        $("#pair-link").removeAttribute("href");
      },
      Math.max(0, d.expires_at * 1000 - Date.now()),
    );
  } catch (e) {
    toast(e.message);
  }
};
$("#personality-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await api("/api/profile", {
      ...state.status.profile,
      name: $("#profile-name").value,
      tone: $("#profile-tone").value,
      language_style: $("#profile-style").value,
      verbosity: $("#profile-verbosity").value,
    });
    toast("Your conversation preferences are saved locally.");
    await refresh();
  } catch (error) {
    toast(error.message);
  }
};
$("#availability-form").onsubmit = async (e) => {
  e.preventDefault();
  const submit = e.target.querySelector("button");
  submit.disabled = true;
  submit.textContent = "Checking availability…";
  try {
    const d = await api("/api/booking/availability", {
      service: $("#booking-service").value,
      start: $("#booking-from").value,
      end: $("#booking-through").value,
      time_zone: state.status.time_zone,
    });
    const grid = $("#booking-slots");
    empty(grid, d.summary || "No available times.");
    if (d.slots?.length) {
      grid.replaceChildren();
      for (const slot of d.slots) {
        const b = button(
          "",
          async () => {
            selectedOffer = slot;
            $("#booking-form").hidden = false;
            $("#booking-selection").textContent = slot.title;
            $("#booking-selection-detail").textContent =
              `${slot.local_start} · ${d.time_zone} · free appointment`;
            grid
              .querySelectorAll("button")
              .forEach((e) => e.setAttribute("aria-pressed", "false"));
            b.setAttribute("aria-pressed", "true");
          },
          "slot",
        );
        b.append(
          make("b", new Date(slot.start).toLocaleString()),
          make("small", d.time_zone),
        );
        grid.append(b);
      }
    }
  } catch (error) {
    toast(error.message);
  } finally {
    submit.disabled = false;
    submit.textContent = "Find available times ↗";
  }
};
$("#booking-form").onsubmit = async (e) => {
  e.preventDefault();
  if (!selectedOffer) return;
  try {
    const r = await api("/api/booking/prepare", {
      offer_id: selectedOffer.offer_id,
      name: $("#attendee-name").value,
      email: $("#attendee-email").value,
    });
    result(r);
    await refresh();
    $("#results").scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (error) {
    toast(error.message);
  }
};

function renderTexting(data) {
  const card = $("#luma-number");
  if (!card) return;
  const t = data.status.texting || {},
    cloud = t.luma_number || {},
    a = cloud.account;
  card.replaceChildren();
  const head = make("div", undefined, "plan-head");
  head.append(make("span", "LUMA’S NUMBER", "eyebrow"));
  if (a) head.append(make("span", a.plan === "plus" ? "Luma Plus" : "Free", "plan-badge " + (a.plan === "plus" ? "plus" : "")));
  card.append(head);
  if (!cloud.signed_in && !cloud.verifying) {
    card.append(
      make("h3", "Text anyone, even without your phone."),
      make("p", "Luma gets its own number for your texts. Free texts every month; Luma Plus adds more and a number that’s just yours.", "intro"),
    );
    const form = make("form", undefined, "inline-form");
    form.innerHTML = '<label>Your name<input name="name" maxlength="60" required placeholder="Marvin"></label><label>Your mobile<input name="phone" type="tel" required placeholder="+1 919 555 0123"></label><button class="button">Text me a code</button>';
    form.onsubmit = async (e) => {
      e.preventDefault();
      let phone = form.phone.value.replace(/[\s().-]/g, "");
      if (/^\d{10}$/.test(phone)) phone = "+1" + phone;
      try {
        toast((await api("/api/texting/start", { name: form.name.value, phone })).summary);
        await refresh();
      } catch (error) {
        toast(error.message);
      }
    };
    card.append(form, make("p", "Your number is only used to verify it’s you and to sign your texts. US and Canada for now.", "footnote"));
    return;
  }
  if (!cloud.signed_in) {
    const form = make("form", undefined, "inline-form");
    form.innerHTML = '<label>Code from the text<input name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="10" required></label><button class="button">Verify</button>';
    form.onsubmit = async (e) => {
      e.preventDefault();
      try {
        toast((await api("/api/texting/finish", { code: form.code.value.trim() })).summary);
        await refresh();
      } catch (error) {
        toast(error.message);
      }
    };
    card.append(make("h3", "Check your texts."), form);
    return;
  }
  if (a) {
    const used = a.texts_used ?? 0,
      limit = a.texts_limit || 1;
    card.append(make("h3", `${a.texts_left ?? Math.max(0, limit - used)} texts left this month`));
    const meter = make("div", undefined, "meter"),
      fill = make("i");
    fill.style.width = Math.min(100, (100 * used) / limit) + "%";
    meter.append(fill);
    card.append(meter, make("p", `${used} of ${limit} used · resets ${a.period_ends ? new Date(a.period_ends).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "monthly"}`, "footnote"));
    if (a.number) card.append(make("p", (a.dedicated_number ? "Your Luma number: " : "Sending from Luma’s shared number: ") + prettyPhone(a.number), "intro"));
    else if (a.number_pending) card.append(make("p", "Your own Luma number is on its way.", "intro"));
  }
  const actions = make("div", undefined, "review-actions");
  if (t.route !== "luma_number")
    actions.append(button("Text from Luma’s number", async () => {
      await api("/api/messages/route", { route: "luma_number" });
      await refresh();
    }, "button"));
  if (a?.plan === "plus") actions.append(button("Manage Luma Plus", async () => window.open((await api("/api/texting/manage", {})).url, "_blank", "noopener")));
  else if (a?.plus?.available !== false)
    actions.append(button(`Get Luma Plus · ${a?.plus?.price || "$9.99/month"}`, openUpgrade, t.route === "luma_number" ? "button" : "pill"));
  actions.append(
    button("Refresh", async () => {
      await api("/api/texting/account", {});
      await refresh();
    }),
    button("Disconnect", async () => {
      await api("/api/texting/signout", {});
      await refresh();
    }),
  );
  card.append(actions);
  if (a?.plan !== "plus" && a?.plus)
    card.append(make("p", `Luma Plus: ${a.plus.texts_limit} texts a month, your own Luma number, replies forwarded to Luma. Texting from your own number through Messages stays free and unlimited.`, "footnote"));
}
$("#browser-show").onclick = async () => {
  try {
    toast((await api("/api/browser/show", { url: $("#browser-site").value })).summary);
  } catch (e) {
    toast(e.message);
  }
};
$("#browser-hide").onclick = async () => {
  try {
    toast((await api("/api/browser/hide", {})).summary);
  } catch (e) {
    toast(e.message);
  }
};
$("#message-route-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await api("/api/messages/route", { route: $("#message-transport").value });
    toast("Texting route saved. Every send still needs review.");
    await refresh();
  } catch (error) {
    toast(error.message);
  }
};
function addGroceryItem(name = "", quantity = 1, unit = "each") {
  const row = make("div", undefined, "grocery-row"),
    item = make("input"),
    qty = make("input"),
    measure = make("select");
  item.placeholder = "Item, e.g. large eggs · one dozen";
  item.value = name;
  item.required = true;
  item.maxLength = 120;
  item.setAttribute("aria-label", "Grocery item");
  qty.type = "number";
  qty.min = "0.01";
  qty.max = "1000";
  qty.step = "0.01";
  qty.value = quantity;
  qty.required = true;
  qty.setAttribute("aria-label", "Quantity");
  for (const value of [
    "each",
    "package",
    "pound",
    "ounce",
    "gallon",
    "liter",
    "bunch",
  ]) {
    const option = make("option", value);
    option.value = value;
    measure.append(option);
  }
  measure.value = unit;
  measure.setAttribute("aria-label", "Unit");
  row.append(
    item,
    qty,
    measure,
    button("×", async () => row.remove()),
  );
  $("#grocery-items").append(row);
}
$("#grocery-add").onclick = () => addGroceryItem();
addGroceryItem();
function renderGroceries(data) {
  const ready =
    data.status.mode !== "kids" &&
    data.status.integrations.shopping &&
    data.status.provider_ready.groceries;
  $("#grocery-create").disabled = !ready;
  $("#retailer-search").disabled = !ready;
  $("#grocery-status").textContent = ready
    ? "Review the exact items and quantities before creating the merchant list. Payment stays in merchant checkout."
    : "Connect an Instacart Developer Platform account and enable shopping on the Mac to create a real list. No order or payment has been made.";
  const target = $("#grocery-receipts");
  target.replaceChildren();
  for (const r of data.grocery_receipts || []) {
    const card = make("article", undefined, "receipt");
    card.append(
      make("span", "SHOPPABLE LIST · CHECKOUT REQUIRED", "eyebrow"),
      make("h3", r.title),
    );
    for (const item of r.items || [])
      card.append(make("p", `${item.quantity} ${item.unit} · ${item.name}`));
    card.append(
      make(
        "p",
        "Product matches, price, inventory and delivery slot need review at the merchant. No order has been placed.",
      ),
    );
    if (/^https:\/\//.test(r.url)) {
      const link = make("a", "Review products & checkout ↗", "button");
      link.href = r.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      card.append(link);
    }
    card.append(
      button("Prepare a text with this list", async () => {
        $("#message-body").value =
          `Could you pick up these groceries? ${(r.items || []).map((i) => `${i.quantity} ${i.unit} ${i.name}`).join(", ")}. Here is the list to review: ${r.url}`;
        $("#people").scrollIntoView({ behavior: "smooth" });
        $("#message-recipient").focus();
      }),
    );
    target.append(card);
  }
}
$("#grocery-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const items = Array.from($("#grocery-items").children).map((row) => ({
      name: row.querySelector("input").value,
      quantity: Number(row.querySelector("input[type=number]").value),
      unit: row.querySelector("select").value,
    }));
    const r = await api("/api/groceries/create", {
      title: $("#grocery-title").value,
      items,
    });
    toast(r.summary);
    await refresh();
  } catch (error) {
    toast(error.message);
  }
};
$("#retailer-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    const r = await api("/api/groceries/nearby", {
      postal_code: $("#grocery-zip").value,
      country_code: "US",
    });
    const target = $("#retailer-results");
    empty(target, "No nearby retailers returned for this area.");
    if (r.retailers.length) {
      target.replaceChildren();
      for (const store of r.retailers)
        target.append(make("p", store.name, "routine"));
    }
  } catch (error) {
    toast(error.message);
  }
};
initialize();
