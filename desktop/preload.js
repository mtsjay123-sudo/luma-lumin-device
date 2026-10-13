// The only things Luma's pages may ask of the app: pick Luma's folder, try
// starting again, and know they're inside the desktop app (for window chrome).
"use strict";
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("lumaDesktop", {
  platform: process.platform,
  chooseFolder: () => ipcRenderer.invoke("luma:choose-folder"),
  retry: () => ipcRenderer.invoke("luma:retry"),
});

window.addEventListener("DOMContentLoaded", () => {
  document.documentElement.classList.add("in-app", "platform-" + process.platform);
});
