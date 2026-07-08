"""Tests for slot-aware run-directory partitioning (run_paths)."""

import json
from datetime import datetime

import pytest

import run_paths


@pytest.fixture
def runs(tmp_path, monkeypatch):
    """Point run_paths at a temp runs/ dir for isolation."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setattr(run_paths, "RUNS_DIR", runs_dir)
    return runs_dir


def _write_manifest(run_dir, slot, run_started_at):
    (run_dir / "manifest.json").write_text(
        json.dumps({"slot": slot, "run_started_at": run_started_at}) + "\n",
        encoding="utf-8",
    )


# 1. Both slots create distinct dirs and running both leaves BOTH intact.
def test_get_run_dir_slots_are_distinct_and_coexist(runs):
    noon = run_paths.get_run_dir("2026-07-08", "noon")
    afternoon = run_paths.get_run_dir("2026-07-08", "afternoon")

    assert noon != afternoon
    assert noon == runs / "2026-07-08" / "noon"
    assert afternoon == runs / "2026-07-08" / "afternoon"

    # Simulate each run writing an artifact; neither should clobber the other.
    (noon / "output" / "watchlist.json").write_text('{"slot": "noon"}', encoding="utf-8")
    (afternoon / "output" / "watchlist.json").write_text('{"slot": "afternoon"}', encoding="utf-8")

    assert (noon / "output" / "watchlist.json").exists()
    assert (afternoon / "output" / "watchlist.json").exists()
    assert json.loads((noon / "output" / "watchlist.json").read_text())["slot"] == "noon"
    assert json.loads((afternoon / "output" / "watchlist.json").read_text())["slot"] == "afternoon"


def test_get_run_dir_rejects_bad_slot(runs):
    with pytest.raises(ValueError):
        run_paths.get_run_dir("2026-07-08", "evening")


# 2. Slot auto-derivation from the clock.
def test_resolve_slot_from_clock():
    assert run_paths.resolve_slot(now=datetime(2026, 7, 8, 11, 35)) == "noon"
    assert run_paths.resolve_slot(now=datetime(2026, 7, 8, 15, 35)) == "afternoon"
    # Boundary: 13:00 sharp is afternoon.
    assert run_paths.resolve_slot(now=datetime(2026, 7, 8, 12, 59)) == "noon"
    assert run_paths.resolve_slot(now=datetime(2026, 7, 8, 13, 0)) == "afternoon"


# 3. --slot override wins over the clock.
def test_resolve_slot_override_wins():
    # Clock says afternoon, but the explicit override forces noon.
    assert run_paths.resolve_slot("noon", now=datetime(2026, 7, 8, 15, 35)) == "noon"
    assert run_paths.resolve_slot("afternoon", now=datetime(2026, 7, 8, 11, 35)) == "afternoon"
    with pytest.raises(ValueError):
        run_paths.resolve_slot("evening")


# 4. Latest-run discovery: afternoon canonical, sorted by run_started_at.
def test_find_run_dir_prefers_afternoon(runs):
    noon = run_paths.get_run_dir("2026-07-08", "noon")
    afternoon = run_paths.get_run_dir("2026-07-08", "afternoon")
    _write_manifest(noon, "noon", "2026-07-08T11:35:00+08:00")
    _write_manifest(afternoon, "afternoon", "2026-07-08T15:35:00+08:00")

    assert run_paths.find_run_dir("2026-07-08") == afternoon
    assert run_paths.find_run_dir("2026-07-08", "noon") == noon
    assert run_paths.find_run_dir("2026-07-08", "afternoon") == afternoon


def test_find_run_dir_noon_only(runs):
    noon = run_paths.get_run_dir("2026-07-08", "noon")
    _write_manifest(noon, "noon", "2026-07-08T11:35:00+08:00")

    # No afternoon yet -> noon is the only (thus canonical) run.
    assert run_paths.find_run_dir("2026-07-08") == noon
    # Explicitly requesting a missing slot returns None.
    assert run_paths.find_run_dir("2026-07-08", "afternoon") is None


def test_list_runs_sorted_by_run_started_at_not_slot_name(runs):
    """Regression guard: 'afternoon' < 'noon' alphabetically must NOT decide order."""
    # Day 1: only afternoon. Day 2: noon then afternoon (later).
    d1_pm = run_paths.get_run_dir("2026-07-07", "afternoon")
    d2_noon = run_paths.get_run_dir("2026-07-08", "noon")
    d2_pm = run_paths.get_run_dir("2026-07-08", "afternoon")
    _write_manifest(d1_pm, "afternoon", "2026-07-07T15:35:00+08:00")
    _write_manifest(d2_noon, "noon", "2026-07-08T11:35:00+08:00")
    _write_manifest(d2_pm, "afternoon", "2026-07-08T15:35:00+08:00")

    ordered = run_paths.list_runs_sorted()  # newest first
    dirs = [d for (_date, _slot, d) in ordered]
    assert dirs == [d2_pm, d2_noon, d1_pm]

    # The newest run overall is day-2 afternoon, not the alphabetically-first slot.
    assert ordered[0][1] == "afternoon"
    assert ordered[0][0] == "2026-07-08"


# 5. Legacy layout (no slot) is discovered as an afternoon run.
def test_legacy_layout_discovered_as_afternoon(runs):
    legacy = runs / "2026-06-30"
    (legacy / "output").mkdir(parents=True)
    (legacy / "output" / "watchlist.json").write_text("{}", encoding="utf-8")

    found = run_paths.iter_run_dirs()
    assert (("2026-06-30", "afternoon", legacy)) in found

    assert run_paths.find_run_dir("2026-06-30") == legacy
    assert run_paths.find_run_dir("2026-06-30", "afternoon") == legacy
    assert run_paths.find_run_dir("2026-06-30", "noon") is None


def test_new_slot_layout_takes_precedence_over_legacy(runs):
    """A date dir with a slot subdir is not double-counted as legacy."""
    date_dir = runs / "2026-07-01"
    afternoon = run_paths.get_run_dir("2026-07-01", "afternoon")
    # A stray output/ at the date level should be ignored once a slot exists.
    (date_dir / "output").mkdir(exist_ok=True)

    runs_found = run_paths.iter_run_dirs()
    date_runs = [t for t in runs_found if t[0] == "2026-07-01"]
    assert date_runs == [("2026-07-01", "afternoon", afternoon)]
