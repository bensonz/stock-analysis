#!/usr/bin/env python3
"""
rps_calculator.py — MA-based RPS computation for A-share stocks.

Uses the local price SQLite DB to compute Relative Price Strength rankings
using smoothed moving averages (MA10) instead of raw close prices.

New RPS formula:
    RPS_N = percentile_rank( MA10_today / MA10_N_trading_days_ago )  across all A-shares

Where MA10 = simple moving average of last 10 close prices.
Lookback periods: 20, 60, 120, 250 trading days.
"""

import os
import sqlite3
import sys
from datetime import datetime, time as _time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import price_adjust


def compute_ma_rps(
    db_path: str,
    date: str = None,
    ma_period: int = 10,
    debug: bool | None = None,
    force_recompute: bool | None = None,
) -> dict:
    """Compute MA-based RPS for all stocks on a given date.

    For each lookback period (20, 60, 120, 250 trading days):
      1. Get MA{ma_period} of close prices on `date`
      2. Get MA{ma_period} of close prices `lookback` trading days before `date`
      3. Compute delta = MA_today / MA_past
      4. Rank all stocks by delta → percentile (0–100)

    Results are cached in the rps_cache table for reuse.

    Returns:
        {code: {"rps20": float|None, "rps60": float|None,
                "rps120": float|None, "rps250": float|None,
                "ma10_today": float}}
    """
    debug_enabled = _debug_enabled() if debug is None else debug
    force_recompute = _debug_force_recompute() if force_recompute is None else force_recompute

    conn = sqlite3.connect(db_path)
    try:
        reference_date = _resolve_reference_date(conn, date)
        if not reference_date:
            return {}
        min_codes = _reference_date_min_codes(conn)

        _debug_print(debug_enabled, f"requested date={date or 'latest'} resolved date={reference_date} ma_period={ma_period}")

        if ma_period == 10 and not force_recompute:
            cached = conn.execute(
                "SELECT code, rps20, rps60, rps120, rps250, ma10 "
                "FROM rps_cache WHERE date=?",
                (reference_date,),
            ).fetchall()
            if cached and (min_codes <= 0 or len(cached) >= min_codes):
                _debug_print(debug_enabled, f"cache hit for {reference_date}: {len(cached)} stocks")
                return {
                    row[0]: {
                        "rps20": row[1], "rps60": row[2],
                        "rps120": row[3], "rps250": row[4],
                        "ma10_today": row[5],
                    }
                    for row in cached
                }
            if cached:
                _debug_print(
                    debug_enabled,
                    f"discarding undersized cache for {reference_date}: {len(cached)} < {min_codes}",
                )
                conn.execute("DELETE FROM rps_cache WHERE date=?", (reference_date,))
                conn.commit()

        if ma_period == 10 and force_recompute:
            _debug_print(debug_enabled, "cache bypassed via force_recompute")

        trading_dates = _load_trading_dates(conn, reference_date, 300, min_codes=min_codes)
        if not trading_dates:
            return {}

        _debug_print(
            debug_enabled,
            f"loaded {len(trading_dates)} trading dates; newest={trading_dates[:3]} oldest={trading_dates[-3:]}",
        )

        today_dates = trading_dates[:ma_period]
        ma_today = _get_ma(conn, today_dates, ma_period)
        if not ma_today:
            return {}

        _debug_print(
            debug_enabled,
            f"today window={today_dates[-1]}→{today_dates[0]} eligible_ma_today={len(ma_today)}",
        )

        # _get_ma returns hfq-scale values (dividend/split-corrected). The
        # RPS deltas below use them directly; the *reported* ma10 (and the
        # rps_cache.ma10 column) is normalized by the reference-date factor
        # back into real price scale — identical to the raw MA whenever no
        # corporate action falls inside the window.
        f_ref = price_adjust.get_factors_on_date(conn, reference_date)
        results = {
            code: {"ma10_today": round(ma / f_ref.get(code, 1.0), 4)}
            for code, ma in ma_today.items()
        }

        for lookback in [20, 60, 120, 250]:
            rps_key = f"rps{lookback}"
            if len(trading_dates) < lookback + ma_period:
                _debug_print(debug_enabled, f"{rps_key}: insufficient history ({len(trading_dates)} dates)")
                for code in results:
                    results[code][rps_key] = None
                continue

            past_dates = trading_dates[lookback: lookback + ma_period]
            ma_past = _get_ma(conn, past_dates, ma_period)
            _debug_print(
                debug_enabled,
                f"{rps_key}: past window={past_dates[-1]}→{past_dates[0]} eligible_ma_past={len(ma_past)}",
            )

            deltas: dict[str, float] = {}
            for code, ma_t in ma_today.items():
                ma_p = ma_past.get(code)
                if ma_p and ma_p > 0:
                    deltas[code] = ma_t / ma_p

            if deltas:
                sorted_codes = sorted(deltas, key=lambda candidate: deltas[candidate])
                _debug_deltas(debug_enabled, rps_key, deltas, sorted_codes, ma_today, ma_past)
                count = len(sorted_codes)
                for rank, code in enumerate(sorted_codes):
                    pct = round(rank / (count - 1) * 100, 2) if count > 1 else 50.0
                    results[code][rps_key] = pct

            for code in results:
                if rps_key not in results[code]:
                    results[code][rps_key] = None

        if ma_period == 10:
            _debug_print(debug_enabled, f"saving cache for {reference_date}: {len(results)} stocks")
            _save_cache(conn, reference_date, results)

        return results
    finally:
        conn.close()


def get_ma_rps_for_stocks(db_path: str, codes: list, date: str = None) -> dict:
    """Get MA-based RPS for specific stocks. Calls compute_ma_rps internally (cached).

    Args:
        db_path: Path to the SQLite price DB.
        codes:   List of stock codes to retrieve.
        date:    Reference date (default: latest available).

    Returns:
        {code: {rps20, rps60, rps120, rps250, ma10_today}}
    """
    all_rps = compute_ma_rps(db_path, date)
    return {code: all_rps[code] for code in codes if code in all_rps}


def compute_ma(db_path: str, code: str, date: str, period: int = 10) -> Optional[float]:
    """Compute MA for a single stock on a date.

    Args:
        db_path: Path to the SQLite price DB.
        code:    Stock code.
        date:    Reference date.
        period:  MA period (default 10).

    Returns:
        MA value or None if insufficient data.
    """
    conn = sqlite3.connect(db_path)
    try:
        reference_date = _resolve_reference_date(conn, date)
        if not reference_date:
            return None

        price_adjust.ensure_adj_schema(conn)
        rows = conn.execute(
            f"SELECT {price_adjust.adjusted_close_sql()}, {price_adjust.factor_sql()} "
            f"FROM daily_prices d{price_adjust.adj_join_sql()} "
            "WHERE d.code=? AND d.date <= ? ORDER BY d.date DESC LIMIT ?",
            (code, reference_date, period),
        ).fetchall()
        if len(rows) < period:
            return None

        # hfq average, normalized by the newest bar's factor → real price scale
        adjusted = [float(row[0]) for row in rows]
        newest_factor = float(rows[0][1]) or 1.0
        return (sum(adjusted) / period) / newest_factor
    finally:
        conn.close()


def compute_ma_alignment(db_path: str, date: str = None) -> dict:
    """Compute MA20, MA120, MA250 for all stocks for MA alignment filtering.

    Returns:
        {code: {"ma20": float, "ma120": float, "ma250": float, "aligned": bool}}
        where aligned = MA20 > MA120 > MA250
    """
    conn = sqlite3.connect(db_path)
    try:
        reference_date = _resolve_reference_date(conn, date)
        if not reference_date:
            return {}
        min_codes = _reference_date_min_codes(conn)

        trading_dates = _load_trading_dates(conn, reference_date, 260, min_codes=min_codes)
        if len(trading_dates) < 250:
            return {}

        # Adjusted (hfq-scale) MAs: the aligned comparison is scale-invariant
        # per stock, and reported values are normalized by the reference-date
        # factor back into real price scale (see _get_ma docstring).
        price_adjust.ensure_adj_schema(conn)
        results: dict[str, dict] = {}
        for period in [20, 120, 250]:
            period_dates = trading_dates[:period]
            if len(period_dates) < period:
                continue
            placeholders = ",".join(["?"] * len(period_dates))
            rows = conn.execute(
                f"SELECT d.code, AVG({price_adjust.adjusted_close_sql()}) FROM daily_prices d"
                f"{price_adjust.adj_join_sql()} "
                f"WHERE d.date IN ({placeholders}) GROUP BY d.code HAVING COUNT(*) = ?",
                period_dates + [period],
            ).fetchall()
            for row in rows:
                code = row[0]
                if code not in results:
                    results[code] = {}
                results[code][f"ma{period}"] = row[1]

        f_ref = price_adjust.get_factors_on_date(conn, reference_date)
        final: dict[str, dict] = {}
        for code, mas in results.items():
            ma20 = mas.get("ma20")
            ma120 = mas.get("ma120")
            ma250 = mas.get("ma250")
            if ma20 is not None and ma120 is not None and ma250 is not None:
                norm = f_ref.get(code, 1.0)
                final[code] = {
                    "ma20": ma20 / norm, "ma120": ma120 / norm, "ma250": ma250 / norm,
                    "aligned": ma20 > ma120 > ma250,
                }
        return final
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_ma(conn: sqlite3.Connection, dates: list, required_count: int) -> dict:
    """Average ADJUSTED close for all stocks over exactly `required_count` dates.

    Values are in hfq scale (close × cumulative factor) — per-stock consistent,
    so ratios across time windows are dividend/split-corrected. Callers that
    report an MA must normalize by the stock's reference-date factor to get
    back to real price scale. The adj_factors LEFT JOIN cannot fan out rows
    ((code,date) is the PK), so HAVING COUNT(*) semantics are unchanged.
    """
    if not dates:
        return {}
    price_adjust.ensure_adj_schema(conn)
    placeholders = ",".join(["?"] * len(dates))
    rows = conn.execute(
        f"SELECT d.code, AVG({price_adjust.adjusted_close_sql()}) FROM daily_prices d"
        f"{price_adjust.adj_join_sql()} "
        f"WHERE d.date IN ({placeholders}) GROUP BY d.code HAVING COUNT(*) = ?",
        dates + [required_count],
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _now() -> datetime:
    """Wall clock, wrapped so tests can inject a fixed time."""
    return datetime.now()


def _session_close_time() -> _time:
    """A-share regular-session close (local time). Env-overridable HHMM."""
    raw = os.getenv("RPS_SESSION_CLOSE_HHMM", "1500").strip()
    try:
        return _time(int(raw[:2]), int(raw[2:4]))
    except (ValueError, IndexError):
        return _time(15, 0)


def _open_session_date() -> Optional[str]:
    """ISO date whose bar must not be used as a reference date because the
    session is still open (the row, if any, is an intraday snapshot rather than a
    settled close). Returns None once the session has closed for the day."""
    now = _now()
    if now.time() < _session_close_time():
        return now.date().isoformat()
    return None


def _resolve_reference_date(conn: sqlite3.Connection, date: str | None) -> Optional[str]:
    """Resolve to the latest sufficiently covered trading date on or before the
    requested date.

    Never selects the current calendar day while the session is still open: that
    day's row (if present) is an intraday snapshot written by the mid-session
    pricedb update, not a settled close, and using it corrupts MA/RPS ranks.
    """
    min_codes = _reference_date_min_codes(conn)

    conditions: list[str] = []
    params: list = []
    if date is not None:
        conditions.append("date <= ?")
        params.append(date)
    open_date = _open_session_date()
    if open_date is not None:
        conditions.append("date < ?")
        params.append(open_date)
    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    if min_codes > 0:
        row = conn.execute(
            f"""
            SELECT date
            FROM daily_prices
            {where_clause}
            GROUP BY date
            HAVING COUNT(DISTINCT code) >= ?
            ORDER BY date DESC
            LIMIT 1
            """,
            params + [min_codes],
        ).fetchone()
        if row and row[0]:
            return row[0]

    row = conn.execute(
        f"SELECT MAX(date) FROM daily_prices {where_clause}",
        params,
    ).fetchone()
    return row[0] if row and row[0] else None


def _load_trading_dates(
    conn: sqlite3.Connection,
    reference_date: str,
    limit: int,
    *,
    min_codes: int | None = None,
) -> list[str]:
    """Load trading dates for MA windows, preferring sufficiently covered dates."""
    min_codes = _reference_date_min_codes(conn) if min_codes is None else min_codes

    if min_codes > 0:
        covered_rows = conn.execute(
            """
            SELECT date
            FROM daily_prices
            WHERE date <= ?
            GROUP BY date
            HAVING COUNT(DISTINCT code) >= ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (reference_date, min_codes, limit),
        ).fetchall()
        covered_dates = [row[0] for row in covered_rows if row and row[0]]
        if covered_dates:
            return covered_dates

    rows = conn.execute(
        "SELECT DISTINCT date FROM daily_prices "
        "WHERE date <= ? ORDER BY date DESC LIMIT ?",
        (reference_date, limit),
    ).fetchall()
    return [row[0] for row in rows if row and row[0]]


def _save_cache(conn: sqlite3.Connection, date: str, results: dict):
    """Persist RPS results to rps_cache table."""
    rows = [
        (
            date, code,
            d.get("rps20"), d.get("rps60"),
            d.get("rps120"), d.get("rps250"),
            d.get("ma10_today"),
        )
        for code, d in results.items()
    ]
    conn.executemany(
        "INSERT OR REPLACE INTO rps_cache "
        "(date, code, rps20, rps60, rps120, rps250, ma10) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def _debug_enabled() -> bool:
    return os.getenv("RPS_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _debug_force_recompute() -> bool:
    return os.getenv("RPS_FORCE_RECOMPUTE", "").strip().lower() in {"1", "true", "yes", "on"}


def _reference_date_coverage_threshold() -> float:
    raw = os.getenv("RPS_REFERENCE_DATE_MIN_COVERAGE", "0.9").strip()
    try:
        value = float(raw)
    except ValueError:
        return 0.9
    return min(1.0, max(0.0, value))


def _reference_date_min_codes(conn: sqlite3.Connection) -> int:
    coverage_threshold = _reference_date_coverage_threshold()
    total_codes_row = conn.execute("SELECT COUNT(DISTINCT code) FROM daily_prices").fetchone()
    total_codes = int(total_codes_row[0] or 0) if total_codes_row else 0
    return int(total_codes * coverage_threshold)


def _debug_codes() -> list[str]:
    raw = os.getenv("RPS_DEBUG_CODES", "").strip()
    if not raw:
        return []
    return [code.strip().split(".")[0] for code in raw.split(",") if code.strip()]


def _debug_limit() -> int:
    raw = os.getenv("RPS_DEBUG_LIMIT", "5").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 5


def _debug_print(enabled: bool, message: str):
    if enabled:
        print(f"[RPS] {message}", file=sys.stderr)


def _debug_deltas(enabled: bool, rps_key: str, deltas: dict[str, float], sorted_codes: list[str], ma_today: dict[str, float], ma_past: dict[str, float]):
    if not enabled or not deltas:
        return

    limit = _debug_limit()
    chosen_codes = _debug_codes()
    _debug_print(enabled, f"{rps_key}: ranked {len(sorted_codes)} stocks; min_delta={deltas[sorted_codes[0]]:.6f} max_delta={deltas[sorted_codes[-1]]:.6f}")

    bottom_codes = sorted_codes[:limit]
    top_codes = sorted_codes[-limit:]
    _debug_print(enabled, f"{rps_key}: bottom {limit} deltas={[(code, round(deltas[code], 6)) for code in bottom_codes]}")
    _debug_print(enabled, f"{rps_key}: top {limit} deltas={[(code, round(deltas[code], 6)) for code in reversed(top_codes)]}")

    if chosen_codes:
        for code in chosen_codes:
            if code not in deltas:
                _debug_print(enabled, f"{rps_key}: {code} missing eligible delta (insufficient history)")
                continue
            rank = sorted_codes.index(code)
            n = len(sorted_codes)
            pct = round(rank / (n - 1) * 100, 2) if n > 1 else 50.0
            _debug_print(
                enabled,
                f"{rps_key}: {code} ma_today={ma_today[code]:.4f} ma_past={ma_past[code]:.4f} delta={deltas[code]:.6f} rank={rank + 1}/{n} rps={pct}",
            )
