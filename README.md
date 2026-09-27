# dmz-countdown
DMZ2.0 Countdown &amp; pricewatch


Static fan page, hosted on GitHub Pages: **https://tceusters.github.io/dmz-countdown/**

* Countdown to the launch of *Call of Duty: Modern Warfare 4* incl. DMZ —
  23 Oct 2026, 00:00 Brussels (PS Store unlock, 22 Oct 22:00 UTC).
* Version chip in the header (`v3 log`) — click it for the change history.
* PS5 price watch for Belgian/Dutch shops, Amazon DE/FR and the PlayStation
  Store, cheapest offer highlighted. Refreshed every morning (~06:00 Brussels)
  by the GitHub Action in `.github/workflows/price-sweep.yml`, which calls the
  Anysite API (secret `ANYSITE_API_KEY`) and redeploys the page.
* `widget/dmz-widget.js` — iPhone home-screen widget (Scriptable app), clock only.

## Files

| file | what |
|---|---|
| `index.html` | the whole page (HTML + CSS + JS, no build step) |
| `prices.json` | current offers + shops that could not be read; `updated` = time of the last sweep (UTC) |
| `changelog.json` | intel log entries, newest first |
| `tools/sweep.py` | daily sweep: reads every shop through the Anysite API and calls `apply_update.py` |
| `tools/apply_update.py` | merges a sweep into the two JSON files and writes a log line when something changed |
| `tools/SWEEP.md` | the procedure and the exact list of sources |
| `.github/workflows/price-sweep.yml` | schedule (06:00 Brussels), commit, GitHub Pages deploy |
| `widget/dmz-widget.js` | Scriptable widget for iPhone |

## Manual edits

* Add a log line: edit `changelog.json` (newest entry first). Give the entry a
  `"version"` when the page itself changed; the chip shows the newest version.
* Change the release moment: edit `T0` at the top of the `<script>` block in
  `index.html`.
* Add or remove a shop: edit `SOURCES` in `tools/sweep.py` (and the table in
  `tools/SWEEP.md`); `prices.json` is what the page shows.

## Setup (once)

1. Settings → Pages → Source: **GitHub Actions**.
2. Settings → Secrets and variables → Actions → New repository secret
   `ANYSITE_API_KEY` (from app.anysite.io → Billing).
3. Actions tab → "Price sweep & deploy" → Run workflow, to do the first sweep
   and deploy by hand.

Unofficial fan page, not affiliated with Activision or Sony.
