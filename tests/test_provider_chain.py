"""Provider-chain doctrine tests (2026-08-01).

User decision after the eastmoney IP-throttle outage: the daily price chain
is AkShare primary → Sina fallback, nothing else. eastmoney clist/direct,
baostock and tushare are retired for price bars (kept only as internal
helpers). These tests pin the doctrine so the chain can't quietly regrow.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb

D1, D2 = "2026-07-30", "2026-07-31"


def test_chain_is_akshare_then_sina_only():
    names = [name for name, _ in pricedb.iter_providers()]
    assert names == [pricedb.PROVIDER_AKSHARE, pricedb.PROVIDER_SINA]


def _conn_with_stock():
    conn = sqlite3.connect(":memory:")
    pricedb.ensure_schema(conn)
    conn.execute("INSERT INTO stocks(code, name, exchange) "
                 "VALUES ('000001', '平安银行', 'SZ')")
    return conn


def test_bulk_fetch_sina_window_filter_and_ignore(monkeypatch):
    conn = _conn_with_stock()
    # pre-existing primary row must NOT be overwritten (amount stays)
    conn.execute("INSERT INTO daily_prices VALUES "
                 "('000001', ?, 11.28, 11.62, 11.18, 11.61, 2777707, 999.0)", (D1,))
    conn.commit()
    monkeypatch.setattr(pricedb, "SINA_REPAIR_SLEEP_SEC", 0.0)
    monkeypatch.setattr(pricedb, "_fetch_klines_sina", lambda stock, datalen: [
        ("000001", "2026-07-29", 11.19, 11.36, 11.18, 11.28, 1511054, None),  # pre-window
        ("000001", D1, 11.28, 11.62, 11.18, 11.61, 2777707, None),            # exists
        ("000001", D2, 11.50, 11.63, 11.28, 11.63, 2024978, None),            # new
    ])

    pricedb._bulk_fetch_sina(conn, [{"code": "000001", "exchange": "SZ"}],
                             "20260730", "20260731", None)

    rows = conn.execute(
        "SELECT date, close, amount FROM daily_prices ORDER BY date").fetchall()
    assert rows == [(D1, 11.61, 999.0), (D2, 11.63, None)]


def test_bulk_fetch_sina_raises_on_empty_weekday_window(monkeypatch):
    conn = _conn_with_stock()
    monkeypatch.setattr(pricedb, "SINA_REPAIR_SLEEP_SEC", 0.0)
    monkeypatch.setattr(pricedb, "_fetch_klines_sina", lambda stock, datalen: [])
    with pytest.raises(RuntimeError, match="no rows"):
        pricedb._bulk_fetch_sina(conn, [{"code": "000001", "exchange": "SZ"}],
                                 "20260730", "20260731", None)


def test_fetch_stock_list_akshare_derives_exchange(monkeypatch):
    import pandas as pd
    fake = pd.DataFrame({"code": ["600000", "000001", "300750", "920001"],
                         "name": ["浦发银行", "平安银行", "宁德时代", "某北交所"]})

    class _AK:
        @staticmethod
        def stock_info_a_code_name():
            return fake

    out = pricedb.fetch_stock_list_akshare(_AK)
    assert {s["code"]: s["exchange"] for s in out} == {
        "600000": "SH", "000001": "SZ", "300750": "SZ", "920001": "BJ"}
