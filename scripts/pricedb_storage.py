#!/usr/bin/env python3
"""
pricedb_storage.py — schema and row persistence. Takes a connection, never opens one.

Extracted from pricedb.py on 2026-08-30. Everything here accepts an explicit
`conn`, so tests drive it against `sqlite3.connect(":memory:")` with no network,
no fixtures and no monkeypatching.

`get_db()` and the DB_PATH/DB_DIR configuration deliberately stayed behind in
pricedb.py. Two tests monkeypatch `pricedb.DB_PATH`; had the factory moved here
it would read `pricedb_storage.DB_PATH` and those patches would silently stop
working — a broken test that still passes is worse than no test. The rule that
falls out is a good one: **storage takes a connection, it does not create one.**

`write_bars` consolidates what were TEN copies of the same INSERT across the
provider functions, in two variants:

  REPLACE — the primary provider's bars win (used on the normal fetch path)
  IGNORE  — whatever landed first stays canonical (repair/backfill paths, where
            sina rows carry NULL amount and must not clobber a richer row)

Ten hand-written copies of `(code,date,open,high,low,close,volume,amount)` is
ten chances to transpose two columns and write a volume into a price. One
definition, tested once.
"""

import os
import sqlite3
from datetime import datetime

import price_adjust

PRICEDB_COVERAGE_THRESHOLD = float(os.getenv("RPS_REFERENCE_DATE_MIN_COVERAGE", "0.9"))

def ensure_schema(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS stocks (
            code        TEXT PRIMARY KEY,
            name        TEXT,
            exchange    TEXT,
            listed_date TEXT,
            last_updated TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_prices (
            code    TEXT,
            date    TEXT,
            open    REAL,
            high    REAL,
            low     REAL,
            close   REAL,
            volume  INTEGER,
            amount  REAL,
            PRIMARY KEY (code, date)
        );

        CREATE INDEX IF NOT EXISTS idx_dp_date
            ON daily_prices(date);
        CREATE INDEX IF NOT EXISTS idx_dp_code_date
            ON daily_prices(code, date);

        CREATE TABLE IF NOT EXISTS rps_cache (
            date    TEXT,
            code    TEXT,
            rps20   REAL,
            rps60   REAL,
            rps120  REAL,
            rps250  REAL,
            ma10    REAL,
            PRIMARY KEY (date, code)
        );
        """
    )
    # adj_factors (read-time price adjustment) is owned by price_adjust.py —
    # single definition, shared by pricedb writers and indicator readers.
    price_adjust.ensure_adj_schema(conn)
    conn.commit()

def clear_all_data(conn: sqlite3.Connection):
    """Clear all data tables for a fresh init attempt."""
    conn.execute("DELETE FROM rps_cache")
    conn.execute("DELETE FROM daily_prices")
    conn.execute("DELETE FROM stocks")
    conn.commit()

def invalidate_rps_cache(conn: sqlite3.Connection, from_date: str | None = None):
    """Invalidate cached RPS rows from a given ISO date onward."""
    if from_date:
        conn.execute("DELETE FROM rps_cache WHERE date >= ?", (from_date,))
    else:
        conn.execute("DELETE FROM rps_cache")
    conn.commit()

def upsert_stocks(conn: sqlite3.Connection, stocks: list[dict]):
    """Insert or refresh stock metadata."""
    if not stocks:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.executemany(
        "INSERT OR REPLACE INTO stocks (code, name, exchange, listed_date, last_updated) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (
                stock["code"],
                stock.get("name"),
                stock.get("exchange"),
                stock.get("listed_date"),
                now,
            )
            for stock in stocks
        ],
    )
    conn.commit()

def _last_fully_covered_date(conn: sqlite3.Connection) -> str | None:
    """Latest date whose row count reaches PRICEDB_COVERAGE_THRESHOLD of the
    known universe. Used as the incremental cursor so partially-fetched recent
    days (truncated by the budget or a flaky provider) get re-fetched instead of
    being skipped forever once a later day advances MAX(date)."""
    total = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
    if not total:
        return None
    min_codes = int(total * PRICEDB_COVERAGE_THRESHOLD)
    row = conn.execute(
        """
        SELECT date
        FROM daily_prices
        GROUP BY date
        HAVING COUNT(DISTINCT code) >= ?
        ORDER BY date DESC
        LIMIT 1
        """,
        (min_codes,),
    ).fetchone()
    return row[0] if row and row[0] else None

def _partial_price_dates(conn: sqlite3.Connection) -> list[str]:
    """Dates whose row count is under half the median daily count — the
    signature of a provider outage that landed only a fragment of the
    universe (e.g. a clist sweep killed mid-flight)."""
    counts = conn.execute(
        "SELECT date, COUNT(*) FROM daily_prices GROUP BY date ORDER BY date"
    ).fetchall()
    if not counts:
        return []
    ordered = sorted(c for _, c in counts)
    median = ordered[len(ordered) // 2]
    return [d for d, c in counts if c < 0.5 * median]


BAR_COLUMNS = "(code,date,open,high,low,close,volume,amount)"


def write_bars(conn: sqlite3.Connection, rows, replace: bool = True) -> int:
    """Persist bar tuples; returns rows actually written.

    `replace=False` (INSERT OR IGNORE) is for repair and backfill paths, where a
    thinner row must not overwrite a richer one already in place — sina bars
    carry NULL amount, so clobbering an iFinD row with one would lose data that
    no later pass restores.
    """
    if not rows:
        return 0
    verb = "INSERT OR REPLACE" if replace else "INSERT OR IGNORE"
    cur = conn.executemany(
        f"{verb} INTO daily_prices {BAR_COLUMNS} VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    return cur.rowcount
