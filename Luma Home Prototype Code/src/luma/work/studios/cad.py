"""3D and CAD: models built from parts, as OpenSCAD, a Blender script, STL/OBJ meshes and a viewer.

Parts are boxes, cylinders, spheres and cones, sized and placed in millimetres; parts marked `cut`
are holes taken out of the rest. From one parts list this writes a parametric OpenSCAD file, a Blender
Python script that builds the model with materials and can render it, STL and OBJ meshes (for 3D
printing and any 3D app), and a viewer page you can spin around. If OpenSCAD or Blender is installed
they're run to prove the files work; the scripts are generated from checked numbers, never free text.
"""
from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

from luma.work.studios.base import Result, Studio, check, esc, hex_color, slug, text

SHAPES = ("box", "cylinder", "sphere", "cone")
OPENSCAD = ["openscad", "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"]
BLENDER = ["blender", "/Applications/Blender.app/Contents/MacOS/Blender"]


def tool(candidates):
    for c in candidates:
        found = shutil.which(c) or (c if Path(c).exists() else None)
        if found:
            return found
    return None


def clean_parts(raw):
    parts = []
    for i, p in enumerate((raw or [])[:24]):
        if not isinstance(p, dict) or p.get("shape") not in SHAPES:
            continue
        size = [float(v) for v in (p.get("size") or [])[:3] if isinstance(v, (int, float)) and not isinstance(v, bool)]
        at = [float(v) for v in (p.get("at") or [0, 0, 0])[:3] if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if len(size) != 3 or len(at) != 3:
            raise ValueError(f"Part {i + 1} needs a size and a position, each three numbers.")
        if p["shape"] in {"cylinder", "sphere"}:
            size[1] = size[0]
        if p["shape"] == "sphere":
            size[2] = size[0]
        if any(not (0 < v <= 10000) for v in (size if p["shape"] != "cone" else [size[0], size[2]])) or (p["shape"] == "cone" and not 0 <= size[1] <= 10000):
            raise ValueError(f"Part {i + 1} ({text(p.get('name'), 40)}) has a size that isn't between 0 and 10 metres.")
        if any(abs(v) > 10000 for v in at):
            raise ValueError(f"Part {i + 1} is placed more than 10 metres away.")
        parts.append({"name": text(p.get("name"), 40) or f"part {i + 1}", "shape": p["shape"], "size": size, "at": at,
                      "color": hex_color(p.get("color"), "#8E8AA8"), "cut": bool(p.get("cut"))})
    if not any(not p["cut"] for p in parts):
        raise ValueError("A model needs at least one solid part.")
    return parts


def scad(name, parts):
    def one(p):
        x, y, z = p["at"]
        sx, sy, sz = p["size"]
        body = {"box": f"cube([{sx}, {sy}, {sz}], center=true);", "cylinder": f"cylinder(h={sz}, d={sx}, center=true, $fn=96);",
                "sphere": f"sphere(d={sx}, $fn=96);", "cone": f"cylinder(h={sz}, d1={sx}, d2={sy}, center=true, $fn=96);"}[p["shape"]]
        return f'    // {p["name"]}\n    translate([{x}, {y}, {z}]) color("{p["color"]}") {body}'
    solids, cuts = [one(p) for p in parts if not p["cut"]], [one(p) for p in parts if p["cut"]]
    out = [f"// {name}, built by Luma. Units: millimetres. Change any number and press F5 (preview) or F6 (render).", "difference() {", "  union() {"]
    out += ["  " + s for s in solids] + ["  }"] + ["  " + c for c in cuts] + ["}"]
    return "\n".join(out) + "\n"


def blender_script(name, parts):
    rows = ",\n    ".join(repr((p["name"], p["shape"], p["size"], p["at"], p["color"], p["cut"])) for p in parts)
    return f'''"""{name}, built by Luma. In Blender: Scripting tab > Open > Run Script. From a terminal:
    blender --background --python this_file.py -- --render preview.png
Units are millimetres (the scene is scaled to metres)."""
import sys
import bpy
from mathutils import Vector

PARTS = [
    {rows}
]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
solids, cuts = [], []
for name, shape, size, at, color, cut in PARTS:
    loc = tuple(v / 1000 for v in at)
    sx, sy, sz = (v / 1000 for v in size)
    if shape == "box":
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        bpy.context.object.scale = (sx, sy, sz)
    elif shape == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=sx / 2, depth=sz, location=loc)
    elif shape == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=sx / 2, location=loc)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=sx / 2, radius2=sy / 2, depth=sz, location=loc)
    obj = bpy.context.object
    obj.name = name
    mat = bpy.data.materials.new(name + " material")
    mat.diffuse_color = tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)) + (1.0,)
    obj.data.materials.append(mat)
    (cuts if cut else solids).append(obj)

if solids:
    base = solids[0]
    for other in solids[1:] + cuts:
        mod = base.modifiers.new(name="join " + other.name, type="BOOLEAN")
        mod.operation = "DIFFERENCE" if other in cuts else "UNION"
        mod.object = other
        other.hide_render = True
        other.display_type = "WIRE"

span = max(max(abs(a) + s / 2 for a, s in zip(at, size)) for _, _, size, at, _, _ in PARTS) / 1000
d = max(span, 0.01) * 3.2
bpy.ops.object.camera_add(location=(d, -d, d * 0.8))
cam = bpy.context.object
cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam
bpy.ops.object.light_add(type="SUN", location=(0, 0, 1))
bpy.context.object.data.energy = 4

if "--render" in sys.argv:
    out = sys.argv[sys.argv.index("--render") + 1]
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 1200, 900
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
'''


def mesh(p, segments=48):
    """Triangles for one part, centered at its position."""
    sx, sy, sz = p["size"]
    cx, cy, cz = p["at"]
    tris = []
    if p["shape"] == "box":
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        v = [(cx + x * hx, cy + y * hy, cz + z * hz) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        for a, b, c, d in faces:
            tris += [(v[a], v[b], v[c]), (v[a], v[c], v[d])]
    elif p["shape"] in {"cylinder", "cone"}:
        r0, r1, h = sx / 2, (sx if p["shape"] == "cylinder" else sy) / 2, sz / 2
        ring = lambda r, z: [(cx + r * math.cos(2 * math.pi * i / segments), cy + r * math.sin(2 * math.pi * i / segments), cz + z) for i in range(segments)]
        bottom, top = ring(r0, -h), ring(r1, h)
        for i in range(segments):
            j = (i + 1) % segments
            tris += [(bottom[i], bottom[j], top[j]), (bottom[i], top[j], top[i])]
            tris.append(((cx, cy, cz - h), bottom[j], bottom[i]))
            tris.append(((cx, cy, cz + h), top[i], top[j]))
    else:
        r, rings = sx / 2, segments // 2
        pt = lambda a, b: (cx + r * math.sin(a) * math.cos(b), cy + r * math.sin(a) * math.sin(b), cz + r * math.cos(a))
        for i in range(rings):
            a0, a1 = math.pi * i / rings, math.pi * (i + 1) / rings
            for j in range(segments):
                b0, b1 = 2 * math.pi * j / segments, 2 * math.pi * (j + 1) / segments
                if i:
                    tris.append((pt(a0, b0), pt(a1, b0), pt(a0, b1)))
                if i < rings - 1:
                    tris.append((pt(a0, b1), pt(a1, b0), pt(a1, b1)))
    return tris


def normal(t):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz, vx, vy, vz = bx - ax, by - ay, bz - az, cx - ax, cy - ay, cz - az
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    length = math.sqrt(sum(c * c for c in n)) or 1
    return tuple(c / length for c in n)


VIEWER = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>html,body{{margin:0;height:100%;background:radial-gradient(circle at 30% 20%,#2a2547,#0e0c16);color:#eee;font-family:system-ui,sans-serif;overflow:hidden}}
canvas{{display:block;touch-action:none}}.tag{{position:fixed;left:18px;top:16px;background:rgba(0,0,0,.35);padding:8px 14px;border-radius:14px;font-size:14px}}</style></head>
<body><canvas id="c" aria-label="{title} in 3D"></canvas><div class="tag">{title} · drag to turn · scroll to zoom</div><script>
const PARTS = {parts};
const cv = document.getElementById('c'), g = cv.getContext('2d'); let W, H; const fit = () => {{ W = cv.width = innerWidth; H = cv.height = innerHeight; }}; addEventListener('resize', fit); fit();
let yaw = 0.7, pitch = 0.5, zoom = 1, drag = null;
cv.addEventListener('pointerdown', e => drag = [e.clientX, e.clientY]); addEventListener('pointerup', () => drag = null);
addEventListener('pointermove', e => {{ if (!drag) return; yaw += (e.clientX - drag[0]) * 0.01; pitch = Math.max(-1.4, Math.min(1.4, pitch + (e.clientY - drag[1]) * 0.01)); drag = [e.clientX, e.clientY]; }});
addEventListener('wheel', e => {{ zoom = Math.max(0.3, Math.min(4, zoom * (e.deltaY > 0 ? 0.9 : 1.1))); }});
const all = PARTS.flatMap(p => p.tris.map(t => ({{t, color: p.color, cut: p.cut}})));
let span = 1; for (const {{t}} of all) for (const v of t) span = Math.max(span, Math.abs(v[0]), Math.abs(v[1]), Math.abs(v[2]));
function draw() {{
  g.clearRect(0, 0, W, H); const s = Math.min(W, H) * 0.38 * zoom / span, cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
  const proj = v => {{ const x = v[0] * cy - v[1] * sy, y = v[0] * sy + v[1] * cy, z = v[2]; const y2 = y * cp - z * sp, z2 = y * sp + z * cp; return [W / 2 + x * s, H / 2 - z2 * s, y2, x, z2]; }};
  const faces = all.map(f => {{ const p = f.t.map(proj); return {{p, d: (p[0][2] + p[1][2] + p[2][2]) / 3, f}}; }}).sort((a, b) => b.d - a.d);
  for (const {{p, f}} of faces) {{
    const ax = p[1][0] - p[0][0], ay = p[1][1] - p[0][1], bx = p[2][0] - p[0][0], by = p[2][1] - p[0][1]; const facing = ax * by - ay * bx;
    if (f.cut) {{ g.strokeStyle = 'rgba(255,90,90,.35)'; g.beginPath(); g.moveTo(p[0][0], p[0][1]); g.lineTo(p[1][0], p[1][1]); g.lineTo(p[2][0], p[2][1]); g.closePath(); g.stroke(); continue; }}
    if (facing > 0) continue;
    // Light from the surface's real direction (so both triangles of a face match), from the upper left, toward the viewer.
    const ux = p[1][3] - p[0][3], uy = p[1][2] - p[0][2], uz = p[1][4] - p[0][4], vx = p[2][3] - p[0][3], vy = p[2][2] - p[0][2], vz = p[2][4] - p[0][4];
    let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; const nl = Math.hypot(nx, ny, nz) || 1; nx /= nl; ny /= nl; nz /= nl;
    const light = 0.38 + 0.62 * Math.abs(nx * -0.45 + ny * -0.55 + nz * 0.7);
    const c = f.color, r = parseInt(c.slice(1, 3), 16) * light, gg = parseInt(c.slice(3, 5), 16) * light, b = parseInt(c.slice(5, 7), 16) * light;
    g.fillStyle = g.strokeStyle = `rgb(${{r|0}},${{gg|0}},${{b|0}})`; g.lineWidth = 0.8; g.beginPath(); g.moveTo(p[0][0], p[0][1]); g.lineTo(p[1][0], p[1][1]); g.lineTo(p[2][0], p[2][1]); g.closePath(); g.fill(); g.stroke();
  }}
  requestAnimationFrame(draw);
}}
draw(); window.__model = {{ triangles: all.length }};
</script></body></html>"""


class Model3D(Studio):
    name, agent, title = "model3d", "design", "3D model"
    description = ("Design a 3D model from parts, in millimetres, centered near 0,0,0. Each part: name, shape (box, cylinder, sphere, cone), size [x, y, z] "
                   "(box: width, depth, height; cylinder: [diameter, diameter, height]; sphere: [diameter, diameter, diameter]; cone: [bottom diameter, top diameter, height]), "
                   "at [x, y, z] its center, color (hex), cut true for holes taken out of the solid parts. Make parts touch or overlap so the model is one piece.")
    fields = {"name": "string", "units": "text", "parts": "parts", "notes": "text"}

    def make(self, ctx, args):
        name = text(args.get("name"), 60) or "Model"
        parts = clean_parts(args.get("parts"))
        folder = f"model/{slug(name, 'model')}"
        stem = f"{folder}/{slug(name, 'model')}"
        ctx.write(stem + ".scad", scad(name, parts))
        ctx.write(stem + "-blender.py", blender_script(name, parts))
        solid_tris = [t for p in parts if not p["cut"] for t in mesh(p)]
        stl = ["solid luma"] + [f"facet normal {' '.join(f'{c:.5f}' for c in normal(t))}\n outer loop\n" + "".join(f"  vertex {x:.4f} {y:.4f} {z:.4f}\n" for x, y, z in t) + " endloop\nendfacet" for t in solid_tris] + ["endsolid luma"]
        ctx.write(stem + ".stl", "\n".join(stl) + "\n")
        obj, offset = [f"# {name}, built by Luma (millimetres)"], 1
        for p in parts:
            if p["cut"]:
                continue
            tris = mesh(p)
            obj.append(f"o {p['name'].replace(' ', '_')}")
            for t in tris:
                obj += [f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in t]
            obj += [f"f {offset + 3 * i} {offset + 3 * i + 1} {offset + 3 * i + 2}" for i in range(len(tris))]
            offset += 3 * len(tris)
        ctx.write(stem + ".obj", "\n".join(obj) + "\n")
        viewer_parts = [{"color": p["color"], "cut": p["cut"], "tris": [[[round(c, 2) for c in v] for v in t] for t in mesh(p, 24)]} for p in parts]
        import json
        ctx.write(f"{folder}/viewer.html", VIEWER.format(title=esc(name), parts=json.dumps(viewer_parts)))
        files = [stem + ".scad", stem + "-blender.py", stem + ".stl", stem + ".obj", f"{folder}/viewer.html"]
        renders = {}
        openscad = tool(OPENSCAD)
        if openscad:
            renders["openscad"] = self.external([openscad, "-o", str(ctx.path(stem + "-openscad.stl")), str(ctx.path(stem + ".scad"))], ctx.path(stem + "-openscad.stl"))
            if renders["openscad"]["ok"]:
                files.append(stem + "-openscad.stl")
        blender = tool(BLENDER)
        if blender:
            renders["blender"] = self.external([blender, "--background", "--factory-startup", "--python", str(ctx.path(stem + "-blender.py")), "--", "--render", str(ctx.path(stem + "-render.png"))],
                                               ctx.path(stem + "-render.png"), timeout=300)
            if renders["blender"]["ok"]:
                files.append(stem + "-render.png")
        lo = [min(p["at"][i] - p["size"][i] / 2 for p in parts if not p["cut"]) for i in range(3)]
        hi = [max(p["at"][i] + p["size"][i] / 2 for p in parts if not p["cut"]) for i in range(3)]
        size = [round(h - l, 1) for l, h in zip(lo, hi)]
        return Result(files=files, summary=f"{name}: {len(parts)} parts, about {size[0]} × {size[1]} × {size[2]} mm. Open {folder}/viewer.html to spin it, the .stl to 3D print, "
                                           f"the .scad in OpenSCAD or the Blender script in Blender.",
                      data={"name": name, "parts": len(parts), "size_mm": size, "triangles": len(solid_tris), "renders": renders, "folder": folder})

    @staticmethod
    def external(argv, output, timeout=120):
        """OpenSCAD or Blender, run on a script Luma generated from checked numbers (no network needed)."""
        try:
            done = subprocess.run(argv, capture_output=True, timeout=timeout)
            return {"ok": done.returncode == 0 and Path(output).exists() and Path(output).stat().st_size > 0, "log": (done.stderr or b"")[-600:].decode("utf-8", "replace")}
        except (OSError, subprocess.TimeoutExpired) as error:
            return {"ok": False, "log": str(error)[:300]}

    def check(self, ctx, result):
        d = result.data
        out = [check("mesh has triangles", d["triangles"] > 0, "The mesh came out empty."),
               check("sensible size", all(0 < s <= 20000 for s in d["size_mm"]), f"Size {d['size_mm']} mm looks wrong.")]
        try:
            compile(ctx.read_text(next(f for f in result.files if f.endswith("-blender.py"))), "blender.py", "exec")
            out.append(check("Blender script is valid Python", True))
        except SyntaxError as error:
            out.append(check("Blender script is valid Python", False, str(error)))
        for app, r in d.get("renders", {}).items():
            out.append(check(f"renders in {app.title()}", r["ok"], r["log"][-300:]))
        if not d.get("renders"):
            out.append(check("rendered in OpenSCAD or Blender", False, "Neither is installed here; install one to render. The STL and viewer still work.", blocking=False))
        return out
