// Draws Luma's logo from its own orb and saves it where the apps look for it.
//
// The logo is one moment of the liquid orb (src/luma/control/web/orb.js) at rest, so the picture and the moving
// thing are the same thing. Run this again whenever the orb's look changes:
//
//   node scripts/orb_logo.cjs            (needs Playwright with Chromium; nothing is downloaded or sent)
//
// It writes:
//   src/luma/control/web/desktop/brand/logo.png   the orb alone on nothing, for the desktop app (tab icon, sign-up, lock screen)
//   src/luma/control/web/phone/icon.png           the orb on Luma's night color, for a phone's home screen
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const WEB = path.join(__dirname, "..", "src", "luma", "control", "web");

(async () => {
  const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  try {
    const page = await browser.newPage();
    await page.setContent("<!doctype html><meta charset='utf-8'><body></body>");
    await page.addScriptTag({ path: path.join(WEB, "orb.js") });
    const made = await page.evaluate(async () => {
      if (!window.LumaOrb.liquid()) return { error: "this browser can't draw the liquid orb (no WebGL)" };
      const logo = window.LumaOrb.still(512, "idle");
      const small = window.LumaOrb.still(256, "idle");   // the desktop never shows it bigger than this
      // The phone's icon can't be see-through (a home screen would fill it with black), so it sits on Luma's night color.
      const canvas = document.createElement("canvas");
      const side = 320;   // enough for any home screen, and a small file
      canvas.width = canvas.height = side;
      const g = canvas.getContext("2d");
      g.fillStyle = "#0b0a0c";
      g.fillRect(0, 0, side, side);
      const glow = g.createRadialGradient(side / 2, side / 2, side * 0.12, side / 2, side / 2, side * 0.64);
      glow.addColorStop(0, "rgba(96, 128, 220, 0.30)");
      glow.addColorStop(1, "rgba(96, 128, 220, 0)");
      g.fillStyle = glow;
      g.fillRect(0, 0, side, side);
      const orb = new Image();
      orb.src = logo;
      await orb.decode();
      g.imageSmoothingQuality = "high";
      g.drawImage(orb, side * 0.15, side * 0.15, side * 0.7, side * 0.7);
      return { logo: small, icon: canvas.toDataURL("image/png") };
    });
    if (made.error) throw new Error(made.error);
    const save = (file, url) => {
      const bytes = Buffer.from(url.split(",")[1], "base64");
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, bytes);
      console.log(`${path.relative(process.cwd(), file)}  ${bytes.length} bytes`);
    };
    save(path.join(WEB, "desktop", "brand", "logo.png"), made.logo);
    save(path.join(WEB, "phone", "icon.png"), made.icon);
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(String(error.message || error)); process.exit(1); });
