# dmz-countdown
DMZ2.0 Countdown &amp; pricewatch


Static fan page, hosted on GitHub Pages: **https://tceusters.github.io/dmz-countdown/**

* Countdown to the launch of *Call of Duty: Modern Warfare 4* incl. DMZ —
  23 Oct 2026, 00:00 Brussels (PS Store unlock, 22 Oct 22:00 UTC).
* Version chip in the header (`v3 log`) — click it for the change history.
* PS5 price watch for Belgian/Dutch shops, Amazon DE/FR and the PlayStation
  Store, cheapest offer highlighted. Refreshed every morning by a scheduled
  Claude task that runs on Tom's PC (reads the shops through the Anysite MCP,
  then pushes `prices.json` / `changelog.json` to `main`). Every push to
  `main` redeploys the page via the GitHub Action.
* `widget/dmz-widget.js` — iPhone home-screen widget (Scriptable app), clock only.

## Files

| file | what |
|---|---|
| `index.html` | the whole page (HTML + CSS + JS, no build step) |
| `prices.json` | current offers + shops that could not be read; `updated` = time of the last sweep (UTC) |
| `changelog.json` | intel log entries, newest first |
| `tools/apply_update.py` | merges a sweep into the two JSON files and writes a log line when something changed |
| `tools/SWEEP.md` | the daily procedure (Claude task) and the exact list of sources |
| `tools/sweep.py` | optional: the same sweep through the Anysite REST API, for an API plan |
| `.github/workflows/price-sweep.yml` | GitHub Pages deploy on every push (+ optional API sweep on manual start) |
| `widget/dmz-widget.js` | Scriptable widget for iPhone |

## Manual edits

* Add a log line: edit `changelog.json` (newest entry first). Give the entry a
  `"version"` when the page itself changed; the chip shows the newest version.
* Change the release moment: edit `T0` at the top of the `<script>` block in
  `index.html`.
* Add or remove a shop: edit `SOURCES` in `tools/sweep.py` (and the table in
  `tools/SWEEP.md`); `prices.json` is what the page shows.

## Setup (once)

1. Settings → Pages → Source: **GitHub Actions**. Every push to `main` then
   deploys the page automatically.
2. The daily sweep is a scheduled Claude task ("DMZ price sweep") bound to
   Tom's PC; see `tools/SWEEP.md`. No GitHub secret is needed for it.
3. Optional, only with an Anysite *API* plan: add the secret `ANYSITE_API_KEY`
   and start the workflow by hand to sweep from GitHub's side.

Unofficial fan page, not affiliated with Activision or Sony.
