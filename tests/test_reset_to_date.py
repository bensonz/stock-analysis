"""--reset-to must roll back the portfolio BOOK only, and lose no closed trade.

Before 2026-10-12 restore_snapshot unlinked every tracking/*.json except
positions.json + portfolio_config.json (taking hypotheses.json, events.json,
rotation_ledger.json, event_inbox_ledger.json with it — none are in the
snapshot), then rewrote tracking/closed/ from the snapshot's closed SUMMARY:
keyed by code (a code traded twice collapsed to one file), no history, and
named {code}.json instead of {code}_{exitDate}.json.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import position_manager as pm
import run_daily
import run_paths

TARGET = "2026-10-09"


def _dump(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _position(code, entry, status="active", exit_date=None, slot=None):
    hist = [{"date": entry, "price": 10.0, "action": "BUY"}]
    pos = {"code": code, "name": f"N{code}", "status": status,
           "entryDate": entry, "entryPrice": 10.0, "shares": 100, "history": hist}
    if exit_date:
        pos.update(exitDate=exit_date, exitPrice=11.0, returnPct=10.0)
        if slot:
            pos["exitSlot"] = slot
        hist.append({"date": exit_date, "price": 11.0, "action": "SELL"})
    return pos


@pytest.fixture
def book(tmp_path, monkeypatch):
    tracking = tmp_path / "tracking"
    closed = tracking / "closed"
    closed.mkdir(parents=True)
    runs = tmp_path / "runs"
    for mod in (pm, run_daily):
        monkeypatch.setattr(mod, "TRACKING_DIR", tracking)
        monkeypatch.setattr(mod, "CLOSED_DIR", closed)
        monkeypatch.setattr(mod, "POSITIONS_FILE", tracking / "positions.json")
        monkeypatch.setattr(mod, "PORTFOLIO_CONFIG_FILE", tracking / "portfolio_config.json")
    monkeypatch.setattr(run_daily, "HYPOTHESES_FILE", tracking / "hypotheses.json")
    monkeypatch.setattr(run_daily, "LEARNINGS_FILE", tmp_path / "LEARNINGS.md")
    monkeypatch.setattr(run_daily, "RUNS_DIR", runs)
    monkeypatch.setattr(run_paths, "RUNS_DIR", runs)
    return tracking


def _snapshot(runs: Path, date: str, slot: str, active: list[dict], positions_json=None):
    out = runs / date / slot / "output"
    out.mkdir(parents=True)
    snap = {
        "snapshot_type": "post_run", "date": date,
        "portfolio_config": {"starting_capital": 1000000},
        "positions_json": positions_json or {"activePositions": [
            {"code": p["code"]} for p in active]},
        "active_positions": {p["code"]: p for p in active},
        # the summary the OLD restore rewrote closed/ from: keyed by code
        "closed_positions": {},
    }
    _dump(out / "positions_snapshot.json", snap)
    return out


NON_POSITION = {
    "hypotheses.json": {"hypotheses": [{"id": "H1"}]},
    "events.json": {"events": [{"name": "CPI"}]},
    "rotation_ledger.json": [{"date": "2026-10-10", "candidates": []}],
    "event_inbox_ledger.json": {"items": {"x": {"decision": "keep"}}},
}


def _seed_non_position(tracking: Path) -> dict[str, bytes]:
    for name, data in NON_POSITION.items():
        _dump(tracking / name, data)
    (tracking / "predictions.jsonl").write_text('{"p": 1}\n{"p": 2}\n', encoding="utf-8")
    (tracking / "event_inbox.md").write_text("# inbox\n- [ ] item\n", encoding="utf-8")
    return {f.name: f.read_bytes() for f in tracking.iterdir() if f.is_file()}


def test_reset_leaves_non_position_state_untouched(book, tmp_path):
    before = _seed_non_position(book)
    _dump(book / "600001.json", _position("600001", "2026-10-01"))
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [_position("600001", "2026-10-01")])

    run_daily.reset_to_date(TARGET)

    for name, raw in before.items():
        assert (book / name).read_bytes() == raw, f"{name} was rewritten or deleted"


def test_closed_trade_on_or_before_target_stays_byte_identical(book, tmp_path):
    old = book / "closed" / "600002_2026-10-08.json"
    _dump(old, _position("600002", "2026-09-20", "closed", "2026-10-08", "noon"))
    legacy = book / "closed" / "600003.json"   # pre-2026-08-06 undated name
    _dump(legacy, _position("600003", "2026-07-01", "closed", "2026-07-15"))
    raw = {old: old.read_bytes(), legacy: legacy.read_bytes()}
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])

    run_daily.reset_to_date(TARGET)

    assert {p: p.read_bytes() for p in raw} == raw
    assert sorted(f.name for f in (book / "closed").iterdir()) == [
        "600002_2026-10-08.json", "600003.json"]


def test_two_closed_trades_in_same_code_both_survive(book, tmp_path):
    a = book / "closed" / "600004_2026-08-10.json"
    b = book / "closed" / "600004_2026-09-15.json"
    _dump(a, _position("600004", "2026-08-01", "closed", "2026-08-10"))
    _dump(b, _position("600004", "2026-09-01", "closed", "2026-09-15"))
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])

    run_daily.reset_to_date(TARGET)

    assert a.exists() and b.exists()


def test_trade_closed_after_target_is_removed_and_reopened(book, tmp_path):
    held = _position("600005", "2026-10-01")
    held["history"].append({"date": TARGET, "price": 10.5, "action": "HOLD"})
    later = book / "closed" / "600005_2026-10-12.json"
    _dump(later, {**held, "status": "closed", "exitDate": "2026-10-12", "exitPrice": 9.0})
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [held])

    run_daily.reset_to_date(TARGET)

    assert not later.exists()
    assert json.loads((book / "600005.json").read_text(encoding="utf-8")) == held


def test_position_opened_after_target_is_removed(book, tmp_path):
    _dump(book / "600006.json", _position("600006", "2026-10-12"))
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])

    run_daily.reset_to_date(TARGET)

    assert not (book / "600006.json").exists()


def test_noon_reset_reopens_trade_closed_by_that_days_afternoon_run(book, tmp_path):
    held = _position("600007", "2026-10-01")
    same_day = book / "closed" / f"600007_{TARGET}.json"
    _dump(same_day, _position("600007", "2026-10-01", "closed", TARGET, "afternoon"))
    _snapshot(tmp_path / "runs", TARGET, "noon", [held])

    run_daily.reset_to_date(TARGET, slot="noon")

    assert not same_day.exists()
    assert (book / "600007.json").exists()


def test_afternoon_reset_keeps_trade_closed_that_day(book, tmp_path):
    same_day = book / "closed" / f"600008_{TARGET}.json"
    _dump(same_day, _position("600008", "2026-10-01", "closed", TARGET, "noon"))
    raw = same_day.read_bytes()
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])

    run_daily.reset_to_date(TARGET)

    assert same_day.read_bytes() == raw


def test_positions_json_is_restored(book, tmp_path):
    _dump(book / "positions.json", {"activePositions": [{"code": "999999"}]})
    pj = {"activePositions": [{"code": "600009"}], "portfolio": {"cash": 1.0}}
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [_position("600009", "2026-10-01")], pj)

    run_daily.reset_to_date(TARGET)

    assert json.loads((book / "positions.json").read_text(encoding="utf-8")) == pj


def _all_bytes(root: Path) -> dict:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_missing_snapshot_fails_loudly_and_deletes_nothing(book, tmp_path, capsys):
    _seed_non_position(book)
    _dump(book / "600010.json", _position("600010", "2026-10-01"))
    _dump(book / "closed" / "600011_2026-10-12.json",
          _position("600011", "2026-10-01", "closed", "2026-10-12"))
    later_run = tmp_path / "runs" / "2026-10-12" / "noon" / "output"
    later_run.mkdir(parents=True)
    before = _all_bytes(tmp_path)

    with pytest.raises(SystemExit) as exc:
        run_daily.reset_to_date(TARGET)

    assert exc.value.code == 1
    assert "No snapshot found" in capsys.readouterr().err
    assert _all_bytes(tmp_path) == before
    assert later_run.is_dir()


def test_malformed_snapshot_fails_loudly_and_deletes_nothing(book, tmp_path, capsys):
    _seed_non_position(book)
    _dump(book / "600012.json", _position("600012", "2026-10-01"))
    out = _snapshot(tmp_path / "runs", TARGET, "afternoon", [])
    snap = json.loads((out / "positions_snapshot.json").read_text(encoding="utf-8"))
    del snap["positions_json"]
    _dump(out / "positions_snapshot.json", snap)
    later_run = tmp_path / "runs" / "2026-10-12" / "noon"
    later_run.mkdir(parents=True)
    before = _all_bytes(tmp_path)

    with pytest.raises(SystemExit) as exc:
        run_daily.reset_to_date(TARGET)

    assert exc.value.code == 1
    assert "positions_json" in capsys.readouterr().err
    assert _all_bytes(tmp_path) == before
    assert later_run.is_dir()


def test_reset_prints_plan_and_names_state_it_does_not_roll_back(book, tmp_path, capsys):
    _seed_non_position(book)
    _dump(book / "600013.json", _position("600013", "2026-10-12"))
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])

    run_daily.reset_to_date(TARGET)

    err = capsys.readouterr().err
    assert "600013.json" in err
    not_rolled = next(l for l in err.splitlines() if "NOT rolled back" in l)
    for name in ("events.json", "rotation_ledger.json", "event_inbox_ledger.json",
                 "predictions.jsonl", "event_inbox.md"):
        assert name in not_rolled


def test_is_position_record_shape():
    assert pm.is_position_record({"code": "600001", "status": "active"})
    assert not pm.is_position_record([{"code": "600001", "status": "active"}])
    assert not pm.is_position_record({"events": []})
    assert not pm.is_position_record({"code": "600001"})


def test_hypotheses_roll_back_only_from_the_runs_own_copy(book, tmp_path, capsys):
    # restore_aux_state (pre-existing) restores hypotheses.json from the run's
    # output/hypotheses_snapshot.json; the reset itself never deletes it.
    _seed_non_position(book)
    out = _snapshot(tmp_path / "runs", TARGET, "afternoon", [])
    _dump(out / "hypotheses_snapshot.json", {"hypotheses": [{"id": "H0"}]})

    run_daily.reset_to_date(TARGET)

    assert json.loads((book / "hypotheses.json").read_text(encoding="utf-8")) == {
        "hypotheses": [{"id": "H0"}]}
    not_rolled = next(l for l in capsys.readouterr().err.splitlines() if "NOT rolled back" in l)
    assert "hypotheses.json" not in not_rolled


def test_snapshot_that_contradicts_closed_book_aborts_before_any_change(book, tmp_path, capsys):
    # held from before the target to after it, yet missing from the snapshot:
    # deleting the closed file would lose the trade with nothing to restore
    _dump(book / "closed" / "600014_2026-10-12.json",
          _position("600014", "2026-10-01", "closed", "2026-10-12"))
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])
    before = _all_bytes(tmp_path)

    with pytest.raises(SystemExit):
        run_daily.reset_to_date(TARGET)

    assert "nothing changed" in capsys.readouterr().err
    assert _all_bytes(tmp_path) == before
