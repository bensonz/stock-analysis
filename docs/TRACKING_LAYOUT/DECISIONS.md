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

Owner confirmed 2026-10-13: keep rolling back LEARNINGS.md. A reset means the
runs after the target went wrong, so lessons written by those runs are suspect
too; restoring the target's copy keeps reruns consistent. (Git still holds the
discarded version if one of those lessons was worth keeping.)

## D6: Snapshot format unchanged

`snapshot_positions` still writes `closed_positions` keyed by code. Nothing
restores from it now; only `check_snapshot_consistency` counts it, and it
compares like with like. Rekeying would raise a false "closed positions
changed" warning on the next run. Revisit in stage 2 if wanted.

## D7: Not fixed — `--slot noon` keeps that date's afternoon run dir

`reset_to_date` deletes `runs/` dirs whose date is after the target only.
After a noon reset, `runs/<target>/afternoon/` stays. Deleting run data was
not asked for; recorded in RUNBOOK and reported.

## D8 (2026-10-12, stage 2): One path module; modules still bind names at import

**Chosen**: `scripts/tracking_paths.py` names every tracking/ path once
(`Layout(root)` + module constants for the live tree). Each user imports the
names it needs (`from tracking_paths import ACTIVE_DIR`), as before with its
own constants, so tests repoint them per module exactly as they did.

**Rejected**: every call site reading `tracking_paths.X` at call time, so one
patch redirects all modules. It would close the 2026-08-19 class of leak
(patched one path, forgot another) for good, but it changes the idiom of ~25
modules and every test fixture in one stage. The root conftest guard (D12
below) already makes such a leak fail the run. Revisit if a leak recurs.

Tools that take a `tracking_dir` argument (build_site, contracts, research/*)
keep it as the tracking/ ROOT and derive sub-paths through `Layout`, so their
signatures did not change.

## D9: The book restore moves into position_manager

`ResetError`, `plan_book_restore`, `apply_book_restore` and the snapshot
validation moved from run_daily to position_manager; run_daily imports them
(so `run_daily.plan_book_restore` still works). Why: TRACKER_SCHEMA rule 1
("position_manager is the only writer") listed `--reset-to` as a violation,
and the reset's writes already went through `position_manager._write_json`.
With the plan in the same module as the paths it touches, the reset tests
patch one module's book paths, not two (stage 1 patched pm AND run_daily —
the double binding that caused 2026-08-19). run_daily keeps the CLI, the run
dir cleanup and the hypotheses/LEARNINGS aux restore (not book state).
`snapshot_positions` stays in run_daily: it only reads.

## D10: Reset order is book → aux → run-dir deletes

Stage 1 deleted the later `runs/` dirs before `apply_book_restore`. If a book
write then failed, the later runs (with their snapshots) were gone, and the
book was half-written. Now the run dirs go last. A failed write leaves them
on disk; the reset can be re-run. Test:
`test_book_is_written_before_later_run_dirs_are_deleted`.

## D11: A non-position file in book/active/ aborts the reset

Before, the root glob had to skip non-position files (ledgers lived there).
book/active/ holds positions only, so a file there that is not a position is
a defect: `plan_book_restore` raises `ResetError` (exit 1, nothing changed)
instead of skipping it. Readers (`load_active_positions`, validator,
contracts, build_site) still skip such a file — they must not crash the run
over it. `is_position_record` stays the shared test (D4).

## D12: The conftest guard hashes the whole tracking/ tree

`scripts/live_state_guard.py` hashes every file under tracking/, any depth.
The old guard listed six names plus `tracking/[0-9]*.json` and
`tracking/closed/*.json`; `predictions.jsonl` and `rotation_ledger.json` were
never covered, and after the move the globs would match nothing. A whole-tree
hash needs no list to keep in sync, and it still trips on a leaked OLD path
(`tracking/{code}.json`). It does not import tracking_paths on purpose: a
guard that reads the writers' path table shares its mistakes.

## D13: The doctor needs no ARTIFACT_EPOCHS entry

Checked every read in `doctor.py`: it reads `runs/<date>/<slot>/` only
(manifest, daily_summary, positions_snapshot, report, input/db_health,
input/event_inbox) and `audit/ACCEPTED.md`. It never reads tracking/ and does
not import position_manager or tracking_paths. The snapshot format did not
change. So no judgement depends on the layout at the time of a run, and an
epoch entry would gate nothing. Changed: only the human text that names the
inbox path in two findings (`fix_cmd` / `detail`) — it tells the owner where
to edit NOW. Pinned by
`test_runs_from_before_the_layout_move_are_judged_from_their_own_artifacts`
(records every file the audit reads; none is under tracking/; no import).

Also checked: no code reads tracking/ at old git revisions (`git show
<rev>:tracking/...` / `git log -- tracking/...`) — the only `git` calls are
run_daily's commit/push and a comment in research/win_rate.py. So no old-path
fallback is needed anywhere.

## D14: portfolio_config.json → book/config.json (renamed)

No trouble found: one reader (`load_portfolio_config`), build_site's
inception anchor, the reset. The snapshot key stays `portfolio_config` (D6:
format unchanged), so old snapshots restore into `book/config.json`.

## D15: tracking/daily/ and its fallbacks are gone

`tracking/daily/` was empty since ef461f8 (2026-03-05) and not in git; only
`position_manager`'s import-time mkdir kept it alive on disk.
`save_daily_summary` now requires `output_dir` (its one pipeline caller
always passed it), and validator's `tracking/daily/{date}.json` fallback is
removed. agents/EVOLVER.md listed `tracking/daily/` — now
`runs/*/*/output/daily_summary.json`.

## D16: Gate-3 tests no longer read the live book

`tests/test_contracts.py` TestPhase3Gate/TestEndToEnd and one corporate
actions test called `validate_phase3_gate` with the default tracking dir,
i.e. they compared the LIVE positions.json with the live active files. They
passed or failed with whatever the pipeline held that day (they failed on the
code commit before the data moved). They now point `contracts.LIVE` at an
empty temp book. Live-data census tests (`test_data_hygiene`) still read the
live `book/closed/` on purpose.

## D17: Code and data in separate commits; the data move is a script

The live pipeline commits to master at the OLD paths until the merge. So the
code commit, the migrate script commit and the data-move commit are separate,
and the data move is `scripts/oneoff/migrate_tracking_layout.py` (git mv;
re-runnable; refuses on old+new with different content or on an unknown root
file). At merge time: merge the code and script commits, run the script on
master's current tracking/, commit that. Between the code commit and the data
commit the tree is inconsistent (two live-census tests fail; the pipeline
would see an empty book) — never deploy one without the other.
