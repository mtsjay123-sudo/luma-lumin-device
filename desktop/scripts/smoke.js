// CI check for first launch, on a real Mac or Windows machine: run the same setup the
// app runs (private Python, Luma's tools, a browser), start Luma from the source the
// app bundles, and make sure it answers. The 2.5 GB model is only checked to exist.
"use strict";
const path = require("node:path");
const http = require("node:http");
const { spawn, execFileSync } = require("node:child_process");
const setup = require("../setup");

const home = path.resolve(process.argv[2] || path.join(require("node:os").tmpdir(), "luma-smoke"));
const runtime = path.resolve(__dirname, "..", "..", "Luma Home Prototype Code");
const PORT = 8195;
const get = (p) => new Promise((resolve) => {
  http.get(`http://127.0.0.1:${PORT}${p}`, { timeout: 3000 }, (r) => { r.resume(); resolve(r.statusCode); }).on("error", () => resolve(0));
});

(async () => {
  let last = "";
  const { python, env } = await setup.ensure(home, (p) => {
    const line = `${p.step}: ${p.label}${p.detail ? " (" + p.detail + ")" : ""}`;
    if (line !== last) { console.log(line); last = line; }
  }, { skipModel: true });
  console.log("python:", python);
  console.log("browser:", env.LUMA_BROWSER_EXECUTABLE || "private Chromium");
  console.log(execFileSync(python, ["-c", "import llama_cpp, playwright, pptx, cryptography, qrcode; print('llama_cpp', llama_cpp.__version__)"], { env: { ...process.env, ...env } }).toString().trim());

  // Luma's own browser can open a real page (skippable where the network is fenced off).
  if (!process.env.LUMA_SMOKE_SKIP_WEB) {
  const probe = "from luma.integrations.browser import BrowserSession\nimport os, tempfile\n" +
    "b = BrowserSession.from_env(tempfile.mkdtemp(), env=os.environ)\nprint('page:', b.open('https://example.com')['title'])\nb.close()";
  console.log(execFileSync(python, ["-c", probe], { env: { ...process.env, ...env, PYTHONPATH: path.join(runtime, "src") }, timeout: 120000 }).toString().trim());
  }

  const child = spawn(python, ["-m", "luma.cli", "serve", "--port", String(PORT), "--no-model"], {
    cwd: runtime, env: { ...process.env, ...env, PYTHONPATH: path.join(runtime, "src"), PYTHONUNBUFFERED: "1", LUMA_STATE_DIR: path.join(home, "state") }, stdio: "inherit",
  });
  let ok = false;
  for (let i = 0; i < 60 && !ok; i++) { await new Promise((r) => setTimeout(r, 1000)); ok = (await get("/api/session")) === 200; }
  const page = await get("/desktop/");
  child.kill();
  if (!ok || page !== 200) throw new Error(`Luma didn't answer (session ok=${ok}, desktop page ${page})`);
  console.log("Luma answered on", PORT);

  // The exact model file is still where the app will fetch it.
  if (process.env.LUMA_SMOKE_SKIP_WEB) { console.log("First launch works (web checks skipped)."); process.exit(0); }
  const r = await fetch(setup.MODEL.url, { method: "HEAD", redirect: "follow" });
  const size = Number(r.headers.get("content-length") || r.headers.get("x-linked-size") || 0);
  console.log("model:", r.status, size);
  if (!r.ok || size !== setup.MODEL.bytes) throw new Error("The model download isn't available as expected.");
  console.log("First launch works.");
  process.exit(0);
})().catch((error) => { console.error(error.tail || ""); console.error(error); process.exit(1); });
