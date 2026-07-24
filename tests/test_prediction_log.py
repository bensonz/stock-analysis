"""Prediction-scoring loop: log → resolve → score.

Every probability the system emits is a bet; these tests lock the ledger
mechanics: dedupe, early drawdown resolution, horizon-elapsed resolution,
earnings resolution from disclosure tables, manual-bet expiry flagging,
Brier/calibration math, and the deep_report extraction/auto-build glue.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import deep_report
import prediction_log


@pytest.fixture()
def ledger(tmp_path):
    return tmp_path / "predictions.jsonl"


def _drawdown_rec(code="000001", made="2026-01-05", entry=100.0, h=3, dd=15):
    return {"id": f"{code}-{made}-x", "code": code, "made": made,
            "kind": "price_drawdown", "params": {"horizon_sessions": h, "drawdown_pct": dd},
            "entry_adj": entry, "p": 0.39, "source": "base_rate:extended_high_momentum",
            "status": "open"}


def _mini_db(tmp_path, closes_by_date, code="000001"):
    """One-stock DB. Coverage floor is total_codes*0.9 = 0 for 1 code — all dates covered."""
    db = tmp_path / "p.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE daily_prices (code TEXT, date TEXT, close REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS adj_factors (code TEXT, date TEXT, factor REAL, PRIMARY KEY(code,date))")
    for d, c in closes_by_date.items():
        conn.execute("INSERT INTO daily_prices VALUES (?,?,?)", (code, d, c))
    conn.commit()
    conn.close()
    return str(db)


def test_append_dedupes_by_id(ledger):
    r = _drawdown_rec()
    assert prediction_log.append([r], ledger) == 1
    assert prediction_log.append([r, _drawdown_rec(made="2026-01-06")], ledger) == 1
    assert len(prediction_log.load_all(ledger)) == 2


def test_drawdown_resolves_early_on_hit(ledger, tmp_path):
    db = _mini_db(tmp_path, {"2026-01-05": 100, "2026-01-06": 95, "2026-01-07": 84})
    prediction_log.append([_drawdown_rec(h=10)], ledger)  # horizon far from elapsed
    prediction_log.resolve_due(today="2026-01-08", path=ledger, db_path=db)
    rec = prediction_log.load_all(ledger)[0]
    assert rec["status"] == "resolved"
    assert rec["outcome"] == 1                      # 84 <= 85 → hit, resolved EARLY
    assert rec["brier"] == round((0.39 - 1) ** 2, 4)


def test_drawdown_resolves_zero_after_horizon(ledger, tmp_path):
    db = _mini_db(tmp_path, {"2026-01-05": 100, "2026-01-06": 95,
                             "2026-01-07": 96, "2026-01-08": 97})
    prediction_log.append([_drawdown_rec(h=3)], ledger)
    prediction_log.resolve_due(today="2026-01-09", path=ledger, db_path=db)
    rec = prediction_log.load_all(ledger)[0]
    assert rec["status"] == "resolved"
    assert rec["outcome"] == 0                      # 3 sessions elapsed, never hit
    assert rec["brier"] == round(0.39 ** 2, 4)


def test_drawdown_stays_open_before_horizon(ledger, tmp_path):
    db = _mini_db(tmp_path, {"2026-01-05": 100, "2026-01-06": 95})
    prediction_log.append([_drawdown_rec(h=5)], ledger)
    prediction_log.resolve_due(today="2026-01-07", path=ledger, db_path=db)
    assert prediction_log.load_all(ledger)[0]["status"] == "open"


def test_earnings_decel_resolves_from_yjbb(ledger, monkeypatch):
    import pandas as pd
    import fundamentals

    monkeypatch.setattr(fundamentals, "_load_table", lambda k, p: pd.DataFrame(
        {"股票代码": ["002245"], "净利润-同比增长": [12.0]}) if p == "20260930" else None)
    prediction_log.append([{
        "id": "002245-2026-07-24-growth", "code": "002245", "made": "2026-07-24",
        "kind": "earnings_decel", "params": {"target_period": "20260930", "decel_below_pct": 20},
        "p": 0.276, "source": "base_rate:growth_persistence", "status": "open"}], ledger)
    prediction_log.resolve_due(today="2026-10-31", path=ledger, db_path="/nonexistent")
    rec = prediction_log.load_all(ledger)[0]
    assert rec["status"] == "resolved" and rec["outcome"] == 1  # 12% < 20% → decelerated


def test_manual_flags_needs_review_at_expiry(ledger):
    prediction_log.append([{
        "id": "x-j1", "code": "x", "made": "2026-07-24", "kind": "manual",
        "event": "价格战", "p_low": 0.15, "p_high": 0.40,
        "expires": "2026-08-01", "source": "judgment", "status": "open"}], ledger)
    prediction_log.resolve_due(today="2026-09-01", path=ledger, db_path="/nonexistent")
    assert prediction_log.load_all(ledger)[0]["status"] == "needs_review"


def test_score_brier_and_calibration(ledger):
    recs = [dict(_drawdown_rec(made=f"2026-01-0{i}"), id=f"r{i}") for i in range(1, 5)]
    for i, (p, outcome) in enumerate(((0.39, 1), (0.39, 0), (0.75, 1), (0.25, 0)), 0):
        recs[i]["p"] = p
        recs[i]["status"] = "resolved"
        recs[i]["outcome"] = outcome
        recs[i]["brier"] = round((p - outcome) ** 2, 4)
    recs[2]["source"] = "judgment"
    prediction_log.append(recs, ledger)
    s = prediction_log.score(ledger)
    assert s["n_resolved"] == 4
    assert s["brier_judgment_sourced"] == round(0.25 ** 2, 4)
    b2040 = next(b for b in s["calibration"] if b["stated_pct"] == "20-40")
    assert b2040["n"] == 3 and b2040["observed_pct"] == round(1 / 3 * 100, 1)


def test_extract_predictions_block_strips_and_parses():
    text = ("# 报告\n\n正文数字 3.5亿元〖内部数据〗\n\n"
            "```predictions\n"
            '[{"event": "价格战", "p_low": 0.15, "p_high": 0.4, "expires": "2027-04-30"}]\n'
            "```\n")
    recs, stripped = deep_report.extract_predictions_block(text)
    assert len(recs) == 1 and recs[0]["event"] == "价格战"
    assert "predictions" not in stripped and "0.15" not in stripped
    assert "正文数字" in stripped
    # malformed json → no records, block still stripped
    bad, stripped2 = deep_report.extract_predictions_block("x\n```predictions\nnope\n```\n")
    assert bad == [] and "nope" not in stripped2


def test_build_auto_predictions_gates_on_subject_state(monkeypatch):
    import base_rates

    monkeypatch.setattr(base_rates, "stock_in_config", lambda c, cfg: {
        "in_class": cfg == "extended_high_momentum",
        "as_of": "2026-07-22", "close_adj": 17.02})
    data = {"code6": "002245", "base_rates": {
        "extended_high_momentum_60d_15pct": {"config": "extended_high_momentum", "frequency_pct": 38.99},
        "high_momentum_healthy_60d_15pct": {"config": "high_momentum_healthy", "frequency_pct": 42.27},
    }}
    preds = deep_report.build_auto_predictions(data, made="2026-07-24")
    assert len(preds) == 1                          # healthy-config: subject not in class
    p = preds[0]
    assert p["kind"] == "price_drawdown" and p["p"] == 0.3899
    assert p["params"] == {"horizon_sessions": 60, "drawdown_pct": 15}
    assert p["entry_adj"] == 17.02


def test_growth_target_period_from_forecast():
    data = {"fundamentals": {
        "latest_report": {"period": "2026一季报", "net_profit_yoy_pct": 38.14},
        "annual_report": {"period": "2025年报", "net_profit_yoy_pct": 45.66},
        "forecast": [{"period": "2026H1", "change_pct": 53.1}],
    }}
    # H1 forecast (20260630) is the latest qualifying period → test Q3 decel
    assert deep_report._growth_target_period(data) == "20260930"
    assert deep_report._growth_target_period({"fundamentals": {
        "latest_report": {"period": "2026一季报", "net_profit_yoy_pct": 10.0}}}) is None
