"""--reset-to must roll back the portfolio BOOK only, and lose no closed trade.

Before 2026-10-12 restore_snapshot unlinked every tracking/*.json except
positions.json + portfolio_config.json (taking hypotheses.json, events.json,
rotation_ledger.json, event_inbox_ledger.json with it — none are in the
snapshot), then rewrote tracking/closed/ from the snapshot's closed SUMMARY:
keyed by code (a code traded twice collapsed to one file), no history, and
named {code}.json instead of {code}_{exitDate}.json.

Since the 2026-10-12 layout move the book is tracking/book/ (active/, closed/,
positions.json, config.json); the non-position state sits in ledgers/ and
calendar/, out of reach of any book glob. Snapshots written before the move
have the same format and must restore the same way.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import position_manager as pm
import run_daily
import run_paths
from tracking_paths import Layout

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
def lay(tmp_path, monkeypatch):
    """A temp tracking/ tree; every path global the reset reaches is rebound."""
    lay = Layout(tmp_path / "tracking").make_dirs()
    runs = tmp_path / "runs"
    monkeypatch.setattr(pm, "ACTIVE_DIR", lay.active)
    monkeypatch.setattr(pm, "CLOSED_DIR", lay.closed)
    monkeypatch.setattr(pm, "POSITIONS_FILE", lay.positions)
    monkeypatch.setattr(pm, "PORTFOLIO_CONFIG_FILE", lay.config)
    monkeypatch.setattr(run_daily, "TRACKING_DIR", lay.root)
    monkeypatch.setattr(run_daily, "LEDGERS_DIR", lay.ledgers)
    monkeypatch.setattr(run_daily, "CALENDAR_DIR", lay.calendar)
    monkeypatch.setattr(run_daily, "HYPOTHESES_FILE", lay.hypotheses)
    monkeypatch.setattr(run_daily, "LEARNINGS_FILE", tmp_path / "LEARNINGS.md")
    monkeypatch.setattr(run_daily, "RUNS_DIR", runs)
    monkeypatch.setattr(run_paths, "RUNS_DIR", runs)
    return lay


@pytest.fixture
def book(lay):
    """book/active/ — where the per-code position files live."""
    return lay.active


@pytest.fixture
def closed(lay):
    return lay.closed


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


def _seed_non_position(lay: Layout) -> dict[Path, bytes]:
    _dump(lay.hypotheses, {"hypotheses": [{"id": "H1"}]})
    _dump(lay.events, {"events": [{"name": "CPI"}]})
    _dump(lay.rotation_ledger, [{"date": "2026-10-10", "candidates": []}])
    _dump(lay.event_inbox_ledger, {"items": {"x": {"decision": "keep"}}})
    lay.predictions.write_text('{"p": 1}\n{"p": 2}\n', encoding="utf-8")
    lay.event_inbox.write_text("# inbox\n- [ ] item\n", encoding="utf-8")
    (lay.root / "README.md").write_text("# tracking\n", encoding="utf-8")
    return {f: f.read_bytes() for f in lay.root.rglob("*")
            if f.is_file() and lay.book not in f.parents}


def test_reset_leaves_non_position_state_untouched(lay, book, tmp_path):
    before = _seed_non_position(lay)
    _dump(book / "600001.json", _position("600001", "2026-10-01"))
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [_position("600001", "2026-10-01")])

    run_daily.reset_to_date(TARGET)

    for f, raw in before.items():
        assert f.read_bytes() == raw, f"{f.name} was rewritten or deleted"


def test_closed_trade_on_or_before_target_stays_byte_identical(closed, tmp_path):
    old = closed / "600002_2026-10-08.json"
    _dump(old, _position("600002", "2026-09-20", "closed", "2026-10-08", "noon"))
    legacy = closed / "600003.json"   # pre-2026-08-06 undated name
    _dump(legacy, _position("600003", "2026-07-01", "closed", "2026-07-15"))
    raw = {old: old.read_bytes(), legacy: legacy.read_bytes()}
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])

    run_daily.reset_to_date(TARGET)

    assert {p: p.read_bytes() for p in raw} == raw
    assert sorted(f.name for f in closed.iterdir()) == [
        "600002_2026-10-08.json", "600003.json"]


def test_two_closed_trades_in_same_code_both_survive(closed, tmp_path):
    a = closed / "600004_2026-08-10.json"
    b = closed / "600004_2026-09-15.json"
    _dump(a, _position("600004", "2026-08-01", "closed", "2026-08-10"))
    _dump(b, _position("600004", "2026-09-01", "closed", "2026-09-15"))
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])

    run_daily.reset_to_date(TARGET)

    assert a.exists() and b.exists()


def test_trade_closed_after_target_is_removed_and_reopened(book, closed, tmp_path):
    held = _position("600005", "2026-10-01")
    held["history"].append({"date": TARGET, "price": 10.5, "action": "HOLD"})
    later = closed / "600005_2026-10-12.json"
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


def test_noon_reset_reopens_trade_closed_by_that_days_afternoon_run(book, closed, tmp_path):
    held = _position("600007", "2026-10-01")
    same_day = closed / f"600007_{TARGET}.json"
    _dump(same_day, _position("600007", "2026-10-01", "closed", TARGET, "afternoon"))
    _snapshot(tmp_path / "runs", TARGET, "noon", [held])

    run_daily.reset_to_date(TARGET, slot="noon")

    assert not same_day.exists()
    assert (book / "600007.json").exists()


def test_afternoon_reset_keeps_trade_closed_that_day(closed, tmp_path):
    same_day = closed / f"600008_{TARGET}.json"
    _dump(same_day, _position("600008", "2026-10-01", "closed", TARGET, "noon"))
    raw = same_day.read_bytes()
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])

    run_daily.reset_to_date(TARGET)

    assert same_day.read_bytes() == raw


def test_positions_json_and_config_are_restored(lay, tmp_path):
    _dump(lay.positions, {"activePositions": [{"code": "999999"}]})
    _dump(lay.config, {"starting_capital": 1})
    pj = {"activePositions": [{"code": "600009"}], "portfolio": {"cash": 1.0}}
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [_position("600009", "2026-10-01")], pj)

    run_daily.reset_to_date(TARGET)

    assert json.loads(lay.positions.read_text(encoding="utf-8")) == pj
    assert json.loads(lay.config.read_text(encoding="utf-8")) == {"starting_capital": 1000000}


def _all_bytes(root: Path) -> dict:
    return {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_missing_snapshot_fails_loudly_and_deletes_nothing(lay, book, closed, tmp_path, capsys):
    _seed_non_position(lay)
    _dump(book / "600010.json", _position("600010", "2026-10-01"))
    _dump(closed / "600011_2026-10-12.json",
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


def test_malformed_snapshot_fails_loudly_and_deletes_nothing(lay, book, tmp_path, capsys):
    _seed_non_position(lay)
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


def test_reset_prints_plan_and_names_state_it_does_not_roll_back(lay, book, tmp_path, capsys):
    _seed_non_position(lay)
    _dump(book / "600013.json", _position("600013", "2026-10-12"))
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])

    run_daily.reset_to_date(TARGET)

    err = capsys.readouterr().err
    assert "600013.json" in err
    not_rolled = next(l for l in err.splitlines() if "NOT rolled back" in l)
    for name in ("calendar/events.json", "ledgers/rotation_ledger.json",
                 "calendar/event_inbox_ledger.json", "ledgers/predictions.jsonl",
                 "calendar/event_inbox.md"):
        assert name in not_rolled


def test_is_position_record_shape():
    assert pm.is_position_record({"code": "600001", "status": "active"})
    assert not pm.is_position_record([{"code": "600001", "status": "active"}])
    assert not pm.is_position_record({"events": []})
    assert not pm.is_position_record({"code": "600001"})


def test_hypotheses_roll_back_only_from_the_runs_own_copy(lay, tmp_path, capsys):
    # restore_aux_state (pre-existing) restores hypotheses.json from the run's
    # output/hypotheses_snapshot.json; the reset itself never deletes it.
    _seed_non_position(lay)
    out = _snapshot(tmp_path / "runs", TARGET, "afternoon", [])
    _dump(out / "hypotheses_snapshot.json", {"hypotheses": [{"id": "H0"}]})

    run_daily.reset_to_date(TARGET)

    assert json.loads(lay.hypotheses.read_text(encoding="utf-8")) == {
        "hypotheses": [{"id": "H0"}]}
    not_rolled = next(l for l in capsys.readouterr().err.splitlines() if "NOT rolled back" in l)
    assert "hypotheses.json" not in not_rolled


def test_snapshot_that_contradicts_closed_book_aborts_before_any_change(closed, tmp_path, capsys):
    # held from before the target to after it, yet missing from the snapshot:
    # deleting the closed file would lose the trade with nothing to restore
    _dump(closed / "600014_2026-10-12.json",
          _position("600014", "2026-10-01", "closed", "2026-10-12"))
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])
    before = _all_bytes(tmp_path)

    with pytest.raises(SystemExit):
        run_daily.reset_to_date(TARGET)

    assert "nothing changed" in capsys.readouterr().err
    assert _all_bytes(tmp_path) == before


def test_book_is_written_before_later_run_dirs_are_deleted(book, tmp_path, monkeypatch):
    # A failed book write must leave the later runs (and their snapshots) on
    # disk, so the reset can be re-run. Before 2026-10-12 the run dirs went first.
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [_position("600015", "2026-10-01")])
    later_run = tmp_path / "runs" / "2026-10-12" / "noon" / "output"
    later_run.mkdir(parents=True)

    def broken_write(path, data):
        raise OSError("disk full")
    monkeypatch.setattr(pm, "_write_json", broken_write)

    with pytest.raises(OSError):
        run_daily.reset_to_date(TARGET)

    assert later_run.is_dir()


def test_later_run_dirs_are_deleted_after_a_good_reset(book, tmp_path):
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])
    later_run = tmp_path / "runs" / "2026-10-12"
    (later_run / "noon").mkdir(parents=True)

    run_daily.reset_to_date(TARGET)

    assert not later_run.exists()


def test_a_non_position_file_in_active_dir_aborts_the_reset(book, tmp_path, capsys):
    # book/active/ holds positions only; a stray state file there is a defect
    # to stop on, never a file to skip (skipping is how the old root glob
    # reached the ledgers).
    _dump(book / "stray.json", {"events": []})
    _snapshot(tmp_path / "runs", TARGET, "afternoon", [])
    before = _all_bytes(tmp_path)

    with pytest.raises(SystemExit):
        run_daily.reset_to_date(TARGET)

    assert "not a position record" in capsys.readouterr().err
    assert _all_bytes(tmp_path) == before


REAL_PRE_MOVE_SNAPSHOT = (Path(__file__).resolve().parent.parent / "runs" / "2026-10-09"
                          / "afternoon" / "output" / "positions_snapshot.json")


def test_snapshot_written_before_the_layout_move_restores_into_the_new_layout(lay, tmp_path):
    # Written by the pre-move code (tracking/{code}.json era). The format does
    # not depend on the layout; it must restore into book/ unchanged.
    snap = json.loads(REAL_PRE_MOVE_SNAPSHOT.read_text(encoding="utf-8"))
    out = tmp_path / "runs" / "2026-10-09" / "afternoon" / "output"
    out.mkdir(parents=True)
    (out / "positions_snapshot.json").write_bytes(REAL_PRE_MOVE_SNAPSHOT.read_bytes())

    run_daily.reset_to_date("2026-10-09")

    assert sorted(f.name for f in lay.active.iterdir()) == sorted(
        f"{c}.json" for c in snap["active_positions"])
    for code, pos in snap["active_positions"].items():
        assert json.loads((lay.active / f"{code}.json").read_text(encoding="utf-8")) == pos
    assert json.loads(lay.positions.read_text(encoding="utf-8")) == snap["positions_json"]
    assert json.loads(lay.config.read_text(encoding="utf-8")) == snap["portfolio_config"]
