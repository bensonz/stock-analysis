#!/usr/bin/env python3
"""
pricedb_health.py — is the price database sound enough to trade on?

Extracted from pricedb.py on 2026-08-30. `db_health` is the loudness layer: its
verdict rides into input/db_health.json, the phase-1 contract, the LLM prompt
and the report banner, and since 2026-08-27 the doctor audits it too.

Isolating it matters because of how it failed. For days the banner said
"adj factors lag prices (2026-08-26 < 2026-08-27) — run 'pricedb.py factors
heal'" while every audit read ✅ 无发现: db_health was measuring correctly and
nothing downstream was listening. A module that only reports is worth being able
to exercise against synthetic database states, which is what this split buys —
build a conn, seed a lag, assert the warning.

Two known weak spots, both visible in the audit trail rather than fixed here:

- `spot_check` has shipped `sampled: 20, checked: 0, fetch_failures: 20` under
  `ok: true` on six days. Zero mismatches out of zero comparisons is not a clean
  bill of health, and `doctor.check_db_health_spot_check` now says so.
- The functions it needs from pricedb (`_fetch_klines_sina`,
  `last_settled_trading_day`, `_get_trade_calendar_cached`) are imported inside
  the function bodies, so the lookup resolves at call time against pricedb's
  globals — same reason as pricedb_factors: no circular import, and existing
  monkeypatch targets keep working.
"""

import sqlite3
from datetime import datetime, timedelta

import price_adjust
from pricedb_bars import _safe_float, _sina_symbol, _yyyymmdd_to_iso
from pricedb_storage import _partial_price_dates

def db_health(conn: sqlite3.Connection, spot_check: bool = False) -> dict:
    """Data-quality health block for the daily pipeline.

    The 2026-07-30 outage lesson: every degradation path already *worked*
    (coverage floor fell back to stale data) but stayed silent for days.
    This block is the loudness layer — it rides into input/db_health.json,
    the LLM prompt, the report banner, and the phase-1 contract.

    ok=False on: screening data >1 session stale, latest day partial, or
    spot-audit price mismatches. Anything notable lands in `warnings`.
    """
    # Deferred: resolves against pricedb's globals at call time.
    from pricedb import _get_trade_calendar_cached, last_settled_trading_day
    out = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "ok": True,
        "warnings": [],
    }
    latest = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()[0]
    out["latest_price_date"] = latest
    if not latest:
        out["ok"] = False
        out["warnings"].append("price DB is empty")
        return out

    counts = conn.execute(
        "SELECT date, COUNT(*) FROM daily_prices GROUP BY date "
        "ORDER BY date DESC LIMIT 30").fetchall()
    ordered = sorted(c for _, c in counts)
    median = ordered[len(ordered) // 2] if ordered else 0
    latest_count = counts[0][1] if counts else 0
    out["latest_row_count"] = latest_count
    out["median_row_count_30d"] = median
    out["latest_partial"] = bool(median and latest_count < 0.5 * median)
    if out["latest_partial"]:
        out["ok"] = False
        out["warnings"].append(
            f"latest day {latest} is PARTIAL ({latest_count} rows vs "
            f"~{median} normal) — run 'pricedb.py repair'")

    # Staleness vs the trading calendar (falls back to weekdays offline).
    expected = last_settled_trading_day().strftime("%Y%m%d")
    out["expected_latest"] = _yyyymmdd_to_iso(expected)
    latest_compact = latest.replace("-", "")
    try:
        cal = _get_trade_calendar_cached()
    except Exception:
        cal = []
    if cal:
        lag = sum(1 for c in cal if latest_compact < c <= expected)
    else:
        lag = len(_weekday_list(latest_compact, expected)) - (
            1 if latest_compact in _weekday_list(latest_compact, expected) else 0)
    out["lag_sessions"] = lag
    if lag >= 1:
        if lag > 1:
            out["ok"] = False
        out["warnings"].append(
            f"screening data is {lag} session(s) stale "
            f"(latest {latest}, expected {out['expected_latest']})")

    cov = price_adjust.factor_coverage(conn)
    out["factor_max_date"] = cov["max_factor_date"]
    if cov["max_factor_date"] and cov["max_factor_date"] < latest:
        out["warnings"].append(
            f"adj factors lag prices ({cov['max_factor_date']} < {latest}) "
            f"— run 'pricedb.py factors heal'")

    recent_partial = [d for d in _partial_price_dates(conn)
                      if d >= (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")]
    out["partial_days_30d"] = recent_partial

    if spot_check:
        out["spot_check"] = _spot_audit(conn, latest)
        if out["spot_check"]["mismatches"]:
            out["ok"] = False
            out["warnings"].append(
                f"spot audit: {len(out['spot_check']['mismatches'])} close-price "
                f"mismatches vs sina on {latest} "
                f"({','.join(m['code'] for m in out['spot_check']['mismatches'][:5])})")
    return out

def _spot_audit(conn: sqlite3.Connection, date_iso: str, sample: int = 20) -> dict:
    """Cross-source correctness check: random codes' stored closes on
    `date_iso` vs sina. Presence checks catch missing data; this catches
    wrong-but-present data (the silent killer). Fetch failures are reported
    but never counted as mismatches."""
    # Deferred: resolves against pricedb's globals at call time.
    from pricedb import _fetch_klines_sina
    import random
    codes = [r[0] for r in conn.execute(
        "SELECT d.code FROM daily_prices d JOIN stocks s ON s.code = d.code "
        "WHERE d.date = ?", (date_iso,))]
    codes = [c for c in codes if _sina_symbol(c, "")]
    picked = random.sample(codes, min(sample, len(codes)))
    checked, mismatches, failures = 0, [], 0
    for code in picked:
        stored = conn.execute(
            "SELECT close FROM daily_prices WHERE code = ? AND date = ?",
            (code, date_iso)).fetchone()[0]
        try:
            rows = _fetch_klines_sina({"code": code, "exchange": ""}, 5)
        except Exception:
            failures += 1
            continue
        ref = next((r[5] for r in rows if r[1] == date_iso), None)
        if ref is None:
            failures += 1
            continue
        checked += 1
        if abs(ref - stored) > 0.011:  # prices are 2dp; anything more is real
            mismatches.append({"code": code, "stored": stored, "sina": ref})
    return {"date": date_iso, "sampled": len(picked), "checked": checked,
            "fetch_failures": failures, "mismatches": mismatches}
