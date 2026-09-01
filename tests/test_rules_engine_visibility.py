"""A crashed sell-discipline check must never read as "no violations".

Audit A3 / top-10 #7, two layers of the same silence:

1. run_rules.py: a rule script exits 1 both for "violations found" AND for an
   unhandled traceback; stderr was nulled whenever returncode was 0/1, and
   non-JSON stdout became {"raw_output": ...} → violations=[] — so a crashed
   check_stop_proximity reported status "violations" with an empty list and
   an unchanged total. The stop-watching layer could die and the log stays
   clean.
2. run_daily's post-apply check wrapped run_all_rules() in
   `except Exception: pass` — the engine itself crashing produced nothing at
   all.

Contract pinned here: crash ≠ clean. A rule whose stdout is not valid JSON
with a violations list is status "error", carries the evidence, and bumps a
crashed_rules counter that downstream surfaces loudly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import run_rules


def _fake_proc(returncode=1, stdout="", stderr=""):
    class P:
        pass
    p = P(); p.returncode = returncode; p.stdout = stdout; p.stderr = stderr
    return p


def test_valid_violation_output_still_counts(monkeypatch, tmp_path):
    rule = tmp_path / "check_x.py"; rule.write_text("#", encoding="utf-8")
    monkeypatch.setattr(run_rules, "RULES_DIR", tmp_path)
    monkeypatch.setattr(run_rules.subprocess, "run",
                        lambda *a, **k: _fake_proc(1, '{"violations": [{"code": "600000"}]}'))
    out = run_rules.run_all_rules(portfolio_data={"activePositions": []})
    assert out["total_violations"] == 1
    assert out["crashed_rules"] == 0
    assert out["rules"][0]["status"] == "violations"


def test_a_traceback_is_an_error_not_an_empty_violation_list(monkeypatch, tmp_path):
    """The exact dark mode: exit 1 + traceback on stderr + non-JSON stdout.
    Old code: status "violations", violations=[], error nulled. Silence."""
    rule = tmp_path / "check_x.py"; rule.write_text("#", encoding="utf-8")
    monkeypatch.setattr(run_rules, "RULES_DIR", tmp_path)
    monkeypatch.setattr(run_rules.subprocess, "run",
                        lambda *a, **k: _fake_proc(1, "", "Traceback (most recent call last): boom"))
    out = run_rules.run_all_rules(portfolio_data={"activePositions": []})
    assert out["rules"][0]["status"] == "error"
    assert "Traceback" in out["rules"][0]["error"]
    assert out["crashed_rules"] == 1


def test_clean_pass_is_still_clean(monkeypatch, tmp_path):
    rule = tmp_path / "check_x.py"; rule.write_text("#", encoding="utf-8")
    monkeypatch.setattr(run_rules, "RULES_DIR", tmp_path)
    monkeypatch.setattr(run_rules.subprocess, "run",
                        lambda *a, **k: _fake_proc(0, '{"violations": []}'))
    out = run_rules.run_all_rules(portfolio_data={"activePositions": []})
    assert out["crashed_rules"] == 0
    assert out["rules"][0]["status"] == "ok"


def test_garbage_stdout_with_exit_zero_is_also_an_error(monkeypatch, tmp_path):
    """Exit 0 with unparseable stdout means the check did not actually run its
    protocol — that is not a pass."""
    rule = tmp_path / "check_x.py"; rule.write_text("#", encoding="utf-8")
    monkeypatch.setattr(run_rules, "RULES_DIR", tmp_path)
    monkeypatch.setattr(run_rules.subprocess, "run",
                        lambda *a, **k: _fake_proc(0, "print debugging leftovers"))
    out = run_rules.run_all_rules(portfolio_data={"activePositions": []})
    assert out["rules"][0]["status"] == "error"
    assert out["crashed_rules"] == 1
