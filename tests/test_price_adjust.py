"""Unit tests for read-time price adjustment (price_adjust + consumers)."""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import price_adjust as pa


def _db():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE daily_prices (code TEXT, date TEXT, open REAL, high REAL,"
        " low REAL, close REAL, volume INTEGER, amount REAL, PRIMARY KEY (code, date))"
    )
    pa.ensure_adj_schema(conn)
    return conn


def test_schema_idempotent():
    conn = _db()
    pa.ensure_adj_schema(conn)  # second call must not raise
    assert conn.execute("SELECT COUNT(*) FROM adj_factors").fetchone()[0] == 0


def test_sql_fragments_enabled(monkeypatch):
    monkeypatch.delenv(pa.PRICE_ADJ_DISABLE_ENV, raising=False)
    assert "LEFT JOIN adj_factors" in pa.adj_join_sql()
    assert pa.adjusted_close_sql() == "d.close * COALESCE(a.factor, 1.0)"


def test_kill_switch_degrades_to_raw(monkeypatch):
    monkeypatch.setenv(pa.PRICE_ADJ_DISABLE_ENV, "1")
    assert pa.adj_join_sql() == ""
    assert pa.adjusted_close_sql() == "d.close"
    assert pa.get_factors_on_date(sqlite3.connect(":memory:"), "2026-07-24") == {}


def test_adjusted_query_composes_with_group_by():
    """The join must not fan out rows or break HAVING COUNT(*)."""
    conn = _db()
    for i, d in enumerate(["2026-07-01", "2026-07-02"]):
        conn.execute("INSERT INTO daily_prices VALUES ('600000', ?, 1,1,1, ?, 0, 0)",
                     (d, 10.0 + i))
    conn.execute("INSERT INTO adj_factors VALUES ('600000', '2026-07-01', 2.0)")
    conn.execute("INSERT INTO adj_factors VALUES ('600000', '2026-07-02', 2.0)")
    sql = (f"SELECT d.code, AVG({pa.adjusted_close_sql()}) FROM daily_prices d"
           f"{pa.adj_join_sql()} WHERE d.date IN ('2026-07-01','2026-07-02') "
           "GROUP BY d.code HAVING COUNT(*) = 2")
    rows = conn.execute(sql).fetchall()
    assert rows == [("600000", 21.0)]  # (10*2 + 11*2)/2


def test_missing_factors_mean_raw():
    conn = _db()
    conn.execute("INSERT INTO daily_prices VALUES ('600000','2026-07-01',1,1,1,10.0,0,0)")
    sql = (f"SELECT AVG({pa.adjusted_close_sql()}) FROM daily_prices d"
           f"{pa.adj_join_sql()} GROUP BY d.code")
    assert conn.execute(sql).fetchone()[0] == 10.0


def test_get_factors_on_date_and_series():
    conn = _db()
    conn.execute("INSERT INTO adj_factors VALUES ('600000','2026-07-01', 2.0)")
    conn.execute("INSERT INTO adj_factors VALUES ('600000','2026-07-02', 2.1)")
    conn.execute("INSERT INTO adj_factors VALUES ('000001','2026-07-02', 1.5)")
    assert pa.get_factors_on_date(conn, "2026-07-02") == {"600000": 2.1, "000001": 1.5}
    assert pa.get_factor_series(conn, "600000") == [("2026-07-01", 2.0), ("2026-07-02", 2.1)]
    assert pa.get_factor_series(conn, "600000", "2026-07-01") == [("2026-07-01", 2.0)]


# --------------------------------------------------------------------------- #
# Ingestion (pricedb factor functions)
# --------------------------------------------------------------------------- #
import pricedb  # noqa: E402


def _pricedb_conn():
    conn = sqlite3.connect(":memory:")
    pricedb.ensure_schema(conn)
    return conn


def test_upsert_diff_detection():
    conn = _pricedb_conn()
    # fresh 1.0 rows: written (presence marker) but NOT a change
    assert pricedb.upsert_adj_factors(conn, [("600000", "2026-07-01", 1.0)]) is None
    # fresh non-1.0 row IS a change (COALESCE previously read 1.0)
    assert pricedb.upsert_adj_factors(conn, [("600000", "2026-07-02", 1.03)]) == "2026-07-02"
    # identical re-upsert: no change
    assert pricedb.upsert_adj_factors(conn, [("600000", "2026-07-02", 1.03)]) is None
    # replacing a value IS a change, earliest date wins
    assert pricedb.upsert_adj_factors(
        conn, [("600000", "2026-07-01", 1.01), ("600000", "2026-07-02", 1.04)]
    ) == "2026-07-01"


def test_forward_fill_from_prior_factor():
    conn = _pricedb_conn()
    for d in ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"]:
        conn.execute("INSERT INTO daily_prices VALUES ('600000', ?, 1,1,1,10,0,0)", (d,))
    # factor rows only on 07-01 (base) and 07-03 (event)
    conn.execute("INSERT INTO adj_factors VALUES ('600000','2026-07-01',1.0)")
    conn.execute("INSERT INTO adj_factors VALUES ('600000','2026-07-03',1.05)")
    filled = pricedb._forward_fill_factors(conn)
    assert filled == 2
    rows = dict(conn.execute("SELECT date, factor FROM adj_factors WHERE code='600000'"))
    assert rows["2026-07-02"] == 1.0     # between base and event
    assert rows["2026-07-04"] == 1.05    # after event, carried forward


def test_forward_fill_skips_unprocessed_codes():
    conn = _pricedb_conn()
    conn.execute("INSERT INTO daily_prices VALUES ('000001','2026-07-01',1,1,1,10,0,0)")
    assert pricedb._forward_fill_factors(conn) == 0
    assert conn.execute("SELECT COUNT(*) FROM adj_factors").fetchone()[0] == 0


class _FakeAk:
    """Raw flat at 20 except an ex-div drop on day 3; hfq mirrors true returns.
    Day-3 raw return = 19.4/20 (=-3%), hfq return = 1.0 → multiplier 1/0.97."""
    def stock_zh_a_hist(self, symbol, period, start_date, end_date, adjust):
        import pandas as pd
        dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"]
        if adjust == "":
            closes = [20.0, 20.0, 19.4, 19.4]
        else:  # hfq: true-return series with 2dp rounding noise on day 2
            closes = [115.0, 115.01, 115.01, 115.01]
        return pd.DataFrame({"日期": dates, "收盘": closes})


def test_derive_factors_return_ratio():
    factors = dict(pricedb.derive_factors_from_akshare(_FakeAk(), "600000",
                                                       "20260701", "20260704"))
    assert factors["2026-07-01"] == 1.0
    assert factors["2026-07-02"] == 1.0            # 0.009% noise < threshold
    assert abs(factors["2026-07-03"] - 20.0 / 19.4) < 1e-6   # dividend multiplier
    assert factors["2026-07-04"] == factors["2026-07-03"]     # carried forward


def test_factor_coverage():
    conn = _db()
    conn.execute("INSERT INTO daily_prices VALUES ('600000','2026-07-01',1,1,1,10,0,0)")
    conn.execute("INSERT INTO daily_prices VALUES ('000001','2026-07-01',1,1,1,10,0,0)")
    conn.execute("INSERT INTO adj_factors VALUES ('600000','2026-07-01', 1.0)")
    cov = pa.factor_coverage(conn)
    assert cov["pair_coverage_pct"] == 50.0
    assert cov["codes_without_factors"] == 1
    assert cov["max_price_date"] == "2026-07-01"


def test_sina_event_parse_with_trailing_comment(monkeypatch):
    """Sina hfq.js is `var x={json};/* signature */` — parse must survive it."""
    class _Resp:
        status_code = 200
        text = ('var sz002832hfq={"total":2,"data":[{"d":"2026-06-09", "f":"6.01"},'
                '{"d":"2025-12-29", "f":"5.81"}]};/* trailing signature */')

    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp())
    events = pricedb.fetch_adj_factor_events_sina("002832", "SZ")
    assert events == [("2025-12-29", 5.81), ("2026-06-09", 6.01)]  # ascending


def test_sina_expand_events_to_dates():
    conn = _pricedb_conn()
    for d in ["2026-06-05", "2026-06-09", "2026-06-10"]:
        conn.execute("INSERT INTO daily_prices VALUES ('002832', ?, 1,1,1,20,0,0)", (d,))
    rows = pricedb._expand_events_to_code_dates(
        conn, "002832", [("2025-12-29", 5.81), ("2026-06-09", 6.01)])
    assert rows == [("002832", "2026-06-05", 5.81),   # pre-ex: prior event's factor
                    ("002832", "2026-06-09", 6.01),   # ex-day: new factor
                    ("002832", "2026-06-10", 6.01)]   # carried forward


def test_sina_symbol_mapping():
    assert pricedb._sina_symbol("600000", "SH") == "sh600000"
    assert pricedb._sina_symbol("002832", "") == "sz002832"
    assert pricedb._sina_symbol("430047", "BJ") is None  # BJ unsupported


# --------------------------------------------------------------------------- #
# Read-path correctness (rps_calculator / fetch_ma_data with a dividend)
# --------------------------------------------------------------------------- #
from datetime import date as _date, timedelta  # noqa: E402

import rps_calculator  # noqa: E402


def _seed_dividend_universe(db_path):
    """3 stocks × 280 trading days. AAA pays a 3% 'dividend' 10 days before the
    end (fake raw gap 100→97, factor 100/97 after); BBB flat 100; CCC drifts
    down. With adjustment AAA is as strong as BBB; without, AAA looks weak."""
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE stocks (code TEXT PRIMARY KEY, name TEXT, exchange TEXT,"
                 " listed_date TEXT, last_updated TEXT)")
    conn.execute("CREATE TABLE daily_prices (code TEXT, date TEXT, open REAL, high REAL,"
                 " low REAL, close REAL, volume INTEGER, amount REAL, PRIMARY KEY (code, date))")
    conn.execute("CREATE TABLE rps_cache (date TEXT, code TEXT, rps20 REAL, rps60 REAL,"
                 " rps120 REAL, rps250 REAL, ma10 REAL, PRIMARY KEY (date, code))")
    pa.ensure_adj_schema(conn)
    for c in ("AAA", "BBB", "CCC"):
        conn.execute("INSERT INTO stocks VALUES (?, ?, 'SH', NULL, NULL)", (c, c))
    start = _date(2025, 6, 2)
    dates = []
    d = start
    while len(dates) < 280:
        if d.weekday() < 5:
            dates.append(d.isoformat())
        d += timedelta(days=1)
    ex_idx = len(dates) - 10  # dividend 10 trading days before the end
    for i, ds in enumerate(dates):
        aaa = 100.0 if i < ex_idx else 97.0
        conn.execute("INSERT INTO daily_prices VALUES ('AAA', ?, ?, ?, ?, ?, 1000, 0)",
                     (ds, aaa, aaa, aaa, aaa))
        conn.execute("INSERT INTO daily_prices VALUES ('BBB', ?, 100,100,100,100, 1000, 0)",
                     (ds,))
        ccc = 100.0 - i * 0.05
        conn.execute("INSERT INTO daily_prices VALUES ('CCC', ?, ?, ?, ?, ?, 1000, 0)",
                     (ds, ccc, ccc, ccc, ccc))
        conn.execute("INSERT INTO adj_factors VALUES ('AAA', ?, ?)",
                     (ds, 1.0 if i < ex_idx else 100.0 / 97.0))
        conn.execute("INSERT INTO adj_factors VALUES ('BBB', ?, 1.0)", (ds,))
        conn.execute("INSERT INTO adj_factors VALUES ('CCC', ?, 1.0)", (ds,))
    conn.commit()
    conn.close()
    return dates


def test_dividend_no_longer_dents_rps(tmp_path, monkeypatch):
    monkeypatch.delenv(pa.PRICE_ADJ_DISABLE_ENV, raising=False)
    db = str(tmp_path / "adj.db")
    _seed_dividend_universe(db)
    rps = rps_calculator.compute_ma_rps(db, force_recompute=True)
    # Adjusted: AAA (flat + dividend) must rank ABOVE the genuinely declining
    # CCC. (AAA and BBB have identical deltas; their relative order is an
    # arbitrary tie-break, so we don't assert it.)
    assert rps["AAA"]["rps20"] > rps["CCC"]["rps20"]
    # F2: reported ma10 stays in REAL price scale (post-dividend ≈ 97, not 100+)
    assert 96.0 < rps["AAA"]["ma10_today"] < 98.0


def test_without_adjustment_dividend_dents_rps(tmp_path, monkeypatch):
    monkeypatch.setenv(pa.PRICE_ADJ_DISABLE_ENV, "1")
    db = str(tmp_path / "raw.db")
    _seed_dividend_universe(db)
    rps = rps_calculator.compute_ma_rps(db, force_recompute=True)
    # Raw: the fake -3% gap sinks AAA below BOTH the flat stock AND the
    # genuinely declining one (the old bug this change fixes).
    assert rps["AAA"]["rps20"] < rps["BBB"]["rps20"]
    assert rps["AAA"]["rps20"] < rps["CCC"]["rps20"]


def test_alignment_values_stay_price_scale(tmp_path, monkeypatch):
    monkeypatch.delenv(pa.PRICE_ADJ_DISABLE_ENV, raising=False)
    db = str(tmp_path / "align.db")
    _seed_dividend_universe(db)
    out = rps_calculator.compute_ma_alignment(db)
    # AAA's MAs normalized to today's scale: near 97 (raw current), not ~100×f
    assert 95.0 < out["AAA"]["ma20"] < 98.5
    assert out["BBB"]["ma20"] == 100.0


def test_fetch_ma_data_price_raw_dist_adjusted(tmp_path, monkeypatch):
    monkeypatch.delenv(pa.PRICE_ADJ_DISABLE_ENV, raising=False)
    db = tmp_path / "fetch.db"
    _seed_dividend_universe(str(db))
    import data_collector
    monkeypatch.setattr(data_collector, "DEFAULT_PRICEDB_PATH", db)
    out = data_collector.fetch_ma_data([{"code": "AAA"}])
    assert out["AAA"]["price"] == 97.0            # raw tradeable price
    # adjusted series is flat at today-scale 97 ⇒ zero distance, no fake dip
    assert abs(out["AAA"]["dist_ma5_pct"]) < 0.2
    assert abs(out["AAA"]["dist_ma20_pct"]) < 0.2
