"""Tests for scripts/research/reentry_stats.py — epoch scoping of compute().

Every test builds its own tracking dir under tmp_path; nothing reads tracking/.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "research"))

import reentry_stats as rs


def _trip(code, entry, exit_, ret, entry_px=10.0, exit_px=10.0):
    return {"code": code, "name": code, "entryDate": entry, "exitDate": exit_,
            "entryPrice": entry_px, "exitPrice": exit_px, "returnPct": ret}


def make_tracking(tmp_path, closed, active=()):
    (tmp_path / "closed").mkdir()
    for i, t in enumerate(closed):
        (tmp_path / "closed" / f"{t['code']}_{i}.json").write_text(
            json.dumps(t), encoding="utf-8")
    for t in active:
        (tmp_path / f"{t['code']}.json").write_text(
            json.dumps({**t, "status": "active"}), encoding="utf-8")
    return tmp_path


def test_since_drops_pre_epoch_reentries(tmp_path):
    d = make_tracking(tmp_path, [
        _trip("600001", "2026-06-01", "2026-06-03", -5.0),
        _trip("600001", "2026-06-10", "2026-06-12", -4.0),   # pre-epoch re-entry
        _trip("600001", "2026-08-01", "2026-08-05", 6.0),    # post-epoch re-entry
    ])
    out = rs.compute(d, since="2026-07-23")
    assert [p["reentry_date"] for p in out["pairs"]] == ["2026-08-01"]


def test_since_keeps_pre_epoch_prior_trip_as_pairing_context(tmp_path):
    d = make_tracking(tmp_path, [
        _trip("600002", "2026-07-01", "2026-07-10", -5.0),   # prior trip, pre-epoch
        _trip("600002", "2026-08-01", "2026-08-05", 3.0),
    ])
    out = rs.compute(d, since="2026-07-23")
    assert out["after_loss"] == {"n": 1, "mean_pct": 3.0, "wins": 1,
                                 "win_rate_pct": 100.0}


def test_since_scopes_book_comparator(tmp_path):
    d = make_tracking(tmp_path, [
        _trip("600003", "2026-07-01", "2026-07-02", -9.0),   # pre-epoch
        _trip("600004", "2026-08-01", "2026-08-02", 2.0),
    ])
    assert rs.compute(d, since="2026-07-23")["book"]["n"] == 1


def test_since_scopes_open_reentries(tmp_path):
    d = make_tracking(tmp_path, [_trip("600005", "2026-06-01", "2026-06-05", 1.0)],
                      active=[{"code": "600005", "name": "x", "entryDate": "2026-06-20",
                               "entryPrice": 10.0}])
    assert rs.compute(d, since="2026-07-23")["open_reentries"] == []


def test_since_none_is_all_history(tmp_path):
    d = make_tracking(tmp_path, [
        _trip("600006", "2026-06-01", "2026-06-03", -5.0),
        _trip("600006", "2026-06-10", "2026-06-12", -4.0),
    ])
    out = rs.compute(d, since=None)
    assert (out["reentry"]["n"], out["book"]["n"]) == (1, 2)
