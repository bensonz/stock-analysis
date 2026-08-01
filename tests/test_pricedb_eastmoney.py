"""Tests for pricedb direct Eastmoney historical daily provider."""
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import pricedb  # noqa: E402


def _create_test_db(path: Path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE daily_prices (
            code TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            amount REAL,
            PRIMARY KEY (code, date)
        );
        """
    )
    return conn


def test_eastmoney_secid_maps_sh_sz_and_skips_bj():
    assert pricedb._eastmoney_secid({"code": "600519", "exchange": "SH"}) == "1.600519"
    assert pricedb._eastmoney_secid({"code": "000001", "exchange": "SZ"}) == "0.000001"
    assert pricedb._eastmoney_secid({"code": "688200", "exchange": "SH"}) == "1.688200"
    assert pricedb._eastmoney_secid({"code": "430047", "exchange": "BJ"}) is None


def test_eastmoney_retired_from_provider_chain(monkeypatch):
    # Doctrine flip 2026-08-01 (was: eastmoney before akshare). After the
    # IP-throttle outage the chain is akshare → sina ONLY; eastmoney paths
    # survive as internal helpers, never as price providers.
    monkeypatch.setattr(pricedb, "get_tushare_token", lambda: None)
    monkeypatch.setitem(sys.modules, "akshare", object())
    monkeypatch.setitem(sys.modules, "baostock", None)

    providers = [name for name, _provider in pricedb.iter_providers()]

    assert pricedb.PROVIDER_EASTMONEY not in providers
    assert pricedb.PROVIDER_EASTMONEY_CLIST not in providers
    assert pricedb.PROVIDER_BAOSTOCK not in providers
    assert pricedb.PROVIDER_TUSHARE not in providers


def test_eastmoney_kline_url_matches_endpoint_shape():
    url = pricedb._eastmoney_kline_url("1.600519", "20260421", "20260430")

    assert url == (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        "?secid=1.600519&fields1=f1&fields2=f51,f52,f53,f54,f55,f56,f57"
        "&klt=101&fqt=0&beg=20260421&end=20260430"
    )


def test_eastmoney_kline_to_tuple_maps_columns():
    row = pricedb._eastmoney_kline_to_tuple(
        {"code": "600519"},
        "2026-04-21,1411.00,1412.01,1419.90,1410.00,21754,3074595192.00",
    )

    assert row == (
        "600519",
        "2026-04-21",
        1411.0,
        1419.9,
        1410.0,
        1412.01,
        21754,
        3074595192.0,
    )


def test_eastmoney_payload_to_rows_ignores_invalid_klines():
    rows = pricedb._eastmoney_payload_to_rows(
        {"code": "000001"},
        {
            "data": {
                "klines": [
                    "2026-04-30,10.1,10.4,10.5,10.0,123456,6543210.5",
                    "bad",
                    "2026-04-30,,10.4,10.5,10.0,123456,6543210.5",
                ]
            }
        },
    )

    assert rows == [("000001", "2026-04-30", 10.1, 10.5, 10.0, 10.4, 123456, 6543210.5)]


def test_fetch_eastmoney_json_falls_back_to_curl(monkeypatch):
    def fail_urllib(url):
        raise RuntimeError("proxy failure")

    monkeypatch.setattr(pricedb, "_fetch_eastmoney_json_urllib", fail_urllib)
    monkeypatch.setattr(pricedb, "_fetch_eastmoney_json_curl", lambda url: '{"data":{"klines":[]}}')

    assert pricedb._fetch_eastmoney_json("https://example.invalid") == {"data": {"klines": []}}


def test_bulk_fetch_eastmoney_retries_skips_bj_and_inserts_from_main_thread(tmp_path, monkeypatch):
    db_path = tmp_path / "prices.db"
    conn = _create_test_db(db_path)
    stocks = [
        {"code": "600519", "name": "贵州茅台", "exchange": "SH"},
        {"code": "000001", "name": "平安银行", "exchange": "SZ"},
        {"code": "430047", "name": "BJ Test", "exchange": "BJ"},
    ]
    calls = {}

    def fake_fetch(stock, beg, end):
        assert beg == "20260421"
        assert end == "20260430"
        calls[stock["code"]] = calls.get(stock["code"], 0) + 1
        if stock["code"] == "600519" and calls[stock["code"]] == 1:
            raise RuntimeError("temporary upstream failure")
        if stock["exchange"] == "BJ":
            return []
        return [
            (
                stock["code"],
                "2026-04-30",
                10.1,
                10.5,
                10.0,
                10.4,
                123456,
                6543210.5,
            )
        ]

    monkeypatch.setenv("PRICEDB_EASTMONEY_WORKERS", "2")
    monkeypatch.setattr(pricedb, "EASTMONEY_RETRY_DELAY", 0)
    monkeypatch.setattr(pricedb, "_UPDATE_DEADLINE", None)
    monkeypatch.setattr(pricedb, "_fetch_klines_eastmoney", fake_fetch)

    pricedb._bulk_fetch_eastmoney(conn, stocks, "20260421", "20260430", None)

    rows = conn.execute(
        "SELECT code, date, open, high, low, close, volume, amount "
        "FROM daily_prices ORDER BY code"
    ).fetchall()
    conn.close()

    assert rows == [
        ("000001", "2026-04-30", 10.1, 10.5, 10.0, 10.4, 123456, 6543210.5),
        ("600519", "2026-04-30", 10.1, 10.5, 10.0, 10.4, 123456, 6543210.5),
    ]
    assert calls["600519"] == 2
    assert calls["430047"] == 1
