# Price-DB outage repair — 2026-08-01

## Incident

- **07-30 landed 681 price rows, 07-31 landed 15** (normal ≈ 5,200).
  Root cause: `push2.eastmoney.com` (clist bulk snapshot, provider #1)
  started refusing connections from this IP ~07-30; the kline fallback
  (`push2his`) was then killed by the 300s update budget; remaining
  providers (akshare→eastmoney-backed, baostock, tushare-denied) failed too.
  By 08-01 the per-stock kline endpoint was ALSO throttled (intermittent
  RemoteDisconnected) — eastmoney is IP-throttling us entirely.
- Defensive layers held: the RPS coverage floor refused to compute on the
  junk days, so 07-30/31 screening silently ran on 07-29 data (stale, not
  corrupt).
- Second-order damage: `adj_factors` stopped at 07-29 while **39 stocks
  went ex-div on 07-30/31** (per eastmoney datacenter calendar). The
  incremental factor sync (`sync_adj_factors_for_today`) would have
  silently reset every cumulative chain to 1.0 across a multi-day gap
  (base lookup on a factor-less day defaults to 1.0).
- This was also the standing backlog: **39 partial days since 2026-03-12**
  (the "~50 near-empty days" memory), which made 21/41 real trades
  unreplayable in the backtest harness.

## Fix (code, all in scripts/pricedb.py + tests/test_factor_heal.py)

1. **Guard**: `sync_adj_factors_for_today` now raises on a multi-day gap
   instead of resetting chains.
2. **`factors heal`**: repairs a factor gap — eastmoney *datacenter* host
   (still reachable) names the ex-div codes per gap day; only codes whose
   stored factors are missing/flat across their own ex-date get re-derived
   (sina events primary, eastmoney return-ratio fallback), anchor-rescaled
   so pre-gap rows diff as unchanged (shallow rps_cache invalidation);
   everyone else is exact forward-fill.
3. **`_sync_or_heal_factors`**: daily pipeline path — same-day f18 fast
   path when possible, auto-falls back to heal on clist failure or lag ≥ 2
   sessions. Wired into `cmd_update` and `factors update`.
4. **`repair`**: fills partial price days from sina per-code klines
   (raw prices verified against stored eastmoney bars incl. the 601818
   ex-div open drop; volume shares→手 ÷100; amount NULL). INSERT OR
   IGNORE — eastmoney rows stay canonical, sweep idempotent. Ends with
   factor heal + rps_cache invalidation from the first repaired date.
   4 workers × 0.25s ≈ 15 req/s (sina politeness).

## Validation checklist

- [x] 6 new unit tests green (chain-reset guard, heal re-derivation with
      anchor rescale, calendar-outage degradation, skip-already-derived,
      sina parse/convert, gap routing); 31 neighboring pricedb/rps tests
      still green.
- [x] Sweep completed 2026-08-01: **191,062 rows, 0 fetch failures**; all
      39 days at full coverage (April days ~5,490 > July ~5,185 — real:
      ~300 codes delisted/suspended in between).
- [x] `factors verify` exit 0 (factors dense through 07-31, factored
      universe 100%). Heal re-derived 1,457 event codes — including latent
      damage on *full* days where the 0.5% f18 threshold had skipped small
      dividends.
- [x] RPS recomputed for 07-29/30/31; 07-31: 5,174 cached, momentum-gate
      pool 389 (plausible). Older invalidated dates refill lazily on
      demand (base_rates/panels compute from closes, not rps_cache).
- [x] Full pytest suite: 397 passed, only the 7 known pre-existing
      failures.
- [x] Replay coverage: **41/41 trades replayable** (was 21/41).
      match_rate 53.7% @1.5pp, mean |diff| 1.93pp — dominated by the known
      entry fill-timing noise (1.87%), not missing data.

## Follow-ups

- **228 of 1,457 event codes failed re-derivation** (sina empty + eastmoney
  fallback throttled + BJ codes): they keep forward-filled factors. Re-run
  `pricedb.py factors heal --beg 2026-03-12 --end 2026-07-31` when the
  eastmoney throttle lifts — the flat-across-ex-date filter re-flags
  exactly these.
- ~~Eastmoney IP throttle Monday risk~~ → RESOLVED 2026-08-01 evening:
  provider chain rewritten to **akshare primary → sina fallback** (user
  decision; eastmoney/baostock/tushare retired for price bars), plus the
  loudness layer: `db_health` block (staleness, partial-day, factor lag,
  20-code cross-source spot audit) → input/db_health.json → prompt banner →
  report banner → phase-1 hard gate (>1 session stale halts the run).
  Weekly audit gained a data-hygiene step (C2).
- 2026-03-12 was the earliest partial day; anything older is full.

---

> **Supersession note (2026-08-25):** the "akshare primary → sina fallback"
> doctrine recorded above was superseded when the paid iFinD seat landed —
> the chain is now **iFinD → AkShare → Sina** (see CLAUDE.md, providers.py).
> This file remains the record of the August outage as it happened.
