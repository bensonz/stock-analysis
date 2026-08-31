# Pricedb intraday + partial-coverage bugs — findings & plan

Discovered 2026-07-17 while investigating why 301345 showed a bogus +1.68% in the
noon screen when it was actually −6.8% intraday.

## Three root causes

### RC1 — Intraday snapshot written as the daily "close" (ingestion)
`pricedb.py::cmd_update` (~L1531-1543): after the daily providers run, if today's
bar didn't land (`today_count == 0` — normal mid-session because the completed
daily bar doesn't exist yet), it calls `_backfill_from_akshare_spot()`.
That function (`ak.stock_zh_a_spot_em()`, L1560) writes the **real-time latest
price** (`最新价`) as the day's `close` for ~5000 stocks. So the noon run
(~11:35) stamps an intraday snapshot as today's close. `INSERT OR REPLACE` means
the afternoon (post-close) run overwrites it with the true close.

### RC2 — Resolver selects the open-session day (screening)
`rps_calculator.py::_resolve_reference_date` picks the latest date that clears a
90% coverage bar (`RPS_REFERENCE_DATE_MIN_COVERAGE=0.9` → 4970 of 5523 codes).
The intraday today-row covers 5282 codes → clears the bar → **reference date =
today (intraday)**. So MA10/20/120/250 and every cross-sectional RPS rank used an
intraday bar as their newest point. Impact is bounded (only the newest MA point;
historical points are real closes) but distorts RPS *ranks* worst on volatile
days — exactly like 2026-07-17. Only the **noon** slot is affected; the afternoon
slot re-runs after close on true closes.

### RC3 — Partial coverage compounds and is never repaired (ingestion)
- `cmd_update` sets `beg = MAX(date) + 1`. Once a partial future day lands even
  one stock, the cursor jumps forward; earlier partial days are **never
  re-fetched**. Only fully-missing *stocks* get backfilled (LEFT JOIN NULL), not
  missing *days* for existing stocks.
- A 300s budget (`PRICEDB_UPDATE_BUDGET`) truncates `bulk_fetch` mid-loop; the run
  still prints "Update complete" and returns.
- Result observed: 07-15 = 663 codes, 07-16 = 806, 07-17 = 5282 (intraday),
  metadata "last updated" stuck at 2026-05-18.

## Fix plan (option B)

1. **[test]** `tests/test_rps_reference_date.py`: assert resolver skips today when
   the session is open (inject `now`). — task #8
2. **[fix]** `_resolve_reference_date`: exclude `date >= today` while session open
   (before 15:00 local, env-overridable). Belt-and-suspenders for the screen. — task #9
3. **[fix]** `cmd_update`: don't spot-backfill today's bar during an open session
   (RC1 at the source); set `beg` from the last *fully-covered* date so partial
   recent days get re-fetched (RC3); don't report success when budget truncated. — task #10
4. **[data]** Backfill 07-15/16, overwrite today's intraday bar with the real
   close, recompute RPS cache; verify per-date coverage. — task #11

## Refinements found while implementing

- **RC1 is broader than the spot fallback.** The per-stock kline path
  (`eastmoney_direct`) also returns *today's forming bar* mid-session, so gating
  only `_backfill_from_akshare_spot` was insufficient. Proper source fix: in
  `cmd_update`, cap `end` at the last closed trading day
  (`most_recent_trading_day(today-1)`) whenever `is_session_open()`. No provider
  ever writes an unsettled bar; the post-close run picks today up normally.
- **`eastmoney_clist` is a today-only snapshot** (`pricedb.py` L890-896): it
  cannot fetch a historical single day. So repairing old partial days *must* go
  through the slow per-stock path. Normal daily operation stays fast because
  beg==end==today → clist; the slow path only engages when there are partial
  historical days to heal (exceptional, self-limiting).
- **RC3 convergence caveat (known follow-up):** the self-healing cursor
  re-fetches *all* stocks from the last fully-covered day, not just the ones
  missing the target days. On a tight budget a multi-day backfill may not reach
  full coverage in one run and re-does work each run. The one-time repair below
  uses a raised `PRICEDB_UPDATE_BUDGET`. A proper fix would fetch only stocks
  missing the target day(s) so runs converge under the default budget — LANDED (resumable coverage cursor, pricedb/__init__.py + tests/test_pricedb_coverage_cursor.py).

## RC4 — Staleness gates conflicted with the end-cap (regression from RC1 fix)

Shipped-then-caught. The RC1 end-cap keeps the DB at the last *closed* session
during an open session. But both staleness gates (run_daily preflight ~L617,
data_collector ~L237) demanded `latest >= most_recent_trading_day(today)`, which
equals *today* on an open trading day. So after the RC1 fix, **every mid-session
run hard-refused with "pricedb is stale" and exited before phase 1** — leaving an
empty run dir. This is what actually killed the 2026-07-20 noon run (not the
environmental red herring first suspected).

Fix: `pricedb.last_settled_trading_day(now)` — previous trading day while the
session is open, today once closed. Both gates use it as the freshness
threshold; "is today a trading day" for the hard-refuse decision is computed
independently so genuinely stale data is still caught. Committed 4d81033.

**Lesson:** the RC1/RC2/RC3 commits passed unit tests but I did not run the full
pipeline end-to-end afterward — the gate interaction only shows up there. Run
`run_daily.py --run` (or the verify skill) after changing ingestion/screening.

## Status
- Investigation: COMPLETE (RC1/RC2/RC3 confirmed empirically)
- Fix RC2 (resolver guard): DONE + tests, committed e548fee
- Fix RC1/RC3 (ingestion): DONE + tests, committed fe528d8 (+ end-cap follow-up)
- Data repair (07-14/15/16 backfill, RPS recompute): DONE (see pricedb_repair/PROGRESS.md)
- Follow-up: make backfill resumable (fetch only missing stocks) so it converges
  under the default 300s budget
