# Fix Pricedb Degradation — Proxy Bypass, Eastmoney Bulk Snapshot, Staleness Gate, Tushare-Free Trade Calendar

## Context

The pipeline has been running **degraded** for several days (2026-05-08 → today). Symptoms:

- `pricedb.py update` fails with: `tushare trade_cal failed: 抱歉，您没有接口(trade_cal)访问权限`
- Falls back to `eastmoney_direct`, which loops 5519 individual `push2his.eastmoney.com/api/qt/stock/kline/get` requests and hits the 600s budget at ~3200/5519 stocks
- `akshare` and `baostock` fallbacks also fail (budget + network)
- Pipeline proceeds anyway because the staleness check is bugged (`>10 days` instead of `< today`)
- Result: RPS/MA-distance computations are run on stale closes from 5 days ago, polluting analyst reasoning

**Root cause investigation (already done, confirmed working):** When the `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` environment variables are bypassed, eastmoney endpoints respond instantly:
- `push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.600000&...` returns today's bar in **0.4s**
- `push2.eastmoney.com/api/qt/clist/get?pn=N&pz=50&...` returns **all 5851 A-shares' daily snapshot in one paginated call (~120 pages, ~30s total)**
- `akshare.tool_trade_date_hist_sina()` returns the full trade calendar in 0.5s with no auth

The user runs Surge proxy on their Mac, which silently intercepts requests to `*.eastmoney.com` and breaks them. The pricedb code already has proxy bypass for one path (`_fetch_eastmoney_json_urllib` and `_fetch_eastmoney_json_curl`), but it's missing on the bulk-fetch workers and on the akshare/baostock paths.

## Goal

Restore the pricedb update flow to:
1. Refresh daily for all ~5500 A-share stocks in **under 60 seconds**
2. Not depend on Tushare permissions (`trade_cal` or `daily`) at all
3. Refuse to run analysis on stale data (hard gate, not a warning)
4. Survive Surge proxy / any user proxy without configuration

## Files To Touch

- `scripts/pricedb.py` — primary changes
- `scripts/data_collector.py` — staleness gate fix
- `scripts/run_daily.py` — preflight wiring
- `scripts/test_local_pricedb.py` — extend tests

Do NOT touch:
- `scripts/run_daily.py` orchestration logic — only the preflight `_check_data_sources` section
- The LLM analysis or apply phases
- The CheeseForTune client

## Required Changes

### 1. Add a new bulk snapshot fetcher: `_bulk_fetch_eastmoney_snapshot`

In `scripts/pricedb.py`, add a new provider path that uses the Eastmoney **clist** endpoint instead of per-stock kline calls. This endpoint returns all A-shares in paginated snapshots (~50 per page, ~120 pages for the whole market).

Endpoint:
```
https://push2.eastmoney.com/api/qt/clist/get
  ?pn=<page>
  &pz=50
  &po=1
  &np=1
  &fltt=2
  &fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048
  &fields=f12,f14,f2,f3,f6,f15,f16,f17,f18,f5
```

Field meanings (verify by inspecting actual response):
- `f12` = stock code (e.g., "600000")
- `f14` = stock name
- `f2`  = current price (close)
- `f3`  = pct change (today)
- `f5`  = volume (lots)
- `f6`  = turnover (¥)
- `f15` = high
- `f16` = low
- `f17` = open
- `f18` = previous close

This gives one daily bar per stock per call. Iterate pages 1..N until `len(diff) < pz`. Each page returns up to 50 rows. ~120 pages total, ~0.4s each = **~50s for the whole market** (versus 600s+ today). Use a ThreadPoolExecutor with `EASTMONEY_DEFAULT_WORKERS` to parallelize pages.

**This is for the daily incremental update only.** Initial DB seeding (long history) still needs the per-stock kline endpoint — keep that path intact as `_bulk_fetch_eastmoney_per_stock`.

### 2. Aggressive proxy bypass for ALL pricedb network paths

The existing `_fetch_eastmoney_json_urllib` already uses `urllib.request.build_opener(urllib.request.ProxyHandler({}))`. Replicate this for:

- Every `requests.Session` constructed inside `pricedb.py` → set `s.trust_env = False`
- The new clist fetcher (use `requests` with `trust_env=False`, NOT urllib — easier pagination/JSON)
- The akshare paths: there's no clean way to disable proxies inside akshare, but we can `os.environ`-strip them inside a context manager just for the akshare call. Add a helper `with _no_proxy_env(): ak.tool_trade_date_hist_sina()`.
- The baostock path: same — wrap in `_no_proxy_env`.

Add at the top of `pricedb.py`:

```python
import contextlib

@contextlib.contextmanager
def _no_proxy_env():
    """Temporarily strip proxy env vars so libraries that ignore trust_env still work.

    Surge and similar proxies intercept *.eastmoney.com and break price fetches.
    Pricedb deliberately bypasses these.
    """
    keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy", "NO_PROXY", "no_proxy")
    saved = {k: os.environ.pop(k, None) for k in keys}
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
```

### 3. Replace `fetch_trade_dates_tushare` with akshare

Add a new function:

```python
def fetch_trade_dates_free(beg: str, end: str) -> list[str]:
    """Fetch open trading dates [beg, end] inclusive using akshare (no auth).

    beg/end format: 'YYYYMMDD'.
    Returns sorted list of 'YYYYMMDD' strings.

    Falls back to a generated weekday list if akshare fails (last-resort, lossy).
    """
    import akshare as ak
    with _no_proxy_env():
        df = _run_with_timeout("akshare trade_cal", lambda: ak.tool_trade_date_hist_sina())
    # df has a 'trade_date' column (or similar) with datetime.date values
    # Convert to YYYYMMDD strings and filter to [beg, end]
    ...
```

Then in `_bulk_fetch_tushare` (if you keep the tushare path at all — see Step 4), replace `fetch_trade_dates_tushare` with `fetch_trade_dates_free`.

### 4. Demote Tushare, promote Eastmoney clist

Update the provider selection order in `cmd_update` (and wherever else it lives):

**Before:**
1. tushare
2. eastmoney_direct (per-stock loop)
3. akshare
4. baostock

**After:**
1. **eastmoney_clist** (new bulk snapshot — fast, no auth, ~50s)
2. eastmoney_direct (per-stock kline — keep as fallback for backfills or partial dates)
3. akshare (fallback)
4. baostock (last resort)
5. tushare (only if `TUSHARE_TOKEN` is set AND the user has confirmed the necessary endpoints work — likely never used)

The clist path should be the default for "today's bar" updates. The per-stock path is still useful for historical backfills (when DB is missing N days), where you genuinely need 250 days × 5500 stocks of klines.

### 5. Fix the staleness gate (CRITICAL)

In `scripts/data_collector.py` line ~232:

**Before:**
```python
if (datetime.now().date() - latest_dt).days > 10:
    raise RuntimeError(f"local pricedb is stale (latest date: {latest_date})")
```

**After:**
```python
# Stale if latest bar is older than the most recent trading day.
# Saturday/Sunday/holidays are OK — staleness only matters on trading days.
from datetime import datetime, timedelta
today = datetime.now().date()
latest_trading_day = _most_recent_trading_day(today)  # NEW helper
if latest_dt < latest_trading_day:
    raise RuntimeError(
        f"local pricedb is stale: latest={latest_date}, "
        f"expected ≥ {latest_trading_day.isoformat()}"
    )
```

Where `_most_recent_trading_day(d)` returns the most recent date ≤ `d` that is a trading day, using `fetch_trade_dates_free` or a cached calendar.

Also wire this into `scripts/run_daily.py`'s preflight (`_check_data_sources` or equivalent): if pricedb is stale **and** today is a trading day **and** the current time is after 09:30 local, the pipeline should **refuse to start phase 2** and exit with a clear error message ("Pricedb is stale — refusing to run analysis on stale data. Check eastmoney connectivity / proxy settings.").

Today's logic ("warn but proceed") is wrong because the LLM treats RPS/MA numbers as today's truth.

### 6. Make pricedb update part of preflight, not just phase 1

Currently `cmd_update` is called from inside phase 1 data collection. The right place is **preflight**: before phase 1 even starts, ensure pricedb is fresh. If the update fails, abort cleanly.

In `scripts/run_daily.py`, the preflight check should:

1. Run `pricedb.cmd_update()` with a tighter budget (300s instead of 600s — the clist path should finish in ~60s, anything taking longer is a real problem)
2. Verify staleness gate passes
3. Only then proceed to phase 1

## Testing Guidelines

Add tests to `scripts/test_local_pricedb.py`. Do not add new test files unless necessary. The goal is to make pricedb regressions catchable in CI / local test runs without hitting the network.

### Test categories

#### A. Pure unit tests (no network, mock everything)

These should be fast (<1s each) and run on every commit:

1. **`test_no_proxy_env_strips_and_restores`** — verify `_no_proxy_env` removes proxy env vars inside the block and restores them after. Test that `NO_PROXY` is also stripped (some libraries respect it inversely).

2. **`test_most_recent_trading_day_weekend`** — given a Saturday/Sunday date and a mocked trade calendar, return the prior Friday.

3. **`test_most_recent_trading_day_holiday`** — given a date that's a holiday, return the prior trading day.

4. **`test_staleness_gate_today_trading_day_stale`** — pricedb at 2026-05-08, today is Wed 2026-05-13 (trading day), expect `RuntimeError("stale")`.

5. **`test_staleness_gate_weekend_ok`** — pricedb at Fri 2026-05-08, today is Sat 2026-05-09, expect no error (markets closed).

6. **`test_staleness_gate_today_fresh`** — pricedb at 2026-05-13, today is 2026-05-13, expect no error.

7. **`test_clist_url_construction`** — verify the URL has the right `fs=` filter (covers all 4 A-share boards), correct fields, correct pagination params.

8. **`test_clist_response_parsing`** — feed a mocked clist JSON response (fixture file, real shape) and verify it produces correct (code, date, ohlcv) tuples. Include edge cases: stocks with `'-'` price (suspended), stocks with `null` fields.

9. **`test_clist_pagination_terminates`** — verify the pagination loop terminates correctly when the last page returns fewer than `pz` rows.

#### B. Integration tests (network, mark with `@pytest.mark.integration`)

These should be skipped by default and run manually with `pytest -m integration`:

1. **`test_eastmoney_clist_live`** — actually hit the live clist endpoint with `trust_env=False`, verify it returns ≥3000 A-shares and that today's date appears in at least one bar (or yesterday's if before market open).

2. **`test_eastmoney_kline_live_single_stock`** — fetch 600000 for the last 10 trading days, verify ≥5 bars, latest bar date is within the last week.

3. **`test_akshare_trade_cal_live`** — fetch the full trade calendar, verify it contains today (if trading day) or the most recent trading day.

4. **`test_proxy_bypass_actually_works`** — set `HTTP_PROXY=http://127.0.0.1:1` (a port that will refuse connection), then call a pricedb fetch wrapped in `_no_proxy_env`. Should succeed. Without the bypass it should fail.

#### C. Smoke test (the big one, separate)

Add `scripts/test_pricedb_smoke.py` (separate file, run manually, not part of unit suite):

```python
"""End-to-end smoke test for pricedb update.

Runs the actual clist fetch against the live market, writes to a temp DB,
asserts completion in < 120s with > 5000 stocks and today's date present.
Skips if today is not a trading day.
"""
```

This is the canary. If this fails in production, the pipeline should not run.

### Test fixtures

Save real Eastmoney clist responses as fixtures under `scripts/test_fixtures/eastmoney_clist_*.json` so that response-parsing tests are realistic. Capture at least 3 fixtures:
- Normal trading day, page 1 (full 50 rows)
- Last page (partial rows)
- Stocks with null/suspended data

Capture these using a one-off script saved as `scripts/dev_capture_fixtures.py` (not run automatically) — useful when Eastmoney changes their response shape.

### Mocking strategy

For the unit tests, mock at the **HTTP boundary** (the `requests.Session.get` call or `_fetch_eastmoney_json` function), NOT at the business logic. This way the tests catch real parsing bugs.

Use `unittest.mock.patch` with the fixture JSON loaded from disk. Example:

```python
from unittest.mock import patch, MagicMock
import json

def _load_fixture(name):
    with open(f"scripts/test_fixtures/{name}.json") as f:
        return json.load(f)

@patch("pricedb._fetch_clist_page")
def test_clist_response_parsing(mock_fetch):
    mock_fetch.return_value = _load_fixture("eastmoney_clist_page1")
    rows = _parse_clist_page(mock_fetch.return_value, target_date="2026-05-13")
    assert len(rows) == 50
    assert rows[0][0] == "600000"  # code
    assert rows[0][1] == "2026-05-13"  # date
    # ...
```

### Pre-existing tests

`scripts/test_local_pricedb.py` already exists — read it, follow its patterns, don't reinvent. If you change a function signature, update existing tests in the same commit.

### Validation before declaring done

1. Run the full unit test suite: `pytest scripts/test_local_pricedb.py -v` — all green
2. Run the integration tests: `pytest scripts/test_local_pricedb.py -m integration -v` — all green
3. Run the smoke test: `python3 scripts/test_pricedb_smoke.py` — completes < 120s with > 5000 stocks
4. Run the full pipeline: `python3 scripts/run_daily.py --run` — completes in < 90 minutes, with `status="ok"` (not "degraded"), and the daily summary shows today's date as the pricedb latest date
5. Run the pipeline a second time on the same day — should be a no-op for pricedb update (already up to date) and complete much faster
6. Set `HTTP_PROXY=http://127.0.0.1:1` and run the pipeline — should still succeed (proxy bypass working)

## Out of Scope

- Don't add new data sources beyond what's listed
- Don't change the SQLite schema
- Don't change the analyst prompt or analysis logic
- Don't add caching beyond what already exists
- Don't change the cron schedule
- Don't try to "fix" akshare's IP rate limiting — just keep it as a tertiary fallback

## Deliverables

1. Modified `scripts/pricedb.py` with:
   - `_no_proxy_env` context manager
   - `_bulk_fetch_eastmoney_snapshot` (clist-based, default)
   - `_bulk_fetch_eastmoney_per_stock` (renamed from current eastmoney_direct path)
   - `fetch_trade_dates_free` (akshare-based)
   - Updated provider order in `cmd_update`
   - Tighter default `PRICEDB_UPDATE_BUDGET_SEC` (300s)

2. Modified `scripts/data_collector.py` with:
   - Corrected staleness gate using `_most_recent_trading_day`

3. Modified `scripts/run_daily.py` with:
   - Preflight that runs pricedb update first
   - Hard refusal to proceed on stale data during trading hours

4. Extended `scripts/test_local_pricedb.py` with at least 12 new unit tests as listed above

5. New `scripts/test_pricedb_smoke.py` smoke test

6. New `scripts/test_fixtures/eastmoney_clist_*.json` (3 fixtures)

7. New `scripts/dev_capture_fixtures.py` (capture script for future maintenance)

8. Commit with clear message: `fix(pricedb): bypass proxy, add clist snapshot, drop tushare dependency, fix staleness gate`

## Notes

- The user is on macOS with Surge proxy. The proxy bypass is the single most important fix — without it, every other change is moot.
- Tushare's free tier no longer includes `trade_cal` for this user. Don't assume tushare works; treat it as a paid-tier opt-in only.
- The Eastmoney endpoints are public, unauthenticated, and rate-limit-friendly when used at ~12 concurrent workers. Do not exceed this.
- The clist endpoint's `fs=` filter `m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048` covers SH main + SH STAR + SZ main + SZ ChiNext + BJ. Verify against `data/pricedb` row count after running.
- Don't introduce dependencies on heavy libraries (pandas DataFrame manipulation is fine, but no new external services).
- Keep the existing per-stock kline path; don't delete it. It's needed for historical backfills.

## When to ask for help

If you discover that:
- The clist response format has changed and fields don't match what's documented above → stop, capture a fresh fixture, share it
- Eastmoney starts rate-limiting at <12 workers → drop to 4 and document the new limit
- The staleness gate breaks the existing CTO test suite → don't override, ask
- Test fixtures get larger than 100KB each → trim to representative samples

Otherwise, proceed.
