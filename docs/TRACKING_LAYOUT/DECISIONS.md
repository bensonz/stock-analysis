# Tracking layout — decisions

## D1 (2026-10-12): Never rewrite closed trades on reset; delete by "not yet closed at the snapshot"

**Context**: The snapshot's `closed_positions` is a summary (no `history`,
`exitReason`, `shares`, `exitSlot`, dividends ...) keyed by `code`. Rebuilding
`closed/` from it loses fields and collapses repeat trades in one code.

**Options**:
- A. Store full closed records in snapshots. Fixes new snapshots only; the
  391 on disk would still restore lossy. Grows every snapshot.
- B. Keep the closed files that already exist; delete only the trades that
  were not closed yet at the snapshot. Works with every old snapshot.

**Chosen**: B. A closed file does not change after exit: `corporate_actions`
touches open positions only ("Closed trades in tracking/closed/ are never
restated"), and nothing else writes `closed/` except `close_position`. So the
file on disk IS the file at the snapshot, unless the trade was still open then.

**Rule** (`run_daily.plan_book_restore`), trade = (`code`, `entryDate`):
- `exitDate > target` → delete; the snapshot restores it if it was active.
- `exitDate == target` and the snapshot holds the trade active → delete (a
  noon snapshot; the afternoon run sold it). Restored active.
- otherwise keep, byte-for-byte.

We match on the snapshot, not on `exitSlot`: 5 of 65 closed files have no
`exitSlot`, and the input (pre-run) snapshot fallback is not "end of slot"
anyway. The snapshot is the one statement of what was open at that moment.

## D2: Fail loudly on contradictions, before any change

Abort (exit 1, "nothing changed") when: the snapshot is not JSON, misses
`active_positions` / `positions_json` / `portfolio_config`, or an active entry
is not an active position record keyed by its own code; a tracking `*.json`
or a closed file cannot be read; a closed file has no `exitDate`; a trade
closed before the target is still active in the snapshot; a trade held across
the target (entry before, exit after) is not in the snapshot (deleting it
would lose the trade with nothing to restore). Checked against all 391
snapshots on disk: none trips.

## D3: Writes first, deletes second; run dirs deleted only after the plan passes

The old code deleted later `runs/` dirs before it read the snapshot fully.
Now: load + validate + plan → print → delete runs → write book → delete book
files. An interrupted reset leaves an extra file, never a lost one. Writes go
through `position_manager._write_json` (atomic).

## D4: One shared position test

`position_manager.is_position_record(data)` = dict with truthy `code` and
`status`. Used by `load_active_positions`, `load_all_tracking_files`,
`snapshot_positions` and the reset. `validator.py` and `contracts.py` keep
their own inline checks on purpose: checks stay independent of the code they
audit (CLAUDE.md, audit layer rule 2).

`load_all_tracking_files` now returns position records only (before: any
dict, so events.json / hypotheses.json / portfolio_config.json leaked in).
Its only caller is a test.

## D5: Keep the hypotheses / LEARNINGS aux restore

`restore_aux_state` (pre-existing) copies `output/hypotheses_snapshot.json`
and `output/LEARNINGS.md` back when the run saved them — a deliberate
rollback for consistent reruns (`snapshot_aux_state`). It is not the data-loss
bug, so it stays; the plan names it as "Restore from the run's output/", and
those names are left out of the "NOT rolled back" line.

## D6: Snapshot format unchanged

`snapshot_positions` still writes `closed_positions` keyed by code. Nothing
restores from it now; only `check_snapshot_consistency` counts it, and it
compares like with like. Rekeying would raise a false "closed positions
changed" warning on the next run. Revisit in stage 2 if wanted.

## D7: Not fixed — `--slot noon` keeps that date's afternoon run dir

`reset_to_date` deletes `runs/` dirs whose date is after the target only.
After a noon reset, `runs/<target>/afternoon/` stays. Deleting run data was
not asked for; recorded in RUNBOOK and reported.
