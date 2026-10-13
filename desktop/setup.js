// First launch: get everything Luma needs, in the app's own folder.
//
// Nothing is installed system-wide and nothing asks for an admin password:
//   1. a private copy of Python (python-build-standalone, checked against its SHA256SUMS)
//   2. Luma's few Python packages, with a prebuilt llama.cpp so nothing has to compile
//   3. a browser for Luma to drive: your Chrome or Edge if you have one, else a private Chromium
//   4. Luma's brain: the Qwen3 4B model file, checked against its published SHA-256
// Every step resumes where it left off if the app is closed halfway.
"use strict";
const crypto = require("node:crypto");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const PYTHON_MINOR = "3.12";
// The exact file Luma was evaluated with (see MODEL_AND_PERSONALITY.md).
const MODEL = {
  file: "Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
  url: "https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/ae44f08e1392f39c0e474af10c3ff8355c8b6688/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
  bytes: 2497280736,
  sha256: "2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e",
};
// Enough to run Luma Desktop. Voice (Whisper, Kokoro) is optional and much larger.
// tzdata: Windows has no time-zone database of its own, and Luma plans your day in yours.
const PACKAGES = ["llama-cpp-python>=0.3.9", "cryptography>=44", "qrcode==8.2", "python-pptx>=1.0,<2", "playwright>=1.56,<2", "numpy", "python-dotenv", "tzdata"];
const UA = { "User-Agent": "LumaDesktop/1.0 (+https://github.com/mtsjay123-sudo/luma-lumin-device)" };

const triple = () => ({
  "darwin-arm64": "aarch64-apple-darwin",
  "darwin-x64": "x86_64-apple-darwin",
  "win32-x64": "x86_64-pc-windows-msvc",
  "win32-arm64": "aarch64-pc-windows-msvc",
  "linux-x64": "x86_64-unknown-linux-gnu",
  "linux-arm64": "aarch64-unknown-linux-gnu",
}[`${process.platform}-${process.arch}`]);

// Prebuilt llama.cpp wheels: Metal on Apple silicon, plain CPU elsewhere.
const wheelIndex = () => process.platform === "darwin" && process.arch === "arm64"
  ? "https://abetlen.github.io/llama-cpp-python/whl/metal"
  : "https://abetlen.github.io/llama-cpp-python/whl/cpu";

function pythonPath(home) {
  return process.platform === "win32" ? path.join(home, "python", "python.exe") : path.join(home, "python", "bin", "python3");
}

function readState(home) {
  try { return JSON.parse(fs.readFileSync(path.join(home, "setup.json"), "utf8")); } catch { return {}; }
}
function writeState(home, next) {
  fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(home, "setup.json"), JSON.stringify({ ...readState(home), ...next }, null, 2));
}

async function getJson(url) {
  const r = await fetch(url, { headers: { ...UA, Accept: "application/vnd.github+json" } });
  if (!r.ok) throw new Error(`${new URL(url).hostname} answered ${r.status}`);
  return r.json();
}

// Download with resume and progress; verifies size and SHA-256 when known.
async function download(url, dest, { bytes, sha256, onBytes } = {}) {
  await fsp.mkdir(path.dirname(dest), { recursive: true });
  const part = dest + ".part";
  let have = fs.existsSync(part) ? fs.statSync(part).size : 0;
  if (bytes && have > bytes) { await fsp.rm(part, { force: true }); have = 0; }
  if (!bytes || have < bytes) {
    const r = await fetch(url, { headers: { ...UA, ...(have ? { Range: `bytes=${have}-` } : {}) }, redirect: "follow" });
    if (r.status === 416 && bytes && have === bytes) { /* already complete */ }
    else {
      if (!(r.ok || r.status === 206)) throw new Error(`${new URL(url).hostname} answered ${r.status}`);
      if (have && r.status !== 206) have = 0; // the server ignored the range: start over
      const total = bytes || (Number(r.headers.get("content-length")) || 0) + have;
      const out = fs.createWriteStream(part, { flags: have ? "a" : "w" });
      let done = have;
      try {
        for await (const chunk of r.body) {
          if (!out.write(chunk)) await new Promise((ok) => out.once("drain", ok));
          done += chunk.length;
          if (onBytes) onBytes(done, total);
        }
      } finally {
        await new Promise((ok) => out.end(ok));
      }
    }
  }
  const size = fs.statSync(part).size;
  if (bytes && size !== bytes) throw new Error(`The download stopped early (${size} of ${bytes} bytes). Try again to resume.`);
  if (sha256) {
    const actual = await hashFile(part);
    if (actual !== sha256) { await fsp.rm(part, { force: true }); throw new Error("The download didn't match its checksum, so I threw it away. Try again."); }
  }
  await fsp.rename(part, dest);
  return dest;
}

function hashFile(file) {
  return new Promise((resolve, reject) => {
    const h = crypto.createHash("sha256");
    fs.createReadStream(file).on("data", (d) => h.update(d)).on("error", reject).on("end", () => resolve(h.digest("hex")));
  });
}

function run(cmd, args, { env, onLine, cwd } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { env: { ...process.env, ...env }, cwd, windowsHide: true });
    let tail = "";
    const feed = (data) => {
      const text = data.toString();
      tail = (tail + text).slice(-4000);
      for (const line of text.split(/\r?\n/)) if (line.trim() && onLine) onLine(line.trim());
    };
    child.stdout.on("data", feed);
    child.stderr.on("data", feed);
    child.on("error", reject);
    child.on("exit", (code) => code === 0 ? resolve(tail) : reject(Object.assign(new Error(`${path.basename(cmd)} exited with ${code}`), { tail })));
  });
}

// ------------------------------------------------------------------ steps ---
// The latest python-build-standalone release lists every file with its SHA-256 in
// SHA256SUMS, so one small download tells us the exact name and checksum to expect.
async function findPython(target) {
  const pattern = new RegExp(`^cpython-${PYTHON_MINOR.replace(".", "\\.")}\\.\\d+\\+\\d+-${target}-install_only\\.tar\\.gz$`);
  const base = "https://github.com/astral-sh/python-build-standalone/releases/latest/download/";
  try {
    const r = await fetch(base + "SHA256SUMS", { headers: UA, redirect: "follow" });
    if (r.ok) {
      const hit = (await r.text()).split(/\r?\n/).map((l) => l.trim().split(/\s+/)).find((p) => p[1] && pattern.test(p[1]));
      if (hit) return { name: hit[1], url: base + hit[1], sha256: hit[0] };
    }
  } catch { /* fall back to the API below */ }
  const release = await getJson("https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest");
  const asset = release.assets.find((a) => pattern.test(a.name));
  if (!asset) throw new Error("I couldn't find the right Python download. Try again later.");
  return { name: asset.name, url: asset.browser_download_url, size: asset.size };
}

async function ensurePython(home, report) {
  const python = pythonPath(home);
  if (fs.existsSync(python)) return python;
  const target = triple();
  if (!target) throw new Error(`Luma doesn't have a Python build for ${process.platform} ${process.arch} yet.`);
  report({ step: "python", label: "Getting Python", fraction: 0 });
  const asset = await findPython(target);
  const sha256 = asset.sha256;
  const archive = path.join(home, "downloads", asset.name);
  await download(asset.url, archive, { bytes: asset.size, sha256, onBytes: (d, t) => report({ step: "python", label: "Getting Python", fraction: t ? d / t : 0, detail: mb(d, t) }) });
  report({ step: "python", label: "Unpacking Python", fraction: 1 });
  await fsp.rm(path.join(home, "python"), { recursive: true, force: true });
  // macOS and Windows 10+ both ship bsdtar. On Windows use the system one by full path:
  // another tar on PATH (Git's) would read "C:" as a remote host.
  const tar = process.platform === "win32" ? path.join(process.env.SystemRoot || "C:\\Windows", "System32", "tar.exe") : "tar";
  await run(tar, ["-xzf", archive, "-C", home]);
  await fsp.rm(archive, { force: true });
  if (!fs.existsSync(python)) throw new Error("Python didn't unpack where I expected.");
  return python;
}

async function ensurePackages(home, python, report) {
  const want = crypto.createHash("sha256").update(JSON.stringify([PACKAGES, wheelIndex()])).digest("hex").slice(0, 16);
  if (readState(home).packages === want) return;
  report({ step: "packages", label: "Installing Luma's tools", fraction: 0.05 });
  const env = { PIP_DISABLE_PIP_VERSION_CHECK: "1", PYTHONNOUSERSITE: "1" };
  try { await run(python, ["-m", "pip", "--version"], { env }); } catch { await run(python, ["-m", "ensurepip", "--upgrade"], { env }); }
  let seen = 0;
  const onLine = (line) => {
    const m = /^(?:Collecting|Downloading|Installing collected packages:?)\s+(\S+)/.exec(line);
    if (m) {
      seen++;
      const name = m[1].replace(/\.whl(\.metadata)?$|\.tar\.gz$/, "").replace(/-\d.*$/, "").replace(/[<>=,].*$/, "");
      report({ step: "packages", label: "Installing Luma's tools", fraction: Math.min(0.95, 0.05 + seen / 60), detail: name });
    }
  };
  const pip = ["-m", "pip", "install", "--no-warn-script-location", "--prefer-binary"];
  const others = PACKAGES.filter((p) => !p.startsWith("llama-cpp-python"));
  const llama = PACKAGES.find((p) => p.startsWith("llama-cpp-python"));
  await run(python, [...pip, ...others], { env, onLine });
  try {
    // A prebuilt llama.cpp first: no compiler needed.
    await run(python, [...pip, "--only-binary", "llama-cpp-python", "--extra-index-url", wheelIndex(), llama], { env, onLine });
    await run(python, ["-c", "import llama_cpp"], { env });
  } catch (error) {
    // No good prebuilt one for this machine (or a broken download): build it from source.
    report({ step: "packages", label: "Building Luma's brain engine (a few minutes)", fraction: 0.6 });
    if (process.platform === "darwin" && !(await hasMacCompiler())) {
      run("xcode-select", ["--install"]).catch(() => {});
      throw new Error("Luma needs Apple's free Command Line Tools to finish setting up. Click Install in the window that just opened, wait for it to finish, then press Try again.");
    }
    const cmake = process.platform === "darwin" && process.arch === "arm64" ? "-DGGML_METAL=on" : "";
    try { await run(python, [...pip, "--no-cache-dir", "--no-binary", "llama-cpp-python", llama], { env: { ...env, CMAKE_ARGS: cmake }, onLine }); }
    catch (second) { throw Object.assign(new Error("Installing Luma's brain engine didn't work. " + lastLine(second.tail || error.tail)), { tail: second.tail }); }
  }
  writeState(home, { packages: want });
}

async function hasMacCompiler() {
  try { await run("xcode-select", ["-p"]); await run("xcrun", ["--find", "clang"]); return true; } catch { return false; }
}

function lastLine(tail) {
  return String(tail || "").trim().split(/\r?\n/).filter((l) => /error/i.test(l)).slice(-1)[0] || "";
}

function installedBrowser() {
  const home = os.homedir();
  const env = process.env;
  if (env.LUMA_BROWSER_EXECUTABLE && fs.existsSync(env.LUMA_BROWSER_EXECUTABLE)) return env.LUMA_BROWSER_EXECUTABLE;
  const candidates = process.platform === "darwin" ? [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    path.join(home, "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
  ] : process.platform === "win32" ? [
    path.join(env.ProgramFiles || "C:\\Program Files", "Google\\Chrome\\Application\\chrome.exe"),
    path.join(env["ProgramFiles(x86)"] || "C:\\Program Files (x86)", "Google\\Chrome\\Application\\chrome.exe"),
    path.join(env.LOCALAPPDATA || path.join(home, "AppData\\Local"), "Google\\Chrome\\Application\\chrome.exe"),
    path.join(env["ProgramFiles(x86)"] || "C:\\Program Files (x86)", "Microsoft\\Edge\\Application\\msedge.exe"),
    path.join(env.ProgramFiles || "C:\\Program Files", "Microsoft\\Edge\\Application\\msedge.exe"),
  ] : ["/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"];
  return candidates.find((p) => fs.existsSync(p)) || null;
}

async function ensureBrowser(home, python, report) {
  const found = installedBrowser();
  if (found) return { LUMA_BROWSER_EXECUTABLE: found };
  const browsers = path.join(home, "browsers");
  const env = { PLAYWRIGHT_BROWSERS_PATH: browsers };
  if (readState(home).browser !== "chromium" || !fs.existsSync(browsers)) {
    report({ step: "browser", label: "Getting a browser for Luma", fraction: 0.1 });
    try {
      await run(python, ["-m", "playwright", "install", "chromium"], { env: { ...env, PYTHONNOUSERSITE: "1" }, onLine: (l) => { const m = /(\d+)%/.exec(l); if (m) report({ step: "browser", label: "Getting a browser for Luma", fraction: Number(m[1]) / 100 }); } });
      writeState(home, { browser: "chromium" });
    } catch {
      // Not fatal: Luma still chats, handles email and plans your day. Shopping and
      // feeds need a browser; installing Chrome (or trying again later) fixes that.
      report({ step: "browser", label: "No browser yet (shopping waits until Chrome is installed)", fraction: 1 });
      return {};
    }
  }
  return env;
}

async function ensureModel(home, report) {
  // A model you already have (LUMA_MODEL_PATH) is used as is.
  if (process.env.LUMA_MODEL_PATH && fs.existsSync(process.env.LUMA_MODEL_PATH)) return process.env.LUMA_MODEL_PATH;
  const file = path.join(home, "models", MODEL.file);
  if (fs.existsSync(file) && fs.statSync(file).size === MODEL.bytes) return file;
  report({ step: "model", label: "Getting Luma's brain", fraction: 0, detail: "2.5 GB, one time" });
  await download(MODEL.url, file, { bytes: MODEL.bytes, sha256: MODEL.sha256, onBytes: (d, t) => report({ step: "model", label: "Getting Luma's brain", fraction: d / t, detail: mb(d, t) }) });
  return file;
}

function mb(done, total) {
  const f = (n) => n >= 1e9 ? (n / 1e9).toFixed(2) + " GB" : Math.round(n / 1e6) + " MB";
  return total ? `${f(done)} of ${f(total)}` : f(done);
}

// Returns the Python to run Luma with and the environment it needs.
async function ensure(home, report = () => {}, { skipModel = false } = {}) {
  fs.mkdirSync(home, { recursive: true });
  const python = await ensurePython(home, report);
  await ensurePackages(home, python, report);
  const browserEnv = await ensureBrowser(home, python, report);
  const env = { ...browserEnv, PYTHONNOUSERSITE: "1" };
  if (!skipModel) env.LUMA_MODEL_PATH = await ensureModel(home, report);
  report({ step: "done", label: "Starting Luma", fraction: 1 });
  return { python, env };
}

function needsSetup(home) {
  const state = readState(home);
  const model = (process.env.LUMA_MODEL_PATH && fs.existsSync(process.env.LUMA_MODEL_PATH)) || fs.existsSync(path.join(home, "models", MODEL.file));
  return !fs.existsSync(pythonPath(home)) || !state.packages || !model;
}

module.exports = { ensure, needsSetup, MODEL, PACKAGES, pythonPath, installedBrowser, download, hashFile };
