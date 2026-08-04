"""Tests for the GEX advisory feed (2026-08-04).

Pure-logic — the backend is monkeypatched. The feed is Tier-2 read-only:
these tests pin the state derivation and graceful degradation, not any
trading rule (there is none by design).
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


def test_read_state_below_flip_is_negative_gamma():
    s = fetch_gex.read_state(RAW)
    assert s["regime"] == "负gamma放大区"
    assert s["dist_to_flip_pct"] == -1.91
    assert s["flip_point"] == 3.041


def test_read_state_above_flip_is_positive_gamma():
    s = fetch_gex.read_state({**RAW, "spot": 3.20})
    assert s["regime"] == "正gamma压制区"
    assert s["dist_to_flip_pct"] > 0


def test_read_state_missing_flip_returns_none():
    assert fetch_gex.read_state({**RAW, "flip_point": None}) is None


def test_overall_reading_all_below():
    states = [{"regime": "负gamma放大区"}] * 5
    o = fetch_gex.overall_reading(states)
    assert o["signal"] == "全面负gamma"
    assert o["below_flip"] == "5/5"


def test_overall_reading_mixed_and_empty():
    o = fetch_gex.overall_reading(
        [{"regime": "负gamma放大区"}, {"regime": "正gamma压制区"},
         {"regime": "正gamma压制区"}])
    assert o["signal"] == "偏正gamma"
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
    assert out["overall"]["signal"] == "全面负gamma"
    assert "api/history/gex" in out["source"]
    assert all(s["name"] for s in out["etf_gex_data"])
