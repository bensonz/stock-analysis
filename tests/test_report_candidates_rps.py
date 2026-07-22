"""RPS>95 stocks are actionable Sweet Spot names, not a Wait List.

Locks in the strategy change: RPS has no upper cap — the sole "too extended"
guard is the MA-distance check (Rule 2b). A high-RPS stock whose price sits
near/below its MAs must land in Sweet Spot, and there must be no Wait List.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import report_generator


def _pool(*stocks):
    return {"strategy_pool": {"stocks": list(stocks)}}


def _stock(code, name, rps120, ma5, ma10, ma20):
    return {
        "code": code, "name": name, "rps120": rps120, "rps60": rps120,
        "dist_ma5_pct": ma5, "dist_ma10_pct": ma10, "dist_ma20_pct": ma20,
    }


def _render(tmp_path, data):
    out = report_generator.generate_candidates_md("2026-07-22", data, output_dir=tmp_path)
    return out.read_text(encoding="utf-8")


def test_rps_over_95_ma_pass_is_sweet_spot(tmp_path):
    # 华盛昌-like: RPS=100 but price sits below its MAs -> not extended -> buyable.
    data = _pool(_stock("002980", "华盛昌", 100, -1.1, -4.8, -11.5))
    text = _render(tmp_path, data)

    assert "## Sweet Spot (1)" in text
    assert "002980" in text
    assert "Wait List" not in text          # the section is gone entirely
    assert "⏳ >95" not in text              # and so is the badge
    assert "✅ PASS" in text                 # >95 now reads as a normal pass


def test_rps_over_95_still_blocked_by_ma_extension(tmp_path):
    # High RPS does NOT bypass Rule 2b: spiked far above MA5 -> fails, not Sweet Spot.
    data = _pool(_stock("000001", "OVEREXT", 99, 8.0, 9.0, 3.0))
    text = _render(tmp_path, data)

    assert "❌ MA5" in text
    assert "## Sweet Spot" not in text
    assert "Wait List" not in text


def test_mixed_pool_groups_all_ma_passers_together(tmp_path):
    # An 85-RPS and a 96-RPS name that both pass MA share the same Sweet Spot.
    data = _pool(
        _stock("600000", "MID", 85, 1.0, 2.0, 3.0),
        _stock("000703", "恒逸石化", 96, 3.2, 3.4, 2.9),
    )
    text = _render(tmp_path, data)

    assert "## Sweet Spot (2)" in text
    assert "600000" in text and "000703" in text
    assert "Wait List" not in text
