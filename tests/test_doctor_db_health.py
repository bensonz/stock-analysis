"""The audit must be able to see what `db_health` already knows.

2026-08-27: the report banner said "adj factors lag prices (2026-08-26 <
2026-08-27) — run 'pricedb.py factors heal'" while the audit for the same run
said ✅ 无发现, 12/12. Neither was lying. `db_health` is computed in Phase 1 and
written to input/db_health.json, where the phase-1 gate, the prompt and the
report banner all read it — but the doctor only ever opened manifest.json and
output/*, so `grep db_health scripts/doctor.py` returned nothing at all.

That lag is not cosmetic: it is the same one that corrupts rps_cache.ma10 into
hfq units (2026-08-25, 002293 read 101.97 against a true MA10 of 11.22), which
a deep report then quoted as a price. db_health had been announcing the cause
for days with nobody downstream listening.

The fix is deliberately NOT a second implementation. db_health stays the single
source of truth for "is the data sound" and the doctor consumes its verdict.
This does not violate the independence rule: that rule stops a check from
sharing a source with the WRITER it audits, and db_health measures the price
database, not the run — reading it is consulting an instrument, not marking our
own homework. Two implementations of the same measurement could disagree, and
then neither could be trusted.

Both findings are `env`, so a one-session lag stays weather. Three consecutive
promotes it — which is the correct reading, because a lag that keeps coming
back means the heal is not running by itself, and THAT is the code change.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import doctor as doc
from test_doctor import make_run


def with_health(runs, date, slot, health):
    """A normal clean run, plus whatever db_health Phase 1 recorded."""
    p = make_run(runs, date, slot)
    (p / "input").mkdir(parents=True, exist_ok=True)
    if health is not None:
        (p / "input" / "db_health.json").write_text(
            json.dumps(health, ensure_ascii=False), encoding="utf-8")
    return p


HEALTHY = {"ok": True, "warnings": [], "latest_price_date": "2026-08-27",
           "spot_check": {"sampled": 20, "checked": 20, "fetch_failures": 0,
                          "mismatches": []}}


def test_a_db_health_warning_becomes_a_finding(tmp_path):
    """The exact 2026-08-27 case: clean run, warning nobody surfaced."""
    p = with_health(tmp_path, "2026-08-27", "afternoon", dict(
        HEALTHY, warnings=["adj factors lag prices (2026-08-26 < 2026-08-27)"
                           " — run 'pricedb.py factors heal'"]))
    res = doc.audit_run("2026-08-27", "afternoon", p, runs_dir=tmp_path, accepted={})
    ids = [f.id for f in res.findings]
    assert any(i.startswith("db-health-warning:") for i in ids), ids


def test_a_healthy_db_produces_nothing(tmp_path):
    p = with_health(tmp_path, "2026-08-27", "afternoon", HEALTHY)
    res = doc.audit_run("2026-08-27", "afternoon", p, runs_dir=tmp_path, accepted={})
    assert [f for f in res.findings if f.check.startswith("db_health")] == []


def test_the_warning_is_env_not_invariant(tmp_path):
    """A stale factor table is the outside world, not a contradiction. One
    occurrence is weather; PROMOTE_AFTER consecutive is the design gap."""
    p = with_health(tmp_path, "2026-08-27", "afternoon",
                    dict(HEALTHY, warnings=["adj factors lag prices"]))
    res = doc.audit_run("2026-08-27", "afternoon", p, runs_dir=tmp_path, accepted={})
    f = next(f for f in res.findings if f.check == "db_health_warnings")
    assert f.kind == doc.ENV
    assert not f.needs_code_change


def test_the_same_warning_on_different_dates_shares_an_id(tmp_path):
    """Recurrence is derived by matching ids across runs. If the dates inside
    the message made each day's lag a distinct id, a warning recurring every
    session would never accumulate a streak and could never promote."""
    a = with_health(tmp_path, "2026-08-26", "afternoon", dict(
        HEALTHY, warnings=["adj factors lag prices (2026-08-25 < 2026-08-26)"]))
    b = with_health(tmp_path, "2026-08-27", "afternoon", dict(
        HEALTHY, warnings=["adj factors lag prices (2026-08-26 < 2026-08-27)"]))
    ra = doc.audit_run("2026-08-26", "afternoon", a, runs_dir=tmp_path, accepted={})
    rb = doc.audit_run("2026-08-27", "afternoon", b, runs_dir=tmp_path, accepted={})
    ida = next(f.id for f in ra.findings if f.check == "db_health_warnings")
    idb = next(f.id for f in rb.findings if f.check == "db_health_warnings")
    assert ida == idb


def test_distinct_warnings_do_not_collide(tmp_path):
    """Folding by id must not merge two unrelated problems into one."""
    p = with_health(tmp_path, "2026-08-27", "afternoon", dict(HEALTHY, warnings=[
        "adj factors lag prices (2026-08-26 < 2026-08-27)",
        "partial day detected: 2026-08-20 has 141 rows",
    ]))
    res = doc.audit_run("2026-08-27", "afternoon", p, runs_dir=tmp_path, accepted={})
    ids = {f.id for f in res.findings if f.check == "db_health_warnings"}
    assert len(ids) == 2, ids


def test_a_spot_check_that_verified_nothing_is_reported(tmp_path):
    """2026-08-27 afternoon really shipped `checked: 0, fetch_failures: 20`
    under `ok: true`. A spot audit that confirmed nothing is not a pass — it is
    the absence of a pass, which is exactly the lie this layer exists to catch."""
    p = with_health(tmp_path, "2026-08-27", "afternoon", dict(
        HEALTHY, spot_check={"date": "2026-08-27", "sampled": 20, "checked": 0,
                             "fetch_failures": 20, "mismatches": []}))
    res = doc.audit_run("2026-08-27", "afternoon", p, runs_dir=tmp_path, accepted={})
    assert any(f.check == "db_health_spot_check" for f in res.findings)


def test_a_missing_db_health_is_skipped_with_a_reason_not_passed(tmp_path):
    """Legacy runs predate the artifact. Silently passing on a missing input is
    the failure mode the whole skipped-with-reason design exists to prevent."""
    p = with_health(tmp_path, "2026-02-10", "afternoon", None)
    res = doc.audit_run("2026-02-10", "afternoon", p, runs_dir=tmp_path, accepted={})
    skipped = {s["check"]: s["reason"] for s in res.skipped}
    assert "check_db_health_warnings" in skipped
    assert "db_health" in skipped["check_db_health_warnings"]
