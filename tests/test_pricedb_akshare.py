"""Tests for pricedb AkShare historical daily provider."""
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
        CREATE TABLE stocks (
            code TEXT PRIMARY KEY,
            name TEXT,
            exchange TEXT,
            listed_date TEXT,
            last_updated TEXT
        );

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

        CREATE TABLE rps_cache (
            date TEXT,
            code TEXT,
            rps20 REAL,
            rps60 REAL,
            rps120 REAL,
            rps250 REAL,
            ma10 REAL,
            PRIMARY KEY (date, code)
        );
        """
    )
    return conn


class _FakeAkShareFrame:
    def __init__(self, rows):
        self._rows = rows
        self.empty = len(rows) == 0

    def iterrows(self):
        return iter(enumerate(self._rows))


class _FakeAkShare:
    def __init__(self):
        self.calls = {}

    def stock_zh_a_hist(self, symbol, period, start_date, end_date, adjust):
        self.calls[symbol] = self.calls.get(symbol, 0) + 1
        assert period == "daily"
        assert start_date == "20260421"
        assert end_date == "20260430"
        assert adjust == ""

        if symbol == "600519" and self.calls[symbol] == 1:
            raise RuntimeError("temporary upstream failure")

        return _FakeAkShareFrame([
            {
                "日期": "2026-04-30",
                "股票代码": symbol,
                "开盘": "10.1",
                "收盘": "10.4",
                "最高": "10.5",
                "最低": "10.0",
                "成交量": "123456",
                "成交额": "6543210.5",
            }
        ])


def test_akshare_hist_row_to_tuple_maps_columns():
    row = {
        "日期": "2026-04-30",
        "开盘": "7.1",
        "最高": "7.5",
        "最低": "7.0",
        "收盘": "7.3",
        "成交量": "1000",
        "成交额": "7300.5",
    }

    assert pricedb._akshare_hist_row_to_tuple({"code": "000001"}, row) == (
        "000001",
        "2026-04-30",
        7.1,
        7.5,
        7.0,
        7.3,
        1000,
        7300.5,
    )


def test_bulk_fetch_akshare_retries_and_inserts_from_main_thread(tmp_path, monkeypatch):
    db_path = tmp_path / "prices.db"
    conn = _create_test_db(db_path)
    stocks = [
        {"code": "600519", "name": "贵州茅台", "exchange": "SH"},
        {"code": "000001", "name": "平安银行", "exchange": "SZ"},
    ]
    conn.executemany(
        "INSERT INTO stocks (code, name, exchange, last_updated) VALUES (?, ?, ?, ?)",
        [(stock["code"], stock["name"], stock["exchange"], "2026-04-30 09:00:00") for stock in stocks],
    )
    conn.commit()

    monkeypatch.setenv("PRICEDB_AKSHARE_WORKERS", "2")
    monkeypatch.setattr(pricedb.providers, "AKSHARE_RETRY_DELAY", 0)
    monkeypatch.setattr(pricedb, "_UPDATE_DEADLINE", None)

    fake_ak = _FakeAkShare()
    pricedb._bulk_fetch_akshare(conn, stocks, "20260421", "20260430", fake_ak)

    rows = conn.execute(
        "SELECT code, date, open, high, low, close, volume, amount "
        "FROM daily_prices ORDER BY code"
    ).fetchall()
    conn.close()

    assert rows == [
        ("000001", "2026-04-30", 10.1, 10.5, 10.0, 10.4, 123456, 6543210.5),
        ("600519", "2026-04-30", 10.1, 10.5, 10.0, 10.4, 123456, 6543210.5),
    ]
    assert fake_ak.calls["600519"] == 2
