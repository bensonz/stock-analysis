#!/usr/bin/env python3
"""
price_adjust.py — read-time price adjustment for indicator math.

The price DB stores RAW (unadjusted) OHLC forever; this module owns the
`adj_factors` table (per-stock per-day cumulative hfq factors) and the SQL
fragments consumers use to compute dividend/split-corrected indicators:

    adjusted_close = close * factor        (hfq scale, per-stock consistent)

Consumers then normalize aggregates by the stock's factor on the reference
date so reported MAs stay in *today's real price scale* (identical to raw
whenever no corporate action falls inside the window).

Display prices, live quotes, and actual trade prices stay raw by design —
those are real tradeable prices. Only return/MA/RPS/VCP math adjusts.

Kill switch: set PRICE_ADJ_DISABLE=1 to reproduce raw behavior instantly
(rollback path — no data changes needed).

See docs/pricedb_adjustment/ and the plan in git history for the full design.
"""
import os
import sqlite3

PRICE_ADJ_DISABLE_ENV = "PRICE_ADJ_DISABLE"


def adjustment_enabled() -> bool:
    """False when the kill switch env is set — all fragments degrade to raw."""
    return os.getenv(PRICE_ADJ_DISABLE_ENV, "").strip() not in ("1", "true", "yes")


def ensure_adj_schema(conn: sqlite3.Connection) -> None:
    """Create the adj_factors table if missing. Idempotent and cheap; every
    read entry point calls this so minimal test DBs work unmodified."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS adj_factors ("
        "  code TEXT NOT NULL,"
        "  date TEXT NOT NULL,"
        "  factor REAL NOT NULL,"
        "  PRIMARY KEY (code, date)"
        ")"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_af_date ON adj_factors(date)")


def adj_join_sql(price_alias: str = "d", factor_alias: str = "a") -> str:
    """LEFT JOIN fragment binding each price row to its factor (or nothing).

    The (code,date) PK guarantees at most one factor row per price row, so
    GROUP BY / HAVING COUNT(*) semantics of the caller are unchanged.
    """
    if not adjustment_enabled():
        return ""
    return (
        f" LEFT JOIN adj_factors {factor_alias} "
        f"ON {factor_alias}.code = {price_alias}.code "
        f"AND {factor_alias}.date = {price_alias}.date "
    )


def adjusted_close_sql(price_alias: str = "d", factor_alias: str = "a") -> str:
    """Expression for the hfq-adjusted close (raw when disabled).

    COALESCE(...,1.0) is safe ONLY because ingestion keeps the table dense
    (forward-filled): a stock either has a factor for every traded date or
    none at all (new listing / not yet backfilled -> constant 1.0 == raw).
    """
    if not adjustment_enabled():
        return f"{price_alias}.close"
    return f"{price_alias}.close * COALESCE({factor_alias}.factor, 1.0)"


def factor_sql(factor_alias: str = "a") -> str:
    """Expression for the row's factor itself (1.0 when disabled/missing)."""
    if not adjustment_enabled():
        return "1.0"
    return f"COALESCE({factor_alias}.factor, 1.0)"


def get_factors_on_date(conn: sqlite3.Connection, date: str) -> dict:
    """{code: factor} on `date` — the f_ref used to normalize hfq aggregates
    back into the reference date's real price scale. Missing codes -> caller
    treats as 1.0."""
    if not adjustment_enabled():
        return {}
    ensure_adj_schema(conn)
    return {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT code, factor FROM adj_factors WHERE date = ?", (date,)
        )
    }


def get_factor_series(conn: sqlite3.Connection, code: str, end_date: str = None) -> list:
    """[(date, factor)] ascending for one stock, up to end_date inclusive."""
    if not adjustment_enabled():
        return []
    ensure_adj_schema(conn)
    if end_date:
        rows = conn.execute(
            "SELECT date, factor FROM adj_factors WHERE code = ? AND date <= ? ORDER BY date",
            (code, end_date),
        )
    else:
        rows = conn.execute(
            "SELECT date, factor FROM adj_factors WHERE code = ? ORDER BY date", (code,)
        )
    return list(rows)


UNIVERSE_COVERAGE_FLOOR = 99.5


def factor_coverage(conn: sqlite3.Connection) -> dict:
    """Coverage stats + a single health verdict for `factors verify` / `status`.

    Two coverage numbers, and only one of them means anything:

    - `pair_coverage_pct` — % of ALL daily_prices rows with a matching factor
      row. Its denominator includes ~324 BJ-exchange codes that can never be
      factored (sina's hfq.js doesn't carry them), so it is permanently stuck
      around 96% on a perfectly healthy DB. Kept for display only.
    - `universe_coverage_pct` — % coverage over the codes that HAVE factors,
      i.e. the rows adjustment actually applies to. This is the real metric.

    Until 2026-08-16 `verify` judged on the universe metric while `status`
    judged `pair_coverage_pct < 99` and told you to run a backfill — so a clean
    DB printed VERIFY OK and a WARNING one second apart, and the warning was
    always wrong. Both callers now read `healthy`/`problems` from here so they
    cannot disagree again.
    """
    ensure_adj_schema(conn)
    total = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
    matched = conn.execute(
        "SELECT COUNT(*) FROM daily_prices d "
        "JOIN adj_factors a ON a.code = d.code AND a.date = d.date"
    ).fetchone()[0]
    missing = [r[0] for r in conn.execute(
        "SELECT DISTINCT code FROM daily_prices "
        "EXCEPT SELECT DISTINCT code FROM adj_factors")]
    # BJ-exchange codes (43x/83x/87x/92x) are deliberately unfactored — they
    # read as 1.0, which is the status quo, not breakage.
    non_bj_missing = [c for c in missing if not c.startswith(("4", "8", "9"))]
    # Fresh IPOs (<30 sessions) have had no corporate actions yet, so factor
    # 1.0 is exactly right. 2026-08-08: two week-old listings false-tripped
    # exit 1 in the weekly audit. Reported separately, exempt from the gate.
    fresh_ipos = []
    if non_bj_missing:
        placeholders = ",".join("?" * len(non_bj_missing))
        fresh_ipos = [r[0] for r in conn.execute(
            f"SELECT code FROM daily_prices WHERE code IN ({placeholders}) "
            "GROUP BY code HAVING COUNT(*) < 30", non_bj_missing)]
        non_bj_missing = [c for c in non_bj_missing if c not in fresh_ipos]
    coverable = conn.execute(
        "SELECT COUNT(*) FROM daily_prices d WHERE d.code IN "
        "(SELECT DISTINCT code FROM adj_factors)").fetchone()[0]
    universe_pct = (matched / coverable * 100.0) if coverable else 0.0
    max_price_date = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()[0]
    max_factor_date = conn.execute("SELECT MAX(date) FROM adj_factors").fetchone()[0]

    problems = []
    if universe_pct < UNIVERSE_COVERAGE_FLOOR:
        problems.append(
            f"factored-universe coverage {universe_pct:.2f}% below "
            f"{UNIVERSE_COVERAGE_FLOOR}% — run 'pricedb.py factors backfill'")
    if non_bj_missing:
        problems.append(
            f"{len(non_bj_missing)} non-BJ codes have no factors at all "
            f"({','.join(sorted(non_bj_missing)[:5])}) — run 'factors backfill'")
    if max_factor_date != max_price_date:
        problems.append(
            f"factor date {max_factor_date or 'none'} lags price date "
            f"{max_price_date or 'none'} — run 'pricedb.py factors heal'")

    return {
        "pair_coverage_pct": (matched / total * 100.0) if total else 0.0,
        "universe_coverage_pct": universe_pct,
        "total_price_rows": total,
        "matched_rows": matched,
        "coverable_rows": coverable,
        "codes_without_factors": len(missing),
        "non_bj_missing": non_bj_missing,
        "fresh_ipos": fresh_ipos,
        "max_price_date": max_price_date,
        "max_factor_date": max_factor_date,
        "problems": problems,
        "healthy": not problems,
    }
