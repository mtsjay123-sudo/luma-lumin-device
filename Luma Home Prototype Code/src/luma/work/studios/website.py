"""Websites: multi-page, responsive sites built from tested sections, then checked in a real browser.

The brain writes the words and picks sections (hero, features, stats, pricing, testimonials, FAQ, team,
call to action, text, contact, gallery); this code owns the HTML, CSS and JavaScript, so every site
works on a phone, has readable colors, and links that go somewhere. Each page is then opened in a real
browser at phone width: no errors, no sideways scrolling, every link and image resolves, and a
screenshot is saved for the preview.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from luma.work.studios.base import Result, Studio, check, contrast, esc, on_color, readable_on, shade, slug, text
from luma.work.studios.media import brand_colors, svg as brand_svg

KINDS = ("hero", "features", "stats", "pricing", "testimonials", "faq", "team", "cta", "text", "contact", "gallery")
ICONS = ["M12 2l3 7h7l-5.5 4.5L18 21l-6-4-6 4 1.5-7.5L2 9h7z", "M4 12l5 5L20 6", "M12 3v18M3 12h18", "M3 12a9 9 0 1018 0 9 9 0 10-18 0zm9-5v5l3 3",
         "M4 19h16M6 15l4-4 3 3 5-6", "M12 21s-7-4.5-7-10a4 4 0 017-2.6A4 4 0 0119 11c0 5.5-7 10-7 10z"]


def icon(i):
    return f'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="{ICONS[i % len(ICONS)]}"/></svg>'


def section_html(s, index, pages):
    kind, heading, body, items = s["kind"], esc(s["heading"]), esc(s["body"]), s["items"]
    if kind == "hero":
        primary = items[0] if items else {"title": "Get started", "extra": ""}
        href = link_for(primary.get("extra"), pages, "#contact")
        second = f'<a class="btn ghost" href="{link_for(items[1].get("extra"), pages, "#features")}">{esc(items[1]["title"])}</a>' if len(items) > 1 else ""
        return (f'<section class="hero" id="top"><div class="wrap"><p class="eyebrow">{esc(s.get("eyebrow") or "")}</p><h1>{heading}</h1><p class="lead">{body}</p>'
                f'<div class="actions"><a class="btn" href="{href}">{esc(primary["title"])}</a>{second}</div></div><div class="orb"></div></section>')
    inner = ""
    if kind == "features":
        inner = '<div class="grid">' + "".join(f'<article class="card"><div class="icon">{icon(i)}</div><h3>{esc(it["title"])}</h3><p>{esc(it["text"])}</p></article>' for i, it in enumerate(items)) + "</div>"
    elif kind == "stats":
        inner = '<div class="stats">' + "".join(f'<div><strong>{esc(it["title"])}</strong><span>{esc(it["text"])}</span></div>' for it in items) + "</div>"
    elif kind == "pricing":
        inner = '<div class="grid pricing">' + "".join(
            f'<article class="card{" featured" if i == min(1, len(items) - 1) and len(items) > 1 else ""}"><h3>{esc(it["title"])}</h3><p class="price">{esc(it["extra"])}</p>'
            f'<ul>{"".join(f"<li>{esc(x.strip())}</li>" for x in re.split(r"[;|]", it["text"]) if x.strip())}</ul><a class="btn" href="#contact">Choose {esc(it["title"])}</a></article>'
            for i, it in enumerate(items)) + "</div>"
    elif kind == "testimonials":
        inner = '<div class="grid">' + "".join(f'<figure class="card quote"><blockquote>“{esc(it["text"])}”</blockquote><figcaption><b>{esc(it["title"])}</b> {esc(it["extra"])}</figcaption></figure>' for it in items) + "</div>"
    elif kind == "faq":
        inner = '<div class="faq">' + "".join(f'<details><summary>{esc(it["title"])}</summary><p>{esc(it["text"])}</p></details>' for it in items) + "</div>"
    elif kind == "team":
        inner = '<div class="grid team">' + "".join(
            f'<article class="card"><div class="avatar">{esc("".join(w[0] for w in it["title"].split()[:2]).upper())}</div><h3>{esc(it["title"])}</h3><p class="muted">{esc(it["extra"])}</p><p>{esc(it["text"])}</p></article>'
            for it in items) + "</div>"
    elif kind == "gallery":
        inner = '<div class="grid gallery">' + "".join(f'<figure class="tile t{i % 4}"><div class="icon">{icon(i)}</div><figcaption><b>{esc(it["title"])}</b><span>{esc(it["text"])}</span></figcaption></figure>' for i, it in enumerate(items)) + "</div>"
    elif kind == "contact":
        email = next((it["extra"] for it in items if "@" in it.get("extra", "")), "")
        lines = "".join(f'<li><b>{esc(it["title"])}</b> {esc(it["text"])}</li>' for it in items if it["title"] or it["text"])
        inner = (f'<div class="contact"><ul>{lines}</ul>' + (f'<a class="btn" href="mailto:{esc(email)}">Email {esc(email)}</a>' if email else "") + "</div>")
    elif kind == "cta":
        button = items[0] if items else {"title": "Get in touch", "extra": ""}
        return (f'<section class="cta" id="s{index}"><div class="wrap"><h2>{heading}</h2><p>{body}</p><a class="btn light" href="{link_for(button.get("extra"), pages, "#contact")}">{esc(button["title"])}</a></div></section>')
    else:  # text
        paragraphs = [p for p in re.split(r"\n{2,}|(?<=[.!?])\s{2,}", s["body"]) if p.strip()] or [s["body"]]
        body = ""
        inner = '<div class="prose">' + "".join(f"<p>{esc(p)}</p>" for p in paragraphs) + "".join(f'<h3>{esc(it["title"])}</h3><p>{esc(it["text"])}</p>' for it in items) + "</div>"
    anchor = {"contact": "contact", "features": "features", "pricing": "pricing", "faq": "faq"}.get(kind, f"s{index}")
    return f'<section id="{anchor}" class="{kind}"><div class="wrap"><h2>{heading}</h2>' + (f'<p class="lead">{body}</p>' if body else "") + inner + "</div></section>"


def link_for(target, pages, default):
    target = str(target or "").strip()
    if not target:
        return default
    if target.startswith(("#", "https://", "mailto:", "tel:")):
        return esc(target)
    name = slug(target.replace(".html", ""))
    return f"{name}.html" if name in pages else default


CSS = """:root{--p:%(p)s;--pd:%(pd)s;--a:%(a)s;--on-p:%(onp)s;--on-a:%(ona)s;--ink:%(ink)s;--muted:%(muted)s;--bg:%(bg)s;--card:%(card)s;--line:%(line)s;--r:18px}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Inter,"Helvetica Neue",Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased}
img,svg{max-width:100%%}a{color:inherit}.wrap{width:min(1120px,100%% - 40px);margin:0 auto}
header{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 86%%,transparent);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.bar{display:flex;align-items:center;justify-content:space-between;height:68px}.brand{display:flex;align-items:center;gap:10px;font-weight:800;text-decoration:none;font-size:1.1rem}
.brand img{width:36px;height:36px}nav{display:flex;gap:22px}nav a{text-decoration:none;color:var(--muted);font-weight:600}nav a[aria-current]{color:var(--ink)}
.menu{display:none;background:none;border:1px solid var(--line);border-radius:10px;padding:8px 12px;color:var(--ink);font:inherit}
section{padding:clamp(56px,9vw,104px) 0}h1{font-size:clamp(2.3rem,6vw,4.4rem);line-height:1.04;letter-spacing:-.02em;margin:.2em 0}h2{font-size:clamp(1.7rem,4vw,2.6rem);line-height:1.15;margin:0 0 .4em;letter-spacing:-.01em}
h3{margin:.4em 0 .2em}.lead{font-size:clamp(1.05rem,2vw,1.25rem);color:var(--muted);max-width:720px}.eyebrow{color:var(--p);font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:.8rem;margin:0}
.hero{position:relative;overflow:hidden}.orb{position:absolute;right:-12vw;top:-10vw;width:46vw;height:46vw;border-radius:50%%;background:radial-gradient(circle at 30%% 30%%,var(--a),var(--p));opacity:.18;filter:blur(10px);pointer-events:none}
.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}.btn{display:inline-block;background:var(--p);color:var(--on-p);padding:14px 24px;border-radius:999px;text-decoration:none;font-weight:700;border:2px solid var(--p);transition:transform .15s}
.btn:hover{transform:translateY(-2px)}.btn.ghost{background:transparent;color:var(--ink);border-color:var(--line)}.btn.light{background:var(--on-p);color:var(--p);border-color:var(--on-p)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px;margin-top:28px}.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:26px}
.icon svg{width:30px;height:30px;fill:none;stroke:var(--p);stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.muted{color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:20px;margin-top:20px}.stats strong{display:block;font-size:clamp(2rem,5vw,3rem);color:var(--p);line-height:1.1}.stats span{color:var(--muted)}
.pricing .featured{border:2px solid var(--p);box-shadow:0 20px 50px -24px var(--p)}.price{font-size:2rem;font-weight:800;margin:.2em 0}.pricing ul{padding-left:1.1em;color:var(--muted)}.pricing .btn{margin-top:10px}
.quote blockquote{margin:0 0 12px;font-size:1.08rem}.quote figcaption{color:var(--muted)}.faq details{border-bottom:1px solid var(--line);padding:16px 0}.faq summary{cursor:pointer;font-weight:700;font-size:1.05rem}
.avatar{width:56px;height:56px;border-radius:50%%;display:grid;place-items:center;background:var(--a);color:var(--on-a);font-weight:800}.gallery .tile{margin:0;border-radius:var(--r);padding:26px;min-height:200px;display:flex;flex-direction:column;justify-content:space-between;color:var(--on-p);background:linear-gradient(135deg,var(--p),var(--pd))}
.gallery .t1,.gallery .t3{background:linear-gradient(135deg,var(--pd),var(--p))}.gallery .icon svg{stroke:var(--on-p)}.gallery figcaption span{display:block;opacity:.9}
.cta{background:linear-gradient(135deg,var(--p),var(--pd));color:var(--on-p);text-align:center}.cta p{max-width:640px;margin:0 auto 24px;opacity:.92}.prose{max-width:760px}.contact ul{list-style:none;padding:0}.contact li{padding:6px 0}
footer{border-top:1px solid var(--line);padding:36px 0;color:var(--muted)}footer .wrap{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
@media (max-width:760px){nav{display:none;position:absolute;top:68px;left:0;right:0;flex-direction:column;background:var(--bg);padding:16px 20px;border-bottom:1px solid var(--line)}nav.open{display:flex}.menu{display:block}}
"""

JS = """document.querySelector('.menu')?.addEventListener('click',e=>{const n=document.querySelector('nav');const open=n.classList.toggle('open');e.currentTarget.setAttribute('aria-expanded',open)});
document.querySelectorAll('.year').forEach(n=>n.textContent=new Date().getFullYear());
"""


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.images, self.title, self._in_title, self.viewport, self.lang, self.missing_alt = [], [], "", False, False, False, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag in {"img", "script", "link"}:
            src = a.get("src") or (a.get("href") if tag == "link" and a.get("rel") in {"stylesheet", "icon"} else None)
            if src:
                self.images.append(src)
            if tag == "img" and not a.get("alt"):
                self.missing_alt += 1
        if tag == "meta" and a.get("name") == "viewport":
            self.viewport = True
        if tag == "html" and a.get("lang"):
            self.lang = True
        self._in_title = tag == "title"

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


class Website(Studio):
    name, agent, title = "website", "design", "Website"
    description = ("Build a website. name: the brand. tagline: one line. primary_color, accent_color: hex like #6E56CF (use the brand colors decided earlier). "
                   "style: modern, playful, elegant or bold. pages: the first page is the home page; each page has sections. Section kinds: hero (heading, body, "
                   "items = buttons: title is the label, extra is a page slug or #section), features (items: title, text), stats (items: title is the number, text the label), "
                   "pricing (items: title plan name, extra price like $29/mo, text features separated by ;), testimonials (items: title name, extra role, text quote), "
                   "faq (items: title question, text answer), team (items: title name, extra role, text bio), cta (heading, body, items[0] button), text (body), "
                   "contact (items: title label, text detail, extra an email), gallery (items: title, text). Real, specific words from the research; no lorem ipsum.")
    fields = {"name": "string", "tagline": "text", "primary_color": "text", "accent_color": "text", "style": "text", "pages": "pages"}

    def make(self, ctx, args):
        name = text(args.get("name"), 40) or ctx.project.get("name") or "Site"
        tagline = text(args.get("tagline"), 120)
        brand = ctx.input("graphics") or {}
        primary, accent = brand_colors(args.get("primary_color") or brand.get("primary"), args.get("accent_color") or brand.get("accent"))
        style = text(args.get("style"), 20).lower()
        dark = style == "bold"
        button, on_button = on_color(primary)
        colors = {"p": button, "pd": shade(button, -0.25), "a": accent, "onp": on_button, "ona": readable_on(accent),
                  "ink": "#F3F1FA" if dark else "#14121F", "muted": "#B9B4CF" if dark else "#5A5670", "bg": "#0E0C16" if dark else "#FFFFFF",
                  "card": "#17142A" if dark else "#F7F6FB", "line": "#2A2640" if dark else "#E7E4F0"}
        if contrast(colors["p"], colors["bg"]) < 3:  # buttons and links need to stand out from the page
            colors["p"] = shade(button, 0.35 if dark else -0.35)
            colors["onp"] = readable_on(colors["p"])
            colors["pd"] = shade(colors["p"], -0.25)
        raw_pages = [p for p in (args.get("pages") or []) if isinstance(p, dict)][:6]
        if not raw_pages:
            raise ValueError("A website needs at least one page.")
        pages, used = [], set()
        for i, p in enumerate(raw_pages):
            page_slug = "index" if i == 0 else (slug(p.get("slug") or p.get("title"), f"page{i}") or f"page{i}")
            while page_slug in used:
                page_slug += "-2"
            used.add(page_slug)
            sections = []
            for s in (p.get("sections") or [])[:8]:
                if not isinstance(s, dict):
                    continue
                kind = s.get("kind") if s.get("kind") in KINDS else "text"
                items = [{"title": text(it.get("title"), 120), "text": text(it.get("text"), 600), "extra": text(it.get("extra"), 120)}
                         for it in (s.get("items") or [])[:8] if isinstance(it, dict)]
                sections.append({"kind": kind, "heading": text(s.get("heading"), 140), "body": text(s.get("body"), 1600), "items": items})
            if sections:
                pages.append({"slug": page_slug, "title": text(p.get("title"), 60) or name, "sections": sections})
        if not pages:
            raise ValueError("The pages have no sections.")
        folder = f"site/{slug(name, 'site')}"
        logo = f"{folder}/logo.svg"
        ctx.write(logo, brand_svg("icon", name, tagline, primary, accent))
        ctx.write(f"{folder}/styles.css", CSS % colors)
        ctx.write(f"{folder}/script.js", JS)
        slugs = {p["slug"] for p in pages}
        nav = lambda current: "".join(f'<a href="{p["slug"]}.html"' + (' aria-current="page"' if p["slug"] == current else "") + f'>{esc(p["title"])}</a>' for p in pages)
        files = [logo, f"{folder}/styles.css", f"{folder}/script.js"]
        for page in pages:
            body = "".join(section_html(s, i, slugs) for i, s in enumerate(page["sections"]))
            desc = esc(tagline or page["sections"][0]["body"][:150])
            doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                   f'<title>{esc(page["title"] if page["slug"] != "index" else name + (" — " + tagline if tagline else ""))}</title><meta name="description" content="{desc}">'
                   f'<link rel="icon" href="logo.svg"><link rel="stylesheet" href="styles.css"></head><body>'
                   f'<header><div class="wrap bar"><a class="brand" href="index.html"><img src="logo.svg" alt="{esc(name)} logo">{esc(name)}</a>'
                   f'<button class="menu" aria-expanded="false" aria-label="Menu">Menu</button><nav>{nav(page["slug"])}</nav></div></header>'
                   f'<main>{body}</main><footer><div class="wrap"><span>© <span class="year"></span> {esc(name)}</span><span>{esc(tagline)}</span></div></footer>'
                   f'<script src="script.js"></script></body></html>')
            ctx.write(f"{folder}/{page['slug']}.html", doc)
            files.append(f"{folder}/{page['slug']}.html")
        shots = self.browser_test(ctx, folder, [p["slug"] for p in pages]) if ctx.can_render else None
        if shots and shots.get("shots"):
            files += shots["shots"]
        return Result(files=files, summary=f"{name} website: {len(pages)} page{'s' if len(pages) != 1 else ''} ({', '.join(p['title'] for p in pages)}). Open {folder}/index.html to see it.",
                      data={"name": name, "folder": folder, "pages": [p["slug"] for p in pages], "primary": colors["p"], "accent": accent, "browser": shots})

    @staticmethod
    def browser_test(ctx, folder, slugs):
        """Open each page in a real browser at phone width: errors, sideways scrolling, broken images, and a screenshot."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return None
        report = {"errors": [], "overflow": [], "broken": [], "shots": []}
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                for width, label in ((390, "phone"), (1280, "desktop")):
                    page = browser.new_page(viewport={"width": width, "height": 844 if width < 500 else 800})
                    page.on("pageerror", lambda e: report["errors"].append(str(e)[:200]))
                    page.on("console", lambda m: report["errors"].append(m.text[:200]) if m.type == "error" else None)
                    for s in slugs:
                        page.goto(ctx.path(f"{folder}/{s}.html").as_uri())
                        page.wait_for_load_state("load")
                        if page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1"):
                            report["overflow"].append(f"{s} ({label})")
                        broken = page.evaluate("[...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute('src'))")
                        report["broken"] += [f"{s}: {b}" for b in broken]
                        if s == slugs[0] or label == "desktop":
                            shot = f"previews/{folder.rsplit('/', 1)[-1]}-{s}-{label}.png"
                            ctx.path(shot).parent.mkdir(parents=True, exist_ok=True)
                            page.screenshot(path=str(ctx.path(shot)), full_page=False)
                            report["shots"].append(shot)
                    page.close()
                browser.close()
        except Exception as error:
            report["unavailable"] = str(error)[:200]
        return report

    def check(self, ctx, result):
        d = result.data
        out, folder = [], d["folder"]
        existing = {f["path"] for f in ctx.files()}
        for s in d["pages"]:
            parser = _Links()
            parser.feed(ctx.read_text(f"{folder}/{s}.html"))
            internal = [l.split("#")[0] for l in parser.links + parser.images if not re.match(r"^(?:https?:|mailto:|tel:|#|data:)", l) and l.split("#")[0]]
            missing = [l for l in internal if f"{folder}/{l}" not in existing]
            out.append(check(f"{s}: links and files resolve", not missing, "Missing: " + ", ".join(missing[:5])))
            out.append(check(f"{s}: title, phone layout and language set", parser.title.strip() and parser.viewport and parser.lang, "A page is missing its title, viewport or language."))
            out.append(check(f"{s}: images have alt text", parser.missing_alt == 0, f"{parser.missing_alt} image(s) without alt text.", blocking=False))
            out.append(check(f"{s}: no placeholder text", not re.search(r"lorem ipsum|\[(?:insert|your)[^\]]*\]", ctx.read_text(f"{folder}/{s}.html"), re.I), "There's placeholder text left."))
        out.append(check("buttons are readable", contrast(d["primary"], readable_on(d["primary"])) >= 4.5, "Button text doesn't stand out from the button color."))
        b = d.get("browser")
        if b and not b.get("unavailable"):
            out.append(check("no errors in the browser", not b["errors"], "; ".join(b["errors"][:3])))
            out.append(check("fits a phone screen", not b["overflow"], "Scrolls sideways on: " + ", ".join(b["overflow"][:4])))
            out.append(check("every image loads", not b["broken"], "Broken: " + ", ".join(b["broken"][:4])))
        else:
            out.append(check("tested in a browser", False, "No browser was available, so only the files were checked.", blocking=False))
        return out
