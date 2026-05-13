#!/usr/bin/env python3
"""End-to-end smoke test for pricedb update.

Runs the actual Eastmoney clist fetch against the live market, writes to a
temporary DB, and asserts the update completes in <120s with >5000 stocks and
today's date present. Skips if today is not a trading day.

This is the canary. If this fails in production, the daily pipeline should not
run analysis (the staleness gate will refuse anyway).

Usage:
    python3 scripts/test_pricedb_smoke.py
"""
import sqlite3
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pricedb


SMOKE_MAX_DURATION_SEC = 120
SMOKE_MIN_STOCKS = 5000


def _seed_universe(conn: sqlite3.Connection) -> int:
    """Seed a minimal stocks table covering all A-share boards.

    The clist fetcher filters by code membership in ``stocks``. To get a true
    smoke signal we need to pre-populate broadly; use a synthetic 6-digit code
    universe covering known A-share prefixes.
    """
    pricedb.ensure_schema(conn)
    rows: list[tuple] = []
    # SH main + STAR
    for base in range(600000, 605000):
        rows.append((str(base), str(base), "SH", None, ""))
    for base in range(688000, 689000):
        rows.append((str(base), str(base), "SH", None, ""))
    # SZ main + ChiNext
    for base in range(0, 4000):
        rows.append((f"{base:06d}", f"{base:06d}", "SZ", None, ""))
    for base in range(300000, 302000):
        rows.append((str(base), str(base), "SZ", None, ""))
    # BJ
    for base in range(430000, 925000, 1):
        if str(base).startswith(("4", "8", "92")):
            rows.append((str(base), str(base), "BJ", None, ""))
            if base > 925000:
                break
    conn.executemany(
        "INSERT OR REPLACE INTO stocks (code, name, exchange, listed_date, last_updated) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def main() -> int:
    today = datetime.now().date()
    if today.weekday() >= 5:
        print(f"⊘ Today ({today.isoformat()}) is a weekend — skipping smoke test.")
        return 0

    print(f"Smoke test: pricedb clist fetch for {today.isoformat()}")
    print(f"  budget: {SMOKE_MAX_DURATION_SEC}s, min stocks: {SMOKE_MIN_STOCKS}")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "smoke.db"
        # Point pricedb to the temp DB
        pricedb.DB_PATH = db_path
        pricedb.DB_DIR = db_path.parent

        conn = sqlite3.connect(str(db_path))
        seeded = _seed_universe(conn)
        print(f"  seeded {seeded:,} stock codes")

        stocks = [
            {"code": row[0], "name": row[1], "exchange": row[2]}
            for row in conn.execute("SELECT code, name, exchange FROM stocks")
        ]

        today_yyyymmdd = today.strftime("%Y%m%d")
        t0 = time.monotonic()
        try:
            pricedb._UPDATE_DEADLINE = t0 + SMOKE_MAX_DURATION_SEC
            pricedb._bulk_fetch_eastmoney_clist(
                conn, stocks, today_yyyymmdd, today_yyyymmdd, None,
            )
        except Exception as e:
            elapsed = time.monotonic() - t0
            print(f"✗ clist fetch failed after {elapsed:.1f}s: {e}")
            return 1
        finally:
            pricedb._UPDATE_DEADLINE = None
        elapsed = time.monotonic() - t0

        count = conn.execute(
            "SELECT COUNT(*) FROM daily_prices WHERE date = ?",
            (today.isoformat(),),
        ).fetchone()[0]
        conn.close()

        print(f"  fetched {count:,} bars in {elapsed:.1f}s")

        ok = True
        if elapsed > SMOKE_MAX_DURATION_SEC:
            print(f"✗ exceeded duration budget ({elapsed:.1f}s > {SMOKE_MAX_DURATION_SEC}s)")
            ok = False
        if count < SMOKE_MIN_STOCKS:
            print(f"✗ too few bars ({count} < {SMOKE_MIN_STOCKS})")
            ok = False

        if not ok:
            return 1
        print(f"✓ smoke test passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
