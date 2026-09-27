#!/usr/bin/env python3
"""
apply_update.py — merge a fresh price sweep into prices.json and log what
changed in changelog.json. Publishing (artifact republish or git push) is done
by the caller afterwards.

Usage:
  python3 tools/apply_update.py NEW_OFFERS.json [--note "text"] [--dry-run]

NEW_OFFERS.json has the same shape as prices.json (only "offers" and
"unavailable" are read):
  {
    "offers": [ {shop, edition, format, price, list_price, url, note, ships_be}, ... ],
    "unavailable": [ {shop, reason}, ... ]
  }

Rules:
  * edition ∈ {standard, steelbook, vault}; format ∈ {disc, digital}
  * price must be a number > 0; url must start with http(s)
  * a sweep with fewer than MIN_OFFERS valid offers is refused (exit 2) so a
    broken run never wipes the page
  * a changelog entry is only written when something actually changed
    (price up/down, new offer, offer gone, best deal changed) or when --note
    is given; the "updated" timestamp is refreshed on every run

Exit codes: 0 ok · 1 unreadable input · 2 too few valid offers (nothing written)
"""
import argparse
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRICES = os.path.join(ROOT, "prices.json")
CHANGELOG = os.path.join(ROOT, "changelog.json")
MIN_OFFERS = 3
MAX_LOG = 60
EDITIONS = {"standard", "steelbook", "vault"}
FORMATS = {"disc", "digital"}


def eur(p):
    return "€" + f"{p:.2f}".replace(".", ",")


def key(o):
    return f"{o['shop']}|{o['edition']}|{o['format']}"


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def validate(offers):
    good, bad = [], []
    for o in offers:
        try:
            shop = str(o["shop"]).strip()
            edition = str(o.get("edition", "standard")).lower()
            fmt = str(o.get("format", "disc")).lower()
            price = float(o["price"])
            url = str(o["url"])
            if not shop or edition not in EDITIONS or fmt not in FORMATS or price <= 0 or not url.startswith("http"):
                raise ValueError("field out of range")
            lp = o.get("list_price")
            good.append({
                "shop": shop,
                "edition": edition,
                "format": fmt,
                "price": round(price, 2),
                "list_price": (round(float(lp), 2) if lp not in (None, "", 0) else None),
                "url": url,
                "note": str(o.get("note", "") or "").strip(),
                "ships_be": str(o.get("ships_be", "yes") or "yes"),
            })
        except Exception as e:  # noqa: BLE001
            bad.append((o, str(e)))
    return good, bad


def best_of(offers):
    cands = [o for o in offers if o["edition"] != "vault"] or offers
    return min(cands, key=lambda o: o["price"]) if cands else None


def label(o):
    """Shop name plus the edition/format when it is not the plain disc version."""
    tag = []
    if o["edition"] != "standard":
        tag.append(o["edition"])
    if o["format"] != "disc":
        tag.append(o["format"])
    return o["shop"] + (f" ({', '.join(tag)})" if tag else "")


def diff(old_offers, new_offers, unavailable_now=(), unavailable_before=()):
    """Human-readable changes. A shop that merely could not be read today (or
    yesterday) is not reported as gone/new — the page already lists it under
    'not read this sweep'; only real price moves and real (de)listings count."""
    old = {key(o): o for o in old_offers}
    new = {key(o): o for o in new_offers}
    flaky = [u.lower() for u in list(unavailable_now) + list(unavailable_before)]

    def unread(o):
        s = o["shop"].lower()
        return any(s.startswith(u) or u.startswith(s) for u in flaky)

    changes = []
    for k, o in new.items():
        if k not in old:
            if not unread(o):
                changes.append(f"new: {label(o)} {eur(o['price'])}")
        elif abs(old[k]["price"] - o["price"]) >= 0.01:
            arrow = "↓" if o["price"] < old[k]["price"] else "↑"
            changes.append(f"{label(o)} {eur(old[k]['price'])} → {eur(o['price'])} {arrow}")
    for k, o in old.items():
        if k not in new and not unread(o):
            changes.append(f"gone: {label(o)}")
    return changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("new_file")
    ap.add_argument("--note", default=None, help="extra changelog line (e.g. a manual change)")
    ap.add_argument("--dry-run", action="store_true", help="print the result, write nothing")
    args = ap.parse_args()

    incoming = load(args.new_file, None)
    if incoming is None:
        print(f"ERROR: cannot read {args.new_file}", file=sys.stderr)
        return 1
    new_offers, bad = validate(incoming.get("offers", []))
    for o, why in bad:
        print(f"WARN: dropped invalid offer {o!r}: {why}", file=sys.stderr)
    if len(new_offers) < MIN_OFFERS:
        print(f"ERROR: only {len(new_offers)} valid offers (< {MIN_OFFERS}); refusing to update.", file=sys.stderr)
        return 2
    unavailable = [
        {"shop": str(u.get("shop", "")).strip(), "reason": str(u.get("reason", "")).strip()}
        for u in incoming.get("unavailable", []) if str(u.get("shop", "")).strip()
    ]

    current = load(PRICES, {"offers": [], "currency": "EUR", "game": "Call of Duty: Modern Warfare 4 (PS5)"})
    log = load(CHANGELOG, [])
    now = dt.datetime.now(dt.timezone.utc)
    today = now.strftime("%Y-%m-%d")

    changes = diff(current.get("offers", []), new_offers,
                   [u["shop"] for u in unavailable],
                   [u.get("shop", "") for u in current.get("unavailable", [])])
    old_best, new_best = best_of(current.get("offers", [])), best_of(new_offers)
    best_changed = (old_best is None) or (new_best is None) or key(old_best) != key(new_best) or abs(old_best["price"] - new_best["price"]) >= 0.01

    entries = []
    if changes:
        text = "Price sweep: " + " · ".join(changes[:6])
        if len(changes) > 6:
            text += f" · +{len(changes) - 6} more"
        if new_best:
            text += f". Best deal{' now' if best_changed else ''}: {label(new_best)} {eur(new_best['price'])}."
        entries.append({"date": today, "text": text})
    if args.note:
        entries.append({"date": today, "text": args.note.strip()})

    current["updated"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    current["offers"] = sorted(new_offers, key=lambda o: (o["price"], o["shop"]))
    current["unavailable"] = unavailable
    current.setdefault("currency", "EUR")
    current.setdefault("game", "Call of Duty: Modern Warfare 4 (PS5)")
    new_log = (entries[::-1] + log)[:MAX_LOG]

    print(f"offers: {len(new_offers)} valid, {len(bad)} dropped; unavailable: {len(unavailable)}")
    print("changes:", "; ".join(changes) if changes else "none")
    for e in entries:
        print("log +", e["text"])
    if args.dry_run:
        return 0

    with open(PRICES, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(CHANGELOG, "w", encoding="utf-8") as f:
        json.dump(new_log, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("written: prices.json, changelog.json — now republish/push them.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
