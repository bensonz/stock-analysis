# Prompt: Fix `/api/alerts/scan` 56s latency (options-learn backend)

> **Repo / host:** `options-learn` backend, deployed at `/opt/options-learn` on Aliyun (`ssh aliyun`), FastAPI + Uvicorn + Postgres + APScheduler, Dockerized via `docker compose`.
> **Backend container:** `options-learn-backend-1` (cmd: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`).
> **Goal:** Make `GET /api/alerts/scan` return in **< 1s** (currently **~56s**) and eliminate the page-transition lag it causes in the frontend. Do NOT change the scanner's analytical logic or output schema — only how/when the underlying IV+price data is sourced.

---

## Problem (root cause — verified)

`GET /api/alerts/scan` → `alert_scanner.scan_alerts(db)` loops over **9 underlyings** (`SCANNER_UNDERLYINGS`) and, per code, calls:
- `live_data.get_live_iv(code)` → OpenVlab `/volatility-surface/{code}` (HTTP)
- `live_data.get_live_price(code)` → AkShare, fallback OpenVlab (HTTP)

These run **serially**, and each OpenVlab call is slow. 9 × ~6s ≈ **56s total**. Measured:
```
/api/alerts/scan -> http:200 ttfb:56.37s total:56.37s   # blocks the entire time
/api/health      -> http:200 ttfb:0.0014s               # server itself is fine
```

Existing caches do NOT help the real-world case:
- `alert_scanner._scan_cache` (TTL 60s) and `live_data._cache` (TTL 60s) only help within a 60s window. The scanner is hit ~once/day (cron), so every real call is a cold 56s call.
- **Crucially:** APScheduler already runs `run_all_snapshots()` (`app/tasks/scheduler.py`) on market-hours cron triggers (9–11 every 30m, 13–14 every 30m, 15:05, 15:10) and populates the **`DailyIVSummary`** table. The scan ignores this persisted snapshot data and refetches live.

**Why the frontend feels slow:** pages that depend on scan data block on this 56s call before rendering content. The HTML shell loads in ~26ms; the data view hangs.

---

## Required changes

### 1. Serve scan from persisted snapshot data, not per-request live fetches (PRIMARY FIX)

Refactor `alert_scanner.scan_alerts(db)` so the per-underlying market context is built from **the latest persisted snapshot in Postgres** (`DailyIVSummary` and the price table `UnderlyingPrice`) instead of calling `get_live_iv` / `get_live_price` synchronously in the request path.

- Add a data-source function, e.g. `build_market_context_from_db(db, code)`, that reads the most recent `DailyIVSummary` row (IV percentile, avg VRP, PCR, term structure, etc.) and latest `UnderlyingPrice` (price, prev_close, SMAs) for each code.
- `scan_alerts` should use this DB path by default. The analytical pipeline downstream (regime inference → setup mapping → quality filters → recommendations) stays **unchanged** — only the data acquisition changes.
- Keep the response schema identical (`ScanResponse`: recommendations, diagnostics, scanned_at, underlyings_scanned). `scanned_at` should reflect the snapshot timestamp (add the snapshot date/time to diagnostics if not already present, so callers know freshness).

### 2. Ensure the scheduler persists everything the scan needs

Audit `run_all_snapshots()` in `app/tasks/scheduler.py`. Confirm it writes, per underlying, all fields the scan reads from `MarketContext` (iv_percentile, avg_vrp, iv_today/yesterday/day_change, price, prev_close, sma20, sma60, pcr fields, term_slope). If any field the scan needs is currently only available via the live path, extend the snapshot job to compute & persist it.

- Add **one more cron trigger at ~09:30** (before the 09:35 external options-scanner cron that calls this endpoint) so fresh data is staged each morning. The options scanner that consumes this runs at 09:35 Asia/Shanghai.

### 3. Keep a live fallback, but bounded and parallel

If no snapshot exists for today (e.g. scheduler missed a run), fall back to live fetch — but:
- Run the 9 per-underlying fetches **concurrently** (e.g. `asyncio.gather` with an async client, or `ThreadPoolExecutor(max_workers=9)`), not serially.
- Apply a hard per-call timeout (e.g. 8s) so a single dead upstream can't stall the whole response.
- Mark `diagnostics` / a response field to indicate the result came from live-fallback vs cached snapshot (so we can tell when the scheduler path failed).

### 4. Frontend: never block navigation on scan data

In the frontend (`options-learn-frontend`, Next.js standalone), the page that shows scan results should render its shell + a loading state immediately and fetch scan data client-side (or stream it), so route transitions are instant even if the API is slow. If the page currently `await`s the scan in a server component before first paint, move the fetch to a client component with a skeleton/loading UI.

---

## Acceptance criteria

- `GET /api/alerts/scan` returns in **< 1s** on a normal day (snapshot path).
- Response schema unchanged; recommendations + diagnostics identical to the live path for the same input data (verify against a recorded sample).
- A response field/diagnostic indicates data freshness (snapshot timestamp) and source (snapshot vs live-fallback).
- Live fallback, when triggered, runs concurrently and completes in well under the old 56s (target < 10s).
- Page transitions in the frontend no longer hang waiting on the scan call.
- `docker compose` build succeeds; `alembic upgrade head` clean (if any new column added for persisted fields).
- Existing tests pass: `backend/tests/test_alerts_router.py`. Add a test that `scan_alerts` uses the DB path and does not call `get_live_iv`/`get_live_price` when a fresh snapshot exists (mock/patch those and assert not-called).

## Files to touch

- `backend/app/services/alert_scanner.py` — add DB-context path; switch `scan_alerts` to it; bounded+parallel live fallback.
- `backend/app/services/live_data.py` — optional: async/parallel variant for fallback.
- `backend/app/tasks/scheduler.py` — ensure snapshot persists all needed fields; add ~09:30 trigger.
- `backend/app/routers/alerts.py` — surface freshness/source in response if needed.
- `backend/app/models/daily_iv_summary.py` / migration — only if a new persisted column is required.
- `frontend/...` — scan results page: shell + client-side fetch with loading state.
- `backend/tests/test_alerts_router.py` — freshness + no-live-call-when-cached test.

## Out of scope / do NOT change

- The regime inference, setup mapping, quality filters, VRP logic, or recommendation text.
- `SCANNER_UNDERLYINGS`, strategy definitions, or the `ScanResponse` schema shape.
- The 09:35 external options-scanner cron (that's on the laptop, separate; it just consumes this endpoint).

## Deploy / verify

```
ssh aliyun
cd /opt/options-learn
git pull            # after PR merged, or apply changes
docker compose build backend frontend
docker compose up -d
# verify latency:
curl -s -o /dev/null -w "%{time_total}s\n" http://localhost:8080/api/alerts/scan   # expect < 1s
docker compose logs --tail=50 backend
```

---
## Done
_Completed: 2026-06-29_

Implemented in the **options-learn** repo (backend code lives there; this prompt
file lives in stock-analysis).

### Changes Made
- `backend/app/models/daily_iv_summary.py` — added `front_month`, `second_month`, `term_slope` columns.
- `backend/alembic/versions/b1d4e7a90c23_add_term_structure_to_daily_iv.py` — migration for the new columns.
- `backend/app/services/snapshot_service.py` — `compute_daily_iv_summaries` now derives + persists term structure (front−second ATM IV, pp).
- `backend/app/services/vrp_service.py` — `get_iv_percentile`/`compute_vrp` gained `use_live` (default True); scanner DB path passes `use_live=False`.
- `backend/app/services/alert_scanner.py` — `build_market_context_from_db()` (no network); `_build_market_context()` dispatches DB-vs-live; renamed live builder to `_build_market_context_live()`; `_has_fresh_snapshot()`, `_prefetch_live_parallel()` (ThreadPoolExecutor, 8s bound); `scan_alerts_detailed()` with `data_source`/`snapshot_date` meta; `scan_alerts` kept as 2-tuple for back-compat.
- `backend/app/routers/alerts.py` — uses `scan_alerts_detailed`; `scanned_at` = snapshot date on DB path, request time on live fallback.
- `backend/app/schemas/alerts.py` — `ScanResponse.data_source` + `snapshot_date`.
- `backend/app/tasks/scheduler.py` — `run_morning_stage()` + 09:31 Asia/Shanghai cron (snapshot + IV summary + price) before the 09:35 external scanner.
- `frontend/src/lib/types.ts` — `AlertScanResponse.data_source`/`snapshot_date`.
- Tracking: `docs/tracking/PROGRESS.md`, `DECISIONS.md` (D33), `backend/CLAUDE.md`.

### Tests
- Added: `TestSnapshotFastPath` (fresh snapshot → DB path, asserts `get_live_iv`/`get_live_price` NOT called; no-snapshot → live fallback) in `test_alert_scanner.py`; `test_persists_term_structure` in `test_snapshot_service.py`; `test_scan_live_fallback_uses_request_time` in `test_alerts_router.py`.
- Fixed: 3 alerts router tests (now mock `scan_alerts_detailed` 3-tuple) and 2 date-rotted DTE-fallback tests (pinned `date.today()`).
- Result: backend **860 passing**. 3 pre-existing failures in `test_strategy_optimizer.py`/`test_suggest_router.py` are network-dependent (AkShare/OpenVlab) and reproduce on a clean HEAD — unrelated to this change. Frontend: alerts-panel 10/10; the new type compiles (pre-existing tsc errors in `strategy/page.test.tsx`/`middleware.test.ts` are unrelated).

### Notes
- Frontend section 4 was already satisfied: `DashboardContent` is a client component and `AlertsPanel` fetches via `useAlerts` (TanStack Query) with a skeleton, so navigation never blocked on the scan. Only the response type was extended.
- DB freshness is keyed on today's `DailyIVSummary`. On weekends/holidays (no today snapshot) the scan uses the bounded parallel live fallback (<10s), not the sub-second snapshot path.
- Latest `DailyIVSummary` rows written before this migration have NULL term structure; the scanner degrades gracefully (no single-expiry setups for that code) until the next snapshot job populates the columns.
- The `< 1s` latency target was verified by design (DB-only path, no network); not yet re-measured against the live Aliyun deploy — run the curl in the Deploy/verify section after deploying.
