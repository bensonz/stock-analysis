"""RPS>95 stocks go to the Wait List, not Sweet Spot (the upper band restored).

Locks in the 2026-07-31 restoration of the original band design: sweet spot
is RPS 75-95 with the >95 overheated zone parked on a Wait List. The 7/22
removal of the cap ("high RPS = strongest, buyable") was falsified within
days: the rank-IC audit measured top-of-pool RPS as the WORST slice at every
horizon (docs/backtest/RESULTS.md), and the 98-99 RPS entries it admitted on
7/27-7/29 took the deepest losses. Rule 2b (MA distance) still guards price
extension separately — the two checks are different concerns.
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


def test_rps_over_95_ma_pass_goes_to_wait_list(tmp_path):
    # RPS=100, price at/below MAs: NOT price-extended, but relative strength
    # is overheated -> Wait List, awaiting pullback into the band.
    data = _pool(_stock("002980", "华盛昌", 100, -1.1, -4.8, -11.5))
    text = _render(tmp_path, data)

    assert "## Wait List (1)" in text
    assert "002980" in text
    assert "⏳ >95" in text
    assert "## Sweet Spot" not in text


def test_rps_over_95_still_blocked_by_ma_extension(tmp_path):
    # High RPS does NOT bypass Rule 2b: spiked far above MA5 -> fails outright.
    data = _pool(_stock("000001", "OVEREXT", 99, 8.0, 9.0, 3.0))
    text = _render(tmp_path, data)

    assert "❌ MA5" in text
    assert "## Sweet Spot" not in text
    assert "Wait List" not in text


def test_report_md_shows_model_from_llm_meta(tmp_path):
    import json
    run_dir = tmp_path / "run"
    out_dir = run_dir / "output"
    out_dir.mkdir(parents=True)
    (run_dir / "llm_meta.json").write_text(json.dumps({
        "provider": "openai", "primary_model": "deepseek-v4-pro",
        "decision_source": "DeepSeek V4 Pro primary",
        "input_tokens": 200784, "output_tokens": 7676,
    }), encoding="utf-8")
    out = report_generator.generate_report_md(
        "2026-07-24", {"market": {}}, {}, output_dir=out_dir)
    text = out.read_text(encoding="utf-8")
    assert "模型: deepseek-v4-pro（DeepSeek V4 Pro primary）" in text
    assert "200784+7676 tokens" in text


def test_report_md_no_meta_no_model_line(tmp_path):
    out = report_generator.generate_report_md(
        "2026-07-24", {"market": {}}, {}, output_dir=tmp_path)
    assert "模型:" not in out.read_text(encoding="utf-8")


def test_mixed_pool_splits_band_from_overheated(tmp_path):
    # An 85-RPS name lands in Sweet Spot; a 96-RPS name parks on the Wait List.
    data = _pool(
        _stock("600000", "MID", 85, 1.0, 2.0, 3.0),
        _stock("000703", "恒逸石化", 96, 3.2, 3.4, 2.9),
    )
    text = _render(tmp_path, data)

    assert "## Sweet Spot (1)" in text
    assert "600000" in text
    assert "## Wait List (1)" in text
    assert "000703" in text
