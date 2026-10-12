"""Fingerprint of the live tracking/ tree — what the root conftest guard compares.

Every file under tracking/, at any depth: book/active, book/closed, the book
state files, ledgers/, calendar/, README. Additions and deletions count too.

Deliberately does NOT import tracking_paths. A guard that asks the writers'
own path table which files to watch shares that table's mistakes: before the
2026-10-12 layout move the guard listed six names plus two globs, and every
state file added since (predictions.jsonl, rotation_ledger.json) went
unwatched. Hashing the whole tree needs no list to keep in sync.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def state_digest(project_root: Path) -> dict[str, str]:
    """{path relative to project_root: sha256} for every file under tracking/."""
    tracking = Path(project_root) / "tracking"
    digests = {}
    if tracking.is_dir():
        for f in sorted(tracking.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(project_root))
                digests[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
    return digests


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """Paths whose content changed, plus paths added or removed."""
    return sorted(rel for rel in set(before) | set(after)
                  if before.get(rel) != after.get(rel))
