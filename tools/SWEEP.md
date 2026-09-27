# Daily price sweep — procedure

Runs every morning at ~06:00 Brussels as a GitHub Action
(`.github/workflows/price-sweep.yml` → `tools/sweep.py`). Goal: refresh
`prices.json` (and `changelog.json` when something changed) with the current
PS5 pre-order / sale prices of *Call of Duty: Modern Warfare 4*, commit, and
redeploy GitHub Pages. `tools/sweep.py` calls the Anysite REST API
(`POST https://api.anysite.io/api/<path>`, header `access-token`, JSON body =
params) — the same endpoints listed below, which `discover` also names when the
sweep is done by hand through the Anysite MCP.

## Ground rules

1. **Never invent a price.** A price goes in only when it was read from the
   shop (or from idealo/Anysite) during this run. If a shop cannot be read,
   list it under `unavailable` with a short reason. Do not copy yesterday's
   price for a shop that failed today.
2. Keep the offer `shop` names exactly as below — the change detection keys on
   `shop|edition|format`.
3. Only edit `prices.json` / `changelog.json` (via the script). Never touch
   the page HTML.
4. If fewer than 3 shops could be read, the script refuses to update — that is
   intended. Just report it.
5. `edition` ∈ `standard`, `steelbook`, `vault`; `format` ∈ `disc`, `digital`.

## Sources (Anysite)

REST path = `/api/<source>/<category>[/<endpoint>]`, e.g. `amazon` → `products`
→ `products` is `POST /api/amazon/products`; `idealo` → `products` →
`products_offers` is `POST /api/idealo/products/offers`. When sweeping by hand
through the MCP, call `discover(source, category)` first if unsure about params.

| # | shop (exact name) | edition / format | how |
|---|---|---|---|
| 1 | `Amazon.fr` | standard / disc | `amazon` → `products` → `products`, params `{domain:"amazon.fr", asin:"B0H37PK1NX"}` → `price`, `list_price`. url `https://www.amazon.fr/dp/B0H37PK1NX` |
| 2 | `Amazon.de` | standard / disc | same, `{domain:"amazon.de", asin:"B0H37MK6VZ"}`. url `https://www.amazon.de/dp/B0H37MK6VZ` |
| 3 | `Amazon.nl` | standard / disc | `amazon` → `products_search`, `{domain:"amazon.nl", query:"Call of Duty Modern Warfare 4 PS5", count:8}`. Include only if a result is clearly MW4 for PS5 (not MWII/MWIII/BO7); otherwise `unavailable` "no MW4 PS5 listing yet". |
| 4 | `MediaMarkt (BE) — UK version` | standard / disc | `webparser` → `render` → `render`, `{url:"https://www.mediamarkt.be/nl/product/_call-of-duty-modern-warfare-4-uk-ps5-2238571.html", only_main_content:true, strip_all_tags:true}` → first `€xx,xx` after the product title. |
| 5 | `MediaMarkt (BE) — FR version` | standard / disc | same with `https://www.mediamarkt.be/nl/product/_call-of-duty-modern-warfare-4-ps5-2238573.html` |
| 6 | `bol.com` | standard / disc | `bol` → `products` → `products`, `{product:"9300000301583191"}` → `price`. url `https://www.bol.com/be/nl/p/call-of-duty-modern-warfare-4-ps5/9300000301583191/` |
| 7 | `bol.com — Steelbook Edition` | steelbook / disc | same, `{product:"9300000301414410"}`. url `https://www.bol.com/be/nl/p/call-of-duty-modern-warfare-4-steelbook-edition-ps5/9300000301414410/` |
| 8 | `Coolblue (BE)` | standard / disc | `coolblue` → `products` → `products`, `{product:"980723"}` → `price` (NL listing; BE is normally identical — keep that note). url `https://www.coolblue.be/nl/product/980723/call-of-duty-modern-warfare-4-ps5.html` |
| 9 | `Smartoys (BE)` | standard / disc | `webparser` → `parse` → `parse`, `{url:"https://www.smartoys.be/catalog/jeux-video-playstation-call-duty-modern-warfare-version-ps5-p-0196388866243.html", only_main_content:true, strip_all_tags:true}` → price appears as `74` newline `.99€` after "NEUF". |
| 10 | `idealo.de — <shop_name>` | standard / disc | `idealo` → `products` → `products_offers`, `{product:"210757850", country:"de", count:20}` → take the offer with the lowest `price`; shop name = `idealo.de — ` + `shop_name`; note = "Cheapest German shop on idealo.de. Shipping extra (€<total_price> delivered in DE); delivery to Belgium not guaranteed."; `ships_be:"check"`; url `https://www.idealo.de/preisvergleich/OffersOfProduct/210757850_-call-of-duty-modern-warfare-4-ps5.html`. Skip offers from `coolblue.de` (already covered by Coolblue BE). |
| 11 | `PlayStation Store (BE)` | standard / digital | `webparser` → `render` → `render`, `{url:"https://store.playstation.com/nl-be/product/EP0002-PPSA07950_00-CODMW4VAULT00001", strip_all_tags:true}`. In the "Edities:" block: price after `MW4-Standard … Instant items voor BO7/WZ` is the Standard price. url `https://store.playstation.com/nl-be/product/EP0002-PPSA07950_00-CODMW4STANDARD01` |
| 12 | `PlayStation Store (BE)` | vault / digital | same page: the price right after the title / after `MW4 Vault … DMZ Deployment Bonus`. url `https://store.playstation.com/nl-be/product/EP0002-PPSA07950_00-CODMW4VAULT00001` |

Best-effort extras (try once with `webparser/render`; on failure list under
`unavailable` with reason "blocked by bot protection" / "no listing found"):

* `Fnac.be` — `https://www.fr.fnac.be/a23163460/Call-Of-Duty-Modern-Warfare-4-PS5-FR-Jeu-video-Playstation-5`
* `Dreamland` — `https://www.dreamland.be/fr/produits/ps5-call-of-duty-modern-warfare-4-fr/02398938`
* `Game Mania` — `https://www.gamemania.be/nl/search?q=modern+warfare+4`
* `Krëfel` — `https://www.krefel.be/nl/search?text=modern%20warfare%204`

Notes to keep per shop (copy from the current `prices.json` unless something
changed): language of the box, delivery remarks, the PS Store early-access and
loyalty-discount remarks.

## How a run works

1. `tools/sweep.py` reads every source above (one call each, the extras
   best-effort) and writes `new_offers.json`:

```json
{
  "offers": [
    {"shop":"Amazon.fr","edition":"standard","format":"disc","price":59.90,"list_price":79.99,
     "url":"https://www.amazon.fr/dp/B0H37PK1NX","note":"…","ships_be":"yes"}
  ],
  "unavailable": [ {"shop":"Fnac.be","reason":"blocked by bot protection"} ]
}
```

2. It hands that file to `tools/apply_update.py`, which validates, diffs against
   the current `prices.json`, refreshes the `updated` timestamp and writes a
   changelog line only when a price moved or a shop was really (de)listed
   (a shop that merely could not be read is not logged as gone/new). It exits
   2 and writes nothing when fewer than 3 valid offers came in — the workflow
   then fails visibly instead of publishing a half-empty page.
3. The workflow commits `prices.json` / `changelog.json` as `dmz-price-bot`
   and redeploys GitHub Pages.

Manual run: Actions tab → "Price sweep & deploy" → Run workflow.
Local test: `ANYSITE_API_KEY=… SWEEP_DRY_RUN=1 python3 tools/sweep.py`.
`SWEEP_EXTRAS=0` skips the four best-effort shops (saves credits).

`apply_update.py` options: `--note "text"` adds a manual log line (add a
`"version"` field to the entry in `changelog.json` when the page itself
changed); `--dry-run` shows the diff without writing.
