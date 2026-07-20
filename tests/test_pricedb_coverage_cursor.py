"""Unit tests for the pricedb incremental-cursor / session-open guards (RC1/RC3).

These are pure-logic tests — no network, no live market.
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb


def test_is_session_open_before_close():
    assert pricedb.is_session_open(datetime(2026, 7, 17, 11, 35)) is True
    assert pricedb.is_session_open(datetime(2026, 7, 17, 14, 59)) is True


def test_is_session_open_after_close():
    assert pricedb.is_session_open(datetime(2026, 7, 17, 15, 0)) is False
    assert pricedb.is_session_open(datetime(2026, 7, 17, 15, 35)) is False


def _seed(conn, coverage_by_date, universe):
    pricedb.ensure_schema(conn)
    codes = [f"{600000 + i:06d}" for i in range(universe)]
    conn.executemany(
        "INSERT INTO stocks(code, name, exchange) VALUES (?, ?, ?)",
        [(c, c, "SH") for c in codes],
    )
    for date, n in coverage_by_date.items():
        conn.executemany(
            "INSERT INTO daily_prices(code, date, open, high, low, close, volume, amount) "
            "VALUES (?, ?, 1, 1, 1, 1, 0, 0)",
            [(codes[i], date, ) for i in range(n)],
        )
    conn.commit()


def test_last_fully_covered_date_skips_partial_recent_days(tmp_path):
    # 07-17 and 07-16 are partial (below 90% of 100); 07-13 is full.
    db = sqlite3.connect(":memory:")
    _seed(
        db,
        {"2026-07-13": 100, "2026-07-16": 80, "2026-07-17": 95},
        universe=100,
    )
    # 90% of 100 = 90. 07-17 has 95 (>=90) -> it IS covered.
    assert pricedb._last_fully_covered_date(db) == "2026-07-17"


def test_last_fully_covered_date_returns_last_full_when_head_is_partial(tmp_path):
    db = sqlite3.connect(":memory:")
    _seed(
        db,
        {"2026-07-13": 100, "2026-07-15": 66, "2026-07-16": 80, "2026-07-17": 85},
        universe=100,
    )
    # 90% of 100 = 90. Only 07-13 clears it -> cursor should re-fetch from 07-13.
    assert pricedb._last_fully_covered_date(db) == "2026-07-13"


def test_last_fully_covered_date_none_when_empty(tmp_path):
    db = sqlite3.connect(":memory:")
    pricedb.ensure_schema(db)
    assert pricedb._last_fully_covered_date(db) is None


def test_last_settled_trading_day_open_session_is_previous_day(monkeypatch):
    # Empty calendar -> most_recent_trading_day uses weekend-walk (deterministic).
    monkeypatch.setattr(pricedb, "_get_trade_calendar_cached", lambda: [])
    from datetime import date

    # Monday 11:35, session open -> last settled is Friday (skips the weekend).
    got = pricedb.last_settled_trading_day(datetime(2026, 7, 20, 11, 35))
    assert got == date(2026, 7, 17)


def test_last_settled_trading_day_after_close_is_today(monkeypatch):
    monkeypatch.setattr(pricedb, "_get_trade_calendar_cached", lambda: [])
    from datetime import date

    # Monday 15:35, session closed -> today's bar has settled.
    got = pricedb.last_settled_trading_day(datetime(2026, 7, 20, 15, 35))
    assert got == date(2026, 7, 20)
