"""SPEC (not yet implemented): the site must not explain failures away.

Screenshot 2026-08-21 16:21 showed the day panel for 2026-08-20 asserting three
things, of which two were false:

    2026-08-20  收盘  [盘前快照·未含当日行情]        ← FALSE: marks ARE that day's close
    975,113                                        ← correct
    该日无逐仓决策记录（早于决策日志上线）           ← FALSE: the run FAILED at Gate 1,
                                                     and the noon run's 4 decisions
                                                     were sitting right there, discarded

Mechanism: `collect_equity_series` picks `max(points, key=time)`. For 08-20 the
winner was `afternoon/input` (pre_run, 15:23) — the pre-run snapshot of the run
that DIED at Gate 1 — beating `noon/output` (post_run, 11:42) from the run that
succeeded. The equity it picked is right (975,113 IS the close), but every
sentence around it was wrong.

Two conflations to undo:

1. **Snapshot TYPE is not mark FRESHNESS.** `pre_run` is written before Phase 1
   collects any prices, so it carries whatever the PREVIOUS run left in
   positions.json. Whether that is stale depends on *when* that was:
       08-21 noon/input  : snapshot 08-21, positions_json.lastUpdated 08-20 → STALE
       08-20 aft /input  : snapshot 08-20, positions_json.lastUpdated 08-20 → FRESH
   The badge must derive from `lastUpdated`'s DATE vs the snapshot's date, not
   from the `pre_run` label.

2. **Missing decisions have several causes and one message.** Across all history
   exactly ONE date (2026-02-13) has a daily_summary whose actions carry no
   `note` — the genuine "predates the decision log" case. Everywhere else the
   message appears, the real cause is a failed run or a missing artifact.

Proposed surface (rename freely — this is the part under review):
    _snapshot_point()      gains "marks_asof"  (positions_json.lastUpdated)
    collect_day_details()  sets  det["stale_marks"]  replacing det["pre"]
                           sets  det["notes_absent_reason"] in
                                 {"run_failed", "predates_note_log", "unknown", None}
                           sets  det["actions_from_slot"] when decisions were
                                 borrowed from a sibling slot
                           sets  det["from_failed_run"] when the winning snapshot
                                 came from a run whose manifest says failed
"""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_site as bs


# ── helpers ──────────────────────────────────────────────────────────────────

def write_snapshot(runs, rel, *, snap_time, stype, equity, last_updated,
                   codes=("688981",)):
    p = runs / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "snapshot_time": snap_time,
        "snapshot_type": stype,
        "positions_json": {
            "lastUpdated": last_updated,
            "portfolio": {"startingCapital": 1000000, "totalEquity": equity,
                          "totalReturnPct": -2.49, "positionsUsed": len(codes)},
            "activePositions": [{"code": c, "name": "测试", "pnl_pct": 1.0,
                                 "currentValue": 1000.0, "weight_pct": 1.0}
                                for c in codes],
        },
    }), encoding="utf-8")


def write_summary(runs, rel, actions):
    p = runs / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"actions": actions}), encoding="utf-8")


def write_manifest(runs, date, slot, status):
    p = runs / date / slot / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"date": date, "slot": slot, "status": status,
                             "run_started_at": f"{date}T15:05:00+08:00"}),
                 encoding="utf-8")


def build_0820(runs):
    """The exact shape that produced the screenshot."""
    write_snapshot(runs, "2026-08-20/noon/input/positions_snapshot.json",
                   snap_time="2026-08-20T11:35:25+08:00", stype="pre_run",
                   equity=971151.0, last_updated="2026-08-19T15:23:48+08:00")
    write_snapshot(runs, "2026-08-20/noon/output/positions_snapshot.json",
                   snap_time="2026-08-20T11:42:52+08:00", stype="post_run",
                   equity=976199.0, last_updated="2026-08-20T11:42:52+08:00")
    # the FAILED afternoon run's pre-run snapshot — later in time, so it wins
    write_snapshot(runs, "2026-08-20/afternoon/input/positions_snapshot.json",
                   snap_time="2026-08-20T15:23:00+08:00", stype="pre_run",
                   equity=975113.0, last_updated="2026-08-20T15:11:20+08:00")
    write_summary(runs, "2026-08-20/noon/output/daily_summary.json", [
        {"code": "688981", "name": "中芯国际", "action": "HOLD",
         "price": 125.5, "pnl_pct": 3.6, "note": "半导体板块 top3, 持有"},
    ])
    write_manifest(runs, "2026-08-20", "noon", "success")
    write_manifest(runs, "2026-08-20", "afternoon", "failed")


def day(runs, date="2026-08-20"):
    series = bs.collect_equity_series(runs)
    return series, bs.collect_day_details(series, [])[date]


# ── A. the badge must track mark freshness, not the pre_run label ────────────

def test_the_screenshot_case_is_not_flagged_stale(tmp_path):
    """08-20's winning snapshot was taken 15:23, AFTER the close, and its marks
    are that day's closing prices. Calling it 未含当日行情 is simply false."""
    runs = tmp_path / "runs"
    build_0820(runs)
    _series, det = day(runs)
    assert det["equity"] == 975113.0            # value was right, keep it
    assert not det.get("stale_marks"), "marks are same-day; must not claim otherwise"


def test_marks_from_a_previous_day_are_flagged(tmp_path):
    """08-21 noon: snapshot 08-21, marks last updated 08-20 → genuinely stale."""
    runs = tmp_path / "runs"
    write_snapshot(runs, "2026-08-21/noon/input/positions_snapshot.json",
                   snap_time="2026-08-21T11:35:25+08:00", stype="pre_run",
                   equity=975113.0, last_updated="2026-08-20T15:23:48+08:00")
    _series, det = day(runs, "2026-08-21")
    assert det["stale_marks"], "marks predate the day being shown"


def test_postrun_is_never_stale(tmp_path):
    runs = tmp_path / "runs"
    write_snapshot(runs, "2026-08-21/noon/output/positions_snapshot.json",
                   snap_time="2026-08-21T11:42:52+08:00", stype="post_run",
                   equity=972657.0, last_updated="2026-08-21T11:42:52+08:00")
    _series, det = day(runs, "2026-08-21")
    assert not det.get("stale_marks")


def test_unknown_freshness_is_shown_not_assumed_fresh(tmp_path):
    """No lastUpdated → we do not know. Per the null-visibility rule that must
    stay visible, never be silently rendered as healthy."""
    runs = tmp_path / "runs"
    write_snapshot(runs, "2026-08-21/noon/input/positions_snapshot.json",
                   snap_time="2026-08-21T11:35:25+08:00", stype="pre_run",
                   equity=975113.0, last_updated=None)
    _series, det = day(runs, "2026-08-21")
    assert det["stale_marks"], "unknown freshness must not read as fresh"


# ── B. the missing-decisions note must state the REAL reason ─────────────────

def test_failed_run_is_named_not_dressed_as_a_missing_feature(tmp_path):
    runs = tmp_path / "runs"
    write_snapshot(runs, "2026-08-20/afternoon/input/positions_snapshot.json",
                   snap_time="2026-08-20T15:23:00+08:00", stype="pre_run",
                   equity=975113.0, last_updated="2026-08-20T15:11:20+08:00")
    write_manifest(runs, "2026-08-20", "afternoon", "failed")
    _series, det = day(runs)
    assert det["notes_absent_reason"] == "run_failed"


def test_the_one_genuinely_old_date_still_says_so(tmp_path):
    """2026-02-13 is the ONLY date in all history with a daily_summary whose
    actions carry no note. That is the real 早于决策日志上线 case."""
    runs = tmp_path / "runs"
    write_snapshot(runs, "2026-02-13/input/positions_snapshot.json",
                   snap_time="2026-02-13T15:35:00+08:00", stype="pre_run",
                   equity=1000000.0, last_updated="2026-02-13T15:35:00+08:00")
    write_summary(runs, "2026-02-13/output/daily_summary.json", [
        {"code": "300373", "name": "扬杰科技", "action": "HOLD", "price": 50.0},
    ])
    _series, det = day(runs, "2026-02-13")
    assert det["notes_absent_reason"] == "predates_note_log"


def test_absent_artifacts_with_no_manifest_admit_ignorance(tmp_path):
    runs = tmp_path / "runs"
    write_snapshot(runs, "2026-05-01/input/positions_snapshot.json",
                   snap_time="2026-05-01T15:35:00+08:00", stype="post_run",
                   equity=1000000.0, last_updated="2026-05-01T15:35:00+08:00")
    _series, det = day(runs, "2026-05-01")
    assert det["notes_absent_reason"] == "unknown"


def test_a_day_with_notes_reports_no_absence_reason(tmp_path):
    runs = tmp_path / "runs"
    build_0820(runs)
    _series, det = day(runs)
    # decisions exist for this date (see C) → nothing to explain
    assert det.get("notes_absent_reason") is None


# ── C. decisions from a sibling slot must not be silently discarded ──────────

def test_sibling_slot_decisions_are_used_and_labelled(tmp_path):
    """The screenshot's worst part: the noon run's decisions existed and were
    thrown away because the afternoon snapshot won on timestamp."""
    runs = tmp_path / "runs"
    build_0820(runs)
    _series, det = day(runs)
    assert [a["c"] for a in det["actions"]] == ["688981"]
    assert det["actions_from_slot"] == "noon", "must say where they came from"


def test_winning_slot_decisions_win_when_present(tmp_path):
    """No borrowing when the winning run has its own."""
    runs = tmp_path / "runs"
    build_0820(runs)
    write_summary(runs, "2026-08-20/afternoon/output/daily_summary.json", [
        {"code": "000703", "name": "恒逸石化", "action": "SELL",
         "price": 20.1, "pnl_pct": 28.9, "note": "收盘卖出"},
    ])
    _series, det = day(runs)
    assert [a["c"] for a in det["actions"]] == ["000703"]
    assert det.get("actions_from_slot") in (None, "afternoon")


# ── D. equity sourced from a failed run must say so ──────────────────────────

def test_equity_from_a_failed_run_is_marked(tmp_path):
    """975,113 is the correct close, but it reached the page via a run that
    failed at Gate 1. Correct number, provenance still worth stating."""
    runs = tmp_path / "runs"
    build_0820(runs)
    _series, det = day(runs)
    assert det["from_failed_run"] is True


def test_equity_from_a_healthy_run_is_not_marked(tmp_path):
    runs = tmp_path / "runs"
    write_snapshot(runs, "2026-08-21/afternoon/output/positions_snapshot.json",
                   snap_time="2026-08-21T15:10:55+08:00", stype="post_run",
                   equity=972697.0, last_updated="2026-08-21T15:10:55+08:00")
    write_manifest(runs, "2026-08-21", "afternoon", "success")
    _series, det = day(runs, "2026-08-21")
    assert not det.get("from_failed_run")


# ── E. regressions: the equity curve itself must not move ────────────────────

def test_selection_by_time_is_unchanged(tmp_path):
    """The fix is about provenance and labels. The number stays 975,113."""
    runs = tmp_path / "runs"
    build_0820(runs)
    series, _det = day(runs)
    assert [p["date"] for p in series] == ["2026-08-20"]
    assert series[0]["equity"] == 975113.0


def test_rendered_page_carries_no_false_staleness_claim(tmp_path, monkeypatch):
    """The four excuse strings all live in the JS by design — which of them a
    day USES is decided by the embedded payload, so assert on that."""
    runs = tmp_path / "runs"
    build_0820(runs)
    monkeypatch.setattr(bs, "RUNS_DIR", runs)
    series = bs.collect_equity_series(runs)
    details = bs.collect_day_details(series, [])
    html = bs.render_html(series, {"portfolio": {"totalEquity": 975113.0},
                                   "activePositions": []},
                          [], bs.compute_stats(series, []), details=details)

    payload = json.loads(re.search(r"const DETAILS = (\{.*?\});", html, re.S).group(1))
    det = payload["2026-08-20"]
    assert not det.get("stale_marks"), "15:23 marks ARE that day's close"
    assert det.get("notes_absent_reason") is None, "decisions were borrowed, not absent"
    assert det["from_failed_run"] is True, "provenance must survive into the page"
    # and the JS must still be able to say the true thing when it applies
    assert "早于决策日志上线" in html
