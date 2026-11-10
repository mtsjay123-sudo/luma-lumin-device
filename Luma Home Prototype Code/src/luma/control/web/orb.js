// Luma, as a drop of liquid light.
//
// One orb for everywhere Luma shows itself: the talk screen, the first-run slides, the small avatar by its name, the
// logo. A small shader draws it, so it moves like liquid and never repeats: ribbons of light turn inside a glass
// ball, the way ink turns in water. Each mood pours into the next instead of switching:
//
//   idle        the marble: wide, slow ribbons (this one is the logo)
//   listening   it opens into a ring, and the ring moves with your voice
//   thinking    the ribbons wind into a spiral
//   speaking    it fills with warm light and moves with Luma's voice
//   waiting     warm and slow, while Luma waits for your answer
//
//   const orb = LumaOrb.mount(element, { mood: "idle" });   // a live orb that fills the element
//   orb.set("speaking", 0.6);                               // mood, and how loud the voice is right now (0 to 1)
//   orb.close();                                            // it drains away, then stops
//   LumaOrb.still(96, "idle")                               // a picture of it (a data URL), for small or still places
//
// Nothing here loads or sends anything. With no WebGL it draws a simpler orb with the ordinary canvas. When the
// person has asked their device for less motion, it holds still and only changes with the mood.
(function () {
  "use strict";

  // Each mood: how fast the liquid flows, how much the ribbons fold, how far they wind into a spiral, how far the
  // middle opens, its light, how much the glass splits light into colors, and its colors (the dark of the glass,
  // the ribbons, the bright heart of a ribbon, the second color at a ribbon's edge).
  const MOODS = {
    idle: { flow: 0.22, turb: 0.22, swirl: 0.0, hollow: 0.0, bright: 1.0, iri: 0.40, deep: [0.030, 0.040, 0.105], mid: [0.52, 0.68, 0.96], lite: [0.97, 0.985, 1.0], glint: [0.98, 0.76, 0.44] },
    listening: { flow: 0.42, turb: 0.40, swirl: 0.0, hollow: 1.0, bright: 1.08, iri: 0.55, deep: [0.010, 0.040, 0.120], mid: [0.24, 0.60, 1.0], lite: [0.86, 0.97, 1.0], glint: [0.36, 0.95, 0.86] },
    waiting: { flow: 0.26, turb: 0.24, swirl: 0.0, hollow: 0.0, bright: 1.04, iri: 0.45, deep: [0.060, 0.035, 0.085], mid: [0.99, 0.72, 0.46], lite: [1.0, 0.95, 0.86], glint: [0.80, 0.64, 1.0] },
    thinking: { flow: 0.80, turb: 0.50, swirl: 1.0, hollow: 0.0, bright: 1.0, iri: 0.65, deep: [0.045, 0.022, 0.125], mid: [0.56, 0.43, 1.0], lite: [0.93, 0.87, 1.0], glint: [1.0, 0.46, 0.72] },
    speaking: { flow: 0.62, turb: 0.52, swirl: 0.0, hollow: 0.0, bright: 1.12, iri: 0.75, deep: [0.060, 0.030, 0.110], mid: [1.0, 0.68, 0.46], lite: [1.0, 0.975, 0.93], glint: [1.0, 0.44, 0.66] },
  };
  const NUMBERS = ["flow", "turb", "swirl", "hollow", "bright", "iri"];
  const COLORS = ["deep", "mid", "lite", "glint"];
  const UNIFORMS = ["uRes", "uT", "uLevel", "uTurb", "uSwirl", "uHollow", "uBright", "uIri", "uOpen", "uSize", "uDeep", "uMid", "uLite", "uGlint"];

  const VERTEX = "attribute vec2 p; void main() { gl_Position = vec4(p, 0.0, 1.0); }";
  const FRAGMENT = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform vec2 uRes;
uniform float uT, uLevel, uTurb, uSwirl, uHollow, uBright, uIri, uOpen, uSize;
uniform vec3 uDeep, uMid, uLite, uGlint;

// The liquid: a point is pushed around by slow waves, each one folding the last, the way ink turns in water.
vec2 fold(vec2 q, float t, float much) {
  for (int i = 1; i < 5; i++) {
    float f = float(i);
    q.x += much * (0.62 / f) * sin(f * 1.5 * q.y + t * (0.50 + 0.07 * f) + 1.7 * f);
    q.y += much * (0.46 / f) * cos(f * 1.8 * q.x - t * (0.42 + 0.09 * f) + 0.6 * f);
  }
  return q;
}
// Where the ribbons run: above zero is ribbon, and the higher, the brighter its heart. (It also hands back where
// the liquid carried this point, for the fine grain inside a ribbon.)
vec3 ribbons(vec2 s, float t, float much) {
  vec2 q = fold(s * 1.3 + vec2(t * 0.06, 0.0), t, much);
  return vec3(sin(q.y * 3.0 + 0.6 * sin(q.x * 1.1 + t * 0.17)), q);
}

void main() {
  vec2 p = (gl_FragCoord.xy - 0.5 * uRes) / min(uRes.x, uRes.y);
  float t = uT;
  float ang = atan(p.y, p.x);
  float r = length(p);

  // The edge of the drop: almost a circle at rest, and it ripples the louder the voice.
  float wave = 0.55 * sin(2.0 * ang + t * 0.7 + 4.0) + 0.40 * sin(3.0 * ang - t * 1.1) + 0.16 * sin(5.0 * ang + t * 1.7 + 1.3);
  float R = uSize * (1.0 + 0.07 * uLevel) * (0.62 + 0.38 * uOpen);
  float edge = R * (1.0 + wave * (0.003 + 0.008 * uTurb + 0.030 * uLevel));
  float k = min(r / edge, 1.0);

  // The glass: a ball, seen through its own curve, so what's inside bends toward the rim.
  float z = sqrt(1.0 - k * k);
  vec3 n = vec3(p / edge, z);
  vec2 s = n.xy * (1.0 + 0.9 * (1.0 - z));

  // Thinking winds the ribbons into a spiral, tightest at the middle.
  float turn = uSwirl * (3.2 * pow(1.0 - k, 1.4) + 0.05 * t);
  s = mat2(cos(turn), -sin(turn), sin(turn), cos(turn)) * s;

  // Listening opens the middle: the liquid draws back into a ring.
  float hole = uHollow * (1.0 - smoothstep(0.36, 0.74, k * (1.0 + 0.04 * sin(3.0 * ang - t * 1.3) + 0.10 * uLevel)));

  // Two sheets of ribbons: the near side of the ball, and the far side seen through it, turning the other way.
  float much = 0.55 + uTurb + 0.5 * uLevel + 1.4 * (1.0 - uOpen);
  float lift = 0.30 * uLevel - 0.15 - 2.2 * hole;   // a louder voice puts more light in it
  vec3 carried = ribbons(s, t, much);
  float near = carried.x + lift;
  float far = ribbons(vec2(-s.x, s.y) * 0.84 + vec2(3.1, 1.7), t * 0.83 + 11.0, much).x + lift - 0.2;
  float silk = 0.5 + 0.5 * sin(carried.z * 9.0 + carried.y * 2.0);            // fine streaks along a ribbon
  float warm = 0.30 + 0.70 * smoothstep(-0.6, 0.6, sin(carried.y * 1.2 + 0.7));   // the second color comes and goes

  // Glass splits light a little, most near the rim, so each ribbon has a faint edge of color.
  vec3 split = (0.02 + 0.16 * k * k) * uIri * vec3(1.0, 0.0, -1.0);
  vec3 body = smoothstep(-0.12, 0.20, near + split);
  vec3 heart = smoothstep(0.40, 0.82, near + split);
  float skirt = smoothstep(-0.62, -0.22, near);
  vec3 behind = smoothstep(-0.05, 0.35, far + 0.6 * split);

  vec3 col = uDeep;
  col = mix(col, uDeep + 0.45 * uMid, 0.75 * behind);
  col = mix(col, 0.82 * uGlint, 0.78 * skirt * warm);
  col = mix(col, uMid, body);
  col = mix(col, uLite, heart * (0.78 + 0.22 * silk));

  // Light on the glass: a lamp up and to the left, a bright rim that splits into colors, one hard glint and a
  // soft sheen, and the warm spot a glass ball throws on its far side.
  vec3 lamp = normalize(vec3(-0.48, 0.62, 0.62));
  vec3 half_ = normalize(lamp + vec3(0.0, 0.0, 1.0));
  float lit = max(dot(n, lamp), 0.0);
  float shine = max(dot(n, half_), 0.0);
  float rim = pow(1.0 - z, 2.4);
  float clear = 1.0 - 0.8 * hole;
  col *= 0.58 + 0.55 * lit;
  col += uLite * rim * 0.42;
  vec3 prism = 0.5 + 0.5 * cos(6.2831 * (k * 1.4 + ang * 0.159155 + t * 0.02 + vec3(0.0, 0.33, 0.67)));
  col += prism * rim * uIri * 0.9;
  col += (vec3(1.0) * (pow(shine, 90.0) * 0.85 + pow(shine, 9.0) * 0.10) + uGlint * pow(max(dot(n, normalize(vec3(0.50, -0.62, 0.60))), 0.0), 7.0) * 0.22) * clear;
  col += uLite * exp(-k * k * 4.0) * uLevel * 0.35 * (1.0 - uHollow);   // its own voice lights it from the middle
  col *= uBright;

  // Where the drop is, and the glow it throws around itself: brighter, and in rays, with the voice.
  float soft = 1.5 / min(uRes.x, uRes.y);
  float inside = 1.0 - smoothstep(edge - soft, edge + soft, r);
  float glass = inside * (1.0 - 0.86 * hole);
  float away = max(r - edge, 0.0);
  float ray = 0.5 + 0.5 * sin(7.0 * ang + t * 0.8 + 2.0 * sin(3.0 * ang - t * 0.5));
  float halo = exp(-away * (20.0 - 9.0 * uLevel)) * (0.10 + 0.50 * uLevel) * (1.0 + 1.2 * uLevel * ray * ray) + exp(-away * 5.5) * 0.05;
  halo *= 1.0 - smoothstep(0.34, 0.5, r);   // the glow is gone before the edge of its box, so the box never shows
  vec3 rgb = col * glass + mix(uMid, uLite, 0.55) * halo * (1.0 - inside);
  float alpha = clamp(glass + halo * (1.0 - inside), 0.0, 1.0);
  gl_FragColor = vec4(rgb, alpha) * uOpen;
}`;

  const calm = () => { try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (_) { return false; } };
  const mix = (a, b, k) => a + (b - a) * k;

  function program(gl) {
    const make = (type, source) => {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader) || "shader");
      return shader;
    };
    const prog = gl.createProgram();
    gl.attachShader(prog, make(gl.VERTEX_SHADER, VERTEX));
    gl.attachShader(prog, make(gl.FRAGMENT_SHADER, FRAGMENT));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog) || "link");
    gl.useProgram(prog);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const at = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(at);
    gl.vertexAttribPointer(at, 2, gl.FLOAT, false, 0, 0);
    const where = {};
    for (const name of UNIFORMS) where[name] = gl.getUniformLocation(prog, name);
    return where;
  }

  // A painter draws one frame of the orb onto a canvas: the shader when the device can, plain shapes when it can't.
  function painter(canvas, plain) {
    let gl = null, where = null, lost = false;
    if (!plain) {
      try {
        gl = canvas.getContext("webgl", { alpha: true, premultipliedAlpha: true, antialias: false, powerPreference: "low-power" });
        if (gl) where = program(gl);
      } catch (_) { gl = null; }
    }
    if (gl && where) {
      // A browser may take the drawing surface away (too many at once, or the computer slept). It comes back.
      canvas.addEventListener("webglcontextlost", (event) => { event.preventDefault(); lost = true; });
      canvas.addEventListener("webglcontextrestored", () => { try { where = program(gl); lost = false; } catch (_) { /* stays blank */ } });
      return {
        liquid: true,
        draw(now, w, h) {
          if (lost) return;
          w = w || canvas.width;
          h = h || canvas.height;
          gl.viewport(0, 0, w, h);
          gl.clearColor(0, 0, 0, 0);
          gl.clear(gl.COLOR_BUFFER_BIT);
          gl.uniform2f(where.uRes, w, h);
          gl.uniform1f(where.uT, now.t);
          gl.uniform1f(where.uLevel, now.level);
          gl.uniform1f(where.uTurb, now.turb + 0.5 * (now.kick || 0));
          gl.uniform1f(where.uSwirl, now.swirl);
          gl.uniform1f(where.uHollow, now.hollow);
          gl.uniform1f(where.uBright, now.bright);
          gl.uniform1f(where.uIri, now.iri);
          gl.uniform1f(where.uOpen, now.open);
          gl.uniform1f(where.uSize, now.size);
          gl.uniform3fv(where.uDeep, now.deep);
          gl.uniform3fv(where.uMid, now.mid);
          gl.uniform3fv(where.uLite, now.lite);
          gl.uniform3fv(where.uGlint, now.glint);
          gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        },
        lose() { try { gl.getExtension("WEBGL_lose_context")?.loseContext(); } catch (_) { /* already gone */ } },
      };
    }
    const g = canvas.getContext("2d");
    const css = (c, a) => `rgba(${Math.round(255 * Math.min(1, c[0]))},${Math.round(255 * Math.min(1, c[1]))},${Math.round(255 * Math.min(1, c[2]))},${a})`;
    return {
      liquid: false,
      draw(now) {
        const W = canvas.width, H = canvas.height, m = Math.min(W, H), cx = W / 2, cy = H / 2;
        const R = m * now.size * (1 + 0.07 * now.level) * (0.62 + 0.38 * now.open);
        g.clearRect(0, 0, W, H);
        g.globalAlpha = now.open;
        const halo = g.createRadialGradient(cx, cy, R * 0.9, cx, cy, R * (1.35 + 0.6 * now.level));
        halo.addColorStop(0, css(now.lite, 0.14 + 0.4 * now.level));
        halo.addColorStop(1, css(now.mid, 0));
        g.fillStyle = halo;
        g.fillRect(0, 0, W, H);
        g.save();
        g.beginPath();
        g.arc(cx, cy, R, 0, Math.PI * 2);
        g.clip();
        const open = now.hollow;
        const body = g.createRadialGradient(cx, cy, R * 0.3, cx, cy, R);
        body.addColorStop(0, css(now.deep, 1 - 0.86 * open));
        body.addColorStop(0.62, css(now.deep, 1 - 0.5 * open));
        body.addColorStop(1, css(now.deep, 1));
        g.fillStyle = body;
        g.fillRect(cx - R, cy - R, R * 2, R * 2);
        g.lineCap = "round";
        for (let i = 0; i < 3; i++) {   // three slow ribbons, so it still drifts
          const y = cy + R * (-0.5 + 0.5 * i) + R * 0.1 * Math.sin(now.t * (0.5 + 0.13 * i) + i * 2.1);
          const bend = R * (0.34 - 0.3 * i) + R * 0.16 * Math.sin(now.t * 0.4 + i * 1.3);
          for (const [wide, color] of [[0.30, css(now.mid, 0.55 * (1 - 0.7 * open))], [0.12, css(now.lite, 0.9 * (1 - 0.7 * open))]]) {
            g.strokeStyle = color;
            g.lineWidth = R * wide * (1 + 0.5 * now.level);
            g.beginPath();
            g.moveTo(cx - R * 1.1, y + bend);
            g.bezierCurveTo(cx - R * 0.4, y - bend, cx + R * 0.4, y + bend, cx + R * 1.1, y - bend);
            g.stroke();
          }
        }
        const rim = g.createRadialGradient(cx, cy, R * 0.72, cx, cy, R);
        rim.addColorStop(0, css(now.lite, 0));
        rim.addColorStop(1, css(now.lite, 0.5 + 0.3 * open));
        g.fillStyle = rim;
        g.fillRect(cx - R, cy - R, R * 2, R * 2);
        const shine = g.createRadialGradient(cx - R * 0.42, cy - R * 0.5, 0, cx - R * 0.42, cy - R * 0.5, R * 0.5);
        shine.addColorStop(0, "rgba(255,255,255,0.75)");
        shine.addColorStop(1, "rgba(255,255,255,0)");
        g.fillStyle = shine;
        g.fillRect(cx - R, cy - R, R * 2, R * 2);
        g.restore();
        g.globalAlpha = 1;
      },
      lose() {},
    };
  }

  // The small orbs (the one beside "Thinking", the stills) share one hidden drawing surface: each is drawn there and
  // copied to its own little canvas. However many there are, they cost one WebGL context between them.
  const SHARED = 512;
  let common = null;
  function copier(canvas, plain) {
    if (!common && !plain) {
      const surface = document.createElement("canvas");
      surface.width = surface.height = SHARED;
      common = { surface, paint: painter(surface) };
    }
    if (plain || !common.paint.liquid || canvas.width > SHARED || canvas.height > SHARED) return painter(canvas, true);
    const g = canvas.getContext("2d");
    return {
      liquid: true,
      draw(now) {
        const w = Math.min(canvas.width, SHARED), h = Math.min(canvas.height, SHARED);
        common.paint.draw(now, w, h);
        g.clearRect(0, 0, canvas.width, canvas.height);
        g.drawImage(common.surface, 0, SHARED - h, w, h, 0, 0, w, h);   // WebGL counts rows from the bottom
      },
      lose() {},
    };
  }

  function look(mood, size) {
    const from = MOODS[mood] || MOODS.idle;
    const now = { t: 0, level: 0, open: 1, kick: 0, size: size || 0.30 };
    for (const key of NUMBERS) now[key] = from[key];
    for (const key of COLORS) now[key] = from[key].slice();
    return now;
  }

  // A live orb inside `host`. It fills the host, keeps itself sharp on any screen, rests when it can't be seen, and
  // cleans up after itself when its host leaves the page.
  // Options: mood (where it starts); size (the ball's radius as a share of the smaller side: 0.30 leaves room for
  // its glow, 0.47 is nearly all ball); small (true for little ones, which share one drawing surface); most (the
  // most pixels across it will ever draw); plain (never use the shader).
  function mount(host, options) {
    options = options || {};
    const canvas = document.createElement("canvas");
    canvas.className = "luma-orb";
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.display = "block";
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    host.appendChild(canvas);
    const paint = options.small ? copier(canvas, options.plain) : painter(canvas, options.plain);
    let mood = MOODS[options.mood] ? options.mood : "idle";
    const now = look(mood, options.size);
    now.open = 0;
    now.kick = 1;   // it arrives already moving, and settles
    let want = 1, loud = 0, frame = 0, last = 0, seen = true, gone = false, placed = false, waited = 0;
    const pace = options.small ? 30 : 0;   // a little orb is redrawn about 30 times a second: at that size nobody can tell, and it's half the work

    function size() {
      const box = host.getBoundingClientRect();
      const scale = Math.min(window.devicePixelRatio || 1, 2);
      const most = options.small ? Math.min(options.most || SHARED, SHARED) : options.most || 900;   // a big screen doesn't need more than this to look liquid
      const w = Math.max(16, Math.min(most, Math.round(box.width * scale))), h = Math.max(16, Math.min(most, Math.round(box.height * scale)));
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    }
    function step(time) {
      frame = 0;
      if (gone) return;
      if (!canvas.isConnected) {
        // Not on the page: either its host hasn't been put there yet (wait a little), or it's been taken away.
        if (placed || ++waited > 600) { stop(); return; }
        frame = requestAnimationFrame(step);
        return;
      }
      placed = true;
      if (pace && last && time - last < pace) { frame = requestAnimationFrame(step); return; }
      const dt = Math.min(0.05, last ? (time - last) / 1000 : 0.016);
      last = time;
      const to = MOODS[mood];
      const ease = 1 - Math.pow(0.03, dt);          // moods pour into each other over about a second
      for (const key of NUMBERS) now[key] = mix(now[key], to[key], ease);
      for (const key of COLORS) for (let i = 0; i < 3; i++) now[key][i] = mix(now[key][i], to[key][i], ease);
      now.level = mix(now.level, loud, loud > now.level ? 1 - Math.pow(0.0005, dt) : 1 - Math.pow(0.08, dt));   // quick to rise, slow to settle
      now.open = mix(now.open, want, 1 - Math.pow(0.01, dt));
      now.kick = mix(now.kick, 0, 1 - Math.pow(0.05, dt));   // a change of mood stirs it, and it settles
      if (!calm()) now.t += dt * (now.flow + 0.9 * now.level + 1.5 * now.kick);
      size();
      paint.draw(now);
      if (want === 0 && now.open < 0.01) { stop(); return; }
      const settled = calm() && Math.abs(now.open - want) < 0.01 && Math.abs(now.level - loud) < 0.01 && NUMBERS.every((key) => Math.abs(now[key] - to[key]) < 0.01);
      if (seen && !document.hidden && !settled) frame = requestAnimationFrame(step);
    }
    function wake() { if (!frame && !gone) { last = 0; frame = requestAnimationFrame(step); } }
    function stop() {
      if (gone) return;
      gone = true;
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      watcher?.disconnect();
      document.removeEventListener("visibilitychange", wake);
      paint.lose();
      canvas.remove();
    }
    let watcher = null;
    try {
      watcher = new IntersectionObserver((entries) => {
        if (placed && !canvas.isConnected) { stop(); return; }
        seen = entries.some((entry) => entry.isIntersecting);
        if (seen) wake();
      });
      watcher.observe(host);
    } catch (_) { /* an old browser: it just keeps running */ }
    document.addEventListener("visibilitychange", wake);
    wake();
    return {
      canvas,
      liquid: paint.liquid,
      get mood() { return mood; },
      get gone() { return gone; },
      get closing() { return want === 0 && !gone; },
      set(next, level) {
        if (MOODS[next] && next !== mood) { mood = next; now.kick = Math.max(now.kick, 0.8); }
        if (typeof level === "number" && isFinite(level)) loud = Math.max(0, Math.min(1, level));
        wake();
      },
      stir() { now.kick = 1; wake(); },
      open() { want = 1; now.kick = Math.max(now.kick, 0.6); wake(); },
      close() { want = 0; wake(); },
      stop,
    };
  }

  // One still picture of the orb, as a data URL: for places where a live one would be wasted. Made once for each
  // mood and size and kept.
  const kept = {};
  const MOMENT = 9;   // the moment the logo was taken at; every still starts from it, so they all match
  function still(pixels, mood, moment) {
    const key = `${pixels}:${mood}:${moment || 0}`;
    if (kept[key] !== undefined) return kept[key];
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = Math.max(16, Math.min(1024, Math.round(pixels)));
    const big = canvas.width > SHARED;   // a big one (an app icon) gets a drawing surface of its own, for as long as it takes
    const paint = big ? painter(canvas) : copier(canvas);
    const now = look(mood, 0.47);   // a still is nearly all ball: there's no room for a glow in a small place
    now.t = MOMENT + (moment || 0);
    paint.draw(now);
    let url = "";
    try { url = canvas.toDataURL("image/png"); } catch (_) { url = ""; }
    if (big) paint.lose();
    kept[key] = url;
    return url;
  }

  // Whether this page can draw the liquid (the shader), or only the simpler orb.
  function liquid() {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 16;
    return copier(canvas).liquid;
  }

  window.LumaOrb = { mount, still, liquid, moods: Object.keys(MOODS) };
})();
