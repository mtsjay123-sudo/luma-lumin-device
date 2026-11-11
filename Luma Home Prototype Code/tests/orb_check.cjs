// Opens Luma's liquid orb (src/luma/control/web/orb.js) in a real browser and reports what it did, as one line of
// JSON. tests/test_orb.py runs this and checks the answers; it skips when there's no browser to run it in.
//
//   node tests/orb_check.cjs [http://127.0.0.1:PORT]      with the address of a running Luma, it also opens the apps
//
// Needs Playwright with Chromium (the same thing scripts/orb_logo.cjs needs). Nothing is downloaded or sent.
const path = require("node:path");
const { chromium, devices } = require("playwright");

const ORB = path.join(__dirname, "..", "src", "luma", "control", "web", "orb.js");
const base = process.argv[2] || "";
const out = { errors: [] };

// Counts the WebGL drawing surfaces the page asks for and listens for anything the page's own rules refuse.
const WATCH = `
  window.__webgl = 0;
  window.__refused = [];
  const real = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (kind, ...rest) { if (/webgl/.test(kind)) window.__webgl += 1; return real.call(this, kind, ...rest); };
  document.addEventListener("securitypolicyviolation", (e) => window.__refused.push(e.violatedDirective + " " + e.blockedURI));
`;

// What an orb looks like right now, from a picture of it (so this is what a person would see): how bright its
// middle and one corner are, how much of its box is lit, its overall color, and a fingerprint of the whole picture.
async function see(page, selector) {
  const shot = (await page.locator(selector).first().screenshot()).toString("base64");
  return page.evaluate(async (b64) => {
    const img = new Image();
    img.src = "data:image/png;base64," + b64;
    await img.decode();
    const c = document.createElement("canvas");
    c.width = img.width; c.height = img.height;
    const g = c.getContext("2d");
    g.drawImage(img, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data;
    const bright = (x, y) => { const i = 4 * (Math.floor(y) * c.width + Math.floor(x)); return Math.round((d[i] + d[i + 1] + d[i + 2]) / 3); };
    let lit = 0, print = 0;
    const tone = [0, 0, 0];
    for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] > 60) { lit += 1; tone[0] += d[i]; tone[1] += d[i + 1]; tone[2] += d[i + 2]; }
    for (let i = 0; i < d.length; i += 97) print = (print * 31 + (d[i] >> 3)) >>> 0;
    return { middle: bright(c.width / 2, c.height / 2), corner: bright(3, 3), lit: lit / (d.length / 4), tone: tone.map((v) => Math.round(v / Math.max(1, lit))), print };
  }, shot);
}

async function alone(browser) {
  // The orb on an empty page: nothing else there to help it or get in its way.
  const context = await browser.newContext({ viewport: { width: 600, height: 500 } });
  const page = await context.newPage();
  const asked = [];
  page.on("request", (r) => asked.push(r.url()));
  page.on("pageerror", (e) => out.errors.push("alone: " + e.message));
  await page.setContent("<!doctype html><meta charset='utf-8'><body style='margin:0;background:#000'><div id='big' style='width:300px;height:300px'></div><div id='plain' style='width:200px;height:200px'></div><div id='smalls'></div></body>");
  await page.evaluate(WATCH);
  await page.addScriptTag({ path: ORB });
  out.moods = await page.evaluate(() => window.LumaOrb.moods);
  out.liquid = await page.evaluate(() => window.LumaOrb.liquid());

  // a big live orb, through every mood
  await page.evaluate(() => { window.big = window.LumaOrb.mount(document.getElementById("big"), { mood: "idle", look: "water" }); });   // as the talk screen asks for it
  await page.waitForTimeout(900);
  out.big = await see(page, "#big");
  out.bigLiquid = await page.evaluate(() => window.big.liquid);
  out.looks = {};
  for (const mood of out.moods) {
    await page.evaluate((m) => window.big.set(m, m === "speaking" ? 0.6 : 0), mood);
    await page.waitForTimeout(1300);
    out.looks[mood] = await see(page, "#big");
  }
  // listening opens its middle: the middle of the ring is see-through
  await page.evaluate(() => window.big.set("listening", 0));
  await page.waitForTimeout(1500);
  out.ring = await see(page, "#big");

  // the plain orb, for a device with no WebGL
  await page.evaluate(() => { window.plain = window.LumaOrb.mount(document.getElementById("plain"), { mood: "idle", plain: true }); });
  await page.waitForTimeout(700);
  out.plain = await see(page, "#plain");
  out.plainLiquid = await page.evaluate(() => window.plain.liquid);

  // twenty small ones share one drawing surface
  const before = await page.evaluate(() => window.__webgl);
  await page.evaluate(() => {
    window.smalls = [];
    for (let i = 0; i < 20; i++) {
      const d = document.createElement("span");
      d.style.cssText = "display:inline-block;width:24px;height:24px";
      document.getElementById("smalls").appendChild(d);
      window.smalls.push(window.LumaOrb.mount(d, { mood: i % 2 ? "thinking" : "idle", small: true, size: 0.47 }));
    }
  });
  await page.waitForTimeout(600);
  out.smallSurfaces = (await page.evaluate(() => window.__webgl)) - before;
  out.surfaces = await page.evaluate(() => window.__webgl);   // in all: the big orb's own, and the one the small ones share
  out.small = await see(page, "#smalls span");

  // stills
  out.stills = await page.evaluate(() => window.LumaOrb.moods.map((m) => window.LumaOrb.still(64, m)));
  out.surfacesAfterStills = await page.evaluate(() => window.__webgl);

  // the marble is what a large orb is when nobody asks for water: the first slides (looked at here, after the surfaces are
  // counted: it gets one of its own)
  out.bigLook = await page.evaluate(() => window.big.look);
  await page.evaluate(() => {
    const d = document.createElement("div");
    d.id = "marble";
    d.style.cssText = "width:300px;height:300px";
    document.body.appendChild(d);
    window.marble = window.LumaOrb.mount(d, { mood: "idle" });
  });
  await page.waitForTimeout(900);
  out.marble = { look: await page.evaluate(() => window.marble.look), idle: await see(page, "#marble") };
  await page.evaluate(() => window.marble.set("speaking", 0.6));
  await page.waitForTimeout(1300);
  out.marble.speaking = await see(page, "#marble");
  await page.evaluate(() => window.marble.set("listening", 0));
  await page.waitForTimeout(1500);
  out.marble.listening = await see(page, "#marble");
  await page.evaluate(() => { window.marble.stop(); document.getElementById("marble").remove(); });

  // it cleans up: closed, it drains away and takes its canvas with it; taken off the page, it stops by itself
  await page.evaluate(() => window.big.close());
  await page.waitForTimeout(2600);
  out.closed = await page.evaluate(() => ({ gone: window.big.gone, canvases: document.querySelectorAll("#big canvas").length }));
  await page.evaluate(() => document.getElementById("smalls").remove());
  await page.waitForTimeout(700);
  out.removed = await page.evaluate(() => window.smalls.every((o) => o.gone));

  // an orb made before its place is on the page waits for it
  await page.evaluate(() => {
    const d = document.createElement("div");
    d.id = "late";
    d.style.cssText = "width:60px;height:60px";
    window.late = window.LumaOrb.mount(d, { small: true, size: 0.47 });
    setTimeout(() => document.body.appendChild(d), 250);
  });
  await page.waitForTimeout(900);
  out.late = { gone: await page.evaluate(() => window.late.gone), lit: (await see(page, "#late")).lit };

  out.asked = asked;
  out.refusedAlone = await page.evaluate(() => window.__refused);
  await context.close();
}

async function still(browser) {
  // Someone who has asked their device for less motion: the orb holds still, and still changes with the mood.
  const context = await browser.newContext({ viewport: { width: 400, height: 400 }, reducedMotion: "reduce" });
  const page = await context.newPage();
  page.on("pageerror", (e) => out.errors.push("calm: " + e.message));
  await page.setContent("<!doctype html><meta charset='utf-8'><body style='margin:0;background:#000'><div id='big' style='width:300px;height:300px'></div></body>");
  await page.addScriptTag({ path: ORB });
  await page.evaluate(() => { window.big = window.LumaOrb.mount(document.getElementById("big"), { mood: "idle", look: "water" }); });
  await page.waitForTimeout(3500);
  const one = await see(page, "#big");
  await page.waitForTimeout(700);
  const two = await see(page, "#big");
  await page.evaluate(() => window.big.set("thinking", 0));
  await page.waitForTimeout(3500);
  const three = await see(page, "#big");
  out.calm = { held: one.print === two.print, changed: three.print !== two.print, lit: one.lit };
  await context.close();
}

async function apps(browser) {
  // The real apps, served by a real Luma: the orb is on the first slides, and the pages' own rules refuse nothing.
  const desk = await browser.newContext({ viewport: { width: 1280, height: 820 } });
  const page = await desk.newPage();
  page.on("pageerror", (e) => out.errors.push("desktop: " + e.message));
  await page.addInitScript(WATCH);
  await page.goto(base + "/desktop/");
  await page.waitForSelector("#su-orb canvas", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(800);
  out.desktop = await page.evaluate(() => ({
    orb: Boolean(window.LumaOrb),
    signup: document.querySelectorAll("#su-orb canvas").length,
    talkPlace: Boolean(document.getElementById("ts-orb")),
    logo: null,
    refused: window.__refused,
  }));
  out.desktop.logo = await page.evaluate(async () => { const r = await fetch("/desktop/logo"); return r.headers.get("content-type"); });
  await desk.close();

  const phone = await browser.newContext({ ...devices["iPhone 13"] });
  const p = await phone.newPage();
  p.on("pageerror", (e) => out.errors.push("phone: " + e.message));
  await p.addInitScript(WATCH);
  await p.goto(base + "/desktop/");   // the owner's own browser is signed in by opening Luma
  await p.goto(base + "/phone/");
  await p.waitForSelector(".t-luma canvas", { timeout: 15000 }).catch(() => {});
  await p.waitForTimeout(800);
  const tour = await p.evaluate(() => document.querySelectorAll(".t-luma canvas").length);
  await p.click("#tour-skip").catch(() => {});
  await p.waitForTimeout(1500);
  out.phone = await p.evaluate((n) => ({
    orb: Boolean(window.LumaOrb),
    tour: n,
    afterTour: document.querySelectorAll("#tour canvas").length,
    state: document.querySelectorAll("#state i canvas").length,
    wide: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    refused: window.__refused,
  }), tour);
  await phone.close();
}

(async () => {
  const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  try {
    await alone(browser);
    await still(browser);
    if (base) await apps(browser);
  } finally {
    await browser.close();
  }
  console.log(JSON.stringify(out));
})().catch((error) => { console.log(JSON.stringify({ crashed: String(error && error.stack || error) })); process.exit(1); });
