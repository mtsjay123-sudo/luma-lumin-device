"use strict";
const params = new URLSearchParams(location.search);
const state = params.get("state") || "starting";
const $ = (id) => document.getElementById(id);
const copy = {
  starting: ["Waking up", "Starting Luma on this computer."],
  setup: ["Setting up Luma", "The first time, Luma gets what it needs to run privately on this computer."],
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
  // Repair reinstalls Luma's tools and checks its brain file, then starts fresh.
  $("repair").addEventListener("click", () => { $("detail").textContent = "Repairing… this can take a few minutes."; window.lumaDesktop?.repair(); });
}
if (state === "setup") $("progress").hidden = false;

// Each step reports its own progress; the bar shows the whole setup, weighted by how long each takes.
const ORDER = ["python", "packages", "browser", "model", "voice", "done"];
const WEIGHT = { python: 0.05, packages: 0.22, browser: 0.08, model: 0.57, voice: 0.08 };
window.lumaDesktop?.onSetup?.((p) => {
  if (state !== "setup") return;
  const at = ORDER.indexOf(p.step);
  for (const li of document.querySelectorAll("#setup li")) {
    const i = ORDER.indexOf(li.dataset.step);
    li.classList.toggle("done", i < at);
    li.classList.toggle("now", i === at);
  }
  const before = ORDER.slice(0, Math.max(at, 0)).reduce((sum, s) => sum + (WEIGHT[s] || 0), 0);
  const overall = p.step === "done" ? 1 : before + (WEIGHT[p.step] || 0) * Math.max(0, Math.min(1, p.fraction || 0));
  const pct = Math.round(overall * 100);
  $("fill").style.width = pct + "%";
  $("percent").textContent = pct + "%";
  const label = p.step === "done" ? "Starting Luma" : p.label || "Working";
  $("step-label").textContent = p.detail && p.step !== "packages" ? `${label} · ${p.detail}` : label;
});
