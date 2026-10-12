"""Root pytest configuration — the ONE owner of the integration-test gate.

Before 2026-09-01 this logic lived twice with incompatible mechanisms:
tests/conftest.py gated on a --run-integration option, scripts/conftest.py on
`-m integration`. Both hooks ran globally over all collected items, so the
documented command (`pytest --run-integration`) skipped all 12 integration
tests anyway, only the undocumented combination of BOTH flags ran them, and
`pytest scripts/ --run-integration` hard-errored because the option was
defined in a conftest pytest never loaded for that path. The 12 tests were
silently dead from 2026-05-13 — long enough for two of them to still call a
provider that was retired in August.

pytest only honours pytest_addoption in the ROOTDIR conftest, which is why
this file must exist and why the split version could never work. The two
sub-conftests keep only their sys.path setup.

It ALSO guards the live portfolio books (restored 2026-10-08). That guard
lived here from 2026-08-14 until the 2026-09-01 rewrite above replaced the
whole file and dropped it without a word — for five weeks nothing caught a
test writing to tracking/. Why it exists:

Tests are supposed to work in temp dirs, but several modules reassign
``position_manager``'s module-level paths (POSITIONS_FILE, TRACKING_DIR) as
globals. One leaked global points a write at the real books. On 2026-08-14 a
full-suite run left tracking/positions.json regenerated with zeroed marks —
equity 982,049 → 948,487 — silently. On 2026-08-19 a test patched
``TRACKING_DIR`` but not ``CLOSED_DIR`` (bound at import from the former) and
wrote two synthetic closed trades into the LIVE tracking/closed/. So it
fingerprints EVERY file under tracking/ (scripts/live_state_guard.py),
including additions and deletions. Until the 2026-10-12 layout move
(docs/TRACKING_LAYOUT) it watched six named files plus the
tracking/[0-9]*.json and tracking/closed/*.json globs — which left
predictions.jsonl and rotation_ledger.json unwatched, and would have watched
nothing in book/active/ after the move. It makes the accident loud; it does
not fix the global-reassignment pattern.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from live_state_guard import changed_paths, state_digest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def guard_live_tracking_state():
    before = state_digest(ROOT)
    yield
    changed = changed_paths(before, state_digest(ROOT))
    if changed:
        pytest.fail(
            "tests mutated LIVE portfolio state: " + ", ".join(changed) + "\n"
            "Restore with `git checkout -- tracking/` (and delete any added "
            "file) and fix the leaked path global before trusting any result "
            "from this run.",
            pytrace=False,
        )


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", action="store_true", default=False,
        help="Run integration tests that hit real external APIs",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: marks tests that hit real APIs (skipped without --run-integration)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return
    skip = pytest.mark.skip(reason="integration test: pass --run-integration to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
