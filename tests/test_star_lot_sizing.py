"""STAR Market (688xxx) 200-share lots — sizing, honest errors, and the gate.

2026-08-17: the pipeline decided to buy 安集科技 688019 @¥248.20 with ¥637,972
deployable. `open_position` refused it as "Insufficient deployable cash for
minimum lot" — false; the lot cost ¥49,640 and cash was 13x that. The real
constraint was the 7% *request* (¥44,658), while the lot was 5.01% of equity
against a 10% *cap*. Five opens had died this way, every one a 688 code.

report.md still printed it under 今日开仓 with entry/stop/target and "新开仓: 1只",
and every gate passed.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import contracts
import position_manager as pm
import report_generator as rg


def test_star_lot_size_is_200():
    assert pm._lot_size_for_code("688019") == 200
    assert pm._lot_size_for_code("688019.SH") == 200
    assert pm._lot_size_for_code("600160") == 100
    # the rounding that produced 0 shares from 179
    assert pm._round_down_to_lot(179, "688019") == 0
    assert pm._round_down_to_lot(200, "688019") == 200


def _open(monkeypatch, tmp_path, *, code, price, alloc, deployable, equity,
          max_pos_pct=10, min_cash_value=0.0):
    """Drive open_position with a synthetic portfolio, writing to a temp dir."""
    monkeypatch.setattr(pm, "TRACKING_DIR", tmp_path)
    monkeypatch.setattr(pm, "load_portfolio_config", lambda: {
        "starting_capital": 1000000, "max_positions": 10,
        "max_position_pct": max_pos_pct, "min_cash_pct": 0})
    monkeypatch.setattr(pm, "load_active_positions", lambda: [])
    monkeypatch.setattr(pm, "build_positions_snapshot", lambda *a, **k: {
        "portfolio": {"cash": deployable, "deployableCash": deployable,
                      "minCashValue": min_cash_value, "totalEquity": equity}})
    monkeypatch.setattr(pm, "regenerate_positions_json", lambda *a, **k: None)
    return pm.open_position({
        "code": code, "name": "测试", "entryPrice": price,
        "stopLoss": round(price * 0.95, 2), "targetPrice": round(price * 1.15, 2),
        "allocation_pct": alloc, "entryDate": "2026-08-17"})


def test_the_real_688019_case_now_opens(monkeypatch, tmp_path):
    """7% of 637,972 buys 179sh; the lot is 200sh = 5.01% of equity, cap is 10%."""
    _open(monkeypatch, tmp_path, code="688019", price=248.20, alloc=7,
          deployable=637972.00, equity=990272.00)
    pos = json.loads((tmp_path / "688019.json").read_text(encoding="utf-8"))
    assert pos["shares"] == 200
    assert pos["allocatedCapital"] == 49640.0
    assert 49640.0 / 990272.0 * 100 < 10        # comfortably inside the cap


def test_round_up_is_refused_when_it_breaches_the_position_cap(monkeypatch, tmp_path):
    """Rounding up is a courtesy, not a licence to blow through max_position_pct."""
    try:
        _open(monkeypatch, tmp_path, code="688019", price=248.20, alloc=1,
              deployable=637972.00, equity=990272.00, max_pos_pct=3)
    except ValueError as e:
        assert "max_position_pct" in str(e) and "49640" in str(e)
    else:
        raise AssertionError("should have refused: lot is 5.01% against a 3% cap")


def test_round_up_is_refused_when_cash_cannot_cover_a_lot(monkeypatch, tmp_path):
    try:
        _open(monkeypatch, tmp_path, code="688019", price=248.20, alloc=50,
              deployable=30000.00, equity=990272.00)
    except ValueError as e:
        msg = str(e)
        assert "exceeds deployable cash" in msg
        assert "Insufficient deployable cash for minimum lot" not in msg  # the old lie
    else:
        raise AssertionError("should have refused: one lot costs more than cash")


def test_round_up_respects_the_min_cash_reserve(monkeypatch, tmp_path):
    try:
        _open(monkeypatch, tmp_path, code="688019", price=248.20, alloc=1,
              deployable=60000.00, equity=990272.00, min_cash_value=50000.0)
    except ValueError as e:
        assert "min cash reserve" in str(e)
    else:
        raise AssertionError("should have refused: lot would eat the reserve")


def test_normal_100_lot_stock_is_unaffected(monkeypatch, tmp_path):
    _open(monkeypatch, tmp_path, code="600160", price=41.20, alloc=3,
          deployable=637972.00, equity=990272.00)
    pos = json.loads((tmp_path / "600160.json").read_text(encoding="utf-8"))
    assert pos["shares"] == 400          # 3% = 19,139 → 464sh → 400


# ── Gate 3: intent vs reality ──

def _log(actions):
    return {"actions": actions, "post_apply_rule_violations": {}}


def test_gate3_hard_fails_when_an_intended_open_vanishes(monkeypatch):
    monkeypatch.setattr(contracts, "_check_position_file_consistency",
                        lambda *a, **k: None)
    g = contracts.validate_phase3_gate(
        "2026-08-17", _log([]), {},
        decisions={"new_positions": [{"code": "688019", "name": "安集科技"}]})
    assert not g.passed
    assert any("neither opened nor skipped" in f for f in g.hard_fails)


def test_gate3_soft_warns_when_the_skip_is_explained(monkeypatch):
    monkeypatch.setattr(contracts, "_check_position_file_consistency",
                        lambda *a, **k: None)
    g = contracts.validate_phase3_gate(
        "2026-08-17",
        _log(["SKIP OPEN 688019: one lot exceeds max_position_pct"]), {},
        decisions={"new_positions": [{"code": "688019", "name": "安集科技"}]})
    assert g.passed                                    # explained → not a blocker
    assert any("688019" in w for w in g.soft_warns)


def test_gate3_is_quiet_when_the_open_actually_happened(monkeypatch):
    monkeypatch.setattr(contracts, "_check_position_file_consistency",
                        lambda *a, **k: None)
    g = contracts.validate_phase3_gate(
        "2026-08-17", _log(["OPEN 688019 @ 248.2"]), {},
        decisions={"new_positions": [{"code": "688019", "name": "安集科技"}]})
    assert g.passed and not any("688019" in w for w in g.soft_warns)


# ── Report: intent must not read as fact ──

def test_report_does_not_print_a_blocked_candidate_as_a_holding(tmp_path):
    decisions = {"new_positions": [
        {"code": "688019", "name": "安集科技", "entry_price": 248.2,
         "stop": 235.79, "target": 285.0, "thesis": "电子化学品龙头",
         "_not_opened": "one lot exceeds max_position_pct 3%"},
        {"code": "600160", "name": "巨化股份", "entry_price": 41.2,
         "thesis": "制冷剂长协涨价"},
    ], "position_decisions": [], "skip_list": []}
    path = rg.generate_report_md("2026-08-17", {}, decisions, output_dir=tmp_path)
    md = path.read_text(encoding="utf-8")

    # split on top-level headings only — "### 1. …" also contains "##"
    def section(title):
        body = md.split(f"## {title}\n")[1]
        return body.split("\n## ")[0]

    opened = section("今日开仓")
    assert "巨化股份" in opened and "安集科技" not in opened
    assert "## ⚠️ 想开但没开成" in md
    assert "安集科技" in section("⚠️ 想开但没开成")
    assert "- 新开仓: 1只" in md                        # not 2
    assert "想开但被执行阶段拦下: 1只" in md
