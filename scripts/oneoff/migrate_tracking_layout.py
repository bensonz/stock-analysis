#!/usr/bin/env python3
"""
migrate_tracking_layout.py — move tracking/ into book/ ledgers/ calendar/ (2026-10-12).

docs/TRACKING_LAYOUT stage 2. The code reads the new paths from
scripts/tracking_paths.py; this script moves the files there with `git mv`,
so history follows each file. Plain rename for a file git does not track.

    tracking/{code}.json           → tracking/book/active/{code}.json
    tracking/closed/*              → tracking/book/closed/*   (names unchanged,
                                     the 42 undated legacy names included)
    tracking/positions.json        → tracking/book/positions.json
    tracking/portfolio_config.json → tracking/book/config.json
    tracking/hypotheses.json       → tracking/ledgers/hypotheses.json
    tracking/predictions.jsonl     → tracking/ledgers/predictions.jsonl
    tracking/rotation_ledger.json  → tracking/ledgers/rotation_ledger.json
    tracking/events.json           → tracking/calendar/events.json
    tracking/event_inbox.md        → tracking/calendar/event_inbox.md
    tracking/event_inbox_ledger.json → tracking/calendar/event_inbox_ledger.json
    tracking/README.md             stays

Safe to re-run. Per file:
  - old there, new absent       → move
  - old there, new same bytes   → remove the old copy (an earlier run moved it)
  - old there, new different    → CONFLICT: refuse, change nothing, exit 2
  - old absent                  → nothing to do
It also refuses (exit 2, nothing changed) on any file at the tracking/ root it
has no rule for, so nothing is left behind at an old path unnoticed. A root
*.json goes to book/active/ only if it is a position record (code + status).

The move map lives here, not in tracking_paths: it is a fact about one move.
tests/test_migrate_tracking_layout.py pins that every target equals the
tracking_paths constant for it.

Usage (from the repo root; dry run by default):
    python3 scripts/oneoff/migrate_tracking_layout.py            # print the plan
    python3 scripts/oneoff/migrate_tracking_layout.py --execute  # do it (stages the moves)
    python3 scripts/oneoff/migrate_tracking_layout.py --root DIR # another checkout
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

#: fixed-name files, relative to tracking/
FIXED = {
    "positions.json": "book/positions.json",
    "portfolio_config.json": "book/config.json",
    "hypotheses.json": "ledgers/hypotheses.json",
    "predictions.jsonl": "ledgers/predictions.jsonl",
    "rotation_ledger.json": "ledgers/rotation_ledger.json",
    "events.json": "calendar/events.json",
    "event_inbox.md": "calendar/event_inbox.md",
    "event_inbox_ledger.json": "calendar/event_inbox_ledger.json",
}
STAYS = {"README.md"}
OLD_CLOSED = "closed"
NEW_CLOSED = "book/closed"
NEW_ACTIVE = "book/active"
NEW_DIRS = {"book", "ledgers", "calendar"}
#: empty since the 2026-03-05 runs/ migration; removed if still there and empty
OLD_EMPTY_DIRS = ("daily",)


class MigrationError(Exception):
    """The move cannot run safely. Raised before anything changes."""


def _is_position_record(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and bool(data.get("code")) and bool(data.get("status"))


def plan(root: Path) -> dict:
    """What a migration of root/tracking would do. Touches nothing.

    Returns {"move": [(old, new)], "drop_duplicate": [(old, new)],
             "conflict": [(old, new)], "unknown": [path]}.
    """
    t = root / "tracking"
    pairs = []
    unknown = []
    if not t.is_dir():
        raise MigrationError(f"{t} does not exist")
    for f in sorted(t.iterdir()):
        name = f.name
        if name.startswith("."):
            continue                      # .DS_Store and friends
        if f.is_dir():
            if name == OLD_CLOSED:
                pairs += [(c, t / NEW_CLOSED / c.name) for c in sorted(f.iterdir())
                          if not c.name.startswith(".")]
            elif name in NEW_DIRS or name in OLD_EMPTY_DIRS:
                continue
            else:
                unknown.append(f)
        elif name in FIXED:
            pairs.append((f, t / FIXED[name]))
        elif name in STAYS:
            continue
        elif f.suffix == ".json" and _is_position_record(f):
            pairs.append((f, t / NEW_ACTIVE / name))
        else:
            unknown.append(f)
    for d in OLD_EMPTY_DIRS:
        if (t / d).is_dir() and any(p for p in (t / d).iterdir() if not p.name.startswith(".")):
            unknown.append(t / d)

    out = {"move": [], "drop_duplicate": [], "conflict": [], "unknown": unknown}
    for old, new in pairs:
        if not new.exists():
            out["move"].append((old, new))
        elif new.read_bytes() == old.read_bytes():
            out["drop_duplicate"].append((old, new))
        else:
            out["conflict"].append((old, new))
    return out


def _tracked(root: Path, path: Path) -> bool:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(path.relative_to(root))],
                       cwd=root, capture_output=True, text=True)
    return r.returncode == 0


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def execute(root: Path, p: dict) -> None:
    """Apply a plan from plan(). Refuses a plan with conflicts or unknowns."""
    if p["conflict"] or p["unknown"]:
        raise MigrationError("plan has conflicts or unknown files; nothing changed")
    for old, new in p["move"]:
        new.parent.mkdir(parents=True, exist_ok=True)
        if _tracked(root, old):
            _git(root, "mv", str(old.relative_to(root)), str(new.relative_to(root)))
        else:
            old.rename(new)
    for old, _new in p["drop_duplicate"]:
        if _tracked(root, old):
            _git(root, "rm", "-q", str(old.relative_to(root)))
        else:
            old.unlink()
    t = root / "tracking"
    for d in (OLD_CLOSED, *OLD_EMPTY_DIRS):
        dd = t / d
        if dd.is_dir():
            for junk in dd.glob(".*"):
                junk.unlink()
            if not any(dd.iterdir()):
                dd.rmdir()


def _print(root: Path, p: dict) -> None:
    def rel(x):
        return x.relative_to(root)
    print(f"move:            {len(p['move'])}")
    for old, new in p["move"]:
        print(f"  {rel(old)} → {rel(new)}")
    print(f"drop duplicate:  {len(p['drop_duplicate'])} (already at the new path, same bytes)")
    for old, new in p["drop_duplicate"]:
        print(f"  {rel(old)} (= {rel(new)})")
    if p["conflict"]:
        print(f"CONFLICT:        {len(p['conflict'])} (old and new both exist, different content)")
        for old, new in p["conflict"]:
            print(f"  {rel(old)} ≠ {rel(new)}")
    if p["unknown"]:
        print(f"UNKNOWN:         {len(p['unknown'])} (no rule for these; move them by hand)")
        for f in p["unknown"]:
            print(f"  {rel(f)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Move tracking/ into book/ ledgers/ calendar/.")
    ap.add_argument("--execute", action="store_true", help="do it (default: print the plan)")
    ap.add_argument("--root", default=str(PROJECT_ROOT), help="repo root (default: this checkout)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        p = plan(root)
    except MigrationError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2
    _print(root, p)
    if p["conflict"] or p["unknown"]:
        print("✗ refused, nothing changed. Resolve the lines above, then re-run.",
              file=sys.stderr)
        return 2
    if not p["move"] and not p["drop_duplicate"]:
        print("✓ already migrated, nothing to do")
        return 0
    if not args.execute:
        print("(dry run — pass --execute to apply)")
        return 0
    execute(root, p)
    print("✓ moved; review with `git status`, then commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
