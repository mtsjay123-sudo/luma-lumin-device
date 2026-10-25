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
    """The brand mark: a rounded square in the brand gradient with the initials."""
    r = size * 0.24
    primary, fg = on_color(primary)
    return (f'<defs><linearGradient id="g{int(x)}{int(y)}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{primary}"/><stop offset="1" stop-color="{shade(primary, -0.25)}"/></linearGradient></defs>'
            f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="{r}" fill="url(#g{int(x)}{int(y)})"/>'
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


def svg(kind, brand, tagline, primary, accent):
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
        body = (f'<rect width="{w}" height="{h}" fill="{primary}"/><circle cx="{w * 0.9}" cy="{h * 0.08}" r="{min(w, h) * 0.38}" fill="{accent}" opacity="0.55"/>'
                f'<circle cx="{w * 0.05}" cy="{h * 0.98}" r="{min(w, h) * 0.28}" fill="{shade(primary, -0.3)}" opacity="0.7"/>')
        body += "".join(f'<text x="{w * 0.08}" y="{top + i * size * 1.12}" font-size="{size}" font-weight="800" fill="{fg}" {FONT}>{esc(line)}</text>' for i, line in enumerate(lines))
        body += mark(w * 0.08, h - min(w, h) * 0.2, min(w, h) * 0.11, shade(primary, -0.35), accent, letters)
        body += f'<text x="{w * 0.08 + min(w, h) * 0.14}" y="{h - min(w, h) * 0.125}" font-size="{min(w, h) * 0.045}" font-weight="700" fill="{fg}" {FONT}>{esc(brand[:24])}</text>'
    elif kind == "mockup":
        primary, fg = on_color(primary)
        body = (f'<rect width="{w}" height="{h}" fill="#F4F2FA"/><rect x="330" y="80" width="540" height="1140" rx="80" fill="#14121F"/>'
                f'<rect x="352" y="102" width="496" height="1096" rx="62" fill="#FFFFFF"/><rect x="352" y="102" width="496" height="300" rx="62" fill="{primary}"/>'
                f'<rect x="352" y="340" width="496" height="62" fill="{primary}"/><rect x="530" y="120" width="140" height="26" rx="13" fill="#14121F"/>'
                + mark(392, 190, 84, shade(primary, -0.3), accent, letters) +
                f'<text x="494" y="246" font-size="38" font-weight="800" fill="{fg}" {FONT}>{esc(brand[:14])}</text>'
                f'<text x="392" y="330" font-size="24" fill="{fg}" {FONT}>{esc((tagline or "Welcome")[:30])}</text>')
        for i in range(3):
            y = 440 + i * 210
            body += (f'<rect x="384" y="{y}" width="432" height="180" rx="28" fill="#F4F2FA"/><circle cx="440" cy="{y + 60}" r="28" fill="{accent if i % 2 else primary}"/>'
                     f'<rect x="490" y="{y + 42}" width="220" height="20" rx="10" fill="#D8D4E8"/><rect x="490" y="{y + 78}" width="160" height="16" rx="8" fill="#E6E3F1"/>'
                     f'<rect x="416" y="{y + 120}" width="368" height="18" rx="9" fill="#E6E3F1"/>')
        body += f'<rect x="384" y="1110" width="432" height="64" rx="32" fill="{accent}"/><text x="600" y="1152" text-anchor="middle" font-size="26" font-weight="700" fill="{readable_on(accent)}" {FONT}>Get started</text>'
    else:  # palette
        swatches = [("Primary", primary), ("Primary dark", shade(primary, -0.3)), ("Accent", accent), ("Ink", dark), ("Surface", "#F4F2FA")]
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
                   "style: modern, playful, elegant or bold. assets: which to make, comma-separated, from logo, icon, social, banner, story, mockup, palette.")
    fields = {"brand": "string", "tagline": "text", "primary_color": "text", "accent_color": "text", "style": "text", "assets": "text"}

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
            ctx.write(rel, svg(kind, brand, tagline, primary, accent))
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
