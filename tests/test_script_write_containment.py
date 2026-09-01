"""LLM-authored scripts may only land inside scripts/rules/ — nowhere else.

Audit A2/top-10 #2: phase3_apply took `decisions["new_scripts"]` — model
output — and wrote it to ANY path under PROJECT_ROOT with mode 0755, after
which Phase 5's `git add -A` committed and pushed it. No allowlist, no
traversal rejection. `{"path": "agents/ANALYST.md"}` would overwrite the
strategy spec with model prose; `{"path": "../../.ssh/authorized_keys"}`
escapes the repo entirely (Path `/` joins do not constrain `..`). It was the
one place model output became executable code on the host unvalidated.

The contract pinned here: rule scripts live in scripts/rules/, are named
check_*.py, and anything else is REFUSED LOUDLY — logged, never written.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import run_daily


def allowed(rel):
    return run_daily.resolve_rule_script_path(rel, project_root=Path("/repo"))


def test_a_proper_rule_script_path_is_allowed():
    got = allowed("scripts/rules/check_volume_spike.py")
    assert got == Path("/repo/scripts/rules/check_volume_spike.py")


def test_traversal_out_of_the_repo_is_refused():
    with pytest.raises(ValueError, match="outside scripts/rules"):
        allowed("../../.ssh/authorized_keys")


def test_traversal_that_reenters_elsewhere_is_refused():
    with pytest.raises(ValueError, match="outside scripts/rules"):
        allowed("scripts/rules/../../agents/ANALYST.md")


def test_overwriting_the_strategy_spec_is_refused():
    with pytest.raises(ValueError, match="outside scripts/rules"):
        allowed("agents/ANALYST.md")


def test_absolute_paths_are_refused():
    with pytest.raises(ValueError, match="outside scripts/rules"):
        allowed("/etc/cron.d/backdoor")


def test_non_check_prefix_is_refused():
    """run_rules.py executes every check_*.py in that directory — the naming
    contract IS the execution contract, so a stray helper.py is refused too."""
    with pytest.raises(ValueError, match="check_"):
        allowed("scripts/rules/helper.py")


def test_non_python_extension_is_refused():
    with pytest.raises(ValueError, match="check_"):
        allowed("scripts/rules/check_thing.sh")
