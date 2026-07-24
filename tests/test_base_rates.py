"""base_rates.py — reference-class frequencies for risk quantification.

Synthetic-panel tests: no DB, no network. The panel builder itself is exercised
against a temp SQLite DB to lock the covered-dates rule (under-covered fetch
days must be excluded, mirroring rps_calculator's reference-date behavior).
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import base_rates
import deep_report
import deep_verify


@pytest.fixture(autouse=True)
def _clear_cache():
    base_rates._PANEL_CACHE.clear()
    yield
    base_rates._PANEL_CACHE.clear()


def test_wilson_ci_basics():
    lo, hi = base_rates.wilson_ci(0, 0)
    assert (lo, hi) == (0.0, 100.0)
    lo, hi = base_rates.wilson_ci(50, 100)
    assert lo < 50.0 < hi
    assert hi - lo < 21  # n=100 → roughly ±10pts
    lo2, hi2 = base_rates.wilson_ci(5000, 10000)
    assert hi2 - lo2 < hi - lo  # more data → tighter


def test_cross_rank_pct_matches_production_formula():
    df = pd.DataFrame([[1.0, 2.0, 3.0, None]], index=["2026-01-01"],
                      columns=list("abcd"))
    pct = base_rates._cross_rank_pct(df)
    # rank/(count-1)*100 over the 3 valid values → 0 / 50 / 100
    assert list(pct.iloc[0][:3]) == [0.0, 50.0, 100.0]
    assert pd.isna(pct.iloc[0]["d"])


def test_panel_drops_under_covered_dates(tmp_path):
    db = tmp_path / "p.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE daily_prices (code TEXT, date TEXT, close REAL)")
    codes = [f"c{i}" for i in range(10)]
    for d in ("2026-01-05", "2026-01-06", "2026-01-08"):
        for c in codes:
            conn.execute("INSERT INTO daily_prices VALUES (?,?,10.0)", (c, d))
    # 2026-01-07 is a partial fetch day: only 2 of 10 codes
    for c in codes[:2]:
        conn.execute("INSERT INTO daily_prices VALUES (?,?,10.0)", (c, "2026-01-07"))
    conn.commit()
    conn.close()

    closes = base_rates._load_closes(str(db))
    assert "2026-01-07" not in closes.index  # excluded, like production RPS
    assert list(closes.index) == ["2026-01-05", "2026-01-06", "2026-01-08"]


def _synthetic_panel(n_days=200, crash_stock_ret=-0.30):
    """Panel where stock 'crash' enters the state then falls 30%, 'flat' doesn't."""
    idx = [f"2026-{1 + d // 28:02d}-{1 + d % 28:02d}" for d in range(n_days)]
    crash = [100.0] * 100 + [100.0 * (1 + crash_stock_ret)] * (n_days - 100)
    flat = [100.0] * n_days
    closes = pd.DataFrame({"crash": crash, "flat": flat}, index=idx)
    ones = pd.DataFrame(1.0, index=idx, columns=closes.columns)
    entry_day = idx[95]
    cond = pd.DataFrame(False, index=idx, columns=closes.columns)
    cond.loc[entry_day, "crash"] = True
    cond.loc[entry_day, "flat"] = True
    panel = {"closes": closes, "dist_ma10_pct": ones * -1,
             "rps20": ones * 95, "rps60": ones * 95,
             "rps120": ones * 95, "rps250": ones * 95}
    return panel, cond


def test_technical_base_rate_counts_entries_and_hits(monkeypatch):
    panel, cond = _synthetic_panel()
    monkeypatch.setitem(base_rates._PANEL_CACHE, "fake.db", panel)
    monkeypatch.setitem(
        base_rates.TECHNICAL_CONFIGS, "extended_high_momentum",
        ("test", lambda p: cond))

    r = base_rates.technical_base_rate("extended_high_momentum", 20, 15,
                                       db_path="fake.db")
    assert r["n_episodes"] == 2          # both stocks entered once
    assert r["n_hit"] == 1               # only 'crash' hit −15% within 20d
    assert r["frequency_pct"] == 50.0
    assert r["wilson95_pct"][0] < 50.0 < r["wilson95_pct"][1]
    assert "样本窗口不足3个月" in r["caveats"]  # single entry date → short window


def test_technical_base_rate_rejects_off_menu_params():
    with pytest.raises(ValueError):
        base_rates.technical_base_rate("free_form_hack", 60, 15)
    with pytest.raises(ValueError):
        base_rates.technical_base_rate("extended_high_momentum", 61, 15)
    with pytest.raises(ValueError):
        base_rates.technical_base_rate("extended_high_momentum", 60, 42)


def test_growth_persistence_from_stubbed_tables(monkeypatch):
    import fundamentals

    def fake_load(kind, period):
        assert kind == "yjbb"
        if period == "20251231":  # older: three high-growth stocks
            return pd.DataFrame({"股票代码": ["a", "b", "c"],
                                 "净利润-同比增长": [50.0, 80.0, 10.0]})
        if period == "20260331":  # newer: a decelerates, b keeps growing
            return pd.DataFrame({"股票代码": ["a", "b", "c"],
                                 "净利润-同比增长": [5.0, 60.0, 12.0]})
        return None

    monkeypatch.setattr(fundamentals, "_load_table", fake_load)
    from datetime import date
    r = base_rates.growth_persistence(today=date(2026, 7, 24))
    assert r["n_episodes"] == 2   # a, b (c wasn't high-growth)
    assert r["n_hit"] == 1        # a fell below 20%
    assert r["frequency_pct"] == 50.0


def test_base_rate_tool_executor_stores_into_corpus(monkeypatch):
    monkeypatch.setattr(
        base_rates, "base_rate",
        lambda cfg, h, dd: {"config": cfg, "frequency_pct": 38.99, "n_episodes": 11442})
    data = {}
    tools, executor = deep_report._make_report_tools(data)
    assert [t["name"] for t in tools] == ["stock_fundamentals", "base_rate"]

    out = executor("base_rate", {"config": "extended_high_momentum"})
    assert "38.99" in out
    assert data["base_rates"]["extended_high_momentum_60d_15pct"]["n_episodes"] == 11442
    nums = deep_verify.flatten_data_numbers(data)
    assert deep_verify.internal_numbers_match(["38.99", "11442"], nums)

    # off-menu config comes back as a tool error string, not an exception
    def raiser(cfg, h, dd):
        raise ValueError("unknown config")
    monkeypatch.setattr(base_rates, "base_rate", raiser)
    assert executor("base_rate", {"config": "nope"}).startswith("Error:")
