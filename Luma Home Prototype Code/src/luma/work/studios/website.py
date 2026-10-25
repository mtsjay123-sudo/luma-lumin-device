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

from luma.work.studios import taste
from luma.work.studios.base import Result, Studio, check, contrast, esc, on_color, readable_on, shade, slug, text
from luma.work.studios.media import brand_colors, svg as brand_svg

KINDS = ("hero", "features", "stats", "pricing", "testimonials", "faq", "team", "cta", "text", "contact", "gallery")

# Six art directions, each a whole system (type, corners, how sections are composed, how loud it is), so a
# site gets a point of view instead of the average of every generated page. The brain picks the one that
# suits the subject; the reason is written into the stylesheet (Design read).
DIRECTIONS = {
    "editorial": {"display": '"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif', "body": '"Avenir Next","Segoe UI",system-ui,sans-serif',
                  "weight": 600, "h1": "clamp(2.6rem,7vw,5.4rem)", "radius": "0", "button": "0", "features": "list", "hero": "split", "dials": (2, 2, 1),
                  "ground": "#F6F6F3", "ink": "#17161B", "why": "a serif voice and a reading measure, for a subject with a story to tell"},
    "bold": {"display": '"Avenir Next Condensed","Arial Narrow","Helvetica Neue",Helvetica,sans-serif', "body": '"Helvetica Neue",Helvetica,Arial,sans-serif',
             "weight": 800, "h1": "clamp(3rem,10vw,7.5rem)", "radius": "0", "button": "0", "features": "big", "hero": "field", "dials": (3, 3, 1),
             "ground": "#FFFFFF", "ink": "#0D0D10", "why": "condensed display type on whole fields of the brand color, for a subject that should be loud"},
    "warm": {"display": 'ui-rounded,"SF Pro Rounded","Avenir Next",system-ui,sans-serif', "body": 'ui-rounded,"Avenir Next","Segoe UI",system-ui,sans-serif',
             "weight": 700, "h1": "clamp(2.4rem,6vw,4.6rem)", "radius": "26px", "button": "999px", "features": "cards", "hero": "split", "dials": (2, 2, 1),
             "ground": "#EEF0EC", "ink": "#1B1D1A", "why": "rounded type and soft stone, for a subject that should feel friendly and close"},
    "technical": {"display": '"Helvetica Neue",Helvetica,Arial,sans-serif', "body": '"Helvetica Neue",Helvetica,Arial,sans-serif',
                  "weight": 700, "h1": "clamp(2.3rem,5.6vw,4.2rem)", "radius": "6px", "button": "6px", "features": "table", "hero": "split", "dials": (1, 2, 1),
                  "ground": "#FFFFFF", "ink": "#111317", "why": "a precise grotesk and tables instead of cards, for a subject people evaluate"},
    "playful": {"display": 'ui-rounded,"Arial Rounded MT Bold","Avenir Next",system-ui,sans-serif', "body": 'ui-rounded,"Avenir Next","Segoe UI",system-ui,sans-serif',
                "weight": 800, "h1": "clamp(2.6rem,7.5vw,5.6rem)", "radius": "22px", "button": "999px", "features": "tiles", "hero": "field", "dials": (3, 3, 1),
                "ground": "#FFFFFF", "ink": "#16141F", "why": "big round type and color blocks, for a subject that should make people smile"},
    "quiet": {"display": '"Avenir Next","Segoe UI",system-ui,sans-serif', "body": '"Avenir Next","Segoe UI",system-ui,sans-serif',
              "weight": 400, "h1": "clamp(2.4rem,6vw,4.4rem)", "radius": "2px", "button": "2px", "features": "list", "hero": "split", "dials": (1, 1, 1),
              "ground": "#FAFAF9", "ink": "#1A1A1C", "why": "light type and a lot of space, for a subject that should feel calm and premium"},
}
ALIASES = {"modern": "technical", "elegant": "editorial", "minimal": "quiet", "luxury": "quiet", "fun": "playful", "friendly": "warm", "loud": "bold"}


def pick_direction(style, name):
    style = str(style or "").lower().strip()
    if style in DIRECTIONS:
        return style
    if style in ALIASES:
        return ALIASES[style]
    import zlib
    return list(DIRECTIONS)[zlib.crc32(str(name).encode()) % len(DIRECTIONS)]


def monogram(name):
    letters = [w[0] for w in re.findall(r"[A-Za-z0-9]+", name)[:2]]
    return ("".join(letters) or name[:1] or "•").upper()


def section_html(s, index, pages, d, name, art=None):
    kind, heading, body, items = s["kind"], esc(s["heading"]), esc(s["body"]), s["items"]
    if kind == "hero":
        primary = items[0] if items else {"title": "Say hello", "extra": ""}
        href = link_for(primary.get("extra"), pages, "#contact")
        second = f'<a class="btn ghost" href="{link_for(items[1].get("extra"), pages, "#s1")}">{esc(items[1]["title"])}</a>' if len(items) > 1 else ""
        mark = (f'<img class="art" src="{art}" alt="{esc(name)} brand artwork">' if art else
                f'<div class="mark" aria-hidden="true">{esc(monogram(name))}</div>')
        return (f'<section class="hero hero-{d["hero"]}" id="top"><div class="wrap"><div class="hero-copy"><h1>{heading}</h1><p class="lead">{body}</p>'
                f'<div class="actions"><a class="btn" href="{href}">{esc(primary["title"])}</a>{second}</div></div>{mark}</div></section>')
    inner = ""
    if kind == "features":
        style = d["features"]
        if style == "list":
            inner = '<dl class="list">' + "".join(f'<div><dt>{esc(it["title"])}</dt><dd>{esc(it["text"])}</dd></div>' for it in items) + "</dl>"
        elif style == "table":
            inner = '<dl class="table">' + "".join(f'<div><dt>{esc(it["title"])}</dt><dd>{esc(it["text"])}</dd></div>' for it in items) + "</dl>"
        elif style == "big":
            inner = '<div class="big">' + "".join(f'<div class="row{" on" if i == 0 else ""}"><h3>{esc(it["title"])}</h3><p>{esc(it["text"])}</p></div>' for i, it in enumerate(items)) + "</div>"
        else:  # cards and tiles: the first one leads, the rest follow
            inner = f'<div class="cards {style}">' + "".join(f'<article class="card{" lead-card" if i == 0 and len(items) > 2 else ""} c{i % 3}"><h3>{esc(it["title"])}</h3><p>{esc(it["text"])}</p></article>'
                                                         for i, it in enumerate(items)) + "</div>"
    elif kind == "stats":
        inner = '<div class="stats">' + "".join(f'<p><strong>{esc(it["title"])}</strong> {esc(it["text"])}</p>' for it in items) + "</div>"
    elif kind == "pricing":
        inner = '<div class="plans">' + "".join(
            f'<article class="card plan"><h3>{esc(it["title"])}</h3><p class="price">{esc(it["extra"])}</p>'
            f'<ul>{"".join(f"<li>{esc(x.strip())}</li>" for x in re.split(r"[;|]", it["text"]) if x.strip())}</ul><a class="btn" href="#contact">Choose {esc(it["title"])}</a></article>'
            for it in items) + "</div>"
    elif kind == "testimonials":
        inner = '<div class="quotes">' + "".join(f'<figure class="quote"><blockquote>“{esc(it["text"])}”</blockquote><figcaption>{esc(it["title"])}{(", " + esc(it["extra"])) if it["extra"] else ""}</figcaption></figure>' for it in items) + "</div>"
    elif kind == "faq":
        inner = '<div class="faq">' + "".join(f'<details><summary>{esc(it["title"])}</summary><p>{esc(it["text"])}</p></details>' for it in items) + "</div>"
    elif kind == "team":
        inner = '<div class="cards team">' + "".join(
            f'<article class="card"><div class="avatar" aria-hidden="true">{esc("".join(w[0] for w in it["title"].split()[:2]).upper())}</div><h3>{esc(it["title"])}</h3><p class="muted">{esc(it["extra"])}</p><p>{esc(it["text"])}</p></article>'
            for it in items) + "</div>"
    elif kind == "gallery":
        inner = '<div class="gallery">' + "".join(f'<figure class="tile t{i % 3}"><figcaption><b>{esc(it["title"])}</b><span>{esc(it["text"])}</span></figcaption></figure>' for i, it in enumerate(items)) + "</div>"
    elif kind == "contact":
        email = next((it["extra"] for it in items if "@" in it.get("extra", "")), "")
        lines = "".join(f'<li><b>{esc(it["title"])}</b> {esc(it["text"])}</li>' for it in items if it["title"] or it["text"])
        inner = (f'<div class="contact"><ul>{lines}</ul>' + (f'<a class="btn" href="mailto:{esc(email)}">Email {esc(email)}</a>' if email else "") + "</div>")
    elif kind == "cta":
        button = items[0] if items else {"title": "Write to us", "extra": ""}
        return (f'<section class="cta" id="s{index}"><div class="wrap"><h2>{heading}</h2><p>{body}</p><a class="btn light" href="{link_for(button.get("extra"), pages, "#contact")}">{esc(button["title"])}</a></div></section>')
    else:  # text
        paragraphs = [p for p in re.split(r"\n{2,}|(?<=[.!?])\s{2,}", s["body"]) if p.strip()] or [s["body"]]
        body = ""
        inner = '<div class="prose">' + "".join(f"<p>{esc(p)}</p>" for p in paragraphs) + "".join(f'<h3>{esc(it["title"])}</h3><p>{esc(it["text"])}</p>' for it in items) + "</div>"
    anchor = {"contact": "contact", "features": "features", "pricing": "pricing", "faq": "faq"}.get(kind, f"s{index}")
    head = f'<div class="head"><h2>{heading}</h2>' + (f'<p class="lead">{body}</p>' if body else "") + "</div>"
    return f'<section id="{anchor}" class="{kind}"><div class="wrap">{head}{inner}</div></section>'


def link_for(target, pages, default):
    target = str(target or "").strip()
    if not target:
        return default
    if target.startswith(("#", "https://", "mailto:", "tel:")):
        return esc(target)
    name = slug(target.replace(".html", ""))
    return f"{name}.html" if name in pages else default


CSS = """/* Design read: %(read)s
   Dials: ENERGY %(e)s / RHYTHM %(r)s / MOTION %(m)s. Motif: the %(name)s monogram, repeated large in the hero and small in the footer.
   One accent (%(a)s), one primary (%(p)s); no gradients, glows, eyebrow labels or hover lifts. Light and dark follow the visitor's setting. */
:root{--p:%(p)s;--pd:%(pd)s;--a:%(a)s;--on-p:%(onp)s;--on-a:%(ona)s;--ink:%(ink)s;--muted:%(muted)s;--bg:%(bg)s;--card:%(card)s;--line:%(line)s;
--r:%(radius)s;--rb:%(button)s;--display:%(display)s;--body:%(body)s;--w:%(weight)s;--h1:%(h1)s}
@media (prefers-color-scheme:dark){:root{--ink:%(dink)s;--muted:%(dmuted)s;--bg:%(dbg)s;--card:%(dcard)s;--line:%(dline)s}}
*{box-sizing:border-box}html,body{overflow-x:clip}html{scroll-behavior:smooth}
body{margin:0;font-family:var(--body);font-size:17px;color:var(--ink);background:var(--bg);line-height:1.6;-webkit-font-smoothing:antialiased}
img,svg{max-width:100%%}a{color:inherit}.wrap{width:min(1120px,100%% - 40px);margin:0 auto}
:focus-visible{outline:3px solid var(--a);outline-offset:3px}
header{position:sticky;top:0;z-index:10;background:var(--bg);border-bottom:1px solid var(--line)}
.bar{display:flex;align-items:center;justify-content:space-between;min-height:68px;gap:16px}.brand{display:flex;align-items:center;gap:10px;font-family:var(--display);font-weight:var(--w);text-decoration:none;font-size:1.15rem}
.brand img{width:34px;height:34px}nav{display:flex;gap:6px}nav a{text-decoration:none;color:var(--muted);font-weight:600;padding:10px 12px;min-height:44px;display:inline-flex;align-items:center}
nav a[aria-current]{color:var(--ink)}nav a:hover{color:var(--ink)}
.menu{display:none;background:none;border:1px solid var(--line);border-radius:var(--rb);min-height:44px;padding:8px 14px;color:var(--ink);font:inherit}
section{padding:clamp(56px,8vw,104px) 0}h1,h2,h3{font-family:var(--display);font-weight:var(--w);overflow-wrap:break-word;min-width:0}
h1{font-size:var(--h1);line-height:1;letter-spacing:-.025em;margin:0 0 .3em}h2{font-size:clamp(1.8rem,4.2vw,3rem);line-height:1.08;margin:0 0 .4em;letter-spacing:-.015em}
h3{font-size:1.2rem;margin:0 0 .3em}.lead{font-size:clamp(1.08rem,2vw,1.3rem);color:var(--muted);max-width:620px;margin:0}.muted{color:var(--muted)}
.head{max-width:760px;margin-bottom:clamp(28px,4vw,48px)}
.hero .wrap{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:clamp(24px,5vw,64px);align-items:center}
.mark{font-family:var(--display);font-weight:var(--w);font-size:clamp(7rem,22vw,17rem);line-height:.8;color:var(--p);text-align:right;letter-spacing:-.06em;user-select:none}
.art{width:100%%;max-height:520px;object-fit:contain;border-radius:var(--r)}.hero{position:relative;overflow:hidden}
.hero-field .wrap{grid-template-columns:minmax(0,1fr)}.hero-field h1{max-width:15ch}.hero-field .mark{position:absolute;right:3vw;bottom:-.12em;font-size:clamp(9rem,30vw,24rem)}
.hero-field .art{max-width:440px;justify-self:end}
.hero-field{background:var(--p);color:var(--on-p)}.hero-field .lead{color:var(--on-p);opacity:.9}.hero-field .mark{color:var(--on-p);opacity:.18}
.hero-field .btn{background:var(--on-p);color:var(--p);border-color:var(--on-p)}.hero-field .btn.ghost{background:transparent;color:var(--on-p);border-color:var(--on-p)}
.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:30px}
.btn{display:inline-flex;align-items:center;min-height:48px;background:var(--p);color:var(--on-p);padding:12px 24px;border-radius:var(--rb);text-decoration:none;font-weight:700;border:2px solid var(--p);transition:background-color .15s,color .15s}
.btn:hover{background:var(--pd);border-color:var(--pd)}.btn.ghost{background:transparent;color:var(--ink);border-color:var(--line)}.btn.ghost:hover{border-color:var(--ink)}
.btn.light{background:var(--on-p);color:var(--p);border-color:var(--on-p)}
.list,.table{margin:0;display:grid;gap:0}.list div{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);gap:24px;padding:22px 0;border-top:1px solid var(--line)}
.list dt{font-family:var(--display);font-weight:var(--w);font-size:1.35rem}.list dd{margin:0;color:var(--muted)}
.table{grid-template-columns:repeat(auto-fit,minmax(min(100%%,260px),1fr));gap:2px;background:var(--line);border:2px solid var(--line);border-radius:var(--r);overflow:hidden}
.table div{background:var(--bg);padding:22px}.table dt{font-weight:700}.table dd{margin:6px 0 0;color:var(--muted)}
.big .row{padding:clamp(22px,4vw,40px) 0;border-top:1px solid var(--line);display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:24px;align-items:baseline}
.big .row h3{font-size:clamp(1.8rem,5vw,3.6rem);line-height:1;margin:0}.big .row p{margin:0;color:var(--muted);font-size:1.1rem}
.big .row.on{background:var(--a);color:var(--on-a);border:0;padding-left:clamp(16px,3vw,32px);padding-right:clamp(16px,3vw,32px)}.big .row.on p{color:var(--on-a);opacity:.85}
.cards{display:flex;flex-wrap:wrap;gap:16px}.cards>*{flex:1 1 250px}
.card{background:var(--card);border-radius:var(--r);padding:26px}.card p{margin:0;color:var(--muted)}.cards>.lead-card{flex-basis:100%%}.lead-card h3{font-size:clamp(1.5rem,3.4vw,2.2rem)}
.tiles .c0{background:var(--p);color:var(--on-p)}.tiles .c1{background:var(--a);color:var(--on-a)}.tiles .c0 p,.tiles .c1 p{color:inherit;opacity:.88}
.stats{display:flex;flex-wrap:wrap;gap:clamp(20px,5vw,64px)}.stats p{margin:0;max-width:260px;color:var(--muted)}
.stats strong{display:block;font-family:var(--display);font-weight:var(--w);font-size:clamp(2.6rem,7vw,4.6rem);line-height:1;color:var(--ink)}
.plans{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%%,260px),1fr));gap:16px}.price{font-family:var(--display);font-size:2.2rem;font-weight:var(--w);margin:.1em 0 .3em}
.plan ul{padding-left:1.1em;color:var(--muted);margin:0 0 18px}
.quotes{display:grid;gap:28px}.quote{margin:0;max-width:760px}.quote blockquote{margin:0 0 10px;font-family:var(--display);font-size:clamp(1.3rem,2.6vw,1.8rem);line-height:1.3}.quote figcaption{color:var(--muted)}
.faq{max-width:820px}.faq details{border-top:1px solid var(--line);padding:18px 0}.faq summary{cursor:pointer;font-weight:700;font-size:1.08rem;min-height:44px;display:flex;align-items:center}
.avatar{width:56px;height:56px;border-radius:50%%;display:grid;place-items:center;background:var(--a);color:var(--on-a);font-weight:800;margin-bottom:12px}
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%%,240px),1fr));gap:16px}.tile{margin:0;border-radius:var(--r);padding:26px;min-height:220px;display:flex;align-items:flex-end}
.tile.t0{background:var(--p);color:var(--on-p)}.tile.t1{background:var(--a);color:var(--on-a)}.tile.t2{background:var(--card);color:var(--ink)}.tile span{display:block;opacity:.85}
.cta{background:var(--p);color:var(--on-p)}.cta p{max-width:640px;margin:0 0 26px;opacity:.92;font-size:1.15rem}.prose{max-width:720px}.contact ul{list-style:none;padding:0;margin:0 0 20px}.contact li{padding:6px 0}
footer{border-top:1px solid var(--line);padding:40px 0;color:var(--muted)}footer .wrap{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap}
footer .sign{font-family:var(--display);font-weight:var(--w);font-size:1.6rem;color:var(--p)}footer nav{display:flex}
@media (max-width:760px){header nav{display:none;position:absolute;top:68px;left:0;right:0;flex-direction:column;background:var(--bg);padding:12px 20px;border-bottom:1px solid var(--line)}
header nav.open{display:flex}.menu{display:inline-flex;align-items:center}.hero .wrap{grid-template-columns:minmax(0,1fr)}.mark{display:none}
.list div,.big .row{grid-template-columns:minmax(0,1fr);gap:8px}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
"""

JS = """document.querySelector('.menu')?.addEventListener('click',e=>{const n=document.querySelector('header nav');const open=n.classList.toggle('open');e.currentTarget.setAttribute('aria-expanded',open)});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){const n=document.querySelector('header nav.open');if(n){n.classList.remove('open');document.querySelector('.menu')?.setAttribute('aria-expanded','false')}}});
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
    description = ("Build a website with a point of view. name: the brand. tagline: one line. primary_color, accent_color: hex like #2F6B4F (the brand colors decided "
                   "earlier). direction: the art direction that suits THIS subject: editorial (a story, a serif voice), bold (loud, condensed type on brand color), "
                   "warm (friendly, rounded), technical (precise, for products people compare), playful (fun, color blocks) or quiet (calm, premium). "
                   "pages: the first page is the home page; each page has sections, in the order of the argument (what a visitor needs to believe, then the proof), "
                   "not a template. Section kinds: hero (heading of 8 words or fewer, body one sentence, items = buttons: title is the label, extra is a page slug or "
                   "#section), features (items: title, text), stats (items: title is a number that came from the research, text the label), pricing (items: title plan "
                   "name, extra price like $29/mo, text features separated by ;), testimonials (only quotes the owner gave you), faq (questions real customers of this "
                   "business would ask), team (items: title name, extra role, text bio), cta (heading, body, items[0] button), text (body), contact (items: title label, "
                   "text detail, extra an email), gallery (items: title, text). Write like a person: specific words from the research, no em dashes, no buzzwords "
                   "(seamless, unlock, elevate, revolutionary, cutting-edge), and buttons that name the action (\"Order lunch\", \"See the menu\"), never \"Get started\" or "
                   "\"Learn more\". No invented numbers, ratings, customers or quotes.")
    fields = {"name": "string", "tagline": "text", "primary_color": "text", "accent_color": "text", "direction": "text", "pages": "pages"}

    def make(self, ctx, args):
        name = text(args.get("name"), 40) or ctx.project.get("name") or "Site"
        tagline = taste.fix_dashes(text(args.get("tagline"), 120))
        brand = ctx.input("graphics") or {}
        primary, accent = brand_colors(args.get("primary_color") or brand.get("primary"), args.get("accent_color") or brand.get("accent"))
        direction = pick_direction(args.get("direction") or args.get("style"), name)
        d = DIRECTIONS[direction]
        button, on_button = on_color(primary)
        ground = d["ground"]
        colors = {"p": button, "pd": shade(button, -0.22), "a": accent, "onp": on_button, "ona": readable_on(accent),
                  "ink": d["ink"], "muted": "#56535F", "bg": ground, "card": "#FFFFFF" if ground.upper() != "#FFFFFF" else "#F3F3F5", "line": "#E2E1E6",
                  "dink": "#F2F1F5", "dmuted": "#B5B2BF", "dbg": "#111114", "dcard": "#1B1B20", "dline": "#2D2D34"}
        if contrast(colors["p"], colors["bg"]) < 3 or contrast(colors["p"], colors["dbg"]) < 2:  # buttons and links stand out in light and dark
            colors["p"] = shade(button, -0.35) if contrast(colors["p"], colors["bg"]) < 3 else shade(button, 0.2)
            colors["onp"] = readable_on(colors["p"])
            colors["pd"] = shade(colors["p"], -0.22)
        sources = " ".join(str(x) for x in (ctx.request, ctx.task, ctx.input("research"), ctx.input("financial_model"), ctx.input("analyze_data"),
                                            [n.get("text") for n in ctx.project.get("notes", [])]))
        quotes_given = bool(re.search(r"\b(?:testimonial|review|quote)s?\b.{0,40}[\"“]", sources, re.I))
        raw_pages = [p for p in (args.get("pages") or []) if isinstance(p, dict)][:6]
        if not raw_pages:
            raise ValueError("A website needs at least one page.")
        pages, used, dropped = [], set(), []
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
                items = [{"title": taste.fix_dashes(text(it.get("title"), 120)), "text": taste.fix_dashes(text(it.get("text"), 600)), "extra": text(it.get("extra"), 120)}
                         for it in (s.get("items") or [])[:8] if isinstance(it, dict)]
                if kind == "stats":  # a number on the page has to come from somewhere real
                    kept = [it for it in items if taste.sourced(it["title"], sources)]
                    dropped += [f"{it['title']} {it['text']}".strip() for it in items if it not in kept]
                    if not kept:
                        continue
                    items = kept
                if kind == "testimonials" and not quotes_given:
                    dropped += [f"a quote from {it['title'] or 'someone'}" for it in items]
                    continue
                sections.append({"kind": kind, "heading": taste.fix_dashes(text(s.get("heading"), 140)), "body": taste.fix_dashes(text(s.get("body"), 1600)), "items": items})
            if sections:
                pages.append({"slug": page_slug, "title": text(p.get("title"), 60) or name, "sections": sections})
        if not pages:
            raise ValueError("The pages have no sections.")
        folder = f"site/{slug(name, 'site')}"
        logo = f"{folder}/logo.svg"
        ctx.write(logo, brand_svg("icon", name, tagline, primary, accent))
        e, r, m = d["dials"]
        ctx.write(f"{folder}/styles.css", CSS % {**colors, **{k: d[k] for k in ("display", "body", "weight", "h1", "radius", "button")},
                                                 "read": f"{name}, {direction}: {d['why']}", "e": e, "r": r, "m": m, "name": esc(name)})
        ctx.write(f"{folder}/script.js", JS)
        # A real picture of this brand beats any decoration: the mockup or social art made in the graphics step, when there is one.
        found = sorted((f["path"] for f in ctx.files() if re.search(r"^graphics/.+-(?:mockup|social)\.svg$", f["path"])), key=lambda f: "mockup" not in f)
        art = None
        if found:
            ctx.write(f"{folder}/hero.svg", ctx.read_text(found[0]))
            art = "hero.svg"
        slugs = {p["slug"] for p in pages}
        nav = lambda current: "".join(f'<a href="{p["slug"]}.html"' + (' aria-current="page"' if p["slug"] == current else "") + f'>{esc(p["title"])}</a>' for p in pages)
        files = [logo, f"{folder}/styles.css", f"{folder}/script.js"] + ([f"{folder}/hero.svg"] if art else [])
        for page in pages:
            body = "".join(section_html(s, i, slugs, d, name, art) for i, s in enumerate(page["sections"]))
            desc = esc(tagline or page["sections"][0]["body"][:150])
            doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                   f'<title>{esc(page["title"] if page["slug"] != "index" else name + (": " + tagline if tagline else ""))}</title><meta name="description" content="{desc}">'
                   f'<meta name="color-scheme" content="light dark"><link rel="icon" href="logo.svg"><link rel="stylesheet" href="styles.css"></head><body>'
                   f'<header><div class="wrap bar"><a class="brand" href="index.html"><img src="logo.svg" alt="{esc(name)} logo">{esc(name)}</a>'
                   f'<button class="menu" aria-expanded="false" aria-label="Menu">Menu</button><nav>{nav(page["slug"])}</nav></div></header>'
                   f'<main>{body}</main><footer><div class="wrap"><span class="sign" aria-hidden="true">{esc(monogram(name))}</span>'
                   f'<span>© <span class="year"></span> {esc(name)}{(". " + esc(tagline)) if tagline else ""}</span></div></footer>'
                   f'<script src="script.js"></script></body></html>')
            ctx.write(f"{folder}/{page['slug']}.html", doc)
            files.append(f"{folder}/{page['slug']}.html")
        shots = self.browser_test(ctx, folder, [p["slug"] for p in pages]) if ctx.can_render else None
        if shots and shots.get("shots"):
            files += shots["shots"]
        copy = " ".join(" ".join([s["heading"], s["body"]] + [it["title"] + " " + it["text"] for it in s["items"]]) for pg in pages for s in pg["sections"]) + " " + tagline
        buttons = [it["title"] for pg in pages for s in pg["sections"] if s["kind"] in ("hero", "cta") for it in s["items"][:2]]
        hero = next((s["heading"] for s in pages[0]["sections"] if s["kind"] == "hero"), "")
        return Result(files=files, summary=f"{name} website ({direction}): {len(pages)} page{'s' if len(pages) != 1 else ''} ({', '.join(p['title'] for p in pages)}). Open {folder}/index.html to see it.",
                      data={"name": name, "folder": folder, "pages": [p["slug"] for p in pages], "primary": colors["p"], "accent": accent, "browser": shots,
                            "direction": direction, "buzzwords": taste.buzzwords(copy), "generic": [b for b in buttons if taste.generic_cta(b)],
                            "hero_words": taste.words(hero), "dropped": dropped,
                            "muted_ok": min(contrast(colors["muted"], colors["bg"]), contrast(colors["dmuted"], colors["dbg"])) >= 4.5})

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
                        if width < 500:  # things you tap are at least 44px tall
                            small = page.evaluate("[...document.querySelectorAll('a.btn, button, summary')].filter(e => e.offsetParent && e.getBoundingClientRect().height < 43.5).map(e => e.textContent.trim().slice(0, 30))")
                            report.setdefault("small", []).extend(f"{s}: {t}" for t in small)
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
        if "buzzwords" in d:  # the taste gates: words that sound generated, buttons that don't say what they do, numbers and quotes nobody can stand behind
            out.append(check("sounds like a person, not a template", not d["buzzwords"], "Rewrite without: " + ", ".join(d["buzzwords"][:8])))
            out.append(check("buttons say what they do", not d["generic"], "Name the action instead of: " + ", ".join(d["generic"][:4])))
            out.append(check("the headline is short", d["hero_words"] <= 9, f"The hero headline is {d['hero_words']} words; keep it to 8 or fewer and put the rest below."))
            out.append(check("secondary text is readable in light and dark", d["muted_ok"], "Gray text is too faint against the page."))
            if d["dropped"]:
                out.append(check("no invented numbers or quotes", False, "Left out (no source for them): " + "; ".join(d["dropped"][:4]), blocking=False))
        b = d.get("browser")
        if b and not b.get("unavailable"):
            out.append(check("no errors in the browser", not b["errors"], "; ".join(b["errors"][:3])))
            out.append(check("fits a phone screen", not b["overflow"], "Scrolls sideways on: " + ", ".join(b["overflow"][:4])))
            out.append(check("every image loads", not b["broken"], "Broken: " + ", ".join(b["broken"][:4])))
            out.append(check("easy to tap on a phone", not b.get("small"), "Under 44px tall: " + ", ".join(b.get("small", [])[:4]), blocking=False))
        else:
            out.append(check("tested in a browser", False, "No browser was available, so only the files were checked.", blocking=False))
        return out
