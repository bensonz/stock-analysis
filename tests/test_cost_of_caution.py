"""cost_of_caution — pricing skipped entries under real exit rules. Offline."""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import cost_of_caution as coc

DAYS = [f"2026-07-{d:02d}" for d in range(1, 16)]


def _panels(series: dict, opens: dict | None = None):
    c = pd.DataFrame(series, index=DAYS)
    o = pd.DataFrame(opens, index=DAYS) if opens else c.copy()
    return {"closes": c, "opens": o}


def _runs(tmp_path, skips_by_run: dict):
    """skips_by_run: {(date, slot): [skip dicts]} -> a fake runs dir."""
    for (d, slot), skips in skips_by_run.items():
        out = tmp_path / d / slot
        out.mkdir(parents=True)
        (out / "response.json").write_text(
            json.dumps({"skip_list": skips}, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_simulate_applies_hard_stop_not_naive_return():
    # Skipped 7/1. Path: entry 7/2 @10, dives to 9.2 (-8%), recovers to 11.
    # Naive says +10% "missed win"; honest replay stops out around -8%.
    p = _panels({"600000": [10, 10, 9.2, 9.2, 10, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11]})
    sim = coc.simulate_if_taken("600000", "2026-07-01", p)
    assert sim["exit_kind"] == "hard_stop"
    assert sim["ret_pct"] < -5


def test_simulate_early_stop_and_winner_paths():
    p = _panels({
        # -3.5% on session 2 → early stop
        "000001": [10, 10, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6, 9.6],
        # clean runner → horizon exit, positive
        "000002": [10, 10, 10.2, 10.4, 10.6, 10.8, 11, 11.2, 11.4, 11.6, 11.8, 12, 12, 12, 12],
    })
    early = coc.simulate_if_taken("000001", "2026-07-01", p)
    assert early["exit_kind"] == "early_stop" and early["sessions"] <= 3
    win = coc.simulate_if_taken("000002", "2026-07-01", p)
    assert win["exit_kind"] == "horizon" and win["ret_pct"] > 5


def test_t_plus_1_no_exit_on_entry_session():
    # Fills at the 7/2 OPEN of 10, and 7/2 itself closes -6%: T+1 forbids an
    # exit that same session; the stop fires on the NEXT session's close.
    p = _panels(
        {"600000": [10, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4]},
        opens={"600000": [10, 10, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4, 9.4]},
    )
    sim = coc.simulate_if_taken("600000", "2026-07-01", p)
    assert sim["exit_kind"] == "hard_stop"
    assert sim["sessions"] == 2


def test_collect_skips_dedupes_to_earliest(tmp_path):
    runs = _runs(tmp_path, {
        ("2026-07-02", "noon"): [{"code": "600000", "name": "甲", "reason": "板块冷"}],
        ("2026-07-03", "afternoon"): [{"code": "600000", "name": "甲", "reason": "板块仍冷"},
                                      {"code": "000002", "name": "乙", "reason": "恐慌 breadth 0.5"}],
    })
    skips = coc.collect_skips(days=30, today=date(2026, 7, 15), runs_dir=runs)
    assert len(skips) == 2
    jia = [s for s in skips if s["code"] == "600000"][0]
    assert jia["skip_date"] == "2026-07-02"          # earliest kept
    assert jia["bucket"] == "sector"
    assert [s for s in skips if s["code"] == "000002"][0]["bucket"] == "regime"


def test_reason_bucketing():
    assert coc.classify_reason("FOMC决议在即，事件风险窗口") == "event"
    assert coc.classify_reason("dist_ma5=7.2% 超限") == "stock"
    assert coc.classify_reason("完全没有理由") == "other"


def test_report_aggregates_and_verdicts(tmp_path):
    runs = _runs(tmp_path, {
        ("2026-07-01", "noon"): [
            {"code": "600000", "name": "跌股", "reason": "板块冷"},   # → hard stop
            {"code": "000002", "name": "涨股", "reason": "恐慌"},     # → +>5% winner
            {"code": "999999", "name": "无价", "reason": "板块冷"},   # → no data
        ],
    })
    p = _panels({
        "600000": [10, 10, 9.2, 9.2, 9.2, 9.2, 9.2, 9.2, 9.2, 9.2, 9.2, 9.2, 9.2, 9.2, 9.2],
        "000002": [10, 10, 10.5, 11, 11.5, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12],
    })
    rep = coc.report(days=30, today=date(2026, 7, 15), runs_dir=runs, panels=p)
    assert rep["n_skips"] == 3 and rep["n_scored"] == 2
    assert rep["verdicts"]["disaster_avoided"] == 1
    assert rep["verdicts"]["win_missed"] == 1
    # net = -(loss + win): the avoided loss offsets the missed win
    loss = [r for r in rep["skips"] if r["code"] == "600000"][0]["ret_pct"]
    win = [r for r in rep["skips"] if r["code"] == "000002"][0]["ret_pct"]
    assert abs(rep["net_savings_pct_sum"] - (-(loss + win))) < 1e-6
    assert rep["by_reason_bucket"]["sector"]["n"] == 1
