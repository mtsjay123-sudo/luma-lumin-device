// Render film.html to frames. `node render.cjs check` makes six stills; `node render.cjs` makes every frame at 30 a second.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const check = process.argv[2] === 'check';
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errors = [];
  p.on('pageerror', (e) => errors.push(String(e)));
  await p.goto('file://' + path.join(__dirname, 'film.html'));
  await p.waitForFunction(() => window.READY === true);
  const duration = await p.evaluate(() => window.DURATION);
  if (check) {
    for (const t of [3, 8.5, 17.8, 24, 30.5, 36.5]) {
      await p.evaluate((x) => window.seek(x), t);
      await p.screenshot({ path: path.join(__dirname, `check-${String(t).replace('.', '_')}.jpg`), type: 'jpeg', quality: 80 });
    }
  } else {
    const dir = path.join(__dirname, 'frames');
    for (const f of fs.readdirSync(dir)) fs.unlinkSync(path.join(dir, f));
    const total = Math.round(duration * 30);
    for (let i = 0; i < total; i++) {
      await p.evaluate((x) => window.seek(x), i / 30);
      await p.screenshot({ path: path.join(dir, `f${String(i).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 93 });
      if (i % 150 === 0) console.log('frame', i, 'of', total);
    }
  }
  console.log('errors', JSON.stringify(errors));
  await b.close();
})();
