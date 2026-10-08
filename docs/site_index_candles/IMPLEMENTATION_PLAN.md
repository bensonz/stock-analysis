# Site: 上证 candles + day-% comparison

Owner ask 2026-10-08: "make the html show k-lines for the underlying comparison,
and show +1% / -0.7%, now I can't even tell if it's correct".

## Stage 1: OHLC data layer
**Goal**: one sina kline fetch feeds both the close cache and a new OHLC cache
(`data/index_cache/sh000001_ohlc.json`).
**Success Criteria**: no extra network call; offline build uses both caches.
**Tests**: load_index_bars merges kline into cache; cache-only fallback.
**Status**: Complete

## Stage 2: per-point comparison payload
**Goal**: each chart point carries real 上证 OHLC (exact date only, never
forward-filled), 上证 day %, 组合 day %, and the 上证 % at snapshot time when the
day's last snapshot predates 15:00.
**Tests**: candle only on exact-date bar; close-only tick for quote-only day;
day % vs previous index close; noon snapshot carries intraday %.
**Status**: Complete

## Stage 3: chart
**Goal**: candles on the shared scale (replace the close line), range selector
全部/近60日/近20日, a 组合/上证/超额 % strip under the chart when wide enough,
tooltip + side panel show both day %.
**Tests**: render_html output markers; headless screenshot + console clean.
**Status**: Complete
