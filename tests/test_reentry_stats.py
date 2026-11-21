"""Tests for scripts/reentry.py (moved up from research/reentry_stats.py 2026-11-21) — epoch scoping of compute().

Every test builds its own tracking dir under tmp_path; nothing reads tracking/.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "research"))

import reentry as rs


def _trip(code, entry, exit_, ret, entry_px=10.0, exit_px=10.0):
    return {"code": code, "name": code, "entryDate": entry, "exitDate": exit_,
            "entryPrice": entry_px, "exitPrice": exit_px, "returnPct": ret}


def make_tracking(tmp_path, closed, active=()):
    """A tracking/ root in the 2026-10-12 layout (book/active, book/closed)."""
    (tmp_path / "book" / "closed").mkdir(parents=True)
    (tmp_path / "book" / "active").mkdir()
    for i, t in enumerate(closed):
        (tmp_path / "book" / "closed" / f"{t['code']}_{i}.json").write_text(
            json.dumps(t), encoding="utf-8")
    for t in active:
        (tmp_path / "book" / "active" / f"{t['code']}.json").write_text(
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


# --- the prompt prints the live record (was hardcoded n=9 −3.71% until 2026-11-21) ---

def test_prompt_line_reports_the_live_record(monkeypatch):
    import run_daily
    monkeypatch.setattr(run_daily.reentry, "compute", lambda since: {
        "reentry": {"n": 7, "mean_pct": -1.86, "wins": 2, "win_rate_pct": 28.6},
        "book": {"n": 35, "mean_pct": -0.05, "wins": 9, "win_rate_pct": 25.7}})
    line = run_daily.reentry_record_line()
    assert "重入 n=7 均值 -1.86% 胜率 29%" in line and "n=35 均值 -0.05%/笔" in line


def test_prompt_line_without_completed_reentries(monkeypatch):
    import run_daily
    monkeypatch.setattr(run_daily.reentry, "compute",
                        lambda since: {"reentry": {"n": 0}, "book": {"n": 0}})
    assert "尚无已完成的重入" in run_daily.reentry_record_line()


def test_prompt_line_says_so_when_it_cannot_compute(monkeypatch, capsys):
    import run_daily

    def boom(since):
        raise OSError("closed/ unreadable")
    monkeypatch.setattr(run_daily.reentry, "compute", boom)
    assert run_daily.reentry_record_line() == "实测记录: 计算失败 (OSError)"
    assert "re-entry record unavailable" in capsys.readouterr().err
