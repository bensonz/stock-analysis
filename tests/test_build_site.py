"""Tests for the static portfolio site generator (2026-08-06).

Pins the equity-series extraction rules: legacy + slotted run layouts,
latest-snapshot-of-the-day wins, broken/empty snapshots skipped.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_site as bs


def _snap(tmp, rel, time, equity, ret=None):
    path = tmp / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "snapshot_time": time,
        "positions_json": {
            "portfolio": {
                "startingCapital": 1000000,
                "totalEquity": equity,
                "totalReturnPct": ret,
                "positionsUsed": 2,
            }
        },
    }), encoding="utf-8")


def test_series_legacy_and_slotted_latest_wins(tmp_path):
    runs = tmp_path / "runs"
    # legacy layout day
    _snap(runs, "2026-03-05/input/positions_snapshot.json",
          "2026-03-05T15:35:00+08:00", 968982.0, -3.1)
    # slotted day: afternoon must beat noon
    _snap(runs, "2026-08-06/noon/input/positions_snapshot.json",
          "2026-08-06T11:35:00+08:00", 960000.0)
    _snap(runs, "2026-08-06/afternoon/input/positions_snapshot.json",
          "2026-08-06T15:35:00+08:00", 964319.0)
    series = bs.collect_equity_series(runs)
    assert [p["date"] for p in series] == ["2026-03-05", "2026-08-06"]
    assert series[1]["equity"] == 964319.0  # afternoon snapshot won


def test_output_postrun_snapshot_beats_input_prerun(tmp_path):
    # 2026-08-07: input/ (pre_run) carries the PREVIOUS close's marks — using
    # it made today's equity equal yesterday's (delta 0). output/ must win.
    runs = tmp_path / "runs"
    _snap(runs, "2026-08-07/noon/input/positions_snapshot.json",
          "2026-08-07T11:35:00+08:00", 972360.0)
    out = runs / "2026-08-07/noon/output/positions_snapshot.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "snapshot_time": "2026-08-07T11:45:02+08:00",
        "snapshot_type": "post_run",
        "positions_json": {"portfolio": {
            "startingCapital": 1000000, "totalEquity": 979412.0,
            "totalReturnPct": -2.06, "positionsUsed": 9}},
    }), encoding="utf-8")
    series = bs.collect_equity_series(runs)
    assert series[0]["equity"] == 979412.0
    assert series[0]["stype"] == "post_run"
    details = bs.collect_day_details(series, [])
    assert "pre" not in details["2026-08-07"]

    # a day with ONLY a pre_run snapshot gets the visible stale marker
    pre = runs / "2026-08-08/noon/input/positions_snapshot.json"
    pre.parent.mkdir(parents=True)
    pre.write_text(json.dumps({
        "snapshot_time": "2026-08-08T11:35:00+08:00",
        "snapshot_type": "pre_run",
        "positions_json": {"portfolio": {
            "startingCapital": 1000000, "totalEquity": 979412.0,
            "positionsUsed": 9}},
    }), encoding="utf-8")
    details = bs.collect_day_details(bs.collect_equity_series(runs), [])
    assert details["2026-08-08"]["pre"] == 1


def test_series_skips_broken_and_empty_snapshots(tmp_path):
    runs = tmp_path / "runs"
    bad = runs / "2026-04-01/input/positions_snapshot.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{not json", encoding="utf-8")
    empty = runs / "2026-04-02/input/positions_snapshot.json"
    empty.parent.mkdir(parents=True)
    empty.write_text(json.dumps({"snapshot_time": "t", "positions_json": {}}),
                     encoding="utf-8")
    _snap(runs, "2026-04-03/input/positions_snapshot.json",
          "2026-04-03T15:35:00+08:00", 1000500.0)
    series = bs.collect_equity_series(runs)
    assert [p["date"] for p in series] == ["2026-04-03"]


def test_inception_anchor_from_config(tmp_path):
    (tmp_path / "portfolio_config.json").write_text(json.dumps({
        "starting_capital": 1000000, "created": "2026-02-03"}), encoding="utf-8")
    p = bs.inception_point(tmp_path)
    assert p == {"date": "2026-02-03", "time": "", "equity": 1000000.0,
                 "ret_pct": 0.0, "positions": 0, "starting": 1000000,
                 "holdings": [], "synthetic": True}
    assert bs.inception_point(tmp_path / "nope") is None


def test_max_drawdown():
    series = [{"equity": e} for e in [100.0, 110.0, 99.0, 105.0]]
    stats = bs.compute_stats(series, [])
    assert stats["max_drawdown_pct"] == 10.0  # 110 → 99


def test_render_html_contains_data_and_no_external_resources(tmp_path):
    series = [{"date": "2026-08-06", "equity": 964319.0, "ret_pct": -3.57,
               "positions": 9, "starting": 1000000}]
    trades = [{"code": "600988", "name": "赤峰黄金", "entryDate": "2026-07-01",
               "exitDate": "2026-07-10", "holdingDays": 9, "returnPct": 5.5,
               "exitReason": "target_hit"}]
    html_out = bs.render_html(series, {"portfolio": {"totalEquity": 964319.0},
                                       "activePositions": []},
                              trades, bs.compute_stats(series, trades))
    assert "964319" in html_out
    assert "赤峰黄金" in html_out
    # self-contained: nothing loaded from the network at view time
    assert "<script src" not in html_out
    assert "<link" not in html_out
    assert "@import" not in html_out
    assert "胜率 100.0%" in html_out


def _manifest(runs, date, slot, started, status, gate_passed=True, hard=(), applied=True):
    d = runs / date / slot
    d.mkdir(parents=True, exist_ok=True)
    m = {"date": date, "slot": slot, "run_started_at": started, "status": status,
         "gates": {"phase3_to_phase4": {"passed": gate_passed, "hard_fails": list(hard)}}}
    if applied:
        m["phases"] = {"apply": {"status": "ok"}}
    (d / "manifest.json").write_text(json.dumps(m), encoding="utf-8")


def test_run_status_banner_only_on_failure(tmp_path, monkeypatch):
    # 7/20 and 8/14 both failed AFTER apply: books moved, commit and site
    # rebuild both skipped, page silently disagreed with reality.
    runs = tmp_path / "runs"
    monkeypatch.setattr(bs, "RUNS_DIR", runs)

    _manifest(runs, "2026-08-13", "afternoon", "2026-08-13T15:35:00+08:00", "degraded")
    assert bs.load_latest_run_status() is None          # healthy → silent

    # newest run failed — picked by run_started_at, never by slot name
    _manifest(runs, "2026-08-14", "afternoon", "2026-08-14T15:35:00+08:00", "failed",
              gate_passed=False, hard=["apply phase had errors: ERROR learnings"])
    st = bs.load_latest_run_status()
    assert st["date"] == "2026-08-14" and st["slot"] == "afternoon"
    assert st["applied"] is True
    assert "ERROR learnings" in st["reasons"][0]

    series = [{"date": "2026-08-14", "equity": 985708.0, "ret_pct": -1.43,
               "positions": 8, "starting": 1000000}]
    html_out = bs.render_html(series, {"portfolio": {"totalEquity": 985708.0},
                                       "activePositions": []},
                              [], bs.compute_stats(series, []), run_status=st)
    assert "最新一次运行未通过校验" in html_out
    assert "ERROR learnings" in html_out
    assert "下方数据已落盘，但该次运行未提交" in html_out

    # and no banner at all when the caller passes nothing
    clean = bs.render_html(series, {"portfolio": {"totalEquity": 985708.0},
                                    "activePositions": []},
                           [], bs.compute_stats(series, []))
    assert "最新一次运行未通过校验" not in clean


def test_holding_row_notes_cover_every_action_type(tmp_path):
    # Until 2026-08-14 the row tooltip read `if (a.a === "HOLD")`, so the
    # 91 SELL/OPEN/RAISE_STOP notes (of 255) silently had no hover — a row
    # that had just been acted on looked like it had nothing to say.
    series = [{"date": "2026-08-14", "equity": 985708.0, "ret_pct": -1.43,
               "positions": 8, "starting": 1000000}]
    html_out = bs.render_html(series, {"portfolio": {"totalEquity": 985708.0},
                                       "activePositions": []},
                              [], bs.compute_stats(series, []))
    assert 'if (a.note) rowNotes[a.c]' in html_out      # every action, not just HOLD
    assert '=== "HOLD"' not in html_out.split("rowNotes")[1][:200]
    assert 'id="rowtip"' in html_out                     # styled tooltip container
    assert "无逐仓决策记录" in html_out                    # missing notes stay explicit


def test_day_details_join(tmp_path):
    runs = tmp_path / "runs"
    _snap(runs, "2026-08-05/noon/input/positions_snapshot.json",
          "2026-08-05T11:35:00+08:00", 960000.0)
    _snap(runs, "2026-08-06/noon/input/positions_snapshot.json",
          "2026-08-06T11:35:00+08:00", 964319.0)
    summary = runs / "2026-08-06/noon/output/daily_summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps({"actions": [
        {"code": "002138", "name": "顺络电子", "action": "HOLD",
         "price": 48.2, "pnl_pct": 10.78, "note": "x" * 500},
        {"code": "603259", "name": "药明康德", "action": "OPEN",
         "price": 126.5, "pnl_pct": 0, "note": "开仓"},
    ]}), encoding="utf-8")
    series = bs.collect_equity_series(runs)
    trades = [{"code": "600988", "name": "赤峰黄金", "exitDate": "2026-08-06",
               "returnPct": -5.2, "exitReason": "stop_hit"}]
    lookup = {("603259", "2026-08-06"): {"sh": 800, "amt": 101200.0, "ap": 10}}
    details = bs.collect_day_details(series, trades, lookup)
    d = details["2026-08-06"]
    assert d["day_pnl"] == 4319.0            # vs previous real snapshot
    assert d["slot"] == "午盘"
    assert len(d["actions"]) == 2
    assert len(d["actions"][0]["note"]) == bs.NOTE_MAX  # truncated
    open_act = d["actions"][1]
    assert (open_act["sh"], open_act["amt"]) == (800, 101200.0)  # sizing joined
    assert "sh" not in d["actions"][0]       # HOLD rows untouched
    assert d["closed"][0]["c"] == "600988"
    assert details["2026-08-05"]["day_pnl"] is None  # no prior snapshot


def test_open_lookup_from_active_and_closed():
    active = {"activePositions": [
        {"code": "603259", "entryDate": "2026-07-31", "shares": 800,
         "allocatedCapital": 101200.0, "allocation_pct": 10}]}
    trades = [{"code": "600988.SH", "entryDate": "2026-07-01", "shares": 5000,
               "allocatedCapital": 99500.0}]
    lk = bs.build_open_lookup(active, trades)
    assert lk[("603259", "2026-07-31")]["sh"] == 800
    assert lk[("600988", "2026-07-01")]["amt"] == 99500.0  # suffix stripped


def test_rebase_index_forward_fills_holidays():
    closes = {"2026-02-02": 3000.0, "2026-02-04": 3300.0}
    out = bs.rebase_index(closes, ["2026-02-03", "2026-02-05"], 1000000.0)
    # base = last close <= 02-03 → 3000; 02-05 forward-fills 02-04's close
    assert out == {"2026-02-03": 1000000.0, "2026-02-05": 1100000.0}
    assert bs.rebase_index({}, ["2026-02-03"], 1e6) == {}
    assert bs.rebase_index(closes, ["2026-01-01"], 1e6) == {}  # no base yet
