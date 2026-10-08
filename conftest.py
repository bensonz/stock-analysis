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
fingerprints the four state files AND every position file, open and closed,
including additions and deletions. It makes the accident loud; it does not
fix the global-reassignment pattern.
"""
import hashlib
from pathlib import Path

import pytest

LIVE_STATE = (
    "tracking/positions.json",
    "tracking/events.json",
    "tracking/hypotheses.json",
    "tracking/portfolio_config.json",
)


def _state_digest():
    root = Path(__file__).resolve().parent
    digests = {}
    for rel in LIVE_STATE:
        f = root / rel
        digests[rel] = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
    # every position file, open and closed — additions and deletions count too
    for pat in ("tracking/[0-9]*.json", "tracking/closed/*.json"):
        for f in sorted(root.glob(pat)):
            digests[str(f.relative_to(root))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return digests


@pytest.fixture(scope="session", autouse=True)
def guard_live_tracking_state():
    before = _state_digest()
    yield
    after = _state_digest()
    changed = sorted({rel for rel in set(before) | set(after)
                      if before.get(rel) != after.get(rel)})
    if changed:
        pytest.fail(
            "tests mutated LIVE portfolio state: " + ", ".join(changed) + "\n"
            "Restore with `git checkout -- tracking/` and fix the leaked path "
            "global before trusting any result from this run.",
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
