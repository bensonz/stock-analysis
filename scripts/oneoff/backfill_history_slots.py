#!/usr/bin/env python3
"""Backfill `slot` (noon/afternoon) onto position history written before
2026-08-11, when only the DATE was recorded and a same-day noon-vs-afternoon
fill was indistinguishable.

Truth source: each run's own output/daily_summary.json lists the actions that
run took, so (date, slot) → {(code, action)} is a fact on disk, not a guess.
Legacy pre-slot runs (runs/<date>/output/) are implicit afternoon per CLAUDE.md.

Idempotent: entries that already carry `slot` are left alone; entries with no
matching run artifact are left WITHOUT a slot (visible gap beats a guess —
see the null-visibility rule).

    python3 scripts/backfill_history_slots.py [--dry-run]
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"
TRACKING_DIR = PROJECT_ROOT / "tracking"
CLOSED_DIR = TRACKING_DIR / "closed"

SKIP_FILES = {"positions.json", "portfolio_config.json", "events.json",
              "hypotheses.json", "rotation_ledger.json"}


def build_action_index() -> dict:
    """(date, code, ACTION) → slot, from every run's daily_summary.json."""
    index = {}
    for day_dir in sorted(RUNS_DIR.iterdir()):
        if not day_dir.is_dir():
            continue
        date = day_dir.name
        candidates = []
        legacy = day_dir / "output" / "daily_summary.json"
        if legacy.exists():
            candidates.append((legacy, "afternoon"))  # pre-slot = afternoon
        for slot_dir in sorted(day_dir.iterdir()):
            f = slot_dir / "output" / "daily_summary.json"
            if slot_dir.is_dir() and f.exists():
                candidates.append((f, slot_dir.name))
        # Chronological, NOT alphabetical: "afternoon" < "noon" as strings
        # (CLAUDE.md's trap). Repeatable actions (HOLD/RAISE_STOP) appear in
        # both slots — 31 such keys on 2026-08-11 — and the pre-backfill
        # history kept the LAST writer (dedup was date+action), so the later
        # run must win here too. OPEN/SELL never collide (verified: 0 cases).
        candidates.sort(key=lambda c: 0 if c[1] == "legacy" else
                        (1 if c[1] == "noon" else 2))
        for path, slot in candidates:
            try:
                summary = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for a in summary.get("actions", []) or []:
                code = str(a.get("code", "")).split(".")[0]
                action = str(a.get("action", "") or "").upper()
                if code and action:
                    index[(date, code, action)] = slot  # later slot overwrites
            for np in summary.get("newPositions", []) or []:
                code = str(np.get("code", "")).split(".")[0]
                if code:
                    index[(date, code, "OPEN")] = slot
    return index


def backfill(dry_run: bool = False) -> dict:
    index = build_action_index()
    stats = {"files": 0, "entries_tagged": 0, "entries_unmatched": 0,
             "entry_slot": 0, "exit_slot": 0}
    files = [f for f in sorted(TRACKING_DIR.glob("*.json"))
             if f.name not in SKIP_FILES] + sorted(CLOSED_DIR.glob("*.json"))
    for f in files:
        try:
            pos = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(pos, dict) or not pos.get("code"):
            continue
        code = str(pos["code"]).split(".")[0]
        changed = False
        for h in pos.get("history", []) or []:
            if h.get("slot") or not h.get("date"):
                continue
            action = str(h.get("action", "") or "").upper()
            slot = index.get((h["date"], code, action))
            if slot:
                # keep key order readable: slot right after date
                items = list(h.items())
                h.clear()
                for k, v in items:
                    h[k] = v
                    if k == "date":
                        h["slot"] = slot
                stats["entries_tagged"] += 1
                changed = True
            else:
                stats["entries_unmatched"] += 1
        if not pos.get("entrySlot") and pos.get("entryDate"):
            slot = index.get((pos["entryDate"], code, "OPEN"))
            if slot:
                pos["entrySlot"] = slot
                stats["entry_slot"] += 1
                changed = True
        if not pos.get("exitSlot") and pos.get("exitDate"):
            slot = (index.get((pos["exitDate"], code, "SELL"))
                    or index.get((pos["exitDate"], code, "CLOSE")))
            if slot:
                pos["exitSlot"] = slot
                stats["exit_slot"] += 1
                changed = True
        if changed:
            stats["files"] += 1
            if not dry_run:
                f.write_text(json.dumps(pos, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
    return stats


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    s = backfill(dry_run=dry)
    print(f"{'[dry-run] ' if dry else ''}files changed: {s['files']} | "
          f"history entries tagged: {s['entries_tagged']} "
          f"(unmatched, left blank: {s['entries_unmatched']}) | "
          f"entrySlot: {s['entry_slot']} | exitSlot: {s['exit_slot']}")
