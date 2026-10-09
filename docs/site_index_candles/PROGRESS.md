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
- Click-a-position history window: any side-panel holding / 当前持仓 /
  历史交易 row opens raw daily candles (20 sessions before entry → 5 after
  exit) from the local price DB, entry/exit/add/trim markers, cost + target
  lines, stop as a step line through KNOWN levels only (OPEN `stop`,
  RAISE_STOP `new_stop`; older RAISE_STOPs lack the value), thesis, exit
  reason, and the day-by-day action timeline. 68 trades (64 closed + 4 open).
- Bug caught in browser test: `#posmodal{display:flex}` overrode `hidden`,
  so the invisible window blocked every click → `#posmodal[hidden]`.
- Trade tables: names/dates no longer wrap one char per line; exit reason
  clipped to 2 lines (full text in the window); tables scroll on phones.
- 2026-10-09 owner feedback: right-edge labels overlapped (成本 = breakeven
  止损 19.29); window scrolled as a whole. Fix: labels merged when equal,
  pushed ≥13px apart otherwise (sweep: 68 trades, 0 overlaps, 2 merged);
  window height bounded, head + chart fixed, only text below scrolls;
  买/卖 markers moved just outside their bar so they don't cover it.
