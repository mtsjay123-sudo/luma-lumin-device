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
  if (!r.ok) throw Error(d.error || "Local request failed");
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
function result(data) {
  const box = make("article", undefined, "result");
  if (data.state === "pending") {
    box.append(
      make("span", "READY FOR YOUR REVIEW", "eyebrow"),
      make("h3", data.tool.replaceAll(".", " · ")),
    );
    for (const [k, v] of Object.entries(data.arguments)) {
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
        "Review these exact details. No message, order or device command has been sent.",
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
      c.querySelector("button").disabled = s.mode === "kids";
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
    toast(e.message);
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
refresh();
setInterval(() => {
  if (!document.hidden) refresh();
}, 4000);
