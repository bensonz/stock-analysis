"""data_collector's iFinD paths: position prices, breadth, sectors, indices.

The contract these must not break: `market.json` and `prices.json` keep the
exact shapes the prompt, report and contracts already expect. iFinD is a faster
and more reliable source, not a new schema — every function here has a sina
counterpart it must be drop-in compatible with.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import data_collector as dc
import ifind_client


class _FakeClient:
    def __init__(self, real_time=None, history=None, basic=None):
        self._real_time = real_time or []
        self._history = history or []
        self._basic = basic or []
        self.data_vol = 0

    def real_time(self, codes, indicators, **kw):
        return self._real_time

    def history_quotation(self, codes, indicators, beg, end, **kw):
        return self._history

    def basic_data(self, codes, indipara, **kw):
        self.last_indipara = indipara
        return self._basic


def _install(monkeypatch, client):
    monkeypatch.setattr(ifind_client, "is_available", lambda: True)
    monkeypatch.setattr(ifind_client, "get_client", lambda: client)
    return client


# ---------------------------------------------------------------------------
# Position prices
# ---------------------------------------------------------------------------


def _rt(thscode, latest=11.6, prev=11.5, volume=994881, stamp="2026-08-25 16:01:08"):
    return {"thscode": thscode, "time": [stamp],
            "table": {"latest": [latest], "open": [11.5], "high": [11.7],
                      "low": [11.4], "preClose": [prev], "volume": [volume],
                      "amount": [1.15e9]}}


def test_position_prices_shape_matches_sina_contract(monkeypatch):
    _install(monkeypatch, _FakeClient(real_time=[_rt("000001.SZ")]))

    out = dc._fetch_position_prices_ifind([{"code": "000001", "name": "平安银行"}])

    assert set(out["000001"]) == {
        "code", "name", "date", "price", "open", "high", "low",
        "prev_close", "change_pct", "volume", "amount", "source"}
    assert out["000001"]["source"] == "ifind"
    assert out["000001"]["name"] == "平安银行"


def test_position_prices_keep_realtime_volume_in_lots(monkeypatch):
    """real_time is already 手 — dividing would be a 100x error."""
    _install(monkeypatch, _FakeClient(real_time=[_rt("000001.SZ", volume=994881)]))

    out = dc._fetch_position_prices_ifind([{"code": "000001", "name": "x"}])

    assert out["000001"]["volume"] == 994881


def test_position_prices_change_pct_computed_from_prev_close(monkeypatch):
    _install(monkeypatch, _FakeClient(real_time=[_rt("000001.SZ", latest=11.0, prev=10.0)]))

    out = dc._fetch_position_prices_ifind([{"code": "000001", "name": "x"}])

    assert out["000001"]["change_pct"] == 10.0


def test_position_prices_skip_suspended(monkeypatch):
    _install(monkeypatch, _FakeClient(real_time=[_rt("000001.SZ", latest=0)]))

    assert dc._fetch_position_prices_ifind([{"code": "000001", "name": "x"}]) == {}


def test_position_prices_empty_when_unconfigured(monkeypatch):
    monkeypatch.setattr(ifind_client, "is_available", lambda: False)

    assert dc._fetch_position_prices_ifind([{"code": "000001", "name": "x"}]) == {}


def test_position_prices_degrade_on_error(monkeypatch):
    class _Boom:
        data_vol = 0

        def real_time(self, *a, **k):
            raise RuntimeError("down")

    _install(monkeypatch, _Boom())

    assert dc._fetch_position_prices_ifind([{"code": "000001", "name": "x"}]) == {}


# ---------------------------------------------------------------------------
# Breadth / sectors
# ---------------------------------------------------------------------------


def _changes(monkeypatch, mapping, date="2026-08-25"):
    monkeypatch.setattr(dc, "_ifind_universe_changes", lambda d=None: (mapping, date))


def test_breadth_counts_by_sign(monkeypatch):
    _changes(monkeypatch, {"a": 1.5, "b": -2.0, "c": 0.0, "d": 0.3})

    assert dc._fetch_breadth_ifind() == {"up": 2, "down": 1, "flat": 1, "total": 4}


def test_breadth_none_when_universe_unavailable(monkeypatch):
    monkeypatch.setattr(dc, "_ifind_universe_changes", lambda d=None: None)

    assert dc._fetch_breadth_ifind() is None


def test_sectors_average_by_industry_worst_first(monkeypatch):
    _changes(monkeypatch, {"a": 3.0, "b": 1.0, "c": -2.0, "d": -4.0})
    monkeypatch.setattr(dc, "_load_sw_industry_map",
                        lambda codes, date: {"a": "医药生物", "b": "医药生物",
                                             "c": "银行", "d": "银行"})

    out = dc._fetch_sectors_ifind()

    assert out["top5"][0] == {"板块名称": "医药生物", "涨跌幅": 2.0, "个股数": 2}
    assert out["bottom5"][0]["板块名称"] == "银行", "bottom5 is worst-first"


def test_sectors_none_when_membership_missing(monkeypatch):
    """No membership must not silently yield zero sectors as a valid answer."""
    _changes(monkeypatch, {"a": 3.0})
    monkeypatch.setattr(dc, "_load_sw_industry_map", lambda codes, date: {})

    assert dc._fetch_sectors_ifind() is None


def test_sw_industry_uses_level_then_date_param_order(monkeypatch, tmp_path):
    """Reversed params return "" instead of erroring — pin the order."""
    client = _install(monkeypatch, _FakeClient(basic=[
        {"thscode": "600519.SH",
         "table": {"ths_the_sw_industry_stock": ["食品饮料"]}}]))
    monkeypatch.setattr(dc, "SW_INDUSTRY_CACHE", tmp_path / "sw.json")

    out = dc._load_sw_industry_map(["600519"], "2026-08-25")

    assert out == {"600519": "食品饮料"}
    assert client.last_indipara[0]["indiparams"] == ["1", "2026-08-25"], \
        "must be [level, date] — the reverse silently returns empty strings"


def test_sw_industry_cache_is_reused(monkeypatch, tmp_path):
    cache = tmp_path / "sw.json"
    cache.write_text(json.dumps({"fetched": "2026-08-25",
                                 "map": {"600519": "食品饮料"}}), encoding="utf-8")
    monkeypatch.setattr(dc, "SW_INDUSTRY_CACHE", cache)
    monkeypatch.setattr(ifind_client, "get_client",
                        lambda: pytest.fail("cache should have been used"))

    assert dc._load_sw_industry_map(["600519"], "2026-08-25") == {"600519": "食品饮料"}


def test_sw_industry_stale_cache_is_refetched(monkeypatch, tmp_path):
    cache = tmp_path / "sw.json"
    cache.write_text(json.dumps({"fetched": "2020-01-01",
                                 "map": {"600519": "旧行业"}}), encoding="utf-8")
    monkeypatch.setattr(dc, "SW_INDUSTRY_CACHE", cache)
    _install(monkeypatch, _FakeClient(basic=[
        {"thscode": "600519.SH", "table": {"ths_the_sw_industry_stock": ["食品饮料"]}}]))

    assert dc._load_sw_industry_map(["600519"], "2026-08-25") == {"600519": "食品饮料"}


# ---------------------------------------------------------------------------
# Indices
# ---------------------------------------------------------------------------


def test_indices_shape_matches_sina_contract(monkeypatch):
    _install(monkeypatch, _FakeClient(real_time=[
        {"thscode": "000001.SH", "time": ["2026-08-25 15:30:00"],
         "table": {"latest": [3889.4449], "preClose": [3882.0079]}}]))

    out = dc._fetch_indices_ifind()

    assert out["上证指数"] == {"code": "sh000001", "close": 3889.445,
                              "change_pct": 0.19, "date": "2026-08-25"}


def test_indices_empty_when_unconfigured(monkeypatch):
    monkeypatch.setattr(ifind_client, "is_available", lambda: False)

    assert dc._fetch_indices_ifind() == {}
