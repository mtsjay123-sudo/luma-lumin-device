// The only things Luma's pages may ask of the app: pick Luma's folder, try
// starting again, know they're inside the desktop app (for window chrome), and
// make the window see-through.
"use strict";
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("lumaDesktop", {
  platform: process.platform,
  chooseFolder: () => ipcRenderer.invoke("luma:choose-folder"),
  retry: () => ipcRenderer.invoke("luma:retry"),
  // First-launch setup progress, for the splash screen.
  onSetup: (callback) => ipcRenderer.on("luma:setup", (_event, progress) => callback(progress)),
  // See-through: { mode: "glass" | "clear", clarity: 0–90, onTop: bool }. The app checks every value.
  getGlass: () => ipcRenderer.invoke("luma:glass-get"),
  setGlass: (glass) => ipcRenderer.invoke("luma:glass-set", { mode: glass?.mode, clarity: glass?.clarity, onTop: glass?.onTop }),
  onGlass: (callback) => ipcRenderer.on("luma:glass", (_event, glass) => callback(glass)),
});

window.addEventListener("DOMContentLoaded", () => {
  document.documentElement.classList.add("in-app", "platform-" + process.platform);
});
