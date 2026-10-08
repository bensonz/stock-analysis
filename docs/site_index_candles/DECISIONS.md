# Decisions

- **Candles on the shared equity scale, not a second scale.** Rebased by the
  same STARTING/IDXBASE factor as the old line, so the existing "one scale, two
  readings" right axis stays exact.
- **Separate OHLC cache file** instead of changing `sh000001.json` from
  `{date: close}` — the close cache is read by tests and carries 2022+ history;
  settled market.json quotes only give a close, so close and bar coverage differ.
- **No forward-filled candles.** A holiday or kline-lag day gets no candle; a
  day with only a settled quote gets a close-only tick. A fake o=h=l=c candle
  would look like real data.
- **上证 day % = close vs previous index close** (what a quote app shows), not
  vs the previous snapshot date. When the previous snapshot is not the previous
  trading day, the UI says so instead of silently comparing different spans.
- **Noon snapshots flagged.** The day's equity can be an 11:4x mark while the
  candle is the 15:00 close (2026-10-08: 上证 −0.27% at 11:35, −0.79% close).
  The run's market.json quote % is shown next to the close %.
- **Range selector, default 近20日.** 141 points on 870px = 6px per candle:
  bodies and labels do not fit. Choice kept in localStorage (try/catch).
- **Settled quotes only fill dates after the kline's last bar.** Found
  2026-09-25 (中秋) carrying a quote stamped 09-25 with 09-24's close (the
  holiday-stamping bug fixed 09-29); inside kline coverage, "no bar" means
  "not a trading day".
- **Noon snapshot with no run-time 上证 quote → no 超额.** 09-08 and 09-11
  noon runs had a DNS failure on the index fetch; comparing an 11:xx equity
  with the 15:00 close would be a wrong number, so the cell shows "—".
- **Per-stock day % from the run's own quote, not snapshot-to-snapshot.**
  It is the number a quote app shows; a book-vs-quote difference is shown as
  a ⚠ flag + a yuan gap in the check line instead of being blended away.
- **Site JS/CSS moved to scripts/site_assets/{app.js,app.css}** (owner choice
  2026-10-08), inlined at build — output stays one offline HTML. Not
  `scripts/site/`: a dir named `site` on sys.path shadows the stdlib module.
  Verified: rendered HTML identical except one blank line at each end of
  the script block.
