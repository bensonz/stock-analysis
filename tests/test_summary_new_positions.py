"""`daily_summary.newPositions` must record what was OPENED, not what was WANTED.

The doctor's first sweep found this on 8 dates across 6 months — 03-11 (×3),
04-08, 06-09 (×2), 07-14, 07-31, 08-04, 08-17, 08-20. Every one names a stock
that `positions_snapshot.activePositions` does not hold, and T+1 forbids the
innocent explanation of opening and closing the same day.

`run_daily.py` builds the field from `allowed_new_positions` — the *intent*
list — while stamping `_not_opened` onto those very dicts 45 lines earlier for
the report to filter on. So on 2026-08-20 the report said, correctly, that
688222 was blocked at 涨停, and the machine-readable artifact two files over
said it was a new position. 688019 in August is the same defect: we corrected
the report prose and left this field lying, which is why 688222 repeated it
three days later.

Blocked candidates are not dropped — they move to `blockedOpens` with the
reason. Deleting them would trade one silent lie for another, and the entry
filter working correctly is exactly the thing worth being able to audit.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import run_daily as rd


def summarise(candidates):
    """The transform under test, as run_daily applies it at the summary write."""
    return (rd.opened_new_positions(candidates),
            rd.blocked_new_positions(candidates))


def test_a_blocked_candidate_is_not_reported_as_a_new_position():
    """2026-08-20: 688222 rejected at 涨停 yet listed as opened."""
    opened, blocked = summarise([
        {"code": "688222", "name": "成都先导",
         "_not_opened": "涨停 (change 13.17%), cannot buy at daily limit"},
    ])
    assert opened == []
    assert blocked == [{"code": "688222", "name": "成都先导",
                        "reason": "涨停 (change 13.17%), cannot buy at daily limit"}]


def test_an_actually_opened_position_is_reported():
    opened, blocked = summarise([{"code": "688981", "name": "中芯国际"}])
    assert opened == [{"code": "688981", "name": "中芯国际"}]
    assert blocked == []


def test_a_mixed_batch_splits_correctly():
    """2026-08-04 shape: four intents, one of which never opened."""
    opened, blocked = summarise([
        {"code": "002138", "name": "顺络电子"},
        {"code": "300001", "name": "特锐德"},
        {"code": "600885", "name": "宏发股份"},
        {"code": "000739", "name": "普洛药业", "_not_opened": "sizing produced 0 shares"},
    ])
    assert [p["code"] for p in opened] == ["002138", "300001", "600885"]
    assert [p["code"] for p in blocked] == ["000739"]


def test_exchange_suffixes_are_stripped_on_both_sides():
    """The snapshot stores bare 6-digit codes; a mismatch here would reintroduce
    the very disagreement this fixes."""
    opened, blocked = summarise([
        {"code": "688981.SH", "name": "中芯国际"},
        {"code": "300750.SZ", "name": "宁德时代", "_not_opened": "no entry price"},
    ])
    assert opened[0]["code"] == "688981"
    assert blocked[0]["code"] == "300750"


def test_blocked_reason_is_carried_not_flattened_to_a_flag():
    """'Why not' is the audit trail — a bare boolean would lose it."""
    _opened, blocked = summarise([
        {"code": "000739", "name": "x", "_not_opened": "ST board limit 5%"},
    ])
    assert blocked[0]["reason"] == "ST board limit 5%"


def test_empty_input_yields_empty_lists_not_none():
    """Consumers must be able to rely on the shape; None would make an absent
    field and a genuinely empty one indistinguishable."""
    assert summarise([]) == ([], [])


def test_the_written_summary_carries_both_fields(tmp_path):
    """End-to-end at the artifact: what the doctor actually reads."""
    import position_manager as pm
    candidates = [
        {"code": "688981", "name": "中芯国际"},
        {"code": "688222", "name": "成都先导", "_not_opened": "涨停, cannot buy"},
    ]
    pm.save_daily_summary(
        "2026-08-20", [], output_dir=tmp_path,
        newPositions=rd.opened_new_positions(candidates),
        blockedOpens=rd.blocked_new_positions(candidates))

    got = json.loads((tmp_path / "daily_summary.json").read_text(encoding="utf-8"))
    assert [p["code"] for p in got["newPositions"]] == ["688981"]
    assert [p["code"] for p in got["blockedOpens"]] == ["688222"]


def test_doctor_passes_on_the_fixed_shape_and_still_fails_on_the_old_one(tmp_path):
    """The regression, closed at the artifact the doctor reads.

    The writer deliberately keeps using `_not_opened` (the execution outcome)
    rather than reading positions.json, so the doctor's snapshot comparison
    stays an INDEPENDENT check. Sourcing both sides from the same file would
    make the check tautological and unable to catch the next disagreement.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import doctor as doc

    def build(new_positions):
        p = tmp_path / ("run" + str(len(list(tmp_path.iterdir())))) / "noon"
        (p / "output").mkdir(parents=True)
        (p / "manifest.json").write_text(json.dumps(
            {"date": "2026-08-20", "slot": "noon", "status": "success",
             "run_started_at": "2026-08-20T11:35:00+08:00"}), encoding="utf-8")
        (p / "output" / "report.md").write_text("#\n", encoding="utf-8")
        (p / "output" / "daily_summary.json").write_text(json.dumps(
            {"actions": [], "newPositions": new_positions}), encoding="utf-8")
        (p / "output" / "positions_snapshot.json").write_text(json.dumps(
            {"snapshot_type": "post_run",
             "positions_json": {"lastUpdated": "2026-08-20T11:42:00+08:00",
                                "activePositions": [{"code": "000703"}]}}),
            encoding="utf-8")
        return p

    candidates = [{"code": "688222", "name": "x", "_not_opened": "涨停"}]

    old = doc.audit_run("2026-08-20", "noon",
                        build([{"code": "688222", "name": "x"}]),
                        runs_dir=tmp_path, accepted={})
    assert "new-position-not-held:688222" in [f.id for f in old.code_findings]

    new = doc.audit_run("2026-08-20", "noon",
                        build(rd.opened_new_positions(candidates)),
                        runs_dir=tmp_path, accepted={})
    assert new.code_findings == []
