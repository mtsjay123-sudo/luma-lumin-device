// Opens the storage screen on the phone page and on the computer in a real browser, makes room, and reports what it
// saw as one line of JSON. tests/test_storage.py runs this and checks the answers; it skips when there's no browser.
//
//   node tests/storage_check.cjs http://127.0.0.1:PORT
//
// Needs Playwright with Chromium (the same thing tests/orb_check.cjs needs). Nothing is downloaded or sent.
const { chromium } = require("playwright");

const base = process.argv[2];
const out = { errors: [] };

function watch(page) {
  page.on("console", (m) => { if (m.type() === "error") out.errors.push("console: " + m.text().slice(0, 200)); });
  page.on("pageerror", (e) => out.errors.push("page: " + String(e).slice(0, 200)));
  page.on("response", (r) => { if (r.status() >= 400) out.errors.push("http " + r.status() + " " + r.url().split(base).join("")); });
  page.on("dialog", (d) => d.accept());
}

(async () => {
  const browser = await chromium.launch();
  try {
    // the phone page
    const phone = await (await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true })).newPage();
    watch(phone);
    await phone.goto(base + "/phone/", { waitUntil: "networkidle" });
    for (const label of ["Skip", "Got it", "Done"]) {
      const b = await phone.$('button:has-text("' + label + '")');
      if (b && await b.isVisible()) { await b.click(); await phone.waitForTimeout(300); break; }
    }
    out.hiddenRowShows = await phone.$eval("#plus-row", (n) => n.offsetParent !== null);
    await phone.click("#make-room");
    await phone.waitForSelector(".room-head", { timeout: 8000 });
    out.phone = await phone.evaluate(() => ({
      title: document.querySelector("#sheet-title").innerText,
      left: document.querySelector(".room-left").innerText,
      segments: document.querySelectorAll(".room-bar i").length,
      kinds: Array.from(document.querySelectorAll(".room-kinds li span")).map((n) => n.innerText),
      options: Array.from(document.querySelectorAll(".room .row b")).map((n) => n.innerText),
      state: (document.querySelector(".room-state") || {}).innerText || "",
    }));
    await phone.locator(".room .row", { hasText: "Chats older than 30 days" }).locator("button").click();
    await phone.waitForSelector(".room-state.freed", { timeout: 8000 });
    out.afterClear = await phone.evaluate(() => ({
      freed: document.querySelector(".room-state.freed").innerText,
      kinds: Array.from(document.querySelectorAll(".room-kinds li span")).map((n) => n.innerText),
      left: document.querySelector(".room-left").innerText,
    }));

    // the computer
    const desk = await (await browser.newContext({ viewport: { width: 1280, height: 860 } })).newPage();
    watch(desk);
    await desk.goto(base + "/desktop/", { waitUntil: "networkidle" });
    await desk.waitForTimeout(1200);
    await desk.locator("#hp-room").scrollIntoViewIfNeeded();
    await desk.click("#hp-room");
    await desk.waitForSelector(".room-sheet .room-head", { timeout: 8000 });
    out.desktop = await desk.evaluate(() => ({
      left: document.querySelector(".room-sheet .room-left").innerText,
      segments: document.querySelectorAll(".room-sheet .room-bar i").length,
      biggest: Array.from(document.querySelectorAll(".room-sheet .item .title")).map((n) => n.innerText),
      health: document.querySelector(".room-sheet").innerText.includes("All good"),
    }));
  } catch (e) {
    out.errors.push("check: " + String(e).split("\n")[0].slice(0, 300));
  }
  await browser.close();
  console.log(JSON.stringify(out));
})();
