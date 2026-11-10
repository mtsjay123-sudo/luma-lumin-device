// Draws Luma's logo from its own orb and saves it everywhere a logo is kept.
//
// The logo is one moment of the liquid orb (src/luma/control/web/orb.js) at rest, so the picture and the moving
// thing are the same thing. Run this again whenever the orb's look changes:
//
//   node scripts/orb_logo.cjs            (needs Playwright with Chromium; nothing is downloaded or sent)
//
// It writes:
//   src/luma/control/web/desktop/brand/logo.png   the orb alone on nothing, for the desktop app (tab icon, sign-up, lock screen)
//   src/luma/control/web/phone/icon.png           the orb on Luma's night color, for a phone's home screen
// and, when the desktop shell is beside this folder (../desktop):
//   ../desktop/build/icon.png, icon.ico, icon.icns   the app's icon: the orb on a night-colored tile
//   ../desktop/assets/orb.js                          a copy of the orb for the start-up screen, which shows before Luma is running
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const WEB = path.join(__dirname, "..", "src", "luma", "control", "web");
const SHELL = path.join(__dirname, "..", "..", "desktop");

// A Windows icon: a small table of sizes, then each size as a PNG.
function ico(pictures) {
  const head = Buffer.alloc(6 + 16 * pictures.length);
  head.writeUInt16LE(0, 0); head.writeUInt16LE(1, 2); head.writeUInt16LE(pictures.length, 4);
  let at = head.length;
  pictures.forEach(({ size, png }, i) => {
    const row = 6 + 16 * i;
    head.writeUInt8(size >= 256 ? 0 : size, row); head.writeUInt8(size >= 256 ? 0 : size, row + 1);
    head.writeUInt8(0, row + 2); head.writeUInt8(0, row + 3);
    head.writeUInt16LE(1, row + 4); head.writeUInt16LE(32, row + 6);
    head.writeUInt32LE(png.length, row + 8); head.writeUInt32LE(at, row + 12);
    at += png.length;
  });
  return Buffer.concat([head, ...pictures.map((p) => p.png)]);
}

// A Mac icon, laid out the way Apple's own tool writes one: a table of contents, then named sizes (the @2x ones
// have their own names), each a PNG.
function icns(pictures) {
  const NAMES = [["ic07", 128], ["ic08", 256], ["ic09", 512], ["ic10", 1024], ["ic11", 32], ["ic12", 64], ["ic13", 256], ["ic14", 512]];
  const part = (name, body) => {
    const head = Buffer.alloc(8);
    head.write(name, 0, "ascii"); head.writeUInt32BE(body.length + 8, 4);
    return Buffer.concat([head, body]);
  };
  const parts = NAMES.map(([name, size]) => part(name, pictures.find((p) => p.size === size).png));
  const list = Buffer.concat(NAMES.map(([name], i) => { const row = Buffer.alloc(8); row.write(name, 0, "ascii"); row.writeUInt32BE(parts[i].length, 4); return row; }));
  const body = Buffer.concat([part("TOC ", list), ...parts]);
  return part("icns", body);
}

(async () => {
  const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
  try {
    const page = await browser.newPage();
    await page.setContent("<!doctype html><meta charset='utf-8'><body></body>");
    await page.addScriptTag({ path: path.join(WEB, "orb.js") });
    const made = await page.evaluate(async () => {
      if (!window.LumaOrb.liquid()) return { error: "this browser can't draw the liquid orb (no WebGL)" };
      const picture = async (url) => { const img = new Image(); img.src = url; await img.decode(); return img; };
      const board = (side) => { const c = document.createElement("canvas"); c.width = c.height = side; const g = c.getContext("2d"); g.imageSmoothingQuality = "high"; return [c, g]; };
      const logo = window.LumaOrb.still(256, "idle");   // the desktop never shows it bigger than this
      const orb = await picture(window.LumaOrb.still(1024, "idle"));

      // The phone's icon can't be see-through (a home screen would fill it with black), so it sits on Luma's night color.
      const [phone, pg] = board(320);
      pg.fillStyle = "#0b0a0c";
      pg.fillRect(0, 0, 320, 320);
      const glow = pg.createRadialGradient(160, 160, 38, 160, 160, 205);
      glow.addColorStop(0, "rgba(96, 128, 220, 0.30)");
      glow.addColorStop(1, "rgba(96, 128, 220, 0)");
      pg.fillStyle = glow;
      pg.fillRect(0, 0, 320, 320);
      pg.drawImage(orb, 48, 48, 224, 224);

      // The app's icon: a rounded tile in Luma's night color with the orb on it, the shape a Mac's Dock expects
      // (the tile is 824 of the 1024 across, with room around it for its shadow).
      const [tile, tg] = board(1024);
      const round = (x, y, w, h, r) => { tg.beginPath(); tg.moveTo(x + r, y); tg.arcTo(x + w, y, x + w, y + h, r); tg.arcTo(x + w, y + h, x, y + h, r); tg.arcTo(x, y + h, x, y, r); tg.arcTo(x, y, x + w, y, r); tg.closePath(); };
      tg.save();
      tg.shadowColor = "rgba(0, 0, 0, 0.35)"; tg.shadowBlur = 28; tg.shadowOffsetY = 12;
      round(100, 100, 824, 824, 186);
      tg.fillStyle = "#08080d";
      tg.fill();
      tg.restore();
      tg.save();
      round(100, 100, 824, 824, 186);
      tg.clip();
      const night = tg.createRadialGradient(512, 470, 60, 512, 512, 640);
      night.addColorStop(0, "#232a52");
      night.addColorStop(0.55, "#0f1124");
      night.addColorStop(1, "#06060b");
      tg.fillStyle = night;
      tg.fillRect(100, 100, 824, 824);
      const light = tg.createRadialGradient(512, 512, 250, 512, 512, 430);
      light.addColorStop(0, "rgba(140, 170, 255, 0.34)");
      light.addColorStop(1, "rgba(140, 170, 255, 0)");
      tg.fillStyle = light;
      tg.fillRect(100, 100, 824, 824);
      tg.drawImage(orb, 512 - 300, 512 - 300, 600, 600);
      tg.restore();
      round(101.5, 101.5, 821, 821, 184.5);
      tg.strokeStyle = "rgba(255, 255, 255, 0.10)"; tg.lineWidth = 3;
      tg.stroke();

      // Every size an icon file holds, each made by halving the one before so small ones stay smooth.
      const sizes = {};
      let from = tile, at = 1024;
      sizes[1024] = tile.toDataURL("image/png");
      for (const size of [512, 256, 128, 64, 48, 32, 24, 16]) {
        while (at / 2 >= size) { const [half, hg] = board(at / 2); hg.drawImage(from, 0, 0, at / 2, at / 2); from = half; at /= 2; }
        const [c, g] = board(size);
        g.drawImage(from, 0, 0, size, size);
        sizes[size] = c.toDataURL("image/png");
      }
      return { logo, phone: phone.toDataURL("image/png"), sizes };
    });
    if (made.error) throw new Error(made.error);
    const bytes = (url) => Buffer.from(url.split(",")[1], "base64");
    const save = (file, data) => {
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, data);
      console.log(`${path.relative(process.cwd(), file)}  ${data.length} bytes`);
    };
    save(path.join(WEB, "desktop", "brand", "logo.png"), bytes(made.logo));
    save(path.join(WEB, "phone", "icon.png"), bytes(made.phone));
    if (fs.existsSync(path.join(SHELL, "build"))) {
      const pictures = Object.entries(made.sizes).map(([size, url]) => ({ size: Number(size), png: bytes(url) }));
      save(path.join(SHELL, "build", "icon.png"), pictures.find((p) => p.size === 1024).png);
      save(path.join(SHELL, "build", "icon.ico"), ico([16, 24, 32, 48, 64, 128, 256].map((size) => pictures.find((p) => p.size === size))));
      save(path.join(SHELL, "build", "icon.icns"), icns(pictures));
      save(path.join(SHELL, "assets", "orb.js"), fs.readFileSync(path.join(WEB, "orb.js")));
    }
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(String(error.message || error)); process.exit(1); });
