"""Tests for local pricedb RPS integration."""
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


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

        CREATE INDEX idx_dp_date ON daily_prices(date);
        CREATE INDEX idx_dp_code_date ON daily_prices(code, date);

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


def _seed_prices(conn: sqlite3.Connection):
    start = date(2025, 6, 16)
    dates = [(start + timedelta(days=index)).isoformat() for index in range(270)]

    conn.executemany(
        "INSERT INTO stocks (code, name, exchange, last_updated) VALUES (?, ?, ?, ?)",
        [
            ("600001", "测试龙头", "SH", "2026-03-12 09:00:00"),
            ("000001", "测试跟风", "SZ", "2026-03-12 09:00:00"),
        ],
    )

    rows = []
    for index, trading_date in enumerate(dates, start=1):
        leader_close = float(index)
        laggard_close = float(max(1, 400 - index))
        rows.append(("600001", trading_date, leader_close, leader_close, leader_close, leader_close, 1000, leader_close * 1000))
        rows.append(("000001", trading_date, laggard_close, laggard_close, laggard_close, laggard_close, 1000, laggard_close * 1000))

    conn.executemany(
        "INSERT INTO daily_prices (code, date, open, high, low, close, volume, amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return dates[-1]


def test_compute_ma_resolves_latest_trading_date(tmp_path):
    from rps_calculator import compute_ma

    db_path = tmp_path / "prices.db"
    conn = _create_test_db(db_path)
    conn.executemany(
        "INSERT INTO stocks (code, name, exchange, last_updated) VALUES (?, ?, ?, ?)",
        [("600001", "测试股", "SH", "2026-03-12 09:00:00")],
    )
    conn.executemany(
        "INSERT INTO daily_prices (code, date, open, high, low, close, volume, amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("600001", "2026-01-05", 10, 10, 10, 10, 1000, 10000),
            ("600001", "2026-01-06", 11, 11, 11, 11, 1000, 11000),
            ("600001", "2026-01-07", 12, 12, 12, 12, 1000, 12000),
            ("600001", "2026-01-08", 13, 13, 13, 13, 1000, 13000),
            ("600001", "2026-01-09", 14, 14, 14, 14, 1000, 14000),
        ],
    )
    conn.commit()
    conn.close()

    ma = compute_ma(str(db_path), "600001", "2026-01-10", period=3)
    assert ma == 13.0


def test_fetch_strategy_pool_local_uses_local_rps_and_filters(tmp_path, monkeypatch):
    import data_collector as dc

    db_path = tmp_path / "prices.db"
    conn = _create_test_db(db_path)
    latest_date = _seed_prices(conn)
    conn.close()

    def fake_batch_enrich(stocks, max_workers=8):
        assert [stock["code"] for stock in stocks] == ["600001"]
        return [{
            "code": "600001.SH",
            "name": "测试龙头",
            "pe": 20.5,
            "pb": 3.2,
            "total_shares": 100_000_000,
            "score_company": 8.2,
            "score_trend": 8.8,
            "score_value": 6.4,
            "highlights": [
                {"tag": "龙头", "text": "行业龙头"},
                {"tag": "成长", "text": "营收增长"},
                {"tag": "盈利", "text": "利润改善"},
                {"tag": "趋势", "text": "趋势向上"},
            ],
            "risks": [{"tag": "板块", "text": "板块短期震荡"}],
            "events": [],
            "industries": [{"name": "测试行业", "level": 1}],
            "concepts": ["测试概念"],
        }]

    monkeypatch.setattr(dc, "batch_enrich", fake_batch_enrich)

    result = dc.fetch_strategy_pool_local(str(db_path))

    assert result["source"] == "local_pricedb"
    assert result["strategy_id"] == dc.LOCAL_STRATEGY_ID
    assert result["date"] == latest_date
    assert result["total_stocks"] == 1

    stock = result["stocks"][0]
    assert stock["code"] == "600001"
    assert stock["name"] == "测试龙头"
    assert stock["market_cap"] == 270.0
    assert stock["highlights_count"] == 4
    assert stock["risks_count"] == 1
    assert stock["rps120"] >= 85
    assert stock["rps250"] >= 85
    assert stock["rps60"] >= 70


def test_fetch_strategy_pool_local_falls_back_when_missing(monkeypatch):
    import data_collector as dc

    sentinel = {
        "source": "api",
        "strategy_id": "407228",
        "total_stocks": 1,
        "stocks": [{"code": "000001", "name": "平安银行"}],
        "error": None,
    }
    monkeypatch.setattr(dc, "fetch_strategy_pool", lambda strategy_id="407228": sentinel)

    result = dc.fetch_strategy_pool_local("/tmp/does-not-exist.db")
    assert result == sentinel


class _FakeFrame:
    def __init__(self, rows):
        self._rows = rows
        self.empty = len(rows) == 0

    def itertuples(self, index=False):
        return iter(self._rows)


class _FakeBaoStockResult:
    def __init__(self, fields, rows, error_code="0", error_msg=""):
        self.fields = fields
        self._rows = rows
        self._idx = -1
        self.error_code = error_code
        self.error_msg = error_msg

    def next(self):
        self._idx += 1
        return self._idx < len(self._rows)

    def get_row_data(self):
        return self._rows[self._idx]


class _FakePro:
    def stock_basic(self, **kwargs):
        class Row:
            def __init__(self, ts_code, name, list_date):
                self.ts_code = ts_code
                self.name = name
                self.list_date = list_date
        return _FakeFrame([
            Row("600519.SH", "贵州茅台", "20010827"),
            Row("000001.SZ", "平安银行", "19910403"),
            Row("430047.BJ", "诺思兰德", "20201124"),
        ])


class _FakeBaoStock:
    def query_all_stock(self, day=None):
        return _FakeBaoStockResult(
            fields=["code", "code_name", "ipoDate"],
            rows=[
                ["sh.600519", "贵州茅台", "2001-08-27"],
                ["sz.000001", "平安银行", "1991-04-03"],
                ["bj.430047", "诺思兰德", "2020-11-24"],
            ],
        )



def test_fetch_stock_list_tushare_parses_stock_basic():
    import pricedb

    stocks = pricedb.fetch_stock_list_tushare(_FakePro())

    assert [stock["code"] for stock in stocks] == ["600519", "000001", "430047"]
    assert [stock["exchange"] for stock in stocks] == ["SH", "SZ", "BJ"]
    assert stocks[0]["listed_date"] == "2001-08-27"



def test_fetch_stock_list_baostock_parses_rows():
    import pricedb

    stocks = pricedb.fetch_stock_list_baostock(_FakeBaoStock())

    assert [stock["code"] for stock in stocks] == ["600519", "000001", "430047"]
    assert [stock["exchange"] for stock in stocks] == ["SH", "SZ", "BJ"]
    assert stocks[1]["name"] == "平安银行"
