// Luma Desktop: a small window onto the Luma running on this computer.
//
// Like the ChatGPT app and its local agent server, this shell holds no smarts
// of its own. It starts Luma's runtime (Python, local model) if it isn't
// running, opens its desktop page, and gives it what a real app needs: a dock
// icon, ⌥Space to summon, downloads, and links that open the right Mac app.
// Closing the window doesn't stop Luma: it stays in the menu bar (or the system
// tray on Windows) and starts at login, so your Goals keep running.
"use strict";
const { app, BrowserWindow, Menu, Tray, nativeImage, shell, dialog, globalShortcut, ipcMain, nativeTheme, Notification, session, powerSaveBlocker, net } = require("electron");
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

// More memory, longer memory: 8K tokens on an 8 GB computer, 16K on 16 GB, 32K on 24 GB and up.
function contextSize() {
  const gb = os.totalmem() / 2 ** 30;
  return gb >= 24 ? 32768 : gb >= 12 ? 16384 : 8192;
}

// While Luma is in the middle of something, the computer doesn't go to sleep on it.
let awake = null;
// Luma's eyes: the vision model downloads quietly after Luma is running, so photos work soon
// without slowing the first launch. Entirely optional — Luma is fine without it.
let visionTried = false;
function fetchVisionInBackground() {
  if (visionTried || !app.isPackaged) return;
  visionTried = true;
  setTimeout(() => {
    setup.ensureVision(setupHome(), () => {}).catch(() => { /* try again next launch */ });
  }, 60000);
}

function keepAwakeWhileWorking() {
  setInterval(() => {
    // With the window's own sign-in cookie, the same way Luma's page asks.
    const req = net.request({ url: `${ORIGIN}/api/activity`, useSessionCookies: true });
    req.on("response", (res) => {
      let body = "";
      res.on("data", (c) => { body += c; });
      res.on("end", () => {
        let busy = false;
        try { busy = ["running", "paused"].includes(JSON.parse(body).activity?.state); } catch { /* not ready */ }
        if (busy && awake === null) awake = powerSaveBlocker.start("prevent-app-suspension");
        if (!busy && awake !== null) { powerSaveBlocker.stop(awake); awake = null; }
      });
    });
    req.on("error", () => {});
    req.end();
  }, 20000);
}

async function startRuntime(dir, python = pythonFor(dir), extraEnv = {}) {
  if (await ping()) return { ok: true };
  const log = fs.openSync(path.join(app.getPath("userData"), "luma-runtime.log"), "a");
  runtime = spawn(python, ["-m", "luma.cli", "serve", "--port", String(PORT)], {
    // PYTHONPATH lets it run straight from the folder even without an installed .venv.
    // LUMA_WHISPER_DOWNLOAD: fetch the speech model once, so you can talk to Luma.
    // LUMA_CONTEXT_SIZE: how much of the conversation Luma can keep in mind at once, sized to this computer's memory.
    cwd: dir, env: { LUMA_CONTEXT_SIZE: String(contextSize()), LUMA_VISION_DIR: setup.visionDir(setupHome()), ...process.env, ...extraEnv, PYTHONUNBUFFERED: "1", LUMA_WHISPER_DOWNLOAD: "1", PYTHONPATH: [path.join(dir, "src"), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter) },
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

// ---------------------------------------------------------------- glass ---
// See-through, like Vision Pro: the window stops frosting what's behind it, so a movie or
// another app stays visible while you work. The page paints thin panels whose fill follows
// clarity (0–90%: how much shows through); Float on top keeps Luma over that video.
//   Mac: always a transparent window; vibrancy on = frosted glass, off = clear.
//   Windows: Electron can't make a framed window see-through per pixel, so the whole window
//     fades by clarity instead; acrylic behind the title bar for glass, none for clear.
//   Linux: transparency is fixed when a window is made, so switching makes a fresh one.
const GLASS = { mode: "glass", clarity: 60, onTop: false };
// Only exactly { mode: "glass"|"clear", clarity: 0–90, onTop: bool }; anything else is refused.
function cleanGlass(g) {
  if (!g || typeof g !== "object" || Array.isArray(g) || Object.keys(g).some((k) => !(k in GLASS))) return null;
  const { mode, clarity, onTop } = g;
  if ((mode !== "glass" && mode !== "clear") || typeof onTop !== "boolean") return null;
  if (typeof clarity !== "number" || !Number.isFinite(clarity) || clarity < 0 || clarity > 90) return null;
  return { mode, clarity: Math.round(clarity), onTop };
}
const savedGlass = () => cleanGlass(readConfig().glass) || { ...GLASS };
const wantsTransparent = (g) => process.platform === "darwin" || (process.platform === "linux" && g.mode === "clear");
let winTransparent = false;

function applyGlass(w, g, was = null) {
  if (!w || w.isDestroyed()) return;
  const clear = g.mode === "clear";
  if (!was || was.mode !== g.mode) {
    if (process.platform === "darwin") w.setVibrancy(clear ? null : "under-window");
    if (process.platform === "win32" && typeof w.setBackgroundMaterial === "function") w.setBackgroundMaterial(clear ? "none" : "acrylic");
  }
  if (process.platform === "win32") w.setOpacity(clear ? 1 - (g.clarity / 100) * 0.55 : 1);
  if (!was || was.onTop !== g.onTop) {
    w.setAlwaysOnTop(g.onTop, "floating");
    // On every desktop too; skipTransformProcessType keeps the Dock icon where it is.
    if (process.platform !== "win32") w.setVisibleOnAllWorkspaces(g.onTop, { skipTransformProcessType: true });
  }
}

function setGlass(next) {
  const was = savedGlass();
  writeConfig({ glass: next });
  if (win && !win.isDestroyed() && wantsTransparent(next) !== winTransparent) rebuildWindow();
  else applyGlass(win, next, was);
  if (was.mode !== next.mode || was.onTop !== next.onTop) buildMenu();
  return next;
}
// From the app's menu: the page hears about it too.
const glassFromMenu = (change) => { const next = setGlass({ ...savedGlass(), ...change }); if (win && !win.isDestroyed()) win.webContents.send("luma:glass", next); };

// --------------------------------------------------------------- window ---
function createWindow({ bounds, url } = {}) {
  const glass = savedGlass();
  winTransparent = wantsTransparent(glass);
  const w = win = new BrowserWindow({
    width: 1180,
    height: 780,
    ...bounds,
    minWidth: 760,
    minHeight: 560,
    title: "Luma",
    show: false,
    // A transparent window lets See-through show what's behind Luma (the page paints the glass).
    ...(winTransparent ? { transparent: true, backgroundColor: "#00000000" } : { backgroundColor: nativeTheme.shouldUseDarkColors ? "#101014" : "#eef0f6" }),
    ...(process.platform === "darwin" ? { vibrancy: "under-window", visualEffectState: "active" } : {}),
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    trafficLightPosition: { x: 28, y: 28 },
    icon: path.join(__dirname, "build", "icon.png"),
    // backgroundThrottling off: Luma's page keeps checking in while hidden, so news still notifies you.
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true, nodeIntegration: false, spellcheck: true, backgroundThrottling: false,
      // Luma answers out loud after "Hey Luma" too, without waiting for a click first.
      autoplayPolicy: "no-user-gesture-required" },
  });
  applyGlass(w, glass);
  w.once("ready-to-show", () => { if (!startHidden) w.show(); });
  w.on("close", (event) => {
    // Closing the window keeps Luma working in the menu bar or tray (⌥Space brings it back).
    if (quitting || !(tray || process.platform === "darwin")) return;
    event.preventDefault();
    w.hide();
    stillHereOnce();
  });

  // Only Luma's own pages load in the window. Everything else opens where it belongs:
  // sms: in Messages, mailto: in Mail, web links in the browser.
  const openOutside = (url) => { if (/^(https?|sms|mailto|tel|facetime):/i.test(url)) shell.openExternal(url); };
  w.webContents.setWindowOpenHandler(({ url }) => { openOutside(url); return { action: "deny" }; });
  w.webContents.on("will-navigate", (event, url) => {
    if (url.startsWith(ORIGIN + "/") || url.startsWith("file://")) return;
    event.preventDefault();
    openOutside(url);
  });
  w.webContents.on("did-fail-load", (_e, code, _desc, url) => { if (w === win && url.startsWith(ORIGIN) && code !== -3) setTimeout(boot, 1500); });

  if (url) w.loadURL(url); else boot();
}

// A fresh window in the same place, on the same page; the old one goes once the new one shows.
function rebuildWindow() {
  const old = win;
  const url = old.webContents.getURL();
  createWindow({ bounds: old.getBounds(), url: url.startsWith(ORIGIN + "/") ? url : null });
  win.once("ready-to-show", () => { if (!old.isDestroyed()) old.destroy(); });
}

function summon() {
  startHidden = false;
  if (!win) return createWindow();
  if (win.isVisible() && win.isFocused()) return win.hide();
  win.show();
  win.focus();
  tellPage("luma-summon"); // with Stay in conversation on, Luma is listening as soon as it's up
}
// Luma's page hears about it (an event on its window), if it's the page that's open.
function tellPage(name) {
  if (win?.webContents.getURL().startsWith(HOME_URL)) win.webContents.executeJavaScript(`window.dispatchEvent(new Event(${JSON.stringify(name)}))`).catch(() => {});
}
// Start talking: from the menu bar icon, or the Voice menu.
function talk() {
  startHidden = false;
  if (!win) createWindow();
  win.show();
  win.focus();
  tellPage("luma-talk");
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
  const glass = savedGlass();
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    ...(isMac ? [{ role: "appMenu" }] : []),
    { label: "File", submenu: [{ label: "New Conversation", accelerator: "CmdOrCtrl+N", click: () => win?.webContents.executeJavaScript("document.dispatchEvent(new KeyboardEvent('keydown',{key:'n',metaKey:true,ctrlKey:true}))") }, { type: "separator" }, isMac ? { role: "close" } : { role: "quit" }] },
    { role: "editMenu" },
    { label: "View", submenu: [
      { label: "Main Chat", accelerator: "CmdOrCtrl+1", click: show("chat") },
      // The page itself handles ⌘⇧Space (in any view and any chat); this just shows it.
      { label: "Talk to Luma", accelerator: "CmdOrCtrl+Shift+Space", registerAccelerator: false, click: talk },
      { label: "Feed", accelerator: "CmdOrCtrl+2", click: show("feed") },
      { label: "Ideas", accelerator: "CmdOrCtrl+3", click: show("ideas") },
      { label: "Goals", accelerator: "CmdOrCtrl+4", click: show("goals") },
      { label: "Library", accelerator: "CmdOrCtrl+5", click: show("library") },
      { type: "separator" },
      { label: "Apps", accelerator: "CmdOrCtrl+,", click: show("apps") },
      { label: "Rules", click: show("rules") },
      { label: "All Controls", accelerator: "CmdOrCtrl+9", click: go(`${ORIGIN}/`) },
      { type: "separator" },
      { label: "See-Through", type: "checkbox", checked: glass.mode === "clear", click: (item) => glassFromMenu({ mode: item.checked ? "clear" : "glass" }) },
      { label: "Float on Top", type: "checkbox", checked: glass.onTop, click: (item) => glassFromMenu({ onTop: item.checked }) },
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
    { label: "Talk to Luma", click: talk },
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
    keepAwakeWhileWorking();
    fetchVisionInBackground();
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
    // See-through: only the desktop page in Luma's own window, and only valid values (cleanGlass).
    const fromHome = (event) => event.sender === win?.webContents && (event.senderFrame?.url || "").startsWith(HOME_URL);
    ipcMain.handle("luma:glass-get", (event) => (fromHome(event) ? cleanGlass(readConfig().glass) : null));
    ipcMain.handle("luma:glass-set", (event, g) => { const next = fromHome(event) && cleanGlass(g); return next ? setGlass(next) : null; });
    // "Hey Luma" brings the window up.
    ipcMain.handle("luma:show", (event) => { if (!trusted(event) || !win) return false; startHidden = false; win.show(); win.focus(); return true; });
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
