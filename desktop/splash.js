"use strict";
const params = new URLSearchParams(location.search);
const state = params.get("state") || "starting";
const $ = (id) => document.getElementById(id);
const copy = {
  starting: ["Waking up…", "Starting Luma's brain on this computer. This takes a few seconds."],
  setup: ["Setting up Luma", "The first time, Luma gets what it needs to run privately on this computer. About 3 GB, once."],
  missing: ["Where's Luma?", "I couldn't find Luma on this computer. Show me the luma-lumin-device folder and I'll remember it."],
  failed: ["Luma didn't start", params.get("detail") || "Something stopped Luma from starting."],
};
const [title, detail] = copy[state] || copy.starting;
$("title").textContent = title;
$("detail").textContent = detail;
document.body.classList.add(state);
if (state === "missing" || state === "failed") {
  $("actions").hidden = false;
  $("choose").addEventListener("click", () => window.lumaDesktop?.chooseFolder());
  $("retry").addEventListener("click", () => window.lumaDesktop?.retry());
}
if (state === "setup") {
  $("setup").hidden = false;
  $("bar").hidden = false;
  $("fine").hidden = false;
}
const ORDER = ["python", "packages", "browser", "model", "done"];
window.lumaDesktop?.onSetup?.((p) => {
  if (state !== "setup") return;
  const at = ORDER.indexOf(p.step);
  for (const li of document.querySelectorAll("#setup li")) {
    const i = ORDER.indexOf(li.dataset.step);
    li.classList.toggle("done", i < at);
    li.classList.toggle("now", i === at);
  }
  if (p.detail && $("how-" + p.step)) $("how-" + p.step).textContent = p.detail;
  if (p.label) $("title").textContent = p.step === "done" ? "Starting Luma" : p.label + "…";
  $("fill").style.width = Math.round(Math.max(0, Math.min(1, p.fraction || 0)) * 100) + "%";
});
