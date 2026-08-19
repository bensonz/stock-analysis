"""Pins the 2026-08-19 data cleanup: semantics fixed in code, history repaired on disk.

Census findings this protects against regressing:
- 奥来德 688378 was opened at noon 2026-07-10 and sold the same afternoon —
  illegal under A-share T+1 — at 51.24, below the day's actual low of 52.92.
- `holdingDays` held CALENDAR days since inception while every consumer (time
  stop, audits, ANALYST.md) speaks in trading sessions; 32 records recomputed.
- 9 pre-tracker trades had no exitReason and no history[]; reasons were
  recovered from their exit-day daily_summary.json, histories synthesized as
  terminal OPEN/SELL pairs marked synthetic.
"""
import glob
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import position_manager as pm


# ── code semantics ──

def _mk_position(tmp_path, monkeypatch, entry_date):
    monkeypatch.setattr(pm, "TRACKING_DIR", tmp_path)
    # CLOSED_DIR is bound at import from TRACKING_DIR — patching one does NOT
    # rebind the other. The first version of this test patched only
    # TRACKING_DIR and silently wrote two synthetic trades into the LIVE
    # tracking/closed/ (found by the very census this file pins, 2026-08-19).
    closed = tmp_path / "closed"
    closed.mkdir(exist_ok=True)
    monkeypatch.setattr(pm, "CLOSED_DIR", closed)
    monkeypatch.setattr(pm, "regenerate_positions_json", lambda *a, **k: None)
    (tmp_path / "600000.json").write_text(json.dumps({
        "code": "600000", "name": "测试", "status": "active",
        "entryDate": entry_date, "entryPrice": 10.0, "shares": 100,
        "stopLoss": 9.5, "history": []}), encoding="utf-8")


def test_same_day_sell_is_refused(tmp_path, monkeypatch):
    _mk_position(tmp_path, monkeypatch, "2026-08-19")
    with pytest.raises(pm.SameDaySellError):
        pm.close_position(code="600000", reason="x", exit_price=9.0,
                          date="2026-08-19")
    # and the position is untouched — still sellable tomorrow
    pos = json.loads((tmp_path / "600000.json").read_text(encoding="utf-8"))
    assert pos["status"] == "active"


def test_next_day_sell_proceeds_with_session_count(tmp_path, monkeypatch):
    # settled week, far from today's DB edge: (08-04, 08-11] = 5 sessions
    _mk_position(tmp_path, monkeypatch, "2026-08-04")   # Tue
    closed = pm.close_position(code="600000", reason="x", exit_price=9.0,
                               date="2026-08-11")       # next Tue
    # 600000 is in the price DB: 5 real sessions, not 7 calendar days
    assert closed["holdingDays"] == 5


def test_trading_days_weekday_fallback():
    # a code the price DB has never heard of → weekday arithmetic
    assert pm._trading_days_held("999999", "2026-08-14", "2026-08-19") == 3
    assert pm._trading_days_held("999999", "2026-08-19", "2026-08-19") == 0


# ── on-disk history state ──

def _closed_records():
    for f in glob.glob(str(ROOT / "tracking" / "closed" / "*.json")):
        yield f, json.loads(Path(f).read_text(encoding="utf-8"))


def test_no_closed_trade_lacks_reason_or_history():
    for f, r in _closed_records():
        assert r.get("exitReason"), f"{f}: exitReason missing"
        assert r.get("history"), f"{f}: history missing"


def test_synthetic_history_is_marked_and_terminal_only():
    synth = [(f, r) for f, r in _closed_records()
             if any(e.get("synthetic") for e in r.get("history", []))]
    assert synth, "the 9 backfilled histories should exist"
    for f, r in synth:
        acts = [e["action"] for e in r["history"]]
        assert acts == ["OPEN", "SELL"], f"{f}: synthetic history must not invent HOLDs"
        assert all(e.get("synthetic") for e in r["history"]), \
            f"{f}: every synthesized entry must say so"


def test_the_t1_violation_stays_marked():
    marked = [r for _, r in _closed_records()
              if r.get("code", "").startswith("688378")
              and r.get("entryDate") == "2026-07-10"]
    assert marked and "t1_violation" in marked[0].get("dataQuality", {})


def test_every_run_dir_has_a_manifest():
    missing = [str(Path(lp).parent) for lp in
               glob.glob(str(ROOT / "runs" / "*" / "log.json")) +
               glob.glob(str(ROOT / "runs" / "*" / "*" / "log.json"))
               if not (Path(lp).parent / "manifest.json").exists()]
    assert missing == [], f"runs without manifest: {missing}"


# ── 2a-i: replayable event schema (epoch 2026-08-19) ──

def test_open_event_carries_position_defining_values(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "TRACKING_DIR", tmp_path)
    closed = tmp_path / "closed"; closed.mkdir()
    monkeypatch.setattr(pm, "CLOSED_DIR", closed)
    monkeypatch.setattr(pm, "regenerate_positions_json", lambda *a, **k: None)
    monkeypatch.setattr(pm, "load_portfolio_config", lambda: {
        "starting_capital": 1000000, "max_positions": 10,
        "max_position_pct": 10, "min_cash_pct": 0})
    monkeypatch.setattr(pm, "load_active_positions", lambda: [])
    monkeypatch.setattr(pm, "build_positions_snapshot", lambda *a, **k: {
        "portfolio": {"cash": 500000.0, "deployableCash": 500000.0,
                      "minCashValue": 0.0, "totalEquity": 1000000.0}})
    pm.open_position({"code": "600000", "name": "测试", "entryPrice": 10.0,
                      "stopLoss": 9.5, "targetPrice": 11.5, "allocation_pct": 5,
                      "entryDate": "2026-08-19", "slot": "noon"})
    pos = json.loads((tmp_path / "600000.json").read_text(encoding="utf-8"))
    ev = pos["history"][0]
    assert ev["action"] == "OPEN"
    # replay fields: without these the event log cannot rebuild the position
    assert ev["shares"] == pos["shares"] == 2500
    assert ev["stop"] == 9.5
    assert ev["allocatedCapital"] == pos["allocatedCapital"] == 25000.0


def test_sell_event_carries_shares(tmp_path, monkeypatch):
    _mk_position(tmp_path, monkeypatch, "2026-08-14")
    pm.close_position(code="600000", reason="x", exit_price=9.0, date="2026-08-18")
    closed_files = list((tmp_path / "closed").glob("600000_*.json"))
    assert len(closed_files) == 1
    ev = json.loads(closed_files[0].read_text(encoding="utf-8"))["history"][-1]
    assert ev["action"] == "SELL" and ev["shares"] == 100


def test_raise_stop_event_records_old_and_resulting_stop(tmp_path, monkeypatch):
    _mk_position(tmp_path, monkeypatch, "2026-08-14")
    pos = pm.update_position("600000", {
        "new_stop": 9.8,
        "history_entry": {"date": "2026-08-18", "slot": "noon", "price": 10.2,
                          "change_pct": 2.0, "action": "RAISE_STOP", "note": "n"}})
    ev = pos["history"][-1]
    assert (ev["old_stop"], ev["new_stop"]) == (9.5, 9.8)
    assert pos["currentStop"] == 9.8

    # a LOWER request is refused — the event must record the RESULTING stop,
    # not the requested one, or replay would apply a raise that never happened
    pos = pm.update_position("600000", {
        "new_stop": 9.0,
        "history_entry": {"date": "2026-08-19", "slot": "noon", "price": 10.0,
                          "change_pct": 0.0, "action": "RAISE_STOP", "note": "n"}})
    ev = pos["history"][-1]
    assert ev["new_stop"] == 9.8 == pos["currentStop"]   # unchanged
    assert "stop_not_raised" in ev


def test_standalone_new_stop_still_works_without_history_entry(tmp_path, monkeypatch):
    _mk_position(tmp_path, monkeypatch, "2026-08-14")
    pos = pm.update_position("600000", {"new_stop": 9.9})
    assert pos["currentStop"] == 9.9
