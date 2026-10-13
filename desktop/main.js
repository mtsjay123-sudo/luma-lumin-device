// Luma Desktop: a small window onto the Luma running on this computer.
//
// Like the ChatGPT app and its local agent server, this shell holds no smarts
// of its own. It starts Luma's runtime (Python, local model) if it isn't
// running, opens its desktop page, and gives it what a real app needs: a dock
// icon, ⌥Space to summon, downloads, and links that open the right Mac app.
// Closing the window doesn't stop Luma: it stays in the menu bar (or the system
// tray on Windows) and starts at login, so your Goals keep running.
"use strict";
const { app, BrowserWindow, Menu, Tray, nativeImage, shell, dialog, globalShortcut, ipcMain, nativeTheme, Notification, session } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const setup = require("./setup");

const PORT = Number(process.env.LUMA_PORT || 8095);
const ORIGIN = `http://127.0.0.1:${PORT}`;
const HOME_URL = `${ORIGIN}/desktop/`;
const SUMMON = process.platform === "darwin" ? "Alt+Space" : "Control+Alt+Space";

let win = null;
let tray = null;
let startHidden = false; // opened at login: work quietly until someone asks for the window
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

async function startRuntime(dir, python = pythonFor(dir), extraEnv = {}) {
  if (await ping()) return { ok: true };
  const log = fs.openSync(path.join(app.getPath("userData"), "luma-runtime.log"), "a");
  runtime = spawn(python, ["-m", "luma.cli", "serve", "--port", String(PORT)], {
    // PYTHONPATH lets it run straight from the folder even without an installed .venv.
    // LUMA_WHISPER_DOWNLOAD: fetch the speech model once, so you can talk to Luma.
    cwd: dir, env: { ...process.env, ...extraEnv, PYTHONUNBUFFERED: "1", LUMA_WHISPER_DOWNLOAD: "1", PYTHONPATH: [path.join(dir, "src"), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter) },
    stdio: ["ignore", log, log], windowsHide: true,
  });
  runtime.on("exit", () => { runtime = null; });
  // The first start loads the model; give it time.
  for (let i = 0; i < 240; i++) {
    if (await ping()) return { ok: true };
    if (!runtime) return { ok: false, reason: "Luma stopped while starting. Help → Runtime Log shows why." };
    await sleep(500);
  }
  return { ok: false, reason: "Luma is taking too long to start." };
}

// Luma's runtime ships inside the app; its Python, tools and brain arrive on first launch.
const bundledRuntime = () => path.join(process.resourcesPath || "", "luma");
const setupHome = () => path.join(app.getPath("userData"), "runtime");
const hasVenv = (dir) => fs.existsSync(path.join(dir, ".venv"));
let booting = false;

async function boot() {
  if (booting) return;
  booting = true;
  try {
    splash("starting");
    if (await ping()) return win.loadURL(HOME_URL);
    const dev = findRuntime();
    let started;
    if (dev && (hasVenv(dev) || !app.isPackaged || readConfig().runtimeDir === dev)) {
      started = await startRuntime(dev); // a developer's own Luma folder
    } else if (isRuntimeDir(bundledRuntime())) {
      if (setup.needsSetup(setupHome())) splash("setup");
      let ready;
      try { ready = await setup.ensure(setupHome(), (p) => win?.webContents.send("luma:setup", p)); }
      catch (error) { return splash("failed", error.message); }
      splash("starting");
      started = await startRuntime(bundledRuntime(), ready.python, ready.env);
    } else {
      return splash("missing");
    }
    if (started.ok) return win.loadURL(HOME_URL);
    splash("failed", started.reason);
  } finally {
    booting = false;
  }
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
    // On a Mac the window is real glass: what's behind it shows through when you pick See-through.
    ...(process.platform === "darwin"
      ? { vibrancy: "under-window", visualEffectState: "active", backgroundColor: "#00000000" }
      : { backgroundColor: nativeTheme.shouldUseDarkColors ? "#101014" : "#eef0f6" }),
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    trafficLightPosition: { x: 28, y: 28 },
    icon: path.join(__dirname, "build", "icon.png"),
    // backgroundThrottling off: Luma's page keeps checking in while hidden, so news still notifies you.
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true, nodeIntegration: false, spellcheck: true, backgroundThrottling: false },
  });
  win.once("ready-to-show", () => { if (!startHidden) win.show(); });
  win.on("close", (event) => {
    // Closing the window keeps Luma working in the menu bar or tray (⌥Space brings it back).
    if (quitting || !(tray || process.platform === "darwin")) return;
    event.preventDefault();
    win.hide();
    stillHereOnce();
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
  startHidden = false;
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
// Luma Desktop switches views by its address hash, without reloading.
const showView = (view) => () => {
  startHidden = false;
  if (!win) createWindow();
  win.show();
  win.focus();
  if (win.webContents.getURL().startsWith(HOME_URL)) win.webContents.executeJavaScript(`location.hash = ${JSON.stringify(view)}`);
  else if (!booting) win.loadURL(HOME_URL + "#" + view);
};

function buildMenu() {
  const isMac = process.platform === "darwin";
  const go = (url) => () => { if (win) { win.show(); win.loadURL(url); } };
  const show = showView;
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    ...(isMac ? [{ role: "appMenu" }] : []),
    { label: "File", submenu: [{ label: "New Conversation", accelerator: "CmdOrCtrl+N", click: () => win?.webContents.executeJavaScript("document.dispatchEvent(new KeyboardEvent('keydown',{key:'n',metaKey:true,ctrlKey:true}))") }, { type: "separator" }, isMac ? { role: "close" } : { role: "quit" }] },
    { role: "editMenu" },
    { label: "View", submenu: [
      { label: "Main Chat", accelerator: "CmdOrCtrl+1", click: show("chat") },
      { label: "Feed", accelerator: "CmdOrCtrl+2", click: show("feed") },
      { label: "Ideas", accelerator: "CmdOrCtrl+3", click: show("ideas") },
      { label: "Goals", accelerator: "CmdOrCtrl+4", click: show("goals") },
      { label: "Library", accelerator: "CmdOrCtrl+5", click: show("library") },
      { type: "separator" },
      { label: "Apps", accelerator: "CmdOrCtrl+,", click: show("apps") },
      { label: "Rules", click: show("rules") },
      { label: "All Controls", accelerator: "CmdOrCtrl+9", click: go(`${ORIGIN}/`) },
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

// ----------------------------------------------------- menu bar / tray ---
const LOGIN_ARGS = ["--hidden"];
const canStartAtLogin = process.platform === "darwin" || process.platform === "win32";
const startsAtLogin = () => canStartAtLogin && app.getLoginItemSettings({ args: LOGIN_ARGS }).openAtLogin;
function setStartAtLogin(on) {
  if (!canStartAtLogin) return;
  app.setLoginItemSettings({ openAtLogin: on, args: LOGIN_ARGS });
  writeConfig({ loginChosen: true });
}

function createTray() {
  const isMac = process.platform === "darwin";
  try {
    const image = nativeImage.createFromPath(path.join(__dirname, "build", isMac ? "trayTemplate.png" : "tray.png"));
    if (isMac) image.setTemplateImage(true);
    tray = new Tray(image);
  } catch (error) {
    console.warn("No menu bar icon:", error.message);
    tray = null;
    return;
  }
  tray.setToolTip("Luma");
  const refresh = () => tray.setContextMenu(Menu.buildFromTemplate([
    { label: "Open Luma", accelerator: SUMMON, registerAccelerator: false, click: showView("chat") },
    { label: "Feed", click: showView("feed") },
    { label: "Goals", click: showView("goals") },
    { type: "separator" },
    ...(canStartAtLogin ? [{ label: "Start Luma When I Log In", type: "checkbox", checked: startsAtLogin(), click: (item) => { setStartAtLogin(item.checked); refresh(); } }] : []),
    { type: "separator" },
    { label: "Quit Luma", click: () => app.quit() },
  ]));
  refresh();
  // Windows and Linux: a click on the tray icon opens Luma (on a Mac it opens the menu).
  if (!isMac) tray.on("click", summon);
}

function stillHereOnce() {
  // The first time the window closes on Windows, say where Luma went.
  if (process.platform === "darwin" || readConfig().trayHintShown) return;
  writeConfig({ trayHintShown: true });
  if (Notification.isSupported()) new Notification({ title: "Luma is still here", body: "It keeps working on your Goals. Click Luma in the tray, or press Ctrl+Alt+Space." }).show();
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
    // First launch: start at login, so Goals run every day (switch it off from the menu bar icon).
    if (canStartAtLogin && app.isPackaged && !readConfig().loginChosen) setStartAtLogin(true);
    startHidden = process.argv.includes("--hidden") || (process.platform === "darwin" && app.getLoginItemSettings().wasOpenedAtLogin);
    createTray();
    // Only Luma's own pages (the splash and the local desktop page) may ask for these.
    const trusted = (event) => { const url = event.senderFrame?.url || ""; return url.startsWith("file://") || url.startsWith(ORIGIN + "/"); };
    ipcMain.handle("luma:choose-folder", (event) => trusted(event) && chooseFolder());
    ipcMain.handle("luma:retry", (event) => { if (!trusted(event)) return false; boot(); return true; });
    session.defaultSession.on("will-download", (_event, item) => {
      item.setSavePath(uniquePath(app.getPath("downloads"), item.getFilename()));
      item.once("done", async (_e, state) => {
        if (state !== "completed") return;
        const file = item.getSavePath();
        if (Notification.isSupported()) new Notification({ title: "Saved to Downloads", body: path.basename(file) }).show();
        // Decks and documents open right away: PowerPoint if it's installed, otherwise Keynote on a Mac.
        if (/\.(pptx|key|docx|pdf|xlsx)$/i.test(file)) {
          const keynote = "/Applications/Keynote.app", powerpoint = "/Applications/Microsoft PowerPoint.app";
          if (process.platform === "darwin" && /\.pptx$/i.test(file) && !fs.existsSync(powerpoint) && fs.existsSync(keynote)) {
            spawn("open", ["-a", keynote, file], { detached: true, stdio: "ignore" }).unref();
            return;
          }
          if (!(await shell.openPath(file))) return; // opened with its usual app
        }
        shell.showItemInFolder(file);
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
  // With a menu bar or tray icon Luma keeps working after its window closes; Quit Luma stops it.
  app.on("window-all-closed", () => { if (!tray && process.platform !== "darwin") app.quit(); });
}
