"""scripts/oneoff/migrate_tracking_layout.py — the one tracking/ layout move.

Each test builds a throwaway git repo in tmp_path with the OLD layout. The
script must: land every file where tracking_paths says it lives, be safe to
re-run, and refuse (changing nothing) when an old and a new path both exist
with different content, or when a root file has no rule.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "oneoff"))

import migrate_tracking_layout as mig
from tracking_paths import Layout


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout


def _dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")


def _position(code, status="active"):
    return {"code": code, "status": status, "entryDate": "2026-10-01"}


@pytest.fixture
def repo(tmp_path):
    """A git repo holding tracking/ in the pre-2026-10-12 layout."""
    t = tmp_path / "tracking"
    _dump(t / "601872.json", _position("601872"))
    _dump(t / "603259.json", _position("603259"))
    _dump(t / "closed" / "000739_2026-10-09.json", _position("000739", "closed"))
    _dump(t / "closed" / "600096.json", _position("600096", "closed"))  # legacy undated
    _dump(t / "positions.json", {"activePositions": []})
    _dump(t / "portfolio_config.json", {"starting_capital": 1000000})
    _dump(t / "hypotheses.json", {"hypotheses": []})
    (t / "predictions.jsonl").write_text('{"p": 1}\n', encoding="utf-8")
    _dump(t / "rotation_ledger.json", [])
    _dump(t / "events.json", {"events": []})
    (t / "event_inbox.md").write_text("# inbox\n", encoding="utf-8")
    _dump(t / "event_inbox_ledger.json", {"items": {}})
    (t / "README.md").write_text("# tracking\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
         "commit", "-q", "-m", "old layout")
    return tmp_path


def _tree(repo):
    t = repo / "tracking"
    return {str(f.relative_to(t)): f.read_bytes() for f in t.rglob("*") if f.is_file()}


def test_every_file_lands_where_tracking_paths_says(repo):
    before = _tree(repo)
    assert mig.main(["--root", str(repo), "--execute"]) == 0

    lay = Layout(repo / "tracking")
    t = repo / "tracking"
    expect = {
        lay.active / "601872.json": before["601872.json"],
        lay.active / "603259.json": before["603259.json"],
        lay.closed / "000739_2026-10-09.json": before["closed/000739_2026-10-09.json"],
        lay.closed / "600096.json": before["closed/600096.json"],
        lay.positions: before["positions.json"],
        lay.config: before["portfolio_config.json"],
        lay.hypotheses: before["hypotheses.json"],
        lay.predictions: before["predictions.jsonl"],
        lay.rotation_ledger: before["rotation_ledger.json"],
        lay.events: before["events.json"],
        lay.event_inbox: before["event_inbox.md"],
        lay.event_inbox_ledger: before["event_inbox_ledger.json"],
        t / "README.md": before["README.md"],
    }
    assert {f: f.read_bytes() for f in t.rglob("*") if f.is_file()} == expect
    assert not (t / "closed").exists()


def test_fixed_map_targets_match_tracking_paths():
    lay = Layout(Path("/x/tracking"))
    by_target = {lay.root / new: old for old, new in mig.FIXED.items()}
    assert set(by_target) == set(lay.files())
    assert lay.root / mig.NEW_ACTIVE == lay.active
    assert lay.root / mig.NEW_CLOSED == lay.closed


def test_moves_are_git_renames_so_history_follows(repo):
    mig.main(["--root", str(repo), "--execute"])
    status = _git(repo, "status", "--porcelain")
    assert "R  tracking/portfolio_config.json -> tracking/book/config.json" in status
    assert "R  tracking/601872.json -> tracking/book/active/601872.json" in status


def test_rerun_is_a_no_op(repo, capsys):
    assert mig.main(["--root", str(repo), "--execute"]) == 0
    after_first = _tree(repo)
    capsys.readouterr()

    assert mig.main(["--root", str(repo), "--execute"]) == 0

    assert _tree(repo) == after_first
    assert "already migrated" in capsys.readouterr().out


def test_rerun_moves_files_added_at_old_paths_since(repo):
    # the live pipeline commits to master at the OLD paths until the merge
    mig.main(["--root", str(repo), "--execute"])
    _dump(repo / "tracking" / "600519.json", _position("600519"))
    _dump(repo / "tracking" / "closed" / "601872_2026-10-13.json",
          _position("601872", "closed"))

    assert mig.main(["--root", str(repo), "--execute"]) == 0

    lay = Layout(repo / "tracking")
    assert (lay.active / "600519.json").exists()
    assert (lay.closed / "601872_2026-10-13.json").exists()
    assert not (repo / "tracking" / "600519.json").exists()


def test_old_copy_identical_to_new_is_dropped(repo):
    mig.main(["--root", str(repo), "--execute"])
    lay = Layout(repo / "tracking")
    (repo / "tracking" / "events.json").write_bytes(lay.events.read_bytes())

    assert mig.main(["--root", str(repo), "--execute"]) == 0

    assert not (repo / "tracking" / "events.json").exists()
    assert lay.events.exists()


def test_refuses_when_old_and_new_differ_and_changes_nothing(repo, capsys):
    lay = Layout(repo / "tracking")
    _dump(lay.positions, {"activePositions": [{"code": "999999"}]})   # differs
    before = _tree(repo)

    assert mig.main(["--root", str(repo), "--execute"]) == 2

    assert _tree(repo) == before
    out = capsys.readouterr()
    assert "CONFLICT" in out.out and "positions.json" in out.out
    assert "nothing changed" in out.err


def test_refuses_on_a_root_file_with_no_rule(repo, capsys):
    (repo / "tracking" / "notes.txt").write_text("?", encoding="utf-8")
    _dump(repo / "tracking" / "scratch.json", {"not": "a position"})
    before = _tree(repo)

    assert mig.main(["--root", str(repo), "--execute"]) == 2

    assert _tree(repo) == before
    out = capsys.readouterr().out
    assert "notes.txt" in out and "scratch.json" in out


def test_dry_run_changes_nothing(repo, capsys):
    before = _tree(repo)
    assert mig.main(["--root", str(repo)]) == 0
    assert _tree(repo) == before
    assert "dry run" in capsys.readouterr().out
