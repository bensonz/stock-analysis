"""Root pytest config: guard the live portfolio books against test leakage.

Test files live in two trees (``tests/`` and ``scripts/``), so this sits at
the rootdir where pytest loads it for both.

Why it exists: tests are supposed to work in temp dirs, but several modules
reassign ``position_manager``'s module-level paths (POSITIONS_FILE,
TRACKING_DIR) as globals. One leaked global points a write at the real
books. On 2026-08-14 a full-suite run that had failures left
tracking/positions.json regenerated with zeroed marks — equity 982,049 →
948,487, unrealized 33,562 → 0 — silently. It was caught only because
``git status`` happened to be read afterwards; a run that ended with a
commit would have shipped corrupted books.

The guard makes that class of accident loud instead of silent. It does not
fix the underlying global-reassignment pattern.

2026-08-19: proven necessary a second time, and widened. A test patched
``TRACKING_DIR`` but not ``CLOSED_DIR`` (bound at import from the former —
patching one does not rebind the other) and wrote two synthetic closed
trades into the LIVE tracking/closed/. This guard did not fire because it
only watched four named files. It now also fingerprints every position
file in tracking/ and tracking/closed/ — the books are the books.
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
