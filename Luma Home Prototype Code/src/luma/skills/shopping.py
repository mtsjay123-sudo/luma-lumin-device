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
    const link = el.querySelector('a[href]'), img = el.querySelector('[itemprop="image"], img');
    if (name && price) push({ title: clean(name.getAttribute('content') || name.textContent).slice(0, 200),
      price: parseFloat(String(price.getAttribute('content') || price.textContent).replace(/[^0-9.]/g, '')), currency: 'USD',
      url: abs(link && link.getAttribute('href')), image: abs(img && (img.getAttribute('content') || img.currentSrc || img.src)), source: 'microdata' });
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
    const img = card.querySelector('img');
    if (title.length > 8 && m) push({ title: title.slice(0, 200), price: parseFloat(m[1].replace(/,/g, '')), currency: 'USD',
      url: abs(link.getAttribute('href')), image: abs(img && (img.currentSrc || img.src)), source: 'page' });
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


def tokens(text):
    words = re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", str(text).lower())
    words = [re.sub(r"^(\d+)(?:st|nd|rd|th)$", r"\1", w) for w in words]  # "2nd gen" is generation 2
    return [t for t in words if t not in STOPWORDS and (len(t) > 1 or t.isdigit())]


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
        if not price or (max_price and price > max_price):
            continue
        score = relevance(query, offer.get("title", ""))
        if score < min_relevance:
            continue
        key = (offer.get("store"), re.sub(r"\W+", " ", offer.get("title", "").lower()).strip()[:80])
        if key in seen:
            continue
        seen.add(key)
        kept.append({**offer, "price": round(price, 2), "relevance": score})
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
    activity.results(trimmed)
    return {"query": query, "offers": trimmed, "best": trimmed[0] if trimmed else None, "checked": checked, "skipped": skipped}


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
