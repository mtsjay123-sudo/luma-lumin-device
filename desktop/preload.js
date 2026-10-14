// The only things Luma's pages may ask of the app: pick Luma's folder, try
// starting again, come to the front ("Hey Luma"), and know they're inside the
// desktop app (for window chrome).
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
});

window.addEventListener("DOMContentLoaded", () => {
  document.documentElement.classList.add("in-app", "platform-" + process.platform);
});
