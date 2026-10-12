"""The root conftest guard must trip on a write to ANY live tracking/ path.

It hashes every file under tracking/ (scripts/live_state_guard.py). These
tests build a tmp project root in the 2026-10-12 layout and check that a
change to each state file, a position file in book/active/ or book/closed/,
an added file and a deleted file are all reported.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from live_state_guard import changed_paths, state_digest
from tracking_paths import Layout


@pytest.fixture
def root(tmp_path):
    lay = Layout(tmp_path / "tracking").make_dirs()
    for f in lay.files():
        f.write_text("{}\n", encoding="utf-8")
    (lay.active / "600001.json").write_text('{"code": "600001"}', encoding="utf-8")
    (lay.closed / "600002_2026-10-09.json").write_text('{"code": "600002"}', encoding="utf-8")
    (lay.root / "README.md").write_text("# tracking\n", encoding="utf-8")
    return tmp_path


def _rel(root, path):
    return str(path.relative_to(root))


@pytest.mark.parametrize("name", [
    "positions", "config", "hypotheses", "predictions", "rotation_ledger",
    "events", "event_inbox", "event_inbox_ledger",
])
def test_a_write_to_each_state_file_trips_the_guard(root, name):
    target = getattr(Layout(root / "tracking"), name)
    before = state_digest(root)
    target.write_text(json.dumps({"changed": True}), encoding="utf-8")
    assert changed_paths(before, state_digest(root)) == [_rel(root, target)]


def test_every_fixed_state_file_is_covered(root):
    """Layout.files() is the full list of fixed-name state files."""
    lay = Layout(root / "tracking")
    digest = state_digest(root)
    assert all(_rel(root, f) in digest for f in lay.files())
    assert len(lay.files()) == 8


@pytest.mark.parametrize("sub", ["active", "closed"])
def test_a_write_to_a_position_file_trips_the_guard(root, sub):
    d = getattr(Layout(root / "tracking"), sub)
    f = sorted(d.glob("*.json"))[0]
    before = state_digest(root)
    f.write_text('{"code": "x"}', encoding="utf-8")
    assert changed_paths(before, state_digest(root)) == [_rel(root, f)]


def test_an_added_position_file_trips_the_guard(root):
    lay = Layout(root / "tracking")
    before = state_digest(root)
    new = lay.active / "600003.json"
    new.write_text('{"code": "600003"}', encoding="utf-8")
    assert changed_paths(before, state_digest(root)) == [_rel(root, new)]


def test_a_deleted_closed_trade_trips_the_guard(root):
    lay = Layout(root / "tracking")
    gone = lay.closed / "600002_2026-10-09.json"
    before = state_digest(root)
    gone.unlink()
    assert changed_paths(before, state_digest(root)) == [_rel(root, gone)]


def test_a_write_to_an_old_layout_path_trips_the_guard_too(root):
    # a leaked pre-move path global would write tracking/{code}.json
    before = state_digest(root)
    stray = root / "tracking" / "600004.json"
    stray.write_text('{"code": "600004"}', encoding="utf-8")
    assert changed_paths(before, state_digest(root)) == [_rel(root, stray)]


def test_no_change_reports_nothing(root):
    assert changed_paths(state_digest(root), state_digest(root)) == []
