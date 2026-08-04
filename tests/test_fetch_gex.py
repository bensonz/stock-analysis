"""Tests for the GEX advisory feed (2026-08-04).

Pure-logic — the backend is monkeypatched. The feed is Tier-2 read-only.

Semantics pinned here (corrected same day by the user): the regime label
keys off the SIGN OF NET GEX — the backend's direct measurement. The
flip_point is the strike-profile zero-crossing, a structural landmark;
deriving "negative gamma" from spot<flip contradicted the backend's own
positive net GEX and was wrong.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_gex


RAW = {
    "underlying": "510050", "expiry_month": "2608", "spot": 2.983,
    "flip_point": 3.0410717, "call_wall": 3.1, "put_wall": 3.0,
    "total_net_gex": 2.63e8, "captured_at": "2026-08-04T03:30:00Z",
}


def test_regression_positive_net_gex_below_flip_is_NOT_negative_gamma():
    # The exact live case the user caught: spot below the profile zero-
    # crossing while dealers are net LONG gamma. Regime must say positive.
    s = fetch_gex.read_state(RAW)
    assert s["regime"] == "净正gamma(压制倾向)"
    assert s["spot_vs_flip"] == "剖面零轴下方(put-gamma主导区)"
    assert s["dist_to_flip_pct"] == -1.91


def test_negative_net_gex_is_amplification_regime():
    s = fetch_gex.read_state({**RAW, "total_net_gex": -5e7, "spot": 3.20})
    assert s["regime"] == "净负gamma(放大倾向)"
    assert s["spot_vs_flip"] == "剖面零轴上方(call-gamma主导区)"


def test_read_state_missing_fields_returns_none():
    assert fetch_gex.read_state({**RAW, "flip_point": None}) is None
    assert fetch_gex.read_state({**RAW, "total_net_gex": None}) is None


def test_overall_all_net_positive_below_flip_keeps_positive_reading():
    states = [fetch_gex.read_state(RAW) for _ in range(5)]
    o = fetch_gex.overall_reading(states)
    assert o["signal"] == "全面净正gamma"
    assert o["net_negative"] == "0/5"
    assert o["below_flip"] == "5/5"
    assert "不改变当前压制判读" in o["implication"]


def test_overall_all_net_negative():
    states = [fetch_gex.read_state({**RAW, "total_net_gex": -1e8})
              for _ in range(3)]
    o = fetch_gex.overall_reading(states)
    assert o["signal"] == "全面净负gamma"
    assert o["net_negative"] == "3/3"


def test_overall_empty():
    assert fetch_gex.overall_reading([])["signal"] == "无数据"


def test_fetch_all_degrades_when_backend_down(monkeypatch):
    monkeypatch.setattr(fetch_gex, "fetch_gex", lambda code: None)
    out = fetch_gex.fetch_all()
    assert out["etf_gex_data"] == []
    assert "error" in out
    assert out["overall"]["signal"] == "无数据"


def test_fetch_all_shape(monkeypatch):
    monkeypatch.setattr(fetch_gex, "fetch_gex",
                        lambda code: {**RAW, "underlying": code})
    out = fetch_gex.fetch_all()
    assert len(out["etf_gex_data"]) == 5
    assert out["overall"]["signal"] == "全面净正gamma"
    assert "api/history/gex" in out["source"]
    assert all(s["name"] for s in out["etf_gex_data"])
