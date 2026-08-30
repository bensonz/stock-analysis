"""`update` must reconcile factors even when it fetches nothing.

The 2026-08-30 root cause. Two individually-correct commands combined into a
gap:

  1. `pricedb.py snapshot` writes the close-slot price rows. It does not touch
     adj_factors — factor sync has never been part of that command.
  2. preflight then runs `pricedb.py update`, which DOES own factor sync
     (`_sync_or_heal_factors`).
  3. But update computes its fetch range first, sees `latest` is already today
     *because the snapshot just wrote it*, hits `beg > end`, prints "Already up
     to date" and returns — several lines above the factor sync.

So the snapshot's success is exactly what makes update skip the reconciliation.
Prices advance, factors do not, and nothing in that path owns closing the gap.
It fired on every afternoon run and never at noon, because at noon the snapshot
refuses while the session is open and prices do not move ahead.

It degraded silently through two layers: `get_factors_on_date` uses an exact
date match and returned {}, then `f_ref.get(code, 1.0)` read the absence as "no
adjustment needed". `rps_cache.ma10` then shipped hfq-scale values as prices —
603259 read 168.28 against a true 162.23, and a deep report quoted a figure
9x off for 002293 on 2026-08-25.

Factor catch-up is RECONCILIATION, not a consequence of fetching. It belongs on
every path through update, which is what these tests pin.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb


def _seed(db_path, price_dates, factor_dates, universe=5):
    conn = sqlite3.connect(str(db_path))
    pricedb.ensure_schema(conn)
    import price_adjust
    price_adjust.ensure_adj_schema(conn)
    codes = [f"{600000 + i:06d}" for i in range(universe)]
    conn.executemany("INSERT INTO stocks(code, name, exchange) VALUES (?, ?, ?)",
                     [(c, c, "SH") for c in codes])
    for d in price_dates:
        conn.executemany(
            "INSERT INTO daily_prices(code, date, open, high, low, close, volume, amount) "
            "VALUES (?, ?, 10, 10, 10, 10, 100, 1000)", [(c, d) for c in codes])
    for d in factor_dates:
        conn.executemany("INSERT INTO adj_factors(code, date, factor) VALUES (?, ?, 1.0)",
                         [(c, d) for c in codes])
    conn.commit()
    return conn, codes


def test_factors_lag_is_detected_when_prices_are_ahead(tmp_path):
    """The state the snapshot leaves behind: prices at T, factors at T-1."""
    conn, _ = _seed(tmp_path / "a.db", ["2026-08-27", "2026-08-28"], ["2026-08-27"])
    import price_adjust
    cov = price_adjust.factor_coverage(conn)
    assert cov["max_price_date"] == "2026-08-28"
    assert cov["max_factor_date"] == "2026-08-27"
    conn.close()


def test_reconcile_closes_the_gap_left_by_a_snapshot(tmp_path):
    """_sync_or_heal_factors must advance factors to meet prices. This is the
    call the early return was skipping."""
    conn, _ = _seed(tmp_path / "b.db", ["2026-08-27", "2026-08-28"], ["2026-08-27"])
    pricedb._sync_or_heal_factors(conn)
    import price_adjust
    cov = price_adjust.factor_coverage(conn)
    assert cov["max_factor_date"] == "2026-08-28", (
        "factors still lag after reconciliation")
    conn.close()


def test_reconcile_is_a_safe_no_op_when_already_level(tmp_path):
    """It has to be cheap to call unconditionally — that is what lets it move
    above the early return instead of being guarded by 'did we fetch'."""
    conn, _ = _seed(tmp_path / "c.db", ["2026-08-28"], ["2026-08-28"])
    assert pricedb._sync_or_heal_factors(conn) is None
    import price_adjust
    assert price_adjust.factor_coverage(conn)["max_factor_date"] == "2026-08-28"
    conn.close()


def test_update_reconciles_factors_on_the_nothing_to_fetch_path(tmp_path, monkeypatch):
    """The regression itself, at the command boundary.

    With prices already at today, update fetches nothing — and must STILL leave
    factors level. Before the fix it returned at "Already up to date" and the
    lag survived into the next run's RPS.
    """
    db = tmp_path / "d.db"
    conn, _ = _seed(db, ["2026-08-27", "2026-08-28"], ["2026-08-27"])
    conn.close()

    import datetime as _dt

    monkeypatch.setattr(pricedb, "DB_PATH", db)
    monkeypatch.setattr(pricedb, "iter_providers",
                        lambda *a, **k: iter([("stub", object())]))
    monkeypatch.setattr(pricedb, "close_provider", lambda *a, **k: None)
    monkeypatch.setattr(pricedb, "_now", lambda: _dt.datetime(2026, 8, 28, 16, 0))
    monkeypatch.setattr(pricedb, "most_recent_trading_day",
                        lambda d: _dt.date(2026, 8, 28))
    monkeypatch.setattr(pricedb, "is_session_open", lambda *a, **k: False)

    pricedb.cmd_update()

    conn = sqlite3.connect(str(db))
    import price_adjust
    cov = price_adjust.factor_coverage(conn)
    conn.close()
    assert cov["max_factor_date"] == "2026-08-28", (
        "update returned early and left factors behind prices — the exact "
        "2026-08-30 defect")
