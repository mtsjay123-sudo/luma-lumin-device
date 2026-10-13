// Luma Desktop: a small window onto the Luma running on this computer.
//
// Like the ChatGPT app and its local agent server, this shell holds no smarts
// of its own. It starts Luma's runtime (Python, local model) if it isn't
// running, opens its desktop page, and gives it what a real app needs: a dock
// icon, ⌥Space to summon, downloads, and links that open the right Mac app.
"use strict";
const { app, BrowserWindow, Menu, shell, dialog, globalShortcut, ipcMain, nativeTheme, Notification, session } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");

const PORT = Number(process.env.LUMA_PORT || 8095);
const ORIGIN = `http://127.0.0.1:${PORT}`;
const HOME_URL = `${ORIGIN}/desktop/`;
const SUMMON = process.platform === "darwin" ? "Alt+Space" : "Control+Alt+Space";

let win = null;
let runtime = null; // only set when this app started Luma, so quitting stops only what we started
let quitting = false;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const configFile = () => path.join(app.getPath("userData"), "luma.json");
function readConfig() {
  try { return JSON.parse(fs.readFileSync(configFile(), "utf8")); } catch { return {}; }
}
function writeConfig(next) {
  fs.mkdirSync(path.dirname(configFile()), { recursive: true });
  fs.writeFileSync(configFile(), JSON.stringify({ ...readConfig(), ...next }, null, 2));
}

// -------------------------------------------------------------- runtime ---
const isRuntimeDir = (dir) => Boolean(dir) && fs.existsSync(path.join(dir, "src", "luma", "cli.py"));

function findRuntime() {
  const home = os.homedir();
  const near = (base) => [path.join(base, "Luma Home Prototype Code"), base];
  const candidates = [
    process.env.LUMA_RUNTIME_DIR,
    readConfig().runtimeDir,
    ...near(path.resolve(__dirname, "..")), // run from the repository
    ...near(path.resolve(path.dirname(app.getPath("exe")), "..", "..", "..")), // Luma.app placed next to the folder
    ...["luma-lumin-device", "Desktop/luma-lumin-device", "Documents/luma-lumin-device", "Developer/luma-lumin-device", "Projects/luma-lumin-device", "code/luma-lumin-device"]
      .flatMap((p) => near(path.join(home, p))),
  ];
  return candidates.find(isRuntimeDir) || null;
}

function pythonFor(dir) {
  const venv = path.join(dir, ".venv", process.platform === "win32" ? "Scripts\\python.exe" : "bin/python");
  return fs.existsSync(venv) ? venv : process.platform === "win32" ? "python" : "python3";
}

function ping() {
  return new Promise((resolve) => {
    const req = http.get(`${ORIGIN}/api/session`, { timeout: 1500 }, (res) => { res.resume(); resolve(res.statusCode === 200); });
    req.on("error", () => resolve(false));
    req.on("timeout", () => { req.destroy(); resolve(false); });
  });
}

async function startRuntime(dir) {
  if (await ping()) return { ok: true };
  const log = fs.openSync(path.join(app.getPath("userData"), "luma-runtime.log"), "a");
  runtime = spawn(pythonFor(dir), ["-m", "luma.cli", "serve", "--port", String(PORT)], {
    // PYTHONPATH lets it run straight from the folder even without an installed .venv.
    cwd: dir, env: { ...process.env, PYTHONUNBUFFERED: "1", PYTHONPATH: [path.join(dir, "src"), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter) },
    stdio: ["ignore", log, log],
  });
  runtime.on("exit", () => { runtime = null; });
  // The first start loads the model; give it time.
  for (let i = 0; i < 240; i++) {
    if (await ping()) return { ok: true };
    if (!runtime) return { ok: false, reason: "Luma stopped while starting. Run scripts/setup_mac.sh once, then try again." };
    await sleep(500);
  }
  return { ok: false, reason: "Luma is taking too long to start." };
}

async function boot() {
  splash("starting");
  if (await ping()) return win.loadURL(HOME_URL);
  const dir = findRuntime();
  if (!dir) return splash("missing");
  const started = await startRuntime(dir);
  if (started.ok) return win.loadURL(HOME_URL);
  splash("failed", started.reason);
}

function splash(state, detail = "") {
  win.loadFile(path.join(__dirname, "splash.html"), { query: { state, detail } });
}

// --------------------------------------------------------------- window ---
function createWindow() {
  win = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 760,
    minHeight: 560,
    title: "Luma",
    show: false,
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#161917" : "#ffffff",
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    trafficLightPosition: { x: 18, y: 18 },
    icon: path.join(__dirname, "build", "icon.png"),
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true, nodeIntegration: false, spellcheck: true },
  });
  win.once("ready-to-show", () => win.show());
  win.on("close", (event) => {
    // Closing the window keeps Luma around (⌥Space brings it back), like a Mac app.
    if (process.platform === "darwin" && !quitting) { event.preventDefault(); win.hide(); }
  });

  // Only Luma's own pages load in the window. Everything else opens where it belongs:
  // sms: in Messages, mailto: in Mail, web links in the browser.
  const openOutside = (url) => { if (/^(https?|sms|mailto|tel|facetime):/i.test(url)) shell.openExternal(url); };
  win.webContents.setWindowOpenHandler(({ url }) => { openOutside(url); return { action: "deny" }; });
  win.webContents.on("will-navigate", (event, url) => {
    if (url.startsWith(ORIGIN + "/") || url.startsWith("file://")) return;
    event.preventDefault();
    openOutside(url);
  });
  win.webContents.on("did-fail-load", (_e, code, _desc, url) => { if (url.startsWith(ORIGIN) && code !== -3) setTimeout(boot, 1500); });

  boot();
}

function summon() {
  if (!win) return createWindow();
  if (win.isVisible() && win.isFocused()) return win.hide();
  win.show();
  win.focus();
}

// ------------------------------------------------------------ downloads ---
function uniquePath(dir, name) {
  const ext = path.extname(name);
  const base = path.basename(name, ext);
  let candidate = path.join(dir, name);
  for (let i = 1; fs.existsSync(candidate); i++) candidate = path.join(dir, `${base} (${i})${ext}`);
  return candidate;
}

// ----------------------------------------------------------------- menu ---
function buildMenu() {
  const isMac = process.platform === "darwin";
  const go = (url) => () => { if (win) { win.show(); win.loadURL(url); } };
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    ...(isMac ? [{ role: "appMenu" }] : []),
    { label: "File", submenu: [{ label: "New Conversation", accelerator: "CmdOrCtrl+N", click: () => win?.webContents.executeJavaScript("document.dispatchEvent(new KeyboardEvent('keydown',{key:'n',metaKey:true,ctrlKey:true}))") }, { type: "separator" }, isMac ? { role: "close" } : { role: "quit" }] },
    { role: "editMenu" },
    { label: "View", submenu: [
      { label: "Luma", accelerator: "CmdOrCtrl+1", click: go(HOME_URL) },
      { label: "All Controls", accelerator: "CmdOrCtrl+2", click: go(`${ORIGIN}/`) },
      { type: "separator" }, { role: "reload" }, { role: "togglefullscreen" },
      ...(app.isPackaged ? [] : [{ role: "toggleDevTools" }]),
    ] },
    { role: "windowMenu" },
    { role: "help", submenu: [
      { label: "Where Luma Keeps Its Folder…", click: chooseFolder },
      { label: "Runtime Log", click: () => shell.openPath(path.join(app.getPath("userData"), "luma-runtime.log")) },
    ] },
  ]));
}

async function chooseFolder() {
  const result = await dialog.showOpenDialog(win, { title: "Where is Luma?", message: "Choose the luma-lumin-device folder (or its “Luma Home Prototype Code” folder).", properties: ["openDirectory"] });
  if (result.canceled || !result.filePaths[0]) return false;
  const picked = result.filePaths[0];
  const dir = [picked, path.join(picked, "Luma Home Prototype Code")].find(isRuntimeDir);
  if (!dir) { dialog.showMessageBox(win, { type: "warning", message: "That folder doesn't have Luma in it.", detail: "Pick the folder that contains “Luma Home Prototype Code”." }); return false; }
  writeConfig({ runtimeDir: dir });
  boot();
  return true;
}

// ------------------------------------------------------------ lifecycle ---
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", summon);
  app.whenReady().then(() => {
    app.setName("Luma");
    buildMenu();
    ipcMain.handle("luma:choose-folder", chooseFolder);
    ipcMain.handle("luma:retry", () => { boot(); return true; });
    session.defaultSession.on("will-download", (_event, item) => {
      item.setSavePath(uniquePath(app.getPath("downloads"), item.getFilename()));
      item.once("done", (_e, state) => {
        if (state !== "completed") return;
        if (Notification.isSupported()) new Notification({ title: "Saved to Downloads", body: path.basename(item.getSavePath()) }).show();
        shell.showItemInFolder(item.getSavePath());
      });
    });
    createWindow();
    if (!globalShortcut.register(SUMMON, summon)) console.warn(`Couldn't register ${SUMMON}`);
    app.on("activate", () => { if (!win) createWindow(); else win.show(); });
  });
  app.on("before-quit", () => { quitting = true; });
  app.on("will-quit", () => {
    globalShortcut.unregisterAll();
    if (runtime) runtime.kill("SIGTERM");
  });
  app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
}
