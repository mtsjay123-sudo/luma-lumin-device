// Walks the phone app and the computer app in a real browser, at several sizes, light and dark, and prints what's
// wrong as JSON: errors in the console, anything that failed to load, a page wider than its screen, a button too small
// for a thumb, anything a person can press sitting under the floating ask bar at the end of a page, and a few things
// the apps must say right (one memory count, a task's real days, no model's name where a customer reads).
// Run by tests/test_app_walk.py: node app_walk.cjs <base url>
const { chromium } = require("playwright");
const base = process.argv[2];
const problems = [], seen = { screens: 0 };
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
}
async function skipFirstRun(p) {
  for (let i = 0; i < 12; i++) {
    const next = await p.$('#tour-skip, button:has-text("Skip"), button:has-text("Next"), button:has-text("Continue"), button:has-text("Get started"), button:has-text("Done")');
    if (next && await next.isVisible()) { await next.click({ timeout: 3000 }).catch(() => {}); await p.waitForTimeout(250); } else break;
  }
}
(async () => {
  const b = await chromium.launch();
  for (const scheme of ["light", "dark"]) {
    for (const width of [360, 390, 430]) {
      const where = `phone ${width} ${scheme}`;
      const ctx = await b.newContext({ viewport: { width, height: 800 }, isMobile: true, hasTouch: true, colorScheme: scheme });
      const p = await ctx.newPage(); watch(p, where);
      await p.goto(base + "/phone/", { waitUntil: "networkidle" }); await p.waitForTimeout(500);
      await skipFirstRun(p); await p.waitForTimeout(400);
      await layout(p, where + " home", true);
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
  console.log(JSON.stringify({ screens: seen.screens, problems }));
})().catch((e) => { console.log(JSON.stringify({ screens: seen.screens, problems: [{ where: "walk", kind: "crashed", text: String(e).slice(0, 300) }] })); });
