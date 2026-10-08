# Progress
## 2026-10-08
- Scoped: only HTML emitter is scripts/build_site.py; overlay was a close-only line.
- Found: 10-08 point = noon snapshot (11:41) vs 上证 kline close → not comparable.
- Done: OHLC cache (sh000001_ohlc.json), candles on shared scale, range
  selector (近20日 default), 组合/上证/超额 % strip, tooltip + side panel
  with real OHLC and both day %.
- Verified: 897 passed / 12 skipped; headless Chromium at 1280px and 400px,
  no console errors. 10-08: 组合 +0.31% (11:41), 上证 −0.27% at run,
  −0.79% close (3842.195 → 3811.904), 超额 +0.58% vs run-time 上证.
- Dates with no candle (all holidays with a pipeline snapshot): 04-06,
  04-12, 05-01, 05-04, 05-05, 06-19, 09-25.
- Fix: zoomed ranges dropped the 1M (0%) baseline; STARTING is always in the y-range again (owner report).
- Owner ask: per-stock day %. Holding `d` = snapshot price / the run's own
  prices.json prev_close (quote dated that day, price == the mark), else "—".
  279/364 holding-days covered (old prices.json are `{}`).
- Side panel: 当日 · 累计 per stock; check line Σ holding P&L vs 组合 day P&L
  in yuan; RAISE_STOP/HOLD no longer count as trades.
- FOUND: 普洛药业 ex-dividend 2026-10-08 (10派1.39, prev_close 27.74→27.61).
  position_manager has no dividend handling → book short ≈ ¥236 (1700 sh).
  Flag `xd` marks book prev ≠ quote prev_close, judged only when yesterday's
  point is a ≥15:00 mark of the previous session: 54 → 11 flags. Others
  (04-14, 06-10, 09-04) cluster per day both directions = previous "close"
  snapshot not at the real close — separate issue, not investigated.
- Holiday-run snapshot (09-25) as previous point no longer blanks 超额 (pdi).
