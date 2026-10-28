"""Find the cheapest real price for something, the way a person would: open a few
stores in Luma's browser, read the listings, and line them up.

Prices come from what the store pages publish: schema.org Product data (JSON-LD
or microdata) first, then the visible product tiles. Nothing is bought here.
Adding to a cart is a separate step that waits for the owner's OK, and checkout
always stays with the owner.
"""
from __future__ import annotations

import json
import re
import urllib.parse

DEFAULT_STORES = [
    {"id": "amazon", "name": "Amazon", "search": "https://www.amazon.com/s?k={q}"},
    {"id": "walmart", "name": "Walmart", "search": "https://www.walmart.com/search?q={q}"},
    {"id": "target", "name": "Target", "search": "https://www.target.com/s?searchTerm={q}"},
    {"id": "bestbuy", "name": "Best Buy", "search": "https://www.bestbuy.com/site/searchpage.jsp?st={q}"},
    {"id": "ebay", "name": "eBay", "search": "https://www.ebay.com/sch/i.html?_nkw={q}&LH_BIN=1"},
]

# Runs inside the store page. Read-only: it never clicks or types.
PRODUCTS_JS = r"""
() => {
  const out = [], seen = new Set();
  const abs = (u) => { try { return u ? new URL(u, location.href).href : null } catch (e) { return null } };
  const clean = (t) => String(t || '').replace(/\s+/g, ' ').trim();
  const push = (o) => {
    if (!o.title || !(o.price > 0)) return;
    const key = (o.url || '') + '|' + o.title.toLowerCase() + '|' + o.price;
    if (seen.has(key)) return;
    seen.add(key); out.push(o);
  };
  const firstImage = (img) => { img = [].concat(img || [])[0]; return abs(img && typeof img === 'object' ? img.url : img); };
  // The product's own picture, as the store shows it. Stores lazy-load pictures, so look past
  // placeholder src values to data-src / srcset, and pick the biggest image in the listing.
  let picIndex = 0;
  const fromSrcset = (v) => { const parts = String(v || '').split(',').map((x) => x.trim().split(/\s+/)[0]).filter(Boolean); return parts[parts.length - 1]; };
  const imgUrl = (img) => {
    if (!img) return null;
    if (img.getAttribute('content')) return abs(img.getAttribute('content'));
    const lazy = img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || img.getAttribute('data-original') || fromSrcset(img.getAttribute('data-srcset'));
    const src = img.currentSrc || img.getAttribute('src') || '';
    const placeholder = !src || /^data:|blank|spacer|placeholder|transparent|\.gif(\?|$)/i.test(src);
    const source = img.closest('picture') && img.closest('picture').querySelector('source[srcset]');
    return abs(placeholder ? (lazy || fromSrcset(img.getAttribute('srcset')) || (source && fromSrcset(source.getAttribute('srcset')))) : src);
  };
  const bestImg = (scope) => {
    let best = null, area = 0;
    for (const img of scope.querySelectorAll('img')) {
      const r = img.getBoundingClientRect(), a = Math.max(r.width * r.height, (img.naturalWidth || 0) * (img.naturalHeight || 0));
      if (a > area && r.width >= 40 && r.height >= 40) { best = img; area = a; }
    }
    return best || scope.querySelector('img');
  };
  const pic = (img) => {
    if (!img) return { image: null };
    const image = imgUrl(img);
    // Mark it so Luma can take a picture of it straight off the page if the address doesn't work.
    const id = String(picIndex++);
    img.setAttribute('data-luma-pic', id);
    // Weak: no address, or the picture on screen is itself the placeholder (nothing better found).
    const shown = abs(img.currentSrc || img.getAttribute('src') || '');
    const weak = !image || (image === shown && (!img.complete || (img.naturalWidth || 0) < 40));
    return { image, pic: id, image_weak: weak };
  };
  // 1. schema.org JSON-LD (most stores publish this)
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
    let data; try { data = JSON.parse(s.textContent) } catch (e) { continue }
    const walk = (n) => {
      if (!n || typeof n !== 'object') return;
      if (Array.isArray(n)) { n.forEach(walk); return; }
      const type = [].concat(n['@type'] || []).join(' ');
      if (/\bProduct\b/i.test(type)) {
        let price = null, currency = null, url = n.url;
        for (const o of [].concat(n.offers || [])) {
          const p = parseFloat(o.price ?? o.lowPrice ?? (o.priceSpecification || {}).price);
          if (p > 0 && (price === null || p < price)) { price = p; currency = o.priceCurrency || currency; url = url || o.url; }
        }
        push({ title: clean(n.name).slice(0, 200), price, currency, url: abs(url || location.href), image: firstImage(n.image),
               rating: n.aggregateRating ? parseFloat(n.aggregateRating.ratingValue) || null : null, source: 'json-ld' });
      }
      if (n.itemListElement) walk([].concat(n.itemListElement).map((e) => (e && e.item) || e));
      if (n['@graph']) walk(n['@graph']);
    };
    walk(data);
  }
  // 2. schema.org microdata
  for (const el of document.querySelectorAll('[itemtype*="schema.org/Product"]')) {
    const name = el.querySelector('[itemprop="name"]'), price = el.querySelector('[itemprop="price"]');
    const link = el.querySelector('a[href]'), meta = el.querySelector('meta[itemprop="image"]'), img = bestImg(el);
    const shown = pic(img);
    if (meta && !shown.image) { shown.image = abs(meta.getAttribute('content')); }
    if (name && price) push({ title: clean(name.getAttribute('content') || name.textContent).slice(0, 200),
      price: parseFloat(String(price.getAttribute('content') || price.textContent).replace(/[^0-9.]/g, '')), currency: 'USD',
      url: abs(link && link.getAttribute('href')), ...shown, source: 'microdata' });
  }
  // 3. visible product tiles: a price, near a link and a picture
  const PRICE = /\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)/;
  const candidates = [];
  for (const e of document.querySelectorAll('body *')) {
    if (candidates.length > 500) break;
    const t = e.textContent || '';
    if (e.children.length <= 3 && t.length < 40 && PRICE.test(t) && e.getClientRects().length) candidates.push(e);
  }
  for (const priceEl of candidates) {
    if (out.length >= 60) break;
    let card = priceEl;
    for (let i = 0; i < 7 && card.parentElement; i++) {
      card = card.parentElement;
      if (card.querySelector('a[href]') && card.querySelector('img')) break;
    }
    const links = [...card.querySelectorAll('a[href]')];
    if (!links.length) continue;
    const link = links.find((a) => clean(a.textContent).length > 12) || links[0];
    const titleEl = card.querySelector('h2, h3, h4, [data-testid*="title" i], [class*="title" i], [class*="name" i]') || link;
    const title = clean(titleEl.getAttribute('title') || titleEl.getAttribute('aria-label') || titleEl.textContent);
    const m = PRICE.exec(priceEl.textContent);
    if (title.length > 8 && m) push({ title: title.slice(0, 200), price: parseFloat(m[1].replace(/,/g, '')), currency: 'USD',
      url: abs(link.getAttribute('href')), ...pic(bestImg(card)), source: 'page' });
  }
  return out.slice(0, 60);
}
"""

STOPWORDS = {"the", "a", "an", "for", "and", "with", "of", "to", "in", "on", "new", "me", "my", "best", "cheap", "cheapest", "deal", "deals", "price", "buy"}
ACCESSORY = {"case", "cover", "protector", "charger", "cable", "strap", "band", "skin", "replacement", "compatible", "holder", "stand", "sticker",
             "decal", "mount", "adapter", "sleeve", "tips", "earhooks", "refurbished", "renewed", "used", "parts"}


def stores_from_env(env):
    raw = (env or {}).get("LUMA_SHOP_STORES_JSON")
    if not raw:
        return DEFAULT_STORES
    stores = json.loads(raw)
    if not isinstance(stores, list) or not all(isinstance(s, dict) and s.get("name") and "{q}" in str(s.get("search", "")) for s in stores):
        raise ValueError("LUMA_SHOP_STORES_JSON must be a list of {name, search} with {q} in the search URL.")
    return [{"id": s.get("id") or re.sub(r"\W+", "", s["name"].lower()), "name": s["name"], "search": s["search"]} for s in stores]


# What stores call the thing and what people call it: "PlayStation 5 Console" is a "ps5".
ALIASES = [(re.compile(r"\bplay ?station ?([345])\b"), r"ps\1"), (re.compile(r"\bnintendo switch\b"), "switch"),
           (re.compile(r"\bxbox series ([xs])\b"), r"xbox series\1"), (re.compile(r"\bair ?pods\b"), "airpods")]
# A game, a controller or a gift card *for* the device, when they asked for the device itself.
CONTENT_FOR = {"esrb", "rating", "rated", "game", "games", "controller", "dualsense", "headset", "membership", "dlc", "gift", "subscription",
               "faceplate", "remote", "voucher"}
# Words that name a device and nothing else: when that's all they asked for, they want the device.
DEVICE = {"ps5", "ps4", "ps3", "xbox", "seriesx", "seriess", "one", "switch", "oled", "lite", "steam", "deck", "quest", "meta", "console",
          "slim", "digital", "edition", "pro", "portal"}


def tokens(text):
    text = str(text).lower()
    for pattern, short in ALIASES:
        text = pattern.sub(short, text)
    words = re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text)
    words = [re.sub(r"^(\d+)(?:st|nd|rd|th)$", r"\1", w) for w in words]  # "2nd gen" is generation 2
    return [t for t in words if t not in STOPWORDS and (len(t) > 1 or t.isdigit())]


# A store's format button read as if it were a product's name: Amazon puts "PlayStation 5 - disc" and its price under every game.
FORMAT_LABEL = re.compile(r"^(?:platform\s*:\s*)?(?:play ?station ?\d|ps\d|xbox(?: series [xs]| one)?|(?:nintendo )?switch(?: 2| oled| lite)?|pc|mac|steam)"
                          r"\s*[-–|:]\s*(?:disc|digital(?: code| download)?|download|physical|online code|key ?card)\s*$", re.I)
BUNDLED = re.compile(r"\b(?:with|w/|includes?|including|plus|and)\b[^,;|]*\b(?:" + "|".join(sorted(ACCESSORY)) + r")\b")
FOR_SOMETHING = re.compile(r"\b(?:for|compatible with|fits|works with)\b")


def relevance(query, title):
    """How well a listing matches what they asked for, 0 to 1. Accessories for the thing rank low."""
    want = set(tokens(query))
    have = set(tokens(title))
    if not want:
        return 0.0
    score = len(want & have) / len(want)
    numbers = {t for t in want if any(ch.isdigit() for ch in t)}
    if numbers and not numbers <= have:
        score *= 0.5  # "AirPods Pro 2" shouldn't match the first generation
    words = tokens(title)
    just_the_device = all(w in DEVICE or w.isdigit() for w in want)
    if just_the_device and any(w in CONTENT_FOR for w in words) and not ({"console", "bundle"} & set(words)):
        score *= 0.35  # "Ghost of Yotei PS5 ESRB Rating: Mature" is a game, not the PS5
    elif just_the_device and not ({"console", "bundle"} & set(words)):
        named = str(title).lower()
        for pattern, short in ALIASES:
            named = pattern.sub(short, named)
        first = min((m.start() for w in want for m in [re.search(rf"\b{re.escape(w)}\b", named)] if m), default=None)
        made_for = FOR_SOMETHING.search(named)
        if first is not None and made_for and made_for.start() < first:
            score *= 0.35  # "KontrolFreek grips for PlayStation 4 and PlayStation 5": made for it, not it
    extra = [i for i, w in enumerate(words) if w in ACCESSORY and w not in want]
    if extra:
        lowered = str(title).lower()
        first = min((i for i, w in enumerate(words) if w in want), default=len(words))
        # "AirPods Pro 2 with MagSafe Case" is the thing itself; "Case for AirPods Pro 2" is not.
        accessory = any(i < first for i in extra) or FOR_SOMETHING.search(lowered) or not BUNDLED.search(lowered) \
            or any(w in {"refurbished", "renewed", "used", "parts", "replacement"} for w in (words[i] for i in extra))
        if accessory:
            score *= 0.35
    return round(score, 3)


def parse_price(value):
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    m = re.search(r"(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)", str(value or ""))
    return float(m[1].replace(",", "")) if m else None


def rank(query, offers, max_price=None, min_relevance=0.6):
    """Real matches only, cheapest first, one per store and title."""
    kept, seen = [], set()
    for offer in offers:
        price = parse_price(offer.get("price"))
        if not price or (max_price and price > max_price) or FORMAT_LABEL.match(" ".join(str(offer.get("title", "")).split())):
            continue
        score = relevance(query, offer.get("title", ""))
        if score < min_relevance:
            continue
        key = (offer.get("store"), re.sub(r"\W+", " ", offer.get("title", "").lower()).strip()[:80])
        if key in seen:
            continue
        seen.add(key)
        kept.append({**offer, "price": round(price, 2), "relevance": score})
    if len(kept) >= 3:  # one "match" at a fraction of what every other store charges is a different thing, read wrong
        middle = sorted(o["price"] for o in kept)[len(kept) // 2]
        kept = [o for o in kept if o["price"] >= 0.3 * middle]
    kept.sort(key=lambda o: (o["price"], -o["relevance"]))
    return kept


def money(value):
    return f"${value:,.2f}".replace(".00", "")


def compare(query, browser, activity, stores, max_price=None, per_store=12, check=None):
    """Visit each store's search page, read listings, rank them. Steps and pictures go to `activity`."""
    query = " ".join(str(query).split())[:120]
    if len(query) < 2:
        raise ValueError("Tell me what to look for.")
    found, checked, skipped = [], [], []
    for store in stores:
        if check:
            check()
        activity.step(f"Checking {store['name']}")
        url = store["search"].replace("{q}", urllib.parse.quote_plus(query))
        try:
            browser.open(url)
            browser.scroll("down", 2)
            snap = browser.screenshot()
            activity.shot(snap.get("jpeg_base64"), snap.get("url"), snap.get("title"))
            listings = browser.products() or []
        except Exception as error:  # one store being down or blocking shouldn't sink the search
            if error.__class__.__name__ == "Stopped":
                raise
            skipped.append({"store": store["name"], "reason": str(error)[:160]})
            continue
        checked.append(store["name"])
        for item in listings[:60]:
            found.append({**item, "store": store["name"], "store_id": store["id"]})
        good = rank(query, [f for f in found if f["store_id"] == store["id"]], max_price)[:per_store]
        shots = page_pictures(browser, good[:3])
        for item in found:
            if item["store_id"] == store["id"] and item.get("pic") in shots:
                item["image_shot"] = shots[item["pic"]]
        activity.step(f"{store['name']}: {len(good)} match{'es' if len(good) != 1 else ''}" + (f", from {money(good[0]['price'])}" if good else ""), done=True)
    offers = rank(query, found, max_price)
    # Keep the list readable: the best few, at most three per store.
    per = {}
    trimmed = []
    for offer in offers:
        if per.get(offer["store"], 0) >= 3:
            continue
        per[offer["store"]] = per.get(offer["store"], 0) + 1
        trimmed.append(offer)
    trimmed = trimmed[:12]
    for offer in trimmed:
        offer.pop("pic", None)
        offer.pop("image_weak", None)
    activity.results(trimmed)
    return {"query": query, "offers": trimmed, "best": trimmed[0] if trimmed else None, "checked": checked, "skipped": skipped}


def page_pictures(browser, offers):
    """Where a listing's picture is missing or still a placeholder, take it straight off the store's page."""
    wanted = [o["pic"] for o in offers if o.get("pic") and (o.get("image_weak") or not o.get("image"))]
    if not wanted or not hasattr(browser, "pictures"):
        return {}
    try:
        shots = browser.pictures(wanted) or {}
    except Exception:  # a picture is nice to have; never fail the search over it
        return {}
    return {pic: "data:image/jpeg;base64," + data for pic, data in shots.items() if data}


def summary(result):
    offers, best = result["offers"], result["best"]
    if not best:
        where = ", ".join(result["checked"]) or "the stores I tried"
        why = f" ({result['skipped'][0]['store']} wouldn't load.)" if result["skipped"] else ""
        return f"I checked {where} and didn't find a real match for {result['query']}.{why} Want me to try different words?"
    others = []
    for offer in offers[1:]:
        if offer["store"] != best["store"] and offer["store"] not in [o.split(" ")[0] for o in others]:
            others.append(f"{offer['store']} {money(offer['price'])}")
        if len(others) == 2:
            break
    line = f"Cheapest I found: {best['title'][:80]} for {money(best['price'])} at {best['store']}."
    if others:
        line += " Next best: " + ", ".join(others) + "."
    return line + " Want me to add it to your cart, or watch the price for a drop?"
