"""etf_shares: share counts of the broad ETFs 汇金 dominates, and their 1- and
5-session change — the 国家队 proxy in report.md."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import etf_shares as es

# trading calendar, newest first — 8 sessions, as trading_dates() returns
DATES = ["2026-11-20", "2026-11-19", "2026-11-18", "2026-11-17",
         "2026-11-16", "2026-11-13", "2026-11-12", "2026-11-11"]


# --- changes ---------------------------------------------------------------

def test_changes_are_against_one_and_five_sessions_back():
    series = {"2026-11-20": 150.0, "2026-11-19": 120.0, "2026-11-13": 100.0}
    assert es.changes(series, DATES) == {
        "asof": "2026-11-20", "shares_wan": 150.0, "chg1_pct": 25.0, "chg_long_pct": 50.0}


def test_asof_is_the_newest_session_the_series_has():
    # today's count is not published yet: asof and both windows shift back one
    series = {"2026-11-19": 120.0, "2026-11-18": 100.0, "2026-11-12": 80.0}
    out = es.changes(series, DATES)
    assert (out["asof"], out["chg1_pct"], out["chg_long_pct"]) == ("2026-11-19", 20.0, 50.0)


def test_a_missing_session_gives_no_change_not_a_wrong_one():
    series = {"2026-11-20": 150.0, "2026-11-18": 100.0}   # 11-19 and 11-13 absent
    out = es.changes(series, DATES)
    assert out["chg1_pct"] is None and out["chg_long_pct"] is None


def test_an_empty_series_is_an_error():
    assert "error" in es.changes({}, DATES)


# --- SSE: one call per date ------------------------------------------------

def test_sse_series_skips_unpublished_sessions_and_fetches_three_dates(monkeypatch):
    calls = []

    def fetch(day):
        calls.append(day)
        return {} if day == "2026-11-20" else {"510050": 100.0, "999999": 1.0}

    monkeypatch.setattr(es, "fetch_sse", fetch)
    out = es.sse_series(DATES)
    assert calls == ["2026-11-20", "2026-11-19", "2026-11-18", "2026-11-12"]
    assert out["510050"] == {"2026-11-19": 100.0, "2026-11-18": 100.0, "2026-11-12": 100.0}
    assert "999999" not in out and "159919" not in out     # only SSE funds in WATCH


def test_sse_series_raises_when_nothing_is_published(monkeypatch):
    monkeypatch.setattr(es, "fetch_sse", lambda day: {})
    with pytest.raises(ValueError, match="未公布"):
        es.sse_series(DATES)


# --- collect ---------------------------------------------------------------

def _sse(day):
    base = {"2026-11-20": 150.0, "2026-11-19": 120.0, "2026-11-13": 100.0}
    return {code: base[day] for code, ex, _, _ in es.WATCH if ex == "SH"}


def _patch(monkeypatch, sse=_sse, szse=lambda code, beg, end: {"2026-11-20": 30.0, "2026-11-19": 20.0}):
    monkeypatch.setattr(es, "trading_dates", lambda today: DATES)
    monkeypatch.setattr(es, "fetch_sse", sse)
    monkeypatch.setattr(es, "fetch_szse", szse)


def test_collect_returns_a_row_per_watched_fund(monkeypatch):
    _patch(monkeypatch)
    out = es.collect("2026-11-22")
    assert out["asof"] == "2026-11-20" and out["holder_asof"] == es.HOLDER_ASOF
    assert [r["code"] for r in out["rows"]] == [w[0] for w in es.WATCH]
    sz = next(r for r in out["rows"] if r["code"] == "159919")
    assert (sz["chg1_pct"], sz["chg_long_pct"]) == (50.0, None)


def test_one_exchange_down_keeps_the_other(monkeypatch):
    def boom(code, beg, end):
        raise OSError("szse down")
    _patch(monkeypatch, szse=boom)
    out = es.collect("2026-11-22")
    by_code = {r["code"]: r for r in out["rows"]}
    assert by_code["159919"]["error"] == "OSError: szse down"
    assert by_code["510050"]["chg_long_pct"] == 50.0


def test_everything_down_is_one_stated_error(monkeypatch):
    def boom(*_a):
        raise OSError("down")
    _patch(monkeypatch, sse=boom, szse=boom)
    assert es.collect("2026-11-22") == {"error": "OSError: down"}


def test_too_little_price_history_is_an_error(monkeypatch):
    monkeypatch.setattr(es, "trading_dates", lambda today: DATES[:3])
    assert "error" in es.collect("2026-11-22")


# --- report.md -------------------------------------------------------------

def _report(tmp_path, etf):
    import report_generator
    data = {"strategy_pool": {"stocks": []}}
    if etf is not None:
        data["etf_shares"] = etf
    return report_generator.generate_report_md(
        "2026-11-22", data, {}, output_dir=tmp_path).read_text(encoding="utf-8")


def test_report_table_shows_shares_changes_and_holder_share(tmp_path):
    body = _report(tmp_path, {
        "asof": "2026-11-20", "holder_asof": "2025-12-31", "long_window": 5,
        "rows": [
            {"code": "510050", "name": "上证50ETF华夏", "exchange": "SH", "huijin_pct": 86.05,
             "asof": "2026-11-20", "shares_wan": 2413417.0, "chg1_pct": 3.2, "chg_long_pct": 48.99},
            {"code": "159919", "name": "沪深300ETF嘉实", "exchange": "SZ", "huijin_pct": 86.97,
             "asof": "2026-11-19", "shares_wan": 1618671.66, "chg1_pct": None, "chg_long_pct": -1.5},
            {"code": "159915", "name": "创业板ETF易方达", "exchange": "SZ", "huijin_pct": 54.03,
             "error": "OSError: szse down"}]})
    assert "截至 **2026-11-20**" in body
    assert "| 510050 上证50ETF华夏 | 241.34 | +3.20% | +48.99% | 86% |" in body
    assert "| 159919 沪深300ETF嘉实 | 161.87（2026-11-19） | — | -1.50% | 87% |" in body
    assert "| 159915 创业板ETF易方达 | ⚠️ OSError: szse down | — | — | 54% |" in body
    assert "None" not in body


def test_report_states_a_failed_fetch(tmp_path):
    assert "⚠️ 数据不可用: OSError: down" in _report(tmp_path, {"error": "OSError: down"})


def test_report_has_no_section_for_runs_without_the_artifact(tmp_path):
    assert "宽基ETF份额" not in _report(tmp_path, None)
