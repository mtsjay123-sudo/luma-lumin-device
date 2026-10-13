"use strict";
const params = new URLSearchParams(location.search);
const state = params.get("state") || "starting";
const $ = (id) => document.getElementById(id);
const copy = {
  starting: ["Waking up…", "Starting Luma's brain on this computer. The first time takes a minute."],
  missing: ["Where's Luma?", "I couldn't find Luma on this computer. Show me the luma-lumin-device folder and I'll remember it."],
  failed: ["Luma didn't start", params.get("detail") || "Something stopped Luma from starting."],
};
const [title, detail] = copy[state] || copy.starting;
$("title").textContent = title;
$("detail").textContent = detail;
document.body.classList.add(state);
if (state !== "starting") {
  $("actions").hidden = false;
  $("choose").addEventListener("click", () => window.lumaDesktop?.chooseFolder());
  $("retry").addEventListener("click", () => window.lumaDesktop?.retry());
}
