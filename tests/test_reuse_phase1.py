"""run_daily.load_saved_phase1 — `--run --reuse-phase1` re-runs a slot from its
saved collection instead of fetching again.

A Gate 2 failure (2026-10-13 afternoon: LLM omitted `target`) leaves the book
untouched, so the slot's phase-1 data is still the truth; re-collecting cost
~4 min for nothing. The loader refuses anything it cannot prove is the same
slot with the same book.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import run_daily

BOOK = {"active_positions": {"600001": {"code": "600001"}},
        "closed_positions": {"000002": {"code": "000002"}}}


def _snapshot(book):
    return lambda snapshot_type, date: {"snapshot_type": snapshot_type, "date": date, **book}


@pytest.fixture
def run_dir(tmp_path):
    (tmp_path / "input").mkdir()
    (tmp_path / "phase1.json").write_text(json.dumps(
        {"date": "2026-10-13", "slot": "afternoon",
         "_log_phase1": {"start": 1.0, "duration_sec": 191.9}}), encoding="utf-8")
    (tmp_path / "input" / "positions_snapshot.json").write_text(json.dumps(BOOK), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps(
        {"phases": {"preflight_pricedb": {"status": "ok", "latest_date": "2026-10-13"}}}),
        encoding="utf-8")
    return tmp_path


def test_reuse_reattaches_the_keys_the_save_strips(run_dir):
    data, _ = run_daily.load_saved_phase1(run_dir, "2026-10-13", "afternoon", _snapshot(BOOK))
    assert {"learnings", "hypothesis_prompt", "_hypothesis_data"} <= set(data)


def test_reuse_returns_the_prior_manifest_phases(run_dir):
    _, phases = run_daily.load_saved_phase1(run_dir, "2026-10-13", "afternoon", _snapshot(BOOK))
    assert phases["preflight_pricedb"]["latest_date"] == "2026-10-13"


def test_missing_phase1_is_refused_naming_the_file(run_dir):
    (run_dir / "phase1.json").unlink()
    with pytest.raises(run_daily.ReusePhase1Error, match="phase1.json"):
        run_daily.load_saved_phase1(run_dir, "2026-10-13", "afternoon", _snapshot(BOOK))


def test_another_date_is_refused(run_dir):
    with pytest.raises(run_daily.ReusePhase1Error, match="2026-10-13"):
        run_daily.load_saved_phase1(run_dir, "2026-10-14", "afternoon", _snapshot(BOOK))


def test_another_slot_is_refused(run_dir):
    with pytest.raises(run_daily.ReusePhase1Error, match="noon"):
        run_daily.load_saved_phase1(run_dir, "2026-10-13", "noon", _snapshot(BOOK))


def test_a_moved_book_is_refused(run_dir):
    moved = {**BOOK, "active_positions": {}}
    with pytest.raises(run_daily.ReusePhase1Error, match="book changed"):
        run_daily.load_saved_phase1(run_dir, "2026-10-13", "afternoon", _snapshot(moved))


def test_missing_snapshot_is_refused(run_dir):
    (run_dir / "input" / "positions_snapshot.json").unlink()
    with pytest.raises(run_daily.ReusePhase1Error, match="positions_snapshot"):
        run_daily.load_saved_phase1(run_dir, "2026-10-13", "afternoon", _snapshot(BOOK))
