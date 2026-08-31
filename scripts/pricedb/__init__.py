#!/usr/bin/env python3
"""
pricedb.py — Local A-share price database management.

SQLite-backed price history for all A-share stocks.
Data sources:
- Stock list: Tushare Pro when available, BaoStock fallback
- Price bars: Tushare Pro, Eastmoney direct fallback, AkShare historical daily fallback, BaoStock fallback

Usage:
    python scripts/pricedb.py init          # Create DB, fetch stock list, download ALL historical data
    python scripts/pricedb.py update        # Incremental update: fetch missing dates since last update
    python scripts/pricedb.py status        # Show DB stats: total stocks, date range, last update
    python scripts/pricedb.py rps [DATE]    # Compute MA-based RPS for all stocks on DATE (default: latest)
    python scripts/pricedb.py query CODE    # Show a stock's recent prices + computed RPS values
"""

import bisect
import contextlib
import os
import socket
import sqlite3
import sys
import threading
import time
import json
import subprocess
import urllib.parse
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from datetime import date as _date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ifind_client
import price_adjust
# Pure bar/code transforms live in pricedb_bars (no I/O, no conn, no clock).
# Re-exported under their original names so every caller and test is unchanged.
from pricedb.bars import (  # noqa: F401
    _akshare_hist_row_to_tuple,
    _baostock_rows,
    _eastmoney_kline_to_tuple,
    _eastmoney_kline_url,
    _eastmoney_payload_to_rows,
    _eastmoney_secid,
    _exchange_from_code,
    _frame_close_series,
    _frame_empty,
    _ifind_tables_to_rows,
    _is_a_share_equity,
    _iso_to_yyyymmdd,
    _return_ratio_factors,
    _safe_float,
    _safe_int,
    _sina_symbol,
    _split_baostock_code,
    _split_tushare_code,
    _weekday_list,
    _yyyymmdd_to_iso,
)
# Schema + row persistence live in pricedb_storage; they take a conn and never
# open one (get_db and DB_PATH stay here — tests monkeypatch pricedb.DB_PATH).
from pricedb.storage import (  # noqa: F401
    _last_fully_covered_date,
    _partial_price_dates,
    clear_all_data,
    ensure_schema,
    invalidate_rps_cache,
    upsert_stocks,
    write_bars,
)
# Adjustment-factor derivation/sync/repair lives in pricedb_factors — the explicit
# owner whose absence let cmd_snapshot advance prices while nothing advanced
# factors (2026-08-30). Network fetches stay HERE; factors imports them lazily.
from pricedb.factors import (  # noqa: F401
    _expand_events_to_code_dates,
    _forward_fill_factors,
    _ifind_event_multipliers,
    _sync_or_heal_factors,
    derive_factors_eastmoney,
    derive_factors_from_akshare,
    heal_adj_factor_gap,
    rebuild_factors_from_ifind,
    sync_adj_factors_for_today,
    upsert_adj_factors,
)
# Health reporting lives in pricedb_health; doctor.py and the phase-1 contract
# both consume its verdict.
from pricedb.health import db_health, _spot_audit  # noqa: F401
# The network layer. providers OWNS the fetchers and their tuning — tests that
# fake fetch internals patch pricedb.providers, not this namespace (2026-08-31).
from pricedb.providers import (  # noqa: F401
    EASTMONEY_CLIST_PAGE_SIZE,
    AKSHARE_RETRY_DELAY,
    EASTMONEY_RETRY_DELAY,
    PRICEDB_CALL_TIMEOUT_SEC,
    PROVIDER_BAOSTOCK,
    PROVIDER_EASTMONEY,
    PROVIDER_EASTMONEY_CLIST,
    PROVIDER_IFIND,
    PROVIDER_TUSHARE,
    TUSHARE_RETRY_DELAY,
    _TimeoutError,
    _backfill_from_akshare_spot,
    _bulk_fetch_akshare,
    _bulk_fetch_baostock,
    _bulk_fetch_eastmoney,
    _bulk_fetch_eastmoney_clist,
    _bulk_fetch_ifind,
    _bulk_fetch_sina,
    _bulk_fetch_tushare,
    _bulk_fetchers,
    _call_tushare,
    _eastmoney_clist_url,
    _fetch_clist_page,
    _fetch_clist_prev_close_map,
    _fetch_eastmoney_json,
    _fetch_eastmoney_json_curl,
    _fetch_eastmoney_json_urllib,
    _fetch_ex_div_codes_datacenter,
    _fetch_klines_akshare,
    _fetch_klines_akshare_with_retries,
    _fetch_klines_baostock,
    _fetch_klines_eastmoney,
    _fetch_klines_eastmoney_with_retries,
    _fetch_klines_sina,
    _ifind_af_series,
    _iter_clist_diff,
    _kline_closes_eastmoney,
    _no_proxy_env,
    _parse_clist_page,
    _positive_int_from_env,
    _read_env_file,
    _run_with_timeout,
    _snapshot_via_ifind,
    bulk_fetch,
    close_provider,
    fetch_adj_factor_events_sina,
    fetch_stock_list,
    fetch_stock_list_akshare,
    fetch_stock_list_baostock,
    fetch_stock_list_tushare,
    fetch_trade_dates_free,
    fetch_trade_dates_tushare,
    get_tushare_token,
    iter_providers,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_DIR = PROJECT_ROOT / "data" / "pricedb"
DB_PATH = DB_DIR / "ashare_prices.db"
ENV_FILE = PROJECT_ROOT / ".env"

# Kept as "eastmoney_direct" for backwards compatibility (manifest references).
PROVIDER_AKSHARE = "akshare"
PROVIDER_SINA = "sina"

# iFinD bulk-fetch tuning. 800 codes/request measured clean (perf 111ms); 500
# leaves headroom. The client threads within a batch, so this is the outer
# chunk at which the update budget is re-checked.
IFIND_BATCH_TIMEOUT_SEC = float(os.getenv("IFIND_BATCH_TIMEOUT", "120"))
# ths_af_stock is an exact published factor, not an inference, so only float
# noise needs suppressing — see the threshold note in sync_adj_factors_for_today.
IFIND_ADJ_EVENT_EPSILON = 1e-9

# History needed: 250-day RPS + 10-day MA buffer → use extra holiday margin
INIT_HISTORY_DAYS = 450
# A-share boards: SH main + SH STAR + SZ main + SZ ChiNext + BJ.

# Per-API-call hard timeout (socket read + connect). If a single call exceeds
# this, we fail fast and let the retry/provider-fallback logic handle it.

# Per-update overall wall-clock budget. Enforced at the top of cmd_update.
# Default tightened to 300s — the clist bulk path should finish in ~60s.
PRICEDB_UPDATE_BUDGET_SEC = float(os.getenv("PRICEDB_UPDATE_BUDGET", "300"))

# Belt-and-suspenders: protect against any library that creates raw sockets
# without explicit timeouts (some baostock/urllib paths). Per-call thread
# wrappers below remain the primary defense.
socket.setdefaulttimeout(PRICEDB_CALL_TIMEOUT_SEC)

# Module-level deadline for cmd_update. Set at the start of cmd_update;
# checked from within bulk_fetch helpers via _budget_exceeded().
_UPDATE_DEADLINE: float | None = None






def _budget_exceeded() -> bool:
    """Return True if the current cmd_update has run past its wall-clock budget."""
    return _UPDATE_DEADLINE is not None and time.monotonic() > _UPDATE_DEADLINE


# Fraction of the known universe a date must cover to count as a "complete"
# trading day. Shared conceptually with rps_calculator's reference-date guard.
PRICEDB_COVERAGE_THRESHOLD = float(os.getenv("RPS_REFERENCE_DATE_MIN_COVERAGE", "0.9"))


def _now() -> datetime:
    """Wall clock, wrapped so tests can inject a fixed time."""
    return datetime.now()


def is_session_open(now: datetime | None = None) -> bool:
    """True while the A-share regular session is still open (before 15:00 local).

    During an open session, the only "today" bar available is a real-time spot
    snapshot, not a settled close — writing it into daily_prices corrupts MA/RPS.
    Env-overridable close time via RPS_SESSION_CLOSE_HHMM (e.g. "1500").
    """
    now = now or _now()
    raw = os.getenv("RPS_SESSION_CLOSE_HHMM", "1500").strip()
    try:
        close_h, close_m = int(raw[:2]), int(raw[2:4])
    except (ValueError, IndexError):
        close_h, close_m = 15, 0
    return (now.hour, now.minute) < (close_h, close_m)


def last_settled_trading_day(now: datetime | None = None) -> _date:
    """Most recent trading day whose session has fully closed.

    During an open session today's bar is not settled yet (and by design is not
    written to daily_prices), so the freshest *legitimate* data is the previous
    trading day. This is the correct "expected latest" for staleness checks and
    mirrors the cmd_update end-cap — without it, a mid-session staleness gate
    would demand a bar that intentionally does not exist yet.
    """
    now = now or _now()
    ref = now.date()
    if is_session_open(now):
        ref = ref - timedelta(days=1)
    return most_recent_trading_day(ref)






# ---------------------------------------------------------------------------
# Trade calendar (no-auth, akshare-based with weekday fallback)
# ---------------------------------------------------------------------------


_TRADE_CALENDAR_CACHE: list[str] | None = None






def _get_trade_calendar_cached() -> list[str]:
    """Return cached trading-day list (YYYYMMDD strings) covering the last ~5 years to today."""
    global _TRADE_CALENDAR_CACHE
    if _TRADE_CALENDAR_CACHE is None:
        beg = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y%m%d")
        end = datetime.now().strftime("%Y%m%d")
        _TRADE_CALENDAR_CACHE = fetch_trade_dates_free(beg, end)
    return _TRADE_CALENDAR_CACHE


def _reset_trade_calendar_cache():
    """Test helper: clear the cached calendar."""
    global _TRADE_CALENDAR_CACHE
    _TRADE_CALENDAR_CACHE = None


def most_recent_trading_day(target: _date, calendar: list[str] | None = None) -> _date:
    """Return the most recent trading day on or before ``target``.

    Uses akshare calendar when available; falls back to walking back over weekends.
    """
    if calendar is None:
        calendar = _get_trade_calendar_cached()
    if calendar:
        key = target.strftime("%Y%m%d")
        idx = bisect.bisect_right(calendar, key) - 1
        if idx >= 0:
            return datetime.strptime(calendar[idx], "%Y%m%d").date()
    d = target
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def get_db() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")
    return conn










# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------






# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------






# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------




















# ---------------------------------------------------------------------------
# Eastmoney direct provider
# ---------------------------------------------------------------------------






















# ---------------------------------------------------------------------------
# Eastmoney clist (bulk daily snapshot) provider
# ---------------------------------------------------------------------------












# ---------------------------------------------------------------------------
# Tushare provider
# ---------------------------------------------------------------------------










# ---------------------------------------------------------------------------
# AkShare provider
# ---------------------------------------------------------------------------










# ---------------------------------------------------------------------------
# BaoStock provider
# ---------------------------------------------------------------------------










# ---------------------------------------------------------------------------
# Unified provider API
# ---------------------------------------------------------------------------












# ---------------------------------------------------------------------------
# Provider-driven sync flows
# ---------------------------------------------------------------------------


def cleanup_failed_init_artifacts():
    """Remove partially created DB files after a failed init."""
    try:
        DB_PATH.unlink(missing_ok=True)
        DB_PATH.with_suffix(DB_PATH.suffix + ".wal").unlink(missing_ok=True)
        DB_PATH.with_suffix(DB_PATH.suffix + ".shm").unlink(missing_ok=True)
    except OSError:
        pass


def cmd_init():
    """Create DB, fetch stock list, download all historical data."""
    beg = (datetime.now() - timedelta(days=INIT_HISTORY_DAYS)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")
    provider_errors = []

    for provider_name, provider in iter_providers():
        if provider_name == PROVIDER_SINA:
            # sina has no stock-list endpoint; init needs list + history from
            # one provider (akshare). repair/update cover sina afterwards.
            close_provider(provider_name, provider)
            continue
        conn = get_db()
        ensure_schema(conn)
        clear_all_data(conn)
        try:
            print(f"Fetching A-share stock list via {provider_name}...", file=sys.stderr)
            stocks = fetch_stock_list(provider_name, provider)
            print(f"  Found {len(stocks)} stocks", file=sys.stderr)
            if not stocks:
                raise RuntimeError(f"{provider_name} returned no stocks")

            upsert_stocks(conn, stocks)
            invalidate_rps_cache(conn)

            print(f"Downloading historical data via {provider_name} ({beg} → {end})...", file=sys.stderr)
            bulk_fetch(conn, stocks, beg, end, provider_name, provider)
            conn.close()
            print(f"Init complete via {provider_name}.", file=sys.stderr)
            close_provider(provider_name, provider)
            return
        except Exception as e:
            provider_errors.append(f"{provider_name}: {e}")
            print(f"  {provider_name} init failed: {e}", file=sys.stderr)
            conn.close()
            close_provider(provider_name, provider)

    cleanup_failed_init_artifacts()
    print("Init failed. Providers tried:", file=sys.stderr)
    for err in provider_errors:
        print(f"  - {err}", file=sys.stderr)
    sys.exit(1)


def cmd_update():
    """Incremental update: fetch missing dates since last update."""
    if not DB_PATH.exists():
        print("DB not found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)

    global _UPDATE_DEADLINE
    _UPDATE_DEADLINE = time.monotonic() + PRICEDB_UPDATE_BUDGET_SEC

    conn = get_db()
    ensure_schema(conn)

    row = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()
    latest = row[0] if row and row[0] else None
    if not latest:
        print("No price data in DB. Run 'init' first.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    # Advance the incremental cursor from the last *fully-covered* day, not just
    # MAX(date). A day left partial by the budget or a flaky provider must be
    # re-fetched, but MAX(date) would skip it once any later day landed a single
    # row. Fall back to MAX(date) if no day yet clears the coverage bar.
    cursor_date = _last_fully_covered_date(conn) or latest
    if cursor_date != latest:
        print(
            f"Last fully-covered day is {cursor_date} (MAX(date)={latest}); "
            f"re-fetching partial days from {cursor_date} forward.",
            file=sys.stderr,
        )
    beg = (datetime.strptime(cursor_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
    # Never fetch today's bar while the session is open — every provider path
    # would return an unsettled intraday bar, which corrupts MA/RPS (RC1).
    # And never fetch a non-trading day at all: on weekends/holidays an
    # uncapped window made the per-code sweep hammer ~5.5k symbols for zero
    # rows until the budget died (surfaced 2026-08-01 by the akshare-primary
    # chain). Cap at the last settled trading day in both cases.
    end_date = _now().date()
    if is_session_open():
        end_date = most_recent_trading_day(end_date - timedelta(days=1))
        print(
            f"Session open — capping fetch window at last closed session {end_date.isoformat()} "
            f"(today's bar is not settled yet).",
            file=sys.stderr,
        )
    else:
        end_date = most_recent_trading_day(end_date)
    end = end_date.strftime("%Y%m%d")
    provider_errors = []

    stocks = [
        {"code": row[0], "name": row[1], "exchange": row[2]}
        for row in conn.execute("SELECT code, name, exchange FROM stocks")
    ]
    if not stocks:
        print("No stocks in DB. Run 'init' first.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    for provider_name, provider in iter_providers():
        if _budget_exceeded():
            print(
                f"  Skipping {provider_name}: update budget exceeded "
                f"({PRICEDB_UPDATE_BUDGET_SEC:.0f}s)",
                file=sys.stderr,
            )
            close_provider(provider_name, provider)
            continue
        try:
            if provider_name == PROVIDER_AKSHARE:
                # Best-effort universe refresh (new listings). A list failure
                # must not cost us the price bars — degrade to the stored
                # universe and keep going.
                try:
                    print("Refreshing stock list via akshare...", file=sys.stderr)
                    latest_stocks = fetch_stock_list(provider_name, provider)
                    if latest_stocks:
                        upsert_stocks(conn, latest_stocks)
                        stocks = [
                            {"code": row[0], "name": row[1], "exchange": row[2]}
                            for row in conn.execute(
                                "SELECT code, name, exchange FROM stocks")
                        ]
                        print(f"  {len(latest_stocks)} stocks in universe",
                              file=sys.stderr)
                except Exception as list_err:
                    print(f"  stock-list refresh failed ({list_err}) — using "
                          f"stored universe of {len(stocks)}", file=sys.stderr)
            else:
                print(f"Using existing stock universe for {provider_name}: {len(stocks)} stocks", file=sys.stderr)

            missing_codes = {
                row[0]
                for row in conn.execute(
                    "SELECT s.code FROM stocks s "
                    "LEFT JOIN daily_prices d ON d.code = s.code "
                    "WHERE d.code IS NULL"
                )
            }

            if beg > end and not missing_codes:
                # Nothing to FETCH is not nothing to DO. `snapshot` writes the
                # close-slot bars without touching adj_factors, and that write
                # is what lands us here — prices already at today, so beg > end.
                # Returning now would skip the reconciliation below and leave
                # factors a session behind on every afternoon run (2026-08-30).
                # Catch-up is a reconciliation step, not a consequence of
                # fetching, so it runs on this path too; it is a cheap no-op
                # when nothing is out of step.
                try:
                    changed = _sync_or_heal_factors(conn)
                    if changed:
                        invalidate_rps_cache(conn, changed)
                except Exception as factor_err:
                    print(f"  WARNING: adjustment-factor sync failed: {factor_err} "
                          f"— run 'pricedb.py factors heal' to repair.",
                          file=sys.stderr)
                print(f"Already up to date (latest: {latest}).", file=sys.stderr)
                close_provider(provider_name, provider)
                conn.close()
                return

            if beg <= end:
                print(f"Updating {len(stocks)} stocks via {provider_name} ({beg} → {end})...", file=sys.stderr)
                invalidate_rps_cache(conn, _yyyymmdd_to_iso(beg))
                bulk_fetch(conn, stocks, beg, end, provider_name, provider)

            if missing_codes:
                missing_stocks = [stock for stock in stocks if stock["code"] in missing_codes]
                init_beg = (datetime.now() - timedelta(days=INIT_HISTORY_DAYS)).strftime("%Y%m%d")
                print(
                    f"Backfilling {len(missing_stocks)} newly discovered stocks via {provider_name} ({init_beg} → {end})...",
                    file=sys.stderr,
                )
                invalidate_rps_cache(conn, _yyyymmdd_to_iso(init_beg))
                bulk_fetch(conn, missing_stocks, init_beg, end, provider_name, provider)

            close_provider(provider_name, provider)

            # Check if today's data actually landed. Only backfill from the
            # AkShare real-time spot endpoint AFTER the session has closed —
            # mid-session that endpoint returns an intraday snapshot, and writing
            # it as today's "close" corrupts MA/RPS (RC1). Before close we leave
            # today absent so the last settled close stays the newest bar.
            today_iso = datetime.now().strftime("%Y-%m-%d")
            today_count = conn.execute(
                "SELECT COUNT(*) FROM daily_prices WHERE date = ?", (today_iso,)
            ).fetchone()[0]
            if today_count == 0 and beg <= end and not is_session_open():
                print(f"  {provider_name} returned no data for {today_iso}, trying AkShare spot...", file=sys.stderr)
                inserted = _backfill_from_akshare_spot(conn, today_iso)
                if inserted:
                    invalidate_rps_cache(conn, today_iso)
                    print(f"  AkShare spot: {inserted} rows inserted for {today_iso}", file=sys.stderr)
                else:
                    print(f"  AkShare spot: no data either", file=sys.stderr)
            elif today_count == 0 and beg <= end and is_session_open():
                print(
                    f"  Session still open — skipping intraday spot backfill for {today_iso} "
                    f"(would not be a settled close).",
                    file=sys.stderr,
                )

            # Best-effort adjustment-factor sync (same-day f18 fast path, or
            # gap heal via the ex-div calendar after downtime). Failure
            # degrades to forward-filled factors and self-heals next run.
            try:
                changed = _sync_or_heal_factors(conn)
                if changed:
                    invalidate_rps_cache(conn, changed)
            except Exception as factor_err:
                print(f"  WARNING: adjustment-factor sync failed: {factor_err} "
                      f"— indicators fall back to last known factors; "
                      f"run 'pricedb.py factors heal' to repair.",
                      file=sys.stderr)

            conn.close()
            if _budget_exceeded():
                print(
                    f"WARNING: update budget ({PRICEDB_UPDATE_BUDGET_SEC:.0f}s) exceeded via "
                    f"{provider_name}; recent-day coverage may be PARTIAL. "
                    f"Re-run 'pricedb update' — the cursor self-heals from the last full day.",
                    file=sys.stderr,
                )
            else:
                print(f"Update complete via {provider_name}.", file=sys.stderr)
            return
        except Exception as e:
            provider_errors.append(f"{provider_name}: {e}")
            print(f"  {provider_name} update failed: {e}", file=sys.stderr)
            close_provider(provider_name, provider)

    conn.close()
    print("Update failed. Providers tried:", file=sys.stderr)
    for err in provider_errors:
        print(f"  - {err}", file=sys.stderr)
    sys.exit(1)




# --------------------------------------------------------------------------- #
# Adjustment factors (read-time price adjustment; see price_adjust.py)
# --------------------------------------------------------------------------- #
# A daily return ratio |m-1| below this is rounding noise from eastmoney's
# 2-dp adjusted closes, not a corporate action. Dividends below 0.5% are
# negligible for MA/RPS anyway.
ADJ_EVENT_THRESHOLD = 0.005
# Politeness for the factor backfill. The first run hammered eastmoney's kline
# API at ~3 req/s with no sleep and got this IP temporarily banned (empty
# replies on push2his AND push2 — which also starves the daily pipeline).
# Never again: pace requests, and circuit-break on failure bursts.
# Owned by pricedb.factors since 2026-09-01 (was defined twice; the duplicate
# made monkeypatch.setattr(pricedb, ...) inert for the heal path).
from pricedb.factors import ADJ_BACKFILL_SLEEP_SEC  # noqa: F401

# Sina repair sweep: 4 workers × 0.25s/request ≈ 15 req/s — polite enough to
# stay under sina's IP-ban radar while covering ~5.5k codes in a few minutes.
SINA_REPAIR_WORKERS = int(os.getenv("SINA_REPAIR_WORKERS", "4"))
SINA_REPAIR_SLEEP_SEC = float(os.getenv("SINA_REPAIR_SLEEP_SEC", "0.25"))
ADJ_BACKFILL_COOLDOWN_SEC = float(os.getenv("ADJ_BACKFILL_COOLDOWN_SEC", "300"))
ADJ_BACKFILL_MAX_COOLDOWNS = 3




















































def cmd_factors(args: list):
    """CLI: pricedb.py factors backfill|update|heal|verify|rebuild [--beg --end]

    backfill — codes with zero factor rows (per-code sina/eastmoney, resumable)
    update   — daily incremental (iFinD af ratio, clist f18 fallback; auto-heals)
    heal     — repair a multi-session gap (ex-div calendar + re-derivation);
               --beg/--end are ISO dates, default = the current gap
    verify   — coverage/lag audit, exit 1 on failure
    rebuild  — rebuild whole series from iFinD ths_af_stock (--code CSV to
               limit, --dry-run to preview). Destructive: it DELETEs each
               rebuilt code's rows first, so back up adj_factors beforehand.
    """
    global _UPDATE_DEADLINE
    _UPDATE_DEADLINE = None  # factor work is budget-exempt (off-hours, resumable)

    sub = args[0] if args else "verify"
    conn = get_db()
    ensure_schema(conn)

    if sub == "verify":
        cov = price_adjust.factor_coverage(conn)
        non_bj_missing, fresh_ipos = cov["non_bj_missing"], cov["fresh_ipos"]
        print(f"Factor coverage (all rows): {cov['pair_coverage_pct']:.2f}%")
        print(f"Factor coverage (factored universe): {cov['universe_coverage_pct']:.2f}%")
        print(f"Codes without factors: {cov['codes_without_factors']} "
              f"(non-BJ: {len(non_bj_missing)}{' — ' + ','.join(non_bj_missing[:5]) if non_bj_missing else ''}"
              f"{f'; 次新豁免 {len(fresh_ipos)}: ' + ','.join(fresh_ipos[:5]) if fresh_ipos else ''})")
        print(f"Latest price date:  {cov['max_price_date']}")
        print(f"Latest factor date: {cov['max_factor_date']}")
        conn.close()
        if not cov["healthy"]:
            for p in cov["problems"]:
                print(f"VERIFY FAILED: {p}", file=sys.stderr)
            sys.exit(1)
        print("VERIFY OK (BJ codes deliberately unfactored — read as 1.0)")
        return

    if sub == "rebuild":
        def _arg(flag, default=None):
            return args[args.index(flag) + 1] if flag in args else default

        if not ifind_client.is_available():
            print("iFinD not configured — cannot rebuild", file=sys.stderr)
            conn.close()
            sys.exit(1)
        dry = "--dry-run" in args
        code_arg = _arg("--code")
        codes = [c.strip() for c in code_arg.split(",")] if code_arg else None
        print(f"factors rebuild from iFinD"
              f"{' (dry run)' if dry else ''}"
              f"{f' — {len(codes)} code(s)' if codes else ' — ALL codes'}",
              file=sys.stderr)
        stats = rebuild_factors_from_ifind(conn, codes, dry_run=dry)
        try:
            print(f"\n  codes targeted : {stats['codes']}"
                  f"{' (SAMPLE)' if stats.get('sampled') else ''}", file=sys.stderr)
            print(f"  rebuilt        : {stats['rebuilt']}", file=sys.stderr)
            print(f"  factor rows    : {stats['rows']:,}", file=sys.stderr)
            print(f"  no iFinD data  : {stats['no_data']}", file=sys.stderr)
            print(f"  failed         : {stats['failed']}", file=sys.stderr)
            print(f"  dataVol spent  : {ifind_client.get_client().data_vol:,}",
                  file=sys.stderr)
            if stats.get("sampled"):
                print(f"  ⚠ SAMPLE ONLY — a real run would cost roughly "
                      f"{stats['estimated_rows']:,} points against the "
                      f"5,000,000 基本面数据 bucket (shared with basic_data_service "
                      f"and report_query). Check the portal before running.",
                      file=sys.stderr)
            if not dry:
                invalidate_rps_cache(conn)
                print("  rps_cache invalidated", file=sys.stderr)
        finally:
            conn.close()
        return

    if sub == "update":
        try:
            changed = _sync_or_heal_factors(conn)
            if changed:
                invalidate_rps_cache(conn, changed)
                print(f"  rps_cache invalidated from {changed}", file=sys.stderr)
        finally:
            conn.close()
        return

    if sub == "heal":
        def _arg(flag, default):
            return args[args.index(flag) + 1] if flag in args else default

        cov = price_adjust.factor_coverage(conn)
        mfd = cov["max_factor_date"]
        default_beg = (
            (datetime.strptime(mfd, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            if mfd else None
        )
        beg = _arg("--beg", default_beg)
        end = _arg("--end", cov["max_price_date"])
        if not beg or not end or beg > end:
            print(f"Nothing to heal (factors {mfd} vs prices {cov['max_price_date']}).",
                  file=sys.stderr)
            conn.close()
            return
        try:
            changed = heal_adj_factor_gap(conn, beg, end)
            if changed:
                invalidate_rps_cache(conn, changed)
                print(f"  rps_cache invalidated from {changed} — run "
                      f"'pricedb.py rps' to recompute.", file=sys.stderr)
        finally:
            conn.close()
        return

    if sub == "backfill":
        import akshare as ak

        def _arg(flag, default):
            return args[args.index(flag) + 1] if flag in args else default

        beg = _arg("--beg", None)
        end = _arg("--end", datetime.now().strftime("%Y%m%d"))
        if beg is None:
            first = conn.execute("SELECT MIN(date) FROM daily_prices").fetchone()[0]
            beg = first.replace("-", "") if first else "20241201"

        # Resumable: a processed code has factor rows (incl. 1.0s); remaining
        # work = codes present in daily_prices with zero factor rows.
        todo = [r[0] for r in conn.execute(
            "SELECT DISTINCT code FROM daily_prices "
            "EXCEPT SELECT DISTINCT code FROM adj_factors ORDER BY 1"
        )]
        exchanges = dict(conn.execute("SELECT code, exchange FROM stocks"))
        print(f"Backfilling factors for {len(todo)} codes ({beg} → {end})...",
              file=sys.stderr)
        earliest_changed: str | None = None
        done = failed = consecutive_failures = cooldowns = 0
        for code in todo:
            try:
                # Sina publishes hfq factors directly (1 tiny request/stock) —
                # primary source. Eastmoney return-ratio derivation and akshare
                # remain as fallbacks for codes sina doesn't carry.
                events = fetch_adj_factor_events_sina(code, exchanges.get(code, ""))
                if events is not None:
                    rows = _expand_events_to_code_dates(conn, code, events)
                else:
                    series = derive_factors_eastmoney(code, exchanges.get(code, ""), beg, end)
                    if not series:
                        series = derive_factors_from_akshare(ak, code, beg, end)
                    rows = [(code, d, f) for d, f in series]
                if rows:
                    changed = upsert_adj_factors(conn, rows)
                    if changed and (earliest_changed is None or changed < earliest_changed):
                        earliest_changed = changed
                done += 1
                consecutive_failures = 0
            except Exception as e:  # keep sweeping; rerun heals the rest
                failed += 1
                consecutive_failures += 1
                print(f"  {code}: FAILED ({str(e)[:80]})", file=sys.stderr)
                if consecutive_failures >= 10:
                    cooldowns += 1
                    if cooldowns > ADJ_BACKFILL_MAX_COOLDOWNS:
                        print(
                            "ABORT: sustained connection failures — likely an "
                            "upstream IP throttle/ban. Backfill is resumable; "
                            "retry later with the same command.",
                            file=sys.stderr,
                        )
                        break
                    print(
                        f"  circuit breaker: {consecutive_failures} consecutive "
                        f"failures — cooling down {ADJ_BACKFILL_COOLDOWN_SEC:.0f}s "
                        f"({cooldowns}/{ADJ_BACKFILL_MAX_COOLDOWNS})",
                        file=sys.stderr,
                    )
                    time.sleep(ADJ_BACKFILL_COOLDOWN_SEC)
                    consecutive_failures = 0
            if (done + failed) % 100 == 0:
                print(f"  progress: {done + failed}/{len(todo)} "
                      f"({failed} failed)", file=sys.stderr)
            time.sleep(ADJ_BACKFILL_SLEEP_SEC)
        filled = _forward_fill_factors(conn)
        print(f"Backfill done: {done} ok, {failed} failed, forward-filled {filled} rows.",
              file=sys.stderr)
        if earliest_changed:
            invalidate_rps_cache(conn, earliest_changed)
            print(f"rps_cache invalidated from {earliest_changed} — run "
                  f"'pricedb.py rps' to recompute.", file=sys.stderr)
        conn.close()
        return

    conn.close()
    print(f"Unknown factors subcommand: {sub}", file=sys.stderr)
    sys.exit(1)








def backfill_amount(conn: sqlite3.Connection, beg: str, end: str,
                    dry_run: bool = False, batch_days: int = 20) -> dict:
    """Fill NULL `daily_prices.amount` from iFinD. Returns a stats dict.

    Why this is a separate command rather than a re-fetch: `amount` is NULL
    wherever _fetch_klines_sina did the filling (sina's kline archive doesn't
    publish turnover), which in August was most sessions. Re-running `update`
    cannot repair them — every writer is INSERT OR IGNORE, and first-writer-wins
    is deliberate, so the existing rows would simply be skipped.

    This writes ONLY the amount column. OHLCV is never touched, so the
    first-writer-wins invariant holds and the command is idempotent.

    Safety gate: iFinD's close for a bar must match the stored close before we
    write. A mismatch means we are about to staple turnover onto a different
    bar — count it and skip. Those are reported, never silently dropped.
    """
    client = ifind_client.get_client()
    ex_map = {c: e for c, e in conn.execute("SELECT code, exchange FROM stocks")}

    dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM daily_prices "
        "WHERE amount IS NULL AND date BETWEEN ? AND ? ORDER BY date",
        (beg, end))]
    stats = {"dates": len(dates), "candidates": 0, "filled": 0,
             "conflicted": 0, "missing": 0, "failed_batches": 0}
    if not dates:
        return stats

    print(f"  {len(dates)} session(s) with NULL amount in {beg}..{end}",
          file=sys.stderr)

    # Group into contiguous date windows so one request covers many sessions.
    for i in range(0, len(dates), batch_days):
        window = dates[i:i + batch_days]
        w_beg, w_end = window[0], window[-1]
        wanted = {}
        for code, date in conn.execute(
                "SELECT code, date FROM daily_prices WHERE amount IS NULL "
                "AND date BETWEEN ? AND ?", (w_beg, w_end)):
            wanted.setdefault(code, set()).add(date)
        if not wanted:
            continue
        stats["candidates"] += sum(len(v) for v in wanted.values())

        ths_to_code = {ifind_client.to_ths_code(c, ex_map.get(c)): c for c in wanted}
        try:
            tables = _run_with_timeout(
                "iFinD amount backfill",
                lambda: client.history_quotation(
                    list(ths_to_code), "close,amount", w_beg, w_end),
                timeout=IFIND_BATCH_TIMEOUT_SEC)
        except Exception as e:
            stats["failed_batches"] += 1
            print(f"    ⚠ {w_beg}..{w_end} failed: {str(e)[:80]}", file=sys.stderr)
            continue

        updates = []
        for table in tables:
            code = ths_to_code.get(table.get("thscode"))
            if not code:
                continue
            cols = table.get("table") or {}
            closes, amounts = cols.get("close") or [], cols.get("amount") or []
            for j, day in enumerate(table.get("time") or []):
                day = str(day)[:10]
                if day not in wanted.get(code, ()):
                    continue
                amount = amounts[j] if j < len(amounts) else None
                close = closes[j] if j < len(closes) else None
                if amount is None or close is None:
                    stats["missing"] += 1
                    continue
                stored = conn.execute(
                    "SELECT close FROM daily_prices WHERE code=? AND date=?",
                    (code, day)).fetchone()
                if not stored or stored[0] is None:
                    stats["missing"] += 1
                    continue
                if abs(stored[0] - close) > max(0.011, abs(close) * 0.0005):
                    stats["conflicted"] += 1
                    continue
                updates.append((amount, code, day))

        if updates and not dry_run:
            cur = conn.executemany(
                "UPDATE daily_prices SET amount = ? "
                "WHERE code = ? AND date = ? AND amount IS NULL", updates)
            conn.commit()
            stats["filled"] += cur.rowcount
        elif updates:
            stats["filled"] += len(updates)
        print(f"    {w_beg}..{w_end}: {len(updates)} filled, "
              f"{stats['conflicted']} conflicted so far", file=sys.stderr)

    return stats


def cmd_backfill_amount(args: list):
    """CLI: pricedb.py backfill-amount [--beg ISO] [--end ISO] [--dry-run]

    Repairs the `amount` column, which is NULL wherever the sina kline fallback
    did the filling. Writes nothing but `amount`.
    """
    global _UPDATE_DEADLINE
    _UPDATE_DEADLINE = None  # off-hours repair, budget-exempt like cmd_repair

    def _arg(flag, default):
        return args[args.index(flag) + 1] if flag in args else default

    dry = "--dry-run" in args
    conn = get_db()
    ensure_schema(conn)

    if not ifind_client.is_available():
        print("iFinD not configured (IFIND_REFRESH_TOKEN) — cannot backfill",
              file=sys.stderr)
        conn.close()
        sys.exit(1)

    first = conn.execute("SELECT MIN(date) FROM daily_prices").fetchone()[0]
    last = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()[0]
    beg = _arg("--beg", first)
    end = _arg("--end", last)

    before = conn.execute(
        "SELECT COUNT(*) FROM daily_prices WHERE amount IS NULL "
        "AND date BETWEEN ? AND ?", (beg, end)).fetchone()[0]
    print(f"amount backfill {beg} → {end}: {before:,} NULL rows"
          f"{' (dry run)' if dry else ''}", file=sys.stderr)

    stats = backfill_amount(conn, beg, end, dry_run=dry)

    after = conn.execute(
        "SELECT COUNT(*) FROM daily_prices WHERE amount IS NULL "
        "AND date BETWEEN ? AND ?", (beg, end)).fetchone()[0]
    conn.close()

    print(f"\n  sessions scanned : {stats['dates']}", file=sys.stderr)
    print(f"  candidates       : {stats['candidates']:,}", file=sys.stderr)
    print(f"  filled           : {stats['filled']:,}", file=sys.stderr)
    print(f"  conflicted       : {stats['conflicted']:,}  "
          f"(close mismatch — NOT written)", file=sys.stderr)
    print(f"  no iFinD amount  : {stats['missing']:,}", file=sys.stderr)
    print(f"  failed batches   : {stats['failed_batches']}", file=sys.stderr)
    print(f"  NULL amount      : {before:,} → {after:,}", file=sys.stderr)
    if stats["conflicted"]:
        print("  ⚠ conflicts mean iFinD and the stored bar disagree on close — "
              "inspect before assuming the stored bar is right", file=sys.stderr)


def cmd_repair(args: list):
    """CLI: pricedb.py repair [--beg ISO] [--end ISO] [--dry-run]

    Fill partial price days from Sina's per-code kline service (raw prices,
    one request per stock covers every gap day in the window at once).
    INSERT OR IGNORE — existing rows are never overwritten, so the primary
    eastmoney data stays canonical and the sweep is idempotent. Finishes
    with a factor-gap heal and rps_cache invalidation from the first
    repaired date.
    """
    global _UPDATE_DEADLINE
    _UPDATE_DEADLINE = None  # repair is budget-exempt (off-hours, resumable)

    def _arg(flag, default):
        return args[args.index(flag) + 1] if flag in args else default

    conn = get_db()
    ensure_schema(conn)
    partial = _partial_price_dates(conn)
    if not partial:
        print("No partial days detected — nothing to repair.", file=sys.stderr)
        conn.close()
        return
    beg = _arg("--beg", min(partial))
    end = _arg("--end", conn.execute(
        "SELECT MAX(date) FROM daily_prices").fetchone()[0])
    targets = [d for d in partial if beg <= d <= end]
    before = dict(conn.execute(
        "SELECT date, COUNT(*) FROM daily_prices WHERE date >= ? AND date <= ? "
        "GROUP BY date", (beg, end)))
    print(f"Partial days in [{beg}, {end}]: "
          f"{', '.join(f'{d}({before.get(d, 0)})' for d in targets)}",
          file=sys.stderr)
    if "--dry-run" in args:
        conn.close()
        return

    # One sina call per code returns its last N bars — size N to reach back
    # past the earliest target date, with margin for suspensions.
    n_dates = conn.execute(
        "SELECT COUNT(DISTINCT date) FROM daily_prices WHERE date >= ?", (beg,)
    ).fetchone()[0]
    datalen = min(1023, n_dates + 15)
    stocks = [
        {"code": r[0], "name": r[1], "exchange": r[2]}
        for r in conn.execute("SELECT code, name, exchange FROM stocks")
    ]
    print(f"Sweeping {len(stocks)} codes via sina (datalen={datalen})...",
          file=sys.stderr)

    inserted = 0
    failures: list[str] = []

    def _one(stock):
        time.sleep(SINA_REPAIR_SLEEP_SEC)
        return _fetch_klines_sina(stock, datalen)

    completed = 0
    with ThreadPoolExecutor(max_workers=SINA_REPAIR_WORKERS,
                            thread_name_prefix="pricedb-sina") as pool:
        futures = {pool.submit(_one, s): s for s in stocks}
        for future in as_completed(futures):
            stock = futures[future]
            completed += 1
            try:
                rows = [r for r in future.result() if beg <= r[1] <= end]
            except Exception as e:
                failures.append(f"{stock['code']}: {str(e)[:60]}")
                rows = []
            if rows:
                # DB writes stay on this (main) thread; workers only fetch.
                inserted += write_bars(conn, rows, replace=False)
            if completed % 250 == 0 or completed == len(stocks):
                print(f"  [sina {completed}/{len(stocks)}] "
                      f"+{inserted} rows, {len(failures)} failed",
                      file=sys.stderr)

    after = dict(conn.execute(
        "SELECT date, COUNT(*) FROM daily_prices WHERE date >= ? AND date <= ? "
        "GROUP BY date", (beg, end)))
    for d in targets:
        print(f"  {d}: {before.get(d, 0)} → {after.get(d, 0)} rows",
              file=sys.stderr)
    if failures:
        print(f"  {len(failures)} codes failed (re-run repair to retry): "
          f"{'; '.join(failures[:5])}", file=sys.stderr)

    if inserted:
        invalidate_rps_cache(conn, beg)
        print(f"rps_cache invalidated from {beg}", file=sys.stderr)
        try:
            heal_adj_factor_gap(conn, beg, end)
        except Exception as e:
            print(f"WARNING: factor heal after repair failed: {e} — run "
                  f"'pricedb.py factors heal --beg {beg}'", file=sys.stderr)
    print(f"Repair done: {inserted} rows inserted.", file=sys.stderr)
    conn.close()


def cmd_status():
    """Show DB stats."""
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}")
        print("Run 'python scripts/pricedb.py init' to create it.")
        return

    conn = get_db()
    ensure_schema(conn)

    stocks_count = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
    prices_count = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
    date_row = conn.execute("SELECT MIN(date), MAX(date) FROM daily_prices").fetchone()
    rps_dates = conn.execute("SELECT COUNT(DISTINCT date) FROM rps_cache").fetchone()[0]
    last_update = conn.execute("SELECT MAX(last_updated) FROM stocks").fetchone()[0]
    factor_cov = price_adjust.factor_coverage(conn)
    conn.close()

    size_mb = DB_PATH.stat().st_size / 1024 / 1024

    print(f"DB path  : {DB_PATH}")
    print(f"DB size  : {size_mb:.1f} MB")
    print(f"Stocks   : {stocks_count:,}")
    print(f"Prices   : {prices_count:,} rows")
    if date_row[0]:
        print(f"Date range: {date_row[0]} → {date_row[1]}")
    else:
        print("Date range: (no price data yet)")
    if last_update:
        print(f"Updated  : {last_update}")
    print(f"RPS cache: {rps_dates} dates computed")
    # Judge on the factored universe, never on pair_coverage_pct — the latter
    # counts unfactorable BJ codes in its denominator and so warns forever.
    unfactored = factor_cov["codes_without_factors"]
    note = f"; {unfactored} codes unfactored — BJ/次新, read as 1.0" if unfactored else ""
    print(f"Adj factors: {factor_cov['universe_coverage_pct']:.1f}% coverage "
          f"(latest {factor_cov['max_factor_date'] or 'none'}{note})")
    for problem in factor_cov["problems"]:
        print(f"WARNING: {problem}")


def cmd_rps(date: str = None):
    """Compute MA-based RPS for all stocks on DATE (default: latest)."""
    if not DB_PATH.exists():
        print("DB not found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from rps_calculator import compute_ma_rps

    if date is None:
        conn = get_db()
        row = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()
        date = row[0] if row and row[0] else None
        conn.close()

    if not date:
        print("No price data in DB.", file=sys.stderr)
        sys.exit(1)

    print(f"Computing MA-based RPS for {date}...", file=sys.stderr)
    t0 = time.time()
    results = compute_ma_rps(str(DB_PATH), date)
    elapsed = time.time() - t0
    print(f"  {len(results)} stocks, {elapsed:.1f}s", file=sys.stderr)

    if not results:
        print("No results.", file=sys.stderr)
        return

    top = sorted(
        [(code, data) for code, data in results.items() if data.get("rps120") is not None],
        key=lambda item: item[1]["rps120"],
        reverse=True,
    )[:20]
    print(f"\nTop 20 by RPS120 on {date}:")
    print(f"{'Code':<8} {'RPS20':>6} {'RPS60':>6} {'RPS120':>7} {'RPS250':>7} {'MA10':>10}")
    for code, data in top:
        r20 = f"{data['rps20']:.1f}" if data.get("rps20") is not None else "n/a"
        r60 = f"{data['rps60']:.1f}" if data.get("rps60") is not None else "n/a"
        r120 = f"{data['rps120']:.1f}" if data.get("rps120") is not None else "n/a"
        r250 = f"{data['rps250']:.1f}" if data.get("rps250") is not None else "n/a"
        ma10 = f"{data['ma10_today']:.2f}" if data.get("ma10_today") is not None else "n/a"
        print(f"{code:<8} {r20:>6} {r60:>6} {r120:>7} {r250:>7} {ma10:>10}")





def cmd_snapshot(argv: list):
    """CLI: pricedb.py snapshot [--date ISO] [--dry-run] [--force]

    Write today's settled bar from Sina's real-time quote feed (see
    snapshot_bars.py for why this exists and how it was validated).

    Refuses to run while the session is open: mid-session the feed reports an
    unsettled intraday bar, and writing that into daily_prices corrupts every
    MA and RPS downstream. --force overrides for testing only, never in a
    scheduled run.

    INSERT OR IGNORE, so existing rows are never overwritten — if the kline
    archive already delivered a day, this cannot damage it.
    """
    import snapshot_bars

    dry = "--dry-run" in argv
    force = "--force" in argv
    target = None
    if "--date" in argv:
        target = argv[argv.index("--date") + 1]

    if is_session_open() and not force:
        print("Session is still open — refusing to write an unsettled bar. "
              "(--force overrides, for testing only.)", file=sys.stderr)
        sys.exit(2)

    if target is None:
        target = most_recent_trading_day(_now().date()).isoformat()

    conn = get_db()
    ensure_schema(conn)
    stocks = [r[0] for r in conn.execute("SELECT code FROM stocks")]
    if not stocks:
        print("No stocks in DB. Run 'init' first.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    before = conn.execute("SELECT COUNT(*) FROM daily_prices WHERE date = ?",
                          (target,)).fetchone()[0]
    print(f"Snapshot for {target}: {len(stocks)} codes, {before} rows already present",
          file=sys.stderr)

    def _progress(done, total, got):
        if done % 1000 == 0 or done == total:
            print(f"  [snapshot {done}/{total}] {got} bars parsed", file=sys.stderr)

    rows, stats = _snapshot_via_ifind(conn, stocks, target)
    if rows is None:
        rows, stats = snapshot_bars.fetch_snapshot_bars(stocks, target,
                                                        progress=_progress)
        print(f"  parsed {stats['rows']} bars "
              f"(unsupported/BJ {stats['skipped_unsupported']}, "
              f"rejected {stats['rejected']}, failed batches {stats['failed_batches']})",
              file=sys.stderr)

    if dry:
        print("  --dry-run: nothing written", file=sys.stderr)
        conn.close()
        return

    n_ins = write_bars(conn, rows, replace=False)
    after = conn.execute("SELECT COUNT(*) FROM daily_prices WHERE date = ?",
                         (target,)).fetchone()[0]
    conn.close()
    print(f"  {target}: {before} → {after} rows ({n_ins} inserted)", file=sys.stderr)
    if stats["failed_batches"]:
        print(f"  WARNING: {stats['failed_batches']} batch(es) failed — day may be "
              f"incomplete; re-run, or let the kline archive fill the rest tonight",
              file=sys.stderr)


def cmd_query(code: str):
    """Show a stock's recent prices and computed RPS values."""
    if not DB_PATH.exists():
        print("DB not found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)

    conn = get_db()
    ensure_schema(conn)

    stock = conn.execute(
        "SELECT code, name, exchange FROM stocks WHERE code=?",
        (code,),
    ).fetchone()
    if not stock:
        print(f"Stock {code} not found in DB.")
        conn.close()
        return

    print(f"Stock: {stock[0]} ({stock[1]}) [{stock[2]}]")

    prices = conn.execute(
        "SELECT date, open, high, low, close, volume FROM daily_prices "
        "WHERE code=? ORDER BY date DESC LIMIT 20",
        (code,),
    ).fetchall()
    conn.close()

    if not prices:
        print("No price data found.")
        return

    print(f"\n{'Date':<12} {'Open':>8} {'High':>8} {'Low':>8} {'Close':>8} {'Volume':>12}")
    for row in prices:
        print(f"{row[0]:<12} {row[1]:>8.2f} {row[2]:>8.2f} {row[3]:>8.2f} {row[4]:>8.2f} {row[5]:>12,}")

    latest_date = prices[0][0]
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from rps_calculator import get_ma_rps_for_stocks

    rps_data = get_ma_rps_for_stocks(str(DB_PATH), [code], latest_date)
    rps = rps_data.get(code, {})
    if rps:
        print(f"\nRPS on {latest_date}:")
        for key in ["rps20", "rps60", "rps120", "rps250"]:
            value = rps.get(key)
            print(f"  {key.upper()}: {value:.1f}" if value is not None else f"  {key.upper()}: n/a")
        if rps.get("ma10_today"):
            print(f"  MA10 : {rps['ma10_today']:.2f}")
    else:
        print(f"\nNo RPS data for {latest_date} (insufficient history).")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    if command == "init":
        cmd_init()
    elif command == "update":
        cmd_update()
    elif command == "status":
        cmd_status()
    elif command == "rps":
        cmd_rps(sys.argv[2] if len(sys.argv) > 2 else None)
    elif command == "factors":
        cmd_factors(sys.argv[2:])
    elif command == "repair":
        cmd_repair(sys.argv[2:])
    elif command == "backfill-amount":
        cmd_backfill_amount(sys.argv[2:])
    elif command == "snapshot":
        cmd_snapshot(sys.argv[2:])
    elif command == "query":
        if len(sys.argv) < 3:
            print("Usage: pricedb.py query CODE", file=sys.stderr)
            sys.exit(1)
        cmd_query(sys.argv[2])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
