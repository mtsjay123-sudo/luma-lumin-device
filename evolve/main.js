(() => {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fine = window.matchMedia("(pointer: fine)").matches;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  /* ---------------------------------------------------------------- entrance */
  requestAnimationFrame(() => $$(".anim").forEach((el) => el.classList.add("in")));
  $$(".anim").forEach((el) => el.addEventListener("animationend", (e) => { if (e.target === el) el.classList.add("done"); }));

  /* ---------------------------------------------------------------- headline letters (hover wave) */
  let k = 0;
  $$("#headline .line").forEach((line) => {
    const text = line.textContent;
    line.setAttribute("aria-label", text);
    line.textContent = "";
    for (const c of text) {
      const s = document.createElement("span");
      s.className = c === " " ? "ch sp" : "ch";
      s.setAttribute("aria-hidden", "true");
      s.style.setProperty("--k", k++);
      s.textContent = c === " " ? " " : c;
      line.appendChild(s);
    }
  });

  /* ---------------------------------------------------------------- nav: gliding three-dot indicator */
  const nav = $("#nav");
  const navDots = $(".nav-dots", nav);
  const active = $(".nav-link.is-active", nav);
  const placeDots = (link) => {
    const x = link.offsetLeft + link.offsetWidth / 2 - 1.5;
    navDots.style.transform = `translateX(${x}px)`;
  };
  if (nav && navDots && active) {
    const init = () => { placeDots(active); nav.classList.add("js-dots"); };
    document.fonts ? document.fonts.ready.then(init) : init();
    $$(".nav-link", nav).forEach((l) => l.addEventListener("mouseenter", () => placeDots(l)));
    nav.addEventListener("mouseleave", () => placeDots(active));
    window.addEventListener("resize", () => placeDots(active));
  }

  /* ---------------------------------------------------------------- mobile menu */
  const burger = $("#burger");
  const menu = $("#mobile-menu");
  const overlay = $("#menu-overlay");
  const setMenu = (open) => {
    burger.setAttribute("aria-expanded", String(open));
    burger.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    menu.hidden = !open;
    overlay.hidden = !open;
    document.body.classList.toggle("menu-open", open);
  };
  burger.addEventListener("click", () => setMenu(burger.getAttribute("aria-expanded") !== "true"));
  overlay.addEventListener("click", () => setMenu(false));
  $$("a", menu).forEach((a) => a.addEventListener("click", () => setMenu(false)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setMenu(false); });
  window.addEventListener("resize", () => { if (window.innerWidth > 720) setMenu(false); });

  /* ---------------------------------------------------------------- stats count-up */
  const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
  const fmt = (v, d) => v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  const runCounters = () => {
    $$(".stat-value").forEach((el, i) => {
      const target = parseFloat(el.dataset.target);
      const dec = parseInt(el.dataset.decimals, 10) || 0;
      const suffix = el.dataset.suffix || "";
      const bar = el.parentElement.querySelector(".stat-bar i");
      if (reduced) { el.textContent = fmt(target, dec) + suffix; if (bar) bar.style.setProperty("--p", 1); return; }
      const dur = 1500 + i * 80;
      setTimeout(() => {
        const t0 = performance.now();
        const tick = (now) => {
          const p = Math.min(1, (now - t0) / dur);
          const e = easeOutCubic(p);
          el.textContent = fmt(target * e, dec) + suffix;
          if (bar) bar.style.setProperty("--p", e);
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      }, 480 + i * 90);
    });
  };
  const stats = $("#stats");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { io.disconnect(); runCounters(); }
    }, { threshold: 0.25 });
    io.observe(stats);
  } else runCounters();

  /* ---------------------------------------------------------------- agent chips: typewriter cycles */
  $$(".chip-v[data-cycle]").forEach((el, n) => {
    const items = el.dataset.cycle.split("|");
    let idx = 0;
    if (reduced) { el.textContent = items[0]; return; }
    const type = (str, done) => {
      let i = 0;
      const step = () => { el.textContent = str.slice(0, ++i); i < str.length ? setTimeout(step, 28 + Math.random() * 40) : done(); };
      step();
    };
    const erase = (done) => {
      const step = () => { el.textContent = el.textContent.slice(0, -1); el.textContent ? setTimeout(step, 14) : done(); };
      step();
    };
    const loop = () => type(items[idx], () => setTimeout(() => erase(() => { idx = (idx + 1) % items.length; loop(); }), 2400 + n * 300));
    setTimeout(loop, 1300 + n * 250);
  });

  /* ---------------------------------------------------------------- HUD clock + live throughput */
  const clock = $("#clock");
  const tok = $("#tok");
  let tokV = 18400;
  const hud = () => {
    const d = new Date();
    clock.textContent = [d.getUTCHours(), d.getUTCMinutes(), d.getUTCSeconds()].map((x) => String(x).padStart(2, "0")).join(":");
    tokV += (Math.random() - 0.48) * 900;
    tokV = Math.max(14000, Math.min(26000, tokV));
    tok.textContent = Math.round(tokV).toLocaleString("en-US");
  };
  hud();
  setInterval(hud, 1000);

  /* ---------------------------------------------------------------- reactive dot-matrix field */
  const cv = $("#dots");
  const ctx = cv.getContext("2d");
  const GAP = 22;
  let W = 0, H = 0, DPR = 1, cols = 0, rows = 0;
  const mouse = { x: -9999, y: -9999, tx: -9999, ty: -9999 };
  const ripples = [];
  const resize = () => {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    cv.width = W * DPR; cv.height = H * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    cols = Math.ceil(W / GAP) + 1; rows = Math.ceil(H / GAP) + 1;
  };
  resize();
  window.addEventListener("resize", resize);

  const ripple = (x, y) => ripples.push({ x, y, t: performance.now() });
  window.addEventListener("pointermove", (e) => { mouse.tx = e.clientX; mouse.ty = e.clientY; }, { passive: true });
  window.addEventListener("pointerdown", (e) => ripple(e.clientX, e.clientY), { passive: true });
  document.addEventListener("mouseleave", () => { mouse.tx = mouse.ty = -9999; });

  let running = !reduced;
  document.addEventListener("visibilitychange", () => {
    running = !document.hidden && !reduced;
    if (running) requestAnimationFrame(draw);
  });

  function draw(now) {
    if (!running) return;
    // ease the glow toward the pointer so it trails a little
    if (mouse.tx < -1000) { mouse.x = mouse.tx; mouse.y = mouse.ty; }
    else if (mouse.x < -1000) { mouse.x = mouse.tx; mouse.y = mouse.ty; }
    else { mouse.x += (mouse.tx - mouse.x) * 0.14; mouse.y += (mouse.ty - mouse.y) * 0.14; }
    for (let i = ripples.length - 1; i >= 0; i--) if (now - ripples[i].t > 1800) ripples.splice(i, 1);

    ctx.clearRect(0, 0, W, H);
    const t = now / 1000;
    const R = 150;
    for (let j = 0; j < rows; j++) {
      const y = j * GAP;
      for (let i = 0; i < cols; i++) {
        const x = i * GAP;
        // slow diagonal "scan" wave so the field breathes even without input
        let a = 0.05 + 0.05 * Math.max(0, Math.sin((x + y) * 0.006 - t * 0.9));
        let r = 0.8;
        const dx = x - mouse.x, dy = y - mouse.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < R * R) { const f = 1 - Math.sqrt(d2) / R; a += f * f * 0.65; r += f * f * 1.6; }
        for (const rp of ripples) {
          const age = (now - rp.t) / 1000, front = age * 520;
          const dd = Math.hypot(x - rp.x, y - rp.y);
          const band = 1 - Math.abs(dd - front) / 46;
          if (band > 0) { const f = band * (1 - age / 1.8); a += f * 0.75; r += f * 1.8; }
        }
        if (a < 0.02) continue;
        ctx.globalAlpha = Math.min(1, a);
        ctx.beginPath();
        ctx.arc(x, y, r, 0, 6.2832);
        ctx.fillStyle = "#fff";
        ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(draw);
  }
  if (running) requestAnimationFrame(draw);

  /* ---------------------------------------------------------------- parallax chips + magnetic CTA */
  const chips = $$(".chip");
  const cta = $("#cta");
  if (fine && !reduced) {
    window.addEventListener("pointermove", (e) => {
      const nx = e.clientX / window.innerWidth - 0.5;
      const ny = e.clientY / window.innerHeight - 0.5;
      chips.forEach((c) => {
        const dpt = parseFloat(c.dataset.depth) || 16;
        c.style.setProperty("--px", `${(-nx * dpt).toFixed(1)}px`);
        c.style.setProperty("--py", `${(-ny * dpt).toFixed(1)}px`);
      });
    }, { passive: true });

    cta.addEventListener("pointermove", (e) => {
      const b = cta.getBoundingClientRect();
      const mx = (e.clientX - b.left - b.width / 2) * 0.18;
      const my = (e.clientY - b.top - b.height / 2) * 0.3;
      cta.style.transform = `translate(${mx}px, ${my - 2}px) scale(1.02)`;
    });
    cta.addEventListener("pointerleave", () => { cta.style.transform = ""; });
  }
  cta.addEventListener("click", (e) => {
    e.preventDefault();
    const b = cta.getBoundingClientRect();
    ripple(b.left + b.width / 2, b.top + b.height / 2);
  });

  /* ---------------------------------------------------------------- logo: spin + shockwave */
  const logo = $("#logo");
  logo.addEventListener("click", (e) => {
    e.preventDefault();
    logo.classList.remove("spin");
    void logo.offsetWidth;
    logo.classList.add("spin");
    const b = logo.getBoundingClientRect();
    ripple(b.left + b.width / 2, b.top + b.height / 2);
    setTimeout(() => logo.classList.remove("spin"), 900);
  });
})();
