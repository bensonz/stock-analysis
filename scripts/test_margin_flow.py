"""Tests for margin_flow — per-stock 融资融券 trend fetcher.

Pure-parse/summary unit tests + a monkeypatched fetch-fallback test, mirroring the
tests/test_pricedb_eastmoney.py conventions. One live smoke test behind the
`integration` marker (skipped unless --run-integration).
"""

import pytest

import margin_flow


def _row(date, rzye, rzyezb=1.5, rzjme=0.0):
    return {"DATE": date, "SCODE": "601958", "SECNAME": "金钼股份",
            "RZYE": rzye, "RZYEZB": rzyezb, "RZJME": rzjme}


def test_margin_url_shape():
    url = margin_flow._margin_url("601958.SH", page_size=10)
    assert url.startswith(margin_flow.EASTMONEY_MARGIN_URL + "?")
    assert "reportName=RPTA_WEB_RZRQ_GGMX" in url
    assert "columns=DATE,SCODE,SECNAME,RZYE,RZYEZB,RZJME" in url  # literal commas kept
    assert "SCODE%3D%22601958%22" in url                          # bare 6-digit, quoted
    assert "pageSize=10" in url


def test_parse_margin_rows_guards_malformed():
    assert margin_flow._parse_margin_rows(None) == []
    assert margin_flow._parse_margin_rows({}) == []
    assert margin_flow._parse_margin_rows({"result": None}) == []
    assert margin_flow._parse_margin_rows({"result": {"data": "nope"}}) == []
    good = {"result": {"data": [_row("2026-07-14", 1.22e9), "junk"]}}
    rows = margin_flow._parse_margin_rows(good)
    assert len(rows) == 1 and rows[0]["RZYE"] == 1.22e9  # non-dict dropped


def test_summarize_none_on_empty():
    assert margin_flow.summarize_margin([]) is None
    assert margin_flow.summarize_margin([{"RZYE": None}]) is None


def test_summarize_deleveraging():
    # newest-first: balance falling, mostly net repayment -> deleveraging
    rows = [
        _row("2026-07-14", 12.20e8, 1.65, 268e4),
        _row("2026-07-13", 12.17e8, 1.70, -2804e4),
        _row("2026-07-10", 12.45e8, 1.72, -1209e4),
        _row("2026-07-09", 12.57e8, 1.69, -1944e4),
        _row("2026-07-08", 12.77e8, 1.82, -3187e4),
    ]
    s = margin_flow.summarize_margin(rows)
    assert s["rzye_yi"] == 12.2
    assert s["pct_float"] == 1.65
    assert s["chg5_pct"] == pytest.approx(-4.46, abs=0.05)
    assert s["net5_repay_days"] == 4
    assert s["signal"] == "deleveraging"


def test_summarize_adding():
    rows = [_row(f"2026-07-{14-i:02d}", (13.0 + (4 - i) * 0.2) * 1e8, 1.5, 500e4)
            for i in range(5)]  # newest highest -> balance rose across window
    s = margin_flow.summarize_margin(rows)
    assert s["chg5_pct"] >= 1
    assert s["signal"] == "adding"


def test_summarize_neutral():
    rows = [_row(f"2026-07-{14-i:02d}", 12.0e8, 1.5, 10e4) for i in range(5)]  # flat
    s = margin_flow.summarize_margin(rows)
    assert s["chg5_pct"] == 0.0
    assert s["signal"] == "neutral"


def test_fetch_margin_flow_swallows_errors(monkeypatch):
    def boom(url):
        raise RuntimeError("network down")
    monkeypatch.setattr(margin_flow, "_fetch_json", boom)
    assert margin_flow.fetch_margin_flow("601958") is None  # no raise


def test_fetch_margin_flow_happy_path(monkeypatch):
    payload = {"result": {"data": [
        _row("2026-07-14", 12.20e8, 1.65, 268e4),
        _row("2026-07-08", 12.77e8, 1.82, -3187e4),
    ]}}
    monkeypatch.setattr(margin_flow, "_fetch_json", lambda url: payload)
    s = margin_flow.fetch_margin_flow("601958.SH")
    assert s["rzye_yi"] == 12.2


@pytest.mark.integration
def test_margin_live():
    s = margin_flow.fetch_margin_flow("601958")
    assert isinstance(s, dict) and "rzye_yi" in s
