#!/usr/bin/env python3
"""
sweep.py — daily PS5 price sweep for Call of Duty: Modern Warfare 4.

Reads every source listed in tools/SWEEP.md through the Anysite REST API
(https://api.anysite.io, header `access-token`), writes the result to
new_offers.json and hands it to tools/apply_update.py, which merges it into
prices.json / changelog.json.

Environment:
  ANYSITE_API_KEY   required — Anysite API key (GitHub secret)
  SWEEP_EXTRAS=0    skip the best-effort shops (Fnac, Dreamland, Game Mania, Krëfel)
  SWEEP_DRY_RUN=1   fetch and print, but do not write prices.json / changelog.json

Exit codes: 0 ok · 2 too few sources could be read (nothing written) · 3 no API key
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.anysite.io/api"
KEY = os.environ.get("ANYSITE_API_KEY", "").strip()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.dirname(os.path.abspath(__file__))
EXTRAS = os.environ.get("SWEEP_EXTRAS", "1") != "0"
DRY = os.environ.get("SWEEP_DRY_RUN", "0") == "1"

PRICE_RE = re.compile(r"€\s?(\d{1,3}(?:[.\s]\d{3})*),(\d{2})")


# ---------------------------------------------------------------- Anysite API
def call(path, params, timeout=120):
    """POST one Anysite endpoint; returns the decoded JSON (list or dict)."""
    req = urllib.request.Request(
        f"{API}/{path.strip('/')}",
        data=json.dumps(params).encode("utf-8"),
        headers={"access-token": KEY, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {e.code} on {path}: {body}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error on {path}: {e.reason}") from None


def items(resp):
    """Normalise an API response to a list of dicts."""
    if isinstance(resp, list):
        return [x for x in resp if isinstance(x, dict)]
    if isinstance(resp, dict):
        for k in ("items", "data", "results"):
            if isinstance(resp.get(k), list):
                return [x for x in resp[k] if isinstance(x, dict)]
        return [resp]
    return []


def first(resp):
    lst = items(resp)
    if not lst:
        raise RuntimeError("empty response")
    return lst[0]


def num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"(\d+)[.,](\d{2})", str(v))
    return float(f"{m.group(1)}.{m.group(2)}") if m else None


def text_of(resp):
    it = first(resp)
    for k in ("cleaned_html", "text", "content", "html"):
        if isinstance(it.get(k), str) and it[k].strip():
            return it[k]
    raise RuntimeError("no text in webparser response")


def price_after(text, anchor, window=600):
    """First €xx,xx after `anchor` (regex) in a stripped-tags text."""
    m = re.search(anchor, text)
    if not m:
        raise RuntimeError(f"anchor not found: {anchor!r}")
    seg = text[m.end(): m.end() + window]
    p = PRICE_RE.search(seg)
    if not p:
        raise RuntimeError(f"no price after {anchor!r}")
    return float(p.group(1).replace(".", "").replace(" ", "") + "." + p.group(2))


def bot_blocked(text):
    t = text.lower()
    return any(s in t for s in ("captcha", "beveiligingscontrole", "enable js", "verify you are human", "ray id", "access denied"))


# ---------------------------------------------------------------- sources
def offer(shop, price, url, note, edition="standard", fmt="disc", list_price=None, ships_be="yes"):
    return {"shop": shop, "edition": edition, "format": fmt, "price": round(price, 2),
            "list_price": (round(list_price, 2) if list_price else None), "url": url, "note": note, "ships_be": ships_be}


def src_amazon(domain, asin, shop, note):
    it = first(call("amazon/products", {"domain": domain, "asin": asin}))
    p = num(it.get("price"))
    if p is None:
        raise RuntimeError("no price (out of stock / unlisted?)")
    lp = num(it.get("list_price"))
    return offer(shop, p, f"https://www.{domain}/dp/{asin}", note, list_price=(lp if lp and lp > p else None))


def src_amazon_nl():
    res = items(call("amazon/products/search", {"domain": "amazon.nl", "query": "Call of Duty Modern Warfare 4 PS5", "count": 8}))
    for it in res:
        t = (it.get("title") or it.get("name") or "").lower()
        if "modern warfare" in t and ("4" in t or "iv" in t.split()) and not re.search(r"\b(ii|iii|2|3)\b|black ops|warzone", t) \
                and ("ps5" in t or "playstation 5" in t or "playstation5" in t):
            p = num(it.get("price"))
            if p:
                asin = it.get("id") or it.get("asin")
                return offer("Amazon.nl", p, it.get("url") or f"https://www.amazon.nl/dp/{asin}", "Dutch listing.",
                             list_price=num(it.get("list_price")))
    raise RuntimeError("no MW4 PS5 listing yet")


def src_mediamarkt(url, shop, note):
    text = text_of(call("webparser/render", {"url": url, "only_main_content": True, "strip_all_tags": True}, timeout=150))
    if bot_blocked(text):
        raise RuntimeError("blocked by bot protection")
    p = price_after(text, r"Modern Warfare 4[^\n]*PS5", window=400)
    return offer(shop, p, url, note)


def src_bol(product_id, url, shop, note, edition="standard"):
    it = first(call("bol/products", {"product": product_id}))
    p = num(it.get("price"))
    if p is None:
        raise RuntimeError("no price")
    lp = num(it.get("list_price"))
    return offer(shop, p, url, note, edition=edition, list_price=(lp if lp and lp > p else None))


def src_coolblue():
    it = first(call("coolblue/products", {"product": "980723"}))
    p = num(it.get("price")) or num((it.get("sales_price") or {}).get("including_vat") if isinstance(it.get("sales_price"), dict) else None)
    if p is None:
        raise RuntimeError("no price")
    return offer("Coolblue (BE)", p, "https://www.coolblue.be/nl/product/980723/call-of-duty-modern-warfare-4-ps5.html",
                 "Price read from the Coolblue NL listing; BE price is normally identical.")


def src_smartoys():
    url = "https://www.smartoys.be/catalog/jeux-video-playstation-call-duty-modern-warfare-version-ps5-p-0196388866243.html"
    text = text_of(call("webparser/parse", {"url": url, "only_main_content": True, "strip_all_tags": True}))
    if bot_blocked(text):
        raise RuntimeError("blocked by bot protection")
    m = re.search(r"NEUF\s*\n\s*(\d{2,3})\s*\n\s*\.(\d{2})\s*€", text) or re.search(r"(\d{2,3})\s*\n\s*\.(\d{2})\s*€", text)
    if not m:
        raise RuntimeError("price pattern not found")
    return offer("Smartoys (BE)", float(f"{m.group(1)}.{m.group(2)}"), url, "Pre-order; store pickup in Wallonia/Brussels.")


def src_idealo():
    res = items(call("idealo/products/offers", {"product": "210757850", "country": "de", "count": 20}))
    res = [o for o in res if num(o.get("price")) and "coolblue" not in (o.get("shop_name") or "").lower()]
    if not res:
        raise RuntimeError("no offers")
    best = min(res, key=lambda o: num(o["price"]))
    total = num(best.get("total_price"))
    note = "Cheapest German shop on idealo.de. " + (f"Shipping extra (€{total:.2f} delivered in DE); " if total else "Shipping extra; ") + \
           "delivery to Belgium not guaranteed."
    return offer(f"idealo.de — {best.get('shop_name', 'shop')}", num(best["price"]),
                 "https://www.idealo.de/preisvergleich/OffersOfProduct/210757850_-call-of-duty-modern-warfare-4-ps5.html",
                 note, ships_be="check")


def src_psstore():
    url_vault = "https://store.playstation.com/nl-be/product/EP0002-PPSA07950_00-CODMW4VAULT00001"
    url_std = "https://store.playstation.com/nl-be/product/EP0002-PPSA07950_00-CODMW4STANDARD01"
    text = text_of(call("webparser/render", {"url": url_vault, "strip_all_tags": True}, timeout=150))
    out = []
    try:
        p = price_after(text, r"MW4-Standard", window=400)
        out.append(offer("PlayStation Store (BE)", p, url_std, "Digital pre-order: campaign early access from 16 Oct + bonus items.", fmt="digital", ships_be="n/a"))
    except RuntimeError as e:
        out.append(("PlayStation Store (BE) — Standard", str(e)))
    try:
        p = price_after(text, r"MW4 Vault", window=400)
        note = f"10% loyalty discount for eligible owners of a previous CoD (≈ €{p * 0.9:.2f}). Includes BlackCell season + DMZ Deployment Bonus."
        out.append(offer("PlayStation Store (BE)", p, url_vault, note, edition="vault", fmt="digital", ships_be="n/a"))
    except RuntimeError as e:
        out.append(("PlayStation Store (BE) — Vault", str(e)))
    return out


def src_extra(shop, url, anchor=r"Modern Warfare 4"):
    text = text_of(call("webparser/render", {"url": url, "only_main_content": True, "strip_all_tags": True}, timeout=100))
    if bot_blocked(text):
        raise RuntimeError("blocked by bot protection")
    if not re.search(anchor, text, re.I):
        raise RuntimeError("no listing found")
    p = price_after(text, anchor, window=500)
    return offer(shop, p, url, "Read from the shop's page; check edition/language on the shop.")


SOURCES = [
    ("Amazon.fr", lambda: src_amazon("amazon.fr", "B0H37PK1NX", "Amazon.fr",
                                    "French box, game itself is multi-language. Sold & shipped by Amazon, delivers to Belgium.")),
    ("Amazon.de", lambda: src_amazon("amazon.de", "B0H37MK6VZ", "Amazon.de", "German listing, delivers to Belgium.")),
    ("Amazon.nl", src_amazon_nl),
    ("MediaMarkt (BE) — UK version", lambda: src_mediamarkt(
        "https://www.mediamarkt.be/nl/product/_call-of-duty-modern-warfare-4-uk-ps5-2238571.html",
        "MediaMarkt (BE) — UK version", "English box. Free delivery above €50, or store pickup.")),
    ("MediaMarkt (BE) — FR version", lambda: src_mediamarkt(
        "https://www.mediamarkt.be/nl/product/_call-of-duty-modern-warfare-4-ps5-2238573.html",
        "MediaMarkt (BE) — FR version", "French box.")),
    ("bol.com", lambda: src_bol("9300000301583191",
                                "https://www.bol.com/be/nl/p/call-of-duty-modern-warfare-4-ps5/9300000301583191/", "bol.com", "Pre-order.")),
    ("bol.com — Steelbook Edition", lambda: src_bol("9300000301414410",
                                                    "https://www.bol.com/be/nl/p/call-of-duty-modern-warfare-4-steelbook-edition-ps5/9300000301414410/",
                                                    "bol.com — Steelbook Edition", "Standard game in a steelbook case.", edition="steelbook")),
    ("Coolblue (BE)", src_coolblue),
    ("Smartoys (BE)", src_smartoys),
    ("idealo.de", src_idealo),
    ("PlayStation Store (BE)", src_psstore),
]
EXTRA_SOURCES = [
    ("Fnac.be", lambda: src_extra("Fnac.be", "https://www.fr.fnac.be/a23163460/Call-Of-Duty-Modern-Warfare-4-PS5-FR-Jeu-video-Playstation-5")),
    ("Dreamland", lambda: src_extra("Dreamland", "https://www.dreamland.be/fr/produits/ps5-call-of-duty-modern-warfare-4-fr/02398938")),
    ("Game Mania", lambda: src_extra("Game Mania", "https://www.gamemania.be/nl/search?q=modern+warfare+4")),
    ("Krëfel", lambda: src_extra("Krëfel", "https://www.krefel.be/nl/search?text=modern%20warfare%204")),
]


# ---------------------------------------------------------------- main
def main():
    if not KEY:
        print("ERROR: ANYSITE_API_KEY is not set.", file=sys.stderr)
        return 3
    offers, unavailable = [], []
    for name, fn in SOURCES + (EXTRA_SOURCES if EXTRAS else []):
        try:
            res = fn()
            for r in (res if isinstance(res, list) else [res]):
                if isinstance(r, tuple):
                    unavailable.append({"shop": r[0], "reason": r[1][:80]})
                    print(f"  -  {r[0]}: {r[1]}")
                else:
                    offers.append(r)
                    print(f"  ok {r['shop']}: €{r['price']:.2f}")
        except Exception as e:  # noqa: BLE001 — one bad shop must not kill the sweep
            reason = str(e).splitlines()[0][:80] if str(e) else e.__class__.__name__
            unavailable.append({"shop": name, "reason": reason})
            print(f"  -  {name}: {reason}")
        time.sleep(1)

    payload = {"offers": offers, "unavailable": unavailable}
    out = os.path.join(ROOT, "new_offers.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"{len(offers)} offers, {len(unavailable)} unavailable → {out}")

    args = [sys.executable, os.path.join(TOOLS, "apply_update.py"), out] + (["--dry-run"] if DRY else [])
    rc = subprocess.call(args)
    try:
        os.remove(out)
    except OSError:
        pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
