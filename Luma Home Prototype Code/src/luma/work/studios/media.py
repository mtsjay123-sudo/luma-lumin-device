"""Graphics: a brand's logo, app icon, social posts, banners, a phone mockup and a palette sheet.

Every asset is an SVG drawn from the brand's name, tagline and colors (sharp at any size, editable in
Figma, Illustrator or a browser), plus a PNG when a browser is available to render it. Text colors are
chosen for contrast and checked against the accessibility standard (4.5 to 1) before anything is saved.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from luma.work.studios.base import Result, Studio, check, contrast, esc, hex_color, on_color, readable_on, shade, slug, text

SIZES = {"logo": (960, 320), "icon": (1024, 1024), "social": (1080, 1080), "banner": (1500, 500), "story": (1080, 1920), "mockup": (1200, 1400), "palette": (1200, 640)}
FONT = "font-family=\"'Inter','Helvetica Neue',Helvetica,Arial,sans-serif\""


def initials(name):
    words = [w for w in re.split(r"[\s\-_]+", name) if w]
    return ("".join(w[0] for w in words[:2]) or "L").upper()


def brand_colors(primary, accent):
    p, a = hex_color(primary, "#6E56CF"), hex_color(accent, "#12A594")
    if contrast(p, a) < 1.4:  # too alike to tell apart: push the accent away
        a = shade(a, 0.45) if sum(int(p[i:i + 2], 16) for i in (1, 3, 5)) < 380 else shade(a, -0.45)
    return p, a


def mark(x, y, size, primary, accent, letters):
    """The brand mark: a rounded square in the brand color with the initials (flat: no gradient, no glow)."""
    r = size * 0.24
    primary, fg = on_color(primary)
    return (f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="{r}" fill="{primary}"/>'
            f'<circle cx="{x + size * 0.78}" cy="{y + size * 0.22}" r="{size * 0.1}" fill="{accent}"/>'
            f'<text x="{x + size / 2}" y="{y + size * 0.64}" text-anchor="middle" font-size="{size * (0.42 if len(letters) > 1 else 0.5)}" font-weight="800" fill="{fg}" {FONT}>{esc(letters)}</text>')


def wrap(words, limit):
    lines, line = [], ""
    for word in words.split():
        if len(line) + len(word) + 1 > limit and line:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    return lines + ([line] if line else [])


def svg(kind, brand, tagline, primary, accent, points=(), action=""):
    w, h = SIZES[kind]
    letters, dark = initials(brand), "#14121F"
    head = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
    if kind == "logo":
        body = mark(32, 32, 256, primary, accent, letters) + f'<text x="330" y="190" font-size="120" font-weight="800" fill="{dark}" {FONT}>{esc(brand[:16])}</text>'
        if tagline:
            body += f'<text x="334" y="250" font-size="34" fill="#55526B" {FONT}>{esc(tagline[:48])}</text>'
    elif kind == "icon":
        body = mark(0, 0, 1024, primary, accent, letters)
    elif kind in {"social", "story", "banner"}:
        primary, fg = on_color(primary)
        size = {"social": 92, "story": 104, "banner": 72}[kind]
        lines = wrap(tagline or brand, {"social": 18, "story": 16, "banner": 30}[kind])[:4]
        top = {"social": 420, "story": 820, "banner": 210}[kind] - (len(lines) - 1) * size * 0.55
        big = min(w, h) * 0.62  # the initials, cropped off the edge: the brand's own shape instead of decoration
        body = (f'<rect width="{w}" height="{h}" fill="{primary}"/>'
                f'<text x="{w * 1.02}" y="{h * 0.36}" text-anchor="end" font-size="{big}" font-weight="800" fill="{fg}" opacity="0.1" {FONT}>{esc(letters)}</text>'
                f'<rect x="0" y="{h * 0.86}" width="{w}" height="{h * 0.14}" fill="{accent}"/>')
        body += "".join(f'<text x="{w * 0.08}" y="{top + i * size * 1.12}" font-size="{size}" font-weight="800" fill="{fg}" {FONT}>{esc(line)}</text>' for i, line in enumerate(lines))
        body += f'<text x="{w * 0.08}" y="{h * 0.93 + min(w, h) * 0.015}" font-size="{min(w, h) * 0.045}" font-weight="800" fill="{readable_on(accent)}" {FONT}>{esc(brand[:28])}</text>'
    elif kind == "mockup":
        primary, fg = on_color(primary)
        body = (f'<rect width="{w}" height="{h}" fill="#F3F3F1"/><rect x="330" y="80" width="540" height="1140" rx="80" fill="#14121F"/>'
                f'<rect x="352" y="102" width="496" height="1096" rx="62" fill="#FFFFFF"/><rect x="352" y="102" width="496" height="300" rx="62" fill="{primary}"/>'
                f'<rect x="352" y="340" width="496" height="62" fill="{primary}"/><rect x="530" y="120" width="140" height="26" rx="13" fill="#14121F"/>'
                + mark(392, 190, 84, shade(primary, -0.3), accent, letters) +
                f'<text x="494" y="246" font-size="38" font-weight="800" fill="{fg}" {FONT}>{esc(brand[:14])}</text>'
                f'<text x="392" y="330" font-size="24" fill="{fg}" {FONT}>{esc((wrap(tagline, 30) or [brand])[0])}</text>')
        rows = [str(t).strip() for t in points if str(t).strip()][:3]
        if not rows:  # nothing real to list yet: the tagline, set big, rather than grey placeholder bars
            for j, line in enumerate(wrap(tagline or brand, 13)[:5]):
                body += f'<text x="392" y="{520 + j * 74}" font-size="62" font-weight="800" fill="{dark}" {FONT}>{esc(line)}</text>'
            body += f'<rect x="392" y="{560 + min(4, len(wrap(tagline or brand, 13)[:5])) * 74}" width="120" height="14" rx="7" fill="{accent}"/>'
        for i, row in enumerate(rows):
            y = 440 + i * 210
            first, *rest = wrap(row, 22)[:3]
            body += (f'<rect x="384" y="{y}" width="432" height="180" rx="28" fill="#F3F3F1"/><circle cx="440" cy="{y + 62}" r="26" fill="{accent if i % 2 else primary}"/>'
                     f'<text x="490" y="{y + 72}" font-size="30" font-weight="800" fill="{dark}" {FONT}>{esc(first)}</text>'
                     + "".join(f'<text x="416" y="{y + 124 + j * 34}" font-size="24" fill="#4F4D57" {FONT}>{esc(line)}</text>' for j, line in enumerate(rest)))
        label = (action or f"Open {brand}")[:22]
        body += f'<rect x="384" y="1110" width="432" height="64" rx="32" fill="{accent}"/><text x="600" y="1152" text-anchor="middle" font-size="26" font-weight="700" fill="{readable_on(accent)}" {FONT}>{esc(label)}</text>'
    else:  # palette
        swatches = [("Primary", primary), ("Primary dark", shade(primary, -0.3)), ("Accent", accent), ("Ink", dark), ("Surface", "#F3F3F1")]
        body = f'<rect width="{w}" height="{h}" fill="#FFFFFF"/><text x="60" y="90" font-size="44" font-weight="800" fill="{dark}" {FONT}>{esc(brand[:30])} colors</text>'
        for i, (label, color) in enumerate(swatches):
            x = 60 + i * 220
            fg = readable_on(color)
            body += (f'<rect x="{x}" y="140" width="200" height="300" rx="24" fill="{color}" stroke="#E6E3F1"/>'
                     f'<text x="{x + 20}" y="400" font-size="26" font-weight="700" fill="{fg}" {FONT}>{color}</text>'
                     f'<text x="{x}" y="490" font-size="24" fill="{dark}" {FONT}>{label}</text>'
                     f'<text x="{x}" y="525" font-size="20" fill="#55526B" {FONT}>text {contrast(color, fg):.1f}:1</text>')
    return head + body + "</svg>"


def render_pngs(jobs):
    """PNGs of SVGs, all drawn by one real browser: [(svg_path, png_path, (w, h))] -> how many were made."""
    made = 0
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for svg_path, png_path, size in jobs:
                page = browser.new_page(viewport={"width": size[0], "height": size[1]})
                page.goto(svg_path.resolve().as_uri())
                page.screenshot(path=str(png_path), omit_background=True)
                page.close()
                made += 1
            browser.close()
    except Exception:
        pass
    return made


class Graphics(Studio):
    name, agent, title, tier = "graphics", "design", "Graphics", "standard"
    description = ("Design brand graphics. brand: the name. tagline: one short line. primary_color and accent_color: hex like #6E56CF or a color name. "
                   "style: modern, playful, elegant or bold. assets: which to make, comma-separated, from logo, icon, social, banner, story, mockup, palette. "
                   "points: three short real lines for the app mockup, separated by ; (menu items, features, prices from the research). action: the mockup's "
                   "button label, naming the action (\"Order lunch\"), never \"Get started\". No gradients or glows.")
    fields = {"brand": "string", "tagline": "text", "primary_color": "text", "accent_color": "text", "style": "text", "assets": "text", "points": "text", "action": "text"}

    def fallback(self, ctx, task):
        name = ctx.project.get("name") or "Luma"
        return {"brand": name, "tagline": text(ctx.project.get("brief"), 60), "primary_color": "", "accent_color": "", "style": "modern", "assets": "logo, icon, social, banner, palette"}

    def make(self, ctx, args):
        brand = text(args.get("brand"), 40) or ctx.project.get("name") or "Brand"
        tagline = text(args.get("tagline"), 90)
        primary, accent = brand_colors(args.get("primary_color"), args.get("accent_color"))
        wanted = [a for a in re.split(r"[,\s]+", str(args.get("assets") or "").lower()) if a in SIZES] or ["logo", "icon", "social", "banner", "palette"]
        files, jobs, png_files = [], [], []
        for kind in dict.fromkeys(wanted):
            rel = f"graphics/{slug(brand, 'brand')}-{kind}.svg"
            ctx.write(rel, svg(kind, brand, tagline, primary, accent, [t for t in str(args.get("points") or "").split(";")], text(args.get("action"), 22)))
            files.append(rel)
            png_files.append(rel[:-4] + ".png")
            jobs.append((ctx.path(rel), ctx.path(png_files[-1]), SIZES[kind]))
        pngs = render_pngs(jobs) if ctx.can_render else 0
        files += png_files[:pngs]
        return Result(files=files, summary=f"{brand} graphics: {', '.join(dict.fromkeys(wanted))}" + (f" (SVG and PNG)" if pngs else " (SVG)") + f", colors {primary} and {accent}.",
                      data={"brand": brand, "tagline": tagline, "primary": primary, "accent": accent, "logo": next((f for f in files if f.endswith("-logo.svg")), None),
                            "icon": next((f for f in files if f.endswith("-icon.svg")), None)})

    def check(self, ctx, result):
        out = []
        for rel in result.files:
            if not rel.endswith(".svg"):
                continue
            try:
                root = ET.fromstring(ctx.read_text(rel))
                ok = root.tag.endswith("svg") and root.get("width") and root.get("height")
            except ET.ParseError as error:
                ok, error_text = False, str(error)
            out.append(check(f"{rel.rsplit('/', 1)[-1]} is valid", ok, "The SVG doesn't parse."))
        p, a = result.data["primary"], result.data["accent"]
        bg, fg = on_color(p)
        out.append(check("text is readable on the brand color", contrast(bg, fg) >= 4.5, f"Best text on {p} is only {contrast(bg, fg):.1f}:1.", blocking=False))
        out.append(check("colors are distinct", contrast(p, a) >= 1.4, "The two brand colors look nearly the same.", blocking=False))
        return out
