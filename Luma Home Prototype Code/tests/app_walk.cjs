// Walks the phone app and the computer app in a real browser, at several sizes, light and dark, and prints what's
// wrong as JSON: errors in the console, anything that failed to load, a page wider than its screen, a button too small
// for a thumb, anything a person can press sitting under the floating ask bar at the end of a page, and a few things
// the apps must say right (one memory count, a task's real days, no model's name where a customer reads).
// Run by tests/test_app_walk.py: node app_walk.cjs <base url>
const { chromium } = require("playwright");
const base = process.argv[2];
const problems = [], seen = { screens: 0 }, access = [], looks = {};
let sees = null, browser = "";
let decoder = null;
const add = (where, kind, text) => problems.push({ where, kind, text: String(text).slice(0, 200) });

function watch(page, where) {
  page.on("console", (m) => { if (m.type() === "error") add(where, "console", m.text()); });
  page.on("pageerror", (e) => add(where, "pageerror", e));
  page.on("response", (r) => { if (r.status() >= 400) add(where, "http " + r.status(), r.url().replace(base, "")); });
}
async function layout(page, where, phone) {
  seen.screens += 1;
  const found = await page.evaluate((phone) => {
    const W = window.innerWidth, out = { wider: document.documentElement.scrollWidth > W + 1, tiny: [] };
    if (phone) for (const el of document.querySelectorAll("button, a")) {
      const r = el.getBoundingClientRect();
      if (el.offsetParent && el.innerText.trim() && r.width && (r.height < 30 || r.width < 30)) out.tiny.push(el.innerText.trim().slice(0, 24) + " " + Math.round(r.width) + "x" + Math.round(r.height));
    }
    return out;
  }, phone);
  if (found.wider) add(where, "wider than the screen", "");
  for (const t of found.tiny.slice(0, 4)) add(where, "too small to tap", t);
  for (const a of await accessible(page, phone)) access.push({ where, ...a });
  looks[where] = await fingerprint(page);
  if (process.env.LUMA_WALK_SHOTS) await page.screenshot({ path: require("path").join(process.env.LUMA_WALK_SHOTS, where.replace(/[^a-z0-9]+/gi, "-") + ".png"), animations: "disabled", caret: "hide" }).catch(() => {});
}
// Can someone who doesn't see it well, or doesn't see it at all, use this screen? Three things code can tell: a control
// with nothing to call it, words too faint against what's behind them (WCAG AA: 4.5 to 1, 3 to 1 for big type), and on
// the phone a thing to press smaller than a thumb (44 px, the game plan's number). Words over a picture or a gradient
// are left out: what's behind them can't be read from here.
async function accessible(page, phone) {
  return page.evaluate((phone) => {
    const out = [], seen = new Set();
    const shown = (el) => { const r = el.getBoundingClientRect(), st = getComputedStyle(el); return r.width > 0 && r.height > 0 && st.visibility !== "hidden" && st.display !== "none" && +st.opacity > 0.05 && el.offsetParent !== null && r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth; };
    const say = (kind, text) => { const k = kind + "|" + text; if (!seen.has(k)) { seen.add(k); out.push({ kind, text: text.slice(0, 80) }); } };
    for (const el of document.querySelectorAll("button, a[href], input, select, textarea, [role=button], [role=switch]")) {
      if (!shown(el) || el.type === "hidden" || el.closest("[aria-hidden=true]")) continue;
      const labelled = el.getAttribute("aria-labelledby") && document.getElementById(el.getAttribute("aria-labelledby").split(" ")[0]);
      const label = el.id && document.querySelector(`label[for="${el.id}"]`);
      const name = (el.innerText || "").trim() || el.getAttribute("aria-label") || el.getAttribute("title") || el.getAttribute("placeholder") || (labelled && labelled.innerText) || (label && label.innerText) || (el.closest("label") && el.closest("label").innerText.trim()) || (el.querySelector("img[alt]") && el.querySelector("img[alt]").alt);
      if (!name) say("nothing to call it", (el.id ? "#" + el.id : el.tagName.toLowerCase() + "." + el.className).slice(0, 60));
      if (phone && !["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName)) { const r = el.getBoundingClientRect(); if (r.height < 43.5 || r.width < 43.5) say("smaller than a thumb", ((el.innerText || el.getAttribute("aria-label") || el.id || "").trim().slice(0, 24) + " " + Math.round(r.width) + "x" + Math.round(r.height))); }
    }
    for (const img of document.querySelectorAll("img")) if (shown(img) && !img.hasAttribute("alt") && !img.closest("[aria-hidden=true]")) say("a picture with no words for it", (img.id || img.src.split("/").pop()).slice(0, 60));
    const rgba = (c) => { const m = c.match(/[\d.]+/g); return m ? [+m[0], +m[1], +m[2], m.length > 3 ? +m[3] : 1] : null; };
    const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
    // What's behind a word: where it's on the screen, everything painted under that very spot (a bar that floats over
    // a dark stage has the stage behind it, though the stage isn't its parent); off the screen, its parents. Where a
    // picture, a gradient or frosted glass is behind it, this can't say, and says nothing.
    const under = (el, node) => {
      const range = document.createRange(); range.selectNodeContents(node);
      const r = range.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
      if (!(x >= 0 && y >= 0 && x < innerWidth && y < innerHeight)) return null;
      const stack = document.elementsFromPoint(x, y), at = stack.indexOf(el);
      return at < 0 ? [] : stack.slice(at);
    };
    const behind = (el, node) => { let over = null; const layers = under(el, node) || (() => { const up = []; for (let n = el; n; n = n.parentElement) up.push(n); return up; })(); if (!layers.length) return null; for (const n of layers) { const st = getComputedStyle(n); if (st.backgroundImage !== "none" || st.backdropFilter && st.backdropFilter !== "none") return null; const b = rgba(st.backgroundColor); if (b && b[3] > 0) { if (b[3] >= 0.99) { if (!over) return b; const a = over[3]; return [over[0] * a + b[0] * (1 - a), over[1] * a + b[1] * (1 - a), over[2] * a + b[2] * (1 - a), 1]; } if (!over) over = b; } } return null; };
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.nodeValue.trim(), el = node.parentElement;
      if (text.length < 2 || !el || !shown(el) || el.closest("[aria-hidden=true], canvas, svg")) continue;
      const st = getComputedStyle(el), fg = rgba(st.color), bg = behind(el, node);
      if (!fg || !bg || fg[3] < 0.99) continue;
      let dim = 1; for (let n = el; n; n = n.parentElement) dim *= +getComputedStyle(n).opacity; if (dim < 0.99) continue;
      const l1 = lum(fg), l2 = lum(bg), ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
      const size = parseFloat(st.fontSize), big = size >= 24 || (size >= 18.66 && +st.fontWeight >= 700);
      if (ratio < (big ? 3 : 4.5)) say("words too faint", text.slice(0, 32) + " (" + ratio.toFixed(1) + " to 1) " + (el.id ? "#" + el.id : el.tagName.toLowerCase() + "." + String(el.className).split(" ")[0]));
    }
    return out;
  }, phone);
}
// What a screen looks like, as 1,024 bits: the whole page's picture shrunk to 32 by 32 and each square marked lighter or darker than
// the screen's middle grey. The water and anything else that moves is hidden first. Two walks of the same screen give
// the same bits or nearly; a layout that jumped doesn't. tests/test_app_walk.py compares these with the last good ones.
async function fingerprint(page) {
  // a sheet sliding up or a list still arriving isn't the screen yet: looked at once it has stopped changing
  let last = await once(page);
  for (let i = 0; i < 8; i++) { await page.waitForTimeout(200); const now = await once(page); if (now === last) return now; last = now; }
  return last;
}
async function once(page) {
  const shot = (await page.screenshot({ type: "png", fullPage: true, animations: "disabled", caret: "hide", mask: [page.locator("canvas, video")] })).toString("base64");
  return decoder.evaluate(async (data) => {
    const img = await createImageBitmap(await (await fetch("data:image/png;base64," + data)).blob());
    const c = new OffscreenCanvas(32, 32), g = c.getContext("2d");
    g.drawImage(img, 0, 0, 32, 32);
    const px = g.getImageData(0, 0, 32, 32).data, grey = [];
    for (let i = 0; i < px.length; i += 4) grey.push(0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2]);
    const mid = [...grey].sort((a, b) => a - b)[512];
    let bits = ""; for (const v of grey) bits += v > mid ? "1" : "0";
    let hex = ""; for (let i = 0; i < 1024; i += 4) hex += parseInt(bits.slice(i, i + 4), 2).toString(16);
    return hex;
  }, shot).catch(() => "");
}
// Can the two checks above see anything? On one screen the walk breaks things on purpose (the dock gone, a panel
// gone, Luma's stage gone; a button with no name and too small to tap, words nearly the colour of what's behind them,
// a picture with no words for it), says what each check made of it, and puts everything back.
const apart = (x, y) => { let n = 0; for (let i = 0; i < Math.min(x.length, y.length); i++) { let v = parseInt(x[i], 16) ^ parseInt(y[i], 16); while (v) { n += v & 1; v >>= 1; } } return n; };
async function proveItSees(page) {
  const whole = await fingerprint(page), sees = { looks: {}, access: [] };
  for (const [name, sel] of [["the dock gone", ".dock"], ["a panel gone", "#memory"], ["the stage gone", ".hello"]]) {
    const had = await page.evaluate((sel) => { const el = document.querySelector(sel); if (!el) return false; el.dataset.was = el.style.display; el.style.display = "none"; return true; }, sel);
    if (!had) continue;
    await page.waitForTimeout(150); sees.looks[name] = apart(whole, await once(page));
    await page.evaluate((sel) => { const el = document.querySelector(sel); el.style.display = el.dataset.was || ""; delete el.dataset.was; }, sel);
    await page.waitForTimeout(150);
  }
  await page.evaluate(() => {
    const box = document.createElement("div"); box.id = "walk-broken"; box.style.cssText = "position:fixed;left:8px;top:120px;z-index:99;background:#ffffff;padding:4px";
    const b = document.createElement("button"); b.style.cssText = "width:20px;height:20px;padding:0;border:0";
    const w = document.createElement("span"); w.textContent = "words nobody could read"; w.style.cssText = "color:#f4f4f4;background:#ffffff;font-size:14px";
    const i = document.createElement("img"); i.src = "data:image/gif;base64,R0lGODlhAQABAAAAACw="; i.style.cssText = "width:10px;height:10px";
    box.append(b, w, i); document.body.append(box);
  });
  sees.access = [...new Set((await accessible(page, true)).map((a) => a.kind))].sort();
  await page.evaluate(() => document.getElementById("walk-broken")?.remove());
  sees.back = apart(whole, await once(page));     // and the screen is as it was
  return sees;
}
async function skipFirstRun(p) {
  for (let i = 0; i < 12; i++) {
    const next = await p.$('#tour-skip, button:has-text("Skip"), button:has-text("Next"), button:has-text("Continue"), button:has-text("Get started"), button:has-text("Done")');
    if (next && await next.isVisible()) { await next.click({ timeout: 3000 }).catch(() => {}); await p.waitForTimeout(250); } else break;
  }
}
(async () => {
  const b = await chromium.launch();
  browser = b.version();
  decoder = await (await b.newContext()).newPage();
  await decoder.goto("about:blank");
  for (const scheme of ["light", "dark"]) {
    for (const width of [360, 390, 430]) {
      const where = `phone ${width} ${scheme}`;
      const ctx = await b.newContext({ viewport: { width, height: 800 }, isMobile: true, hasTouch: true, colorScheme: scheme });
      const p = await ctx.newPage(); watch(p, where);
      await p.goto(base + "/phone/", { waitUntil: "networkidle" }); await p.waitForTimeout(500);
      await skipFirstRun(p); await p.waitForTimeout(400);
      await layout(p, where + " home", true);
      if (width === 390 && scheme === "dark") sees = await proveItSees(p);
      const said = await p.evaluate(() => ({ brain: document.getElementById("brain")?.innerText || "", deck: document.querySelectorAll("#deck > *").length,
        cards: [...document.querySelectorAll("#deck > *")].map((c) => c.innerText).join(" | ") }));
      if (/qwen|llama|gguf/i.test(said.brain)) add(where, "a model's name where a customer reads", said.brain);
      if (/long day at work/i.test(said.cards)) add(where, "a passing remark is a memory card", said.cards);
      const how = await p.evaluate(() => ({ shown: !!document.getElementById("how") && !document.getElementById("how").hidden,
        text: document.getElementById("how-rows")?.innerText || "", forget: document.querySelectorAll(".how-forget").length }));
      if (!how.shown || !/listen, not fix it/i.test(how.text) || !/just need to vent/i.test(how.text) || how.forget < 2)
        add(where, "how to be with you isn't shown in their own words, each line forgettable", JSON.stringify(how));
      for (const sel of ["#chain-list > *", "#deck > *", "#make-room"]) {
        const el = await p.$(sel); if (!el || !(await el.isVisible())) continue;
        await el.click({ timeout: 3000 }).catch(() => add(where, "couldn't press", sel));
        await p.waitForTimeout(300); await layout(p, `${where} sheet ${sel}`, true);
        const c = await p.$("#sheet-close"); if (c && await c.isVisible()) await c.click({ timeout: 3000 }).catch(() => {});
        await p.waitForTimeout(250);
      }
      await ctx.close();
    }
    for (const width of [1024, 1280, 1440]) {
      const where = `computer ${width} ${scheme}`;
      const ctx = await b.newContext({ viewport: { width, height: 800 }, colorScheme: scheme });
      const p = await ctx.newPage(); watch(p, where);
      await p.goto(base + "/desktop/", { waitUntil: "networkidle" }); await p.waitForTimeout(900);
      await skipFirstRun(p);
      const more = await p.$("#nav-more"); if (more && await more.isVisible()) await more.click({ timeout: 3000 }).catch(() => add(where, "couldn't press", "More"));
      for (const v of ["work", "identity", "goals", "feed", "news", "ideas", "projects", "library", "apps"]) {
        const el = await p.$(`[data-view="${v}"]`);
        if (!el || !(await el.isVisible())) { add(where, "not in the side bar", v); continue; }
        await el.click({ timeout: 3000 }).catch(() => add(where, "couldn't press", v)); await p.waitForTimeout(600);
        await layout(p, `${where} ${v}`, false);
        const under = await p.evaluate(() => {
          const view = document.querySelector(".view:not([hidden])"), dock = document.getElementById("dock-chat");
          if (!view || !dock || dock.hidden) return [];
          let sc = view; while (sc && sc.scrollHeight <= sc.clientHeight + 2) sc = sc.parentElement;
          if (sc) sc.scrollTop = sc.scrollHeight;
          const d = dock.getBoundingClientRect(), out = [];
          for (const x of view.querySelectorAll("button, a, input")) { const r = x.getBoundingClientRect(); if (r.width && r.height && r.right > d.left && r.left < d.right && r.bottom > d.top && r.top < d.bottom) out.push((x.innerText || x.id || x.className).trim().slice(0, 30)); }
          return out;
        });
        if (under.length) add(`${where} ${v}`, "under the ask bar at the end of the page", under.join(" | "));
        if (v === "work") { const t = await p.evaluate(() => document.querySelector("#work").innerText); if (/worked for you|Qwen|Llama|Brain:/i.test(t)) add(where, "the Overview reads like a dashboard", t.slice(0, 120)); }
        if (v === "goals") { const t = await p.evaluate(() => [...document.querySelectorAll("#goals .goal")].map((g) => g.innerText).join(" || ")); if (/undefined|Goal · Every day at 08:00/.test(t) || (t && !/Weekdays at 8 AM/.test(t))) add(where, "a task doesn't say its real days", t.slice(0, 160)); }
        if (v === "identity") {
          const t = await p.evaluate(() => ({ count: document.querySelector(".mem-rail .count")?.innerText || "", pill: document.querySelector("#top-pills")?.innerText || "", how: [...document.querySelectorAll(".how-row")].length }));
          const deck = (t.count.match(/\/\s*(\d+)/) || [])[1], pill = (t.pill.match(/(\d+)\s+saved/) || [])[1];
          if (deck && pill && deck !== pill) add(where, "two memory counts", `${pill} saved, ${deck} in the deck`);
          if (!t.how) add(where, "How to be with you is missing", "");
        }
      }
      await ctx.close();
    }
  }
  await b.close();
  console.log(JSON.stringify({ screens: seen.screens, problems, access, looks, sees, browser }));
})().catch((e) => { console.log(JSON.stringify({ screens: seen.screens, problems: [{ where: "walk", kind: "crashed", text: String(e).slice(0, 300) }] })); });
