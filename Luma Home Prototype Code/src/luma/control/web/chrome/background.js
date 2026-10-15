// Luma for Chrome: keeps one request open to Luma on this computer and does what it asks.
const LUMA = "http://127.0.0.1:8095";
let running = false;

async function token() { return (await chrome.storage.local.get("token")).token; }

async function loop() {
  if (running) return;
  running = true;
  try {
    while (true) {
      const t = await token();
      if (!t) break;
      let cmd = null;
      try {
        const r = await fetch(`${LUMA}/api/ext/next?token=${encodeURIComponent(t)}`);
        if (r.status === 403) { await chrome.storage.local.remove("token"); break; }
        cmd = (await r.json()).command;
      } catch (_) { await new Promise((ok) => setTimeout(ok, 5000)); continue; }  // Luma not running yet
      if (!cmd) continue;
      let result;
      try { result = await run(cmd); } catch (e) { result = { error: String(e).slice(0, 200) }; }
      fetch(`${LUMA}/api/ext/done?token=${encodeURIComponent(t)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: cmd.id, result }) }).catch(() => {});
    }
  } finally { running = false; }
}

function loaded(tabId) {
  return new Promise((ok) => {
    const done = (id, info) => { if (id === tabId && info.status === "complete") { chrome.tabs.onUpdated.removeListener(done); ok(); } };
    chrome.tabs.onUpdated.addListener(done);
    setTimeout(ok, 15000);
  });
}

async function first(tabId, selector) {
  // Click through to the first song or video the search shows.
  try {
    const [{ result } = {}] = await chrome.scripting.executeScript({ target: { tabId }, args: [selector], func: (sel) => {
      const link = document.querySelector(sel);
      if (!link) return null;
      location.href = link.href;
      return (link.getAttribute("title") || link.textContent || "").trim().slice(0, 120) || link.href;
    } });
    return result;
  } catch (_) { return null; }  // the page didn't load (offline, or an error page)
}

async function playIn(tab, q) {
  await loaded(tab.id);
  await new Promise((ok) => setTimeout(ok, 2500));
  let title = await first(tab.id, 'a[href*="watch?v="]');
  if (!title) {
    await chrome.tabs.update(tab.id, { url: "https://www.youtube.com/results?search_query=" + q });
    await loaded(tab.id);
    await new Promise((ok) => setTimeout(ok, 2000));
    title = await first(tab.id, 'a#video-title[href*="watch?v="], a[href^="/watch?v="]');
  }
  if (!title) return { error: "YouTube didn't load. Is this computer online?", tab: tab.id };
  await new Promise((ok) => setTimeout(ok, 3500));  // let it start before stepping back
  return { playing: title, tab: tab.id };
}

async function run(cmd) {
  if (cmd.kind === "open") {
    const url = String(cmd.url || "");
    if (!/^https?:\/\//i.test(url)) throw new Error("Only web addresses.");
    const tab = await chrome.tabs.create({ url, active: cmd.background ? false : true });
    return { opened: url, tab: tab.id };
  }
  if (cmd.kind === "play") {
    // Music in a tab of its own, behind what they're doing. Chrome won't start sound in a tab that was never shown,
    // so the music tab shows for a moment, starts, and then the tab they were on comes back to the front.
    const [was] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    const q = encodeURIComponent(cmd.query || "music");
    const tab = await chrome.tabs.create({ url: "https://music.youtube.com/search?q=" + q, active: true });
    try { return await playIn(tab, q); }
    finally { if (was?.id) chrome.tabs.update(was.id, { active: true }).catch(() => {}); }
  }

  if (cmd.kind === "read") {
    const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    if (!tab || !/^https?:/.test(tab.url || "")) return { title: tab?.title || "", url: tab?.url || "", text: "" };
    const [{ result } = {}] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: () => document.body.innerText.slice(0, 8000) });
    return { title: tab.title, url: tab.url, text: result || "" };
  }
  if (cmd.kind === "tabs") {
    const tabs = await chrome.tabs.query({});
    return { tabs: tabs.slice(0, 40).map((t) => ({ title: t.title, url: t.url, active: t.active })) };
  }
  throw new Error("Unknown step.");
}

chrome.runtime.onStartup.addListener(loop);
chrome.runtime.onInstalled.addListener(() => { chrome.alarms.create("luma", { periodInMinutes: 1 }); loop(); });
chrome.alarms.onAlarm.addListener(loop);
chrome.storage.onChanged.addListener((c) => { if (c.token?.newValue) loop(); });
loop();
