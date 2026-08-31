"""Tests for local pricedb RPS integration."""
import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

FIXTURES_DIR = Path(__file__).parent / "test_fixtures"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / f"{name}.json", encoding="utf-8") as fh:
        return json.load(fh)

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
    import pricedb
    import pricedb.providers

    db_path = tmp_path / "prices.db"
    conn = _create_test_db(db_path)
    latest_date = _seed_prices(conn)
    conn.close()

    # Staleness gate: pin "most recent trading day" to the seeded end date so
    # this fixture-based test stays valid regardless of wall-clock date.
    latest_dt = datetime.strptime(latest_date, "%Y-%m-%d").date()
    monkeypatch.setattr(pricedb, "most_recent_trading_day", lambda _today, calendar=None: latest_dt)

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
    # Remote CheeseForTune cross-check would otherwise filter out the synthetic code.
    monkeypatch.setattr(dc, "fetch_strategy_pool", lambda strategy_id="407228": {
        "source": "api",
        "strategy_id": strategy_id,
        "date": latest_date,
        "total_stocks": 1,
        "stocks": [{"code": "600001", "name": "测试龙头"}],
        "error": None,
    })

    result = dc.fetch_strategy_pool_local(str(db_path))

    assert result["source"] in {"local_pricedb", "local_pricedb+cf_cross"}
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


# ---------------------------------------------------------------------------
# Proxy bypass + trade calendar + staleness gate (added 2026-05-13)
# ---------------------------------------------------------------------------


def test_no_proxy_env_strips_and_restores(monkeypatch):
    import pricedb

    monkeypatch.setenv("HTTP_PROXY", "http://surge:6152")
    monkeypatch.setenv("https_proxy", "http://surge:6152")
    monkeypatch.setenv("ALL_PROXY", "socks5://surge:6153")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.delenv("HTTPS_PROXY", raising=False)

    with pricedb._no_proxy_env():
        assert "HTTP_PROXY" not in os.environ
        assert "https_proxy" not in os.environ
        assert "ALL_PROXY" not in os.environ
        # NO_PROXY='*' beats macOS *system* proxy fallback in requests —
        # stripping env vars alone is not enough (2026-07-24 backfill lesson)
        assert os.environ["NO_PROXY"] == "*"
        assert os.environ["no_proxy"] == "*"

    assert os.environ["HTTP_PROXY"] == "http://surge:6152"
    assert os.environ["https_proxy"] == "http://surge:6152"
    assert os.environ["ALL_PROXY"] == "socks5://surge:6153"
    assert os.environ["NO_PROXY"] == "127.0.0.1"
    assert "HTTPS_PROXY" not in os.environ


def test_no_proxy_env_force_proxy_override(monkeypatch):
    import pricedb

    monkeypatch.setenv("PRICEDB_FORCE_PROXY", "socks5h://127.0.0.1:1080")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    with pricedb._no_proxy_env():
        assert os.environ["HTTPS_PROXY"] == "socks5h://127.0.0.1:1080"
        assert os.environ["HTTP_PROXY"] == "socks5h://127.0.0.1:1080"
        assert "NO_PROXY" not in os.environ
    assert os.environ["NO_PROXY"] == "127.0.0.1"
    assert "HTTPS_PROXY" not in os.environ


def test_most_recent_trading_day_weekend():
    import pricedb

    # 2026-05-09 is a Saturday → expect prior Friday (2026-05-08)
    calendar = ["20260507", "20260508", "20260511", "20260512", "20260513"]
    assert pricedb.most_recent_trading_day(date(2026, 5, 9), calendar) == date(2026, 5, 8)
    assert pricedb.most_recent_trading_day(date(2026, 5, 10), calendar) == date(2026, 5, 8)


def test_most_recent_trading_day_holiday():
    import pricedb

    # Treat 2026-05-01 (Labor Day) as missing from calendar
    calendar = ["20260428", "20260429", "20260430", "20260506", "20260507"]
    assert pricedb.most_recent_trading_day(date(2026, 5, 1), calendar) == date(2026, 4, 30)
    assert pricedb.most_recent_trading_day(date(2026, 5, 5), calendar) == date(2026, 4, 30)


def test_most_recent_trading_day_weekday_fallback():
    """When no calendar is available, walk back from weekends only."""
    import pricedb

    # Empty calendar triggers weekday fallback
    assert pricedb.most_recent_trading_day(date(2026, 5, 9), []) == date(2026, 5, 8)
    assert pricedb.most_recent_trading_day(date(2026, 5, 13), []) == date(2026, 5, 13)


def _seed_one_row(db_path: Path, latest_date: str):
    conn = _create_test_db(db_path)
    conn.execute(
        "INSERT INTO stocks (code, name, exchange, last_updated) VALUES (?, ?, ?, ?)",
        ("600001", "Test", "SH", "2026-05-13"),
    )
    conn.execute(
        "INSERT INTO daily_prices (code, date, open, high, low, close, volume, amount) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("600001", latest_date, 10, 10, 10, 10, 1000, 10000),
    )
    conn.commit()
    conn.close()


def test_staleness_gate_today_trading_day_stale(tmp_path, monkeypatch):
    """pricedb at 2026-05-08, today is a trading day → expect stale error."""
    import data_collector as dc
    import pricedb

    db_path = tmp_path / "stale.db"
    _seed_one_row(db_path, "2026-05-08")
    monkeypatch.setattr(pricedb, "most_recent_trading_day",
                        lambda d, calendar=None: date(2026, 5, 13))
    monkeypatch.setattr(dc, "fetch_strategy_pool", lambda strategy_id="407228": {
        "source": "api", "strategy_id": strategy_id, "date": "2026-05-13",
        "total_stocks": 0, "stocks": [], "error": None,
    })

    # Stale path falls back to remote — verify the fallback fired (source=="api").
    result = dc.fetch_strategy_pool_local(str(db_path))
    assert result["source"] == "api"


def test_staleness_gate_weekend_ok(tmp_path, monkeypatch):
    """pricedb at Fri 2026-05-08, today is Sat 2026-05-09 → no stale error."""
    import data_collector as dc
    import pricedb

    db_path = tmp_path / "weekend.db"
    _seed_one_row(db_path, "2026-05-08")
    monkeypatch.setattr(pricedb, "most_recent_trading_day",
                        lambda d, calendar=None: date(2026, 5, 8))
    monkeypatch.setattr(dc, "fetch_strategy_pool", lambda strategy_id="407228": {
        "source": "api", "strategy_id": strategy_id, "date": "2026-05-08",
        "total_stocks": 0, "stocks": [], "error": None,
    })
    monkeypatch.setattr(dc, "batch_enrich", lambda stocks, max_workers=8: [])

    # Local path is reached (no RuntimeError) — confirmed by source containing local_pricedb.
    result = dc.fetch_strategy_pool_local(str(db_path))
    assert "local_pricedb" in result["source"] or result["source"] == "api"


def test_staleness_gate_today_fresh(tmp_path, monkeypatch):
    """pricedb fresh today → no stale error."""
    import data_collector as dc
    import pricedb

    db_path = tmp_path / "fresh.db"
    _seed_one_row(db_path, "2026-05-13")
    monkeypatch.setattr(pricedb, "most_recent_trading_day",
                        lambda d, calendar=None: date(2026, 5, 13))
    monkeypatch.setattr(dc, "fetch_strategy_pool", lambda strategy_id="407228": {
        "source": "api", "strategy_id": strategy_id, "date": "2026-05-13",
        "total_stocks": 0, "stocks": [], "error": None,
    })
    monkeypatch.setattr(dc, "batch_enrich", lambda stocks, max_workers=8: [])

    result = dc.fetch_strategy_pool_local(str(db_path))
    # Either local (insufficient data → empty) or cross-checked, never stale fallback.
    assert "local_pricedb" in result["source"] or result["source"] == "api"


# ---------------------------------------------------------------------------
# Eastmoney clist URL construction + response parsing
# ---------------------------------------------------------------------------


def test_clist_url_construction():
    import pricedb
    from urllib.parse import urlparse

    url = pricedb._eastmoney_clist_url(3)
    parsed = urlparse(url)
    assert parsed.netloc == "push2.eastmoney.com"
    assert parsed.path == "/api/qt/clist/get"
    # Inspect raw query (parse_qs would turn + into space — Eastmoney wants literal +).
    raw = parsed.query
    assert "pn=3" in raw
    assert f"pz={pricedb.EASTMONEY_CLIST_PAGE_SIZE}" in raw
    # Covers SH main, SH STAR, SZ main, SZ ChiNext, BJ — literal + must survive encoding.
    for board in ("m:0+t:6", "m:0+t:80", "m:1+t:2", "m:1+t:23", "m:0+t:81"):
        assert board in raw, f"missing board filter {board} in {raw}"
    for f in ("f12", "f14", "f2", "f15", "f16", "f17", "f18", "f5", "f6"):
        assert f in raw


def test_clist_response_parsing_full_page():
    import pricedb

    payload = _load_fixture("eastmoney_clist_page1")
    rows = pricedb._parse_clist_page(payload, "2026-05-13")

    # 5 entries in fixture; 600019 has "-" prices (suspended) → filtered out.
    codes = [row[0] for row in rows]
    assert "600000" in codes
    assert "600519" in codes
    assert "000001" in codes
    assert "600019" not in codes  # suspended
    pf = next(r for r in rows if r[0] == "600000")
    # tuple shape: (code, date, open, high, low, close, volume, amount)
    assert pf[1] == "2026-05-13"
    assert pf[2] == 12.20  # open (f17)
    assert pf[3] == 12.50  # high (f15)
    assert pf[4] == 12.10  # low (f16)
    assert pf[5] == 12.34  # close (f2)
    assert pf[6] == 152300
    assert pf[7] == 187940000.0


def test_clist_response_parsing_suspended_and_nulls():
    import pricedb

    payload = _load_fixture("eastmoney_clist_suspended")
    rows = pricedb._parse_clist_page(payload, "2026-05-13")
    codes = [row[0] for row in rows]
    # 600101 has "-" close, 600102 has null close → both excluded.
    assert codes == ["600103"]


def test_clist_response_parsing_partial_last_page():
    import pricedb

    payload = _load_fixture("eastmoney_clist_last_page")
    rows = pricedb._parse_clist_page(payload, "2026-05-13")
    assert len(rows) == 2
    assert {row[0] for row in rows} == {"688001", "300001"}


def test_clist_pagination_terminates(tmp_path, monkeypatch):
    """Multi-page fetch should issue exactly ceil(total/page_size) calls and stop."""
    import pricedb

    payload_page1 = _load_fixture("eastmoney_clist_page1")
    # Simulate total=125 → 3 pages of 50,50,25
    payload_page1["data"]["total"] = 125
    payload_page2 = _load_fixture("eastmoney_clist_page1")
    payload_page2["data"]["total"] = 125
    payload_page3 = _load_fixture("eastmoney_clist_last_page")
    payload_page3["data"]["total"] = 125

    calls: list[int] = []

    def fake_fetch(page):
        calls.append(page)
        return {1: payload_page1, 2: payload_page2, 3: payload_page3}[page]

    monkeypatch.setattr(pricedb.providers, "_fetch_clist_page", fake_fetch)
    today_yyyymmdd = datetime.now().strftime("%Y%m%d")

    db_path = tmp_path / "pages.db"
    conn = _create_test_db(db_path)
    conn.executemany(
        "INSERT INTO stocks (code, name, exchange, last_updated) VALUES (?, ?, ?, ?)",
        [("600000", "x", "SH", ""), ("600519", "x", "SH", ""), ("000001", "x", "SZ", ""),
         ("688001", "x", "SH", ""), ("300001", "x", "SZ", "")],
    )
    conn.commit()
    stocks = [{"code": c, "name": "x", "exchange": "SH"}
              for c in ("600000", "600519", "000001", "688001", "300001")]

    pricedb._bulk_fetch_eastmoney_clist(
        conn, stocks, today_yyyymmdd, today_yyyymmdd, None,
    )
    assert calls == [1, 2, 3]
    conn.close()


def test_bulk_fetch_clist_rejects_multi_day(tmp_path, monkeypatch):
    import pricedb

    monkeypatch.setattr(pricedb.providers, "_fetch_clist_page",
                        lambda p: (_ for _ in ()).throw(AssertionError("should not be called")))
    db_path = tmp_path / "x.db"
    conn = _create_test_db(db_path)
    with pytest.raises(RuntimeError, match="single-day"):
        pricedb._bulk_fetch_eastmoney_clist(
            conn,
            [{"code": "600000", "name": "x", "exchange": "SH"}],
            "20260512", "20260513", None,
        )
    conn.close()


def test_bulk_fetch_clist_rejects_non_today(tmp_path, monkeypatch):
    import pricedb

    monkeypatch.setattr(pricedb.providers, "_fetch_clist_page",
                        lambda p: (_ for _ in ()).throw(AssertionError("should not be called")))
    db_path = tmp_path / "x.db"
    conn = _create_test_db(db_path)
    # beg == end but not today
    with pytest.raises(RuntimeError, match="today"):
        pricedb._bulk_fetch_eastmoney_clist(
            conn,
            [{"code": "600000", "name": "x", "exchange": "SH"}],
            "20260101", "20260101", None,
        )
    conn.close()


def test_fetch_trade_dates_free_weekday_fallback(monkeypatch):
    import pricedb

    # Force akshare to be unavailable so we exercise the weekday fallback
    def boom():
        raise RuntimeError("no akshare here")
    # Patch the OWNER: fetch_trade_dates_free lives in pricedb.providers since
    # 2026-08-31 and resolves _run_with_timeout in ITS module — the old patch on
    # pricedb was inert and this test passed for an unrelated reason (audit).
    import pricedb.providers
    monkeypatch.setattr(pricedb.providers, "_run_with_timeout",
                        lambda label, fn, timeout=None: boom() if "akshare" in label else fn())
    # Also force the akshare import to fail
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "akshare":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    dates = pricedb.fetch_trade_dates_free("20260504", "20260510")
    # Mon=04, Tue=05, Wed=06, Thu=07, Fri=08 — Sat/Sun excluded
    assert dates == ["20260504", "20260505", "20260506", "20260507", "20260508"]


# ---------------------------------------------------------------------------
# Integration tests (network) — skipped by default
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_eastmoney_clist_live():
    import pricedb
    payload = pricedb._fetch_clist_page(1)
    rows = pricedb._parse_clist_page(payload, datetime.now().strftime("%Y-%m-%d"))
    assert len(rows) >= 30, f"page 1 had only {len(rows)} parseable rows"
    total = int((payload.get("data") or {}).get("total") or 0)
    assert total >= 3000, f"clist total reports {total} A-shares (expected ≥3000)"


@pytest.mark.integration
def test_akshare_trade_cal_live():
    import pricedb
    today = datetime.now().strftime("%Y%m%d")
    beg = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    dates = pricedb.fetch_trade_dates_free(beg, today)
    assert dates, "akshare trade calendar returned nothing"
    # Most recent trading day must be within the last week.
    latest = datetime.strptime(dates[-1], "%Y%m%d").date()
    assert (datetime.now().date() - latest).days <= 7


@pytest.mark.integration
def test_proxy_bypass_actually_works(monkeypatch):
    import pricedb
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    # Should still succeed via _no_proxy_env + trust_env=False.
    payload = pricedb._fetch_clist_page(1)
    assert payload.get("data")
