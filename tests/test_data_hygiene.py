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
