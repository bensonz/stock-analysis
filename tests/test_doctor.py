"""The doctor's own quality gate.

Two properties matter more than any individual check:

1. **An invariant is a defect on its first occurrence; an env finding is not.**
   Getting this backwards in either direction destroys the tool — flag weather
   as a bug and it becomes noise nobody reads, treat a contradiction as weather
   and 688019 sits in the artifacts for four days again.

2. **A check that cannot run says so.** Silently passing because the artifact
   was missing is how a health report starts lying, which is the exact failure
   the doctor exists to catch. Every skip carries a reason.

Both spurious-finding classes the first sweep produced are pinned here as
regressions: judging Feb runs by August's artifact contract, and calling a
post-midnight rerun's marks "stale" because they were *newer* than the run date.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import doctor as doc


# ── fixtures ─────────────────────────────────────────────────────────────────

def make_run(runs, date, slot, *, status="success", held=("000703",),
             new_positions=(), actions=(), snapshot_type="post_run",
             last_updated=None, gates=None, phases=None, artifacts=True,
             manifest=True):
    p = runs / date / slot
    (p / "output").mkdir(parents=True, exist_ok=True)
    if manifest:
        (p / "manifest.json").write_text(json.dumps({
            "date": date, "slot": slot, "status": status,
            "run_started_at": f"{date}T15:05:00+08:00",
            "phases": phases if phases is not None else {},
            "gates": gates if gates is not None else {},
        }), encoding="utf-8")
    if artifacts:
        (p / "output" / "report.md").write_text("# r\n", encoding="utf-8")
        (p / "output" / "daily_summary.json").write_text(json.dumps({
            "date": date,
            "actions": list(actions),
            "newPositions": list(new_positions),
        }, ensure_ascii=False), encoding="utf-8")
        (p / "output" / "positions_snapshot.json").write_text(json.dumps({
            "snapshot_time": f"{date}T15:10:00+08:00",
            "snapshot_type": snapshot_type,
            "positions_json": {
                "lastUpdated": last_updated or f"{date}T15:10:00+08:00",
                "portfolio": {"startingCapital": 1000000, "totalEquity": 1000000},
                "activePositions": [{"code": c, "name": "x"} for c in held],
            },
        }, ensure_ascii=False), encoding="utf-8")
    return p


def audit(runs, date, slot, accepted=None):
    return doc.audit_run(date, slot, runs / date / slot, runs_dir=runs,
                         accepted=accepted or {})


# ── 1. invariant vs env: the whole classification ────────────────────────────

def test_invariant_is_a_defect_on_first_occurrence(tmp_path):
    """688019: newPositions claimed an open the snapshot never held. T+1 rules
    out the innocent explanation, so one occurrence is already enough."""
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-17", "noon", held=("000703",),
             new_positions=[{"code": "688019", "name": "安集科技"}])
    res = audit(runs, "2026-08-17", "noon")
    ids = [f.id for f in res.code_findings]
    assert "new-position-not-held:688019" in ids
    assert res.verdict == "code_change_needed"


def test_env_finding_is_weather_on_first_occurrence(tmp_path):
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-20", "afternoon", status="failed",
             phases={"collect": {"status": "failed", "errors": ["boom"]}})
    res = audit(runs, "2026-08-20", "afternoon")
    assert [f.id for f in res.ops_findings] == ["phase-failed:collect"]
    assert res.code_findings == []
    assert res.verdict == "action_needed"


def test_env_finding_is_promoted_once_it_reproduces(tmp_path):
    """eastmoney: occurrence 1 weather, occurrence 2 pattern, occurrence 3 a
    design gap. Nothing was watching, so it took a human noticing on day three."""
    runs = tmp_path / "runs"
    phases = {"collect": {"status": "failed", "errors": ["eastmoney dead"]}}
    dates = ["2026-08-18", "2026-08-19", "2026-08-20"]
    for i, d in enumerate(dates):
        p = make_run(runs, d, "afternoon", status="failed", phases=phases)
        res = doc.audit_run(d, "afternoon", p, runs_dir=runs, accepted={})
        doc.write_result(res, p)
        assert res.findings[0].occurrences == i + 1

    assert res.findings[0].occurrences == doc.PROMOTE_AFTER
    assert res.verdict == "code_change_needed", "3rd consecutive is not weather"
    assert res.findings[0].first_seen == dates[0]


def test_recurrence_counts_consecutive_not_lifetime(tmp_path):
    """Twice last week and once today is three weather events, not a streak."""
    runs = tmp_path / "runs"
    phases = {"collect": {"status": "failed", "errors": ["x"]}}
    for d, ph in [("2026-08-17", phases), ("2026-08-18", phases),
                  ("2026-08-19", {}), ("2026-08-20", phases)]:
        p = make_run(runs, d, "afternoon",
                     status="failed" if ph else "success", phases=ph)
        doc.write_result(doc.audit_run(d, "afternoon", p, runs_dir=runs,
                                       accepted={}), p)
    res = audit(runs, "2026-08-20", "afternoon")
    assert res.findings[0].occurrences == 1, "the clean run broke the streak"
    assert res.code_findings == []


# ── 2. a check that cannot run must say so ───────────────────────────────────

def test_missing_artifact_is_skipped_with_a_reason_not_passed(tmp_path):
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-20", "afternoon", status="failed", artifacts=False)
    res = audit(runs, "2026-08-20", "afternoon")
    assert res.checks_run < len(doc.CHECKS)
    assert res.skipped, "silent pass on a missing artifact is the lie we hunt"
    assert all(s["reason"] for s in res.skipped)


def test_a_check_that_raises_is_recorded_not_swallowed(tmp_path, monkeypatch):
    def exploding(_v):
        raise ValueError("bad check")
    monkeypatch.setattr(doc, "CHECKS", [exploding])
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-20", "noon")
    res = audit(runs, "2026-08-20", "noon")
    assert res.skipped and "bad check" in res.skipped[0]["reason"]


def test_absent_manifest_is_itself_a_finding(tmp_path):
    """Absence must not read as health — it is the 'never fired vs died early'
    hole, and it gets a name."""
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-20", "afternoon", manifest=False)
    res = audit(runs, "2026-08-20", "afternoon")
    assert [f.id for f in res.findings] == ["manifest-absent"]


# ── 3. regressions: the two spurious classes the first sweep produced ────────

def test_february_runs_are_not_judged_by_august_artifacts(tmp_path):
    """positions_snapshot.json did not exist until 2026-03-05. Nine Feb–Mar runs
    were flagged for 'missing' it — the same epoch error D9 names for gates."""
    runs = tmp_path / "runs"
    p = runs / "2026-02-03" / "afternoon" / "output"
    p.mkdir(parents=True)
    (p / "report.md").write_text("# r\n", encoding="utf-8")
    (p / "daily_summary.json").write_text('{"actions":[]}', encoding="utf-8")
    (p.parent / "manifest.json").write_text(json.dumps(
        {"date": "2026-02-03", "slot": "afternoon", "status": "success",
         "run_started_at": "2026-02-03T15:35:00+08:00"}), encoding="utf-8")
    res = doc.audit_run("2026-02-03", "afternoon", p.parent, runs_dir=runs,
                        accepted={})
    assert "success-missing-artifacts" not in [f.id for f in res.findings]


def test_artifact_missing_after_its_epoch_is_still_a_defect(tmp_path):
    runs = tmp_path / "runs"
    p = make_run(runs, "2026-08-20", "noon")
    (p / "output" / "positions_snapshot.json").unlink()
    res = audit(runs, "2026-08-20", "noon")
    assert "success-missing-artifacts" in [f.id for f in res.findings]


def test_marks_newer_than_the_run_date_are_not_called_stale(tmp_path):
    """08-11 and 08-12 afternoon were manual reruns finishing after midnight.
    The first draft compared with != and called both directions stale, which was
    false about those runs: the marking step ran, just late."""
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-11", "afternoon",
             last_updated="2026-08-12T00:18:32+08:00")
    res = audit(runs, "2026-08-11", "afternoon")
    assert "postrun-marks-stale" not in [f.id for f in res.findings]


def test_marks_older_than_the_run_date_are_flagged(tmp_path):
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-21", "afternoon",
             last_updated="2026-08-20T15:23:00+08:00")
    res = audit(runs, "2026-08-21", "afternoon")
    assert "postrun-marks-stale" in [f.id for f in res.code_findings]


def test_undated_marks_are_flagged_rather_than_assumed_fresh(tmp_path):
    runs = tmp_path / "runs"
    p = make_run(runs, "2026-08-21", "afternoon")
    snap = json.loads((p / "output" / "positions_snapshot.json").read_text())
    del snap["positions_json"]["lastUpdated"]
    (p / "output" / "positions_snapshot.json").write_text(
        json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    res = audit(runs, "2026-08-21", "afternoon")
    assert "postrun-marks-undated" in [f.id for f in res.code_findings]


# ── 4. ids are the recurrence key, so they must be stable and distinct ───────

def test_two_different_hard_fails_get_different_ids(tmp_path):
    """08-12 noon produced 11 hard fails; the first draft gave them one id, which
    would have counted a single recurring failure as eleven."""
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-12", "noon", status="failed", gates={
        "phase1_to_phase2": {"passed": False,
                             "hard_fails": ["partial day", "sector data empty"]}})
    res = audit(runs, "2026-08-12", "noon")
    ids = [f.id for f in res.findings if f.check == "gate_hard_fail"]
    assert len(ids) == len(set(ids)) == 2


def test_id_survives_number_churn_so_recurrence_can_promote(tmp_path):
    """'454 rows vs ~5210' and '1102 rows vs ~5210' are the same failure."""
    a = doc._digest("latest price day is partial (454 rows vs ~5210)")
    b = doc._digest("latest price day is partial (1102 rows vs ~5210)")
    c = doc._digest("sector breadth data empty")
    assert a == b and a != c


# ── 5. acceptance is human-authored input, never doctor output ───────────────

def test_accepted_finding_stops_demanding_a_code_change(tmp_path):
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-17", "noon",
             new_positions=[{"code": "688019", "name": "x"}])
    res = audit(runs, "2026-08-17", "noon",
                accepted={"new-position-not-held:688019": "已知, TODO stage 2"})
    assert res.code_findings == []
    assert [f.id for f in res.accepted_findings] == ["new-position-not-held:688019"]
    assert res.verdict == "clean"


def test_accepted_file_parses_the_documented_format(tmp_path):
    f = tmp_path / "ACCEPTED.md"
    f.write_text("# Accepted\n\n"
                 "- `manifest-absent` — 预检失败零留痕, TODO Stage 4\n"
                 "- gate-hard-fail:x:abc123 — 天气\n"
                 "not a bullet line\n", encoding="utf-8")
    got = doc.load_accepted(f)
    assert got["manifest-absent"].startswith("预检失败")
    assert got["gate-hard-fail:x:abc123"] == "天气"
    assert len(got) == 2


def test_missing_accepted_file_is_not_an_error(tmp_path):
    assert doc.load_accepted(tmp_path / "nope.md") == {}


# ── 6. legitimate shapes that must NOT be flagged ────────────────────────────

def test_selling_a_position_removes_it_without_complaint(tmp_path):
    """SELL's whole point is that the code leaves the snapshot."""
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-20", "noon", held=("000703",),
             actions=[{"code": "603127", "action": "SELL", "name": "x"}])
    res = audit(runs, "2026-08-20", "noon")
    assert res.findings == []


def test_sell_recorded_but_still_held_is_flagged(tmp_path):
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-20", "noon", held=("000703", "603127"),
             actions=[{"code": "603127", "action": "SELL", "name": "x"}])
    res = audit(runs, "2026-08-20", "noon")
    assert "sold-still-held:603127" in [f.id for f in res.code_findings]


def test_hold_on_a_code_we_do_not_own_is_a_ghost(tmp_path):
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-20", "noon", held=("000703",),
             actions=[{"code": "999999", "action": "HOLD", "name": "ghost"}])
    res = audit(runs, "2026-08-20", "noon")
    assert "action-on-unheld:999999" in [f.id for f in res.code_findings]


def test_a_healthy_run_produces_nothing(tmp_path):
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-21", "afternoon", held=("000703", "688981"),
             actions=[{"code": "000703", "action": "HOLD", "name": "x"}])
    res = audit(runs, "2026-08-21", "afternoon")
    assert res.findings == [] and res.verdict == "clean"


def test_gate_failure_reported_as_success_is_caught(tmp_path):
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-20", "noon", status="success",
             gates={"phase1_to_phase2": {"passed": False, "hard_fails": ["x"]}})
    res = audit(runs, "2026-08-20", "noon")
    assert "gate-failure-as-success" in [f.id for f in res.code_findings]


# ── 7. the boundary: detection only ──────────────────────────────────────────

def test_doctor_writes_only_into_the_run_dir(tmp_path):
    """It may never touch tracking/ or closed/. A system that repairs its own
    trade records produces numbers nobody can audit."""
    runs = tmp_path / "runs"
    tracking = tmp_path / "tracking"
    (tracking / "closed").mkdir(parents=True)
    (tracking / "positions.json").write_text("{}", encoding="utf-8")
    before = {p: p.read_bytes() for p in tracking.rglob("*") if p.is_file()}

    p = make_run(runs, "2026-08-20", "noon",
                 new_positions=[{"code": "688019", "name": "x"}])
    doc.write_result(audit(runs, "2026-08-20", "noon"), p)

    after = {q: q.read_bytes() for q in tracking.rglob("*") if q.is_file()}
    assert before == after
    assert (p / "audit-result.md").exists()
    assert (p / "audit-result.json").exists()


def test_result_round_trips_so_recurrence_can_read_it(tmp_path):
    runs = tmp_path / "runs"
    p = make_run(runs, "2026-08-20", "noon",
                 new_positions=[{"code": "688019", "name": "x"}])
    doc.write_result(audit(runs, "2026-08-20", "noon"), p)
    loaded = json.loads((p / "audit-result.json").read_text(encoding="utf-8"))
    assert loaded["verdict"] == "code_change_needed"
    assert loaded["findings"][0]["id"] == "new-position-not-held:688019"
    assert loaded["checks_total"] == len(doc.CHECKS)


def test_markdown_states_coverage_and_its_own_limits(tmp_path):
    runs = tmp_path / "runs"
    make_run(runs, "2026-08-20", "afternoon", status="failed", artifacts=False)
    md = doc.render_md(audit(runs, "2026-08-20", "afternoon"))
    assert "检查覆盖" in md
    assert "跳过" in md
    assert "只发现，不修复" in md


# ── 8. recurrence walks the CALENDAR, not the execution clock ────────────────

def test_neighbours_are_calendar_order_not_start_time(tmp_path):
    """The house rule sorts runs by run_started_at because slot names sort wrong
    ("afternoon" < "noon"). That is right for the equity curve and wrong here.

    Backfilled legacy manifests carry timestamps that do not track their own
    dates — one put 2026-04-30 between 04-09 and 04-10 — and a rerun finishing
    after midnight sorts after the *next* day's noon. Either scrambles the
    neighbour chain, and a scrambled chain reads three consecutive eastmoney
    failures as three unrelated weather events, killing the one promotion this
    tool exists to make.
    """
    runs = tmp_path / "runs"
    for date, slot, started in [
        ("2026-04-09", "afternoon", "2026-04-09T15:35:00+08:00"),
        ("2026-04-30", "afternoon", "2026-04-09T20:00:00+08:00"),   # bad backfill
        ("2026-04-10", "afternoon", "2026-04-10T15:35:00+08:00"),
        ("2026-04-10", "noon", "2026-04-10T11:35:00+08:00"),
    ]:
        p = make_run(runs, date, slot)
        m = json.loads((p / "manifest.json").read_text())
        m["run_started_at"] = started
        (p / "manifest.json").write_text(json.dumps(m), encoding="utf-8")

    order = [(d, s) for d, s, _ in doc.calendar_order(runs)]
    assert order == [("2026-04-09", "afternoon"),
                     ("2026-04-10", "noon"),
                     ("2026-04-10", "afternoon"),
                     ("2026-04-30", "afternoon")]


def test_a_late_rerun_does_not_break_a_streak(tmp_path):
    """08-11 afternoon finished at 00:18 on 08-12 — by start time it lands after
    08-12 noon, which would split one streak into two."""
    runs = tmp_path / "runs"
    phases = {"collect": {"status": "failed", "errors": ["eastmoney dead"]}}
    plan = [("2026-08-11", "afternoon", "2026-08-12T00:18:32+08:00"),
            ("2026-08-12", "noon", "2026-08-12T11:35:00+08:00"),
            ("2026-08-12", "afternoon", "2026-08-12T15:05:00+08:00")]
    for date, slot, started in plan:
        p = make_run(runs, date, slot, status="failed", phases=phases)
        m = json.loads((p / "manifest.json").read_text())
        m["run_started_at"] = started
        (p / "manifest.json").write_text(json.dumps(m), encoding="utf-8")

    for date, slot, _ in plan:
        p = runs / date / slot
        doc.write_result(doc.audit_run(date, slot, p, runs_dir=runs,
                                       accepted={}), p)

    res = doc.audit_run("2026-08-12", "afternoon", runs / "2026-08-12" / "afternoon",
                        runs_dir=runs, accepted={})
    assert res.findings[0].occurrences == 3
    assert res.findings[0].first_seen == "2026-08-11"


def test_a_cold_sweep_converges_in_one_pass(tmp_path):
    """Backfilling history must not need a second run to get counts right."""
    runs = tmp_path / "runs"
    phases = {"collect": {"status": "failed", "errors": ["x"]}}
    for d in ("2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20"):
        make_run(runs, d, "afternoon", status="failed", phases=phases)
    doc.main(["--since", "2026-08-01", "--runs-dir", str(runs)])
    last = json.loads((runs / "2026-08-20" / "afternoon" / "audit-result.json")
                      .read_text(encoding="utf-8"))
    assert last["findings"][0]["occurrences"] == 4
    assert last["verdict"] == "code_change_needed"


# ── 9. the standing view: what is broken right now ───────────────────────────

def test_open_view_folds_by_problem_not_by_instance(tmp_path):
    """One defect on eight dates is ONE thing to go fix. Folding by finding id
    was the obvious first cut and it was wrong — ids carry the stock code, so a
    single bug in how newPositions is written rendered as eleven rows demanding
    eleven fixes."""
    runs = tmp_path / "runs"
    for d, code in [("2026-08-04", "000739"), ("2026-08-17", "688019"),
                    ("2026-08-20", "688222")]:
        p = make_run(runs, d, "noon", new_positions=[{"code": code, "name": "x"}])
        doc.write_result(doc.audit_run(d, "noon", p, runs_dir=runs, accepted={}), p)

    groups = doc.open_findings(runs)
    assert len(groups) == 1
    g = groups[0]
    assert g["check"] == "new_positions_absent_from_snapshot"
    assert len(g["instances"]) == 3 and len(g["dates"]) == 3
    assert g["needs_code"] and g["last_seen"] == "2026-08-20"


def test_open_view_separates_code_from_operator_work(tmp_path):
    runs = tmp_path / "runs"
    p = make_run(runs, "2026-08-19", "afternoon", status="failed",
                 phases={"collect": {"status": "failed", "errors": ["x"]}})
    doc.write_result(doc.audit_run("2026-08-19", "afternoon", p, runs_dir=runs,
                                   accepted={}), p)
    p = make_run(runs, "2026-08-20", "noon",
                 new_positions=[{"code": "688222", "name": "x"}])
    doc.write_result(doc.audit_run("2026-08-20", "noon", p, runs_dir=runs,
                                   accepted={}), p)

    groups = {g["check"]: g for g in doc.open_findings(runs)}
    assert groups["new_positions_absent_from_snapshot"]["needs_code"] is True
    assert groups["phase_failed"]["needs_code"] is False
    out = doc.render_open(list(groups.values()))
    assert "需要改代码 (1)" in out and "需要人工操作 (1)" in out


def test_open_view_is_empty_when_everything_is_clean(tmp_path):
    runs = tmp_path / "runs"
    p = make_run(runs, "2026-08-21", "afternoon")
    doc.write_result(doc.audit_run("2026-08-21", "afternoon", p, runs_dir=runs,
                                   accepted={}), p)
    assert doc.open_findings(runs) == []
    assert "（无）" in doc.render_open([])


def test_open_writes_a_file_you_can_just_open(tmp_path):
    """A command you have to remember to run is a command nobody runs."""
    runs = tmp_path / "runs"
    p = make_run(runs, "2026-08-20", "noon",
                 new_positions=[{"code": "688222", "name": "x"}])
    doc.write_result(doc.audit_run("2026-08-20", "noon", p, runs_dir=runs,
                                   accepted={}), p)
    rc = doc.main(["--open", "--runs-dir", str(runs)])
    assert rc == 1
    written = tmp_path / "audit" / "OPEN.md"
    assert written.exists()
    assert "new_positions_absent_from_snapshot" in written.read_text(encoding="utf-8")


def test_open_respects_runs_dir_and_leaves_the_real_file_alone(tmp_path):
    """Import-bound paths are how tests leaked two synthetic trades into
    tracking/closed/ on 08-19. Not again."""
    real = doc.OPEN_FILE
    before = real.read_bytes() if real.exists() else None
    runs = tmp_path / "runs"
    p = make_run(runs, "2026-08-21", "noon")
    doc.write_result(doc.audit_run("2026-08-21", "noon", p, runs_dir=runs,
                                   accepted={}), p)
    doc.main(["--open", "--runs-dir", str(runs)])
    after = real.read_bytes() if real.exists() else None
    assert after == before, "the real audit/OPEN.md must not be touched"
