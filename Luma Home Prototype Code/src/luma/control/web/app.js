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
function result(data) {
  const identity = data.action && `${data.action}:${data.state}`;
  if (identity && renderedActions.has(identity)) return;
  if (identity) renderedActions.add(identity);
  const box = make("article", undefined, "result");
  if (data.state === "pending") {
    box.append(
      make("span", "READY FOR YOUR REVIEW", "eyebrow"),
      make("h3", data.tool.replaceAll(".", " · ")),
    );
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
      row.append(
        make("b", k.replaceAll("_", " ") + ": "),
        make("span", String(v)),
      );
      box.append(row);
    }
    box.append(
      make(
        "p",
        "Review these exact details. No message, booking, order or device command has been sent.",
        "footnote",
      ),
    );
    const buttons = make("div", undefined, "review-actions");
    for (const [label, path] of [
      ["Confirm action", "/api/confirm"],
      ["Cancel", "/api/cancel"],
    ]) {
      const b = make("button", label, label === "Cancel" ? "pill" : "button");
      b.onclick = async () => {
        buttons.querySelectorAll("button").forEach((e) => (e.disabled = true));
        try {
          const r = await api(path, {
            id: data.action,
            token: data.confirm_token,
          });
          result(r);
        } catch (e) {
          result({ summary: e.message });
        }
        await refresh();
      };
      buttons.append(b);
    }
    box.append(buttons);
  } else {
    const text =
      data.text ||
      data.summary ||
      (data.memories
        ? data.memories.length
          ? "Here’s what you asked me to remember."
          : "No matching memories yet."
        : data.tasks
          ? "Your reminders are below."
          : data.state === "cancelled"
            ? "Action cancelled."
            : "Done.");
    box.append(make("p", text));
    if (data.memories)
      for (const m of data.memories)
        box.append(make("p", m.text, "remembered"));
    if (data.results)
      for (const h of data.results) {
        const a = make("a", h.title);
        if (/^https:\/\//.test(h.url)) {
          a.href = h.url;
          a.target = "_blank";
          a.rel = "noreferrer";
          box.append(a, make("p", h.snippet, "footnote"));
        }
      }
    if (data.handoff && /^https:\/\//.test(data.url)) {
      const a = make("a", "Continue to merchant ↗", "button");
      a.href = data.url;
      a.target = "_blank";
      a.rel = "noreferrer";
      box.append(
        a,
        make(
          "p",
          `List: ${data.items}. Budget: $${(data.budget_cents / 100).toFixed(2)}. Cart and payment still need review at the merchant.`,
          "footnote",
        ),
      );
    }
  }
  $("#results").prepend(box);
  while ($("#results").children.length > 6)
    $("#results").lastElementChild.remove();
}
function empty(target, text) {
  target.replaceChildren(make("p", text, "empty"));
}
async function refresh() {
  try {
    state = await api("/api/state");
    const s = state.status;
    renderExtra(state);
    $("#privacy").textContent = s.microphone_muted
      ? "Microphone off"
      : "Microphone on · mute";
    $("#privacy").classList.toggle("enabled", !s.microphone_muted);
    $("#device-status").textContent = s.microphone_muted
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
        row.append(b);
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
        s.mode === "kids" || state.viewer === "phone" || (!on && !s.provider_ready?.[service]);
      c.querySelector("small").textContent =
        s.mode === "kids"
          ? "Unavailable in Kids mode"
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
  busy = true;
  $("#send").disabled = true;
  $("#send").textContent = "Thinking locally…";
  const text = $("#message").value;
  try {
    const d = await api("/api/chat", { text });
    result(d);
    $("#message").value = "";
    await refresh();
  } catch (e) {
    result({ summary: e.message });
  } finally {
    busy = false;
    $("#send").disabled = false;
    $("#send").textContent = "Ask Luma ↗";
  }
};
$("#privacy").onclick = () => setting("muted", !state.status.microphone_muted);
$("#mode").onchange = async (e) => {
  await setting("mode", e.target.value);
  $("#results").replaceChildren();
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
    copy.append(make("b", c.name), make("p", c.phone));
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
  $("#message-route").textContent = data.status.integrations.sms
    ? data.status.message_route === "twilio"
      ? "Review before sending from the configured Twilio number."
      : "Review before sending through this Mac’s Messages account. Acceptance is not a delivery receipt."
    : "Prepare a draft for your own phone number. You will copy the text and tap Send in Messages.";
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
    await api("/api/contacts/save", {
      name: $("#contact-name").value,
      phone: $("#contact-phone").value.replace(/[\s()-]/g, ""),
    });
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
