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


def test_read_state_without_net_gex_returns_none():
    """Regime cannot be inferred from anything else, so a row without it says
    nothing and must not pad a denominator."""
    assert fetch_gex.read_state({**RAW, "total_net_gex": None}) is None


def test_read_state_keeps_a_row_that_has_no_flip_point():
    """REVERSES this file's earlier assertion, which required flip_point and so
    pinned a real bug in place.

    On 2026-08-31 the backend returned all five underlyings; three came back
    with flip_point=None and net GEX of -74.8M, -2.8M and -18.8M. Requiring the
    flip point discarded exactly those three, leaving the two positive ones, and
    the report published 全面净正gamma (0/2 negative) when the truth across all
    five was 偏净负gamma (3/5) — the opposite reading, sent to the model.

    The correlation is what makes it dangerous: flip_point is a zero-crossing of
    the gamma profile, and the backend cannot locate one when the profile never
    crosses zero within the strike range — much likelier under strongly negative
    net gamma. So the absent field tracks the signal, and dropping on it
    silently deleted the amplifying half of the board.

    flip_point is descriptive: it feeds dist_to_flip_pct and spot_vs_flip and
    nothing else. Both go null; the regime survives.
    """
    s = fetch_gex.read_state({**RAW, "flip_point": None, "total_net_gex": -7.48e7})
    assert s is not None
    assert s["regime"] == "净负gamma(放大倾向)"
    assert s["flip_point"] is None and s["dist_to_flip_pct"] is None
    assert s["spot_vs_flip"] is None


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
