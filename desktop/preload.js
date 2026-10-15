// The only things Luma's pages may ask of the app: pick Luma's folder, try
// starting again, come to the front ("Hey Luma"), know they're inside the
// desktop app (for window chrome), and make the window see-through.
"use strict";
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("lumaDesktop", {
  platform: process.platform,
  chooseFolder: () => ipcRenderer.invoke("luma:choose-folder"),
  retry: () => ipcRenderer.invoke("luma:retry"),
  // "Hey Luma" brings Luma's window up.
  show: () => ipcRenderer.invoke("luma:show"),
  // First-launch setup progress, for the splash screen.
  onSetup: (callback) => ipcRenderer.on("luma:setup", (_event, progress) => callback(progress)),
  // See-through: { mode: "glass" | "clear", clarity: 0–90, onTop: bool }. The app checks every value.
  getGlass: () => ipcRenderer.invoke("luma:glass-get"),
  setGlass: (glass) => ipcRenderer.invoke("luma:glass-set", { mode: glass?.mode, clarity: glass?.clarity, onTop: glass?.onTop }),
  onGlass: (callback) => ipcRenderer.on("luma:glass", (_event, glass) => callback(glass)),
  // Touch ID lock: can this Mac do it, and ask for a fingerprint (true only if it matched).
  canLock: () => ipcRenderer.invoke("luma:can-lock"),
  unlock: () => ipcRenderer.invoke("luma:unlock"),
  // Luma Link: open the paired device's Luma in this window, or come back to this computer's.
  useDevice: (entry) => ipcRenderer.invoke("luma:use-device", { url: entry?.url, origin: entry?.origin, fingerprint: entry?.fingerprint }),
  useLocal: () => ipcRenderer.invoke("luma:use-local"),
  prefersDevice: () => ipcRenderer.invoke("luma:device-pref"),
  // Luma's runtime stopped and the app started it again: the page says so, kindly.
  onRestarted: (callback) => ipcRenderer.on("luma:restarted", (_event, info) => callback(info)),
  // Repair: reinstall Luma's tools and fetch its brain again, then start fresh.
  repair: () => ipcRenderer.invoke("luma:repair"),
  // The Browser page is a real browser here: share a site's sign-in with Luma's own browser, and back.
  webCookies: (url) => ipcRenderer.invoke("luma:web-cookies-get", String(url || "")),
  setWebCookies: (list) => ipcRenderer.invoke("luma:web-cookies-set", Array.isArray(list) ? list.slice(0, 400) : []),
});

window.addEventListener("DOMContentLoaded", () => {
  document.documentElement.classList.add("in-app", "platform-" + process.platform);
});
