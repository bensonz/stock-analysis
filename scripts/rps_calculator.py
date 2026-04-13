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
from typing import Optional


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

        _debug_print(debug_enabled, f"requested date={date or 'latest'} resolved date={reference_date} ma_period={ma_period}")

        if ma_period == 10 and not force_recompute:
            cached = conn.execute(
                "SELECT code, rps20, rps60, rps120, rps250, ma10 "
                "FROM rps_cache WHERE date=?",
                (reference_date,),
            ).fetchall()
            if cached:
                _debug_print(debug_enabled, f"cache hit for {reference_date}: {len(cached)} stocks")
                return {
                    row[0]: {
                        "rps20": row[1], "rps60": row[2],
                        "rps120": row[3], "rps250": row[4],
                        "ma10_today": row[5],
                    }
                    for row in cached
                }

        if ma_period == 10 and force_recompute:
            _debug_print(debug_enabled, "cache bypassed via force_recompute")

        trading_dates = [
            row[0] for row in conn.execute(
                "SELECT DISTINCT date FROM daily_prices "
                "WHERE date <= ? ORDER BY date DESC LIMIT 300",
                (reference_date,),
            )
        ]
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

        results = {code: {"ma10_today": round(ma, 4)} for code, ma in ma_today.items()}

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

        rows = conn.execute(
            "SELECT close FROM daily_prices "
            "WHERE code=? AND date <= ? ORDER BY date DESC LIMIT ?",
            (code, reference_date, period),
        ).fetchall()
        if len(rows) < period:
            return None

        closes = [float(row[0]) for row in rows]
        return sum(closes) / period
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

        trading_dates = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT date FROM daily_prices "
                "WHERE date <= ? ORDER BY date DESC LIMIT 260",
                (reference_date,),
            )
        ]
        if len(trading_dates) < 250:
            return {}

        results: dict[str, dict] = {}
        for period in [20, 120, 250]:
            period_dates = trading_dates[:period]
            if len(period_dates) < period:
                continue
            placeholders = ",".join(["?"] * len(period_dates))
            rows = conn.execute(
                f"SELECT code, AVG(close) FROM daily_prices "
                f"WHERE date IN ({placeholders}) GROUP BY code HAVING COUNT(*) = ?",
                period_dates + [period],
            ).fetchall()
            for row in rows:
                code = row[0]
                if code not in results:
                    results[code] = {}
                results[code][f"ma{period}"] = row[1]

        final: dict[str, dict] = {}
        for code, mas in results.items():
            ma20 = mas.get("ma20")
            ma120 = mas.get("ma120")
            ma250 = mas.get("ma250")
            if ma20 is not None and ma120 is not None and ma250 is not None:
                final[code] = {
                    "ma20": ma20, "ma120": ma120, "ma250": ma250,
                    "aligned": ma20 > ma120 > ma250,
                }
        return final
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_ma(conn: sqlite3.Connection, dates: list, required_count: int) -> dict:
    """Compute average close for all stocks over exactly `required_count` dates."""
    if not dates:
        return {}
    placeholders = ",".join(["?"] * len(dates))
    rows = conn.execute(
        f"SELECT code, AVG(close) FROM daily_prices "
        f"WHERE date IN ({placeholders}) GROUP BY code HAVING COUNT(*) = ?",
        dates + [required_count],
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _resolve_reference_date(conn: sqlite3.Connection, date: str | None) -> Optional[str]:
    """Resolve to the latest sufficiently covered trading date on or before the requested date."""
    coverage_threshold = _reference_date_coverage_threshold()
    total_codes_row = conn.execute("SELECT COUNT(DISTINCT code) FROM daily_prices").fetchone()
    total_codes = int(total_codes_row[0] or 0) if total_codes_row else 0
    min_codes = int(total_codes * coverage_threshold)

    params: list = []
    where_clause = ""
    if date is not None:
        where_clause = "WHERE date <= ?"
        params.append(date)

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

    if date is None:
        row = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()
    else:
        row = conn.execute(
            "SELECT MAX(date) FROM daily_prices WHERE date <= ?",
            (date,),
        ).fetchone()
    return row[0] if row and row[0] else None


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
