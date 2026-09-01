"""tracking/ writes must be atomic — a crash mid-write may not eat a position.

Audit A6 (2026-08-31): zero locking or atomic writes anywhere in the repo,
bare truncate-then-write on every book artifact, and the two launchd jobs have
already fired simultaneously once (2026-08-26 sleep-deferral). The nastiest
consequence path: a torn tracking/{code}.json fails json.loads in
load_active_positions, the file is skipped, and the position VANISHES from the
book — cash recomputed as if it was never held. Not an error; an absence.

position_manager._write_json is the single choke point for nearly all book
mutations, so hardening this one function covers positions.json, every
tracking/{code}.json, closed/ moves and portfolio config in one move:
write to a temp file in the SAME directory, fsync, os.replace. POSIX rename
atomicity guarantees a reader sees the old bytes or the new bytes, never a
prefix of the new.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import position_manager as pm


def test_write_then_read_round_trips(tmp_path):
    p = tmp_path / "x.json"
    pm._write_json(p, {"code": "600000", "shares": 1600})
    assert json.loads(p.read_text(encoding="utf-8")) == {"code": "600000", "shares": 1600}


def test_a_failed_write_leaves_the_original_intact(tmp_path):
    """Honest scope note: even the OLD code survived this case (json.dumps
    raises before write_text runs), so this is a regression guard, not the
    motivating scenario. The scenario atomicity actually fixes — process
    killed mid-write syscall — cannot be simulated in-process; os.replace
    semantics are what carry that guarantee."""
    p = tmp_path / "x.json"
    pm._write_json(p, {"good": True})
    with pytest.raises(TypeError):
        pm._write_json(p, {"bad": object()})   # unserializable
    assert json.loads(p.read_text(encoding="utf-8")) == {"good": True}, (
        "original content was destroyed by a failed write")


def test_no_temp_debris_after_success_or_failure(tmp_path):
    p = tmp_path / "x.json"
    pm._write_json(p, {"a": 1})
    with pytest.raises(TypeError):
        pm._write_json(p, {"bad": object()})
    leftovers = [f for f in tmp_path.iterdir() if f.name != "x.json"]
    assert leftovers == [], f"temp files left behind: {leftovers}"


def test_replace_is_same_directory(tmp_path, monkeypatch):
    """os.replace is only atomic within a filesystem; the temp file must be
    created beside the target, not in /tmp (which can be a different mount)."""
    p = tmp_path / "sub" / "x.json"
    p.parent.mkdir()
    seen = {}
    real_replace = pm.os.replace

    def spy(src, dst):
        seen["src_dir"] = Path(src).parent
        return real_replace(src, dst)

    monkeypatch.setattr(pm.os, "replace", spy)
    pm._write_json(p, {"a": 1})
    assert seen["src_dir"] == p.parent
