"""`pricedb backfill-amount` — repairing turnover without touching prices.

Context: `amount` was NULL on 268k of 2.2M rows because _fetch_klines_sina
(sina's kline archive) doesn't publish turnover, and it did most of the filling
whenever akshare was throttled. Re-running `update` cannot fix that — every
writer is INSERT OR IGNORE and first-writer-wins is deliberate.

So this command exists to write ONE column. The tests below exist to keep it
that way: the moment it can touch OHLCV, it stops being a safe repair and
becomes a silent rewrite of the trading record.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb

D1, D2 = "2026-08-24", "2026-08-25"


class _FakeClient:
    """Returns one table per requested code from a {code: (dates, closes, amounts)} map."""

    def __init__(self, data):
        self.data = data
        self.data_vol = 0
        self.calls = 0

    def history_quotation(self, codes, indicators, beg, end, **kwargs):
        self.calls += 1
        tables = []
        for ths in codes:
            code = ths.split(".")[0]
            if code not in self.data:
                continue
            dates, closes, amounts = self.data[code]
            tables.append({"thscode": ths, "time": dates,
                           "table": {"close": closes, "amount": amounts}})
        return tables


def _conn(rows):
    conn = sqlite3.connect(":memory:")
    pricedb.ensure_schema(conn)
    conn.execute("INSERT INTO stocks(code,name,exchange) VALUES ('000001','平安银行','SZ')")
    conn.executemany(
        "INSERT INTO daily_prices(code,date,open,high,low,close,volume,amount) "
        "VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    return conn


def _install(monkeypatch, data):
    client = _FakeClient(data)
    monkeypatch.setattr(pricedb.ifind_client, "get_client", lambda: client)
    return client


def test_fills_null_amount(monkeypatch):
    conn = _conn([("000001", D1, 11.5, 11.7, 11.4, 11.61, 100, None)])
    _install(monkeypatch, {"000001": ([D1], [11.61], [1.5e9])})

    stats = pricedb.backfill_amount(conn, D1, D2)

    assert stats["filled"] == 1
    assert conn.execute("SELECT amount FROM daily_prices").fetchone()[0] == 1.5e9


def test_never_touches_ohlcv(monkeypatch):
    """The whole safety argument for this command."""
    conn = _conn([("000001", D1, 11.5, 11.7, 11.4, 11.61, 100, None)])
    # iFinD agrees on close but we hand it divergent everything-else; only
    # `amount` is in the UPDATE statement, so none of it can land.
    _install(monkeypatch, {"000001": ([D1], [11.61], [1.5e9])})

    pricedb.backfill_amount(conn, D1, D2)

    assert conn.execute(
        "SELECT open,high,low,close,volume FROM daily_prices").fetchone() == \
        (11.5, 11.7, 11.4, 11.61, 100)


def test_close_mismatch_is_conflicted_not_written(monkeypatch):
    """A close disagreement means we'd staple turnover onto a different bar."""
    conn = _conn([("000001", D1, 11.5, 11.7, 11.4, 11.61, 100, None)])
    _install(monkeypatch, {"000001": ([D1], [99.0], [1.5e9])})

    stats = pricedb.backfill_amount(conn, D1, D2)

    assert stats["conflicted"] == 1
    assert stats["filled"] == 0
    assert conn.execute("SELECT amount FROM daily_prices").fetchone()[0] is None


def test_existing_amount_is_not_overwritten(monkeypatch):
    conn = _conn([("000001", D1, 11.5, 11.7, 11.4, 11.61, 100, 777.0)])
    _install(monkeypatch, {"000001": ([D1], [11.61], [1.5e9])})

    pricedb.backfill_amount(conn, D1, D2)

    assert conn.execute("SELECT amount FROM daily_prices").fetchone()[0] == 777.0


def test_dry_run_writes_nothing(monkeypatch):
    conn = _conn([("000001", D1, 11.5, 11.7, 11.4, 11.61, 100, None)])
    _install(monkeypatch, {"000001": ([D1], [11.61], [1.5e9])})

    stats = pricedb.backfill_amount(conn, D1, D2, dry_run=True)

    assert stats["filled"] == 1, "dry run still reports what it would fill"
    assert conn.execute("SELECT amount FROM daily_prices").fetchone()[0] is None


def test_missing_ifind_amount_is_counted_not_guessed(monkeypatch):
    """Non-trading rows have no turnover; record the gap rather than inventing 0."""
    conn = _conn([("000001", D1, 11.5, 11.7, 11.4, 11.61, 100, None)])
    _install(monkeypatch, {"000001": ([D1], [11.61], [None])})

    stats = pricedb.backfill_amount(conn, D1, D2)

    assert stats["missing"] == 1 and stats["filled"] == 0
    assert conn.execute("SELECT amount FROM daily_prices").fetchone()[0] is None


def test_idempotent(monkeypatch):
    conn = _conn([("000001", D1, 11.5, 11.7, 11.4, 11.61, 100, None)])
    _install(monkeypatch, {"000001": ([D1], [11.61], [1.5e9])})

    pricedb.backfill_amount(conn, D1, D2)
    second = pricedb.backfill_amount(conn, D1, D2)

    assert second["candidates"] == 0 and second["filled"] == 0


def test_skips_dates_outside_window(monkeypatch):
    conn = _conn([("000001", "2026-01-05", 1, 1, 1, 1.0, 10, None),
                  ("000001", D1, 11.5, 11.7, 11.4, 11.61, 100, None)])
    client = _install(monkeypatch, {"000001": ([D1], [11.61], [1.5e9])})

    stats = pricedb.backfill_amount(conn, D1, D2)

    assert stats["candidates"] == 1, "the January row is out of window"
    assert conn.execute("SELECT amount FROM daily_prices WHERE date='2026-01-05'"
                        ).fetchone()[0] is None


def test_batch_failure_is_reported_not_swallowed(monkeypatch):
    conn = _conn([("000001", D1, 11.5, 11.7, 11.4, 11.61, 100, None)])

    class _Boom:
        data_vol = 0

        def history_quotation(self, *a, **k):
            raise RuntimeError("network down")

    monkeypatch.setattr(pricedb.ifind_client, "get_client", lambda: _Boom())

    stats = pricedb.backfill_amount(conn, D1, D2)

    assert stats["failed_batches"] == 1 and stats["filled"] == 0
