(() => {
  "use strict";

  // LED dot numbers, the same 5x7 grid the device's display and the app use.
  const FONT = {
    0: ["01110", "10001", "10001", "10001", "10001", "10001", "01110"], 1: ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    2: ["01110", "10001", "00001", "00010", "00100", "01000", "11111"], 3: ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    4: ["00010", "00110", "01010", "10010", "11111", "00010", "00010"], 5: ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    6: ["00110", "01000", "10000", "11110", "10001", "10001", "01110"], 7: ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    8: ["01110", "10001", "10001", "01110", "10001", "10001", "01110"], 9: ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    ":": ["0", "0", "1", "0", "1", "0", "0"],
  };
  const SVG = "http://www.w3.org/2000/svg";

  function led(span, text) {
    span.replaceChildren();
    for (const ch of String(text)) {
      const rows = FONT[ch];
      if (!rows) continue;
      const svg = document.createElementNS(SVG, "svg");
      svg.setAttribute("viewBox", `0 0 ${rows[0].length * 10} 70`);
      svg.setAttribute("aria-hidden", "true");
      rows.forEach((row, y) => [...row].forEach((bit, x) => {
        const c = document.createElementNS(SVG, "circle");
        c.setAttribute("cx", x * 10 + 5); c.setAttribute("cy", y * 10 + 5); c.setAttribute("r", 3.6);
        if (bit !== "1") c.setAttribute("class", "off");
        svg.append(c);
      }));
      span.append(svg);
    }
    span.setAttribute("role", "img");
    span.setAttribute("aria-label", span.dataset.label || String(text));
  }

  // the hero device shows the visitor's own time, like it would on their counter
  const clock = document.querySelector("[data-clock]");
  function tick() {
    const d = new Date();
    clock.dataset.led = `${d.getHours() % 12 || 12}:${String(d.getMinutes()).padStart(2, "0")}`;
    led(clock, clock.dataset.led);
  }
  if (clock) { tick(); setInterval(tick, 20000); }
  document.querySelectorAll("[data-led]:not([data-clock])").forEach((s) => led(s, s.dataset.led));

  // memory deck: the front card faces you, the rest fan away like folders on a shelf
  const deck = document.getElementById("deck");
  if (!deck) return;
  const cards = [...deck.querySelectorAll(".card")];
  const pos = document.getElementById("deck-pos");
  let at = Math.floor((cards.length - 1) / 2);
  function layout() {
    const narrow = deck.clientWidth < 520;
    cards.forEach((c, i) => {
      const off = i - at, a = Math.abs(off), s = Math.sign(off);
      c.classList.toggle("front", off === 0);
      c.setAttribute("aria-selected", String(off === 0));
      c.tabIndex = off === 0 ? 0 : -1;
      const x = s * ((narrow ? 92 : 110) + (a - 1) * (narrow ? 14 : 30));
      c.style.transform = off === 0 ? "translateZ(40px)" : `translateX(${x}px) translateZ(${-a * 34}px) rotateY(${s * -62}deg)`;
      c.style.opacity = String(Math.max(0, 1 - a * 0.14));
      c.style.zIndex = String(100 - a);
    });
    if (pos) pos.textContent = `${at + 1} of ${cards.length}`;
  }
  function go(i) { at = Math.max(0, Math.min(cards.length - 1, i)); layout(); }
  cards.forEach((c, i) => {
    // the back cards hide their text, so name each one in full for screen readers
    c.setAttribute("aria-label", `${c.querySelector(".tag").textContent}: ${c.querySelector("p").textContent}`);
    c.addEventListener("click", () => go(i));
  });
  deck.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") { go(at - 1); e.preventDefault(); }
    if (e.key === "ArrowRight") { go(at + 1); e.preventDefault(); }
  });
  let downX = null;
  deck.addEventListener("pointerdown", (e) => { downX = e.clientX; });
  deck.addEventListener("pointerup", (e) => {
    if (downX == null) return;
    const dx = e.clientX - downX;
    downX = null;
    if (Math.abs(dx) > 30) go(at + (dx < 0 ? 1 : -1));
  });
  document.getElementById("deck-prev")?.addEventListener("click", () => go(at - 1));
  document.getElementById("deck-next")?.addEventListener("click", () => go(at + 1));
  addEventListener("resize", layout);
  layout();
})();
