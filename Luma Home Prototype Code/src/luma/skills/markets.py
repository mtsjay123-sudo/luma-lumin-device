"""Stock, index and crypto prices, read live from free public quotes: no account, no API key.

Stocks and indexes come from Stooq's public CSV quotes (the latest price, and the last two
daily closes for the day's move). Crypto comes from Coinbase's public market stats (the
price now against 24 hours ago). The price is always read right then, never remembered, and
a quote that can't be read is reported as missing, never guessed.
"""
from __future__ import annotations

import csv
import io
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone

NAMES = {
    "apple": "AAPL", "tesla": "TSLA", "nvidia": "NVDA", "microsoft": "MSFT", "amazon": "AMZN", "google": "GOOGL", "alphabet": "GOOGL",
    "meta": "META", "facebook": "META", "netflix": "NFLX", "amd": "AMD", "intel": "INTC", "disney": "DIS", "nike": "NKE",
    "coca cola": "KO", "coca-cola": "KO", "coke": "KO", "walmart": "WMT", "costco": "COST", "starbucks": "SBUX", "boeing": "BA",
    "jpmorgan": "JPM", "jp morgan": "JPM", "palantir": "PLTR", "coinbase": "COIN", "gamestop": "GME", "amc": "AMC", "uber": "UBER",
    "spotify": "SPOT", "paypal": "PYPL", "shopify": "SHOP", "salesforce": "CRM", "oracle": "ORCL", "ibm": "IBM", "snapchat": "SNAP",
    "snap": "SNAP", "roblox": "RBLX", "robinhood": "HOOD", "ford": "F", "rivian": "RIVN", "lucid": "LCID", "pfizer": "PFE",
    "moderna": "MRNA", "berkshire": "BRK-B", "visa": "V", "mastercard": "MA", "target": "TGT", "home depot": "HD", "mcdonald's": "MCD",
    "mcdonalds": "MCD", "chipotle": "CMG", "broadcom": "AVGO", "tsmc": "TSM", "airbnb": "ABNB", "doordash": "DASH", "reddit": "RDDT",
}
INDEXES = {"s&p 500": "^SPX", "s&p": "^SPX", "sp500": "^SPX", "s and p": "^SPX", "the market": "^SPX", "stock market": "^SPX", "stocks today": "^SPX",
           "dow jones": "^DJI", "dow": "^DJI", "nasdaq": "^NDQ"}
INDEX_NAMES = {"^SPX": "the S&P 500", "^DJI": "the Dow", "^NDQ": "the Nasdaq"}
CRYPTO = {"bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH", "solana": "SOL", "dogecoin": "DOGE", "doge": "DOGE", "xrp": "XRP",
          "litecoin": "LTC", "cardano": "ADA"}
CRYPTO_NAMES = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "DOGE": "Dogecoin", "XRP": "XRP", "LTC": "Litecoin", "ADA": "Cardano"}
MARKET_WORDS = re.compile(r"\b(?:stocks?|shares?|share price|stock price|trading at|ticker|market|markets|s&p|s and p|sp500|dow|nasdaq|"
                          r"bitcoin|btc|ethereum|eth|crypto|solana|doge(?:coin)?|xrp|litecoin|cardano|price of)\b|\$[a-z]{1,5}\b", re.I)
TICKER = re.compile(r"\$([A-Z]{1,5}(?:-[A-Z])?)\b|\b([A-Z]{2,5})\b(?= (?:stock|shares|share price|price|ticker))")
NOT_TICKERS = {"I", "A", "AI", "US", "USA", "OK", "TV", "CEO", "IPO", "ETF", "THE", "AND", "NFT", "LOL", "NBA", "NFL", "WHAT", "HOW"}

STOOQ_QUOTE = "https://stooq.com/q/l/?s={s}&f=sd2t2ohlcv&h&e=csv"
STOOQ_DAILY = "https://stooq.com/q/d/l/?s={s}&i=d&d1={d1}&d2={d2}"
COINBASE = "https://api.exchange.coinbase.com/products/{p}-USD/stats"
YAHOO_NEWS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={s}&region=US&lang=en-US"


def wants(text):
    """A question about a price, not just a word like 'market' in passing ('farmers market')."""
    text = str(text or "")
    return bool(MARKET_WORDS.search(text)) and bool(symbols(text)) and not re.search(r"\b(?:farmers?|flea|super) ?market\b", text, re.I)


def symbols(text, limit=3):
    """('stock', 'TSLA', 'Tesla') / ('index', '^SPX', 'the S&P 500') / ('crypto', 'BTC', 'Bitcoin'), in the order they were said."""
    raw, lowered = str(text or ""), str(text or "").lower()
    found = []
    def add(kind, sym, name, at):
        if not any(f[1] == sym for f in found):
            found.append((at, kind, sym, name))
    for m in TICKER.finditer(raw):
        sym = m.group(1) or m.group(2)
        if sym not in NOT_TICKERS:
            add("stock", sym, sym, m.start())
    for table, kind in ((NAMES, "stock"), (INDEXES, "index"), (CRYPTO, "crypto")):
        for word in sorted(table, key=len, reverse=True):
            m = re.search(rf"(?<![\w$]){re.escape(word)}(?![\w])", lowered)
            if m:
                sym = table[word]
                name = INDEX_NAMES.get(sym) if kind == "index" else CRYPTO_NAMES.get(sym) if kind == "crypto" else word.title()
                add(kind, sym, name, m.start())
    general = re.search(r"\b(?:how(?:'s| is| are) (?:the )?(?:market|markets|stocks)|stock market)\b", lowered)
    if general and not found:
        add("index", "^SPX", "the S&P 500", general.start())
    return [(k, s, n) for _, k, s, n in sorted(found)][:limit]


def _get(url, fetch=None):
    if fetch:
        return fetch(url)
    from luma.integrations.browser import check_url
    request = urllib.request.Request(check_url(url), headers={"User-Agent": "Mozilla/5.0 (Luma personal assistant)", "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read(500_000)


def _stooq(sym):
    return (sym.lower() if sym.startswith("^") else sym.lower().replace(".", "-") + ".us")


def stock(sym, now=None, fetch=None):
    """The latest price and the day's move for a stock or index, or None when there's no quote."""
    rows = list(csv.DictReader(io.StringIO(_get(STOOQ_QUOTE.format(s=_stooq(sym)), fetch).decode("utf-8", "replace"))))
    if not rows:
        return None
    row = rows[0]
    try:
        price = float(row.get("Close") or "")
    except ValueError:
        return None  # "N/D": no such symbol, or no data
    out = {"symbol": sym, "price": price, "date": row.get("Date") or "", "source": "Stooq", "url": f"https://stooq.com/q/?s={_stooq(sym)}"}
    now = now or datetime.now(timezone.utc)
    try:
        daily = _get(STOOQ_DAILY.format(s=_stooq(sym), d1=(now - timedelta(days=14)).strftime("%Y%m%d"), d2=now.strftime("%Y%m%d")), fetch)
        closes = [(r["Date"], float(r["Close"])) for r in csv.DictReader(io.StringIO(daily.decode("utf-8", "replace"))) if r.get("Close") not in (None, "", "N/D")]
        before = [c for d, c in closes if d < out["date"]] if out["date"] else [c for _, c in closes[:-1]]
        if before:
            out["previous_close"] = before[-1]
            out["change_pct"] = round((price - before[-1]) / before[-1] * 100, 2)
    except Exception:
        pass  # the price alone is still right
    return out


def crypto(sym, fetch=None):
    """The price now and the move over the last 24 hours, or None."""
    data = json.loads(_get(COINBASE.format(p=sym), fetch).decode("utf-8", "replace") or "{}")
    try:
        last, opened = float(data["last"]), float(data["open"])
    except (KeyError, TypeError, ValueError):
        return None
    return {"symbol": sym, "price": last, "change_pct": round((last - opened) / opened * 100, 2) if opened else None, "window": "24h",
            "source": "Coinbase", "url": f"https://www.coinbase.com/price/{CRYPTO_NAMES.get(sym, sym).lower()}"}


def headlines(sym, fetch=None, limit=2):
    """A couple of fresh headlines about one stock."""
    from luma.skills.news import parse
    try:
        return parse(_get(YAHOO_NEWS.format(s=sym), fetch), "Yahoo Finance")[:limit]
    except Exception:
        return []


def money(price):
    return f"${price:,.2f}" if price >= 1 else f"${price:.4f}"


def line(name, sym, quote, today):
    """'Tesla (TSLA) is at $251.34, up 2.10% today.'"""
    label = name if sym.startswith("^") or quote.get("window") == "24h" else f"{name} ({sym})" if name.upper() != sym else sym
    move = ""
    if quote.get("change_pct") is not None:
        pct = quote["change_pct"]
        span = "in the last 24 hours" if quote.get("window") == "24h" else "today" if quote.get("date") == today else "on the day"
        move = f", {'up' if pct > 0 else 'down' if pct < 0 else 'flat'}" + (f" {abs(pct):.2f}%" if pct else "") + f" {span}"
    when = "" if quote.get("window") == "24h" or not quote.get("date") or quote["date"] == today else f" (last trade {quote['date']})"
    price = f"{quote['price']:,.2f}" if sym.startswith("^") else money(quote["price"])
    return f"{label} is at {price}{move}{when}."
