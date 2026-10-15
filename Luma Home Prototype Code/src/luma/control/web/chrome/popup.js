const show = async () => {
  const { token } = await chrome.storage.local.get("token");
  document.getElementById("paired").hidden = !token;
  document.getElementById("unpaired").hidden = Boolean(token);
};
document.getElementById("go").addEventListener("click", async () => {
  const msg = document.getElementById("msg");
  msg.className = ""; msg.textContent = "Connecting…";
  try {
    const r = await fetch("http://127.0.0.1:8095/api/ext/pair", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: document.getElementById("code").value }) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "That didn't work.");
    await chrome.storage.local.set({ token: d.token });
    msg.textContent = "";
    show();
  } catch (e) { msg.className = "err"; msg.textContent = e.message.includes("Failed to fetch") ? "Open Luma on this computer first." : e.message; }
});
document.getElementById("unpair").addEventListener("click", async () => { await chrome.storage.local.remove("token"); show(); });
show();
