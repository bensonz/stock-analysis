"""A run leaves a record from its first second (2026-11-21).

2026-11-04 afternoon was killed mid-LLM call and 2026-11-11 noon hung 4h20m
with the network down; both left the doctor with no manifest to read.
"""
import json
import signal
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import run_daily
from contracts import PipelineStatus, RunManifest


@pytest.fixture
def manifest():
    m = RunManifest(date="2026-11-23", status=PipelineStatus.SUCCESS, slot="noon",
                    run_started_at="2026-11-23T11:35:00+08:00")
    m.add_phase("health_check", "ok", details={"sources": {}})
    return m


@pytest.fixture(autouse=True)
def restore_sigterm():
    old = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGTERM, old)


def test_start_marker_reads_failed_until_the_run_finishes(tmp_path, manifest):
    run_daily.begin_run_record(manifest, tmp_path / "run")
    on_disk = json.loads((tmp_path / "run" / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk["status"] == "failed"
    assert on_disk["phases"]["unfinished"]["errors"][0].startswith("CRITICAL:")
    assert on_disk["phases"]["health_check"]["status"] == "ok"
    # the live manifest is untouched: its real outcome is decided later
    assert "unfinished" not in manifest.phases
    assert manifest.status == PipelineStatus.SUCCESS


def test_sigterm_writes_a_failed_manifest_naming_the_kill(tmp_path, manifest, monkeypatch):
    monkeypatch.setattr(run_daily, "refresh_site", lambda: None)
    run_daily.begin_run_record(manifest, tmp_path)
    handler = signal.getsignal(signal.SIGTERM)
    with pytest.raises(SystemExit) as e:
        handler(signal.SIGTERM, None)
    assert e.value.code == 128 + signal.SIGTERM
    on_disk = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk["status"] == "failed"
    assert "unfinished" not in on_disk["phases"]
    assert "killed by signal" in on_disk["phases"]["killed"]["errors"][0]


def test_all_sources_down_needs_both_feeds_down():
    ok, down = {"status": "ok"}, {"status": "down"}
    assert run_daily.all_external_sources_down({"sina": down, "cheesefortune": down, "pricedb": ok})
    assert run_daily.all_external_sources_down({})          # no health data = nothing ok
    assert not run_daily.all_external_sources_down({"sina": ok, "cheesefortune": down})
    assert not run_daily.all_external_sources_down({"sina": down, "cheesefortune": ok})
