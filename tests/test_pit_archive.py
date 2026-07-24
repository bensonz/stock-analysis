"""Unit tests for the PIT archiver mechanics (no network)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pit_archive as pit


def test_write_day_and_immutability(tmp_path):
    p = pit.write_day("src", "2026-07-01", [{"a": 1}], archive_dir=tmp_path)
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["rows"] == [{"a": 1}] and data["date"] == "2026-07-01"
    # second write must NOT overwrite (immutability)
    pit.write_day("src", "2026-07-01", [{"a": 999}], archive_dir=tmp_path)
    assert json.loads(p.read_text(encoding="utf-8"))["rows"] == [{"a": 1}]


def test_archived_dates(tmp_path):
    pit.write_day("src", "2026-07-01", [], archive_dir=tmp_path)
    pit.write_day("src", "2026-07-02", [], archive_dir=tmp_path)
    assert pit.archived_dates("src", tmp_path) == {"2026-07-01", "2026-07-02"}
    assert pit.archived_dates("other", tmp_path) == set()


def test_run_source_backfills_only_missing(tmp_path):
    pit.write_day("src", "2026-07-01", [{"old": True}], archive_dir=tmp_path)
    fetched = []

    def fetch(date_iso):
        fetched.append(date_iso)
        return [{"d": date_iso}]

    stats = pit.run_source("src", fetch, ["2026-07-01", "2026-07-02", "2026-07-03"],
                           archive_dir=tmp_path, sleep_sec=0)
    assert fetched == ["2026-07-02", "2026-07-03"]   # existing day untouched
    assert stats["written"] == 2 and stats["failed"] == 0


def test_run_source_archives_empty_days(tmp_path):
    stats = pit.run_source("src", lambda d: [], ["2026-07-01"],
                           archive_dir=tmp_path, sleep_sec=0)
    assert stats["written"] == 1 and stats["empty"] == 1
    assert (tmp_path / "src" / "2026-07-01.json").exists()


def test_run_source_circuit_breaker(tmp_path):
    def boom(date_iso):
        raise ConnectionError("banned")

    days = [f"2026-07-{i:02d}" for i in range(1, 11)]
    stats = pit.run_source("src", boom, days, archive_dir=tmp_path, sleep_sec=0)
    assert stats["aborted"] is True
    assert stats["failed"] == pit.MAX_CONSECUTIVE_FAILURES   # stopped early
    assert pit.archived_dates("src", tmp_path) == set()


def test_failure_then_recovery_resumes(tmp_path):
    calls = {"n": 0}

    def flaky(date_iso):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("transient")
        return [{"ok": True}]

    days = ["2026-07-01", "2026-07-02"]
    stats = pit.run_source("src", flaky, days, archive_dir=tmp_path, sleep_sec=0)
    assert stats["failed"] == 1 and stats["written"] == 1
    # rerun heals the failed day (backfill-first)
    stats2 = pit.run_source("src", flaky, days, archive_dir=tmp_path, sleep_sec=0)
    assert stats2["written"] == 1
    assert pit.archived_dates("src", tmp_path) == set(days)
